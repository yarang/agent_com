/**
 * Mediator Management UI Controller
 *
 * Manages the Mediator Management page including:
 * - LLM Models list and management
 * - Prompt library with create/edit/duplicate
 * - Mediators with model/prompt selection
 * - Chat room mediator assignment
 */

// Mediator Management State
const mediatorState = {
    currentProjectId: null,
    projects: [],
    models: [],
    prompts: [],
    mediators: [],
    selectedModel: null,
    selectedPrompt: null,
    selectedMediator: null,
    filters: {
        modelProvider: '',
        promptCategory: '',
        showActiveOnly: true,
    },
};

// DOM Elements Cache
const mediatorElements = {
    // Project selector
    projectSelect: null,

    // Models
    modelsGrid: null,
    modelProviderFilter: null,
    refreshModelsBtn: null,

    // Prompts
    promptsGrid: null,
    promptCategoryFilter: null,
    createPromptBtn: null,
    refreshPromptsBtn: null,

    // Mediators
    mediatorsList: null,
    showActiveOnly: null,
    refreshMediatorsBtn: null,
    createMediatorBtn: null,

    // Mediator Modal
    mediatorModal: null,
    mediatorForm: null,
    mediatorModalTitle: null,
    mediatorId: null,
    mediatorName: null,
    mediatorDescription: null,
    mediatorModel: null,
    mediatorPrompt: null,
    mediatorSystemPrompt: null,
    mediatorTemperature: null,
    temperatureValue: null,
    mediatorMaxTokens: null,
    mediatorActive: null,
    closeMediatorModal: null,
    cancelMediatorBtn: null,

    // Prompt Modal
    promptModal: null,
    promptForm: null,
    promptModalTitle: null,
    promptId: null,
    promptName: null,
    promptDescription: null,
    promptCategory: null,
    promptPublic: null,
    promptSystemPrompt: null,
    promptActive: null,
    closePromptModal: null,
    cancelPromptBtn: null,

    // Prompt Detail Modal
    promptDetailModal: null,
    promptDetailTitle: null,
    promptDetailContent: null,
    closePromptDetailModal: null,
    closePromptDetailBtn: null,
    duplicatePromptBtn: null,
};

/**
 * Initialize Mediator Management page
 */
async function initMediatorManagement() {
    console.log('Initializing Mediator Management...');

    // Cache DOM elements
    cacheMediatorElements();

    // Set up event listeners
    setupMediatorEventListeners();

    // Load initial data
    await loadMediatorData();

    console.log('Mediator Management initialized');
}

/**
 * Cache DOM elements for performance
 */
