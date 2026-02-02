/**
 * Project Chat Room Module
 *
 * Provides Discord/Slack-like chat interface for project-based messaging.
 * Handles real-time message updates via WebSocket.
 */

// Chat room state
const chatRooms = {}; // project_id -> { messages, participants, unreadCount }
let currentProjectId = null;

/**
 * Initialize project chat functionality
 */
function initProjectChat() {
    console.log('Initializing project chat rooms...');

    // Setup WebSocket message handler for project messages
    setupProjectMessageHandler();

    console.log('Project chat initialized');
}

/**
 * Setup WebSocket message handler for project events
 */
function setupProjectMessageHandler() {
    // Register handler for project messages
    if (typeof onWebSocketMessage === 'function') {
        onWebSocketMessage(handleProjectWebSocketMessage);
    }
}

/**
 * Handle incoming WebSocket messages for projects
 * @param {Object} data - WebSocket message data
 */
function handleProjectWebSocketMessage(data) {
    const { type, project_id } = data;

    switch (type) {
        case 'project_message':
            handleNewProjectMessage(data);
            break;
        case 'agent_assignment_changed':
            handleAgentAssignmentChange(data);
            break;
        case 'project_updated':
            handleProjectUpdate(data);
            break;
    }
}

/**
 * Handle new project message from WebSocket
 * @param {Object} data - Message data
 */
function handleNewProjectMessage(data) {
    const { project_id, data: messageData } = data;

    // Add message to chat room
    if (chatRooms[project_id]) {
        chatRooms[project_id].messages.push(messageData);
        chatRooms[project_id].lastActivity = new Date(messageData.timestamp);

        // If this is the current project, append message
        if (currentProjectId === project_id) {
            appendMessageToChat(messageData);
        } else {
            // Increment unread count
            chatRooms[project_id].unreadCount++;
            updateProjectUnreadIndicator(project_id);
        }
    }
}

/**
 * Handle agent assignment change from WebSocket
 * @param {Object} data - Assignment data
 */
function handleAgentAssignmentChange(data) {
    const { project_id, data: assignmentData } = data;
    console.log('Agent assignment changed:', assignmentData);

    // Update participants list if showing
    if (currentProjectId === project_id) {
        refreshProjectParticipants(project_id);
    }
}

/**
 * Handle project update from WebSocket
 * @param {Object} data - Project update data
 */
function handleProjectUpdate(data) {
    const { project_id, data: updateData } = data;
    console.log('Project updated:', updateData);

    // Refresh projects list
    if (typeof loadProjects === 'function') {
        loadProjects();
    }
}

/**
 * Open chat room for a project
 * @param {string} projectId - Project ID
 */
async function openProjectChatRoom(projectId) {
    currentProjectId = projectId;

    // Initialize chat room if needed
    if (!chatRooms[projectId]) {
        chatRooms[projectId] = {
            messages: [],
            participants: [],
            unreadCount: 0,
            lastActivity: null,
        };
    }

    // Create or show chat room UI
    showChatRoomUI(projectId);

    // Load messages
    await loadProjectMessages(projectId);

    // Clear unread count
    chatRooms[projectId].unreadCount = 0;
    updateProjectUnreadIndicator(projectId);

    // Load participants
    await refreshProjectParticipants(projectId);
}

/**
 * Show chat room UI
 * @param {string} projectId - Project ID
 */
