import React, { useState, useEffect } from 'react';
import { secretsAPI } from './secretsAPI';

const SecretsManager = ({ onSecretsUpdated }) => {
  const [secrets, setSecrets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [newSecret, setNewSecret] = useState({ name: '', value: '', description: '' });
  const [editingSecret, setEditingSecret] = useState(null);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [decryptedSecrets, setDecryptedSecrets] = useState({}); // Store decrypted values
  const [showPassword, setShowPassword] = useState({}); // Track which passwords are visible

  useEffect(() => {
    fetchSecrets();
  }, []);

  const fetchSecrets = async () => {
    try {
      setLoading(true);
      const data = await secretsAPI.getSecrets();
      setSecrets(data);
      setError('');
    } catch (err) {
      setError(err.message);
      console.error('Error fetching secrets:', err);
    } finally {
      setLoading(false);
    }
  };

  const createSecret = async (e) => {
    e.preventDefault();
    if (!newSecret.name.trim() || !newSecret.value.trim()) return;

    try {
      await secretsAPI.createSecret(newSecret);
      setNewSecret({ name: '', value: '', description: '' });
      setShowCreateForm(false);
      await fetchSecrets();
      setError('');
      // Notify parent component that secrets were updated
      if (onSecretsUpdated) {
        onSecretsUpdated();
      }
    } catch (err) {
      setError(err.message);
      console.error('Error creating secret:', err);
    }
  };

  const updateSecret = async (id, updatedSecret) => {
    try {
      await secretsAPI.updateSecret(id, updatedSecret);
      setEditingSecret(null);
      await fetchSecrets();
      setError('');
      // Notify parent component that secrets were updated
      if (onSecretsUpdated) {
        onSecretsUpdated();
      }
    } catch (err) {
      setError(err.message);
      console.error('Error updating secret:', err);
    }
  };

  const deleteSecret = async (id, secretName) => {
    // Check if this is a protected secret
    if (secretName === 'GITHUB_TOKEN') {
      setError(`Cannot delete required secret: ${secretName}. This secret is required for the application to function.`);
      return;
    }

    if (!window.confirm('Are you sure you want to delete this secret? This action cannot be undone.')) {
      return;
    }

    try {
      await secretsAPI.deleteSecret(id);
      await fetchSecrets();
      // Clear any decrypted values for this secret
      setDecryptedSecrets(prev => {
        const updated = { ...prev };
        delete updated[id];
        return updated;
      });
      setError('');
    } catch (err) {
      setError(err.message);
      console.error('Error deleting secret:', err);
    }
  };

  const toggleDecryption = async (id) => {
    if (decryptedSecrets[id]) {
      // Hide the secret
      setDecryptedSecrets(prev => {
        const updated = { ...prev };
        delete updated[id];
        return updated;
      });
      setShowPassword(prev => ({ ...prev, [id]: false }));
    } else {
      // Decrypt and show the secret
      try {
        const decrypted = await secretsAPI.getDecryptedSecret(id);
        setDecryptedSecrets(prev => ({ ...prev, [id]: decrypted.value }));
        setShowPassword(prev => ({ ...prev, [id]: true }));
        setError('');
      } catch (err) {
        setError(err.message);
        console.error('Error decrypting secret:', err);
      }
    }
  };

  const startEdit = (secret) => {
    setEditingSecret({ ...secret });
  };

  const cancelEdit = () => {
    setEditingSecret(null);
  };

  const handleEditSubmit = (e) => {
    e.preventDefault();
    updateSecret(editingSecret.id, {
      name: editingSecret.name,
      value: editingSecret.value,
      description: editingSecret.description
    });
  };

  const copyToClipboard = async (text) => {
    try {
      await navigator.clipboard.writeText(text);
      // You could add a toast notification here
      console.log('Copied to clipboard');
    } catch (err) {
      console.error('Failed to copy to clipboard:', err);
    }
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleString();
  };

  const isRequiredSecret = (secretName) => {
    return secretName === 'GITHUB_TOKEN';
  };

  const getRequiredSecrets = () => {
    const required = ['GITHUB_TOKEN'];
    const existing = secrets.map(s => s.name);
    return required.filter(name => !existing.includes(name));
  };

  const missingSecrets = getRequiredSecrets();

  return (
    <div className="secrets-manager">
      <div className="secrets-header">
        <h1>🔐 Secrets Manager</h1>
        <p>Securely store and manage encrypted secrets</p>
        <button 
          onClick={() => setShowCreateForm(!showCreateForm)} 
          className="add-secret-btn"
        >
          {showCreateForm ? 'Cancel' : '+ Add New Secret'}
        </button>
      </div>

      {error && <div className="error">{error}</div>}

      {/* Missing Required Secrets Warning */}
      {missingSecrets.length > 0 && (
        <div className="missing-secrets-warning">
          <h3>⚠️ Required Configuration Missing</h3>
          <p>The following required secrets are not configured:</p>
          <ul>
            {missingSecrets.map(secret => (
              <li key={secret}>
                <strong>{secret}</strong>
                {secret === 'GITHUB_TOKEN' && ' - Your GitHub Personal Access Token'}
              </li>
            ))}
          </ul>
          <p className="warning-note">
            <strong>Action Required:</strong> Click "+ Add New Secret" above to add these required secrets.
          </p>
        </div>
      )}

      {/* GitHub Configuration Info */}
      <div className="config-info">
        <h3>⚙️ Required Secrets</h3>
        <div className="config-section">
          <h4>GITHUB_TOKEN</h4>
          <p>Your GitHub Personal Access Token for authentication:</p>
          <ol>
            <li>Go to <a href="https://github.com/settings/tokens" target="_blank" rel="noopener noreferrer">GitHub Settings → Tokens</a></li>
            <li>Generate a new token with <code>repo</code> and <code>read:org</code> scopes</li>
            <li>Create a secret named <strong>GITHUB_TOKEN</strong> with your token as the value</li>
          </ol>
          
          <h4 style={{marginTop: '20px'}}>SSO Authorization for Organizations</h4>
          <div className="sso-notice">
            <p><strong>🔐 If your organization requires SAML SSO:</strong></p>
            <ol>
              <li>Go to <a href="https://github.com/settings/tokens" target="_blank" rel="noopener noreferrer">GitHub Settings → Personal Access Tokens</a></li>
              <li>Find your token in the list</li>
              <li>Click <strong>"Configure SSO"</strong> next to your token</li>
              <li>Click <strong>"Authorize"</strong> for each organization that requires SSO</li>
              <li>Complete the SSO authentication flow if prompted</li>
            </ol>
            <p className="sso-warning">
              <strong>Important:</strong> Without SSO authorization, you'll get "Resource protected by organization SAML enforcement" errors when accessing organization resources.
            </p>
          </div>
          
          <h4 style={{marginTop: '20px'}}>GitHub API URL (Environment Variable)</h4>
          <p>The GitHub API URL is configured via environment variable, not as a secret:</p>
          <ul>
            <li><strong>For GitHub.com:</strong> No configuration needed (uses <code>https://api.github.com</code> by default)</li>
            <li><strong>For GitHub Enterprise:</strong> Set <code>GITHUB_API_URL</code> environment variable before starting the backend:
              <br/><code>$env:GITHUB_API_URL="https://your-enterprise.com/api/v3"</code> (Windows)
              <br/><code>export GITHUB_API_URL="https://your-enterprise.com/api/v3"</code> (Linux/Mac)
            </li>
          </ul>
          <p className="config-note">
            <strong>Note:</strong> GITHUB_TOKEN is the only required secret for the application to function.
          </p>
        </div>
      </div>

      {showCreateForm && (
        <div className="secret-form-container">
          <h2>Create New Secret</h2>
          <form onSubmit={createSecret} className="secret-form">
            <input
              type="text"
              placeholder="Secret name (unique)"
              value={newSecret.name}
              onChange={(e) => setNewSecret({ ...newSecret, name: e.target.value })}
              required
              maxLength="255"
            />
            <input
              type="password"
              placeholder="Secret value"
              value={newSecret.value}
              onChange={(e) => setNewSecret({ ...newSecret, value: e.target.value })}
              required
            />
            <textarea
              placeholder="Description (optional)"
              value={newSecret.description}
              onChange={(e) => setNewSecret({ ...newSecret, description: e.target.value })}
              rows="3"
            />
            <div className="form-actions">
              <button type="submit" className="save-btn">Create Secret</button>
              <button type="button" onClick={() => setShowCreateForm(false)} className="cancel-btn">
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      <div className="secrets-section">
        <h2>Stored Secrets ({secrets.length})</h2>
        {loading ? (
          <div className="loading">Loading secrets...</div>
        ) : secrets.length === 0 ? (
          <div className="no-secrets">
            <p>No secrets found. Create your first secret to get started!</p>
          </div>
        ) : (
          <div className="secrets-grid">
            {secrets.map(secret => (
              <div key={secret.id} className="secret-card">
                {editingSecret && editingSecret.id === secret.id ? (
                  <form onSubmit={handleEditSubmit} className="edit-form">
                    <input
                      type="text"
                      value={editingSecret.name}
                      onChange={(e) => setEditingSecret({ ...editingSecret, name: e.target.value })}
                      required
                      maxLength="255"
                    />
                    <input
                      type="password"
                      placeholder="New value (leave empty to keep current)"
                      value={editingSecret.value || ''}
                      onChange={(e) => setEditingSecret({ ...editingSecret, value: e.target.value })}
                    />
                    <textarea
                      value={editingSecret.description || ''}
                      onChange={(e) => setEditingSecret({ ...editingSecret, description: e.target.value })}
                      rows="3"
                      placeholder="Description"
                    />
                    <div className="form-actions">
                      <button type="submit" className="save-btn">Save</button>
                      <button type="button" onClick={cancelEdit} className="cancel-btn">Cancel</button>
                    </div>
                  </form>
                ) : (
                  <>
                    <div className="secret-header">
                      <div className="secret-name-group">
                        <h3>{secret.name}</h3>
                        {isRequiredSecret(secret.name) && (
                          <span className="required-badge">Required</span>
                        )}
                      </div>
                      <span className="secret-id">ID: {secret.id}</span>
                    </div>
                    
                    {secret.description && (
                      <p className="secret-description">{secret.description}</p>
                    )}

                    <div className="secret-value">
                      <label>Secret Value:</label>
                      <div className="value-display">
                        {showPassword[secret.id] ? (
                          <span className="decrypted-value">
                            {decryptedSecrets[secret.id]}
                          </span>
                        ) : (
                          <span className="encrypted-placeholder">••••••••••••</span>
                        )}
                        <div className="value-actions">
                          <button 
                            onClick={() => toggleDecryption(secret.id)}
                            className="toggle-btn"
                            title={showPassword[secret.id] ? 'Hide value' : 'Show value'}
                          >
                            {showPassword[secret.id] ? '🙈' : '👁️'}
                          </button>
                          {showPassword[secret.id] && (
                            <button 
                              onClick={() => copyToClipboard(decryptedSecrets[secret.id])}
                              className="copy-btn"
                              title="Copy to clipboard"
                            >
                              📋
                            </button>
                          )}
                        </div>
                      </div>
                    </div>

                    <div className="secret-metadata">
                      <small>Created: {formatDate(secret.created_at)}</small>
                      {secret.updated_at !== secret.created_at && (
                        <small>Updated: {formatDate(secret.updated_at)}</small>
                      )}
                    </div>

                    <div className="secret-actions">
                      <button onClick={() => startEdit(secret)} className="edit-btn">
                        ✏️ Edit
                      </button>
                      <button 
                        onClick={() => deleteSecret(secret.id, secret.name)} 
                        className="delete-btn"
                        disabled={isRequiredSecret(secret.name)}
                        title={isRequiredSecret(secret.name) ? 'This required secret cannot be deleted' : 'Delete secret'}
                      >
                        🗑️ Delete
                      </button>
                    </div>
                  </>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default SecretsManager;