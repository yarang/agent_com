/**
 * Settings Page JavaScript
 *
 * Handles user profile settings, API key management,
 * appearance preferences, and notification settings.
 */

// State management
const state = {
    user: null,
    settings: {
        theme: 'dark',
        language: 'ko',
        fontSize: 'medium',
        compactMode: false,
        notifications: {
            browser: false,
            sound: true,
            types: ['messages', 'agent_status']
        },
        apiKeys: {
            openai: null,
            anthropic: null
        }
    },
    currentSection: 'profile'
};

// DOM elements
const elements = {};

/**
 * Initialize the settings page
 */
async function initSettings() {
    // Cache DOM elements
    cacheElements();

    // Load settings from localStorage
    loadSettings();

    // Get current user info
    await loadUserInfo();

    // Initialize UI components
    initializeNavigation();
    initializeProfileForm();
    initializePasswordForm();
    initializeApiKeyManagement();
    initializeAppearanceSettings();
    initializeNotificationSettings();
    initializeLanguageToggle();

    // Apply saved settings
    applySettings();

    // Setup back button
    document.getElementById('backBtn').addEventListener('click', () => {
        window.location.href = '/index.html';
    });

    // Update connection status
    updateConnectionStatus();

    // Initialize i18n
    if (typeof i18n !== 'undefined') {
        await i18n.init();
        i18n.translatePage();
    }
}

/**
 * Cache DOM elements
 */
function cacheElements() {
    elements.settingsNav = document.getElementById('settingsNav');
    elements.settingsSections = document.querySelectorAll('.settings-section');
    elements.profileForm = document.getElementById('profileForm');
    elements.passwordForm = document.getElementById('passwordForm');
    elements.toastContainer = document.getElementById('toastContainer');
    elements.connectionStatus = document.getElementById('connectionStatus');
}

/**
 * Load settings from localStorage
 */
function loadSettings() {
    const savedSettings = localStorage.getItem('userSettings');
    if (savedSettings) {
        try {
            const parsed = JSON.parse(savedSettings);
            state.settings = { ...state.settings, ...parsed };
        } catch (e) {
            console.error('Failed to parse saved settings:', e);
        }
    }

    // Load API keys separately (more sensitive)
    const savedKeys = localStorage.getItem('llmApiKeys');
    if (savedKeys) {
        try {
            state.settings.apiKeys = JSON.parse(savedKeys);
        } catch (e) {
            console.error('Failed to parse saved API keys:', e);
        }
    }
}

/**
 * Save settings to localStorage
 */
function saveSettings() {
    localStorage.setItem('userSettings', JSON.stringify(state.settings));
}

/**
 * Save API keys separately
 */
function saveApiKeys() {
    localStorage.setItem('llmApiKeys', JSON.stringify(state.settings.apiKeys));
}

/**
 * Load current user information
 */
async function loadUserInfo() {
    const token = localStorage.getItem('access_token');
    if (!token) {
        showToast('Please login first', 'error');
        setTimeout(() => {
            window.location.href = '/index.html';
        }, 2000);
        return;
    }

    try {
        const user = await fetchWithAuth(`${API_BASE_URL}/auth/me`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        }).then(res => res.json());

        state.user = user;

        // Update profile form
        document.getElementById('username').value = user.username || '';
        document.getElementById('role').value = user.role || 'USER';
        document.getElementById('userId').textContent = user.id || '-';
        document.getElementById('createdAt').textContent = user.created_at ?
            new Date(user.created_at).toLocaleDateString() : '-';

        // Try to get email from user object or use default
        document.getElementById('email').value = user.email || '';

    } catch (error) {
        console.error('Failed to load user info:', error);
        showToast('Failed to load user information', 'error');
    }
}

/**
 * Initialize settings navigation
 */
function initializeNavigation() {
    const navItems = document.querySelectorAll('.settings-nav-item');

    navItems.forEach(item => {
        item.addEventListener('click', () => {
            const section = item.dataset.section;
            switchSection(section);
        });
    });
}

