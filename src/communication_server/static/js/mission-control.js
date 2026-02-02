/**
 * Mission Control Center UI Controller
 *
 * Manages the 3-Pane layout for Owner Dashboard including:
 * - Left Pane: Agent & Assets management
 * - Center Pane: Communication/Chat interface
 * - Right Pane: Decision Desk for Spec review
 */

// Mission Control State
const mcState = {
    agents: [],
    messages: [],
    currentSpec: null,
    pendingDecisions: 0,
    wsConnected: false,
    currentProjectId: 'proj_main',
    selectedAgentId: null,
};

// DOM Elements Cache
const mcElements = {
    // Agent List
    agentList: null,
    activeAgentCount: null,
    refreshAgentsBtn: null,

    // Chat
    chatMessages: null,
    chatContainer: null,
    messageInput: null,
    sendMessageBtn: null,
    roomTitle: null,
    roomStatus: null,

    // Decision Desk
    currentSpecCard: null,
    pendingDecisionsBadge: null,
    diffViewer: null,
    rejectChangesBtn: null,
    approveChangesBtn: null,

    // Connection Status
    wsConnectionStatus: null,

    // Modals
    createAgentModal: null,
    panicModal: null,
    approvalModal: null,
    createAgentForm: null,
    panicConfirmInput: null,
    confirmPanicBtn: null,
    finalApprovalBtn: null,
    approvalComment: null,
};

/**
 * Initialize Mission Control Center
 */
async function initMissionControl() {
    console.log('Initializing Mission Control Center...');

    // Cache DOM elements
    cacheMCElements();

    // Set up event listeners
    setupMCEventListeners();

    // Load initial data
    await loadMissionControlData();

    // Connect WebSocket for real-time updates
    connectMissionControlWebSocket();

    console.log('Mission Control Center initialized');
}

/**
 * Cache DOM elements for performance
 */
function cacheMCElements() {
    // Agent List
    mcElements.agentList = document.getElementById('agentList');
    mcElements.activeAgentCount = document.getElementById('activeAgentCount');
    mcElements.refreshAgentsBtn = document.getElementById('refreshAgentsBtn');

    // Chat
    mcElements.chatMessages = document.getElementById('chatMessages');
    mcElements.chatContainer = document.getElementById('chatContainer');
    mcElements.messageInput = document.getElementById('messageInput');
    mcElements.sendMessageBtn = document.getElementById('sendMessageBtn');
    mcElements.roomTitle = document.getElementById('roomTitle');
    mcElements.roomStatus = document.getElementById('roomStatus');

    // Decision Desk
    mcElements.currentSpecCard = document.getElementById('currentSpecCard');
    mcElements.pendingDecisionsBadge = document.getElementById('pendingDecisionsBadge');
    mcElements.diffViewer = document.getElementById('diffViewer');
    mcElements.rejectChangesBtn = document.getElementById('rejectChangesBtn');
    mcElements.approveChangesBtn = document.getElementById('approveChangesBtn');

    // Connection Status
    mcElements.wsConnectionStatus = document.getElementById('wsConnectionStatus');

    // Modals
    mcElements.createAgentModal = document.getElementById('createAgentModal');
    mcElements.panicModal = document.getElementById('panicModal');
    mcElements.approvalModal = document.getElementById('approvalModal');
    mcElements.createAgentForm = document.getElementById('createAgentForm');
    mcElements.panicConfirmInput = document.getElementById('panicConfirmInput');
    mcElements.confirmPanicBtn = document.getElementById('confirmPanicBtn');
    mcElements.finalApprovalBtn = document.getElementById('finalApprovalBtn');
    mcElements.approvalComment = document.getElementById('approvalComment');
}

/**
 * Set up event listeners
 */
