/**
 * 8xSovia AI Studio - Centralized Configuration
 *
 * This file contains all global configuration constants to prevent duplication
 * across multiple files and enable easy environment-specific configuration.
 */

const AppConfig = (() => {
    /**
     * Automatically detect the API base URL based on environment
     * - Development: Uses localhost:8000
     * - Production: Uses same origin as the web app
     */
    const getApiBaseUrl = () => {
        const isDev = ['localhost', '127.0.0.1'].includes(window.location.hostname);
        return isDev ? 'http://localhost:8000' : window.location.origin;
    };

    return {
        // API Configuration
        API_BASE_URL: getApiBaseUrl(),

        // Application Metadata
        APP_NAME: '8xSovia AI Studio',
        VERSION: '1.0.0',

        // UI Configuration
        TOAST_DURATION: 3000, // milliseconds
        DEBOUNCE_DELAY: 300,  // milliseconds for search/filter debouncing

        // Pagination
        DEFAULT_PAGE_SIZE: 50,
        MAX_PAGE_SIZE: 100,

        // Cache Configuration
        CACHE_TTL: 300000, // 5 minutes in milliseconds

        // Feature Flags
        FEATURES: {
            COLLECTIONS: true,
            COMPARISON: true,
            SMART_FILTERS: true,
            VIDEO_PREVIEW: true
        }
    };
})();

// Make available globally for backwards compatibility
if (typeof window !== 'undefined') {
    window.AppConfig = AppConfig;
}
