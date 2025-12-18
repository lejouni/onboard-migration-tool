"""
Parallel AI Analysis Module
Optimized version of repository analysis with concurrent processing
"""

import asyncio
import httpx
from typing import List, Dict
from workflow_parser import WorkflowParser
from workflow_duplicate_detector import DuplicateDetector
from assessment_logic import determine_assessment_types
from workflow_enhancement_helpers import (
    fetch_repo_file_tree,
    generate_enhancement_recommendations,
    generate_new_workflow_recommendations
)
from database import get_db, get_templates_db
from templates_models import Template


async def analyze_single_repository(
    repo_name: str,
    github_token: str,
    templates_for_detection: list,
    detector: DuplicateDetector,
    cached_tool_keywords: dict = None,
    cached_available_categories: dict = None
) -> dict:
    """
    Analyze a single repository (optimized for parallel processing)
    
    Args:
        repo_name: Repository name in format "owner/repo"
        github_token: GitHub authentication token
        templates_for_detection: List of templates for duplicate detection
        detector: DuplicateDetector instance
    
    Returns:
        Dictionary with repository analysis results
    """
    repo_result = {
        "repository": repo_name,
        "total_workflows": 0,
        "blackduck_analysis": None,
        "error": None
    }
    
    try:
        headers = {
            'Authorization': f'token {github_token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        
        workflow_url = f"https://api.github.com/repos/{repo_name}/contents/.github/workflows"
        
        async with httpx.AsyncClient(verify=False, timeout=30.0) as client:
            # Parallel fetch of multiple API endpoints
            file_tree_task = fetch_repo_file_tree(repo_name, github_token, client)
            languages_task = client.get(f"https://api.github.com/repos/{repo_name}/languages", headers=headers)
            root_task = client.get(f"https://api.github.com/repos/{repo_name}/contents/", headers=headers)
            workflow_task = client.get(workflow_url, headers=headers)
            
            # Wait for all API calls to complete in parallel
            file_list, languages_response, root_response, workflow_response = await asyncio.gather(
                file_tree_task,
                languages_task,
                root_task,
                workflow_task,
                return_exceptions=True
            )
            
            # Process languages
            detected_languages = []
            if not isinstance(languages_response, Exception) and languages_response.status_code == 200:
                languages_data = languages_response.json()
                detected_languages = list(languages_data.keys())
            
            # Determine assessment types
            assessment_recommendation = determine_assessment_types(
                file_list if not isinstance(file_list, Exception) else [],
                detected_languages
            )
            
            # Check for polaris files
            polaris_files = []
            has_polaris_in_root = False
            
            if not isinstance(root_response, Exception) and root_response.status_code == 200:
                root_data = root_response.json()
                for item in root_data:
                    if item.get("type") == "file" and item.get("name") in ["polaris.yml", "polaris.yaml"]:
                        polaris_files.append({
                            "name": item.get("name"),
                            "path": item.get("path"),
                            "size": item.get("size"),
                            "sha": item.get("sha"),
                            "download_url": item.get("download_url")
                        })
                        has_polaris_in_root = True
            
            # Process workflow files
            if not isinstance(workflow_response, Exception) and workflow_response.status_code == 200:
                workflow_files = workflow_response.json()
                repo_result["total_workflows"] = len(workflow_files) if isinstance(workflow_files, list) else 0
                
                parsed_workflows = []
                has_security_scan = False
                has_build_job = False
                
                if isinstance(workflow_files, list) and len(workflow_files) > 0:
                    parser = WorkflowParser()
                    
                    # Download all workflow contents in parallel
                    workflow_download_tasks = []
                    workflow_metadata = []
                    
                    for workflow_file in workflow_files:
                        if workflow_file.get('type') == 'file' and workflow_file.get('name', '').endswith(('.yml', '.yaml')):
                            workflow_download_tasks.append(
                                client.get(workflow_file['download_url'], headers=headers)
                            )
                            workflow_metadata.append(workflow_file)
                    
                    # Wait for all workflow downloads to complete
                    workflow_contents = await asyncio.gather(*workflow_download_tasks, return_exceptions=True)
                    
                    # Process each workflow
                    for workflow_file, file_response in zip(workflow_metadata, workflow_contents):
                        if not isinstance(file_response, Exception) and file_response.status_code == 200:
                            workflow_content = file_response.text
                            
                            try:
                                analysis = parser.analyze_workflow(workflow_content, workflow_file['name'])
                                
                                # Detect duplicates
                                duplicates = detector.detect_all_duplicates(
                                    workflow_content=workflow_content,
                                    workflow_file_path=workflow_file['path'],
                                    templates=templates_for_detection
                                )
                                
                                parsed_workflows.append({
                                    "file": {
                                        "name": workflow_file['name'],
                                        "path": workflow_file['path'],
                                        "download_url": workflow_file['download_url']
                                    },
                                    "analysis": analysis,
                                    "content": workflow_content,
                                    "duplicates": duplicates
                                })
                                
                                if analysis.get('has_security_scan', False):
                                    has_security_scan = True
                                if analysis.get('has_build_job', False):
                                    has_build_job = True
                            except Exception as parse_err:
                                print(f"Warning: Could not parse workflow {workflow_file['name']}: {parse_err}")
                
                # Generate analysis based on workflow status
                repo_result["blackduck_analysis"] = await generate_blackduck_analysis(
                    repo_name=repo_name,
                    has_security_scan=has_security_scan,
                    has_build_job=has_build_job,
                    parsed_workflows=parsed_workflows,
                    detected_languages=detected_languages,
                    assessment_recommendation=assessment_recommendation,
                    has_polaris_in_root=has_polaris_in_root,
                    polaris_files=polaris_files,
                    cached_tool_keywords=cached_tool_keywords,
                    cached_available_categories=cached_available_categories
                )
            else:
                # No workflow files
                templates_db = next(get_templates_db())
                try:
                    recommended_templates = generate_new_workflow_recommendations(
                        db=templates_db,
                        assessment_recommendation=assessment_recommendation,
                        detected_languages=detected_languages
                    )
                finally:
                    templates_db.close()
                
                repo_result["blackduck_analysis"] = {
                    "has_blackduck_tools": False,
                    "detected_tools": [],
                    "detected_languages": detected_languages,
                    "detected_package_managers": [
                        {"name": pm.package_manager, "files": pm.files_found, "languages": pm.languages}
                        for pm in assessment_recommendation.package_managers
                    ],
                    "status": "no_workflows",
                    "message": "📝 No GitHub Actions workflows found. Start by adding security scanning workflows.",
                    "recommended_templates": recommended_templates,
                    "has_polaris_in_root": has_polaris_in_root,
                    "polaris_files": polaris_files
                }
    
    except Exception as e:
        repo_result["error"] = str(e)
        print(f"Error analyzing repository {repo_name}: {e}")
    
    return repo_result


async def generate_blackduck_analysis(
    repo_name: str,
    has_security_scan: bool,
    has_build_job: bool,
    parsed_workflows: list,
    detected_languages: list,
    assessment_recommendation,
    has_polaris_in_root: bool,
    polaris_files: list,
    cached_tool_keywords: dict = None,
    cached_available_categories: dict = None
) -> dict:
    """Generate BlackDuck analysis based on workflow status (optimized with cached data)"""
    
    workflow_duplicates = [
        {
            "workflow_file": parsed_wf['file']['name'],
            "workflow_path": parsed_wf['file']['path'],
            "duplicates": parsed_wf['duplicates']
        }
        for parsed_wf in parsed_workflows
        if parsed_wf.get('duplicates', {}).get('has_duplicates', False)
    ]
    
    # Use cached tool keywords if available, otherwise fetch from DB
    if cached_tool_keywords is not None:
        tool_keywords = cached_tool_keywords
    else:
        # Fallback: fetch from DB (should rarely happen)
        templates_db = next(get_templates_db())
        try:
            available_categories = templates_db.query(Template.category).filter(
                Template.category.isnot(None),
                Template.category != ''
            ).distinct().all()
            available_tools = {cat[0].lower(): cat[0] for cat in available_categories}
            
            tool_keywords = {}
            for tool_key, tool_name in available_tools.items():
                if tool_key in ['polaris', 'coverity', 'blackduck_sca', 'srm']:
                    if tool_key == 'blackduck_sca':
                        tool_keywords['blackduck'] = 'Black Duck SCA'
                        tool_keywords['black duck'] = 'Black Duck SCA'
                    elif tool_key == 'srm':
                        tool_keywords['srm'] = 'SRM'
                    else:
                        tool_keywords[tool_key] = tool_name.title()
        finally:
            templates_db.close()
    
    # Collect BlackDuck-specific security evidence
    security_evidence = []
    has_blackduck_tools = False
    
    if has_security_scan:
        for parsed_wf in parsed_workflows:
            analysis = parsed_wf["analysis"]
            if analysis.get('has_security_scan', False):
                evidence = {
                    "workflow_file": parsed_wf["file"]["name"],
                    "workflow_path": parsed_wf["file"]["path"],
                    "detected_tools": []
                }
                
                for job_name, job_info in analysis.get('jobs', {}).items():
                    for step in job_info.get('steps', []):
                        step_name = (step.get('name') or '').lower()
                        step_uses = (step.get('uses') or '').lower()
                        step_run = (step.get('run') or '').lower()
                        
                        for keyword, display_name in tool_keywords.items():
                            if keyword in step_name or keyword in step_run or keyword in step_uses:
                                evidence["detected_tools"].append({
                                    "tool": display_name,
                                    "job": job_name,
                                    "step": step.get('name', 'Unnamed step')
                                })
                                has_blackduck_tools = True
                                break
                
                if evidence["detected_tools"]:
                    security_evidence.append(evidence)
    
    # If BlackDuck tools are detected, return configured status
    if has_blackduck_tools:
        return {
            "has_blackduck_tools": True,
            "detected_tools": [],
            "detected_languages": detected_languages,
            "detected_package_managers": [
                {"name": pm.package_manager, "files": pm.files_found, "languages": pm.languages}
                for pm in assessment_recommendation.package_managers
            ],
            "status": "configured",
            "message": "✅ Security scanning is already configured in this repository",
            "security_evidence": security_evidence,
            "recommended_templates": [],
            "workflow_duplicates": workflow_duplicates,
            "has_polaris_in_root": has_polaris_in_root,
            "polaris_files": polaris_files
        }
    
    elif parsed_workflows:
        # Has workflows but no BlackDuck tools - provide enhancement recommendations
        templates_db = next(get_templates_db())
        try:
            if has_build_job:
                # Has build jobs - recommend step enhancements
                recommended_templates = generate_enhancement_recommendations(
                    db=templates_db,
                    repo_name=repo_name,
                    parsed_workflows=parsed_workflows,
                    assessment_recommendation=assessment_recommendation,
                    detected_languages=detected_languages
                )
                status_message = "⚡ Existing workflows detected. Enhance them with security scanning."
            else:
                # Has workflows but no build jobs - recommend new workflow or job additions
                recommended_templates = generate_new_workflow_recommendations(
                    db=templates_db,
                    assessment_recommendation=assessment_recommendation,
                    detected_languages=detected_languages
                )
                status_message = "⚡ Workflows exist but no build jobs detected. Add security scanning workflows."
        finally:
            templates_db.close()
        
        return {
            "has_blackduck_tools": False,
            "detected_tools": [],
            "detected_languages": detected_languages,
            "detected_package_managers": [
                {"name": pm.package_manager, "files": pm.files_found, "languages": pm.languages}
                for pm in assessment_recommendation.package_managers
            ],
            "status": "needs_enhancement",
            "message": status_message,
            "recommended_templates": recommended_templates,
            "workflow_duplicates": workflow_duplicates,
            "has_polaris_in_root": has_polaris_in_root,
            "polaris_files": polaris_files
        }
    
    else:
        # No workflows at all - recommend new workflow
        templates_db = next(get_templates_db())
        try:
            recommended_templates = generate_new_workflow_recommendations(
                db=templates_db,
                assessment_recommendation=assessment_recommendation,
                detected_languages=detected_languages
            )
        finally:
            templates_db.close()
        
        return {
            "has_blackduck_tools": False,
            "detected_tools": [],
            "detected_languages": detected_languages,
            "detected_package_managers": [
                {"name": pm.package_manager, "files": pm.files_found, "languages": pm.languages}
                for pm in assessment_recommendation.package_managers
            ],
            "status": "needs_new_workflow",
            "message": "📝 Add a new security scanning workflow to this repository.",
            "recommended_templates": recommended_templates,
            "workflow_duplicates": workflow_duplicates,
            "has_polaris_in_root": has_polaris_in_root,
            "polaris_files": polaris_files
        }


async def analyze_repositories_parallel(
    repositories: List[str],
    github_token: str,
    templates_for_detection: list
) -> List[dict]:
    """
    Analyze multiple repositories in parallel (optimized with cached DB queries)
    
    Args:
        repositories: List of repository names
        github_token: GitHub authentication token
        templates_for_detection: List of templates for duplicate detection
    
    Returns:
        List of repository analysis results
    """
    detector = DuplicateDetector()
    
    # OPTIMIZATION: Fetch template categories once for all repositories
    cached_tool_keywords = {}
    cached_available_categories = {}
    
    templates_db = next(get_templates_db())
    try:
        available_categories = templates_db.query(Template.category).filter(
            Template.category.isnot(None),
            Template.category != ''
        ).distinct().all()
        
        available_tools = {cat[0].lower(): cat[0] for cat in available_categories}
        cached_available_categories = available_tools
        
        # Build tool keywords cache
        for tool_key, tool_name in available_tools.items():
            if tool_key in ['polaris', 'coverity', 'blackduck_sca', 'srm']:
                if tool_key == 'blackduck_sca':
                    cached_tool_keywords['blackduck'] = 'Black Duck SCA'
                    cached_tool_keywords['black duck'] = 'Black Duck SCA'
                elif tool_key == 'srm':
                    cached_tool_keywords['srm'] = 'SRM'
                else:
                    cached_tool_keywords[tool_key] = tool_name.title()
    finally:
        templates_db.close()
    
    # Create tasks for parallel execution with cached data
    tasks = [
        analyze_single_repository(
            repo_name=repo_name,
            github_token=github_token,
            templates_for_detection=templates_for_detection,
            detector=detector,
            cached_tool_keywords=cached_tool_keywords,
            cached_available_categories=cached_available_categories
        )
        for repo_name in repositories
    ]
    
    # Execute all tasks in parallel
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Handle exceptions
    processed_results = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            processed_results.append({
                "repository": repositories[i] if i < len(repositories) else "unknown",
                "total_workflows": 0,
                "blackduck_analysis": None,
                "error": str(result)
            })
        else:
            processed_results.append(result)
    
    return processed_results