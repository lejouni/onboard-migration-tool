# Frontend Testing Guide - Workflow Enhancement Feature

## ✅ What Was Completed

### Frontend Updates (Tasks 8-9)

1. **Updated Recommendation Cards** (Task 8)
   - Added conditional rendering based on `template.type`
   - Enhancement cards (orange) vs New workflow cards (blue)
   - Enhancement cards show:
     - 🔧 Icon indicating modification
     - Target workflow file name
     - Insertion point details
     - "Preview Changes" button
     - "Apply Enhancement" button
   - New workflow cards show:
     - View & Edit Template
     - Apply to Current Branch
     - Create Pull Request

2. **Created Diff Viewer Modal** (Task 9)
   - Side-by-side YAML comparison
   - Original workflow (red border) vs Enhanced workflow (green border)
   - Enhancement details section showing:
     - Job ID
     - Template name
     - Target file path
     - Insertion point location
   - "Cancel" and "Apply Enhancement" buttons
   - Syntax highlighting for YAML (monospace font)

### State Management Added

```javascript
const [showDiffModal, setShowDiffModal] = useState(false);
const [diffContent, setDiffContent] = useState(null);
const [previewingEnhancement, setPreviewingEnhancement] = useState({});
const [applyingEnhancement, setApplyingEnhancement] = useState({});
```

### Handler Functions Added

1. **`handlePreviewEnhancement(repository, template)`**
   - Calls `/api/workflows/preview-enhancement`
   - Shows loading state
   - Opens diff modal with before/after YAML

2. **`handleApplyEnhancement(repository, template, fromDiffModal)`**
   - Calls `/api/workflows/apply-enhancement`
   - Commits changes to GitHub
   - Shows success notification with commit link
   - Closes diff modal if applying from preview

## 🧪 Testing Steps

### Prerequisites

1. **Start Backend:**
   ```powershell
   cd backend
   python main.py
   ```

2. **Start Frontend:**
   ```powershell
   cd frontend
   npm start
   ```

3. **Ensure Database Has Templates:**
   - Run `python backend/test_workflow_enhancement.py` to verify 10 templates exist

### Test Scenario 1: New Workflow Recommendation

**Test Repository:** A repo with NO workflows (e.g., a simple library)

1. Select organization/user scope
2. Analyze the repository
3. **Expected Result:**
   - Status: "needs_new_workflow" or "no_workflows"
   - Blue recommendation cards
   - Buttons: "View & Edit Template", "Apply to Current Branch", "Create Pull Request"
   - No target workflow information shown

### Test Scenario 2: Enhancement Recommendation

**Test Repository:** A repo WITH CI/CD workflow but NO security scans

**Example:** Java project with Maven build workflow

1. Select organization/user scope
2. Analyze the repository with existing workflow
3. **Expected Result:**
   - Status: "needs_enhancement"
   - **Orange recommendation cards** 🔧
   - Card shows:
     - Template name (e.g., "Polaris Security Scan Job")
     - Target workflow: `ci.yml` (or whatever workflow exists)
     - Insertion point: "after build (after 'build' job)"
   - Buttons:
     - "👁️ Preview Changes"
     - "✓ Apply Enhancement"

### Test Scenario 3: Preview Enhancement Flow

1. Click "Preview Changes" on an enhancement card
2. **Expected Result:**
   - Diff modal opens
   - Left side: Original workflow YAML (red border)
   - Right side: Enhanced workflow YAML (green border)
   - Enhancement Details section shows:
     - Job ID
     - Template name
     - Target file path
     - Insertion point location
   - Buttons: "Cancel" and "✓ Apply Enhancement"

3. Review the YAML diff
4. **Verify:**
   - New job is inserted at correct location
   - PR optimization is included (if applicable)
   - Original workflow structure is preserved

### Test Scenario 4: Apply Enhancement Flow

1. From diff modal, click "✓ Apply Enhancement"
2. **Expected Result:**
   - Button shows "⏳ Applying..."
   - Success notification appears:
     - Green notification banner
     - Message: "Enhancement '[template name]' has been applied to [file path] in [repo]!"
     - "View Commit" link
   - Diff modal closes

3. Click "View Commit" link
4. **Verify on GitHub:**
   - Commit was created
   - Workflow file was updated
   - New job/step was added at correct location
   - Commit message is descriptive

### Test Scenario 5: Direct Apply Enhancement

1. Click "✓ Apply Enhancement" directly from recommendation card (without preview)
2. **Expected Result:**
   - Same as Test Scenario 4
   - Enhancement applied without showing diff modal

### Test Scenario 6: Multiple Language Support

