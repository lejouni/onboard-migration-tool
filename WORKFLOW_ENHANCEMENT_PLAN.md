# AI-Analysis Workflow Enhancement Plan
## Recommending Steps to Add to Existing Workflows

## 📋 Executive Summary

Instead of only recommending **new workflow files**, enhance AI-Analysis to recommend **adding specific steps/jobs to existing workflows**. This allows incremental security improvements without replacing existing CI/CD pipelines.

### Example Use Case
- **Repository**: Java project with Maven build workflow
- **AI Detection**: Primary language = Java, has `pom.xml`
- **Current Behavior**: Recommend creating new `polaris-sast.yml` file
- **Enhanced Behavior**: Recommend adding Polaris scan job to existing `maven-build.yml` with `polaris_assessment_types: SAST,SCA`

---

## 🎯 Goals

1. **Analyze existing workflows** for language/build patterns
2. **Recommend step/job additions** instead of new files
3. **Intelligent assessment type selection** based on detected package managers
4. **Show diff/preview** of proposed changes
5. **Apply changes** to existing workflows (direct commit or PR)

---

## 🔍 Current State Analysis

### What We Have Now
```
AI-Analysis Flow:
1. Detect repository languages (Python, Java, JS, etc.)
2. Check for existing workflows
3. If workflows exist → Check for Black Duck tools
4. If no Black Duck tools → Recommend NEW workflow templates
```

### Templates Structure
```
backend/templates/blackduck/
├── polaris-sast.yml           # Full workflow file
├── coverity-scan.yml          # Full workflow file
├── blackduck-sca.yml          # Full workflow file
└── comprehensive-security.yml # Full workflow file
```

### Limitation
Templates are **complete workflow files** - we need **reusable step fragments**.

---

## 🏗️ Architecture Plan

### 1. New Template Structure

Create **step templates** alongside full workflow templates:

```
backend/templates/blackduck/
├── workflows/                    # Full workflow files (existing)
│   ├── polaris-sast.yml
│   ├── coverity-scan.yml
│   └── blackduck-sca.yml
│
├── steps/                        # NEW: Reusable step fragments
│   ├── polaris-step.yml          # Just the Polaris scan step
│   ├── coverity-step.yml         # Just the Coverity scan step
│   ├── blackduck-sca-step.yml    # Just the SCA scan step
│   └── setup-steps/              # Language-specific setup
│       ├── java-setup.yml
│       ├── python-setup.yml
│       └── node-setup.yml
│
└── jobs/                         # NEW: Complete job fragments
    ├── polaris-job.yml           # Complete Polaris job
    ├── coverity-job.yml          # Complete Coverity job
    └── sca-job.yml               # Complete SCA job
```

### 2. Step Template Format

**`steps/polaris-step.yml`** (parameterized fragment):
```yaml
# Fragment: Polaris SAST/SCA Step
# Parameters: {assessment_types, language, has_package_manager}
---
- name: Polaris Security Scan
  uses: blackduck-inc/black-duck-security-scan@v2
  with:
    polaris_server_url: ${{ vars.POLARIS_SERVER_URL }}
    polaris_access_token: ${{ secrets.POLARIS_ACCESS_TOKEN }}
    polaris_application_name: ${{ github.event.repository.name }}
    polaris_project_name: ${{ github.event.repository.name }}
    polaris_assessment_types: '{{ASSESSMENT_TYPES}}'  # SAST or SAST,SCA
    polaris_prComment_enabled: true
    github_token: ${{ secrets.GITHUB_TOKEN }}
    {{#if BUILD_COMMAND}}
    polaris_build_command: '{{BUILD_COMMAND}}'
    {{/if}}
```