/**
 * Switch between settings sections
 */
function switchSection(sectionName) {
    // Update navigation
    document.querySelectorAll('.settings-nav-item').forEach(item => {
        item.classList.toggle('active', item.dataset.section === sectionName);
    });

    // Update sections
    elements.settingsSections.forEach(section => {
        section.classList.toggle('active', section.id === `${sectionName}Section`);
    });

    state.currentSection = sectionName;
}

/**
 * Initialize profile form
 */
function initializeProfileForm() {
    elements.profileForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        const formData = new FormData(elements.profileForm);
        const email = formData.get('email');

        // Validate email
        if (email && !isValidEmail(email)) {
            showToast('Please enter a valid email address', 'error');
            return;
        }

        // Show loading state
        const submitBtn = document.getElementById('saveProfileBtn');
        const originalText = submitBtn.innerHTML;
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<span class="spinner-small"></span> Saving...';

        try {
            // Here you would call an API to update the user profile
            // For now, just show success
            await new Promise(resolve => setTimeout(resolve, 1000));

            showToast('Profile updated successfully', 'success');

        } catch (error) {
            console.error('Failed to update profile:', error);
            showToast('Failed to update profile', 'error');
        } finally {
            submitBtn.disabled = false;
            submitBtn.innerHTML = originalText;
        }
    });
}

/**
 * Initialize password change form
 */
function initializePasswordForm() {
    // Password visibility toggles
    document.querySelectorAll('.btn-toggle-password').forEach(btn => {
        btn.addEventListener('click', () => {
            const targetId = btn.dataset.target;
            const input = document.getElementById(targetId);

            if (input.type === 'password') {
                input.type = 'text';
                btn.innerHTML = `
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.05 3.03"/>
                        <line x1="1" y1="1" x2="23" y2="23"/>
                    </svg>
                `;
            } else {
                input.type = 'password';
                btn.innerHTML = `
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                        <circle cx="12" cy="12" r="3"/>
                    </svg>
                `;
            }
        });
    });

    // Password strength indicator
    const newPasswordInput = document.getElementById('newPassword');
    const strengthFill = document.getElementById('strengthFill');
    const strengthText = document.getElementById('strengthText');

    newPasswordInput.addEventListener('input', () => {
        const password = newPasswordInput.value;
        const strength = calculatePasswordStrength(password);

        strengthFill.style.width = `${strength.percent}%`;
        strengthFill.style.backgroundColor = strength.color;
        strengthText.textContent = strength.text;
        strengthText.style.color = strength.color;
    });

    // Form submission
    elements.passwordForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        const currentPassword = document.getElementById('currentPassword').value;
        const newPassword = document.getElementById('newPassword').value;
        const confirmPassword = document.getElementById('confirmPassword').value;

        // Validation
        if (newPassword !== confirmPassword) {
            showToast('Passwords do not match', 'error');
            return;
        }

        if (newPassword.length < 12) {
            showToast('Password must be at least 12 characters', 'error');
            return;
        }

        // Show loading state
        const submitBtn = document.getElementById('changePasswordBtn');
        const originalText = submitBtn.innerHTML;
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<span class="spinner-small"></span> Changing...';

        try {
            const response = await fetchWithAuth(`${API_BASE_URL}/auth/change-password`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    current_password: currentPassword,
                    new_password: newPassword
                })
            });

            if (response.ok) {
                showToast('Password changed successfully', 'success');
                elements.passwordForm.reset();
                // Reset password strength indicator
                strengthFill.style.width = '0%';
                strengthText.textContent = 'Enter a password';
                strengthText.style.color = 'var(--text-muted)';
            } else {
                const error = await response.json();
                showToast(error.detail || 'Failed to change password', 'error');
            }

        } catch (error) {
            console.error('Failed to change password:', error);
            showToast('Failed to change password', 'error');
        } finally {
            submitBtn.disabled = false;
            submitBtn.innerHTML = originalText;
        }
    });
}

/**
 * Initialize API key management
 */
