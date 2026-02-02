/**
 * WebSocket Manager for AI Agent Communication System
 *
 * Manages WebSocket connections with automatic reconnection,
 * event handling, and connection status tracking.
 *
 * @module websocket
 */

// Connection states
const ConnectionState = {
    DISCONNECTED: 'disconnected',
    CONNECTING: 'connecting',
    CONNECTED: 'connected',
    ERROR: 'error',
    RECONNECTING: 'reconnecting',
};

// WebSocket configuration
const WS_CONFIG = {
    maxReconnectAttempts: 5,
    baseReconnectDelay: 1000,
    maxReconnectDelay: 30000,
    reconnectBackoffMultiplier: 2,
    heartbeatInterval: 30000,
    connectionTimeout: 10000,
};

/**
 * WebSocketManager class for managing WebSocket connections
 */
class WebSocketManager {
    constructor(url) {
        this.url = url;
        this.ws = null;
        this.connectionState = ConnectionState.DISCONNECTED;
        this.reconnectAttempts = 0;
        this.reconnectTimeout = null;
        this.heartbeatTimeout = null;
        this.connectionTimeout = null;
        this.handlers = {};
        this.messageQueue = [];
        this.manualClose = false;
    }

    /**
     * Connect to WebSocket server
     * @param {string} token - Optional authentication token
     */
    connect(token = null) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            console.warn('WebSocket already connected');
            return;
        }

        if (this.connectionState === ConnectionState.CONNECTING ||
            this.connectionState === ConnectionState.RECONNECTING) {
            console.warn('WebSocket connection in progress');
            return;
        }

        this.manualClose = false;
        this.setConnectionState(ConnectionState.CONNECTING);

        // Build WebSocket URL with token if provided
        let wsUrl = this.url;
        if (token) {
            const separator = wsUrl.includes('?') ? '&' : '?';
            wsUrl = `${wsUrl}${separator}token=${encodeURIComponent(token)}`;
        }

        console.log(`Connecting to WebSocket: ${wsUrl.replace(/token=.+$/, 'token=***')}`);

        try {
            this.ws = new WebSocket(wsUrl);

            // Set connection timeout
            this.connectionTimeout = setTimeout(() => {
                if (this.connectionState === ConnectionState.CONNECTING) {
                    console.error('WebSocket connection timeout');
                    this.ws.close();
                }
            }, WS_CONFIG.connectionTimeout);

            // Setup event handlers
            this.ws.onopen = (event) => this.handleOpen(event);
            this.ws.onmessage = (event) => this.handleMessage(event);
            this.ws.onerror = (error) => this.handleError(error);
            this.ws.onclose = (event) => this.handleClose(event);

        } catch (error) {
            console.error('WebSocket connection error:', error);
            this.setConnectionState(ConnectionState.ERROR);
            this.scheduleReconnect();
        }
    }

    /**
     * Handle WebSocket open event
     * @param {Event} event - Open event
     */
    handleOpen(event) {
        console.log('WebSocket connected');

        if (this.connectionTimeout) {
            clearTimeout(this.connectionTimeout);
            this.connectionTimeout = null;
        }

        this.setConnectionState(ConnectionState.CONNECTED);
        this.reconnectAttempts = 0;

        // Start heartbeat
        this.startHeartbeat();

        // Send queued messages
        this.flushMessageQueue();

        // Emit connected event
        this.emit('connected', {});

        // Update UI status
        this.updateConnectionStatusUI('connected');
    }

    /**
     * Handle WebSocket message event
     * @param {MessageEvent} event - Message event
     */
    handleMessage(event) {
        try {
            const data = JSON.parse(event.data);
            console.log('WebSocket message received:', data);

            // Handle different message types
            this.handleMessageType(data);

            // Emit to registered handlers
            const messageType = data.type || 'message';
            this.emit(messageType, data);

            // Also emit to wildcard handlers
            this.emit('*', data);

        } catch (error) {
            console.error('Error parsing WebSocket message:', error);
        }
    }

    /**
     * Handle specific message types
     * @param {Object} data - Message data
     */
    handleMessageType(data) {
        switch (data.type) {
            case 'ping':
                // Respond with pong
                this.send('pong', {});
                break;

            case 'pong':
                // Reset heartbeat timeout
                this.resetHeartbeat();
                break;

            case 'agent_status_change':
                // Agent status changed
                this.emit('agentStatusChange', data.data);
                break;

            case 'new_communication':
                // New communication message
                this.emit('newCommunication', data.data);
                break;

            case 'meeting_event':
                // Meeting event
                this.emit('meetingEvent', data.data);
                break;

            case 'agent_registered':
                // Agent registered
                this.emit('agentRegistered', data.data);
                break;

            case 'agent_unregistered':
                // Agent unregistered
                this.emit('agentUnregistered', data.data);
                break;

            case 'connected':
                // Initial connection confirmation
                console.log('WebSocket connection confirmed by server');
                break;

            default:
                // Unknown message type
                console.log('Unknown WebSocket message type:', data.type);
        }
    }

    /**
     * Handle WebSocket error event
     * @param {Event} error - Error event
     */
    handleError(error) {
        console.error('WebSocket error:', error);
        this.setConnectionState(ConnectionState.ERROR);
        this.updateConnectionStatusUI('error');
        this.emit('error', { error });
    }

    /**
     * Handle WebSocket close event
     * @param {CloseEvent} event - Close event
     */
    handleClose(event) {
        console.log('WebSocket closed:', event.code, event.reason);

        if (this.connectionTimeout) {
            clearTimeout(this.connectionTimeout);
            this.connectionTimeout = null;
        }

        this.stopHeartbeat();
        this.setConnectionState(ConnectionState.DISCONNECTED);
        this.updateConnectionStatusUI('disconnected');

        this.emit('disconnected', { code: event.code, reason: event.reason });

        // Don't reconnect if manually closed or policy violation (auth failed)
        if (!this.manualClose && event.code !== 1008) {
            this.scheduleReconnect();
        }
    }

    /**
     * Schedule reconnection attempt
     */
    scheduleReconnect() {
        if (this.manualClose) {
            return;
        }

        if (this.reconnectAttempts >= WS_CONFIG.maxReconnectAttempts) {
            console.error('Max reconnection attempts reached');
            this.setConnectionState(ConnectionState.ERROR);
            this.emit('reconnectFailed', {});
            return;
        }

        this.reconnectAttempts++;

        // Calculate delay with exponential backoff
        const delay = Math.min(
            WS_CONFIG.baseReconnectDelay * Math.pow(WS_CONFIG.reconnectBackoffMultiplier, this.reconnectAttempts - 1),
            WS_CONFIG.maxReconnectDelay
        );

        console.log(`Scheduling reconnection attempt ${this.reconnectAttempts}/${WS_CONFIG.maxReconnectAttempts} in ${delay}ms`);

        this.setConnectionState(ConnectionState.RECONNECTING);
        this.updateConnectionStatusUI('reconnecting');

        this.reconnectTimeout = setTimeout(() => {
            this.connect();
        }, delay);

        this.emit('reconnecting', { attempt: this.reconnectAttempts, delay });
    }

    /**
     * Cancel reconnection attempt
     */
    cancelReconnect() {
        if (this.reconnectTimeout) {
            clearTimeout(this.reconnectTimeout);
            this.reconnectTimeout = null;
        }
    }

    /**
     * Disconnect WebSocket
     * @param {number} code - Close code
     * @param {string} reason - Close reason
     */
    disconnect(code = 1000, reason = 'Client closed connection') {
        this.manualClose = true;
        this.cancelReconnect();
        this.stopHeartbeat();

        if (this.ws) {
            this.ws.close(code, reason);
            this.ws = null;
        }

        this.setConnectionState(ConnectionState.DISCONNECTED);
        this.updateConnectionStatusUI('disconnected');
    }

    /**
     * Send message through WebSocket
     * @param {string} type - Message type
     * @param {Object} data - Message data
     */
    send(type, data = {}) {
        const message = { type, ...data };

        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(message));
        } else {
            // Queue message for later sending
            this.messageQueue.push(message);
            console.warn('WebSocket not connected, message queued');
        }
    }

    /**
     * Flush queued messages
     */
    flushMessageQueue() {
        while (this.messageQueue.length > 0 && this.ws && this.ws.readyState === WebSocket.OPEN) {
            const message = this.messageQueue.shift();
            this.ws.send(JSON.stringify(message));
        }
    }

    /**
     * Register event handler
     * @param {string} event - Event name
     * @param {Function} handler - Handler function
     */
    on(event, handler) {
        if (!this.handlers[event]) {
            this.handlers[event] = [];
        }
        this.handlers[event].push(handler);
    }

    /**
     * Unregister event handler
     * @param {string} event - Event name
     * @param {Function} handler - Handler function
     */
    off(event, handler) {
        if (!this.handlers[event]) {
            return;
        }

        const index = this.handlers[event].indexOf(handler);
        if (index > -1) {
            this.handlers[event].splice(index, 1);
        }
    }

    /**
     * Emit event to handlers
     * @param {string} event - Event name
     * @param {Object} data - Event data
     */
    emit(event, data) {
        const handlers = this.handlers[event] || [];
        handlers.forEach(handler => {
            try {
                handler(data);
            } catch (error) {
                console.error(`WebSocket handler error for event "${event}":`, error);
            }
        });
    }

    /**
     * Set connection state
     * @param {string} state - Connection state
     */
    setConnectionState(state) {
        const oldState = this.connectionState;
        this.connectionState = state;

        if (oldState !== state) {
            this.emit('stateChange', { oldState, newState: state });
        }
    }

    /**
     * Get connection state
     * @returns {string} Current connection state
     */
    getConnectionState() {
        return this.connectionState;
    }

    /**
     * Check if connected
     * @returns {boolean} True if connected
     */
    isConnected() {
        return this.connectionState === ConnectionState.CONNECTED &&
               this.ws &&
               this.ws.readyState === WebSocket.OPEN;
    }

    /**
     * Start heartbeat to keep connection alive
     */
    startHeartbeat() {
        this.stopHeartbeat();

        this.heartbeatTimeout = setTimeout(() => {
            if (this.isConnected()) {
                this.send('ping', { timestamp: Date.now() });
                this.startHeartbeat();
            }
        }, WS_CONFIG.heartbeatInterval);
    }

    /**
     * Stop heartbeat
     */
    stopHeartbeat() {
        if (this.heartbeatTimeout) {
            clearTimeout(this.heartbeatTimeout);
            this.heartbeatTimeout = null;
        }
    }

    /**
     * Reset heartbeat timeout (called on pong)
     */
    resetHeartbeat() {
        this.startHeartbeat();
    }

    /**
     * Update connection status in UI
     * @param {string} status - Connection status
     */
    updateConnectionStatusUI(status) {
        const badge = document.getElementById('connectionStatus');
        if (!badge) return;

        // Remove all status classes
        badge.classList.remove('connected', 'connecting', 'disconnected', 'error', 'reconnecting');

        // Add current status class
        badge.classList.add(status);

        // Update status text
        const textElement = badge.querySelector('.status-text');
        if (!textElement) return;

        const statusLabels = {
            connected: '연결됨',
            connecting: '연결 중...',
            disconnected: '연결 해제',
            error: '연결 오류',
            reconnecting: '재연결 중...',
        };

        // Use i18n if available
        if (typeof i18n !== 'undefined' && i18n.t) {
            const key = `connection.${status}`;
            textElement.textContent = i18n.t(key);
            textElement.setAttribute('data-i18n', key);
        } else {
            textElement.textContent = statusLabels[status] || status;
        }
    }

    /**
     * Get connection info
     * @returns {Object} Connection information
     */
    getConnectionInfo() {
        return {
            url: this.url,
            state: this.connectionState,
            connected: this.isConnected(),
            reconnectAttempts: this.reconnectAttempts,
        };
    }
}

