"""
Workflow Duplicate Detection Module
Detects exact matches between workflow files and templates for removal recommendations
"""

import yaml
from typing import Dict, List, Any, Optional, Tuple
from workflow_parser import WorkflowParser, WorkflowYAMLLoader, WorkflowYAMLDumper


class DuplicateDetector:
    """Detects duplicate content between workflows and templates"""
    
    def __init__(self):
        self.parser = WorkflowParser()
    
    def normalize_yaml_content(self, content: str) -> Dict[str, Any]:
        """
        Normalize YAML content for comparison by parsing and re-dumping
        This removes formatting differences while preserving structure
        """
        try:
            parsed = yaml.load(content, Loader=WorkflowYAMLLoader)
            return parsed
        except Exception as e:
            print(f"Error normalizing YAML: {e}")
            return {}
    
    def compare_yaml_structures(self, struct1: Dict[str, Any], struct2: Dict[str, Any]) -> bool:
        """
        Deep comparison of two YAML structures
        Returns True if they are semantically identical
        """
        if type(struct1) != type(struct2):
            return False
        
        if isinstance(struct1, dict):
            if set(struct1.keys()) != set(struct2.keys()):
                return False
            return all(
                self.compare_yaml_structures(struct1[key], struct2[key])
                for key in struct1.keys()
            )
        
        elif isinstance(struct1, list):
            if len(struct1) != len(struct2):
                return False
            return all(
                self.compare_yaml_structures(item1, item2)
                for item1, item2 in zip(struct1, struct2)
            )
        
        else:
            return struct1 == struct2
    
    def detect_job_duplicates(
        self,
        workflow_content: str,
        template_content: str,
        template_name: str,
        template_id: int
    ) -> List[Dict[str, Any]]:
        """
        Detect if any jobs in the workflow exactly match the template job
        
        Returns list of duplicate job matches with removal recommendations
        """
        duplicates = []
        
        try:
            # Parse workflow and template
            workflow_data = self.normalize_yaml_content(workflow_content)
            template_data = self.normalize_yaml_content(template_content)
            
            if not workflow_data or not template_data:
                return duplicates
            
            workflow_jobs = workflow_data.get('jobs', {})
            
            # Template should be a single job definition
            if not isinstance(template_data, dict):
                return duplicates
            
            # Compare each workflow job with the template
            for job_name, job_content in workflow_jobs.items():
                if self.compare_yaml_structures(job_content, template_data):
                    duplicates.append({
                        'type': 'job',
                        'job_name': job_name,
                        'template_id': template_id,
                        'template_name': template_name,
                        'match_type': 'exact',
                        'recommendation': f"Remove job '{job_name}' - exact duplicate of template '{template_name}'"
                    })
        
        except Exception as e:
            print(f"Error detecting job duplicates: {e}")
        
        return duplicates
    
    def detect_step_duplicates(
        self,
        workflow_content: str,
        template_content: str,
        template_name: str,
        template_id: int
    ) -> List[Dict[str, Any]]:
        """
        Detect if any steps in the workflow exactly match the template steps
        
        Returns list of duplicate step matches with removal recommendations
        """
        duplicates = []
        
        try:
            # Parse workflow and template
            workflow_data = self.normalize_yaml_content(workflow_content)
            template_data = self.normalize_yaml_content(template_content)
            
            if not workflow_data or not template_data:
                return duplicates
            
            workflow_jobs = workflow_data.get('jobs', {})
            
            # Template should be a list of steps
            if not isinstance(template_data, list):
                return duplicates
            
            # Compare steps in each job
            for job_name, job_content in workflow_jobs.items():
                job_steps = job_content.get('steps', [])
                
                if not isinstance(job_steps, list):
                    continue
                
                # Check if template steps exist consecutively in job steps
                template_len = len(template_data)
                for i in range(len(job_steps) - template_len + 1):
                    consecutive_steps = job_steps[i:i + template_len]
                    
                    if self.compare_yaml_structures(consecutive_steps, template_data):
                        duplicates.append({
                            'type': 'steps',
                            'job_name': job_name,
                            'step_indices': list(range(i, i + template_len)),
                            'step_count': template_len,
                            'template_id': template_id,
                            'template_name': template_name,
                            'match_type': 'exact',
                            'recommendation': f"Remove {template_len} step(s) from job '{job_name}' (indices {i}-{i+template_len-1}) - exact duplicate of template '{template_name}'"
                        })
        
        except Exception as e:
            print(f"Error detecting step duplicates: {e}")
        
        return duplicates
    
    def detect_workflow_duplicate(
        self,
        workflow_content: str,
        template_content: str,
        template_name: str,
        template_id: int
    ) -> Optional[Dict[str, Any]]:
        """
        Detect if the entire workflow matches the template
        
        Returns duplicate info if entire workflow is a duplicate, None otherwise
        """
        try:
            # Parse both
            workflow_data = self.normalize_yaml_content(workflow_content)
            template_data = self.normalize_yaml_content(template_content)
            
            if not workflow_data or not template_data:
                return None
            
            # Compare entire structures
            if self.compare_yaml_structures(workflow_data, template_data):
                return {
                    'type': 'complete_workflow',
                    'template_id': template_id,
                    'template_name': template_name,
                    'match_type': 'exact',
                    'recommendation': f"Remove entire workflow file - exact duplicate of template '{template_name}'"
                }
        
        except Exception as e:
            print(f"Error detecting workflow duplicate: {e}")
        
        return None
    
    def detect_all_duplicates(
        self,
        workflow_content: str,
        workflow_file_path: str,
        templates: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Detect all types of duplicates between a workflow and available templates
        
        Args:
            workflow_content: The workflow YAML content
            workflow_file_path: Path to the workflow file
            templates: List of template dictionaries with id, name, content, template_type
        
        Returns:
            Dictionary with duplicate detection results
        """
        results = {
            'workflow_file': workflow_file_path,
            'has_duplicates': False,
            'complete_workflow_duplicate': None,
            'job_duplicates': [],
            'step_duplicates': []
        }
        
        for template in templates:
            template_id = template.get('id')
            template_name = template.get('name')
            template_content = template.get('content')
            template_type = template.get('template_type', 'workflow')
            
            if not template_content:
                continue
            
            # Check for complete workflow duplicate
            if template_type == 'workflow':
                workflow_dup = self.detect_workflow_duplicate(
                    workflow_content,
                    template_content,
                    template_name,
                    template_id
                )
                if workflow_dup:
                    results['complete_workflow_duplicate'] = workflow_dup
                    results['has_duplicates'] = True
                    # If entire workflow is duplicate, no need to check further
                    break
            
            # Check for job duplicates
            elif template_type == 'job':
                job_dups = self.detect_job_duplicates(
                    workflow_content,
                    template_content,
                    template_name,
                    template_id
                )
                if job_dups:
                    results['job_duplicates'].extend(job_dups)
                    results['has_duplicates'] = True
            
            # Check for step duplicates
            elif template_type == 'step':
                step_dups = self.detect_step_duplicates(
                    workflow_content,
                    template_content,
                    template_name,
                    template_id
                )
                if step_dups:
                    results['step_duplicates'].extend(step_dups)
                    results['has_duplicates'] = True
        
        return results
    
    def remove_job_from_workflow(
        self,
        workflow_content: str,
        job_name: str
    ) -> str:
        """
        Remove a specific job from the workflow
        
        Args:
            workflow_content: Original workflow YAML content
            job_name: Name of the job to remove
        
        Returns:
            Modified workflow content with job removed
        """
        try:
            workflow_data = yaml.load(workflow_content, Loader=WorkflowYAMLLoader)
            
            if 'jobs' in workflow_data and job_name in workflow_data['jobs']:
                del workflow_data['jobs'][job_name]
                
                # Convert back to YAML
                modified_content = yaml.dump(
                    workflow_data,
                    Dumper=WorkflowYAMLDumper,
                    default_flow_style=False,
                    sort_keys=False,
                    allow_unicode=True
                )
                
                return modified_content
            
            return workflow_content
        
        except Exception as e:
            print(f"Error removing job from workflow: {e}")
            return workflow_content
    
    def remove_steps_from_job(
        self,
        workflow_content: str,
        job_name: str,
        step_indices: List[int]
    ) -> str:
        """
        Remove specific steps from a job in the workflow
        
        Args:
            workflow_content: Original workflow YAML content
            job_name: Name of the job containing the steps
            step_indices: List of step indices to remove
        
        Returns:
            Modified workflow content with steps removed
        """
        try:
            workflow_data = yaml.load(workflow_content, Loader=WorkflowYAMLLoader)
            
            if 'jobs' not in workflow_data or job_name not in workflow_data['jobs']:
                return workflow_content
            
            job = workflow_data['jobs'][job_name]
            if 'steps' not in job or not isinstance(job['steps'], list):
                return workflow_content
            
            # Remove steps in reverse order to maintain indices
            for index in sorted(step_indices, reverse=True):
                if 0 <= index < len(job['steps']):
                    del job['steps'][index]
            
            # Convert back to YAML
            modified_content = yaml.dump(
                workflow_data,
                Dumper=WorkflowYAMLDumper,
                default_flow_style=False,
                sort_keys=False,
                allow_unicode=True
            )
            
            return modified_content
        
        except Exception as e:
            print(f"Error removing steps from job: {e}")
            return workflow_content