function setupMCEventListeners() {
    // Refresh agents button
    mcElements.refreshAgentsBtn?.addEventListener('click', loadMissionControlData);

    // Chat input
    mcElements.sendMessageBtn?.addEventListener('click', handleSendMessage);
    mcElements.messageInput?.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSendMessage();
        }
    });

    // Auto-resize textarea
    mcElements.messageInput?.addEventListener('input', function() {
        this.style.height = 'auto';
        this.style.height = Math.min(this.scrollHeight, 120) + 'px';
    });

    // Decision Desk buttons
    mcElements.rejectChangesBtn?.addEventListener('click', handleRejectChanges);
    mcElements.approveChangesBtn?.addEventListener('click', showApprovalModal);

    // Create Agent Form
    mcElements.createAgentForm?.addEventListener('submit', handleCreateAgent);

    // Panic confirmation input
    mcElements.panicConfirmInput?.addEventListener('input', function() {
        mcElements.confirmPanicBtn.disabled = this.value !== 'PAUSE';
    });

    // Confirmation checklist for approval
    const reviewCheck = document.getElementById('reviewCheck');
    const testCheck = document.getElementById('testCheck');
    const freezeCheck = document.getElementById('freezeCheck');

    const updateApprovalButton = () => {
        mcElements.finalApprovalBtn.disabled = !(reviewCheck?.checked && testCheck?.checked && freezeCheck?.checked);
    };

    reviewCheck?.addEventListener('change', updateApprovalButton);
    testCheck?.addEventListener('change', updateApprovalButton);
    freezeCheck?.addEventListener('change', updateApprovalButton);

    // Final approval button
    mcElements.finalApprovalBtn?.addEventListener('click', handleFinalApproval);

    // Diff view toggle buttons
    document.querySelectorAll('.btn-diff-toggle').forEach(btn => {
        btn.addEventListener('click', (e) => {
            document.querySelectorAll('.btn-diff-toggle').forEach(b => b.classList.remove('active'));
            e.target.classList.add('active');
            // In a real implementation, this would switch the diff view
        });
    });
}

/**
 * Load initial Mission Control data
 */
async function loadMissionControlData() {
    try {
        // Fetch agents, messages, and spec data in parallel
        const [agentsData, messagesData, specData] = await Promise.all([
            fetchAgents().catch(() => ({ agents: [] })),
            fetchProjectMessages(mcState.currentProjectId).catch(() => ({ messages: [] })),
            fetchCurrentSpec().catch(() => null),
        ]);

        // Update state
        mcState.agents = agentsData.agents || [];
        mcState.messages = messagesData.messages || [];
        mcState.currentSpec = specData;

        // Update UI
        renderAgentList();
        renderChatMessages();
        updatePendingDecisionsBadge();
        renderCurrentSpec();

    } catch (error) {
        console.error('Error loading Mission Control data:', error);
    }
}

/**
 * Fetch current spec data
 */
async function fetchCurrentSpec() {
    // This is a placeholder - in a real implementation, this would call the API
    return {
        id: 'SPEC-001',
        title: 'Frontend Architecture Update',
        version: 'v2.3',
        status: 'WAITING',
        description: 'Update the frontend architecture to use React 19 with Server Components and implement the 3-pane Mission Control layout.',
    };
}

/**
 * Render agent list in left pane
 */
function renderAgentList() {
    if (!mcElements.agentList) return;

    // Update count
    if (mcElements.activeAgentCount) {
        mcElements.activeAgentCount.textContent = mcState.agents.filter(a => a.status === 'online' || a.status === 'active').length;
    }

    if (mcState.agents.length === 0) {
        mcElements.agentList.innerHTML = `
            <div class="empty-state">
                <p>No agents registered</p>
            </div>
        `;
        return;
    }

    mcElements.agentList.innerHTML = mcState.agents.map(agent => createAgentItem(agent)).join('');
}

/**
 * Create an agent item HTML
 */
