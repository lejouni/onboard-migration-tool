"""
Script to add template fragments and full workflow templates to the database
- Job/step fragments can be used to enhance existing workflows
- Full workflow templates can be used to create new workflows from scratch
"""
import os
import json
from database import SessionLocal
from templates_crud import TemplateCRUD
from templates_models import Template

# Path to templates directory
TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), 'templates', 'blackduck')
TEMPLATES_JSON = os.path.join(TEMPLATES_DIR, 'templates.json')

# Polaris Job Fragment (complete job that can be inserted into workflow)
POLARIS_JOB_FRAGMENT = """polaris-security-scan:
  runs-on: ubuntu-latest
  name: Polaris Security Analysis
  steps:
    - name: Checkout Source
      uses: actions/checkout@v4
      
    - name: Polaris SAST+SCA Scan
      uses: blackduck-inc/black-duck-security-scan@v2
      with:
        polaris_server_url: ${{ vars.POLARIS_SERVER_URL }}
        polaris_access_token: ${{ secrets.POLARIS_ACCESS_TOKEN }}
        polaris_application_name: ${{ github.event.repository.name }}
        polaris_project_name: ${{ github.event.repository.name }}
        polaris_assessment_types: '{assessment_types}'
        polaris_test_sast_type: ${{ (github.event_name == 'pull_request' && contains(fromJSON('["opened","synchronize","reopened"]'), github.event.action)) && 'SAST_RAPID' || '' }}
        polaris_prComment_enabled: true
        github_token: ${{ secrets.GITHUB_TOKEN }}
    
    - name: Save Logs
      if: always()
      uses: actions/upload-artifact@v4
      with:
        name: polaris-logs
        path: ${{ github.workspace }}/.bridge
        include-hidden-files: true"""

# Polaris Step Fragment (just the scan step, can be added to existing job)
POLARIS_STEP_FRAGMENT = """- name: Polaris Security Scan
  uses: blackduck-inc/black-duck-security-scan@v2
  with:
    polaris_server_url: ${{ vars.POLARIS_SERVER_URL }}
    polaris_access_token: ${{ secrets.POLARIS_ACCESS_TOKEN }}
    polaris_application_name: ${{ github.event.repository.name }}
    polaris_project_name: ${{ github.event.repository.name }}
    polaris_assessment_types: '{assessment_types}'
    polaris_test_sast_type: ${{ (github.event_name == 'pull_request' && contains(fromJSON('["opened","synchronize","reopened"]'), github.event.action)) && 'SAST_RAPID' || '' }}
    polaris_prComment_enabled: true
    github_token: ${{ secrets.GITHUB_TOKEN }}"""

# Coverity Job Fragment
COVERITY_JOB_FRAGMENT = """coverity-security-scan:
  runs-on: ubuntu-latest
  name: Coverity Static Analysis
  steps:
    - name: Checkout Source
      uses: actions/checkout@v4
      
    - name: Coverity Scan
      uses: blackduck-inc/black-duck-security-scan@v2
      with:
        coverity_url: ${{ vars.COVERITY_URL }}
        coverity_user: ${{ secrets.COVERITY_USER }}
        coverity_passphrase: ${{ secrets.COVERITY_PASSPHRASE }}
        coverity_project_name: ${{ github.event.repository.name }}
        coverity_stream_name: ${{ github.event.repository.name }}-${{ github.ref_name }}
        coverity_prComment_enabled: true
        github_token: ${{ secrets.GITHUB_TOKEN }}
    
    - name: Save Logs
      if: always()
      uses: actions/upload-artifact@v4
      with:
        name: coverity-logs
        path: ${{ github.workspace }}/.bridge
        include-hidden-files: true"""

# Black Duck SCA Step Fragment
BLACKDUCK_SCA_STEP_FRAGMENT = """- name: Black Duck SCA Scan
  uses: blackduck-inc/black-duck-security-scan@v2
  with:
    blackduck_url: ${{ vars.BLACKDUCK_URL }}
    blackduck_api_token: ${{ secrets.BLACKDUCK_API_TOKEN }}
    blackduck_scan_full: true
    blackduck_prComment_enabled: true
    github_token: ${{ secrets.GITHUB_TOKEN }}"""

