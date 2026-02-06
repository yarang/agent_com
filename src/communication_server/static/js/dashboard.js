/**
 * Dashboard initialization and logic for AI Agent Communication System Status Board
 *
 * Manages the main dashboard functionality including data fetching,
 * real-time updates via WebSocket, and UI rendering.
 */

// Dashboard state
let agents = [];
let registeredAgents = [];
let statistics = null;
let activity = null;
let timeline = [];
let refreshInterval = null;
let currentChartType = 'hourly'; // hourly, daily, top
let chartInstance = null;
let i18n = null; // Will be initialized from i18n.js

// DOM dashboardElements (cached for performance)
const dashboardElements = {
    totalAgents: null,
    activeAgents: null,
    totalMessages: null,
    totalMeetings: null,
    decisionsMade: null,
    agentsGrid: null,
    timelineContainer: null,
    currentTime: null,
    connectionStatus: null,
    activeConnections: null,
    // Agent registration dashboardElements
    agentNickname: null,
    registerAgentBtn: null,
    registrationResult: null,
    registrationError: null,
    registrationErrorText: null,
    generatedApiKey: null,
    copyApiKeyBtn: null,
    // Agent management dashboardElements
    agentManagementBody: null,
    refreshManagementBtn: null,
    // Chart dashboardElements
    activityChart: null,
    chartTabs: null,
};

/**
 * Initialize the dashboard on page load
 */
async function initDashboard() {
    console.log('대시보드 초기화 중...');

    // Wait for i18n to be ready
    await waitForI18n();

    // Cache DOM dashboardElements
    cacheElements();

    // Start current time update
    updateCurrentTime();
    setInterval(updateCurrentTime, 1000);

    // Set up language toggle
    setupLanguageToggle();

    // Set up refresh button handlers
    document.getElementById('refreshBtn')?.addEventListener('click', refreshData);
    dashboardElements.refreshManagementBtn?.addEventListener('click', refreshAgentManagement);

    // Set up chart tab handlers
    setupChartTabs();

    // Set up agent registration handlers
    dashboardElements.registerAgentBtn?.addEventListener('click', handleAgentRegistration);
    dashboardElements.copyApiKeyBtn?.addEventListener('click', handleCopyApiKey);
    dashboardElements.agentNickname?.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            handleAgentRegistration();
        }
    });

    // Fetch initial data
    await loadInitialData();

    // Load registered agents for management
    await loadRegisteredAgents();

    // Connect to WebSocket for real-time updates
    connectWebSocket(handleWebSocketMessage, onWebSocketConnect, onWebSocketDisconnect);

    // Set up auto-refresh as fallback (every 30 seconds)
    refreshInterval = setInterval(refreshData, 30000);

    console.log('대시보드 초기화 완료');
}

/**
 * Cache DOM dashboardElements for performance
 */
function cacheElements() {
    dashboardElements.totalAgents = document.getElementById('totalAgents');
    dashboardElements.activeAgents = document.getElementById('activeAgents');
    dashboardElements.totalMessages = document.getElementById('totalMessages');
    dashboardElements.totalMeetings = document.getElementById('totalMeetings');
    dashboardElements.decisionsMade = document.getElementById('decisionsMade');
    dashboardElements.agentsGrid = document.getElementById('agentsGrid');
    dashboardElements.timelineContainer = document.getElementById('timelineContainer');
    dashboardElements.currentTime = document.getElementById('currentTime');
    dashboardElements.activeConnections = document.getElementById('activeConnections');
    // Agent registration dashboardElements
    dashboardElements.agentNickname = document.getElementById('agentNickname');
    dashboardElements.registerAgentBtn = document.getElementById('registerAgentBtn');
    dashboardElements.registrationResult = document.getElementById('registrationResult');
    dashboardElements.registrationError = document.getElementById('registrationError');
    dashboardElements.registrationErrorText = document.getElementById('registrationErrorText');
    dashboardElements.generatedApiKey = document.getElementById('generatedApiKey');
    dashboardElements.copyApiKeyBtn = document.getElementById('copyApiKeyBtn');
    // Agent management dashboardElements
    dashboardElements.agentManagementBody = document.getElementById('agentManagementBody');
    dashboardElements.refreshManagementBtn = document.getElementById('refreshManagementBtn');
    // Chart dashboardElements
    dashboardElements.activityChart = document.getElementById('activityChart');
    dashboardElements.chartTabs = document.querySelectorAll('.chart-tab');
}

