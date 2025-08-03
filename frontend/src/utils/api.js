import { auth } from '../firebase';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

/**
 * Get the current Firebase ID token
 * @returns {Promise<string>} The ID token
 */
const getIdToken = async () => {
  const user = auth.currentUser;
  if (!user) {
    throw new Error('No authenticated user');
  }
  return await user.getIdToken();
};

/**
 * Make an authenticated API request
 * @param {string} endpoint - The API endpoint (without base URL)
 * @param {Object} options - Fetch options
 * @returns {Promise<Object>} The response data
 */
export const apiRequest = async (endpoint, options = {}) => {
  try {
    const token = await getIdToken();
    
    const url = `${API_BASE_URL}${endpoint}`;
    const config = {
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
        ...options.headers,
      },
      ...options,
    };

    const response = await fetch(url, config);
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    console.error('API request failed:', error);
    throw error;
  }
};

/**
 * GET request
 * @param {string} endpoint - The API endpoint
 * @returns {Promise<Object>} The response data
 */
export const apiGet = (endpoint) => apiRequest(endpoint, { method: 'GET' });

/**
 * POST request
 * @param {string} endpoint - The API endpoint
 * @param {Object} data - The data to send
 * @returns {Promise<Object>} The response data
 */
export const apiPost = (endpoint, data) => apiRequest(endpoint, {
  method: 'POST',
  body: JSON.stringify(data),
});

/**
 * PUT request
 * @param {string} endpoint - The API endpoint
 * @param {Object} data - The data to send
 * @returns {Promise<Object>} The response data
 */
export const apiPut = (endpoint, data) => apiRequest(endpoint, {
  method: 'PUT',
  body: JSON.stringify(data),
});

/**
 * DELETE request
 * @param {string} endpoint - The API endpoint
 * @returns {Promise<Object>} The response data
 */
export const apiDelete = (endpoint) => apiRequest(endpoint, { method: 'DELETE' });

// Example usage functions
export const api = {
  // User profile endpoints
  getUserProfile: () => apiGet('/api/user/profile'),
  updateUserProfile: (profileData) => apiPut('/api/user/profile', profileData),
  
  // Protected route example
  getProtectedData: () => apiGet('/api/protected'),
  
  // Upload endpoints
  uploadImageMetadata: (metadata) => apiPost('/api/upload/metadata', metadata),
};

export default api; 