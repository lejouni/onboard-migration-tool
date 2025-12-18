"""Update Polaris Security Scan Workflow with proper metadata"""
from database import SessionLocal
from templates_models import Template

db = SessionLocal()

try:
    # Find the Polaris Security Scan Workflow
    template = db.query(Template).filter(Template.name == "Polaris Security Scan Workflow").first()
    
    if template:
        print(f"\n📝 Updating: {template.name}")
        
        # Update category
        template.category = "polaris"
        
        # Update metadata to match Polaris SAST capabilities
        template.meta_data = {
            "tool": ["Polaris"],
            "compatible_languages": ["JavaScript", "TypeScript", "Java", "Python", "C#", "Go", "C", "C++", "Ruby", "PHP", "Scala", "Kotlin"],
            "use_cases": ["SAST", "SCA", "Code quality", "Security vulnerabilities"],
            "secrets": ["POLARIS_ACCESS_TOKEN"],
            "variables": ["POLARIS_SERVER_URL"],
            "features": ["sast", "sca", "pr_comments", "pr_optimization"],
            "workflow_file": "polaris-sast.yml"
        }
        
        db.commit()
        
        print(f"✅ Updated metadata:")
        print(f"  Category: {template.category}")
        print(f"  Languages: {template.meta_data['compatible_languages']}")
        print(f"  Tools: {template.meta_data['tool']}")
        print(f"  Features: {template.meta_data['features']}")
        print(f"  Secrets: {template.meta_data['secrets']}")
        print(f"  Variables: {template.meta_data['variables']}")
        
    else:
        print("❌ Template not found!")
        
finally:
    db.close()
