"""Final verification: YAML files match database templates"""
import os
from database import SessionLocal
from templates_models import Template

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), 'templates', 'blackduck')

db = SessionLocal()

try:
    workflows = db.query(Template).filter(Template.template_type == 'workflow').all()
    
    print("\n" + "="*70)
    print("FINAL VERIFICATION: YAML FILES ↔ DATABASE TEMPLATES")
    print("="*70 + "\n")
    
    yaml_files = [
        'coverity-scan.yml',
        'polaris-sast.yml',
        'blackduck-sca.yml',
        'srm-scan.yml'
    ]
    
    db_name_map = {
        'coverity-scan': 'Black Duck Coverity Static Analysis Workflow',
        'polaris-sast': 'Polaris Security Scan Workflow',
        'blackduck-sca': 'Black Duck SCA Scan Workflow',
        'srm-scan': 'Black Duck SRM Workflow'
    }
    
    all_match = True
    
    for yaml_file in yaml_files:
        file_path = os.path.join(TEMPLATES_DIR, yaml_file)
        
        with open(file_path, 'r', encoding='utf-8') as f:
            yaml_content = f.read()
        
        base_name = yaml_file.replace('.yml', '')
        db_name = db_name_map.get(base_name)
        db_template = next((t for t in workflows if t.name == db_name), None)
        
        matches = yaml_content.strip() == db_template.content.strip() if db_template else False
        
        status = "✅" if matches else "❌"
        print(f"{status} {yaml_file:30} ↔ {db_name}")
        
        if not matches:
            all_match = False
            
    print("\n" + "="*70)
    
    if all_match:
        print("✅ SUCCESS: All YAML files match their database templates!")
    else:
        print("❌ FAILURE: Some files don't match!")
    
    print("="*70 + "\n")
    
    print("📋 SUMMARY:")
    print(f"   YAML Files:     {len(yaml_files)}")
    print(f"   DB Templates:   {len(workflows)}")
    print(f"   All Match:      {all_match}")
    
    print("\n📂 YAML FILES LOCATION:")
    print(f"   {TEMPLATES_DIR}")
    
    print("\n📦 DATABASE TEMPLATES:")
    for t in workflows:
        meta = t.meta_data if isinstance(t.meta_data, dict) else {}
        langs = meta.get('compatible_languages', [])
        print(f"   • {t.name}")
        print(f"     Category: {t.category}, Languages: {', '.join(langs) if langs else 'N/A'}")
    
finally:
    db.close()
