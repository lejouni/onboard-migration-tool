# GitHub Enterprise Support

This application now supports GitHub Enterprise Server in addition to GitHub.com.

## Configuration

To use GitHub Enterprise Server, you need to configure the GitHub API URL before starting the backend application.

### Setting up GitHub Enterprise URL

The application reads the GitHub API base URL from the `GITHUB_API_URL` environment variable. If not set, it defaults to `https://api.github.com` (GitHub.com).

#### Windows PowerShell

```powershell
$env:GITHUB_API_URL="https://github.enterprise.com/api/v3"
python backend/main.py
```

Or set it permanently:
```powershell
[System.Environment]::SetEnvironmentVariable('GITHUB_API_URL', 'https://github.enterprise.com/api/v3', 'User')
```

#### Linux/Mac

```bash
export GITHUB_API_URL="https://github.enterprise.com/api/v3"
python backend/main.py
```

Or add to your `.bashrc` or `.zshrc`:
```bash
echo 'export GITHUB_API_URL="https://github.enterprise.com/api/v3"' >> ~/.bashrc
```

#### Docker

If running in Docker, pass the environment variable:
```bash
docker run -e GITHUB_API_URL="https://github.enterprise.com/api/v3" your-image
```

Or in `docker-compose.yml`:
```yaml
services:
  backend:
    environment:
      - GITHUB_API_URL=https://github.enterprise.com/api/v3
```

## URL Format

The GitHub Enterprise Server API URL must follow this format:

```
https://<your-hostname>/api/v3
```

**Examples:**
- `https://github.enterprise.com/api/v3`
- `https://github.mycompany.com/api/v3`
- `https://git.internal.company.com/api/v3`

**Important:** 
- Always use `https://` (secure connection)
- Always end with `/api/v3` (GitHub Enterprise API version 3)
- Do NOT include a trailing slash after `/api/v3`

## Authentication

GitHub Enterprise Server uses the same token-based authentication as GitHub.com. You'll need to:

1. Generate a Personal Access Token (PAT) from your GitHub Enterprise Server instance
2. Store it in the application using the Secrets Manager
3. The token should have the same scopes as required for GitHub.com:
   - `repo` - Full control of private repositories
   - `read:org` - Read org and team membership
   - `admin:org` - Full control of orgs and teams (if managing organization secrets)

## Configuration Architecture

**Important:** The GitHub API URL is configured via **environment variable only**, not through Secrets Manager.

- **GITHUB_API_URL** - Environment variable (configuration, not a secret)
  - Set before starting the backend
  - Defaults to `https://api.github.com` if not set
  - Not stored in the database

- **GITHUB_TOKEN** - Stored in Secrets Manager (sensitive credential)
  - Encrypted in the database
  - Managed through the Secrets Manager UI
  - Can be updated at runtime

This separation follows best practices:
- **Configuration** (API URL) = Environment variable
- **Secrets** (tokens) = Encrypted database storage

## Verification

To verify your GitHub Enterprise connection is working:

1. Set the `GITHUB_API_URL` environment variable to your GitHub Enterprise Server URL
2. Start the backend - you should see: `✓ Using GitHub API URL: https://github.enterprise.com/api/v3`
3. Start the frontend and open the application
4. Navigate to the **Secrets Manager** tab
5. Create a secret named `GITHUB_TOKEN` with your GitHub Enterprise Personal Access Token
6. Go to the **GitHub Organizations** tab
7. You should see your Enterprise organizations listed

**Expected startup output:**
```
✓ Created GITHUB_TOKEN secret (empty - requires configuration)
✓ Using GitHub API URL: https://github.enterprise.com/api/v3
  (From GITHUB_API_URL environment variable)
```

## Troubleshooting

### Connection Errors

If you see connection errors:
- Verify your GitHub Enterprise Server hostname is correct
- Ensure the URL ends with `/api/v3`
- Check that your GitHub Enterprise Server is accessible from your network
- Verify SSL certificates are valid (the application currently disables SSL verification for development)

### Authentication Errors

If you see authentication errors:
- Verify your Personal Access Token is from your GitHub Enterprise Server (not GitHub.com)
- Check that the token has the required scopes
- Ensure the token hasn't expired

### API Version Compatibility

This application uses GitHub API v3, which is supported by:
- GitHub Enterprise Server 2.20 and later
- GitHub.com

If you're using an older version of GitHub Enterprise Server, you may need to upgrade.

## Default Behavior

If `GITHUB_API_URL` is not set, the application defaults to GitHub.com (`https://api.github.com`). This means:
- No configuration needed for GitHub.com users
- Existing installations continue to work without changes
- GitHub.com and GitHub Enterprise users can use the same codebase

## Multiple Environments

If you need to support both GitHub.com and GitHub Enterprise:

1. **Option 1:** Run separate instances with different environment variables
2. **Option 2:** Switch the environment variable and restart the backend when needed
3. **Option 3:** Use a configuration file or deployment-specific environment setup

## Security Considerations

- Always use HTTPS URLs for production
- Store tokens securely using the Secrets Manager
- Consider enabling SSL certificate verification in production (currently disabled for development)
- Follow your organization's security policies for token management
- Regularly rotate Personal Access Tokens
- Use the minimum required token scopes

## Support

For issues related to:
- **GitHub Enterprise Server setup:** Contact your GitHub Enterprise administrator
- **API connectivity:** Check your network configuration and firewall rules
- **Application bugs:** Report issues in the project repository