**`jobs/polaris-job.yml`** (complete job fragment):
```yaml
# Fragment: Complete Polaris Job
# Can be inserted as new job in existing workflow
---
polaris-security-scan:
  runs-on: ubuntu-latest
  name: Polaris Security Analysis
  steps:
    - name: Checkout Source
      uses: actions/checkout@v4
      
    {{#if LANGUAGE_SETUP}}
    {{{LANGUAGE_SETUP}}}
    {{/if}}
    
    {{#if DEPENDENCY_INSTALL}}
    {{{DEPENDENCY_INSTALL}}}
    {{/if}}
    
    - name: Polaris Security Scan
      uses: blackduck-inc/black-duck-security-scan@v2
      with:
        polaris_server_url: ${{ vars.POLARIS_SERVER_URL }}
        polaris_access_token: ${{ secrets.POLARIS_ACCESS_TOKEN }}
        polaris_application_name: ${{ github.event.repository.name }}
        polaris_project_name: ${{ github.event.repository.name }}
        polaris_assessment_types: '{{ASSESSMENT_TYPES}}'
        {{#if USE_RAPID_SCAN}}
        # Use SAST_RAPID for PR events (faster scans)
        polaris_test_sast_type: ${{ github.event_name == 'pull_request' && 'SAST_RAPID' || '' }}
        {{/if}}
        polaris_prComment_enabled: true
        github_token: ${{ secrets.GITHUB_TOKEN }}
```

---

## 🧠 Enhanced AI-Analysis Logic

### Step 1: Workflow Content Analysis

```python
async def analyze_existing_workflows(repo_name, github_token):
    """
    Deep analysis of existing workflow files
    Returns: {
        'workflow_files': [...],
        'detected_patterns': {
            'build_tools': ['maven', 'gradle', 'npm'],
            'languages': ['Java', 'JavaScript'],
            'test_frameworks': ['JUnit', 'Jest'],
            'existing_security_tools': ['CodeQL'],
            'job_names': ['build', 'test', 'deploy']
        },
        'insertion_opportunities': [
            {
                'file': 'maven-ci.yml',
                'suggested_position': 'after_build_job',
                'reason': 'Security scan should run after build succeeds'
            }
        ]
    }
    """
```

### Step 2: Smart Recommendation Engine

```python
def generate_workflow_recommendations(analysis, languages, package_managers):
    """
    Generate recommendations for workflow enhancements
    
    Logic:
    1. If NO workflows exist → Recommend full workflow templates (current behavior)
    2. If workflows exist WITHOUT security tools → Recommend adding jobs/steps
    3. If workflows exist WITH partial security → Recommend completing coverage
    
    Returns: {
        'recommendation_type': 'add_job' | 'add_step' | 'new_workflow',
        'target_workflow': 'maven-ci.yml',
        'suggested_addition': {
            'type': 'job',
            'position': 'end',
            'content': '<job yaml>',
            'parameters': {
                'assessment_types': 'SAST,SCA',
                'language': 'Java',
                'build_command': 'mvn clean install'
            }
        }
    }
    """
```

### Step 3: Assessment Type Intelligence

```python
def determine_assessment_types(language, has_package_manager, workflow_context):
    """
    Smart selection of Polaris assessment types
    
    Rules:
    - Java/Python/Node.js WITHOUT package manager file → SAST only
    - Java with pom.xml/build.gradle → SAST,SCA
    - Python with requirements.txt/Pipfile → SAST,SCA
    - JavaScript with package.json → SAST,SCA
    - C/C++ → SAST only (use Coverity instead)
    
    Returns: 'SAST' | 'SAST,SCA' | 'SCA'
    """
    
    assessment_map = {
        'Java': {
            'has_maven': 'SAST,SCA',      # pom.xml detected
            'has_gradle': 'SAST,SCA',     # build.gradle detected
            'default': 'SAST'
        },
        'Python': {
            'has_requirements': 'SAST,SCA',   # requirements.txt
            'has_pipfile': 'SAST,SCA',        # Pipfile
            'has_poetry': 'SAST,SCA',         # pyproject.toml
            'default': 'SAST'
        },
        'JavaScript': {
            'has_package_json': 'SAST,SCA',   # Always SCA for Node
            'default': 'SAST,SCA'
        },
        'TypeScript': {
            'has_package_json': 'SAST,SCA',
            'default': 'SAST,SCA'
        }
    }
    
    return assessment_map.get(language, {}).get(
        f'has_{package_manager}', 
        assessment_map.get(language, {}).get('default', 'SAST')
    )
```

