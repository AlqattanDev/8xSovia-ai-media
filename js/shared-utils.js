/**
 * 8xSovia AI Studio - Shared Utilities
 *
 * Common utility functions used across all pages to prevent code duplication.
 * Includes toast notifications, string escaping, modal management, and more.
 */

const SharedUtils = (() => {
    // ===== TOAST NOTIFICATIONS =====

    /**
     * Display a toast notification to the user
     * @param {string} message - The message to display
     * @param {string} type - Toast type: 'info', 'success', 'error', 'warning'
     */
    function showToast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.textContent = message;
        toast.setAttribute('role', 'alert');
        toast.setAttribute('aria-live', 'assertive');
        document.body.appendChild(toast);

        // Auto-remove after configured duration
        setTimeout(() => {
            toast.remove();
        }, AppConfig.TOAST_DURATION || 3000);
    }

    // ===== STRING ESCAPING =====

    /**
     * Escape HTML special characters to prevent XSS
     * @param {string} text - Text to escape
     * @returns {string} HTML-safe text
     */
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * Escape JavaScript special characters for safe inline JS
     * @param {string} text - Text to escape
     * @returns {string} JS-safe text
     */
    function escapeJs(text) {
        return text.replace(/\\/g, '\\\\')
                  .replace(/'/g, "\\'")
                  .replace(/"/g, '\\"')
                  .replace(/\n/g, '\\n')
                  .replace(/\r/g, '\\r');
    }

    // ===== MODAL MANAGEMENT =====

    /**
     * Open a modal by ID
     * @param {string} modalId - The ID of the modal element
     */
    function openModal(modalId) {
        const modal = document.getElementById(modalId);
        if (!modal) {
            console.warn(`Modal with ID '${modalId}' not found`);
            return;
        }
        modal.classList.add('active');
        document.body.style.overflow = 'hidden';
    }

    /**
     * Close a modal by ID
     * @param {string} modalId - The ID of the modal element
     */
    function closeModal(modalId) {
        const modal = document.getElementById(modalId);
        if (!modal) {
            console.warn(`Modal with ID '${modalId}' not found`);
            return;
        }
        modal.classList.remove('active');
        document.body.style.overflow = 'auto';
    }

    // ===== DEBOUNCING =====

    /**
     * Create a debounced version of a function
     * @param {Function} func - Function to debounce
     * @param {number} delay - Delay in milliseconds
     * @returns {Function} Debounced function
     */
    function debounce(func, delay = AppConfig.DEBOUNCE_DELAY || 300) {
        let timeout;
        return function(...args) {
            clearTimeout(timeout);
            timeout = setTimeout(() => func.apply(this, args), delay);
        };
    }

    // ===== FORMATTING HELPERS =====

    /**
     * Format a date for display
     * @param {string|Date} date - Date to format
     * @param {object} options - Intl.DateTimeFormat options
     * @returns {string} Formatted date string
     */
    function formatDate(date, options = {}) {
        const defaultOptions = {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            ...options
        };
        return new Date(date).toLocaleDateString(undefined, defaultOptions);
    }

    /**
     * Format a relative time (e.g., "2 hours ago")
     * @param {string|Date} date - Date to format
     * @returns {string} Relative time string
     */
    function formatRelativeTime(date) {
        const now = new Date();
        const past = new Date(date);
        const diffMs = now - past;
        const diffMins = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMins / 60);
        const diffDays = Math.floor(diffHours / 24);

        if (diffMins < 1) return 'Just now';
        if (diffMins < 60) return `${diffMins} minute${diffMins !== 1 ? 's' : ''} ago`;
        if (diffHours < 24) return `${diffHours} hour${diffHours !== 1 ? 's' : ''} ago`;
        if (diffDays < 7) return `${diffDays} day${diffDays !== 1 ? 's' : ''} ago`;
        return formatDate(date);
    }

    // ===== CLIPBOARD =====

    /**
     * Copy text to clipboard with user feedback
     * @param {string} text - Text to copy
     * @param {string} successMessage - Optional success message
     */
    async function copyToClipboard(text, successMessage = 'Copied to clipboard!') {
        try {
            await navigator.clipboard.writeText(text);
            showToast(successMessage, 'success');
        } catch (err) {
            console.error('Failed to copy to clipboard:', err);
            showToast('Failed to copy', 'error');
        }
    }

    // ===== DOM HELPERS =====

    /**
     * Safely get element by ID with error handling
     * @param {string} id - Element ID
     * @returns {HTMLElement|null} Element or null
     */
    function getElement(id) {
        const el = document.getElementById(id);
        if (!el) {
            console.warn(`Element with ID '${id}' not found`);
        }
        return el;
    }

    /**
     * Create element with classes and attributes
     * @param {string} tag - HTML tag name
     * @param {object} options - {classes: [], attrs: {}, text: ''}
     * @returns {HTMLElement} Created element
     */
    function createElement(tag, options = {}) {
        const el = document.createElement(tag);

        if (options.classes) {
            el.className = Array.isArray(options.classes)
                ? options.classes.join(' ')
                : options.classes;
        }

        if (options.attrs) {
            Object.entries(options.attrs).forEach(([key, value]) => {
                el.setAttribute(key, value);
            });
        }

        if (options.text) {
            el.textContent = options.text;
        }

        if (options.html) {
            el.innerHTML = options.html;
        }

        return el;
    }

    // Public API
    return {
        // Toast notifications
        showToast,

        // String escaping
        escapeHtml,
        escapeJs,

        // Modal management
        openModal,
        closeModal,

        // Utilities
        debounce,
        formatDate,
        formatRelativeTime,
        copyToClipboard,

        // DOM helpers
        getElement,
        createElement
    };
})();

// Make available globally
if (typeof window !== 'undefined') {
    window.SharedUtils = SharedUtils;
}
