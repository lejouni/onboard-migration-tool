import httpx
import asyncio
import os

async def test():
    token = os.getenv('GITHUB_TOKEN')
    headers = {
        'Authorization': f'Bearer {token}',
        'Accept': 'application/vnd.github+json',
        'X-GitHub-Api-Version': '2022-11-28'
    }
    
    async with httpx.AsyncClient(verify=False) as client:
        # Test 1: Can we GET the base tree?
        print("Test 1: Getting base tree...")
        r = await client.get(
            'https://api.github.com/repos/HippotechOrg/hippotech-front/git/trees/d3857ba61c0c984d759bb4ac92cd27d26c91c21e',
            headers=headers
        )
        print(f'GET Tree status: {r.status_code}')
        if r.status_code == 200:
            print("✓ Base tree is accessible")
        else:
            print(f"✗ Base tree access failed: {r.text}")
        
        # Test 2: Check repository permissions
        print("\nTest 2: Checking repository permissions...")
        r = await client.get(
            'https://api.github.com/repos/HippotechOrg/hippotech-front',
            headers=headers
        )
        print(f'Repo GET status: {r.status_code}')
        if r.status_code == 200:
            repo_data = r.json()
            print(f"Permissions: {repo_data.get('permissions', {})}")
        
        # Test 3: Check if token has workflow scope
        print("\nTest 3: Checking token scopes...")
        r = await client.get('https://api.github.com/user', headers=headers)
        scopes = r.headers.get('x-oauth-scopes', '')
        print(f'Token scopes: {scopes}')
        if 'workflow' in scopes:
            print("✓ Token has workflow scope")
        else:
            print("✗ Token missing workflow scope - required for .github/workflows/* files")
        
        # Test 4: Try creating a tree without base_tree
        print("\nTest 4: Creating tree WITHOUT base_tree...")
        payload = {
            "tree": [{
                "path": ".github/workflows/maven.yml",
                "mode": "100644",
                "type": "blob",
                "sha": "e638595b39558b8048896f063c0ba33c84727bae"
            }]
        }
        r = await client.post(
            'https://api.github.com/repos/HippotechOrg/hippotech-front/git/trees',
            headers=headers,
            json=payload
        )
        print(f'POST Tree (no base) status: {r.status_code}')
        print(f'Response: {r.text}')

asyncio.run(test())