// Global WebSocket manager instance
let wsManager = null;

/**
 * Initialize WebSocket manager
 * @param {string} url - WebSocket URL
 * @returns {WebSocketManager} WebSocket manager instance
 */
function initWebSocketManager(url) {
    if (wsManager) {
        wsManager.disconnect();
    }

    wsManager = new WebSocketManager(url);
    return wsManager;
}

/**
 * Get WebSocket manager instance
 * @returns {WebSocketManager|null} WebSocket manager instance
 */
function getWebSocketManager() {
    return wsManager;
}

/**
 * Connect to WebSocket
 * @param {string} token - Optional authentication token
 */
function connectWebSocket(token = null) {
    if (!wsManager) {
        console.error('WebSocket manager not initialized');
        return;
    }

    wsManager.connect(token);
}

/**
 * Disconnect WebSocket
 */
function disconnectWebSocket() {
    if (wsManager) {
        wsManager.disconnect();
    }
}

/**
 * Send WebSocket message
 * @param {string} type - Message type
 * @param {Object} data - Message data
 */
function sendWebSocketMessage(type, data = {}) {
    if (!wsManager) {
        console.error('WebSocket manager not initialized');
        return;
    }

    wsManager.send(type, data);
}

/**
 * Register WebSocket event handler
 * @param {string} event - Event name
 * @param {Function} handler - Handler function
 */
