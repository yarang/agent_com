/**
 * View Router for AI Agent Communication System
 *
 * Provides hash-based routing for Single Page Application (SPA) navigation.
 * Supports route guards for authentication and dynamic view switching.
 *
 * @module router
 */

// View constants
const Views = {
    DASHBOARD: 'dashboard',
    MISSION_CONTROL: 'mission-control',
    LOGIN: 'login',
    SETTINGS: 'settings',
    MEDIATORS: 'mediators',
    PROJECTS: 'projects',
};

// Router state
let currentView = Views.DASHBOARD;
let currentPath = '';
let routes = {};
let beforeHooks = [];
let afterHooks = [];
let isInitialized = false;

/**
 * Router class for managing SPA navigation
 */
class Router {
    constructor() {
        this.currentView = Views.DASHBOARD;
        this.currentPath = '';
        this.routes = {};
        this.beforeHooks = [];
        this.afterHooks = [];
    }

    /**
     * Register a route with its handler
     * @param {string} path - Route path (without #)
     * @param {Function} handler - Route handler function
     * @param {Object} options - Route options
     * @param {boolean} options.requiresAuth - Whether route requires authentication
     * @param {string} options.title - Page title
     */
    register(path, handler, options = {}) {
        this.routes[path] = {
            handler,
            requiresAuth: options.requiresAuth ?? false,
            title: options.title || this.formatTitle(path),
        };
    }

    /**
     * Format path to title
     * @param {string} path - Route path
     * @returns {string} Formatted title
     */
    formatTitle(path) {
        return path
            .split('-')
            .map(word => word.charAt(0).toUpperCase() + word.slice(1))
            .join(' ');
    }

    /**
     * Register a before navigation hook
     * @param {Function} hook - Hook function(to, from)
     */
    beforeEach(hook) {
        this.beforeHooks.push(hook);
    }

    /**
     * Register an after navigation hook
     * @param {Function} hook - Hook function(to, from)
     */
    afterEach(hook) {
        this.afterHooks.push(hook);
    }

    /**
     * Navigate to a path
     * @param {string} path - Route path
     * @param {Object} params - Optional route parameters
     */
    async navigate(path, params = {}) {
        const fromPath = this.currentPath;
        const route = this.routes[path];

        // Check if route exists
        if (!route) {
            console.warn(`Route not found: ${path}`);
            // Default to dashboard for unknown routes
            this.navigate(Views.DASHBOARD);
            return;
        }

        // Check authentication requirement
        if (route.requiresAuth && typeof auth !== 'undefined' && !auth.isAuthenticated()) {
            console.log('Route requires authentication, redirecting to login');
            window.location.hash = Views.LOGIN;
            return;
        }

        // Execute before hooks
        for (const hook of this.beforeHooks) {
            try {
                const result = await hook(path, fromPath);
                if (result === false) {
                    console.log('Navigation cancelled by before hook');
                    return;
                }
            } catch (error) {
                console.error('Before hook error:', error);
            }
        }

        // Update URL hash
        window.location.hash = path;

        // Store current path
        this.currentPath = path;
        this.currentView = path;

        // Update page title
        if (route.title) {
            document.title = `${route.title} - AI Agent Communication System`;
        }

        // Execute route handler
        try {
            await route.handler(params);

            // Execute after hooks
            for (const hook of this.afterHooks) {
                try {
                    await hook(path, fromPath);
                } catch (error) {
                    console.error('After hook error:', error);
                }
            }
        } catch (error) {
            console.error(`Route handler error for ${path}:`, error);
        }

        // Dispatch navigation event
        this.dispatchNavigationEvent(path, fromPath);
    }

    /**
     * Dispatch custom navigation event
     * @param {string} toPath - Target path
     * @param {string} fromPath - Source path
     */
    dispatchNavigationEvent(toPath, fromPath) {
        const event = new CustomEvent('routechange', {
            detail: { to: toPath, from: fromPath }
        });
        window.dispatchEvent(event);
    }

    /**
     * Get current path
     * @returns {string} Current path
     */
    getCurrentPath() {
        return this.currentPath;
    }

    /**
     * Get current view
     * @returns {string} Current view
     */
    getCurrentView() {
        return this.currentView;
    }

    /**
     * Check if a path is the current path
     * @param {string} path - Path to check
     * @returns {boolean} True if path matches current path
     */
    isActive(path) {
        return this.currentPath === path;
    }

