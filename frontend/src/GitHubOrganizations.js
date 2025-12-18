import React, { useState, useEffect, useCallback } from 'react';
import { githubAPI } from './githubAPI';

const GitHubOrganizations = () => {
  const [organizations, setOrganizations] = useState([]);
  const [selectedOrg, setSelectedOrg] = useState('');
  const [selectedScope, setSelectedScope] = useState('organization'); // 'organization' or 'user'
  const [orgDetails, setOrgDetails] = useState(null);
  const [showOrgDetailsModal, setShowOrgDetailsModal] = useState(false);
  const [orgSecrets, setOrgSecrets] = useState([]);
  const [orgVariables, setOrgVariables] = useState([]);
  const [orgCustomProperties, setOrgCustomProperties] = useState([]);
  const [loadingOrgDetails, setLoadingOrgDetails] = useState(false);
  const [repositories, setRepositories] = useState([]);
  const [selectedRepo, setSelectedRepo] = useState('');
  const [selectedRepoDetails, setSelectedRepoDetails] = useState(null);
  const [viewingRepoName, setViewingRepoName] = useState(''); // For modal display only
  const [selectedReposForOnboarding, setSelectedReposForOnboarding] = useState(new Set());
  const [repositoryBranches, setRepositoryBranches] = useState(new Map()); // Map of repo full_name -> branches array
  const [selectedBranches, setSelectedBranches] = useState(new Map()); // Map of repo full_name -> Set of branch names
  const [showOnboardingModal, setShowOnboardingModal] = useState(false);
  const [onboardingScanResults, setOnboardingScanResults] = useState(null);
  const [scanningRepos, setScanningRepos] = useState(false);
  const [showMigrationModal, setShowMigrationModal] = useState(false);
  const [migrationResult, setMigrationResult] = useState(null);
  const [migratingPolaris, setMigratingPolaris] = useState(false);
  const [availableLanguages, setAvailableLanguages] = useState([]);
  const [selectedLanguage, setSelectedLanguage] = useState('');
  const [filterPolarisFiles, setFilterPolarisFiles] = useState(false);
  const [filterWithWorkflows, setFilterWithWorkflows] = useState(false);
  const [loading, setLoading] = useState(true);
  const [loadingLanguages, setLoadingLanguages] = useState(false);
  const [loadingRepos, setLoadingRepos] = useState(false);
  const [loadingRepoDetails, setLoadingRepoDetails] = useState(false);
  const [error, setError] = useState('');
  const [tokenStatus, setTokenStatus] = useState(null);
  const [userInfo, setUserInfo] = useState(null);

  const loadOrganizations = useCallback(async () => {
    try {
      const data = await githubAPI.getOrganizations();
      setOrganizations(data.organizations || []);
    } catch (err) {
      setError(err.message);
      console.error('Error loading organizations:', err);
    }
  }, []);

  const loadUserInfo = useCallback(async () => {
    try {
      const user = await githubAPI.getUserInfo();
      setUserInfo(user);
    } catch (err) {
      console.error('Error loading user info:', err);
    }
  }, []);

  const checkTokenAndLoadData = useCallback(async () => {
    try {
      setLoading(true);
      setError('');
      
      // Check token status first
      const status = await githubAPI.checkTokenStatus();
      setTokenStatus(status);
      
      if (status.has_token && status.is_valid) {
        // Load organizations and user info
        await Promise.all([
          loadOrganizations(),
          loadUserInfo()
        ]);
      }
    } catch (err) {
      console.error('Error in checkTokenAndLoadData:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [loadOrganizations, loadUserInfo]);

  useEffect(() => {
    checkTokenAndLoadData();
  }, [checkTokenAndLoadData]);

  const loadLanguages = useCallback(async (organization = null) => {
    try {
      setLoadingLanguages(true);
      setError('');
      
      const scope = selectedScope;
      const org = organization || (selectedScope === 'organization' ? selectedOrg : null);
      
      // For user scope, don't pass organization parameter at all
      const data = selectedScope === 'user' 
        ? await githubAPI.getLanguages(scope)
        : await githubAPI.getLanguages(scope, org);
      setAvailableLanguages(data.languages || []);
      
      // Also load all repositories when languages are loaded
      setSelectedLanguage('all');
      const repoData = selectedScope === 'user'
        ? await githubAPI.getRepositories(scope, null, 'all')
        : await githubAPI.getRepositories(scope, org, 'all');
      setRepositories(repoData.repositories || []);
    } catch (err) {
      setError(`Failed to load languages: ${err.message}`);
      console.error('Error loading languages:', err);
    } finally {
      setLoadingLanguages(false);
    }
  }, [selectedScope, selectedOrg]);

  // Combined function to load languages and all repositories automatically
  const loadLanguagesAndRepositories = useCallback(async () => {
    try {
      setLoadingLanguages(true);
      setError('');
      
      // For user scope, fetch all repositories directly without organization parameter
      const [languagesData, repositoriesData] = await Promise.all([
        githubAPI.getLanguages('user'),
        githubAPI.getRepositories('user', null, 'all')
      ]);
      
      setAvailableLanguages(languagesData.languages || []);
      
      // Debug: Check workflow_info data
      console.log('First 3 repos with workflow_info:', 
        repositoriesData.repositories?.slice(0, 3).map(r => ({
          name: r.name,
          workflow_info: r.workflow_info
        }))
      );
      
      setRepositories(repositoriesData.repositories || []);
      setSelectedLanguage('all');
    } catch (err) {
      setError(`Failed to load repositories: ${err.message}`);
      console.error('Error loading repositories:', err);
    } finally {
      setLoadingLanguages(false);
    }
  }, []);

  const loadRepositories = useCallback(async (language) => {
    if (!language || language.trim() === '') return;
    
    try {
      setLoadingRepos(true);
      setError('');
      
      const scope = selectedScope;
      const organization = selectedScope === 'organization' ? selectedOrg : null;
      
      // For user scope, don't pass organization parameter
      const data = selectedScope === 'user'
        ? await githubAPI.getRepositories(scope, null, language)
        : await githubAPI.getRepositories(scope, organization, language);
      setRepositories(data.repositories || []);
    } catch (err) {
      setError(`Failed to load repositories: ${err.message}`);
      console.error('Error loading repositories:', err);
    } finally {
      setLoadingRepos(false);
    }
  }, [selectedScope, selectedOrg]);

  const loadRepositoryDetails = useCallback(async (repoName) => {
    if (!repoName) return;
    
    try {
      setLoadingRepoDetails(true);
      setError('');
      
      const scope = selectedScope;
      const organization = selectedScope === 'organization' ? selectedOrg : null;
      
      // For user scope, don't pass organization parameter
      const data = selectedScope === 'user'
        ? await githubAPI.getRepositoryDetails(scope, repoName)
        : await githubAPI.getRepositoryDetails(scope, repoName, organization);
      setSelectedRepoDetails(data);
      
      // Initialize selected branches with default branch
      if (data && data.default_branch && data.branches) {
        setSelectedBranches(prev => {
          const newMap = new Map(prev);
          newMap.set(data.full_name, new Set([data.default_branch]));
          return newMap;
        });
      }
    } catch (err) {
      setError(`Failed to load repository details: ${err.message}`);
      console.error('Error loading repository details:', err);
    } finally {
      setLoadingRepoDetails(false);
    }
  }, [selectedScope, selectedOrg]);

  const loadRepositoryDetailsByOwner = async (owner, repoName) => {
    if (!owner || !repoName) return;
    
    try {
      setLoadingRepoDetails(true);
      setError('');
      
      // Call the API directly with owner and repo name
      const response = await fetch(`http://localhost:8000/api/github/repositories/${encodeURIComponent(owner)}/${encodeURIComponent(repoName)}/details`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      setSelectedRepoDetails(data);
      
      // Initialize selected branches with default branch
      if (data && data.default_branch && data.branches) {
        setSelectedBranches(prev => {
          const newMap = new Map(prev);
          newMap.set(data.full_name, new Set([data.default_branch]));
          return newMap;
        });
      }
    } catch (err) {
      setError(`Failed to load repository details: ${err.message}`);
      console.error('Error loading repository details:', err);
    } finally {
      setLoadingRepoDetails(false);
    }
  };

  const loadOrganizationDetails = useCallback(async (orgLogin) => {
    if (!orgLogin) return;
    
    try {
      setError('');
      const data = await githubAPI.getOrganizationDetails(orgLogin);
      setOrgDetails(data);
    } catch (err) {
      setError(`Failed to load organization details: ${err.message}`);
      console.error('Error loading organization details:', err);
    }
  }, []);

  const handleViewOrgDetails = async () => {
    if (!orgDetails) return;
    
    setLoadingOrgDetails(true);
    setShowOrgDetailsModal(true);
    
    try {
      // Load organization secrets, variables, and custom properties
      const [secretsData, variablesData, propertiesData] = await Promise.all([
        githubAPI.getOrganizationSecrets(orgDetails.login),
        githubAPI.getOrganizationVariables(orgDetails.login),
        githubAPI.getOrganizationCustomProperties(orgDetails.login)
      ]);
      
      setOrgSecrets(secretsData.secrets || []);
      setOrgVariables(variablesData.variables || []);
      setOrgCustomProperties(propertiesData.custom_properties || []);
    } catch (err) {
      console.error('Error loading organization details:', err);
      setOrgSecrets([]);
      setOrgVariables([]);
      setOrgCustomProperties([]);
    } finally {
      setLoadingOrgDetails(false);
    }
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleDateString();
  };

  const formatNumber = (num) => {
    if (num === null || num === undefined) return '0';
    if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`;
    if (num >= 1000) return `${(num / 1000).toFixed(1)}K`;
    return num.toString();
  };

  const handleScopeChange = (scope) => {
    setSelectedScope(scope);
    setSelectedOrg('');
    setOrgDetails(null);
    setRepositories([]);
    setSelectedRepo('');
    setSelectedRepoDetails(null);
    setAvailableLanguages([]);
    setSelectedLanguage('');
    setSelectedReposForOnboarding(new Set());
    
    // Automatically load languages and repositories for user scope
    if (scope === 'user') {
      loadLanguagesAndRepositories();
    }
  };

  const handleOrgChange = (orgLogin) => {
    setSelectedOrg(orgLogin);
    setRepositories([]);
    setSelectedRepo('');
    setSelectedRepoDetails(null);
    setAvailableLanguages([]);
    setSelectedLanguage('');
    setSelectedReposForOnboarding(new Set());
    
    if (orgLogin) {
      loadOrganizationDetails(orgLogin);
      loadLanguages(orgLogin);
    } else {
      setOrgDetails(null);
    }
  };

  const handleLanguageFilter = (language) => {
    setSelectedLanguage(language);
    setSelectedRepo('');
    
    // For user scope with loaded repositories, filter client-side
    if (selectedScope === 'user' && repositories.length > 0) {
      // Don't clear repositories, just update the selected language
      // The filtering will happen in the render via .filter()
      return;
    }
    
    // For organization scope, make API call
    setRepositories([]);
    if (language && language.trim() !== '') {
      loadRepositories(language);
    }
  };

  const handleRepoDropdownChange = (repoName) => {
    setSelectedRepo(repoName);
    setSelectedRepoDetails(null);
    
    if (repoName) {
      loadRepositoryDetails(repoName);
    }
  };

  const handleViewRepoDetails = (repo) => {
    // Load and show details without changing the dropdown selection
    setSelectedRepoDetails(null);
    setViewingRepoName(repo.name);
    
    if (repo && repo.full_name) {
      // Extract owner from full_name (format: owner/repo-name)
      const owner = repo.full_name.split('/')[0];
      loadRepositoryDetailsByOwner(owner, repo.name);
    }
  };

  const loadRepositoryBranches = async (repoFullName) => {
    try {
      const response = await fetch(`/api/github/repositories/${encodeURIComponent(repoFullName)}/branches`, {
        credentials: 'include'
      });
      
      if (!response.ok) {
        throw new Error(`Failed to fetch branches: ${response.status}`);
      }
      
      const branches = await response.json();
      setRepositoryBranches(prev => new Map(prev).set(repoFullName, branches));
      
      // Initialize selected branches for this repo with default branch
      const repo = repositories.find(r => r.full_name === repoFullName);
      if (repo && repo.default_branch) {
        const defaultBranch = branches.find(b => b.name === repo.default_branch);
        if (defaultBranch) {
          setSelectedBranches(prev => {
            const newMap = new Map(prev);
            newMap.set(repoFullName, new Set([repo.default_branch]));
            return newMap;
          });
        }
      }
      
      return branches;
    } catch (err) {
      console.error(`Error loading branches for ${repoFullName}:`, err);
      return [];
    }
  };

  const handleRepositoryToggle = (repo) => {
    const newSelected = new Set(selectedReposForOnboarding);
    if (newSelected.has(repo.id)) {
      newSelected.delete(repo.id);
      // Also clear selected branches for this repo
      setSelectedBranches(prev => {
        const newMap = new Map(prev);
        newMap.delete(repo.full_name);
        return newMap;
      });
    } else {
      newSelected.add(repo.id);
      // Load branches for this repository if not already loaded
      if (!repositoryBranches.has(repo.full_name)) {
        loadRepositoryBranches(repo.full_name);
      }
    }
    setSelectedReposForOnboarding(newSelected);
  };

  const handleBranchToggle = (repoFullName, branchName) => {
    setSelectedBranches(prev => {
      const newMap = new Map(prev);
      const branches = newMap.get(repoFullName) || new Set();
      const newBranches = new Set(branches);
      
      if (newBranches.has(branchName)) {
        newBranches.delete(branchName);
      } else {
        newBranches.add(branchName);
      }
      
      newMap.set(repoFullName, newBranches);
      return newMap;
    });
  };

  const handleSelectAllBranches = (repoFullName) => {
    const branches = repositoryBranches.get(repoFullName) || [];
    setSelectedBranches(prev => {
      const newMap = new Map(prev);
      newMap.set(repoFullName, new Set(branches.map(b => b.name)));
      return newMap;
    });
  };

  const handleDeselectAllBranches = (repoFullName) => {
    setSelectedBranches(prev => {
      const newMap = new Map(prev);
      newMap.set(repoFullName, new Set());
      return newMap;
    });
  };

  const handleSelectAllRepositories = () => {
    const filteredRepos = repositories.filter(repo => selectedRepo === '' || repo.name === selectedRepo);
    const newSelected = new Set([...selectedReposForOnboarding, ...filteredRepos.map(repo => repo.id)]);
    setSelectedReposForOnboarding(newSelected);
    
    // Load branches for newly selected repositories
    filteredRepos.forEach(repo => {
      if (!repositoryBranches.has(repo.full_name)) {
        loadRepositoryBranches(repo.full_name);
      }
    });
  };

  const handleDeselectAllRepositories = () => {
    setSelectedReposForOnboarding(new Set());
  };

  const handleOnboardSelected = async () => {
    const selectedRepos = repositories.filter(repo => selectedReposForOnboarding.has(repo.id));
    
    // Build repository list with their selected branches
    const repositoriesWithBranches = selectedRepos.map(repo => {
      const branches = selectedBranches.get(repo.full_name);
      return {
        repository: repo.full_name,
        branches: branches && branches.size > 0 
          ? Array.from(branches) 
          : [repo.default_branch] // Default to default branch if none selected
      };
    });
    
    // Open the modal
    setShowOnboardingModal(true);
    setOnboardingScanResults(null);
    setScanningRepos(true);
    
    try {
      // Call the backend API to scan repositories with branch selection
      const response = await fetch('http://localhost:8000/api/onboarding/scan', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          repositories: repositoriesWithBranches
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to scan repositories');
      }

      const data = await response.json();
      setOnboardingScanResults(data);
    } catch (err) {
      setError(`Scan failed: ${err.message}`);
    } finally {
      setScanningRepos(false);
    }
  };

  const handleCloseOnboardingModal = () => {
    setShowOnboardingModal(false);
    setOnboardingScanResults(null);
  };

  const handleMigratePolaris = async (repository, filePath) => {
    try {
      setMigratingPolaris(true);
      setMigrationResult(null);
      setShowMigrationModal(true);

      const response = await fetch('http://localhost:8000/api/polaris/convert', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          repository: repository,
          file_path: filePath
        })
      });

      const data = await response.json();
      
      if (data.success) {
        setMigrationResult({
          success: true,
          repository: repository,
          originalFile: filePath,
          coverityYaml: data.coverity_yaml,
          polarisYaml: data.polaris_yaml,
          metadata: data.metadata
        });
      } else {
        setMigrationResult({
          success: false,
          error: data.error || 'Conversion failed'
        });
      }
    } catch (err) {
      setMigrationResult({
        success: false,
        error: err.message
      });
    } finally {
      setMigratingPolaris(false);
    }
  };

  const handleCloseMigrationModal = () => {
    setShowMigrationModal(false);
    setMigrationResult(null);
  };

  const handleDownloadCoverityYaml = () => {
    if (migrationResult && migrationResult.coverityYaml) {
      const blob = new Blob([migrationResult.coverityYaml], { type: 'text/yaml' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'coverity.yaml';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    }
  };

  const handleCreatePullRequest = async () => {
    if (!migrationResult || !migrationResult.coverityYaml) return;
    
    try {
      setMigratingPolaris(true); // Show loading state
      
      const response = await fetch('http://localhost:8000/api/polaris/create-pr', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          repository: migrationResult.repository,
          coverity_yaml_content: migrationResult.coverityYaml,
          original_polaris_file: migrationResult.originalFile
        })
      });

      const data = await response.json();
      
      if (data.success) {
        // Update migration result to show PR was created
        setMigrationResult(prev => ({
          ...prev,
          pullRequestUrl: data.pull_request_url,
          branchName: data.branch_name,
          pullRequestCreated: true
        }));
        
        // Open the PR in a new tab without using alert
        setTimeout(() => {
          window.open(data.pull_request_url, '_blank');
        }, 100);
      } else {
        // Update migration result to show error
        setMigrationResult(prev => ({
          ...prev,
          pullRequestError: data.error
        }));
      }
    } catch (err) {
      // Update migration result to show error
      setMigrationResult(prev => ({
        ...prev,
        pullRequestError: err.message
      }));
    } finally {
      setMigratingPolaris(false);
    }
  };

  const renderYamlWithHighlight = (yamlContent) => {
    if (!yamlContent) return null;
    
    // Split into lines and add syntax highlighting
    const lines = yamlContent.split('\n');
    return lines.map((line, idx) => {
      // Handle empty lines
      if (line.trim() === '') {
        return <div key={idx} style={{ height: '1.8em' }}>&nbsp;</div>;
      }
      
      // Highlight comments (lines starting with #)
      if (line.trim().startsWith('#')) {
        return <div key={idx} style={{ color: '#6a9955', whiteSpace: 'pre' }}>{line}</div>;
      }
      
      // Highlight keys (text before colon)
      const keyMatch = line.match(/^(\s*)([a-zA-Z0-9_-]+)(\s*:)/);
      if (keyMatch) {
        const indent = keyMatch[1];
        const key = keyMatch[2];
        const colon = keyMatch[3];
        const rest = line.substring(keyMatch[0].length);
        
        return (
          <div key={idx} style={{ whiteSpace: 'pre' }}>
            <span style={{ color: '#d4d4d4' }}>{indent}</span>
            <span style={{ color: '#9cdcfe' }}>{key}</span>
            <span style={{ color: '#d4d4d4' }}>{colon}</span>
            <span style={{ color: '#ce9178' }}>{rest}</span>
          </div>
        );
      }
      
      // Highlight list items (lines starting with -)
      if (line.trim().startsWith('-')) {
        return (
          <div key={idx} style={{ color: '#d4d4d4', whiteSpace: 'pre' }}>{line}</div>
        );
      }
      
      // Default rendering with preserved whitespace
      return <div key={idx} style={{ color: '#d4d4d4', whiteSpace: 'pre' }}>{line}</div>;
    });
  };

  const refreshData = () => {
    if (selectedScope === 'user') {
      loadLanguages();
    } else {
      checkTokenAndLoadData();
    }
  };

  // Show loading state while checking token
  if (loading && !tokenStatus) {
    return (
      <div className="github-organizations">
        <div className="loading-container">
          <div className="loading-spinner"></div>
          <p>Checking GitHub token status...</p>
        </div>
      </div>
    );
  }
  
  if (!tokenStatus?.has_token || !tokenStatus?.is_valid) {
    return (
      <div className="github-organizations">
        <div className="github-header">
          <h1>🐙 GitHub Organizations</h1>
          <p>Manage and explore your GitHub organizations and repositories</p>
        </div>

        <div className="token-setup-prompt">
          <div className="setup-card">
            <h2>🔑 GitHub Token Required</h2>
            
            {!tokenStatus?.has_token ? (
              <div className="setup-message">
                <p>To explore GitHub organizations and repositories, you need to add a GITHUB_TOKEN secret.</p>
                <div className="setup-steps">
                  <h3>Setup Steps:</h3>
                  <ol>
                    <li>Go to the <strong>🔐 Secrets Management</strong> tab</li>
                    <li>Click <strong>"+ Add New Secret"</strong></li>
                    <li>Set the name to: <code>GITHUB_TOKEN</code></li>
                    <li>Set the value to your GitHub Personal Access Token</li>
                    <li>Add a description (optional)</li>
                    <li>Click <strong>"Create Secret"</strong></li>
                    <li>Return to this page and click <strong>"Refresh"</strong></li>
                  </ol>
                </div>
              </div>
            ) : (
              <div className="setup-message error">
                <p>Your GITHUB_TOKEN exists but is invalid or expired.</p>
                <div className="setup-steps">
                  <h3>Fix Steps:</h3>
                  <ol>
                    <li>Go to the <strong>🔐 Secrets Management</strong> tab</li>
                    <li>Find the <strong>GITHUB_TOKEN</strong> secret</li>
                    <li>Click <strong>"✏️ Edit"</strong></li>
                    <li>Update the value with a valid GitHub Personal Access Token</li>
                    <li>Click <strong>"Save"</strong></li>
                    <li>Return to this page and click <strong>"Refresh"</strong></li>
                  </ol>
                </div>
              </div>
            )}

            <div className="token-info">
              <h3>📋 How to create a GitHub Personal Access Token:</h3>
              <ol>
                <li>Go to <a href="https://github.com/settings/tokens" target="_blank" rel="noopener noreferrer">GitHub Settings → Personal Access Tokens</a></li>
                <li>Click <strong>"Generate new token"</strong></li>
                <li>Give it a name (e.g., "Organization Explorer")</li>
                <li>Select scopes: <code>read:org</code>, <code>read:user</code>, <code>repo</code></li>
                <li>Click <strong>"Generate token"</strong></li>
                <li>Copy the token (you won't see it again!)</li>
              </ol>
            </div>

            <div className="setup-actions">
              <button onClick={refreshData} className="refresh-btn">
                🔄 Refresh
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="github-organizations">
      <div className="github-header">
        <h1>🐙 GitHub Organizations</h1>
        <p>Explore and manage your GitHub organizations and repositories</p>
        
        {userInfo && (
          <div className="user-info">
            <img src={userInfo.avatar_url} alt={userInfo.login} className="user-avatar" />
            <div className="user-details">
              <span className="user-name">{userInfo.name || userInfo.login}</span>
              <span className="user-login">@{userInfo.login}</span>
            </div>
            <button onClick={refreshData} className="refresh-btn" title="Refresh data">
              🔄
            </button>
          </div>
        )}
      </div>

      {error && <div className="error">{error}</div>}

      {loading ? (
        <div className="loading">Loading data...</div>
      ) : (
        <div className="github-content">
          {/* Scope Selection */}
          <div className="scope-selector">
            <h2>📂 Repository Scope</h2>
            <div className="scope-options">
              <label className="scope-option">
                <input
                  type="radio"
                  value="organization"
                  checked={selectedScope === 'organization'}
                  onChange={(e) => handleScopeChange(e.target.value)}
                />
                <span className="scope-label">
                  🏢 Organization Repositories
                  <small>Browse repositories within a specific organization</small>
                </span>
              </label>
              <label className="scope-option">
                <input
                  type="radio"
                  value="user"
                  checked={selectedScope === 'user'}
                  onChange={(e) => handleScopeChange(e.target.value)}
                />
                <span className="scope-label">
                  👤 All My Repositories
                  <small>Browse all repositories you have access to</small>
                </span>
              </label>
            </div>
          </div>

          {/* Organization Selection (only shown when organization scope is selected) */}
          {selectedScope === 'organization' && (
            <div className="org-selector">
              <h2>🏢 Select Organization ({organizations.length} found)</h2>
              <select 
                value={selectedOrg} 
                onChange={(e) => handleOrgChange(e.target.value)}
                className="org-select"
              >
                <option value="">-- Select an organization --</option>
                {organizations.map(org => (
                  <option key={org.id} value={org.login}>
                    {org.name || org.login}
                    {org.description && ` - ${org.description.substring(0, 50)}${org.description.length > 50 ? '...' : ''}`}
                  </option>
                ))}
              </select>

              {organizations.length === 0 && (
                <div className="no-organizations">
                  <p>No organizations found for your GitHub account.</p>
                  <p>You may need to be a member of an organization or have the appropriate permissions.</p>
                </div>
              )}
            </div>
          )}

          {/* User Repositories (shown when user scope is selected) */}
          {selectedScope === 'user' && (
            <div className="user-repos-section">
              <div className="user-repos-header">
                <h2>👤 Your Repositories</h2>
                <p>Browse all repositories you have access to</p>
                {loadingLanguages ? (
                  <div className="loading">🔄 Loading your repositories...</div>
                ) : availableLanguages.length === 0 ? (
                  <button onClick={loadLanguages} className="load-languages-btn">
                    🔄 Load Programming Languages & Repositories
                  </button>
                ) : (
                  <div className="success-message">
                    ✅ Loaded {availableLanguages.length} programming languages and {repositories.length} repositories
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Organization Details */}
          {selectedScope === 'organization' && selectedOrg && orgDetails && (
            <div className="org-details">
              <div className="org-info">
                <h2>
                  {orgDetails.avatar_url && (
                    <img src={orgDetails.avatar_url} alt={orgDetails.name} className="org-avatar" />
                  )}
                  {orgDetails.name || orgDetails.login}
                </h2>
                {orgDetails.description && <p className="org-description">{orgDetails.description}</p>}
                
                <div className="org-stats">
                  <div className="stat-item">
                    <span className="stat-label">Public Repos:</span>
                    <span className="stat-value">{formatNumber(orgDetails.public_repos)}</span>
                  </div>
                  <div className="stat-item">
                    <span className="stat-label">Followers:</span>
                    <span className="stat-value">{formatNumber(orgDetails.followers)}</span>
                  </div>
                  <div className="stat-item">
                    <span className="stat-label">Following:</span>
                    <span className="stat-value">{formatNumber(orgDetails.following)}</span>
                  </div>
                  <div className="stat-item">
                    <span className="stat-label">Created:</span>
                    <span className="stat-value">{formatDate(orgDetails.created_at)}</span>
                  </div>
                </div>

                <div className="org-actions">
                  <button 
                    onClick={handleViewOrgDetails}
                    className="repo-link"
                  >
                    📄 Details
                  </button>
                  <a href={orgDetails.html_url} target="_blank" rel="noopener noreferrer" className="repo-link">
                    🔗 View on GitHub
                  </a>
                </div>
              </div>
            </div>
          )}

          {/* Repositories Section */}
          {((selectedScope === 'organization' && selectedOrg) || selectedScope === 'user') && (availableLanguages.length > 0 || repositories.length > 0) && (
            <div className="repositories-section">
              <h2>
                📚 All Repositories ({repositories.length} found)
                {selectedScope === 'user' ? ' - All Your Repositories' : ` - ${selectedOrg}`}
              </h2>
              
              {loadingRepos ? (
                <div className="loading">Loading repositories...</div>
              ) : repositories.length === 0 ? (
                <div className="no-repositories">
                  <p>No repositories found for the selected criteria.</p>
                  <p>
                    {selectedLanguage === 'all' 
                      ? 'Try selecting a specific programming language.'
                      : `No repositories found for language: ${selectedLanguage}`
                    }
                  </p>
                </div>
              ) : (
                <>
                  {/* Repository Selector */}
                  <div className="repo-selector">
                    <select 
                      value={selectedRepo} 
                      onChange={(e) => handleRepoDropdownChange(e.target.value)}
                      className="repo-select"
                    >
                      <option value="">-- Show all repositories --</option>
                      {repositories.map(repo => (
                        <option key={repo.id} value={repo.name}>
                          {repo.name}
                          {repo.description && ` - ${repo.description.substring(0, 50)}${repo.description.length > 50 ? '...' : ''}`}
                        </option>
                      ))}
                    </select>
                  </div>

                  {/* Language Filter */}
                  {availableLanguages.length > 0 && (
                    <div className="language-filter">
                      <label htmlFor="language-select">Filter by Programming Language:</label>
                      <select 
                        id="language-select"
                        value={selectedLanguage} 
                        onChange={(e) => handleLanguageFilter(e.target.value)}
                        className="language-select"
                      >
                        <option value="all">All Languages ({availableLanguages.length} total)</option>
                        {availableLanguages.map(language => (
                          <option key={language.name || language} value={language.name || language}>
                            {language.name || language}
                          </option>
                        ))}
                      </select>
                    </div>
                  )}

                  {/* Additional Filters */}
                  <div className="additional-filters">
                    <label className="filter-checkbox">
                      <input
                        type="checkbox"
                        checked={filterPolarisFiles}
                        onChange={(e) => setFilterPolarisFiles(e.target.checked)}
                      />
                      <span>Only repos with polaris.yml/polaris.yaml</span>
                    </label>
                    <label className="filter-checkbox">
                      <input
                        type="checkbox"
                        checked={filterWithWorkflows}
                        onChange={(e) => setFilterWithWorkflows(e.target.checked)}
                      />
                      <span>Only repos with GitHub workflow files</span>
                    </label>
                  </div>

                  {/* Repository Onboarding Controls */}
                  {repositories.length > 0 && (
                    <div className="onboarding-controls">
                      <div className="onboarding-header">
                        <h3>Repository Onboarding</h3>
                        <p>Select repositories to onboard to your development environment</p>
                      </div>
                      
                      <div className="onboarding-actions">
                        <div className="selection-controls">
                          <button 
                            onClick={handleSelectAllRepositories}
                            className="select-btn select-all"
                            disabled={repositories.filter(repo => selectedRepo === '' || repo.name === selectedRepo).length === 0}
                          >
                            ✅ Select All
                          </button>
                          <button 
                            onClick={handleDeselectAllRepositories}
                            className="select-btn deselect-all"
                            disabled={selectedReposForOnboarding.size === 0}
                          >
                            ❌ Deselect All
                          </button>
                        </div>
                        
                        <div className="onboard-action">
                          <button 
                            onClick={handleOnboardSelected}
                            className="onboard-btn"
                            disabled={selectedReposForOnboarding.size === 0}
                          >
                            🚀 Onboard Selected ({selectedReposForOnboarding.size})
                          </button>
                        </div>
                      </div>
                    </div>
                  )}

                  <div className="repositories-grid">
                    {repositories.length === 0 && selectedLanguage !== 'all' && selectedLanguage !== '' ? (
                      <div className="no-repositories">
                        <p>No repositories found for the selected language: <strong>{selectedLanguage}</strong></p>
                        <p>Try selecting a different language or "All Languages" to see all repositories.</p>
                      </div>
                    ) : (
                      repositories
                        .filter(repo => {
                          // Filter by selected repository from dropdown
                          if (selectedRepo !== '' && repo.name !== selectedRepo) {
                            return false;
                          }
                          // Filter by language - for user scope, filter client-side
                          if (selectedScope === 'user' && selectedLanguage && selectedLanguage !== 'all') {
                            return repo.language === selectedLanguage;
                          }
                          // Filter by polaris files in root
                          if (filterPolarisFiles) {
                            if (!repo.workflow_info?.has_polaris_in_root) {
                              return false;
                            }
                          }
                          
                          // Filter by repositories with workflow files
                          if (filterWithWorkflows) {
                            if (!repo.workflow_info?.has_workflows) {
                              return false;
                            }
                          }
                          
                          return true;
                        })
                        .slice(0, 20)
                        .map(repo => (
                          <div key={repo.id} className="repo-card">
                        <div className="repo-header">
                          <div className="repo-header-left">
                            <input
                              type="checkbox"
                              checked={selectedReposForOnboarding.has(repo.id)}
                              onChange={() => handleRepositoryToggle(repo)}
                              className="repo-checkbox"
                              title="Select for onboarding"
                            />
                            <h3 className="repo-name">
                              <a href={repo.html_url} target="_blank" rel="noopener noreferrer">
                                {repo.name}
                              </a>
                            </h3>
                          </div>
                          <div className="repo-badges">
                            {repo.private && <span className="badge private">🔒 Private</span>}
                            {repo.fork && <span className="badge fork">🍴 Fork</span>}
                            {repo.archived && <span className="badge archived">📦 Archived</span>}
                          </div>
                        </div>

                        {repo.description && (
                          <p className="repo-description">{repo.description}</p>
                        )}

                        <div className="repo-stats">
                          <div className="stat-item">
                            <span className="stat-icon">⭐</span>
                            <span className="stat-value">{formatNumber(repo.stargazers_count)}</span>
                          </div>
                          <div className="stat-item">
                            <span className="stat-icon">🍴</span>
                            <span className="stat-value">{formatNumber(repo.forks_count)}</span>
                          </div>
                          <div className="stat-item">
                            <span className="stat-icon">👁️</span>
                            <span className="stat-value">{formatNumber(repo.watchers_count)}</span>
                          </div>
                          <div className="stat-item">
                            <span className="stat-icon">🐛</span>
                            <span className="stat-value">{formatNumber(repo.open_issues_count)}</span>
                          </div>
                        </div>

                        <div className="repo-metadata">
                          {repo.languages_detail && Object.keys(repo.languages_detail).length > 0 ? (
                            <div className="metadata-item languages-list">
                              {Object.entries(repo.languages_detail)
                                .sort(([,a], [,b]) => b - a)
                                .slice(0, 3)
                                .map(([lang]) => (
                                  <span key={lang} className="language-tag">
                                    <span className="language-dot" style={{backgroundColor: getLanguageColor(lang)}}></span>
                                    <span className="language-name">{lang}</span>
                                  </span>
                                ))}
                              {Object.keys(repo.languages_detail).length > 3 && (
                                <span className="language-tag more">+{Object.keys(repo.languages_detail).length - 3}</span>
                              )}
                            </div>
                          ) : repo.language && (
                            <div className="metadata-item">
                              <span className="language-dot" style={{backgroundColor: getLanguageColor(repo.language)}}></span>
                              <span className="language-name">{repo.language}</span>
                            </div>
                          )}
                          {repo.license && (
                            <div className="metadata-item">
                              <span className="license">📄 {repo.license}</span>
                            </div>
                          )}
                          <div className="metadata-item">
                            <span className="update-time">🕒 Updated {formatDate(repo.updated_at)}</span>
                          </div>
                        </div>

                        {repo.topics && repo.topics.length > 0 && (
                          <div className="repo-topics">
                            {repo.topics.slice(0, 5).map(topic => (
                              <span key={topic} className="topic-tag">{topic}</span>
                            ))}
                            {repo.topics.length > 5 && (
                              <span className="topic-tag more">+{repo.topics.length - 5} more</span>
                            )}
                          </div>
                        )}

                        <div className="repo-actions">
                          <button 
                            onClick={() => handleViewRepoDetails(repo)}
                            className="details-btn repo-link"
                            disabled={loadingRepoDetails && viewingRepoName === repo.name}
                          >
                            {loadingRepoDetails && viewingRepoName === repo.name ? '⏳ Loading...' : '📄 Details'}
                          </button>
                          <a href={repo.html_url} target="_blank" rel="noopener noreferrer" className="repo-link">
                            🔗 View
                          </a>
                          <a href={repo.clone_url} className="repo-link" title="Clone URL">
                            📥 Clone
                          </a>
                        </div>
                      </div>
                        ))
                    )}
                  </div>

                  {repositories.filter(repo => {
                    if (selectedRepo !== '' && repo.name !== selectedRepo) return false;
                    if (selectedScope === 'user' && selectedLanguage && selectedLanguage !== 'all') {
                      return repo.language === selectedLanguage;
                    }
                    return true;
                  }).length > 20 && (
                    <div className="pagination-info">
                      <p>Showing first 20 repositories. Use the dropdown above to filter or view specific repositories.</p>
                    </div>
                  )}
                </>
              )}
            </div>
          )}

          {/* Repository Details Modal */}
          {viewingRepoName && selectedRepoDetails && (
            <div className="repo-details-modal">
              <div className="repo-details-content">
                <div className="repo-details-header">
                  <h2>📄 Repository Details: {viewingRepoName}</h2>
                  <button 
                    className="close-btn" 
                    onClick={() => {
                      setViewingRepoName('');
                      setSelectedRepoDetails(null);
                    }}
                    title="Close"
                  >
                    ✕
                  </button>
                </div>
                
                {loadingRepoDetails ? (
                  <div className="repo-details-body">
                    <div className="loading">Loading repository details...</div>
                  </div>
                ) : (
                  <div className="repo-details-body">
                    <div className="details-grid">
                      <div className="detail-section">
                        <h3>📋 Basic Information</h3>
                        <div className="detail-item">
                          <strong>Full Name:</strong> {selectedRepoDetails.full_name}
                        </div>
                        <div className="detail-item">
                          <strong>Description:</strong> {selectedRepoDetails.description || 'No description provided'}
                        </div>
                        
                        <div className="repo-stats" style={{marginTop: '15px', marginBottom: '15px'}}>
                          <div className="stat-item">
                            <span className="stat-icon">⭐</span>
                            <span className="stat-value">{formatNumber(selectedRepoDetails.stargazers_count || 0)}</span>
                          </div>
                          <div className="stat-item">
                            <span className="stat-icon">🍴</span>
                            <span className="stat-value">{formatNumber(selectedRepoDetails.forks_count || 0)}</span>
                          </div>
                          <div className="stat-item">
                            <span className="stat-icon">👁️</span>
                            <span className="stat-value">{formatNumber(selectedRepoDetails.watchers_count || 0)}</span>
                          </div>
                          <div className="stat-item">
                            <span className="stat-icon">🐛</span>
                            <span className="stat-value">{formatNumber(selectedRepoDetails.open_issues_count || 0)}</span>
                          </div>
                        </div>

                        <div className="repo-metadata">
                          {selectedRepoDetails.license && (
                            <div className="metadata-item">
                              <span className="license">� {selectedRepoDetails.license.name}</span>
                            </div>
                          )}
                          <div className="metadata-item">
                            <span className="update-time">🕒 Updated {formatDate(selectedRepoDetails.updated_at)}</span>
                          </div>
                          <div className="metadata-item">
                            <span className="update-time">🚀 Pushed {formatDate(selectedRepoDetails.pushed_at)}</span>
                          </div>
                          <div className="metadata-item">
                            <span className="update-time">📅 Created {formatDate(selectedRepoDetails.created_at)}</span>
                          </div>
                        </div>

                        <div className="detail-item" style={{marginTop: '15px'}}>
                          <strong>Default Branch:</strong> {selectedRepoDetails.default_branch}
                        </div>
                        <div className="detail-item">
                          <strong>Size:</strong> {formatNumber(selectedRepoDetails.size)} KB
                        </div>
                      </div>

                      {/* Branches Section for Onboarding Selection */}
                      {selectedRepoDetails.branches && selectedRepoDetails.branches.length > 0 && (
                        <div className="detail-section">
                          <h3>🌿 Branches ({selectedRepoDetails.branches.length})</h3>
                          <div className="branches-onboarding">
                            <div className="branches-header">
                              <p style={{marginBottom: '10px', color: '#666'}}>
                                Select branches to include in onboarding scan:
                              </p>
                              <div className="branch-selection-actions">
                                <button
                                  className="btn-secondary"
                                  onClick={() => {
                                    const allBranchNames = selectedRepoDetails.branches.map(b => b.name);
                                    setSelectedBranches(prev => {
                                      const newMap = new Map(prev);
                                      newMap.set(selectedRepoDetails.full_name, new Set(allBranchNames));
                                      return newMap;
                                    });
                                  }}
                                >
                                  Select All
                                </button>
                                <button
                                  className="btn-secondary"
                                  onClick={() => {
                                    setSelectedBranches(prev => {
                                      const newMap = new Map(prev);
                                      newMap.set(selectedRepoDetails.full_name, new Set([selectedRepoDetails.default_branch]));
                                      return newMap;
                                    });
                                  }}
                                >
                                  Default Only
                                </button>
                                <button
                                  className="btn-secondary"
                                  onClick={() => {
                                    setSelectedBranches(prev => {
                                      const newMap = new Map(prev);
                                      newMap.set(selectedRepoDetails.full_name, new Set());
                                      return newMap;
                                    });
                                  }}
                                >
                                  Clear All
                                </button>
                              </div>
                            </div>
                            <div className="branches-list">
                              {selectedRepoDetails.branches.map(branch => {
                                const isSelected = selectedBranches.get(selectedRepoDetails.full_name)?.has(branch.name) || false;
                                const isDefault = branch.name === selectedRepoDetails.default_branch;
                                return (
                                  <div key={branch.name} className={`branch-item ${isSelected ? 'selected' : ''}`}>
                                    <label className="branch-checkbox-label">
                                      <input
                                        type="checkbox"
                                        checked={isSelected}
                                        onChange={() => {
                                          setSelectedBranches(prev => {
                                            const newMap = new Map(prev);
                                            const branches = newMap.get(selectedRepoDetails.full_name) || new Set();
                                            const newBranches = new Set(branches);
                                            
                                            if (newBranches.has(branch.name)) {
                                              newBranches.delete(branch.name);
                                            } else {
                                              newBranches.add(branch.name);
                                            }
                                            
                                            newMap.set(selectedRepoDetails.full_name, newBranches);
                                            return newMap;
                                          });
                                        }}
                                      />
                                      <span className="branch-name">
                                        {branch.name}
                                        {isDefault && <span className="default-badge">DEFAULT</span>}
                                      </span>
                                    </label>
                                    <span className="branch-commit-sha" title={`Latest commit: ${branch.commit?.sha || 'N/A'}`}>
                                      {branch.commit?.sha?.substring(0, 7) || 'N/A'}
                                    </span>
                                  </div>
                                );
                              })}
                            </div>
                            <div className="selected-branches-count">
                              {(selectedBranches.get(selectedRepoDetails.full_name)?.size || 0)} of {selectedRepoDetails.branches.length} branches selected
                            </div>
                          </div>
                        </div>
                      )}

                      {selectedRepoDetails.topics && selectedRepoDetails.topics.length > 0 && (
                        <div className="detail-section">
                          <h3>🏷️ Topics</h3>
                          <div className="topics">
                            {selectedRepoDetails.topics.map(topic => (
                              <span key={topic} className="topic-tag">{topic}</span>
                            ))}
                          </div>
                        </div>
                      )}

                      <div className="detail-section">
                        <h3>🔧 Custom Properties</h3>
                        {selectedRepoDetails.custom_properties && Object.keys(selectedRepoDetails.custom_properties).length > 0 ? (
                          <table className="custom-properties-table">
                            <thead>
                              <tr>
                                <th>Property</th>
                                <th>Value</th>
                              </tr>
                            </thead>
                            <tbody>
                              {Object.entries(selectedRepoDetails.custom_properties).map(([key, value]) => (
                                <tr key={key}>
                                  <td><strong>{key}</strong></td>
                                  <td>{value}</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        ) : (
                          <p style={{color: '#666', fontStyle: 'italic'}}>No custom properties defined for this repository.</p>
                        )}
                      </div>

                      {selectedRepoDetails.latest_release && (
                        <div className="detail-section">
                          <h3>🚀 Latest Release</h3>
                          <div className="release-info">
                            <div className="detail-item">
                              <strong>Version:</strong> {selectedRepoDetails.latest_release.tag_name}
                            </div>
                            <div className="detail-item">
                              <strong>Name:</strong> {selectedRepoDetails.latest_release.name || 'N/A'}
                            </div>
                            <div className="detail-item">
                              <strong>Published:</strong> {new Date(selectedRepoDetails.latest_release.published_at).toLocaleDateString()}
                            </div>
                            {selectedRepoDetails.latest_release.body && (
                              <div className="detail-item">
                                <strong>Release Notes:</strong>
                                <div className="release-notes">{selectedRepoDetails.latest_release.body.substring(0, 200)}{selectedRepoDetails.latest_release.body.length > 200 ? '...' : ''}</div>
                              </div>
                            )}
                            <div className="detail-item">
                              <a href={selectedRepoDetails.latest_release.html_url} target="_blank" rel="noopener noreferrer" className="repo-link">
                                View Release →
                              </a>
                            </div>
                          </div>
                        </div>
                      )}

                      {selectedRepoDetails.languages_detail && Object.keys(selectedRepoDetails.languages_detail).length > 0 && (
                        <div className="detail-section">
                          <h3>💻 Programming Languages</h3>
                          <div className="languages-breakdown">
                            {Object.entries(selectedRepoDetails.languages_detail)
                              .sort(([,a], [,b]) => b - a)
                              .map(([lang, bytes], index) => {
                                const totalBytes = Object.values(selectedRepoDetails.languages_detail).reduce((a, b) => a + b, 0);
                                const percentage = totalBytes > 0 ? ((bytes / totalBytes) * 100).toFixed(1) : 0;
                                const isPrimary = index === 0; // First language (highest percentage) is primary
                                return (
                                  <div key={lang} className={`language-item ${isPrimary ? 'primary-language' : ''}`}>
                                    <span className="language-dot" style={{backgroundColor: getLanguageColor(lang)}}></span>
                                    <span className="language-name">{lang} {isPrimary && <span className="primary-badge">Primary</span>}</span>
                                    <span className="language-percentage">{percentage}%</span>
                                    <div className="language-bar">
                                      <div 
                                        className="language-fill" 
                                        style={{ width: `${percentage}%`, backgroundColor: getLanguageColor(lang) }}
                                      ></div>
                                    </div>
                                  </div>
                                );
                              })}
                          </div>
                        </div>
                      )}

                      {selectedRepoDetails.workflow_info && selectedRepoDetails.workflow_info.workflow_files && selectedRepoDetails.workflow_info.workflow_files.length > 0 ? (
                        <div className="detail-section">
                          <h3>⚡ GitHub Actions Workflows ({selectedRepoDetails.workflow_info.total_count})</h3>
                          <div className="workflows-list">
                            {selectedRepoDetails.workflow_info.workflow_files.map((workflow, index) => (
                              <div key={index} className="workflow-item">
                                <div className="workflow-header">
                                  <span className="workflow-name">📄 {workflow.name}</span>
                                  <div className="workflow-actions">
                                    <span className="workflow-size">({(workflow.size / 1024).toFixed(1)} KB)</span>
                                    <a href={workflow.html_url} target="_blank" rel="noopener noreferrer" className="workflow-link">
                                      View File
                                    </a>
                                    {workflow.download_url && (
                                      <a href={workflow.download_url} target="_blank" rel="noopener noreferrer" className="workflow-link download">
                                        Download
                                      </a>
                                    )}
                                  </div>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      ) : (
                        <div className="detail-section">
                          <h3>⚡ GitHub Actions Workflows</h3>
                          <p style={{color: '#666', fontStyle: 'italic'}}>No workflow files found in .github/workflows directory.</p>
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Organization Details Modal */}
          {showOrgDetailsModal && orgDetails && (
            <div className="repo-details-modal">
              <div className="repo-details-content">
                <div className="repo-details-header">
                  <h2>🏢 Organization Details: {orgDetails.name || orgDetails.login}</h2>
                  <button 
                    className="close-btn" 
                    onClick={() => setShowOrgDetailsModal(false)}
                    title="Close"
                  >
                    ✕
                  </button>
                </div>
                
                {loadingOrgDetails ? (
                  <div className="repo-details-body">
                    <div className="loading">Loading organization details...</div>
                  </div>
                ) : (
                  <div className="repo-details-body">
                    <div className="details-grid">
                      {/* Basic Information */}
                      <div className="detail-section">
                        <h3>📋 Basic Information</h3>
                        <div className="detail-item">
                          <strong>Name:</strong> {orgDetails.name || 'N/A'}
                        </div>
                        <div className="detail-item">
                          <strong>Login:</strong> {orgDetails.login}
                        </div>
                        <div className="detail-item">
                          <strong>Description:</strong> {orgDetails.description || 'No description provided'}
                        </div>
                        {orgDetails.location && (
                          <div className="detail-item">
                            <strong>Location:</strong> {orgDetails.location}
                          </div>
                        )}
                        {orgDetails.email && (
                          <div className="detail-item">
                            <strong>Email:</strong> {orgDetails.email}
                          </div>
                        )}
                        {orgDetails.blog && (
                          <div className="detail-item">
                            <strong>Website:</strong> <a href={orgDetails.blog} target="_blank" rel="noopener noreferrer">{orgDetails.blog}</a>
                          </div>
                        )}
                        <div className="detail-item">
                          <strong>Public Repos:</strong> {orgDetails.public_repos || 0}
                        </div>
                        <div className="detail-item">
                          <strong>Created:</strong> {formatDate(orgDetails.created_at)}
                        </div>
                        <div className="detail-item">
                          <strong>Updated:</strong> {formatDate(orgDetails.updated_at)}
                        </div>
                        <div className="detail-item" style={{marginTop: '15px'}}>
                          <a href={orgDetails.html_url} target="_blank" rel="noopener noreferrer" className="repo-link">
                            🔗 View on GitHub
                          </a>
                        </div>
                      </div>

                      {/* Organization Secrets */}
                      <div className="detail-section">
                        <h3>🔐 Organization Secrets</h3>
                        {orgSecrets && orgSecrets.length > 0 ? (
                          <table className="custom-properties-table">
                            <thead>
                              <tr>
                                <th>Secret Name</th>
                                <th>Created</th>
                                <th>Updated</th>
                              </tr>
                            </thead>
                            <tbody>
                              {orgSecrets.map((secret, index) => (
                                <tr key={index}>
                                  <td>{secret.name}</td>
                                  <td>{formatDate(secret.created_at)}</td>
                                  <td>{formatDate(secret.updated_at)}</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        ) : (
                          <p style={{color: '#666', fontStyle: 'italic'}}>No organization secrets found or insufficient permissions.</p>
                        )}
                      </div>

                      {/* Organization Variables */}
                      <div className="detail-section">
                        <h3>📊 Organization Variables</h3>
                        {orgVariables && orgVariables.length > 0 ? (
                          <table className="custom-properties-table">
                            <thead>
                              <tr>
                                <th>Variable Name</th>
                                <th>Value</th>
                              </tr>
                            </thead>
                            <tbody>
                              {orgVariables.map((variable, index) => (
                                <tr key={index}>
                                  <td>{variable.name}</td>
                                  <td>{variable.value}</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        ) : (
                          <p style={{color: '#666', fontStyle: 'italic'}}>No organization variables found or insufficient permissions.</p>
                        )}
                      </div>

                      {/* Custom Properties */}
                      <div className="detail-section">
                        <h3>🏷️ Custom Properties Schema</h3>
                        {orgCustomProperties && orgCustomProperties.length > 0 ? (
                          <table className="custom-properties-table">
                            <thead>
                              <tr>
                                <th>Property Name</th>
                                <th>Type</th>
                                <th>Required</th>
                                <th>Default Value</th>
                              </tr>
                            </thead>
                            <tbody>
                              {orgCustomProperties.map((prop, index) => (
                                <tr key={index}>
                                  <td>{prop.property_name}</td>
                                  <td>{prop.value_type || 'string'}</td>
                                  <td>{prop.required ? 'Yes' : 'No'}</td>
                                  <td>{prop.default_value || 'N/A'}</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        ) : (
                          <p style={{color: '#666', fontStyle: 'italic'}}>No custom properties schema defined for this organization.</p>
                        )}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Onboarding Scanner Modal */}
      {showOnboardingModal && (
        <div className="modal-overlay">
          <div className="modal-content large-modal">
            <div className="modal-header">
              <h2>🚀 Repository Onboarding Scanner</h2>
              <button className="modal-close" onClick={handleCloseOnboardingModal}>×</button>
            </div>
            
            <div className="modal-body">
              {scanningRepos ? (
                <div className="scanning-message">
                  <div className="loading-spinner"></div>
                  <p>Scanning repositories for workflow files and matching with template keywords...</p>
                </div>
              ) : onboardingScanResults ? (
                <div className="scan-results">
                  <div className="results-summary">
                    <div className="summary-card">
                      <span className="summary-label">Repositories Scanned</span>
                      <span className="summary-value">{onboardingScanResults.total_repositories}</span>
                    </div>
                    <div className="summary-card">
                      <span className="summary-label">Templates Used</span>
                      <span className="summary-value">{onboardingScanResults.total_templates_used}</span>
                    </div>
                    {onboardingScanResults.search_all_branches && (
                      <div className="summary-card">
                        <span className="summary-label">Search Mode</span>
                        <span className="summary-value">All Branches</span>
                      </div>
                    )}
                  </div>

                  {/* Show all keywords being searched */}
                  {onboardingScanResults.all_keywords && onboardingScanResults.all_keywords.length > 0 && (
                    <div className="keywords-searched-section">
                      <h4>🔑 Keywords Searched:</h4>
                      <div className="keywords-searched-list">
                        {onboardingScanResults.all_keywords.map((keyword, idx) => (
                          <span key={idx} className="keyword-tag">{keyword}</span>
                        ))}
                      </div>
                    </div>
                  )}

                  <div className="results-list">
                    {onboardingScanResults.results.map((result, idx) => (
                      <div key={idx} className="result-item">
                        <div className="result-header">
                          <h4>📦 {result.repository}</h4>
                          <div className="result-stats">
                            <span className="stat-badge success">{result.workflows_with_matches} with matches</span>
                            <span className="stat-badge warning">{result.workflows_without_matches} without matches</span>
                            <span className="stat-badge info">{result.total_workflows} total workflows</span>
                            {result.branches_scanned && result.branches_scanned > 1 && (
                              <span className="stat-badge branch">{result.branches_scanned} branches</span>
                            )}
                          </div>
                        </div>

                        {result.error ? (
                          <div className="error-message">Error: {result.error}</div>
                        ) : (
                          <div className="workflows-list">
                            {/* Workflows with matches */}
                            {result.workflows.filter(w => w.has_matches).length > 0 && (
                              <div className="workflows-section">
                                <h5>✅ Workflows with Matches ({result.workflows_with_matches})</h5>
                                {result.workflows.filter(w => w.has_matches).map((workflow, widx) => (
                                  <div key={widx} className="workflow-item matched">
                                    <div className="workflow-header">
                                      <div>
                                        <span className="workflow-name">📄 {workflow.name}</span>
                                        {workflow.branch && <span className="workflow-branch"> (Branch: {workflow.branch})</span>}
                                        <span className="workflow-path">{workflow.path}</span>
                                      </div>
                                    </div>
                                    <div className="workflow-matches">
                                      <div className="matched-keywords">
                                        <strong>Keywords:</strong>
                                        {workflow.matched_keywords.map((keyword, kidx) => (
                                          <span key={kidx} className="keyword-tag">{keyword}</span>
                                        ))}
                                      </div>
                                      <div className="matched-templates">
                                        <strong>Matching Templates:</strong>
                                        {workflow.matched_templates.map((template, tidx) => (
                                          <span key={tidx} className="template-tag" title={template.description}>
                                            {template.name}
                                          </span>
                                        ))}
                                      </div>
                                    </div>
                                    <div className="workflow-actions">
                                      <a
                                        href={`https://github.com/${result.repository}/blob/main/${workflow.path}`}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="btn-view-file"
                                      >
                                        👁️ View
                                      </a>
                                      <a
                                        href={`https://raw.githubusercontent.com/${result.repository}/main/${workflow.path}`}
                                        download
                                        className="btn-download-file"
                                      >
                                        ⬇️ Download
                                      </a>
                                      {(workflow.name === 'polaris.yml' || workflow.name === 'polaris.yaml') && (
                                        <button
                                          className="btn-migrate-file"
                                          onClick={() => handleMigratePolaris(result.repository, workflow.path)}
                                        >
                                          🔄 Migrate
                                        </button>
                                      )}
                                    </div>
                                  </div>
                                ))}
                              </div>
                            )}

                            {/* Workflows without matches */}
                            {result.workflows.filter(w => !w.has_matches).length > 0 && (
                              <div className="workflows-section">
                                <h5>❌ Workflows without Matches ({result.workflows_without_matches})</h5>
                                {result.workflows.filter(w => !w.has_matches).map((workflow, widx) => (
                                  <div key={widx} className="workflow-item unmatched">
                                    <div className="workflow-header">
                                      <div>
                                        <span className="workflow-name">📄 {workflow.name}</span>
                                        {workflow.branch && <span className="workflow-branch"> (Branch: {workflow.branch})</span>}
                                        <span className="workflow-path">{workflow.path}</span>
                                      </div>
                                    </div>
                                    {workflow.error && (
                                      <div className="workflow-error">Error: {workflow.error}</div>
                                    )}
                                    <div className="workflow-actions">
                                      <a
                                        href={workflow.html_url || `https://github.com/${result.repository}/blob/main/${workflow.path}`}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="btn-view-file"
                                      >
                                        👁️ View
                                      </a>
                                      <a
                                        href={workflow.download_url || `https://raw.githubusercontent.com/${result.repository}/main/${workflow.path}`}
                                        download
                                        className="btn-download-file"
                                      >
                                        ⬇️ Download
                                      </a>
                                    </div>
                                  </div>
                                ))}
                              </div>
                            )}
                          </div>
                        )}

                        {/* Matched Files by Name */}
                        {result.matched_files && result.matched_files.length > 0 && (
                          <div className="workflows-section">
                            <h5>📁 Files with Matching Keywords in Name ({result.total_matched_files})</h5>
                            {result.matched_files.map((file, fidx) => (
                              <div key={fidx} className="workflow-item matched">
                                <div className="workflow-header">
                                  <div>
                                    <span className="workflow-name">📄 {file.name}</span>
                                    {/* Display branch information */}
                                    {file.branch && <span className="workflow-branch"> (Branch: {file.branch})</span>}
                                    <span className="workflow-path">{file.path}</span>
                                  </div>
                                </div>
                                <div className="workflow-matches">
                                  <div className="matched-keywords">
                                    <strong>Matched Keywords in Filename:</strong>
                                    {file.matched_keywords.map((keyword, kidx) => (
                                      <span key={kidx} className="keyword-tag">{keyword}</span>
                                    ))}
                                  </div>
                                  <div className="matched-templates">
                                    <strong>Matching Templates:</strong>
                                    {file.matched_templates.map((template, tidx) => (
                                      <span key={tidx} className="template-tag" title={template.description}>
                                        {template.name}
                                      </span>
                                    ))}
                                  </div>
                                </div>
                                <div className="workflow-actions">
                                  <a
                                    href={`https://github.com/${result.repository}/blob/${file.branch || 'main'}/${file.path}`}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="btn-view-file"
                                  >
                                    👁️ View
                                  </a>
                                  <a
                                    href={`https://raw.githubusercontent.com/${result.repository}/${file.branch || 'main'}/${file.path}`}
                                    download
                                    className="btn-download-file"
                                  >
                                    ⬇️ Download
                                  </a>
                                  {(file.name === 'polaris.yml' || file.name === 'polaris.yaml') && (
                                    <button
                                      className="btn-migrate-file"
                                      onClick={() => handleMigratePolaris(result.repository, file.path)}
                                    >
                                      🔄 Migrate
                                    </button>
                                  )}
                                </div>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              ) : null}
            </div>
          </div>
        </div>
      )}

      {/* Migration Result Modal */}
      {showMigrationModal && (
        <div className="modal-overlay">
          <div className="modal-content migration-modal">
            <div className="modal-header">
              <h2>🔄 Polaris to Coverity Migration</h2>
              <button className="btn-close-modal" onClick={handleCloseMigrationModal}>✕</button>
            </div>
            <div className="modal-body">
              {migratingPolaris ? (
                <div className="scanning-message">
                  <div className="loading-spinner"></div>
                  <p>Converting Polaris configuration to Coverity format...</p>
                </div>
              ) : migrationResult ? (
                migrationResult.success ? (
                  <div className="files-comparison">
                    <div className="file-side original-file">
                      <div className="yaml-header">
                        <h4>📄 Original {migrationResult.originalFile}</h4>
                      </div>
                      <div className="yaml-content">
                        {renderYamlWithHighlight(migrationResult.polarisYaml)}
                      </div>
                    </div>
                    <div className="file-side converted-file">
                      <div className="yaml-header">
                        <h4>🔄 Generated coverity.yaml</h4>
                        <div className="yaml-actions">
                            <button className="btn-download-yaml" onClick={handleDownloadCoverityYaml}>
                              ⬇️ Download coverity.yaml
                            </button>
                            {!migrationResult.pullRequestUrl && (
                              <button 
                                className="btn-create-pr" 
                                onClick={handleCreatePullRequest}
                                disabled={migratingPolaris}
                              >
                                🔀 Create Pull Request
                              </button>
                            )}
                            {migrationResult.pullRequestUrl && (
                              <a 
                                href={migrationResult.pullRequestUrl} 
                                target="_blank" 
                                rel="noopener noreferrer"
                                className="btn-view-pr"
                              >
                                👁️ View Pull Request
                              </a>
                            )}
                          </div>
                          {/* Show success message when PR is created */}
                          {migrationResult.pullRequestCreated && (
                            <div className="pr-success-message">
                              <p>✅ <strong>Pull Request created successfully!</strong></p>
                              <p>Branch: <code>{migrationResult.branchName}</code></p>
                              <p>The pull request has been opened in a new tab.</p>
                            </div>
                          )}
                          {/* Show error message if PR creation failed */}
                          {migrationResult.pullRequestError && (
                            <div className="pr-error-message">
                              <p>❌ <strong>Failed to create Pull Request:</strong></p>
                              <p className="error-details">{migrationResult.pullRequestError}</p>
                            </div>
                          )}
                        </div>
                        <div className="yaml-content">
                          {renderYamlWithHighlight(migrationResult.coverityYaml)}
                        </div>
                      </div>
                    </div>
                ) : (
                  <div className="migration-error">
                    <h3>❌ Migration Failed</h3>
                    <p className="error-message">{migrationResult.error}</p>
                  </div>
                )
              ) : null}
            </div>
          </div>
        </div>
      )}
    </div>
  );

  // Helper function to get language color
  function getLanguageColor(language) {
    const colors = {
      'JavaScript': '#f1e05a',
      'TypeScript': '#3178c6',
      'Python': '#3572A5',
      'Java': '#b07219',
      'C#': '#239120',
      'C++': '#f34b7d',
      'C': '#555555',
      'Go': '#00ADD8',
      'Rust': '#dea584',
      'PHP': '#4F5D95',
      'Ruby': '#701516',
      'Swift': '#fa7343',
      'Kotlin': '#A97BFF',
      'Dart': '#00B4AB',
      'Shell': '#89e051',
      'HTML': '#e34c26',
      'CSS': '#1572B6'
    };
    return colors[language] || '#586069';
  }
};

export default GitHubOrganizations;