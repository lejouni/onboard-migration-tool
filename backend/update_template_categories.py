"""
Script to update template_type and category for existing templates.
This is useful for maintaining template organization without using the UI.
"""

import sys
from sqlalchemy.orm import Session
from database import SessionLocal
from templates_crud import TemplateCRUD

def list_templates(db: Session):
    """List all templates with their current type and category"""
    templates = TemplateCRUD.get_all_templates(db)
    
    print("\n" + "="*80)
    print("CURRENT TEMPLATES")
    print("="*80)
    
    for template in templates:
        print(f"\nID: {template.id}")
        print(f"Name: {template.name}")
        print(f"Type: {template.template_type or 'Not set'}")
        print(f"Category: {template.category or 'Not set'}")
        if template.meta_data:
            if 'compatible_languages' in template.meta_data:
                print(f"Languages: {', '.join(template.meta_data['compatible_languages'])}")
            if 'tools' in template.meta_data:
                print(f"Tools: {', '.join(template.meta_data['tools'])}")
        print("-" * 80)
    
    print(f"\nTotal templates: {len(templates)}\n")

def update_template_metadata(db: Session, template_id: int, template_type: str = None, 
                            category: str = None):
    """Update template type and/or category"""
    template = TemplateCRUD.get_template_by_id(db, template_id)
    
    if not template:
        print(f"❌ Template with ID {template_id} not found!")
        return False
    
    print(f"\n📝 Updating template: {template.name}")
    print(f"Current type: {template.template_type or 'Not set'}")
    print(f"Current category: {template.category or 'Not set'}")
    
    updated = TemplateCRUD.update_template(
        db=db,
        template_id=template_id,
        template_type=template_type,
        category=category
    )
    
    if updated:
        print(f"✅ Updated successfully!")
        print(f"New type: {updated.template_type}")
        print(f"New category: {updated.category}")
        return True
    else:
        print(f"❌ Failed to update template")
        return False

def interactive_update(db: Session):
    """Interactive mode to update templates"""
    list_templates(db)
    
    print("\n" + "="*80)
    print("UPDATE TEMPLATE")
    print("="*80)
    
    try:
        template_id = int(input("\nEnter template ID to update (or 0 to exit): "))
        if template_id == 0:
            return
        
        template = TemplateCRUD.get_template_by_id(db, template_id)
        if not template:
            print(f"❌ Template with ID {template_id} not found!")
            return
        
        print(f"\nUpdating: {template.name}")
        print(f"Current type: {template.template_type or 'Not set'}")
        print(f"Current category: {template.category or 'Not set'}")
        
        print("\nTemplate Types:")
        print("  1. workflow - Complete workflow file")
        print("  2. job - Job fragment to add to existing workflow")
        print("  3. step - Step fragment to insert into existing job")
        
        type_choice = input("\nEnter template type (workflow/job/step) or press Enter to skip: ").strip().lower()
        template_type = type_choice if type_choice in ['workflow', 'job', 'step'] else None
        
        print("\nCategories:")
        print("  1. polaris - Polaris SAST/SCA")
        print("  2. coverity - Coverity SAST")
        print("  3. blackduck_sca - Black Duck SCA")
        print("  4. srm - Software Risk Manager")
        print("  5. custom - Custom category")
        
        category = input("\nEnter category or press Enter to skip: ").strip().lower()
        category = category if category else None
        
        if template_type or category:
            confirm = input(f"\nConfirm update? (y/n): ").strip().lower()
            if confirm == 'y':
                update_template_metadata(db, template_id, template_type, category)
            else:
                print("❌ Update cancelled")
        else:
            print("❌ No changes specified")
            
    except ValueError:
        print("❌ Invalid input!")
    except KeyboardInterrupt:
        print("\n❌ Cancelled")

def bulk_update_by_name_pattern(db: Session):
    """Bulk update templates based on name patterns"""
    templates = TemplateCRUD.get_all_templates(db)
    
    updates = [
        # Update workflow templates (names ending with 'Workflow')
        {
            'pattern': 'Workflow',
            'template_type': 'workflow',
            'check_func': lambda name: name.endswith('Workflow')
        },
        # Update job fragments (names containing 'Job')
        {
            'pattern': 'Job',
            'template_type': 'job',
            'check_func': lambda name: 'Job' in name and not name.endswith('Workflow')
        },
        # Update step fragments (names containing 'Step')
        {
            'pattern': 'Step',
            'template_type': 'step',
            'check_func': lambda name: 'Step' in name
        }
    ]
    
    print("\n" + "="*80)
    print("BULK UPDATE BY NAME PATTERN")
    print("="*80)
    
    updated_count = 0
    for template in templates:
        for update_rule in updates:
            if update_rule['check_func'](template.name):
                if template.template_type != update_rule['template_type']:
                    print(f"\n📝 Updating: {template.name}")
                    print(f"   Old type: {template.template_type}")
                    print(f"   New type: {update_rule['template_type']}")
                    
                    TemplateCRUD.update_template(
                        db=db,
                        template_id=template.id,
                        template_type=update_rule['template_type']
                    )
                    updated_count += 1
                break
    
    print(f"\n✅ Updated {updated_count} templates")

if __name__ == "__main__":
    db = SessionLocal()
    
    try:
        if len(sys.argv) > 1:
            command = sys.argv[1]
            
            if command == "list":
                list_templates(db)
            
            elif command == "bulk":
                bulk_update_by_name_pattern(db)
            
            elif command == "update":
                if len(sys.argv) >= 4:
                    # python update_template_categories.py update <id> <type> [category]
                    template_id = int(sys.argv[2])
                    template_type = sys.argv[3]
                    category = sys.argv[4] if len(sys.argv) > 4 else None
                    update_template_metadata(db, template_id, template_type, category)
                else:
                    print("Usage: python update_template_categories.py update <id> <type> [category]")
                    print("Example: python update_template_categories.py update 1 workflow polaris")
            
            else:
                print("Unknown command. Available commands:")
                print("  list - List all templates")
                print("  bulk - Bulk update based on name patterns")
                print("  update <id> <type> [category] - Update specific template")
                print("  (no args) - Interactive mode")
        
        else:
            # Interactive mode
            interactive_update(db)
    
    finally:
        db.close()