/**
 * Wait for i18n to be ready
 */
async function waitForI18n() {
    const maxAttempts = 50; // 5 seconds max
    let attempts = 0;

    while (typeof window.i18n === 'undefined' && attempts < maxAttempts) {
        await new Promise(resolve => setTimeout(resolve, 100));
        attempts++;
    }

    if (typeof window.i18n !== 'undefined') {
        i18n = window.i18n;
        console.log('i18n initialized:', i18n.getCurrentLanguage());
    } else {
        console.warn('i18n not available, continuing without translations');
    }
}

/**
 * Setup language toggle functionality
 */
function setupLanguageToggle() {
    const languageBtn = document.getElementById('languageBtn');
    const languageDropdown = document.getElementById('languageDropdown');
    const currentLangSpan = document.getElementById('currentLang');

    if (!languageBtn || !languageDropdown || !currentLang) {
        return;
    }

    // Update current language display
    updateLanguageDisplay();

    // Toggle dropdown
    languageBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        const isVisible = languageDropdown.style.display !== 'none';
        languageDropdown.style.display = isVisible ? 'none' : 'block';
    });

    // Close dropdown when clicking outside
    document.addEventListener('click', () => {
        languageDropdown.style.display = 'none';
    });

    // Language options
    languageDropdown.querySelectorAll('.language-option').forEach(option => {
        option.addEventListener('click', async (e) => {
            e.stopPropagation();
            const lang = option.getAttribute('data-lang');
            if (i18n && lang) {
                await i18n.setLanguage(lang);
                updateLanguageDisplay();
                // Update charts with new language
                if (activity) updateChart();
            }
            languageDropdown.style.display = 'none';
        });
    });

    // Listen for language changes from other sources
    window.addEventListener('languageChanged', () => {
        updateLanguageDisplay();
    });
}

/**
 * Update language display in the toggle button
 */
function updateLanguageDisplay() {
    const currentLangSpan = document.getElementById('currentLang');
    if (!currentLangSpan) return;

    if (i18n) {
        const currentLang = i18n.getCurrentLanguage();
        currentLangSpan.textContent = currentLang.toUpperCase();
    }
}

/**
 * Get translated text using i18n
 */
function t(key, params = {}) {
    if (i18n && typeof i18n.t === 'function') {
        return i18n.t(key, params);
    }
    return key; // Fallback to key if i18n not available
}

/**
 * Setup chart tab switching
 */
function setupChartTabs() {
    dashboardElements.chartTabs.forEach(tab => {
        tab.addEventListener('click', () => {
            const chartType = tab.dataset.chart;
            switchChart(chartType);

            // Update active tab
            dashboardElements.chartTabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
        });
    });
}

/**
 * Switch chart type
 */
function switchChart(chartType) {
    currentChartType = chartType;
    updateChart();
}

/**
 * Load initial data from API
 */