def load_workflow_templates():
    """Load full workflow templates from YAML files and templates.json metadata"""
    
    # Templates to skip (use existing Polaris Security Scan Workflow instead)
    SKIP_TEMPLATES = [
        "Black Duck Polaris SAST",
        "Comprehensive Black Duck Security"
    ]
    
    # Load templates metadata
    with open(TEMPLATES_JSON, 'r') as f:
        templates_config = json.load(f)
    
    workflow_templates = []
    
    for template_meta in templates_config['templates']:
        # Skip templates that should use Polaris Security Scan Workflow instead
        if template_meta['name'] in SKIP_TEMPLATES:
            print(f"⏭️  Skipping '{template_meta['name']}' (using Polaris Security Scan Workflow instead)")
            continue
            
        # Read the YAML file content
        yaml_file = os.path.join(TEMPLATES_DIR, template_meta['file'])
        
        if not os.path.exists(yaml_file):
            print(f"⚠️  Warning: Template file not found: {yaml_file}")
            continue
            
        with open(yaml_file, 'r', encoding='utf-8') as f:
            yaml_content = f.read()
        
        # Add "Workflow" suffix to template name
        template_name = template_meta['name'] + " Workflow"
        
        # Determine category from tools
        tools = template_meta.get('tools', [])
        if 'Polaris' in tools and 'Coverity' in tools:
            category = 'comprehensive'
        elif 'Polaris' in tools:
            category = 'polaris'
        elif 'Coverity' in tools:
            category = 'coverity'
        elif 'Black Duck SCA' in tools:
            category = 'blackduck_sca'
        elif 'SRM' in tools:
            category = 'srm'
        else:
            category = 'general'
        
        # Build metadata
        metadata = {
            "tool": tools,
            "compatible_languages": template_meta.get('languages', []),
            "use_cases": template_meta.get('use_cases', []),
            "secrets": template_meta.get('requirements', {}).get('secrets', []),
            "variables": template_meta.get('requirements', {}).get('variables', []),
            "required_custom_attributes": [],
            "features": [],
            "workflow_file": template_meta['file']
        }
        
        # Add features based on tools
        if 'Polaris' in tools or category == 'polaris':
            metadata['features'].extend(['sast', 'sca', 'pr_comments'])
        if 'Coverity' in tools or category == 'coverity':
            metadata['features'].extend(['sast', 'pr_comments'])
        if 'Black Duck SCA' in tools or category == 'blackduck_sca':
            metadata['features'].extend(['sca', 'dependencies', 'pr_comments'])
        if 'SRM' in tools or category == 'srm':
            metadata['features'].extend(['risk_management', 'compliance'])
        
        # Generate keywords
        keywords_list = [category] + tools + template_meta.get('languages', [])
        keywords = ','.join([k.lower().replace(' ', '_') for k in keywords_list])
        
        workflow_templates.append({
            "name": template_name,
            "description": template_meta.get('description', ''),
            "content": yaml_content,
            "keywords": keywords,
            "template_type": "workflow",
            "category": category,
            "metadata": metadata
        })
    
    return workflow_templates