### Step 4: PR Event Optimization

```python
def should_use_rapid_scan(workflow_context):
    """
    Determine if SAST_RAPID should be used based on GitHub event
    
    Rules:
    - Pull request events (opened, synchronize, reopened) → Use SAST_RAPID
    - Push to main/master/develop branches → Use full SAST
    - Scheduled/manual runs → Use full SAST
    
    Benefits:
    - SAST_RAPID is faster for PR feedback
    - Full SAST provides comprehensive analysis for main branch
    - Optimizes CI/CD pipeline performance
    
    Returns: bool (True = use SAST_RAPID for PRs)
    """
    return True  # Always recommend this optimization


def generate_polaris_config_with_event_optimization(assessment_types, language):
    """
    Generate Polaris configuration with PR event optimization
    
    Example output for PR events:
    ```yaml
    polaris_assessment_types: 'SAST,SCA'
    polaris_test_sast_type: ${{ github.event_name == 'pull_request' && 'SAST_RAPID' || '' }}
    ```
    
    How it works:
    - On pull_request events → Sets polaris_test_sast_type: 'SAST_RAPID'
    - On push/workflow_dispatch → polaris_test_sast_type is empty (full SAST)
    - SCA always runs at full depth regardless of event type
    """
    config = {
        'polaris_assessment_types': assessment_types,
        'include_rapid_scan': True,  # Always include for better PR experience
        'rapid_scan_expression': "${{ github.event_name == 'pull_request' && 'SAST_RAPID' || '' }}"
    }
    return config
```

---

## 🎨 UI/UX Enhancements

### Recommendation Card Types

#### Type 1: Add Job to Existing Workflow
```
┌─────────────────────────────────────────────────────┐
│ 🔧 Enhance Existing Workflow                       │
├─────────────────────────────────────────────────────┤
│ File: `.github/workflows/maven-ci.yml`             │
│                                                     │
│ 📊 Recommended Addition:                           │
│ Add "Polaris Security Scan" job                    │
│                                                     │
│ ✓ SAST + SCA analysis (pom.xml detected)          │
│ ✓ Runs after build job completes                  │
│ ✓ PR comments enabled                             │
│                                                     │
│ [View Diff] [View Full YAML] [Apply Changes]      │
└─────────────────────────────────────────────────────┘
```

#### Type 2: Add Step to Existing Job
```
┌─────────────────────────────────────────────────────┐
│ 🔍 Add Security Step to Build Job                  │
├─────────────────────────────────────────────────────┤
│ File: `.github/workflows/python-test.yml`          │
│ Job: `test`                                         │
│                                                     │
│ 📊 Recommended Addition:                           │
│ Add Polaris scan step after tests                  │
│                                                     │
│ ✓ SAST + SCA analysis (requirements.txt detected) │
│ ✓ Position: After "Run tests" step                │
│                                                     │
│ [View Changes] [Apply to Branch] [Create PR]      │
└─────────────────────────────────────────────────────┘
```

### Diff Preview Modal

When user clicks "View Diff":
```yaml
# .github/workflows/maven-ci.yml

  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Build with Maven
        run: mvn clean install
        
+ polaris-security-scan:              # NEW JOB
+   runs-on: ubuntu-latest
+   needs: build                       # Runs after build
+   name: Polaris Security Analysis
+   steps:
+     - uses: actions/checkout@v4
+     - name: Setup Java
+       uses: actions/setup-java@v4
+       with:
+         java-version: '17'
+         distribution: 'temurin'
+     - name: Polaris SAST+SCA Scan
+       uses: blackduck-inc/black-duck-security-scan@v2
+       with:
+         polaris_server_url: ${{ vars.POLARIS_SERVER_URL }}
+         polaris_access_token: ${{ secrets.POLARIS_ACCESS_TOKEN }}
+         polaris_assessment_types: 'SAST,SCA'  # SCA enabled (pom.xml detected)
+         polaris_test_sast_type: ${{ github.event_name == 'pull_request' && 'SAST_RAPID' || '' }}  # Fast scans for PRs
+         polaris_prComment_enabled: true
+         github_token: ${{ secrets.GITHUB_TOKEN }}
```

