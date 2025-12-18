import requests
import json

# Test the secrets API
base_url = "http://localhost:8000"

def test_secrets_api():
    print("Testing Secrets API...")
    
    # Test 1: Create a secret
    print("\n1. Creating a secret...")
    secret_data = {
        "name": "test-secret",
        "value": "my-secret-password",
        "description": "Test secret for demo"
    }
    
    response = requests.post(f"{base_url}/api/secrets", json=secret_data)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        created_secret = response.json()
        print(f"Created secret: {json.dumps(created_secret, indent=2)}")
        secret_id = created_secret["id"]
    else:
        print(f"Error: {response.text}")
        return
    
    # Test 2: Get all secrets
    print("\n2. Getting all secrets...")
    response = requests.get(f"{base_url}/api/secrets")
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        secrets = response.json()
        print(f"All secrets: {json.dumps(secrets, indent=2)}")
    else:
        print(f"Error: {response.text}")
    
    # Test 3: Get secret by ID (without decryption)
    print(f"\n3. Getting secret {secret_id}...")
    response = requests.get(f"{base_url}/api/secrets/{secret_id}")
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        secret = response.json()
        print(f"Secret: {json.dumps(secret, indent=2)}")
    else:
        print(f"Error: {response.text}")
    
    # Test 4: Get secret with decrypted value
    print(f"\n4. Getting decrypted secret {secret_id}...")
    response = requests.get(f"{base_url}/api/secrets/{secret_id}/decrypt")
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        secret = response.json()
        print(f"Decrypted secret: {json.dumps(secret, indent=2)}")
    else:
        print(f"Error: {response.text}")
    
    # Test 5: Update secret
    print(f"\n5. Updating secret {secret_id}...")
    update_data = {
        "description": "Updated test secret"
    }
    response = requests.put(f"{base_url}/api/secrets/{secret_id}", json=update_data)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        updated_secret = response.json()
        print(f"Updated secret: {json.dumps(updated_secret, indent=2)}")
    else:
        print(f"Error: {response.text}")
    
    # Test 6: Get secret by name
    print(f"\n6. Getting secret by name 'test-secret'...")
    response = requests.get(f"{base_url}/api/secrets/name/test-secret")
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        secret = response.json()
        print(f"Secret by name: {json.dumps(secret, indent=2)}")
    else:
        print(f"Error: {response.text}")
    
    # Test 7: Delete secret
    print(f"\n7. Deleting secret {secret_id}...")
    response = requests.delete(f"{base_url}/api/secrets/{secret_id}")
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"Delete result: {json.dumps(result, indent=2)}")
    else:
        print(f"Error: {response.text}")
    
    print("\nAPI testing completed!")

if __name__ == "__main__":
    test_secrets_api()