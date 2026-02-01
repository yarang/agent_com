/**
 * I18n (Internationalization) Manager
 *
 * Handles language switching and translation loading for the dashboard.
 */

class I18n {
    constructor() {
        this.currentLanguage = this.loadLanguage();
        this.translations = {};
        this.fallbackLanguage = 'ko';
        this STORAGE_KEY = 'dashboard_language';
        this.SUPPORTED_LANGUAGES = ['ko', 'en'];
    }

    /**
     * Load language preference from localStorage
     * @returns {string} Language code
     */
    loadLanguage() {
        const stored = localStorage.getItem(this.STORAGE_KEY);
        if (stored && this.SUPPORTED_LANGUAGES.includes(stored)) {
            return stored;
        }
        // Try browser language detection
        const browserLang = navigator.language?.split('-')[0];
        if (browserLang && this.SUPPORTED_LANGUAGES.includes(browserLang)) {
            return browserLang;
        }
        return 'ko'; // Default to Korean
    }

    /**
     * Load translations for current language
     * @returns {Promise<void>}
     */
    async loadTranslations() {
        try {
            const response = await fetch(`/api/v1/i18n/${this.currentLanguage}`);
            if (!response.ok) {
                throw new Error(`Failed to load translations: ${response.status}`);
            }
            const data = await response.json();
            this.translations = data.translations || {};
        } catch (error) {
            console.error('Error loading translations:', error);
            // Load fallback translations
            await this.loadFallbackTranslations();
        }
    }

    /**
     * Load fallback translations
     * @returns {Promise<void>}
     */
    async loadFallbackTranslations() {
        if (this.currentLanguage === this.fallbackLanguage) {
            return;
        }
        try {
            const response = await fetch(`/api/v1/i18n/${this.fallbackLanguage}`);
            if (!response.ok) {
                return;
            }
            const data = await response.json();
            this.translations = data.translations || {};
        } catch (error) {
            console.error('Error loading fallback translations:', error);
        }
    }

    /**
     * Set current language and reload translations
     * @param {string} lang - Language code
     * @returns {Promise<void>}
     */
    async setLanguage(lang) {
        if (!this.SUPPORTED_LANGUAGES.includes(lang)) {
            console.warn(`Unsupported language: ${lang}`);
            return;
        }

        if (lang === this.currentLanguage) {
            return;
        }

        this.currentLanguage = lang;
        localStorage.setItem(this.STORAGE_KEY, lang);

        // Reload translations
        await this.loadTranslations();

        // Update all [data-i18n] elements
        this.updateDOM();

        // Update HTML lang attribute
        document.documentElement.lang = lang;
    }

    /**
     * Get translation for a key
     * Supports nested keys with dot notation (e.g., 'stats.totalAgents')
     * @param {string} key - Translation key
     * @param {Object} params - Optional parameters for string interpolation
     * @returns {string} Translated string
     */
    t(key, params = {}) {
        const keys = key.split('.');
        let value = this.translations;

        for (const k of keys) {
            if (value && typeof value === 'object' && k in value) {
                value = value[k];
            } else {
                // Key not found, return the key itself
                console.warn(`Translation key not found: ${key}`);
                return key;
            }
        }

        if (typeof value !== 'string') {
            console.warn(`Translation value is not a string: ${key}`);
            return key;
        }

        // Replace parameters in the string (e.g., {nickname})
        return this.interpolate(value, params);
    }

    /**
     * Interpolate parameters into a string
     * @param {string} str - String with placeholders
     * @param {Object} params - Parameters to replace
     * @returns {string} Interpolated string
     */
    interpolate(str, params) {
        return str.replace(/\{(\w+)\}/g, (match, key) => {
            return params[key] !== undefined ? params[key] : match;
        });
    }

    /**
     * Update all DOM elements with data-i18n attribute
     */
    updateDOM() {
        // Update text content
        document.querySelectorAll('[data-i18n]').forEach(element => {
            const key = element.getAttribute('data-i18n');
            const translation = this.t(key);
            element.textContent = translation;
        });

        // Update placeholders
        document.querySelectorAll('[data-i18n-placeholder]').forEach(element => {
            const key = element.getAttribute('data-i18n-placeholder');
            const translation = this.t(key);
            element.placeholder = translation;
        });

        // Update titles
        document.querySelectorAll('[data-i18n-title]').forEach(element => {
            const key = element.getAttribute('data-i18n-title');
            const translation = this.t(key);
            element.title = translation;
        });

        // Dispatch custom event for other components to listen
        window.dispatchEvent(new CustomEvent('languageChanged', {
            detail: { language: this.currentLanguage }
        }));
    }

    /**
     * Get current language
     * @returns {string} Current language code
     */
    getCurrentLanguage() {
        return this.currentLanguage;
    }

    /**
     * Get supported languages
     * @returns {Array<string>} Array of language codes
     */
    getSupportedLanguages() {
        return [...this.SUPPORTED_LANGUAGES];
    }

    /**
     * Initialize i18n system
     * @returns {Promise<void>}
     */
    async init() {
        await this.loadTranslations();
        this.updateDOM();
        document.documentElement.lang = this.currentLanguage;
    }
}

// Create global i18n instance
const i18n = new I18n();

// Initialization promise
let i18nReady = false;
const i18nInitPromise = i18n.init().then(() => {
    i18nReady = true;
});

/**
 * Wait for i18n to be initialized
 * @returns {Promise<void>}
 */
function waitForI18n() {
    return i18nInitPromise;
}

/**
 * Global translation function
 * @param {string} key - Translation key
 * @param {Object} params - Optional parameters
 * @returns {string} Translated string
 */
function t(key, params = {}) {
    return i18n.t(key, params);
}

// Auto-initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => i18n.init());
} else {
    i18n.init();
}
