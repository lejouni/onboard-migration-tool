from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class SecretBase(BaseModel):
    """Base secret model"""
    name: str = Field(..., min_length=1, max_length=255, description="Unique name for the secret")
    description: Optional[str] = Field(None, description="Optional description of the secret")

class SecretCreate(SecretBase):
    """Model for creating a new secret"""
    value: str = Field(..., min_length=1, description="The secret value to encrypt and store")

class SecretUpdate(BaseModel):
    """Model for updating a secret"""
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="New name for the secret")
    value: Optional[str] = Field(None, min_length=1, description="New secret value")
    description: Optional[str] = Field(None, description="New description")

class SecretResponse(SecretBase):
    """Model for secret response (without the actual secret value)"""
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class SecretWithValue(SecretResponse):
    """Model for secret response with decrypted value"""
    value: str = Field(..., description="The decrypted secret value")

class SecretsList(BaseModel):
    """Model for paginated secrets list"""
    secrets: list[SecretResponse]
    total: int
    skip: int
    limit: int