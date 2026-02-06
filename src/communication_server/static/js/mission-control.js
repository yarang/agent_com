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
    tasks: [],  // Task management state
    currentSpec: null,
    pendingDecisions: 0,
    wsConnected: false,
    currentProjectId: null,  // Will be set when projects load
    projects: [],
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

    // Project Management
    projectSelect: null,
    createProjectBtn: null,

    // Task Management
    tasksList: null,
    refreshTasksBtn: null,
    createTaskBtn: null,
    taskStatusFilter: null,

    // Modals
    createAgentModal: null,
    panicModal: null,
    approvalModal: null,
    createProjectModal: null,
    createAgentForm: null,
    createProjectForm: null,
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

    // Load projects first, then load other data
    await loadProjects();

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

    // Task Management
    mcElements.tasksList = document.getElementById('tasksList');
    mcElements.refreshTasksBtn = document.getElementById('refreshTasksBtn');
    mcElements.createTaskBtn = document.getElementById('createTaskBtn');
    mcElements.taskStatusFilter = document.getElementById('taskStatusFilter');
    mcElements.pendingDecisionsBadge = document.getElementById('pendingDecisionsBadge');
    mcElements.diffViewer = document.getElementById('diffViewer');
    mcElements.rejectChangesBtn = document.getElementById('rejectChangesBtn');
    mcElements.approveChangesBtn = document.getElementById('approveChangesBtn');

    // Connection Status
    mcElements.wsConnectionStatus = document.getElementById('wsConnectionStatus');

    // Project Management
    mcElements.projectSelect = document.getElementById('projectSelect');
    mcElements.createProjectBtn = document.getElementById('createProjectBtn');

    // Modals
    mcElements.createAgentModal = document.getElementById('createAgentModal');
    mcElements.panicModal = document.getElementById('panicModal');
    mcElements.approvalModal = document.getElementById('approvalModal');
    mcElements.createProjectModal = document.getElementById('createProjectModal');
    mcElements.createAgentForm = document.getElementById('createAgentForm');
    mcElements.createProjectForm = document.getElementById('createProjectForm');
    mcElements.panicConfirmInput = document.getElementById('panicConfirmInput');
    mcElements.confirmPanicBtn = document.getElementById('confirmPanicBtn');
    mcElements.finalApprovalBtn = document.getElementById('finalApprovalBtn');
    mcElements.approvalComment = document.getElementById('approvalComment');
}

/**
 * Set up event listeners
 */
