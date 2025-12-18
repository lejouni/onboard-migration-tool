"""
Migration script to update template categories from tool names to scanning types.

New category system:
- Categories represent scanning types: SAST, SCA, IAC, DAST
- Templates can have multiple categories (comma-separated)
- Template mappings:
  - Polaris → SAST,SCA,IAC,DAST
  - Black Duck SCA → SCA,IAC
  - Coverity → SAST,IAC
  - SRM → Remove (deprecated)
"""

from database import SessionLocal
from templates_models import Template
from sqlalchemy import text

def migrate_categories():
    """Migrate template categories to new scanning type system"""
    db = SessionLocal()
    
    try:
        # Define the category mappings
        category_mappings = {
            'polaris': 'SAST,SCA,IAC,DAST',
            'blackduck_sca': 'SCA,IAC',
            'coverity': 'SAST,IAC',
            'srm': None  # Will be removed
        }
        
        print("Starting category migration...")
        print("-" * 60)
        
        # Get all templates
        templates = db.query(Template).all()
        
        updated_count = 0
        removed_count = 0
        
        for template in templates:
            old_category = template.category
            
            if old_category in category_mappings:
                new_category = category_mappings[old_category]
                
                if new_category is None:
                    # Remove SRM templates
                    print(f"Removing deprecated template: {template.name} (category: {old_category})")
                    db.delete(template)
                    removed_count += 1
                else:
                    # Update to new category system
                    print(f"Updating: {template.name}")
                    print(f"  Old category: {old_category}")
                    print(f"  New category: {new_category}")
                    template.category = new_category
                    updated_count += 1
            else:
                print(f"Warning: Unknown category '{old_category}' for template: {template.name}")
        
        # Commit changes
        db.commit()
        
        print("-" * 60)
        print(f"Migration complete!")
        print(f"  Templates updated: {updated_count}")
        print(f"  Templates removed: {removed_count}")
        
        # Display final state
        print("\nFinal template categories:")
        print("-" * 60)
        templates = db.query(Template).all()
        for template in templates:
            print(f"{template.name:50} → {template.category}")
        
    except Exception as e:
        print(f"Error during migration: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    migrate_categories()