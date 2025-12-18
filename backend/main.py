from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_serializer
from typing import List, Optional
from datetime import datetime
import uvicorn
import httpx
import os
from sqlalchemy.orm import Session

# Import our modules
from database import get_db, get_templates_db, create_tables
from secrets_crud import SecretCRUD
from secrets_models import SecretCreate, SecretUpdate, SecretResponse, SecretWithValue, SecretsList
from github_service import GitHubService
from templates_crud import TemplateCRUD
from templates_models import Template
from polaris_converter import convert_polaris_to_coverity
from optimized_search import optimized_search
from workflow_analyzer import LocalWorkflowAnalyzer
from workflow_parser import WorkflowParser
from assessment_logic import determine_assessment_types
from workflow_enhancement_helpers import (
    fetch_repo_file_tree,
    generate_enhancement_recommendations,
    generate_new_workflow_recommendations
)
from crypto import decrypt_secret
from workflow_duplicate_detector import DuplicateDetector
from ai_analysis_parallel import analyze_repositories_parallel

app = FastAPI(
    title="Backend API with Secrets Management",
    description="A FastAPI backend with encrypted secrets storage",
    version="1.0.0"
)

# Create database tables on startup
create_tables()

def initialize_templates_from_files(db: Session):
    """Initialize database templates from template files if database is empty"""
    import json
    from pathlib import Path
    
    # Check if templates already exist
    existing_templates = TemplateCRUD.get_all_templates(db)
    if existing_templates:
        # Check if any template has invalid meta_data (JSON string instead of dict)
        needs_refresh = any(
            isinstance(t.meta_data, str) for t in existing_templates
        )
        if needs_refresh:
            print(f"⚠ Detected invalid template data, clearing and re-initializing...")
            # Delete all existing templates
            for template in existing_templates:
                db.delete(template)
            db.commit()
        else:
            print(f"✓ Templates already initialized ({len(existing_templates)} templates found)")
            return
    
    # Load templates from templates/blackduck directory
    templates_dir = Path(__file__).parent / "templates" / "blackduck"
    templates_json_path = templates_dir / "templates.json"
    
    if not templates_json_path.exists():
        print(f"Warning: Template configuration file not found at {templates_json_path}")
        return
    
    try:
        with open(templates_json_path, 'r') as f:
            templates_config = json.load(f)
        
        templates_data = templates_config.get('templates', [])
        loaded_count = 0
        
        for template_info in templates_data:
            template_file = template_info.get('file')
            if not template_file:
                continue
            
            template_file_path = templates_dir / template_file
            if not template_file_path.exists():
                print(f"Warning: Template file not found: {template_file_path}")
                continue
            
            # Read template content
            with open(template_file_path, 'r') as f:
                template_content = f.read()
            
            # Prepare meta_data
            meta_data = {
                'compatible_languages': template_info.get('languages', []),
                'tools': template_info.get('tools', []),
                'use_cases': template_info.get('use_cases', []),
                'requirements': template_info.get('requirements', {})
            }
            
            # Get template type from config or infer from file path
            template_type = template_info.get('template_type', 'workflow')
            tools = template_info.get('tools', [])
            use_cases = template_info.get('use_cases', [])
            
            # Determine category from tools and use_cases
            category_parts = []
            
            # Add tool-specific categories
            if 'Polaris' in tools:
                category_parts.append('polaris')
            if 'Coverity' in tools:
                category_parts.append('coverity')
            if 'Black Duck SCA' in tools or any('SCA' in uc for uc in use_cases):
                category_parts.append('blackduck_sca')
            if 'SRM' in tools:
                category_parts.append('srm')
            
            # Add scanning type categories
            if any('SAST' in uc for uc in use_cases):
                category_parts.append('SAST')
            if any('SCA' in uc or 'Dependency' in uc for uc in use_cases):
                category_parts.append('SCA')
            
            category = ','.join(category_parts) if category_parts else 'security'
            
            # Create template
            try:
                TemplateCRUD.create_template(
                    db,
                    name=template_info['name'],
                    content=template_content,
                    description=template_info.get('description'),
                    keywords=','.join(template_info.get('tools', [])),
                    template_type=template_type,
                    category=category,
                    meta_data=meta_data
                )
                loaded_count += 1
            except Exception as e:
                print(f"Warning: Could not create template '{template_info['name']}': {e}")
        
        print(f"✓ Initialized {loaded_count} templates from template files")
        
    except Exception as e:
        print(f"Warning: Could not initialize templates from files: {e}")

@app.on_event("startup")
async def startup_event():
    """Initialize required secrets and templates on startup if they don't exist"""
    from database import SecretsSessionLocal, TemplatesSessionLocal
    secrets_db = SecretsSessionLocal()
    templates_db = TemplatesSessionLocal()
    try:
        # Check and create GITHUB_TOKEN if missing
        github_token = SecretCRUD.get_secret_by_name(secrets_db, "GITHUB_TOKEN")
        if not github_token:
            SecretCRUD.create_secret(
                secrets_db,
                name="GITHUB_TOKEN",
                value="",  # Empty value - user must fill this
                description="[AUTO-GENERATED] Your GitHub Personal Access Token - Please update with your actual token from https://github.com/settings/tokens"
            )
            print("✓ Created GITHUB_TOKEN secret (empty - requires configuration)")
        
        # Log GitHub API URL configuration (from environment variable)
        github_api_url = os.getenv('GITHUB_API_URL', 'https://api.github.com')
        print(f"✓ Using GitHub API URL: {github_api_url}")
        if github_api_url == 'https://api.github.com':
            print("  (Default GitHub.com - set GITHUB_API_URL environment variable for GitHub Enterprise Server)")
        else:
            print("  (From GITHUB_API_URL environment variable)")
        
        # Initialize templates from files if database is empty
        initialize_templates_from_files(templates_db)
        
    except Exception as e:
        print(f"Warning: Could not initialize required secrets and templates: {e}")
    finally:
        secrets_db.close()
        templates_db.close()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class Item(BaseModel):
    id: Optional[int] = None
    name: str
    description: Optional[str] = None

class ItemCreate(BaseModel):
    name: str
    description: Optional[str] = None

# In-memory storage (replace with database in production)
items_db = []
next_id = 1