function cacheMediatorElements() {
    // Project selector
    mediatorElements.projectSelect = document.getElementById('projectSelect');

    // Models
    mediatorElements.modelsGrid = document.getElementById('modelsGrid');
    mediatorElements.modelProviderFilter = document.getElementById('modelProviderFilter');
    mediatorElements.refreshModelsBtn = document.getElementById('refreshModelsBtn');

    // Prompts
    mediatorElements.promptsGrid = document.getElementById('promptsGrid');
    mediatorElements.promptCategoryFilter = document.getElementById('promptCategoryFilter');
    mediatorElements.createPromptBtn = document.getElementById('createPromptBtn');

    // Mediators
    mediatorElements.mediatorsList = document.getElementById('mediatorsList');
    mediatorElements.showActiveOnly = document.getElementById('showActiveOnly');
    mediatorElements.refreshMediatorsBtn = document.getElementById('refreshMediatorsBtn');
    mediatorElements.createMediatorBtn = document.getElementById('createMediatorBtn');

    // Mediator Modal
    mediatorElements.mediatorModal = document.getElementById('mediatorModal');
    mediatorElements.mediatorForm = document.getElementById('mediatorForm');
    mediatorElements.mediatorModalTitle = document.getElementById('mediatorModalTitle');
    mediatorElements.mediatorId = document.getElementById('mediatorId');
    mediatorElements.mediatorName = document.getElementById('mediatorName');
    mediatorElements.mediatorDescription = document.getElementById('mediatorDescription');
    mediatorElements.mediatorModel = document.getElementById('mediatorModel');
    mediatorElements.mediatorPrompt = document.getElementById('mediatorPrompt');
    mediatorElements.mediatorSystemPrompt = document.getElementById('mediatorSystemPrompt');
    mediatorElements.mediatorTemperature = document.getElementById('mediatorTemperature');
    mediatorElements.temperatureValue = document.getElementById('temperatureValue');
    mediatorElements.mediatorMaxTokens = document.getElementById('mediatorMaxTokens');
    mediatorElements.mediatorActive = document.getElementById('mediatorActive');
    mediatorElements.closeMediatorModal = document.getElementById('closeMediatorModal');
    mediatorElements.cancelMediatorBtn = document.getElementById('cancelMediatorBtn');

    // Prompt Modal
    mediatorElements.promptModal = document.getElementById('promptModal');
    mediatorElements.promptForm = document.getElementById('promptForm');
    mediatorElements.promptModalTitle = document.getElementById('promptModalTitle');
    mediatorElements.promptId = document.getElementById('promptId');
    mediatorElements.promptName = document.getElementById('promptName');
    mediatorElements.promptDescription = document.getElementById('promptDescription');
    mediatorElements.promptCategory = document.getElementById('promptCategory');
    mediatorElements.promptPublic = document.getElementById('promptPublic');
    mediatorElements.promptSystemPrompt = document.getElementById('promptSystemPrompt');
    mediatorElements.promptActive = document.getElementById('promptActive');
    mediatorElements.closePromptModal = document.getElementById('closePromptModal');
    mediatorElements.cancelPromptBtn = document.getElementById('cancelPromptBtn');

    // Prompt Detail Modal
    mediatorElements.promptDetailModal = document.getElementById('promptDetailModal');
    mediatorElements.promptDetailTitle = document.getElementById('promptDetailTitle');
    mediatorElements.promptDetailContent = document.getElementById('promptDetailContent');
    mediatorElements.closePromptDetailModal = document.getElementById('closePromptDetailModal');
    mediatorElements.closePromptDetailBtn = document.getElementById('closePromptDetailBtn');
    mediatorElements.duplicatePromptBtn = document.getElementById('duplicatePromptBtn');
}

/**
 * Set up event listeners
 */
function setupMediatorEventListeners() {
    // Project selection
    mediatorElements.projectSelect?.addEventListener('change', handleProjectChange);

    // Model filter
    mediatorElements.modelProviderFilter?.addEventListener('change', handleModelFilterChange);
    mediatorElements.refreshModelsBtn?.addEventListener('click', loadModels);

    // Prompt filter
    mediatorElements.promptCategoryFilter?.addEventListener('change', handlePromptFilterChange);
    mediatorElements.createPromptBtn?.addEventListener('click', showCreatePromptModal);

    // Mediator filter
    mediatorElements.showActiveOnly?.addEventListener('change', handleActiveFilterChange);
    mediatorElements.refreshMediatorsBtn?.addEventListener('click', loadMediators);
    mediatorElements.createMediatorBtn?.addEventListener('click', showCreateMediatorModal);

    // Mediator Form
    mediatorElements.mediatorForm?.addEventListener('submit', handleMediatorFormSubmit);
    mediatorElements.mediatorTemperature?.addEventListener('input', handleTemperatureChange);
    mediatorElements.closeMediatorModal?.addEventListener('click', () => closeModal('mediatorModal'));
    mediatorElements.cancelMediatorBtn?.addEventListener('click', () => closeModal('mediatorModal'));

    // Prompt Form
    mediatorElements.promptForm?.addEventListener('submit', handlePromptFormSubmit);
    mediatorElements.closePromptModal?.addEventListener('click', () => closeModal('promptModal'));
    mediatorElements.cancelPromptBtn?.addEventListener('click', () => closeModal('promptModal'));

    // Prompt Detail Modal
    mediatorElements.closePromptDetailModal?.addEventListener('click', () => closeModal('promptDetailModal'));
    mediatorElements.closePromptDetailBtn?.addEventListener('click', () => closeModal('promptDetailModal'));
    mediatorElements.duplicatePromptBtn?.addEventListener('click', handleDuplicatePrompt);
}

/**
 * Load initial mediator data
 */
async function loadMediatorData() {
    try {
        // Load projects
        await loadProjects();

        // Load models (global, not project-specific)
        await loadModels();

        // Prompts and mediators will be loaded after project selection
        if (mediatorState.currentProjectId) {
            await Promise.all([
                loadPrompts(),
                loadMediators(),
            ]);
        } else {
            showEmptyState('prompts', 'Select a project to view prompts');
            showEmptyState('mediators', 'Select a project to view mediators');
        }
    } catch (error) {
        console.error('Error loading mediator data:', error);
    }
}