---

## 🔧 Implementation Steps

### Phase 1: Template Refactoring (Week 1)
1. Create `steps/` and `jobs/` directories
2. Extract reusable fragments from full workflow templates
3. Create parameter substitution system (use Jinja2 or similar)
4. Add metadata to fragments (compatible_languages, required_params)

### Phase 2: Workflow Parser (Week 1-2)
1. Implement YAML workflow parser
2. Extract job names, step names, triggers
3. Detect build tools, languages from workflow content
4. Identify insertion points (after build, before deploy, etc.)

### Phase 3: Smart Recommendation Engine (Week 2-3)
1. Implement `analyze_existing_workflows()`
2. Implement `determine_assessment_types()`
3. Implement `generate_workflow_recommendations()`
4. Add logic for job vs step recommendations

### Phase 4: Diff Generation (Week 3)
1. YAML manipulation library integration (ruamel.yaml or PyYAML)
2. Generate "before" and "after" YAML
3. Create unified diff output
4. Syntax highlighting for diff view

### Phase 5: Application Logic (Week 3-4)
1. Modify existing workflow files (not create new)
2. Update `/api/templates/apply` endpoint for workflow modifications
3. Add YAML validation before committing
4. Handle edge cases (duplicate jobs, conflicting names)

### Phase 6: Frontend UI (Week 4)
1. New recommendation card type for "enhance workflow"
2. Diff viewer modal component
3. Position selector (add to job X, add after job Y)
4. Preview changes before applying

---

## 📊 Data Structures

### Enhanced Analysis Response
```json
{
  "repository": "owner/repo",
  "total_workflows": 3,
  "detected_languages": ["Java", "JavaScript"],
  "detected_package_managers": ["maven", "npm"],
  "blackduck_analysis": {
    "has_blackduck_tools": false,
    "existing_workflows": [
      {
        "file_name": "maven-ci.yml",
        "file_path": ".github/workflows/maven-ci.yml",
        "jobs": ["build", "test"],
        "detected_tools": ["maven", "junit"],
        "has_security_scans": false,
        "insertion_opportunities": [
          {
            "type": "job",
            "position": "after",
            "anchor": "test",
            "reason": "Security scan after tests"
          }
        ]
      }
    ],
    "recommendations": [
      {
        "type": "enhance_workflow",
        "target_workflow": "maven-ci.yml",
        "recommendation": {
          "action": "add_job",
          "tool": "Polaris",
          "assessment_types": "SAST,SCA",
          "reason": "Java project with pom.xml - enable SAST+SCA",
          "template_source": "jobs/polaris-job.yml",
          "parameters": {
            "language": "Java",
            "build_command": "mvn clean install",
            "java_version": "17"
          },
          "insertion_point": {
            "type": "job",
            "position": "end",
            "after_job": "test"
          }
        },
        "preview_available": true,
        "diff_url": "/api/workflows/diff/preview/..."
      }
    ]
  }
}
```

---

## 🧪 Example Scenarios

### Scenario 1: Java with Maven
```
Repository: spring-boot-app
Files: pom.xml, src/main/java/**
Workflows: .github/workflows/maven-build.yml

Recommendation:
→ Add Polaris job to maven-build.yml
→ Assessment types: SAST,SCA (pom.xml detected)
→ PR Optimization: SAST_RAPID for pull requests
→ Position: After 'build' job
→ Setup: Java 17 (detected from pom.xml)

Generated Code:
  polaris_assessment_types: 'SAST,SCA'
  polaris_test_sast_type: ${{ github.event_name == 'pull_request' && 'SAST_RAPID' || '' }}
```

