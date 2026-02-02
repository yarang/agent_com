/**
 * API Client for AI Agent Communication System Status Board
 *
 * Provides functions for fetching data from the REST API
 * and managing WebSocket connections for real-time updates.
 * Supports both HTTP/HTTPS and WS/WSS protocols with auto-detection.
 */

// Detect current protocol
const isHttps = window.location.protocol === 'https:';

// API Configuration - always use port 8000
const API_BASE_URL = `${window.location.protocol}//${window.location.hostname}:8000/api/v1`;

// WebSocket URL with protocol detection - always use port 8000
const WS_PROTOCOL = isHttps ? 'wss' : 'ws';
const WS_URL = `${WS_PROTOCOL}://${window.location.hostname}:8000/ws/status`;

// WebSocket connection
let ws = null;
let reconnectTimeout = null;
let messageHandlers = [];
let authToken = null; // Store authentication token

/**
 * Set authentication token for WebSocket connections
 * @param {string} token - JWT access token or API token
 */
function setAuthToken(token) {
    authToken = token;
    // If WebSocket is connected, reconnect with new token
    if (ws && ws.readyState === WebSocket.OPEN) {
        disconnectWebSocket();
    }
}

/**
 * Get WebSocket URL with token
 * @param {string} baseUrl - Base WebSocket URL
 * @returns {string} WebSocket URL with token parameter
 */
function getWsUrlWithToken(baseUrl) {
    if (authToken) {
        return `${baseUrl}?token=${encodeURIComponent(authToken)}`;
    }
    return baseUrl;
}

/**
 * Fetch with authentication headers
 * @param {string} url - API endpoint URL
 * @param {Object} options - Fetch options
 * @returns {Promise<Response>} Fetch response
 */
async function fetchWithAuth(url, options = {}) {
    const headers = {
        'Content-Type': 'application/json',
        ...options.headers,
    };

    // Add authorization header if token is available
    if (authToken && !headers['Authorization']) {
        headers['Authorization'] = `Bearer ${authToken}`;
    }

    return fetch(url, {
        ...options,
        headers,
        credentials: 'include', // Include cookies for CORS
    });
}

/**
 * Fetch all agents from the API
 * @param {string} [projectId] - Optional project ID to filter agents
 * @returns {Promise<Object>} Response with agents array
 */
async function fetchAgents(projectId = null) {
    try {
        let url = `${API_BASE_URL}/status/agents`;
        if (projectId) {
            url += `?project_id=${encodeURIComponent(projectId)}`;
        }
        const response = await fetchWithAuth(url);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error('Error fetching agents:', error);
        throw error;
    }
}

/**
 * Fetch detailed information about a specific agent
 * @param {string} displayId - The agent's display ID (e.g., @FrontendExpert-ef123456)
 * @returns {Promise<Object>} Response with agent details and statistics
 */