/**
 * Load projects
 */
async function loadProjects() {
    try {
        const data = await fetchProjects();
        mediatorState.projects = data.projects || [];

        // Populate project selector
        if (mediatorElements.projectSelect) {
            const currentValue = mediatorElements.projectSelect.value;
            mediatorElements.projectSelect.innerHTML = '<option value="">Select project...</option>';

            mediatorState.projects.forEach(project => {
                const option = document.createElement('option');
                option.value = project.project_id;
                option.textContent = project.name || project.project_id;
                mediatorElements.projectSelect.appendChild(option);
            });

            // Restore previous selection or select first project
            if (currentValue && mediatorState.projects.find(p => p.project_id === currentValue)) {
                mediatorElements.projectSelect.value = currentValue;
            } else if (mediatorState.projects.length > 0) {
                mediatorElements.projectSelect.value = mediatorState.projects[0].project_id;
                handleProjectChange();
            }
        }
    } catch (error) {
        console.error('Error loading projects:', error);
        showProjectError();
    }
}

/**
 * Handle project change
 */
async function handleProjectChange() {
    const projectId = mediatorElements.projectSelect?.value;
    mediatorState.currentProjectId = projectId || null;

    if (projectId) {
        await Promise.all([
            loadPrompts(),
            loadMediators(),
        ]);
    } else {
        showEmptyState('prompts', 'Select a project to view prompts');
        showEmptyState('mediators', 'Select a project to view mediators');
    }
}

/**
 * Load models
 */
async function loadModels() {
    if (!mediatorElements.modelsGrid) return;

    showLoadingState('models');

    try {
        const options = {};
        if (mediatorState.filters.modelProvider) {
            options.provider = mediatorState.filters.modelProvider;
        }

        const data = await fetchMediatorModels(options);
        mediatorState.models = data.models || [];

        renderModels();
        updateMediatorFormModels();
    } catch (error) {
        console.error('Error loading models:', error);
        showErrorState('models', 'Failed to load models');
    }
}

/**
 * Render models grid
 */
function renderModels() {
    if (!mediatorElements.modelsGrid) return;

    if (mediatorState.models.length === 0) {
        showEmptyState('models', 'No models available');
        return;
    }

    mediatorElements.modelsGrid.innerHTML = mediatorState.models.map(model => createModelCard(model)).join('');
}

/**
 * Create model card HTML
 */
function createModelCard(model) {
    const { id, name, provider, model_id: modelId, max_tokens: maxTokens, is_active: isActive } = model;

    return `
        <div class="model-card ${!isActive ? 'inactive' : ''}" data-model-id="${escapeHtml(id)}">
            <div class="model-card-header">
                <div class="model-card-name">${escapeHtml(name)}</div>
                <div class="model-card-provider">${escapeHtml(provider)}</div>
            </div>
            <div class="model-card-details">
                <div class="model-card-detail">
                    <span class="label">Model ID:</span>
                    <span class="value">${escapeHtml(modelId)}</span>
                </div>
                <div class="model-card-detail">
                    <span class="label">Max Tokens:</span>
                    <span class="value">${formatNumber(maxTokens)}</span>
                </div>
                <div class="model-card-detail">
                    <span class="label">Status:</span>
                    <span class="value">${isActive ? 'Active' : 'Inactive'}</span>
                </div>
            </div>
        </div>
    `;
}

/**
 * Load prompts
 */
async function loadPrompts() {
    if (!mediatorState.currentProjectId || !mediatorElements.promptsGrid) return;

    showLoadingState('prompts');

    try {
        const options = {};
        if (mediatorState.filters.promptCategory) {
            options.category = mediatorState.filters.promptCategory;
        }

        const data = await fetchMediatorPrompts(mediatorState.currentProjectId, options);
        mediatorState.prompts = data.prompts || [];

        renderPrompts();
        updateMediatorFormPrompts();
    } catch (error) {
        console.error('Error loading prompts:', error);
        showErrorState('prompts', 'Failed to load prompts');
    }
}

/**
 * Render prompts grid
 */
