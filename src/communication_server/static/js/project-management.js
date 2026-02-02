/**
 * Project Management Module
 *
 * Provides UI and functionality for creating, editing, and deleting projects.
 * Includes modal forms for project CRUD operations.
 */

// Modal state
let currentEditingProjectId = null;

/**
 * Initialize project management functionality
 */
function initProjectManagement() {
    console.log('Initializing project management...');

    // Add "New Project" button to project sidebar
    const projectSidebar = document.getElementById('projectSidebar');
    if (projectSidebar) {
        addCreateProjectButton(projectSidebar);
    }

    // Setup modal handlers
    setupProjectModalHandlers();

    console.log('Project management initialized');
}

/**
 * Add "New Project" button to the project sidebar
 */
function addCreateProjectButton(sidebar) {
    const header = sidebar.querySelector('.sidebar-header');
    if (!header) return;

    // Check if button already exists
    if (header.querySelector('#createProjectBtn')) return;

    const createBtn = document.createElement('button');
    createBtn.id = 'createProjectBtn';
    createBtn.className = 'btn btn-primary btn-sm';
    createBtn.innerHTML = `
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="12" y1="5" x2="12" y2="19"></line>
            <line x1="5" y1="12" x2="19" y2="12"></line>
        </svg>
        <span>New Project</span>
    `;
    createBtn.onclick = () => showCreateProjectModal();

    header.appendChild(createBtn);
}

/**
 * Show create project modal
 */
function showCreateProjectModal() {
    currentEditingProjectId = null;
    const modal = getOrCreateProjectModal();

    // Reset form
    const form = document.getElementById('projectForm');
    if (form) {
        form.reset();
        document.getElementById('projectId').readOnly = false;
    }

    // Update title
    const title = document.getElementById('projectModalTitle');
    if (title) title.textContent = 'New Project';

    // Show modal
    modal.classList.add('active');
}

/**
 * Show edit project modal
 * @param {string} projectId - Project ID to edit
 */
async function showEditProjectModal(projectId) {
    currentEditingProjectId = projectId;
    const modal = getOrCreateProjectModal();

    try {
        // Fetch project details
        const project = await getProject(projectId);

        // Populate form
        const form = document.getElementById('projectForm');
        if (form) {
            document.getElementById('projectId').value = project.project_id;
            document.getElementById('projectId').readOnly = true; // Cannot change ID
            document.getElementById('projectName').value = project.name;
            document.getElementById('projectDescription').value = project.description || '';
            document.getElementById('projectTags').value = project.tags ? project.tags.join(', ') : '';
        }

        // Update title
        const title = document.getElementById('projectModalTitle');
        if (title) title.textContent = 'Edit Project';

        // Show modal
        modal.classList.add('active');

    } catch (error) {
        console.error('Failed to load project details:', error);
        showErrorNotification('Failed to load project details');
    }
}

/**
 * Get or create the project modal
 */
function getOrCreateProjectModal() {
    let modal = document.getElementById('projectModal');

    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'projectModal';
        modal.className = 'modal';
        modal.innerHTML = `
            <div class="modal-overlay" onclick="closeProjectModal()"></div>
            <div class="modal-content modal-lg">
                <div class="modal-header">
                    <h3 id="projectModalTitle">New Project</h3>
                    <button class="btn-close" onclick="closeProjectModal()">&times;</button>
                </div>
                <form id="projectForm" class="modal-body">
                    <div class="form-group">
                        <label for="projectId">Project ID *</label>
                        <input type="text" id="projectId" name="project_id"
                               pattern="^[a-z][a-z0-9_]*[a-z0-9]$" required
                               placeholder="my-project">
                        <small class="form-text">Lowercase alphanumeric with underscores (e.g., my_project)</small>
                    </div>
                    <div class="form-group">
                        <label for="projectName">Name *</label>
                        <input type="text" id="projectName" name="name" required
                               placeholder="My Project" maxlength="100">
                    </div>
                    <div class="form-group">
                        <label for="projectDescription">Description</label>
                        <textarea id="projectDescription" name="description"
                                  rows="3" maxlength="500"
                                  placeholder="Brief description of the project"></textarea>
                    </div>
                    <div class="form-group">
                        <label for="projectTags">Tags</label>
                        <input type="text" id="projectTags" name="tags"
                               placeholder="tag1, tag2, tag3">
                        <small class="form-text">Comma-separated tags</small>
                    </div>
                </form>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" onclick="closeProjectModal()">Cancel</button>
                    <button type="submit" form="projectForm" class="btn btn-primary">Save Project</button>
                </div>
            </div>
        `;

        document.body.appendChild(modal);

        // Setup form submission
        const form = modal.querySelector('#projectForm');
        form.onsubmit = handleProjectFormSubmit;
    }

    return modal;
}

