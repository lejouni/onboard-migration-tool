"""
Test script for workflow enhancement features
Tests the helper functions and assessment logic
"""

import sys
import json

# Test imports
print("Testing imports...")
try:
    from workflow_parser import WorkflowParser
    from assessment_logic import determine_assessment_types, AssessmentType
    from pr_optimization import generate_polaris_config_with_event_optimization
    from workflow_enhancement_helpers import (
        generate_enhancement_recommendations,
        generate_new_workflow_recommendations
    )
    print("✓ All imports successful")
except Exception as e:
    print(f"✗ Import error: {e}")
    sys.exit(1)

# Test 1: Workflow Parser
print("\n" + "="*60)
print("Test 1: Workflow Parser")
print("="*60)

sample_workflow = """
name: CI Build
on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-java@v3
        with:
          java-version: '11'
      - name: Build with Maven
        run: mvn clean package
      
  test:
    runs-on: ubuntu-latest
    needs: build
    steps:
      - uses: actions/checkout@v3
      - name: Run tests
        run: mvn test
"""

try:
    parser = WorkflowParser()
    analysis = parser.analyze_workflow(sample_workflow, "ci.yml")
    
    print(f"✓ Workflow parsed successfully")
    print(f"  - Workflow name: {analysis['workflow_name']}")
    print(f"  - Jobs: {analysis['job_count']}")
    print(f"  - Has build job: {analysis['has_build_job']}")
    print(f"  - Has test job: {analysis['has_test_job']}")
    print(f"  - Has security scan: {analysis['has_security_scan']}")
    print(f"  - Has PR trigger: {analysis['has_pr_trigger']}")
    print(f"  - Build tools: {analysis['build_tools']}")
    print(f"  - Languages: {analysis['languages']}")
    print(f"  - Insertion points: {len(analysis['insertion_points'])}")
    
    if analysis['insertion_points']:
        first_point = analysis['insertion_points'][0]
        print(f"    * Preferred: {first_point['location']} (after {first_point['after_job']})")
        print(f"    * Reasoning: {first_point['reasoning']}")
    
except Exception as e:
    print(f"✗ Workflow parsing failed: {e}")
    import traceback
    traceback.print_exc()

# Test 2: Assessment Type Determination
print("\n" + "="*60)
print("Test 2: Assessment Type Determination")
print("="*60)

test_cases = [
    {
        "name": "Java Maven project",
        "files": ["src/main/java/App.java", "pom.xml", "README.md"],
        "languages": ["Java"]
    },
    {
        "name": "Python with requirements",
        "files": ["main.py", "requirements.txt"],
        "languages": ["Python"]
    },
    {
        "name": "JavaScript NPM project",
        "files": ["src/index.js", "package.json"],
        "languages": ["JavaScript"]
    },
    {
        "name": "Plain Python (no package manager)",
        "files": ["script.py", "utils.py"],
        "languages": ["Python"]
    }
]

for test in test_cases:
    try:
        recommendation = determine_assessment_types(test['files'], test['languages'])
        print(f"\n✓ {test['name']}")
        print(f"  - Assessment type: {recommendation.assessment_type.value}")
        print(f"  - Primary language: {recommendation.primary_language}")
        print(f"  - Package managers: {len(recommendation.package_managers)}")
        for pm in recommendation.package_managers:
            print(f"    * {pm.package_manager}: {pm.files_found}")
    except Exception as e:
        print(f"✗ {test['name']} failed: {e}")

# Test 3: PR Optimization
print("\n" + "="*60)
print("Test 3: PR Optimization")
print("="*60)

test_configs = [
    {"assessment": AssessmentType.SAST, "has_pr": True, "should_optimize": True},
    {"assessment": AssessmentType.SAST, "has_pr": False, "should_optimize": False},
    {"assessment": AssessmentType.SAST_SCA, "has_pr": True, "should_optimize": True},
    {"assessment": AssessmentType.SCA, "has_pr": True, "should_optimize": False},
]

for config in test_configs:
    try:
        env_vars = generate_polaris_config_with_event_optimization(
            config['assessment'],
            config['has_pr']
        )
        
        has_optimization = 'POLARIS_TEST_SAST_TYPE' in env_vars
        result = "✓" if has_optimization == config['should_optimize'] else "✗"
        
        print(f"\n{result} {config['assessment'].value} with PR={config['has_pr']}")
        print(f"  - Expected optimization: {config['should_optimize']}")
        print(f"  - Got optimization: {has_optimization}")
        
        for key, value in env_vars.items():
            print(f"  - {key}: {value}")
    except Exception as e:
        print(f"✗ Test failed: {e}")

# Test 4: Template Query (requires database)
print("\n" + "="*60)
print("Test 4: Database Template Query")
print("="*60)

try:
    from database import get_db
    from templates_crud import TemplateCRUD
    
    db = next(get_db())
    try:
        # Get all templates by type
        workflows = TemplateCRUD.get_templates_by_type(db, 'workflow')
        jobs = TemplateCRUD.get_templates_by_type(db, 'job')
        steps = TemplateCRUD.get_templates_by_type(db, 'step')
        
        print(f"✓ Database connected successfully")
        print(f"  - Workflow templates: {len(workflows)}")
        print(f"  - Job fragments: {len(jobs)}")
        print(f"  - Step fragments: {len(steps)}")
        
        # Show job fragments
        if jobs:
            print(f"\n  Job fragments:")
            for job in jobs:
                print(f"    * {job.name} (category: {job.category})")
                try:
                    meta_data = json.loads(job.meta_data) if job.meta_data else {}
                    languages = meta_data.get('compatible_languages', [])
                    if languages:
                        print(f"      Languages: {', '.join(languages)}")
                except Exception:
                    pass
        
        # Test category filtering
        polaris_templates = TemplateCRUD.get_templates_by_category(db, 'polaris')
        print(f"\n  - Polaris templates: {len(polaris_templates)}")
        
    finally:
        db.close()
        
except Exception as e:
    print(f"✗ Database test failed: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*60)
print("All tests completed!")
print("="*60)
