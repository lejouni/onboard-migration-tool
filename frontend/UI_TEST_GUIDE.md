# Secrets Management UI Test Guide

## Testing the Secrets Management Interface

### Prerequisites
1. Backend server running on http://localhost:8000
2. Frontend server running on http://localhost:3001
3. Navigate to the frontend URL: http://localhost:3001

### Test Scenarios

#### 1. Navigation Test
- ✅ Verify you can see two tabs: "📋 Items Management" and "🔐 Secrets Management"
- ✅ Click on "🔐 Secrets Management" tab
- ✅ Verify the secrets management interface loads

#### 2. Create Secret Test
- ✅ Click the "+ Add New Secret" button
- ✅ Fill in the form:
  - Name: `test-password`
  - Value: `my-secret-value-123`
  - Description: `Test secret for demo`
- ✅ Click "Create Secret"
- ✅ Verify the secret appears in the list
- ✅ Verify the secret value shows as dots (••••••••••••)

#### 3. View Secret Test
- ✅ Click the eye icon (👁️) next to a secret
- ✅ Verify the secret value is revealed
- ✅ Click the eye icon again to hide the value
- ✅ Verify the value is hidden again

#### 4. Copy Secret Test
- ✅ Reveal a secret value
- ✅ Click the clipboard icon (📋)
- ✅ Paste somewhere to verify it copied correctly

#### 5. Edit Secret Test
- ✅ Click the "✏️ Edit" button on a secret
- ✅ Modify the name, value, or description
- ✅ Click "Save"
- ✅ Verify the changes are reflected

#### 6. Delete Secret Test
- ✅ Click the "🗑️ Delete" button on a secret
- ✅ Confirm the deletion in the popup
- ✅ Verify the secret is removed from the list

#### 7. Error Handling Test
- ✅ Try creating a secret with a duplicate name
- ✅ Verify you get an appropriate error message
- ✅ Try creating a secret with empty name or value
- ✅ Verify form validation works

### Expected UI Features

#### Visual Elements
- Header with gradient background and emoji
- Tab navigation between Items and Secrets
- Card-based layout for secrets
- Responsive grid layout
- Hover effects on cards and buttons

#### Security Features
- Secrets values are hidden by default
- Eye icon to toggle visibility
- Copy to clipboard functionality
- Confirmation for deletion

#### User Experience
- Loading states
- Error messages
- Form validation
- Responsive design
- Intuitive icons and colors

### API Endpoints Being Used
- `GET /api/secrets` - List all secrets
- `POST /api/secrets` - Create new secret
- `GET /api/secrets/{id}/decrypt` - Get decrypted value
- `PUT /api/secrets/{id}` - Update secret
- `DELETE /api/secrets/{id}` - Delete secret

### Troubleshooting

#### Common Issues
1. **CORS Error**: Make sure backend CORS includes port 3001
2. **Connection Refused**: Verify backend is running on port 8000
3. **Not Loading**: Check browser console for JavaScript errors
4. **API Errors**: Check backend logs for detailed error messages

#### Browser Console Commands
Test API directly from browser console:
```javascript
// Test creating a secret
fetch('http://localhost:8000/api/secrets', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    name: 'test-console',
    value: 'console-test-value',
    description: 'Created from console'
  })
}).then(r => r.json()).then(console.log);

// Test getting secrets
fetch('http://localhost:8000/api/secrets')
  .then(r => r.json())
  .then(console.log);
```

### Success Criteria
- ✅ All CRUD operations work correctly
- ✅ Encryption/decryption functions properly
- ✅ UI is responsive and user-friendly
- ✅ Error handling provides clear feedback
- ✅ Navigation between tabs works smoothly
- ✅ Security features (hiding values) work as expected