function renderPrompts() {
    if (!mediatorElements.promptsGrid) return;

    if (mediatorState.prompts.length === 0) {
        showEmptyState('prompts', 'No prompts found. Create your first prompt!');
        return;
    }

    mediatorElements.promptsGrid.innerHTML = mediatorState.prompts.map(prompt => createPromptCard(prompt)).join('');
}

/**
 * Create prompt card HTML
 */
function createPromptCard(prompt) {
    const { id, name, description, category, system_prompt: systemPrompt, is_public: isPublic, is_active: isActive } = prompt;

    return `
        <div class="prompt-card ${!isActive ? 'inactive' : ''}" data-prompt-id="${escapeHtml(id)}" onclick="viewPromptDetail('${escapeHtml(id)}')">
            <div class="prompt-card-header">
                <div class="prompt-card-name">${escapeHtml(name)}</div>
                <div class="prompt-card-category">${escapeHtml(category || 'system')}</div>
            </div>
            ${description ? `<div class="prompt-card-description">${escapeHtml(description)}</div>` : ''}
            <div class="prompt-card-preview">${escapeHtml(systemPrompt)}</div>
            <div class="prompt-card-meta">
                <div class="prompt-card-public">
                    ${isPublic ? '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg> Public' : 'Private'}
                </div>
                <div class="prompt-card-actions">
                    <button class="btn-icon" onclick="event.stopPropagation(); editPrompt('${escapeHtml(id)}')" title="Edit">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
                    </button>
                    <button class="btn-icon" onclick="event.stopPropagation(); deletePrompt('${escapeHtml(id)}')" title="Delete">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
                    </button>
                </div>
            </div>
        </div>
    `;
}

/**
 * Load mediators
 */
async function loadMediators() {
    if (!mediatorState.currentProjectId || !mediatorElements.mediatorsList) return;

    showLoadingState('mediators');

    try {
        const options = {};
        if (mediatorState.filters.showActiveOnly) {
            options.is_active = true;
        }

        const data = await fetchMediators(mediatorState.currentProjectId, options);
        mediatorState.mediators = data.mediators || [];

        renderMediators();
    } catch (error) {
        console.error('Error loading mediators:', error);
        showErrorState('mediators', 'Failed to load mediators');
    }
}

/**
 * Render mediators list
 */
function renderMediators() {
    if (!mediatorElements.mediatorsList) return;

    if (mediatorState.mediators.length === 0) {
        showEmptyState('mediators', 'No mediators found. Create your first mediator!');
        return;
    }

    mediatorElements.mediatorsList.innerHTML = mediatorState.mediators.map(mediator => createMediatorItem(mediator)).join('');
}

/**
 * Create mediator item HTML
 */
function createMediatorItem(mediator) {
    const { id, name, description, model, model_id: modelId, default_prompt_id: defaultPromptId, temperature, max_tokens: maxTokens, is_active: isActive } = mediator;

    const modelName = mediatorState.models.find(m => m.id === modelId)?.name || 'Unknown Model';
    const promptName = mediatorState.prompts.find(p => p.id === defaultPromptId)?.name || null;

    return `
        <div class="mediator-item ${!isActive ? 'inactive' : ''}" data-mediator-id="${escapeHtml(id)}">
            <div class="mediator-status ${isActive ? 'active' : 'inactive'}"></div>
            <div class="mediator-icon">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"/>
                    <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
                    <line x1="12" y1="19" x2="12" y2="23"/>
                    <line x1="8" y1="23" x2="16" y2="23"/>
                </svg>
            </div>
            <div class="mediator-info">
                <div class="mediator-name">${escapeHtml(name)}</div>
                <div class="mediator-details">
                    <span class="mediator-model">${escapeHtml(modelName)}</span>
                    ${promptName ? `<span class="mediator-prompt">${escapeHtml(promptName)}</span>` : ''}
                    ${temperature !== null && temperature !== undefined ? `<span class="mediator-temperature">T: ${temperature}</span>` : ''}
                </div>
            </div>
            <div class="mediator-actions">
                <button class="btn-icon" onclick="editMediator('${escapeHtml(id)}')" title="Edit">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
                        <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
                    </svg>
                </button>
                <button class="btn-icon" onclick="toggleMediatorActive('${escapeHtml(id)}')" title="${isActive ? 'Deactivate' : 'Activate'}">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        ${isActive
                            ? '<rect x="6" y="4" width="4" height="16"/><rect x="14" y="4" width="4" height="16"/>'
                            : '<polygon points="5 3 19 12 5 21 5 3"/>'
                        }
                    </svg>
                </button>
                <button class="btn-icon" onclick="deleteMediator('${escapeHtml(id)}')" title="Delete">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <polyline points="3 6 5 6 21 6"/>
                        <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
                    </svg>
                </button>
            </div>
        </div>
    `;
}

