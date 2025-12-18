import requests
import json

# Test workflow content with mixed security tools
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
      run: |
        echo "Deploying application"
        # This workflow has:
        # - Polaris (SAST) ✓
        # - npm (needs SCA) ❌
        # - gradle (needs SCA) ❌  
        # - Docker (needs BDBA) ❌
"""

# Test the analysis
response = requests.post(
    "http://localhost:8000/api/ai-analyze",
    json={"content": test_workflow},
    headers={"Content-Type": "application/json"}
)

if response.status_code == 200:
    result = response.json()
    print("=== BLACKDUCK ANALYSIS RESULTS ===")
    print(json.dumps(result, indent=2))
else:
    print(f"Error: {response.status_code}")
    print(response.text)