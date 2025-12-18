# SSO (Single Sign-On) Authentication for GitHub Organizations

## Overview

Some GitHub organizations require SAML SSO (Security Assertion Markup Language Single Sign-On) authentication. When an organization has SSO enabled, Personal Access Tokens (PATs) must be explicitly authorized for that organization, even if the token has the correct scopes.

## Why SSO Authorization is Required

Organizations use SAML SSO to:
- Enforce centralized authentication through identity providers (like Okta, Azure AD, etc.)
- Maintain security compliance
- Control access to organization resources
- Audit user access

## Identifying SSO Requirements

### Error Messages
If you see any of these errors, the organization requires SSO authorization:

```
❌ Resource protected by organization SAML enforcement
❌ Although you appear to have the correct authorization credentials, the organization has enabled SAML SSO
❌ This organization requires members to enable SAML SSO
```

### Organization Settings
1. Visit the organization's GitHub page: `https://github.com/YOUR_ORG`
2. Look for "SSO" badge or "SAML SSO" in settings
3. Check if you see "Configure SAML SSO" option in your profile

## How to Authorize Your Token for SSO

### Step 1: Access Token Settings
1. Go to [GitHub Settings → Personal Access Tokens](https://github.com/settings/tokens)
2. You'll see a list of all your tokens

### Step 2: Configure SSO
1. Find the token you're using in this application
2. Next to the token, click **"Configure SSO"** or **"Enable SSO"**
3. You'll see a list of organizations that require SSO

### Step 3: Authorize Organizations
1. Find your organization in the list
2. Click **"Authorize"** next to the organization name
3. You may be redirected to your organization's SSO provider (Okta, Azure AD, etc.)
4. Complete the authentication flow with your organization credentials
5. You'll be redirected back to GitHub

### Step 4: Verify Authorization
After authorization:
- The organization should show "Authorized" status
- The token will now work with that organization's resources
- No need to update the token in this application - authorization is per-token, not per-value

## Important Notes

### Token Authorization Status
- SSO authorization is tied to the **token itself**, not the token value
- If you regenerate or create a new token, you must authorize it again
- Authorization may expire based on your organization's policies (typically 1-365 days)

### Multiple Organizations
- If you work with multiple organizations, authorize your token for each one
- You can authorize a single token for multiple organizations
- Each organization's authorization is independent

### Re-authorization
You may need to re-authorize if:
- Your organization's SSO session expires
- Organization policies change
- You regenerate your token
- You see "Resource protected" errors again

## Troubleshooting

### "I authorized my token but still get errors"
1. **Wait a few minutes**: Authorization can take 1-2 minutes to propagate
2. **Clear cache**: Click "Clear Cache" in the application
3. **Verify token**: Ensure you authorized the correct token
4. **Check expiration**: Your SSO session may have expired
5. **Re-authorize**: Try the authorization process again

### "I don't see 'Configure SSO' option"
- **Token too old**: Older token formats may not support SSO - create a new token
- **Token type**: Ensure you're using a Personal Access Token (PAT), not an OAuth app token
- **Wrong token**: Make sure you're looking at the correct token

### "Organization not listed in SSO configuration"
- **Not a member**: You may need to be added to the organization first
- **No SSO required**: That organization may not have SSO enabled
- **Pending invitation**: Accept organization invitation before configuring SSO

### "SSO session expired"
- Organizations can set SSO session durations (1 day to 1 year)
- When expired, you'll need to re-authorize
- Contact your organization admin about session duration policies

## Application Features for SSO

### Automatic Detection
This application automatically detects SSO-related errors and provides helpful messages:

```
🔒 This organization requires SAML SSO authorization.
Organization: your-org-name

To authorize your token:
1. Go to https://github.com/settings/tokens
2. Find your token and click 'Configure SSO'
3. Click 'Authorize' for the organization
4. Complete the SSO authentication flow
```

### Configuration Guidance
The **Secrets Management** tab includes:
- Step-by-step SSO authorization instructions
- Links to GitHub token settings
- Common troubleshooting tips
- Visual guides for the authorization process

## Best Practices

### For Users
1. ✅ **Authorize immediately**: Configure SSO right after creating a token
2. ✅ **Document expiration**: Note when your organization's SSO sessions expire
3. ✅ **Use descriptive names**: Name tokens clearly (e.g., "Work Token - Expires June 2026")
4. ✅ **Monitor access**: Regularly check if re-authorization is needed
5. ✅ **Keep tokens secure**: Never share tokens, even if SSO-protected

### For Organizations
1. ✅ **Document SSO requirements**: Provide clear instructions to members
2. ✅ **Set reasonable expiration**: Balance security with usability (30-90 days typical)
3. ✅ **Provide support**: Help members troubleshoot SSO issues
4. ✅ **Audit regularly**: Review who has authorized tokens
5. ✅ **Communicate changes**: Notify members of SSO policy updates

## GitHub Enterprise Server SSO

For GitHub Enterprise Server (GHES) with SSO:

1. **URL Configuration**: Ensure `GITHUB_API_URL` points to your GHES instance
   ```
   https://github.your-company.com/api/v3
   ```

2. **SSO Provider**: May use different IdP than GitHub.com organizations
3. **Authorization**: Same process but through your enterprise's SSO portal
4. **Policies**: May differ from GitHub.com (shorter/longer sessions, different requirements)

## Security Considerations

### Why This is Secure
- SSO adds an extra layer of authentication
- Organization admins can revoke access instantly
- Audit trails track token usage
- Prevents unauthorized access even with valid tokens

### What SSO Doesn't Protect
- **Token storage**: You still must protect your token value
- **Token scopes**: SSO doesn't change what the token can do
- **Other organizations**: Authorization is per-organization
- **Token regeneration**: New tokens need new authorization

## Support and Resources

### GitHub Documentation
- [About SAML SSO authentication](https://docs.github.com/en/enterprise-cloud@latest/authentication/authenticating-with-saml-single-sign-on/about-authentication-with-saml-single-sign-on)
- [Authorizing a PAT for SSO](https://docs.github.com/en/enterprise-cloud@latest/authentication/authenticating-with-saml-single-sign-on/authorizing-a-personal-access-token-for-use-with-saml-single-sign-on)

### Application Support
- Check **Secrets Management** tab for configuration guidance
- Review error messages for specific SSO instructions
- Contact your organization admin for SSO-specific policies

### Common Questions

**Q: Do I need to update my token in the application after SSO authorization?**  
A: No! The token value doesn't change, only its authorization status.

**Q: Can I use the same token for both SSO and non-SSO organizations?**  
A: Yes! A token can be authorized for multiple SSO organizations while still working with non-SSO organizations.

**Q: How often do I need to re-authorize?**  
A: Depends on your organization's policy. Typically 30-90 days, but can range from 1 day to 1 year.

**Q: What happens if my SSO session expires while I'm using the application?**  
A: You'll start seeing "Resource protected" errors. Simply re-authorize your token.

**Q: Can organization admins see my token?**  
A: No, admins can only see that a token is authorized and when it was last used. They cannot see the token value.

---

**Last Updated**: December 2025  
**Application Version**: 1.0.0