async function loadInitialData() {
    try {
        // Get selected project ID for filtering
        const selectedProject = typeof getSelectedProjectId === 'function' ? getSelectedProjectId() : null;

        // Fetch all data in parallel - use persistent agent API
        const [agentsData, statsData, activityData, timelineData, registeredAgentsData, projectsData] = await Promise.all([
            fetchAgentsList({ project_id: selectedProject, is_active: true }).catch(() => ({ agents: [] })),
            fetchStatistics().catch(() => null),
            fetchActivity().catch(() => null),
            fetchTimeline(50).catch(() => []),
            fetchAgentsList({ project_id: selectedProject }).catch(() => ({ agents: [] })),
            fetchProjects().catch(() => ({ projects: [] })),
        ]);

        // Store data
        agents = agentsData.agents || [];
        statistics = statsData;
        activity = activityData;
        timeline = timelineData;
        registeredAgents = registeredAgentsData.agents || [];

        // Update UI
        updateStatistics();
        renderAgents();
        updateChart();
        renderTimeline();
        renderAgentManagementTable();

        // Update messages project filter
        const projects = projectsData.projects || [];
        if (typeof updateProjectFilter === 'function') {
            updateProjectFilter(projects);
        }

    } catch (error) {
        console.error('초기 데이터 로딩 오류:', error);
        showError('대시보드 데이터를 로드하지 못했습니다. 페이지를 새로고침해주세요.');
    }
}

/**
 * Refresh all data
 */
async function refreshData() {
    console.log('데이터 새로고침 중...');

    try {
        // Get selected project ID for filtering
        const selectedProject = typeof getSelectedProjectId === 'function' ? getSelectedProjectId() : null;

        // Fetch all data in parallel - use persistent agent API
        const [agentsData, statsData, activityData, timelineData] = await Promise.all([
            fetchAgentsList({ project_id: selectedProject, is_active: true }).catch(() => null),
            fetchStatistics().catch(() => null),
            fetchActivity().catch(() => null),
            fetchTimeline(50).catch(() => null),
        ]);

        // Update stored data
        if (agentsData) agents = agentsData.agents || [];
        if (statsData) statistics = statsData;
        if (activityData) activity = activityData;
        if (timelineData) timeline = timelineData;

        // Update UI
        if (statistics) updateStatistics();
        renderAgents();
        if (activity) updateChart();
        if (timeline.length > 0) renderTimeline();

    } catch (error) {
        console.error('데이터 새로고침 오류:', error);
    }
}

/**
 * Update statistics display
 */
function updateStatistics() {
    if (!statistics) return;

    animateValue(dashboardElements.totalAgents, parseInt(dashboardElements.totalAgents.textContent) || 0, statistics.total_agents || 0, 500);
    animateValue(dashboardElements.activeAgents, parseInt(dashboardElements.activeAgents.textContent) || 0, statistics.active_agents || 0, 500);
    animateValue(dashboardElements.totalMessages, parseInt(dashboardElements.totalMessages.textContent) || 0, statistics.total_messages || 0, 500);
    animateValue(dashboardElements.totalMeetings, parseInt(dashboardElements.totalMeetings.textContent) || 0, statistics.total_meetings || 0, 500);
    animateValue(dashboardElements.decisionsMade, parseInt(dashboardElements.decisionsMade.textContent) || 0, statistics.decisions_made || 0, 500);
}

/**
 * Animate a number value from start to end
 */
function animateValue(element, start, end, duration) {
    if (!element) return;

    const range = end - start;
    const increment = range / (duration / 16);
    let current = start;

    const timer = setInterval(() => {
        current += increment;

        if ((increment > 0 && current >= end) || (increment < 0 && current <= end)) {
            current = end;
            clearInterval(timer);
        }

        element.textContent = Math.round(current).toLocaleString();
    }, 16);
}

/**
 * Render agents grid
 */
function renderAgents() {
    if (!dashboardElements.agentsGrid) return;

    if (agents.length === 0) {
        dashboardElements.agentsGrid.innerHTML = `
            <div class="empty-state">
                <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <circle cx="12" cy="12" r="10"></circle>
                    <line x1="12" y1="8" x2="12" y2="12"></line>
                    <line x1="12" y1="16" x2="12.01" y2="16"></line>
                </svg>
                <p>등록된 에이전트가 없습니다</p>
            </div>
        `;
        return;
    }

    dashboardElements.agentsGrid.innerHTML = agents.map(agent => createAgentCard(agent)).join('');
}

