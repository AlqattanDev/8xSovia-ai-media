/**
 * 8xSovia AI Studio - API Client
 *
 * Centralized API communication wrapper to prevent code duplication
 * and provide consistent error handling across all API calls.
 */

const ApiClient = (() => {
    /**
     * Base request function with error handling
     * @param {string} endpoint - API endpoint (e.g., '/api/media')
     * @param {object} options - Fetch options
     * @returns {Promise<any>} Response data
     * @throws {Error} On request failure
     */
    async function request(endpoint, options = {}) {
        const url = `${AppConfig.API_BASE_URL}${endpoint}`;

        try {
            const response = await fetch(url, {
                headers: {
                    'Content-Type': 'application/json',
                    ...options.headers
                },
                ...options
            });

            // Handle HTTP errors
            if (!response.ok) {
                const errorText = await response.text().catch(() => response.statusText);
                throw new Error(`HTTP ${response.status}: ${errorText}`);
            }

            // Handle empty responses
            if (response.status === 204) {
                return null;
            }

            // Parse JSON response
            return await response.json();

        } catch (error) {
            console.error(`API ${options.method || 'GET'} ${endpoint} failed:`, error);
            throw error;
        }
    }

    /**
     * GET request
     * @param {string} endpoint - API endpoint
     * @param {object} params - URL query parameters
     * @returns {Promise<any>} Response data
     */
    async function get(endpoint, params = {}) {
        // Build query string
        const queryString = Object.keys(params).length > 0
            ? '?' + new URLSearchParams(params).toString()
            : '';

        return request(endpoint + queryString, {
            method: 'GET'
        });
    }

    /**
     * POST request
     * @param {string} endpoint - API endpoint
     * @param {object} data - Request body data
     * @returns {Promise<any>} Response data
     */
    async function post(endpoint, data = {}) {
        return request(endpoint, {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }

    /**
     * PUT request
     * @param {string} endpoint - API endpoint
     * @param {object} data - Request body data
     * @returns {Promise<any>} Response data
     */
    async function put(endpoint, data = {}) {
        return request(endpoint, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    }

    /**
     * PATCH request
     * @param {string} endpoint - API endpoint
     * @param {object} data - Request body data
     * @returns {Promise<any>} Response data
     */
    async function patch(endpoint, data = {}) {
        return request(endpoint, {
            method: 'PATCH',
            body: JSON.stringify(data)
        });
    }

    /**
     * DELETE request
     * @param {string} endpoint - API endpoint
     * @returns {Promise<any>} Response data
     */
    async function del(endpoint) {
        return request(endpoint, {
            method: 'DELETE'
        });
    }

    /**
     * Upload file(s)
     * @param {string} endpoint - API endpoint
     * @param {FormData} formData - Form data with files
     * @returns {Promise<any>} Response data
     */
    async function upload(endpoint, formData) {
        const url = `${AppConfig.API_BASE_URL}${endpoint}`;

        try {
            const response = await fetch(url, {
                method: 'POST',
                body: formData
                // Don't set Content-Type header - let browser set it with boundary
            });

            if (!response.ok) {
                const errorText = await response.text().catch(() => response.statusText);
                throw new Error(`HTTP ${response.status}: ${errorText}`);
            }

            return await response.json();

        } catch (error) {
            console.error(`API upload to ${endpoint} failed:`, error);
            throw error;
        }
    }

    /**
     * Execute API call with automatic error toast
     * @param {Promise} apiCall - API call promise
     * @param {object} messages - {success, error} messages
     * @returns {Promise<any>} Response data or null on error
     */
    async function withToast(apiCall, messages = {}) {
        try {
            const data = await apiCall;

            if (messages.success) {
                SharedUtils.showToast(messages.success, 'success');
            }

            return data;

        } catch (error) {
            const errorMessage = messages.error || 'Operation failed';
            SharedUtils.showToast(errorMessage, 'error');
            return null;
        }
    }

    // Public API
    return {
        // HTTP methods
        get,
        post,
        put,
        patch,
        delete: del,
        upload,

        // Utilities
        withToast,

        // Direct access to request function for custom calls
        request
    };
})();

// Make available globally
if (typeof window !== 'undefined') {
    window.ApiClient = ApiClient;
}
