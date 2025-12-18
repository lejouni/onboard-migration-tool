"""
Workflow Enhancement Helper Functions
Provides helper functions for generating workflow and enhancement recommendations
"""

import json
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from templates_crud import TemplateCRUD
from assessment_logic import AssessmentType, should_include_sast
from pr_optimization import should_add_pr_optimization


def fill_template_placeholders(template_content: str, assessment_type: str = None) -> str:
    """
    Fill placeholders in template content with actual values
    Placeholders: {assessment_types}
    
    Maps assessment types to Polaris assessment_types parameter:
    - SAST -> SAST
    - SCA -> SCA
    - SAST_SCA or SAST,SCA -> SAST,SCA
    """
    if not assessment_type:
        assessment_type = "SAST"  # Default
    
    # Normalize assessment type format
    # Handle both "SAST_SCA" and "SAST,SCA" formats
    if "SAST" in assessment_type.upper() and "SCA" in assessment_type.upper():
        polaris_assessment_types = "SAST,SCA"
    elif "SAST" in assessment_type.upper():
        polaris_assessment_types = "SAST"
    elif "SCA" in assessment_type.upper():
        polaris_assessment_types = "SCA"
    else:
        polaris_assessment_types = assessment_type
    
    # Replace placeholders
    filled_content = template_content.replace("{assessment_types}", polaris_assessment_types)
    
    return filled_content


