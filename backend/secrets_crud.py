from sqlalchemy.orm import Session
from database import Secret
from crypto import encrypt_secret, decrypt_secret
from datetime import datetime
from typing import List, Optional

class SecretCRUD:
    """CRUD operations for secrets"""
    
    @staticmethod
    def create_secret(db: Session, name: str, value: str, description: str = None) -> Secret:
        """Create a new secret"""
        # Check if secret with this name already exists
        existing = db.query(Secret).filter(Secret.name == name).first()
        if existing:
            raise ValueError(f"Secret with name '{name}' already exists")
        
        # Encrypt the secret value
        encrypted_value = encrypt_secret(value)
        
        # Create new secret
        secret = Secret(
            name=name,
            description=description,
            encrypted_value=encrypted_value
        )
        
        db.add(secret)
        db.commit()
        db.refresh(secret)
        return secret
    
    @staticmethod
    def get_secret(db: Session, secret_id: int) -> Optional[Secret]:
        """Get a secret by ID"""
        return db.query(Secret).filter(Secret.id == secret_id).first()
    
    @staticmethod
    def get_secret_by_name(db: Session, name: str) -> Optional[Secret]:
        """Get a secret by name"""
        return db.query(Secret).filter(Secret.name == name).first()
    
    @staticmethod
    def get_secrets(db: Session, skip: int = 0, limit: int = 100) -> List[Secret]:
        """Get all secrets (without decrypted values)"""
        return db.query(Secret).offset(skip).limit(limit).all()
    
    @staticmethod
    def update_secret(db: Session, secret_id: int, name: str = None, value: str = None, description: str = None) -> Optional[Secret]:
        """Update a secret"""
        secret = db.query(Secret).filter(Secret.id == secret_id).first()
        if not secret:
            return None
        
        # Update fields if provided
        if name is not None:
            # Check if new name already exists (and it's not the same secret)
            existing = db.query(Secret).filter(Secret.name == name, Secret.id != secret_id).first()
            if existing:
                raise ValueError(f"Secret with name '{name}' already exists")
            secret.name = name
        
        if value is not None:
            secret.encrypted_value = encrypt_secret(value)
        
        if description is not None:
            secret.description = description
        
        secret.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(secret)
        return secret
    
    @staticmethod
    def delete_secret(db: Session, secret_id: int) -> bool:
        """Delete a secret"""
        secret = db.query(Secret).filter(Secret.id == secret_id).first()
        if not secret:
            return False
        
        db.delete(secret)
        db.commit()
        return True
    
    @staticmethod
    def decrypt_secret_value(secret: Secret) -> str:
        """Decrypt the value of a secret"""
        return decrypt_secret(secret.encrypted_value)