function showChatRoomUI(projectId) {
    // Check if chat room container exists
    let chatContainer = document.getElementById('projectChatRoom');

    if (!chatContainer) {
        chatContainer = document.createElement('div');
        chatContainer.id = 'projectChatRoom';
        chatContainer.className = 'project-chat-room';
        document.body.appendChild(chatContainer);
    }

    chatContainer.innerHTML = `
        <div class="chat-room" data-project-id="${projectId}">
            <div class="chat-header">
                <div class="chat-info">
                    <svg class="chat-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
                    </svg>
                    <div class="chat-details">
                        <h3 class="chat-title">#${projectId}</h3>
                        <span class="chat-topic">Project chat room</span>
                    </div>
                </div>
                <div class="chat-actions">
                    <button class="btn-icon" onclick="refreshProjectParticipants('${projectId}')" title="Refresh participants">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M23 4v6h-6"></path>
                            <path d="M1 20v-6h6"></path>
                            <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path>
                        </svg>
                    </button>
                    <button class="btn-icon" onclick="closeProjectChatRoom()" title="Close chat">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <line x1="18" y1="6" x2="6" y2="18"></line>
                            <line x1="6" y1="6" x2="18" y2="18"></line>
                        </svg>
                    </button>
                </div>
            </div>

            <div class="chat-messages" id="chatMessages-${projectId}">
                <div class="chat-loading">Loading messages...</div>
            </div>

            <div class="chat-input-area">
                <form id="chatForm-${projectId}" onsubmit="handleChatSubmit(event, '${projectId}')">
                    <div class="input-wrapper">
                        <input type="text"
                               id="chatInput-${projectId}"
                               class="chat-input"
                               placeholder="Message #${projectId}"
                               autocomplete="off"
                               maxlength="10000">
                        <button type="submit" class="btn btn-primary btn-send" title="Send">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <line x1="22" y1="2" x2="11" y2="13"></line>
                                <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
                            </svg>
                        </button>
                    </div>
                </form>
            </div>
        </div>
    `;

    // Show the chat room
    chatContainer.classList.add('active');

    // Focus input
    setTimeout(() => {
        const input = document.getElementById(`chatInput-${projectId}`);
        if (input) input.focus();
    }, 100);
}

/**
 * Load project messages
 * @param {string} projectId - Project ID
 */
async function loadProjectMessages(projectId) {
    const messagesContainer = document.getElementById(`chatMessages-${projectId}`);

    try {
        const data = await getProjectMessages(projectId, { limit: 100 });

        // Update state
        chatRooms[projectId].messages = data.messages || [];

        // Render messages
        renderMessages(projectId, data.messages || []);

    } catch (error) {
        console.error('Failed to load messages:', error);
        if (messagesContainer) {
            messagesContainer.innerHTML = `
                <div class="chat-error">
                    Failed to load messages: ${error.message}
                </div>
            `;
        }
    }
}

/**
 * Render messages in chat room
 * @param {string} projectId - Project ID
 * @param {Array} messages - Messages array
 */
function renderMessages(projectId, messages) {
    const container = document.getElementById(`chatMessages-${projectId}`);
    if (!container) return;

    if (messages.length === 0) {
        container.innerHTML = `
            <div class="chat-empty">
                <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
                </svg>
                <p>No messages yet. Start the conversation!</p>
            </div>
        `;
        return;
    }

    container.innerHTML = messages.map(msg => createMessageHTML(msg)).join('');

    // Scroll to bottom
    scrollToBottom(container);
}

/**
 * Create HTML for a message
 * @param {Object} message - Message object
 * @returns {string} HTML string
 */
function createMessageHTML(message) {
    const { from_agent, content, timestamp, message_type } = message;

    // Format timestamp
    const time = formatChatTime(timestamp);

    // Get message type class
    const typeClass = `message-type-${message_type || 'statement'}`;

    // Get avatar initials
    const initials = getAgentInitials(from_agent);

    return `
        <div class="chat-message ${typeClass}" data-message-id="${message.message_id}">
            <div class="message-avatar">${initials}</div>
            <div class="message-content">
                <div class="message-header">
                    <span class="message-author">${escapeHtml(from_agent)}</span>
                    <span class="message-time">${time}</span>
                </div>
                <div class="message-body">${escapeHtml(content)}</div>
            </div>
        </div>
    `;
}

/**
 * Append a new message to the chat
 * @param {Object} message - Message object
 */
function appendMessageToChat(message) {
    const container = document.getElementById(`chatMessages-${currentProjectId}`);
    if (!container) return;

    // Remove empty state if present
    const emptyState = container.querySelector('.chat-empty');
    if (emptyState) {
        emptyState.remove();
    }

    // Remove loading indicator
    const loading = container.querySelector('.chat-loading');
    if (loading) {
        loading.remove();
    }

    // Append message
    const messageHTML = createMessageHTML(message);
    container.insertAdjacentHTML('beforeend', messageHTML);

    // Scroll to bottom
    scrollToBottom(container);
}