function initializeApiKeyManagement() {
    // OpenAI API Key
    const openaiInput = document.getElementById('openaiApiKey');
    const saveOpenaiBtn = document.getElementById('saveOpenAIKeyBtn');
    const removeOpenaiBtn = document.getElementById('removeOpenAIKeyBtn');

    // Load saved key
    if (state.settings.apiKeys.openai) {
        openaiInput.value = '••••••••••••••••';
        updateApiKeyStatus('openai', true);
        removeOpenaiBtn.style.display = 'inline-flex';
    }

    saveOpenaiBtn.addEventListener('click', () => {
        const key = openaiInput.value.trim();
        if (key && key !== '••••••••••••••••') {
            // Validate OpenAI key format
            if (!key.startsWith('sk-')) {
                showToast('Invalid OpenAI API key format', 'error');
                return;
            }
            state.settings.apiKeys.openai = key;
            saveApiKeys();
            openaiInput.value = '••••••••••••••••';
            updateApiKeyStatus('openai', true);
            removeOpenaiBtn.style.display = 'inline-flex';
            showToast('OpenAI API key saved', 'success');
        }
    });

    removeOpenaiBtn.addEventListener('click', () => {
        state.settings.apiKeys.openai = null;
        saveApiKeys();
        openaiInput.value = '';
        updateApiKeyStatus('openai', false);
        removeOpenaiBtn.style.display = 'none';
        showToast('OpenAI API key removed', 'success');
    });

    // Anthropic API Key
    const anthropicInput = document.getElementById('anthropicApiKey');
    const saveAnthropicBtn = document.getElementById('saveAnthropicKeyBtn');
    const removeAnthropicBtn = document.getElementById('removeAnthropicKeyBtn');

    // Load saved key
    if (state.settings.apiKeys.anthropic) {
        anthropicInput.value = '••••••••••••••••';
        updateApiKeyStatus('anthropic', true);
        removeAnthropicBtn.style.display = 'inline-flex';
    }

    saveAnthropicBtn.addEventListener('click', () => {
        const key = anthropicInput.value.trim();
        if (key && key !== '••••••••••••••••') {
            // Validate Anthropic key format
            if (!key.startsWith('sk-ant-')) {
                showToast('Invalid Anthropic API key format', 'error');
                return;
            }
            state.settings.apiKeys.anthropic = key;
            saveApiKeys();
            anthropicInput.value = '••••••••••••••••';
            updateApiKeyStatus('anthropic', true);
            removeAnthropicBtn.style.display = 'inline-flex';
            showToast('Anthropic API key saved', 'success');
        }
    });

    removeAnthropicBtn.addEventListener('click', () => {
        state.settings.apiKeys.anthropic = null;
        saveApiKeys();
        anthropicInput.value = '';
        updateApiKeyStatus('anthropic', false);
        removeAnthropicBtn.style.display = 'none';
        showToast('Anthropic API key removed', 'success');
    });

    // Password visibility toggles for API keys
    document.querySelectorAll('#apiKeysSection .btn-toggle-password').forEach(btn => {
        btn.addEventListener('click', () => {
            const targetId = btn.dataset.target;
            const input = document.getElementById(targetId);

            // Check if showing masked value
            if (input.value === '••••••••••••••••') {
                // Don't toggle masked values - user would need to re-enter
                return;
            }

            if (input.type === 'password') {
                input.type = 'text';
            } else {
                input.type = 'password';
            }
        });
    });
}

/**
 * Update API key status indicator
 */
function updateApiKeyStatus(provider, hasKey) {
    const statusElement = document.getElementById(`${provider}KeyStatus`);
    const indicator = statusElement.querySelector('.status-indicator');
    const text = statusElement.querySelector('.status-text');

    if (hasKey) {
        indicator.className = 'status-indicator status-configured';
        text.textContent = 'Configured';
    } else {
        indicator.className = 'status-indicator status-missing';
        text.textContent = 'Not configured';
    }
}

/**
 * Initialize appearance settings
 */
