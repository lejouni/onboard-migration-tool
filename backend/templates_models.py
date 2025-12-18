from sqlalchemy import Column, Integer, String, Text, DateTime, JSON
from sqlalchemy.sql import func
from database import TemplatesBase

class Template(TemplatesBase):
    """Template model for storing reusable text templates"""
    __tablename__ = "templates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    content = Column(Text, nullable=False)
    keywords = Column(Text, nullable=True)  # Comma-separated keywords
    
    # New fields for workflow enhancement feature
    template_type = Column(String(50), nullable=True, default='workflow')  # 'workflow', 'job', 'step'
    category = Column(String(100), nullable=True)  # 'polaris', 'coverity', 'blackduck_sca', etc.
    meta_data = Column(JSON, nullable=True)  # Store tool, languages, parameters, etc. (renamed from metadata to avoid SQLAlchemy conflict)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<Template(id={self.id}, name='{self.name}', type='{self.template_type}')>"
