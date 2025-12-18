"""Clean up unused templates from database"""
from database import SessionLocal
from templates_models import Template

db = SessionLocal()

try:
    # Templates to remove - old workflows without proper naming/metadata
    templates_to_remove = [
        "Run Polaris SAST for non-compiled languages",
        "Run Polaris SCA for non-compiled languages",
        "Run Polaris SAST and SCA for non-compiled languages",
        "Black Duck SCA Scan",  # Old one without "Workflow" suffix
        "Polaris steps"
    ]
    
    print("\n=== CLEANING UP UNUSED TEMPLATES ===\n")
    
    removed_count = 0
    
    for template_name in templates_to_remove:
        template = db.query(Template).filter(Template.name == template_name).first()
        if template:
            print(f"🗑️  Removing: {template_name}")
            print(f"   Type: {template.template_type or 'None'}")
            print(f"   Category: {template.category or 'None'}")
            db.delete(template)
            removed_count += 1
        else:
            print(f"⚠️  Not found: {template_name}")
    
    db.commit()
    
    print(f"\n✅ Removed {removed_count} templates")
    
    # Show remaining templates
    remaining = db.query(Template).all()
    
    print(f"\n📊 REMAINING TEMPLATES ({len(remaining)}):\n")
    
    workflows = [t for t in remaining if t.template_type == 'workflow']
    jobs = [t for t in remaining if t.template_type == 'job']
    steps = [t for t in remaining if t.template_type == 'step']
    
    print(f"Workflows ({len(workflows)}):")
    for t in workflows:
        print(f"  ✓ {t.name}")
    
    print(f"\nJobs ({len(jobs)}):")
    for t in jobs:
        print(f"  ✓ {t.name}")
    
    print(f"\nSteps ({len(steps)}):")
    for t in steps:
        print(f"  ✓ {t.name}")
    
    print("\n" + "="*60)
    print("SUMMARY:")
    print(f"  • {len(workflows)} workflow templates (all end with 'Workflow')")
    print(f"  • {len(jobs)} job fragments (for enhancing workflows)")
    print(f"  • {len(steps)} step fragments (for inserting into jobs)")
    print(f"  • Total: {len(remaining)} templates")
    print("="*60)
    
finally:
    db.close()
