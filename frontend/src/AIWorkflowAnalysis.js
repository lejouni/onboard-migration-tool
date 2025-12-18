import React, { useState, useEffect, useCallback } from 'react';
import { githubAPI } from './githubAPI';

const AIWorkflowAnalysis = () => {
  const [organizations, setOrganizations] = useState([]);
  const [selectedOrg, setSelectedOrg] = useState('');
  const [selectedScope, setSelectedScope] = useState('user'); // 'organization' or 'user'
  const [orgDetails, setOrgDetails] = useState(null);
  const [showOrgDetailsModal, setShowOrgDetailsModal] = useState(false);
  const [orgSecrets, setOrgSecrets] = useState([]);
  const [orgVariables, setOrgVariables] = useState([]);
  const [orgCustomProperties, setOrgCustomProperties] = useState([]);
  const [loadingOrgDetails, setLoadingOrgDetails] = useState(false);
  const [repositories, setRepositories] = useState([]);
  const [selectedReposForAnalysis, setSelectedReposForAnalysis] = useState(new Set());
  const [availableLanguages, setAvailableLanguages] = useState([]);
  const [selectedLanguage, setSelectedLanguage] = useState('');
  const [filterWithWorkflows, setFilterWithWorkflows] = useState(true); // Default to only repos with workflows
  const [analysisResults, setAnalysisResults] = useState(null);
  const [showAnalysisModal, setShowAnalysisModal] = useState(false);
  const [loadingAnalysis, setLoadingAnalysis] = useState(false);
  const [applyingTemplate, setApplyingTemplate] = useState({}); // Track which templates are being applied
  const [viewingTemplate, setViewingTemplate] = useState(null); // { repository, templateName, content, method }
  const [editedTemplateContent, setEditedTemplateContent] = useState(''); // Modified template content
  const [loading, setLoading] = useState(true);
  const [loadingLanguages, setLoadingLanguages] = useState(false);
  const [error, setError] = useState('');
  const [tokenStatus, setTokenStatus] = useState(null);
  const [userInfo, setUserInfo] = useState(null);
  const [notification, setNotification] = useState(null); // { type: 'success' | 'error' | 'info', message: '', link: '' }
  const [showDiffModal, setShowDiffModal] = useState(false);
  const [diffContent, setDiffContent] = useState(null); // { original_workflow, enhanced_workflow, template_name, job_id }
  const [previewingEnhancement, setPreviewingEnhancement] = useState({}); // Track which enhancements are being previewed
  const [applyingEnhancement, setApplyingEnhancement] = useState({}); // Track which enhancements are being applied

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
      setRepositories(repositoriesData.repositories || []);
      setSelectedLanguage('all');
    } catch (err) {
      setError(`Failed to load repositories: ${err.message}`);
      console.error('Error loading repositories:', err);
    } finally {
      setLoadingLanguages(false);
    }
  }, []);

  const handleScopeChange = (scope) => {
    setSelectedScope(scope);
    setSelectedOrg('');
    setOrgDetails(null);
    setRepositories([]);
    setAvailableLanguages([]);
    setSelectedLanguage('');
    setSelectedReposForAnalysis(new Set());
    setAnalysisResults(null);
    
    // Automatically load languages and repositories for user scope
    if (scope === 'user') {
      loadLanguagesAndRepositories();
    }
  };

  const handleOrgChange = async (orgLogin) => {
    setSelectedOrg(orgLogin);
    setRepositories([]);
    setAvailableLanguages([]);
    setSelectedLanguage('');
    setSelectedReposForAnalysis(new Set());
    setAnalysisResults(null);
    setOrgDetails(null);
    
    if (orgLogin) {
      // Load languages and org details in parallel
      try {
        const [, orgData] = await Promise.all([
          loadLanguages(orgLogin),
          githubAPI.getOrganizationDetails(orgLogin)
        ]);
        setOrgDetails(orgData);
      } catch (err) {
        console.error('Error loading organization details:', err);
        // Still load languages even if org details fail
        loadLanguages(orgLogin);
      }
    }
  };

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

  const handleLanguageFilter = (language) => {
    setSelectedLanguage(language);
    // For user scope with loaded repositories, just update the filter
    // The filtering will happen in the render via .filter()
  };

  const handleRepositoryToggle = (repo) => {
    const newSelected = new Set(selectedReposForAnalysis);
    if (newSelected.has(repo.id)) {
      newSelected.delete(repo.id);
    } else {
      newSelected.add(repo.id);
    }
    setSelectedReposForAnalysis(newSelected);
  };

  const handleSelectAllRepositories = () => {
    const filteredRepos = getFilteredRepositories();
    const newSelected = new Set([...selectedReposForAnalysis, ...filteredRepos.map(repo => repo.id)]);
    setSelectedReposForAnalysis(newSelected);
  };

  const handleDeselectAllRepositories = () => {
    setSelectedReposForAnalysis(new Set());
  };

  const getFilteredRepositories = () => {
    return repositories.filter(repo => {
      // Filter by language - for user scope, filter client-side
      if (selectedScope === 'user' && selectedLanguage && selectedLanguage !== 'all') {
        if (repo.language !== selectedLanguage) return false;
      }
      
      // Filter by repositories with workflow files
      if (filterWithWorkflows) {
        if (!repo.workflow_info?.has_workflows) {
          return false;
        }
      }
      
      return true;
    });
  };

  const handleAIAnalysis = async () => {
    const selectedRepos = repositories.filter(repo => selectedReposForAnalysis.has(repo.id));
    
    if (selectedRepos.length === 0) {
      setError('Please select at least one repository for analysis');
      return;
    }

    setLoadingAnalysis(true);
    setError('');
    
    try {
      // Call the AI analysis endpoint
      const response = await fetch('http://localhost:8000/api/ai-analyze', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          repositories: selectedRepos.map(repo => repo.full_name),
          analysis_type: 'comprehensive'
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to analyze repositories');
      }

      const data = await response.json();
      setAnalysisResults(data);
      setShowAnalysisModal(true); // Open modal with results
    } catch (err) {
      setError(`Analysis failed: ${err.message}`);
    } finally {
      setLoadingAnalysis(false);
    }
  };

  const handleApplyTemplate = async (repository, templateName, method) => {
    const key = `${repository}-${templateName}-${method}`;
    
    setApplyingTemplate(prev => ({ ...prev, [key]: true }));
    setError('');
    setNotification(null);
    
    try {
      // If there's edited content from viewing, use it; otherwise, use original template
      const templateContent = viewingTemplate && viewingTemplate.repository === repository && viewingTemplate.templateName === templateName
        ? editedTemplateContent
        : null;
      
      const requestBody = {
        template_name: templateName,
        repository: repository,
        method: method,
        branch: 'main', // Default to main branch
        pr_title: `Add ${templateName} workflow`,
        pr_body: `This PR adds the ${templateName} workflow template to enhance repository security scanning.\n\nThis template was recommended based on the detected technologies and current workflow configuration.`
      };
      
      // If we have edited content, include it in the request
      if (templateContent) {
        requestBody.template_content = templateContent;
      }
      
      const response = await fetch('http://localhost:8000/api/templates/apply', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to apply template');
      }

      const result = await response.json();
      
      if (result.success) {
        if (method === 'direct') {
          setNotification({
            type: 'success',
            message: `Template "${templateName}" has been applied directly to the ${result.branch} branch of ${repository}!`,
            link: result.commit_url,
            linkText: 'View Commit'
          });
        } else {
          setNotification({
            type: 'success',
            message: `Pull request #${result.pr_number} created for template "${templateName}" in ${repository}!`,
            link: result.pr_url,
            linkText: 'View Pull Request'
          });
        }
        
        // Close the template viewer if open
        setViewingTemplate(null);
        setEditedTemplateContent('');
      }
    } catch (err) {
      setNotification({
        type: 'error',
        message: `Failed to apply template: ${err.message}`
      });
    } finally {
      setApplyingTemplate(prev => ({ ...prev, [key]: false }));
    }
  };

  const handleViewTemplate = async (repository, templateName, method) => {
    try {
      // Fetch the template content
      const response = await fetch(`http://localhost:8000/api/templates/search/${encodeURIComponent(templateName)}`);
      
      if (!response.ok) {
        throw new Error('Failed to fetch template');
      }
      
      const templates = await response.json();
      
      if (!templates || templates.length === 0) {
        throw new Error('Template not found');
      }
      
      const template = templates[0];
      
      setViewingTemplate({
        repository,
        templateName,
        method,
        originalContent: template.content
      });
      
      setEditedTemplateContent(template.content);
      
    } catch (err) {
      setNotification({
        type: 'error',
        message: `Failed to load template: ${err.message}`
      });
    }
  };

  const handleCloseTemplateViewer = () => {
    setViewingTemplate(null);
    setEditedTemplateContent('');
  };

  const handleApplyFromViewer = async () => {
    if (!viewingTemplate) return;
    
    await handleApplyTemplate(
      viewingTemplate.repository,
      viewingTemplate.templateName,
      viewingTemplate.method
    );
  };

  // Handler for previewing workflow enhancement
  const handlePreviewEnhancement = async (repository, template) => {
    const key = `${repository}-${template.template_id}`;
    setPreviewingEnhancement(prev => ({ ...prev, [key]: true }));
    setError('');
    setNotification(null);

    try {
      const response = await fetch('http://localhost:8000/api/workflows/preview-enhancement', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          repository: repository,
          workflow_file_path: template.target_workflow.file_path,
          template_id: template.template_id,
          insertion_point: template.target_workflow.insertion_point,
          assessment_type: template.assessment_type
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to preview enhancement');
      }

      const result = await response.json();
      
      // Unescape any escaped newlines in the workflow content
      const processContent = (content) => {
        if (typeof content === 'string') {
          return content.replace(/\\n/g, '\n').replace(/\\r/g, '\r');
        }
        return content;
      };
      
      setDiffContent({
        ...result,
        original_workflow: processContent(result.original_workflow),
        enhanced_workflow: processContent(result.enhanced_workflow),
        repository: repository,
        workflow_file_path: template.target_workflow.file_path,
        template_id: template.template_id,
        insertion_point: template.target_workflow.insertion_point
      });
      setShowDiffModal(true);
    } catch (err) {
      setNotification({
        type: 'error',
        message: `Failed to preview enhancement: ${err.message}`
      });
    } finally {
      setPreviewingEnhancement(prev => ({ ...prev, [key]: false }));
    }
  };

  // Handler for applying workflow enhancement
  const handleApplyEnhancement = async (repository, template, fromDiffModal = false, method = 'direct') => {
    const key = `${repository}-${template.template_id}-${method}`;
    setApplyingEnhancement(prev => ({ ...prev, [key]: true }));
    setError('');
    setNotification(null);

    try {
      const response = await fetch('http://localhost:8000/api/workflows/apply-enhancement', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          repository: repository,
          workflow_file_path: template.target_workflow.file_path,
          template_id: template.template_id,
          insertion_point: template.target_workflow.insertion_point,
          branch_name: method === 'pull_request' ? `add-${template.template_name.toLowerCase().replace(/\s+/g, '-')}` : 'main',
          commit_message: `Add ${template.template_name} to ${template.target_workflow.file_name}`,
          method: method,
          assessment_type: template.assessment_type
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to apply enhancement');
      }

      const result = await response.json();
      
      if (method === 'pull_request') {
        setNotification({
          type: 'success',
          message: `Pull request created for "${result.template_name}" in ${repository}!`,
          link: result.pr_html_url || result.commit_html_url,
          linkText: 'View Pull Request'
        });
      } else {
        setNotification({
          type: 'success',
          message: `Enhancement "${result.template_name}" has been applied to ${result.workflow_file_path} in ${repository}!`,
          link: result.commit_html_url,
          linkText: 'View Commit'
        });
      }

      // Close diff modal if applying from there
      if (fromDiffModal) {
        setShowDiffModal(false);
        setDiffContent(null);
      }
    } catch (err) {
      setNotification({
        type: 'error',
        message: `Failed to apply enhancement: ${err.message}`
      });
    } finally {
      setApplyingEnhancement(prev => ({ ...prev, [key]: false }));
    }
  };

  const refreshData = () => {
    if (selectedScope === 'user') {
      loadLanguagesAndRepositories();
    } else {
      checkTokenAndLoadData();
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

  // Show loading state while checking token
  if (loading && !tokenStatus) {
    return (
      <div className="ai-workflow-analysis">
        <div className="loading-container">
          <div className="loading-spinner"></div>
          <p>Checking GitHub token status...</p>
        </div>
      </div>
    );
  }
  
  if (!tokenStatus?.has_token || !tokenStatus?.is_valid) {
    return (
      <div className="ai-workflow-analysis">
        <div className="github-header">
          <h1>🤖 AI-Powered Workflow Analysis</h1>
          <p>Analyze GitHub Actions workflows using advanced AI technology</p>
        </div>

        <div className="token-setup-prompt">
          <div className="setup-card">
            <h2>🔑 GitHub Token Required</h2>
            
            {!tokenStatus?.has_token ? (
              <div className="setup-message">
                <p>To analyze GitHub workflows, you need to add a GITHUB_TOKEN secret.</p>
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
                <li>Give it a name (e.g., "AI Workflow Analysis")</li>
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
    <div className="ai-workflow-analysis">
      <div className="github-header">
        <h1>🤖 AI-Powered Workflow Analysis</h1>
        <p>Select repositories and analyze their GitHub Actions workflows using advanced AI technology</p>
        
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

      {/* Notification Toast */}
      {notification && (
        <div style={{
          position: 'fixed',
          top: '20px',
          right: '20px',
          maxWidth: '450px',
          zIndex: 9999,
          background: notification.type === 'success' 
            ? 'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)' 
            : notification.type === 'error'
            ? 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)'
            : 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
          color: 'white',
          padding: '20px 25px',
          borderRadius: '12px',
          boxShadow: '0 10px 30px rgba(0,0,0,0.3)',
          animation: 'slideInRight 0.4s ease-out',
          display: 'flex',
          flexDirection: 'column',
          gap: '12px'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: '16px', fontWeight: '600', marginBottom: '8px' }}>
                {notification.type === 'success' ? '✅ Success!' : notification.type === 'error' ? '❌ Error' : 'ℹ️ Info'}
              </div>
              <div style={{ fontSize: '14px', lineHeight: '1.5' }}>
                {notification.message}
              </div>
            </div>
            <button
              onClick={() => setNotification(null)}
              style={{
                background: 'rgba(255,255,255,0.2)',
                border: 'none',
                color: 'white',
                fontSize: '20px',
                width: '28px',
                height: '28px',
                borderRadius: '50%',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                marginLeft: '10px',
                transition: 'all 0.2s ease'
              }}
              onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(255,255,255,0.3)'}
              onMouseLeave={(e) => e.currentTarget.style.background = 'rgba(255,255,255,0.2)'}
            >×</button>
          </div>
          {notification.link && (
            <a
              href={notification.link}
              target="_blank"
              rel="noopener noreferrer"
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
                background: 'rgba(255,255,255,0.2)',
                padding: '8px 16px',
                borderRadius: '8px',
                color: 'white',
                textDecoration: 'none',
                fontSize: '13px',
                fontWeight: '600',
                alignSelf: 'flex-start',
                transition: 'all 0.2s ease'
              }}
              onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(255,255,255,0.3)'}
              onMouseLeave={(e) => e.currentTarget.style.background = 'rgba(255,255,255,0.2)'}
            >
              {notification.linkText || 'View Details'} →
            </a>
          )}
        </div>
      )}

      {loading ? (
        <div className="loading">Loading data...</div>
      ) : (
        <div className="ai-analysis-content">
          {/* AI Analysis Features Info */}
          <div className="ai-features-section" style={{
            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            borderRadius: '16px',
            padding: '40px',
            marginBottom: '30px',
            boxShadow: '0 10px 30px rgba(0,0,0,0.2)',
            color: 'white'
          }}>
            <h2 style={{
              fontSize: '32px',
              marginBottom: '10px',
              textAlign: 'center',
              fontWeight: '700',
              textShadow: '2px 2px 4px rgba(0,0,0,0.2)'
            }}>🎯 Black Duck Tool Detection & Template Recommendations</h2>
            <p style={{
              textAlign: 'center',
              fontSize: '16px',
              marginBottom: '35px',
              opacity: '0.95'
            }}>Comprehensive analysis to check Black Duck security tools and recommend best practices</p>
            <div className="features-grid" style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
              gap: '25px'
            }}>
              <div className="feature-card" style={{
                background: 'rgba(255, 255, 255, 0.15)',
                backdropFilter: 'blur(10px)',
                borderRadius: '12px',
                padding: '25px',
                border: '1px solid rgba(255, 255, 255, 0.2)',
                transition: 'transform 0.3s ease, box-shadow 0.3s ease',
                cursor: 'pointer'
              }} onMouseEnter={(e) => {
                e.currentTarget.style.transform = 'translateY(-5px)';
                e.currentTarget.style.boxShadow = '0 8px 20px rgba(0,0,0,0.3)';
              }} onMouseLeave={(e) => {
                e.currentTarget.style.transform = 'translateY(0)';
                e.currentTarget.style.boxShadow = 'none';
              }}>
                <div style={{ fontSize: '48px', marginBottom: '15px', textAlign: 'center' }}>🔍</div>
                <h3 style={{ fontSize: '20px', marginBottom: '12px', fontWeight: '600' }}>Tool Detection</h3>
                <p style={{ fontSize: '14px', lineHeight: '1.6', opacity: '0.9' }}>
                  Automatically scan workflows to detect if Black Duck security tools are already in use
                </p>
              </div>
              <div className="feature-card" style={{
                background: 'rgba(255, 255, 255, 0.15)',
                backdropFilter: 'blur(10px)',
                borderRadius: '12px',
                padding: '25px',
                border: '1px solid rgba(255, 255, 255, 0.2)',
                transition: 'transform 0.3s ease, box-shadow 0.3s ease',
                cursor: 'pointer'
              }} onMouseEnter={(e) => {
                e.currentTarget.style.transform = 'translateY(-5px)';
                e.currentTarget.style.boxShadow = '0 8px 20px rgba(0,0,0,0.3)';
              }} onMouseLeave={(e) => {
                e.currentTarget.style.transform = 'translateY(0)';
                e.currentTarget.style.boxShadow = 'none';
              }}>
                <div style={{ fontSize: '48px', marginBottom: '15px', textAlign: 'center' }}>💻</div>
                <h3 style={{ fontSize: '20px', marginBottom: '12px', fontWeight: '600' }}>Language Analysis</h3>
                <p style={{ fontSize: '14px', lineHeight: '1.6', opacity: '0.9' }}>
                  Identify programming languages used in your repositories
                </p>
              </div>
              <div className="feature-card" style={{
                background: 'rgba(255, 255, 255, 0.15)',
                backdropFilter: 'blur(10px)',
                borderRadius: '12px',
                padding: '25px',
                border: '1px solid rgba(255, 255, 255, 0.2)',
                transition: 'transform 0.3s ease, box-shadow 0.3s ease',
                cursor: 'pointer'
              }} onMouseEnter={(e) => {
                e.currentTarget.style.transform = 'translateY(-5px)';
                e.currentTarget.style.boxShadow = '0 8px 20px rgba(0,0,0,0.3)';
              }} onMouseLeave={(e) => {
                e.currentTarget.style.transform = 'translateY(0)';
                e.currentTarget.style.boxShadow = 'none';
              }}>
                <div style={{ fontSize: '48px', marginBottom: '15px', textAlign: 'center' }}>📦</div>
                <h3 style={{ fontSize: '20px', marginBottom: '12px', fontWeight: '600' }}>Package Manager Detection</h3>
                <p style={{ fontSize: '14px', lineHeight: '1.6', opacity: '0.9' }}>
                  Discover dependency management systems (npm, pip, maven, etc.)
                </p>
              </div>
              <div className="feature-card" style={{
                background: 'rgba(255, 255, 255, 0.15)',
                backdropFilter: 'blur(10px)',
                borderRadius: '12px',
                padding: '25px',
                border: '1px solid rgba(255, 255, 255, 0.2)',
                transition: 'transform 0.3s ease, box-shadow 0.3s ease',
                cursor: 'pointer'
              }} onMouseEnter={(e) => {
                e.currentTarget.style.transform = 'translateY(-5px)';
                e.currentTarget.style.boxShadow = '0 8px 20px rgba(0,0,0,0.3)';
              }} onMouseLeave={(e) => {
                e.currentTarget.style.transform = 'translateY(0)';
                e.currentTarget.style.boxShadow = 'none';
              }}>
                <div style={{ fontSize: '48px', marginBottom: '15px', textAlign: 'center' }}>🎯</div>
                <h3 style={{ fontSize: '20px', marginBottom: '12px', fontWeight: '600' }}>Smart Recommendations</h3>
                <p style={{ fontSize: '14px', lineHeight: '1.6', opacity: '0.9' }}>
                  Get template suggestions based on your tech stack and missing security tools
                </p>
              </div>
              <div className="feature-card" style={{
                background: 'rgba(255, 255, 255, 0.15)',
                backdropFilter: 'blur(10px)',
                borderRadius: '12px',
                padding: '25px',
                border: '1px solid rgba(255, 255, 255, 0.2)',
                transition: 'transform 0.3s ease, box-shadow 0.3s ease',
                cursor: 'pointer'
              }} onMouseEnter={(e) => {
                e.currentTarget.style.transform = 'translateY(-5px)';
                e.currentTarget.style.boxShadow = '0 8px 20px rgba(0,0,0,0.3)';
              }} onMouseLeave={(e) => {
                e.currentTarget.style.transform = 'translateY(0)';
                e.currentTarget.style.boxShadow = 'none';
              }}>
                <div style={{ fontSize: '48px', marginBottom: '15px', textAlign: 'center' }}>⚡</div>
                <h3 style={{ fontSize: '20px', marginBottom: '12px', fontWeight: '600' }}>Quick Analysis</h3>
                <p style={{ fontSize: '14px', lineHeight: '1.6', opacity: '0.9' }}>
                  Fast scanning without complex AI processing - instant results
                </p>
              </div>
              <div className="feature-card" style={{
                background: 'rgba(255, 255, 255, 0.15)',
                backdropFilter: 'blur(10px)',
                borderRadius: '12px',
                padding: '25px',
                border: '1px solid rgba(255, 255, 255, 0.2)',
                transition: 'transform 0.3s ease, box-shadow 0.3s ease',
                cursor: 'pointer'
              }} onMouseEnter={(e) => {
                e.currentTarget.style.transform = 'translateY(-5px)';
                e.currentTarget.style.boxShadow = '0 8px 20px rgba(0,0,0,0.3)';
              }} onMouseLeave={(e) => {
                e.currentTarget.style.transform = 'translateY(0)';
                e.currentTarget.style.boxShadow = 'none';
              }}>
                <div style={{ fontSize: '48px', marginBottom: '15px', textAlign: 'center' }}>💰</div>
                <h3 style={{ fontSize: '20px', marginBottom: '12px', fontWeight: '600' }}>Zero Cost</h3>
                <p style={{ fontSize: '14px', lineHeight: '1.6', opacity: '0.9' }}>
                  Completely free local analysis with no external API calls
                </p>
              </div>
            </div>
          </div>

          {/* Scope Selection */}
          <div className="scope-selector">
            <h2>📂 Repository Scope</h2>
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
                  <small>Analyze workflows across all repositories you have access to</small>
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
                  <small>Analyze workflows within a specific organization</small>
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

          {/* Organization Details Card */}
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

          {/* User Repositories (shown when user scope is selected) */}
          {selectedScope === 'user' && (
            <div className="user-repos-section">
              <div className="user-repos-header">
                <h2>👤 Your Repositories</h2>
                <p>Select repositories for AI workflow analysis</p>
                {loadingLanguages ? (
                  <div className="loading">🔄 Loading your repositories...</div>
                ) : availableLanguages.length === 0 ? (
                  <button onClick={loadLanguagesAndRepositories} className="load-languages-btn">
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

          {/* Repositories Section */}
          {((selectedScope === 'organization' && selectedOrg) || selectedScope === 'user') && (availableLanguages.length > 0 || repositories.length > 0) && (
            <div className="repositories-section">
              <h2>
                📚 Repository Selection ({getFilteredRepositories().length} available)
                {selectedScope === 'user' ? ' - All Your Repositories' : ` - ${selectedOrg}`}
              </h2>
              
              {repositories.length === 0 ? (
                <div className="no-repositories">
                  <p>No repositories found for the selected criteria.</p>
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
                        checked={filterWithWorkflows}
                        onChange={(e) => setFilterWithWorkflows(e.target.checked)}
                      />
                      <span>Only repos with GitHub workflow files (Recommended for AI Analysis)</span>
                    </label>
                  </div>

                  {/* Repository Analysis Controls */}
                  {getFilteredRepositories().length > 0 && (
                    <div className="analysis-controls">
                      <div className="analysis-header">
                        <h3>🤖 AI Workflow Analysis</h3>
                        <p>Select repositories to analyze their GitHub Actions workflows with AI</p>
                      </div>
                      
                      <div className="analysis-actions">
                        <div className="selection-controls">
                          <button 
                            onClick={handleSelectAllRepositories}
                            className="select-btn select-all"
                            disabled={getFilteredRepositories().length === 0}
                          >
                            ✅ Select All ({getFilteredRepositories().length})
                          </button>
                          <button 
                            onClick={handleDeselectAllRepositories}
                            className="select-btn deselect-all"
                            disabled={selectedReposForAnalysis.size === 0}
                          >
                            ❌ Deselect All
                          </button>
                        </div>
                        
                        <div className="analyze-action">
                          <button 
                            onClick={handleAIAnalysis}
                            className="analyze-btn"
                            disabled={selectedReposForAnalysis.size === 0 || loadingAnalysis}
                          >
                            {loadingAnalysis ? '🔄 Analyzing...' : `🤖 Analyze Selected (${selectedReposForAnalysis.size})`}
                          </button>
                        </div>
                      </div>

                      {loadingAnalysis && (
                        <div className="analysis-status">
                          <div className="loading-spinner"></div>
                          <p>Analyzing repositories with AI... This may take a few moments as we process each workflow file.</p>
                        </div>
                      )}
                    </div>
                  )}

                  <div className="repositories-grid">
                    {getFilteredRepositories().slice(0, 20).map(repo => (
                      <div key={repo.id} className="repo-card">
                        <div className="repo-header">
                          <div className="repo-header-left">
                            <input
                              type="checkbox"
                              checked={selectedReposForAnalysis.has(repo.id)}
                              onChange={() => handleRepositoryToggle(repo)}
                              className="repo-checkbox"
                              title="Select for AI analysis"
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
                            {repo.workflow_info?.has_workflows && <span className="badge workflows">⚡ Workflows</span>}
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
                          {repo.workflow_info?.total_count && (
                            <div className="stat-item">
                              <span className="stat-icon">⚡</span>
                              <span className="stat-value">{repo.workflow_info.total_count} workflows</span>
                            </div>
                          )}
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
                          {repo.workflow_info?.has_workflows && (
                            <a href={`${repo.html_url}/actions`} target="_blank" rel="noopener noreferrer" className="repo-link">
                              ⚡ Actions
                            </a>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>

                  {getFilteredRepositories().length > 20 && (
                    <div className="pagination-info">
                      <p>Showing first 20 repositories. Use filters above to narrow down your selection.</p>
                    </div>
                  )}
                </>
              )}
            </div>
          )}

          {/* Analysis Results Modal */}
          {showAnalysisModal && analysisResults && (
            <div className="modal-overlay" onClick={() => setShowAnalysisModal(false)} style={{
              position: 'fixed',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              backgroundColor: 'rgba(0, 0, 0, 0.7)',
              display: 'flex',
              justifyContent: 'center',
              alignItems: 'center',
              zIndex: 1000,
              backdropFilter: 'blur(5px)'
            }}>
              <div className="modal-content analysis-modal" onClick={(e) => e.stopPropagation()} style={{
                background: 'linear-gradient(to bottom, #ffffff, #f8f9fa)',
                borderRadius: '20px',
                maxWidth: '90vw',
                maxHeight: '90vh',
                width: '1200px',
                boxShadow: '0 25px 50px rgba(0, 0, 0, 0.3)',
                overflow: 'hidden',
                display: 'flex',
                flexDirection: 'column'
              }}>
                <div className="modal-header" style={{
                  background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                  color: 'white',
                  padding: '25px 30px',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  borderBottom: '3px solid rgba(255, 255, 255, 0.2)'
                }}>
                  <h2 style={{
                    margin: 0,
                    fontSize: '28px',
                    fontWeight: '700',
                    textShadow: '2px 2px 4px rgba(0,0,0,0.2)'
                  }}>🤖 Black Duck Analysis Results</h2>
                  <button className="modal-close" onClick={() => setShowAnalysisModal(false)} style={{
                    background: 'rgba(255, 255, 255, 0.2)',
                    border: 'none',
                    fontSize: '32px',
                    color: 'white',
                    cursor: 'pointer',
                    width: '45px',
                    height: '45px',
                    borderRadius: '50%',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    transition: 'all 0.3s ease'
                  }} onMouseEnter={(e) => {
                    e.currentTarget.style.background = 'rgba(255, 255, 255, 0.3)';
                    e.currentTarget.style.transform = 'rotate(90deg)';
                  }} onMouseLeave={(e) => {
                    e.currentTarget.style.background = 'rgba(255, 255, 255, 0.2)';
                    e.currentTarget.style.transform = 'rotate(0deg)';
                  }}>×</button>
                </div>
                
                <div className="modal-body" style={{
                  flex: 1,
                  overflowY: 'auto',
                  padding: '30px'
                }}>
                  {analysisResults.error ? (
                    <div className="analysis-error" style={{
                      background: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
                      color: 'white',
                      padding: '30px',
                      borderRadius: '12px',
                      textAlign: 'center'
                    }}>
                      <h3 style={{ fontSize: '24px', marginBottom: '15px' }}>❌ Analysis Failed</h3>
                      <p className="error-message" style={{ fontSize: '16px' }}>{analysisResults.error}</p>
                    </div>
                  ) : (
                    <div className="analysis-success">
                      {/* Analysis Summary */}
                      <div className="analysis-summary" style={{ marginBottom: '30px' }}>
                        <div className="summary-stats" style={{
                          display: 'grid',
                          gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
                          gap: '20px'
                        }}>
                          <div className="summary-card" style={{
                            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                            color: 'white',
                            padding: '25px',
                            borderRadius: '12px',
                            textAlign: 'center',
                            boxShadow: '0 4px 15px rgba(0,0,0,0.1)',
                            transition: 'transform 0.3s ease'
                          }} onMouseEnter={(e) => e.currentTarget.style.transform = 'translateY(-5px)'}
                             onMouseLeave={(e) => e.currentTarget.style.transform = 'translateY(0)'}>
                            <span className="summary-label" style={{
                              display: 'block',
                              fontSize: '14px',
                              color: 'rgba(255, 255, 255, 0.95)',
                              marginBottom: '10px',
                              fontWeight: '500'
                            }}>Repositories Analyzed</span>
                            <span className="summary-value" style={{
                              display: 'block',
                              fontSize: '36px',
                              fontWeight: '700'
                            }}>{analysisResults.repositories?.length || 0}</span>
                          </div>
                          <div className="summary-card" style={{
                            background: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
                            color: 'white',
                            padding: '25px',
                            borderRadius: '12px',
                            textAlign: 'center',
                            boxShadow: '0 4px 15px rgba(0,0,0,0.1)',
                            transition: 'transform 0.3s ease'
                          }} onMouseEnter={(e) => e.currentTarget.style.transform = 'translateY(-5px)'}
                             onMouseLeave={(e) => e.currentTarget.style.transform = 'translateY(0)'}>
                            <span className="summary-label" style={{
                              display: 'block',
                              fontSize: '14px',
                              opacity: '0.9',
                              marginBottom: '10px'
                            }}>Total Workflows</span>
                            <span className="summary-value" style={{
                              display: 'block',
                              fontSize: '36px',
                              fontWeight: '700'
                            }}>{analysisResults.total_workflows || 0}</span>
                          </div>
                          <div className="summary-card" style={{
                            background: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
                            color: 'white',
                            padding: '25px',
                            borderRadius: '12px',
                            textAlign: 'center',
                            boxShadow: '0 4px 15px rgba(0,0,0,0.1)',
                            transition: 'transform 0.3s ease'
                          }} onMouseEnter={(e) => e.currentTarget.style.transform = 'translateY(-5px)'}
                             onMouseLeave={(e) => e.currentTarget.style.transform = 'translateY(0)'}>
                            <span className="summary-label" style={{
                              display: 'block',
                              fontSize: '14px',
                              opacity: '0.9',
                              marginBottom: '10px'
                            }}>Analysis Cost</span>
                            <span className="summary-value success" style={{
                              display: 'block',
                              fontSize: '36px',
                              fontWeight: '700'
                            }}>FREE</span>
                          </div>
                          <div className="summary-card" style={{
                            background: 'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)',
                            color: 'white',
                            padding: '25px',
                            borderRadius: '12px',
                            textAlign: 'center',
                            boxShadow: '0 4px 15px rgba(0,0,0,0.1)',
                            transition: 'transform 0.3s ease'
                          }} onMouseEnter={(e) => e.currentTarget.style.transform = 'translateY(-5px)'}
                             onMouseLeave={(e) => e.currentTarget.style.transform = 'translateY(0)'}>
                            <span className="summary-label" style={{
                              display: 'block',
                              fontSize: '14px',
                              opacity: '0.9',
                              marginBottom: '10px'
                            }}>Processing Time</span>
                            <span className="summary-value" style={{
                              display: 'block',
                              fontSize: '36px',
                              fontWeight: '700'
                            }}>{analysisResults.processing_time || '0'}ms</span>
                          </div>
                        </div>
                      </div>

                      {/* Repository Analysis Details */}
                      {analysisResults.repositories && analysisResults.repositories.length > 0 && (
                        <div className="repository-analyses" style={{
                          display: 'flex',
                          flexDirection: 'column',
                          gap: '20px'
                        }}>
                          {analysisResults.repositories.map((repoAnalysis, index) => (
                            <div key={index} className="repo-analysis-card" style={{
                              background: 'white',
                              borderRadius: '12px',
                              padding: '25px',
                              boxShadow: '0 4px 15px rgba(0,0,0,0.08)',
                              border: '1px solid #e0e0e0',
                              transition: 'box-shadow 0.3s ease'
                            }} onMouseEnter={(e) => e.currentTarget.style.boxShadow = '0 8px 25px rgba(0,0,0,0.15)'}
                               onMouseLeave={(e) => e.currentTarget.style.boxShadow = '0 4px 15px rgba(0,0,0,0.08)'}>
                              <div className="repo-analysis-header" style={{
                                display: 'flex',
                                justifyContent: 'space-between',
                                alignItems: 'center',
                                marginBottom: '20px',
                                paddingBottom: '15px',
                                borderBottom: '2px solid #f0f0f0'
                              }}>
                                <h3 style={{
                                  margin: 0,
                                  fontSize: '20px',
                                  fontWeight: '600',
                                  color: '#333'
                                }}>📦 {repoAnalysis.repository}</h3>
                                <div className="analysis-badges" style={{
                                  display: 'flex',
                                  gap: '10px'
                                }}>
                                  {repoAnalysis.total_workflows > 0 && (
                                    <span className="badge info" style={{
                                      background: '#e3f2fd',
                                      color: '#1976d2',
                                      padding: '6px 14px',
                                      borderRadius: '20px',
                                      fontSize: '13px',
                                      fontWeight: '600'
                                    }}>{repoAnalysis.total_workflows} workflows</span>
                                  )}
                                  {repoAnalysis.blackduck_analysis?.has_blackduck_tools ? (
                                    <span className="badge success" style={{
                                      background: '#e8f5e9',
                                      color: '#2e7d32',
                                      padding: '6px 14px',
                                      borderRadius: '20px',
                                      fontSize: '13px',
                                      fontWeight: '600'
                                    }}>✅ Black Duck Configured</span>
                                  ) : (
                                    <span className="badge warning" style={{
                                      background: '#fff3e0',
                                      color: '#f57c00',
                                      padding: '6px 14px',
                                      borderRadius: '20px',
                                      fontSize: '13px',
                                      fontWeight: '600'
                                    }}>⚠️ No Black Duck Tools</span>
                                  )}
                                </div>
                              </div>

                              {repoAnalysis.error ? (
                                <div className="repo-error" style={{
                                  background: '#ffebee',
                                  color: '#c62828',
                                  padding: '15px',
                                  borderRadius: '8px',
                                  fontSize: '14px'
                                }}>Error: {repoAnalysis.error}</div>
                              ) : (
                                <div className="repo-analysis-content">
                                  {/* Black Duck Status */}
                                  {repoAnalysis.blackduck_analysis && (
                                    <div className="blackduck-status">
                                      <div className={`status-message ${repoAnalysis.blackduck_analysis.has_blackduck_tools ? 'success' : 'warning'}`} style={{
                                        background: repoAnalysis.blackduck_analysis.has_blackduck_tools 
                                          ? 'linear-gradient(135deg, #e8f5e9 0%, #c8e6c9 100%)'
                                          : 'linear-gradient(135deg, #fff3e0 0%, #ffe0b2 100%)',
                                        padding: '20px',
                                        borderRadius: '10px',
                                        marginBottom: '20px',
                                        border: `2px solid ${repoAnalysis.blackduck_analysis.has_blackduck_tools ? '#4caf50' : '#ff9800'}`
                                      }}>
                                        <h4 style={{
                                          margin: 0,
                                          fontSize: '16px',
                                          color: repoAnalysis.blackduck_analysis.has_blackduck_tools ? '#2e7d32' : '#f57c00',
                                          fontWeight: '600'
                                        }}>{repoAnalysis.blackduck_analysis.message}</h4>
                                      </div>
                                      
                                      {/* Security Evidence - Show proof of existing security scanning */}
                                      {repoAnalysis.blackduck_analysis.security_evidence && repoAnalysis.blackduck_analysis.security_evidence.length > 0 && (
                                        <div className="security-evidence-section" style={{ marginBottom: '20px' }}>
                                          <h5 style={{
                                            fontSize: '15px',
                                            fontWeight: '600',
                                            marginBottom: '12px',
                                            color: '#555',
                                            textAlign: 'left'
                                          }}>🔒 Security Scanning Evidence:</h5>
                                          <div className="evidence-list" style={{
                                            display: 'flex',
                                            flexDirection: 'column',
                                            gap: '12px'
                                          }}>
                                            {repoAnalysis.blackduck_analysis.security_evidence.map((evidence, evidenceIdx) => (
                                              <div key={evidenceIdx} className="evidence-item" style={{
                                                background: 'linear-gradient(135deg, #e8f5e9 0%, #f1f8f4 100%)',
                                                padding: '15px',
                                                borderRadius: '10px',
                                                border: '2px solid #4caf50',
                                                boxShadow: '0 2px 8px rgba(76, 175, 80, 0.15)'
                                              }}>
                                                <div style={{
                                                  display: 'flex',
                                                  alignItems: 'center',
                                                  justifyContent: 'space-between',
                                                  marginBottom: '10px',
                                                  gap: '10px'
                                                }}>
                                                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flex: 1 }}>
                                                    <span style={{
                                                      fontSize: '13px',
                                                      fontWeight: '600',
                                                      color: '#2e7d32'
                                                    }}>📄 {evidence.workflow_file}</span>
                                                    <span style={{
                                                      fontSize: '11px',
                                                      color: '#666',
                                                      fontStyle: 'italic'
                                                    }}>{evidence.workflow_path}</span>
                                                  </div>
                                                  <button
                                                    onClick={() => {
                                                      const matchingRepo = repositories.find(r => r.full_name === repoAnalysis.repository);
                                                      const defaultBranch = matchingRepo?.default_branch || 'main';
                                                      const githubUrl = `https://github.com/${repoAnalysis.repository}/blob/${defaultBranch}/${evidence.workflow_path}`;
                                                      window.open(githubUrl, '_blank');
                                                    }}
                                                    style={{
                                                      background: 'linear-gradient(135deg, #2196f3 0%, #1976d2 100%)',
                                                      color: 'white',
                                                      border: 'none',
                                                      padding: '6px 12px',
                                                      borderRadius: '6px',
                                                      fontSize: '11px',
                                                      fontWeight: '600',
                                                      cursor: 'pointer',
                                                      display: 'flex',
                                                      alignItems: 'center',
                                                      gap: '4px',
                                                      transition: 'all 0.2s',
                                                      boxShadow: '0 2px 4px rgba(33, 150, 243, 0.3)'
                                                    }}
                                                    onMouseEnter={(e) => {
                                                      e.currentTarget.style.transform = 'translateY(-1px)';
                                                      e.currentTarget.style.boxShadow = '0 4px 8px rgba(33, 150, 243, 0.4)';
                                                    }}
                                                    onMouseLeave={(e) => {
                                                      e.currentTarget.style.transform = 'translateY(0)';
                                                      e.currentTarget.style.boxShadow = '0 2px 4px rgba(33, 150, 243, 0.3)';
                                                    }}
                                                  >
                                                    <span>👁️</span>
                                                    <span>View Workflow</span>
                                                  </button>
                                                </div>
                                                
                                                {evidence.detected_tools && evidence.detected_tools.length > 0 && (
                                                  <div style={{
                                                    display: 'flex',
                                                    flexDirection: 'column',
                                                    gap: '8px',
                                                    marginTop: '10px'
                                                  }}>
                                                    {evidence.detected_tools.map((tool, toolIdx) => (
                                                      <div key={toolIdx} style={{
                                                        background: 'white',
                                                        padding: '10px 12px',
                                                        borderRadius: '6px',
                                                        border: '1px solid #c8e6c9',
                                                        display: 'flex',
                                                        alignItems: 'center',
                                                        gap: '12px'
                                                      }}>
                                                        <span style={{
                                                          background: 'linear-gradient(135deg, #4caf50 0%, #66bb6a 100%)',
                                                          color: 'white',
                                                          padding: '4px 10px',
                                                          borderRadius: '12px',
                                                          fontSize: '11px',
                                                          fontWeight: '600',
                                                          minWidth: '80px',
                                                          textAlign: 'center'
                                                        }}>🛡️ {tool.tool}</span>
                                                        <div style={{
                                                          display: 'flex',
                                                          flexDirection: 'column',
                                                          gap: '2px',
                                                          flex: 1
                                                        }}>
                                                          <span style={{
                                                            fontSize: '12px',
                                                            color: '#555',
                                                            fontWeight: '500'
                                                          }}>
                                                            Job: <span style={{ color: '#1976d2' }}>{tool.job}</span>
                                                          </span>
                                                          <span style={{
                                                            fontSize: '11px',
                                                            color: '#666'
                                                          }}>
                                                            Step: {tool.step}
                                                          </span>
                                                        </div>
                                                      </div>
                                                    ))}
                                                  </div>
                                                )}
                                              </div>
                                            ))}
                                          </div>
                                        </div>
                                      )}
                                      
                                      {/* Detected Languages */}
                                      {repoAnalysis.blackduck_analysis.detected_languages && repoAnalysis.blackduck_analysis.detected_languages.length > 0 && (
                                        <div className="detected-info" style={{ marginBottom: '20px' }}>
                                          <h5 style={{
                                            fontSize: '15px',
                                            fontWeight: '600',
                                            marginBottom: '12px',
                                            color: '#555',
                                            textAlign: 'left'
                                          }}>💻 Detected Languages:</h5>
                                          <div className="info-tags" style={{
                                            display: 'flex',
                                            flexWrap: 'wrap',
                                            gap: '8px'
                                          }}>
                                            {repoAnalysis.blackduck_analysis.detected_languages.map((lang, idx) => {
                                              // Find the matching repository to get the primary language
                                              const matchingRepo = repositories.find(r => r.full_name === repoAnalysis.repository);
                                              const isPrimaryLanguage = matchingRepo && matchingRepo.language === lang;
                                              return (
                                                <span key={idx} className="info-tag language" style={{
                                                  background: isPrimaryLanguage 
                                                    ? 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)' 
                                                    : 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                                                  color: 'white',
                                                  padding: '6px 14px',
                                                  borderRadius: '20px',
                                                  fontSize: '13px',
                                                  fontWeight: isPrimaryLanguage ? '600' : '500',
                                                  border: isPrimaryLanguage ? '2px solid #ff6b9d' : 'none',
                                                  boxShadow: isPrimaryLanguage ? '0 4px 12px rgba(240, 147, 251, 0.4)' : 'none'
                                                }}>
                                                  {isPrimaryLanguage && '⭐ '}
                                                  {lang}
                                                </span>
                                              );
                                            })}
                                          </div>
                                        </div>
                                      )}
                                      
                                      {/* Detected Package Managers */}
                                      {repoAnalysis.blackduck_analysis.detected_package_managers && repoAnalysis.blackduck_analysis.detected_package_managers.length > 0 && (
                                        <div className="detected-info" style={{ marginBottom: '20px' }}>
                                          <h5 style={{
                                            fontSize: '15px',
                                            fontWeight: '600',
                                            marginBottom: '12px',
                                            color: '#555',
                                            textAlign: 'left'
                                          }}>📦 Detected Package Managers:</h5>
                                          <div className="info-tags" style={{
                                            display: 'flex',
                                            flexWrap: 'wrap',
                                            gap: '8px'
                                          }}>
                                            {repoAnalysis.blackduck_analysis.detected_package_managers.map((pm, idx) => (
                                              <span key={idx} className="info-tag package-manager" style={{
                                                background: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
                                                color: 'white',
                                                padding: '6px 14px',
                                                borderRadius: '20px',
                                                fontSize: '13px',
                                                fontWeight: '500'
                                              }}>{typeof pm === 'string' ? pm : pm.name}</span>
                                            ))}
                                          </div>
                                        </div>
                                      )}
                                      
                                      {/* Detected Black Duck Tools */}
                                      {repoAnalysis.blackduck_analysis.detected_tools && repoAnalysis.blackduck_analysis.detected_tools.length > 0 && (
                                        <div className="detected-tools-section" style={{ marginBottom: '20px' }}>
                                          <h5 style={{
                                            fontSize: '15px',
                                            fontWeight: '600',
                                            marginBottom: '12px',
                                            color: '#555',
                                            textAlign: 'left'
                                          }}>🔧 Black Duck Tools in Use:</h5>
                                          <div className="tools-list" style={{
                                            display: 'flex',
                                            flexDirection: 'column',
                                            gap: '10px'
                                          }}>
                                            {repoAnalysis.blackduck_analysis.detected_tools.map((tool, toolIdx) => (
                                              <div key={toolIdx} className="tool-item" style={{
                                                background: '#f5f5f5',
                                                padding: '12px 16px',
                                                borderRadius: '8px',
                                                display: 'flex',
                                                justifyContent: 'space-between',
                                                alignItems: 'center'
                                              }}>
                                                <span className="tool-name" style={{
                                                  fontWeight: '600',
                                                  color: '#333',
                                                  fontSize: '14px'
                                                }}>{tool.tool_type.toUpperCase()}</span>
                                                <span className="tool-file" style={{
                                                  color: '#666',
                                                  fontSize: '13px'
                                                }}>in {tool.file_name}</span>
                                              </div>
                                            ))}
                                          </div>
                                        </div>
                                      )}
                                      
                                      {/* Template Recommendations */}
                                      {repoAnalysis.blackduck_analysis.recommended_templates && repoAnalysis.blackduck_analysis.recommended_templates.length > 0 && (
                                        <div className="recommendations-section">
                                          <h5 style={{
                                            fontSize: '15px',
                                            fontWeight: '600',
                                            marginBottom: '15px',
                                            color: '#555'
                                          }}>💡 Recommended Black Duck Templates:</h5>
                                          <div className="recommendations-list" style={{
                                            display: 'flex',
                                            flexDirection: 'column',
                                            gap: '20px'
                                          }}>
                                            {(() => {
                                              // Group templates by type
                                              const templates = repoAnalysis.blackduck_analysis.recommended_templates;
                                              const workflowTemplates = templates.filter(t => t.type === 'new_workflow');
                                              const stepTemplates = templates.filter(t => t.template_fragment_type === 'step');
                                              const jobTemplates = templates.filter(t => t.template_fragment_type === 'job');
                                              
                                              const renderTemplate = (template, tmplIdx, cardBackground, borderColor, headerColor, badgeBackground) => {
                                                const isEnhancement = template.type === 'enhance_workflow';
                                                return (
                                                  <div key={tmplIdx} className="recommendation-card" style={{
                                                    background: cardBackground,
                                                    borderRadius: '10px',
                                                    padding: '20px',
                                                    border: `2px solid ${borderColor}`,
                                                    transition: 'transform 0.3s ease'
                                                  }} onMouseEnter={(e) => e.currentTarget.style.transform = 'translateX(5px)'}
                                                     onMouseLeave={(e) => e.currentTarget.style.transform = 'translateX(0)'}>
                                                    <div className="recommendation-header" style={{
                                                      display: 'flex',
                                                      justifyContent: 'space-between',
                                                      alignItems: 'center',
                                                      marginBottom: '12px'
                                                    }}>
                                                      <span className="template-name" style={{
                                                        fontWeight: '700',
                                                        fontSize: '16px',
                                                        color: headerColor
                                                      }}>{isEnhancement ? '🔧 ' : ''}{template.template_name}</span>
                                                      <span className={`template-category ${template.category}`} style={{
                                                        background: badgeBackground,
                                                        color: 'white',
                                                        padding: '4px 12px',
                                                        borderRadius: '15px',
                                                        fontSize: '11px',
                                                        fontWeight: '600',
                                                        letterSpacing: '0.5px'
                                                      }}>{template.category.toUpperCase()}</span>
                                                    </div>
                                                    
                                                    {/* Show target workflow info for enhancements */}
                                                    {isEnhancement && template.target_workflow && (
                                                      <div style={{
                                                        background: 'rgba(255, 152, 0, 0.1)',
                                                        padding: '10px',
                                                        borderRadius: '6px',
                                                        marginBottom: '12px',
                                                        fontSize: '13px'
                                                      }}>
                                                        <div style={{ marginBottom: '4px' }}>
                                                          <strong>📄 Target:</strong> {template.target_workflow.file_name}
                                                        </div>
                                                        <div style={{ fontSize: '12px', color: '#666' }}>
                                                          {template.template_fragment_type === 'step' ? (
                                                            <>
                                                              <strong>Insert step into:</strong> "{template.target_workflow.insertion_point.target_job}" job
                                                              {template.target_workflow.insertion_point.after_step && 
                                                                ` (after ${template.target_workflow.insertion_point.after_step} steps)`}
                                                            </>
                                                          ) : (
                                                            <>
                                                              <strong>Insert:</strong> {template.target_workflow.insertion_point.location.replace(/_/g, ' ')}
                                                              {template.target_workflow.insertion_point.after_job && 
                                                                ` (after "${template.target_workflow.insertion_point.after_job}" job)`}
                                                            </>
                                                          )}
                                                        </div>
                                                      </div>
                                                    )}
                                                    
                                                    <p className="template-description" style={{
                                                      margin: '0 0 12px 0',
                                                      fontSize: '14px',
                                                      color: '#424242',
                                                      lineHeight: '1.6'
                                                    }}>{template.description}</p>
                                                    <div className="template-reason" style={{
                                                      fontSize: '13px',
                                                      color: '#555',
                                                      fontStyle: 'italic',
                                                      paddingTop: '10px',
                                                      borderTop: '1px solid rgba(0,0,0,0.1)',
                                                      marginBottom: '15px'
                                                    }}>
                                                      <strong style={{ color: headerColor }}>Why:</strong> {template.reason}
                                                    </div>
                                                    
                                                    {/* Action Buttons */}
                                                    <div className="template-actions" style={{
                                                      display: 'flex',
                                                      gap: '10px',
                                                      marginTop: '15px',
                                                      flexWrap: 'wrap'
                                                    }}>
                                                      {isEnhancement ? (
                                                        <button
                                                          onClick={() => handlePreviewEnhancement(repoAnalysis.repository, template)}
                                                          disabled={previewingEnhancement[`${repoAnalysis.repository}-${template.template_id}`]}
                                                          style={{
                                                            flex: '1 1 100%',
                                                            background: previewingEnhancement[`${repoAnalysis.repository}-${template.template_id}`]
                                                              ? '#ccc'
                                                              : 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                                                            color: 'white',
                                                            border: 'none',
                                                            padding: '10px 15px',
                                                            borderRadius: '8px',
                                                            fontSize: '13px',
                                                            fontWeight: '600',
                                                            cursor: previewingEnhancement[`${repoAnalysis.repository}-${template.template_id}`] ? 'not-allowed' : 'pointer',
                                                            transition: 'all 0.3s ease',
                                                            boxShadow: '0 2px 8px rgba(0,0,0,0.1)'
                                                          }}
                                                          onMouseEnter={(e) => {
                                                            if (!previewingEnhancement[`${repoAnalysis.repository}-${template.template_id}`]) {
                                                              e.currentTarget.style.transform = 'translateY(-2px)';
                                                              e.currentTarget.style.boxShadow = '0 4px 12px rgba(0,0,0,0.2)';
                                                            }
                                                          }}
                                                          onMouseLeave={(e) => {
                                                            e.currentTarget.style.transform = 'translateY(0)';
                                                            e.currentTarget.style.boxShadow = '0 2px 8px rgba(0,0,0,0.1)';
                                                          }}
                                                        >
                                                          {previewingEnhancement[`${repoAnalysis.repository}-${template.template_id}`]
                                                            ? '⏳ Loading Preview...'
                                                            : '👁️ Preview Changes'}
                                                        </button>
                                                      ) : (
                                                        <>
                                                          <button
                                                            onClick={() => handleViewTemplate(repoAnalysis.repository, template.template_name, 'direct')}
                                                            style={{
                                                              flex: '1 1 100%',
                                                              background: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
                                                              color: 'white',
                                                              border: 'none',
                                                              padding: '10px 15px',
                                                              borderRadius: '8px',
                                                              fontSize: '13px',
                                                              fontWeight: '600',
                                                              cursor: 'pointer',
                                                              transition: 'all 0.3s ease',
                                                              boxShadow: '0 2px 8px rgba(0,0,0,0.1)'
                                                            }}
                                                            onMouseEnter={(e) => {
                                                              e.currentTarget.style.transform = 'translateY(-2px)';
                                                              e.currentTarget.style.boxShadow = '0 4px 12px rgba(0,0,0,0.2)';
                                                            }}
                                                            onMouseLeave={(e) => {
                                                              e.currentTarget.style.transform = 'translateY(0)';
                                                              e.currentTarget.style.boxShadow = '0 2px 8px rgba(0,0,0,0.1)';
                                                            }}
                                                          >
                                                            👁️ View & Edit Template
                                                          </button>
                                                          
                                                          <button
                                                            onClick={() => handleApplyTemplate(repoAnalysis.repository, template.template_name, 'direct')}
                                                            disabled={applyingTemplate[`${repoAnalysis.repository}-${tmplIdx}-direct`]}
                                                            style={{
                                                              flex: 1,
                                                              background: applyingTemplate[`${repoAnalysis.repository}-${tmplIdx}-direct`] 
                                                                ? '#ccc' 
                                                                : 'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)',
                                                              color: 'white',
                                                              border: 'none',
                                                              padding: '10px 15px',
                                                              borderRadius: '8px',
                                                              fontSize: '13px',
                                                              fontWeight: '600',
                                                              cursor: applyingTemplate[`${repoAnalysis.repository}-${tmplIdx}-direct`] ? 'not-allowed' : 'pointer',
                                                              transition: 'all 0.3s ease',
                                                              boxShadow: '0 2px 8px rgba(0,0,0,0.1)'
                                                            }}
                                                            onMouseEnter={(e) => {
                                                              if (!applyingTemplate[`${repoAnalysis.repository}-${tmplIdx}-direct`]) {
                                                                e.currentTarget.style.transform = 'translateY(-2px)';
                                                                e.currentTarget.style.boxShadow = '0 4px 12px rgba(0,0,0,0.2)';
                                                              }
                                                            }}
                                                            onMouseLeave={(e) => {
                                                              e.currentTarget.style.transform = 'translateY(0)';
                                                              e.currentTarget.style.boxShadow = '0 2px 8px rgba(0,0,0,0.1)';
                                                            }}
                                                          >
                                                            {applyingTemplate[`${repoAnalysis.repository}-${tmplIdx}-direct`] 
                                                              ? '⏳ Applying...' 
                                                              : '✓ Apply to Current Branch'}
                                                          </button>
                                                          
                                                          <button
                                                            onClick={() => handleApplyTemplate(repoAnalysis.repository, template.template_name, 'pull_request')}
                                                            disabled={applyingTemplate[`${repoAnalysis.repository}-${tmplIdx}-pr`]}
                                                            style={{
                                                              flex: 1,
                                                              background: applyingTemplate[`${repoAnalysis.repository}-${tmplIdx}-pr`] 
                                                                ? '#ccc' 
                                                                : 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                                                              color: 'white',
                                                              border: 'none',
                                                              padding: '10px 15px',
                                                              borderRadius: '8px',
                                                              fontSize: '13px',
                                                              fontWeight: '600',
                                                              cursor: applyingTemplate[`${repoAnalysis.repository}-${tmplIdx}-pr`] ? 'not-allowed' : 'pointer',
                                                              transition: 'all 0.3s ease',
                                                              boxShadow: '0 2px 8px rgba(0,0,0,0.1)'
                                                            }}
                                                            onMouseEnter={(e) => {
                                                              if (!applyingTemplate[`${repoAnalysis.repository}-${tmplIdx}-pr`]) {
                                                                e.currentTarget.style.transform = 'translateY(-2px)';
                                                                e.currentTarget.style.boxShadow = '0 4px 12px rgba(0,0,0,0.2)';
                                                              }
                                                            }}
                                                            onMouseLeave={(e) => {
                                                              e.currentTarget.style.transform = 'translateY(0)';
                                                              e.currentTarget.style.boxShadow = '0 2px 8px rgba(0,0,0,0.1)';
                                                            }}
                                                          >
                                                            {applyingTemplate[`${repoAnalysis.repository}-${tmplIdx}-pr`] 
                                                              ? '⏳ Creating PR...' 
                                                              : '🔀 Create Pull Request'}
                                                          </button>
                                                        </>
                                                      )}
                                                    </div>
                                                  </div>
                                                );
                                              };
                                              
                                              return (
                                                <>
                                                  {/* Step Templates */}
                                                  {stepTemplates.length > 0 && (
                                                    <div className="template-group">
                                                      <div style={{
                                                        display: 'flex',
                                                        alignItems: 'center',
                                                        gap: '10px',
                                                        marginBottom: '12px',
                                                        paddingBottom: '8px',
                                                        borderBottom: '2px solid #4caf50'
                                                      }}>
                                                        <span style={{
                                                          fontSize: '14px',
                                                          fontWeight: '700',
                                                          color: '#2e7d32',
                                                          textTransform: 'uppercase',
                                                          letterSpacing: '0.5px'
                                                        }}>🔧 Job Steps</span>
                                                        <span style={{
                                                          background: '#4caf50',
                                                          color: 'white',
                                                          padding: '2px 8px',
                                                          borderRadius: '12px',
                                                          fontSize: '11px',
                                                          fontWeight: '600'
                                                        }}>{stepTemplates.length}</span>
                                                        <span style={{
                                                          fontSize: '11px',
                                                          color: '#666',
                                                          fontStyle: 'italic'
                                                        }}>Insert into existing job</span>
                                                      </div>
                                                      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                                                        {stepTemplates.map((template, tmplIdx) => 
                                                          renderTemplate(
                                                            template, 
                                                            tmplIdx,
                                                            'linear-gradient(135deg, #e8f5e9 0%, #c8e6c9 100%)',
                                                            '#4caf50',
                                                            '#2e7d32',
                                                            '#388e3c'
                                                          )
                                                        )}
                                                      </div>
                                                    </div>
                                                  )}
                                                  
                                                  {/* Job Templates */}
                                                  {jobTemplates.length > 0 && (
                                                    <div className="template-group">
                                                      <div style={{
                                                        display: 'flex',
                                                        alignItems: 'center',
                                                        gap: '10px',
                                                        marginBottom: '12px',
                                                        paddingBottom: '8px',
                                                        borderBottom: '2px solid #ff9800'
                                                      }}>
                                                        <span style={{
                                                          fontSize: '14px',
                                                          fontWeight: '700',
                                                          color: '#e65100',
                                                          textTransform: 'uppercase',
                                                          letterSpacing: '0.5px'
                                                        }}>⚙️ Workflow Jobs</span>
                                                        <span style={{
                                                          background: '#ff9800',
                                                          color: 'white',
                                                          padding: '2px 8px',
                                                          borderRadius: '12px',
                                                          fontSize: '11px',
                                                          fontWeight: '600'
                                                        }}>{jobTemplates.length}</span>
                                                        <span style={{
                                                          fontSize: '11px',
                                                          color: '#666',
                                                          fontStyle: 'italic'
                                                        }}>Add to existing workflow</span>
                                                      </div>
                                                      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                                                        {jobTemplates.map((template, tmplIdx) => 
                                                          renderTemplate(
                                                            template, 
                                                            tmplIdx,
                                                            'linear-gradient(135deg, #fff3e0 0%, #ffe0b2 100%)',
                                                            '#ff9800',
                                                            '#e65100',
                                                            '#f57c00'
                                                          )
                                                        )}
                                                      </div>
                                                    </div>
                                                  )}
                                                  
                                                  {/* New Workflow Templates */}
                                                  {workflowTemplates.length > 0 && (
                                                    <div className="template-group">
                                                      <div style={{
                                                        display: 'flex',
                                                        alignItems: 'center',
                                                        gap: '10px',
                                                        marginBottom: '12px',
                                                        paddingBottom: '8px',
                                                        borderBottom: '2px solid #2196f3'
                                                      }}>
                                                        <span style={{
                                                          fontSize: '14px',
                                                          fontWeight: '700',
                                                          color: '#1565c0',
                                                          textTransform: 'uppercase',
                                                          letterSpacing: '0.5px'
                                                        }}>📄 New Workflows</span>
                                                        <span style={{
                                                          background: '#2196f3',
                                                          color: 'white',
                                                          padding: '2px 8px',
                                                          borderRadius: '12px',
                                                          fontSize: '11px',
                                                          fontWeight: '600'
                                                        }}>{workflowTemplates.length}</span>
                                                        <span style={{
                                                          fontSize: '11px',
                                                          color: '#666',
                                                          fontStyle: 'italic'
                                                        }}>Create new workflow file</span>
                                                      </div>
                                                      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                                                        {workflowTemplates.map((template, tmplIdx) => 
                                                          renderTemplate(
                                                            template, 
                                                            tmplIdx,
                                                            'linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%)',
                                                            '#2196f3',
                                                            '#1565c0',
                                                            '#1976d2'
                                                          )
                                                        )}
                                                      </div>
                                                    </div>
                                                  )}
                                                </>
                                              );
                                            })()}
                                          </div>
                                        </div>
                                      )}
                                    </div>
                                  )}
                                </div>
                              )}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>
                
                <div className="modal-footer" style={{
                  background: '#f8f9fa',
                  padding: '20px 30px',
                  borderTop: '1px solid #e0e0e0',
                  display: 'flex',
                  justifyContent: 'flex-end'
                }}>
                  <button className="btn-close" onClick={() => setShowAnalysisModal(false)} style={{
                    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                    color: 'white',
                    border: 'none',
                    padding: '12px 30px',
                    borderRadius: '25px',
                    fontSize: '16px',
                    fontWeight: '600',
                    cursor: 'pointer',
                    transition: 'all 0.3s ease',
                    boxShadow: '0 4px 15px rgba(102, 126, 234, 0.4)'
                  }} onMouseEnter={(e) => {
                    e.currentTarget.style.transform = 'translateY(-2px)';
                    e.currentTarget.style.boxShadow = '0 6px 20px rgba(102, 126, 234, 0.6)';
                  }} onMouseLeave={(e) => {
                    e.currentTarget.style.transform = 'translateY(0)';
                    e.currentTarget.style.boxShadow = '0 4px 15px rgba(102, 126, 234, 0.4)';
                  }}>Close</button>
                </div>
              </div>
            </div>
          )}
          
          {/* Template Viewer/Editor Modal */}
          {viewingTemplate && (
            <div className="template-viewer-overlay" style={{
              position: 'fixed',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              background: 'rgba(0,0,0,0.7)',
              display: 'flex',
              justifyContent: 'center',
              alignItems: 'center',
              zIndex: 10000,
              backdropFilter: 'blur(5px)'
            }}>
              <div className="template-viewer-modal" style={{
                background: 'white',
                borderRadius: '15px',
                width: '90%',
                maxWidth: '1000px',
                maxHeight: '90vh',
                display: 'flex',
                flexDirection: 'column',
                boxShadow: '0 20px 60px rgba(0,0,0,0.3)'
              }}>
                {/* Header */}
                <div className="template-viewer-header" style={{
                  padding: '25px 30px',
                  borderBottom: '2px solid #e0e0e0',
                  background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                  color: 'white',
                  borderRadius: '15px 15px 0 0'
                }}>
                  <h2 style={{ margin: 0, fontSize: '24px', fontWeight: '700' }}>
                    📝 View & Edit Template
                  </h2>
                  <p style={{ margin: '8px 0 0 0', fontSize: '14px', opacity: 0.9 }}>
                    {viewingTemplate.templateName} → {viewingTemplate.repository}
                  </p>
                </div>
                
                {/* Content */}
                <div className="template-viewer-content" style={{
                  flex: 1,
                  padding: '20px 30px',
                  overflowY: 'auto'
                }}>
                  <div style={{ marginBottom: '15px' }}>
                    <div style={{
                      background: '#fff3cd',
                      border: '1px solid #ffc107',
                      borderRadius: '8px',
                      padding: '12px 15px',
                      color: '#856404',
                      fontSize: '14px',
                      marginBottom: '15px'
                    }}>
                      <strong>ℹ️ Note:</strong> Modifications made here will only apply to this specific deployment. 
                      The original template in the database will remain unchanged.
                    </div>
                    <label style={{
                      display: 'block',
                      fontWeight: '600',
                      marginBottom: '10px',
                      color: '#333',
                      fontSize: '15px'
                    }}>
                      Template Content (YAML):
                    </label>
                    <textarea
                      value={editedTemplateContent}
                      onChange={(e) => setEditedTemplateContent(e.target.value)}
                      style={{
                        width: '100%',
                        minHeight: '400px',
                        padding: '15px',
                        fontFamily: '"Fira Code", "Courier New", monospace',
                        fontSize: '13px',
                        border: '2px solid #ddd',
                        borderRadius: '8px',
                        resize: 'vertical',
                        lineHeight: '1.6',
                        background: '#f8f9fa'
                      }}
                      spellCheck="false"
                    />
                  </div>
                </div>
                
                {/* Footer */}
                <div className="template-viewer-footer" style={{
                  padding: '20px 30px',
                  borderTop: '2px solid #e0e0e0',
                  display: 'flex',
                  gap: '15px',
                  justifyContent: 'flex-end',
                  background: '#f8f9fa'
                }}>
                  <button
                    onClick={handleCloseTemplateViewer}
                    style={{
                      background: '#6c757d',
                      color: 'white',
                      border: 'none',
                      padding: '12px 25px',
                      borderRadius: '8px',
                      fontSize: '14px',
                      fontWeight: '600',
                      cursor: 'pointer',
                      transition: 'all 0.3s ease'
                    }}
                    onMouseEnter={(e) => e.currentTarget.style.background = '#5a6268'}
                    onMouseLeave={(e) => e.currentTarget.style.background = '#6c757d'}
                  >
                    Cancel
                  </button>
                  
                  <button
                    onClick={() => handleApplyFromViewer()}
                    disabled={applyingTemplate[`${viewingTemplate.repository}-${viewingTemplate.templateName}-${viewingTemplate.method}`]}
                    style={{
                      background: applyingTemplate[`${viewingTemplate.repository}-${viewingTemplate.templateName}-${viewingTemplate.method}`]
                        ? '#ccc'
                        : 'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)',
                      color: 'white',
                      border: 'none',
                      padding: '12px 25px',
                      borderRadius: '8px',
                      fontSize: '14px',
                      fontWeight: '600',
                      cursor: applyingTemplate[`${viewingTemplate.repository}-${viewingTemplate.templateName}-${viewingTemplate.method}`] ? 'not-allowed' : 'pointer',
                      transition: 'all 0.3s ease',
                      boxShadow: '0 4px 15px rgba(67, 233, 123, 0.4)'
                    }}
                    onMouseEnter={(e) => {
                      if (!applyingTemplate[`${viewingTemplate.repository}-${viewingTemplate.templateName}-${viewingTemplate.method}`]) {
                        e.currentTarget.style.transform = 'translateY(-2px)';
                        e.currentTarget.style.boxShadow = '0 6px 20px rgba(67, 233, 123, 0.6)';
                      }
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.transform = 'translateY(0)';
                      e.currentTarget.style.boxShadow = '0 4px 15px rgba(67, 233, 123, 0.4)';
                    }}
                  >
                    {applyingTemplate[`${viewingTemplate.repository}-${viewingTemplate.templateName}-${viewingTemplate.method}`]
                      ? '⏳ Applying...'
                      : `✓ Apply to ${viewingTemplate.method === 'direct' ? 'Current Branch' : 'Pull Request'}`}
                  </button>
                </div>
              </div>
            </div>
          )}
          
          {/* Diff Viewer Modal */}
          {showDiffModal && diffContent && (
            <div className="diff-viewer-overlay" style={{
              position: 'fixed',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              background: 'rgba(0,0,0,0.7)',
              display: 'flex',
              justifyContent: 'center',
              alignItems: 'center',
              zIndex: 10000,
              backdropFilter: 'blur(5px)'
            }}>
              <div className="diff-viewer-modal" style={{
                background: 'white',
                borderRadius: '15px',
                width: '95%',
                maxWidth: '1400px',
                maxHeight: '90vh',
                display: 'flex',
                flexDirection: 'column',
                boxShadow: '0 20px 60px rgba(0,0,0,0.3)'
              }}>
                {/* Header */}
                <div className="diff-viewer-header" style={{
                  padding: '25px 30px',
                  borderBottom: '2px solid #e0e0e0',
                  background: 'linear-gradient(135deg, #ff9800 0%, #ff5722 100%)',
                  color: 'white',
                  borderRadius: '15px 15px 0 0'
                }}>
                  <h2 style={{ margin: 0, fontSize: '24px', fontWeight: '700' }}>
                    🔍 Preview Workflow Enhancement
                  </h2>
                  <p style={{ margin: '8px 0 0 0', fontSize: '14px', opacity: 0.9 }}>
                    {diffContent.template_name} → {diffContent.repository}/{diffContent.workflow_file_path}
                  </p>
                </div>
                
                {/* Content */}
                <div className="diff-viewer-content" style={{
                  flex: 1,
                  padding: '20px 30px',
                  overflowY: 'auto',
                  background: '#f5f5f5'
                }}>
                  <div style={{
                    background: '#fff3cd',
                    border: '1px solid #ffc107',
                    borderRadius: '8px',
                    padding: '12px 15px',
                    color: '#856404',
                    fontSize: '14px',
                    marginBottom: '20px'
                  }}>
                    <strong>ℹ️ Preview:</strong> The highlighted section below shows what will be added to your workflow.
                  </div>
                  
                  {/* Side-by-side diff view */}
                  <div style={{
                    display: 'grid',
                    gridTemplateColumns: '1fr 1fr',
                    gap: '20px',
                    height: '500px'
                  }}>
                    {/* Original Workflow */}
                    <div style={{
                      background: 'white',
                      borderRadius: '8px',
                      overflow: 'hidden',
                      border: '2px solid #ddd'
                    }}>
                      <div style={{
                        background: '#f44336',
                        color: 'white',
                        padding: '10px 15px',
                        fontWeight: '600',
                        fontSize: '14px'
                      }}>
                        📄 Original Workflow
                      </div>
                      <pre style={{
                        margin: 0,
                        padding: '15px',
                        fontSize: '12px',
                        fontFamily: 'Monaco, Courier, monospace',
                        overflow: 'auto',
                        height: 'calc(100% - 42px)',
                        background: '#fafafa',
                        color: '#333',
                        lineHeight: '1.5',
                        textAlign: 'left',
                        whiteSpace: 'pre'
                      }}>
                        {diffContent.original_workflow}
                      </pre>
                    </div>
                    
                    {/* Enhanced Workflow */}
                    <div style={{
                      background: 'white',
                      borderRadius: '8px',
                      overflow: 'hidden',
                      border: '2px solid #4caf50'
                    }}>
                      <div style={{
                        background: '#4caf50',
                        color: 'white',
                        padding: '10px 15px',
                        fontWeight: '600',
                        fontSize: '14px'
                      }}>
                        ✨ Enhanced Workflow
                      </div>
                      <pre style={{
                        margin: 0,
                        padding: '15px',
                        fontSize: '12px',
                        fontFamily: 'Monaco, Courier, monospace',
                        overflow: 'auto',
                        height: 'calc(100% - 42px)',
                        background: '#f1f8e9',
                        color: '#333',
                        lineHeight: '1.5',
                        textAlign: 'left',
                        whiteSpace: 'pre'
                      }}>
                        {diffContent.enhanced_workflow}
                      </pre>
                    </div>
                  </div>
                  
                  {/* Enhancement Details */}
                  <div style={{
                    marginTop: '20px',
                    background: 'linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%)',
                    borderRadius: '12px',
                    padding: '20px 24px',
                    border: '2px solid #e9ecef',
                    boxShadow: '0 2px 8px rgba(0,0,0,0.05)'
                  }}>
                    <div style={{
                      display: 'flex',
                      alignItems: 'center',
                      marginBottom: '16px',
                      paddingBottom: '12px',
                      borderBottom: '2px solid #dee2e6'
                    }}>
                      <span style={{
                        fontSize: '20px',
                        marginRight: '10px'
                      }}>📋</span>
                      <h4 style={{
                        margin: 0,
                        fontSize: '16px',
                        fontWeight: '700',
                        color: '#2c3e50',
                        letterSpacing: '0.3px'
                      }}>
                        Enhancement Details
                      </h4>
                    </div>
                    
                    <div style={{
                      display: 'grid',
                      gridTemplateColumns: '1fr 1fr',
                      gap: '12px'
                    }}>
                      <div style={{
                        background: '#f8f9fa',
                        padding: '12px 16px',
                        borderRadius: '8px',
                        border: '1px solid #e9ecef'
                      }}>
                        <div style={{
                          fontSize: '11px',
                          fontWeight: '600',
                          color: '#6c757d',
                          textTransform: 'uppercase',
                          letterSpacing: '0.5px',
                          marginBottom: '6px'
                        }}>Job ID</div>
                        <div style={{
                          fontSize: '14px',
                          fontWeight: '600',
                          color: '#495057',
                          fontFamily: 'Monaco, Courier, monospace'
                        }}>{diffContent.job_id}</div>
                      </div>
                      
                      <div style={{
                        background: '#f8f9fa',
                        padding: '12px 16px',
                        borderRadius: '8px',
                        border: '1px solid #e9ecef'
                      }}>
                        <div style={{
                          fontSize: '11px',
                          fontWeight: '600',
                          color: '#6c757d',
                          textTransform: 'uppercase',
                          letterSpacing: '0.5px',
                          marginBottom: '6px'
                        }}>Template</div>
                        <div style={{
                          fontSize: '14px',
                          fontWeight: '600',
                          color: '#495057'
                        }}>{diffContent.template_name}</div>
                      </div>
                      
                      <div style={{
                        background: '#f8f9fa',
                        padding: '12px 16px',
                        borderRadius: '8px',
                        border: '1px solid #e9ecef',
                        gridColumn: '1 / -1'
                      }}>
                        <div style={{
                          fontSize: '11px',
                          fontWeight: '600',
                          color: '#6c757d',
                          textTransform: 'uppercase',
                          letterSpacing: '0.5px',
                          marginBottom: '6px'
                        }}>Target File</div>
                        <div style={{
                          fontSize: '14px',
                          fontWeight: '600',
                          color: '#495057',
                          fontFamily: 'Monaco, Courier, monospace'
                        }}>{diffContent.workflow_file_path}</div>
                      </div>
                      
                      <div style={{
                        background: '#fff3e0',
                        padding: '12px 16px',
                        borderRadius: '8px',
                        border: '1px solid #ffe0b2',
                        gridColumn: '1 / -1'
                      }}>
                        <div style={{
                          fontSize: '11px',
                          fontWeight: '600',
                          color: '#e65100',
                          textTransform: 'uppercase',
                          letterSpacing: '0.5px',
                          marginBottom: '6px'
                        }}>Insertion Point</div>
                        <div style={{
                          fontSize: '14px',
                          fontWeight: '600',
                          color: '#e65100'
                        }}>
                          {diffContent.insertion_point.location.replace(/_/g, ' ').split(' ').map(word => 
                            word.charAt(0).toUpperCase() + word.slice(1)
                          ).join(' ')}
                          {diffContent.insertion_point.after_job && (
                            <span style={{
                              marginLeft: '8px',
                              padding: '2px 8px',
                              background: '#ff9800',
                              color: 'white',
                              borderRadius: '4px',
                              fontSize: '12px',
                              fontWeight: '600'
                            }}>
                              after "{diffContent.insertion_point.after_job}"
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
                
                {/* Footer */}
                <div className="diff-viewer-footer" style={{
                  padding: '20px 30px',
                  borderTop: '2px solid #e0e0e0',
                  display: 'flex',
                  gap: '15px',
                  justifyContent: 'flex-end',
                  background: '#f8f9fa'
                }}>
                  <button
                    onClick={() => {
                      setShowDiffModal(false);
                      setDiffContent(null);
                    }}
                    style={{
                      background: '#6c757d',
                      color: 'white',
                      border: 'none',
                      padding: '12px 25px',
                      borderRadius: '8px',
                      fontSize: '14px',
                      fontWeight: '600',
                      cursor: 'pointer',
                      transition: 'all 0.3s ease'
                    }}
                    onMouseEnter={(e) => e.currentTarget.style.background = '#5a6268'}
                    onMouseLeave={(e) => e.currentTarget.style.background = '#6c757d'}
                  >
                    Cancel
                  </button>
                  
                  <button
                    onClick={() => {
                      const template = {
                        template_id: diffContent.template_id,
                        template_name: diffContent.template_name,
                        target_workflow: {
                          file_path: diffContent.workflow_file_path,
                          insertion_point: diffContent.insertion_point,
                          file_name: diffContent.workflow_file_path.split('/').pop()
                        }
                      };
                      handleApplyEnhancement(diffContent.repository, template, true, 'direct');
                    }}
                    disabled={applyingEnhancement[`${diffContent.repository}-${diffContent.template_id}-direct`]}
                    style={{
                      background: applyingEnhancement[`${diffContent.repository}-${diffContent.template_id}-direct`]
                        ? '#ccc'
                        : 'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)',
                      color: 'white',
                      border: 'none',
                      padding: '12px 25px',
                      borderRadius: '8px',
                      fontSize: '14px',
                      fontWeight: '600',
                      cursor: applyingEnhancement[`${diffContent.repository}-${diffContent.template_id}-direct`] ? 'not-allowed' : 'pointer',
                      transition: 'all 0.3s ease',
                      boxShadow: '0 4px 15px rgba(67, 233, 123, 0.4)'
                    }}
                    onMouseEnter={(e) => {
                      if (!applyingEnhancement[`${diffContent.repository}-${diffContent.template_id}-direct`]) {
                        e.currentTarget.style.transform = 'translateY(-2px)';
                        e.currentTarget.style.boxShadow = '0 6px 20px rgba(67, 233, 123, 0.6)';
                      }
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.transform = 'translateY(0)';
                      e.currentTarget.style.boxShadow = '0 4px 15px rgba(67, 233, 123, 0.4)';
                    }}
                  >
                    {applyingEnhancement[`${diffContent.repository}-${diffContent.template_id}-direct`]
                      ? '⏳ Applying...'
                      : '✓ Apply to Current Branch'}
                  </button>
                  
                  <button
                    onClick={() => {
                      const template = {
                        template_id: diffContent.template_id,
                        template_name: diffContent.template_name,
                        target_workflow: {
                          file_path: diffContent.workflow_file_path,
                          insertion_point: diffContent.insertion_point,
                          file_name: diffContent.workflow_file_path.split('/').pop()
                        }
                      };
                      handleApplyEnhancement(diffContent.repository, template, true, 'pull_request');
                    }}
                    disabled={applyingEnhancement[`${diffContent.repository}-${diffContent.template_id}-pull_request`]}
                    style={{
                      background: applyingEnhancement[`${diffContent.repository}-${diffContent.template_id}-pull_request`]
                        ? '#ccc'
                        : 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                      color: 'white',
                      border: 'none',
                      padding: '12px 25px',
                      borderRadius: '8px',
                      fontSize: '14px',
                      fontWeight: '600',
                      cursor: applyingEnhancement[`${diffContent.repository}-${diffContent.template_id}-pull_request`] ? 'not-allowed' : 'pointer',
                      transition: 'all 0.3s ease',
                      boxShadow: '0 4px 15px rgba(102, 126, 234, 0.4)'
                    }}
                    onMouseEnter={(e) => {
                      if (!applyingEnhancement[`${diffContent.repository}-${diffContent.template_id}-pull_request`]) {
                        e.currentTarget.style.transform = 'translateY(-2px)';
                        e.currentTarget.style.boxShadow = '0 6px 20px rgba(102, 126, 234, 0.6)';
                      }
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.transform = 'translateY(0)';
                      e.currentTarget.style.boxShadow = '0 4px 15px rgba(102, 126, 234, 0.4)';
                    }}
                  >
                    {applyingEnhancement[`${diffContent.repository}-${diffContent.template_id}-pull_request`]
                      ? '⏳ Creating PR...'
                      : '🔀 Create Pull Request'}
                  </button>
                </div>
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
    </div>
  );
};

export default AIWorkflowAnalysis;