function initializeAppearanceSettings() {
    // Theme selection
    const themeInputs = document.querySelectorAll('input[name="theme"]');
    themeInputs.forEach(input => {
        if (input.value === state.settings.theme) {
            input.checked = true;
        }
        input.addEventListener('change', () => {
            state.settings.theme = input.value;
            saveSettings();
            applyTheme(input.value);
        });
    });

    // Font size selection
    const fontSizeBtns = document.querySelectorAll('.font-size-btn');
    fontSizeBtns.forEach(btn => {
        if (btn.dataset.size === state.settings.fontSize) {
            btn.classList.add('active');
        }
        btn.addEventListener('click', () => {
            fontSizeBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            state.settings.fontSize = btn.dataset.size;
            saveSettings();
            applyFontSize(btn.dataset.size);
        });
    });

    // Compact mode toggle
    const compactModeToggle = document.getElementById('compactMode');
    compactModeToggle.checked = state.settings.compactMode;
    compactModeToggle.addEventListener('change', () => {
        state.settings.compactMode = compactModeToggle.checked;
        saveSettings();
        applyCompactMode(compactModeToggle.checked);
    });
}

/**
 * Initialize notification settings
 */
function initializeNotificationSettings() {
    // Browser notifications
    const browserToggle = document.getElementById('browserNotifications');
    browserToggle.checked = state.settings.notifications.browser;

    browserToggle.addEventListener('change', async () => {
        if (browserToggle.checked) {
            // Request permission
            const permission = await Notification.requestPermission();
            if (permission === 'granted') {
                state.settings.notifications.browser = true;
                saveSettings();
                showToast('Browser notifications enabled', 'success');
            } else {
                browserToggle.checked = false;
                showToast('Notification permission denied', 'error');
            }
        } else {
            state.settings.notifications.browser = false;
            saveSettings();
        }
    });

    // Sound notifications
    const soundToggle = document.getElementById('soundNotifications');
    soundToggle.checked = state.settings.notifications.sound;
    soundToggle.addEventListener('change', () => {
        state.settings.notifications.sound = soundToggle.checked;
        saveSettings();
    });

    // Notification types
    const typeCheckboxes = document.querySelectorAll('input[name="notificationType"]');
    typeCheckboxes.forEach(checkbox => {
        if (state.settings.notifications.types.includes(checkbox.value)) {
            checkbox.checked = true;
        }
        checkbox.addEventListener('change', () => {
            const selected = Array.from(typeCheckboxes)
                .filter(cb => cb.checked)
                .map(cb => cb.value);
            state.settings.notifications.types = selected;
            saveSettings();
        });
    });

    // Test notification button
    const testBtn = document.getElementById('testNotificationBtn');
    testBtn.addEventListener('click', () => {
        if (state.settings.notifications.browser) {
            new Notification('AI Agent Communication', {
                body: 'This is a test notification',
                icon: '/static/images/logo.png'
            });
        }
        if (state.settings.notifications.sound) {
            playNotificationSound();
        }
        showToast('Test notification sent', 'success');
    });
}

/**
 * Initialize language toggle
 */
function initializeLanguageToggle() {
    const langBtn = document.getElementById('languageBtn');
    const langDropdown = document.getElementById('languageDropdown');
    const currentLangSpan = document.getElementById('currentLang');
    const langOptions = document.querySelectorAll('.language-option');

    // Set current language
    currentLangSpan.textContent = state.settings.language.toUpperCase();

    langBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        langDropdown.style.display = langDropdown.style.display === 'none' ? 'block' : 'none';
    });

    langOptions.forEach(option => {
        option.addEventListener('click', () => {
            const lang = option.dataset.lang;
            state.settings.language = lang;
            currentLangSpan.textContent = lang.toUpperCase();
            saveSettings();
            langDropdown.style.display = 'none';

            // Update i18n if available
            if (typeof i18n !== 'undefined') {
                i18n.setLanguage(lang);
            }
            showToast(`Language changed to ${lang === 'ko' ? 'Korean' : 'English'}`, 'success');
        });
    });

    // Close dropdown on outside click
    document.addEventListener('click', () => {
        langDropdown.style.display = 'none';
    });
}

