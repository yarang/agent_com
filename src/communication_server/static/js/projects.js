/**
 * Project Sidebar Component for AI Agent Communication System
 *
 * Manages the project sidebar with chat-like channel listing
 * and project-based agent filtering.
 */

// Project state
let projects = [];
let selectedProjectId = null; // null = "All Agents"
let sidebarCollapsed = false;

// DOM projectElements
const projectElements = {
    projectSidebar: null,
    projectList: null,
    sidebarToggle: null,
    sidebarExpand: null,
    mainContent: null,
};

/**
 * Initialize the project sidebar
 */
async function initProjectSidebar() {
    console.log('Initializing project sidebar...');

    // Cache DOM projectElements
    projectElements.projectSidebar = document.getElementById('projectSidebar');
    projectElements.projectList = document.getElementById('projectList');
    projectElements.sidebarToggle = document.getElementById('sidebarToggle');
    projectElements.sidebarExpand = document.getElementById('sidebarExpand');
    projectElements.mainContent = document.querySelector('.main');

    if (!projectElements.projectSidebar) {
        console.warn('Project sidebar element not found');
        return;
    }

    // Set up toggle buttons
    projectElements.sidebarToggle?.addEventListener('click', toggleSidebar);
    projectElements.sidebarExpand?.addEventListener('click', toggleSidebar);

    // Load collapsed state from localStorage
    const savedCollapsed = localStorage.getItem('sidebarCollapsed');
    if (savedCollapsed === 'true') {
        sidebarCollapsed = true;
        projectElements.projectSidebar.classList.add('collapsed');
        projectElements.mainContent?.classList.add('sidebar-collapsed');
        updateToggleButtonIcon();
    }

    // Load selected project from localStorage
    const savedProject = localStorage.getItem('selectedProjectId');
    if (savedProject) {
        selectedProjectId = savedProject === 'null' ? null : savedProject;
    }

    // Load initial projects
    await loadProjects();

    // Set up keyboard shortcuts
    setupKeyboardShortcuts();

    console.log('Project sidebar initialized');
}

/**
 * Load projects from API
 */
async function loadProjects() {
    try {
        const data = await fetchProjects();
        projects = data.projects || [];
        renderProjectList();

        // Update messages project filter
        if (typeof updateProjectFilter === 'function') {
            updateProjectFilter(projects);
        }
    } catch (error) {
        console.error('Failed to load projects:', error);
    }
}

/**
 * Render the project list
 */
function renderProjectList() {
    if (!projectElements.projectList) return;

    projectElements.projectList.innerHTML = projects.map(project => {
        const isSelected = (project.project_id === null && selectedProjectId === null) ||
                          project.project_id === selectedProjectId;
        const selectedClass = isSelected ? 'selected' : '';
        const onlineClass = project.is_online ? 'online' : 'offline';
        const pid = project.project_id || '';

        // Don't show action buttons for "All Agents"
        const actionButtons = project.project_id ? `
            <button class="project-action-btn" data-action="chat" data-project-id="${pid}" title="Open chat">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
                </svg>
            </button>
            <button class="project-action-btn" data-action="edit" data-project-id="${pid}" title="Edit project">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
                    <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
                </svg>
            </button>
            <button class="project-action-btn" data-action="delete" data-project-id="${pid}" title="Delete project">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polyline points="3 6 5 6 21 6"></polyline>
                    <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                </svg>
            </button>
        ` : '';

        return `
            <div class="project-channel ${selectedClass}"
                 data-project-id="${pid}"
                 ondblclick="handleProjectDblClick('${pid}')">
                <div class="project-icon"
                     onclick="selectProject('${pid}')">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        ${project.project_id === null
                            ? '<circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/>'
                            : '<rect x="3" y="3" width="18" height="18" rx="2"/><path d="M9 3v18"/><path d="M15 3v18"/>'
                        }
                    </svg>
                </div>
                <div class="project-info" onclick="selectProject('${pid}')">
                    <span class="project-name">${escapeHtml(project.name)}</span>
                    <span class="agent-count">${project.agent_count}</span>
                </div>
                <div class="project-status ${onlineClass}"></div>
                ${actionButtons}
            </div>
        `;
    }).join('');

    // Setup action button handlers
    setupProjectActionButtons();
}

