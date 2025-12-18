import sys
import os
sys.path.append(r'C:\Users\JouniLehto\repos\migration-tool\backend')

from workflow_analyzer import LocalWorkflowAnalyzer

# Test workflow content
test_workflow = """
name: Mixed Security Test
on:
  push:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    
    steps:
    - name: Checkout
      uses: actions/checkout@v4
    
    - name: Setup Node.js
      uses: actions/setup-node@v3
      with:
        node-version: '18'
        
    - name: Install npm dependencies
      run: npm install
      
    - name: Setup Java
      uses: actions/setup-java@v3
      with:
        java-version: '17'
        
    - name: Build with Gradle
      run: ./gradlew build
      
    - name: Polaris SAST scan
      uses: blackduck-inc/black-duck-security-scan@v2
      with:
        polaris_server_url: ${{ vars.POLARIS_SERVER_URL }}
        polaris_access_token: ${{ secrets.POLARIS_ACCESS_TOKEN }}
    - name: Build Docker image
      run: docker build -t myapp:latest .
      
    - name: Deploy to production
      run: echo "Deploying application"
"""

# Test the analyzer directly
import asyncio

async def test_analyzer():
    analyzer = LocalWorkflowAnalyzer()
    result = await analyzer.analyze_workflow(test_workflow, "test-workflow.yml")
    return result

result = asyncio.run(test_analyzer())

print("=== BLACKDUCK ANALYSIS RESULTS ===")
print("\n🔧 DETECTED BLACK DUCK TOOLS:")
for tool in result.blackduck_analysis.detected_tools:
    print(f"  ✅ {tool.tool_type.value} (quality: {tool.configuration_quality:.1f})")

print("\n📦 DETECTED PACKAGE MANAGERS:")
for pm in result.blackduck_analysis.package_managers:
    print(f"  📦 {pm.name} → Files: {pm.files_detected}")

print(f"\n🚨 SECURITY GAPS ({len(result.blackduck_analysis.security_gaps)} found):")
for gap in result.blackduck_analysis.security_gaps:
    print(f"  ❌ Missing {gap.missing_tool.value} ({gap.priority} priority)")
    print(f"     Trigger: {gap.technology_trigger}")
    print(f"     Reasoning: {gap.reasoning}")
    print()

print(f"\n📦 BINARY ARTIFACTS: {result.blackduck_analysis.binary_artifacts}")

print("\n💡 RECOMMENDATIONS:")
for rec in result.blackduck_analysis.recommendations:
    print(f"  • {rec}")