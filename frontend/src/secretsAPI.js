import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000/api';

// Set default timeout and error handling
axios.defaults.timeout = 10000;

export const secretsAPI = {
  // Get all secrets (without decrypted values)
  getSecrets: async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/secrets`);
      return response.data;
    } catch (error) {
      throw new Error(`Failed to fetch secrets: ${error.response?.data?.detail || error.message}`);
    }
  },

  // Get a secret by ID (without decrypted value)
  getSecret: async (id) => {
    try {
      const response = await axios.get(`${API_BASE_URL}/secrets/${id}`);
      return response.data;
    } catch (error) {
      throw new Error(`Failed to fetch secret: ${error.response?.data?.detail || error.message}`);
    }
  },

  // Get a secret with decrypted value
  getDecryptedSecret: async (id) => {
    try {
      const response = await axios.get(`${API_BASE_URL}/secrets/${id}/decrypt`);
      return response.data;
    } catch (error) {
      throw new Error(`Failed to decrypt secret: ${error.response?.data?.detail || error.message}`);
    }
  },

  // Create a new secret
  createSecret: async (secret) => {
    try {
      const response = await axios.post(`${API_BASE_URL}/secrets`, secret);
      return response.data;
    } catch (error) {
      throw new Error(`Failed to create secret: ${error.response?.data?.detail || error.message}`);
    }
  },

  // Update a secret
  updateSecret: async (id, updates) => {
    try {
      const response = await axios.put(`${API_BASE_URL}/secrets/${id}`, updates);
      return response.data;
    } catch (error) {
      throw new Error(`Failed to update secret: ${error.response?.data?.detail || error.message}`);
    }
  },

  // Delete a secret
  deleteSecret: async (id) => {
    try {
      const response = await axios.delete(`${API_BASE_URL}/secrets/${id}`);
      return response.data;
    } catch (error) {
      throw new Error(`Failed to delete secret: ${error.response?.data?.detail || error.message}`);
    }
  },

  // Get secret by name
  getSecretByName: async (name) => {
    try {
      const response = await axios.get(`${API_BASE_URL}/secrets/name/${encodeURIComponent(name)}`);
      return response.data;
    } catch (error) {
      throw new Error(`Failed to fetch secret by name: ${error.response?.data?.detail || error.message}`);
    }
  }
};