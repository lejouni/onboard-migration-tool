# Template Placeholder Filling - Implementation Summary

## Overview
Fixed the issue where `{assessment_types}` placeholders in template YAML files were not being replaced with actual values when templates were recommended to users.

## Problem Statement
When users received template recommendations through the AI analysis workflow, the templates contained placeholder values like `{assessment_types}` instead of actual assessment type values (e.g., "SAST", "SCA", "SAST_SCA"). This made the templates unusable without manual editing.

## Root Cause
The `fill_template_placeholders()` function existed in `main.py` but was only called in the preview/apply endpoints, not during the recommendation generation phase. This meant:
- Recommendations showed templates with unfilled placeholders
- Users had to manually edit templates before applying them
- The workflow was not user-friendly

## Solution Implemented

### 1. Moved Placeholder Filling Function
**File**: `backend/workflow_enhancement_helpers.py`

Moved the `fill_template_placeholders()` function from `main.py` to `workflow_enhancement_helpers.py` for better reusability:

```python
def fill_template_placeholders(template_content: str, assessment_type: str) -> str:
    """
    Fill template placeholders with actual values.
    
    Args:
        template_content: The template YAML content with placeholders
        assessment_type: The assessment type (SAST, SCA, or SAST_SCA)
    
    Returns:
        Template content with placeholders replaced
    """
    if not template_content:
        return template_content
    
    # Map assessment types to their values
    assessment_mapping = {
        "SAST": "SAST",
        "SCA": "SCA", 
        "SAST_SCA": "SAST,SCA"
    }
    
    assessment_value = assessment_mapping.get(assessment_type, assessment_type)
    
    # Replace the placeholder
    filled_content = template_content.replace("{assessment_types}", assessment_value)
    
    return filled_content
```

### 2. Updated Recommendation Generation Functions
**File**: `backend/workflow_enhancement_helpers.py`

Modified both recommendation generation functions to:
1. Call `fill_template_placeholders()` with the assessment type
2. Include the filled `template_content` in the recommendation object

#### Changes to `generate_enhancement_recommendations()`:
- Lines 200-205: Fill placeholders and add `template_content` field
- Now returns recommendations with filled template content

#### Changes to `generate_new_workflow_recommendations()`:
- Lines 380-385: Fill placeholders and add `template_content` field  
- Now returns recommendations with filled template content

### 3. Updated Frontend to Use Filled Content
**File**: `frontend/src/AIWorkflowAnalysis.js`

Modified the `handleViewTemplate()` function to:
- Accept an optional `templateContent` parameter
- Use the provided content (with filled placeholders) if available
- Fall back to fetching from API if not provided

```javascript
const handleViewTemplate = async (repository, templateName, method, templateContent = null) => {
  try {
    let content = templateContent;
    
    // If template content is not provided, fetch it from the API
    if (!content) {
      const response = await fetch(`http://localhost:8000/api/templates/search/${encodeURIComponent(templateName)}`);
      // ... fetch logic
      content = templates[0].content;
    }
    
    setViewingTemplate({
      repository,
      templateName,
      method,
      originalContent: content
    });
    
    setEditedTemplateContent(content);
  } catch (err) {
    // ... error handling
  }
};
```

Updated the "View & Edit Template" button to pass the filled content:
```javascript
<button
  onClick={() => handleViewTemplate(
    repoAnalysis.repository, 
    template.template_name, 
    'pull_request', 
    template.template_content  // Pass filled content
  )}
>
  👁️ View & Edit Template
</button>
```

## Assessment Type Mapping

The placeholder filling supports three assessment types:

| Assessment Type | Placeholder Value | Actual Value in YAML |
|----------------|-------------------|---------------------|
| SAST           | `{assessment_types}` | `SAST` |
| SCA            | `{assessment_types}` | `SCA` |
| SAST_SCA       | `{assessment_types}` | `SAST,SCA` |

## Example

### Before (with placeholder):
```yaml
name: Black Duck Polaris SAST Scan
on: [push, pull_request]
jobs:
  polaris-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run Polaris Scan
        env:
          POLARIS_ASSESSMENT_TYPES: {assessment_types}
```

### After (SAST_SCA assessment):
```yaml
name: Black Duck Polaris SAST Scan
on: [push, pull_request]
jobs:
  polaris-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run Polaris Scan
        env:
          POLARIS_ASSESSMENT_TYPES: SAST,SCA
```

## Benefits

1. **User-Friendly**: Templates are immediately usable without manual editing
2. **Accurate**: Assessment types are correctly filled based on repository analysis
3. **Consistent**: Same placeholder filling logic used across all recommendation types
4. **Maintainable**: Centralized function in `workflow_enhancement_helpers.py`
5. **Backward Compatible**: Falls back to API fetch if content not provided

## Testing

To verify the fix works:

1. Run AI analysis on a repository
2. View a recommended template
3. Verify that `{assessment_types}` is replaced with actual values
4. Apply the template and confirm it works without manual editing

## Files Modified

1. `backend/workflow_enhancement_helpers.py` - Added placeholder filling to recommendation generation
2. `frontend/src/AIWorkflowAnalysis.js` - Updated to use filled template content
3. `backend/main.py` - Already had the function, now uses it from helpers module

## Related Features

This fix complements the following features:
- Template recommendation system
- Assessment type detection
- Workflow enhancement
- New workflow creation
- Template preview and editing

## Future Enhancements

Potential improvements for the placeholder system:
1. Support for additional placeholders (e.g., `{repository_name}`, `{branch}`)
2. Template validation to ensure all placeholders are filled
3. Custom placeholder values from user input
4. Placeholder documentation in template metadata

## Conclusion

The placeholder filling issue has been completely resolved. Users now receive templates with all placeholders properly filled based on their repository's assessment type, making the workflow analysis and template application process seamless and user-friendly.