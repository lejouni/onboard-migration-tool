# Workflow Enhancement Feature - Implementation Design

## Overview
Enhance the AI-Analysis endpoint to generate both "new_workflow" and "enhance_workflow" recommendations.

## Current State Analysis

### Existing `/api/ai-analyze` Endpoint (line 1476)
- Currently analyzes repositories for Black Duck tools
- Generates `recommended_templates` for repos without security tools
- Returns template recommendations as objects with: template_name, description, tool_type, category, reason
- Does NOT parse workflow YAML structure
- Does NOT check for existing jobs/steps
- Only recommends full workflow templates

### New Modules Created
1. **workflow_parser.py** - Parse GitHub Actions YAML structure
2. **assessment_logic.py** - Determine SAST vs SAST,SCA based on package managers  
3. **pr_optimization.py** - Generate PR optimization configuration
4. **Template fragments in database** - Job and step fragments ready to use

## Enhancement Design

### Step 1: Enhance Repository Analysis Function
Modify the repository analysis in `/api/ai-analyze` to:

1. **Detect existing workflows AND their structure**:
   - Use `WorkflowParser.analyze_workflow()` on each workflow file
   - Track: jobs, steps, build tools, existing security scans, triggers

2. **Get repository file list** for package manager detection:
   - Fetch repository tree: `/repos/{owner}/{repo}/git/trees/{branch}?recursive=1`
   - Extract file paths for assessment_logic.determine_assessment_types()

3. **Generate TWO types of recommendations**:
   
   **A. `new_workflow` recommendations** (existing behavior - enhanced):
   - When: No workflows OR no build/CI jobs detected
   - Use: Full workflow templates from database (template_type='workflow')
   - Include: Intelligently selected assessment types (SAST vs SAST,SCA)
   - Include: PR optimization if applicable
   
   **B. `enhance_workflow` recommendations** (NEW):
   - When: Workflows with build jobs exist BUT no security scans
   - Use: Job or step fragments from database (template_type='job'/'step')
   - Include: Insertion point information (after_build, after_test, end)
   - Include: Which existing workflow file to modify
   - Include: Assessment type based on detected package managers
   - Include: PR optimization if workflow has PR triggers

### Step 2: Enhanced Recommendation Object Structure

```python
{
    "type": "new_workflow" | "enhance_workflow",
    "template_name": str,
    "description": str,
    "tool_type": "polaris" | "coverity" | "blackduck",
    "category": "sast" | "sca" | "sast,sca",
    "assessment_type": "SAST" | "SCA" | "SAST,SCA",
    "reason": str,
    
    # For enhance_workflow only:
    "target_workflow": {
        "file_name": ".github/workflows/ci.yml",
        "file_path": ".github/workflows/ci.yml",
        "insertion_point": {
            "location": "after_build" | "after_test" | "end",
            "after_job": str | null,
            "reasoning": str
        }
    },
    
    # Enhancement options:
    "has_pr_optimization": bool,
    "pr_optimization_reason": str | null,
    
    # Package manager detection results:
    "detected_package_managers": [
        {"name": "maven", "files": ["pom.xml"], "languages": ["java"]}
    ],
    
    # Template info:
    "template_id": int,  # Database template ID
    "template_type": "workflow" | "job" | "step",
    "template_fragment_type": "job" | "step" | null  # For fragments
}
```

### Step 3: Backend Implementation Flow

