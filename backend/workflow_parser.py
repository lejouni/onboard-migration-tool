"""
GitHub Actions Workflow YAML Parser and Manipulator
Handles parsing, analyzing, and modifying workflow YAML structure
"""

import yaml
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import re


# Custom YAML loader to preserve 'on' as a string key (not convert to True)
class WorkflowYAMLLoader(yaml.SafeLoader):
    pass

# Remove 'on', 'off', 'yes', 'no' from boolean resolution
for ch in "OoYyNn":
    if ch in WorkflowYAMLLoader.yaml_implicit_resolvers:
        WorkflowYAMLLoader.yaml_implicit_resolvers[ch] = [
            (tag, regexp) for tag, regexp in WorkflowYAMLLoader.yaml_implicit_resolvers[ch]
            if tag != 'tag:yaml.org,2002:bool'
        ]


# Custom YAML dumper to handle 'on' key properly (don't convert to 'true')
class WorkflowYAMLDumper(yaml.SafeDumper):
    def write_line_break(self, data=None):
        super().write_line_break(data)
    
    def increase_indent(self, flow=False, indentless=False):
        return super().increase_indent(flow, False)

def represent_str(dumper, data):
    # Always use literal style for multi-line strings to preserve formatting
    if '\n' in data:
        # Strip trailing whitespace from each line but preserve structure
        lines = data.split('\n')
        cleaned_data = '\n'.join(line.rstrip() for line in lines)
        # Use literal block style (|) for multi-line strings
        return dumper.represent_scalar('tag:yaml.org,2002:str', cleaned_data, style='|')
    # Use plain style for single-line strings (no quotes unless necessary)
    return dumper.represent_scalar('tag:yaml.org,2002:str', data)

WorkflowYAMLDumper.add_representer(str, represent_str)


@dataclass
class WorkflowJob:
    """Represents a job in a GitHub Actions workflow"""
    name: str
    runs_on: str
    steps: List[Dict[str, Any]]
    needs: Optional[List[str]] = None
    if_condition: Optional[str] = None
    strategy: Optional[Dict[str, Any]] = None
    environment: Optional[str] = None


@dataclass
class WorkflowStructure:
    """Represents the parsed structure of a workflow"""
    name: str
    on_triggers: Dict[str, Any]
    jobs: Dict[str, WorkflowJob]
    env: Optional[Dict[str, str]] = None
    defaults: Optional[Dict[str, Any]] = None


@dataclass
class InsertionPoint:
    """Represents where a new job can be inserted"""
    location: str  # "after_build", "after_test", "end"
    after_job: Optional[str]  # Job ID to insert after
    reasoning: str