### Scenario 2: Python with requirements.txt
```
Repository: flask-api
Files: requirements.txt, app.py
Workflows: .github/workflows/python-test.yml

Recommendation:
→ Add Polaris step to 'test' job
→ Assessment types: SAST,SCA (requirements.txt detected)
→ PR Optimization: SAST_RAPID for pull requests
→ Position: After 'Run tests' step
→ Setup: Python 3.11 (detected from workflow)

Generated Code:
  polaris_assessment_types: 'SAST,SCA'
  polaris_test_sast_type: ${{ github.event_name == 'pull_request' && 'SAST_RAPID' || '' }}
```

### Scenario 3: Node.js with package.json
```
Repository: react-dashboard
Files: package.json, src/**
Workflows: .github/workflows/node-ci.yml

Recommendation:
→ Add Polaris job to node-ci.yml
→ Assessment types: SAST,SCA (package.json always has deps)
→ PR Optimization: SAST_RAPID for pull requests
→ Position: Parallel with 'test' job
→ Setup: Node 18 (detected from workflow)

Generated Code:
  polaris_assessment_types: 'SAST,SCA'
  polaris_test_sast_type: ${{ github.event_name == 'pull_request' && 'SAST_RAPID' || '' }}
```

### Scenario 4: No Existing Workflows
```
Repository: new-python-project
Files: app.py, requirements.txt
Workflows: (none)

Recommendation:
→ Create new workflow: polaris-sast.yml (current behavior)
→ Assessment types: SAST,SCA
→ PR Optimization: SAST_RAPID for pull requests
→ Full template with all required steps

Generated Code:
  polaris_assessment_types: 'SAST,SCA'
  polaris_test_sast_type: ${{ github.event_name == 'pull_request' && 'SAST_RAPID' || '' }}
```

---

## ⚡ PR Event Optimization Feature

### Overview
Automatically optimize scan performance by using **SAST_RAPID** for pull request events while maintaining full SAST depth for main branch commits.

### How It Works

**GitHub Event Detection**:
```yaml
polaris_test_sast_type: ${{ github.event_name == 'pull_request' && 'SAST_RAPID' || '' }}
```

This expression evaluates to:
- `'SAST_RAPID'` when triggered by pull request events (opened, synchronize, reopened)
- `''` (empty/unset) when triggered by push, workflow_dispatch, or schedule events

### Benefits

| Event Type | SAST Mode | Speed | Use Case |
|------------|-----------|-------|----------|
| Pull Request | SAST_RAPID | ⚡ Fast | Quick feedback for developers |
| Push to main | Full SAST | 🔍 Thorough | Comprehensive analysis |
| Scheduled scan | Full SAST | 🔍 Thorough | Deep security audit |
| Manual trigger | Full SAST | 🔍 Thorough | On-demand analysis |

### Performance Impact

**SAST_RAPID Benefits**:
- ✅ 30-70% faster scan times for PRs
- ✅ Faster developer feedback loop
- ✅ Reduced CI/CD queue times
- ✅ Lower compute resource usage

**Full SAST Benefits**:
- ✅ Comprehensive vulnerability detection
- ✅ Deep dataflow analysis
- ✅ Complete code coverage
- ✅ Regulatory compliance reporting

### When It's Applied

The AI-Analysis will **always recommend** this optimization when:
1. Repository has or will have pull request triggers in workflow
2. Polaris SAST is being configured
3. Assessment types include 'SAST' or 'SAST,SCA'

### Example Generated YAML

