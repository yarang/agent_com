/**
 * Authentication Module for AI Agent Communication System
 *
 * Manages user authentication, session handling, token management,
 * and protected route guards.
 *
 * @module auth
 */

// Authentication state
let accessToken = null;
let refreshTokenValue = null;
let user = null;
let tokenRefreshTimer = null;
let authCallbacks = [];

// Storage keys
const STORAGE_KEYS = {
    ACCESS_TOKEN: 'access_token',
    REFRESH_TOKEN: 'refresh_token',
    USER: 'user',
    REMEMBER_ME: 'remember_me',
    RETURN_URL: 'auth_return_url',
};

// Token refresh interval (5 minutes before expiry)
const TOKEN_REFRESH_INTERVAL = 4 * 60 * 1000;

/**
 * AuthManager class for managing authentication
 */
class AuthManager {
    constructor() {
        this.accessToken = null;
        this.refreshTokenValue = null;
        this.user = null;
        this.tokenRefreshTimer = null;
        this.loadFromStorage();
    }

    /**
     * Load authentication data from storage
     */
    loadFromStorage() {
        try {
            this.accessToken = localStorage.getItem(STORAGE_KEYS.ACCESS_TOKEN) ||
                              sessionStorage.getItem(STORAGE_KEYS.ACCESS_TOKEN);
            this.refreshTokenValue = localStorage.getItem(STORAGE_KEYS.REFRESH_TOKEN) ||
                                     sessionStorage.getItem(STORAGE_KEYS.REFRESH_TOKEN);
            const userJson = localStorage.getItem(STORAGE_KEYS.USER) ||
                             sessionStorage.getItem(STORAGE_KEYS.USER);
            this.user = userJson ? JSON.parse(userJson) : null;
        } catch (error) {
            console.error('Error loading auth data from storage:', error);
            this.clearStorage();
        }
    }

    /**
     * Save authentication data to storage
     * @param {boolean} remember - Whether to use persistent storage
     */
    saveToStorage(remember = true) {
        const storage = remember ? localStorage : sessionStorage;

        try {
            storage.setItem(STORAGE_KEYS.ACCESS_TOKEN, this.accessToken || '');
            storage.setItem(STORAGE_KEYS.REFRESH_TOKEN, this.refreshTokenValue || '');
            storage.setItem(STORAGE_KEYS.USER, JSON.stringify(this.user || {}));

            // Set remember me flag
            localStorage.setItem(STORAGE_KEYS.REMEMBER_ME, remember.toString());
        } catch (error) {
            console.error('Error saving auth data to storage:', error);
        }
    }

    /**
     * Clear authentication data from storage
     */
    clearStorage() {
        localStorage.removeItem(STORAGE_KEYS.ACCESS_TOKEN);
        localStorage.removeItem(STORAGE_KEYS.REFRESH_TOKEN);
        localStorage.removeItem(STORAGE_KEYS.USER);
        sessionStorage.removeItem(STORAGE_KEYS.ACCESS_TOKEN);
        sessionStorage.removeItem(STORAGE_KEYS.REFRESH_TOKEN);
        sessionStorage.removeItem(STORAGE_KEYS.USER);
    }

    /**
     * Login with username and password
     * @param {string} username - Username
     * @param {string} password - Password
     * @param {boolean} remember - Whether to remember login
     * @returns {Promise<Object>} Login result
     */
    async login(username, password, remember = true) {
        try {
            const response = await fetch(`${API_BASE_URL}/auth/login`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password }),
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new AuthError(errorData.detail || 'Login failed', response.status);
            }

            const data = await response.json();

            this.accessToken = data.access_token;
            this.refreshTokenValue = data.refresh_token;
            this.user = data.user || { username };

            this.saveToStorage(remember);
            this.startTokenRefresh();

            // Update API client token
            if (typeof setAuthToken === 'function') {
                setAuthToken(this.accessToken);
            }

            // Notify callbacks
            this.notifyCallbacks('login', this.user);

