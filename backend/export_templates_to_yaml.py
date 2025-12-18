"""Export templates from database to YAML files"""
import os
from database import SessionLocal
from templates_models import Template
from templates_crud import TemplateCRUD

def export_templates_to_yaml():
    """Export all workflow templates from database to YAML files"""
    db = SessionLocal()
    
    try:
        # Get all workflow templates
        workflows = TemplateCRUD.get_templates_by_type(db, 'workflow')
        
        print(f"\n=== Exporting {len(workflows)} workflow templates ===\n")
        
        # Create templates directory structure
        templates_dir = "templates/blackduck"
        os.makedirs(templates_dir, exist_ok=True)
        
        exported_count = 0
        
        for template in workflows:
            # Determine filename based on category or name
            if template.category:
                # Use category-based naming
                filename = f"{template.category}.yml"
            else:
                # Fallback to name-based naming (convert to kebab-case)
                name_parts = template.name.replace('Workflow', '').strip()
                filename = name_parts.lower().replace(' ', '-') + '.yml'
            
            filepath = os.path.join(templates_dir, filename)
            
            # Write template content to file
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(template.content)
            
            print(f"✓ Exported: {template.name} -> {filepath}")
            exported_count += 1
        
        print(f"\n=== Successfully exported {exported_count} templates ===\n")
        
        # Also export job and step fragments if they exist
        jobs = TemplateCRUD.get_templates_by_type(db, 'job')
        steps = TemplateCRUD.get_templates_by_type(db, 'step')
        
        if jobs:
            jobs_dir = os.path.join(templates_dir, "jobs")
            os.makedirs(jobs_dir, exist_ok=True)
            print(f"\nExporting {len(jobs)} job fragments...")
            for job in jobs:
                filename = job.name.lower().replace(' ', '-') + '.yml'
                filepath = os.path.join(jobs_dir, filename)
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(job.content)
                print(f"✓ Exported job: {job.name} -> {filepath}")
        
        if steps:
            steps_dir = os.path.join(templates_dir, "steps")
            os.makedirs(steps_dir, exist_ok=True)
            print(f"\nExporting {len(steps)} step fragments...")
            for step in steps:
                filename = step.name.lower().replace(' ', '-') + '.yml'
                filepath = os.path.join(steps_dir, filename)
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(step.content)
                print(f"✓ Exported step: {step.name} -> {filepath}")
        
    finally:
        db.close()

if __name__ == "__main__":
    export_templates_to_yaml()