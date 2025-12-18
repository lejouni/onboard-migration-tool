from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os

# Create database directory if it doesn't exist
os.makedirs("data", exist_ok=True)

# SQLite database URLs - separate databases for secrets and templates
SECRETS_DATABASE_URL = "sqlite:///./data/secrets.db"
TEMPLATES_DATABASE_URL = "sqlite:///./data/templates.db"

# Create SQLAlchemy engines
secrets_engine = create_engine(
    SECRETS_DATABASE_URL, 
    connect_args={"check_same_thread": False}  # Needed for SQLite
)

templates_engine = create_engine(
    TEMPLATES_DATABASE_URL, 
    connect_args={"check_same_thread": False}  # Needed for SQLite
)

# Create sessionmakers
SecretsSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=secrets_engine)
TemplatesSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=templates_engine)

# Create base classes for models
SecretsBase = declarative_base()
TemplatesBase = declarative_base()

# Keep backward compatibility
engine = secrets_engine
SessionLocal = SecretsSessionLocal
Base = SecretsBase

class Secret(SecretsBase):
    """Secret model for storing encrypted secrets"""
    __tablename__ = "secrets"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)
    encrypted_value = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# Create all tables
def create_tables():
    # Create secrets tables
    SecretsBase.metadata.create_all(bind=secrets_engine)
    # Create templates tables
    from templates_models import Template
    TemplatesBase.metadata.create_all(bind=templates_engine)

# Dependency to get secrets database session
def get_db():
    db = SecretsSessionLocal()
    try:
        yield db
    finally:
        db.close()

# Dependency to get templates database session
def get_templates_db():
    db = TemplatesSessionLocal()
    try:
        yield db
    finally:
        db.close()