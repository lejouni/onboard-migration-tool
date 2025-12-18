from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from templates_models import Template
from typing import List, Optional

class TemplateCRUD:
    """CRUD operations for templates"""

    @staticmethod
    def create_template(db: Session, name: str, content: str, description: str = None, keywords: str = None, 
                       template_type: str = 'workflow', category: str = None, meta_data: dict = None) -> Template:
        """Create a new template"""
        try:
            template = Template(
                name=name,
                description=description,
                content=content,
                keywords=keywords,
                template_type=template_type,
                category=category,
                meta_data=meta_data
            )
            db.add(template)
            db.commit()
            db.refresh(template)
            return template
        except IntegrityError:
            db.rollback()
            raise ValueError(f"Template with name '{name}' already exists")

    @staticmethod
    def get_template_by_id(db: Session, template_id: int) -> Optional[Template]:
        """Get a template by ID"""
        return db.query(Template).filter(Template.id == template_id).first()

    @staticmethod
    def get_template_by_name(db: Session, name: str) -> Optional[Template]:
        """Get a template by name"""
        return db.query(Template).filter(Template.name == name).first()

    @staticmethod
    def get_all_templates(db: Session) -> List[Template]:
        """Get all templates"""
        return db.query(Template).order_by(Template.name).all()

    @staticmethod
    def update_template(db: Session, template_id: int, name: str = None, content: str = None, description: str = None, 
                       keywords: str = None, template_type: str = None, category: str = None, meta_data: dict = None) -> Optional[Template]:
        """Update a template"""
        template = TemplateCRUD.get_template_by_id(db, template_id)
        if not template:
            return None

        try:
            if name is not None:
                template.name = name
            if content is not None:
                template.content = content
            if description is not None:
                template.description = description
            if keywords is not None:
                template.keywords = keywords
            if template_type is not None:
                template.template_type = template_type
            if category is not None:
                template.category = category
            if meta_data is not None:
                template.meta_data = meta_data

            db.commit()
            db.refresh(template)
            return template
        except IntegrityError:
            db.rollback()
            raise ValueError(f"Template with name '{name}' already exists")

    @staticmethod
    def delete_template(db: Session, template_id: int) -> bool:
        """Delete a template"""
        template = TemplateCRUD.get_template_by_id(db, template_id)
        if not template:
            return False

        db.delete(template)
        db.commit()
        return True

    @staticmethod
    def search_templates(db: Session, query: str) -> List[Template]:
        """Search templates by name, description, or keywords"""
        search_pattern = f"%{query}%"
        return db.query(Template).filter(
            (Template.name.ilike(search_pattern)) |
            (Template.description.ilike(search_pattern)) |
            (Template.keywords.ilike(search_pattern))
        ).order_by(Template.name).all()

    @staticmethod
    def get_templates_by_type(db: Session, template_type: str) -> List[Template]:
        """Get all templates of a specific type (workflow, job, step)"""
        return db.query(Template).filter(Template.template_type == template_type).order_by(Template.name).all()

    @staticmethod
    def get_templates_by_category(db: Session, category: str) -> List[Template]:
        """Get all templates of a specific category (polaris, coverity, blackduck_sca)"""
        return db.query(Template).filter(Template.category == category).order_by(Template.name).all()

    @staticmethod
    def get_job_fragments(db: Session, language: str = None) -> List[Template]:
        """Get job fragments, optionally filtered by compatible language"""
        query = db.query(Template).filter(Template.template_type == 'job')
        
        if language:
            # Filter by language in meta_data JSON
            # Note: This requires JSON support in SQLite (version 3.38.0+)
            templates = query.all()
            return [t for t in templates if t.meta_data and language in t.meta_data.get('compatible_languages', [])]
        
        return query.order_by(Template.name).all()

    @staticmethod
    def get_step_fragments(db: Session, language: str = None) -> List[Template]:
        """Get step fragments, optionally filtered by compatible language"""
        query = db.query(Template).filter(Template.template_type == 'step')
        
        if language:
            templates = query.all()
            return [t for t in templates if t.meta_data and language in t.meta_data.get('compatible_languages', [])]
        
        return query.order_by(Template.name).all()
