"""
Script to add required_custom_attributes field to existing templates that don't have it
"""
from database import SessionLocal
from templates_models import Template
from sqlalchemy.orm.attributes import flag_modified

def add_required_custom_attributes():
    """Add required_custom_attributes to all templates that don't have it"""
    db = SessionLocal()
    
    try:
        # Get all templates
        templates = db.query(Template).all()
        
        updated_count = 0
        
        for template in templates:
            # Check if template has metadata
            if template.meta_data is None:
                template.meta_data = {}
            
            # Check if required_custom_attributes exists
            if 'required_custom_attributes' not in template.meta_data:
                template.meta_data['required_custom_attributes'] = []
                # Mark the meta_data field as modified so SQLAlchemy knows to update it
                flag_modified(template, 'meta_data')
                updated_count += 1
                print(f"✅ Added required_custom_attributes to: {template.name}")
            else:
                print(f"⏭️  Skipped (already has field): {template.name}")
        
        # Commit changes
        if updated_count > 0:
            db.commit()
            print(f"\n✅ Successfully updated {updated_count} templates")
        else:
            print("\n✅ All templates already have required_custom_attributes field")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    add_required_custom_attributes()