# Secrets Management API

## Overview

The backend now includes a comprehensive secrets management system with the following features:

- ✅ **Encrypted Storage**: All secret values are encrypted using Fernet (symmetric encryption)
- ✅ **SQLite Database**: Local database storage for secrets metadata and encrypted values
- ✅ **Full CRUD Operations**: Create, read, update, and delete secrets
- ✅ **Name-based Lookup**: Find secrets by unique name
- ✅ **Secure Decryption**: Separate endpoint for retrieving decrypted values
- ✅ **Automatic Key Management**: Encryption key is generated and stored securely

## Database Schema

### Secrets Table
```sql
CREATE TABLE secrets (
    id INTEGER PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,
    encrypted_value TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

## API Endpoints

### Base URL: `http://localhost:8000/api/secrets`

### 1. Create Secret
- **POST** `/api/secrets`
- **Body**: 
```json
{
    "name": "my-secret",
    "value": "secret-password",
    "description": "Optional description"
}
```
- **Response**: Secret metadata (without value)

### 2. List All Secrets
- **GET** `/api/secrets?skip=0&limit=100`
- **Response**: Array of secrets (without decrypted values)

### 3. Get Secret by ID
- **GET** `/api/secrets/{id}`
- **Response**: Secret metadata (without value)

### 4. Get Decrypted Secret
- **GET** `/api/secrets/{id}/decrypt`
- **Response**: Secret with decrypted value
- ⚠️ **Security**: Use carefully, returns plaintext

### 5. Get Secret by Name
- **GET** `/api/secrets/name/{name}`
- **Response**: Secret metadata (without value)

### 6. Update Secret
- **PUT** `/api/secrets/{id}`
- **Body**: 
```json
{
    "name": "new-name",
    "value": "new-value",
    "description": "new-description"
}
```
- **Note**: All fields are optional

### 7. Delete Secret
- **DELETE** `/api/secrets/{id}`
- **Response**: Confirmation message

## Security Features

### Encryption
- **Algorithm**: Fernet (AES 128 in CBC mode)
- **Key Storage**: `data/secret.key` (auto-generated)
- **Key Rotation**: Manual (regenerate key file)

### Access Control
- No authentication required (add JWT for production)
- CORS enabled for localhost:3000
- Input validation with Pydantic models

## File Structure

```
backend/
├── main.py              # Updated with secrets endpoints
├── database.py          # SQLAlchemy models and connection
├── crypto.py            # Encryption/decryption utilities
├── secrets_crud.py      # CRUD operations
├── secrets_models.py    # Pydantic models
├── test_secrets_api.py  # API testing script
└── data/                # Created automatically
    ├── secrets.db       # SQLite database
    └── secret.key       # Encryption key
```

## Usage Examples

### Python Client
```python
import requests

# Create a secret
response = requests.post('http://localhost:8000/api/secrets', json={
    'name': 'db-password',
    'value': 'super-secret-password',
    'description': 'Database connection password'
})

secret_id = response.json()['id']

# Get decrypted value
response = requests.get(f'http://localhost:8000/api/secrets/{secret_id}/decrypt')
secret_value = response.json()['value']
```

### JavaScript/Frontend
```javascript
// Create a secret
const response = await fetch('http://localhost:8000/api/secrets', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        name: 'api-key',
        value: 'sk-1234567890',
        description: 'External API key'
    })
});

const secret = await response.json();

// Get all secrets (without values)
const secretsList = await fetch('http://localhost:8000/api/secrets')
    .then(r => r.json());
```

## Production Considerations

### Security Enhancements Needed
1. **Authentication**: Add JWT or API key authentication
2. **Authorization**: Role-based access control
3. **Audit Logging**: Track secret access and modifications
4. **Key Rotation**: Implement automatic key rotation
5. **HTTPS**: Use TLS for all communications
6. **Rate Limiting**: Prevent brute force attacks

### Database Scaling
1. **PostgreSQL**: Migrate from SQLite for production
2. **Connection Pooling**: Use connection pools
3. **Backups**: Implement encrypted database backups
4. **High Availability**: Database clustering

### Monitoring
1. **Metrics**: Track secret access patterns
2. **Alerts**: Unusual access attempts
3. **Health Checks**: Database connectivity

## Testing

Run the test script:
```bash
cd backend
python test_secrets_api.py
```

Or test individual endpoints:
```bash
# Create secret
curl -X POST "http://localhost:8000/api/secrets" \
     -H "Content-Type: application/json" \
     -d '{"name":"test","value":"password","description":"Test secret"}'

# List secrets
curl "http://localhost:8000/api/secrets"

# Get decrypted secret (replace 1 with actual ID)
curl "http://localhost:8000/api/secrets/1/decrypt"
```

## Error Handling

The API returns appropriate HTTP status codes:
- **200**: Success
- **400**: Bad request (validation errors, duplicate names)
- **404**: Secret not found
- **500**: Server error (encryption/database issues)

All errors include descriptive messages in the response body.