async function fetchAgentInfo(displayId) {
    try {
        const response = await fetchWithAuth(`${API_BASE_URL}/status/agents/${encodeURIComponent(displayId)}`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error('Error fetching agent info:', error);
        throw error;
    }
}

/**
 * Fetch all projects with agent counts
 * @returns {Promise<Object>} Response with projects array
 */
async function fetchProjects() {
    try {
        const response = await fetchWithAuth(`${API_BASE_URL}/projects`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error('Error fetching projects:', error);
        throw error;
    }
}

/**
 * Fetch agents for a specific project
 * @param {string} projectId - Project ID
 * @returns {Promise<Object>} Response with agents array
 */
async function fetchProjectAgents(projectId) {
    try {
        const response = await fetchWithAuth(`${API_BASE_URL}/projects/${encodeURIComponent(projectId)}/agents`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error('Error fetching project agents:', error);
        throw error;
    }
}

/**
 * Fetch system-wide statistics
 * @returns {Promise<Object>} Response with system statistics
 */
async function fetchStatistics() {
    try {
        const response = await fetchWithAuth(`${API_BASE_URL}/status/statistics`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error('Error fetching statistics:', error);
        throw error;
    }
}

/**
 * Fetch activity patterns
 * @param {string} [agentId] - Optional agent ID to filter by
 * @returns {Promise<Object>} Response with activity patterns
 */
async function fetchActivity(agentId = null) {
    try {
        const url = agentId
            ? `${API_BASE_URL}/status/activity?agent_id=${encodeURIComponent(agentId)}`
            : `${API_BASE_URL}/status/activity`;

        const response = await fetchWithAuth(url);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error('Error fetching activity:', error);
        throw error;
    }
}

/**
 * Fetch message timeline
 * @param {number} [limit=100] - Maximum number of events to return
 * @returns {Promise<Array>} Response with message events
 */
async function fetchTimeline(limit = 100) {
    try {
        const response = await fetchWithAuth(`${API_BASE_URL}/status/timeline?limit=${limit}`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error('Error fetching timeline:', error);
        throw error;
    }
}

/**
 * Update agent status
 * @param {string} displayId - The agent's display ID
 * @param {string} status - New status (online, offline, active, idle, error)
 * @param {string} [currentMeeting] - Optional current meeting UUID
 * @returns {Promise<Object>} Response with updated agent info
 */
async function updateAgentStatus(displayId, status, currentMeeting = null) {
    try {
        const params = new URLSearchParams({ status });
        if (currentMeeting) {
            params.append('current_meeting', currentMeeting);
        }

        const response = await fetchWithAuth(
            `${API_BASE_URL}/status/agents/${encodeURIComponent(displayId)}/status?${params}`,
            { method: 'PUT' }
        );

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error('Error updating agent status:', error);
        throw error;
    }
}

/**
 * Register a new agent
 * @param {Object} registration - Agent registration data
 * @param {string} registration.full_id - Full UUID of the agent
 * @param {string} registration.nickname - Agent nickname
 * @param {Array<string>} registration.capabilities - List of agent capabilities
 * @returns {Promise<Object>} Response with registered agent info
 */
async function registerAgent(registration) {
    try {
        const response = await fetchWithAuth(`${API_BASE_URL}/status/agents/register`, {
            method: 'POST',
            body: JSON.stringify(registration),
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error('Error registering agent:', error);
        throw error;
    }
}

/**
 * Unregister an agent
 * @param {string} displayId - The agent's display ID
 * @returns {Promise<Object>} Response with confirmation
 */
async function unregisterAgent(displayId) {
    try {
        const response = await fetchWithAuth(
            `${API_BASE_URL}/status/agents/${encodeURIComponent(displayId)}`,
            { method: 'DELETE' }
        );

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error('Error unregistering agent:', error);
        throw error;
    }
}

/**
 * Send heartbeat for an agent
 * @param {string} displayId - The agent's display ID
 * @returns {Promise<Object>} Response with heartbeat confirmation
 */
async function sendHeartbeat(displayId) {
    try {
        const response = await fetchWithAuth(
            `${API_BASE_URL}/status/agents/${encodeURIComponent(displayId)}/heartbeat`,
            { method: 'POST' }
        );

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error('Error sending heartbeat:', error);
        throw error;
    }
}

/**
 * Connect to WebSocket for real-time updates
 * Automatically uses WSS for HTTPS and WS for HTTP
 * @param {Function} onMessage - Callback function for incoming messages
 * @param {Function} onConnect - Callback function when connection is established
 * @param {Function} onDisconnect - Callback function when connection is closed
 * @param {string} [token] - Optional authentication token (uses global authToken if not provided)
 * @returns {WebSocket} The WebSocket connection
 */
function connectWebSocket(onMessage, onConnect, onDisconnect, token) {
    if (ws && ws.readyState === WebSocket.OPEN) {
        console.warn('WebSocket already connected');
        return ws;
    }

    // Use provided token or global auth token
    const connectionToken = token || authToken;
    const wsUrl = getWsUrlWithToken(WS_URL);

    console.log(`Connecting to WebSocket: ${wsUrl.replace(/token=.+$/, 'token=***')}`);

    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
        console.log('WebSocket connected');
        updateConnectionStatus('connected');
        if (onConnect) onConnect();
    };

    ws.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            console.log('WebSocket message received:', data);

            // Handle different message types
            handleMessage(data, onMessage);
        } catch (error) {
            console.error('Error parsing WebSocket message:', error);
        }
    };

    ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        updateConnectionStatus('error');
    };

    ws.onclose = (event) => {
        console.log('WebSocket closed:', event.code, event.reason);
        updateConnectionStatus('disconnected');

        if (onDisconnect) onDisconnect();

        // Attempt to reconnect after 5 seconds if not a policy violation
        // Policy violation (1008) means authentication failed - don't auto-reconnect
        if (event.code !== 1008) {
            scheduleReconnect(onMessage, onConnect, onDisconnect);
        }
    };

    return ws;
}

/**
 * Schedule reconnection attempt
 */
function scheduleReconnect(onMessage, onConnect, onDisconnect) {
    if (reconnectTimeout) {
        clearTimeout(reconnectTimeout);
    }

    reconnectTimeout = setTimeout(() => {
        console.log('Attempting to reconnect WebSocket...');
        updateConnectionStatus('connecting');
        connectWebSocket(onMessage, onConnect, onDisconnect);
    }, 5000);
}

/**
 * Disconnect WebSocket
 */
function disconnectWebSocket() {
    if (reconnectTimeout) {
        clearTimeout(reconnectTimeout);
        reconnectTimeout = null;
    }

    if (ws) {
        ws.close();
        ws = null;
    }

    updateConnectionStatus('disconnected');
}

/**
 * Handle incoming WebSocket message
 */
function handleMessage(data, callback) {
    const { type, timestamp } = data;

    // Call the callback with the full message data
    if (callback) {
        callback(data);
    }

    // Also dispatch to registered handlers
    messageHandlers.forEach(handler => handler(data));
}

/**
 * Register a message handler
 * @param {Function} handler - Handler function
 */
function onWebSocketMessage(handler) {
    messageHandlers.push(handler);
}

/**
 * Remove a message handler
 * @param {Function} handler - Handler function to remove
 */
function offWebSocketMessage(handler) {
    const index = messageHandlers.indexOf(handler);
    if (index > -1) {
        messageHandlers.splice(index, 1);
    }
}

/**
 * Send a message through WebSocket
 * @param {Object} message - Message object to send
 */
function sendWebSocketMessage(message) {
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify(message));
    } else {
        console.warn('WebSocket not connected, cannot send message');
    }
}

/**
 * Send ping through WebSocket
 */
function pingWebSocket() {
    sendWebSocketMessage({ type: 'ping' });
}

/**
 * Update connection status in the UI
 */
function updateConnectionStatus(status) {
    const badge = document.getElementById('connectionStatus');
    if (!badge) return;

    // Remove all status classes
    badge.classList.remove('connected', 'connecting', 'disconnected', 'error');

    // Add current status class
    badge.classList.add(status);

    // Update status text using i18n if available
    const text = badge.querySelector('.status-text');
    if (!text) return;

    // Use i18n if available, otherwise fallback to hardcoded labels
    if (typeof i18n !== 'undefined' && i18n.t) {
        const key = `connection.${status}`;
        text.textContent = i18n.t(key);
        // Update data-i18n attribute for dynamic language switching
        text.setAttribute('data-i18n', key);
    } else {
        // Fallback for when i18n is not loaded yet
        const statusLabels = {
            connected: '연결됨',
            connecting: '연결 중...',
            disconnected: '연결 해제',
            error: '연결 오류',
        };
        text.textContent = statusLabels[status] || status;
    }
}

/**
 * Format timestamp for display
 * @param {string} isoString - ISO format timestamp
 * @returns {string} Formatted timestamp
 */
function formatTimestamp(isoString) {
    const date = new Date(isoString);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);

    if (diffMins < 1) {
        return 'Just now';
    } else if (diffMins < 60) {
        return `${diffMins}m ago`;
    } else if (diffMins < 1440) {
        const hours = Math.floor(diffMins / 60);
        return `${hours}h ago`;
    } else {
        const days = Math.floor(diffMins / 1440);
        return `${days}d ago`;
    }
}