/**
 * Handle chat form submission
 * @param {Event} e - Form submit event
 * @param {string} projectId - Project ID
 */
async function handleChatSubmit(e, projectId) {
    e.preventDefault();

    const input = document.getElementById(`chatInput-${projectId}`);
    const content = input.value.trim();

    if (!content) return;

    // Get current agent ID (would normally come from auth context)
    const fromAgent = getCurrentAgentId();

    const messageData = {
        from_agent: fromAgent,
        content: content,
        message_type: 'statement',
    };

    try {
        const message = await sendProjectMessage(projectId, messageData);

        // Clear input
        input.value = '';

        // Message will be added via WebSocket broadcast

    } catch (error) {
        console.error('Failed to send message:', error);
        showErrorNotification(`Failed to send message: ${error.message}`);
    }
}

/**
 * Refresh project participants list
 * @param {string} projectId - Project ID
 */
async function refreshProjectParticipants(projectId) {
    try {
        const data = await fetchProjectAgents(projectId);
        chatRooms[projectId].participants = data.agents || [];

        // Update UI if showing
        // TODO: Implement participants list panel

    } catch (error) {
        console.error('Failed to load participants:', error);
    }
}

/**
 * Close project chat room
 */
function closeProjectChatRoom() {
    const container = document.getElementById('projectChatRoom');
    if (container) {
        container.classList.remove('active');
    }
    currentProjectId = null;
}

/**
 * Update project unread indicator
 * @param {string} projectId - Project ID
 */
function updateProjectUnreadIndicator(projectId) {
    const unreadCount = chatRooms[projectId]?.unreadCount || 0;

    // Update project sidebar item
    const projectItem = document.querySelector(`.project-channel[data-project-id="${projectId}"]`);
    if (projectItem) {
        const badge = projectItem.querySelector('.unread-badge') || document.createElement('span');
        badge.className = 'unread-badge';

        if (unreadCount > 0) {
            badge.textContent = unreadCount > 99 ? '99+' : unreadCount;
            badge.style.display = 'inline';
        } else {
            badge.style.display = 'none';
        }

        if (!projectItem.querySelector('.unread-badge')) {
            projectItem.appendChild(badge);
        }
    }
}

/**
 * Get current agent ID
 * @returns {string} Agent ID
 */
function getCurrentAgentId() {
    // TODO: Get from auth context
    return 'System';
}

/**
 * Format chat time
 * @param {string} timestamp - ISO timestamp
 * @returns {string} Formatted time
 */
function formatChatTime(timestamp) {
    const date = new Date(timestamp);
    const now = new Date();
    const diff = now - date;

    // Less than a minute
    if (diff < 60000) {
        return 'Just now';
    }

    // Less than an hour
    if (diff < 3600000) {
        const mins = Math.floor(diff / 60000);
        return `${mins}m ago`;
    }

    // Today
    if (date.toDateString() === now.toDateString()) {
        return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }

    // This week
    const weekAgo = new Date(now - 7 * 86400000);
    if (date > weekAgo) {
        return date.toLocaleDateString([], { weekday: 'short' });
    }

    // Older
    return date.toLocaleDateString([], { month: 'short', day: 'numeric' });
}

/**
 * Get agent initials from agent ID
 * @param {string} agentId - Agent ID
 * @returns {string} Initials
 */
function getAgentInitials(agentId) {
    // Remove @ prefix if present
    const id = agentId.replace('@', '');

    // Extract nickname part
    const match = id.match(/^([A-Z][a-z]+)/);
    if (match) {
        return match[1].substring(0, 2).toUpperCase();
    }

    // Use first 2 characters
    return id.substring(0, 2).toUpperCase();
}

/**
 * Scroll chat container to bottom
 * @param {HTMLElement} container - Chat container
 */
function scrollToBottom(container) {
    container.scrollTop = container.scrollHeight;
}

/**
 * Escape HTML to prevent XSS
 * @param {string} text - Text to escape
 * @returns {string} Escaped text
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Show error notification
 */
function showErrorNotification(message) {
    // Reuse notification from project-management if available
    if (typeof showNotification === 'function') {
        showNotification(message, 'error');
    } else {
        alert(message);
    }
}

