import httpx
import asyncio
import os
import sys

async def check_scopes():
    # Get token from secrets database
    sys.path.append('/app')
    from database import get_db
    from secrets_crud import SecretCRUD
    
    db = next(get_db())
    github_token_secret = SecretCRUD.get_secret_by_name(db, "GITHUB_TOKEN")
    
    if not github_token_secret:
        print("ERROR: GITHUB_TOKEN not found in database")
        return
    
    from crypto import decrypt_secret
    github_token = decrypt_secret(github_token_secret.encrypted_value)
    
    headers = {
        'Authorization': f'Bearer {github_token}',
        'Accept': 'application/vnd.github+json',
        'X-GitHub-Api-Version': '2022-11-28'
    }
    
    async with httpx.AsyncClient(verify=False) as client:
        print("Checking token scopes...")
        r = await client.get('https://api.github.com/user', headers=headers)
        scopes = r.headers.get('x-oauth-scopes', '')
        print(f'Status: {r.status_code}')
        print(f'Token scopes: {scopes}')
        print(f'Accepted OAuth scopes: {r.headers.get("x-accepted-oauth-scopes", "")}')
        
        if 'workflow' in scopes:
            print("✓ Token HAS workflow scope")
        else:
            print("✗ Token MISSING workflow scope")
            print("\nTO FIX:")
            print("1. Go to https://github.com/settings/tokens")
            print("2. Find your token and click 'Edit'")
            print("3. Check the 'workflow' scope checkbox")
            print("4. Click 'Update token'")
            print("5. Update the token in Secrets Manager")

asyncio.run(check_scopes())