function createAgentItem(agent) {
    const { agent_id, nickname, status, role } = agent;

    const statusClass = status === 'online' || status === 'active' ? 'active' : status.toLowerCase();
    const roleIcon = getRoleIcon(role);

    return `
        <div class="agent-item" data-agent-id="${escapeHtml(agent_id)}">
            <div class="agent-avatar ${statusClass}">
                ${roleIcon}
            </div>
            <div class="agent-info">
                <div class="agent-name">${escapeHtml(nickname)}</div>
                <div class="agent-role">${role ? escapeHtml(role) : 'Agent'}</div>
            </div>
            <div class="agent-actions">
                <button class="agent-action-btn pause" onclick="showPanicModal('${escapeHtml(agent_id)}', '${escapeHtml(nickname)}')" title="Pause Agent">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <rect x="6" y="4" width="4" height="16"/>
                        <rect x="14" y="4" width="4" height="16"/>
                    </svg>
                </button>
                <button class="agent-action-btn" onclick="viewAgentKeys('${escapeHtml(agent_id)}')" title="View Keys">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
                        <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
                    </svg>
                </button>
                <button class="agent-action-btn delete" onclick="deleteAgent('${escapeHtml(agent_id)}', '${escapeHtml(nickname)}')" title="Delete Agent">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <polyline points="3 6 5 6 21 6"/>
                        <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
                    </svg>
                </button>
            </div>
        </div>
    `;
}

/**
 * Get role icon SVG
 */
function getRoleIcon(role) {
    const icons = {
        architect: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>',
        developer: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg>',
        qa: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>',
        security: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>',
    };
    return icons[role] || '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/></svg>';
}

/**
 * Render chat messages
 */
function renderChatMessages() {
    if (!mcElements.chatMessages) return;

    const systemMessage = mcElements.chatMessages.querySelector('.chat-system-message');
    let html = systemMessage ? systemMessage.outerHTML : '';

    mcState.messages.forEach(msg => {
        if (msg.sender_type === 'human') {
            html += createHumanMessage(msg);
        } else {
            html += createAgentMessage(msg);
        }
    });

    mcElements.chatMessages.innerHTML = html;

    // Scroll to bottom
    scrollToChatBottom();
}

/**
 * Create human message HTML
 */
function createHumanMessage(msg) {
    const { content, created_at } = msg;
    const time = formatMessageTime(created_at);

    return `
        <div class="chat-message-human">
            <div class="chat-message-bubble-human">
                <div class="message-content">${escapeHtml(content)}</div>
                <div class="message-time">${time}</div>
            </div>
        </div>
    `;
}

/**
 * Create agent message HTML
 */
function createAgentMessage(msg) {
    const { sender, content, model, created_at } = msg;
    const time = formatMessageTime(created_at);

    return `
        <div class="chat-message-agent">
            <div class="chat-message-avatar-agent">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <rect x="3" y="11" width="18" height="10" rx="2"/>
                    <circle cx="12" cy="5" r="2"/>
                    <path d="M12 7v4"/>
                    <line x1="8" y1="16" x2="8" y2="16"/>
                    <line x1="16" y1="16" x2="16" y2="16"/>
                </svg>
            </div>
            <div class="chat-message-bubble-agent">
                <div class="chat-message-header-agent">
                    <span class="chat-message-sender-agent">${escapeHtml(sender)}</span>
                    ${model ? `<span class="chat-message-model-agent">${escapeHtml(model)}</span>` : ''}
                </div>
                <div class="message-content">${escapeHtml(content)}</div>
                <div class="message-time">${time}</div>
            </div>
        </div>
    `;
}

/**
 * Format message time
 */
function formatMessageTime(timestamp) {
    const date = new Date(timestamp);
    const hours = date.getHours().toString().padStart(2, '0');
    const minutes = date.getMinutes().toString().padStart(2, '0');
    return `${hours}:${minutes}`;
}

/**
 * Scroll chat to bottom
 */
function scrollToChatBottom() {
    if (mcElements.chatContainer) {
        mcElements.chatContainer.scrollTop = mcElements.chatContainer.scrollHeight;
    }
}

/**
 * Handle send message
 */
