import React, { useState, useEffect } from 'react';
import { githubAPI } from './githubAPI';

const GitHubOrganizations = () => {
  const [organizations, setOrganizations] = useState([]);
  const [selectedOrg, setSelectedOrg] = useState('');
  const [selectedScope, setSelectedScope] = useState('organization'); // 'organization' or 'user'
  const [orgDetails, setOrgDetails] = useState(null);
  const [repositories, setRepositories] = useState([]);
  const [selectedRepo, setSelectedRepo] = useState('');
  const [availableLanguages, setAvailableLanguages] = useState([]);
  const [selectedLanguage, setSelectedLanguage] = useState('');
  const [loading, setLoading] = useState(true);
  const [loadingLanguages, setLoadingLanguages] = useState(false);
  const [loadingRepos, setLoadingRepos] = useState(false);
  const [error, setError] = useState('');
  const [tokenStatus, setTokenStatus] = useState(null);
  const [userInfo, setUserInfo] = useState(null);

  useEffect(() => {
    checkTokenAndLoadData();
  }, []);

  const checkTokenAndLoadData = async () => {
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
      setError(err.message);
      console.error('Error checking token status:', err);
    } finally {
      setLoading(false);
    }
  };

  const loadOrganizations = async () => {
    try {
      const data = await githubAPI.getOrganizations();
      setOrganizations(data.organizations || []);
    } catch (err) {
      setError(err.message);
      console.error('Error loading organizations:', err);
    }
  };

  const loadUserInfo = async () => {
    try {
      const user = await githubAPI.getUserInfo();
      setUserInfo(user);
    } catch (err) {
      console.error('Error loading user info:', err);
    }
  };

  const loadRepositories = async (orgLogin, language, scope = 'organization') => {
    if (!language || language.trim() === '') {
      setError('Please select a programming language first.');
      return;
    }
    
    try {
      setLoadingRepos(true);
      setError('');
      
      let repoData;
      if (scope === 'user') {
        repoData = await githubAPI.getUserRepositories(language);
      } else {
        if (!orgLogin) {
          setError('Please select an organization first.');
          return;
        }
        repoData = await githubAPI.getOrganizationRepositories(orgLogin, language);
      }
      
      setRepositories(repoData.repositories || []);
    } catch (err) {
      setError(`Failed to load repositories: ${err.message}`);
      console.error('Error loading repositories:', err);
    } finally {
      setLoadingRepos(false);
    }
  };

  const loadLanguages = async (orgLogin, scope = 'organization') => {
    try {
      setLoadingLanguages(true);
      setError('');
      
      let languageData;
      if (scope === 'user') {
        languageData = await githubAPI.getUserLanguages();
      } else {
        if (!orgLogin) {
          setError('Please select an organization first.');
          return;
        }
        languageData = await githubAPI.getOrganizationLanguages(orgLogin);
      }
      
      setAvailableLanguages(languageData.languages || []);
    } catch (err) {
      setError(`Failed to load languages: ${err.message}`);
      console.error('Error loading languages:', err);
    } finally {
      setLoadingLanguages(false);
    }
  };

  const handleScopeChange = async (scope) => {
    setSelectedScope(scope);
    setSelectedOrg('');
    setSelectedLanguage('');
    setOrgDetails(null);
    setRepositories([]);
    setSelectedRepo('');
    setAvailableLanguages([]);
    
    if (scope === 'user') {
      // Load user languages immediately
      await loadLanguages('', 'user');
    }
  };

  const handleOrgSelect = async (orgLogin) => {
    setSelectedOrg(orgLogin);
    setOrgDetails(null);
    setRepositories([]);
    setSelectedRepo('');
    setSelectedLanguage('');
    setAvailableLanguages([]);
    
    if (orgLogin) {
      try {
        setLoading(true);
        
        // Load organization details and languages in parallel
        const [details] = await Promise.all([
          githubAPI.getOrganizationDetails(orgLogin),
          loadLanguages(orgLogin, 'organization')
        ]);
        
        setOrgDetails(details);
      } catch (err) {
        setError(`Failed to load organization data: ${err.message}`);
        console.error('Error loading organization data:', err);
      } finally {
        setLoading(false);
      }
    }
  };

  const handleLanguageSelect = async (language) => {
    setSelectedLanguage(language);
    setSelectedRepo('');
    setRepositories([]);
    
    if (language && language.trim() !== '') {
      if (selectedScope === 'user') {
        await loadRepositories('', language, 'user');
      } else if (selectedOrg) {
        await loadRepositories(selectedOrg, language, 'organization');
      }
    }
  };

  const handleLanguageFilter = (language) => {
    setSelectedLanguage(language);
    setSelectedRepo('');
    setRepositories([]);
    
    if (language && language.trim() !== '' && language !== 'all') {
      if (selectedScope === 'user') {
        loadRepositories('', language, 'user');
      } else if (selectedOrg) {
        loadRepositories(selectedOrg, language, 'organization');
      }
    } else if (language === 'all') {
      // Load all repositories without language filter
      if (selectedScope === 'user') {
        loadRepositories('', '', 'user');
      } else if (selectedOrg) {
        loadRepositories(selectedOrg, '', 'organization');
      }
    }
  };

  const refreshData = () => {
    checkTokenAndLoadData();
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleDateString();
  };

  const formatNumber = (num) => {
    if (num === null || num === undefined) return 'N/A';
    return num.toLocaleString();
  };

  // Render token setup prompt
  if (!tokenStatus?.has_token || !tokenStatus?.is_valid) {
    return (
      <div className="github-organizations">
        <div className="github-header">
          <h1>🐙 GitHub Organizations</h1>
          <p>View and manage your GitHub organizations</p>
        </div>

        <div className="token-setup-prompt">
          <div className="setup-card">
            <h2>🔑 GitHub Token Required</h2>
            
            {!tokenStatus?.has_token ? (
              <div className="setup-message">
                <p>To access your GitHub organizations, you need to add a GITHUB_TOKEN secret.</p>
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
                <li>Give it a name (e.g., "Backend App")</li>
                <li>Select scopes: <code>read:org</code>, <code>read:user</code></li>
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
        <p>View and manage your GitHub organizations</p>
        
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
        <div className="loading">Loading organizations...</div>
      ) : (
        <div className="organizations-content">
          <div className="org-selector">
            <h2>Select Organization ({organizations.length} found)</h2>
            <select 
              value={selectedOrg} 
              onChange={(e) => handleOrgSelect(e.target.value)}
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
          </div>

          {organizations.length === 0 && (
            <div className="no-organizations">
              <p>No organizations found for your GitHub account.</p>
              <p>You may need to be a member of an organization or have the appropriate permissions.</p>
            </div>
          )}

          {selectedOrg && orgDetails && (
            <div className="org-details">
              <h2>Organization Details</h2>
              <div className="org-card">
                <div className="org-header">
                  <img src={orgDetails.avatar_url} alt={orgDetails.login} className="org-avatar" />
                  <div className="org-info">
                    <h3>{orgDetails.name || orgDetails.login}</h3>
                    <p className="org-login">@{orgDetails.login}</p>
                    {orgDetails.description && (
                      <p className="org-description">{orgDetails.description}</p>
                    )}
                  </div>
                </div>

                <div className="org-stats">
                  <div className="stat-item">
                    <span className="stat-label">Public Repositories</span>
                    <span className="stat-value">{formatNumber(orgDetails.public_repos)}</span>
                  </div>
                  <div className="stat-item">
                    <span className="stat-label">Followers</span>
                    <span className="stat-value">{formatNumber(orgDetails.followers)}</span>
                  </div>
                  <div className="stat-item">
                    <span className="stat-label">Following</span>
                    <span className="stat-value">{formatNumber(orgDetails.following)}</span>
                  </div>
                  <div className="stat-item">
                    <span className="stat-label">Created</span>
                    <span className="stat-value">{formatDate(orgDetails.created_at)}</span>
                  </div>
                </div>

                {(orgDetails.location || orgDetails.email || orgDetails.blog || orgDetails.company) && (
                  <div className="org-metadata">
                    {orgDetails.location && (
                      <div className="metadata-item">
                        <span className="metadata-label">📍 Location:</span>
                        <span className="metadata-value">{orgDetails.location}</span>
                      </div>
                    )}
                    {orgDetails.email && (
                      <div className="metadata-item">
                        <span className="metadata-label">📧 Email:</span>
                        <span className="metadata-value">
                          <a href={`mailto:${orgDetails.email}`}>{orgDetails.email}</a>
                        </span>
                      </div>
                    )}
                    {orgDetails.blog && (
                      <div className="metadata-item">
                        <span className="metadata-label">🌐 Website:</span>
                        <span className="metadata-value">
                          <a href={orgDetails.blog} target="_blank" rel="noopener noreferrer">
                            {orgDetails.blog}
                          </a>
                        </span>
                      </div>
                    )}
                    {orgDetails.company && (
                      <div className="metadata-item">
                        <span className="metadata-label">🏢 Company:</span>
                        <span className="metadata-value">{orgDetails.company}</span>
                      </div>
                    )}
                  </div>
                )}

                <div className="org-actions">
                  <a 
                    href={orgDetails.html_url} 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="view-github-btn"
                  >
                    🔗 View on GitHub
                  </a>
                </div>
              </div>
            </div>
          )}

          {selectedOrg && (
            <div className="repositories-section">
              <h2>Repositories ({repositories.length} found)</h2>
              
              {loadingRepos ? (
                <div className="loading">Loading repositories...</div>
              ) : repositories.length === 0 ? (
                <div className="no-repositories">
                  <p>No repositories found for this organization.</p>
                  <p>You may need additional permissions to view repositories.</p>
                </div>
              ) : (
                <>
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
                          <option key={language} value={language}>
                            {language}
                          </option>
                        ))}
                      </select>
                    </div>
                  )}

                  <div className="repo-selector">
                    <select 
                      value={selectedRepo} 
                      onChange={(e) => setSelectedRepo(e.target.value)}
                      className="repo-select"
                    >
                      <option value="">-- Select a repository --</option>
                      {repositories.map(repo => (
                        <option key={repo.id} value={repo.name}>
                          {repo.name}
                          {repo.description && ` - ${repo.description.substring(0, 50)}${repo.description.length > 50 ? '...' : ''}`}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className="repositories-grid">
                    {repositories.length === 0 && selectedLanguage !== 'all' ? (
                      <div className="no-repositories">
                        <p>No repositories found for the selected language: <strong>{selectedLanguage}</strong></p>
                        <p>Try selecting a different language or "All Languages" to see all repositories.</p>
                      </div>
                    ) : (
                      repositories.slice(0, 20).map(repo => (
                      <div key={repo.id} className="repo-card">
                        <div className="repo-header">
                          <h3 className="repo-name">
                            <a href={repo.html_url} target="_blank" rel="noopener noreferrer">
                              {repo.name}
                            </a>
                          </h3>
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
                          {repo.language && (
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

                  {repositories.length > 20 && (
                    <div className="repo-summary">
                      <p>Showing first 20 of {repositories.length} repositories.</p>
                      <p>Use the dropdown above to search for specific repositories.</p>
                    </div>
                  )}
                </>
              )}
            </div>
          )}
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