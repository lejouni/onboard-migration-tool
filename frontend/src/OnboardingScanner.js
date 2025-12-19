import React, { useState } from 'react';
import { getOrganizationRepositories, getUserRepositories } from './githubAPI';
import axios from 'axios';

// Use relative URL for Docker/nginx proxy, or localhost for local development
const API_BASE_URL = process.env.REACT_APP_API_URL ? process.env.REACT_APP_API_URL.replace('/api', '') : '';

function OnboardingScanner() {
  const [repositories, setRepositories] = useState([]);
  const [selectedRepos, setSelectedRepos] = useState([]);
  const [scanResults, setScanResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [loadingRepos, setLoadingRepos] = useState(false);
  const [error, setError] = useState('');
  const [scope, setScope] = useState('user'); // 'user' or 'organization'
  const [orgName, setOrgName] = useState('');

  const loadRepositories = async () => {
    try {
      setLoadingRepos(true);
      setError('');
      
      let repos;
      if (scope === 'user') {
        repos = await getUserRepositories();
      } else {
        if (!orgName.trim()) {
          setError('Please enter an organization name');
          return;
        }
        repos = await getOrganizationRepositories(orgName);
      }
      
      setRepositories(repos);
    } catch (err) {
      setError(err.message || 'Failed to load repositories');
      setRepositories([]);
    } finally {
      setLoadingRepos(false);
    }
  };

  const toggleRepository = (repoFullName) => {
    setSelectedRepos(prev => {
      if (prev.includes(repoFullName)) {
        return prev.filter(r => r !== repoFullName);
      } else {
        return [...prev, repoFullName];
      }
    });
  };

  const toggleSelectAll = () => {
    if (selectedRepos.length === repositories.length) {
      setSelectedRepos([]);
    } else {
      setSelectedRepos(repositories.map(r => r.full_name));
    }
  };

  const scanRepositories = async () => {
    if (selectedRepos.length === 0) {
      setError('Please select at least one repository to scan');
      return;
    }

    try {
      setLoading(true);
      setError('');
      setScanResults(null);

      const response = await axios.post(`${API_BASE_URL}/api/onboarding/scan`, selectedRepos);
      setScanResults(response.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to scan repositories');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="onboarding-scanner">
      <div className="onboarding-header">
        <h2>🚀 Repository Onboarding Scanner</h2>
        <p className="subtitle">Scan repositories for workflow files and match them with template keywords</p>
      </div>

      {error && (
        <div className="error-message">
          <span>⚠️ {error}</span>
        </div>
      )}

      <div className="onboarding-content">
        {/* Repository Selection Section */}
        <div className="repo-selection-section">
          <div className="scope-selector">
            <label>
              <input
                type="radio"
                value="user"
                checked={scope === 'user'}
                onChange={(e) => {
                  setScope(e.target.value);
                  setRepositories([]);
                  setSelectedRepos([]);
                }}
              />
              My Repositories
            </label>
            <label>
              <input
                type="radio"
                value="organization"
                checked={scope === 'organization'}
                onChange={(e) => {
                  setScope(e.target.value);
                  setRepositories([]);
                  setSelectedRepos([]);
                }}
              />
              Organization Repositories
            </label>
          </div>

          {scope === 'organization' && (
            <div className="org-input">
              <input
                type="text"
                placeholder="Enter organization name"
                value={orgName}
                onChange={(e) => setOrgName(e.target.value)}
              />
            </div>
          )}

          <button 
            onClick={loadRepositories} 
            disabled={loadingRepos}
            className="btn-primary"
          >
            {loadingRepos ? '⏳ Loading...' : '📥 Load Repositories'}
          </button>

          {repositories.length > 0 && (
            <div className="repository-list">
              <div className="list-header">
                <h3>Select Repositories to Scan ({selectedRepos.length}/{repositories.length})</h3>
                <button onClick={toggleSelectAll} className="btn-secondary btn-sm">
                  {selectedRepos.length === repositories.length ? '❌ Deselect All' : '✅ Select All'}
                </button>
              </div>
              
              <div className="repo-items">
                {repositories.map(repo => (
                  <label key={repo.full_name} className="repo-item">
                    <input
                      type="checkbox"
                      checked={selectedRepos.includes(repo.full_name)}
                      onChange={() => toggleRepository(repo.full_name)}
                    />
                    <div className="repo-info">
                      <span className="repo-name">{repo.full_name}</span>
                      {repo.description && (
                        <span className="repo-description">{repo.description}</span>
                      )}
                    </div>
                  </label>
                ))}
              </div>

              <button
                onClick={scanRepositories}
                disabled={loading || selectedRepos.length === 0}
                className="btn-primary btn-scan"
              >
                {loading ? '🔍 Scanning...' : `🔍 Scan ${selectedRepos.length} Selected ${selectedRepos.length === 1 ? 'Repository' : 'Repositories'}`}
              </button>
            </div>
          )}
        </div>

        {/* Results Section */}
        {scanResults && (
          <div className="scan-results">
            <h3>📊 Scan Results</h3>
            <div className="results-summary">
              <div className="summary-card">
                <span className="summary-label">Repositories Scanned</span>
                <span className="summary-value">{scanResults.total_repositories}</span>
              </div>
              <div className="summary-card">
                <span className="summary-label">Templates Used</span>
                <span className="summary-value">{scanResults.total_templates_used}</span>
              </div>
            </div>

            <div className="results-list">
              {scanResults.results.map((result, idx) => (
                <div key={idx} className="result-item">
                  <div className="result-header">
                    <h4>{result.repository}</h4>
                    <div className="result-stats">
                      <span className="stat-badge success">{result.workflows_with_matches} with matches</span>
                      <span className="stat-badge warning">{result.workflows_without_matches} without matches</span>
                      <span className="stat-badge info">{result.total_workflows} total workflows</span>
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
                                <span className="workflow-name">{workflow.name}</span>
                                <span className="workflow-path">{workflow.path}</span>
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
                                <div className="workflow-info">
                                  <span className="workflow-name">{workflow.name}</span>
                                  <span className="workflow-path">{workflow.path}</span>
                                </div>
                                <div className="workflow-actions">
                                  <button
                                    className="btn-view"
                                    onClick={() => workflow.html_url && window.open(workflow.html_url, '_blank')}
                                    disabled={!workflow.html_url}
                                    title={workflow.html_url ? "View workflow on GitHub" : "URL not available"}
                                  >
                                    👁️ View
                                  </button>
                                  <button
                                    className="btn-download"
                                    onClick={() => workflow.download_url && window.open(workflow.download_url, '_blank')}
                                    disabled={!workflow.download_url}
                                    title={workflow.download_url ? "Download workflow file" : "URL not available"}
                                  >
                                    💾 Download
                                  </button>
                                </div>
                              </div>
                              {workflow.error && (
                                <div className="workflow-error">Error: {workflow.error}</div>
                              )}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default OnboardingScanner;