            return { success: true, user: this.user };
        } catch (error) {
            console.error('Login error:', error);
            throw error;
        }
    }

    /**
     * Signup with username, password, and email
     * @param {string} username - Username
     * @param {string} password - Password
     * @param {string} email - Email address
     * @param {boolean} remember - Whether to remember login
     * @returns {Promise<Object>} Signup result
     */
    async signup(username, password, email, remember = true) {
        try {
            const response = await fetch(`${API_BASE_URL}/auth/signup`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password, email }),
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new AuthError(errorData.detail || 'Signup failed', response.status);
            }

            const data = await response.json();

            // Auto-login after signup
            return await this.login(username, password, remember);
        } catch (error) {
            console.error('Signup error:', error);
            throw error;
        }
    }

    /**
     * Refresh access token
     * @returns {Promise<boolean>} True if refresh succeeded
     */
    async refreshAccessToken() {
        if (!this.refreshTokenValue) {
            return false;
        }

        try {
            const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ refresh_token: this.refreshTokenValue }),
            });

            if (!response.ok) {
                throw new Error('Token refresh failed');
            }

            const data = await response.json();

            this.accessToken = data.access_token;
            if (data.refresh_token) {
                this.refreshTokenValue = data.refresh_token;
            }

            this.saveToStorage(localStorage.getItem(STORAGE_KEYS.REMEMBER_ME) === 'true');

            // Update API client token
            if (typeof setAuthToken === 'function') {
                setAuthToken(this.accessToken);
            }

            return true;
        } catch (error) {
            console.error('Token refresh error:', error);
            this.logout();
            return false;
        }
    }

    /**
     * Start automatic token refresh
     */
    startTokenRefresh() {
        this.stopTokenRefresh();

        tokenRefreshTimer = setInterval(async () => {
            await this.refreshAccessToken();
        }, TOKEN_REFRESH_INTERVAL);
    }

    /**
     * Stop automatic token refresh
     */
    stopTokenRefresh() {
        if (tokenRefreshTimer) {
            clearInterval(tokenRefreshTimer);
            tokenRefreshTimer = null;
        }
    }

    /**
     * Logout and clear session
     */
    logout() {
        this.stopTokenRefresh();

        // Clear tokens
        this.accessToken = null;
        this.refreshTokenValue = null;
        this.user = null;

        // Clear storage
        this.clearStorage();

        // Clear API client token
        if (typeof setAuthToken === 'function') {
            setAuthToken(null);
        }

        // Notify callbacks
        this.notifyCallbacks('logout');

        // Navigate to login
        if (typeof router !== 'undefined') {
            router.navigate(Views.LOGIN);
        }
    }

    /**
     * Check if user is authenticated
     * @returns {boolean} True if authenticated
     */
    isAuthenticated() {
        // If we have an access token, consider the user authenticated
        // The user object may not be populated if the API doesn't return it
        return !!this.accessToken;
    }

    /**
     * Get current user
     * @returns {Object|null} User object
     */
    getUser() {
        // Return user object, or create a default one if not set but authenticated
        if (!this.user && this.accessToken) {
            return { username: 'User' };
        }
        return this.user;
    }

    /**
     * Get current user
     * @returns {Object|null} User object
     */
    getUser() {
        return this.user;
    }

    /**
     * Get access token
     * @returns {string|null} Access token
     */
    getAccessToken() {
        return this.accessToken;
    }

    /**
     * Get authorization header value
     * @returns {string|null} Bearer token
     */
    getAuthHeader() {
        return this.accessToken ? `Bearer ${this.accessToken}` : null;
    }

    /**
     * Register authentication state change callback
     * @param {Function} callback - Callback function(event, data)
     */
    onAuthChange(callback) {
        authCallbacks.push(callback);
    }

    /**
     * Remove authentication state change callback
     * @param {Function} callback - Callback function to remove
     */
    offAuthChange(callback) {
        const index = authCallbacks.indexOf(callback);
        if (index > -1) {
            authCallbacks.splice(index, 1);
        }
    }

    /**
     * Notify all callbacks of auth state change
     * @param {string} event - Event type (login, logout)
     * @param {Object} data - Event data
     */
    notifyCallbacks(event, data = null) {
        authCallbacks.forEach(callback => {
            try {
                callback(event, data);
            } catch (error) {
                console.error('Auth callback error:', error);
            }
        });

        // Dispatch custom event
        const customEvent = new CustomEvent('authchange', {
            detail: { event, data }
        });
        window.dispatchEvent(customEvent);
    }

    /**
     * Fetch current user profile from server
     * @returns {Promise<Object>} User profile
     */
    async fetchUserProfile() {
        if (!this.isAuthenticated()) {
            throw new AuthError('Not authenticated', 401);
        }

        try {
            const response = await fetchWithAuth(`${API_BASE_URL}/auth/me`);

            if (!response.ok) {
                throw new AuthError('Failed to fetch user profile', response.status);
            }

            const data = await response.json();
            this.user = data;
            this.saveToStorage(localStorage.getItem(STORAGE_KEYS.REMEMBER_ME) === 'true');

            return data;
        } catch (error) {
            console.error('Fetch user profile error:', error);
            throw error;
        }
    }

    /**
     * Update user profile
     * @param {Object} updates - Profile updates
     * @returns {Promise<Object>} Updated user profile
     */
    async updateProfile(updates) {
        if (!this.isAuthenticated()) {
            throw new AuthError('Not authenticated', 401);
        }

        try {
            const response = await fetchWithAuth(`${API_BASE_URL}/auth/me`, {
                method: 'PUT',
                body: JSON.stringify(updates),
            });

            if (!response.ok) {
                throw new AuthError('Failed to update profile', response.status);
            }

            const data = await response.json();
            this.user = { ...this.user, ...data };
            this.saveToStorage(localStorage.getItem(STORAGE_KEYS.REMEMBER_ME) === 'true');

            return data;
        } catch (error) {
            console.error('Update profile error:', error);
            throw error;
        }
    }

    /**
     * Change password
     * @param {string} oldPassword - Current password
     * @param {string} newPassword - New password
     * @returns {Promise<boolean>} True if password changed
     */
    async changePassword(oldPassword, newPassword) {
        if (!this.isAuthenticated()) {
            throw new AuthError('Not authenticated', 401);
        }

        try {
            const response = await fetchWithAuth(`${API_BASE_URL}/auth/change-password`, {
                method: 'POST',
                body: JSON.stringify({ old_password: oldPassword, new_password: newPassword }),
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new AuthError(errorData.detail || 'Failed to change password', response.status);
            }

            return true;
        } catch (error) {
            console.error('Change password error:', error);
            throw error;
        }
    }
}

