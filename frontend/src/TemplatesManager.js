import React, { useState, useEffect } from 'react';
import { templatesAPI } from './templatesAPI';

const TemplatesManager = () => {
  const [templates, setTemplates] = useState([]);
  const [filteredTemplates, setFilteredTemplates] = useState([]);
  const [existingCategories, setExistingCategories] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedTemplate, setSelectedTemplate] = useState(null);
  const [isEditing, setIsEditing] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [successMessage, setSuccessMessage] = useState('');
  
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    content: '',
    keywords: '',
    template_type: 'workflow',
    category: '',
    meta_data: {
      compatible_languages: [],
      tools: [],
      secrets: [],
      variables: [],
      features: [],
      required_custom_attributes: []
    }
  });

  useEffect(() => {
    loadTemplates();
  }, []);

  useEffect(() => {
    if (searchQuery.trim() === '') {
      setFilteredTemplates(templates);
    } else {
      const query = searchQuery.toLowerCase();
      const filtered = templates.filter(template => 
        template.name.toLowerCase().includes(query) ||
        (template.description && template.description.toLowerCase().includes(query))
      );
      setFilteredTemplates(filtered);
    }
  }, [searchQuery, templates]);

  const loadTemplates = async () => {
    try {
      setLoading(true);
      setError('');
      const data = await templatesAPI.getAllTemplates();
      setTemplates(data);
      setFilteredTemplates(data);
      
      // Extract unique categories from existing templates
      const categories = [...new Set(
        data
          .filter(t => t.category && t.category.trim() !== '')
          .map(t => t.category)
      )].sort();
      setExistingCategories(categories);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateNew = () => {
    setIsCreating(true);
    setIsEditing(false);
    setSelectedTemplate(null);
    setFormData({ 
      name: '', 
      description: '', 
      content: '', 
      keywords: '',
      template_type: 'workflow',
      category: '',
      meta_data: {
        compatible_languages: [],
        tools: [],
        secrets: [],
        variables: [],
        features: [],
        required_custom_attributes: []
      }
    });
    setError('');
    setSuccessMessage('');
  };

  const handleEdit = (template) => {
    setIsEditing(true);
    setIsCreating(false);
    setSelectedTemplate(template);
    setFormData({
      name: template.name,
      description: template.description || '',
      content: template.content,
      keywords: template.keywords || '',
      template_type: template.template_type || 'workflow',
      category: template.category || '',
      meta_data: template.meta_data || {
        compatible_languages: [],
        tools: [],
        secrets: [],
        variables: [],
        features: [],
        required_custom_attributes: []
      }
    });
    setError('');
    setSuccessMessage('');
  };

  const handleView = (template) => {
    setSelectedTemplate(template);
    setIsEditing(false);
    setIsCreating(false);
    setFormData({
      name: template.name,
      description: template.description || '',
      content: template.content,
      keywords: template.keywords || '',
      template_type: template.template_type || 'workflow',
      category: template.category || '',
      meta_data: template.meta_data || {
        compatible_languages: [],
        tools: [],
        secrets: [],
        variables: [],
        features: [],
        required_custom_attributes: []
      }
    });
  };

  const handleCancel = () => {
    setIsCreating(false);
    setIsEditing(false);
    setSelectedTemplate(null);
    setFormData({ 
      name: '', 
      description: '', 
      content: '', 
      keywords: '',
      template_type: 'workflow',
      category: '',
      meta_data: {
        compatible_languages: [],
        tools: [],
        secrets: [],
        variables: [],
        features: [],
        required_custom_attributes: []
      }
    });
    setError('');
    setSuccessMessage('');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccessMessage('');

    if (!formData.name.trim()) {
      setError('Template name is required');
      return;
    }

    if (!formData.content.trim()) {
      setError('Template content is required');
      return;
    }

    try {
      if (isCreating) {
        await templatesAPI.createTemplate(formData);
        setSuccessMessage('Template created successfully!');
      } else if (isEditing) {
        await templatesAPI.updateTemplate(selectedTemplate.id, formData);
        setSuccessMessage('Template updated successfully!');
      }
      
      await loadTemplates();
      setTimeout(() => {
        handleCancel();
      }, 1500);
    } catch (err) {
      setError(err.message);
    }
  };

  const handleDelete = async (templateId, templateName) => {
    if (!window.confirm(`Are you sure you want to delete template "${templateName}"?`)) {
      return;
    }

    try {
      setError('');
      await templatesAPI.deleteTemplate(templateId);
      setSuccessMessage('Template deleted successfully!');
      await loadTemplates();
      if (selectedTemplate?.id === templateId) {
        handleCancel();
      }
      setTimeout(() => setSuccessMessage(''), 3000);
    } catch (err) {
      setError(err.message);
    }
  };

  const handleCopyToClipboard = (content) => {
    navigator.clipboard.writeText(content);
    setSuccessMessage('Template copied to clipboard!');
    setTimeout(() => setSuccessMessage(''), 2000);
  };

  const handleTextareaKeyDown = (e) => {
    // Handle Tab key to insert a tab character instead of changing focus
    if (e.key === 'Tab') {
      e.preventDefault();
      const target = e.target;
      const start = target.selectionStart;
      const end = target.selectionEnd;
      const value = target.value;
      
      // Insert tab character at cursor position
      const newValue = value.substring(0, start) + '\t' + value.substring(end);
      setFormData({ ...formData, content: newValue });
      
      // Set cursor position after the inserted tab
      setTimeout(() => {
        target.selectionStart = target.selectionEnd = start + 1;
      }, 0);
    }
  };

  return (
    <div className="templates-manager">
      <div className="templates-header">
        <h2>📄 Template Manager</h2>
        <p className="subtitle">Create and manage reusable text templates</p>
      </div>

      {error && (
        <div className="error-message">
          ⚠️ {error}
        </div>
      )}

      {successMessage && (
        <div className="success-message">
          ✅ {successMessage}
        </div>
      )}

      <div className="templates-container">
        {/* Left Panel - Templates List */}
        <div className="templates-list-panel">
          <div className="templates-controls">
            <input
              type="text"
              placeholder="🔍 Search templates..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="search-input"
            />
            <button onClick={handleCreateNew} className="btn-create">
              ➕ New Template
            </button>
          </div>

          {loading ? (
            <div className="loading">Loading templates...</div>
          ) : (
            <div className="templates-list">
              {filteredTemplates.length === 0 ? (
                <div className="no-templates">
                  {searchQuery ? 'No templates found matching your search.' : 'No templates yet. Create your first template!'}
                </div>
              ) : (
                <>
                  {/* Group templates by type */}
                  {(() => {
                    const stepTemplates = filteredTemplates.filter(t => t.template_type === 'step');
                    const jobTemplates = filteredTemplates.filter(t => t.template_type === 'job');
                    const workflowTemplates = filteredTemplates.filter(t => t.template_type === 'workflow');
                    const otherTemplates = filteredTemplates.filter(t => !t.template_type || !['step', 'job', 'workflow'].includes(t.template_type));

                    const renderTemplateGroup = (templates, icon, title, color) => {
                      if (templates.length === 0) return null;
                      
                      return (
                        <div className="template-category-group" style={{ marginBottom: '20px' }}>
                          <div style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '8px',
                            padding: '8px 12px',
                            background: `linear-gradient(135deg, ${color}15 0%, ${color}08 100%)`,
                            borderLeft: `3px solid ${color}`,
                            marginBottom: '10px',
                            borderRadius: '4px'
                          }}>
                            <span style={{ fontSize: '14px' }}>{icon}</span>
                            <span style={{
                              fontSize: '13px',
                              fontWeight: '700',
                              color: color,
                              textTransform: 'uppercase',
                              letterSpacing: '0.5px'
                            }}>{title}</span>
                            <span style={{
                              background: color,
                              color: 'white',
                              padding: '2px 8px',
                              borderRadius: '10px',
                              fontSize: '11px',
                              fontWeight: '600'
                            }}>{templates.length}</span>
                          </div>
                          {templates.map(template => (
                            <div
                              key={template.id}
                              className={`template-item ${selectedTemplate?.id === template.id ? 'active' : ''}`}
                              onClick={() => handleView(template)}
                              style={{
                                borderLeft: `3px solid ${color}`,
                                marginBottom: '8px'
                              }}
                            >
                              <div className="template-item-header">
                                <h4>{template.name}</h4>
                                <div className="template-actions">
                                  <button
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      handleEdit(template);
                                    }}
                                    className="btn-icon"
                                    title="Edit"
                                  >
                                    ✏️
                                  </button>
                                  <button
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      handleDelete(template.id, template.name);
                                    }}
                                    className="btn-icon btn-delete"
                                    title="Delete"
                                  >
                                    🗑️
                                  </button>
                                </div>
                              </div>
                              {template.category && (
                                <div style={{ marginBottom: '4px' }}>
                                  <span style={{
                                    background: color,
                                    color: 'white',
                                    padding: '2px 8px',
                                    borderRadius: '12px',
                                    fontSize: '10px',
                                    fontWeight: '600',
                                    letterSpacing: '0.5px'
                                  }}>
                                    {template.category.toUpperCase()}
                                  </span>
                                </div>
                              )}
                              {template.description && (
                                <p className="template-description">{template.description}</p>
                              )}
                              <div className="template-meta">
                                <span className="template-date">
                                  Updated: {new Date(template.updated_at).toLocaleDateString()}
                                </span>
                              </div>
                            </div>
                          ))}
                        </div>
                      );
                    };

                    return (
                      <>
                        {renderTemplateGroup(stepTemplates, '🔧', 'Job Steps', '#4caf50')}
                        {renderTemplateGroup(jobTemplates, '⚙️', 'Workflow Jobs', '#ff9800')}
                        {renderTemplateGroup(workflowTemplates, '📄', 'Complete Workflows', '#2196f3')}
                        {renderTemplateGroup(otherTemplates, '📝', 'Other Templates', '#9e9e9e')}
                      </>
                    );
                  })()}
                </>
              )}
            </div>
          )}
        </div>

        {/* Right Panel - Template Details/Editor */}
        <div className="template-detail-panel">
          {isCreating || isEditing ? (
            <div className="template-editor">
              <h3>{isCreating ? '➕ Create New Template' : '✏️ Edit Template'}</h3>
              <form onSubmit={handleSubmit}>
                <div className="form-group">
                  <label htmlFor="name">Template Name *</label>
                  <input
                    type="text"
                    id="name"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    placeholder="Enter template name"
                    required
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="description">Description</label>
                  <input
                    type="text"
                    id="description"
                    value={formData.description}
                    onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                    placeholder="Enter template description (optional)"
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="template_type">Template Type *</label>
                  <select
                    id="template_type"
                    value={formData.template_type}
                    onChange={(e) => setFormData({ ...formData, template_type: e.target.value })}
                    required
                    style={{
                      width: '100%',
                      padding: '8px',
                      borderRadius: '4px',
                      border: '1px solid #ddd',
                      fontSize: '14px'
                    }}
                  >
                    <option value="workflow">📄 Workflow - Complete workflow file</option>
                    <option value="job">⚙️ Job - Job to add to existing workflow</option>
                    <option value="step">🔧 Step - Step to insert into existing job</option>
                  </select>
                  <small className="form-help">
                    💡 Workflow templates create new files, Job fragments add jobs to workflows, Step fragments insert into existing jobs.
                  </small>
                </div>

                <div className="form-group">
                  <label htmlFor="category">Category</label>
                  <input
                    type="text"
                    id="category"
                    value={formData.category}
                    onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                    placeholder="e.g., polaris, coverity, docker, kubernetes"
                    list="category-suggestions"
                  />
                  <datalist id="category-suggestions">
                    {existingCategories.map((cat, idx) => (
                      <option key={idx} value={cat}>{cat}</option>
                    ))}
                  </datalist>
                  <small className="form-help">
                    💡 Category helps organize templates by tool or purpose. Select existing category or type a new one.
                    {existingCategories.length > 0 && (
                      <span style={{ display: 'block', marginTop: '4px', color: '#666' }}>
                        Existing: {existingCategories.join(', ')}
                      </span>
                    )}
                  </small>
                </div>

                <div className="form-group">
                  <label htmlFor="keywords">Keywords (Multiple allowed)</label>
                  <input
                    type="text"
                    id="keywords"
                    value={formData.keywords}
                    onChange={(e) => setFormData({ ...formData, keywords: e.target.value })}
                    placeholder="Enter keywords separated by commas (e.g., workflow, ci/cd, deployment, docker, kubernetes)"
                  />
                  <small className="form-help">
                    💡 Add multiple keywords separated by commas. These will be used to match workflow files during onboarding.
                  </small>
                  {formData.keywords && (
                    <div className="keywords-preview">
                      <strong>Preview:</strong>
                      {formData.keywords.split(',').map((keyword, index) => (
                        <span key={index} className="keyword-tag">{keyword.trim()}</span>
                      ))}
                    </div>
                  )}
                </div>

                {/* Metadata Section */}
                <div style={{
                  background: '#f8f9fa',
                  padding: '15px',
                  borderRadius: '6px',
                  marginBottom: '15px',
                  border: '1px solid #dee2e6'
                }}>
                  <h4 style={{ marginTop: 0, marginBottom: '12px', fontSize: '14px', fontWeight: '600' }}>
                    📋 Metadata (Optional)
                  </h4>
                  
                  <div className="form-group">
                    <label htmlFor="compatible_languages">Compatible Languages</label>
                    <input
                      type="text"
                      id="compatible_languages"
                      value={formData.meta_data?.compatible_languages?.join(', ') || ''}
                      onChange={(e) => {
                        const languages = e.target.value ? e.target.value.split(',').map(s => s.trim()).filter(s => s) : [];
                        setFormData({
                          ...formData,
                          meta_data: {
                            ...formData.meta_data,
                            compatible_languages: languages
                          }
                        });
                      }}
                      placeholder="e.g., Java, Python, JavaScript, C, C++"
                    />
                    <small className="form-help">
                      💡 Comma-separated list of programming languages this template supports
                    </small>
                  </div>

                  <div className="form-group">
                    <label htmlFor="tools">Tools</label>
                    <input
                      type="text"
                      id="tools"
                      value={formData.meta_data?.tools?.join(', ') || ''}
                      onChange={(e) => {
                        const tools = e.target.value ? e.target.value.split(',').map(s => s.trim()).filter(s => s) : [];
                        setFormData({
                          ...formData,
                          meta_data: {
                            ...formData.meta_data,
                            tools: tools
                          }
                        });
                      }}
                      placeholder="e.g., polaris, coverity, docker"
                    />
                    <small className="form-help">
                      💡 Comma-separated list of tools/technologies used in this template
                    </small>
                  </div>

                  <div className="form-group">
                    <label htmlFor="secrets">Required Secrets</label>
                    <input
                      type="text"
                      id="secrets"
                      value={formData.meta_data?.secrets?.join(', ') || ''}
                      onChange={(e) => {
                        const secrets = e.target.value ? e.target.value.split(',').map(s => s.trim()).filter(s => s) : [];
                        setFormData({
                          ...formData,
                          meta_data: {
                            ...formData.meta_data,
                            secrets: secrets
                          }
                        });
                      }}
                      placeholder="e.g., POLARIS_ACCESS_TOKEN, GITHUB_TOKEN"
                    />
                    <small className="form-help">
                      💡 Comma-separated list of GitHub secrets required by this template
                    </small>
                  </div>

                  <div className="form-group">
                    <label htmlFor="variables">Required Variables</label>
                    <input
                      type="text"
                      id="variables"
                      value={formData.meta_data?.variables?.join(', ') || ''}
                      onChange={(e) => {
                        const variables = e.target.value ? e.target.value.split(',').map(s => s.trim()).filter(s => s) : [];
                        setFormData({
                          ...formData,
                          meta_data: {
                            ...formData.meta_data,
                            variables: variables
                          }
                        });
                      }}
                      placeholder="e.g., POLARIS_SERVER_URL, NODE_VERSION"
                    />
                    <small className="form-help">
                      💡 Comma-separated list of GitHub variables required by this template
                    </small>
                  </div>

                  <div className="form-group">
                    <label htmlFor="features">Features</label>
                    <input
                      type="text"
                      id="features"
                      value={formData.meta_data?.features?.join(', ') || ''}
                      onChange={(e) => {
                        const features = e.target.value ? e.target.value.split(',').map(s => s.trim()).filter(s => s) : [];
                        setFormData({
                          ...formData,
                          meta_data: {
                            ...formData.meta_data,
                            features: features
                          }
                        });
                      }}
                      placeholder="e.g., SAST, SCA, PR Optimization"
                    />
                    <small className="form-help">
                      💡 Comma-separated list of features provided by this template
                    </small>
                  </div>

                  <div className="form-group" style={{ marginBottom: 0 }}>
                    <label htmlFor="required_custom_attributes">Required Custom Attributes</label>
                    <input
                      type="text"
                      id="required_custom_attributes"
                      value={formData.meta_data?.required_custom_attributes?.join(', ') || ''}
                      onChange={(e) => {
                        const attributes = e.target.value ? e.target.value.split(',').map(s => s.trim()).filter(s => s) : [];
                        setFormData({
                          ...formData,
                          meta_data: {
                            ...formData.meta_data,
                            required_custom_attributes: attributes
                          }
                        });
                      }}
                      placeholder="e.g., team, environment, compliance-level"
                    />
                    <small className="form-help">
                      💡 Comma-separated list of GitHub custom repository attributes required by this template
                    </small>
                  </div>
                </div>

                <div className="form-group">
                  <label htmlFor="content">Template Content *</label>
                  <textarea
                    id="content"
                    value={formData.content}
                    onChange={(e) => setFormData({ ...formData, content: e.target.value })}
                    onKeyDown={handleTextareaKeyDown}
                    placeholder="Enter template content"
                    rows="15"
                    required
                  />
                </div>

                <div className="form-actions">
                  <button type="submit" className="btn-primary">
                    {isCreating ? '✅ Create Template' : '💾 Save Changes'}
                  </button>
                  <button type="button" onClick={handleCancel} className="btn-secondary">
                    ❌ Cancel
                  </button>
                </div>
              </form>
            </div>
          ) : selectedTemplate ? (
            <div className="template-viewer">
              <div className="template-viewer-header">
                <h3>{selectedTemplate.name}</h3>
                <div className="template-viewer-actions">
                  <button
                    onClick={() => handleCopyToClipboard(selectedTemplate.content)}
                    className="btn-copy"
                  >
                    📋 Copy
                  </button>
                  <button
                    onClick={() => handleEdit(selectedTemplate)}
                    className="btn-edit"
                  >
                    ✏️ Edit
                  </button>
                </div>
              </div>
              
              {/* Show template type and category */}
              {(selectedTemplate.template_type || selectedTemplate.category) && (
                <div style={{ 
                  display: 'flex', 
                  gap: '10px', 
                  marginBottom: '12px',
                  flexWrap: 'wrap'
                }}>
                  {selectedTemplate.template_type && (
                    <span style={{
                      background: selectedTemplate.template_type === 'step' ? '#4caf50' :
                                  selectedTemplate.template_type === 'job' ? '#ff9800' :
                                  selectedTemplate.template_type === 'workflow' ? '#2196f3' : '#9e9e9e',
                      color: 'white',
                      padding: '4px 12px',
                      borderRadius: '15px',
                      fontSize: '12px',
                      fontWeight: '600',
                      letterSpacing: '0.5px'
                    }}>
                      {selectedTemplate.template_type === 'step' ? '🔧 STEP' :
                       selectedTemplate.template_type === 'job' ? '⚙️ JOB' :
                       selectedTemplate.template_type === 'workflow' ? '📄 WORKFLOW' : 
                       selectedTemplate.template_type.toUpperCase()}
                    </span>
                  )}
                  {selectedTemplate.category && (
                    <span style={{
                      background: '#673ab7',
                      color: 'white',
                      padding: '4px 12px',
                      borderRadius: '15px',
                      fontSize: '12px',
                      fontWeight: '600',
                      letterSpacing: '0.5px'
                    }}>
                      {selectedTemplate.category.toUpperCase()}
                    </span>
                  )}
                </div>
              )}
              
              {selectedTemplate.description && (
                <p className="template-viewer-description">{selectedTemplate.description}</p>
              )}
              
              {selectedTemplate.keywords && (
                <div className="template-keywords">
                  {selectedTemplate.keywords.split(',').map((keyword, index) => (
                    <span key={index} className="keyword-tag">{keyword.trim()}</span>
                  ))}
                </div>
              )}
              
              {/* Show metadata if available */}
              {selectedTemplate.meta_data && (
                <div style={{
                  background: '#f5f5f5',
                  padding: '12px',
                  borderRadius: '6px',
                  marginBottom: '12px',
                  fontSize: '13px'
                }}>
                  <strong style={{ display: 'block', marginBottom: '8px' }}>📋 Metadata:</strong>
                  {selectedTemplate.meta_data.compatible_languages && (
                    <div style={{ marginBottom: '6px' }}>
                      <strong>Languages:</strong> {selectedTemplate.meta_data.compatible_languages.join(', ')}
                    </div>
                  )}
                  {selectedTemplate.meta_data.tools && (
                    <div style={{ marginBottom: '6px' }}>
                      <strong>Tools:</strong> {selectedTemplate.meta_data.tools.join(', ')}
                    </div>
                  )}
                  {selectedTemplate.meta_data.secrets && (
                    <div style={{ marginBottom: '6px' }}>
                      <strong>Required Secrets:</strong> {selectedTemplate.meta_data.secrets.join(', ')}
                    </div>
                  )}
                  {selectedTemplate.meta_data.variables && (
                    <div style={{ marginBottom: '6px' }}>
                      <strong>Required Variables:</strong> {selectedTemplate.meta_data.variables.join(', ')}
                    </div>
                  )}
                  {selectedTemplate.meta_data.required_custom_attributes && selectedTemplate.meta_data.required_custom_attributes.length > 0 && (
                    <div style={{ marginBottom: '6px' }}>
                      <strong>Required Custom Attributes:</strong> {selectedTemplate.meta_data.required_custom_attributes.join(', ')}
                    </div>
                  )}
                </div>
              )}
              
              <div className="template-viewer-meta">
                <span>Created: {new Date(selectedTemplate.created_at).toLocaleString()}</span>
                <span>Updated: {new Date(selectedTemplate.updated_at).toLocaleString()}</span>
              </div>

              <div className="template-content-viewer">
                <h4>Content:</h4>
                <pre>{selectedTemplate.content}</pre>
              </div>
            </div>
          ) : (
            <div className="template-placeholder">
              <div className="placeholder-icon">📄</div>
              <h3>No Template Selected</h3>
              <p>Select a template from the list to view its content, or create a new template.</p>
              <button onClick={handleCreateNew} className="btn-primary">
                ➕ Create New Template
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default TemplatesManager;