/**
 * Handle model filter change
 */
async function handleModelFilterChange() {
    mediatorState.filters.modelProvider = mediatorElements.modelProviderFilter?.value || '';
    await loadModels();
}

/**
 * Handle prompt filter change
 */
async function handlePromptFilterChange() {
    mediatorState.filters.promptCategory = mediatorElements.promptCategoryFilter?.value || '';
    await loadPrompts();
}

/**
 * Handle active filter change
 */
async function handleActiveFilterChange() {
    mediatorState.filters.showActiveOnly = mediatorElements.showActiveOnly?.checked ?? true;
    await loadMediators();
}

/**
 * Handle temperature change
 */
function handleTemperatureChange() {
    if (mediatorElements.temperatureValue && mediatorElements.mediatorTemperature) {
        mediatorElements.temperatureValue.textContent = mediatorElements.mediatorTemperature.value;
    }
}

/**
 * Show create mediator modal
 */
function showCreateMediatorModal() {
    if (!mediatorState.currentProjectId) {
        alert('Please select a project first');
        return;
    }

    mediatorState.selectedMediator = null;

    if (mediatorElements.mediatorModalTitle) {
        mediatorElements.mediatorModalTitle.textContent = 'Create Mediator';
    }

    resetMediatorForm();
    updateMediatorFormModels();
    updateMediatorFormPrompts();

    openModal('mediatorModal');
}

/**
 * Show create prompt modal
 */
function showCreatePromptModal() {
    if (!mediatorState.currentProjectId) {
        alert('Please select a project first');
        return;
    }

    mediatorState.selectedPrompt = null;

    if (mediatorElements.promptModalTitle) {
        mediatorElements.promptModalTitle.textContent = 'Create Prompt';
    }

    resetPromptForm();
    openModal('promptModal');
}

/**
 * View prompt detail
 */
async function viewPromptDetail(promptId) {
    const prompt = mediatorState.prompts.find(p => p.id === promptId);
    if (!prompt) return;

    mediatorState.selectedPrompt = prompt;

    if (mediatorElements.promptDetailTitle) {
        mediatorElements.promptDetailTitle.textContent = prompt.name;
    }

    if (mediatorElements.promptDetailContent) {
        const variables = prompt.variables ? Object.keys(prompt.variables) : [];

        mediatorElements.promptDetailContent.innerHTML = `
            <div class="prompt-detail-header">
                <div class="prompt-detail-name">${escapeHtml(prompt.name)}</div>
                <div class="prompt-detail-meta">
                    <span class="prompt-detail-category">${escapeHtml(prompt.category || 'system')}</span>
                    ${prompt.is_public ? '<span class="prompt-detail-category">Public</span>' : '<span class="prompt-detail-category" style="background: var(--bg-tertiary); color: var(--text-secondary);">Private</span>'}
                </div>
                ${prompt.description ? `<div class="prompt-detail-description">${escapeHtml(prompt.description)}</div>` : ''}
            </div>
            ${variables.length > 0 ? `
                <div class="prompt-detail-section">
                    <div class="prompt-detail-section-label">Variables</div>
                    <div class="prompt-detail-variables">
                        ${variables.map(v => `<span class="prompt-detail-variable">${escapeHtml(v)}</span>`).join('')}
                    </div>
                </div>
            ` : ''}
            <div class="prompt-detail-section">
                <div class="prompt-detail-section-label">System Prompt</div>
                <div class="prompt-detail-prompt">${escapeHtml(prompt.system_prompt)}</div>
            </div>
        `;
    }

    openModal('promptDetailModal');
}

/**
 * Edit prompt
 */
