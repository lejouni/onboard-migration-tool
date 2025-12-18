"""Verify workflow templates in database"""
from database import SessionLocal
from templates_models import Template
import json

db = SessionLocal()

try:
    workflows = db.query(Template).filter(Template.template_type == 'workflow').all()
    
    print('\n=== WORKFLOW TEMPLATES IN DATABASE ===\n')
    
    for w in workflows:
        meta = w.meta_data if isinstance(w.meta_data, dict) else (json.loads(w.meta_data) if w.meta_data else {})
        print(f'Name: {w.name}')
        print(f'  Category: {w.category}')
        print(f'  Languages: {meta.get("compatible_languages", [])}')
        print(f'  Tools: {meta.get("tool", [])}')
        print(f'  Secrets: {meta.get("secrets", [])}')
        print(f'  Variables: {meta.get("variables", [])}')
        print(f'  Features: {meta.get("features", [])}')
        print(f'  Content length: {len(w.content)} chars')
        print()
        
    print(f'\nTotal workflow templates: {len(workflows)}')
    
    # Show templates that end with "Workflow"
    workflow_suffix = [w for w in workflows if w.name.endswith('Workflow')]
    print(f'Templates ending with "Workflow": {len(workflow_suffix)}')
    for w in workflow_suffix:
        print(f'  - {w.name}')
    
finally:
    db.close()
