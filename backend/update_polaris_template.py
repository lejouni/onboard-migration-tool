"""Update Polaris Security Scan Workflow with content from polaris-sast.yml"""
import os
from database import SessionLocal
from templates_models import Template

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), 'templates', 'blackduck')

db = SessionLocal()

try:
    # Read the polaris-sast.yml file
    yaml_file = os.path.join(TEMPLATES_DIR, 'polaris-sast.yml')
    
    with open(yaml_file, 'r', encoding='utf-8') as f:
        yaml_content = f.read()
    
    # Find the Polaris Security Scan Workflow in database
    template = db.query(Template).filter(
        Template.name == 'Polaris Security Scan Workflow'
    ).first()
    
    if template:
        print(f"\n📝 Updating: {template.name}")
        print(f"   Old content: {len(template.content)} chars")
        print(f"   New content: {len(yaml_content)} chars")
        
        # Update the content
        template.content = yaml_content
        
        db.commit()
        
        print(f"   ✅ Updated successfully!")
        
        # Verify
        print(f"\n✓ Verification:")
        print(f"   Database content: {len(template.content)} chars")
        print(f"   Matches YAML file: {template.content.strip() == yaml_content.strip()}")
    else:
        print("❌ Template not found in database!")
        
finally:
    db.close()
