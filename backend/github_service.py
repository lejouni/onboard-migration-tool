import asyncio
import httpx
import os
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from secrets_crud import SecretCRUD
from datetime import datetime, timedelta
from workflow_analyzer import LocalWorkflowAnalyzer

class RepositoryCache:
    """Simple in-memory cache for repository data"""
    def __init__(self):
        self.cache = {}
        self.cache_ttl = timedelta(minutes=10)  # Cache for 10 minutes
    
    def get(self, key: str) -> Optional[Dict]:
        """Get cached data if not expired"""
        if key in self.cache:
            entry = self.cache[key]
            if datetime.now() - entry['timestamp'] < self.cache_ttl:
                return entry['data']
            else:
                # Expired, remove it
                del self.cache[key]
        return None
    
    def set(self, key: str, data: List[Dict]):
        """Cache the data"""
        self.cache[key] = {
            'data': data,
            'timestamp': datetime.now()
        }
    
    def clear(self):
        """Clear all cached data"""
        self.cache = {}

class GitHubService:
    """Service for interacting with GitHub API"""
    
    BASE_URL = os.getenv('GITHUB_API_URL', 'https://api.github.com')
    _repo_cache = RepositoryCache()  # Shared cache instance
    
    @staticmethod
    def get_base_url(db: Session = None) -> str:
        """Get GitHub API base URL from environment variable (default: https://api.github.com)"""
        # Always use environment variable or default - no database lookup
        return os.getenv('GITHUB_API_URL', 'https://api.github.com')
    
    @staticmethod
    def get_http_client() -> httpx.AsyncClient:
        """Create an HTTP client with proper SSL configuration"""
        # Temporary SSL fix for development environments
        # In production, you should use verify=True with proper certificates
        return httpx.AsyncClient(
            verify=False,  # Temporarily disable SSL verification for development
            timeout=30.0,  # Set timeout
            follow_redirects=True
        )
    
    @staticmethod
    def is_sso_error(error_message: str) -> bool:
        """Check if error is related to SSO enforcement"""
        sso_keywords = [
            "protected by organization SAML enforcement",
            "SAML",
            "SSO",
            "single sign-on",
            "organization requires members to enable",
            "must grant your Personal Access token access to this organization"
        ]
        return any(keyword.lower() in error_message.lower() for keyword in sso_keywords)
    
    @staticmethod
    def get_sso_error_message(org_name: str = None) -> str:
        """Get helpful SSO error message"""
        base_msg = "This organization requires SAML SSO authorization. "
        steps = (
            "To authorize your token:\n"
            "1. Go to https://github.com/settings/tokens\n"
            "2. Find your token and click 'Configure SSO'\n"
            "3. Click 'Authorize' for the organization\n"
            "4. Complete the SSO authentication flow"
        )
        if org_name:
            return f"{base_msg}Organization: {org_name}\n\n{steps}"
        return f"{base_msg}\n\n{steps}"
    
    @staticmethod
    async def get_github_token(db: Session) -> Optional[str]:
        """Get GITHUB_TOKEN from secrets storage"""
        try:
            secret = SecretCRUD.get_secret_by_name(db, "GITHUB_TOKEN")
            if secret:
                return SecretCRUD.decrypt_secret_value(secret)
            return None
        except Exception as e:
            print(f"Error getting GitHub token: {e}")
            return None
    
    @staticmethod
    async def get_user_info(token: str) -> Dict:
        """Get authenticated user information"""
        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Backend-App/1.0"
        }
        
        async with GitHubService.get_http_client() as client:
            response = await client.get(f"{GitHubService.BASE_URL}/user", headers=headers)
            response.raise_for_status()
            return response.json()
    
    @staticmethod
    async def get_token_scopes(token: str) -> List[str]:
        """Get the scopes for the current token"""
        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Backend-App/1.0"
        }
        
        async with GitHubService.get_http_client() as client:
            response = await client.get(f"{GitHubService.BASE_URL}/user", headers=headers)
            response.raise_for_status()
            # GitHub returns scopes in the X-OAuth-Scopes header
            scopes_header = response.headers.get('X-OAuth-Scopes', '')
            return [scope.strip() for scope in scopes_header.split(',') if scope.strip()]
    
    @staticmethod
    async def get_user_organizations(token: str) -> List[Dict]:
        """Get organizations for the authenticated user"""
        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Backend-App/1.0"
        }
        
        organizations = []
        page = 1
        per_page = 100
        
        async with GitHubService.get_http_client() as client:
            while True:
                response = await client.get(
                    f"{GitHubService.BASE_URL}/user/orgs",
                    headers=headers,
                    params={"page": page, "per_page": per_page}
                )
                response.raise_for_status()
                
                orgs_page = response.json()
                if not orgs_page:
                    break
                
                organizations.extend(orgs_page)
                page += 1
                
                # GitHub API returns less than per_page items on the last page
                if len(orgs_page) < per_page:
                    break
        
        return organizations
    
    @staticmethod
    async def get_organization_details(token: str, org_name: str) -> Dict:
        """Get detailed information about a specific organization"""
        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Backend-App/1.0"
        }
        
        async with GitHubService.get_http_client() as client:
            response = await client.get(
                f"{GitHubService.BASE_URL}/orgs/{org_name}",
                headers=headers
            )
            
            # Check for SSO errors before raising status
            if response.status_code == 403:
                error_text = response.text
                if GitHubService.is_sso_error(error_text):
                    raise Exception(GitHubService.get_sso_error_message(org_name))
            
            response.raise_for_status()
            return response.json()
    
    @staticmethod
    async def get_organization_repositories(token: str, org_name: str) -> List[Dict]:
        """Get repositories for a specific organization with language details"""
        # Check cache first
        cache_key = f"org:{org_name}"
        cached_data = GitHubService._repo_cache.get(cache_key)
        if cached_data is not None:
            return cached_data
        
        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Backend-App/1.0"
        }
        
        repositories = []
        per_page = 100
        
        async with GitHubService.get_http_client() as client:
            # Only fetch first page for faster response (we'll only detail 10 repos anyway)
            response = await client.get(
                f"{GitHubService.BASE_URL}/orgs/{org_name}/repos",
                headers=headers,
                params={"page": 1, "per_page": per_page, "sort": "updated", "direction": "desc"}
            )
            
            # Check for SSO errors before raising status
            if response.status_code == 403:
                error_text = response.text
                if GitHubService.is_sso_error(error_text):
                    raise Exception(GitHubService.get_sso_error_message(org_name))
            
            response.raise_for_status()
            repositories = response.json()
        
        # Only fetch detailed info for the first 10 repositories to speed up response
        # Users can view details for specific repos individually
        repos_to_fetch_languages = repositories[:10] if repositories else []
        repos_without_languages = repositories[10:] if len(repositories) > 10 else []
        
        if repos_to_fetch_languages:
            # Limit concurrent requests to avoid overwhelming the API
            max_concurrent = 3  # Reduced for more API calls per repo
            semaphore = asyncio.Semaphore(max_concurrent)
            
            async def fetch_repo_details(repo):
                async with semaphore:
                    async with GitHubService.get_http_client() as client:
                        try:
                            owner = repo.get("owner", {}).get("login")
                            repo_name = repo.get("name")
                            if owner and repo_name:
                                # Fetch languages
                                lang_response = await client.get(
                                    f"{GitHubService.BASE_URL}/repos/{owner}/{repo_name}/languages",
                                    headers=headers
                                )
                                if lang_response.status_code == 200:
                                    languages = lang_response.json()
                                    repo["languages_detail"] = languages
                                else:
                                    repo["languages_detail"] = {}
                                
                                # Fetch workflow files info
                                try:
                                    workflows_response = await client.get(
                                        f"{GitHubService.BASE_URL}/repos/{owner}/{repo_name}/contents/.github/workflows",
                                        headers=headers
                                    )
                                    if workflows_response.status_code == 200:
                                        workflows_data = workflows_response.json()
                                        workflow_files = []
                                        
                                        for item in workflows_data:
                                            if item.get("type") == "file" and item.get("name", "").endswith((".yml", ".yaml")):
                                                workflow_files.append({
                                                    "name": item.get("name"),
                                                    "path": item.get("path"),
                                                    "size": item.get("size"),
                                                    "sha": item.get("sha")
                                                })
                                        
                                        repo["workflow_info"] = {
                                            "workflow_files": workflow_files,
                                            "total_count": len(workflow_files),
                                            "has_workflows": len(workflow_files) > 0
                                        }
                                    else:
                                        repo["workflow_info"] = {
                                            "workflow_files": [],
                                            "total_count": 0,
                                            "has_workflows": False
                                        }
                                except Exception:
                                    repo["workflow_info"] = {
                                        "workflow_files": [],
                                        "total_count": 0,
                                        "has_workflows": False
                                    }
                                
                                # Check for polaris files in root
                                try:
                                    root_response = await client.get(
                                        f"{GitHubService.BASE_URL}/repos/{owner}/{repo_name}/contents/",
                                        headers=headers
                                    )
                                    if root_response.status_code == 200:
                                        root_data = root_response.json()
                                        polaris_files = [
                                            item for item in root_data 
                                            if item.get("type") == "file" and item.get("name") in ["polaris.yml", "polaris.yaml"]
                                        ]
                                        if not repo.get("workflow_info"):
                                            repo["workflow_info"] = {
                                                "workflow_files": [],
                                                "total_count": 0,
                                                "has_workflows": False
                                            }
                                        repo["workflow_info"]["has_polaris_in_root"] = len(polaris_files) > 0
                                        # Add polaris files to workflow_files list
                                        for pf in polaris_files:
                                            repo["workflow_info"]["workflow_files"].append({
                                                "name": pf.get("name"),
                                                "path": pf.get("name"),
                                                "size": pf.get("size", 0),
                                                "sha": pf.get("sha", "")
                                            })
                                except Exception:
                                    if not repo.get("workflow_info"):
                                        repo["workflow_info"] = {
                                            "workflow_files": [],
                                            "total_count": 0,
                                            "has_workflows": False
                                        }
                                    repo["workflow_info"]["has_polaris_in_root"] = False
                            else:
                                repo["languages_detail"] = {}
                                repo["workflow_info"] = {
                                    "workflow_files": [],
                                    "total_count": 0,
                                    "has_workflows": False,
                                    "has_polaris_in_root": False
                                }
                        except Exception as e:
                            print(f"Could not fetch details for {repo.get('full_name', 'unknown')}: {e}")
                            repo["languages_detail"] = {}
                            repo["workflow_info"] = {
                                "workflow_files": [],
                                "total_count": 0,
                                "has_workflows": False,
                                "has_polaris_in_root": False
                            }
                        return repo
            
            # Fetch details for the first batch of repositories
            try:
                repos_with_details = await asyncio.gather(*[fetch_repo_details(repo) for repo in repos_to_fetch_languages], return_exceptions=True)
                # Filter out any exceptions and keep valid repositories
                repos_with_details = [repo for repo in repos_with_details if not isinstance(repo, Exception)]
            except Exception as e:
                print(f"Error fetching repo details: {e}")
                # Fallback: set empty details for first batch
                for repo in repos_to_fetch_languages:
                    repo["languages_detail"] = {}
                    repo["workflow_info"] = {
                        "workflow_files": [],
                        "total_count": 0,
                        "has_workflows": False,
                        "has_polaris_in_root": False
                    }
                repos_with_details = repos_to_fetch_languages
        else:
            repos_with_details = []
        
        # Set empty details for remaining repositories
        for repo in repos_without_languages:
            repo["languages_detail"] = {}
            repo["workflow_info"] = {
                "workflow_files": [],
                "total_count": 0,
                "has_workflows": False,
                "has_polaris_in_root": False
            }
        
        # Combine both lists
        all_repositories = repos_with_details + repos_without_languages
        
        # Cache the result
        GitHubService._repo_cache.set(cache_key, all_repositories)
        
        return all_repositories
    
    @staticmethod
    async def get_organization_secrets(token: str, org_name: str) -> List[Dict]:
        """Get organization secrets (only names, not values)"""
        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Backend-App/1.0"
        }
        
        try:
            async with GitHubService.get_http_client() as client:
                response = await client.get(
                    f"{GitHubService.BASE_URL}/orgs/{org_name}/actions/secrets",
                    headers=headers
                )
                if response.status_code == 200:
                    data = response.json()
                    return data.get("secrets", [])
                else:
                    print(f"Could not fetch organization secrets: {response.status_code}")
                    return []
        except Exception as e:
            print(f"Error fetching organization secrets: {e}")
            return []
    
    @staticmethod
    async def get_organization_custom_properties(token: str, org_name: str) -> List[Dict]:
        """Get organization custom properties schema"""
        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "Backend-App/1.0"
        }
        
        try:
            async with GitHubService.get_http_client() as client:
                response = await client.get(
                    f"{GitHubService.BASE_URL}/orgs/{org_name}/properties/schema",
                    headers=headers
                )
                if response.status_code == 200:
                    return response.json()
                else:
                    print(f"Could not fetch organization custom properties: {response.status_code}")
                    return []
        except Exception as e:
            print(f"Error fetching organization custom properties: {e}")
            return []
    
    @staticmethod
    async def get_organization_variables(token: str, org_name: str) -> List[Dict]:
        """Get organization variables (names and values)"""
        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "Backend-App/1.0"
        }
        
        try:
            async with GitHubService.get_http_client() as client:
                response = await client.get(
                    f"{GitHubService.BASE_URL}/orgs/{org_name}/actions/variables",
                    headers=headers
                )
                if response.status_code == 200:
                    data = response.json()
                    return data.get('variables', [])
                else:
                    print(f"Could not fetch organization variables: {response.status_code}")
                    return []
        except Exception as e:
            print(f"Error fetching organization variables: {e}")
            return []
    
    @staticmethod
    async def get_user_repositories(token: str) -> List[Dict]:
        """Get all repositories the authenticated user has access to with language details"""
        # Check cache first
        cache_key = "user:repos"
        cached_data = GitHubService._repo_cache.get(cache_key)
        if cached_data is not None:
            return cached_data
        
        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Backend-App/1.0"
        }
        
        repositories = []
        per_page = 100

        async with GitHubService.get_http_client() as client:
            # Only fetch first page for faster response (we'll only detail first N repos)
            response = await client.get(
                f"{GitHubService.BASE_URL}/user/repos",
                headers=headers,
                params={
                    "page": 1,
                    "per_page": per_page,
                    "sort": "updated",
                    "direction": "desc",
                    "affiliation": "owner,collaborator,organization_member"
                }
            )
            response.raise_for_status()
            repositories = response.json()
        
        # Only fetch detailed info for the first 10 repositories to speed up response
        # Users can view details for specific repos individually
        repos_to_fetch_languages = repositories[:10] if repositories else []
        repos_without_languages = repositories[10:] if len(repositories) > 10 else []
        
        if repos_to_fetch_languages:
            # Limit concurrent requests to avoid overwhelming the API
            max_concurrent = 3  # Reduced for more API calls per repo
            semaphore = asyncio.Semaphore(max_concurrent)
            
            async def fetch_repo_details_user(repo):
                async with semaphore:
                    async with GitHubService.get_http_client() as client:
                        try:
                            owner = repo.get("owner", {}).get("login")
                            repo_name = repo.get("name")
                            if owner and repo_name:
                                # Fetch languages
                                lang_response = await client.get(
                                    f"{GitHubService.BASE_URL}/repos/{owner}/{repo_name}/languages",
                                    headers=headers
                                )
                                if lang_response.status_code == 200:
                                    languages = lang_response.json()
                                    repo["languages_detail"] = languages
                                else:
                                    repo["languages_detail"] = {}
                                
                                # Fetch workflow files info
                                try:
                                    workflows_response = await client.get(
                                        f"{GitHubService.BASE_URL}/repos/{owner}/{repo_name}/contents/.github/workflows",
                                        headers=headers
                                    )
                                    if workflows_response.status_code == 200:
                                        workflows_data = workflows_response.json()
                                        workflow_files = []
                                        
                                        for item in workflows_data:
                                            if item.get("type") == "file" and item.get("name", "").endswith((".yml", ".yaml")):
                                                workflow_files.append({
                                                    "name": item.get("name"),
                                                    "path": item.get("path"),
                                                    "size": item.get("size"),
                                                    "sha": item.get("sha")
                                                })
                                        
                                        repo["workflow_info"] = {
                                            "workflow_files": workflow_files,
                                            "total_count": len(workflow_files),
                                            "has_workflows": len(workflow_files) > 0
                                        }
                                    else:
                                        repo["workflow_info"] = {
                                            "workflow_files": [],
                                            "total_count": 0,
                                            "has_workflows": False
                                        }
                                except Exception:
                                    repo["workflow_info"] = {
                                        "workflow_files": [],
                                        "total_count": 0,
                                        "has_workflows": False
                                    }
                                
                                # Check for polaris files in root
                                try:
                                    root_response = await client.get(
                                        f"{GitHubService.BASE_URL}/repos/{owner}/{repo_name}/contents/",
                                        headers=headers
                                    )
                                    if root_response.status_code == 200:
                                        root_data = root_response.json()
                                        polaris_files = [
                                            item for item in root_data 
                                            if item.get("type") == "file" and item.get("name") in ["polaris.yml", "polaris.yaml"]
                                        ]
                                        if not repo.get("workflow_info"):
                                            repo["workflow_info"] = {
                                                "workflow_files": [],
                                                "total_count": 0,
                                                "has_workflows": False
                                            }
                                        repo["workflow_info"]["has_polaris_in_root"] = len(polaris_files) > 0
                                        # Add polaris files to workflow_files list
                                        for pf in polaris_files:
                                            repo["workflow_info"]["workflow_files"].append({
                                                "name": pf.get("name"),
                                                "path": pf.get("name"),
                                                "size": pf.get("size", 0),
                                                "sha": pf.get("sha", "")
                                            })
                                except Exception:
                                    if not repo.get("workflow_info"):
                                        repo["workflow_info"] = {
                                            "workflow_files": [],
                                            "total_count": 0,
                                            "has_workflows": False
                                        }
                                    repo["workflow_info"]["has_polaris_in_root"] = False
                            else:
                                repo["languages_detail"] = {}
                                repo["workflow_info"] = {
                                    "workflow_files": [],
                                    "total_count": 0,
                                    "has_workflows": False,
                                    "has_polaris_in_root": False
                                }
                        except Exception as e:
                            print(f"Could not fetch details for {repo.get('full_name', 'unknown')}: {e}")
                            repo["languages_detail"] = {}
                            repo["workflow_info"] = {
                                "workflow_files": [],
                                "total_count": 0,
                                "has_workflows": False,
                                "has_polaris_in_root": False
                            }
                        return repo
            
            # Fetch details for the first batch of repositories
            try:
                repos_with_details = await asyncio.gather(*[fetch_repo_details_user(repo) for repo in repos_to_fetch_languages], return_exceptions=True)
                # Filter out any exceptions and keep valid repositories
                repos_with_details = [repo for repo in repos_with_details if not isinstance(repo, Exception)]
            except Exception as e:
                print(f"Error fetching repo details: {e}")
                # Fallback: set empty details for first batch
                for repo in repos_to_fetch_languages:
                    repo["languages_detail"] = {}
                    repo["workflow_info"] = {
                        "workflow_files": [],
                        "total_count": 0,
                        "has_workflows": False,
                        "has_polaris_in_root": False
                    }
                repos_with_details = repos_to_fetch_languages
        else:
            repos_with_details = []
        
        # Set empty details for remaining repositories
        for repo in repos_without_languages:
            repo["languages_detail"] = {}
            repo["workflow_info"] = {
                "workflow_files": [],
                "total_count": 0,
                "has_workflows": False,
                "has_polaris_in_root": False
            }
        
        # Combine both lists
        all_repositories = repos_with_details + repos_without_languages
        
        # Cache the result
        GitHubService._repo_cache.set(cache_key, all_repositories)
        
        return all_repositories
    
    @staticmethod
    async def get_repository_details(token: str, owner: str, repo_name: str) -> Dict:
        """Get detailed information about a specific repository including custom properties"""
        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Backend-App/1.0"
        }
        
        try:
            async with GitHubService.get_http_client() as client:
                # Get basic repository information
                repo_response = await client.get(
                    f"{GitHubService.BASE_URL}/repos/{owner}/{repo_name}",
                    headers=headers
                )
                
                print(f"Repository details request for {owner}/{repo_name}: HTTP {repo_response.status_code}")
                
                if repo_response.status_code == 404:
                    print(f"Repository {owner}/{repo_name} not found - it may not exist or you may not have access")
                    # Check token scopes directly to provide helpful error message
                    try:
                        # Make a simple API call to check scopes from headers
                        scope_check_response = await client.get(f"{GitHubService.BASE_URL}/user", headers=headers)
                        if scope_check_response.status_code == 200:
                            scopes_header = scope_check_response.headers.get('X-OAuth-Scopes', '')
                            scopes = [scope.strip() for scope in scopes_header.split(',') if scope.strip()]
                            has_repo_scope = "repo" in scopes
                            has_public_repo_scope = "public_repo" in scopes
                            
                            print(f"Token scopes: {scopes}")
                            
                            if not has_repo_scope and not has_public_repo_scope:
                                raise ValueError(f"Repository {owner}/{repo_name} not found. Your GitHub token may not have the required scopes. Current scopes: {', '.join(scopes) if scopes else 'none'}. You need 'repo' scope for private repositories or 'public_repo' for public repositories.")
                            elif not has_repo_scope:
                                raise ValueError(f"Repository {owner}/{repo_name} not found. This may be a private repository and your token only has 'public_repo' scope. You need 'repo' scope for private repositories.")
                            else:
                                raise ValueError(f"Repository {owner}/{repo_name} not found. Your token has sufficient permissions ('repo' scope), so this repository may not exist, may have been deleted, or may have been moved/renamed.")
                        else:
                            raise ValueError(f"Repository {owner}/{repo_name} not found")
                    except ValueError:
                        # Re-raise ValueError as-is
                        raise
                    except Exception as scope_error:
                        print(f"Could not check token scopes: {scope_error}")
                        raise ValueError(f"Repository {owner}/{repo_name} not found")
                elif repo_response.status_code == 403:
                    print(f"Access denied to repository {owner}/{repo_name}")
                    raise ValueError(f"Access denied to repository {owner}/{repo_name}")
                elif repo_response.status_code != 200:
                    print(f"Failed to fetch repository {owner}/{repo_name}: HTTP {repo_response.status_code}")
                    raise ValueError(f"Failed to fetch repository details: HTTP {repo_response.status_code}")
                
                repo_data = repo_response.json()
                
                # Make all additional requests concurrently to avoid client closure issues
                async def fetch_custom_properties():
                    try:
                        properties_headers = {
                            **headers,
                            "Accept": "application/vnd.github+json"
                        }
                        props_response = await client.get(
                            f"{GitHubService.BASE_URL}/repos/{owner}/{repo_name}/properties/values",
                            headers=properties_headers
                        )
                        if props_response.status_code == 200:
                            return props_response.json()
                    except Exception as e:
                        print(f"Could not fetch custom properties: {e}")
                    return {}

                async def fetch_languages():
                    try:
                        lang_response = await client.get(
                            f"{GitHubService.BASE_URL}/repos/{owner}/{repo_name}/languages",
                            headers=headers
                        )
                        if lang_response.status_code == 200:
                            return lang_response.json()
                        else:
                            return {}
                    except Exception as e:
                        print(f"Could not fetch languages: {e}")
                    return {}

                async def fetch_topics():
                    try:
                        topics_headers = {
                            **headers,
                            "Accept": "application/vnd.github.mercy-preview+json"
                        }
                        topics_response = await client.get(
                            f"{GitHubService.BASE_URL}/repos/{owner}/{repo_name}/topics",
                            headers=topics_headers
                        )
                        if topics_response.status_code == 200:
                            topics_data = topics_response.json()
                            return topics_data.get("names", [])
                    except Exception as e:
                        print(f"Could not fetch topics: {e}")
                    return []

                async def fetch_latest_release():
                    try:
                        release_response = await client.get(
                            f"{GitHubService.BASE_URL}/repos/{owner}/{repo_name}/releases/latest",
                            headers=headers
                        )
                        if release_response.status_code == 200:
                            return release_response.json()
                    except Exception as e:
                        print(f"Could not fetch latest release: {e}")
                    return None

                async def fetch_branches():
                    try:
                        # Fetch repository branches
                        branches = await GitHubService.get_repository_branches(token, owner, repo_name)
                        return branches
                    except Exception as e:
                        print(f"Could not fetch branches: {e}")
                        return []

                async def fetch_workflow_files():
                    try:
                        # First, check if the .github/workflows directory exists
                        workflows_response = await client.get(
                            f"{GitHubService.BASE_URL}/repos/{owner}/{repo_name}/contents/.github/workflows",
                            headers=headers
                        )
                        if workflows_response.status_code == 200:
                            workflows_data = workflows_response.json()
                            workflow_files = []
                            
                            # Process workflow files
                            for item in workflows_data:
                                if item.get("type") == "file" and item.get("name", "").endswith((".yml", ".yaml")):
                                    workflow_info = {
                                        "name": item.get("name"),
                                        "path": item.get("path"),
                                        "size": item.get("size"),
                                        "download_url": item.get("download_url"),
                                        "html_url": item.get("html_url"),
                                        "sha": item.get("sha")
                                    }
                                    workflow_files.append(workflow_info)
                            
                            return {
                                "workflow_files": workflow_files,
                                "total_count": len(workflow_files),
                                "has_workflows": len(workflow_files) > 0
                            }
                        elif workflows_response.status_code == 404:
                            # No .github/workflows directory
                            return {
                                "workflow_files": [],
                                "total_count": 0,
                                "has_workflows": False,
                                "note": "No .github/workflows directory found"
                            }
                        else:
                            print(f"Could not fetch workflows: HTTP {workflows_response.status_code}")
                            return {
                                "workflow_files": [],
                                "total_count": 0,
                                "has_workflows": False,
                                "error": f"HTTP {workflows_response.status_code}"
                            }
                    except Exception as e:
                        print(f"Could not fetch workflow files: {e}")
                        return {
                            "workflow_files": [],
                            "total_count": 0,
                            "has_workflows": False,
                            "error": str(e)
                        }

                # Execute all requests concurrently
                results = await asyncio.gather(
                    fetch_custom_properties(),
                    fetch_languages(),
                    fetch_topics(),
                    fetch_latest_release(),
                    fetch_workflow_files(),
                    fetch_branches(),
                    return_exceptions=True
                )
                
                # Handle results, replacing exceptions with default values
                custom_properties_raw = results[0] if not isinstance(results[0], Exception) else {}
                languages = results[1] if not isinstance(results[1], Exception) else {}
                topics = results[2] if not isinstance(results[2], Exception) else []
                latest_release = results[3] if not isinstance(results[3], Exception) else None
                workflow_data = results[4] if not isinstance(results[4], Exception) else {
                    "workflow_files": [],
                    "total_count": 0,
                    "has_workflows": False,
                    "error": "Failed to fetch"
                }
                branches = results[5] if not isinstance(results[5], Exception) else []
                
                # Transform custom properties from GitHub API format to key-value pairs
                custom_properties = {}
                if custom_properties_raw and isinstance(custom_properties_raw, list):
                    for prop in custom_properties_raw:
                        if isinstance(prop, dict) and "property_name" in prop and "value" in prop:
                            custom_properties[prop["property_name"]] = prop["value"]
                elif isinstance(custom_properties_raw, dict):
                    custom_properties = custom_properties_raw
            
            # Combine all data
            detailed_repo = {
                **repo_data,
                "custom_properties": custom_properties,
                "languages_detail": languages,
                "topics_list": topics,
                "latest_release": latest_release,
                "workflow_info": workflow_data,
                "branches": branches
            }
            
            return detailed_repo
            
        except ValueError as e:
            # Re-raise ValueError with clear message
            raise e
        except httpx.HTTPStatusError as e:
            print(f"HTTP error getting repository details: {e.response.status_code} - {e.response.text}")
            raise ValueError(f"GitHub API error: {e.response.status_code}")
        except httpx.RequestError as e:
            print(f"Network error getting repository details: {e}")
            raise ValueError(f"Network error: {str(e)}")
        except Exception as e:
            print(f"Unexpected error getting repository details: {e}")
            raise ValueError(f"Unexpected error: {str(e)}")
    
    @staticmethod
    async def verify_token(token: str) -> bool:
        """Verify if the GitHub token is valid"""
        try:
            await GitHubService.get_user_info(token)
            return True
        except httpx.HTTPStatusError as e:
            print(f"HTTP error verifying token: {e.response.status_code} - {e.response.text}")
            return False
        except httpx.RequestError as e:
            print(f"Network error verifying token: {e}")
            return False
        except Exception as e:
            print(f"Unexpected error verifying token: {e}")
            return False
    
    @staticmethod
    def format_organization(org: Dict) -> Dict:
        """Format organization data for API response"""
        return {
            "id": org.get("id"),
            "login": org.get("login"),
            "name": org.get("name"),
            "description": org.get("description"),
            "avatar_url": org.get("avatar_url"),
            "html_url": org.get("html_url"),
            "public_repos": org.get("public_repos"),
            "followers": org.get("followers"),
            "following": org.get("following"),
            "created_at": org.get("created_at"),
            "updated_at": org.get("updated_at"),
            "location": org.get("location"),
            "email": org.get("email"),
            "blog": org.get("blog"),
            "company": org.get("company")
        }
    
    @staticmethod
    def format_repository(repo: Dict) -> Dict:
        """Format repository data for API response"""
        return {
            "id": repo.get("id"),
            "name": repo.get("name"),
            "full_name": repo.get("full_name"),
            "description": repo.get("description"),
            "html_url": repo.get("html_url"),
            "clone_url": repo.get("clone_url"),
            "ssh_url": repo.get("ssh_url"),
            "language": repo.get("language"),
            "languages_detail": repo.get("languages_detail", {}),
            "stargazers_count": repo.get("stargazers_count"),
            "watchers_count": repo.get("watchers_count"),
            "forks_count": repo.get("forks_count"),
            "open_issues_count": repo.get("open_issues_count"),
            "private": repo.get("private"),
            "fork": repo.get("fork"),
            "archived": repo.get("archived"),
            "disabled": repo.get("disabled"),
            "created_at": repo.get("created_at"),
            "updated_at": repo.get("updated_at"),
            "pushed_at": repo.get("pushed_at"),
            "size": repo.get("size"),
            "default_branch": repo.get("default_branch"),
            "topics": repo.get("topics", []),
            "license": repo.get("license", {}).get("name") if repo.get("license") else None,
            "workflow_info": repo.get("workflow_info", {
                "workflow_files": [],
                "total_count": 0,
                "has_workflows": False,
                "has_polaris_in_root": False
            })
        }
    
    @staticmethod
    def _find_containing_block(lines, matching_line_index):
        """
        Find the containing job or step for a line that matches the search term.
        Returns the complete block (job or step) information.
        """
        if matching_line_index < 0 or matching_line_index >= len(lines):
            return None
        
        # Get the indentation level of the matching line
        matching_line = lines[matching_line_index]
        matching_indent = len(matching_line) - len(matching_line.lstrip())
        
        # Walk backwards to find the start of the current block
        current_line_idx = matching_line_index
        block_start_idx = matching_line_index
        block_type = "unknown"
        block_name = "unnamed"
        
        # Look for job or step definitions by walking up
        while current_line_idx >= 0:
            line = lines[current_line_idx]
            stripped_line = line.strip()
            line_indent = len(line) - len(line.lstrip())
            
            # Skip empty lines and comments
            if not stripped_line or stripped_line.startswith('#'):
                current_line_idx -= 1
                continue
            
            # If we find a line with less indentation, it might be our block start
            if line_indent < matching_indent or line_indent == 0:
                # Check if this looks like a job definition
                if stripped_line.startswith('jobs:') or (
                    ':' in stripped_line and 
                    not stripped_line.startswith('-') and
                    current_line_idx > 0 and
                    lines[current_line_idx - 1].strip() == 'jobs:'
                ):
                    block_type = "job"
                    if ':' in stripped_line:
                        block_name = stripped_line.split(':')[0].strip()
                    block_start_idx = current_line_idx
                    break
                # Check if this looks like a step
                elif stripped_line.startswith('- name:'):
                    block_type = "step"
                    block_name = stripped_line.replace('- name:', '').strip().strip('"\'')
                    block_start_idx = current_line_idx
                    break
                elif stripped_line.startswith('-') and 'name:' in stripped_line:
                    block_type = "step"
                    # Extract name from inline format like "- name: Step Name"
                    name_part = stripped_line.split('name:', 1)[1].strip().strip('"\'')
                    block_name = name_part
                    block_start_idx = current_line_idx
                    break
                # Check for step without explicit name
                elif stripped_line.startswith('- '):
                    block_type = "step"
                    block_name = "unnamed step"
                    block_start_idx = current_line_idx
                    break
            
            current_line_idx -= 1
        
        # Walk forward to find the end of the block
        block_end_idx = matching_line_index
        base_indent = len(lines[block_start_idx]) - len(lines[block_start_idx].lstrip()) if block_start_idx < len(lines) else 0
        
        for i in range(block_start_idx + 1, len(lines)):
            line = lines[i]
            stripped_line = line.strip()
            
            # Skip empty lines and comments
            if not stripped_line or stripped_line.startswith('#'):
                block_end_idx = i
                continue
                
            line_indent = len(line) - len(line.lstrip())
            
            # If we encounter a line with same or less indentation than block start, 
            # and it's not continuing the current block, we've reached the end
            if line_indent <= base_indent:
                # Check if this starts a new block at the same level
                if (stripped_line.startswith('- ') or 
                    (':' in stripped_line and not stripped_line.startswith(' '))):
                    break
            
            block_end_idx = i
        
        # Extract the block content
        block_lines = lines[block_start_idx:block_end_idx + 1]
        block_content = '\n'.join(block_lines)
        
        return {
            'block_id': f"{block_type}_{block_name}_{block_start_idx}",
            'block_type': block_type,
            'block_name': block_name,
            'start_line': block_start_idx + 1,  # Convert to 1-based line numbers
            'end_line': block_end_idx + 1,
            'content': block_content.strip()
        }

    @staticmethod
    async def search_repositories_by_workflow_content(token: str, search_term: str, scope: str = 'user', org_name: str = None) -> Dict:
        """Search repositories by content within their workflow files"""
        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Backend-App/1.0"
        }
        
        try:
            # Get repositories based on scope
            if scope == 'user':
                repositories = await GitHubService.get_user_repositories(token)
            elif scope == 'organization' and org_name:
                repositories = await GitHubService.get_organization_repositories(token, org_name)
            else:
                raise ValueError("Invalid scope or missing organization name")
            
            matching_repositories = []
            search_stats = {
                "total_repositories_searched": len(repositories),
                "repositories_with_workflows": 0,
                "matching_repositories": 0,
                "total_workflow_files_searched": 0,
                "matching_workflow_files": 0
            }
            
            # Limit concurrent requests to avoid overwhelming the API
            max_concurrent = 3  # Conservative limit for content downloading
            semaphore = asyncio.Semaphore(max_concurrent)
            
            async def search_repository_workflows(repo):
                async with semaphore:
                    try:
                        owner = repo.get("owner", {}).get("login")
                        repo_name = repo.get("name")
                        
                        if not owner or not repo_name:
                            return None
                        
                        async with GitHubService.get_http_client() as client:
                            # Check if .github/workflows directory exists
                            workflows_response = await client.get(
                                f"{GitHubService.BASE_URL}/repos/{owner}/{repo_name}/contents/.github/workflows",
                                headers=headers
                            )
                            
                            if workflows_response.status_code != 200:
                                return None
                            
                            workflows_data = workflows_response.json()
                            workflow_files = [
                                item for item in workflows_data 
                                if item.get("type") == "file" and item.get("name", "").endswith((".yml", ".yaml"))
                            ]
                            
                            if not workflow_files:
                                return None
                            
                            search_stats["repositories_with_workflows"] += 1
                            search_stats["total_workflow_files_searched"] += len(workflow_files)
                            
                            matching_files = []
                            
                            # Search through each workflow file
                            for workflow_file in workflow_files:
                                try:
                                    content_response = await client.get(
                                        workflow_file.get("download_url"),
                                        headers={
                                            "User-Agent": "Backend-App/1.0"
                                        }
                                    )
                                    
                                    if content_response.status_code == 200:
                                        content = content_response.text
                                        
                                        # Case-insensitive search
                                        if search_term.lower() in content.lower():
                                            # Parse the YAML content to find complete jobs/steps containing the search term
                                            lines = content.split('\n')
                                            matching_blocks = []
                                            
                                            # Find all line numbers that contain the search term
                                            matching_line_numbers = []
                                            for i, line in enumerate(lines, 1):
                                                if search_term.lower() in line.lower():
                                                    matching_line_numbers.append(i)
                                            
                                            # For each matching line, find the containing job or step
                                            processed_blocks = set()  # Track which blocks we've already processed
                                            
                                            for line_num in matching_line_numbers:
                                                block_info = GitHubService._find_containing_block(lines, line_num - 1)  # Convert to 0-based index
                                                
                                                if block_info and block_info['block_id'] not in processed_blocks:
                                                    processed_blocks.add(block_info['block_id'])
                                                    matching_blocks.append({
                                                        "block_type": block_info['block_type'],
                                                        "block_name": block_info['block_name'],
                                                        "start_line": block_info['start_line'],
                                                        "end_line": block_info['end_line'],
                                                        "content": block_info['content'],
                                                        "matching_line": line_num,
                                                        "matching_text": lines[line_num - 1].strip()
                                                    })
                                            
                                            matching_files.append({
                                                "name": workflow_file.get("name"),
                                                "path": workflow_file.get("path"),
                                                "html_url": workflow_file.get("html_url"),
                                                "download_url": workflow_file.get("download_url"),
                                                "size": workflow_file.get("size"),
                                                "matching_blocks": matching_blocks,
                                                "matches": matching_blocks,  # Keep for backward compatibility
                                                "total_matches": len(matching_blocks)
                                            })
                                            
                                            search_stats["matching_workflow_files"] += 1
                                
                                except Exception as e:
                                    print(f"Error searching workflow file {workflow_file.get('name')}: {e}")
                                    continue
                            
                            if matching_files:
                                search_stats["matching_repositories"] += 1
                                return {
                                    **GitHubService.format_repository(repo),
                                    "matching_workflow_files": matching_files,
                                    "total_matching_files": len(matching_files),
                                    "total_matches": sum(f["total_matches"] for f in matching_files)
                                }
                            
                            return None
                            
                    except Exception as e:
                        print(f"Error searching repository {repo.get('full_name', 'unknown')}: {e}")
                        return None
            
            # Execute searches concurrently
            print(f"Searching {len(repositories)} repositories for workflow content: '{search_term}'")
            search_results = await asyncio.gather(
                *[search_repository_workflows(repo) for repo in repositories],
                return_exceptions=True
            )
            
            # Filter out None results and exceptions
            matching_repositories = [
                result for result in search_results 
                if result is not None and not isinstance(result, Exception)
            ]
            
            return {
                "search_term": search_term,
                "scope": scope,
                "organization": org_name if scope == 'organization' else None,
                "matching_repositories": matching_repositories,
                "search_statistics": search_stats,
                "success": True
            }
            
        except Exception as e:
            print(f"Error in workflow content search: {e}")
            return {
                "search_term": search_term,
                "scope": scope,
                "organization": org_name if scope == 'organization' else None,
                "matching_repositories": [],
                "search_statistics": {
                    "total_repositories_searched": 0,
                    "repositories_with_workflows": 0,
                    "matching_repositories": 0,
                    "total_workflow_files_searched": 0,
                    "matching_workflow_files": 0
                },
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    async def get_repository_workflows(token: str, owner: str, repo: str) -> List[Dict]:
        """Get all workflow files from a repository"""
        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Backend-App/1.0"
        }
        
        async with GitHubService.get_http_client() as client:
            try:
                # Get workflow files from .github/workflows directory
                response = await client.get(
                    f"{GitHubService.BASE_URL}/repos/{owner}/{repo}/contents/.github/workflows",
                    headers=headers
                )
                
                if response.status_code == 200:
                    workflows_data = response.json()
                    workflow_files = []
                    
                    for item in workflows_data:
                        if item['type'] == 'file' and (item['name'].endswith('.yml') or item['name'].endswith('.yaml')):
                            workflow_files.append({
                                'name': item['name'],
                                'path': item['path'],
                                'sha': item['sha'],
                                'size': item['size'],
                                'url': item['url'],
                                'html_url': item['html_url'],
                                'download_url': item['download_url']
                            })
                    
                    return workflow_files
                elif response.status_code == 404:
                    # No workflows directory
                    return []
                else:
                    response.raise_for_status()
                    return []
            except Exception as e:
                print(f"Error fetching workflows for {owner}/{repo}: {e}")
                return []
    
    @staticmethod
    async def get_repository_branches(token: str, owner: str, repo: str) -> List[Dict]:
        """Get all branches from a repository"""
        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Backend-App/1.0"
        }
        
        branches = []
        page = 1
        per_page = 100
        
        async with GitHubService.get_http_client() as client:
            try:
                while True:
                    response = await client.get(
                        f"{GitHubService.BASE_URL}/repos/{owner}/{repo}/branches",
                        headers=headers,
                        params={"page": page, "per_page": per_page}
                    )
                    
                    if response.status_code == 200:
                        branches_page = response.json()
                        if not branches_page:
                            break
                        
                        branches.extend([{
                            'name': branch['name'],
                            'commit_sha': branch['commit']['sha'],
                            'protected': branch.get('protected', False)
                        } for branch in branches_page])
                        
                        # If we got fewer than per_page results, we're done
                        if len(branches_page) < per_page:
                            break
                        
                        page += 1
                    elif response.status_code == 404:
                        # Repository not found or no branches
                        return []
                    else:
                        response.raise_for_status()
                        return []
                        
                return branches
            except Exception as e:
                print(f"Error fetching branches for {owner}/{repo}: {e}")
                return []
    
    @staticmethod
    async def get_repository_workflows_by_branch(token: str, owner: str, repo: str, branch: str) -> List[Dict]:
        """Get all workflow files from a repository for a specific branch"""
        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Backend-App/1.0"
        }
        
        async with GitHubService.get_http_client() as client:
            try:
                # Get workflow files from .github/workflows directory on specific branch
                response = await client.get(
                    f"{GitHubService.BASE_URL}/repos/{owner}/{repo}/contents/.github/workflows",
                    headers=headers,
                    params={"ref": branch}
                )
                
                if response.status_code == 200:
                    workflows_data = response.json()
                    workflow_files = []
                    
                    for item in workflows_data:
                        if item['type'] == 'file' and (item['name'].endswith('.yml') or item['name'].endswith('.yaml')):
                            workflow_files.append({
                                'name': item['name'],
                                'path': item['path'],
                                'sha': item['sha'],
                                'size': item['size'],
                                'url': item['url'],
                                'html_url': item['html_url'],
                                'download_url': item['download_url'],
                                'branch': branch
                            })
                    
                    return workflow_files
                elif response.status_code == 404:
                    # No workflows directory on this branch
                    return []
                else:
                    response.raise_for_status()
                    return []
            except Exception as e:
                print(f"Error fetching workflows for {owner}/{repo} on branch {branch}: {e}")
                return []
    
    @staticmethod
    async def get_file_content(token: str, owner: str, repo: str, file_path: str) -> str:
        """Get the content of a file from a repository"""
        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3.raw",
            "User-Agent": "Backend-App/1.0"
        }
        
        async with GitHubService.get_http_client() as client:
            try:
                response = await client.get(
                    f"{GitHubService.BASE_URL}/repos/{owner}/{repo}/contents/{file_path}",
                    headers=headers
                )
                response.raise_for_status()
                return response.text
            except Exception as e:
                print(f"Error fetching file content for {owner}/{repo}/{file_path}: {e}")
                return ""
    
    @staticmethod
    async def search_files_by_name(token: str, owner: str, repo: str, keywords: List[str]) -> List[Dict]:
        """Search for files in a repository whose names contain any of the keywords"""
        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Backend-App/1.0"
        }
        
        matched_files = []
        per_page = 100
        max_pages = 10  # GitHub Search API returns up to 1000 results (10 pages x 100 per_page)
        
        async with GitHubService.get_http_client() as client:
            try:
                # Use GitHub code search API to find files by name
                for keyword in keywords:
                    try:
                        # Search for files containing the keyword in their name, with pagination
                        search_query = f"{keyword} in:path repo:{owner}/{repo}"
                        page = 1
                        while page <= max_pages:
                            response = await client.get(
                                f"{GitHubService.BASE_URL}/search/code",
                                headers=headers,
                                params={"q": search_query, "per_page": per_page, "page": page}
                            )
                            
                            if response.status_code == 200:
                                data = response.json()
                                items = data.get('items', [])
                                for item in items:
                                    # Check if keyword is in the file name (not just path)
                                    file_name = item['name'].lower()
                                    if keyword.lower() in file_name:
                                        matched_files.append({
                                            'name': item['name'],
                                            'path': item['path'],
                                            'matched_keyword': keyword,
                                            'url': item.get('html_url') or item.get('url', ''),
                                            'sha': item.get('sha', '')
                                        })
                                # Stop if fewer than per_page results returned
                                if len(items) < per_page:
                                    break
                                page += 1
                                # Tiny delay between pages to respect rate limits
                                await asyncio.sleep(0.15)
                            else:
                                # Break pagination loop for this keyword on non-200
                                break
                        
                        # Add small delay between keyword batches to avoid rate limiting
                        await asyncio.sleep(0.2)
                        
                    except Exception as e:
                        print(f"Error searching for keyword '{keyword}' in {owner}/{repo}: {e}")
                        continue
                
                # Remove duplicates based on path
                unique_files = {}
                for file in matched_files:
                    if file['path'] not in unique_files:
                        unique_files[file['path']] = file
                    else:
                        # If file already exists, add the keyword to a list
                        if 'matched_keywords' not in unique_files[file['path']]:
                            unique_files[file['path']]['matched_keywords'] = [unique_files[file['path']]['matched_keyword']]
                            del unique_files[file['path']]['matched_keyword']
                        unique_files[file['path']]['matched_keywords'].append(file['matched_keyword'])
                
                # Convert back to list and ensure all have matched_keywords
                result = []
                for file in unique_files.values():
                    if 'matched_keyword' in file:
                        file['matched_keywords'] = [file['matched_keyword']]
                        del file['matched_keyword']
                    result.append(file)
                
                return result
                
            except Exception as e:
                print(f"Error searching files by name in {owner}/{repo}: {e}")
                return []

    @staticmethod
    async def list_repository_tree(token: str, owner: str, repo: str, branch: Optional[str] = None) -> Dict:
        """
        List the repository tree for the given branch (or default branch if not provided).
        Returns a dict with keys: tree: List[entries], truncated: bool, sha: str, url: str
        Each entry has: path, mode, type ('blob' for files), sha, size (optional), url
        """
        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Backend-App/1.0"
        }

        async with GitHubService.get_http_client() as client:
            try:
                use_branch = branch
                if not use_branch:
                    # Fetch default branch
                    repo_resp = await client.get(
                        f"{GitHubService.BASE_URL}/repos/{owner}/{repo}", headers=headers
                    )
                    if repo_resp.status_code != 200:
                        return {"tree": [], "truncated": False}
                    repo_data = repo_resp.json()
                    use_branch = repo_data.get("default_branch", "main")

                # Fetch tree recursively
                tree_resp = await client.get(
                    f"{GitHubService.BASE_URL}/repos/{owner}/{repo}/git/trees/{use_branch}",
                    headers=headers,
                    params={"recursive": "1"}
                )
                if tree_resp.status_code != 200:
                    return {"tree": [], "truncated": False, "branch": use_branch}
                tree_data = tree_resp.json()
                # Add the branch information to the response
                tree_data["branch"] = use_branch
                return tree_data
            except Exception as e:
                print(f"Error listing repository tree for {owner}/{repo}: {e}")
                return {"tree": [], "truncated": False, "branch": branch or "main"}

    @staticmethod
    async def create_coverity_migration_pr(token: str, owner: str, repo: str, branch_name: str, 
                                          coverity_yaml_content: str, original_polaris_file: str) -> str:
        """
        Create a pull request to add coverity.yaml file to the repository
        """
        async with GitHubService.get_http_client() as client:
            headers = {
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28"
            }
            
            # Get the default branch and its latest commit SHA
            repo_response = await client.get(
                f"{GitHubService.BASE_URL}/repos/{owner}/{repo}",
                headers=headers
            )
            repo_data = repo_response.json()
            default_branch = repo_data["default_branch"]
            
            # Get the latest commit SHA of the default branch
            ref_response = await client.get(
                f"{GitHubService.BASE_URL}/repos/{owner}/{repo}/git/ref/heads/{default_branch}",
                headers=headers
            )
            ref_data = ref_response.json()
            base_sha = ref_data["object"]["sha"]
            
            # Create a new branch
            create_ref_response = await client.post(
                f"{GitHubService.BASE_URL}/repos/{owner}/{repo}/git/refs",
                headers=headers,
                json={
                    "ref": f"refs/heads/{branch_name}",
                    "sha": base_sha
                }
            )
            
            if create_ref_response.status_code not in [200, 201]:
                raise Exception(f"Failed to create branch: {create_ref_response.text}")
            
            # Check if coverity.yaml already exists in the repository
            import base64
            content_encoded = base64.b64encode(coverity_yaml_content.encode()).decode()
            
            # Try to get existing file to check if it exists and get its SHA
            existing_file_sha = None
            try:
                existing_file_response = await client.get(
                    f"{GitHubService.BASE_URL}/repos/{owner}/{repo}/contents/coverity.yaml",
                    headers=headers,
                    params={"ref": default_branch}
                )
                if existing_file_response.status_code == 200:
                    existing_file_data = existing_file_response.json()
                    existing_file_sha = existing_file_data["sha"]
            except Exception:
                # File doesn't exist, which is fine
                pass
            
            # Create or update the coverity.yaml file in the new branch
            file_payload = {
                "message": f"Add coverity.yaml (migrated from {original_polaris_file})",
                "content": content_encoded,
                "branch": branch_name
            }
            
            # If file exists, include the SHA for update
            if existing_file_sha:
                file_payload["sha"] = existing_file_sha
            
            create_file_response = await client.put(
                f"{GitHubService.BASE_URL}/repos/{owner}/{repo}/contents/coverity.yaml",
                headers=headers,
                json=file_payload
            )
            
            if create_file_response.status_code not in [200, 201]:
                raise Exception(f"Failed to create coverity.yaml file: {create_file_response.text}")
            
            # Create the pull request
            pr_body = f"""## Polaris to Coverity Migration

This pull request adds a `coverity.yaml` file that has been automatically migrated from `{original_polaris_file}`.

### Changes:
- ✅ Added `coverity.yaml` with converted configuration
- 🔄 Migrated from Polaris format to Coverity format

### Migration Details:
The conversion includes:
- Build and clean commands
- Compiler configuration (cov-configure)
- Analysis arguments (cov-analyze-args)
- Skip files configuration
- File system exclusions

### Next Steps:
1. Review the generated `coverity.yaml` configuration
2. Test the configuration in your CI/CD pipeline
3. Update any custom build scripts if needed
4. Consider removing `{original_polaris_file}` after successful migration

---
*This pull request was automatically generated by the Onboarding Tool.*
"""
            
            create_pr_response = await client.post(
                f"{GitHubService.BASE_URL}/repos/{owner}/{repo}/pulls",
                headers=headers,
                json={
                    "title": f"Add coverity.yaml (migrated from {original_polaris_file})",
                    "body": pr_body,
                    "head": branch_name,
                    "base": default_branch
                }
            )
            
            if create_pr_response.status_code not in [200, 201]:
                raise Exception(f"Failed to create pull request: {create_pr_response.text}")
            
            pr_data = create_pr_response.json()
            return pr_data["html_url"]

    @staticmethod
    async def analyze_workflows_and_recommend_templates(token: str, search_results: Dict, available_templates: List[Dict]) -> Dict:
        """Analyze workflow search results and recommend templates using local MCP server"""
        analyzer = LocalWorkflowAnalyzer()
        
        enriched_results = {
            **search_results,
            "template_recommendations": []
        }
        
        try:
            for repo in search_results.get("matching_repositories", []):
                repo_recommendations = []
                
                for workflow_file in repo.get("matching_workflow_files", []):
                    # Get the full workflow content
                    async with GitHubService.get_http_client() as client:
                        try:
                            content_response = await client.get(
                                workflow_file.get("download_url"),
                                headers={"User-Agent": "Backend-App/1.0"}
                            )
                            
                            if content_response.status_code == 200:
                                workflow_content = content_response.text
                                
                                # Analyze the workflow
                                analysis = await analyzer.analyze_workflow(
                                    workflow_content, 
                                    workflow_file.get("name", "workflow.yml")
                                )
                                
                                # Find template matches
                                template_matches = await analyzer.find_template_matches(
                                    analysis, 
                                    available_templates
                                )
                                
                                # Create enriched workflow file data
                                enriched_workflow = {
                                    **workflow_file,
                                    "analysis": {
                                        "technologies": [
                                            {
                                                "name": tech.name,
                                                "type": tech.type.value,
                                                "confidence": tech.confidence,
                                                "evidence": tech.evidence[:2]  # Limit evidence
                                            } for tech in analysis.technologies
                                        ],
                                        "patterns": [
                                            {
                                                "type": pattern.pattern_type,
                                                "description": pattern.description,
                                                "confidence": pattern.confidence
                                            } for pattern in analysis.patterns[:3]  # Limit patterns
                                        ],
                                        "scores": {
                                            "complexity": round(analysis.complexity_score, 2),
                                            "security": round(analysis.security_score, 2),
                                            "modernization": round(analysis.modernization_score, 2)
                                        },
                                        "recommendations": analysis.recommendations[:3]  # Limit recommendations
                                    },
                                    "template_matches": [
                                        {
                                            "template_id": match.template_id,
                                            "template_name": match.template_name,
                                            "similarity_score": round(match.similarity_score, 2),
                                            "matching_features": match.matching_features[:3],
                                            "missing_features": match.missing_features[:3],
                                            "improvement_potential": match.improvement_potential
                                        } for match in template_matches[:3]  # Top 3 matches
                                    ]
                                }
                                
                                repo_recommendations.append(enriched_workflow)
                        
                        except Exception as e:
                            print(f"Error analyzing workflow {workflow_file.get('name')}: {e}")
                            # Add original workflow without analysis
                            repo_recommendations.append(workflow_file)
                
                # Update repository with analyzed workflows
                if repo_recommendations:
                    enriched_repo = {
                        **repo,
                        "analyzed_workflow_files": repo_recommendations,
                        "analysis_summary": {
                            "total_analyzed": len(repo_recommendations),
                            "avg_security_score": round(
                                sum(w.get("analysis", {}).get("scores", {}).get("security", 0) 
                                    for w in repo_recommendations if "analysis" in w) / 
                                max(len([w for w in repo_recommendations if "analysis" in w]), 1), 2
                            ),
                            "top_recommendation": repo_recommendations[0].get("template_matches", [{}])[0].get("template_name") if repo_recommendations and repo_recommendations[0].get("template_matches") else None
                        }
                    }
                    enriched_results["template_recommendations"].append(enriched_repo)
        
        except Exception as e:
            print(f"Error in workflow analysis: {e}")
            # Return original results if analysis fails
            return search_results
        
        return enriched_results