async function handleSendMessage() {
    const content = mcElements.messageInput?.value?.trim();
    if (!content) return;

    // Add to local state immediately
    const message = {
        id: `local_${Date.now()}`,
        sender_type: 'human',
        sender: 'Owner',
        content,
        model: null,
        created_at: new Date().toISOString(),
    };

    mcState.messages.push(message);
    renderChatMessages();

    // Clear input
    if (mcElements.messageInput) {
        mcElements.messageInput.value = '';
        mcElements.messageInput.style.height = 'auto';
    }

    try {
        // Send to server
        await sendProjectMessage(mcState.currentProjectId, {
            from_agent: 'owner',
            content,
            message_type: 'statement',
        });
    } catch (error) {
        console.error('Error sending message:', error);
    }
}

/**
 * Update pending decisions badge
 */
function updatePendingDecisionsBadge() {
    mcState.pendingDecisions = mcState.agents.filter(a => a.status === 'pending_approval').length;

    if (mcElements.pendingDecisionsBadge) {
        mcElements.pendingDecisionsBadge.textContent = `${mcState.pendingDecisions} Pending`;
        mcElements.pendingDecisionsBadge.style.display = mcState.pendingDecisions > 0 ? 'block' : 'none';
    }
}

/**
 * Render current spec card
 */
function renderCurrentSpec() {
    if (!mcElements.currentSpecCard || !mcState.currentSpec) return;

    const spec = mcState.currentSpec;
    const statusClass = spec.status?.toLowerCase() || 'draft';

    mcElements.currentSpecCard.innerHTML = `
        <div class="spec-header">
            <div class="spec-title">${escapeHtml(spec.title)}</div>
            <span class="spec-status status-${statusClass}">${spec.status}</span>
        </div>
        <div class="spec-meta">
            <span class="spec-id">${escapeHtml(spec.id)}</span>
            <span class="spec-version">${escapeHtml(spec.version)}</span>
        </div>
        <div class="spec-description">${escapeHtml(spec.description)}</div>
    `;
}

/**
 * Handle reject changes
 */
function handleRejectChanges() {
    const reason = prompt('Please provide a reason for rejection:');
    if (!reason) return;

    // In a real implementation, this would call the API
    console.log('Rejected with reason:', reason);

    // Show system message
    addSystemMessage('Changes rejected. Reason: ' + reason);
}

/**
 * Show approval modal
 */
function showApprovalModal() {
    if (mcElements.approvalModal) {
        mcElements.approvalModal.style.display = 'flex';
    }
}

/**
 * Handle final approval
 */
async function handleFinalApproval() {
    const comment = mcElements.approvalComment?.value || '';

    // In a real implementation, this would call the API
    console.log('Approved with comment:', comment);

    closeModal('approvalModal');

    // Show system message
    addSystemMessage('Changes approved and spec frozen successfully.');
}

/**
 * Add system message to chat
 */
function addSystemMessage(content) {
    const html = `
        <div class="chat-system-message">
            <span class="system-message-content">${escapeHtml(content)}</span>
        </div>
    `;

    if (mcElements.chatMessages) {
        mcElements.chatMessages.insertAdjacentHTML('beforeend', html);
        scrollToChatBottom();
    }
}

/**
 * Handle create agent
 */
async function handleCreateAgent(e) {
    e.preventDefault();

    const role = document.getElementById('agentRole')?.value;
    const name = document.getElementById('agentName')?.value;
    const accessLevels = Array.from(document.querySelectorAll('input[name="accessLevel"]:checked'))
        .map(cb => cb.value);

    if (!role || !name) {
        alert('Please fill in all required fields');
        return;
    }

    try {
        // In a real implementation, this would call the API
        console.log('Creating agent:', { role, name, accessLevels });

        closeModal('createAgentModal');

        // Add system message
        addSystemMessage(`Agent "${name}" created successfully with role: ${role}`);

        // Reload data
        await loadMissionControlData();

    } catch (error) {
        console.error('Error creating agent:', error);
        alert('Failed to create agent: ' + error.message);
    }
}

/**
 * Show panic modal
 */
function showPanicModal(agentId, nickname) {
    mcState.selectedAgentId = agentId;

    if (mcElements.panicModal) {
        mcElements.panicModal.style.display = 'flex';
    }

    if (mcElements.panicConfirmInput) {
        mcElements.panicConfirmInput.value = '';
        mcElements.confirmPanicBtn.disabled = true;
    }
}

