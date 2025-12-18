# Template Editor Feature

## Overview
This feature allows users to view and edit GitHub workflow templates before applying them to repositories. Modifications are temporary and only affect the specific application - they are NOT saved to the template database.

## User Workflow

1. **Analyze Repository**
   - User runs AI-Powered Workflow Analysis on one or more repositories
   - System detects languages and recommends appropriate workflow templates

2. **View Template** (Optional)
   - User clicks "View & Edit Template" button on any recommendation card
   - Modal opens displaying the template content in an editable textarea
   - Template content is fetched from the database via GET `/api/templates/search/{templateName}`

3. **Edit Template** (Optional)
   - User can modify the YAML content in the textarea editor
   - Changes are stored in React state (`editedTemplateContent`)
   - Warning message reminds user that modifications are temporary

4. **Apply Template**
   - User can apply either:
     - From the modal: Click "Apply to Current Branch" or "Create Pull Request"
     - From the card: Click the standard apply buttons (uses original template)
   - Modified content (if any) is sent to backend via `template_content` parameter
   - Original template in database remains unchanged

## Technical Implementation

### Frontend Components

**State Management** (`AIWorkflowAnalysis.js`):
```javascript
const [viewingTemplate, setViewingTemplate] = useState(null);
// Structure: { repository, templateName, method, originalContent }

const [editedTemplateContent, setEditedTemplateContent] = useState('');
// Stores user's modifications to the template
```

**Key Functions**:
- `handleViewTemplate(repo, templateName, method)` - Fetches and displays template
- `handleCloseTemplateViewer()` - Closes modal and clears state
- `handleApplyFromViewer()` - Applies template with modifications
- `handleApplyTemplate()` - Modified to include `template_content` if edited

**UI Components**:
- **View & Edit Template Button**: Pink gradient button with eye icon (👁️)
- **Template Editor Modal**: Full-screen overlay with:
  - Gradient header showing template and repository names
  - Warning note about temporary modifications
  - Textarea with monospace font (Fira Code/Courier New)
  - Cancel and Apply buttons in footer

### Backend Changes

**Endpoint**: `POST /api/templates/apply`

**Modified Request Body**:
```json
{
  "template_name": "string (required)",
  "repository": "string (required, format: owner/repo)",
  "method": "direct | pull_request",
  "branch": "string (default: main)",
  "pr_title": "string (optional)",
  "pr_body": "string (optional)",
  "template_content": "string (optional, for custom content)"
}
```

**Logic** (`backend/main.py` lines 1088-1115):
```python
template_content = request.get("template_content")

if template_content:
    # Use custom content provided by user
    content_to_apply = template_content
else:
    # Fetch from database
    templates = TemplateCRUD.search_templates(db, template_name)
    template = templates[0]
    content_to_apply = template.content

# Use content_to_apply for GitHub commit/PR
```

## API Endpoints Used

### Fetch Template Content
```
GET /api/templates/search/{templateName}
Response: { templates: [{ name, content, category, description }] }
```

### Apply Template
```
POST /api/templates/apply
Body: {
  template_name, repository, method,
  [template_content]  // Optional: custom content
}
Response: {
  success, method, repository, branch/pr_url, message
}
```

## Design Decisions

### Why Not Save Modifications?
1. **Maintain Clean Templates**: Database templates remain pristine and reusable
2. **Repository-Specific Customizations**: Users often need one-off changes
3. **Avoid Template Pollution**: Prevents accumulation of specialized variants
4. **Clear Intent**: Feature name "View & Edit" implies temporary nature

### Why Modal Instead of Inline Edit?
1. **Focused Experience**: Full-screen editing without distractions
2. **Clear Context**: Shows exactly what will be applied
3. **Explicit Actions**: Cancel vs Apply buttons make intent clear
4. **Visual Separation**: Distinguishes viewing from applying

### Why Not Validate YAML?
- **Current Implementation**: No YAML validation
- **Future Enhancement**: Could add YAML linting before apply
- **Trade-off**: Simplicity vs safety (GitHub will validate on push)

## Styling Details

### View & Edit Template Button
```css
background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%)
width: 100% (flex: 1 1 100%)
padding: 12px 20px
border-radius: 8px
hover: translateY(-2px) + enhanced shadow
```

### Template Editor Modal
```css
Overlay:
  background: rgba(0, 0, 0, 0.7)
  backdrop-filter: blur(5px)
  z-index: 10000

Modal Container:
  width: 90%, max-width: 1000px
  max-height: 90vh
  background: white
  border-radius: 12px

Textarea:
  font-family: 'Fira Code', 'Courier New', monospace
  min-height: 400px
  resize: vertical
  background: #f8f9fa
```

## Integration with Existing Features

### Template Application Flow
1. Original flow (no modifications):
   - User clicks "Apply to Current Branch" or "Create Pull Request"
   - `handleApplyTemplate()` sends request without `template_content`
   - Backend fetches from database

2. New flow (with modifications):
   - User clicks "View & Edit Template"
   - User modifies content in modal
   - User clicks "Apply to Current Branch" or "Create Pull Request" in modal
   - `handleApplyFromViewer()` → `handleApplyTemplate()` with `template_content`
   - Backend uses provided content

### Loading States
- Same `applyingTemplate` state object used for all apply operations
- Button disabled during application
- Toast notifications show success/error

### Notification System
- Success: Green toast with commit URL or PR link
- Error: Red toast with error message
- Auto-dismiss after 10s (success) or 8s (error)

## Testing Checklist

- [ ] View template (fetch and display)
- [ ] Edit template (modify content)
- [ ] Apply without modifications (uses original from database)
- [ ] Apply with modifications (uses edited content)
- [ ] Apply via direct commit with edits
- [ ] Apply via pull request with edits
- [ ] Verify database template unchanged after apply
- [ ] Test modal close (Cancel button)
- [ ] Test modal close (X button or overlay click if implemented)
- [ ] Test with very large template files
- [ ] Test with invalid YAML (should fail at GitHub)
- [ ] Test concurrent edits (multiple templates viewed)

## Future Enhancements

1. **YAML Validation**: Lint YAML before sending to GitHub
2. **Syntax Highlighting**: Use CodeMirror or Monaco Editor
3. **Diff View**: Show changes from original template
4. **Reset Button**: Restore original content after edits
5. **Session Persistence**: Save drafts to localStorage
6. **Template Preview**: Render YAML structure in tree view
7. **Error Recovery**: Better handling of invalid YAML
8. **Keyboard Shortcuts**: Ctrl+S to apply, Esc to close

## Code Locations

**Frontend**:
- `frontend/src/AIWorkflowAnalysis.js`
  - Lines 10-18: State declarations
  - Lines 236-341: Handler functions
  - Lines 1477-1503: View & Edit button
  - Lines 1608-1755: Template editor modal

**Backend**:
- `backend/main.py`
  - Lines 1088-1115: Modified request handling with `template_content`
  - Lines 1153-1160: Direct commit using `content_to_apply`
  - Lines 1215-1222: Pull request using `content_to_apply`

**Styling**:
- `frontend/src/index.css` (if modal styles moved there)
- Inline styles in `AIWorkflowAnalysis.js`

## Backward Compatibility

The feature is fully backward compatible:
- `template_content` parameter is optional
- Existing API calls without `template_content` work unchanged
- Database operations remain the same
- No changes to template storage or retrieval
