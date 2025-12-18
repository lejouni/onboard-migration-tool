"""Test workflow recommendation filtering"""
from database import SessionLocal
from templates_crud import TemplateCRUD
import json

db = SessionLocal()

try:
    # Get all workflow templates
    workflow_templates = TemplateCRUD.get_templates_by_type(db, 'workflow')
    
    print(f'\n=== ALL WORKFLOW TEMPLATES ({len(workflow_templates)}) ===\n')
    for t in workflow_templates:
        meta = t.meta_data if isinstance(t.meta_data, dict) else {}
        print(f'{t.name}')
        print(f'  Ends with "Workflow": {t.name.endswith("Workflow")}')
        print(f'  Category: {t.category}')
        print(f'  Languages: {meta.get("compatible_languages", [])}')
        print()
    
    # Filter by name ending with "Workflow"
    filtered = [t for t in workflow_templates if t.name.endswith('Workflow')]
    
    print(f'\n=== FILTERED BY "Workflow" SUFFIX ({len(filtered)}) ===\n')
    for t in filtered:
        meta = t.meta_data if isinstance(t.meta_data, dict) else {}
        print(f'{t.name}')
        print(f'  Category: {t.category}')
        print(f'  Languages: {meta.get("compatible_languages", [])}')
        print()
    
    # Test filtering for SAST recommendation with Java
    print('\n=== SAST RECOMMENDATION FOR JAVA ===\n')
    sast_templates = [
        t for t in filtered 
        if t.category in ['polaris', 'coverity']
    ]
    
    for t in sast_templates:
        meta = t.meta_data if isinstance(t.meta_data, dict) else {}
        languages = [l.lower() for l in meta.get('compatible_languages', [])]
        print(f'{t.name}')
        print(f'  Category: {t.category}')
        print(f'  Languages: {meta.get("compatible_languages", [])}')
        print(f'  Compatible with Java: {"java" in languages or "all" in languages}')
        print()
    
finally:
    db.close()
