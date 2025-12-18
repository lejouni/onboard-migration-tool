"""Test step fragment insertion into existing jobs"""
import yaml
from workflow_parser import WorkflowParser

# Sample workflow with a build job
sample_workflow = """
name: CI
on: [push, pull_request]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
      
      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '18'
      
      - name: Install dependencies
        run: npm install
      
      - name: Build
        run: npm run build
      
      - name: Test
        run: npm test
"""

# Polaris step fragment
polaris_step = """
- name: Polaris Security Scan
  uses: blackduck-inc/black-duck-security-scan@v2
  with:
    polaris_server_url: ${{ vars.POLARIS_SERVER_URL }}
    polaris_access_token: ${{ secrets.POLARIS_ACCESS_TOKEN }}
    polaris_application_name: ${{ github.event.repository.name }}
    polaris_project_name: ${{ github.event.repository.name }}
    polaris_assessment_types: 'SAST,SCA'
    polaris_prComment_enabled: true
    github_token: ${{ secrets.GITHUB_TOKEN }}
"""

def test_insert_step_after_build():
    """Test inserting security scan step after build steps"""
    parser = WorkflowParser()
    
    print("\n=== TEST: Insert Step After Build ===\n")
    print("Original workflow:")
    print(sample_workflow)
    print("\n" + "="*60 + "\n")
    
    # Insert step after build
    enhanced = parser.insert_step_into_job(
        workflow_content=sample_workflow,
        step_yaml=polaris_step,
        target_job='build',
        insert_position='after_build'
    )
    
    print("Enhanced workflow:")
    print(enhanced)
    print("\n" + "="*60 + "\n")
    
    # Verify the step was inserted
    enhanced_dict = yaml.safe_load(enhanced)
    build_steps = enhanced_dict['jobs']['build']['steps']
    
    print(f"Total steps in build job: {len(build_steps)}")
    print("\nStep order:")
    for i, step in enumerate(build_steps):
        print(f"  {i+1}. {step.get('name', 'Unnamed')}")
    
    # Find Polaris step
    polaris_index = None
    build_index = None
    test_index = None
    
    for i, step in enumerate(build_steps):
        name = step.get('name', '')
        if 'Polaris' in name:
            polaris_index = i
        if 'Build' in name:
            build_index = i
        if 'Test' in name:
            test_index = i
    
    print(f"\nBuild step index: {build_index}")
    print(f"Polaris step index: {polaris_index}")
    print(f"Test step index: {test_index}")
    
    # Verify Polaris is after Build but before or at Test
    if polaris_index and build_index:
        if polaris_index > build_index:
            print("\n✅ SUCCESS: Polaris step inserted after Build step")
        else:
            print("\n❌ FAIL: Polaris step should be after Build step")
    else:
        print("\n❌ FAIL: Could not find required steps")

def test_insert_step_at_end():
    """Test inserting step at end of job"""
    parser = WorkflowParser()
    
    print("\n=== TEST: Insert Step At End ===\n")
    
    enhanced = parser.insert_step_into_job(
        workflow_content=sample_workflow,
        step_yaml=polaris_step,
        target_job='build',
        insert_position='end'
    )
    
    enhanced_dict = yaml.safe_load(enhanced)
    build_steps = enhanced_dict['jobs']['build']['steps']
    
    last_step = build_steps[-1]
    print(f"Last step: {last_step.get('name', 'Unnamed')}")
    
    if 'Polaris' in last_step.get('name', ''):
        print("✅ SUCCESS: Polaris step inserted at end")
    else:
        print("❌ FAIL: Polaris step should be last")

if __name__ == '__main__':
    test_insert_step_after_build()
    test_insert_step_at_end()
