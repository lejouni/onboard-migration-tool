# Template Database - Clean & Optimized

## Current Templates (8 Total)

### ✅ Workflow Templates (4)
**Used when:** Repository has NO workflows, create new `.github/workflows/*.yml` file

1. **Polaris Security Scan Workflow**
   - Languages: JavaScript, TypeScript, Java, Python, C#, Go, C++, Ruby, PHP, Scala, Kotlin
   - Tools: Polaris
   - Features: SAST, SCA, PR comments, PR optimization
   - Secrets: POLARIS_ACCESS_TOKEN
   - Variables: POLARIS_SERVER_URL

2. **Black Duck Coverity Static Analysis Workflow**
   - Languages: C, C++
   - Tools: Coverity
   - Features: SAST, PR comments
   - Secrets: COVERITY_USER, COVERITY_PASSPHRASE
   - Variables: COVERITY_URL

3. **Black Duck SCA Scan Workflow**
   - Languages: All
   - Tools: Black Duck SCA
   - Features: SCA, dependencies, PR comments
   - Secrets: BLACKDUCK_API_TOKEN
   - Variables: BLACKDUCK_URL

4. **Black Duck SRM Workflow**
   - Languages: All
   - Tools: SRM
   - Features: Risk management, compliance
   - Secrets: SRM_API_KEY
   - Variables: SRM_URL, SRM_PROJECT_ID

### ✅ Job Fragments (2)
**Used when:** Repository HAS workflows but NO suitable build jobs, add complete new job

1. **Polaris Security Scan Job**
   - Complete job with checkout + Polaris scan
   - Includes SAST+SCA, PR optimization
   - Category: polaris

2. **Coverity Security Scan Job**
   - Complete job with checkout + Coverity scan
   - Category: coverity

### ✅ Step Fragments (2)
**Used when:** Repository HAS workflows WITH build jobs, insert step into existing job

1. **Polaris Security Scan Step**
   - Just the security scan action
   - Inserted after build steps in existing job
   - Category: polaris

2. **Black Duck SCA Scan Step**
   - Just the SCA scan action
   - Inserted after build/install steps
   - Category: blackduck_sca

---

## Recommendation Logic

```
Repository Analysis
    │
    ├─ Has workflows?
    │   │
    │   ├─ YES → Has build job?
    │   │          │
    │   │          ├─ YES → Use STEP FRAGMENTS
    │   │          │         Insert scan into existing build job
    │   │          │
    │   │          └─ NO  → Use JOB FRAGMENTS
    │   │                   Add new security scan job
    │   │
    │   └─ NO  → Use WORKFLOW TEMPLATES
    │             Create new .github/workflows/*.yml
    │             Filter: name.endswith('Workflow')
    │             Filter: compatible_languages
    │             Filter: assessment_type matching category
```

---

## Removed Templates (5)

The following old templates were removed as they don't fit the current logic:

- ❌ Run Polaris SAST for non-compiled languages (no metadata, wrong naming)
- ❌ Run Polaris SCA for non-compiled languages (no metadata, wrong naming)
- ❌ Run Polaris SAST and SCA for non-compiled languages (no metadata, wrong naming)
- ❌ Black Duck SCA Scan (duplicate, no "Workflow" suffix)
- ❌ Polaris steps (unclear purpose, no metadata)

---

## Benefits of Clean Database

✅ **Clear naming convention**
- All workflows end with "Workflow"
- Jobs end with "Job"
- Steps end with "Step"

✅ **Complete metadata**
- All templates have languages, tools, secrets, variables
- Enables smart filtering and recommendations

✅ **No duplicates**
- One comprehensive Polaris workflow instead of multiple variants
- Clear separation: workflow vs job vs step

✅ **Predictable behavior**
- Recommendation logic is straightforward
- Easy to understand and maintain

---

## Maintenance

To add new templates, use `populate_template_fragments.py`:
- Job/step fragments are defined directly in the script
- Workflow templates are loaded from YAML files in `templates/blackduck/`
- Metadata comes from `templates.json`
- Run `python populate_template_fragments.py` to update database
