/**
 * Chart rendering module for AI Agent Communication System Status Board
 *
 * Handles Chart.js integration for activity visualization.
 * This file is kept for compatibility but chart functionality
 * has been integrated into dashboard.js for the tab-based interface.
 */

// Chart.js default configuration
Chart.defaults.color = '#cbd5e1';
Chart.defaults.borderColor = '#334155';
Chart.defaults.font.family = "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif";

/**
 * Destroy all charts
 * Used for cleanup
 */
function destroyAllCharts() {
    // Charts are now managed in dashboard.js
    // This function is kept for compatibility
    console.log('Charts destroyed');
}

/**
 * Resize all charts to fit their containers
 */
function resizeAllCharts() {
    // Charts are now managed in dashboard.js
    // This function is kept for compatibility
    console.log('Charts resized');
}

// Handle window resize
let resizeTimeout;
window.addEventListener('resize', () => {
    clearTimeout(resizeTimeout);
    resizeTimeout = setTimeout(() => {
        resizeAllCharts();
    }, 250);
});

// Export functions
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        destroyAllCharts,
        resizeAllCharts,
    };
}
