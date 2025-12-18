import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000/api';

export const templatesAPI = {
  // Get all templates
  getAllTemplates: async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/templates`);
      return response.data;
    } catch (error) {
      throw new Error(`Failed to fetch templates: ${error.response?.data?.detail || error.message}`);
    }
  },

  // Get a template by ID
  getTemplate: async (templateId) => {
    try {
      const response = await axios.get(`${API_BASE_URL}/templates/${templateId}`);
      return response.data;
    } catch (error) {
      if (error.response?.status === 404) {
        throw new Error(`Template not found`);
      }
      throw new Error(`Failed to fetch template: ${error.response?.data?.detail || error.message}`);
    }
  },

  // Search templates
  searchTemplates: async (query) => {
    try {
      const response = await axios.get(`${API_BASE_URL}/templates/search/${encodeURIComponent(query)}`);
      return response.data;
    } catch (error) {
      throw new Error(`Failed to search templates: ${error.response?.data?.detail || error.message}`);
    }
  },

  // Create a new template
  createTemplate: async (templateData) => {
    try {
      const response = await axios.post(`${API_BASE_URL}/templates`, templateData);
      return response.data;
    } catch (error) {
      if (error.response?.status === 400) {
        throw new Error(error.response.data.detail);
      }
      throw new Error(`Failed to create template: ${error.response?.data?.detail || error.message}`);
    }
  },

  // Update a template
  updateTemplate: async (templateId, templateData) => {
    try {
      const response = await axios.put(`${API_BASE_URL}/templates/${templateId}`, templateData);
      return response.data;
    } catch (error) {
      if (error.response?.status === 404) {
        throw new Error(`Template not found`);
      }
      if (error.response?.status === 400) {
        throw new Error(error.response.data.detail);
      }
      throw new Error(`Failed to update template: ${error.response?.data?.detail || error.message}`);
    }
  },

  // Delete a template
  deleteTemplate: async (templateId) => {
    try {
      const response = await axios.delete(`${API_BASE_URL}/templates/${templateId}`);
      return response.data;
    } catch (error) {
      if (error.response?.status === 404) {
        throw new Error(`Template not found`);
      }
      throw new Error(`Failed to delete template: ${error.response?.data?.detail || error.message}`);
    }
  },

  // Apply a template to a repository
  applyTemplate: async (templateName, repository, method = 'pull_request', branch = 'main') => {
    try {
      const requestData = {
        template_name: templateName,
        repository: repository,
        method: method, // 'direct' or 'pull_request'
        branch: branch,
        pr_title: `Add ${templateName} workflow`,
        pr_body: `This PR adds the ${templateName} workflow template for Black Duck security scanning.`
      };
      
      const response = await axios.post(`${API_BASE_URL}/templates/apply`, requestData);
      return response.data;
    } catch (error) {
      if (error.response?.status === 404) {
        throw new Error(error.response.data.detail || 'Template or GitHub token not found');
      }
      if (error.response?.status === 400) {
        throw new Error(error.response.data.detail || 'Invalid request');
      }
      throw new Error(`Failed to apply template: ${error.response?.data?.detail || error.message}`);
    }
  }
};