function setupMCEventListeners() {
    // Project selection
    mcElements.projectSelect?.addEventListener('change', onProjectChange);

    // Create project button
    mcElements.createProjectBtn?.addEventListener('click', showCreateProjectModal);

    // Refresh agents button
    mcElements.refreshAgentsBtn?.addEventListener('click', loadMissionControlData);

    // Task management event listeners
    mcElements.refreshTasksBtn?.addEventListener('click', loadMissionControlData);
    mcElements.createTaskBtn?.addEventListener('click', showCreateTaskModal);
    mcElements.taskStatusFilter?.addEventListener('change', renderTaskList);

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

    // Create Project Form
    mcElements.createProjectForm?.addEventListener('submit', handleCreateProject);

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
        // If no project selected, show empty state
        if (!mcState.currentProjectId) {
            mcState.agents = [];
            mcState.messages = [];
            mcState.tasks = [];
            renderAgentList();
            renderChatMessages();
            renderTaskList();
            return;
        }

        // Fetch agents, messages, tasks, and spec for current project in parallel
        const [agentsData, messagesData, tasksData, specData] = await Promise.all([
            fetchAgentsList({ project_id: mcState.currentProjectId }).catch(() => ({ agents: [] })),
            fetchProjectMessages(mcState.currentProjectId).catch(() => ({ messages: [] })),
            fetchTasks({ project_id: mcState.currentProjectId }).catch(() => ({ tasks: [] })),
            fetchCurrentSpec().catch(() => null),
        ]);

        // Update state
        mcState.agents = agentsData.agents || [];
        mcState.messages = messagesData.messages || [];
        mcState.tasks = tasksData.tasks || [];
        mcState.currentSpec = specData;

        // Update UI
        renderAgentList();
        renderChatMessages();
        renderTaskList();
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

// ==================== Project Management Functions ====================

/**
 * Load projects and populate dropdown
 */
async function loadProjects() {
    try {
        console.log('Loading projects...');
        const data = await fetchProjects();

        if (!data || !data.projects) {
            console.warn('No projects data received');
            return;
        }

        mcState.projects = data.projects;

        // Populate dropdown
        populateProjectDropdown();

        // Auto-select first project if available and no current project
        if (mcState.projects.length > 0 && !mcState.currentProjectId) {
            const firstProject = mcState.projects[0];
            if (firstProject.project_id) {
                mcState.currentProjectId = firstProject.project_id;
                mcElements.projectSelect.value = firstProject.project_id;
                await loadMissionControlData();
            }
        }

        console.log(`Loaded ${mcState.projects.length} projects`);
    } catch (error) {
        console.error('Error loading projects:', error);
        // Show error in dropdown
        if (mcElements.projectSelect) {
            mcElements.projectSelect.innerHTML = '<option value="">Error loading projects</option>';
        }
    }
}

/**
 * Populate project dropdown with projects
 */
function populateProjectDropdown() {
    if (!mcElements.projectSelect) return;

    mcElements.projectSelect.innerHTML = '';

    if (mcState.projects.length === 0) {
        mcElements.projectSelect.innerHTML = '<option value="">No projects available</option>';
        return;
    }

    mcState.projects.forEach(project => {
        if (!project.project_id) return;

        const option = document.createElement('option');
        option.value = project.project_id;
        option.textContent = project.name ? `${project.name} (${project.project_id})` : project.project_id;
        mcElements.projectSelect.appendChild(option);
    });
}

/**
 * Handle project selection change
 */
async function onProjectChange(event) {
    const newProjectId = event.target.value;

    if (!newProjectId) {
        mcState.currentProjectId = null;
        mcState.agents = [];
        mcState.messages = [];
        renderAgentList();
        renderChatMessages();
        return;
    }

    console.log(`Project changed to: ${newProjectId}`);
    mcState.currentProjectId = newProjectId;

    // Reload data for new project
    await loadMissionControlData();

    // Update connection status
    updateMCConnectionStatus('connected');
}

/**
 * Show create project modal
 */
function showCreateProjectModal() {
    // Check if modal exists in DOM
    let modal = document.getElementById('createProjectModal');

    if (!modal) {
        // Create modal dynamically
        modal = document.createElement('div');
        modal.id = 'createProjectModal';
        modal.className = 'modal';
        modal.innerHTML = `
            <div class="modal-overlay"></div>
            <div class="modal-content">
                <div class="modal-header">
                    <h3>Create New Project</h3>
                    <button class="btn-close" onclick="closeModal('createProjectModal')">&times;</button>
                </div>
                <div class="modal-body">
                    <form id="createProjectForm">
                        <div class="form-group">
                            <label for="newProjectId">Project ID</label>
                            <input type="text" id="newProjectId" class="form-control" placeholder="my_project" required pattern="[a-z0-9_]+" title="Use lowercase letters, numbers, and underscores only">
                            <small class="form-hint">Use lowercase letters, numbers, and underscores</small>
                        </div>
                        <div class="form-group">
                            <label for="newProjectName">Project Name</label>
                            <input type="text" id="newProjectName" class="form-control" placeholder="My Project" required>
                        </div>
                        <div class="form-group">
                            <label for="newProjectDescription">Description</label>
                            <textarea id="newProjectDescription" class="form-control" rows="3" placeholder="Project description..."></textarea>
                        </div>
                        <div class="form-actions">
                            <button type="button" class="btn btn-secondary" onclick="closeModal('createProjectModal')">Cancel</button>
                            <button type="submit" class="btn btn-primary">Create Project</button>
                        </div>
                    </form>
                </div>
            </div>
        `;
        document.body.appendChild(modal);

        // Add event listener to form
        const form = modal.querySelector('#createProjectForm');
        form.addEventListener('submit', handleCreateProject);
    }

    modal.style.display = 'flex';
}

/**
 * Handle create project form submission
 */
async function handleCreateProject(event) {
    event.preventDefault();

    const projectId = document.getElementById('newProjectId')?.value?.trim();
    const projectName = document.getElementById('newProjectName')?.value?.trim();
    const projectDescription = document.getElementById('newProjectDescription')?.value?.trim();

    if (!projectId || !projectName) {
        alert('Please fill in all required fields');
        return;
    }

    try {
        console.log('Creating project:', { projectId, projectName });

        const result = await createProject({
            project_id: projectId,
            name: projectName,
            description: projectDescription || '',
        });

        // Close modal
        closeModal('createProjectModal');

        // Add system message
        addSystemMessage(`Project "${projectName}" created successfully.`);

        // Reload projects
        await loadProjects();

        // Select the newly created project
        if (mcElements.projectSelect) {
            mcElements.projectSelect.value = projectId;
            await onProjectChange({ target: mcElements.projectSelect });
        }

    } catch (error) {
        console.error('Error creating project:', error);
        alert('Failed to create project: ' + (error.message || 'Unknown error'));
    }
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
window.loadProjects = loadProjects;
window.onProjectChange = onProjectChange;
window.showCreateProjectModal = showCreateProjectModal;
window.handleCreateProject = handleCreateProject;

// ==================== Task Management Functions ====================

/**
 * Render task list in the Tasks section
 */
function renderTaskList() {
    if (!mcElements.tasksList) return;

    // Get filter value
    const statusFilter = mcElements.taskStatusFilter?.value || '';

    // Filter tasks based on selected status
    let filteredTasks = mcState.tasks;
    if (statusFilter) {
        filteredTasks = mcState.tasks.filter(task => task.status === statusFilter);
    }

    if (filteredTasks.length === 0) {
        mcElements.tasksList.innerHTML = `
            <div class="empty-state">
                <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                    <path d="M9 11l3 3L22 4"/>
                    <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/>
                </svg>
                <p>No tasks found</p>
                ${statusFilter ? '<small>Try clearing the status filter</small>' : '<small>Create a task to get started</small>'}
            </div>
        `;
        return;
    }

    mcElements.tasksList.innerHTML = filteredTasks.map(task => createTaskItem(task)).join('');
}

/**
 * Create a task item HTML
 * @param {Object} task - Task object
 * @returns {string} HTML string for task item
 */
function createTaskItem(task) {
    const { id, title, description, status, priority, assigned_to, due_date } = task;

    // Status badge styling
    const statusConfig = {
        pending: { class: 'status-pending', label: 'Pending' },
        in_progress: { class: 'status-in-progress', label: 'In Progress' },
        review: { class: 'status-review', label: 'Review' },
        completed: { class: 'status-completed', label: 'Completed' },
        blocked: { class: 'status-blocked', label: 'Blocked' },
    };

    const statusInfo = statusConfig[status] || { class: 'status-pending', label: status };

    // Priority badge styling
    const priorityConfig = {
        low: { class: 'priority-low', label: 'Low' },
        medium: { class: 'priority-medium', label: 'Medium' },
        high: { class: 'priority-high', label: 'High' },
        critical: { class: 'priority-critical', label: 'Critical' },
    };

    const priorityInfo = priorityConfig[priority] || { class: 'priority-medium', label: priority || 'Medium' };

    // Find assigned agent name
    const assignedAgent = assigned_to ? mcState.agents.find(a => a.id === assigned_to || a.agent_id === assigned_to) : null;
    const assignedAgentName = assignedAgent?.nickname || assignedAgent?.name || 'Unassigned';

    // Format due date
    let dueDateDisplay = '';
    if (due_date) {
        const dueDate = new Date(due_date);
        const now = new Date();
        const isOverdue = dueDate < now && status !== 'completed';
        dueDateDisplay = `
            <div class="task-due-date ${isOverdue ? 'overdue' : ''}">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <circle cx="12" cy="12" r="10"/>
                    <polyline points="12 6 12 12 16 14"/>
                </svg>
                <span>${dueDate.toLocaleDateString()}</span>
            </div>
        `;
    }

    return `
        <div class="task-item" data-task-id="${escapeHtml(id)}">
            <div class="task-header">
                <div class="task-status-badges">
                    <span class="task-status-badge ${statusInfo.class}">${statusInfo.label}</span>
                    <span class="task-priority-badge ${priorityInfo.class}">${priorityInfo.label}</span>
                </div>
                <div class="task-actions">
                    <button class="task-action-btn" onclick="handleTaskStatusUpdate('${escapeHtml(id)}', 'completed')" title="Mark Complete">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <polyline points="20 6 9 17 4 12"/>
                        </svg>
                    </button>
                    <button class="task-action-btn" onclick="handleTaskEdit('${escapeHtml(id)}')" title="Edit Task">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
                            <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
                        </svg>
                    </button>
                    <button class="task-action-btn" onclick="handleTaskDelete('${escapeHtml(id)}')" title="Delete Task">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <polyline points="3 6 5 6 21 6"/>
                            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
                        </svg>
                    </button>
                </div>
            </div>
            <div class="task-content">
                <div class="task-title">${escapeHtml(title)}</div>
                ${description ? `<div class="task-description">${escapeHtml(description)}</div>` : ''}
            </div>
            <div class="task-footer">
                <div class="task-assignment">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
                        <circle cx="12" cy="7" r="4"/>
                    </svg>
                    <span>${escapeHtml(assignedAgentName)}</span>
                </div>
                ${dueDateDisplay}
            </div>
        </div>
    `;
}

/**
 * Handle task creation
 * @param {Object} taskData - Task data from form
 */
async function handleCreateTask(taskData) {
    try {
        const result = await createTask({
            ...taskData,
            project_id: mcState.currentProjectId,
        });

        // Show success message
        showNotification('Task created successfully', 'success');

        // Reload tasks
        await loadMissionControlData();

        return result;
    } catch (error) {
        console.error('Error creating task:', error);
        showNotification('Failed to create task: ' + (error.message || 'Unknown error'), 'error');
        throw error;
    }
}

/**
 * Handle task status update
 * @param {string} taskId - Task ID
 * @param {string} newStatus - New status
 */
async function handleTaskStatusUpdate(taskId, newStatus) {
    try {
        await updateTask(taskId, { status: newStatus });
        showNotification('Task status updated', 'success');
        await loadMissionControlData();
    } catch (error) {
        console.error('Error updating task status:', error);
        showNotification('Failed to update task status', 'error');
    }
}

/**
 * Handle task edit (opens edit modal)
 * @param {string} taskId - Task ID
 */
function handleTaskEdit(taskId) {
    // For now, just show an alert - in future, open an edit modal
    const task = mcState.tasks.find(t => t.id === taskId);
    if (task) {
        alert(`Edit Task: ${task.title}\n\nThis will open an edit modal in a future update.`);
    }
}

/**
 * Handle task deletion
 * @param {string} taskId - Task ID
 */
async function handleTaskDelete(taskId) {
    if (!confirm('Are you sure you want to delete this task?')) {
        return;
    }

    try {
        await deleteTask(taskId);
        showNotification('Task deleted successfully', 'success');
        await loadMissionControlData();
    } catch (error) {
        console.error('Error deleting task:', error);
        showNotification('Failed to delete task', 'error');
    }
}

/**
 * Assign task to an agent
 * @param {string} taskId - Task ID
 */
async function handleAssignTaskToAgent(taskId) {
    // Get list of available agents
    const agentOptions = mcState.agents.map(agent => {
        const id = agent.id || agent.agent_id;
        const name = agent.nickname || agent.name;
        return `${id}:${name}`;
    }).join('\n');

    if (mcState.agents.length === 0) {
        showNotification('No agents available to assign', 'warning');
        return;
    }

    const selection = prompt(
        'Enter agent ID to assign:\n\n' +
        mcState.agents.map(agent => {
            const id = agent.id || agent.agent_id;
            const name = agent.nickname || agent.name;
            return `- ${id}: ${name}`;
        }).join('\n')
    );

    if (!selection) return;

    try {
        await assignTask(taskId, { assigned_to: selection });
        showNotification('Task assigned successfully', 'success');
        await loadMissionControlData();
    } catch (error) {
        console.error('Error assigning task:', error);
        showNotification('Failed to assign task', 'error');
    }
}

/**
 * Show notification message
 * @param {string} message - Notification message
 * @param {string} type - Notification type (success, error, warning, info)
 */
function showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.innerHTML = `
        <span>${escapeHtml(message)}</span>
        <button class="notification-close" onclick="this.parentElement.remove()">&times;</button>
    `;

    // Add to page
    document.body.appendChild(notification);

    // Auto-remove after 3 seconds
    setTimeout(() => {
        notification.remove();
    }, 3000);
}

/**
 * Show create task modal
 */
function showCreateTaskModal() {
    // Create modal HTML
    const modalHtml = `
        <div class="modal" id="createTaskModal" style="display: flex;">
            <div class="modal-overlay" onclick="closeModal('createTaskModal')"></div>
            <div class="modal-content">
                <div class="modal-header">
                    <h3>Create New Task</h3>
                    <button class="btn-close" onclick="closeModal('createTaskModal')">&times;</button>
                </div>
                <div class="modal-body">
                    <form id="createTaskForm">
                        <div class="form-group">
                            <label for="taskTitle">Title *</label>
                            <input type="text" id="taskTitle" class="form-control" placeholder="Enter task title" required>
                        </div>
                        <div class="form-group">
                            <label for="taskDescription">Description</label>
                            <textarea id="taskDescription" class="form-control" rows="3" placeholder="Enter task description"></textarea>
                        </div>
                        <div class="form-row">
                            <div class="form-group">
                                <label for="taskPriority">Priority</label>
                                <select id="taskPriority" class="form-control">
                                    <option value="low">Low</option>
                                    <option value="medium" selected>Medium</option>
                                    <option value="high">High</option>
                                    <option value="critical">Critical</option>
                                </select>
                            </div>
                            <div class="form-group">
                                <label for="taskStatus">Status</label>
                                <select id="taskStatus" class="form-control">
                                    <option value="pending" selected>Pending</option>
                                    <option value="in_progress">In Progress</option>
                                    <option value="review">Review</option>
                                    <option value="blocked">Blocked</option>
                                </select>
                            </div>
                        </div>
                        <div class="form-group">
                            <label for="taskAssignee">Assign To</label>
                            <select id="taskAssignee" class="form-control">
                                <option value="">Unassigned</option>
                                ${mcState.agents.map(agent => {
                                    const id = agent.id || agent.agent_id;
                                    const name = agent.nickname || agent.name;
                                    return `<option value="${escapeHtml(id)}">${escapeHtml(name)}</option>`;
                                }).join('')}
                            </select>
                        </div>
                        <div class="form-group">
                            <label for="taskDueDate">Due Date (optional)</label>
                            <input type="datetime-local" id="taskDueDate" class="form-control">
                        </div>
                        <div class="modal-actions">
                            <button type="button" class="btn btn-secondary" onclick="closeModal('createTaskModal')">Cancel</button>
                            <button type="submit" class="btn btn-primary">Create Task</button>
                        </div>
                    </form>
                </div>
            </div>
        </div>
    `;

    // Remove existing modal if present
    const existingModal = document.getElementById('createTaskModal');
    if (existingModal) {
        existingModal.remove();
    }

    // Add modal to page
    document.body.insertAdjacentHTML('beforeend', modalHtml);

    // Set up form submission
    const form = document.getElementById('createTaskForm');
    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        const taskData = {
            title: document.getElementById('taskTitle').value.trim(),
            description: document.getElementById('taskDescription').value.trim(),
            priority: document.getElementById('taskPriority').value,
            status: document.getElementById('taskStatus').value,
            assigned_to: document.getElementById('taskAssignee').value || null,
            due_date: document.getElementById('taskDueDate').value || null,
        };

        await handleCreateTask(taskData);
        closeModal('createTaskModal');
    });
}

// Make task functions globally available
window.handleTaskStatusUpdate = handleTaskStatusUpdate;
window.handleTaskEdit = handleTaskEdit;
window.handleTaskDelete = handleTaskDelete;
window.handleAssignTaskToAgent = handleAssignTaskToAgent;
window.handleCreateTask = handleCreateTask;
window.showNotification = showNotification;
window.showCreateTaskModal = showCreateTaskModal;

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