// Add styles
const chatStyles = document.createElement('style');
chatStyles.textContent = `
    .project-chat-room {
        display: none;
        position: fixed;
        top: 0;
        right: 0;
        bottom: 0;
        width: 400px;
        max-width: 90vw;
        background: white;
        box-shadow: -4px 0 20px rgba(0, 0, 0, 0.1);
        z-index: 9000;
        flex-direction: column;
    }

    .project-chat-room.active {
        display: flex;
    }

    .chat-room {
        display: flex;
        flex-direction: column;
        height: 100%;
    }

    .chat-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 16px;
        border-bottom: 1px solid #e5e7eb;
        background: #f9fafb;
    }

    .chat-info {
        display: flex;
        align-items: center;
        gap: 12px;
    }

    .chat-icon {
        color: #6b7280;
    }

    .chat-title {
        margin: 0;
        font-size: 16px;
        font-weight: 600;
        color: #111827;
    }

    .chat-topic {
        font-size: 12px;
        color: #6b7280;
    }

    .chat-actions {
        display: flex;
        gap: 8px;
    }

    .btn-icon {
        background: none;
        border: none;
        padding: 8px;
        border-radius: 6px;
        cursor: pointer;
        color: #6b7280;
        display: flex;
        align-items: center;
        justify-content: center;
    }

    .btn-icon:hover {
        background: #e5e7eb;
        color: #111827;
    }

    .chat-messages {
        flex: 1;
        overflow-y: auto;
        padding: 16px;
        display: flex;
        flex-direction: column;
        gap: 12px;
    }

    .chat-empty {
        text-align: center;
        padding: 40px 20px;
        color: #9ca3af;
    }

    .chat-empty svg {
        margin-bottom: 16px;
    }

    .chat-message {
        display: flex;
        gap: 12px;
        align-items: flex-start;
    }

    .message-avatar {
        width: 36px;
        height: 36px;
        border-radius: 50%;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 12px;
        font-weight: 600;
        flex-shrink: 0;
    }

    .message-content {
        flex: 1;
        min-width: 0;
    }

    .message-header {
        display: flex;
        align-items: baseline;
        gap: 8px;
        margin-bottom: 4px;
    }

    .message-author {
        font-weight: 600;
        font-size: 14px;
        color: #111827;
    }

    .message-time {
        font-size: 11px;
        color: #9ca3af;
    }

    .message-body {
        font-size: 14px;
        color: #374151;
        line-height: 1.5;
        word-break: break-word;
    }

    .message-type-question {
        background: #fef3c7;
        border-radius: 8px;
        padding: 8px 12px;
    }

    .message-type-question .message-body {
        color: #92400e;
    }

    .chat-input-area {
        padding: 16px;
        border-top: 1px solid #e5e7eb;
        background: white;
    }

    .input-wrapper {
        display: flex;
        gap: 8px;
    }

    .chat-input {
        flex: 1;
        padding: 10px 14px;
        border: 1px solid #d1d5db;
        border-radius: 20px;
        font-size: 14px;
    }

    .chat-input:focus {
        outline: none;
        border-color: #3b82f6;
        box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
    }

    .btn-send {
        width: 40px;
        height: 40px;
        border-radius: 50%;
        padding: 0;
        display: flex;
        align-items: center;
        justify-content: center;
    }

    .unread-badge {
        position: absolute;
        top: 4px;
        right: 4px;
        background: #ef4444;
        color: white;
        font-size: 10px;
        font-weight: 600;
        padding: 2px 6px;
        border-radius: 10px;
        min-width: 18px;
        text-align: center;
    }

    .project-channel {
        position: relative;
    }
`;

if (!document.querySelector('style[data-project-chat]')) {
    chatStyles.setAttribute('data-project-chat', 'true');
    document.head.appendChild(chatStyles);
}

// Make functions globally available
window.initProjectChat = initProjectChat;
window.openProjectChatRoom = openProjectChatRoom;
window.closeProjectChatRoom = closeProjectChatRoom;
window.handleChatSubmit = handleChatSubmit;

// Auto-initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initProjectChat);
} else {
    initProjectChat();
}