function editPrompt(promptId) {
    const prompt = mediatorState.prompts.find(p => p.id === promptId);
    if (!prompt) return;

    mediatorState.selectedPrompt = prompt;

    if (mediatorElements.promptModalTitle) {
        mediatorElements.promptModalTitle.textContent = 'Edit Prompt';
    }

    if (mediatorElements.promptId) mediatorElements.promptId.value = prompt.id;
    if (mediatorElements.promptName) mediatorElements.promptName.value = prompt.name;
    if (mediatorElements.promptDescription) mediatorElements.promptDescription.value = prompt.description || '';
    if (mediatorElements.promptCategory) mediatorElements.promptCategory.value = prompt.category || 'system';
    if (mediatorElements.promptPublic) mediatorElements.promptPublic.checked = prompt.is_public || false;
    if (mediatorElements.promptSystemPrompt) mediatorElements.promptSystemPrompt.value = prompt.system_prompt;
    if (mediatorElements.promptActive) mediatorElements.promptActive.checked = prompt.is_active !== false;

    closeModal('promptDetailModal');
    openModal('promptModal');
}

/**
 * Delete prompt
 */
async function deletePrompt(promptId) {
    const prompt = mediatorState.prompts.find(p => p.id === promptId);
    if (!prompt) return;

    const confirmed = confirm(`Are you sure you want to delete the prompt "${prompt.name}"?`);

    if (!confirmed) return;

    try {
        await deleteMediatorPrompt(mediatorState.currentProjectId, promptId);
        await loadPrompts();
        await loadMediators(); // Refresh mediators as they might reference this prompt
    } catch (error) {
        console.error('Error deleting prompt:', error);
        alert('Failed to delete prompt: ' + error.message);
    }
}

/**
 * Handle duplicate prompt
 */
async function handleDuplicatePrompt() {
    if (!mediatorState.selectedPrompt) return;

    try {
        const result = await duplicateMediatorPrompt(mediatorState.currentProjectId, mediatorState.selectedPrompt.id);
        closeModal('promptDetailModal');
        await loadPrompts();

        // Optionally open the edit modal for the duplicated prompt
        if (result.prompt) {
            setTimeout(() => editPrompt(result.prompt.id), 100);
        }
    } catch (error) {
        console.error('Error duplicating prompt:', error);
        alert('Failed to duplicate prompt: ' + error.message);
    }
}

/**
 * Edit mediator
 */
function editMediator(mediatorId) {
    const mediator = mediatorState.mediators.find(m => m.id === mediatorId);
    if (!mediator) return;

    mediatorState.selectedMediator = mediator;

    if (mediatorElements.mediatorModalTitle) {
        mediatorElements.mediatorModalTitle.textContent = 'Edit Mediator';
    }

    if (mediatorElements.mediatorId) mediatorElements.mediatorId.value = mediator.id;
    if (mediatorElements.mediatorName) mediatorElements.mediatorName.value = mediator.name;
    if (mediatorElements.mediatorDescription) mediatorElements.mediatorDescription.value = mediator.description || '';
    if (mediatorElements.mediatorModel) mediatorElements.mediatorModel.value = mediator.model_id || '';
    if (mediatorElements.mediatorPrompt) mediatorElements.mediatorPrompt.value = mediator.default_prompt_id || '';
    if (mediatorElements.mediatorSystemPrompt) mediatorElements.mediatorSystemPrompt.value = mediator.system_prompt || '';
    if (mediatorElements.mediatorTemperature) {
        mediatorElements.mediatorTemperature.value = mediator.temperature ?? 0.7;
        if (mediatorElements.temperatureValue) {
            mediatorElements.temperatureValue.textContent = mediator.temperature ?? 0.7;
        }
    }
    if (mediatorElements.mediatorMaxTokens) mediatorElements.mediatorMaxTokens.value = mediator.max_tokens || 1000;
    if (mediatorElements.mediatorActive) mediatorElements.mediatorActive.checked = mediator.is_active !== false;

    updateMediatorFormModels();
    updateMediatorFormPrompts();

    openModal('mediatorModal');
}

/**
 * Toggle mediator active status
 */
async function toggleMediatorActive(mediatorId) {
    const mediator = mediatorState.mediators.find(m => m.id === mediatorId);
    if (!mediator) return;

    try {
        await updateMediator(mediatorState.currentProjectId, mediatorId, {
            is_active: !mediator.is_active,
        });
        await loadMediators();
    } catch (error) {
        console.error('Error toggling mediator:', error);
        alert('Failed to update mediator: ' + error.message);
    }
}