/**
 * Create an agent card HTML
 */
function createAgentCard(agent) {
    const { agent_id, nickname, status, capabilities, last_seen, current_meeting } = agent;

    const statusClass = status.toLowerCase();
    const statusIcons = {
        online: '<div class="status-dot online"></div>',
        active: '<div class="status-dot active"></div>',
        idle: '<div class="status-dot idle"></div>',
        offline: '<div class="status-dot offline"></div>',
        error: '<div class="status-dot error"></div>',
    };
    const statusIcon = statusIcons[statusClass] || statusIcons.offline;

    // Use i18n for status labels
    const statusLabel = t(`status.${statusClass}`) || status;

    const formattedLastSeen = formatTimestamp(last_seen);
    const capabilityTags = capabilities.map(cap =>
        `<span class="capability-tag">${escapeHtml(cap)}</span>`
    ).join('');

    const meetingInfo = current_meeting
        ? `<div class="agent-meeting-info">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect>
                <line x1="16" y1="2" x2="16" y2="6"></line>
                <line x1="8" y1="2" x2="8" y2="6"></line>
                <line x1="3" y1="10" x2="21" y2="10"></line>
            </svg>
            ${t('agentStatus.inMeeting')}: ${escapeHtml(current_meeting.substring(0, 8))}...
           </div>`
        : '';

    const lastActivityLabel = t('agentStatus.lastActivity');

    return `
        <div class="agent-card" data-agent-id="${escapeHtml(agent_id)}">
            <div class="agent-card-header">
                <div>
                    <div class="agent-display-id">${escapeHtml(agent_id)}</div>
                    <div class="agent-nickname">${escapeHtml(nickname)}</div>
                </div>
                <div class="agent-status">
                    ${statusIcon}
                    <span>${statusLabel}</span>
                </div>
            </div>
            <div class="agent-card-body">
                <div class="agent-info-row">
                    <span class="agent-info-label">${lastActivityLabel}:</span>
                    <span class="agent-info-value">${formattedLastSeen}</span>
                </div>
                <div class="agent-capabilities">
                    ${capabilityTags}
                </div>
                ${meetingInfo}
            </div>
        </div>
    `;
}

/**
 * Update chart based on current tab
 */
function updateChart() {
    if (!activity || !dashboardElements.activityChart) return;

    const ctx = dashboardElements.activityChart.getContext('2d');

    // Destroy existing chart
    if (chartInstance) {
        chartInstance.destroy();
    }

    switch (currentChartType) {
        case 'hourly':
            chartInstance = createHourlyChart(ctx, activity.activity_by_hour || []);
            break;
        case 'daily':
            chartInstance = createDailyChart(ctx, activity.activity_by_day || {});
            break;
        case 'top':
            chartInstance = createTopAgentsChart(ctx, activity.top_agents || []);
            break;
    }
}

/**
 * Create hourly activity chart
 */
function createHourlyChart(ctx, data) {
    const hours = Array.from({ length: 24 }, (_, i) => `${i}시`);
    const messagesLabel = t('charts.messages');

    return new Chart(ctx, {
        type: 'bar',
        data: {
            labels: hours,
            datasets: [{
                label: messagesLabel,
                data: data,
                backgroundColor: 'rgba(99, 102, 241, 0.7)',
                borderColor: 'rgba(99, 102, 241, 1)',
                borderWidth: 1,
                borderRadius: 4,
            }]
        },
        options: getChartOptions(t('charts.hourlyActivity'))
    });
}

/**
 * Create daily activity chart
 */
