/**
 * Messages component for AI Agent Communication System
 *
 * Manages the message history list with filtering and detail view.
 */

// Messages state
let messages = [];
let selectedProjectId = null;
let currentOffset = 0;
const pageSize = 50;
let isLoading = false;
let hasMore = true;

// DOM messageElements
const messageElements = {
    messagesList: null,
    messagesLoading: null,
    messageProjectFilter: null,
    refreshMessagesBtn: null,
    messageModal: null,
    messageModalOverlay: null,
    closeMessageModal: null,
    modalSender: null,
    modalRecipient: null,
    modalTimestamp: null,
    modalContent: null,
    modalProject: null,
    modalType: null,
};

/**
 * Initialize the messages component
 */
async function initMessages() {
    console.log('Initializing messages component...');

    // Cache DOM messageElements
    messageElements.messagesList = document.getElementById('messagesList');
    messageElements.messagesLoading = document.getElementById('messagesLoading');
    messageElements.messageProjectFilter = document.getElementById('messageProjectFilter');
    messageElements.refreshMessagesBtn = document.getElementById('refreshMessagesBtn');
    messageElements.messageModal = document.getElementById('messageModal');
    messageElements.messageModalOverlay = document.getElementById('messageModalOverlay');
    messageElements.closeMessageModal = document.getElementById('closeMessageModal');
    messageElements.modalSender = document.getElementById('modalSender');
    messageElements.modalRecipient = document.getElementById('modalRecipient');
    messageElements.modalTimestamp = document.getElementById('modalTimestamp');
    messageElements.modalContent = document.getElementById('modalContent');
    messageElements.modalProject = document.getElementById('modalProject');
    messageElements.modalType = document.getElementById('modalType');

    if (!messageElements.messagesList) {
        console.warn('Messages list element not found');
        return;
    }

    // Set up event listeners
    messageElements.messageProjectFilter?.addEventListener('change', handleProjectFilterChange);
    messageElements.refreshMessagesBtn?.addEventListener('click', refreshMessages);
    messageElements.closeMessageModal?.addEventListener('click', closeMessageModal);
    messageElements.messageModalOverlay?.addEventListener('click', closeMessageModal);

    // Set up infinite scroll
    messageElements.messagesList.addEventListener('scroll', handleScroll);

    // Load initial messages
    await loadMessages();

    console.log('Messages component initialized');
}

/**
 * Load messages from API
 */
async function loadMessages(reset = true) {
    if (isLoading) return;

    if (reset) {
        currentOffset = 0;
        hasMore = true;
        messages = [];
    }

    if (!hasMore) return;

    isLoading = true;
    showLoading(true);

    try {
        const projectId = selectedProjectId || undefined;
        const data = await fetchMessages({
            project_id: projectId,
            limit: pageSize,
            offset: currentOffset,
        });

        const newMessages = data || [];

        if (reset) {
            messages = newMessages;
        } else {
            messages = [...messages, ...newMessages];
        }

        // Update pagination state
        hasMore = newMessages.length === pageSize;
        currentOffset += newMessages.length;

        // Check if no messages exist
        if (messages.length === 0) {
            renderEmptyState();
        } else {
            renderMessages();
        }
    } catch (error) {
        console.error('Failed to load messages:', error);
        renderErrorState();
    } finally {
        isLoading = false;
        showLoading(false);
    }
}

/**
 * Render messages list
 */
function renderMessages() {
    if (!messageElements.messagesList) return;

    messageElements.messagesList.innerHTML = messages.map(msg => createMessageItem(msg)).join('');
}

/**
 * Create a message item HTML
 */
function createMessageItem(msg) {
    const { message_id, from_agent, to_agent, timestamp, content_preview, project_id, message_type } = msg;

    const formattedTime = formatTimestamp(timestamp);
    const projectName = project_id || 'All Projects';
    const typeLabel = message_type || 'direct';

    return `
        <div class="message-item" data-message-id="${escapeHtml(message_id)}" onclick="viewMessageDetail('${escapeHtml(message_id)}')">
            <div class="message-header">
                <div class="message-participants">
                    <span class="message-sender">${escapeHtml(from_agent)}</span>
                    <svg class="message-arrow" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <line x1="5" y1="12" x2="19" y2="12"></line>
                        <polyline points="12 5 19 12 12 19"></polyline>
                    </svg>
                    <span class="message-recipient">${escapeHtml(to_agent || 'All')}</span>
                </div>
                <span class="message-timestamp">${formattedTime}</span>
            </div>
            <div class="message-preview">${escapeHtml(content_preview)}</div>
            <div class="message-meta">
                ${project_id ? `<span class="message-project">${escapeHtml(projectName)}</span>` : ''}
                <span class="message-type">${typeLabel}</span>
            </div>
        </div>
    `;
}