/**
 * Delete mediator
 */
async function deleteMediator(mediatorId) {
    const mediator = mediatorState.mediators.find(m => m.id === mediatorId);
    if (!mediator) return;

    const confirmed = confirm(`Are you sure you want to delete the mediator "${mediator.name}"?`);

    if (!confirmed) return;

    try {
        await deleteMediatorApi(mediatorState.currentProjectId, mediatorId);
        await loadMediators();
    } catch (error) {
        console.error('Error deleting mediator:', error);
        alert('Failed to delete mediator: ' + error.message);
    }
}

/**
 * Handle mediator form submit
 */
async function handleMediatorFormSubmit(e) {
    e.preventDefault();

    const data = {
        name: mediatorElements.mediatorName?.value,
        description: mediatorElements.mediatorDescription?.value,
        model_id: mediatorElements.mediatorModel?.value,
        default_prompt_id: mediatorElements.mediatorPrompt?.value || null,
        system_prompt: mediatorElements.mediatorSystemPrompt?.value || null,
        temperature: parseFloat(mediatorElements.mediatorTemperature?.value),
        max_tokens: parseInt(mediatorElements.mediatorMaxTokens?.value),
        is_active: mediatorElements.mediatorActive?.checked ?? true,
    };

    try {
        if (mediatorState.selectedMediator) {
            await updateMediator(mediatorState.currentProjectId, mediatorState.selectedMediator.id, data);
        } else {
            await createMediatorApi(mediatorState.currentProjectId, data);
        }

        closeModal('mediatorModal');
        await loadMediators();
    } catch (error) {
        console.error('Error saving mediator:', error);
        alert('Failed to save mediator: ' + error.message);
    }
}

/**
 * Handle prompt form submit
 */
async function handlePromptFormSubmit(e) {
    e.preventDefault();

    const data = {
        name: mediatorElements.promptName?.value,
        description: mediatorElements.promptDescription?.value,
        category: mediatorElements.promptCategory?.value,
        is_public: mediatorElements.promptPublic?.checked ?? false,
        system_prompt: mediatorElements.promptSystemPrompt?.value,
        is_active: mediatorElements.promptActive?.checked ?? true,
    };

    try {
        if (mediatorState.selectedPrompt) {
            await updateMediatorPrompt(mediatorState.currentProjectId, mediatorState.selectedPrompt.id, data);
        } else {
            await createMediatorPrompt(mediatorState.currentProjectId, data);
        }

        closeModal('promptModal');
        await loadPrompts();
    } catch (error) {
        console.error('Error saving prompt:', error);
        alert('Failed to save prompt: ' + error.message);
    }
}

/**
 * Reset mediator form
 */
function resetMediatorForm() {
    if (mediatorElements.mediatorForm) {
        mediatorElements.mediatorForm.reset();
    }
    if (mediatorElements.mediatorId) mediatorElements.mediatorId.value = '';
    if (mediatorElements.mediatorDescription) mediatorElements.mediatorDescription.value = '';
    if (mediatorElements.mediatorPrompt) mediatorElements.mediatorPrompt.value = '';
    if (mediatorElements.mediatorSystemPrompt) mediatorElements.mediatorSystemPrompt.value = '';
    if (mediatorElements.mediatorTemperature) {
        mediatorElements.mediatorTemperature.value = 0.7;
        if (mediatorElements.temperatureValue) {
            mediatorElements.temperatureValue.textContent = '0.7';
        }
    }
    if (mediatorElements.mediatorMaxTokens) mediatorElements.mediatorMaxTokens.value = 1000;
    if (mediatorElements.mediatorActive) mediatorElements.mediatorActive.checked = true;
}

/**
 * Reset prompt form
 */
function resetPromptForm() {
    if (mediatorElements.promptForm) {
        mediatorElements.promptForm.reset();
    }
    if (mediatorElements.promptId) mediatorElements.promptId.value = '';
    if (mediatorElements.promptDescription) mediatorElements.promptDescription.value = '';
    if (mediatorElements.promptCategory) mediatorElements.promptCategory.value = '';
    if (mediatorElements.promptPublic) mediatorElements.promptPublic.checked = false;
    if (mediatorElements.promptSystemPrompt) mediatorElements.promptSystemPrompt.value = '';
    if (mediatorElements.promptActive) mediatorElements.promptActive.checked = true;
}