class WorkflowParser:
    """Parse and manipulate GitHub Actions workflow YAML"""
    
    # Patterns for detecting step types
    BUILD_PATTERNS = [
        r'mvn.*(?:compile|package|install)',
        r'gradle.*(?:build|assemble)',
        r'npm.*(?:run.*build|build)',
        r'dotnet.*build',
        r'go.*build',
        r'cargo.*build',
        r'make(?:\s|$)'
    ]
    
    TEST_PATTERNS = [
        r'mvn.*test',
        r'gradle.*test',
        r'npm.*(?:run.*test|test)',
        r'dotnet.*test',
        r'go.*test',
        r'cargo.*test',
        r'pytest',
        r'jest',
        r'run.*tests?'
    ]
    
    SECURITY_TOOL_PATTERNS = [
        r'polaris',
        r'coverity',
        r'blackduck',
        r'black.*duck',
        r'codeql',
        r'snyk',
        r'sonarqube',
        r'owasp'
    ]
    
    def __init__(self):
        pass
    
    def parse_workflow(self, content: str) -> WorkflowStructure:
        """Parse workflow YAML content into structured format"""
        try:
            workflow_dict = yaml.safe_load(content)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML: {e}")
        
        if not isinstance(workflow_dict, dict):
            raise ValueError("Workflow YAML must be a dictionary")
        
        # Extract workflow name
        name = workflow_dict.get('name', 'Unnamed Workflow')
        
        # Extract triggers
        on_triggers = workflow_dict.get('on', {})
        if isinstance(on_triggers, str):
            on_triggers = {on_triggers: {}}
        
        # Extract environment variables
        env = workflow_dict.get('env', None)
        
        # Extract defaults
        defaults = workflow_dict.get('defaults', None)
        
        # Parse jobs
        jobs = {}
        jobs_dict = workflow_dict.get('jobs', {})
        
        for job_id, job_config in jobs_dict.items():
            if not isinstance(job_config, dict):
                continue
            
            jobs[job_id] = WorkflowJob(
                name=job_config.get('name', job_id),
                runs_on=job_config.get('runs-on', 'ubuntu-latest'),
                steps=job_config.get('steps', []),
                needs=job_config.get('needs', None),
                if_condition=job_config.get('if', None),
                strategy=job_config.get('strategy', None),
                environment=job_config.get('environment', None)
            )
        
        return WorkflowStructure(
            name=name,
            on_triggers=on_triggers,
            jobs=jobs,
            env=env,
            defaults=defaults
        )
    
    def analyze_workflow(self, content: str, file_name: str = "workflow.yml") -> Dict[str, Any]:
        """
        Analyze workflow structure and return comprehensive analysis
        
        Returns:
            Dictionary with:
            - has_jobs: bool
            - job_count: int
            - jobs: Dict[job_id, job_info]
            - has_build_job: bool
            - has_test_job: bool
            - has_security_scan: bool
            - build_tools: List[str]
            - languages: List[str]
            - security_tools: List[str]
            - triggers: Dict
            - has_pr_trigger: bool
            - insertion_points: List[InsertionPoint]
        """
        structure = self.parse_workflow(content)
        
        # Initialize analysis results
        analysis = {
            'file_name': file_name,
            'workflow_name': structure.name,
            'has_jobs': len(structure.jobs) > 0,
            'job_count': len(structure.jobs),
            'jobs': {},
            'has_build_job': False,
            'has_test_job': False,
            'has_security_scan': False,
            'build_tools': [],
            'languages': [],
            'security_tools': [],
            'triggers': structure.on_triggers,
            'has_pr_trigger': False,
            'insertion_points': []
        }
        
        # Check for PR trigger
        analysis['has_pr_trigger'] = self.has_pr_trigger(structure.on_triggers)
        
        # Analyze each job
        for job_id, job in structure.jobs.items():
            job_analysis = self._analyze_job(job)
            analysis['jobs'][job_id] = job_analysis
            
            # Update workflow-level flags
            if job_analysis['has_build_steps']:
                analysis['has_build_job'] = True
            if job_analysis['has_test_steps']:
                analysis['has_test_job'] = True
            if job_analysis['has_security_scan']:
                analysis['has_security_scan'] = True
            
            # Collect unique build tools, languages, security tools
            for tool in job_analysis['build_tools']:
                if tool not in analysis['build_tools']:
                    analysis['build_tools'].append(tool)
            
            for lang in job_analysis['languages']:
                if lang not in analysis['languages']:
                    analysis['languages'].append(lang)
            
            for sec_tool in job_analysis['security_tools']:
                if sec_tool not in analysis['security_tools']:
                    analysis['security_tools'].append(sec_tool)
        
        # Find insertion points
        analysis['insertion_points'] = [
            {
                'location': point.location,
                'after_job': point.after_job,
                'reasoning': point.reasoning
            }
            for point in self._find_insertion_points(structure)
        ]
        
        return analysis
    
    def _analyze_job(self, job: WorkflowJob) -> Dict[str, Any]:
        """Analyze a single job"""
        job_info = {
            'name': job.name,
            'runs_on': job.runs_on,
            'step_count': len(job.steps),
            'has_build_steps': False,
            'has_test_steps': False,
            'has_security_scan': False,
            'build_tools': [],
            'languages': [],
            'security_tools': [],
            'steps': []
        }
        
        for step in job.steps:
            step_analysis = self._analyze_step(step)
            job_info['steps'].append(step_analysis)
            
            if step_analysis['is_build_step']:
                job_info['has_build_steps'] = True
            if step_analysis['is_test_step']:
                job_info['has_test_steps'] = True
            if step_analysis['is_security_scan']:
                job_info['has_security_scan'] = True
            
            # Collect tools and languages
            if step_analysis['build_tool'] and step_analysis['build_tool'] not in job_info['build_tools']:
                job_info['build_tools'].append(step_analysis['build_tool'])
            
            if step_analysis['language'] and step_analysis['language'] not in job_info['languages']:
                job_info['languages'].append(step_analysis['language'])
            
            if step_analysis['security_tool'] and step_analysis['security_tool'] not in job_info['security_tools']:
                job_info['security_tools'].append(step_analysis['security_tool'])
        
        return job_info
    
    def _analyze_step(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze a single step"""
        step_info = {
            'name': step.get('name', 'Unnamed step'),
            'uses': step.get('uses', None),
            'run': step.get('run', None),
            'is_build_step': False,
            'is_test_step': False,
            'is_security_scan': False,
            'build_tool': None,
            'language': None,
            'security_tool': None
        }
        
        # Analyze run commands
        if step_info['run']:
            run_text = str(step_info['run']).lower()
            
            # Check for build patterns
            for pattern in self.BUILD_PATTERNS:
                if re.search(pattern, run_text):
                    step_info['is_build_step'] = True
                    step_info['build_tool'] = self._extract_build_tool(run_text)
                    break
            
            # Check for test patterns
            for pattern in self.TEST_PATTERNS:
                if re.search(pattern, run_text):
                    step_info['is_test_step'] = True
                    break
            
            # Check for security tools
            for pattern in self.SECURITY_TOOL_PATTERNS:
                if re.search(pattern, run_text):
                    step_info['is_security_scan'] = True
                    step_info['security_tool'] = self._extract_security_tool(run_text)
                    break
        
        # Analyze uses (actions)
        if step_info['uses']:
            uses_text = str(step_info['uses']).lower()
            
            # Detect language from setup actions
            step_info['language'] = self._detect_language_from_action(uses_text)
            
            # Check for security tool actions
            for pattern in self.SECURITY_TOOL_PATTERNS:
                if re.search(pattern, uses_text):
                    step_info['is_security_scan'] = True
                    step_info['security_tool'] = self._extract_security_tool(uses_text)
                    break
        
        return step_info
    
    def _extract_build_tool(self, text: str) -> Optional[str]:
        """Extract build tool from text"""
        if 'mvn' in text or 'maven' in text:
            return 'maven'
        elif 'gradle' in text:
            return 'gradle'
        elif 'npm' in text:
            return 'npm'
        elif 'dotnet' in text:
            return 'dotnet'
        elif 'go' in text and 'build' in text:
            return 'go'
        elif 'cargo' in text:
            return 'cargo'
        elif 'make' in text:
            return 'make'
        return None
    
    def _extract_security_tool(self, text: str) -> Optional[str]:
        """Extract security tool from text"""
        if 'polaris' in text:
            return 'polaris'
        elif 'coverity' in text:
            return 'coverity'
        elif 'blackduck' in text or 'black-duck' in text:
            return 'blackduck'
        elif 'codeql' in text:
            return 'codeql'
        elif 'snyk' in text:
            return 'snyk'
        elif 'sonarqube' in text or 'sonar' in text:
            return 'sonarqube'
        return None
    
    def _detect_language_from_action(self, action: str) -> Optional[str]:
        """Detect programming language from GitHub action"""
        if 'setup-java' in action:
            return 'java'
        elif 'setup-python' in action:
            return 'python'
        elif 'setup-node' in action:
            return 'javascript'
        elif 'setup-dotnet' in action:
            return 'csharp'
        elif 'setup-go' in action:
            return 'go'
        elif 'setup-ruby' in action:
            return 'ruby'
        return None
    
    def _find_insertion_points(self, structure: WorkflowStructure) -> List[InsertionPoint]:
        """Find optimal insertion points for new jobs"""
        insertion_points = []
        
        # Strategy: Insert after build, or after test, or at end
        build_job = None
        test_job = None
        last_job = None
        
        for job_id, job in structure.jobs.items():
            last_job = job_id
            
            # Check if this is a build job
            if any(re.search(pattern, ' '.join([str(s.get('run', '')) for s in job.steps]).lower()) 
                   for pattern in self.BUILD_PATTERNS):
                build_job = job_id
            
            # Check if this is a test job
            if any(re.search(pattern, ' '.join([str(s.get('run', '')) for s in job.steps]).lower()) 
                   for pattern in self.TEST_PATTERNS):
                test_job = job_id
        
        # Preferred: after build job
        if build_job:
            insertion_points.append(InsertionPoint(
                location="after_build",
                after_job=build_job,
                reasoning="Security scanning should run after build to analyze compiled code"
            ))
        
        # Alternative: after test job
        if test_job and test_job != build_job:
            insertion_points.append(InsertionPoint(
                location="after_test",
                after_job=test_job,
                reasoning="Security scanning can run in parallel with or after tests"
            ))
        
        # Fallback: at the end
        if last_job:
            insertion_points.append(InsertionPoint(
                location="end",
                after_job=last_job,
                reasoning="Security scanning will run at the end of the workflow"
            ))
        else:
            insertion_points.append(InsertionPoint(
                location="end",
                after_job=None,
                reasoning="Security scanning will be the first job"
            ))
        
        return insertion_points
    
    def has_pr_trigger(self, on_triggers: Dict[str, Any]) -> bool:
        """Check if workflow has pull_request trigger"""
        if isinstance(on_triggers, dict):
            return 'pull_request' in on_triggers or 'pull_request_target' in on_triggers
        elif isinstance(on_triggers, list):
            return 'pull_request' in on_triggers or 'pull_request_target' in on_triggers
        return False
    
    def generate_job_yaml(self, template: Dict[str, Any], placeholders: Dict[str, str]) -> str:
        """
        Generate job YAML from template with placeholder substitution
        
        Args:
            template: Template dictionary with meta_data and content
            placeholders: Dictionary of placeholder -> value mappings
        
        Returns:
            YAML string of the job
        """
        content = template.get('content', '')
        
        # Substitute placeholders
        for placeholder, value in placeholders.items():
            # Handle both ${PLACEHOLDER} and $PLACEHOLDER formats
            content = content.replace(f'${{{placeholder}}}', value)
            content = content.replace(f'${placeholder}', value)
        
        return content
    
    def merge_job_into_workflow(
        self,
        workflow_content: str,
        job_yaml: str,
        job_id: str,
        insert_after: Optional[str] = None
    ) -> str:
        """
        Merge a new job into an existing workflow
        
        Args:
            workflow_content: Original workflow YAML content
            job_yaml: YAML content of the job to insert
            job_id: ID for the new job
            insert_after: Job ID to insert after (None = at end)
        
        Returns:
            Modified workflow YAML content
        """
        # Parse existing workflow with custom loader to preserve 'on' key
        workflow_dict = yaml.load(workflow_content, Loader=WorkflowYAMLLoader)
        
        # Parse new job with custom loader
        job_dict = yaml.load(job_yaml, Loader=WorkflowYAMLLoader)
        
        # If job_dict has a single top-level key (job name), extract the inner content
        # This handles templates that include the job name like "polaris-security-scan: {...}"
        if isinstance(job_dict, dict) and len(job_dict) == 1:
            # Extract the inner job definition
            job_dict = list(job_dict.values())[0]
        
        # Ensure jobs section exists
        if 'jobs' not in workflow_dict:
            workflow_dict['jobs'] = {}
        
        # If insert_after is specified, we need to preserve order
        if insert_after and insert_after in workflow_dict['jobs']:
            # Create a new ordered dict
            new_jobs = {}
            for existing_job_id, existing_job in workflow_dict['jobs'].items():
                new_jobs[existing_job_id] = existing_job
                
                # Insert new job after this one
                if existing_job_id == insert_after:
                    new_jobs[job_id] = job_dict
            
            workflow_dict['jobs'] = new_jobs
        else:
            # Just append at the end
            workflow_dict['jobs'][job_id] = job_dict
        
        # Convert back to YAML with nice formatting
        # Use custom dumper to preserve 'on' key (don't convert to 'true')
        return yaml.dump(
            workflow_dict, 
            Dumper=WorkflowYAMLDumper,
            default_flow_style=False, 
            sort_keys=False, 
            width=999999,
            allow_unicode=True,
            indent=2
        )
    
    def insert_step_into_job(
        self, 
        workflow_content: str, 
        step_yaml: str, 
        target_job: str,
        insert_position: str = "end"
    ) -> str:
        """
        Insert a step into an existing job
        
        Args:
            workflow_content: Workflow YAML content
            step_yaml: Step YAML content (can be single step or list of steps)
            target_job: ID of the job to insert the step into
            insert_position: Where to insert - 'end', 'after_build', or 'before_end'
        
        Returns:
            Modified workflow YAML content with step inserted
        """
        workflow_dict = yaml.load(workflow_content, Loader=WorkflowYAMLLoader)
        
        # Parse step YAML
        step_data = yaml.load(step_yaml, Loader=WorkflowYAMLLoader)
        
        # Convert to list of steps if it's a single step
        if isinstance(step_data, dict):
            new_steps = [step_data]
        elif isinstance(step_data, list):
            new_steps = step_data
        else:
            raise ValueError("Step YAML must be a dict or list")
        
        # Find target job
        if 'jobs' not in workflow_dict or target_job not in workflow_dict['jobs']:
            raise ValueError(f"Job '{target_job}' not found in workflow")
        
        job = workflow_dict['jobs'][target_job]
        
        # Ensure steps exist
        if 'steps' not in job:
            job['steps'] = []
        
        # Determine insertion point
        if insert_position == "end":
            # Add at the end
            job['steps'].extend(new_steps)
        elif insert_position == "after_build":
            # Find last build/compile step and insert after it
            build_keywords = ['build', 'compile', 'maven', 'gradle', 'npm run build', 'test']
            insert_index = len(job['steps'])  # Default to end
            
            for i, step in enumerate(job['steps']):
                step_name = (step.get('name') or '').lower()
                step_run = (step.get('run') or '').lower()
                
                # Check if this is a build step
                if any(keyword in step_name or keyword in step_run for keyword in build_keywords):
                    insert_index = i + 1
            
            # Insert after build steps
            for new_step in reversed(new_steps):
                job['steps'].insert(insert_index, new_step)
        elif insert_position == "before_end":
            # Insert before last step (usually artifact upload or similar)
            insert_index = max(0, len(job['steps']) - 1)
            for new_step in reversed(new_steps):
                job['steps'].insert(insert_index, new_step)
        else:
            # Default to end
            job['steps'].extend(new_steps)
        
        # Convert back to YAML
        return yaml.dump(
            workflow_dict,
            Dumper=WorkflowYAMLDumper,
            default_flow_style=False,
            sort_keys=False,
            width=999999,
            allow_unicode=True,
            indent=2
        )
    
    def add_job_dependency(self, workflow_content: str, job_id: str, needs: List[str]) -> str:
        """
        Add 'needs' dependency to a job
        
        Args:
            workflow_content: Workflow YAML content
            job_id: ID of the job to modify
            needs: List of job IDs this job depends on
        
        Returns:
            Modified workflow YAML content
        """
        workflow_dict = yaml.load(workflow_content, Loader=WorkflowYAMLLoader)
        
        if 'jobs' in workflow_dict and job_id in workflow_dict['jobs']:
            workflow_dict['jobs'][job_id]['needs'] = needs
        
        return yaml.dump(
            workflow_dict,
            Dumper=WorkflowYAMLDumper,
            default_flow_style=False,
            sort_keys=False,
            width=999999,
            allow_unicode=True,
            indent=2
        )

    def add_enhancement_comments(
        self,
        original_yaml: str,
        enhanced_yaml: str,
        enhancement_description: str,
        template_name: str,
        insertion_type: str = "job"  # 'job' or 'step'
    ) -> str:
        """
        Add comments to enhanced workflow explaining what was added
        
        Args:
            original_yaml: Original workflow YAML content
            enhanced_yaml: Enhanced workflow YAML content (without comments)
            enhancement_description: Description of what was enhanced
            template_name: Name of template that was applied
            insertion_type: Type of enhancement - 'job' or 'step'
        
        Returns:
            Enhanced YAML with comments preserved and added
        """
        from datetime import datetime
        
        lines = enhanced_yaml.split('\n')
        result_lines = []
        
        # Add header comment
        header_comment = f"""# Enhanced by Onboarding Tool
# Template: {template_name}
# Changes: {enhancement_description}
# Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        
        # Check if original had header comments, preserve them
        original_lines = original_yaml.split('\n')
        original_comments = []
        for line in original_lines:
            if line.strip().startswith('#'):
                original_comments.append(line)
            elif line.strip():
                break
        
        if original_comments:
            result_lines.extend(original_comments)
            result_lines.append('')
        
        result_lines.append(header_comment.rstrip())
        result_lines.append('')
        
        # Track if we're in the newly added section
        in_jobs = False
        job_added = False
        
        for i, line in enumerate(lines):
            # Skip empty lines at the start
            if i < 3 and not line.strip():
                continue
                
            # Detect jobs section
            if line.strip() == 'jobs:':
                in_jobs = True
                result_lines.append(line)
                continue
            
            # Detect new job addition (increased indentation under jobs)
            if in_jobs and line.startswith('  ') and line[2] != ' ' and ':' in line and not job_added:
                # This is a job definition
                job_name = line.split(':')[0].strip()
                
                # Check if this job exists in original
                if f"  {job_name}:" not in original_yaml:
                    # This is the newly added job
                    result_lines.append(f"  # >>> Added by enhancement: {template_name}")
                    result_lines.append(f"  # {enhancement_description}")
                    job_added = True
            
            result_lines.append(line)
        
        return '\n'.join(result_lines)
    
    def add_step_enhancement_comments(
        self,
        original_yaml: str,
        enhanced_yaml: str,
        enhancement_description: str,
        template_name: str,
        target_job: str
    ) -> str:
        """
        Add comments to workflow when steps are added to existing job
        
        Args:
            original_yaml: Original workflow YAML content
            enhanced_yaml: Enhanced workflow YAML content
            enhancement_description: Description of enhancement
            template_name: Name of template applied
            target_job: Job that was enhanced
        
        Returns:
            Enhanced YAML with comments
        """
        from datetime import datetime
        
        lines = enhanced_yaml.split('\n')
        result_lines = []
        
        # Add header comment
        header_comment = f"""# Enhanced by Onboarding Tool
# Template: {template_name}
# Changes: {enhancement_description}
# Target Job: {target_job}
# Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        
        # Preserve original header comments
        original_lines = original_yaml.split('\n')
        original_comments = []
        for line in original_lines:
            if line.strip().startswith('#'):
                original_comments.append(line)
            elif line.strip():
                break
        
        if original_comments:
            result_lines.extend(original_comments)
            result_lines.append('')
        
        result_lines.append(header_comment.rstrip())
        result_lines.append('')
        
        # Parse both YAMLs to find added steps
        original_dict = yaml.load(original_yaml, Loader=WorkflowYAMLLoader)
        enhanced_dict = yaml.load(enhanced_yaml, Loader=WorkflowYAMLLoader)
        
        original_steps = []
        if 'jobs' in original_dict and target_job in original_dict['jobs']:
            original_steps = original_dict['jobs'][target_job].get('steps', [])
        
        enhanced_steps = []
        if 'jobs' in enhanced_dict and target_job in enhanced_dict['jobs']:
            enhanced_steps = enhanced_dict['jobs'][target_job].get('steps', [])
        
        # Find new steps
        new_step_names = []
        for step in enhanced_steps:
            step_name = step.get('name', '')
            if step_name and not any(s.get('name') == step_name for s in original_steps):
                new_step_names.append(step_name)
        
        # Add comments before new steps
        in_target_job = False
        in_steps = False
        step_comment_added = False
        
        for i, line in enumerate(lines):
            # Skip initial empty lines
            if i < 3 and not line.strip():
                continue
            
            # Detect target job
            if f"  {target_job}:" in line:
                in_target_job = True
            
            # Detect steps section in target job
            if in_target_job and '    steps:' in line:
                in_steps = True
            
            # Detect new step
            if in_steps and '      - name:' in line and not step_comment_added:
                step_name_in_line = line.split('name:')[1].strip()
                if step_name_in_line in new_step_names:
                    result_lines.append(f"      # >>> Added steps by enhancement: {template_name}")
                    result_lines.append(f"      # {enhancement_description}")
                    step_comment_added = True
            
            result_lines.append(line)
        
        return '\n'.join(result_lines)