def populate_template_fragments():
    """Add template fragments and full workflow templates to database"""
    db = SessionLocal()
    
    try:
        # Load job and step fragments
        fragments = [
            {
                "name": "Polaris Security Scan Job",
                "description": "Complete Polaris security scan job that can be added to existing workflows. Includes SAST+SCA with PR optimization.",
                "content": POLARIS_JOB_FRAGMENT,
                "keywords": "polaris,sast,sca,security,job,fragment",
                "template_type": "job",
                "category": "polaris",
                "metadata": {
                    "tool": "polaris",
                    "compatible_languages": ["Java", "Python", "JavaScript", "TypeScript", "C#", "Go", "Ruby", "PHP"],
                    "parameters": {
                        "required": ["assessment_types"],
                        "optional": []
                    },
                    "features": ["pr_optimization", "sast", "sca", "pr_comments"],
                    "secrets": ["POLARIS_ACCESS_TOKEN"],
                    "variables": ["POLARIS_SERVER_URL"],
                    "required_custom_attributes": [],
                    "runs_after": ["build", "test"],
                    "use_case": "Add complete security scan job to existing CI/CD workflow"
                }
            },
            {
                "name": "Polaris Security Scan Step",
                "description": "Polaris scan step that can be added to an existing job. Includes SAST+SCA with PR optimization.",
                "content": POLARIS_STEP_FRAGMENT,
                "keywords": "polaris,sast,sca,security,step,fragment",
                "template_type": "step",
                "category": "polaris",
                "metadata": {
                    "tool": "polaris",
                    "compatible_languages": ["Java", "Python", "JavaScript", "TypeScript", "C#", "Go", "Ruby", "PHP"],
                    "parameters": {
                        "required": ["assessment_types"],
                        "optional": []
                    },
                    "features": ["pr_optimization", "sast", "sca", "pr_comments"],
                    "secrets": ["POLARIS_ACCESS_TOKEN"],
                    "variables": ["POLARIS_SERVER_URL"],
                    "required_custom_attributes": [],
                    "insert_after": ["build", "test", "install"],
                    "use_case": "Add security scan step to existing build/test job"
                }
            },
            {
                "name": "Coverity Security Scan Job",
                "description": "Complete Coverity static analysis job for C/C++ projects.",
                "content": COVERITY_JOB_FRAGMENT,
                "keywords": "coverity,sast,security,c,cpp,job,fragment",
                "template_type": "job",
                "category": "coverity",
                "metadata": {
                    "tool": "coverity",
                    "compatible_languages": ["C", "C++"],
                    "parameters": {
                        "required": [],
                        "optional": []
                    },
                    "features": ["sast", "pr_comments"],
                    "secrets": ["COVERITY_USER", "COVERITY_PASSPHRASE"],
                    "variables": ["COVERITY_URL"],
                    "required_custom_attributes": [],
                    "runs_after": ["build"],
                    "use_case": "Add Coverity static analysis for C/C++ projects"
                }
            },
            {
                "name": "Black Duck SCA Scan Step",
                "description": "Black Duck Software Composition Analysis step for dependency scanning.",
                "content": BLACKDUCK_SCA_STEP_FRAGMENT,
                "keywords": "blackduck,sca,dependencies,security,step,fragment",
                "template_type": "step",
                "category": "blackduck_sca",
                "metadata": {
                    "tool": "blackduck_sca",
                    "compatible_languages": ["All"],
                    "parameters": {
                        "required": [],
                        "optional": []
                    },
                    "features": ["sca", "dependencies", "pr_comments"],
                    "secrets": ["BLACKDUCK_API_TOKEN"],
                    "variables": ["BLACKDUCK_URL"],
                    "required_custom_attributes": [],
                    "insert_after": ["build", "install"],
                    "use_case": "Add dependency scanning to existing workflow"
                }
            }
        ]
        
        print("Adding job and step fragments to database...\n")
        
        for fragment in fragments:
            # Check if template already exists
            existing = TemplateCRUD.search_templates(db, fragment["name"])
            
            if existing:
                print(f"⚠️  Template '{fragment['name']}' already exists, updating...")
                # Update the existing template
                existing_template = existing[0]
                existing_template.content = fragment["content"]
                existing_template.description = fragment["description"]
                existing_template.keywords = fragment["keywords"]
                existing_template.template_type = fragment["template_type"]
                existing_template.category = fragment["category"]
                existing_template.meta_data = fragment["metadata"]
                db.commit()
                print(f"✅ Updated {fragment['template_type']}: {fragment['name']}")
            else:
                TemplateCRUD.create_template(
                    db=db,
                    name=fragment["name"],
                    description=fragment["description"],
                    content=fragment["content"],
                    keywords=fragment["keywords"],
                    template_type=fragment["template_type"],
                    category=fragment["category"],
                    meta_data=fragment["metadata"]
                )
                print(f"✅ Added {fragment['template_type']}: {fragment['name']}")
        
        # Load and add full workflow templates
        print("\nAdding full workflow templates to database...\n")
        workflow_templates = load_workflow_templates()
        
        for workflow in workflow_templates:
            # Check if template already exists
            existing = TemplateCRUD.search_templates(db, workflow["name"])
            
            if existing:
                print(f"⚠️  Template '{workflow['name']}' already exists, updating...")
                # Update the existing template
                existing_template = existing[0]
                existing_template.content = workflow["content"]
                existing_template.description = workflow["description"]
                existing_template.keywords = workflow["keywords"]
                existing_template.template_type = workflow["template_type"]
                existing_template.category = workflow["category"]
                existing_template.meta_data = workflow["metadata"]
                db.commit()
                print(f"✅ Updated {workflow['template_type']}: {workflow['name']}")
            else:
                TemplateCRUD.create_template(
                    db=db,
                    name=workflow["name"],
                    description=workflow["description"],
                    content=workflow["content"],
                    keywords=workflow["keywords"],
                    template_type=workflow["template_type"],
                    category=workflow["category"],
                    meta_data=workflow["metadata"]
                )
                print(f"✅ Added {workflow['template_type']}: {workflow['name']}")
        
        print("\n✅ All templates populated successfully!")
        
        # Show summary
        all_templates = db.query(Template).all()
        workflows = [t for t in all_templates if t.template_type == 'workflow']
        jobs = [t for t in all_templates if t.template_type == 'job']
        steps = [t for t in all_templates if t.template_type == 'step']
        
        print("\n📊 Template Summary:")
        print(f"   Workflows: {len(workflows)}")
        print(f"   Jobs: {len(jobs)}")
        print(f"   Steps: {len(steps)}")
        print(f"   Total: {len(all_templates)}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    populate_template_fragments()