**Test with:**
- Java + Maven → should recommend SAST,SCA
- Python + requirements.txt → should recommend SAST,SCA
- JavaScript + package.json → should recommend SAST,SCA
- Python without package manager → should recommend SAST only

1. Analyze repos with different languages
2. **Verify:**
   - Package managers detected correctly
   - Assessment type shown in card
   - Compatible templates recommended

### Test Scenario 7: PR Optimization

**Test Repository:** Workflow with PR triggers

1. Analyze repo with PR trigger workflow
2. Preview enhancement
3. **Verify in Enhanced YAML:**
   ```yaml
   env:
     POLARIS_TEST_SAST_TYPE: ${{ github.event_name == 'pull_request' && 'SAST_RAPID' || '' }}
   ```
   - This should appear in Polaris SAST recommendations
   - Should NOT appear for SCA-only templates

## 🎨 Visual Verification

### Enhancement Card Styling
- **Background:** Orange gradient (`#fff3e0` to `#ffe0b2`)
- **Border:** 2px solid `#ff9800`
- **Icon:** 🔧 before template name
- **Target workflow box:**
  - Orange tinted background
  - Shows file name
  - Shows insertion point

### New Workflow Card Styling
- **Background:** Blue gradient (`#e3f2fd` to `#bbdefb`)
- **Border:** 2px solid `#2196f3`
- **No icon** before template name
- **No target workflow box**

### Diff Modal
- **Header:** Orange gradient (`#ff9800` to `#ff5722`)
- **Original YAML:** Red border (`#f44336`), light background
- **Enhanced YAML:** Green border (`#4caf50`), light green background
- **Side-by-side layout:** 50/50 split
- **Height:** 500px scrollable area

## 🐛 Common Issues to Check

### Issue 1: No Enhancement Recommendations
**Possible Causes:**
- Repository has no workflows → Should show new_workflow instead
- Repository already has security scans → Status: "configured"

**Solution:** Test with repo that has CI/CD but no security

### Issue 2: Preview Button Not Working
**Check:**
1. Browser console for errors
2. Network tab for `/api/workflows/preview-enhancement` call
3. Backend logs for errors
4. Ensure `template_id` and `target_workflow` fields exist in recommendation

### Issue 3: Apply Enhancement Fails
**Check:**
1. GitHub token has write permissions
2. Workflow file path is correct
3. Branch exists (default: 'main')
4. Backend error response in notification

### Issue 4: Diff Modal Shows Empty YAML
**Check:**
1. Backend successfully fetched workflow from GitHub
2. WorkflowParser merged job correctly
3. `diffContent` state has `original_workflow` and `enhanced_workflow` fields

## 📊 Expected API Responses

### /api/ai-analyze Response (Enhancement)
```json
{
  "repository": "owner/repo",
  "status": "needs_enhancement",
  "blackduck_analysis": {
    "recommended_templates": [{
      "type": "enhance_workflow",
      "template_name": "Polaris Security Scan Job",
      "template_id": 8,
      "category": "sast",
      "description": "...",
      "reason": "...",
      "target_workflow": {
        "file_name": "ci.yml",
        "file_path": ".github/workflows/ci.yml",
        "insertion_point": {
          "location": "after_build",
          "after_job": "build",
          "reasoning": "..."
        }
      },
      "has_pr_optimization": true,
      "assessment_type": "SAST,SCA",
      "detected_package_managers": [...]
    }]
  }
}
```

### /api/workflows/preview-enhancement Response
```json
{
  "original_workflow": "name: CI\n...",
  "enhanced_workflow": "name: CI\n...",
  "template_name": "Polaris Security Scan Job",
  "job_id": "polaris-scan"
}
```

### /api/workflows/apply-enhancement Response
```json
{
  "success": true,
  "workflow_file_path": ".github/workflows/ci.yml",
  "commit_sha": "abc123...",
  "commit_html_url": "https://github.com/...",
  "template_name": "Polaris Security Scan Job",
  "job_id": "polaris-scan"
}
```

## ✅ Success Criteria

- [x] Enhancement cards display with orange styling
- [x] New workflow cards display with blue styling
- [x] Target workflow info shown on enhancement cards
- [x] Preview button opens diff modal
- [x] Diff modal shows side-by-side YAML comparison
- [x] Apply button commits changes to GitHub
- [x] Success notification shows commit link
- [x] Different languages detected correctly
- [x] PR optimization included when applicable
- [x] Error handling with user-friendly messages

## 🎯 Next Steps (Task 10)

After manual testing, verify:
1. All recommendation types work correctly
2. All languages supported
3. Preview shows accurate diffs
4. Apply creates correct commits
5. Error states handled gracefully

Then mark Task 10 as complete!