```python
async def analyze_repositories_with_blackduck(request: RepositoryAnalysisRequest):
    for repo_name in request.repositories:
        # 1. Get repository file tree
        file_list = await fetch_repo_file_tree(repo_name, github_token)
        
        # 2. Determine assessment types based on package managers
        assessment_recommendation = determine_assessment_types(
            file_list, 
            detected_languages
        )
        
        # 3. Fetch and parse workflow files
        workflow_files = await fetch_workflow_files(repo_name, github_token)
        
        if workflow_files:
            # Parse each workflow
            parsed_workflows = []
            for wf_file in workflow_files:
                parser = WorkflowParser()
                analysis = parser.analyze_workflow(wf_file.content, wf_file.name)
                parsed_workflows.append({
                    "file": wf_file,
                    "analysis": analysis
                })
            
            # Check if ANY workflow has security scans
            has_security = any(w["analysis"]["has_security_scan"] for w in parsed_workflows)
            
            # Check if ANY workflow has build jobs
            has_build = any(w["analysis"]["has_build_job"] for w in parsed_workflows)
            
            if has_security:
                # Already has security scans
                repo_result["blackduck_analysis"] = {
                    "status": "configured",
                    "recommended_templates": []
                }
            elif has_build:
                # Has workflows with builds but no security - ENHANCE
                recommendations = await generate_enhancement_recommendations(
                    repo_name=repo_name,
                    parsed_workflows=parsed_workflows,
                    assessment_recommendation=assessment_recommendation,
                    detected_languages=detected_languages
                )
                repo_result["blackduck_analysis"] = {
                    "status": "needs_enhancement",
                    "recommended_templates": recommendations  # type: "enhance_workflow"
                }
            else:
                # Has workflows but no builds - NEW WORKFLOW
                recommendations = await generate_new_workflow_recommendations(
                    assessment_recommendation=assessment_recommendation,
                    detected_languages=detected_languages
                )
                repo_result["blackduck_analysis"] = {
                    "status": "needs_new_workflow",
                    "recommended_templates": recommendations  # type: "new_workflow"
                }
        else:
            # No workflows at all - NEW WORKFLOW
            recommendations = await generate_new_workflow_recommendations(
                assessment_recommendation=assessment_recommendation,
                detected_languages=detected_languages
            )
            repo_result["blackduck_analysis"] = {
                "status": "no_workflows",
                "recommended_templates": recommendations
            }
```

### Step 4: Helper Functions to Implement

#### `fetch_repo_file_tree(repo_name, token)`
- Call GitHub API: `/repos/{owner}/{repo}/git/trees/{default_branch}?recursive=1`
- Return list of file paths

#### `generate_enhancement_recommendations(repo_name, parsed_workflows, assessment_recommendation, languages)`
- Find the best workflow to enhance (the one with most build steps)
- Get insertion points from WorkflowParser
- Query template fragments from database matching:
  - `template_type='job'` or `'step'`
  - `category` matching tool (polaris/coverity/blackduck_sca)
  - `meta_data.compatible_languages` contains detected language
- Check if workflow has PR triggers
- Generate PR optimization config if applicable
- Build recommendation object with type="enhance_workflow"

#### `generate_new_workflow_recommendations(assessment_recommendation, languages)`
- Query full workflow templates from database:
  - `template_type='workflow'`
  - `category` matching recommended tools
- Apply PR optimization (always yes for new workflows with push+PR triggers)
- Build recommendation object with type="new_workflow"

### Step 5: Database Query Examples

```python
from templates_crud import TemplateCRUD
from assessment_logic import AssessmentType

# Get job fragment for Polaris SAST for Java
db = next(get_db())
job_fragments = TemplateCRUD.get_templates_by_type(db, 'job')
polaris_jobs = [t for t in job_fragments if t.category == 'polaris']
java_compatible = [
    t for t in polaris_jobs 
    if 'java' in json.loads(t.meta_data).get('compatible_languages', [])
]

# Get full workflow templates
workflows = TemplateCRUD.get_templates_by_type(db, 'workflow')
polaris_workflows = [t for t in workflows if t.category == 'polaris']
```

## Frontend Changes (Tasks 8-9)
- Will be implemented after backend is working
- Display "enhance_workflow" cards differently
- Show diff viewer modal
- Preview/Apply endpoints

## Testing Strategy
1. Test with Java Maven repo (has pom.xml → SAST,SCA)
2. Test with Python no requirements.txt → SAST only
3. Test with repo that has workflows but no security scans
4. Test with repo that has workflows with existing security scans
5. Test PR optimization inclusion

## Next Steps
1. Implement `fetch_repo_file_tree()`
2. Integrate `determine_assessment_types()` into analysis loop
3. Implement `generate_enhancement_recommendations()`
4. Implement `generate_new_workflow_recommendations()`
5. Test with real repositories
6. Implement preview/apply endpoints (Tasks 6-7)
7. Update frontend (Tasks 8-9)
8. End-to-end testing (Task 10)
