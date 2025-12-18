# Template Usage in the System

## Template Types

The system uses three types of templates:

### 1. **Step Fragments** (`template_type='step'`)
- **What**: Individual security scanning steps (just the action, not a full job)
- **When Used**: Add a security scan to an **EXISTING JOB** that already has build steps
- **Examples**: 
  - `Polaris Security Scan Step` - Just the Polaris action step
  - `Black Duck SCA Scan Step` - Just the Black Duck SCA action step

### 2. **Job Fragments** (`template_type='job'`)
- **What**: Complete jobs with checkout, setup, and security scanning
- **When Used**: Add a new security scanning job to an **EXISTING WORKFLOW**
- **Examples**:
  - `Polaris Security Scan Job` - Complete job with checkout + Polaris scan
  - `Coverity Security Scan Job` - Complete job with checkout + Coverity scan
- **Used in**: `generate_enhancement_recommendations()` in `workflow_enhancement_helpers.py`

### 3. **Full Workflow Templates** (`template_type='workflow'`)
- **What**: Complete GitHub Actions workflow files
- **When Used**: Create a **NEW WORKFLOW** from scratch when repository has NO suitable workflows
- **Examples**:
  - `Polaris Security Scan Workflow` - Full .github/workflows/polaris.yml
  - `Black Duck SCA Scan Workflow` - Full .github/workflows/blackduck-sca.yml
  - `Black Duck Coverity Static Analysis Workflow` - Full .github/workflows/coverity.yml
  - `Black Duck SRM Workflow` - Full .github/workflows/srm.yml
- **Filter**: Only templates ending with "Workflow" suffix are recommended
- **Used in**: `generate_new_workflow_recommendations()` in `workflow_enhancement_helpers.py`

## Decision Flow

```
Repository Analysis
    |
    ├─ Has existing workflows?
    │   |
    │   ├─ YES → Enhance existing workflow
    │   │          └─ Use JOB FRAGMENTS (template_type='job')
    │   │             - Add complete security scanning job to workflow
    │   │             - Example: Add "polaris-security-scan" job to existing CI workflow
    │   │
    │   └─ NO → Create new workflow
    │              └─ Use WORKFLOW TEMPLATES (template_type='workflow')
    │                 - Create brand new .github/workflows/*.yml file
    │                 - Example: Create polaris-security-scan.yml
    │
    └─ Future: Add to existing job?
               └─ Use STEP FRAGMENTS (template_type='step')
                  - Insert security scan step into existing job
                  - Example: Add Polaris step after build step in "build" job
```

## Current Implementation Status

✅ **Job Fragments** - Fully implemented
- Used when enhancing existing workflows
- Added as new jobs to .github/workflows/*.yml

✅ **Workflow Templates** - Fully implemented
- Used when creating new workflows
- Filter by "Workflow" suffix in name
- Filter by compatible languages and assessment type

⚠️ **Step Fragments** - Partially implemented
- Templates exist in database
- NOT YET USED in recommendation logic
- Future enhancement: Insert steps into existing jobs instead of adding new jobs

## Template Metadata

All templates now include rich metadata:
- `compatible_languages`: ["Java", "Python", "JavaScript", etc.]
- `tool`: ["Polaris", "Coverity", "Black Duck SCA"]
- `features`: ["sast", "sca", "pr_comments", "pr_optimization"]
- `secrets`: ["POLARIS_ACCESS_TOKEN", etc.]
- `variables`: ["POLARIS_SERVER_URL", etc.]
- `use_cases`: ["SAST", "Code quality", etc.]

This metadata enables intelligent filtering and recommendations.