**Full configuration with PR optimization**:
```yaml
- name: Polaris Security Scan
  uses: blackduck-inc/black-duck-security-scan@v2
  with:
    polaris_server_url: ${{ vars.POLARIS_SERVER_URL }}
    polaris_access_token: ${{ secrets.POLARIS_ACCESS_TOKEN }}
    polaris_application_name: ${{ github.event.repository.name }}
    polaris_project_name: ${{ github.event.repository.name }}
    polaris_assessment_types: 'SAST,SCA'
    
    # PR Optimization: Use rapid scans for faster PR feedback
    polaris_test_sast_type: ${{ github.event_name == 'pull_request' && 'SAST_RAPID' || '' }}
    
    polaris_prComment_enabled: true
    github_token: ${{ secrets.GITHUB_TOKEN }}
```

### User Communication

When showing recommendations, the UI will display:
```
✅ Optimized for PR performance
   - Pull requests: Fast SAST_RAPID scans
   - Main branch: Comprehensive full SAST
```

### Implementation in Recommendation Engine

```python
def generate_polaris_recommendation(language, has_package_manager, workflow_triggers):
    """
    Generate Polaris recommendation with automatic PR optimization
    """
    assessment_types = determine_assessment_types(language, has_package_manager)
    
    # Check if workflow has PR triggers
    has_pr_trigger = 'pull_request' in workflow_triggers
    
    config = {
        'assessment_types': assessment_types,
        'parameters': {
            'polaris_assessment_types': assessment_types,
        }
    }
    
    # Always add PR optimization if PR trigger exists or is recommended
    if has_pr_trigger or should_recommend_pr_trigger(workflow_triggers):
        config['parameters']['polaris_test_sast_type'] = (
            "${{ github.event_name == 'pull_request' && 'SAST_RAPID' || '' }}"
        )
        config['features'] = ['pr_optimization']
        config['description_suffix'] = ' with optimized PR scans'
    
    return config
```

### Edge Cases

**Case 1: Workflow with only push trigger**
- Still include the optimization (harmless, prepares for future PR trigger)
- Expression evaluates to empty string, no effect

**Case 2: SCA-only assessment**
- Do NOT include `polaris_test_sast_type` (only applies to SAST)
- Only add when assessment_types contains 'SAST'

**Case 3: Existing workflow already has optimization**
- Detect existing `polaris_test_sast_type` parameter
- Don't duplicate, preserve user's configuration

### Testing Strategy

Test cases to verify:
1. ✅ PR event → `polaris_test_sast_type: 'SAST_RAPID'`
2. ✅ Push event → `polaris_test_sast_type: ''` (empty)
3. ✅ workflow_dispatch → `polaris_test_sast_type: ''`
4. ✅ SCA-only → Parameter not included
5. ✅ SAST or SAST,SCA → Parameter included

---

## 🔐 Required Secrets/Variables

### Template Fragments Will Need
```yaml
# Required for all Polaris recommendations
secrets:
  - POLARIS_ACCESS_TOKEN
  
variables:
  - POLARIS_SERVER_URL

# Already available
secrets:
  - GITHUB_TOKEN (always available)
```

---

## 🎯 Success Metrics

1. **Adoption Rate**: % of users who apply "enhance workflow" vs "new workflow"
2. **Accuracy**: % of recommendations that apply successfully
3. **Relevance**: User feedback on assessment type selection
4. **Coverage**: % of workflows that get enhanced vs replaced

---

## 🚧 Challenges & Solutions

### Challenge 1: YAML Parsing Complexity
**Problem**: GitHub Actions YAML can be complex (anchors, templates, matrix)
**Solution**: Use `ruamel.yaml` library (preserves comments, formatting)

### Challenge 2: Insertion Point Detection
**Problem**: Where to add the job/step in existing workflow?
**Solution**: Heuristics-based algorithm:
- Security scans → After build/test jobs
- Check for `needs: [build]` dependencies
- Default: End of jobs section

### Challenge 3: Parameter Inference
**Problem**: How to determine build commands, Java version, etc.?
**Solution**: Parse existing workflow steps:
```yaml
# Existing step tells us Java version
- name: Setup Java
  uses: actions/setup-java@v4
  with:
    java-version: '17'  # ← Extract this
```

