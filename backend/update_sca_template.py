"""Update SCA template in database from corrected YAML file"""
from database import SessionLocal
from templates_crud import TemplateCRUD

def update_sca_template():
    """Update the Black Duck SCA Scan Workflow template in database from file"""
    db = SessionLocal()
    
    try:
        # Read the corrected file
        with open('templates/blackduck/SCA,IAC.yml', 'r', encoding='utf-8') as f:
            corrected_content = f.read()
        
        # Get the template from database
        template = TemplateCRUD.get_template_by_name(db, "Black Duck SCA Scan Job")
        
        if not template:
            print("Template 'Black Duck SCA Scan Job' not found!")
            return
        
        print(f"Found template: {template.name}")
        print(f"Current content length: {len(template.content)} characters")
        print(f"New content length: {len(corrected_content)} characters")
        
        # Update the template
        TemplateCRUD.update_template(db, template.id, content=corrected_content)
        print(f"✓ Updated template in database: {template.name}")
        
    finally:
        db.close()

if __name__ == "__main__":
    update_sca_template()