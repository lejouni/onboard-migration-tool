"""Remove duplicate workflow templates from database"""
from database import SessionLocal
from templates_models import Template

db = SessionLocal()

try:
    templates_to_remove = [
        "Black Duck Polaris SAST Workflow",
        "Comprehensive Black Duck Security Workflow"
    ]
    
    print("\n=== REMOVING DUPLICATE WORKFLOW TEMPLATES ===\n")
    
    for template_name in templates_to_remove:
        template = db.query(Template).filter(Template.name == template_name).first()
        if template:
            print(f"🗑️  Removing: {template_name}")
            db.delete(template)
        else:
            print(f"⚠️  Not found: {template_name}")
    
    db.commit()
    
    print("\n✅ Cleanup complete!")
    
    # Show remaining workflow templates
    workflows = db.query(Template).filter(Template.template_type == 'workflow').all()
    print(f"\n📊 Remaining workflow templates: {len(workflows)}")
    for w in workflows:
        suffix = " ✓" if w.name.endswith('Workflow') else ""
        print(f"  - {w.name}{suffix}")
    
finally:
    db.close()