/**
 * Setup modal handlers
 */
function setupProjectModalHandlers() {
    // Close modal on escape key
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            closeProjectModal();
        }
    });
}

/**
 * Close project modal
 */
function closeProjectModal() {
    const modal = document.getElementById('projectModal');
    if (modal) {
        modal.classList.remove('active');
    }
    currentEditingProjectId = null;
}

/**
 * Handle project form submission
 * @param {Event} e - Form submit event
 */
async function handleProjectFormSubmit(e) {
    e.preventDefault();

    const form = e.target;
    const formData = new FormData(form);

    const projectData = {
        project_id: formData.get('project_id'),
        name: formData.get('name'),
        description: formData.get('description') || '',
        tags: formData.get('tags') ? formData.get('tags').split(',').map(t => t.trim()).filter(t => t) : [],
    };

    try {
        if (currentEditingProjectId) {
            // Update existing project
            await updateProject(currentEditingProjectId, {
                name: projectData.name,
                description: projectData.description,
                tags: projectData.tags,
            });
            showSuccessNotification(`Project "${projectData.name}" updated successfully`);
        } else {
            // Create new project
            const result = await createProject(projectData);
            showSuccessNotification(`Project "${projectData.name}" created successfully`);

            // Show API keys warning
            if (result.api_keys && result.api_keys.length > 0) {
                const apiKey = result.api_keys[0].api_key;
                showInfoNotification(`API Key generated (save it now): ${apiKey}`, 10000);
            }
        }

        closeProjectModal();

        // Refresh projects list
        if (typeof loadProjects === 'function') {
            await loadProjects();
        }

    } catch (error) {
        console.error('Failed to save project:', error);
        const errorMsg = error.response?.data?.detail || error.message || 'Failed to save project';
        showErrorNotification(errorMsg);
    }
}

/**
 * Confirm delete project
 * @param {string} projectId - Project ID to delete
 */
async function confirmDeleteProject(projectId) {
    const confirmed = confirm(
        `Are you sure you want to delete project "${projectId}"?\n\n` +
        `This action cannot be undone. All project data will be lost.`
    );

    if (!confirmed) return;

    try {
        // First try without force
        await deleteProject(projectId, false);
        showSuccessNotification(`Project "${projectId}" deleted successfully`);

        // Refresh projects list
        if (typeof loadProjects === 'function') {
            await loadProjects();
        }

    } catch (error) {
        console.error('Failed to delete project:', error);
        const errorMsg = error.response?.data?.detail || error.message || '';

        // Check if error is about active agents
        if (errorMsg.includes('active agents') || errorMsg.includes('active sessions')) {
            const forceConfirmed = confirm(
                `Project "${projectId}" has active agents.\n\n` +
                `Do you want to force delete anyway? This may interrupt active sessions.`
            );

            if (forceConfirmed) {
                try {
                    await deleteProject(projectId, true);
                    showSuccessNotification(`Project "${projectId}" force deleted`);

                    if (typeof loadProjects === 'function') {
                        await loadProjects();
                    }
                } catch (forceError) {
                    console.error('Failed to force delete:', forceError);
                    showErrorNotification(`Failed to delete: ${forceError.message}`);
                }
            }
        } else {
            showErrorNotification(`Failed to delete: ${errorMsg}`);
        }
    }
}

/**
 * Show success notification
 * @param {string} message - Notification message
 */
function showSuccessNotification(message, duration = 3000) {
    showNotification(message, 'success', duration);
}

/**
 * Show error notification
 * @param {string} message - Notification message
 */
function showErrorNotification(message, duration = 5000) {
    showNotification(message, 'error', duration);
}

/**
 * Show info notification
 * @param {string} message - Notification message
 */
