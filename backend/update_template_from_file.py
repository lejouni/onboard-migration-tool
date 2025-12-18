"""Update database template from corrected YAML file"""
from database import SessionLocal
from templates_crud import TemplateCRUD

def update_template_from_file():
    """Update the Black Duck SCA Scan Step template in database from file"""
    db = SessionLocal()
    
    try:
        # Read the corrected file
        with open('templates/blackduck/steps/black-duck-sca-scan-step.yml', 'r', encoding='utf-8') as f:
            corrected_content = f.read()
        
        # Get the template from database
        template = TemplateCRUD.get_template_by_name(db, "Black Duck SCA Scan Step")
        
        if not template:
            print("Template 'Black Duck SCA Scan Step' not found!")
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
    update_template_from_file()