### Challenge 4: Name Conflicts
**Problem**: Job/step names might conflict
**Solution**: Auto-rename with suffix:
```yaml
polaris-security-scan  # Default
polaris-security-scan-2  # If conflict
```

### Challenge 5: Validation
**Problem**: Modified YAML might be invalid
**Solution**: 
- Pre-validate with YAML parser
- GitHub API dry-run validation
- Rollback mechanism if commit fails

---

## 🎨 Frontend Components Needed

### 1. Enhanced Recommendation Card
```jsx
<WorkflowEnhancementCard
  recommendation={rec}
  onViewDiff={() => showDiffModal(rec)}
  onApply={() => applyWorkflowChange(rec)}
  type="enhance_workflow"  // vs "new_workflow"
/>
```

### 2. Diff Viewer Modal
```jsx
<DiffViewerModal
  originalYaml={original}
  modifiedYaml={modified}
  fileName="maven-ci.yml"
  additions={additions}
  deletions={deletions}
  onApprove={() => applyChanges()}
  onCancel={() => closeModal()}
/>
```

### 3. Insertion Point Selector
```jsx
<InsertionPointSelector
  jobs={['build', 'test', 'deploy']}
  selectedPosition="after_test"
  onChange={(pos) => updateInsertionPoint(pos)}
/>
```

---

## 📝 API Endpoints Needed

### New Endpoints

```python
@app.post("/api/workflows/analyze")
async def analyze_workflow_structure(
    repository: str,
    workflow_file: str
):
    """
    Deep analysis of workflow file structure
    Returns jobs, steps, insertion opportunities
    """
    
@app.post("/api/workflows/preview-enhancement")
async def preview_workflow_enhancement(
    repository: str,
    workflow_file: str,
    enhancement: dict
):
    """
    Generate diff preview of proposed changes
    Returns: original, modified, diff
    """
    
@app.post("/api/workflows/apply-enhancement")
async def apply_workflow_enhancement(
    repository: str,
    workflow_file: str,
    enhancement: dict,
    method: str = "direct"  # or "pull_request"
):
    """
    Apply changes to existing workflow file
    Modifies file instead of creating new one
    """
```

### Modified Endpoints

```python
@app.get("/api/ai-analysis/{org}/{repo}")
async def ai_analyze_repository(org: str, repo: str):
    """
    Enhanced to return 'enhance_workflow' recommendations
    in addition to 'new_workflow' recommendations
    """
```

---

## 🗂️ Database Schema Changes

### New Table: `workflow_fragments`
```sql
CREATE TABLE workflow_fragments (
    id INTEGER PRIMARY KEY,
    name VARCHAR(255),
    type VARCHAR(50),  -- 'job', 'step', 'setup'
    tool VARCHAR(100),  -- 'polaris', 'coverity', 'blackduck_sca'
    category VARCHAR(100),
    content TEXT,  -- YAML content with placeholders
    parameters JSON,  -- Required/optional parameters
    compatible_languages JSON,  -- ['Java', 'Python', ...]
    metadata JSON,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

Example row:
```json
{
  "id": 1,
  "name": "Polaris Security Scan Job",
  "type": "job",
  "tool": "polaris",
  "content": "polaris-security-scan:\n  runs-on: ubuntu-latest\n  ...",
  "parameters": {
    "required": ["assessment_types", "language"],
    "optional": ["build_command", "java_version"]
  },
  "compatible_languages": ["Java", "Python", "JavaScript", "TypeScript"],
  "metadata": {
    "requires_build": false,
    "runs_after": ["build", "test"],
    "secrets": ["POLARIS_ACCESS_TOKEN"],
    "variables": ["POLARIS_SERVER_URL"]
  }
}
```

---

## 🔄 Migration Path

### Phase 1: Parallel Mode (Weeks 1-2)
- Keep existing "new workflow" recommendations
- Add new "enhance workflow" recommendations
- Let users choose approach

### Phase 2: Smart Default (Weeks 3-4)
- If workflows exist → Default to "enhance"
- If no workflows → Default to "new"
- Allow user override

### Phase 3: Full Integration (Week 5+)
- Unified recommendation engine
- Context-aware suggestions
- A/B testing for optimization

---

## 📚 Technical Dependencies

### Python Libraries
```txt
ruamel.yaml>=0.17.0  # YAML parsing with comment preservation
pyyaml>=6.0          # Fallback YAML parser
jinja2>=3.1.0        # Template rendering
difflib              # Built-in diff generation
```

### JavaScript Libraries (Frontend)
```json
{
  "react-diff-viewer": "^3.1.1",
  "js-yaml": "^4.1.0",
  "prismjs": "^1.29.0"
}
```

---

## 🎓 Learning from User Behavior

### Analytics to Track
1. Which recommendation type users prefer (enhance vs new)
2. Success rate of automatic assessment type selection
3. Manual overrides of suggested insertion points
4. Most common workflow patterns in user repositories

### Feedback Loop
```python
@app.post("/api/recommendations/feedback")
async def record_recommendation_feedback(
    recommendation_id: str,
    action: str,  # 'applied', 'rejected', 'modified'
    feedback: dict
):
    """
    Track which recommendations work well
    Use ML to improve future suggestions
    """