/**
 * Custom AuthError class
 */
class AuthError extends Error {
    constructor(message, code = 0) {
        super(message);
        this.name = 'AuthError';
        this.code = code;
    }
}

// Create singleton auth instance
const auth = new AuthManager();

// ==================== Redirect Functions ====================

/**
 * Check if current page is exempt from authentication redirect
 * Prevents infinite redirect loops on login/signup pages
 * @returns {boolean} True if current page is exempt from redirect
 */
function isExemptPage() {
    const exemptPaths = ['/login.html', '/login', '/signup.html', '/signup'];
    const currentPath = window.location.pathname;
    return exemptPaths.some(path => currentPath.includes(path));
}

/**
 * Store the current URL for post-login redirect
 * Stores full path including query parameters and hash fragments
 */
function storeReturnUrl() {
    const returnUrl = window.location.pathname + window.location.search + window.location.hash;
    sessionStorage.setItem(STORAGE_KEYS.RETURN_URL, returnUrl);
}

/**
 * Get and clear the stored return URL
 * Returns the stored URL or default dashboard if invalid/missing
 * @returns {string} Return URL for post-login redirect
 */
function getReturnUrl() {
    let returnUrl = sessionStorage.getItem(STORAGE_KEYS.RETURN_URL);
    sessionStorage.removeItem(STORAGE_KEYS.RETURN_URL);

    // Validate return URL - prevent redirecting to login/signup or external domains
    if (!returnUrl) {
        return '/index.html';
    }

    // Check if return URL points to login or signup pages
    const exemptPatterns = ['/login', '/signup'];
    const isExempt = exemptPatterns.some(pattern => returnUrl.includes(pattern));

    if (isExempt) {
        return '/index.html';
    }

    // Ensure return URL is relative (prevent open redirect vulnerabilities)
    if (returnUrl.startsWith('http://') || returnUrl.startsWith('https://')) {
        return '/index.html';
    }

    return returnUrl || '/index.html';
}

/**
 * Redirect unauthenticated user to login page
 * Stores current URL before redirect for post-login return
 */
function redirectToLogin() {
    if (isExemptPage()) {
        return; // Don't redirect if already on login page
    }
    storeReturnUrl();
    window.location.href = '/login.html';
}

// ==================== Auth Initialization ====================

// Initialize auth on page load
function initAuth() {
    auth.loadFromStorage();

    // Check if user is authenticated
    if (!auth.isAuthenticated() && !isExemptPage()) {
        // Redirect to login for protected pages
        redirectToLogin();
        return;
    }

    if (auth.isAuthenticated()) {
        auth.startTokenRefresh();

        // Update API client token
        if (typeof setAuthToken === 'function') {
            setAuthToken(auth.getAccessToken());
        }
    }
}

// Handle 401 responses globally
function handleAuthError(response) {
    if (response.status === 401) {
        // Token expired or invalid, try refresh then logout
        auth.refreshAccessToken().catch(() => {
            auth.logout();
        });
    }
    return response;
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        AuthManager,
        AuthError,
        auth,
        initAuth,
        handleAuthError,
        STORAGE_KEYS,
        isExemptPage,
        storeReturnUrl,
        getReturnUrl,
        redirectToLogin,
    };
}

// Browser environment: attach to window object
if (typeof window !== 'undefined') {
    window.AuthManager = AuthManager;
    window.AuthError = AuthError;
    window.auth = auth;
    window.initAuth = initAuth;
    window.handleAuthError = handleAuthError;
    window.isExemptPage = isExemptPage;
    window.storeReturnUrl = storeReturnUrl;
    window.getReturnUrl = getReturnUrl;
    window.redirectToLogin = redirectToLogin;
}

// Initialize auth when DOM is ready (but NOT on login/signup pages)
if (typeof window !== 'undefined') {
    // Don't initialize auth on login or signup pages to prevent redirect loops
    const isLoginPage = isExemptPage();

    if (!isLoginPage) {
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', initAuth);
        } else {
            initAuth();
        }
    }
}