function createDailyChart(ctx, data) {
    const dayOrder = ['월', '화', '수', '목', '금', '토', '일'];
    const labels = dayOrder;
    const values = labels.map(day => data[day] || 0);
    const messagesLabel = t('charts.messages');

    return new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: messagesLabel,
                data: values,
                borderColor: 'rgba(16, 185, 129, 1)',
                backgroundColor: 'rgba(16, 185, 129, 0.1)',
                borderWidth: 2,
                fill: true,
                tension: 0.4,
                pointBackgroundColor: 'rgba(16, 185, 129, 1)',
                pointBorderColor: '#fff',
                pointBorderWidth: 2,
                pointRadius: 4,
                pointHoverRadius: 6,
            }]
        },
        options: getChartOptions(t('charts.dailyActivity'))
    });
}

/**
 * Create top agents chart
 */
function createTopAgentsChart(ctx, data) {
    const sortedData = [...data]
        .sort((a, b) => b.message_count - a.message_count)
        .slice(0, 10);

    const labels = sortedData.map(item => item.agent_id || item.display_id || t('agentList.unknown'));
    const values = sortedData.map(item => item.message_count || 0);
    const messagesLabel = t('charts.messages');

    return new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: messagesLabel,
                data: values,
                backgroundColor: [
                    'rgba(99, 102, 241, 0.7)',
                    'rgba(16, 185, 129, 0.7)',
                    'rgba(245, 158, 11, 0.7)',
                    'rgba(239, 68, 68, 0.7)',
                    'rgba(59, 130, 246, 0.7)',
                    'rgba(139, 92, 246, 0.7)',
                    'rgba(236, 72, 153, 0.7)',
                    'rgba(20, 184, 166, 0.7)',
                    'rgba(249, 115, 22, 0.7)',
                    'rgba(168, 85, 247, 0.7)',
                ],
                borderColor: [
                    'rgba(99, 102, 241, 1)',
                    'rgba(16, 185, 129, 1)',
                    'rgba(245, 158, 11, 1)',
                    'rgba(239, 68, 68, 1)',
                    'rgba(59, 130, 246, 1)',
                    'rgba(139, 92, 246, 1)',
                    'rgba(236, 72, 153, 1)',
                    'rgba(20, 184, 166, 1)',
                    'rgba(249, 115, 22, 1)',
                    'rgba(168, 85, 247, 1)',
                ],
                borderWidth: 1,
                borderRadius: 4,
            }]
        },
        options: {
            ...getChartOptions(t('charts.topAgents')),
            indexAxis: 'y',
        }
    });
}

/**
 * Get common chart options
 */
function getChartOptions(title) {
    return {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                display: false
            },
            tooltip: {
                backgroundColor: 'rgba(30, 41, 59, 0.95)',
                titleColor: '#f8fafc',
                bodyColor: '#cbd5e1',
                borderColor: '#475569',
                borderWidth: 1,
                cornerRadius: 8,
                padding: 12,
            }
        },
        scales: {
            x: {
                grid: {
                    color: 'rgba(51, 65, 85, 0.5)'
                },
                ticks: {
                    color: '#cbd5e1'
                }
            },
            y: {
                beginAtZero: true,
                grid: {
                    color: 'rgba(51, 65, 85, 0.5)'
                },
                ticks: {
                    color: '#cbd5e1',
                    precision: 0
                }
            }
        }
    };
}

/**
 * Render timeline
 */
function renderTimeline() {
    if (!dashboardElements.timelineContainer || timeline.length === 0) {
        if (dashboardElements.timelineContainer) {
            dashboardElements.timelineContainer.innerHTML = `
                <div class="empty-state">
                    <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <circle cx="12" cy="12" r="10"></circle>
                        <line x1="12" y1="8" x2="12" y2="12"></line>
                        <line x1="12" y1="16" x2="12.01" y2="16"></line>
                    </svg>
                    <p>${t('timeline.empty')}</p>
                </div>
            `;
        }
        return;
    }

    dashboardElements.timelineContainer.innerHTML = `<div class="timeline-list">${timeline.map(event => createTimelineItem(event)).join('')}</div>`;
}

/**
 * Create a timeline item HTML
 */
