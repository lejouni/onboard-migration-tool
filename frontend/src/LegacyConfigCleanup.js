import React, { useState, useEffect, useCallback, useRef } from 'react';
import { githubAPI } from './githubAPI';
import Dashboard from './Dashboard';

const LegacyConfigCleanup = () => {
  const [organizations, setOrganizations] = useState([]);
  const [selectedOrg, setSelectedOrg] = useState('');
  const [selectedScope, setSelectedScope] = useState('user');
  const [repositories, setRepositories] = useState([]);
  const [legacyFiles, setLegacyFiles] = useState([]);
  const [selectedFiles, setSelectedFiles] = useState(new Set());
  const [loading, setLoading] = useState(false);
  const [scanning, setScanning] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState('');
  const [tokenStatus, setTokenStatus] = useState(null);
  const [userInfo, setUserInfo] = useState(null);
  const [notification, setNotification] = useState(null);
  const [deletionMode, setDeletionMode] = useState('direct'); // 'direct' or 'pr'
  const [showConfirmModal, setShowConfirmModal] = useState(false);
  const [repositoryFilter, setRepositoryFilter] = useState('all');
  const [reasonFilter, setReasonFilter] = useState('all');
  const [keywordFilter, setKeywordFilter] = useState('all');
  const [branchFilter, setBranchFilter] = useState('all');
  const [scanProgress, setScanProgress] = useState({ current: 0, total: 0 });
  const [keywords, setKeywords] = useState(['coverity', 'polaris', 'blackduck']);
  const [newKeyword, setNewKeyword] = useState('');
  const [scanAllBranches, setScanAllBranches] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [itemsPerPage, setItemsPerPage] = useState(20);
  const [scanDuration, setScanDuration] = useState(0);
  const [completedScanDuration, setCompletedScanDuration] = useState(null);
  const scanStartTimeRef = useRef(null);

  // Function to check if filename contains legacy keywords
  const isLegacyConfigFile = (filename) => {
    const lowerFilename = filename.toLowerCase();
    const hasYamlExtension = lowerFilename.endsWith('.yml') || lowerFilename.endsWith('.yaml');
    const hasLegacyKeyword = keywords.some(keyword => lowerFilename.includes(keyword.toLowerCase()));
    return hasYamlExtension && hasLegacyKeyword;
  };

  // Function to check if path is a workflow file
  const isWorkflowFile = (path) => {
    const lowerPath = path.toLowerCase();
    return lowerPath.includes('.github/workflows/') && 
           (lowerPath.endsWith('.yml') || lowerPath.endsWith('.yaml'));
  };

  // Add keyword to the list
  const addKeyword = () => {
    const trimmed = newKeyword.trim().toLowerCase();
    if (trimmed && !keywords.includes(trimmed)) {
      setKeywords([...keywords, trimmed]);
      setNewKeyword('');
    }
  };

  // Remove keyword from the list
  const removeKeyword = (keyword) => {
    setKeywords(keywords.filter(k => k !== keyword));
  };

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
      
      const status = await githubAPI.checkTokenStatus();
      setTokenStatus(status);
      
      if (status.has_token && status.is_valid) {
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

  // Timer effect for tracking scan duration
  useEffect(() => {
    let interval;
    if (scanning && scanStartTimeRef.current) {
      interval = setInterval(() => {
        setScanDuration(Math.floor((Date.now() - scanStartTimeRef.current) / 1000));
      }, 1000);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [scanning]);

  // Reset to first page when filters change
  useEffect(() => {
    setCurrentPage(1);
  }, [repositoryFilter, reasonFilter, keywordFilter, branchFilter, itemsPerPage]);

  const scanForLegacyConfigs = async () => {
    try {
      setScanning(true);
      setError('');
      setLegacyFiles([]);
      setSelectedFiles(new Set());
      setScanProgress({ current: 0, total: 0 });
      scanStartTimeRef.current = Date.now();
      setScanDuration(0);
      setCurrentPage(1);
      setCompletedScanDuration(null);
      console.log('Scan started at:', scanStartTimeRef.current);
      
      // First, load repositories if not already loaded
      let reposToScan = repositories;
      if (repositories.length === 0) {
        try {
          const scope = selectedScope;
          const org = selectedScope === 'organization' ? selectedOrg : null;
          
          const data = selectedScope === 'user'
            ? await githubAPI.getRepositories(scope, null, 'all')
            : await githubAPI.getRepositories(scope, org, 'all');
          
          reposToScan = data.repositories || [];
          setRepositories(reposToScan);
        } catch (err) {
          setError(`Failed to load repositories: ${err.message}`);
          setScanning(false);
          return;
        }
      }

      const foundFiles = [];
      setScanProgress({ current: 0, total: reposToScan.length });

      // Parallel processing with batches to improve performance
      const BATCH_SIZE = 10; // Process 10 repos at a time
      const batches = [];
      
      for (let i = 0; i < reposToScan.length; i += BATCH_SIZE) {
        batches.push(reposToScan.slice(i, i + BATCH_SIZE));
      }

      let processedCount = 0;

      for (const batch of batches) {
        const batchPromises = batch.map(async (repo) => {
          const repoName = repo.full_name;
          
          try {
            let branchesToScan = ['main']; // Default to main branch
            
            // If scanning all branches, fetch the list of branches
            if (scanAllBranches) {
              try {
                const [owner, repoNameOnly] = repoName.split('/');
                const branchesResponse = await fetch(`http://localhost:8000/api/github/repositories/${owner}/${repoNameOnly}/branches`);
                if (branchesResponse.ok) {
                  const branchesData = await branchesResponse.json();
                  branchesToScan = branchesData.branches?.map(b => b.name) || ['main'];
                  console.log(`Repository ${repoName}: scanning ${branchesToScan.length} branches:`, branchesToScan);
                } else {
                  console.warn(`Failed to get branches for ${repoName}: ${branchesResponse.status}`);
                }
              } catch (err) {
                console.warn(`Error fetching branches for ${repoName}:`, err);
              }
            } else {
              console.log(`Repository ${repoName}: scanning default branch only`);
            }
            
            const repoLegacyFiles = [];
            
            // Scan each branch
            for (const branch of branchesToScan) {
              try {
                console.log(`Scanning ${repoName} branch: ${branch}`);
                // Get repository tree for this branch
                const response = await fetch(`http://localhost:8000/api/github/repositories/${repoName}/tree?branch=${encodeURIComponent(branch)}`);
                
                if (!response.ok) {
                  console.warn(`Failed to get tree for ${repoName} branch ${branch}`);
                  continue;
                }
                
                const treeData = await response.json();
                const files = treeData.tree || [];
            
                // Check for legacy config files (anywhere in the repository)
                for (const file of files) {
              if (file.type !== 'blob') continue;
              
              const fileName = file.path.split('/').pop();
              
              // Check 1: Legacy config files by filename (YAML/YML files with keywords in name)
              if (isLegacyConfigFile(fileName)) {
                // Find which keywords matched in the filename
                const matchedKeywords = keywords.filter(keyword => 
                  fileName.toLowerCase().includes(keyword.toLowerCase())
                );
                
                  repoLegacyFiles.push({
                    repository: repoName,
                    path: file.path,
                    branch: branch,
                    sha: file.sha,
                    url: file.url,
                    id: `${repoName}:${branch}:${file.path}`,
                    reason: 'Legacy filename',
                    matchedKeywords: matchedKeywords
                  });
                // Skip content check since we already found it by filename
                continue;
              }
              
              // Check 2: Workflow files with legacy keywords in content (only if not already found by filename)
              if (isWorkflowFile(file.path)) {
                try {
                  const contentResponse = await fetch(`http://localhost:8000/api/github/repositories/${repoName}/contents/${encodeURIComponent(file.path)}`);
                  
                  if (contentResponse.ok) {
                    const contentData = await contentResponse.json();
                    const content = contentData.content || '';
                    
                    // Decode base64 content
                    let decodedContent = '';
                    try {
                      decodedContent = atob(content);
                    } catch (e) {
                      // If not base64, use as is
                      decodedContent = content;
                    }
                    
                    // Find which keywords matched
                    const matchedKeywords = keywords.filter(keyword => 
                      decodedContent.toLowerCase().includes(keyword.toLowerCase())
                    );
                    
                    if (matchedKeywords.length > 0) {
                        repoLegacyFiles.push({
                          repository: repoName,
                          path: file.path,
                          branch: branch,
                          sha: file.sha,
                          url: file.url,
                          id: `${repoName}:${branch}:${file.path}`,
                          reason: 'Workflow with legacy keywords',
                          matchedKeywords: matchedKeywords
                        });
                    }
                  }
                } catch (err) {
                  console.error(`Error checking workflow content for ${file.path}:`, err);
                }
              }
                }
              } catch (err) {
                console.error(`Error scanning ${repoName} branch ${branch}:`, err);
              }
            }
            
            return repoLegacyFiles;
          } catch (err) {
            console.error(`Error scanning ${repoName}:`, err);
            return [];
          }
        });

        // Wait for the batch to complete
        const batchResults = await Promise.all(batchPromises);
        
        // Add results to foundFiles
        batchResults.forEach(files => foundFiles.push(...files));
        
        // Update progress
        processedCount += batch.length;
        setScanProgress({ current: processedCount, total: reposToScan.length });
        
        // Update UI with current results
        setLegacyFiles([...foundFiles]);
      }

      setScanProgress({ current: 0, total: 0 });
      
      // Calculate and set scan duration
      const now = Date.now();
      const duration = scanStartTimeRef.current ? Math.floor((now - scanStartTimeRef.current) / 1000) : 0;
      console.log('Scan completion - now:', now, 'scanStartTime:', scanStartTimeRef.current, 'duration:', duration);
      setCompletedScanDuration(duration);
      scanStartTimeRef.current = null;
      
      if (foundFiles.length === 0) {
        setNotification({
          type: 'success',
          message: '✅ No legacy configuration files found!'
        });
      } else {
        setNotification({
          type: 'info',
          message: `Found ${foundFiles.length} legacy configuration file(s)`
        });
      }
    } catch (err) {
      setError(`Failed to scan for legacy configs: ${err.message}`);
    } finally {
      setScanning(false);
      setScanProgress({ current: 0, total: 0 });
    }
  };

  const toggleFileSelection = (fileId) => {
    const newSelection = new Set(selectedFiles);
    if (newSelection.has(fileId)) {
      newSelection.delete(fileId);
    } else {
      newSelection.add(fileId);
    }
    setSelectedFiles(newSelection);
  };

  const toggleSelectAll = () => {
    const filteredFiles = legacyFiles.filter(file => 
      (repositoryFilter === 'all' || file.repository === repositoryFilter) &&
      (reasonFilter === 'all' || file.reason === reasonFilter) &&
      (keywordFilter === 'all' || (file.matchedKeywords && file.matchedKeywords.includes(keywordFilter))) &&
      (branchFilter === 'all' || file.branch === branchFilter)
    );
    const filteredIds = filteredFiles.map(f => f.id);
    const allFilteredSelected = filteredIds.every(id => selectedFiles.has(id));
    
    if (allFilteredSelected && filteredIds.length > 0) {
      // Deselect all filtered files
      const newSelection = new Set(selectedFiles);
      filteredIds.forEach(id => newSelection.delete(id));
      setSelectedFiles(newSelection);
    } else {
      // Select all filtered files
      const newSelection = new Set(selectedFiles);
      filteredIds.forEach(id => newSelection.add(id));
      setSelectedFiles(newSelection);
    }
  };

  const openConfirmModal = () => {
    if (selectedFiles.size === 0) {
      setNotification({
        type: 'error',
        message: 'No files selected for deletion'
      });
      return;
    }
    setShowConfirmModal(true);
  };

  const deleteSelectedFiles = async () => {
    setShowConfirmModal(false);

    try {
      setDeleting(true);
      setError('');
      let successCount = 0;
      let failCount = 0;

      for (const fileId of selectedFiles) {
        const file = legacyFiles.find(f => f.id === fileId);
        if (!file) continue;

        try {
          const endpoint = deletionMode === 'pr' 
            ? `http://localhost:8000/api/github/repositories/${file.repository}/delete-file-pr`
            : `http://localhost:8000/api/github/repositories/${file.repository}/delete-file`;
          
          const response = await fetch(endpoint, {
            method: deletionMode === 'pr' ? 'POST' : 'DELETE',
            headers: {
              'Content-Type': 'application/json'
            },
            body: JSON.stringify({
              file_path: file.path,
              commit_message: `Remove legacy ${file.path} configuration file`,
              pr_title: `Remove legacy configuration file: ${file.path}`,
              pr_body: `This pull request removes the legacy configuration file \`${file.path}\`.\n\nThis file is no longer needed as we have migrated to the new configuration system.`
            })
          });

          if (response.ok) {
            successCount++;
          } else {
            failCount++;
            const errorData = await response.json();
            const actionText = deletionMode === 'pr' ? 'create PR for' : 'delete';
            console.error(`Failed to ${actionText} ${file.path}:`, errorData);
          }
        } catch (err) {
          failCount++;
          console.error(`Error processing ${file.path}:`, err);
        }
      }

      // Remove processed files from the list if direct deletion
      if (deletionMode === 'direct') {
        setLegacyFiles(legacyFiles.filter(f => !selectedFiles.has(f.id)));
        setSelectedFiles(new Set());
      }

      const actionText = deletionMode === 'pr' ? 'Created PR for' : 'Deleted';
      setNotification({
        type: successCount > 0 ? 'success' : 'error',
        message: `✅ ${actionText} ${successCount} file(s)${failCount > 0 ? `, ${failCount} failed` : ''}`
      });
    } catch (err) {
      setError(`Failed to delete files: ${err.message}`);
    } finally {
      setDeleting(false);
    }
  };

  if (loading) {
    return (
      <div className="container">
        <div className="loading-container">
          <div className="loading-spinner"></div>
          <p>Loading...</p>
        </div>
      </div>
    );
  }

  if (!tokenStatus?.has_token || !tokenStatus?.is_valid) {
    return (
      <div className="container">
        <div className="error-container">
          <h2>⚠️ GitHub Token Required</h2>
          <p>Please configure your GitHub token in the Secrets Management tab.</p>
        </div>
      </div>
    );
  }

  return (
    <div style={{
      maxWidth: '1400px',
      margin: '40px auto',
      padding: '40px',
      background: 'white',
      borderRadius: '24px',
      boxShadow: '0 20px 60px rgba(0, 0, 0, 0.3)',
      minHeight: 'calc(100vh - 260px)'
    }}>
      <div style={{
        marginBottom: '40px',
        paddingBottom: '24px',
        borderBottom: '1px solid #e8e8e8'
      }}>
        <h2 style={{
          margin: '0 0 12px 0',
          fontSize: '32px',
          fontWeight: '700',
          background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
          WebkitBackgroundClip: 'text',
          WebkitTextFillColor: 'transparent',
          backgroundClip: 'text'
        }}>🧹 Legacy Configuration Cleanup</h2>
        <p style={{
          margin: 0,
          color: '#666',
          fontSize: '15px',
          lineHeight: '1.6'
        }}>Scan repositories for legacy YAML/YML files containing "coverity" or "polaris" in the filename</p>
      </div>

      {/* Notification */}
      {notification && (
        <div className={`notification ${notification.type}`} style={{
          padding: '16px 20px',
          borderRadius: '16px',
          marginBottom: '24px',
          background: notification.type === 'success' ? 'linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%)' : 
                     notification.type === 'error' ? 'linear-gradient(135deg, #f8d7da 0%, #f5c6cb 100%)' : 'linear-gradient(135deg, #d1ecf1 0%, #bee5eb 100%)',
          color: notification.type === 'success' ? '#155724' : 
                 notification.type === 'error' ? '#721c24' : '#0c5460',
          border: 'none',
          boxShadow: '0 4px 12px rgba(0, 0, 0, 0.08)',
          fontWeight: '500',
          fontSize: '14px'
        }}>
          {notification.message}
        </div>
      )}

      {/* Error Display */}
      {error && (
        <div className="error-message" style={{
          background: 'linear-gradient(135deg, #f8d7da 0%, #f5c6cb 100%)',
          color: '#721c24',
          padding: '16px 20px',
          borderRadius: '16px',
          marginBottom: '24px',
          border: 'none',
          boxShadow: '0 4px 12px rgba(0, 0, 0, 0.08)',
          fontWeight: '500',
          fontSize: '14px'
        }}>
          {error}
        </div>
      )}

      {/* User Info */}
      {userInfo && (
          <div className="user-info" style={{
          background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
          color: 'white',
          padding: '20px 24px',
          borderRadius: '16px',
          marginBottom: '32px',
          display: 'flex',
          alignItems: 'center',
          gap: '16px',
          border: 'none',
          boxShadow: '0 8px 24px rgba(102, 126, 234, 0.3)'
        }}>
          {userInfo.avatar_url && (
            <img src={userInfo.avatar_url} alt="Avatar" style={{
              width: '56px',
              height: '56px',
              borderRadius: '50%',
              border: '3px solid white',
              boxShadow: '0 4px 12px rgba(0, 0, 0, 0.15)'
            }} />
          )}
          <div>
            <div style={{ fontWeight: '600', fontSize: '16px' }}>{userInfo.name || userInfo.login}</div>
            <div style={{ opacity: '0.9', fontSize: '14px' }}>@{userInfo.login}</div>
          </div>
        </div>
      )}

      {/* Scope Selection */}
      <div className="form-group" style={{ marginBottom: '32px' }}>
        <label style={{
          display: 'block',
          marginBottom: '12px',
          fontWeight: '600',
          fontSize: '15px',
          color: '#333'
        }}>Scope:</label>
        <div style={{ display: 'flex', gap: '12px' }}>
          <button
            onClick={() => {
              setSelectedScope('user');
              setSelectedOrg('');
              setRepositories([]);
              setLegacyFiles([]);
            }}
            style={{
              padding: '12px 28px',
              borderRadius: '12px',
              border: 'none',
              background: selectedScope === 'user' ? 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' : '#f5f5f5',
              color: selectedScope === 'user' ? 'white' : '#666',
              cursor: 'pointer',
              fontWeight: '600',
              fontSize: '14px',
              transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
              boxShadow: selectedScope === 'user' ? '0 4px 12px rgba(102, 126, 234, 0.4)' : '0 2px 8px rgba(0, 0, 0, 0.05)',
              transform: selectedScope === 'user' ? 'translateY(-2px)' : 'none'
            }}
            onMouseOver={(e) => {
              if (selectedScope !== 'user') {
                e.target.style.background = '#e8e8e8';
                e.target.style.transform = 'translateY(-2px)';
              }
            }}
            onMouseOut={(e) => {
              if (selectedScope !== 'user') {
                e.target.style.background = '#f5f5f5';
                e.target.style.transform = 'none';
              }
            }}
          >
            👤 User Repositories
          </button>
          <button
            onClick={() => {
              setSelectedScope('organization');
              setRepositories([]);
              setLegacyFiles([]);
            }}
            style={{
              padding: '12px 28px',
              borderRadius: '12px',
              border: 'none',
              background: selectedScope === 'organization' ? 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' : '#f5f5f5',
              color: selectedScope === 'organization' ? 'white' : '#666',
              cursor: 'pointer',
              fontWeight: '600',
              fontSize: '14px',
              transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
              boxShadow: selectedScope === 'organization' ? '0 4px 12px rgba(102, 126, 234, 0.4)' : '0 2px 8px rgba(0, 0, 0, 0.05)',
              transform: selectedScope === 'organization' ? 'translateY(-2px)' : 'none'
            }}
            onMouseOver={(e) => {
              if (selectedScope !== 'organization') {
                e.target.style.background = '#e8e8e8';
                e.target.style.transform = 'translateY(-2px)';
              }
            }}
            onMouseOut={(e) => {
              if (selectedScope !== 'organization') {
                e.target.style.background = '#f5f5f5';
                e.target.style.transform = 'none';
              }
            }}
          >
            🏢 Organization
          </button>
          </div>
      </div>

      {/* Organization Selection */}
      {selectedScope === 'organization' && (
        <div className="form-group" style={{ marginBottom: '32px' }}>
          <label style={{
            display: 'block',
            marginBottom: '12px',
            fontWeight: '600',
            fontSize: '15px',
            color: '#333'
          }}>Select Organization:</label>
          <select
            value={selectedOrg}
            onChange={(e) => {
              setSelectedOrg(e.target.value);
              setRepositories([]);
              setLegacyFiles([]);
            }}
            style={{
              width: '100%',
              padding: '14px 16px',
              borderRadius: '12px',
              border: '2px solid #e8e8e8',
              fontSize: '14px',
              backgroundColor: '#fff',
              color: '#333',
              cursor: 'pointer',
              transition: 'all 0.3s ease',
              boxShadow: '0 2px 8px rgba(0, 0, 0, 0.05)'
            }}
            onFocus={(e) => {
              e.target.style.borderColor = '#667eea';
              e.target.style.boxShadow = '0 4px 12px rgba(102, 126, 234, 0.2)';
            }}
            onBlur={(e) => {
              e.target.style.borderColor = '#e8e8e8';
              e.target.style.boxShadow = '0 2px 8px rgba(0, 0, 0, 0.05)';
            }}
          >
            <option value="">-- Select Organization --</option>
            {organizations.map(org => (
              <option key={org.login} value={org.login}>{org.login}</option>
            ))}
          </select>
        </div>
      )}

      {/* Keywords Management */}
      <div className="form-group" style={{ marginBottom: '32px' }}>
        <label style={{
          display: 'block',
          marginBottom: '12px',
          fontWeight: '600',
          fontSize: '15px',
          color: '#333'
        }}>Search Keywords:</label>
        
        {/* Current Keywords Display */}
        <div style={{ marginBottom: '16px', display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
          {keywords.map(keyword => (
            <div key={keyword} style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '8px',
              padding: '8px 14px',
              background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
              color: 'white',
              borderRadius: '20px',
              fontSize: '13px',
              fontWeight: '500',
              boxShadow: '0 2px 8px rgba(102, 126, 234, 0.3)'
            }}>
              <span>{keyword}</span>
              <button
                onClick={() => removeKeyword(keyword)}
                style={{
                  background: 'rgba(255, 255, 255, 0.3)',
                  border: 'none',
                  borderRadius: '50%',
                  width: '20px',
                  height: '20px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  cursor: 'pointer',
                  fontSize: '12px',
                  color: 'white',
                  fontWeight: 'bold',
                  transition: 'all 0.2s ease'
                }}
                onMouseOver={(e) => {
                  e.target.style.background = 'rgba(255, 255, 255, 0.5)';
                }}
                onMouseOut={(e) => {
                  e.target.style.background = 'rgba(255, 255, 255, 0.3)';
                }}
                title="Remove keyword"
              >
                ×
              </button>
            </div>
          ))}
        </div>
        
        {/* Add New Keyword Input */}
        <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
          <input
            type="text"
            value={newKeyword}
            onChange={(e) => setNewKeyword(e.target.value)}
            onKeyPress={(e) => {
              if (e.key === 'Enter') {
                e.preventDefault();
                addKeyword();
              }
            }}
            placeholder="Add new keyword..."
            style={{
              flex: 1,
              padding: '12px 16px',
              borderRadius: '12px',
              border: '2px solid #e8e8e8',
              fontSize: '14px',
              transition: 'all 0.3s ease',
              outline: 'none'
            }}
            onFocus={(e) => {
              e.target.style.borderColor = '#667eea';
              e.target.style.boxShadow = '0 4px 12px rgba(102, 126, 234, 0.2)';
            }}
            onBlur={(e) => {
              e.target.style.borderColor = '#e8e8e8';
              e.target.style.boxShadow = 'none';
            }}
          />
          <button
            onClick={addKeyword}
            disabled={!newKeyword.trim()}
            style={{
              padding: '12px 24px',
              background: newKeyword.trim() ? 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' : '#ddd',
              color: 'white',
              border: 'none',
              borderRadius: '12px',
              cursor: newKeyword.trim() ? 'pointer' : 'not-allowed',
              fontWeight: '600',
              fontSize: '14px',
              transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
              boxShadow: newKeyword.trim() ? '0 4px 12px rgba(102, 126, 234, 0.4)' : 'none'
            }}
            onMouseOver={(e) => {
              if (newKeyword.trim()) {
                e.target.style.transform = 'translateY(-2px)';
                e.target.style.boxShadow = '0 6px 20px rgba(102, 126, 234, 0.5)';
              }
            }}
            onMouseOut={(e) => {
              if (newKeyword.trim()) {
                e.target.style.transform = 'none';
                e.target.style.boxShadow = '0 4px 12px rgba(102, 126, 234, 0.4)';
              }
            }}
          >
            ➕ Add
          </button>
        </div>
      </div>

      {/* Branch Selection */}
      <div className="form-group" style={{ marginBottom: '32px' }}>
        <label style={{
          display: 'block',
          marginBottom: '12px',
          fontWeight: '600',
          fontSize: '15px',
          color: '#333'
        }}>Scan branches:</label>
        <div style={{ display: 'flex', gap: '12px' }}>
          <label style={{
            display: 'flex',
            alignItems: 'center',
            cursor: 'pointer',
            padding: '12px 20px',
            borderRadius: '12px',
            border: scanAllBranches === false ? '3px solid #667eea' : '2px solid #e8e8e8',
            background: scanAllBranches === false ? 'linear-gradient(135deg, rgba(102, 126, 234, 0.1) 0%, rgba(118, 75, 162, 0.1) 100%)' : 'white',
            transition: 'all 0.3s ease',
            fontSize: '14px',
            fontWeight: '600',
            boxShadow: scanAllBranches === false ? '0 4px 12px rgba(102, 126, 234, 0.2)' : '0 2px 8px rgba(0, 0, 0, 0.05)'
          }}>
            <input
              type="radio"
              name="branchSelection"
              checked={scanAllBranches === false}
              onChange={() => setScanAllBranches(false)}
              style={{
                marginRight: '10px',
                cursor: 'pointer',
                width: '18px',
                height: '18px',
                accentColor: '#667eea'
              }}
            />
            🌿 Default branch only
          </label>
          <label style={{
            display: 'flex',
            alignItems: 'center',
            cursor: 'pointer',
            padding: '12px 20px',
            borderRadius: '12px',
            border: scanAllBranches === true ? '3px solid #667eea' : '2px solid #e8e8e8',
            background: scanAllBranches === true ? 'linear-gradient(135deg, rgba(102, 126, 234, 0.1) 0%, rgba(118, 75, 162, 0.1) 100%)' : 'white',
            transition: 'all 0.3s ease',
            fontSize: '14px',
            fontWeight: '600',
            boxShadow: scanAllBranches === true ? '0 4px 12px rgba(102, 126, 234, 0.2)' : '0 2px 8px rgba(0, 0, 0, 0.05)'
          }}>
            <input
              type="radio"
              name="branchSelection"
              checked={scanAllBranches === true}
              onChange={() => setScanAllBranches(true)}
              style={{
                marginRight: '10px',
                cursor: 'pointer',
                width: '18px',
                height: '18px',
                accentColor: '#667eea'
              }}
            />
            🌳 All branches
          </label>
        </div>
      </div>

      {/* Scan Button */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '20px', flexWrap: 'wrap' }}>
        <button
          onClick={scanForLegacyConfigs}
          disabled={scanning || (selectedScope === 'organization' && !selectedOrg)}
          style={{
          padding: '14px 36px',
          background: scanning || (selectedScope === 'organization' && !selectedOrg) ? '#ccc' : 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
          color: 'white',
          border: 'none',
          borderRadius: '12px',
          cursor: scanning || (selectedScope === 'organization' && !selectedOrg) ? 'not-allowed' : 'pointer',
          fontWeight: '600',
          fontSize: '15px',
          transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
          boxShadow: scanning || (selectedScope === 'organization' && !selectedOrg) ? 'none' : '0 4px 12px rgba(102, 126, 234, 0.4)',
          transform: 'none'
        }}
        onMouseOver={(e) => {
          if (!scanning && !(selectedScope === 'organization' && !selectedOrg)) {
            e.target.style.transform = 'translateY(-2px)';
            e.target.style.boxShadow = '0 6px 20px rgba(102, 126, 234, 0.5)';
          }
        }}
        onMouseOut={(e) => {
          if (!scanning && !(selectedScope === 'organization' && !selectedOrg)) {
            e.target.style.transform = 'none';
            e.target.style.boxShadow = '0 4px 12px rgba(102, 126, 234, 0.4)';
          }
        }}
      >
        {scanning ? (scanProgress.total > 0 ? `🔍 Scanning... (${scanProgress.current}/${scanProgress.total})` : '🔍 Scanning...') : '🔍 Scan for Legacy Configs'}
      </button>
        
        {scanning && (
          <div style={{
            padding: '12px 24px',
            background: 'linear-gradient(135deg, #667eea15 0%, #764ba215 100%)',
            borderRadius: '8px',
            border: '1px solid #667eea30',
            display: 'flex',
            alignItems: 'center',
            gap: '10px',
            fontSize: '14px',
            fontWeight: '500',
            color: '#667eea'
          }}>
            <span style={{ fontSize: '18px' }}>⏱️</span>
            <span>Scan Duration: {Math.floor(scanDuration / 60)}:{(scanDuration % 60).toString().padStart(2, '0')}</span>
          </div>
        )}
      </div>

      {/* Dashboard Visualizations */}
      {legacyFiles.length > 0 && (
        <div style={{ marginTop: '40px', marginBottom: '40px' }}>
          <Dashboard legacyFiles={legacyFiles} scanDuration={completedScanDuration} />
        </div>
      )}

      {/* Legacy Files List */}
      {legacyFiles.length > 0 && (
          <div style={{ marginTop: '40px' }}>
            <div style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              marginBottom: '24px',
              paddingBottom: '20px',
              borderBottom: '1px solid #e8e8e8'
            }}>
              <h3 style={{
                margin: 0,
                fontSize: '22px',
                fontWeight: '700',
                background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
                backgroundClip: 'text'
              }}>Found {legacyFiles.length} Legacy Configuration File(s)</h3>
              
              <div style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
                {/* Completed Scan Duration */}
                {completedScanDuration !== null && (
                  <div style={{
                    padding: '8px 16px',
                    background: 'linear-gradient(135deg, #43e97b15 0%, #38f9d715 100%)',
                    borderRadius: '8px',
                    border: '1px solid #43e97b30',
                    fontSize: '13px',
                    fontWeight: '500',
                    color: '#059669',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px'
                  }}>
                    <span>⏱️</span>
                    <span>Scan completed in {Math.floor(completedScanDuration / 60)}:{(completedScanDuration % 60).toString().padStart(2, '0')}</span>
                  </div>
                )}
                
                {/* Page Size Selector */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                  <label style={{ fontSize: '14px', fontWeight: '500', color: '#666' }}>Per page:</label>
                  <select
                    value={itemsPerPage}
                    onChange={(e) => setItemsPerPage(Number(e.target.value))}
                    style={{
                      padding: '8px 12px',
                      fontSize: '14px',
                      border: '1px solid #ddd',
                      borderRadius: '6px',
                      cursor: 'pointer',
                      background: 'white'
                    }}
                  >
                    <option value={10}>10</option>
                    <option value={20}>20</option>
                    <option value={50}>50</option>
                    <option value={100}>100</option>
                  </select>
                </div>
              </div>
            </div>

            {/* Filter Bar */}
            <div style={{ 
              display: 'flex', 
              gap: '16px', 
              marginBottom: '24px',
              flexWrap: 'wrap',
              alignItems: 'center'
            }}>
              {/* Repository Filter */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <label style={{ fontSize: '14px', fontWeight: '500', color: '#666' }}>Repository:</label>
                <select
                  value={repositoryFilter}
                  onChange={(e) => {
                    setRepositoryFilter(e.target.value);
                    setSelectedFiles(new Set()); // Clear selection when filter changes
                  }}
                  style={{
                    padding: '10px 16px',
                    borderRadius: '12px',
                    border: '2px solid #e8e8e8',
                    fontSize: '14px',
                    cursor: 'pointer',
                    minWidth: '250px',
                    backgroundColor: '#fff',
                    transition: 'all 0.3s ease',
                    boxShadow: '0 2px 8px rgba(0, 0, 0, 0.05)'
                  }}
                  onFocus={(e) => {
                    e.target.style.borderColor = '#667eea';
                    e.target.style.boxShadow = '0 4px 12px rgba(102, 126, 234, 0.2)';
                  }}
                  onBlur={(e) => {
                    e.target.style.borderColor = '#e8e8e8';
                    e.target.style.boxShadow = '0 2px 8px rgba(0, 0, 0, 0.05)';
                  }}
                >
                  <option value="all">All Repositories</option>
                  {[...new Set(legacyFiles.map(f => f.repository))].sort().map(repo => (
                    <option key={repo} value={repo}>
                      {repo} ({legacyFiles.filter(f => f.repository === repo).length})
                    </option>
                  ))}
                </select>
                
                <label style={{ fontSize: '14px', fontWeight: '500', color: '#666', marginLeft: '12px' }}>Type:</label>
                <select
                  value={reasonFilter}
                  onChange={(e) => {
                    setReasonFilter(e.target.value);
                    setSelectedFiles(new Set()); // Clear selection when filter changes
                  }}
                  style={{
                    padding: '10px 16px',
                    borderRadius: '12px',
                    border: '2px solid #e8e8e8',
                    fontSize: '14px',
                    cursor: 'pointer',
                    minWidth: '250px',
                    backgroundColor: '#fff',
                    transition: 'all 0.3s ease',
                    boxShadow: '0 2px 8px rgba(0, 0, 0, 0.05)'
                  }}
                  onFocus={(e) => {
                    e.target.style.borderColor = '#667eea';
                    e.target.style.boxShadow = '0 4px 12px rgba(102, 126, 234, 0.2)';
                  }}
                  onBlur={(e) => {
                    e.target.style.borderColor = '#e8e8e8';
                    e.target.style.boxShadow = '0 2px 8px rgba(0, 0, 0, 0.05)';
                  }}
                >
                  <option value="all">All Types</option>
                  <option value="Legacy filename">Legacy filename</option>
                  <option value="Workflow with legacy keywords">Workflow with legacy keywords</option>
                </select>
                
                <label style={{ fontSize: '14px', fontWeight: '500', color: '#666', marginLeft: '12px' }}>Keyword:</label>
                <select
                  value={keywordFilter}
                  onChange={(e) => {
                    setKeywordFilter(e.target.value);
                    setSelectedFiles(new Set()); // Clear selection when filter changes
                  }}
                  style={{
                    padding: '10px 16px',
                    borderRadius: '12px',
                    border: '2px solid #e8e8e8',
                    fontSize: '14px',
                    cursor: 'pointer',
                    minWidth: '200px',
                    backgroundColor: '#fff',
                    transition: 'all 0.3s ease',
                    boxShadow: '0 2px 8px rgba(0, 0, 0, 0.05)'
                  }}
                  onFocus={(e) => {
                    e.target.style.borderColor = '#667eea';
                    e.target.style.boxShadow = '0 4px 12px rgba(102, 126, 234, 0.2)';
                  }}
                  onBlur={(e) => {
                    e.target.style.borderColor = '#e8e8e8';
                    e.target.style.boxShadow = '0 2px 8px rgba(0, 0, 0, 0.05)';
                  }}
                >
                  <option value="all">All Keywords</option>
                  {keywords.map(keyword => (
                    <option key={keyword} value={keyword}>{keyword}</option>
                  ))}
                </select>
                
                <label style={{ fontSize: '14px', fontWeight: '500', color: '#666', marginLeft: '12px' }}>Branch:</label>
                <select
                  value={branchFilter}
                  onChange={(e) => {
                    setBranchFilter(e.target.value);
                    setSelectedFiles(new Set()); // Clear selection when filter changes
                  }}
                  style={{
                    padding: '10px 16px',
                    borderRadius: '12px',
                    border: '2px solid #e8e8e8',
                    fontSize: '14px',
                    cursor: 'pointer',
                    minWidth: '200px',
                    backgroundColor: '#fff',
                    transition: 'all 0.3s ease',
                    boxShadow: '0 2px 8px rgba(0, 0, 0, 0.05)'
                  }}
                  onFocus={(e) => {
                    e.target.style.borderColor = '#667eea';
                    e.target.style.boxShadow = '0 4px 12px rgba(102, 126, 234, 0.2)';
                  }}
                  onBlur={(e) => {
                    e.target.style.borderColor = '#e8e8e8';
                    e.target.style.boxShadow = '0 2px 8px rgba(0, 0, 0, 0.05)';
                  }}
                >
                  <option value="all">All Branches</option>
                  {[...new Set(legacyFiles.map(f => f.branch || 'main'))].sort().map(branch => (
                    <option key={branch} value={branch}>{branch}</option>
                  ))}
                </select>
              </div>
            </div>

            <div style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
            marginBottom: '20px'
          }}>
            <div style={{ display: 'flex', gap: '12px' }}>
              <button
                onClick={toggleSelectAll}
                style={{
                  padding: '10px 20px',
                  background: '#f5f5f5',
                  color: '#333',
                  border: 'none',
                  borderRadius: '12px',
                  cursor: 'pointer',
                  fontSize: '14px',
                  fontWeight: '600',
                  transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
                  boxShadow: '0 2px 8px rgba(0, 0, 0, 0.05)'
                }}
                onMouseOver={(e) => {
                  e.target.style.background = '#e8e8e8';
                  e.target.style.transform = 'translateY(-2px)';
                  e.target.style.boxShadow = '0 4px 12px rgba(0, 0, 0, 0.1)';
                }}
                onMouseOut={(e) => {
                  e.target.style.background = '#f5f5f5';
                  e.target.style.transform = 'none';
                  e.target.style.boxShadow = '0 2px 8px rgba(0, 0, 0, 0.05)';
                }}
              >
                {selectedFiles.size === legacyFiles.length ? '❌ Deselect All' : '✅ Select All'}
              </button>
              <button
                onClick={openConfirmModal}
                disabled={selectedFiles.size === 0}
                style={{
                  padding: '10px 20px',
                  background: selectedFiles.size > 0 ? 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)' : '#ddd',
                  color: 'white',
                  border: 'none',
                  borderRadius: '12px',
                  cursor: selectedFiles.size > 0 ? 'pointer' : 'not-allowed',
                  fontWeight: '600',
                  fontSize: '14px',
                  transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
                  boxShadow: selectedFiles.size > 0 ? '0 4px 12px rgba(245, 87, 108, 0.4)' : 'none'
                }}
                onMouseOver={(e) => {
                  if (selectedFiles.size > 0) {
                    e.target.style.transform = 'translateY(-2px)';
                    e.target.style.boxShadow = '0 6px 20px rgba(245, 87, 108, 0.5)';
                  }
                }}
                onMouseOut={(e) => {
                  if (selectedFiles.size > 0) {
                    e.target.style.transform = 'none';
                    e.target.style.boxShadow = '0 4px 12px rgba(245, 87, 108, 0.4)';
                  }
                }}
              >
                {`🗑️ Remove Selected (${selectedFiles.size})`}
              </button>
            </div>
          </div>

            {(() => {
              // Calculate filtered files
              const filteredFiles = legacyFiles.filter(file => 
                (repositoryFilter === 'all' || file.repository === repositoryFilter) &&
                (reasonFilter === 'all' || file.reason === reasonFilter) &&
                (keywordFilter === 'all' || (file.matchedKeywords && file.matchedKeywords.includes(keywordFilter))) &&
                (branchFilter === 'all' || file.branch === branchFilter)
              );

              // Calculate pagination
              const totalPages = Math.ceil(filteredFiles.length / itemsPerPage);
              const startIndex = (currentPage - 1) * itemsPerPage;
              const endIndex = startIndex + itemsPerPage;
              const paginatedFiles = filteredFiles.slice(startIndex, endIndex);

              return (
                <>
                  {/* Pagination Info and Controls */}
                  <div style={{ 
                    display: 'flex', 
                    justifyContent: 'space-between', 
                    alignItems: 'center',
                    marginBottom: '20px',
                    padding: '16px',
                    background: '#f8f9fa',
                    borderRadius: '8px'
                  }}>
                    <div style={{ fontSize: '14px', color: '#666' }}>
                      Showing {filteredFiles.length > 0 ? startIndex + 1 : 0} - {Math.min(endIndex, filteredFiles.length)} of {filteredFiles.length} files
                    </div>
                    
                    {totalPages > 1 && (
                      <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                        <button
                          onClick={() => setCurrentPage(1)}
                          disabled={currentPage === 1}
                          style={{
                            padding: '6px 12px',
                            fontSize: '14px',
                            border: '1px solid #ddd',
                            borderRadius: '6px',
                            background: currentPage === 1 ? '#f0f0f0' : 'white',
                            cursor: currentPage === 1 ? 'not-allowed' : 'pointer',
                            color: currentPage === 1 ? '#999' : '#333'
                          }}
                        >
                          ⏮️ First
                        </button>
                        <button
                          onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
                          disabled={currentPage === 1}
                          style={{
                            padding: '6px 12px',
                            fontSize: '14px',
                            border: '1px solid #ddd',
                            borderRadius: '6px',
                            background: currentPage === 1 ? '#f0f0f0' : 'white',
                            cursor: currentPage === 1 ? 'not-allowed' : 'pointer',
                            color: currentPage === 1 ? '#999' : '#333'
                          }}
                        >
                          ◀️ Prev
                        </button>
                        <span style={{ padding: '6px 12px', fontSize: '14px', fontWeight: '500' }}>
                          Page {currentPage} of {totalPages}
                        </span>
                        <button
                          onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))}
                          disabled={currentPage === totalPages}
                          style={{
                            padding: '6px 12px',
                            fontSize: '14px',
                            border: '1px solid #ddd',
                            borderRadius: '6px',
                            background: currentPage === totalPages ? '#f0f0f0' : 'white',
                            cursor: currentPage === totalPages ? 'not-allowed' : 'pointer',
                            color: currentPage === totalPages ? '#999' : '#333'
                          }}
                        >
                          Next ▶️
                        </button>
                        <button
                          onClick={() => setCurrentPage(totalPages)}
                          disabled={currentPage === totalPages}
                          style={{
                            padding: '6px 12px',
                            fontSize: '14px',
                            border: '1px solid #ddd',
                            borderRadius: '6px',
                            background: currentPage === totalPages ? '#f0f0f0' : 'white',
                            cursor: currentPage === totalPages ? 'not-allowed' : 'pointer',
                            color: currentPage === totalPages ? '#999' : '#333'
                          }}
                        >
                          Last ⏭️
                        </button>
                      </div>
                    )}
                  </div>

                  <div style={{
                    border: 'none',
                    borderRadius: '16px',
                    overflow: 'hidden',
                    boxShadow: '0 4px 20px rgba(0, 0, 0, 0.08)',
                    background: 'white'
                  }}>
                    <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                      <thead>
                        <tr style={{ background: 'linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%)', borderBottom: 'none' }}>
                          <th style={{ padding: '18px 20px', textAlign: 'left', width: '60px', fontWeight: '700', fontSize: '12px', color: '#666', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                            <input
                              type="checkbox"
                              checked={(() => {
                                const currentFilteredFiles = legacyFiles.filter(file => 
                                  (repositoryFilter === 'all' || file.repository === repositoryFilter) &&
                                  (reasonFilter === 'all' || file.reason === reasonFilter) &&
                                  (keywordFilter === 'all' || (file.matchedKeywords && file.matchedKeywords.includes(keywordFilter))) &&
                                  (branchFilter === 'all' || file.branch === branchFilter)
                                );
                                return currentFilteredFiles.length > 0 && 
                                       currentFilteredFiles.every(f => selectedFiles.has(f.id));
                              })()}
                        onChange={toggleSelectAll}
                        style={{ cursor: 'pointer' }}
                      />
                    </th>
                    <th style={{ padding: '18px 20px', textAlign: 'left', fontWeight: '700', fontSize: '12px', color: '#666', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Repository</th>
                    <th style={{ padding: '18px 20px', textAlign: 'left', fontWeight: '700', fontSize: '12px', color: '#666', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Branch</th>
                    <th style={{ padding: '18px 20px', textAlign: 'left', fontWeight: '700', fontSize: '12px', color: '#666', textTransform: 'uppercase', letterSpacing: '0.5px' }}>File Path</th>
                    <th style={{ padding: '18px 20px', textAlign: 'center', width: '120px', fontWeight: '700', fontSize: '12px', color: '#666', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Actions</th>
                        </tr>
                      </thead>
                      <tbody>
                        {paginatedFiles.map((file) => (
                    <tr key={file.id} style={{
                      borderTop: '1px solid #f0f0f0',
                      background: selectedFiles.has(file.id) ? 'linear-gradient(135deg, #fff5f9 0%, #ffe5f1 100%)' : 'white',
                      transition: 'all 0.3s ease'
                    }}
                    onMouseOver={(e) => {
                      if (!selectedFiles.has(file.id)) {
                        e.currentTarget.style.background = '#fafafa';
                      }
                    }}
                    onMouseOut={(e) => {
                      if (!selectedFiles.has(file.id)) {
                        e.currentTarget.style.background = 'white';
                      }
                    }}>
                      <td style={{ padding: '18px 20px' }}>
                        <input
                          type="checkbox"
                          checked={selectedFiles.has(file.id)}
                          onChange={() => toggleFileSelection(file.id)}
                          style={{ 
                            cursor: 'pointer',
                            width: '18px',
                            height: '18px',
                            accentColor: '#667eea'
                          }}
                        />
                      </td>
                      <td style={{ padding: '18px 20px', fontWeight: '600', fontSize: '14px', color: '#333' }}>
                        📦 {file.repository}
                      </td>
                      <td style={{ padding: '18px 20px', fontSize: '13px', color: '#667eea', fontWeight: '600' }}>
                        🌿 {file.branch || 'main'}
                      </td>
                      <td style={{ padding: '18px 20px', fontFamily: 'monospace', fontSize: '13px', color: '#f5576c', fontWeight: '500' }}>
                        <div>{file.path}</div>
                        {file.reason && (
                          <div style={{ fontSize: '11px', color: '#999', marginTop: '4px', fontFamily: 'inherit' }}>
                            {file.reason}
                          </div>
                        )}
                        {file.matchedKeywords && file.matchedKeywords.length > 0 && (
                          <div style={{ marginTop: '8px', display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                            {file.matchedKeywords.map(keyword => (
                              <span key={keyword} style={{
                                display: 'inline-block',
                                padding: '4px 10px',
                                background: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
                                color: 'white',
                                borderRadius: '12px',
                                fontSize: '11px',
                                fontWeight: '600',
                                fontFamily: 'inherit',
                                boxShadow: '0 2px 6px rgba(245, 87, 108, 0.3)'
                              }}>
                                {keyword}
                              </span>
                            ))}
                          </div>
                        )}
                      </td>
                      <td style={{ padding: '18px 20px', textAlign: 'center' }}>
                        <button
                          onClick={() => {
                            const url = `https://github.com/${file.repository}/blob/${file.branch || 'main'}/${file.path}`;
                            window.open(url, '_blank', 'noopener,noreferrer');
                          }}
                          style={{
                            padding: '8px 16px',
                            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                            color: 'white',
                            border: 'none',
                            borderRadius: '8px',
                            cursor: 'pointer',
                            fontSize: '13px',
                            fontWeight: '600',
                            transition: 'all 0.3s ease',
                            boxShadow: '0 2px 8px rgba(102, 126, 234, 0.3)'
                          }}
                          onMouseOver={(e) => {
                            e.target.style.transform = 'translateY(-2px)';
                            e.target.style.boxShadow = '0 4px 12px rgba(102, 126, 234, 0.5)';
                          }}
                          onMouseOut={(e) => {
                            e.target.style.transform = 'none';
                            e.target.style.boxShadow = '0 2px 8px rgba(102, 126, 234, 0.3)';
                          }}
                        >
                          👁️ View
                        </button>
                      </td>
                    </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>

                  {/* Bottom Pagination Controls */}
                  {totalPages > 1 && (
                    <div style={{ 
                      display: 'flex', 
                      justifyContent: 'center',
                      alignItems: 'center',
                      marginTop: '24px',
                      gap: '8px'
                    }}>
                      <button
                        onClick={() => setCurrentPage(1)}
                        disabled={currentPage === 1}
                        style={{
                          padding: '8px 16px',
                          fontSize: '14px',
                          border: '1px solid #ddd',
                          borderRadius: '6px',
                          background: currentPage === 1 ? '#f0f0f0' : 'white',
                          cursor: currentPage === 1 ? 'not-allowed' : 'pointer',
                          color: currentPage === 1 ? '#999' : '#333'
                        }}
                      >
                        ⏮️ First
                      </button>
                      <button
                        onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
                        disabled={currentPage === 1}
                        style={{
                          padding: '8px 16px',
                          fontSize: '14px',
                          border: '1px solid #ddd',
                          borderRadius: '6px',
                          background: currentPage === 1 ? '#f0f0f0' : 'white',
                          cursor: currentPage === 1 ? 'not-allowed' : 'pointer',
                          color: currentPage === 1 ? '#999' : '#333'
                        }}
                      >
                        ◀️ Prev
                      </button>
                      <span style={{ padding: '8px 16px', fontSize: '14px', fontWeight: '500' }}>
                        Page {currentPage} of {totalPages}
                      </span>
                      <button
                        onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))}
                        disabled={currentPage === totalPages}
                        style={{
                          padding: '8px 16px',
                          fontSize: '14px',
                          border: '1px solid #ddd',
                          borderRadius: '6px',
                          background: currentPage === totalPages ? '#f0f0f0' : 'white',
                          cursor: currentPage === totalPages ? 'not-allowed' : 'pointer',
                          color: currentPage === totalPages ? '#999' : '#333'
                        }}
                      >
                        Next ▶️
                      </button>
                      <button
                        onClick={() => setCurrentPage(totalPages)}
                        disabled={currentPage === totalPages}
                        style={{
                          padding: '8px 16px',
                          fontSize: '14px',
                          border: '1px solid #ddd',
                          borderRadius: '6px',
                          background: currentPage === totalPages ? '#f0f0f0' : 'white',
                          cursor: currentPage === totalPages ? 'not-allowed' : 'pointer',
                          color: currentPage === totalPages ? '#999' : '#333'
                        }}
                      >
                        Last ⏭️
                      </button>
                    </div>
                  )}
                </>
              );
            })()}
          </div>
      )}

      {/* Confirmation Modal */}
      {showConfirmModal && (
          <div style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: 'rgba(0, 0, 0, 0.7)',
            backdropFilter: 'blur(8px)',
            WebkitBackdropFilter: 'blur(8px)',
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center',
            zIndex: 1000,
            animation: 'fadeIn 0.3s ease'
          }}>
            <div style={{
              background: 'white',
              borderRadius: '24px',
              padding: '40px',
              maxWidth: '650px',
              width: '90%',
              maxHeight: '85vh',
              overflow: 'auto',
              boxShadow: '0 20px 60px rgba(0, 0, 0, 0.4)',
              border: 'none',
              transform: 'scale(1)',
              animation: 'slideUp 0.3s ease'
            }}>
              <h2 style={{ 
                marginTop: 0, 
                marginBottom: '12px', 
                fontSize: '28px', 
                fontWeight: '700',
                background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
                backgroundClip: 'text'
              }}>Confirm File Removal</h2>
              
              <p style={{ marginBottom: '24px', color: '#666', fontSize: '15px', lineHeight: '1.6' }}>
                You have selected <strong style={{ color: '#667eea' }}>{selectedFiles.size}</strong> file(s) for removal:
              </p>

              {/* File List */}
              <div style={{
                maxHeight: '240px',
                overflowY: 'auto',
                border: 'none',
                borderRadius: '16px',
                marginBottom: '28px',
                background: 'linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%)',
                padding: '8px'
              }}>
                {legacyFiles.filter(f => selectedFiles.has(f.id)).map((file, index) => (
                  <div key={file.id} style={{
                    padding: '16px 20px',
                    marginBottom: index < selectedFiles.size - 1 ? '8px' : '0',
                    fontSize: '14px',
                    background: 'white',
                    borderRadius: '12px',
                    boxShadow: '0 2px 8px rgba(0, 0, 0, 0.05)'
                  }}>
                    <div style={{ fontWeight: '600', color: '#333', marginBottom: '6px', fontSize: '14px' }}>📦 {file.repository}</div>
                    <div style={{ color: '#f5576c', fontFamily: 'monospace', fontSize: '13px', fontWeight: '500' }}>
                      {file.path}
                    </div>
                  </div>
                ))}
              </div>

              {/* Deletion Mode Selection */}
              <div style={{ 
                marginBottom: '32px',
                padding: '20px',
                background: 'linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%)',
                borderRadius: '16px',
                border: 'none'
              }}>
                <label style={{ fontWeight: '700', marginBottom: '16px', display: 'block', fontSize: '16px', color: '#333' }}>
                  Choose removal method:
                </label>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  <label style={{ 
                    display: 'flex', 
                    alignItems: 'center', 
                    cursor: 'pointer',
                    fontSize: '14px',
                    padding: '16px 20px',
                    background: deletionMode === 'direct' ? 'white' : 'rgba(255, 255, 255, 0.5)',
                    borderRadius: '12px',
                    border: deletionMode === 'direct' ? '3px solid #f5576c' : 'none',
                    transition: 'all 0.3s ease',
                    boxShadow: deletionMode === 'direct' ? '0 4px 12px rgba(245, 87, 108, 0.3)' : '0 2px 8px rgba(0, 0, 0, 0.05)'
                  }}>
                    <input
                      type="radio"
                      name="deletionMode"
                      value="direct"
                      checked={deletionMode === 'direct'}
                      onChange={() => setDeletionMode('direct')}
                      style={{ 
                        marginRight: '14px', 
                        cursor: 'pointer',
                        width: '20px',
                        height: '20px',
                        accentColor: '#f5576c'
                      }}
                    />
                    <div>
                      <div style={{ fontWeight: '700', fontSize: '15px', color: '#333' }}>🗑️ Direct Delete</div>
                      <div style={{ fontSize: '13px', color: '#666', marginTop: '6px', lineHeight: '1.4' }}>
                        Files will be permanently deleted immediately
                      </div>
                    </div>
                  </label>
                  <label style={{ 
                    display: 'flex', 
                    alignItems: 'center', 
                    cursor: 'pointer',
                    fontSize: '14px',
                    padding: '16px 20px',
                    background: deletionMode === 'pr' ? 'white' : 'rgba(255, 255, 255, 0.5)',
                    borderRadius: '12px',
                    border: deletionMode === 'pr' ? '3px solid #667eea' : 'none',
                    transition: 'all 0.3s ease',
                    boxShadow: deletionMode === 'pr' ? '0 4px 12px rgba(102, 126, 234, 0.3)' : '0 2px 8px rgba(0, 0, 0, 0.05)'
                  }}>
                    <input
                      type="radio"
                      name="deletionMode"
                      value="pr"
                      checked={deletionMode === 'pr'}
                      onChange={() => setDeletionMode('pr')}
                      style={{ 
                        marginRight: '14px', 
                        cursor: 'pointer',
                        width: '20px',
                        height: '20px',
                        accentColor: '#667eea'
                      }}
                    />
                    <div>
                      <div style={{ fontWeight: '700', fontSize: '15px', color: '#333' }}>📝 Create Pull Request</div>
                      <div style={{ fontSize: '13px', color: '#666', marginTop: '6px', lineHeight: '1.4' }}>
                        Create PRs for review before deletion
                      </div>
                    </div>
                  </label>
                </div>
              </div>

              {/* Action Buttons */}
              <div style={{ display: 'flex', gap: '16px', justifyContent: 'flex-end', marginTop: '32px' }}>
                <button
                  onClick={() => setShowConfirmModal(false)}
                  disabled={deleting}
                  style={{
                    padding: '14px 32px',
                    background: '#f5f5f5',
                    color: '#333',
                    border: 'none',
                    borderRadius: '12px',
                    cursor: deleting ? 'not-allowed' : 'pointer',
                    fontWeight: '600',
                    fontSize: '15px',
                    opacity: deleting ? 0.6 : 1,
                    transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
                    boxShadow: '0 2px 8px rgba(0, 0, 0, 0.05)'
                  }}
                  onMouseOver={(e) => {
                    if (!deleting) {
                      e.target.style.background = '#e8e8e8';
                      e.target.style.transform = 'translateY(-2px)';
                      e.target.style.boxShadow = '0 4px 12px rgba(0, 0, 0, 0.1)';
                    }
                  }}
                  onMouseOut={(e) => {
                    if (!deleting) {
                      e.target.style.background = '#f5f5f5';
                      e.target.style.transform = 'none';
                      e.target.style.boxShadow = '0 2px 8px rgba(0, 0, 0, 0.05)';
                    }
                  }}
                >
                  Cancel
                </button>
                <button
                  onClick={deleteSelectedFiles}
                  disabled={deleting}
                  style={{
                    padding: '14px 32px',
                    background: deleting ? '#ddd' : (deletionMode === 'pr' ? 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' : 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)'),
                    color: 'white',
                    border: 'none',
                    borderRadius: '12px',
                    cursor: deleting ? 'not-allowed' : 'pointer',
                    fontWeight: '700',
                    fontSize: '15px',
                    transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
                    boxShadow: deleting ? 'none' : (deletionMode === 'pr' ? '0 4px 12px rgba(102, 126, 234, 0.4)' : '0 4px 12px rgba(245, 87, 108, 0.4)')
                  }}
                  onMouseOver={(e) => {
                    if (!deleting) {
                      e.target.style.transform = 'translateY(-2px)';
                      e.target.style.boxShadow = deletionMode === 'pr' ? '0 6px 20px rgba(102, 126, 234, 0.5)' : '0 6px 20px rgba(245, 87, 108, 0.5)';
                    }
                  }}
                  onMouseOut={(e) => {
                    if (!deleting) {
                      e.target.style.transform = 'none';
                      e.target.style.boxShadow = deletionMode === 'pr' ? '0 4px 12px rgba(102, 126, 234, 0.4)' : '0 4px 12px rgba(245, 87, 108, 0.4)';
                    }
                  }}
                >
                  {deleting ? 'Processing...' : (deletionMode === 'pr' ? 'Create PRs' : 'Delete Files')}
                </button>
              </div>
            </div>
        </div>
      )}
    </div>
  );
};

export default LegacyConfigCleanup;
