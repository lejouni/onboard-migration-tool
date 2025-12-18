"""Compare YAML files with database templates"""
import os
from database import SessionLocal
from templates_models import Template

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), 'templates', 'blackduck')

db = SessionLocal()

try:
    # Get workflow templates from database
    workflows = db.query(Template).filter(Template.template_type == 'workflow').all()
    
    print("\n=== COMPARING YAML FILES WITH DATABASE ===\n")
    
    yaml_files = [
        'coverity-scan.yml',
        'polaris-sast.yml',
        'blackduck-sca.yml',
        'srm-scan.yml',
        'comprehensive-security.yml'
    ]
    
    for yaml_file in yaml_files:
        file_path = os.path.join(TEMPLATES_DIR, yaml_file)
        
        if not os.path.exists(file_path):
            print(f"❌ {yaml_file} - FILE NOT FOUND")
            continue
        
        with open(file_path, 'r', encoding='utf-8') as f:
            yaml_content = f.read()
        
        # Try to find matching template in database
        # The database template names have " Workflow" suffix
        base_name = yaml_file.replace('.yml', '')
        
        # Map file names to expected database names
        db_name_map = {
            'coverity-scan': 'Black Duck Coverity Static Analysis Workflow',
            'polaris-sast': 'Polaris Security Scan Workflow',
            'blackduck-sca': 'Black Duck SCA Scan Workflow',
            'srm-scan': 'Black Duck SRM Workflow',
            'comprehensive-security': 'Comprehensive Black Duck Security Workflow'
        }
        
        db_name = db_name_map.get(base_name)
        db_template = None
        
        if db_name:
            db_template = next((t for t in workflows if t.name == db_name), None)
        
        print(f"\n📄 {yaml_file}")
        print(f"   File size: {len(yaml_content)} chars")
        
        if db_template:
            print(f"   ✓ Found in DB: {db_template.name}")
            print(f"   DB size: {len(db_template.content)} chars")
            
            if yaml_content.strip() == db_template.content.strip():
                print(f"   ✅ CONTENT MATCHES")
            else:
                print(f"   ⚠️  CONTENT DIFFERS")
                print(f"   File has {len(yaml_content)} chars, DB has {len(db_template.content)} chars")
        else:
            print(f"   ⏭️  NOT IN DATABASE (likely skipped)")
    
    print("\n\n=== DATABASE TEMPLATES ===\n")
    for t in workflows:
        print(f"✓ {t.name}")
        print(f"  Content: {len(t.content)} chars")
        print(f"  Category: {t.category}")
        print()
    
finally:
    db.close()
