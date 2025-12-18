"""
Optimized search implementation for GitHub workflow keyword scanning
Performance improvements for faster repository scanning
"""
import asyncio
import re
import time
from typing import List, Dict, Set, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
import hashlib
import json
import httpx

@dataclass
class SearchCache:
    """Cache entry for search results"""
    content: str
    keywords_found: Set[str]
    timestamp: datetime
    file_hash: str

class OptimizedSearch:
    """
    Optimized search class with multiple performance improvements
    """
    
    def __init__(self):
        # Simple in-memory cache (could be Redis in production)
        self.cache = {}
        self.cache_ttl = timedelta(hours=1)  # Cache results for 1 hour
        
        # Pre-compiled regex patterns for faster searching
        self.keyword_patterns = {}
    
    def compile_keyword_patterns(self, keywords: List[str]) -> Dict[str, re.Pattern]:
        """
        Pre-compile regex patterns for all keywords for faster searching
        This avoids recompiling the same patterns repeatedly
        """
        patterns = {}
        for keyword in keywords:
            if keyword not in self.keyword_patterns:
                # Use word boundaries for more accurate matching
                pattern = re.compile(rf'\b{re.escape(keyword.lower())}\b', re.IGNORECASE)
                patterns[keyword] = pattern
                self.keyword_patterns[keyword] = pattern
            else:
                patterns[keyword] = self.keyword_patterns[keyword]
        return patterns
    
    async def search_repositories_concurrent(
        self,
        github_service,
        token: str,
        repositories_data: List,
        keyword_to_templates: Dict[str, List[Dict]],
        search_all_branches: bool = False,
        max_concurrent: int = 5  # Slightly higher concurrency for better throughput
    ) -> List[Dict]:
        """
        Process multiple repositories concurrently instead of sequentially
        Supports searching specific branches per repository or all branches
        
        repositories_data can be:
        - List of strings: ["owner/repo1", "owner/repo2"] (legacy format)
        - List of dicts: [{"repository": "owner/repo1", "branches": ["main", "dev"]}, ...]
        """
        # Create semaphore to limit concurrent requests
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def scan_single_repo(repo_data):
            async with semaphore:
                try:
                    # Handle both string and dict formats
                    if isinstance(repo_data, str):
                        repo_id = repo_data
                        branches = None
                    else:
                        repo_id = repo_data.get("repository")
                        branches = repo_data.get("branches")
                    
                    return await self.scan_repository_optimized(
                        github_service, token, repo_id, keyword_to_templates, 
                        search_all_branches=search_all_branches,
                        specific_branches=branches
                    )
                except Exception as e:
                    repo_id_str = repo_data if isinstance(repo_data, str) else repo_data.get("repository", "unknown")
                    print(f"Error scanning repository {repo_id_str}: {e}")
                    return {
                        "repository": repo_id_str,
                        "error": str(e),
                        "total_workflows": 0,
                        "workflows_with_matches": 0,
                        "workflows_without_matches": 0,
                        "workflows": [],
                        "matched_files": [],
                        "total_matched_files": 0
                    }
        
        # Process all repositories concurrently
        tasks = [scan_single_repo(repo_data) for repo_data in repositories_data]
        results = await asyncio.gather(*tasks)
        
        return results
    
    async def scan_repository_optimized(
        self,
        github_service,
        token: str,
        repo_id: str,
        keyword_to_templates: Dict[str, List[Dict]],
        search_all_branches: bool = False,
        specific_branches: Optional[List[str]] = None
    ) -> Dict:
        """
        Optimized single repository scanning with multiple improvements
        Supports searching specific branches, all branches, or default branch only
        
        Args:
            specific_branches: List of branch names to scan (e.g., ["main", "dev"])
                             If provided, only these branches will be scanned
                             Takes precedence over search_all_branches
        """
        owner, repo_name = repo_id.split('/')
        
        # Pre-compile keyword patterns
        all_keywords = list(keyword_to_templates.keys())
        keyword_patterns = self.compile_keyword_patterns(all_keywords)
        
        # Check for polaris files in repository root
        polaris_files = []
        has_polaris_in_root = False
        try:
            headers = {
                'Authorization': f'token {token}',
                'Accept': 'application/vnd.github.v3+json'
            }
            root_url = f"https://api.github.com/repos/{owner}/{repo_name}/contents/"
            
            async with httpx.AsyncClient(verify=False, timeout=30.0) as client:
                root_response = await client.get(root_url, headers=headers)
                
                if root_response.status_code == 200:
                    root_data = root_response.json()
                    for item in root_data:
                        if item.get("type") == "file" and item.get("name") in ["polaris.yml", "polaris.yaml"]:
                            polaris_files.append({
                                "name": item.get("name"),
                                "path": item.get("path"),
                                "size": item.get("size"),
                                "sha": item.get("sha"),
                                "download_url": item.get("download_url")
                            })
                            has_polaris_in_root = True
        except Exception as e:
            print(f"Error checking for polaris files in {repo_id}: {e}")
        
        if specific_branches:
            # Scan only the specified branches
            all_workflow_matches = []
            branches_scanned = 0
            
            for branch_name in specific_branches:
                try:
                    # Get workflow files for this branch
                    workflows = await github_service.get_repository_workflows_by_branch(
                        token, owner, repo_name, branch_name
                    )
                    
                    if workflows:
                        # Fetch file contents and search
                        workflow_matches = await self.fetch_and_search_parallel_with_branch(
                            github_service, token, owner, repo_name, workflows, 
                            keyword_to_templates, keyword_patterns, branch_name
                        )
                        all_workflow_matches.extend(workflow_matches)
                    
                    branches_scanned += 1
                    
                except Exception as e:
                    print(f"Error scanning branch {branch_name} in {repo_id}: {e}")
                    continue
            
            # Search files by name across specified branches
            matched_files = await self.search_files_by_name_via_tree(
                github_service, token, owner, repo_name, all_keywords, keyword_to_templates, specific_branches
            )
            if matched_files is None:
                matched_files = await self.search_files_by_name_batched(
                    github_service, token, owner, repo_name, all_keywords, keyword_to_templates, specific_branches
                )
            
            workflow_matches = all_workflow_matches
            
        elif search_all_branches:
            # Search all branches when flag is set
            branches = await github_service.get_repository_branches(token, owner, repo_name)
            if not branches:
                # No branches found, return empty result
                return {
                    "repository": repo_id,
                    "total_workflows": 0,
                    "workflows_with_matches": 0,
                    "workflows_without_matches": 0,
                    "workflows": [],
                    "matched_files": [],
                    "total_matched_files": 0,
                    "branches_scanned": 0
                }
            
            all_workflow_matches = []
            branches_scanned = 0
            
            for branch in branches:
                branch_name = branch['name']
                try:
                    # Get workflow files for this branch
                    workflows = await github_service.get_repository_workflows_by_branch(
                        token, owner, repo_name, branch_name
                    )
                    
                    if workflows:
                        # Fetch file contents and search
                        workflow_matches_for_branch = await self.fetch_and_search_parallel_with_branch(
                            github_service, token, owner, repo_name, workflows, 
                            keyword_to_templates, keyword_patterns, branch_name
                        )
                        all_workflow_matches.extend(workflow_matches_for_branch)
                    
                    branches_scanned += 1
                    
                except Exception as e:
                    print(f"Error scanning branch {branch_name} in {repo_id}: {e}")
                    continue
            
            # Search files by name across all branches
            branch_names = [branch['name'] for branch in branches]
            matched_files = await self.search_files_by_name_via_tree(
                github_service, token, owner, repo_name, all_keywords, keyword_to_templates, branch_names
            )
            if matched_files is None:
                matched_files = await self.search_files_by_name_batched(
                    github_service, token, owner, repo_name, all_keywords, keyword_to_templates, branch_names
                )
            
            workflow_matches = all_workflow_matches
            
        else:
            # Original behavior: scan default branch only
            workflows = await github_service.get_repository_workflows(token, owner, repo_name)
            
            # Fetch file contents in parallel
            workflow_matches = await self.fetch_and_search_parallel(
                github_service, token, owner, repo_name, workflows, 
                keyword_to_templates, keyword_patterns
            )
            
            # Search files by name (optimized with batching)
            matched_files = await self.search_files_by_name_via_tree(
                github_service, token, owner, repo_name, all_keywords, keyword_to_templates
            )
            if matched_files is None:
                matched_files = await self.search_files_by_name_batched(
                    github_service, token, owner, repo_name, all_keywords, keyword_to_templates
                )
            
            branches_scanned = 1

        # Fallback: also check workflow filenames themselves for keyword matches
        # This ensures filename matching works even if GitHub code search misses items
        if workflow_matches:
            matched_from_workflow_names = self._match_keywords_in_filenames(
                workflows, all_keywords, keyword_to_templates
            )
            # Merge by path+branch to avoid deduplicating files from different branches
            by_path_branch = {f"{f['path']}#{f.get('branch', 'default')}": f for f in matched_files}
            for f in matched_from_workflow_names:
                key = f"{f['path']}#{f.get('branch', 'default')}"
                if key in by_path_branch:
                    # union keywords and templates if duplicate exists
                    existing = by_path_branch[key]
                    existing_kw = set(existing.get("matched_keywords", []))
                    new_kw = set(f.get("matched_keywords", []))
                    existing["matched_keywords"] = sorted(existing_kw.union(new_kw))
                    # templates are objects with id/name/description
                    tmpl_key = lambda t: (t.get("id"), t.get("name"))
                    existing_tm = {tmpl_key(t): t for t in existing.get("matched_templates", [])}
                    for t in f.get("matched_templates", []):
                        existing_tm[tmpl_key(t)] = t
                    existing["matched_templates"] = list(existing_tm.values())
                else:
                    by_path_branch[key] = f
            matched_files = list(by_path_branch.values())
        
        # Calculate statistics
        workflows_with_matches = [w for w in workflow_matches if w['has_matches']]
        workflows_without_matches = [w for w in workflow_matches if not w['has_matches']]
        
        result = {
            "repository": repo_id,
            "owner": owner,
            "name": repo_name,
            "total_workflows": len(workflow_matches),
            "workflows_with_matches": len(workflows_with_matches),
            "workflows_without_matches": len(workflows_without_matches),
            "workflows": workflow_matches,
            "matched_files": matched_files,
            "total_matched_files": len(matched_files),
            "has_polaris_in_root": has_polaris_in_root,
            "polaris_files": polaris_files
        }
        
        if search_all_branches:
            result["branches_scanned"] = branches_scanned
        
        return result
    
    async def fetch_and_search_parallel(
        self,
        github_service,
        token: str,
        owner: str,
        repo_name: str,
        workflows: List[Dict],
        keyword_to_templates: Dict[str, List[Dict]],
        keyword_patterns: Dict[str, re.Pattern],
    max_concurrent: int = 8
    ) -> List[Dict]:
        """
        Fetch workflow file contents in parallel and search them efficiently
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def process_single_workflow(workflow: Dict):
            async with semaphore:
                # Generate cache key
                cache_key = f"{owner}/{repo_name}/{workflow['path']}/{workflow.get('sha', '')}"
                
                # Check cache first
                if cache_key in self.cache:
                    cache_entry = self.cache[cache_key]
                    if datetime.now() - cache_entry.timestamp < self.cache_ttl:
                        # Use cached keywords
                        matched_keywords = list(cache_entry.keywords_found)
                        matched_templates = set()
                        for keyword in matched_keywords:
                            if keyword in keyword_to_templates:
                                for template in keyword_to_templates[keyword]:
                                    matched_templates.add((template['id'], template['name'], template['description']))
                        
                        return {
                            "name": workflow['name'],
                            "path": workflow['path'],
                            "html_url": workflow.get('html_url'),
                            "download_url": workflow.get('download_url'),
                            "matched_keywords": matched_keywords,
                            "matched_templates": [
                                {"id": t[0], "name": t[1], "description": t[2]}
                                for t in matched_templates
                            ],
                            "has_matches": len(matched_keywords) > 0,
                            "cached": True
                        }
                
                # Fetch content from API
                try:
                    content = await github_service.get_file_content(
                        token, owner, repo_name, workflow['path']
                    )
                    
                    # Optimized search using pre-compiled regex patterns
                    matched_keywords = []
                    matched_templates = set()
                    keywords_found = set()
                    
                    for keyword, pattern in keyword_patterns.items():
                        if pattern.search(content):
                            matched_keywords.append(keyword)
                            keywords_found.add(keyword)
                            for template in keyword_to_templates[keyword]:
                                matched_templates.add((template['id'], template['name'], template['description']))
                    
                    # Cache the result
                    self.cache[cache_key] = SearchCache(
                        content=content[:1000],  # Cache only first 1000 chars to save memory
                        keywords_found=keywords_found,
                        timestamp=datetime.now(),
                        file_hash=workflow.get('sha', '')
                    )
                    
                    return {
                        "name": workflow['name'],
                        "path": workflow['path'],
                        "html_url": workflow.get('html_url'),
                        "download_url": workflow.get('download_url'),
                        "matched_keywords": matched_keywords,
                        "matched_templates": [
                            {"id": t[0], "name": t[1], "description": t[2]}
                            for t in matched_templates
                        ],
                        "has_matches": len(matched_keywords) > 0,
                        "cached": False
                    }
                    
                except Exception as e:
                    print(f"Error processing workflow {workflow['path']}: {e}")
                    return {
                        "name": workflow['name'],
                        "path": workflow['path'],
                        "html_url": workflow.get('html_url'),
                        "download_url": workflow.get('download_url'),
                        "matched_keywords": [],
                        "matched_templates": [],
                        "has_matches": False,
                        "error": str(e)
                    }
        
        # Process all workflows in parallel
        tasks = [process_single_workflow(workflow) for workflow in workflows]
        results = await asyncio.gather(*tasks)
        
        return results
    
    async def fetch_and_search_parallel_with_branch(
        self,
        github_service,
        token: str,
        owner: str,
        repo_name: str,
        workflows: List[Dict],
        keyword_to_templates: Dict[str, List[Dict]],
        keyword_patterns: Dict[str, re.Pattern],
        branch: str,
        max_concurrent: int = 8
    ) -> List[Dict]:
        """
        Fetch workflow file contents in parallel and search them efficiently
        Includes branch information in the results
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def process_single_workflow(workflow: Dict):
            async with semaphore:
                # Generate cache key with branch
                cache_key = f"{owner}/{repo_name}/{branch}/{workflow['path']}/{workflow.get('sha', '')}"
                
                # Check cache first
                if cache_key in self.cache:
                    cache_entry = self.cache[cache_key]
                    if datetime.now() - cache_entry.timestamp < self.cache_ttl:
                        # Use cached keywords
                        matched_keywords = list(cache_entry.keywords_found)
                        matched_templates = set()
                        for keyword in matched_keywords:
                            if keyword in keyword_to_templates:
                                for template in keyword_to_templates[keyword]:
                                    matched_templates.add((template['id'], template['name'], template['description']))
                        
                        return {
                            "name": workflow['name'],
                            "path": workflow['path'],
                            "branch": branch,
                            "html_url": workflow.get('html_url'),
                            "download_url": workflow.get('download_url'),
                            "matched_keywords": matched_keywords,
                            "matched_templates": [
                                {"id": t[0], "name": t[1], "description": t[2]}
                                for t in matched_templates
                            ],
                            "has_matches": len(matched_keywords) > 0,
                            "cached": True
                        }
                
                # Fetch content from API
                try:
                    content = await github_service.get_file_content(
                        token, owner, repo_name, workflow['path']
                    )
                    
                    # Optimized search using pre-compiled regex patterns
                    matched_keywords = []
                    matched_templates = set()
                    keywords_found = set()
                    
                    for keyword, pattern in keyword_patterns.items():
                        if pattern.search(content):
                            matched_keywords.append(keyword)
                            keywords_found.add(keyword)
                            if keyword in keyword_to_templates:
                                for template in keyword_to_templates[keyword]:
                                    matched_templates.add((template['id'], template['name'], template['description']))
                    
                    # Cache the result
                    cache_entry = SearchCache(
                        content=content,
                        keywords_found=keywords_found,
                        timestamp=datetime.now(),
                        file_hash=workflow.get('sha', '')
                    )
                    self.cache[cache_key] = cache_entry
                    
                    return {
                        "name": workflow['name'],
                        "path": workflow['path'],
                        "branch": branch,
                        "html_url": workflow.get('html_url'),
                        "download_url": workflow.get('download_url'),
                        "matched_keywords": matched_keywords,
                        "matched_templates": [
                            {"id": t[0], "name": t[1], "description": t[2]}
                            for t in matched_templates
                        ],
                        "has_matches": len(matched_keywords) > 0,
                        "cached": False
                    }
                    
                except Exception as e:
                    print(f"Error processing workflow {workflow['path']} on branch {branch}: {e}")
                    return {
                        "name": workflow['name'],
                        "path": workflow['path'],
                        "branch": branch,
                        "html_url": workflow.get('html_url'),
                        "download_url": workflow.get('download_url'),
                        "matched_keywords": [],
                        "matched_templates": [],
                        "has_matches": False,
                        "error": str(e)
                    }
        
        # Process all workflows in parallel
        tasks = [process_single_workflow(workflow) for workflow in workflows]
        results = await asyncio.gather(*tasks)
        
        return results
    
    async def search_files_by_name_batched(
        self,
        github_service,
        token: str,
        owner: str,
        repo_name: str,
        keywords: List[str],
        keyword_to_templates: Dict[str, List[Dict]],
        branches: Optional[List[str]] = None
    ) -> List[Dict]:
        """
        Optimized filename search with batching to reduce API calls.
        Supports searching specific branches if provided.
        
        Args:
            branches: Optional list of branch names to search. If None, searches across all branches.
        """
        # Group keywords to reduce API calls
        # GitHub search API works better with fewer, broader queries
        batch_size = 3  # Conservative batch size
        keyword_batches = [keywords[i:i + batch_size] for i in range(0, len(keywords), batch_size)]
        # Use dict keyed by path to deduplicate across batches and enrich matches
        dedup_by_path: Dict[str, Dict] = {}

        for batch in keyword_batches:
            try:
                # Use existing method but with controlled batching
                batch_files = await github_service.search_files_by_name(
                    token, owner, repo_name, batch
                )
                # Process results and link to templates (dedup + merge keywords)
                for file_info in batch_files:
                    file_name = file_info.get('name', '')
                    file_path = file_info.get('path', '')
                    file_name_lower = file_name.lower()
                    # Prefer keywords computed by service if present
                    service_keywords = file_info.get('matched_keywords', [])
                    # Also detect within current batch to be safe
                    batch_detected = [k for k in batch if k.lower() in file_name_lower]
                    combined_keywords = sorted(set(service_keywords) | set(batch_detected))

                    if combined_keywords:
                        # Map keywords to templates
                        tmpl_set = set()
                        for kw in combined_keywords:
                            if kw in keyword_to_templates:
                                for template in keyword_to_templates[kw]:
                                    tmpl_set.add((template['id'], template['name'], template['description']))

                        new_entry = {
                            "name": file_name,
                            "path": file_path,
                            "matched_keywords": combined_keywords,
                            "matched_templates": [
                                {"id": t[0], "name": t[1], "description": t[2]}
                                for t in tmpl_set
                            ],
                            "url": file_info.get('url', '')
                        }

                        if file_path in dedup_by_path:
                            # Merge keywords and templates
                            existing = dedup_by_path[file_path]
                            existing["matched_keywords"] = sorted(
                                set(existing.get("matched_keywords", [])) | set(new_entry["matched_keywords"])
                            )
                            def keyf(t):
                                return (t.get("id"), t.get("name"))
                            tm = {keyf(t): t for t in existing.get("matched_templates", [])}
                            for t in new_entry.get("matched_templates", []):
                                tm[keyf(t)] = t
                            existing["matched_templates"] = list(tm.values())
                        else:
                            dedup_by_path[file_path] = new_entry
                
                # Small delay between batches to respect rate limits
                await asyncio.sleep(0.2)
                
            except Exception as e:
                print(f"Error in batched filename search: {e}")
                continue
        
        return list(dedup_by_path.values())

    async def search_files_by_name_via_tree(
        self,
        github_service,
        token: str,
        owner: str,
        repo_name: str,
        keywords: List[str],
        keyword_to_templates: Dict[str, List[Dict]],
        branches: Optional[List[str]] = None
    ) -> Optional[List[Dict]]:
        """
        Fast filename scan using Git Trees API to enumerate files in the repo.
        Supports searching specific branches or the default branch.
        Returns None to signal fallback if tree listing fails.
        
        Args:
            branches: Optional list of branch names to search. If None, searches default branch only.
        """
        try:
            # If specific branches are provided, search each branch
            if branches:
                return await self._search_files_in_multiple_branches(
                    github_service, token, owner, repo_name, keywords, keyword_to_templates, branches
                )
            
            # Default behavior: search default branch only
            return await self._search_files_in_single_branch(
                github_service, token, owner, repo_name, keywords, keyword_to_templates, None
            )
        except Exception as e:
            print(f"Tree-based filename search failed for {owner}/{repo_name}: {e}")
            return None

    async def _search_files_in_multiple_branches(
        self,
        github_service,
        token: str,
        owner: str,
        repo_name: str,
        keywords: List[str],
        keyword_to_templates: Dict[str, List[Dict]],
        branches: List[str]
    ) -> List[Dict]:
        """
        Search files across multiple branches using tree API calls.
        Returns separate entries for each branch where a file is found.
        """
        all_results = []
        
        print(f"DEBUG: Searching files in {len(branches)} branches: {branches}")
        
        for branch in branches:
            try:
                print(f"DEBUG: Searching branch: {branch}")
                branch_results = await self._search_files_in_single_branch(
                    github_service, token, owner, repo_name, keywords, keyword_to_templates, branch
                )
                
                print(f"DEBUG: Branch {branch} returned {len(branch_results) if branch_results else 0} files")
                
                if branch_results:
                    # Add branch information to each result and add to our list
                    for file_result in branch_results:
                        file_result_with_branch = file_result.copy()
                        file_result_with_branch["branch"] = branch
                        all_results.append(file_result_with_branch)
                            
            except Exception as e:
                print(f"Error searching files in branch {branch} for {owner}/{repo_name}: {e}")
                continue
        
        print(f"DEBUG: Final result: {len(all_results)} total file entries found across all branches")
        return all_results

    async def _search_files_in_single_branch(
        self,
        github_service,
        token: str,
        owner: str,
        repo_name: str,
        keywords: List[str],
        keyword_to_templates: Dict[str, List[Dict]],
        branch: Optional[str] = None
    ) -> Optional[List[Dict]]:
        """
        Search files in a single branch using the tree API.
        """
        tree_data = await github_service.list_repository_tree(token, owner, repo_name, branch)
        tree = tree_data.get("tree", []) if isinstance(tree_data, dict) else []
        if not tree:
            return None
            
        # Get the actual branch name used from the response
        actual_branch = tree_data.get("branch", branch or "main")
            
        keywords_lower = [k.lower() for k in keywords]
        by_path: Dict[str, Dict] = {}
        
        for entry in tree:
            if entry.get("type") != "blob":
                continue
            path = entry.get("path", "")
            if not path:
                continue
                
            # Extract filename portion
            name = path.split('/')[-1]
            name_lower = name.lower()
            matched = [k for k in keywords_lower if k in name_lower]
            if not matched:
                continue
                
            # Re-map lowercase keywords back to originals (preserve display)
            matched_originals = sorted({orig for orig in keywords for ml in matched if orig.lower() == ml})
            tmpl_set = set()
            for kw in matched_originals:
                if kw in keyword_to_templates:
                    for t in keyword_to_templates[kw]:
                        tmpl_set.add((t['id'], t['name'], t['description']))
                        
            entry_obj = {
                "name": name,
                "path": path,
                "branch": actual_branch,
                "matched_keywords": matched_originals,
                "matched_templates": [
                    {"id": t[0], "name": t[1], "description": t[2]}
                    for t in tmpl_set
                ],
                "url": ""
            }
            
            if path in by_path:
                # Merge keywords and templates
                existing = by_path[path]
                existing["matched_keywords"] = sorted(set(existing["matched_keywords"]) | set(entry_obj["matched_keywords"]))
                def tkey(t):
                    return (t.get("id"), t.get("name"))
                tm = {tkey(t): t for t in existing.get("matched_templates", [])}
                for t in entry_obj.get("matched_templates", []):
                    tm[tkey(t)] = t
                existing["matched_templates"] = list(tm.values())
            else:
                by_path[path] = entry_obj
                
        return list(by_path.values())

    

    def _match_keywords_in_filenames(
        self,
        workflows: List[Dict],
        keywords: List[str],
        keyword_to_templates: Dict[str, List[Dict]]
    ) -> List[Dict]:
        """
        Local fallback: scan provided workflow file names for keyword matches
        and build the same result shape used for matched_files.
        """
        results: Dict[str, Dict] = {}
        for wf in workflows:
            name = wf.get("name", "")
            path = wf.get("path", "")
            name_lower = name.lower()
            matched = [k for k in keywords if k.lower() in name_lower]
            if not matched:
                continue
            tmpl_set = set()
            for kw in matched:
                if kw in keyword_to_templates:
                    for t in keyword_to_templates[kw]:
                        tmpl_set.add((t['id'], t['name'], t['description']))
            results[path] = {
                "name": name,
                "path": path,
                "matched_keywords": sorted(set(matched)),
                "matched_templates": [
                    {"id": t[0], "name": t[1], "description": t[2]}
                    for t in tmpl_set
                ]
            }
        return list(results.values())
    
    def get_cache_stats(self) -> Dict:
        """Get cache performance statistics"""
        total_entries = len(self.cache)
        expired_entries = sum(
            1 for entry in self.cache.values()
            if datetime.now() - entry.timestamp > self.cache_ttl
        )
        
        return {
            "total_cache_entries": total_entries,
            "expired_entries": expired_entries,
            "active_entries": total_entries - expired_entries,
            "cache_hit_ratio": "Not implemented yet"
        }
    
    def clear_expired_cache(self):
        """Clean up expired cache entries"""
        now = datetime.now()
        expired_keys = [
            key for key, entry in self.cache.items()
            if now - entry.timestamp > self.cache_ttl
        ]
        for key in expired_keys:
            del self.cache[key]
        
        return len(expired_keys)


# Global instance
optimized_search = OptimizedSearch()


# Additional optimization strategies for production:

class ProductionOptimizations:
    """
    Additional optimizations for production deployment
    """
    
    @staticmethod
    def setup_redis_cache():
        """
        10. REDIS CACHING - Replace in-memory cache with Redis
        - Persistent cache across server restarts
        - Shared cache across multiple server instances
        - Better memory management
        """
        pass
    
    @staticmethod
    def implement_database_indexing():
        """
        11. DATABASE OPTIMIZATION
        - Index keywords column for faster template queries
        - Cache template-keyword mappings
        - Use database views for complex queries
        """
        pass
    
    @staticmethod
    def setup_background_jobs():
        """
        12. BACKGROUND PROCESSING
        - Queue heavy searches using Celery/RQ
        - Pre-fetch popular repositories
        - Schedule periodic cache warming
        """
        pass
    
    @staticmethod
    def implement_search_analytics():
        """
        13. SEARCH ANALYTICS
        - Track search performance metrics
        - Identify slow repositories/keywords
        - Optimize based on usage patterns
        """
        pass