import React, { useState, useEffect, useCallback } from 'react';
import { githubAPI } from './githubAPI';

const WorkflowSearch = () => {
  const [organizations, setOrganizations] = useState([]);
  const [selectedOrg, setSelectedOrg] = useState('');
  const [selectedScope, setSelectedScope] = useState('user'); // 'organization' or 'user'
  const [workflowSearchTerm, setWorkflowSearchTerm] = useState('');
  const [workflowSearchResults, setWorkflowSearchResults] = useState(null);
  const [loadingWorkflowSearch, setLoadingWorkflowSearch] = useState(false);
  const [aiAnalysisEnabled, setAiAnalysisEnabled] = useState(false);
  const [loading, setLoading] = useState(true);
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

  const handleWorkflowSearch = async (searchTerm) => {
    if (!searchTerm || searchTerm.trim().length < 2) {
      setError('Search term must be at least 2 characters long');
      return;
    }

    try {
      setLoadingWorkflowSearch(true);
      setError('');
      
      const scope = selectedScope;
      const organization = selectedScope === 'organization' ? selectedOrg : undefined;
      
      if (selectedScope === 'organization' && !selectedOrg) {
        setError('Please select an organization first');
        return;
      }

      // Choose endpoint based on AI analysis setting
      const endpoint = aiAnalysisEnabled 
        ? `/api/github/search/workflow-content/analyze?search_term=${encodeURIComponent(searchTerm.trim())}&scope=${scope}${organization ? `&organization=${organization}` : ''}`
        : `/api/github/search/workflow-content?search_term=${encodeURIComponent(searchTerm.trim())}&scope=${scope}${organization ? `&organization=${organization}` : ''}`;
      
      const response = await fetch(endpoint);
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `HTTP ${response.status}`);
      }
      
      const searchResults = await response.json();
      setWorkflowSearchResults(searchResults);
      
    } catch (err) {
      setError(`Failed to search workflows: ${err.message}`);
      console.error('Error searching workflows:', err);
    } finally {
      setLoadingWorkflowSearch(false);
    }
  };

  const clearWorkflowSearch = () => {
    setWorkflowSearchResults(null);
    setWorkflowSearchTerm('');
  };

  const handleScopeChange = (scope) => {
    setSelectedScope(scope);
    setSelectedOrg('');
    setWorkflowSearchResults(null);
    setWorkflowSearchTerm('');
  };

  const refreshData = () => {
    checkTokenAndLoadData();
  };

  // Show loading state while checking token
  if (loading && !tokenStatus) {
    return (
      <div className="workflow-search">
        <div className="loading-container">
          <div className="loading-spinner"></div>
          <p>Checking GitHub token status...</p>
        </div>
      </div>
    );
  }
  
  if (!tokenStatus?.has_token || !tokenStatus?.is_valid) {
    return (
      <div className="workflow-search">
        <div className="github-header">
          <h1>🔍 GitHub Workflow Search</h1>
          <p>Search for content within GitHub Actions workflow files</p>
        </div>

        <div className="token-setup-prompt">
          <div className="setup-card">
            <h2>🔑 GitHub Token Required</h2>
            
            {!tokenStatus?.has_token ? (
              <div className="setup-message">
                <p>To search GitHub workflow files, you need to add a GITHUB_TOKEN secret.</p>
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
                <li>Give it a name (e.g., "Workflow Search App")</li>
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
    <div className="workflow-search">
      <div className="github-header">
        <h1>🔍 GitHub Workflow Search</h1>
        <p>Search for text within GitHub Actions workflow files across your repositories</p>
        
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
        <div className="workflow-search-content">
          {/* Scope Selection */}
          <div className="scope-selector">
            <h2>📂 Search Scope</h2>
            <div className="scope-options">
              <label className="scope-option">
                <input
                  type="radio"
                  value="user"
                  checked={selectedScope === 'user'}
                  onChange={(e) => handleScopeChange(e.target.value)}
                />
                <span className="scope-label">
                  👤 All My Repositories
                  <small>Search workflow files across all repositories you have access to</small>
                </span>
              </label>
              <label className="scope-option">
                <input
                  type="radio"
                  value="organization"
                  checked={selectedScope === 'organization'}
                  onChange={(e) => handleScopeChange(e.target.value)}
                />
                <span className="scope-label">
                  🏢 Organization Repositories
                  <small>Search workflow files within a specific organization</small>
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
                onChange={(e) => setSelectedOrg(e.target.value)}
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

          {/* Workflow Search Section */}
          {((selectedScope === 'organization' && selectedOrg) || selectedScope === 'user') && (
            <div className="workflow-search-main">
              <div className="workflow-search-header">
                <h2>🔍 Search Workflow Content</h2>
                <p>Search for text within GitHub Actions workflow files</p>
              </div>
              
              {/* AI Analysis Toggle */}
              <div className="ai-analysis-toggle">
                <label className="toggle-label">
                  <input
                    type="checkbox"
                    checked={aiAnalysisEnabled}
                    onChange={(e) => setAiAnalysisEnabled(e.target.checked)}
                    className="toggle-checkbox"
                  />
                  <span className="toggle-slider"></span>
                  <span className="toggle-text">
                    🤖 AI-Powered Analysis & Template Recommendations
                    <small>
                      {aiAnalysisEnabled 
                        ? "✅ Enabled - Get smart insights and template suggestions (100% Free)" 
                        : "❌ Disabled - Basic search only"}
                    </small>
                  </span>
                </label>
                
                {aiAnalysisEnabled && (
                  <div className="ai-features-info">
                    <h4>🎯 AI Analysis Features:</h4>
                    <ul>
                      <li>🔧 <strong>Technology Detection</strong> - Identify languages, build tools, deployment targets</li>
                      <li>📋 <strong>Pattern Recognition</strong> - Find CI/CD patterns, security practices, quality checks</li>
                      <li>📊 <strong>Smart Scoring</strong> - Complexity, security, and modernization scores</li>
                      <li>🎯 <strong>Template Matching</strong> - Find similar saved templates with similarity scores</li>
                      <li>💡 <strong>Recommendations</strong> - Actionable suggestions for improvement</li>
                    </ul>
                    <div className="cost-info">
                      💰 <strong>Cost:</strong> $0 - Uses local analysis, no external API calls!
                    </div>
                  </div>
                )}
              </div>
              
              <div className="workflow-search-form">
                <div className="search-input-group">
                  <input
                    type="text"
                    placeholder="Enter search term (e.g., 'deploy', 'docker', 'azure', 'uses: actions/checkout')"
                    value={workflowSearchTerm}
                    onChange={(e) => setWorkflowSearchTerm(e.target.value)}
                    onKeyPress={(e) => {
                      if (e.key === 'Enter') {
                        handleWorkflowSearch(workflowSearchTerm);
                      }
                    }}
                    className="search-input"
                    disabled={loadingWorkflowSearch}
                  />
                  <button 
                    onClick={() => handleWorkflowSearch(workflowSearchTerm)}
                    disabled={loadingWorkflowSearch || workflowSearchTerm.trim().length < 2}
                    className="search-button"
                  >
                    {loadingWorkflowSearch ? '⏳ Searching...' : '🔍 Search'}
                  </button>
                  {workflowSearchResults && (
                    <button 
                      onClick={clearWorkflowSearch}
                      className="clear-search-button"
                    >
                      ❌ Clear
                    </button>
                  )}
                </div>
                
                <div className="search-tips">
                  <h4>💡 Search Tips:</h4>
                  <ul>
                    <li><strong>"deploy"</strong> - Find deployment workflows</li>
                    <li><strong>"docker"</strong> - Locate containerization setups</li>
                    <li><strong>"uses: actions/checkout"</strong> - Find specific action usage</li>
                    <li><strong>"azure"</strong> - Azure-specific implementations</li>
                    <li><strong>"test"</strong> - Testing strategies and configurations</li>
                    <li><strong>"env:"</strong> - Environment variable patterns</li>
                  </ul>
                </div>
                
                {loadingWorkflowSearch && (
                  <div className="search-status">
                    <div className="loading-spinner"></div>
                    <p>Searching workflow files... This may take a moment as we download and analyze each workflow file.</p>
                  </div>
                )}
                
                {workflowSearchResults && (
                  <div className="search-results">
                    <div className="search-summary">
                      <h3>Search Results for "{workflowSearchResults.search_term}"</h3>
                      {workflowSearchResults.analysis_metadata && (
                        <div className="ai-analysis-badge">
                          🤖 AI Analysis Enabled - {workflowSearchResults.analysis_metadata.total_templates_available} templates available for matching
                        </div>
                      )}
                      <div className="search-stats">
                        <div className="stat-item">
                          <span className="stat-label">Matching Repositories:</span>
                          <span className="stat-value">{workflowSearchResults.search_statistics.matching_repositories}</span>
                        </div>
                        <div className="stat-item">
                          <span className="stat-label">Total Searched:</span>
                          <span className="stat-value">{workflowSearchResults.search_statistics.total_repositories_searched}</span>
                        </div>
                        <div className="stat-item">
                          <span className="stat-label">Repositories with Workflows:</span>
                          <span className="stat-value">{workflowSearchResults.search_statistics.repositories_with_workflows}</span>
                        </div>
                        <div className="stat-item">
                          <span className="stat-label">Workflow Files Found:</span>
                          <span className="stat-value">{workflowSearchResults.search_statistics.matching_workflow_files}</span>
                        </div>
                        {workflowSearchResults.analysis_metadata && (
                          <div className="stat-item ai-stat">
                            <span className="stat-label">🤖 AI Analysis:</span>
                            <span className="stat-value">${workflowSearchResults.analysis_metadata.cost}</span>
                          </div>
                        )}
                      </div>
                    </div>
                    
                    {(workflowSearchResults.matching_repositories?.length > 0 || workflowSearchResults.template_recommendations?.length > 0) ? (
                      <div className="search-results-list">
                        {/* Show AI-analyzed results if available */}
                        {workflowSearchResults.template_recommendations && workflowSearchResults.template_recommendations.length > 0 && 
                          workflowSearchResults.template_recommendations.map(repo => (
                            <div key={repo.id} className="search-result-item ai-analyzed">
                              <div className="repo-header">
                                <h4 className="repo-name">
                                  <a href={repo.html_url} target="_blank" rel="noopener noreferrer">
                                    {repo.name}
                                  </a>
                                  <span className="ai-badge">🤖 AI Analyzed</span>
                                </h4>
                                <div className="repo-stats">
                                  <span className="match-count">
                                    {repo.total_matching_files} file{repo.total_matching_files !== 1 ? 's' : ''}, {repo.total_matches} match{repo.total_matches !== 1 ? 'es' : ''}
                                  </span>
                                  {repo.analysis_summary && (
                                    <span className="security-score">
                                      🔒 Security: {(repo.analysis_summary.avg_security_score * 100).toFixed(0)}%
                                    </span>
                                  )}
                                </div>
                              </div>
                              
                              {repo.description && (
                                <p className="repo-description">{repo.description}</p>
                              )}
                              
                              {/* Template Recommendation */}
                              {repo.analysis_summary?.top_recommendation && (
                                <div className="top-recommendation">
                                  💡 <strong>Recommended Template:</strong> {repo.analysis_summary.top_recommendation}
                                </div>
                              )}
                              
                              <div className="matching-files">
                                {repo.analyzed_workflow_files.map((file, fileIndex) => (
                                  <div key={fileIndex} className="workflow-file-match ai-enhanced">
                                    <div className="file-header">
                                      <span className="file-name">📄 {file.name}</span>
                                      <div className="file-actions">
                                        <span className="file-size">({(file.size / 1024).toFixed(1)} KB)</span>
                                        <a href={file.html_url} target="_blank" rel="noopener noreferrer" className="file-link">
                                          View File
                                        </a>
                                        {file.download_url && (
                                          <a href={file.download_url} target="_blank" rel="noopener noreferrer" className="file-link download">
                                            Download
                                          </a>
                                        )}
                                      </div>
                                    </div>
                                    
                                    {/* AI Analysis Results */}
                                    {file.analysis && (
                                      <div className="ai-analysis-results">
                                        <div className="analysis-scores">
                                          <div className="score-item">
                                            <span>🔧 Complexity:</span>
                                            <div className="score-bar">
                                              <div className="score-fill" style={{width: `${file.analysis.scores.complexity * 100}%`}}></div>
                                              <span className="score-text">{(file.analysis.scores.complexity * 100).toFixed(0)}%</span>
                                            </div>
                                          </div>
                                          <div className="score-item">
                                            <span>🔒 Security:</span>
                                            <div className="score-bar">
                                              <div className="score-fill security" style={{width: `${file.analysis.scores.security * 100}%`}}></div>
                                              <span className="score-text">{(file.analysis.scores.security * 100).toFixed(0)}%</span>
                                            </div>
                                          </div>
                                          <div className="score-item">
                                            <span>⚡ Modern:</span>
                                            <div className="score-bar">
                                              <div className="score-fill modern" style={{width: `${file.analysis.scores.modernization * 100}%`}}></div>
                                              <span className="score-text">{(file.analysis.scores.modernization * 100).toFixed(0)}%</span>
                                            </div>
                                          </div>
                                        </div>
                                        
                                        {/* Technologies */}
                                        {file.analysis.technologies.length > 0 && (
                                          <div className="detected-technologies">
                                            <h5>🔧 Detected Technologies:</h5>
                                            <div className="tech-tags">
                                              {file.analysis.technologies.map((tech, techIndex) => (
                                                <span key={techIndex} className={`tech-tag ${tech.type}`}>
                                                  {tech.name} ({(tech.confidence * 100).toFixed(0)}%)
                                                </span>
                                              ))}
                                            </div>
                                          </div>
                                        )}
                                        
                                        {/* Template Matches */}
                                        {file.template_matches && file.template_matches.length > 0 && (
                                          <div className="template-matches">
                                            <h5>🎯 Template Recommendations:</h5>
                                            {file.template_matches.map((match, matchIndex) => (
                                              <div key={matchIndex} className="template-match">
                                                <div className="template-header">
                                                  <span className="template-name">{match.template_name}</span>
                                                  <span className="similarity-score">{(match.similarity_score * 100).toFixed(0)}% match</span>
                                                </div>
                                                <p className="improvement-note">{match.improvement_potential}</p>
                                              </div>
                                            ))}
                                          </div>
                                        )}
                                        
                                        {/* Recommendations */}
                                        {file.analysis.recommendations.length > 0 && (
                                          <div className="ai-recommendations">
                                            <h5>💡 Improvement Suggestions:</h5>
                                            <ul>
                                              {file.analysis.recommendations.map((rec, recIndex) => (
                                                <li key={recIndex}>{rec}</li>
                                              ))}
                                            </ul>
                                          </div>
                                        )}
                                      </div>
                                    )}
                                    
                                    {/* Original workflow content display */}
                                    <div className="file-matches">
                                      {file.matching_blocks && file.matching_blocks.length > 0 ? (
                                        // Display complete jobs/steps containing the search term
                                        <>
                                          {file.matching_blocks.slice(0, 3).map((block, blockIndex) => (
                                            <div key={blockIndex} className="workflow-block-match">
                                              <div className="block-header">
                                                <span className="block-type">{block.block_type === 'job' ? '🔨' : '📋'} {block.block_type.charAt(0).toUpperCase() + block.block_type.slice(1)}: </span>
                                                <span className="block-name">{block.block_name}</span>
                                                <span className="block-location">Lines {block.start_line}-{block.end_line}</span>
                                              </div>
                                              <pre className="block-content">
                                                <code>{block.content}</code>
                                              </pre>
                                            </div>
                                          ))}
                                          {file.matching_blocks.length > 3 && (
                                            <div className="more-blocks">
                                              +{file.matching_blocks.length - 3} more {file.matching_blocks.length - 3 === 1 ? 'block' : 'blocks'} in this file
                                            </div>
                                          )}
                                        </>
                                      ) : (
                                        // Fallback to line-by-line display if blocks aren't available
                                        <>
                                          {file.matches && file.matches.slice(0, 5).map((match, matchIndex) => (
                                            <div key={matchIndex} className="match-item">
                                              <span className="line-number">Line {match.line_number}:</span>
                                              <code className="match-content">{match.line_content}</code>
                                            </div>
                                          ))}
                                          {file.matches && file.matches.length > 5 && (
                                            <div className="more-matches">
                                              +{file.matches.length - 5} more match{file.matches.length - 5 !== 1 ? 'es' : ''} in this file
                                            </div>
                                          )}
                                        </>
                                      )}
                                    </div>
                                  </div>
                                ))}
                              </div>
                            </div>
                          ))}
                        
                        {/* Regular search results */}
                        {workflowSearchResults.matching_repositories && workflowSearchResults.matching_repositories.map(repo => (
                            <div key={repo.id} className="search-result-item">
                              <div className="repo-header">
                              <h4 className="repo-name">
                                <a href={repo.html_url} target="_blank" rel="noopener noreferrer">
                                  {repo.name}
                                </a>
                              </h4>
                              <span className="match-count">
                                {repo.total_matching_files} file{repo.total_matching_files !== 1 ? 's' : ''}, {repo.total_matches} match{repo.total_matches !== 1 ? 'es' : ''}
                              </span>
                            </div>
                            
                            {repo.description && (
                              <p className="repo-description">{repo.description}</p>
                            )}
                            
                            <div className="matching-files">
                              {repo.matching_workflow_files.map((file, fileIndex) => (
                                <div key={fileIndex} className="workflow-file-match">
                                  <div className="file-header">
                                    <span className="file-name">📄 {file.name}</span>
                                    <div className="file-actions">
                                      <span className="file-size">({(file.size / 1024).toFixed(1)} KB)</span>
                                      <a href={file.html_url} target="_blank" rel="noopener noreferrer" className="file-link">
                                        View File
                                      </a>
                                      {file.download_url && (
                                        <a href={file.download_url} target="_blank" rel="noopener noreferrer" className="file-link download">
                                          Download
                                        </a>
                                      )}
                                    </div>
                                  </div>
                                  <div className="file-matches">
                                    {file.matching_blocks && file.matching_blocks.length > 0 ? (
                                      // Display complete jobs/steps containing the search term
                                      <>
                                        {file.matching_blocks.slice(0, 3).map((block, blockIndex) => (
                                          <div key={blockIndex} className="workflow-block-match">
                                            <div className="block-header">
                                              <span className="block-type">{block.block_type === 'job' ? '🔨' : '📋'} {block.block_type.charAt(0).toUpperCase() + block.block_type.slice(1)}: </span>
                                              <span className="block-name">{block.block_name}</span>
                                              <span className="block-location">Lines {block.start_line}-{block.end_line}</span>
                                            </div>
                                            <pre className="block-content">
                                              <code>{block.content}</code>
                                            </pre>
                                          </div>
                                        ))}
                                        {file.matching_blocks.length > 3 && (
                                          <div className="more-blocks">
                                            +{file.matching_blocks.length - 3} more {file.matching_blocks.length - 3 === 1 ? 'block' : 'blocks'} in this file
                                          </div>
                                        )}
                                      </>
                                    ) : (
                                      // Fallback to line-by-line display if blocks aren't available
                                      <>
                                        {file.matches && file.matches.slice(0, 5).map((match, matchIndex) => (
                                          <div key={matchIndex} className="match-item">
                                            <span className="line-number">Line {match.line_number}:</span>
                                            <code className="match-content">{match.line_content}</code>
                                          </div>
                                        ))}
                                        {file.matches && file.matches.length > 5 && (
                                          <div className="more-matches">
                                            +{file.matches.length - 5} more match{file.matches.length - 5 !== 1 ? 'es' : ''} in this file
                                          </div>
                                        )}
                                      </>
                                    )}
                                  </div>
                                </div>
                              ))}
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="no-search-results">
                        <div className="no-results-icon">🔍</div>
                        <h4>No Results Found</h4>
                        <p>No repositories found containing "{workflowSearchResults.search_term}" in their workflow files.</p>
                        <div className="search-suggestions">
                          <h5>Try searching for:</h5>
                          <ul>
                            <li>Common workflow keywords: "deploy", "build", "test"</li>
                            <li>Specific actions: "actions/checkout", "actions/setup-node"</li>
                            <li>Technology names: "docker", "azure", "aws"</li>
                            <li>Configuration patterns: "env:", "secrets.", "matrix:"</li>
                          </ul>
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default WorkflowSearch;