/**
 * Render empty state
 */
function renderEmptyState() {
    if (!messageElements.messagesList) return;

    messageElements.messagesList.innerHTML = `
        <div class="empty-state">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
            </svg>
            <p>No messages found</p>
            <p style="font-size: 0.875rem; color: var(--text-muted); margin-top: var(--space-xs);">
                Messages will appear here when agents communicate.
            </p>
        </div>
    `;
}

/**
 * Render error state
 */
function renderErrorState() {
    if (!messageElements.messagesList) return;

    messageElements.messagesList.innerHTML = `
        <div class="error-state">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="10"></circle>
                <line x1="12" y1="8" x2="12" y2="12"></line>
                <line x1="12" y1="16" x2="12.01" y2="16"></line>
            </svg>
            <p>Failed to load messages</p>
            <button class="btn btn-secondary" style="margin-top: var(--space-md);" onclick="refreshMessages()">
                Retry
            </button>
        </div>
    `;
}

/**
 * View message detail
 */
async function viewMessageDetail(messageId) {
    try {
        const message = await fetchMessageDetail(messageId);

        // Populate modal
        if (messageElements.modalSender) {
            messageElements.modalSender.textContent = message.from_agent || 'Unknown';
        }
        if (messageElements.modalRecipient) {
            messageElements.modalRecipient.textContent = message.to_agent || 'All';
        }
        if (messageElements.modalTimestamp) {
            messageElements.modalTimestamp.textContent = formatFullDate(message.timestamp);
        }
        if (messageElements.modalContent) {
            messageElements.modalContent.textContent = message.content || '';
        }
        if (messageElements.modalProject) {
            messageElements.modalProject.textContent = message.project_id || 'No Project';
            messageElements.modalProject.style.display = message.project_id ? 'inline-block' : 'none';
        }
        if (messageElements.modalType) {
            messageElements.modalType.textContent = message.message_type || 'direct';
        }

        // Show modal
        if (messageElements.messageModal) {
            messageElements.messageModal.style.display = 'flex';
        }
    } catch (error) {
        console.error('Failed to load message detail:', error);
        alert('Failed to load message details. Please try again.');
    }
}

/**
 * Close message modal
 */
function closeMessageModal() {
    if (messageElements.messageModal) {
        messageElements.messageModal.style.display = 'none';
    }
}

/**
 * Handle project filter change
 */
async function handleProjectFilterChange() {
    if (!messageElements.messageProjectFilter) return;

    selectedProjectId = messageElements.messageProjectFilter.value || null;
    await loadMessages(true);
}

/**
 * Refresh messages
 */
async function refreshMessages() {
    await loadMessages(true);
}

/**
 * Handle scroll for infinite scroll
 */
function handleScroll() {
    if (!messageElements.messagesList || isLoading || !hasMore) return;

    const { scrollTop, scrollHeight, clientHeight } = messageElements.messagesList;

    // Load more when scrolled to 80% of the list
    if (scrollTop + clientHeight >= scrollHeight * 0.8) {
        loadMessages(false);
    }
}

/**
 * Show/hide loading indicator
 */
function showLoading(show) {
    if (messageElements.messagesLoading) {
        messageElements.messagesLoading.style.display = show ? 'flex' : 'none';
    }
}

/**
 * Update project filter options
 */
function updateProjectFilter(projects) {
    if (!messageElements.messageProjectFilter) return;

    // Get current selected value
    const currentValue = messageElements.messageProjectFilter.value;

    // Clear existing options (keep first "All Projects" option)
    messageElements.messageProjectFilter.innerHTML = `
        <option value="" data-i18n="messages.allProjects">All Projects</option>
    `;

    // Add project options
    projects.forEach(project => {
        const option = document.createElement('option');
        option.value = project.project_id || '';
        option.textContent = project.name || 'All Projects';
        messageElements.messageProjectFilter.appendChild(option);
    });

    // Restore selected value
    if (currentValue) {
        messageElements.messageProjectFilter.value = currentValue;
    }
}

/**
 * Handle new message from WebSocket
 */
function handleNewMessage(message) {
    // Prepend new message to the list
    messages.unshift(message);
    renderMessages();
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Make functions globally available
window.initMessages = initMessages;
window.viewMessageDetail = viewMessageDetail;
window.closeMessageModal = closeMessageModal;
window.refreshMessages = refreshMessages;
window.updateProjectFilter = updateProjectFilter;
window.handleNewMessage = handleNewMessage;

// Auto-initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initMessages);
} else {
    initMessages();
}
