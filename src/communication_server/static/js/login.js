/**
 * Login Page JavaScript
 *
 * Handles login and signup form submissions with validation
 * and API integration for the AI Agent Communication System.
 */

// Wait for DOM to be ready
document.addEventListener('DOMContentLoaded', function() {
    // DOM Elements
    const loginForm = document.getElementById('loginForm');
    const signupForm = document.getElementById('signupForm');
    const loginBtn = document.getElementById('loginBtn');
    const signupBtn = document.getElementById('signupBtn');
    const loginError = document.getElementById('loginError');
    const loginErrorText = document.getElementById('loginErrorText');
    const signupError = document.getElementById('signupError');
    const signupErrorText = document.getElementById('signupErrorText');
    const loginSuccess = document.getElementById('loginSuccess');
    const loginSuccessText = document.getElementById('loginSuccessText');
    const loginFooter = document.getElementById('loginFooter');

    const loginUsername = document.getElementById('loginUsername');
    const loginPassword = document.getElementById('loginPassword');
    const signupUsername = document.getElementById('signupUsername');
    const signupEmail = document.getElementById('signupEmail');
    const signupPassword = document.getElementById('signupPassword');
    const signupConfirmPassword = document.getElementById('signupConfirmPassword');
    const rememberMeCheckbox = document.getElementById('rememberMe');

    // Tab switching
    const tabs = document.querySelectorAll('.login-tab');
    tabs.forEach(tab => {
        tab.addEventListener('click', function() {
            const targetTab = this.dataset.tab;

            // Update tab active state
            tabs.forEach(t => t.classList.remove('active'));
            this.classList.add('active');

            // Show/hide forms
            if (targetTab === 'login') {
                loginForm.classList.add('active');
                signupForm.classList.remove('active');
            } else {
                loginForm.classList.remove('active');
                signupForm.classList.add('active');
            }

            // Clear any errors when switching tabs
            hideError(loginError);
            hideError(signupError);

            // Reset success state
            resetSuccessState();
        });
    });

    // Password visibility toggles
    const toggleLoginPassword = document.getElementById('toggleLoginPassword');
    const toggleSignupPassword = document.getElementById('toggleSignupPassword');
    const toggleSignupConfirmPassword = document.getElementById('toggleSignupConfirmPassword');

    if (toggleLoginPassword) {
        setupPasswordToggle(toggleLoginPassword, loginPassword);
    }

    if (toggleSignupPassword) {
        setupPasswordToggle(toggleSignupPassword, signupPassword);
    }

    // Add confirm password toggle dynamically if button exists
    const confirmPasswordToggle = signupConfirmPassword?.parentElement?.querySelector('.password-toggle-btn');
    if (confirmPasswordToggle) {
        setupPasswordToggle(confirmPasswordToggle, signupConfirmPassword);
    }

    // Form validation
    loginForm.addEventListener('submit', handleLogin);
    signupForm.addEventListener('submit', handleSignup);

    // Input validation on blur
    setupInputValidation(loginUsername, validateUsername);
    setupInputValidation(loginPassword, validatePassword);
    setupInputValidation(signupUsername, validateSignupUsername);
    setupInputValidation(signupEmail, validateEmail);
    setupInputValidation(signupPassword, validatePassword);
    setupInputValidation(signupConfirmPassword, (value) => validateConfirmPassword(value, signupPassword.value));

    /**
     * Handle login form submission
     */
    async function handleLogin(event) {
        event.preventDefault();
        hideError(loginError);

        const username = loginUsername.value.trim();
        const password = loginPassword.value;
        const rememberMe = rememberMeCheckbox.checked;

        // Validate inputs
        const usernameError = validateUsername(username);
        if (usernameError) {
            showError(loginError, loginErrorText, usernameError);
            return;
        }

        const passwordError = validatePassword(password);
        if (passwordError) {
            showError(loginError, loginErrorText, passwordError);
            return;
        }

        // Set loading state
        setButtonLoading(loginBtn, true);

        try {
            // Call API login function
            const response = await window.login(username, password);

            // Check if response contains access_token
            if (response && response.access_token) {
                // Store tokens
                localStorage.setItem('access_token', response.access_token);
                if (response.refresh_token) {
                    localStorage.setItem('refresh_token', response.refresh_token);
                }

                // Store user info if available
                if (response.user) {
                    localStorage.setItem('user', JSON.stringify(response.user));
                }

                // Store remember me preference
                if (rememberMe) {
                    localStorage.setItem('remember_me', 'true');
                    localStorage.setItem('last_username', username);
                } else {
                    localStorage.removeItem('remember_me');
                    localStorage.removeItem('last_username');
                }

                // Update auth token in API module
                if (window.setAuthToken) {
                    window.setAuthToken(response.access_token);
                }

                // Show success state
                showSuccessState('Login successful! Redirecting...');

                // Get return URL or default to dashboard
                const returnUrl = sessionStorage.getItem('auth_return_url') || '/index.html';

                // Clear return URL
                sessionStorage.removeItem('auth_return_url');

                // Redirect after delay
                setTimeout(() => {
                    window.location.href = returnUrl;
                }, 1000);
            } else {
                showError(loginError, loginErrorText, 'Invalid response from server. Please try again.');
            }
        } catch (error) {
            console.error('Login error:', error);
            handleApiError(error, loginError, loginErrorText, 'Login failed. Please check your credentials and try again.');
        } finally {
            setButtonLoading(loginBtn, false);
        }
    }

    /**
     * Handle signup form submission
     */
    async function handleSignup(event) {
        event.preventDefault();
        hideError(signupError);

        const username = signupUsername.value.trim();
        const email = signupEmail.value.trim();
        const password = signupPassword.value;
        const confirmPassword = signupConfirmPassword.value;

        // Validate inputs
        const usernameError = validateSignupUsername(username);
        if (usernameError) {
            showError(signupError, signupErrorText, usernameError);
            return;
        }

        const emailError = validateEmail(email);
        if (emailError) {
            showError(signupError, signupErrorText, emailError);
            return;
        }

        const passwordError = validatePassword(password);
        if (passwordError) {
            showError(signupError, signupErrorText, passwordError);
            return;
        }

        const confirmPasswordError = validateConfirmPassword(confirmPassword, password);
        if (confirmPasswordError) {
            showError(signupError, signupErrorText, confirmPasswordError);
            return;
        }

        // Set loading state
        setButtonLoading(signupBtn, true);

        try {
            // Call signup API (this needs to be implemented in api.js)
            const response = await signupApiCall(username, email, password);

            // Show success state
            showSuccessState('Account created successfully! Redirecting to login...');

            // Switch to login tab and pre-fill username
            setTimeout(() => {
                resetSuccessState();
                document.querySelector('[data-tab="login"]').click();
                loginUsername.value = username;
            }, 1500);
        } catch (error) {
            console.error('Signup error:', error);
            handleApiError(error, signupError, signupErrorText, 'Signup failed. Please try again.');
        } finally {
            setButtonLoading(signupBtn, false);
        }
    }

    /**
     * API call for signup (extends api.js functionality)
     */
    async function signupApiCall(username, email, password) {
        try {
            const response = await fetch(`${window.API_BASE_URL}/auth/signup`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ username, email, password }),
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.detail || data.message || 'Signup failed');
            }

            return data;
        } catch (error) {
            console.error('Signup API error:', error);
            throw error;
        }
    }

    /**
     * Handle API errors with user-friendly messages
     */
    function handleApiError(error, errorElement, errorTextElement, defaultMessage) {
        let errorMessage = defaultMessage;

        if (error.message) {
            errorMessage = error.message;
        } else if (error.detail) {
            errorMessage = error.detail;
        }

        // Common error message mapping
        const errorMessages = {
            'Invalid credentials': 'Invalid username or password',
            'User not found': 'Invalid username or password',
            'Incorrect password': 'Invalid username or password',
            'Username already exists': 'This username is already taken',
            'Email already registered': 'This email is already registered',
            'Password too weak': 'Password must be at least 12 characters',
            'Invalid email': 'Please enter a valid email address',
        };

        for (const [key, value] of Object.entries(errorMessages)) {
            if (errorMessage.includes(key)) {
                errorMessage = value;
                break;
            }
        }

        showError(errorElement, errorTextElement, errorMessage);
    }

    /**
     * Validation functions
     */
    function validateUsername(value) {
        if (!value || value.trim() === '') {
            return 'Please enter your username or email';
        }
        if (value.length < 3) {
            return 'Username must be at least 3 characters';
        }
        return null;
    }

    function validateSignupUsername(value) {
        if (!value || value.trim() === '') {
            return 'Please enter a username';
        }
        if (value.length < 3) {
            return 'Username must be at least 3 characters';
        }
        if (value.length > 30) {
            return 'Username must be less than 30 characters';
        }
        if (!/^[a-zA-Z0-9_-]+$/.test(value)) {
            return 'Username can only contain letters, numbers, underscores, and hyphens';
        }
        return null;
    }

    function validateEmail(value) {
        if (!value || value.trim() === '') {
            return 'Please enter your email';
        }
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!emailRegex.test(value)) {
            return 'Please enter a valid email address';
        }
        return null;
    }

    function validatePassword(value) {
        if (!value || value === '') {
            return 'Please enter your password';
        }
        if (value.length < 12) {
            return 'Password must be at least 12 characters';
        }
        return null;
    }

    function validateConfirmPassword(value, password) {
        if (!value || value === '') {
            return 'Please confirm your password';
        }
        if (value !== password) {
            return 'Passwords do not match';
        }
        return null;
    }

    /**
     * Setup input validation on blur
     */
    function setupInputValidation(inputElement, validationFn) {
        if (!inputElement) return;

        inputElement.addEventListener('blur', function() {
            const error = validationFn(this.value);
            if (error) {
                this.classList.add('error');
            } else {
                this.classList.remove('error');
            }
        });

        inputElement.addEventListener('input', function() {
            this.classList.remove('error');
        });
    }

    /**
     * Setup password visibility toggle
     */
    function setupPasswordToggle(button, input) {
        button.addEventListener('click', function() {
            const isPassword = input.type === 'password';
            input.type = isPassword ? 'text' : 'password';

            // Update icon
            if (isPassword) {
                // Show eye-off icon
                this.innerHTML = `
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/>
                        <line x1="1" y1="1" x2="23" y2="23"/>
                    </svg>
                `;
                this.setAttribute('title', 'Hide password');
            } else {
                // Show eye icon
                this.innerHTML = `
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                        <circle cx="12" cy="12" r="3"/>
                    </svg>
                `;
                this.setAttribute('title', 'Show password');
            }
        });
    }

    /**
     * UI helper functions
     */
    function showError(errorElement, textElement, message) {
        errorElement.classList.remove('hidden');
        textElement.textContent = message;
    }

    function hideError(errorElement) {
        errorElement.classList.add('hidden');
    }

    function setButtonLoading(button, isLoading) {
        if (isLoading) {
            button.classList.add('loading');
            button.disabled = true;
        } else {
            button.classList.remove('loading');
            button.disabled = false;
        }
    }

    function showSuccessState(message) {
        // Hide forms
        loginForm.classList.remove('active');
        signupForm.classList.remove('active');

        // Hide footer
        loginFooter.style.display = 'none';

        // Hide tabs
        document.querySelector('.login-tabs').style.display = 'none';

        // Show success
        loginSuccess.classList.add('active');
        loginSuccessText.textContent = message;
    }

    function resetSuccessState() {
        loginSuccess.classList.remove('active');
        loginFooter.style.display = '';
        document.querySelector('.login-tabs').style.display = '';
    }

    // Check for existing session on page load
    checkExistingSession();

    // Load remembered username
    loadRememberedUsername();
});

/**
 * Check if user is already logged in
 */
function checkExistingSession() {
    const accessToken = localStorage.getItem('access_token');
    if (accessToken) {
        // User is already logged in, redirect to dashboard
        window.location.href = '/index.html';
    }
}

/**
 * Load remembered username
 */
function loadRememberedUsername() {
    const rememberMe = localStorage.getItem('remember_me');
    const lastUsername = localStorage.getItem('last_username');

    if (rememberMe === 'true' && lastUsername) {
        const loginUsername = document.getElementById('loginUsername');
        const rememberMeCheckbox = document.getElementById('rememberMe');
        if (loginUsername && rememberMeCheckbox) {
            loginUsername.value = lastUsername;
            rememberMeCheckbox.checked = true;
        }
    }
}