    /**
     * Initialize router
     */
    init() {
        if (isInitialized) {
            console.warn('Router already initialized');
            return;
        }

        // Handle initial hash on page load
        const initialHash = window.location.hash.slice(1) || Views.DASHBOARD;
        this.navigateToInitial(initialHash);

        // Listen for hash changes
        window.addEventListener('hashchange', () => {
            const path = window.location.hash.slice(1) || Views.DASHBOARD;
            this.navigate(path);
        });

        // Handle popstate (browser back/forward)
        window.addEventListener('popstate', () => {
            const path = window.location.hash.slice(1) || Views.DASHBOARD;
            this.navigate(path);
        });

        isInitialized = true;
        console.log('Router initialized');
    }

    /**
     * Navigate to initial hash
     * @param {string} hash - Initial hash
     */
    async navigateToInitial(hash) {
        // Check if it's a valid route
        if (this.routes[hash]) {
            await this.navigate(hash);
        } else {
            // Default to dashboard
            await this.navigate(Views.DASHBOARD);
        }
    }

    /**
     * Get all registered routes
     * @returns {Array} Array of route paths
     */
    getRoutes() {
        return Object.keys(this.routes);
    }

    /**
     * Get route info
     * @param {string} path - Route path
     * @returns {Object|null} Route info or null
     */
    getRoute(path) {
        return this.routes[path] || null;
    }
}

// Create singleton router instance
const router = new Router();

// Register default routes
router.register(Views.DASHBOARD, () => {
    // Dashboard is the default view (index.html)
    // No action needed as it's the main page
    console.log('Navigated to dashboard');
}, { requiresAuth: false, title: 'Dashboard' });

router.register(Views.MISSION_CONTROL, () => {
    // Navigate to mission control page
    console.log('Navigated to mission control');
    // Actual navigation happens by loading mission-control.html
}, { requiresAuth: false, title: 'Mission Control' });

router.register(Views.LOGIN, () => {
    // Navigate to login page
    console.log('Navigated to login');
    // Actual navigation happens by loading login.html
}, { requiresAuth: false, title: 'Login' });

router.register(Views.SETTINGS, () => {
    console.log('Navigated to settings');
}, { requiresAuth: true, title: 'Settings' });

router.register(Views.MEDIATORS, () => {
    console.log('Navigated to mediators');
}, { requiresAuth: true, title: 'Mediators' });

router.register(Views.PROJECTS, () => {
    console.log('Navigated to projects');
}, { requiresAuth: false, title: 'Projects' });

// Add authentication guard
router.beforeEach((to, from) => {
    // Check if route requires authentication
    const route = router.getRoute(to);
    if (route?.requiresAuth && typeof auth !== 'undefined' && !auth.isAuthenticated()) {
        console.log(`Route ${to} requires authentication, redirecting to login`);
        router.navigate(Views.LOGIN);
        return false; // Cancel navigation
    }

    // If user is authenticated and tries to access login, redirect to dashboard
    if (to === Views.LOGIN && typeof auth !== 'undefined' && auth.isAuthenticated()) {
        router.navigate(Views.DASHBOARD);
        return false; // Cancel navigation
    }

    return true; // Allow navigation
});

// Add analytics hook (after navigation)
router.afterEach((to, from) => {
    // Track page view (could integrate with analytics)
    console.log(`Navigation: ${from || '(initial)'} → ${to}`);

    // Update active navigation links
    updateActiveNavLinks(to);
});

/**
 * Update active navigation links
 * @param {string} currentPath - Current route path
 */
function updateActiveNavLinks(currentPath) {
    // Remove active class from all nav links
    document.querySelectorAll('.nav-link').forEach(link => {
        link.classList.remove('active');
    });

    // Add active class to current nav link
    const currentLink = document.querySelector(`.nav-link[href="#${currentPath}"]`);
    if (currentLink) {
        currentLink.classList.add('active');
    }
}

/**
 * Navigate to login page
 */
function navigateToLogin() {
    router.navigate(Views.LOGIN);
}

/**
 * Navigate to dashboard
 */
function navigateToDashboard() {
    router.navigate(Views.DASHBOARD);
}

/**
 * Navigate to mission control
 */
function navigateToMissionControl() {
    router.navigate(Views.MISSION_CONTROL);
}

/**
 * Navigate back to previous page
 */
function navigateBack() {
    if (window.history.length > 1) {
        window.history.back();
    } else {
        router.navigate(Views.DASHBOARD);
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        Router,
        router,
        Views,
        navigateToLogin,
        navigateToDashboard,
        navigateToMissionControl,
        navigateBack,
    };
}

// Browser environment: attach to window object
if (typeof window !== 'undefined') {
    window.Router = Router;
    window.router = router;
    window.Views = Views;
    window.navigateToLogin = navigateToLogin;
    window.navigateToDashboard = navigateToDashboard;
    window.navigateToMissionControl = navigateToMissionControl;
    window.navigateBack = navigateBack;
}