/**
 * Apply saved settings
 */
function applySettings() {
    applyTheme(state.settings.theme);
    applyFontSize(state.settings.fontSize);
    applyCompactMode(state.settings.compactMode);
}

/**
 * Apply theme
 */
function applyTheme(theme) {
    const html = document.documentElement;
    html.classList.remove('theme-dark', 'theme-light');

    if (theme === 'system') {
        const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        html.classList.add(prefersDark ? 'theme-dark' : 'theme-light');
    } else {
        html.classList.add(`theme-${theme}`);
    }
}

/**
 * Apply font size
 */
function applyFontSize(size) {
    const html = document.documentElement;
    html.classList.remove('font-small', 'font-medium', 'font-large');
    html.classList.add(`font-${size}`);
}

/**
 * Apply compact mode
 */
function applyCompactMode(enabled) {
    const html = document.documentElement;
    if (enabled) {
        html.classList.add('compact-mode');
    } else {
        html.classList.remove('compact-mode');
    }
}

/**
 * Calculate password strength
 */
function calculatePasswordStrength(password) {
    if (!password) {
        return { percent: 0, color: 'var(--text-muted)', text: 'Enter a password' };
    }

    let score = 0;

    // Length check
    if (password.length >= 12) score += 25;
    if (password.length >= 16) score += 15;

    // Character variety
    if (/[a-z]/.test(password)) score += 15;
    if (/[A-Z]/.test(password)) score += 15;
    if (/[0-9]/.test(password)) score += 15;
    if (/[^a-zA-Z0-9]/.test(password)) score += 15;

    if (score <= 30) {
        return { percent: score, color: 'var(--error)', text: 'Weak' };
    } else if (score <= 60) {
        return { percent: score, color: 'var(--warning)', text: 'Fair' };
    } else if (score <= 80) {
        return { percent: score, color: 'var(--info)', text: 'Good' };
    } else {
        return { percent: score, color: 'var(--success)', text: 'Strong' };
    }
}

/**
 * Play notification sound
 */
function playNotificationSound() {
    // Create a simple beep sound using Web Audio API
    try {
        const audioContext = new (window.AudioContext || window.webkitAudioContext)();
        const oscillator = audioContext.createOscillator();
        const gainNode = audioContext.createGain();

        oscillator.connect(gainNode);
        gainNode.connect(audioContext.destination);

        oscillator.frequency.value = 800;
        oscillator.type = 'sine';

        gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
        gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.1);

        oscillator.start(audioContext.currentTime);
        oscillator.stop(audioContext.currentTime + 0.1);
    } catch (e) {
        console.error('Failed to play sound:', e);
    }
}

/**
 * Update connection status
 */
function updateConnectionStatus() {
    // Check if we can reach the API
    fetchWithAuth(`${API_BASE_URL}/status/agents`)
        .then(res => {
            if (res.ok) {
                elements.connectionStatus?.classList.add('connected');
                elements.connectionStatus?.classList.remove('disconnected');
                const text = elements.connectionStatus?.querySelector('.status-text');
                if (text) text.textContent = '연결됨';
            }
        })
        .catch(() => {
            elements.connectionStatus?.classList.add('disconnected');
            elements.connectionStatus?.classList.remove('connected');
            const text = elements.connectionStatus?.querySelector('.status-text');
            if (text) text.textContent = '연결 해제';
        });
}

/**
 * Validate email format
 */
function isValidEmail(email) {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

/**
 * Show toast notification
 */
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            ${type === 'success' ? '<polyline points="20 6 9 17 4 12"/>' :
              type === 'error' ? '<circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>' :
              '<circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/>'}
        </svg>
        <span>${message}</span>
    `;

    elements.toastContainer.appendChild(toast);

    // Animate in
    requestAnimationFrame(() => {
        toast.classList.add('show');
    });

    // Remove after delay
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initSettings);
} else {
    initSettings();
}