function createTimelineItem(event) {
    const { timestamp, from_agent, to_agent, event_type, description } = event;

    const eventTypeClass = event_type.toLowerCase();
    const formattedTime = formatTimelineTimestamp(timestamp);

    // Use i18n for event type labels
    const eventTypeLabel = t(`timelineEvents.${event_type}`) || event_type;

    const eventTypeIcons = {
        message: '<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>',
        status_change: '<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/>',
        meeting: '<rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/>',
        decision: '<polyline points="20 6 9 17 4 12"/>',
        register: '<path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="8.5" cy="7" r="4"/><line x1="20" y1="8" x2="20" y2="14"/><line x1="23" y1="11" x2="17" y2="11"/>',
        unregister: '<path d="M3 6h18"/><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/>',
    };
    const eventTypeIcon = eventTypeIcons[event_type] || eventTypeIcons.message;

    return `
        <div class="timeline-item ${eventTypeClass}">
            <div class="timeline-icon">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    ${eventTypeIcon}
                </svg>
            </div>
            <div class="timeline-content">
                <div class="timeline-header">
                    <span class="timeline-type">${eventTypeLabel}</span>
                    <span class="timeline-time">${formattedTime}</span>
                </div>
                <div class="timeline-description">${escapeHtml(description)}</div>
                ${from_agent ? `<div class="timeline-agents">${escapeHtml(from_agent)}${to_agent ? ` → ${escapeHtml(to_agent)}` : ''}</div>` : ''}
            </div>
        </div>
    `;
}

/**
 * Handle WebSocket message
 */
function handleWebSocketMessage(data) {
    const { type, data: eventData } = data;

    switch (type) {
        case 'agent_status_change':
            handleAgentStatusChange(eventData);
            break;
        case 'new_communication':
            handleNewCommunication(eventData);
            break;
        case 'meeting_event':
            handleMeetingEvent(eventData);
            break;
        case 'agent_registered':
            handleAgentRegistered(eventData);
            break;
        case 'agent_unregistered':
            handleAgentUnregistered(eventData);
            break;
        case 'connected':
            console.log('WebSocket 연결 확인');
            break;
        case 'pong':
            break;
        default:
            console.log('알 수 없는 메시지 타입:', type);
    }
}

/**
 * Handle agent status change
 */
function handleAgentStatusChange(data) {
    const { agent_id, old_status, new_status } = data;

    const agentIndex = agents.findIndex(a => a.agent_id === agent_id);
    if (agentIndex !== -1) {
        agents[agentIndex].status = new_status;
        renderAgents();

        if (statistics) {
            if (new_status === 'active' || new_status === 'online') {
                statistics.active_agents++;
            } else if (old_status === 'active' || old_status === 'online') {
                statistics.active_agents--;
            }
            updateStatistics();
        }
    }
}

/**
 * Handle new communication event
 */
function handleNewCommunication(data) {
    if (statistics) {
        statistics.total_messages++;
        updateStatistics();
    }
    refreshData();
}

/**
 * Handle meeting event
 */
function handleMeetingEvent(data) {
    const { meeting_id, event_type } = data;

    if (event_type === 'decision_made' && statistics) {
        statistics.decisions_made++;
        updateStatistics();
    }
    refreshData();
}

/**
 * Handle agent registration
 */
function handleAgentRegistered(data) {
    const { agent_id, nickname } = data;
    console.log('에이전트 등록됨:', agent_id, nickname);
    refreshData();
}

/**
 * Handle agent unregistration
 */
function handleAgentUnregistered(data) {
    const { agent_id } = data;
    console.log('에이전트 삭제됨:', agent_id);
    refreshData();
}

/**
 * WebSocket connection established callback
 */
function onWebSocketConnect() {
    console.log('WebSocket 연결됨');
    refreshData();
}

/**
 * WebSocket disconnected callback
 */
function onWebSocketDisconnect() {
    console.log('WebSocket 연결 해제됨');
}