async def fetch_repo_file_tree(repo_name: str, github_token: str, http_client) -> List[str]:
    """
    Fetch repository file tree to detect package managers
    
    Args:
        repo_name: Repository name in format "owner/repo"
        github_token: GitHub personal access token
        http_client: httpx.AsyncClient instance
    
    Returns:
        List of file paths in the repository
    """
    try:
        headers = {
            'Authorization': f'token {github_token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        
        # Get default branch first
        repo_url = f"https://api.github.com/repos/{repo_name}"
        repo_response = await http_client.get(repo_url, headers=headers)
        
        if repo_response.status_code != 200:
            return []
        
        repo_data = repo_response.json()
        default_branch = repo_data.get('default_branch', 'main')
        
        # Get file tree recursively
        tree_url = f"https://api.github.com/repos/{repo_name}/git/trees/{default_branch}?recursive=1"
        tree_response = await http_client.get(tree_url, headers=headers)
        
        if tree_response.status_code != 200:
            return []
        
        tree_data = tree_response.json()
        tree_items = tree_data.get('tree', [])
        
        # Extract file paths (not directories)
        file_paths = [
            item['path'] for item in tree_items 
            if item['type'] == 'blob'
        ]
        
        return file_paths
    
    except Exception as e:
        print(f"Error fetching file tree for {repo_name}: {e}")
        return []


def generate_enhancement_recommendations(
    db: Session,
    repo_name: str,
    parsed_workflows: List[Dict[str, Any]],
    assessment_recommendation: Any,
    detected_languages: List[str]
) -> List[Dict[str, Any]]:
    """
    Generate enhancement recommendations for repositories with existing workflows
    
    Args:
        db: Database session
        repo_name: Repository name
        parsed_workflows: List of parsed workflow analyses
        assessment_recommendation: AssessmentRecommendation from determine_assessment_types()
        detected_languages: List of detected programming languages
    
    Returns:
        List of enhancement recommendation objects
    """
    recommendations = []
    
    # Find the best workflow to enhance (one with most build steps)
    best_workflow = None
    max_build_steps = 0
    
    for wf in parsed_workflows:
        analysis = wf['analysis']
        if analysis.get('has_build_job', False):
            build_job_count = sum(
                1 for job_info in analysis.get('jobs', {}).values() 
                if job_info.get('has_build_steps', False)
            )
            if build_job_count > max_build_steps:
                max_build_steps = build_job_count
                best_workflow = wf
    
    if not best_workflow:
        # No workflow with build steps found, fall back to first workflow
        best_workflow = parsed_workflows[0] if parsed_workflows else None
    
    if not best_workflow:
        return []
    
    workflow_analysis = best_workflow['analysis']
    workflow_file = best_workflow['file']
    
    # Get insertion points
    insertion_points = workflow_analysis.get('insertion_points', [])
    preferred_insertion = insertion_points[0] if insertion_points else None
    
    # Check if workflow has PR trigger
    has_pr_trigger = workflow_analysis.get('has_pr_trigger', False)
    
    # Determine primary language for template filtering
    primary_language = assessment_recommendation.primary_language.lower()
    
    # Get assessment type
    assessment_type = assessment_recommendation.assessment_type
    
    # Determine if we should use step fragments or job fragments
    # Use step fragments if there's a suitable build job to insert into
    use_step_fragments = False
    target_job_name = None
    
    for job_name, job_info in workflow_analysis.get('jobs', {}).items():
        if job_info.get('has_build_steps', False):
            # Found a job with build steps - we can insert a step here
            use_step_fragments = True
            target_job_name = job_name
            break
    
    # Query appropriate fragments based on whether we're adding steps or jobs
    if use_step_fragments:
        fragments = TemplateCRUD.get_templates_by_type(db, 'step')
    else:
        fragments = TemplateCRUD.get_templates_by_type(db, 'job')
    
    # Filter fragments by category and language compatibility
    suitable_fragments = []
    
    # Tool categories that support SAST
    sast_tools = ['polaris', 'coverity']
    # Tool categories that support SCA
    sca_tools = ['blackduck_sca', 'black_duck_sca']
    
    for fragment in fragments:
        # Parse meta_data
        try:
            meta_data = json.loads(fragment.meta_data) if fragment.meta_data else {}
        except Exception:
            meta_data = {}
        
        compatible_languages = [lang.lower() for lang in meta_data.get('compatible_languages', [])]
        
        # Check language compatibility
        if primary_language != 'unknown' and compatible_languages:
            if primary_language not in compatible_languages:
                continue
        
        # Parse fragment categories (comma-separated, lowercase for comparison)
        fragment_categories = [cat.strip().lower() for cat in (fragment.category or '').split(',')]
        
        # Match categories to assessment type
        # Accept both explicit scanning types (SAST, SCA) and tool names (polaris, coverity, blackduck_sca)
        is_suitable = False
        
        if assessment_type == AssessmentType.SAST:
            # Accept SAST category or SAST-capable tools
            if 'sast' in fragment_categories or any(tool in fragment_categories for tool in sast_tools):
                is_suitable = True
        elif assessment_type == AssessmentType.SCA:
            # Accept SCA category or SCA-capable tools
            if 'sca' in fragment_categories or any(tool in fragment_categories for tool in sca_tools):
                is_suitable = True
        elif assessment_type == AssessmentType.SAST_SCA:
            # For SAST_SCA, accept:
            # 1. Templates with both SAST and SCA categories
            # 2. Polaris (supports both SAST and SCA)
            # 3. Any SAST or SCA tool (we'll recommend both types)
            if ('sast' in fragment_categories and 'sca' in fragment_categories) or \
               'polaris' in fragment_categories or \
               any(tool in fragment_categories for tool in sast_tools + sca_tools):
                is_suitable = True
        
        if is_suitable:
            suitable_fragments.append((fragment, meta_data))
    
    # Generate recommendations from suitable fragments
    for fragment, meta_data in suitable_fragments:
        tool_type = fragment.category
        
        # Fill template placeholders with actual values
        filled_content = fill_template_placeholders(fragment.content, assessment_type.value)
        
        # Build different recommendation based on fragment type
        if use_step_fragments:
            # Step fragment - insert into existing job
            recommendation = {
                "type": "enhance_workflow",
                "template_name": fragment.name,
                "template_content": filled_content,  # Add filled content
                "description": fragment.description or f"Add {tool_type} security scanning step to build job",
                "tool_type": tool_type,
                "category": fragment.category,
                "assessment_type": assessment_type.value,
                "reason": f"Add {assessment_type.value} scanning step to existing build job '{target_job_name}'. {assessment_recommendation.reasoning}",
                
                # Target workflow info
                "target_workflow": {
                    "file_name": workflow_file['name'],
                    "file_path": workflow_file['path'],
                    "insertion_point": {
                        "location": "step_in_job",
                        "target_job": target_job_name,
                        "after_step": "build",
                        "reasoning": f"Insert security scan step after build steps in '{target_job_name}' job"
                    }
                },
                
                # PR optimization
                "has_pr_optimization": should_add_pr_optimization(assessment_type, has_pr_trigger),
                "pr_optimization_reason": (
                    "Uses SAST_RAPID for pull requests, full SAST for pushes"
                    if should_add_pr_optimization(assessment_type, has_pr_trigger)
                    else None
                ),
                
                # Package manager info
                "detected_package_managers": [
                    {
                        "name": pm.package_manager,
                        "files": pm.files_found,
                        "languages": pm.languages
                    }
                    for pm in assessment_recommendation.package_managers
                ],
                
                # Template info
                "template_id": fragment.id,
                "template_type": fragment.template_type,
                "template_fragment_type": "step"
            }
        else:
            # Job fragment - add new job to workflow
            recommendation = {
                "type": "enhance_workflow",
                "template_name": fragment.name,
                "template_content": filled_content,  # Add filled content
                "description": fragment.description or f"Add {tool_type} security scanning to existing workflow",
                "tool_type": tool_type,
                "category": fragment.category,
                "assessment_type": assessment_type.value,
                "reason": f"Enhance existing workflow with {assessment_type.value} scanning. {assessment_recommendation.reasoning}",
                
                # Target workflow info
                "target_workflow": {
                    "file_name": workflow_file['name'],
                    "file_path": workflow_file['path'],
                    "insertion_point": {
                        "location": preferred_insertion['location'] if preferred_insertion else "end",
                        "after_job": preferred_insertion['after_job'] if preferred_insertion else None,
                        "reasoning": preferred_insertion['reasoning'] if preferred_insertion else "Add at end of workflow"
                    }
                },
                
                # PR optimization
                "has_pr_optimization": should_add_pr_optimization(assessment_type, has_pr_trigger),
                "pr_optimization_reason": (
                    "Uses SAST_RAPID for pull requests, full SAST for pushes"
                    if should_add_pr_optimization(assessment_type, has_pr_trigger)
                    else None
                ),
                
                # Package manager info
                "detected_package_managers": [
                    {
                        "name": pm.package_manager,
                        "files": pm.files_found,
                        "languages": pm.languages
                    }
                    for pm in assessment_recommendation.package_managers
                ],
                
                # Template info
                "template_id": fragment.id,
                "template_type": fragment.template_type,
                "template_fragment_type": "job"
            }
        
        recommendations.append(recommendation)
    
    return recommendations


def generate_new_workflow_recommendations(
    db: Session,
    assessment_recommendation: Any,
    detected_languages: List[str]
) -> List[Dict[str, Any]]:
    """
    Generate new workflow recommendations for repositories without suitable workflows.
    
    Logic:
    - If supported primary language exists → recommend Polaris (SAST)
    - If only package manager exists (no supported language) → recommend Black Duck SCA
    - Only recommends templates with names ending in 'Workflow' to indicate complete workflow templates
    
    Args:
        db: Database session
        assessment_recommendation: AssessmentRecommendation from determine_assessment_types()
        detected_languages: List of detected programming languages
    
    Returns:
        List of new workflow recommendation objects
    """
    recommendations = []
    
    # Get assessment type
    assessment_type = assessment_recommendation.assessment_type
    primary_language = assessment_recommendation.primary_language.lower()
    has_package_manager = len(assessment_recommendation.package_managers) > 0
    
    # Query full workflow templates
    workflow_templates = TemplateCRUD.get_templates_by_type(db, 'workflow')
    
    # Check if the primary language is actually supported by any template
    has_supported_language = False
    if primary_language not in ['unknown', '']:
        for template in workflow_templates:
            try:
                meta_data = json.loads(template.meta_data) if template.meta_data else {}
                compatible_languages = [lang.lower() for lang in meta_data.get('compatible_languages', [])]
                if primary_language in compatible_languages:
                    has_supported_language = True
                    break
            except Exception:
                continue
    
    # Filter templates by scanning type categories, language, and name ending with 'Workflow'
    suitable_templates = []
    
    for template in workflow_templates:
        # Only recommend templates with names ending in 'Workflow'
        if not template.name.endswith('Workflow'):
            continue
        
        # Parse template categories (comma-separated scanning types)
        template_categories = [cat.strip() for cat in (template.category or '').split(',')]
        
        # Match categories to assessment type
        matches_assessment = False
        if assessment_type == AssessmentType.SAST:
            # Recommend templates that support SAST
            if 'SAST' in template_categories:
                matches_assessment = True
        elif assessment_type == AssessmentType.SCA:
            # Recommend templates that support SCA
            if 'SCA' in template_categories:
                matches_assessment = True
        elif assessment_type == AssessmentType.SAST_SCA:
            # Recommend templates that support both SAST and SCA
            if 'SAST' in template_categories and 'SCA' in template_categories:
                matches_assessment = True
        
        if not matches_assessment:
            continue
            
        # Parse meta_data
        try:
            meta_data = json.loads(template.meta_data) if template.meta_data else {}
        except Exception:
            meta_data = {}
        
        compatible_languages = [lang.lower() for lang in meta_data.get('compatible_languages', [])]
        
        # Check language compatibility if we have a supported language
        if has_supported_language and compatible_languages:
            if primary_language not in compatible_languages:
                continue
        
        suitable_templates.append((template, meta_data))
    
    # Generate recommendations
    for template, meta_data in suitable_templates:
        tool_type = template.category
        
        # Fill template placeholders with actual values
        filled_content = fill_template_placeholders(template.content, assessment_type.value)
        
        # Build reason based on what we detected
        template_categories = [cat.strip() for cat in (template.category or '').split(',')]
        
        if assessment_type == AssessmentType.SAST_SCA:
            # For SAST_SCA, mention both capabilities
            if has_supported_language and has_package_manager:
                pm_names = ', '.join([pm.package_manager for pm in assessment_recommendation.package_managers])
                reason = f"Repository has {primary_language.title()} code and uses {pm_names} package manager(s). Template supports {', '.join(template_categories)} scanning. {assessment_recommendation.reasoning}"
            elif has_supported_language:
                reason = f"Repository has {primary_language.title()} code. Template supports {', '.join(template_categories)} scanning. {assessment_recommendation.reasoning}"
            else:
                reason = f"Template supports {', '.join(template_categories)} scanning. {assessment_recommendation.reasoning}"
        elif has_supported_language:
            reason = f"Repository has {primary_language.title()} code. Template supports {', '.join(template_categories)} scanning. {assessment_recommendation.reasoning}"
        elif has_package_manager:
            pm_names = ', '.join([pm.package_manager for pm in assessment_recommendation.package_managers])
            reason = f"Repository uses {pm_names} package manager(s). Template supports {', '.join(template_categories)} scanning. {assessment_recommendation.reasoning}"
        else:
            reason = f"Template supports {', '.join(template_categories)} scanning. {assessment_recommendation.reasoning}"
        
        recommendation = {
            "type": "new_workflow",
            "template_name": template.name,
            "template_content": filled_content,  # Add filled content
            "description": template.description or f"Complete {tool_type} security workflow",
            "tool_type": tool_type,
            "category": template.category,
            "assessment_type": assessment_type.value,
            "reason": reason,
            
            # PR optimization (always yes for new workflows with SAST)
            "has_pr_optimization": should_include_sast(assessment_type),
            "pr_optimization_reason": (
                "Uses SAST_RAPID for pull requests, full SAST for pushes"
                if should_include_sast(assessment_type)
                else None
            ),
            
            # Package manager info
            "detected_package_managers": [
                {
                    "name": pm.package_manager,
                    "files": pm.files_found,
                    "languages": pm.languages
                }
                for pm in assessment_recommendation.package_managers
            ],
            
            # Template info
            "template_id": template.id,
            "template_type": template.template_type,
            "template_fragment_type": None
        }
        
        recommendations.append(recommendation)
    
    return recommendations