```

---

## ✅ Testing Strategy

### Unit Tests
- YAML parsing and manipulation
- Assessment type selection logic
- Template parameter substitution
- Diff generation accuracy

### Integration Tests
- End-to-end workflow enhancement
- GitHub API workflow file updates
- PR creation with modified workflows

### Real-World Test Cases
```
Test Case 1: Spring Boot app with existing Maven CI
Test Case 2: React app with existing Node CI  
Test Case 3: Django app with existing Python tests
Test Case 4: Multi-language monorepo
Test Case 5: Complex workflow with matrix builds
```

---

## 📅 Timeline Estimate

| Phase | Duration | Deliverable |
|-------|----------|------------|
| Phase 1: Template Refactoring | 1 week | Step/job fragments library |
| Phase 2: Workflow Parser | 1 week | YAML analysis engine |
| Phase 3: Recommendation Engine | 2 weeks | Smart suggestion logic |
| Phase 4: Diff Generation | 1 week | Preview system |
| Phase 5: Application Logic | 1 week | Modify workflow files |
| Phase 6: Frontend UI | 1 week | Enhanced UI components |
| Phase 7: Testing & Refinement | 2 weeks | Production-ready |
| **Total** | **9 weeks** | **Complete feature** |

---

## 🚀 Quick Win (MVP)

For faster delivery, start with:

1. **Polaris job addition only** (most requested)
2. **PR optimization included** (SAST_RAPID for pull requests - high value, low effort)
3. **Simple insertion logic** (always append to end of jobs)
4. **Manual diff review** (no automatic application)
5. **Single language support** (Java or Python first)

This MVP can be delivered in **3-4 weeks** and provide immediate value.

**MVP Features**:
- ✅ Add Polaris job to existing workflows
- ✅ Smart SAST vs SAST,SCA selection
- ✅ Automatic PR event optimization
- ✅ Diff preview before applying
- ✅ Direct commit or PR application

---

## 🎯 Success Criteria

1. ✅ 80%+ of "enhance workflow" recommendations apply successfully
2. ✅ 90%+ accuracy in assessment type selection (SAST vs SAST,SCA)
3. ✅ 100% of Polaris recommendations include PR optimization (SAST_RAPID)
4. ✅ Users can preview changes before applying
5. ✅ No breaking of existing workflows
6. ✅ Clear rollback mechanism if issues occur
7. ✅ PR scans complete 30-70% faster than full SAST

---

## 📞 Next Steps

1. **Approve plan** and prioritize features
2. **Choose MVP scope** (quick win vs full implementation)
3. **Assign development resources**
4. **Create detailed technical specs** for each phase
5. **Set up test repositories** for validation