/**
 * View agent keys
 */
function viewAgentKeys(agentId) {
    // In a real implementation, this would show the agent's API keys
    alert(`View keys for agent: ${agentId}\n\nThis would show the agent's API key information.`);
}

/**
 * Delete agent
 */
function deleteAgent(agentId, nickname) {
    const confirmed = confirm(`Are you sure you want to delete agent "${nickname}"?\n\nThis action cannot be undone.`);

    if (!confirmed) return;

    // In a real implementation, this would call the API
    console.log('Deleting agent:', agentId);

    addSystemMessage(`Agent "${nickname}" deleted.`);

    // Reload data
    loadMissionControlData();
}

/**
 * Connect Mission Control WebSocket
 */
function connectMissionControlWebSocket() {
    connectWebSocket(
        handleMCWebSocketMessage,
        onMCWebSocketConnect,
        onMCWebSocketDisconnect
    );
}

/**
 * Handle Mission Control WebSocket message
 */
function handleMCWebSocketMessage(data) {
    const { type, data: eventData } = data;

    switch (type) {
        case 'agent_status_change':
            handleMCAgentStatusChange(eventData);
            break;
        case 'new_message':
            handleMCNewMessage(eventData);
            break;
        case 'spec_update':
            handleMCSpecUpdate(eventData);
            break;
    }
}

/**
 * Handle agent status change
 */
function handleMCAgentStatusChange(data) {
    const { agent_id, new_status } = data;

    const agentIndex = mcState.agents.findIndex(a => a.agent_id === agent_id);
    if (agentIndex !== -1) {
        mcState.agents[agentIndex].status = new_status;
        renderAgentList();
    }
}

/**
 * Handle new message
 */
function handleMCNewMessage(data) {
    mcState.messages.push(data);
    renderChatMessages();
}

/**
 * Handle spec update
 */
function handleMCSpecUpdate(data) {
    mcState.currentSpec = data;
    renderCurrentSpec();
    updatePendingDecisionsBadge();
}

/**
 * WebSocket connected callback
 */
function onMCWebSocketConnect() {
    mcState.wsConnected = true;
    updateMCConnectionStatus('connected');
}

/**
 * WebSocket disconnected callback
 */
function onMCWebSocketDisconnect() {
    mcState.wsConnected = false;
    updateMCConnectionStatus('disconnected');
}

/**
 * Update connection status display
 */
function updateMCConnectionStatus(status) {
    if (!mcElements.wsConnectionStatus) return;

    const badge = mcElements.wsConnectionStatus;
    const dot = badge.querySelector('.status-dot');
    const text = badge.querySelector('.status-text');

    if (!dot || !text) return;

    // Remove all status classes
    badge.classList.remove('connected', 'connecting', 'disconnected');
    dot.classList.remove('connected', 'connecting', 'disconnected');

    // Add current status
    badge.classList.add(status);
    dot.classList.add(status);

    // Update text
    const statusTexts = {
        connected: 'Connected',
        connecting: 'Connecting...',
        disconnected: 'Disconnected',
    };
    text.textContent = statusTexts[status] || status;
}

/**
 * Close modal
 */
function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.style.display = 'none';
    }
}

/**
 * Show budget modal (placeholder)
 */
function showBudgetModal() {
    alert('Budget settings modal\n\nThis would open the budget configuration modal.');
}

/**
 * Show security modal (placeholder)
 */
function showSecurityModal() {
    alert('Security settings modal\n\nThis would open the security configuration modal.');
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
window.closeModal = closeModal;
window.showPanicModal = showPanicModal;
window.viewAgentKeys = viewAgentKeys;
window.deleteAgent = deleteAgent;
window.showBudgetModal = showBudgetModal;
window.showSecurityModal = showSecurityModal;

// Initialize Mission Control when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initMissionControl);
} else {
    initMissionControl();
}

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    disconnectWebSocket();
});