function onWebSocketEvent(event, handler) {
    if (!wsManager) {
        console.error('WebSocket manager not initialized');
        return;
    }

    wsManager.on(event, handler);
}

/**
 * Unregister WebSocket event handler
 * @param {string} event - Event name
 * @param {Function} handler - Handler function
 */
function offWebSocketEvent(event, handler) {
    if (!wsManager) {
        console.error('WebSocket manager not initialized');
        return;
    }

    wsManager.off(event, handler);
}

/**
 * Get WebSocket connection state
 * @returns {string} Connection state
 */
function getWebSocketState() {
    return wsManager ? wsManager.getConnectionState() : ConnectionState.DISCONNECTED;
}

/**
 * Check if WebSocket is connected
 * @returns {boolean} True if connected
 */
function isWebSocketConnected() {
    return wsManager ? wsManager.isConnected() : false;
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        WebSocketManager,
        ConnectionState,
        WS_CONFIG,
        initWebSocketManager,
        getWebSocketManager,
        connectWebSocket,
        disconnectWebSocket,
        sendWebSocketMessage,
        onWebSocketEvent,
        offWebSocketEvent,
        getWebSocketState,
        isWebSocketConnected,
    };
}

// Browser environment: attach to window object
if (typeof window !== 'undefined') {
    window.WebSocketManager = WebSocketManager;
    window.ConnectionState = ConnectionState;
    window.WS_CONFIG = WS_CONFIG;
    window.initWebSocketManager = initWebSocketManager;
    window.getWebSocketManager = getWebSocketManager;
    window.connectWebSocket = connectWebSocket;
    window.disconnectWebSocket = disconnectWebSocket;
    window.sendWebSocketMessage = sendWebSocketMessage;
    window.onWebSocketEvent = onWebSocketEvent;
    window.offWebSocketEvent = offWebSocketEvent;
    window.getWebSocketState = getWebSocketState;
    window.isWebSocketConnected = isWebSocketConnected;
}

// Cleanup on page unload
if (typeof window !== 'undefined') {
    window.addEventListener('beforeunload', () => {
        disconnectWebSocket();
    });
}