/**
 * Update current time display
 */
function updateCurrentTime() {
    if (!dashboardElements.currentTime) return;

    const now = new Date();
    const hours = now.getHours().toString().padStart(2, '0');
    const minutes = now.getMinutes().toString().padStart(2, '0');
    const seconds = now.getSeconds().toString().padStart(2, '0');
    dashboardElements.currentTime.textContent = `${hours}:${minutes}:${seconds}`;
}

/**
 * Show error message
 */
function showError(message) {
    console.error(message);
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Send periodic ping to keep WebSocket alive
 */
setInterval(() => {
    pingWebSocket();
}, 30000);

// ==================== Agent Registration Functions ====================

/**
 * Handle agent registration
 */
async function handleAgentRegistration() {
    const nickname = dashboardElements.agentNickname?.value?.trim();

    if (!nickname) {
        showRegistrationError(t('registration.errorNicknameRequired'));
        return;
    }

    if (!/^[a-zA-Z0-9_-]+$/.test(nickname)) {
        showRegistrationError(t('registration.errorNicknameInvalid'));
        return;
    }

    dashboardElements.registerAgentBtn.disabled = true;
    dashboardElements.registerAgentBtn.innerHTML = `
        <div class="spinner-small"></div>
        ${t('registration.generating')}
    `;

    try {
        // Get selected project ID for the new agent
        const selectedProject = typeof getSelectedProjectId === 'function' ? getSelectedProjectId() : null;

        // Use persistent agent creation API
        const result = await createAgent({
            name: nickname,
            agent_type: 'worker',
            nickname: nickname,
            project_id: selectedProject,
            capabilities: ['chat', 'task'],
            config: {},
        });

        // Show success with the created agent's ID
        showRegistrationResult(result.id || result.agent_id, nickname);
        dashboardElements.agentNickname.value = '';
        await loadRegisteredAgents();

    } catch (error) {
        console.error('에이전트 등록 오류:', error);
        showRegistrationError(error.message || t('registration.errorGeneric'));
    } finally {
        dashboardElements.registerAgentBtn.disabled = false;
        dashboardElements.registerAgentBtn.innerHTML = `
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M12 5v14M5 12h14"></path>
            </svg>
            ${t('registration.generateButton')}
        `;
    }
}

/**
 * Show registration result
 */
function showRegistrationResult(token, nickname) {
    dashboardElements.registrationResult.style.display = 'block';
    dashboardElements.registrationError.style.display = 'none';
    dashboardElements.generatedApiKey.textContent = token;
}

/**
 * Show registration error
 */
function showRegistrationError(message) {
    dashboardElements.registrationResult.style.display = 'none';
    dashboardElements.registrationError.style.display = 'flex';
    dashboardElements.registrationErrorText.textContent = message;
}

/**
 * Handle copy API key button
 */
async function handleCopyApiKey() {
    const apiKey = dashboardElements.generatedApiKey?.textContent;
    if (!apiKey) return;

    const success = await copyToClipboard(apiKey);

    const btn = dashboardElements.copyApiKeyBtn;
    if (success) {
        btn.innerHTML = `
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="20 6 9 17 4 12"></polyline>
            </svg>
            ${t('registration.copiedButton')}
        `;
        setTimeout(() => {
            btn.innerHTML = `
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <rect x="9" y="9" width="13" height="13" rx="2"/>
                    <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
                </svg>
                <span class="copy-text" data-i18n="registration.copyButton">${t('registration.copyButton')}</span>
            `;
        }, 2000);
    }
}

// ==================== Agent Management Functions ====================

/**
 * Load registered agents for management
 */
async function loadRegisteredAgents() {
    try {
        // Get selected project ID for filtering
        const selectedProject = typeof getSelectedProjectId === 'function' ? getSelectedProjectId() : null;

        // Use persistent agent API
        const data = await fetchAgentsList({ project_id: selectedProject });
        registeredAgents = data.agents || [];
        renderAgentManagementTable();
    } catch (error) {
        console.error('등록된 에이전트 로딩 오류:', error);
        renderAgentManagementError();
    }
}

/**
 * Refresh agent management table
 */
async function refreshAgentManagement() {
    console.log('에이전트 관리 목록 새로고침 중...');
    await loadRegisteredAgents();
}

/**
 * Render agent management table
 */
function renderAgentManagementTable() {
    if (!dashboardElements.agentManagementBody) return;

    if (registeredAgents.length === 0) {
        dashboardElements.agentManagementBody.innerHTML = `
            <tr>
                <td colspan="4">
                    <div class="empty-state">
                        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <circle cx="12" cy="12" r="10"></circle>
                            <line x1="12" y1="8" x2="12" y2="12"></line>
                            <line x1="12" y1="16" x2="12.01" y2="16"></line>
                        </svg>
                        <p>${t('agentList.empty')}</p>
                    </div>
                </td>
            </tr>
        `;
        return;
    }

    dashboardElements.agentManagementBody.innerHTML = registeredAgents.map(agent => createAgentManagementRow(agent)).join('');
}

/**
 * Create agent management table row
 */
function createAgentManagementRow(agent) {
    const { agent_id, nickname, status } = agent;
    const statusClass = status?.toLowerCase() || 'offline';

    // Use i18n for status labels
    const statusLabel = t(`status.${statusClass}`) || t('agentList.unknown');

    return `
        <tr data-agent-id="${escapeHtml(agent_id)}">
            <td>
                <span class="status-badge ${statusClass}">
                    <span class="status-dot"></span>
                    ${statusLabel}
                </span>
            </td>
            <td>${escapeHtml(nickname)}</td>
            <td><code>${escapeHtml(agent_id)}</code></td>
            <td>
                <button class="btn-icon btn-delete" onclick="handleDeleteAgent('${escapeHtml(agent_id)}', '${escapeHtml(nickname)}')" data-i18n-title="agentList.deleteTooltip" title="${t('agentList.deleteTooltip')}">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <polyline points="3 6 5 6 21 6"></polyline>
                        <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                    </svg>
                </button>
            </td>
        </tr>
    `;
}

/**
 * Render agent management error state
 */
function renderAgentManagementError() {
    if (!dashboardElements.agentManagementBody) return;

    dashboardElements.agentManagementBody.innerHTML = `
        <tr>
            <td colspan="4">
                <div class="error-state">
                    <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <circle cx="12" cy="12" r="10"></circle>
                        <line x1="12" y1="8" x2="12" y2="12"></line>
                        <line x1="12" y1="16" x2="12.01" y2="16"></line>
                    </svg>
                    <p>${t('agentList.loadError')}</p>
                    <button class="btn btn-secondary" onclick="refreshAgentManagement()">${t('agentList.retryButton')}</button>
                </div>
            </td>
        </tr>
    `;
}

/**
 * Handle delete agent button click
 */
async function handleDeleteAgent(agentId, nickname) {
    const confirmMessage = t('deleteConfirm.message', { nickname });
    const confirmed = confirm(confirmMessage);

    if (!confirmed) {
        return;
    }

    try {
        await deleteAgent(agentId);
        await loadRegisteredAgents();
        await refreshData();

    } catch (error) {
        console.error('에이전트 삭제 오류:', error);
        const errorMessage = t('deleteConfirm.error', { error: error.message || t('common.error') });
        alert(errorMessage);
    }
}

// Make functions globally available
window.handleDeleteAgent = handleDeleteAgent;
window.refreshAgentManagement = refreshAgentManagement;

// Initialize dashboard when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initDashboard);
} else {
    initDashboard();
}

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    disconnectWebSocket();
    if (refreshInterval) {
        clearInterval(refreshInterval);
    }
    if (chartInstance) {
        chartInstance.destroy();
    }
});
