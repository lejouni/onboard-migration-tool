from cryptography.fernet import Fernet
import base64
import os

# Generate or load encryption key
def get_encryption_key():
    """Get or generate encryption key"""
    key_file = "data/secret.key"
    
    if os.path.exists(key_file):
        with open(key_file, "rb") as f:
            key = f.read()
    else:
        # Generate new key
        key = Fernet.generate_key()
        os.makedirs("data", exist_ok=True)
        with open(key_file, "wb") as f:
            f.write(key)
    
    return key

# Initialize Fernet cipher
_cipher = None

def get_cipher():
    """Get initialized Fernet cipher"""
    global _cipher
    if _cipher is None:
        key = get_encryption_key()
        _cipher = Fernet(key)
    return _cipher

def encrypt_secret(value: str) -> str:
    """Encrypt a secret value"""
    cipher = get_cipher()
    encrypted_bytes = cipher.encrypt(value.encode())
    return base64.b64encode(encrypted_bytes).decode()

def decrypt_secret(encrypted_value: str) -> str:
    """Decrypt a secret value"""
    cipher = get_cipher()
    encrypted_bytes = base64.b64decode(encrypted_value.encode())
    decrypted_bytes = cipher.decrypt(encrypted_bytes)
    return decrypted_bytes.decode()