/**
 * Setup project action button handlers
 */
function setupProjectActionButtons() {
    document.querySelectorAll('.project-action-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            const action = btn.dataset.action;
            const projectId = btn.dataset.projectId;

            switch (action) {
                case 'chat':
                    openProjectChatRoom(projectId);
                    break;
                case 'edit':
                    showEditProjectModal(projectId);
                    break;
                case 'delete':
                    confirmDeleteProject(projectId);
                    break;
            }
        });
    });
}

/**
 * Handle project double-click - open chat room
 * @param {string} projectId - Project ID
 */
function handleProjectDblClick(projectId) {
    if (projectId && typeof openProjectChatRoom === 'function') {
        openProjectChatRoom(projectId);
    }
}

/**
 * Select a project and filter agents
 * @param {string} projectId - Project ID (empty string for "All Agents")
 */
async function selectProject(projectId) {
    const pid = projectId === '' ? null : projectId;
    selectedProjectId = pid;

    // Save to localStorage
    localStorage.setItem('selectedProjectId', pid === null ? 'null' : pid);

    // Update UI
    renderProjectList();

    // Update messages project filter dropdown
    const messageFilter = document.getElementById('messageProjectFilter');
    if (messageFilter) {
        messageFilter.value = pid || '';
    }

    // Filter agents - this will trigger a reload in dashboard.js
    if (typeof refreshData === 'function') {
        await refreshData();
    }
}

/**
 * Toggle sidebar collapse state
 */
function toggleSidebar() {
    sidebarCollapsed = !sidebarCollapsed;
    projectElements.projectSidebar.classList.toggle('collapsed', sidebarCollapsed);
    projectElements.mainContent?.classList.toggle('sidebar-collapsed', sidebarCollapsed);

    // Update toggle button icon
    updateToggleButtonIcon();

    // Save state
    localStorage.setItem('sidebarCollapsed', sidebarCollapsed);
}

/**
 * Update toggle button icon based on collapsed state
 */
function updateToggleButtonIcon() {
    if (!projectElements.sidebarToggle) return;

    const icon = sidebarCollapsed
        ? `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="11 17 6 12 11 7"/>
            <polyline points="18 17 13 12 18 7"/>
           </svg>`
        : `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="13 7 18 12 13 17"/>
            <polyline points="6 7 11 12 6 17"/>
           </svg>`;

    projectElements.sidebarToggle.innerHTML = icon;
    projectElements.sidebarToggle.title = sidebarCollapsed ? '접기 / Collapse' : '펼치기 / Expand';
}

/**
 * Get the currently selected project ID
 * @returns {string|null} Project ID or null for "All Agents"
 */
function getSelectedProjectId() {
    return selectedProjectId;
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
 * Setup keyboard shortcuts for project switching
 */
function setupKeyboardShortcuts() {
    document.addEventListener('keydown', (e) => {
        // Cmd/Ctrl + number to switch projects
        if ((e.metaKey || e.ctrlKey) && e.key >= '1' && e.key <= '9') {
            e.preventDefault();
            const index = parseInt(e.key) - 1;
            if (index < projects.length) {
                const project = projects[index];
                selectProject(project.project_id || '');
            }
        }
    });
}

// Make functions globally available
window.initProjectSidebar = initProjectSidebar;
window.selectProject = selectProject;
window.getSelectedProjectId = getSelectedProjectId;
window.loadProjects = loadProjects;
window.renderProjectList = renderProjectList;
window.toggleSidebar = toggleSidebar;
window.handleProjectDblClick = handleProjectDblClick;

// Auto-initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initProjectSidebar);
} else {
    initProjectSidebar();
}