/**
 * Format timestamp for timeline display
 * @param {string} isoString - ISO format timestamp
 * @returns {string} Formatted timestamp
 */
function formatTimelineTimestamp(isoString) {
    const date = new Date(isoString);
    const hours = date.getHours().toString().padStart(2, '0');
    const minutes = date.getMinutes().toString().padStart(2, '0');
    const seconds = date.getSeconds().toString().padStart(2, '0');
    return `${hours}:${minutes}:${seconds}`;
}

/**
 * Format full date for display
 * @param {string} isoString - ISO format timestamp
 * @returns {string} Formatted date and time
 */
function formatFullDate(isoString) {
    const date = new Date(isoString);
    return date.toLocaleString();
}

/**
 * Login to get JWT token
 * @param {string} username - Admin username
 * @param {string} password - Admin password
 * @returns {Promise<Object>} Response with access token
 */
async function login(username, password) {
    try {
        const response = await fetchWithAuth(`${API_BASE_URL}/auth/login`, {
            method: 'POST',
            body: JSON.stringify({ username, password }),
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error('Error logging in:', error);
        throw error;
    }
}

/**
 * Refresh JWT token
 * @param {string} refreshToken - Refresh token
 * @returns {Promise<Object>} Response with new access token
 */
async function refreshToken(refreshToken) {
    try {
        const response = await fetchWithAuth(`${API_BASE_URL}/auth/refresh`, {
            method: 'POST',
            body: JSON.stringify({ refresh_token: refreshToken }),
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error('Error refreshing token:', error);
        throw error;
    }
}

/**
 * Create agent token (register new agent)
 * @param {string} nickname - Agent nickname
 * @returns {Promise<Object>} Response with token
 */
async function createAgentToken(nickname) {
    try {
        const response = await fetchWithAuth(`${API_BASE_URL}/auth/token`, {
            method: 'POST',
            body: JSON.stringify({ nickname }),
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error('Error creating agent token:', error);
        throw error;
    }
}

/**
 * Fetch all registered agents (management view)
 * @returns {Promise<Object>} Response with agents array
 */
async function fetchRegisteredAgents() {
    try {
        const response = await fetchWithAuth(`${API_BASE_URL}/status/agents`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error('Error fetching registered agents:', error);
        throw error;
    }
}

/**
 * Delete an agent by ID
 * @param {string} agentId - Agent ID to delete
 * @returns {Promise<Object>} Response with confirmation
 */
async function deleteAgent(agentId) {
    try {
        const response = await fetchWithAuth(`${API_BASE_URL}/status/agents/${agentId}`, {
            method: 'DELETE',
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error('Error deleting agent:', error);
        throw error;
    }
}

/**
 * Fetch supported languages from the API
 * @returns {Promise<Object>} Response with languages array and default language
 */
async function fetchLanguages() {
    try {
        const response = await fetchWithAuth(`${API_BASE_URL}/i18n/languages`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error('Error fetching languages:', error);
        throw error;
    }
}

/**
 * Fetch translations for a specific language
 * @param {string} language - Language code (ko, en)
 * @returns {Promise<Object>} Response with translation dictionary
 */
async function fetchTranslations(language) {
    try {
        const response = await fetchWithAuth(`${API_BASE_URL}/i18n/${language}`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error('Error fetching translations:', error);
        throw error;
    }
}

/**
 * Copy text to clipboard
 * @param {string} text - Text to copy
 * @returns {Promise<boolean>} Success status
 */
async function copyToClipboard(text) {
    try {
        if (navigator.clipboard && navigator.clipboard.writeText) {
            await navigator.clipboard.writeText(text);
            return true;
        } else {
            // Fallback for older browsers
            const textArea = document.createElement('textarea');
            textArea.value = text;
            textArea.style.position = 'fixed';
            textArea.style.left = '-999999px';
            document.body.appendChild(textArea);
            textArea.select();
            try {
                document.execCommand('copy');
                return true;
            } catch (err) {
                console.error('Fallback copy failed:', err);
                return false;
            } finally {
                document.body.removeChild(textArea);
            }
        }
    } catch (error) {
        console.error('Error copying to clipboard:', error);
        return false;
    }
}

/**
 * Get connection information for display
 * @returns {Object} Connection information
 */
function getConnectionInfo() {
    return {
        isHttps,
        protocol: window.location.protocol,
        hostname: window.location.hostname,
        apiUrl: API_BASE_URL,
        wsUrl: WS_URL,
        wsProtocol: WS_PROTOCOL,
    };
}

/**
 * Fetch messages with optional filtering
 * @param {Object} options - Query options
 * @param {string} [options.project_id] - Filter by project ID
 * @param {number} [options.limit=50] - Maximum results
 * @param {number} [options.offset=0] - Pagination offset
 * @param {string} [options.search] - Search in content
 * @returns {Promise<Array>} Response with messages array
 */
async function fetchMessages(options = {}) {
    const { project_id = null, limit = 50, offset = 0, search = null } = options;

    const params = new URLSearchParams({ limit, offset });
    if (project_id) params.append('project_id', project_id);
    if (search) params.append('search', search);

    try {
        const response = await fetchWithAuth(`${API_BASE_URL}/messages?${params}`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error('Error fetching messages:', error);
        throw error;
    }
}

/**
 * Fetch message detail by ID
 * @param {string} messageId - Message UUID
 * @returns {Promise<Object>} Response with message details
 */
async function fetchMessageDetail(messageId) {
    try {
        const response = await fetchWithAuth(`${API_BASE_URL}/messages/${encodeURIComponent(messageId)}`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error('Error fetching message detail:', error);
        throw error;
    }
}

// ==================== Project Management API ====================

/**
 * Create a new project
 * @param {Object} projectData - Project data
 * @param {string} projectData.project_id - Project ID (snake_case)
 * @param {string} projectData.name - Project name
 * @param {string} [projectData.description] - Project description
 * @param {string[]} [projectData.tags] - Project tags
 * @returns {Promise<Object>} Response with created project and API keys
 */
async function createProject(projectData) {
    try {
        const response = await fetchWithAuth(`${API_BASE_URL}/projects`, {
            method: 'POST',
            body: JSON.stringify(projectData),
        });
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error('Error creating project:', error);
        throw error;
    }
}

/**
 * Get project details
 * @param {string} projectId - Project ID
 * @returns {Promise<Object>} Response with project details
 */
async function getProject(projectId) {
    try {
        const response = await fetchWithAuth(`${API_BASE_URL}/projects/${encodeURIComponent(projectId)}`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error('Error getting project:', error);
        throw error;
    }
}

/**
 * Update a project
 * @param {string} projectId - Project ID
 * @param {Object} updates - Project updates
 * @param {string} [updates.name] - New name
 * @param {string} [updates.description] - New description
 * @param {string[]} [updates.tags] - New tags
 * @param {string} [updates.status] - New status (active, inactive, suspended)
 * @returns {Promise<Object>} Response with updated project
 */
async function updateProject(projectId, updates) {
    try {
        const response = await fetchWithAuth(`${API_BASE_URL}/projects/${encodeURIComponent(projectId)}`, {
            method: 'PUT',
            body: JSON.stringify(updates),
        });
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error('Error updating project:', error);
        throw error;
    }
}

/**
 * Delete a project
 * @param {string} projectId - Project ID
 * @param {boolean} [force=false] - Force delete even with active agents
 * @returns {Promise<Object>} Response with deletion confirmation
 */
async function deleteProject(projectId, force = false) {
    try {
        const url = force
            ? `${API_BASE_URL}/projects/${encodeURIComponent(projectId)}?force=true`
            : `${API_BASE_URL}/projects/${encodeURIComponent(projectId)}`;
        const response = await fetchWithAuth(url, {
            method: 'DELETE',
        });
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error('Error deleting project:', error);
        throw error;
    }
}

/**
 * Assign an agent to a project
 * @param {string} projectId - Project ID
 * @param {Object} assignment - Assignment data
 * @param {string} assignment.agent_id - Agent ID to assign
 * @param {string} [assignment.role='member'] - Agent role
 * @returns {Promise<Object>} Response with assignment confirmation
 */
async function assignAgentToProject(projectId, assignment) {
    try {
        const response = await fetchWithAuth(`${API_BASE_URL}/projects/${encodeURIComponent(projectId)}/agents`, {
            method: 'POST',
            body: JSON.stringify(assignment),
        });
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error('Error assigning agent to project:', error);
        throw error;
    }
}

/**
 * Unassign an agent from a project
 * @param {string} projectId - Project ID
 * @param {string} agentId - Agent ID to unassign
 * @returns {Promise<Object>} Response with unassignment confirmation
 */
async function unassignAgentFromProject(projectId, agentId) {
    try {
        const response = await fetchWithAuth(
            `${API_BASE_URL}/projects/${encodeURIComponent(projectId)}/agents/${encodeURIComponent(agentId)}`,
            {
                method: 'DELETE',
            }
        );
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error('Error unassigning agent from project:', error);
        throw error;
    }
}

/**
 * Send a message to a project chat room
 * @param {string} projectId - Project ID
 * @param {Object} message - Message data
 * @param {string} message.from_agent - Sender agent ID
 * @param {string} message.content - Message content
 * @param {string} [message.message_type='statement'] - Message type
 * @param {string} [message.in_reply_to] - ID of message this replies to
 * @returns {Promise<Object>} Response with created message
 */
async function sendProjectMessage(projectId, message) {
    try {
        const response = await fetchWithAuth(`${API_BASE_URL}/projects/${encodeURIComponent(projectId)}/messages`, {
            method: 'POST',
            body: JSON.stringify(message),
        });
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error('Error sending project message:', error);
        throw error;
    }
}

/**
 * Get messages from a project chat room
 * @param {string} projectId - Project ID
 * @param {Object} options - Query options
 * @param {number} [options.limit=50] - Maximum results
 * @param {string} [options.before] - Pagination cursor (message ID)
 * @returns {Promise<Object>} Response with messages array
 */
async function getProjectMessages(projectId, options = {}) {
    const { limit = 50, before = null } = options;

    const params = new URLSearchParams({ limit });
    if (before) params.append('before', before);

    try {
        const response = await fetchWithAuth(`${API_BASE_URL}/projects/${encodeURIComponent(projectId)}/messages?${params}`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error('Error fetching project messages:', error);
        throw error;
    }
}

// Export functions for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        fetchAgents,
        fetchAgentInfo,
        fetchStatistics,
        fetchActivity,
        fetchTimeline,
        updateAgentStatus,
        registerAgent,
        unregisterAgent,
        sendHeartbeat,
        connectWebSocket,
        disconnectWebSocket,
        sendWebSocketMessage,
        pingWebSocket,
        onWebSocketMessage,
        offWebSocketMessage,
        formatTimestamp,
        formatTimelineTimestamp,
        formatFullDate,
        login,
        refreshToken,
        createAgentToken,
        fetchRegisteredAgents,
        deleteAgent,
        copyToClipboard,
        setAuthToken,
        getWsUrlWithToken,
        getConnectionInfo,
        fetchLanguages,
        fetchTranslations,
        fetchProjects,
        fetchProjectAgents,
        fetchMessages,
        fetchMessageDetail,
        // Project management
        createProject,
        getProject,
        updateProject,
        deleteProject,
        assignAgentToProject,
        unassignAgentFromProject,
        sendProjectMessage,
        getProjectMessages,
    };
}

// Browser environment: attach to window object
if (typeof window !== 'undefined') {
    window.fetchAgents = fetchAgents;
    window.fetchAgentInfo = fetchAgentInfo;
    window.fetchStatistics = fetchStatistics;
    window.fetchActivity = fetchActivity;
    window.fetchTimeline = fetchTimeline;
    window.updateAgentStatus = updateAgentStatus;
    window.registerAgent = registerAgent;
    window.unregisterAgent = unregisterAgent;
    window.sendHeartbeat = sendHeartbeat;
    window.connectWebSocket = connectWebSocket;
    window.disconnectWebSocket = disconnectWebSocket;
    window.sendWebSocketMessage = sendWebSocketMessage;
    window.pingWebSocket = pingWebSocket;
    window.onWebSocketMessage = onWebSocketMessage;
    window.offWebSocketMessage = offWebSocketMessage;
    window.formatTimestamp = formatTimestamp;
    window.formatTimelineTimestamp = formatTimelineTimestamp;
    window.formatFullDate = formatFullDate;
    window.login = login;
    window.refreshToken = refreshToken;
    window.createAgentToken = createAgentToken;
    window.fetchRegisteredAgents = fetchRegisteredAgents;
    window.deleteAgent = deleteAgent;
    window.copyToClipboard = copyToClipboard;
    window.setAuthToken = setAuthToken;
    window.getWsUrlWithToken = getWsUrlWithToken;
    window.getConnectionInfo = getConnectionInfo;
    window.fetchLanguages = fetchLanguages;
    window.fetchTranslations = fetchTranslations;
    window.fetchProjects = fetchProjects;
    window.fetchProjectAgents = fetchProjectAgents;
    window.fetchMessages = fetchMessages;
    window.fetchMessageDetail = fetchMessageDetail;
    // Project management
    window.createProject = createProject;
    window.getProject = getProject;
    window.updateProject = updateProject;
    window.deleteProject = deleteProject;
    window.assignAgentToProject = assignAgentToProject;
    window.unassignAgentFromProject = unassignAgentFromProject;
    window.sendProjectMessage = sendProjectMessage;
    window.getProjectMessages = getProjectMessages;
}
