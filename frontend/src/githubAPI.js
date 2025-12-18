import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000/api';

// Set timeout to 30 seconds for GitHub API calls (some operations like fetching workflow info can be slow)
axios.defaults.timeout = 30000;

export const githubAPI = {
  // Check if GITHUB_TOKEN exists and is valid
  checkTokenStatus: async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/github/token-status`);
      return response.data;
    } catch (error) {
      throw new Error(`Failed to check GitHub token status: ${error.response?.data?.detail || error.message}`);
    }
  },

  // Get GitHub token scopes
  getTokenScopes: async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/github/token-scopes`);
      return response.data;
    } catch (error) {
      throw new Error(`Failed to fetch token scopes: ${error.response?.data?.detail || error.message}`);
    }
  },

  // Get GitHub organizations for the authenticated user
  getOrganizations: async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/github/organizations`);
      return response.data;
    } catch (error) {
      if (error.response?.status === 404) {
        throw new Error('GITHUB_TOKEN secret not found. Please add it in Secrets Management.');
      } else if (error.response?.status === 401) {
        throw new Error('GITHUB_TOKEN is invalid. Please update it in Secrets Management.');
      }
      throw new Error(`Failed to fetch organizations: ${error.response?.data?.detail || error.message}`);
    }
  },

  // Get detailed information about a specific organization
  getOrganizationDetails: async (orgName) => {
    try {
      const response = await axios.get(`${API_BASE_URL}/github/organizations/${encodeURIComponent(orgName)}`);
      return response.data;
    } catch (error) {
      if (error.response?.status === 404) {
        throw new Error('GITHUB_TOKEN secret not found. Please add it in Secrets Management.');
      } else if (error.response?.status === 401) {
        throw new Error('GITHUB_TOKEN is invalid. Please update it in Secrets Management.');
      }
      throw new Error(`Failed to fetch organization details: ${error.response?.data?.detail || error.message}`);
    }
  },

  // Get GitHub user information
  getUserInfo: async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/github/user`);
      return response.data;
    } catch (error) {
      if (error.response?.status === 404) {
        throw new Error('GITHUB_TOKEN secret not found. Please add it in Secrets Management.');
      } else if (error.response?.status === 401) {
        throw new Error('GITHUB_TOKEN is invalid. Please update it in Secrets Management.');
      }
      throw new Error(`Failed to fetch user info: ${error.response?.data?.detail || error.message}`);
    }
  },

  // Get repositories for a specific organization (requires language parameter)
  getOrganizationRepositories: async (orgName, language) => {
    if (!language || language.trim() === '') {
      throw new Error('Language parameter is required. Use "all" to get repositories of all languages.');
    }
    
    try {
      const params = new URLSearchParams({ language });
      const url = `${API_BASE_URL}/github/organizations/${encodeURIComponent(orgName)}/repositories?${params.toString()}`;
      const response = await axios.get(url);
      return response.data;
    } catch (error) {
      if (error.response?.status === 400) {
        throw new Error('Language selection is required. Please select a programming language.');
      } else if (error.response?.status === 404) {
        throw new Error('GITHUB_TOKEN secret not found. Please add it in Secrets Management.');
      } else if (error.response?.status === 401) {
        throw new Error('GITHUB_TOKEN is invalid. Please update it in Secrets Management.');
      }
      throw new Error(`Failed to fetch repositories: ${error.response?.data?.detail || error.message}`);
    }
  },

  // Get available programming languages for an organization
  getOrganizationLanguages: async (orgName) => {
    try {
      const response = await axios.get(`${API_BASE_URL}/github/organizations/${encodeURIComponent(orgName)}/languages`);
      return response.data;
    } catch (error) {
      if (error.response?.status === 404) {
        throw new Error('GITHUB_TOKEN secret not found. Please add it in Secrets Management.');
      } else if (error.response?.status === 401) {
        throw new Error('GITHUB_TOKEN is invalid. Please update it in Secrets Management.');
      }
      throw new Error(`Failed to fetch languages: ${error.response?.data?.detail || error.message}`);
    }
  },

  // Get all user repositories (requires language parameter)
  getUserRepositories: async (language) => {
    if (!language || language.trim() === '') {
      throw new Error('Language parameter is required. Use "all" to get repositories of all languages.');
    }
    
    try {
      const params = new URLSearchParams({ language });
      const url = `${API_BASE_URL}/github/user/repositories?${params.toString()}`;
      const response = await axios.get(url);
      return response.data;
    } catch (error) {
      if (error.response?.status === 400) {
        throw new Error('Language selection is required. Please select a programming language.');
      } else if (error.response?.status === 404) {
        throw new Error('GITHUB_TOKEN secret not found. Please add it in Secrets Management.');
      } else if (error.response?.status === 401) {
        throw new Error('GITHUB_TOKEN is invalid. Please update it in Secrets Management.');
      }
      throw new Error(`Failed to fetch user repositories: ${error.response?.data?.detail || error.message}`);
    }
  },

  // Get available programming languages for all user repositories
  getUserLanguages: async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/github/user/languages`);
      return response.data;
    } catch (error) {
      if (error.response?.status === 404) {
        throw new Error('GITHUB_TOKEN secret not found. Please add it in Secrets Management.');
      } else if (error.response?.status === 401) {
        throw new Error('GITHUB_TOKEN is invalid. Please update it in Secrets Management.');
      }
      throw new Error(`Failed to fetch user languages: ${error.response?.data?.detail || error.message}`);
    }
  },

  // Generic function to get languages based on scope
  getLanguages: async (scope, organization) => {
    if (scope === 'organization') {
      if (!organization) {
        throw new Error('Organization is required when scope is "organization"');
      }
      return await githubAPI.getOrganizationLanguages(organization);
    } else if (scope === 'user') {
      return await githubAPI.getUserLanguages();
    } else {
      throw new Error('Invalid scope. Must be "organization" or "user"');
    }
  },

  // Generic function to get repositories based on scope
  getRepositories: async (scope, organization, language) => {
    if (scope === 'organization') {
      if (!organization) {
        throw new Error('Organization is required when scope is "organization"');
      }
      return await githubAPI.getOrganizationRepositories(organization, language);
    } else if (scope === 'user') {
      return await githubAPI.getUserRepositories(language);
    } else {
      throw new Error('Invalid scope. Must be "organization" or "user"');
    }
  },

  // Generic function to get repository details based on scope
  getRepositoryDetails: async (scope, repoName, organization) => {
    let owner;
    if (scope === 'organization') {
      if (!organization) {
        throw new Error('Organization is required when scope is "organization"');
      }
      owner = organization;
    } else if (scope === 'user') {
      // For user scope, we need to get the current user's login
      try {
        const userInfo = await githubAPI.getUserInfo();
        owner = userInfo.login;
      } catch (error) {
        throw new Error('Failed to get user info for repository details');
      }
    } else {
      throw new Error('Invalid scope. Must be "organization" or "user"');
    }
    
    try {
      const response = await axios.get(`${API_BASE_URL}/github/repositories/${encodeURIComponent(owner)}/${encodeURIComponent(repoName)}/details`);
      return response.data;
    } catch (error) {
      if (error.response?.status === 404) {
        throw new Error('GITHUB_TOKEN secret not found or repository not found. Please add it in Secrets Management.');
      } else if (error.response?.status === 401) {
        throw new Error('GITHUB_TOKEN is invalid. Please update it in Secrets Management.');
      }
      throw new Error(`Failed to fetch repository details: ${error.response?.data?.detail || error.message}`);
    }
  },

  // Get organization secrets (only names)
  getOrganizationSecrets: async (orgName) => {
    try {
      const response = await axios.get(`${API_BASE_URL}/github/organizations/${encodeURIComponent(orgName)}/secrets`);
      return response.data;
    } catch (error) {
      if (error.response?.status === 404) {
        throw new Error('GITHUB_TOKEN secret not found. Please add it in Secrets Management.');
      } else if (error.response?.status === 401) {
        throw new Error('GITHUB_TOKEN is invalid. Please update it in Secrets Management.');
      }
      throw new Error(`Failed to fetch organization secrets: ${error.response?.data?.detail || error.message}`);
    }
  },

  // Get organization custom properties
  getOrganizationCustomProperties: async (orgName) => {
    try {
      const response = await axios.get(`${API_BASE_URL}/github/organizations/${encodeURIComponent(orgName)}/custom-properties`);
      return response.data;
    } catch (error) {
      if (error.response?.status === 404) {
        throw new Error('GITHUB_TOKEN secret not found. Please add it in Secrets Management.');
      } else if (error.response?.status === 401) {
        throw new Error('GITHUB_TOKEN is invalid. Please update it in Secrets Management.');
      }
      throw new Error(`Failed to fetch organization custom properties: ${error.response?.data?.detail || error.message}`);
    }
  },

  // Get organization variables
  getOrganizationVariables: async (orgName) => {
    try {
      const response = await axios.get(`${API_BASE_URL}/github/organizations/${encodeURIComponent(orgName)}/variables`);
      return response.data;
    } catch (error) {
      if (error.response?.status === 404) {
        throw new Error('GITHUB_TOKEN secret not found. Please add it in Secrets Management.');
      } else if (error.response?.status === 401) {
        throw new Error('GITHUB_TOKEN is invalid. Please update it in Secrets Management.');
      }
      throw new Error(`Failed to fetch organization variables: ${error.response?.data?.detail || error.message}`);
    }
  }
};

// Named exports for backward compatibility and convenience
export const getOrganizations = githubAPI.getOrganizations;
export const getUserInfo = githubAPI.getUserInfo;

// Simplified repository functions for OnboardingScanner (fetch all repos without language filter)
export const getUserRepositories = async () => {
  try {
    const response = await axios.get(`${API_BASE_URL}/github/user/repositories?language=all`);
    return response.data;
  } catch (error) {
    if (error.response?.status === 404) {
      throw new Error('GITHUB_TOKEN secret not found. Please add it in Secrets Management.');
    } else if (error.response?.status === 401) {
      throw new Error('GITHUB_TOKEN is invalid. Please update it in Secrets Management.');
    }
    throw new Error(`Failed to fetch user repositories: ${error.response?.data?.detail || error.message}`);
  }
};

export const getOrganizationRepositories = async (orgName) => {
  try {
    const response = await axios.get(`${API_BASE_URL}/github/organizations/${encodeURIComponent(orgName)}/repositories?language=all`);
    return response.data;
  } catch (error) {
    if (error.response?.status === 404) {
      throw new Error('GITHUB_TOKEN secret not found. Please add it in Secrets Management.');
    } else if (error.response?.status === 401) {
      throw new Error('GITHUB_TOKEN is invalid. Please update it in Secrets Management.');
    }
    throw new Error(`Failed to fetch organization repositories: ${error.response?.data?.detail || error.message}`);
  }
};