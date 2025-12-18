"""Show all templates in database categorized by type"""
from database import SessionLocal
from templates_models import Template

db = SessionLocal()

try:
    all_templates = db.query(Template).all()
    
    # Group by template_type
    by_type = {'workflow': [], 'job': [], 'step': [], 'other': []}
    
    for t in all_templates:
        template_type = t.template_type or 'other'
        if template_type in by_type:
            by_type[template_type].append(t)
        else:
            by_type['other'].append(t)
    
    print(f"\n=== ALL TEMPLATES ({len(all_templates)}) ===\n")
    
    for type_name, templates in by_type.items():
        if not templates:
            continue
            
        print(f"\n{type_name.upper()} TEMPLATES ({len(templates)}):")
        print("=" * 60)
        
        for t in templates:
            meta = t.meta_data if isinstance(t.meta_data, dict) else {}
            has_metadata = bool(meta.get('compatible_languages') or meta.get('tool'))
            ends_with_workflow = t.name.endswith('Workflow')
            
            status = []
            if has_metadata:
                status.append("✓ metadata")
            else:
                status.append("✗ no metadata")
            
            if type_name == 'workflow' and ends_with_workflow:
                status.append("✓ suffix")
            elif type_name == 'workflow' and not ends_with_workflow:
                status.append("✗ no suffix")
            
            status_str = " | ".join(status)
            print(f"  • {t.name}")
            print(f"    Category: {t.category or 'None'} | {status_str}")
            
    # Identify templates to remove
    print("\n\n=== CLEANUP RECOMMENDATIONS ===\n")
    
    to_remove = []
    
    # Workflow templates without "Workflow" suffix or metadata
    for t in by_type['workflow']:
        if not t.name.endswith('Workflow'):
            to_remove.append((t, f"Workflow doesn't end with 'Workflow' suffix"))
        elif not t.meta_data or not isinstance(t.meta_data, dict):
            to_remove.append((t, "Workflow missing metadata"))
    
    # Other category templates
    for t in by_type['other']:
        to_remove.append((t, "Unknown template_type"))
    
    if to_remove:
        print("Templates to remove:")
        for t, reason in to_remove:
            print(f"  🗑️  {t.name}")
            print(f"      Reason: {reason}")
            print(f"      Type: {t.template_type or 'None'}")
            print()
    else:
        print("✅ All templates are properly configured!")
    
    print(f"\nTotal templates to remove: {len(to_remove)}")
    
    # Show what will remain
    remaining = len(all_templates) - len(to_remove)
    print(f"Templates remaining after cleanup: {remaining}")
    
    # Count by type after cleanup
    remaining_by_type = {
        'workflow': len([t for t in by_type['workflow'] if t not in [x[0] for x in to_remove]]),
        'job': len(by_type['job']),
        'step': len(by_type['step'])
    }
    
    print(f"\nAfter cleanup:")
    print(f"  Workflows: {remaining_by_type['workflow']}")
    print(f"  Jobs: {remaining_by_type['job']}")
    print(f"  Steps: {remaining_by_type['step']}")
    
finally:
    db.close()