/**
 * Update mediator form models dropdown
 */
function updateMediatorFormModels() {
    if (!mediatorElements.mediatorModel) return;

    const currentValue = mediatorElements.mediatorModel.value;
    mediatorElements.mediatorModel.innerHTML = '<option value="">Select model...</option>';

    mediatorState.models.forEach(model => {
        if (!model.is_active) return;
        const option = document.createElement('option');
        option.value = model.id;
        option.textContent = `${model.name} (${model.provider})`;
        mediatorElements.mediatorModel.appendChild(option);
    });

    if (currentValue) {
        mediatorElements.mediatorModel.value = currentValue;
    }
}

/**
 * Update mediator form prompts dropdown
 */
function updateMediatorFormPrompts() {
    if (!mediatorElements.mediatorPrompt) return;

    const currentValue = mediatorElements.mediatorPrompt.value;
    mediatorElements.mediatorPrompt.innerHTML = '<option value="">None (use model default)</option>';

    mediatorState.prompts.forEach(prompt => {
        if (!prompt.is_active) return;
        const option = document.createElement('option');
        option.value = prompt.id;
        option.textContent = prompt.name;
        mediatorElements.mediatorPrompt.appendChild(option);
    });

    if (currentValue) {
        mediatorElements.mediatorPrompt.value = currentValue;
    }
}

/**
 * Show loading state
 */
function showLoadingState(section) {
    const container = section === 'models' ? mediatorElements.modelsGrid :
                      section === 'prompts' ? mediatorElements.promptsGrid :
                      mediatorElements.mediatorsList;

    if (!container) return;

    container.innerHTML = `
        <div class="loading-state">
            <div class="spinner"></div>
            <p>Loading...</p>
        </div>
    `;
}

/**
 * Show empty state
 */
function showEmptyState(section, message) {
    const container = section === 'models' ? mediatorElements.modelsGrid :
                      section === 'prompts' ? mediatorElements.promptsGrid :
                      mediatorElements.mediatorsList;

    if (!container) return;

    container.innerHTML = `
        <div class="empty-state">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="10"/>
                <line x1="12" y1="8" x2="12" y2="12"/>
                <line x1="12" y1="16" x2="12.01" y2="16"/>
            </svg>
            <p>${escapeHtml(message)}</p>
        </div>
    `;
}

/**
 * Show error state
 */
function showErrorState(section, message) {
    const container = section === 'models' ? mediatorElements.modelsGrid :
                      section === 'prompts' ? mediatorElements.promptsGrid :
                      mediatorElements.mediatorsList;

    if (!container) return;

    container.innerHTML = `
        <div class="empty-state">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="var(--error)" stroke-width="2">
                <circle cx="12" cy="12" r="10"/>
                <line x1="15" y1="9" x2="9" y2="15"/>
                <line x1="9" y1="9" x2="15" y2="15"/>
            </svg>
            <p style="color: var(--error);">${escapeHtml(message)}</p>
        </div>
    `;
}

/**
 * Show project error
 */
function showProjectError() {
    if (mediatorElements.projectSelect) {
        mediatorElements.projectSelect.innerHTML = '<option value="">No projects available</option>';
    }
}

/**
 * Open modal
 */
function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.style.display = 'flex';
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
 * Format number
 */
function formatNumber(num) {
    if (num >= 1000000) {
        return (num / 1000000).toFixed(1) + 'M';
    }
    if (num >= 1000) {
        return (num / 1000).toFixed(1) + 'K';
    }
    return num.toString();
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
    if (text === null || text === undefined) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Create mediator API wrapper (name conflict with imported function)
 */
async function createMediatorApi(projectId, data) {
    return await createMediator(projectId, data);
}

/**
 * Delete mediator API wrapper (name conflict)
 */
async function deleteMediatorApi(projectId, mediatorId) {
    return await deleteMediator(projectId, mediatorId);
}

// Make functions globally available
window.viewPromptDetail = viewPromptDetail;
window.editPrompt = editPrompt;
window.deletePrompt = deletePrompt;
window.editMediator = editMediator;
window.toggleMediatorActive = toggleMediatorActive;
window.deleteMediator = deleteMediator;

// Initialize Mediator Management when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initMediatorManagement);
} else {
    initMediatorManagement();
}
