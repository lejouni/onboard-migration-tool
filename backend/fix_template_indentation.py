"""Fix indentation issues in database templates"""
from database import SessionLocal
from templates_models import Template
from templates_crud import TemplateCRUD

def fix_template_indentation():
    """Fix tab indentation issues in templates"""
    db = SessionLocal()
    
    try:
        # Get the Black Duck SCA Scan Step template
        template = TemplateCRUD.get_template_by_name(db, "Black Duck SCA Scan Step")
        
        if not template:
            print("Template 'Black Duck SCA Scan Step' not found!")
            return
        
        print(f"Found template: {template.name}")
        print(f"Current content length: {len(template.content)} characters")
        
        # Fix the indentation by replacing tabs with spaces
        original_content = template.content
        fixed_content = original_content.replace('\t', '    ')  # Replace tabs with 4 spaces
        
        if original_content != fixed_content:
            # Update the template
            TemplateCRUD.update_template(db, template.id, content=fixed_content)
            print(f"✓ Fixed indentation in template: {template.name}")
            print(f"  Replaced {original_content.count(chr(9))} tab characters with spaces")
        else:
            print(f"✓ No indentation issues found in template: {template.name}")
        
        # Check all other templates for similar issues
        all_templates = TemplateCRUD.get_all_templates(db)
        fixed_count = 0
        
        for t in all_templates:
            if t.id == template.id:
                continue  # Already fixed
            
            if '\t' in t.content:
                fixed = t.content.replace('\t', '    ')
                TemplateCRUD.update_template(db, t.id, content=fixed)
                print(f"✓ Fixed indentation in template: {t.name}")
                fixed_count += 1
        
        if fixed_count > 0:
            print(f"\n✓ Fixed indentation in {fixed_count + 1} templates total")
        else:
            print(f"\n✓ Only 1 template needed fixing")
        
    finally:
        db.close()

if __name__ == "__main__":
    fix_template_indentation()