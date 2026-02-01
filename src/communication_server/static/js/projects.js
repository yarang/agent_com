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

// DOM elements
const elements = {
    projectSidebar: null,
    projectList: null,
    sidebarToggle: null,
    mainContent: null,
};

/**
 * Initialize the project sidebar
 */
async function initProjectSidebar() {
    console.log('Initializing project sidebar...');

    // Cache DOM elements
    elements.projectSidebar = document.getElementById('projectSidebar');
    elements.projectList = document.getElementById('projectList');
    elements.sidebarToggle = document.getElementById('sidebarToggle');
    elements.mainContent = document.querySelector('.main');

    if (!elements.projectSidebar) {
        console.warn('Project sidebar element not found');
        return;
    }

    // Set up toggle button
    elements.sidebarToggle?.addEventListener('click', toggleSidebar);

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
    if (!elements.projectList) return;

    elements.projectList.innerHTML = projects.map(project => {
        const isSelected = (project.project_id === null && selectedProjectId === null) ||
                          project.project_id === selectedProjectId;
        const selectedClass = isSelected ? 'selected' : '';
        const onlineClass = project.is_online ? 'online' : 'offline';

        return `
            <div class="project-channel ${selectedClass}"
                 data-project-id="${project.project_id || ''}"
                 onclick="selectProject('${project.project_id || ''}')">
                <div class="project-icon">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        ${project.project_id === null
                            ? '<circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/>'
                            : '<rect x="3" y="3" width="18" height="18" rx="2"/><path d="M9 3v18"/><path d="M15 3v18"/>'
                        }
                    </svg>
                </div>
                <div class="project-info">
                    <span class="project-name">${escapeHtml(project.name)}</span>
                    <span class="agent-count">${project.agent_count}</span>
                </div>
                <div class="project-status ${onlineClass}"></div>
            </div>
        `;
    }).join('');
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
    elements.projectSidebar.classList.toggle('collapsed', sidebarCollapsed);
    elements.mainContent?.classList.toggle('sidebar-collapsed', sidebarCollapsed);

    // Save state
    localStorage.setItem('sidebarCollapsed', sidebarCollapsed);
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
window.toggleSidebar = toggleSidebar;

// Auto-initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initProjectSidebar);
} else {
    initProjectSidebar();
}
