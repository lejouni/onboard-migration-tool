from database import get_db
from templates_crud import TemplateCRUD
import json

db = next(get_db())
templates = TemplateCRUD.get_all_templates(db)

print(f"Total templates: {len(templates)}\n")

for template in templates:
    print(f"Template: {template.name}")
    print(f"Type: {template.template_type}")
    if template.meta_data:
        print(f"Metadata keys: {list(template.meta_data.keys())}")
        if 'required_custom_attributes' in template.meta_data:
            print(f"✅ Has required_custom_attributes: {template.meta_data['required_custom_attributes']}")
        else:
            print("❌ Missing required_custom_attributes")
    else:
        print("❌ No metadata")
    print("-" * 50)

db.close()