@app.get("/")
async def root():
    return {"message": "Welcome to the Backend API"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.post("/api/cache/clear")
async def clear_cache():
    """Clear the repository cache"""
    GitHubService._repo_cache.clear()
    return {"status": "success", "message": "Repository cache cleared"}

@app.get("/api/items", response_model=List[Item])
async def get_items():
    return items_db

@app.get("/api/items/{item_id}", response_model=Item)
async def get_item(item_id: int):
    item = next((item for item in items_db if item["id"] == item_id), None)
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return item

@app.post("/api/items", response_model=Item)
async def create_item(item: ItemCreate):
    global next_id
    new_item = {
        "id": next_id,
        "name": item.name,
        "description": item.description
    }
    items_db.append(new_item)
    next_id += 1
    return new_item

@app.put("/api/items/{item_id}", response_model=Item)
async def update_item(item_id: int, item: ItemCreate):
    existing_item = next((item for item in items_db if item["id"] == item_id), None)
    if existing_item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    
    existing_item["name"] = item.name
    existing_item["description"] = item.description
    return existing_item

@app.delete("/api/items/{item_id}")
async def delete_item(item_id: int):
    global items_db
    items_db = [item for item in items_db if item["id"] != item_id]
    return {"message": "Item deleted successfully"}

# ========== SECRETS MANAGEMENT ENDPOINTS ==========

@app.get("/api/secrets", response_model=List[SecretResponse])
async def get_secrets(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Get all secrets (without decrypted values)"""
    try:
        secrets = SecretCRUD.get_secrets(db, skip=skip, limit=limit)
        return secrets
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching secrets: {str(e)}")

@app.get("/api/secrets/{secret_id}", response_model=SecretResponse)
async def get_secret(secret_id: int, db: Session = Depends(get_db)):
    """Get a secret by ID (without decrypted value)"""
    try:
        secret = SecretCRUD.get_secret(db, secret_id)
        if not secret:
            raise HTTPException(status_code=404, detail="Secret not found")
        return secret
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching secret: {str(e)}")

@app.get("/api/secrets/{secret_id}/decrypt", response_model=SecretWithValue)
async def get_secret_decrypted(secret_id: int, db: Session = Depends(get_db)):
    """Get a secret by ID with decrypted value"""
    try:
        secret = SecretCRUD.get_secret(db, secret_id)
        if not secret:
            raise HTTPException(status_code=404, detail="Secret not found")
        
        # Decrypt the value
        decrypted_value = SecretCRUD.decrypt_secret_value(secret)
        
        # Create response with decrypted value
        return SecretWithValue(
            id=secret.id,
            name=secret.name,
            description=secret.description,
            value=decrypted_value,
            created_at=secret.created_at,
            updated_at=secret.updated_at
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error decrypting secret: {str(e)}")

@app.post("/api/secrets", response_model=SecretResponse)
async def create_secret(secret: SecretCreate, db: Session = Depends(get_db)):
    """Create a new secret"""
    try:
        new_secret = SecretCRUD.create_secret(
            db, 
            name=secret.name, 
            value=secret.value, 
            description=secret.description
        )
        return new_secret
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating secret: {str(e)}")

@app.put("/api/secrets/{secret_id}", response_model=SecretResponse)
async def update_secret(secret_id: int, secret: SecretUpdate, db: Session = Depends(get_db)):
    """Update a secret"""
    try:
        updated_secret = SecretCRUD.update_secret(
            db, 
            secret_id, 
            name=secret.name, 
            value=secret.value, 
            description=secret.description
        )
        if not updated_secret:
            raise HTTPException(status_code=404, detail="Secret not found")
        return updated_secret
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating secret: {str(e)}")

@app.delete("/api/secrets/{secret_id}")
async def delete_secret(secret_id: int, db: Session = Depends(get_db)):
    """Delete a secret"""
    try:
        # Check if this is a protected secret
        secret = SecretCRUD.get_secret_by_id(db, secret_id)
        if secret and secret.name in ["GITHUB_TOKEN", "GITHUB_API_URL"]:
            raise HTTPException(
                status_code=403, 
                detail=f"Cannot delete required secret: {secret.name}"
            )
        
        success = SecretCRUD.delete_secret(db, secret_id)
        if not success:
            raise HTTPException(status_code=404, detail="Secret not found")
        return {"message": "Secret deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting secret: {str(e)}")

@app.get("/api/secrets/name/{secret_name}", response_model=SecretResponse)
async def get_secret_by_name(secret_name: str, db: Session = Depends(get_db)):
    """Get a secret by name (without decrypted value)"""
    try:
        secret = SecretCRUD.get_secret_by_name(db, secret_name)
        if not secret:
            raise HTTPException(status_code=404, detail="Secret not found")
        return secret
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching secret: {str(e)}")

# ========== GITHUB API ENDPOINTS ==========

@app.get("/api/github/token-status")
async def check_github_token_status(db: Session = Depends(get_db)):
    """Check if GITHUB_TOKEN exists and is valid"""
    try:
        token = await GitHubService.get_github_token(db)
        if not token:
            return {
                "has_token": False,
                "is_valid": False,
                "message": "GITHUB_TOKEN secret not found. Please add it in Secrets Management."
            }
        
        is_valid = await GitHubService.verify_token(token)
        if not is_valid:
            return {
                "has_token": True,
                "is_valid": False,
                "message": "GITHUB_TOKEN exists but is invalid. Please update it in Secrets Management."
            }
        
        # Get user info to show which user the token belongs to
        user_info = await GitHubService.get_user_info(token)
        return {
            "has_token": True,
            "is_valid": True,
            "user": {
                "login": user_info.get("login"),
                "name": user_info.get("name"),
                "avatar_url": user_info.get("avatar_url")
            },
            "message": f"GITHUB_TOKEN is valid for user: {user_info.get('login')}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error checking token status: {str(e)}")

@app.get("/api/github/token-scopes")
async def get_github_token_scopes(db: Session = Depends(get_db)):
    """Get the scopes available for the current GitHub token"""
    try:
        token = await GitHubService.get_github_token(db)
        if not token:
            raise HTTPException(
                status_code=404,
                detail="GITHUB_TOKEN secret not found. Please add it in Secrets Management."
            )
        
        scopes = await GitHubService.get_token_scopes(token)
        return {
            "scopes": scopes,
            "has_repo_scope": "repo" in scopes,
            "has_public_repo_scope": "public_repo" in scopes,
            "message": "These are the scopes available for your GitHub token. 'repo' scope is needed for private repositories."
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching token scopes: {str(e)}")

@app.post("/api/github/cache/clear")
async def clear_github_cache():
    """Clear the GitHub repository cache"""
    try:
        GitHubService._repo_cache.clear()
        return {
            "success": True,
            "message": "GitHub repository cache cleared successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error clearing cache: {str(e)}")

@app.get("/api/github/organizations")
async def get_github_organizations(db: Session = Depends(get_db)):
    """Get GitHub organizations for the authenticated user"""
    try:
        token = await GitHubService.get_github_token(db)
        if not token:
            raise HTTPException(
                status_code=404, 
                detail="GITHUB_TOKEN secret not found. Please add it in Secrets Management."
            )
        
        if not await GitHubService.verify_token(token):
            raise HTTPException(
                status_code=401,
                detail="GITHUB_TOKEN is invalid. Please update it in Secrets Management."
            )
        
        organizations = await GitHubService.get_user_organizations(token)
        
        # Format the response
        formatted_orgs = [GitHubService.format_organization(org) for org in organizations]
        
        return {
            "organizations": formatted_orgs,
            "count": len(formatted_orgs)
        }
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        # Check if this is an SSO-related error
        if GitHubService.is_sso_error(error_msg):
            raise HTTPException(
                status_code=403,
                detail=GitHubService.get_sso_error_message()
            )
        raise HTTPException(status_code=500, detail=f"Error fetching organizations: {error_msg}")

@app.get("/api/github/organizations/{org_name}")
async def get_github_organization_details(org_name: str, db: Session = Depends(get_db)):
    """Get detailed information about a specific GitHub organization"""
    try:
        token = await GitHubService.get_github_token(db)
        if not token:
            raise HTTPException(
                status_code=404,
                detail="GITHUB_TOKEN secret not found. Please add it in Secrets Management."
            )
        
        if not await GitHubService.verify_token(token):
            raise HTTPException(
                status_code=401,
                detail="GITHUB_TOKEN is invalid. Please update it in Secrets Management."
            )
        
        org_details = await GitHubService.get_organization_details(token, org_name)
        return GitHubService.format_organization(org_details)
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        if GitHubService.is_sso_error(error_msg):
            raise HTTPException(
                status_code=403,
                detail=GitHubService.get_sso_error_message(org_name)
            )
        raise HTTPException(status_code=500, detail=f"Error fetching organization details: {error_msg}")

@app.get("/api/github/organizations/{org_name}/repositories")
async def get_github_organization_repositories(org_name: str, language: str, db: Session = Depends(get_db)):
    """Get repositories for a specific GitHub organization filtered by language (language is required)"""
    if not language or language.strip() == "":
        raise HTTPException(
            status_code=400,
            detail="Language parameter is required. Use 'all' to get repositories of all languages."
        )
    
    try:
        token = await GitHubService.get_github_token(db)
        if not token:
            raise HTTPException(
                status_code=404,
                detail="GITHUB_TOKEN secret not found. Please add it in Secrets Management."
            )
        
        if not await GitHubService.verify_token(token):
            raise HTTPException(
                status_code=401,
                detail="GITHUB_TOKEN is invalid. Please update it in Secrets Management."
            )
        
        repositories = await GitHubService.get_organization_repositories(token, org_name)
        
        # Enhanced filtering: check both primary language and detailed language breakdown
        if language.lower() != "all":
            filtered_repositories = []
            for repo in repositories:
                repo_has_language = False
                
                # Check primary language
                if repo.get("language") and repo.get("language").lower() == language.lower():
                    repo_has_language = True
                
                # Check detailed language breakdown if available
                if not repo_has_language and repo.get("languages_detail") and isinstance(repo.get("languages_detail"), dict):
                    for lang_name, bytes_count in repo.get("languages_detail").items():
                        if lang_name and bytes_count > 0 and lang_name.lower() == language.lower():
                            repo_has_language = True
                            break
                
                if repo_has_language:
                    filtered_repositories.append(repo)
            
            repositories = filtered_repositories
        
        # Format the response
        formatted_repos = [GitHubService.format_repository(repo) for repo in repositories]
        
        return {
            "organization": org_name,
            "repositories": formatted_repos,
            "count": len(formatted_repos),
            "filtered_by_language": language if language.lower() != "all" else None,
            "filter_method": "comprehensive" if language.lower() != "all" else "none",
            "note": "Filtering includes both primary language and detailed language breakdown" if language.lower() != "all" else None
        }
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        if GitHubService.is_sso_error(error_msg):
            raise HTTPException(
                status_code=403,
                detail=GitHubService.get_sso_error_message(org_name)
            )
        raise HTTPException(status_code=500, detail=f"Error fetching repositories: {error_msg}")

@app.get("/api/github/organizations/{org_name}/languages")
async def get_github_organization_languages(org_name: str, db: Session = Depends(get_db)):
    """Get available programming languages for a specific GitHub organization (comprehensive list)"""
    try:
        token = await GitHubService.get_github_token(db)
        if not token:
            raise HTTPException(
                status_code=404,
                detail="GITHUB_TOKEN secret not found. Please add it in Secrets Management."
            )
        
        if not await GitHubService.verify_token(token):
            raise HTTPException(
                status_code=401,
                detail="GITHUB_TOKEN is invalid. Please update it in Secrets Management."
            )
        
        repositories = await GitHubService.get_organization_repositories(token, org_name)
        
        # Get comprehensive list of all languages (primary + secondary from detailed breakdown)
        languages = set()
        language_stats = {}
        repos_with_detailed_languages = 0
        
        for repo in repositories:
            # Add primary language if available
            if repo.get("language"):
                primary_lang = repo.get("language")
                languages.add(primary_lang)
                language_stats[primary_lang] = language_stats.get(primary_lang, {"repo_count": 0, "is_primary": 0})
                language_stats[primary_lang]["repo_count"] += 1
                language_stats[primary_lang]["is_primary"] += 1
            
            # Add all languages from detailed breakdown if available
            if repo.get("languages_detail") and isinstance(repo.get("languages_detail"), dict):
                repos_with_detailed_languages += 1
                for lang_name, bytes_count in repo.get("languages_detail").items():
                    if lang_name and bytes_count > 0:  # Only include languages with actual code
                        languages.add(lang_name)
                        if lang_name not in language_stats:
                            language_stats[lang_name] = {"repo_count": 0, "is_primary": 0}
                        # Only increment repo_count if this language wasn't already counted for this repo
                        if repo.get("language") != lang_name:
                            language_stats[lang_name]["repo_count"] += 1
        
        # Sort languages by popularity (most used first) and create objects with name and count
        sorted_languages = sorted(
            list(languages), 
            key=lambda lang: (language_stats.get(lang, {}).get("repo_count", 0), lang.lower()), 
            reverse=True
        )
        
        # Format languages as objects with name and count
        formatted_languages = [
            {
                "name": lang,
                "count": language_stats.get(lang, {}).get("repo_count", 0)
            }
            for lang in sorted_languages
        ]
        
        return {
            "organization": org_name,
            "languages": formatted_languages,
            "language_stats": language_stats,
            "total_repositories": len(repositories),
            "repos_with_detailed_languages": repos_with_detailed_languages,
            "collection_method": "comprehensive" if repos_with_detailed_languages > 0 else "primary_only",
            "note": f"Collected from {repos_with_detailed_languages} repositories with detailed language data + primary languages from all {len(repositories)} repositories"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching languages: {str(e)}")

@app.get("/api/github/organizations/{org_name}/secrets")
async def get_github_organization_secrets(org_name: str, db: Session = Depends(get_db)):
    """Get organization secrets (only names, not values)"""
    try:
        token = await GitHubService.get_github_token(db)
        if not token:
            raise HTTPException(
                status_code=404,
                detail="GITHUB_TOKEN secret not found. Please add it in Secrets Management."
            )
        
        if not await GitHubService.verify_token(token):
            raise HTTPException(
                status_code=401,
                detail="GITHUB_TOKEN is invalid. Please update it in Secrets Management."
            )
        
        secrets = await GitHubService.get_organization_secrets(token, org_name)
        return {
            "organization": org_name,
            "secrets": secrets,
            "count": len(secrets)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching organization secrets: {str(e)}")

@app.get("/api/github/organizations/{org_name}/custom-properties")
async def get_github_organization_custom_properties(org_name: str, db: Session = Depends(get_db)):
    """Get organization custom properties schema"""
    try:
        token = await GitHubService.get_github_token(db)
        if not token:
            raise HTTPException(
                status_code=404,
                detail="GITHUB_TOKEN secret not found. Please add it in Secrets Management."
            )
        
        if not await GitHubService.verify_token(token):
            raise HTTPException(
                status_code=401,
                detail="GITHUB_TOKEN is invalid. Please update it in Secrets Management."
            )
        
        properties = await GitHubService.get_organization_custom_properties(token, org_name)
        return {
            "organization": org_name,
            "custom_properties": properties,
            "count": len(properties)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching organization custom properties: {str(e)}")

@app.get("/api/github/organizations/{org_name}/variables")
async def get_github_organization_variables(org_name: str, db: Session = Depends(get_db)):
    """Get organization variables (names and values)"""
    try:
        token = await GitHubService.get_github_token(db)
        if not token:
            raise HTTPException(
                status_code=404,
                detail="GITHUB_TOKEN secret not found. Please add it in Secrets Management."
            )
        
        if not await GitHubService.verify_token(token):
            raise HTTPException(
                status_code=401,
                detail="GITHUB_TOKEN is invalid. Please update it in Secrets Management."
            )
        
        variables = await GitHubService.get_organization_variables(token, org_name)
        return {
            "organization": org_name,
            "variables": variables,
            "count": len(variables)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching organization variables: {str(e)}")



@app.get("/api/github/user/repositories")
async def get_github_user_repositories(language: str, db: Session = Depends(get_db)):
    """Get all repositories the authenticated user has access to, filtered by language (language is required)"""
    if not language or language.strip() == "":
        raise HTTPException(
            status_code=400,
            detail="Language parameter is required. Use 'all' to get repositories of all languages."
        )
    
    try:
        token = await GitHubService.get_github_token(db)
        if not token:
            raise HTTPException(
                status_code=404,
                detail="GITHUB_TOKEN secret not found. Please add it in Secrets Management."
            )
        
        if not await GitHubService.verify_token(token):
            raise HTTPException(
                status_code=401,
                detail="GITHUB_TOKEN is invalid. Please update it in Secrets Management."
            )
        
        repositories = await GitHubService.get_user_repositories(token)
        
        # Enhanced filtering: check both primary language and detailed language breakdown
        if language.lower() != "all":
            filtered_repositories = []
            for repo in repositories:
                repo_has_language = False
                
                # Check primary language
                if repo.get("language") and repo.get("language").lower() == language.lower():
                    repo_has_language = True
                
                # Check detailed language breakdown if available
                if not repo_has_language and repo.get("languages_detail") and isinstance(repo.get("languages_detail"), dict):
                    for lang_name, bytes_count in repo.get("languages_detail").items():
                        if lang_name and bytes_count > 0 and lang_name.lower() == language.lower():
                            repo_has_language = True
                            break
                
                if repo_has_language:
                    filtered_repositories.append(repo)
            
            repositories = filtered_repositories
        
        # Format the response
        formatted_repos = [GitHubService.format_repository(repo) for repo in repositories]
        
        return {
            "scope": "user_all_repositories",
            "repositories": formatted_repos,
            "count": len(formatted_repos),
            "filtered_by_language": language if language.lower() != "all" else None,
            "filter_method": "comprehensive" if language.lower() != "all" else "none",
            "note": "Filtering includes both primary language and detailed language breakdown" if language.lower() != "all" else None
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching user repositories: {str(e)}")

@app.get("/api/github/user/languages")
async def get_github_user_languages(db: Session = Depends(get_db)):
    """Get available programming languages for all user repositories (comprehensive list)"""
    try:
        token = await GitHubService.get_github_token(db)
        if not token:
            raise HTTPException(
                status_code=404,
                detail="GITHUB_TOKEN secret not found. Please add it in Secrets Management."
            )
        
        if not await GitHubService.verify_token(token):
            raise HTTPException(
                status_code=401,
                detail="GITHUB_TOKEN is invalid. Please update it in Secrets Management."
            )
        
        repositories = await GitHubService.get_user_repositories(token)
        
        # Get comprehensive list of all languages (primary + secondary from detailed breakdown)
        languages = set()
        language_stats = {}
        repos_with_detailed_languages = 0
        
        for repo in repositories:
            # Add primary language if available
            if repo.get("language"):
                primary_lang = repo.get("language")
                languages.add(primary_lang)
                language_stats[primary_lang] = language_stats.get(primary_lang, {"repo_count": 0, "is_primary": 0})
                language_stats[primary_lang]["repo_count"] += 1
                language_stats[primary_lang]["is_primary"] += 1
            
            # Add all languages from detailed breakdown if available
            if repo.get("languages_detail") and isinstance(repo.get("languages_detail"), dict):
                repos_with_detailed_languages += 1
                for lang_name, bytes_count in repo.get("languages_detail").items():
                    if lang_name and bytes_count > 0:  # Only include languages with actual code
                        languages.add(lang_name)
                        if lang_name not in language_stats:
                            language_stats[lang_name] = {"repo_count": 0, "is_primary": 0}
                        # Only increment repo_count if this language wasn't already counted for this repo
                        if repo.get("language") != lang_name:
                            language_stats[lang_name]["repo_count"] += 1
        
        # Sort languages by popularity (most used first) and create objects with name and count
        sorted_languages = sorted(
            list(languages), 
            key=lambda lang: (language_stats.get(lang, {}).get("repo_count", 0), lang.lower()), 
            reverse=True
        )
        
        # Format languages as objects with name and count
        formatted_languages = [
            {
                "name": lang,
                "count": language_stats.get(lang, {}).get("repo_count", 0)
            }
            for lang in sorted_languages
        ]
        
        return {
            "scope": "user_all_repositories",
            "languages": formatted_languages,
            "language_stats": language_stats,
            "total_repositories": len(repositories),
            "repos_with_detailed_languages": repos_with_detailed_languages,
            "collection_method": "comprehensive" if repos_with_detailed_languages > 0 else "primary_only",
            "note": f"Collected from {repos_with_detailed_languages} repositories with detailed language data + primary languages from all {len(repositories)} repositories"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching user languages: {str(e)}")

@app.get("/api/github/user")
async def get_github_user(db: Session = Depends(get_db)):
    """Get GitHub user information for the authenticated token"""
    try:
        token = await GitHubService.get_github_token(db)
        if not token:
            raise HTTPException(
                status_code=404,
                detail="GITHUB_TOKEN secret not found. Please add it in Secrets Management."
            )
        
        user_info = await GitHubService.get_user_info(token)
        return {
            "login": user_info.get("login"),
            "name": user_info.get("name"),
            "email": user_info.get("email"),
            "avatar_url": user_info.get("avatar_url"),
            "html_url": user_info.get("html_url"),
            "company": user_info.get("company"),
            "location": user_info.get("location"),
            "bio": user_info.get("bio"),
            "public_repos": user_info.get("public_repos"),
            "followers": user_info.get("followers"),
            "following": user_info.get("following"),
            "created_at": user_info.get("created_at")
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching user info: {str(e)}")

@app.get("/api/github/repositories/{owner}/{repo_name}/details")
async def get_github_repository_details(owner: str, repo_name: str, db: Session = Depends(get_db)):
    """Get detailed information about a specific repository including custom properties"""
    try:
        token = await GitHubService.get_github_token(db)
        if not token:
            raise HTTPException(
                status_code=404,
                detail="GITHUB_TOKEN secret not found. Please add it in Secrets Management."
            )
        
        if not await GitHubService.verify_token(token):
            raise HTTPException(
                status_code=401,
                detail="GITHUB_TOKEN is invalid. Please update it in Secrets Management."
            )
        
        try:
            repo_details = await GitHubService.get_repository_details(token, owner, repo_name)
            # Also fetch branches
            branches = await GitHubService.get_repository_branches(token, owner, repo_name)
        except ValueError as e:
            # Handle specific repository errors (not found, access denied, etc.)
            if "not found" in str(e).lower():
                raise HTTPException(status_code=404, detail=str(e))
            elif "access denied" in str(e).lower():
                raise HTTPException(status_code=403, detail=str(e))
            else:
                raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error fetching repository details: {str(e)}")
        
        # Format the response with enhanced details
        formatted_details = {
            **GitHubService.format_repository(repo_details),
            "custom_properties": repo_details.get("custom_properties", {}),
            "languages_detail": repo_details.get("languages_detail", {}),
            "topics_complete": repo_details.get("topics_list", []),
            "latest_release": repo_details.get("latest_release"),
            "readme_info": repo_details.get("readme_info"),
            "owner_details": {
                "login": repo_details.get("owner", {}).get("login"),
                "type": repo_details.get("owner", {}).get("type"),
                "avatar_url": repo_details.get("owner", {}).get("avatar_url"),
                "html_url": repo_details.get("owner", {}).get("html_url")
            },
            "network_info": {
                "network_count": repo_details.get("network_count"),
                "subscribers_count": repo_details.get("subscribers_count"),
                "forks_count": repo_details.get("forks_count"),
                "stargazers_count": repo_details.get("stargazers_count"),
                "watchers_count": repo_details.get("watchers_count")
            },
            "repository_stats": {
                "size": repo_details.get("size"),
                "open_issues_count": repo_details.get("open_issues_count"),
                "has_issues": repo_details.get("has_issues"),
                "has_projects": repo_details.get("has_projects"),
                "has_wiki": repo_details.get("has_wiki"),
                "has_pages": repo_details.get("has_pages"),
                "has_downloads": repo_details.get("has_downloads"),
                "has_discussions": repo_details.get("has_discussions")
            },
            "permissions": {
                "admin": repo_details.get("permissions", {}).get("admin"),
                "maintain": repo_details.get("permissions", {}).get("maintain"),
                "push": repo_details.get("permissions", {}).get("push"),
                "triage": repo_details.get("permissions", {}).get("triage"),
                "pull": repo_details.get("permissions", {}).get("pull")
            },
            "workflow_info": repo_details.get("workflow_info", {
                "workflow_files": [],
                "total_count": 0,
                "has_workflows": False
            }),
            "branches": branches  # Add branches to repository details
        }
        
        return formatted_details
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching repository details: {str(e)}")

@app.get("/api/github/repositories/{owner}/{repo_name}/branches")
async def get_repository_branches(owner: str, repo_name: str, db: Session = Depends(get_db)):
    """Get all branches for a specific repository"""
    try:
        token = await GitHubService.get_github_token(db)
        if not token:
            raise HTTPException(
                status_code=404,
                detail="GITHUB_TOKEN secret not found. Please add it in Secrets Management."
            )
        
        if not await GitHubService.verify_token(token):
            raise HTTPException(
                status_code=401,
                detail="GITHUB_TOKEN is invalid. Please update it in Secrets Management."
            )
        
        branches = await GitHubService.get_repository_branches(token, owner, repo_name)
        return {"branches": branches}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching repository branches: {str(e)}")

@app.get("/api/github/repositories/{full_repo_name:path}/tree")
async def get_repository_tree(full_repo_name: str, branch: str = "main", db: Session = Depends(get_db)):
    """Get repository file tree for detecting legacy config files"""
    try:
        token = await GitHubService.get_github_token(db)
        if not token:
            raise HTTPException(
                status_code=404,
                detail="GITHUB_TOKEN secret not found. Please add it in Secrets Management."
            )
        
        if not await GitHubService.verify_token(token):
            raise HTTPException(
                status_code=401,
                detail="GITHUB_TOKEN is invalid. Please update it in Secrets Management."
            )
        
        async with httpx.AsyncClient(verify=False) as client:
            headers = {
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github.v3+json"
            }
            
            # If no specific branch provided, get the default branch
            branch_to_use = branch
            if not branch or branch == "main":
                repo_url = f"https://api.github.com/repos/{full_repo_name}"
                repo_response = await client.get(repo_url, headers=headers)
                if repo_response.status_code == 200:
                    repo_data = repo_response.json()
                    branch_to_use = repo_data.get('default_branch', 'main')
            
            # Get tree recursively to find files in subdirectories
            tree_url = f"https://api.github.com/repos/{full_repo_name}/git/trees/{branch_to_use}?recursive=1"
            tree_response = await client.get(tree_url, headers=headers)
            
            if tree_response.status_code != 200:
                error_detail = f"Failed to fetch repository tree: {tree_response.status_code}"
                print(f"Error getting tree for {full_repo_name}/{default_branch}: {error_detail}, Response: {tree_response.text}")
                raise HTTPException(status_code=tree_response.status_code, detail=error_detail)
            
            return tree_response.json()
            
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"Exception in get_repository_tree for {full_repo_name}:")
        print(f"Error: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error fetching repository tree: {str(e)}")

@app.get("/api/github/repositories/{full_repo_name:path}/contents/{file_path:path}")
async def get_file_contents(full_repo_name: str, file_path: str, db: Session = Depends(get_db)):
    """Get file contents from a repository"""
    try:
        token = await GitHubService.get_github_token(db)
        if not token:
            raise HTTPException(
                status_code=404,
                detail="GITHUB_TOKEN secret not found. Please add it in Secrets Management."
            )
        
        if not await GitHubService.verify_token(token):
            raise HTTPException(
                status_code=401,
                detail="GITHUB_TOKEN is invalid. Please update it in Secrets Management."
            )
        
        async with httpx.AsyncClient(verify=False) as client:
            file_url = f"https://api.github.com/repos/{full_repo_name}/contents/{file_path}"
            headers = {
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github.v3+json"
            }
            
            file_response = await client.get(file_url, headers=headers)
            
            if file_response.status_code != 200:
                error_detail = f"Failed to fetch file contents: {file_response.status_code}"
                print(f"Error getting file {full_repo_name}/{file_path}: {error_detail}")
                raise HTTPException(status_code=file_response.status_code, detail=error_detail)
            
            return file_response.json()
            
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"Exception in get_file_contents for {full_repo_name}/{file_path}:")
        print(f"Error: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error fetching file contents: {str(e)}")

class DeleteFileRequest(BaseModel):
    file_path: str
    commit_message: str
    branch: str = "main"

@app.delete("/api/github/repositories/{full_repo_name:path}/delete-file")
async def delete_repository_file(
    full_repo_name: str,
    request: DeleteFileRequest,
    db: Session = Depends(get_db)
):
    """Delete a file from a repository"""
    try:
        token = await GitHubService.get_github_token(db)
        if not token:
            raise HTTPException(
                status_code=404,
                detail="GITHUB_TOKEN secret not found. Please add it in Secrets Management."
            )
        
        if not await GitHubService.verify_token(token):
            raise HTTPException(
                status_code=401,
                detail="GITHUB_TOKEN is invalid. Please update it in Secrets Management."
            )
        
        async with httpx.AsyncClient(verify=False) as client:
            headers = {
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github.v3+json"
            }
            
            # Get file SHA
            file_url = f"https://api.github.com/repos/{full_repo_name}/contents/{request.file_path}"
            file_response = await client.get(file_url, headers=headers, params={"ref": request.branch})
            
            if file_response.status_code != 200:
                raise HTTPException(status_code=404, detail=f"File not found: {request.file_path}")
            
            file_data = file_response.json()
            file_sha = file_data.get('sha')
            
            # Delete file using request() method with DELETE and JSON body
            import json
            delete_response = await client.request(
                "DELETE",
                file_url,
                headers={**headers, "Content-Type": "application/json"},
                content=json.dumps({
                    "message": request.commit_message,
                    "sha": file_sha,
                    "branch": request.branch
                }).encode('utf-8')
            )
            
            if delete_response.status_code not in [200, 204]:
                raise HTTPException(
                    status_code=delete_response.status_code,
                    detail=f"Failed to delete file: {delete_response.text}"
                )
            
            return {"message": f"Successfully deleted {request.file_path}", "commit": delete_response.json()}
            
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"Exception in delete_repository_file for {full_repo_name}/{request.file_path}:")
        print(f"Error: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error deleting file: {str(e)}")

class DeleteFilePRRequest(BaseModel):
    file_path: str
    commit_message: str
    pr_title: str
    pr_body: str
    branch: str = "main"

@app.post("/api/github/repositories/{full_repo_name:path}/delete-file-pr")
async def delete_repository_file_pr(
    full_repo_name: str,
    request: DeleteFilePRRequest,
    db: Session = Depends(get_db)
):
    """Create a pull request to delete a file from a repository"""
    try:
        token = await GitHubService.get_github_token(db)
        if not token:
            raise HTTPException(
                status_code=404,
                detail="GITHUB_TOKEN secret not found. Please add it in Secrets Management."
            )
        
        if not await GitHubService.verify_token(token):
            raise HTTPException(
                status_code=401,
                detail="GITHUB_TOKEN is invalid. Please update it in Secrets Management."
            )
        
        async with httpx.AsyncClient(verify=False) as client:
            headers = {
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github.v3+json"
            }
            
            # Get repository info
            repo_url = f"https://api.github.com/repos/{full_repo_name}"
            repo_response = await client.get(repo_url, headers=headers)
            
            if repo_response.status_code != 200:
                raise HTTPException(status_code=404, detail="Repository not found")
            
            repo_data = repo_response.json()
            default_branch = repo_data.get('default_branch', 'main')
            
            # Get the SHA of the default branch
            ref_url = f"https://api.github.com/repos/{full_repo_name}/git/refs/heads/{default_branch}"
            ref_response = await client.get(ref_url, headers=headers)
            
            if ref_response.status_code != 200:
                raise HTTPException(status_code=404, detail=f"Branch {default_branch} not found")
            
            ref_data = ref_response.json()
            base_sha = ref_data['object']['sha']
            
            # Create a new branch
            import time
            new_branch_name = f"remove-legacy-config-{int(time.time())}"
            create_branch_url = f"https://api.github.com/repos/{full_repo_name}/git/refs"
            import json
            create_branch_response = await client.request(
                "POST",
                create_branch_url,
                headers={**headers, "Content-Type": "application/json"},
                content=json.dumps({
                    "ref": f"refs/heads/{new_branch_name}",
                    "sha": base_sha
                }).encode('utf-8')
            )
            
            if create_branch_response.status_code != 201:
                raise HTTPException(status_code=500, detail=f"Failed to create branch: {create_branch_response.text}")
            
            # Get file SHA
            file_url = f"https://api.github.com/repos/{full_repo_name}/contents/{request.file_path}"
            file_response = await client.get(file_url, headers=headers, params={"ref": new_branch_name})
            
            if file_response.status_code != 200:
                raise HTTPException(status_code=404, detail=f"File not found: {request.file_path}")
            
            file_data = file_response.json()
            file_sha = file_data.get('sha')
            
            # Delete file in the new branch
            delete_response = await client.request(
                "DELETE",
                file_url,
                headers={**headers, "Content-Type": "application/json"},
                content=json.dumps({
                    "message": request.commit_message,
                    "sha": file_sha,
                    "branch": new_branch_name
                }).encode('utf-8')
            )
            
            if delete_response.status_code not in [200, 204]:
                raise HTTPException(
                    status_code=delete_response.status_code,
                    detail=f"Failed to delete file: {delete_response.text}"
                )
            
            # Create pull request
            pr_url = f"https://api.github.com/repos/{full_repo_name}/pulls"
            pr_response = await client.request(
                "POST",
                pr_url,
                headers={**headers, "Content-Type": "application/json"},
                content=json.dumps({
                    "title": request.pr_title,
                    "body": request.pr_body,
                    "head": new_branch_name,
                    "base": default_branch
                }).encode('utf-8')
            )
            
            if pr_response.status_code != 201:
                raise HTTPException(
                    status_code=pr_response.status_code,
                    detail=f"Failed to create pull request: {pr_response.text}"
                )
            
            pr_data = pr_response.json()
            return {
                "message": f"Successfully created PR to delete {request.file_path}",
                "pr_url": pr_data.get('html_url'),
                "pr_number": pr_data.get('number')
            }
            
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"Exception in delete_repository_file_pr for {full_repo_name}/{request.file_path}:")
        print(f"Error: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error creating PR to delete file: {str(e)}")

@app.get("/api/github/search/workflow-content")
async def search_repositories_by_workflow_content(
    search_term: str, 
    scope: str = 'user', 
    organization: str = None, 
    db: Session = Depends(get_db)
):
    """Search repositories by content within their GitHub workflow files"""
    if not search_term or len(search_term.strip()) < 2:
        raise HTTPException(
            status_code=400,
            detail="Search term must be at least 2 characters long"
        )
    
    if scope not in ['user', 'organization']:
        raise HTTPException(
            status_code=400,
            detail="Scope must be either 'user' or 'organization'"
        )
    
    if scope == 'organization' and not organization:
        raise HTTPException(
            status_code=400,
            detail="Organization name is required when scope is 'organization'"
        )
    
    try:
        token = await GitHubService.get_github_token(db)
        if not token:
            raise HTTPException(
                status_code=404,
                detail="GITHUB_TOKEN secret not found. Please add it in Secrets Management."
            )
        
        if not await GitHubService.verify_token(token):
            raise HTTPException(
                status_code=401,
                detail="GITHUB_TOKEN is invalid. Please update it in Secrets Management."
            )
        
        search_results = await GitHubService.search_repositories_by_workflow_content(
            token=token,
            search_term=search_term.strip(),
            scope=scope,
            org_name=organization
        )
        
        return search_results
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error searching workflow content: {str(e)}")

@app.get("/api/github/search/workflow-content/analyze")
async def analyze_workflows_with_templates(
    search_term: str, 
    scope: str = 'user', 
    organization: str = None, 
    db: Session = Depends(get_db),
    templates_db: Session = Depends(get_templates_db)
):
    """Search and analyze repositories' workflow files with AI-powered template recommendations"""
    if not search_term or len(search_term.strip()) < 2:
        raise HTTPException(
            status_code=400,
            detail="Search term must be at least 2 characters long"
        )
    
    if scope not in ['user', 'organization']:
        raise HTTPException(
            status_code=400,
            detail="Scope must be either 'user' or 'organization'"
        )
    
    if scope == 'organization' and not organization:
        raise HTTPException(
            status_code=400,
            detail="Organization name is required when scope is 'organization'"
        )
    
    try:
        token = await GitHubService.get_github_token(db)
        if not token:
            raise HTTPException(
                status_code=404,
                detail="GITHUB_TOKEN secret not found. Please add it in Secrets Management."
            )
        
        if not await GitHubService.verify_token(token):
            raise HTTPException(
                status_code=401,
                detail="GITHUB_TOKEN is invalid. Please update it in Secrets Management."
            )
        
        # First, get basic workflow search results
        search_results = await GitHubService.search_repositories_by_workflow_content(
            token=token,
            search_term=search_term.strip(),
            scope=scope,
            org_name=organization
        )
        
        # Get available templates for comparison
        available_templates = TemplateCRUD.get_all_templates(templates_db)
        
        # Convert templates to format expected by analyzer
        template_list = [
            {
                "id": str(template.id),
                "name": template.name,
                "description": template.description or "",
                "content": template.content,
                "keywords": template.keywords or ""
            }
            for template in available_templates
        ]
        
        # Analyze workflows and get template recommendations
        try:
            analyzed_results = await GitHubService.analyze_workflows_and_recommend_templates(
                token=token,
                search_results=search_results,
                available_templates=template_list
            )
        except Exception as analysis_error:
            print(f"Analysis error: {analysis_error}")
            import traceback
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=f"Error during workflow analysis: {str(analysis_error)}")
        
        return {
            **analyzed_results,
            "analysis_metadata": {
                "total_templates_available": len(template_list),
                "analysis_method": "local_mcp_server",
                "cost": "free",
                "features": [
                    "Technology detection",
                    "CI/CD pattern recognition", 
                    "Security assessment",
                    "Template similarity matching",
                    "Improvement recommendations"
                ]
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"General error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error analyzing workflow content: {str(e)}")

# ==================== Template Management API ====================

class TemplateCreate(BaseModel):
    """Schema for creating a template"""
    name: str
    description: Optional[str] = None
    content: str
    keywords: Optional[str] = None
    template_type: Optional[str] = 'workflow'
    category: Optional[str] = None
    meta_data: Optional[dict] = None

class TemplateUpdate(BaseModel):
    """Schema for updating a template"""
    name: Optional[str] = None
    description: Optional[str] = None
    content: Optional[str] = None
    keywords: Optional[str] = None
    template_type: Optional[str] = None
    category: Optional[str] = None
    meta_data: Optional[dict] = None

class TemplateResponse(BaseModel):
    """Schema for template response"""
    id: int
    name: str
    description: Optional[str]
    content: str
    keywords: Optional[str]
    template_type: Optional[str] = 'workflow'  # 'workflow', 'job', 'step'
    category: Optional[str] = None  # 'polaris', 'coverity', 'blackduck_sca', etc.
    meta_data: Optional[dict] = None  # Store tool, languages, parameters, etc.
    created_at: datetime
    updated_at: datetime

    @field_serializer('created_at', 'updated_at')
    def serialize_datetime(self, dt: datetime, _info):
        return dt.isoformat() if dt else None

    class Config:
        from_attributes = True

@app.post("/api/templates", response_model=TemplateResponse)
async def create_template(template: TemplateCreate, db: Session = Depends(get_templates_db)):
    """Create a new template"""
    try:
        new_template = TemplateCRUD.create_template(
            db=db,
            name=template.name,
            content=template.content,
            description=template.description,
            keywords=template.keywords,
            template_type=template.template_type,
            category=template.category,
            meta_data=template.meta_data
        )
        return new_template
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating template: {str(e)}")

@app.get("/api/templates", response_model=List[TemplateResponse])
async def get_all_templates(db: Session = Depends(get_templates_db)):
    """Get all templates"""
    try:
        templates = TemplateCRUD.get_all_templates(db)
        return templates
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching templates: {str(e)}")

@app.get("/api/templates/{template_id}", response_model=TemplateResponse)
async def get_template(template_id: int, db: Session = Depends(get_templates_db)):
    """Get a template by ID"""
    template = TemplateCRUD.get_template_by_id(db, template_id)
    if not template:
        raise HTTPException(status_code=404, detail=f"Template with ID {template_id} not found")
    return template

@app.get("/api/templates/search/{query}", response_model=List[TemplateResponse])
async def search_templates(query: str, db: Session = Depends(get_templates_db)):
    """Search templates by name or description"""
    try:
        templates = TemplateCRUD.search_templates(db, query)
        return templates
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error searching templates: {str(e)}")

@app.put("/api/templates/{template_id}", response_model=TemplateResponse)
async def update_template(template_id: int, template: TemplateUpdate, db: Session = Depends(get_templates_db)):
    """Update a template"""
    try:
        updated_template = TemplateCRUD.update_template(
            db=db,
            template_id=template_id,
            name=template.name,
            content=template.content,
            description=template.description,
            keywords=template.keywords,
            template_type=template.template_type,
            category=template.category,
            meta_data=template.meta_data
        )
        if not updated_template:
            raise HTTPException(status_code=404, detail=f"Template with ID {template_id} not found")
        return updated_template
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating template: {str(e)}")

@app.delete("/api/templates/{template_id}")
async def delete_template(template_id: int, db: Session = Depends(get_templates_db)):
    """Delete a template"""
    try:
        success = TemplateCRUD.delete_template(db, template_id)
        if not success:
            raise HTTPException(status_code=404, detail=f"Template with ID {template_id} not found")
        return {"message": f"Template {template_id} deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting template: {str(e)}")

@app.post("/api/templates/apply")
async def apply_template_to_repository(request: dict, db: Session = Depends(get_templates_db)):
    """
    Apply a template to a repository either directly or via pull request.
    
    Request body:
    {
        "template_name": "Black Duck SCA for JavaScript/npm",
        "repository": "owner/repo",
        "branch": "main",  # optional, defaults to main
        "method": "direct" | "pull_request",  # direct commit or create PR
        "pr_title": "Add Black Duck SCA workflow",  # optional, for PR method
        "pr_body": "This PR adds Black Duck SCA scanning..."  # optional, for PR method
    }
    """
    try:
        template_name = request.get("template_name")
        repository = request.get("repository")
        method = request.get("method", "direct")
        branch = request.get("branch", "main")
        pr_title = request.get("pr_title", f"Add {template_name} workflow")
        pr_body = request.get("pr_body", f"This PR adds the {template_name} workflow template.")
        template_content = request.get("template_content")  # Optional: custom template content
        
        if not template_name or not repository:
            raise HTTPException(status_code=400, detail="template_name and repository are required")
        
        if method not in ["direct", "pull_request"]:
            raise HTTPException(status_code=400, detail="method must be 'direct' or 'pull_request'")
        
        # Use provided template content or fetch from database
        if template_content:
            # Use custom content provided by user (for temporary modifications)
            content_to_apply = template_content
        else:
            # Get template from database
            templates = TemplateCRUD.search_templates(db, template_name)
            if not templates:
                raise HTTPException(status_code=404, detail=f"Template '{template_name}' not found")
            
            template = templates[0]  # Use first matching template
            content_to_apply = template.content
        
        # Get GitHub token
        github_token_secret = SecretCRUD.get_secret_by_name(db, "GITHUB_TOKEN")
        if not github_token_secret:
            raise HTTPException(status_code=404, detail="GITHUB_TOKEN secret not found")
        
        github_token = decrypt_secret(github_token_secret.encrypted_value)
        
        # Parse repository owner and name
        parts = repository.split('/')
        if len(parts) != 2:
            raise HTTPException(status_code=400, detail="Repository must be in format 'owner/repo'")
        
        owner, repo_name = parts
        
        # Generate workflow filename from template name (sanitize it)
        import re
        workflow_filename = re.sub(r'[^a-zA-Z0-9-]', '-', template.name.lower()) + '.yml'
        workflow_path = f".github/workflows/{workflow_filename}"
        
        async with httpx.AsyncClient(verify=False) as client:
            headers = {
                "Authorization": f"token {github_token}",
                "Accept": "application/vnd.github.v3+json"
            }
            
            if method == "direct":
                # Direct commit to branch
                # First, check if file already exists
                file_url = f"https://api.github.com/repos/{owner}/{repo_name}/contents/{workflow_path}"
                params = {"ref": branch}
                
                file_sha = None
                file_response = await client.get(file_url, headers=headers, params=params)
                if file_response.status_code == 200:
                    file_sha = file_response.json().get("sha")
                
                # Create or update the file
                import base64
                content_base64 = base64.b64encode(content_to_apply.encode()).decode()
                
                commit_data = {
                    "message": f"Add {template_name} workflow",
                    "content": content_base64,
                    "branch": branch
                }
                
                if file_sha:
                    commit_data["sha"] = file_sha  # Required for updating existing file
                
                commit_response = await client.put(file_url, headers=headers, json=commit_data)
                
                if commit_response.status_code not in [200, 201]:
                    raise HTTPException(status_code=500, detail=f"Failed to commit workflow: {commit_response.text}")
                
                return {
                    "success": True,
                    "method": "direct",
                    "repository": repository,
                    "branch": branch,
                    "workflow_path": workflow_path,
                    "commit_url": commit_response.json().get("commit", {}).get("html_url"),
                    "message": f"Template '{template_name}' applied directly to {branch} branch"
                }
            
            else:  # pull_request
                # Create a new branch and PR
                # 1. Get the base branch SHA
                ref_url = f"https://api.github.com/repos/{owner}/{repo_name}/git/ref/heads/{branch}"
                ref_response = await client.get(ref_url, headers=headers)
                
                if ref_response.status_code != 200:
                    raise HTTPException(status_code=500, detail=f"Failed to get base branch: {ref_response.text}")
                
                base_sha = ref_response.json()["object"]["sha"]
                
                # 2. Create a new branch
                new_branch = f"add-{workflow_filename.replace('.yml', '')}"
                create_ref_url = f"https://api.github.com/repos/{owner}/{repo_name}/git/refs"
                create_ref_data = {
                    "ref": f"refs/heads/{new_branch}",
                    "sha": base_sha
                }
                
                create_ref_response = await client.post(create_ref_url, headers=headers, json=create_ref_data)
                
                # If branch already exists, try with a timestamp
                if create_ref_response.status_code == 422:
                    from datetime import datetime
                    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
                    new_branch = f"add-{workflow_filename.replace('.yml', '')}-{timestamp}"
                    create_ref_data["ref"] = f"refs/heads/{new_branch}"
                    create_ref_response = await client.post(create_ref_url, headers=headers, json=create_ref_data)
                
                if create_ref_response.status_code != 201:
                    raise HTTPException(status_code=500, detail=f"Failed to create branch: {create_ref_response.text}")
                
                # 3. Add the workflow file to the new branch
                file_url = f"https://api.github.com/repos/{owner}/{repo_name}/contents/{workflow_path}"
                
                import base64
                content_base64 = base64.b64encode(content_to_apply.encode()).decode()
                
                commit_data = {
                    "message": f"Add {template_name} workflow",
                    "content": content_base64,
                    "branch": new_branch
                }
                
                commit_response = await client.put(file_url, headers=headers, json=commit_data)
                
                if commit_response.status_code not in [200, 201]:
                    raise HTTPException(status_code=500, detail=f"Failed to commit workflow: {commit_response.text}")
                
                # 4. Create pull request
                pr_url = f"https://api.github.com/repos/{owner}/{repo_name}/pulls"
                pr_data = {
                    "title": pr_title,
                    "body": pr_body,
                    "head": new_branch,
                    "base": branch
                }
                
                pr_response = await client.post(pr_url, headers=headers, json=pr_data)
                
                if pr_response.status_code != 201:
                    raise HTTPException(status_code=500, detail=f"Failed to create pull request: {pr_response.text}")
                
                pr_data = pr_response.json()
                
                return {
                    "success": True,
                    "method": "pull_request",
                    "repository": repository,
                    "base_branch": branch,
                    "pr_branch": new_branch,
                    "workflow_path": workflow_path,
                    "pr_url": pr_data.get("html_url"),
                    "pr_number": pr_data.get("number"),
                    "message": f"Pull request created for template '{template_name}'"
                }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error applying template: {str(e)}")

# ==================== Onboarding Endpoints ====================

@app.post("/api/onboarding/scan")
async def scan_repositories_for_onboarding(
    request: dict,
    db: Session = Depends(get_db),
    templates_db: Session = Depends(get_templates_db)
):
    """
    Scan selected repositories for workflow files and match against template keywords.
    Supports searching specific branches per repository.
    
    Request body:
    {
        "repositories": [
            {
                "repository": "owner/repo1",
                "branches": ["main", "dev"]
            },
            {
                "repository": "owner/repo2",
                "branches": ["main"]
            }
        ]
    }
    
    Or legacy format:
    {
        "repositories": ["owner/repo1", "owner/repo2"],
        "search_all_branches": false
    }
    """
    try:
        # Handle both old format (list) and new format (dict with branches)
        repositories_data = request.get("repositories", [])
        
        # Check if new format (list of objects with branches)
        if repositories_data and isinstance(repositories_data[0], dict) and "repository" in repositories_data[0]:
            # New format with per-repository branch selection
            search_all_branches = False
        elif isinstance(request, list):
            # Very old format - just a list of repo names
            repositories_data = [{"repository": repo, "branches": None} for repo in request]
            search_all_branches = False
        else:
            # Old format with search_all_branches flag
            repo_list = request.get("repositories", [])
            repositories_data = [{"repository": repo, "branches": None} for repo in repo_list]
            search_all_branches = request.get("search_all_branches", False)
        
        # Get GitHub token
        token = await GitHubService.get_github_token(db)
        if not token:
            raise HTTPException(status_code=401, detail="GitHub token not found. Please configure GITHUB_TOKEN in secrets.")
        
        # Get all templates with keywords
        templates = TemplateCRUD.get_all_templates(templates_db)
        templates_with_keywords = [t for t in templates if t.keywords]
        
        if not templates_with_keywords:
            raise HTTPException(status_code=400, detail="No templates with keywords found. Please add keywords to templates first.")
        
        # Build keyword map from templates
        keyword_to_templates = {}
        for template in templates_with_keywords:
            keywords = [k.strip().lower() for k in template.keywords.split(',')]
            for keyword in keywords:
                if keyword not in keyword_to_templates:
                    keyword_to_templates[keyword] = []
                keyword_to_templates[keyword].append({
                    "id": template.id,
                    "name": template.name,
                    "description": template.description
                })
        
        # Use optimized concurrent scanner for repositories
        results = await optimized_search.search_repositories_concurrent(
            GitHubService,
            token,
            repositories_data,
            keyword_to_templates,
            search_all_branches=search_all_branches
        )
        
        return {
            "success": True,
            "total_repositories": len(repositories_data),
            "total_templates_used": len(templates_with_keywords),
            "all_keywords": sorted(list(keyword_to_templates.keys())),
            "results": results
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error scanning repositories: {str(e)}")


# Polaris Migration Models
class PolarisConversionRequest(BaseModel):
    repository: str
    file_path: str

class PolarisConversionResponse(BaseModel):
    success: bool
    coverity_yaml: Optional[str] = None
    polaris_yaml: Optional[str] = None
    metadata: Optional[dict] = None
    error: Optional[str] = None


@app.post("/api/polaris/convert", response_model=PolarisConversionResponse)
async def convert_polaris_file(request: PolarisConversionRequest, db: Session = Depends(get_db)):
    """
    Convert polaris.yml to coverity.yaml
    """
    try:
        # Get GitHub token
        token = await GitHubService.get_github_token(db)
        if not token:
            raise HTTPException(status_code=401, detail="GitHub token not configured")
        
        # Parse repository owner and name
        parts = request.repository.split('/')
        if len(parts) != 2:
            raise HTTPException(status_code=400, detail="Invalid repository format. Expected: owner/repo")
        owner, repo_name = parts
        
        # Fetch the polaris.yml file content
        file_content = await GitHubService.get_file_content(token, owner, repo_name, request.file_path)
        
        if not file_content:
            raise HTTPException(status_code=404, detail="Polaris file not found")
        
        # Convert polaris.yml to coverity.yaml
        coverity_yaml_content, metadata, polaris_content = convert_polaris_to_coverity(file_content)
        
        return PolarisConversionResponse(
            success=True,
            coverity_yaml=coverity_yaml_content,
            polaris_yaml=polaris_content,
            metadata=metadata
        )
        
    except HTTPException:
        raise
    except Exception as e:
        return PolarisConversionResponse(
            success=False,
            error=str(e)
        )


# Pull Request Models
class CreatePullRequestRequest(BaseModel):
    repository: str
    coverity_yaml_content: str
    original_polaris_file: str

class CreatePullRequestResponse(BaseModel):
    success: bool
    pull_request_url: Optional[str] = None
    branch_name: Optional[str] = None
    error: Optional[str] = None


class ApplyToCurrentBranchRequest(BaseModel):
    repository: str
    coverity_yaml_content: str
    original_polaris_file: str

class ApplyToCurrentBranchResponse(BaseModel):
    success: bool
    commit_url: Optional[str] = None
    commit_sha: Optional[str] = None
    branch_name: Optional[str] = None
    error: Optional[str] = None


@app.post("/api/polaris/apply-to-branch", response_model=ApplyToCurrentBranchResponse)
async def apply_to_current_branch(request: ApplyToCurrentBranchRequest, db: Session = Depends(get_db)):
    """
    Apply coverity.yaml file directly to the current (default) branch of the repository
    """
    try:
        # Get GitHub token
        token = await GitHubService.get_github_token(db)
        if not token:
            raise HTTPException(status_code=401, detail="GitHub token not configured")
        
        # Parse repository owner and name
        parts = request.repository.split('/')
        if len(parts) != 2:
            raise HTTPException(status_code=400, detail="Invalid repository format. Expected: owner/repo")
        owner, repo_name = parts
        
        # Get repository default branch
        async with httpx.AsyncClient(verify=False) as client:
            headers = {
                "Authorization": f"token {token}",
                "Accept": "application/vnd.github.v3+json"
            }
            
            # Get repository info to find default branch
            repo_url = f"https://api.github.com/repos/{owner}/{repo_name}"
            repo_response = await client.get(repo_url, headers=headers)
            
            if repo_response.status_code != 200:
                raise HTTPException(status_code=404, detail="Repository not found")
            
            repo_data = repo_response.json()
            default_branch = repo_data.get('default_branch', 'main')
            
            # Create or update polaris.yaml file in the default branch
            file_path = "polaris.yaml"
            file_url = f"https://api.github.com/repos/{owner}/{repo_name}/contents/{file_path}"
            
            # Check if file already exists
            file_check_response = await client.get(
                file_url,
                headers=headers,
                params={"ref": default_branch}
            )
            
            import base64
            content_base64 = base64.b64encode(request.coverity_yaml_content.encode()).decode()
            
            commit_data = {
                "message": f"Migrate from {request.original_polaris_file} to polaris.yaml (CoP to Polaris)",
                "content": content_base64,
                "branch": default_branch
            }
            
            # If file exists, include its SHA for update
            if file_check_response.status_code == 200:
                existing_file = file_check_response.json()
                commit_data["sha"] = existing_file["sha"]
            
            # Create or update the file
            commit_response = await client.put(file_url, headers=headers, json=commit_data)
            
            if commit_response.status_code not in [200, 201]:
                error_msg = commit_response.json().get('message', 'Unknown error')
                raise HTTPException(
                    status_code=commit_response.status_code,
                    detail=f"Failed to commit file: {error_msg}"
                )
            
            result = commit_response.json()
            commit_url = result.get('commit', {}).get('html_url')
            commit_sha = result.get('commit', {}).get('sha')
            
            return ApplyToCurrentBranchResponse(
                success=True,
                commit_url=commit_url,
                commit_sha=commit_sha,
                branch_name=default_branch
            )
            
    except HTTPException:
        raise
    except Exception as e:
        return ApplyToCurrentBranchResponse(
            success=False,
            error=str(e)
        )


@app.post("/api/polaris/create-pr", response_model=CreatePullRequestResponse)
async def create_pull_request(request: CreatePullRequestRequest, db: Session = Depends(get_db)):
    """
    Create a pull request to add coverity.yaml file to the repository
    """
    try:
        # Get GitHub token
        token = await GitHubService.get_github_token(db)
        if not token:
            raise HTTPException(status_code=401, detail="GitHub token not configured")
        
        # Parse repository owner and name
        parts = request.repository.split('/')
        if len(parts) != 2:
            raise HTTPException(status_code=400, detail="Invalid repository format. Expected: owner/repo")
        owner, repo_name = parts
        
        # Create a unique branch name
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        branch_name = f"polaris-to-coverity-migration-{timestamp}"
        
        # Create the pull request using GitHub API
        pr_url = await GitHubService.create_coverity_migration_pr(
            token, owner, repo_name, branch_name, 
            request.coverity_yaml_content, request.original_polaris_file
        )
        
        return CreatePullRequestResponse(
            success=True,
            pull_request_url=pr_url,
            branch_name=branch_name
        )
        
    except HTTPException:
        raise
    except Exception as e:
        return CreatePullRequestResponse(
            success=False,
            error=str(e)
        )

class WorkflowAnalysisRequest(BaseModel):
    content: str

class RepositoryAnalysisRequest(BaseModel):
    repositories: List[str]
    analysis_type: str = "comprehensive"

@app.post("/api/ai-analyze")
async def analyze_repositories_with_blackduck(request: RepositoryAnalysisRequest, db: Session = Depends(get_db), templates_db: Session = Depends(get_templates_db)):
    """Analyze multiple repositories' workflow files using Black Duck security tools analysis (Optimized with parallel processing)"""
    try:
        import time
        start_time = time.time()
        
        results = {
            "repositories": [],
            "total_workflows": 0,
            "analysis_cost": 0.00,  # Free local analysis
            "processing_time": 0,
            "analysis_type": request.analysis_type
        }
        
        # Get GitHub token from secrets
        github_token = None
        try:
            secret = SecretCRUD.get_secret_by_name(db, "GITHUB_TOKEN")
            if secret:
                github_token = decrypt_secret(secret.encrypted_value)
        except Exception as e:
            print(f"Warning: Could not get GitHub token: {e}")
        
        if not github_token:
            raise HTTPException(status_code=400, detail="GITHUB_TOKEN secret not found or invalid")
        
        # Get all templates for duplicate detection (once, outside the loop)
        all_templates = TemplateCRUD.get_all_templates(templates_db)
        templates_for_detection = [
            {
                'id': t.id,
                'name': t.name,
                'content': t.content,
                'template_type': t.template_type or 'workflow'
            }
            for t in all_templates
        ]
        
        # Use parallel processing for repository analysis
        repo_results = await analyze_repositories_parallel(
            repositories=request.repositories,
            github_token=github_token,
            templates_for_detection=templates_for_detection
        )
        
        # Aggregate results
        for repo_result in repo_results:
            results["repositories"].append(repo_result)
            results["total_workflows"] += repo_result.get("total_workflows", 0)
        
        # Calculate processing time
        processing_time = int((time.time() - start_time) * 1000)
        results["processing_time"] = processing_time
        
        return results
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error analyzing repositories: {str(e)}")

@app.post("/api/ai-analyze-workflow")
async def analyze_workflow_with_blackduck(request: WorkflowAnalysisRequest):
    """Analyze single workflow content using Black Duck security tools analysis"""
    try:
        analyzer = LocalWorkflowAnalyzer()
        result = await analyzer.analyze_workflow(request.content, "test-workflow.yml")
        
        # Convert the result to a dictionary for JSON serialization
        return {
            "file_name": result.file_name,
            "technologies": [{"name": t.name, "type": t.type.value, "confidence": t.confidence, "evidence": t.evidence} for t in result.technologies],
            "patterns": [{"name": p.name, "category": p.category.value, "confidence": p.confidence, "evidence": p.evidence} for p in result.patterns],
            "complexity_score": result.complexity_score,
            "security_score": result.security_score,
            "modernization_score": result.modernization_score,
            "blackduck_analysis": {
                "detected_tools": [
                    {
                        "tool_type": tool.tool_type.value,
                        "is_configured": tool.is_configured,
                        "configuration_quality": tool.configuration_quality,
                        "evidence": tool.evidence,
                        "issues": tool.issues
                    } for tool in result.blackduck_analysis.detected_tools
                ],
                "package_managers": [
                    {
                        "name": pm.name,
                        "files_detected": pm.files_detected,
                        "languages": pm.languages
                    } for pm in result.blackduck_analysis.package_managers
                ],
                "binary_artifacts": result.blackduck_analysis.binary_artifacts,
                "security_gaps": [
                    {
                        "missing_tool": gap.missing_tool.value,
                        "technology_trigger": gap.technology_trigger,
                        "priority": gap.priority,
                        "reasoning": gap.reasoning
                    } for gap in result.blackduck_analysis.security_gaps
                ],
                "recommendations": result.blackduck_analysis.recommendations
            }
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error analyzing workflow: {str(e)}")


# Workflow Enhancement Models
class WorkflowEnhancementPreviewRequest(BaseModel):
    repository: str
    workflow_file_path: str
    template_id: int
    insertion_point: dict  # {location, after_job, reasoning}
    assessment_type: Optional[str] = None  # SAST, SCA, or SAST,SCA

class WorkflowEnhancementApplyRequest(BaseModel):
    repository: str
    workflow_file_path: str
    template_id: int
    insertion_point: dict
    branch_name: Optional[str] = None
    commit_message: Optional[str] = None
    method: Optional[str] = 'direct'  # 'direct' or 'pull_request'
    assessment_type: Optional[str] = None  # SAST, SCA, or SAST,SCA


def fill_template_placeholders(template_content: str, assessment_type: str = None) -> str:
    """
    Fill placeholders in template content with actual values
    Placeholders: {assessment_types}
    
    Maps assessment types to Polaris assessment_types parameter:
    - SAST -> SAST
    - SCA -> SCA
    - SAST_SCA or SAST,SCA -> SAST,SCA
    """
    if not assessment_type:
        assessment_type = "SAST"  # Default
    
    # Normalize assessment type format
    # Handle both "SAST_SCA" and "SAST,SCA" formats
    if "SAST" in assessment_type.upper() and "SCA" in assessment_type.upper():
        polaris_assessment_types = "SAST,SCA"
    elif "SAST" in assessment_type.upper():
        polaris_assessment_types = "SAST"
    elif "SCA" in assessment_type.upper():
        polaris_assessment_types = "SCA"
    else:
        polaris_assessment_types = assessment_type
    
    # Replace placeholders
    filled_content = template_content.replace("{assessment_types}", polaris_assessment_types)
    
    return filled_content


@app.post("/api/workflows/preview-enhancement")
async def preview_workflow_enhancement(request: WorkflowEnhancementPreviewRequest):
    """
    Preview what would be added to an existing workflow
    Returns before/after YAML for comparison
    """
    try:
        # Get GitHub token
        github_token = None
        try:
            db = next(get_db())
            try:
                secret = SecretCRUD.get_secret_by_name(db, "GITHUB_TOKEN")
                if secret:
                    github_token = decrypt_secret(secret.encrypted_value)
            finally:
                db.close()
        except Exception as e:
            print(f"Warning: Could not get GitHub token: {e}")
        
        if not github_token:
            raise HTTPException(status_code=400, detail="GITHUB_TOKEN secret not found or invalid")
        
        # Fetch original workflow content
        headers = {
            'Authorization': f'token {github_token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        
        workflow_url = f"https://api.github.com/repos/{request.repository}/contents/{request.workflow_file_path}"
        
        async with httpx.AsyncClient(verify=False) as client:
            response = await client.get(workflow_url, headers=headers)
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=404,
                    detail=f"Workflow file not found: {request.workflow_file_path}"
                )
            
            file_data = response.json()
            original_content = client.get(file_data['download_url'], headers=headers)
            original_workflow = (await original_content).text
        
        # Get template from database
        templates_db = next(get_templates_db())
        try:
            template = TemplateCRUD.get_template_by_id(templates_db, request.template_id)
            if not template:
                raise HTTPException(status_code=404, detail="Template not found")
            
            # Fill template placeholders with actual values
            filled_template_content = fill_template_placeholders(
                template.content, 
                request.assessment_type
            )
            
            # Check if this is a step fragment or job fragment
            parser = WorkflowParser()
            
            if template.template_type == 'step':
                # Insert step into existing job
                target_job = request.insertion_point.get('target_job')
                if not target_job:
                    raise HTTPException(
                        status_code=400, 
                        detail="target_job required in insertion_point for step fragments"
                    )
                
                insert_position = request.insertion_point.get('after_step', 'after_build')
                
                enhanced_workflow = parser.insert_step_into_job(
                    workflow_content=original_workflow,
                    step_yaml=filled_template_content,
                    target_job=target_job,
                    insert_position=insert_position
                )
                
                # Add comments explaining the enhancement
                enhanced_workflow_with_comments = parser.add_step_enhancement_comments(
                    original_yaml=original_workflow,
                    enhanced_yaml=enhanced_workflow,
                    enhancement_description=f"Added {template.name} steps to {target_job} job",
                    template_name=template.name,
                    target_job=target_job
                )
                
                return {
                    "success": True,
                    "original_workflow": original_workflow,
                    "enhanced_workflow": enhanced_workflow_with_comments,
                    "step_inserted": True,
                    "target_job": target_job,
                    "template_name": template.name,
                    "insertion_point": request.insertion_point
                }
            else:
                # Job fragment - merge as new job
                job_id = f"security-scan-{template.category}"
                
                # Merge job into workflow
                enhanced_workflow = parser.merge_job_into_workflow(
                    workflow_content=original_workflow,
                    job_yaml=filled_template_content,
                    job_id=job_id,
                    insert_after=request.insertion_point.get('after_job')
                )
                
                # Add comments explaining the enhancement
                enhanced_workflow_with_comments = parser.add_enhancement_comments(
                    original_yaml=original_workflow,
                    enhanced_yaml=enhanced_workflow,
                    enhancement_description=f"Added {job_id} job for {template.category} security scanning",
                    template_name=template.name,
                    insertion_type="job"
                )
                
                return {
                    "success": True,
                    "original_workflow": original_workflow,
                    "enhanced_workflow": enhanced_workflow_with_comments,
                    "job_id": job_id,
                    "template_name": template.name,
                    "insertion_point": request.insertion_point
                }
        finally:
            templates_db.close()
            
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error previewing enhancement: {str(e)}")


@app.post("/api/workflows/apply-enhancement")
async def apply_workflow_enhancement(request: WorkflowEnhancementApplyRequest):
    """
    Apply enhancement to an existing workflow file in the repository
    Creates a commit with the modified workflow
    """
    try:
        # Get GitHub token
        github_token = None
        try:
            db = next(get_db())
            try:
                secret = SecretCRUD.get_secret_by_name(db, "GITHUB_TOKEN")
                if secret:
                    github_token = decrypt_secret(secret.encrypted_value)
            finally:
                db.close()
        except Exception as e:
            print(f"Warning: Could not get GitHub token: {e}")
        
        if not github_token:
            raise HTTPException(status_code=400, detail="GITHUB_TOKEN secret not found or invalid")
        
        headers = {
            'Authorization': f'token {github_token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        
        # Get template
        templates_db = next(get_templates_db())
        try:
            template = TemplateCRUD.get_template_by_id(templates_db, request.template_id)
            if not template:
                raise HTTPException(status_code=404, detail="Template not found")
        finally:
            templates_db.close()
        
        async with httpx.AsyncClient(verify=False) as client:
            # 1. Get current file content and SHA
            file_url = f"https://api.github.com/repos/{request.repository}/contents/{request.workflow_file_path}"
            file_response = await client.get(file_url, headers=headers)
            
            if file_response.status_code != 200:
                raise HTTPException(
                    status_code=404,
                    detail=f"Workflow file not found: {request.workflow_file_path}"
                )
            
            file_data = file_response.json()
            file_sha = file_data['sha']
            
            # Get original content
            original_response = await client.get(file_data['download_url'], headers=headers)
            original_content = original_response.text
            
            # 2. Generate enhanced workflow
            # Fill template placeholders with actual values
            filled_template_content = fill_template_placeholders(
                template.content, 
                request.assessment_type
            )
            
            parser = WorkflowParser()
            
            # Check if this is a step fragment or job fragment
            if template.template_type == 'step':
                # Insert step into existing job
                target_job = request.insertion_point.get('target_job')
                if not target_job:
                    raise HTTPException(
                        status_code=400,
                        detail="target_job required in insertion_point for step fragments"
                    )
                
                insert_position = request.insertion_point.get('after_step', 'after_build')
                
                enhanced_content = parser.insert_step_into_job(
                    workflow_content=original_content,
                    step_yaml=filled_template_content,
                    target_job=target_job,
                    insert_position=insert_position
                )
                
                # Add comments explaining the enhancement
                enhanced_content = parser.add_step_enhancement_comments(
                    original_yaml=original_content,
                    enhanced_yaml=enhanced_content,
                    enhancement_description=f"Added {template.name} steps to {target_job} job",
                    template_name=template.name,
                    target_job=target_job
                )
                
                commit_message = request.commit_message or f"Add {template.name} step to {target_job} job"
            else:
                # Job fragment - merge as new job
                job_id = f"security-scan-{template.category}"
                enhanced_content = parser.merge_job_into_workflow(
                    workflow_content=original_content,
                    job_yaml=filled_template_content,
                    job_id=job_id,
                    insert_after=request.insertion_point.get('after_job')
                )
                
                # Add comments explaining the enhancement
                enhanced_content = parser.add_enhancement_comments(
                    original_yaml=original_content,
                    enhanced_yaml=enhanced_content,
                    enhancement_description=f"Added {job_id} job for {template.category} security scanning",
                    template_name=template.name,
                    insertion_type="job"
                )
                
                commit_message = request.commit_message or f"Add {template.name} to workflow"
            
            # 3. Prepare commit
            import base64
            encoded_content = base64.b64encode(enhanced_content.encode('utf-8')).decode('utf-8')
            
            branch = request.branch_name or 'main'
            
            # If method is pull_request, create a new branch first
            if request.method == 'pull_request':
                # Get default branch SHA
                repo_url = f"https://api.github.com/repos/{request.repository}"
                repo_response = await client.get(repo_url, headers=headers)
                default_branch = repo_response.json()['default_branch']
                
                # Get ref for default branch
                ref_url = f"https://api.github.com/repos/{request.repository}/git/ref/heads/{default_branch}"
                ref_response = await client.get(ref_url, headers=headers)
                base_sha = ref_response.json()['object']['sha']
                
                # Create new branch (check if it already exists first)
                check_branch_url = f"https://api.github.com/repos/{request.repository}/git/ref/heads/{branch}"
                check_response = await client.get(check_branch_url, headers=headers)
                
                if check_response.status_code == 404:
                    # Branch doesn't exist, create it
                    create_ref_url = f"https://api.github.com/repos/{request.repository}/git/refs"
                    create_ref_payload = {
                        "ref": f"refs/heads/{branch}",
                        "sha": base_sha
                    }
                    create_ref_response = await client.post(create_ref_url, headers=headers, json=create_ref_payload)
                    
                    if create_ref_response.status_code not in [201]:
                        raise HTTPException(
                            status_code=create_ref_response.status_code,
                            detail=f"Failed to create branch: {create_ref_response.json().get('message', 'Unknown error')}"
                        )
                elif check_response.status_code == 200:
                    # Branch already exists, update the ref to point to the latest commit
                    update_ref_url = f"https://api.github.com/repos/{request.repository}/git/refs/heads/{branch}"
                    update_ref_payload = {
                        "sha": base_sha,
                        "force": True
                    }
                    await client.patch(update_ref_url, headers=headers, json=update_ref_payload)
            
            # 4. Update file via GitHub API
            update_payload = {
                "message": commit_message,
                "content": encoded_content,
                "sha": file_sha,
                "branch": branch
            }
            
            update_response = await client.put(
                file_url,
                headers=headers,
                json=update_payload
            )
            
            if update_response.status_code not in [200, 201]:
                error_detail = update_response.json() if update_response.status_code != 404 else {"message": "Update failed"}
                raise HTTPException(
                    status_code=update_response.status_code,
                    detail=f"Failed to update workflow: {error_detail.get('message', 'Unknown error')}"
                )
            
            result = update_response.json()
            
            # 5. If pull request, create it
            pr_html_url = None
            if request.method == 'pull_request':
                pr_url = f"https://api.github.com/repos/{request.repository}/pulls"
                pr_payload = {
                    "title": commit_message,
                    "head": branch,
                    "base": repo_response.json()['default_branch'],
                    "body": f"This PR adds {template.name} security scanning to the workflow.\n\nTemplate: {template.name}\nCategory: {template.category}"
                }
                pr_response = await client.post(pr_url, headers=headers, json=pr_payload)
                
                if pr_response.status_code == 201:
                    pr_data = pr_response.json()
                    pr_html_url = pr_data['html_url']
            
            return {
                "success": True,
                "workflow_file_path": request.workflow_file_path,
                "commit_sha": result['commit']['sha'],
                "commit_html_url": result['commit']['html_url'],
                "template_name": template.name,
                "job_id": job_id,
                "pr_html_url": pr_html_url
            }
            
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()


# ==================== Workflow Duplicate Detection & Removal ====================

class DuplicateDetectionRequest(BaseModel):
    """Request to detect duplicates in workflow files"""
    repository: str
    workflow_file_path: str
    template_ids: Optional[List[int]] = None  # If None, check against all templates

class DuplicateRemovalRequest(BaseModel):
    """Request to remove duplicates from workflow files"""
    repository: str
    workflow_file_path: str
    duplicates_to_remove: List[dict]  # List of duplicate items to remove
    method: str = 'pull_request'  # 'direct' or 'pull_request'
    branch_name: Optional[str] = None
    commit_message: Optional[str] = None


@app.post("/api/workflows/detect-duplicates")
async def detect_workflow_duplicates(request: DuplicateDetectionRequest, db: Session = Depends(get_db), templates_db: Session = Depends(get_templates_db)):
    """
    Detect duplicate content between a workflow file and templates.
    Returns information about exact matches at workflow, job, and step levels.
    """
    try:
        # Get GitHub token
        github_token = None
        try:
            secret = SecretCRUD.get_secret_by_name(db, "GITHUB_TOKEN")
            if secret:
                github_token = decrypt_secret(secret.encrypted_value)
        except Exception as e:
            print(f"Warning: Could not get GitHub token: {e}")
        
        if not github_token:
            raise HTTPException(status_code=400, detail="GITHUB_TOKEN secret not found or invalid")
        
        # Fetch workflow content from GitHub
        headers = {
            'Authorization': f'token {github_token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        
        workflow_url = f"https://api.github.com/repos/{request.repository}/contents/{request.workflow_file_path}"
        
        async with httpx.AsyncClient(verify=False) as client:
            response = await client.get(workflow_url, headers=headers)
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=404,
                    detail=f"Workflow file not found: {request.workflow_file_path}"
                )
            
            file_data = response.json()
            content_response = await client.get(file_data['download_url'], headers=headers)
            workflow_content = content_response.text
        
        # Get templates to compare against
        if request.template_ids:
            templates = [TemplateCRUD.get_template_by_id(templates_db, tid) for tid in request.template_ids]
            templates = [t for t in templates if t is not None]
        else:
            templates = TemplateCRUD.get_all_templates(templates_db)
        
        if not templates:
            return {
                "success": True,
                "repository": request.repository,
                "workflow_file": request.workflow_file_path,
                "duplicates_found": False,
                "message": "No templates available for comparison"
            }
        
        # Initialize duplicate detector
        detector = DuplicateDetector()
        
        # Detect duplicates against each template
        all_duplicates = {
            "workflow_duplicates": [],
            "job_duplicates": [],
            "step_duplicates": []
        }
        
        for template in templates:
            try:
                duplicates = detector.detect_all_duplicates(
                    workflow_content=workflow_content,
                    template_content=template.content,
                    template_name=template.name,
                    template_id=template.id
                )
                
                # Aggregate results
                if duplicates["is_complete_duplicate"]:
                    all_duplicates["workflow_duplicates"].append({
                        "template_id": template.id,
                        "template_name": template.name,
                        "template_category": template.category,
                        "match_percentage": duplicates["match_percentage"],
                        "can_remove_file": True,
                        "reasoning": f"Entire workflow matches template '{template.name}'"
                    })
                
                for job_dup in duplicates["duplicate_jobs"]:
                    all_duplicates["job_duplicates"].append({
                        "template_id": template.id,
                        "template_name": template.name,
                        "job_name": job_dup["job_name"],
                        "match_percentage": job_dup["match_percentage"],
                        "can_remove": True,
                        "reasoning": f"Job '{job_dup['job_name']}' matches template '{template.name}'"
                    })
                
                for step_dup in duplicates["duplicate_steps"]:
                    all_duplicates["step_duplicates"].append({
                        "template_id": template.id,
                        "template_name": template.name,
                        "job_name": step_dup["job_name"],
                        "step_indices": step_dup["step_indices"],
                        "step_count": len(step_dup["step_indices"]),
                        "match_percentage": step_dup["match_percentage"],
                        "can_remove": True,
                        "reasoning": f"{len(step_dup['step_indices'])} steps in job '{step_dup['job_name']}' match template '{template.name}'"
                    })
                
            except Exception as e:
                print(f"Error comparing with template {template.name}: {e}")
                continue
        
        # Determine overall status
        duplicates_found = (
            len(all_duplicates["workflow_duplicates"]) > 0 or
            len(all_duplicates["job_duplicates"]) > 0 or
            len(all_duplicates["step_duplicates"]) > 0
        )
        
        return {
            "success": True,
            "repository": request.repository,
            "workflow_file": request.workflow_file_path,
            "duplicates_found": duplicates_found,
            "duplicates": all_duplicates,
            "summary": {
                "complete_workflow_matches": len(all_duplicates["workflow_duplicates"]),
                "duplicate_jobs": len(all_duplicates["job_duplicates"]),
                "duplicate_step_sequences": len(all_duplicates["step_duplicates"]),
                "total_templates_checked": len(templates)
            },
            "message": "Duplicate detection completed successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error detecting duplicates: {str(e)}")


@app.post("/api/workflows/remove-duplicates")
async def remove_workflow_duplicates(request: DuplicateRemovalRequest, db: Session = Depends(get_db)):
    """
    Remove duplicate content from a workflow file.
    Can remove entire file, specific jobs, or step sequences.
    Creates a PR or direct commit based on method.
    """
    try:
        # Get GitHub token
        github_token = None
        try:
            secret = SecretCRUD.get_secret_by_name(db, "GITHUB_TOKEN")
            if secret:
                github_token = decrypt_secret(secret.encrypted_value)
        except Exception as e:
            print(f"Warning: Could not get GitHub token: {e}")
        
        if not github_token:
            raise HTTPException(status_code=400, detail="GITHUB_TOKEN secret not found or invalid")
        
        headers = {
            'Authorization': f'token {github_token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        
        # Parse repository
        parts = request.repository.split('/')
        if len(parts) != 2:
            raise HTTPException(status_code=400, detail="Repository must be in format 'owner/repo'")
        owner, repo_name = parts
        
        # Check if we should remove the entire file
        remove_entire_file = any(
            dup.get("type") == "complete_workflow" or dup.get("can_remove_file")
            for dup in request.duplicates_to_remove
        )
        
        async with httpx.AsyncClient(verify=False) as client:
            if remove_entire_file:
                # Remove the entire workflow file
                file_url = f"https://api.github.com/repos/{request.repository}/contents/{request.workflow_file_path}"
                
                # Get file SHA
                file_response = await client.get(file_url, headers=headers)
                if file_response.status_code != 200:
                    raise HTTPException(status_code=404, detail="Workflow file not found")
                
                file_data = file_response.json()
                file_sha = file_data['sha']
                
                # Determine branch
                branch = request.branch_name or 'main'
                commit_message = request.commit_message or f"Remove duplicate workflow file {request.workflow_file_path}"
                
                # If pull request method, create a new branch
                pr_html_url = None
                if request.method == 'pull_request':
                    # Get default branch
                    repo_url = f"https://api.github.com/repos/{request.repository}"
                    repo_response = await client.get(repo_url, headers=headers)
                    default_branch = repo_response.json()['default_branch']
                    
                    # Get base SHA
                    ref_url = f"https://api.github.com/repos/{request.repository}/git/ref/heads/{default_branch}"
                    ref_response = await client.get(ref_url, headers=headers)
                    base_sha = ref_response.json()['object']['sha']
                    
                    # Create new branch
                    import datetime
                    timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
                    branch = request.branch_name or f"remove-duplicate-workflow-{timestamp}"
                    
                    create_ref_url = f"https://api.github.com/repos/{request.repository}/git/refs"
                    create_ref_payload = {
                        "ref": f"refs/heads/{branch}",
                        "sha": base_sha
                    }
                    create_ref_response = await client.post(create_ref_url, headers=headers, json=create_ref_payload)
                    
                    if create_ref_response.status_code not in [201]:
                        # Branch might already exist, try to update it
                        update_ref_url = f"https://api.github.com/repos/{request.repository}/git/refs/heads/{branch}"
                        update_ref_payload = {"sha": base_sha, "force": True}
                        await client.patch(update_ref_url, headers=headers, json=update_ref_payload)
                
                # Delete the file
                delete_payload = {
                    "message": commit_message,
                    "sha": file_sha,
                    "branch": branch
                }
                
                delete_response = await client.delete(file_url, headers=headers, json=delete_payload)
                
                if delete_response.status_code not in [200, 204]:
                    raise HTTPException(
                        status_code=delete_response.status_code,
                        detail=f"Failed to delete workflow file: {delete_response.text}"
                    )
                
                # Create PR if requested
                if request.method == 'pull_request':
                    pr_url = f"https://api.github.com/repos/{request.repository}/pulls"
                    pr_payload = {
                        "title": commit_message,
                        "head": branch,
                        "base": default_branch,
                        "body": f"This PR removes the duplicate workflow file `{request.workflow_file_path}`.\n\nThe workflow content matches existing templates and is redundant."
                    }
                    pr_response = await client.post(pr_url, headers=headers, json=pr_payload)
                    
                    if pr_response.status_code == 201:
                        pr_data = pr_response.json()
                        pr_html_url = pr_data['html_url']
                
                return {
                    "success": True,
                    "action": "file_removed",
                    "workflow_file": request.workflow_file_path,
                    "branch": branch,
                    "method": request.method,
                    "pr_url": pr_html_url,
                    "message": f"Workflow file {request.workflow_file_path} removed successfully"
                }
            
            else:
                # Partial removal - remove specific jobs or steps
                file_url = f"https://api.github.com/repos/{request.repository}/contents/{request.workflow_file_path}"
                file_response = await client.get(file_url, headers=headers)
                
                if file_response.status_code != 200:
                    raise HTTPException(status_code=404, detail="Workflow file not found")
                
                file_data = file_response.json()
                file_sha = file_data['sha']
                
                # Get original content
                content_response = await client.get(file_data['download_url'], headers=headers)
                original_content = content_response.text
                
                # Apply removals
                detector = DuplicateDetector()
                modified_content = original_content
                
                # Sort removals: jobs first, then steps
                jobs_to_remove = [d for d in request.duplicates_to_remove if d.get("type") == "job"]
                steps_to_remove = [d for d in request.duplicates_to_remove if d.get("type") == "steps"]
                
                # Remove jobs
                for job_dup in jobs_to_remove:
                    job_name = job_dup.get("job_name")
                    if job_name:
                        modified_content = detector.remove_job_from_workflow(modified_content, job_name)
                
                # Remove step sequences
                for step_dup in steps_to_remove:
                    job_name = step_dup.get("job_name")
                    step_indices = step_dup.get("step_indices", [])
                    if job_name and step_indices:
                        modified_content = detector.remove_steps_from_job(
                            modified_content, job_name, step_indices
                        )
                
                # Determine branch and commit message
                branch = request.branch_name or 'main'
                commit_message = request.commit_message or "Remove duplicate workflow content"
                
                # If pull request method, create a new branch
                pr_html_url = None
                if request.method == 'pull_request':
                    repo_url = f"https://api.github.com/repos/{request.repository}"
                    repo_response = await client.get(repo_url, headers=headers)
                    default_branch = repo_response.json()['default_branch']
                    
                    ref_url = f"https://api.github.com/repos/{request.repository}/git/ref/heads/{default_branch}"
                    ref_response = await client.get(ref_url, headers=headers)
                    base_sha = ref_response.json()['object']['sha']
                    
                    import datetime
                    timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
                    branch = request.branch_name or f"remove-duplicates-{timestamp}"
                    
                    create_ref_url = f"https://api.github.com/repos/{request.repository}/git/refs"
                    create_ref_payload = {
                        "ref": f"refs/heads/{branch}",
                        "sha": base_sha
                    }
                    create_ref_response = await client.post(create_ref_url, headers=headers, json=create_ref_payload)
                    
                    if create_ref_response.status_code not in [201]:
                        # Branch might already exist, try to update it
                        update_ref_url = f"https://api.github.com/repos/{request.repository}/git/refs/heads/{branch}"
                        update_ref_payload = {"sha": base_sha, "force": True}
                        await client.patch(update_ref_url, headers=headers, json=update_ref_payload)
                
                # Update file with modified content
                import base64
                encoded_content = base64.b64encode(modified_content.encode('utf-8')).decode('utf-8')
                
                update_payload = {
                    "message": commit_message,
                    "content": encoded_content,
                    "sha": file_sha,
                    "branch": branch
                }
                
                update_response = await client.put(file_url, headers=headers, json=update_payload)
                
                if update_response.status_code not in [200, 201]:
                    raise HTTPException(
                        status_code=update_response.status_code,
                        detail=f"Failed to update workflow file: {update_response.text}"
                    )
                
                # Create PR if requested
                if request.method == 'pull_request':
                    pr_url = f"https://api.github.com/repos/{request.repository}/pulls"
                    pr_payload = {
                        "title": commit_message,
                        "head": branch,
                        "base": default_branch,
                        "body": f"This PR removes duplicate content from `{request.workflow_file_path}`.\n\nRemoved {len(jobs_to_remove)} duplicate jobs and {len(steps_to_remove)} duplicate step sequences."
                    }
                    pr_response = await client.post(pr_url, headers=headers, json=pr_payload)
                    
                    if pr_response.status_code == 201:
                        pr_data = pr_response.json()
                        pr_html_url = pr_data['html_url']
                
                return {
                    "success": True,
                    "action": "content_modified",
                    "workflow_file": request.workflow_file_path,
                    "branch": branch,
                    "method": request.method,
                    "pr_url": pr_html_url,
                    "jobs_removed": len(jobs_to_remove),
                    "step_sequences_removed": len(steps_to_remove),
                    "message": f"Duplicate content removed from {request.workflow_file_path}"
                }
                
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error removing duplicates: {str(e)}")


@app.get("/api/metrics/dashboard")
async def get_dashboard_metrics():
    """Get dashboard metrics for visualization"""
    try:
        # This is a placeholder - you can extend this with actual data from your database
        # For now, returning mock data structure that the frontend expects
        return {
            "scanMetrics": {
                "totalRepos": 0,
                "scannedRepos": 0,
                "workflowsFound": 0,
                "lastScanDate": None
            },
            "workflowTypes": [
                {"name": "Black Duck", "count": 0},
                {"name": "Coverity", "count": 0},
                {"name": "Polaris", "count": 0},
                {"name": "SRM", "count": 0}
            ],
            "migrationStats": {
                "completed": 0,
                "failed": 0,
                "inProgress": 0,
                "pending": 0
            },
            "recentActivity": [],
            "healthScore": {
                "secretsConfigured": True,
                "ssoEnabled": 0,
                "totalOrgs": 0
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching metrics: {str(e)}")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)