function showInfoNotification(message, duration = 5000) {
    showNotification(message, 'info', duration);
}

/**
 * Show notification
 * @param {string} message - Notification message
 * @param {string} type - Notification type (success, error, info)
 * @param {number} duration - Duration in milliseconds
 */
function showNotification(message, type = 'info', duration = 3000) {
    // Remove existing notifications
    const existing = document.querySelector('.notification-toast');
    if (existing) {
        existing.remove();
    }

    const toast = document.createElement('div');
    toast.className = `notification-toast notification-${type}`;
    toast.textContent = message;
    toast.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 12px 20px;
        border-radius: 8px;
        background: ${type === 'success' ? '#10b981' : type === 'error' ? '#ef4444' : '#3b82f6'};
        color: white;
        font-size: 14px;
        font-weight: 500;
        z-index: 10000;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        animation: slideIn 0.3s ease-out;
    `;

    document.body.appendChild(toast);

    setTimeout(() => {
        toast.style.animation = 'slideOut 0.3s ease-out';
        setTimeout(() => toast.remove(), 300);
    }, duration);
}

// Add CSS animations
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }

    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(100%);
            opacity: 0;
        }
    }

    .modal {
        display: none;
    }

    .modal.active {
        display: flex;
        align-items: center;
        justify-content: center;
    }

    .modal-overlay {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(0, 0, 0, 0.5);
        z-index: 9998;
    }

    .modal-content {
        position: relative;
        background: white;
        border-radius: 12px;
        max-height: 90vh;
        overflow: auto;
        z-index: 9999;
    }

    .modal-lg {
        width: 90%;
        max-width: 600px;
    }

    .modal-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 20px;
        border-bottom: 1px solid #e5e7eb;
    }

    .modal-header h3 {
        margin: 0;
        font-size: 18px;
        font-weight: 600;
    }

    .btn-close {
        background: none;
        border: none;
        font-size: 24px;
        cursor: pointer;
        padding: 0;
        width: 32px;
        height: 32px;
        display: flex;
        align-items: center;
        justify-content: center;
        border-radius: 6px;
        color: #6b7280;
    }

    .btn-close:hover {
        background: #f3f4f6;
        color: #111827;
    }

    .modal-body {
        padding: 20px;
    }

    .modal-footer {
        display: flex;
        justify-content: flex-end;
        gap: 12px;
        padding: 20px;
        border-top: 1px solid #e5e7eb;
    }

    .form-group {
        margin-bottom: 20px;
    }

    .form-group label {
        display: block;
        margin-bottom: 8px;
        font-weight: 500;
        font-size: 14px;
        color: #374151;
    }

    .form-group input,
    .form-group textarea {
        width: 100%;
        padding: 10px 12px;
        border: 1px solid #d1d5db;
        border-radius: 6px;
        font-size: 14px;
        font-family: inherit;
    }

    .form-group input:focus,
    .form-group textarea:focus {
        outline: none;
        border-color: #3b82f6;
        box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
    }

    .form-text {
        display: block;
        margin-top: 6px;
        font-size: 12px;
        color: #6b7280;
    }

    .btn {
        padding: 10px 20px;
        border-radius: 6px;
        font-size: 14px;
        font-weight: 500;
        cursor: pointer;
        border: none;
        display: inline-flex;
        align-items: center;
        gap: 8px;
    }

    .btn-sm {
        padding: 6px 12px;
        font-size: 12px;
    }

    .btn-primary {
        background: #3b82f6;
        color: white;
    }

    .btn-primary:hover {
        background: #2563eb;
    }

    .btn-secondary {
        background: #e5e7eb;
        color: #374151;
    }

    .btn-secondary:hover {
        background: #d1d5db;
    }
`;

if (!document.querySelector('style[data-project-management]')) {
    style.setAttribute('data-project-management', 'true');
    document.head.appendChild(style);
}

// Make functions globally available
window.initProjectManagement = initProjectManagement;
window.showCreateProjectModal = showCreateProjectModal;
window.showEditProjectModal = showEditProjectModal;
window.closeProjectModal = closeProjectModal;
window.confirmDeleteProject = confirmDeleteProject;

// Auto-initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initProjectManagement);
} else {
    initProjectManagement();
}
