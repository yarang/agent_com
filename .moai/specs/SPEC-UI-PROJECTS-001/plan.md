# Implementation Plan: SPEC-UI-PROJECTS-001

**SPEC ID:** SPEC-UI-PROJECTS-001
**Title:** Project-Based Agent Filtering UI Implementation Plan
**Created:** 2026-02-01

---

## Overview

This plan outlines the implementation of a chat-like project sidebar for the Communication Server dashboard, enabling users to filter and view agents by project.

---

## Implementation Milestones

### Primary Goal (Priority High)

**Milestone 1: Backend Project API**

Implement backend endpoints for project listing and agent filtering.

**Tasks:**
- Create `GET /api/v1/projects` endpoint
- Modify `GET /api/v1/status/agents` to support `project_id` query parameter
- Add project_id to AgentInfo model if needed
- Implement project-to-agent mapping in agent registry

**Success Criteria:**
- Projects API returns list of projects with agent counts
- Agent filtering by project_id works correctly
- All existing tests still pass

**Estimated Complexity:** Medium

---

### Secondary Goal (Priority High)

**Milestone 2: Sidebar Component**

Create the project sidebar UI component.

**Tasks:**
- Add sidebar container to dashboard HTML
- Create project channel component rendering
- Add CSS styling for sidebar layout
- Implement active state styling

**Success Criteria:**
- Sidebar visible on left side of dashboard
- Project channels display with names and counts
- Active project visually distinguished

**Estimated Complexity:** High

---

### Tertiary Goal (Priority Medium)

**Milestone 3: Project Filtering Logic**

Implement project selection and agent filtering.

**Tasks:**
- Add project selection state management
- Filter agent grid by selected project
- Update stats for selected project
- Handle "All Agents" channel

**Success Criteria:**
- Clicking project filters agents correctly
- Stats update to show project-specific counts
- "All Agents" shows all agents

**Estimated Complexity:** Medium

---

### Final Goal (Priority Low)

**Milestone 4: Polish and Enhancement**

Add polish features and optimize user experience.

**Tasks:**
- Add sidebar collapse/expand toggle
- Remember selected project in localStorage
- Add keyboard shortcuts
- Add project metadata tooltip on hover
- Optimize for mobile responsiveness

**Success Criteria:**
- Sidebar can be collapsed to save space
- Selected project persists across page reloads
- Smooth animations for state transitions

**Estimated Complexity:** Low

---

## Technical Approach

### Directory Structure

```
src/communication_server/
├── static/
│   ├── css/
│   │   └── styles.css (add sidebar styles)
│   └── js/
│       ├── sidebar.js (new module)
│       └── api.js (add project APIs)
└── api/
    └── projects.py (new endpoint)
```

### HTML Layout Changes

Modify `index.html` to add sidebar:

```html
<div class="dashboard-container">
    <!-- NEW: Project Sidebar -->
    <aside class="project-sidebar" id="projectSidebar">
        <div class="sidebar-header">
            <h2>Projects</h2>
            <button class="btn-collapse" id="collapseSidebarBtn">
                <svg><!-- collapse icon --></svg>
            </button>
        </div>
        <nav class="sidebar-nav">
            <div class="project-channel all-agents active" data-project-id="">
                <div class="project-icon">
                    <svg><!-- globe icon --></svg>
                </div>
                <div class="project-info">
                    <span class="project-name">All Agents</span>
                    <span class="agent-count" id="allAgentsCount">0</span>
                </div>
            </div>
            <div class="project-channels" id="projectChannels">
                <!-- Project channels rendered here -->
            </div>
        </nav>
        <div class="sidebar-footer">
            <a href="/settings" class="sidebar-link">
                <svg><!-- settings icon --></svg>
                <span>Settings</span>
            </a>
        </div>
    </aside>

    <!-- Existing Main Content (adjusted layout) -->
    <main class="main with-sidebar">
        <!-- ... existing content ... -->
    </main>
</div>
```

### CSS Styling

```css
/* Project Sidebar Styles */
.project-sidebar {
    width: 240px;
    background: var(--bg-secondary);
    border-right: 1px solid var(--border-color);
    display: flex;
    flex-direction: column;
    transition: width 0.3s ease, transform 0.3s ease;
}

.project-sidebar.collapsed {
    width: 60px;
}

.sidebar-header {
    padding: 16px;
    border-bottom: 1px solid var(--border-color);
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.project-channel {
    padding: 12px 16px;
    display: flex;
    align-items: center;
    gap: 12px;
    cursor: pointer;
    border-radius: 8px;
    margin: 4px 8px;
    transition: background-color 0.2s;
}

.project-channel:hover {
    background: var(--bg-hover);
}

.project-channel.active {
    background: var(--primary-bg);
    border-left: 3px solid var(--primary-color);
}

.project-channel.active .project-name {
    font-weight: 600;
}

.project-icon {
    width: 32px;
    height: 32px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--bg-tertiary);
    border-radius: 8px;
    color: var(--text-secondary);
}

.project-info {
    flex: 1;
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.project-name {
    font-size: 14px;
    color: var(--text-primary);
}

.agent-count {
    font-size: 12px;
    color: var(--text-secondary);
    background: var(--bg-tertiary);
    padding: 2px 8px;
    border-radius: 12px;
}

.project-status {
    width: 8px;
    height: 8px;
    border-radius: 50%;
}

.project-status.online {
    background: var(--success-color);
}

.project-status.offline {
    background: var(--text-muted);
}

/* Adjust main content layout */
.main.with-sidebar {
    margin-left: 0;
}

@media (max-width: 1024px) {
    .project-sidebar {
        position: fixed;
        left: 0;
        top: 0;
        bottom: 0;
        z-index: 100;
        transform: translateX(-100%);
    }

    .project-sidebar.open {
        transform: translateX(0);
    }
}
```

### JavaScript Module

Create `src/communication_server/static/js/sidebar.js`:

```javascript
/**
 * Project Sidebar Module
 *
 * Manages project channel selection and agent filtering.
 */

class ProjectSidebar {
    constructor() {
        this.projects = [];
        this.selectedProjectId = null;
        this.sidebarElement = null;
        this.channelsElement = null;
    }

    async init() {
        // Cache DOM elements
        this.sidebarElement = document.getElementById('projectSidebar');
        this.channelsElement = document.getElementById('projectChannels');

        // Load saved selection
        this.loadSelectedProject();

        // Fetch and render projects
        await this.loadProjects();

        // Set up event listeners
        this.setupEventListeners();
    }

    async loadProjects() {
        try {
            const data = await fetchProjects();
            this.projects = data.projects || [];
            this.renderProjectChannels();
            this.updateAllAgentsCount(data.total_agents || 0);
        } catch (error) {
            console.error('Failed to load projects:', error);
        }
    }

    renderProjectChannels() {
        if (!this.channelsElement) return;

        this.channelsElement.innerHTML = this.projects
            .map(project => this.createProjectChannel(project))
            .join('');

        // Set active state
        this.updateActiveState();
    }

    createProjectChannel(project) {
        const isActive = project.project_id === this.selectedProjectId;
        const statusClass = project.active_count > 0 ? 'online' : 'offline';

        return `
            <div class="project-channel ${isActive ? 'active' : ''}"
                 data-project-id="${escapeHtml(project.project_id)}"
                 title="${escapeHtml(project.description)}">
                <div class="project-icon">
                    ${this.getProjectIcon(project.project_id)}
                </div>
                <div class="project-info">
                    <span class="project-name">${escapeHtml(project.name)}</span>
                    <span class="agent-count">${project.agent_count}</span>
                </div>
                <div class="project-status ${statusClass}"></div>
            </div>
        `;
    }

    selectProject(projectId) {
        this.selectedProjectId = projectId;

        // Save to localStorage
        localStorage.setItem('selectedProject', projectId || '');

        // Update active state
        this.updateActiveState();

        // Filter agents
        this.filterAgentsByProject(projectId);
    }

    async filterAgentsByProject(projectId) {
        try {
            const data = await fetchAgentsByProject(projectId);
            agents = data.agents || [];
            renderAgents();
            updateStatistics();
        } catch (error) {
            console.error('Failed to filter agents:', error);
        }
    }

    updateActiveState() {
        // Remove active from all channels
        document.querySelectorAll('.project-channel').forEach(el => {
            el.classList.remove('active');
        });

        // Add active to selected
        const selector = this.selectedProjectId
            ? `[data-project-id="${this.selectedProjectId}"]`
            : '.all-agents';
        document.querySelector(selector)?.classList.add('active');
    }

    loadSelectedProject() {
        const saved = localStorage.getItem('selectedProject');
        this.selectedProjectId = saved === 'null' ? null : saved;
    }

    setupEventListeners() {
        // Channel click handlers
        this.sidebarElement.addEventListener('click', (e) => {
            const channel = e.target.closest('.project-channel');
            if (channel) {
                const projectId = channel.dataset.projectId;
                this.selectProject(projectId);
            }
        });

        // Collapse button
        document.getElementById('collapseSidebarBtn')?.addEventListener('click', () => {
            this.sidebarElement.classList.toggle('collapsed');
        });
    }

    getProjectIcon(projectId) {
        // Generate consistent SVG icon based on project ID
        const hash = hashCode(projectId);
        const colors = ['#6366f1', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6'];
        const color = colors[Math.abs(hash) % colors.length];

        return `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="${color}" stroke-width="2">
            <rect x="3" y="3" width="18" height="18" rx="2"/>
            <path d="M9 3v18"/>
            <path d="M15 3v18"/>
        </svg>`;
    }

    updateAllAgentsCount(count) {
        const el = document.getElementById('allAgentsCount');
        if (el) el.textContent = count;
    }
}

// Helper function
function hashCode(str) {
    let hash = 0;
    for (let i = 0; i < str.length; i++) {
        const char = str.charCodeAt(i);
        hash = ((hash << 5) - hash) + char;
        hash = hash & hash;
    }
    return hash;
}

// Initialize sidebar
const projectSidebar = new ProjectSidebar();

// Export for dashboard integration
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { ProjectSidebar };
}
```

### Backend API Implementation

Create `src/communication_server/api/projects.py`:

```python
"""
Project management API endpoints.
"""

from fastapi import APIRouter, Depends, Query
from communication_server.services.agent_registry import get_agent_registry
from mcp_broker.project.registry import get_project_registry

router = APIRouter(prefix="/projects", tags=["projects"])

@router.get("")
async def list_projects() -> dict:
    """
    Get list of all projects with agent counts.

    Returns projects with their metadata and agent statistics.
    """
    agent_registry = get_agent_registry()
    project_registry = get_project_registry()

    # Get all agents
    all_agents = await agent_registry.get_all_agents()

    # Get all projects
    projects = await project_registry.list_projects()

    # Count agents per project
    project_data = []
    total_agent_count = len(all_agents)

    for project in projects:
        project_agents = [
            a for a in all_agents
            if hasattr(a, 'project_id') and a.project_id == project.project_id
        ]

        active_agents = [
            a for a in project_agents
            if a.status in ('online', 'active')
        ]

        project_data.append({
            "project_id": project.project_id,
            "name": project.metadata.name,
            "description": project.metadata.description,
            "agent_count": len(project_agents),
            "active_count": len(active_agents),
            "is_online": len(active_agents) > 0,
            "tags": project.metadata.tags,
        })

    return {
        "projects": project_data,
        "total_agents": total_agent_count,
    }
```

Modify `src/communication_server/api/status.py`:

```python
@router.get("/status/agents")
async def get_all_agents(
    project_id: str | None = Query(None, description="Filter by project ID")
) -> dict:
    """Get all registered agents, optionally filtered by project."""
    registry = get_agent_registry()
    agents = await registry.get_all_agents()

    # Filter by project if specified
    if project_id:
        agents = [a for a in agents if getattr(a, 'project_id', None) == project_id]

    return {
        "agents": [
            {
                "agent_id": agent.agent_id,
                "full_id": agent.full_id,
                "nickname": agent.nickname,
                "status": agent.status,
                "capabilities": agent.capabilities,
                "last_seen": agent.last_seen.isoformat(),
                "current_meeting": str(agent.current_meeting) if agent.current_meeting else None,
                "project_id": getattr(agent, 'project_id', None),
            }
            for agent in agents
        ]
    }
```

---

## Migration Strategy

### Phase 1: Backend Foundation

Implement backend changes without UI:
1. Add project_id to AgentInfo model
2. Create projects API endpoint
3. Modify agents endpoint to support filtering
4. Add tests for new functionality

### Phase 2: UI Component

Add sidebar to dashboard:
1. Update HTML layout
2. Add CSS styling
3. Create JavaScript module
4. Render project channels

### Phase 3: Integration

Connect sidebar to agent filtering:
1. Implement project selection
2. Filter agent grid
3. Update statistics
4. Add localStorage persistence

### Phase 4: Refinement

Polish and optimize:
1. Add collapse animation
2. Improve mobile responsiveness
3. Add keyboard shortcuts
4. Performance optimization

---

## Risks and Response Plans

### Risk 1: AgentInfo Lacks project_id

**Description:** Current AgentInfo model doesn't have project_id field

**Mitigation:**
- Add optional project_id field to AgentInfo
- Modify agent registration to accept project context
- Backfill existing agents with default project

**Response Plan:**
- Implement project_id as optional field
- Create data migration script if needed

### Risk 2: Performance with Many Projects

**Description:** Sidebar may become cluttered with many projects

**Mitigation:**
- Add search/filter for projects
- Implement lazy loading for large project lists
- Consider pagination or virtual scrolling

**Response Plan:**
- Monitor performance with 10+ projects
- Add search if sidebar exceeds viewport height

### Risk 3: Mobile Layout Issues

**Description:** Fixed sidebar may not work well on small screens

**Mitigation:**
- Use collapsible sidebar on mobile
- Implement overlay drawer pattern
- Add hamburger menu for sidebar toggle

**Response Plan:**
- Test on mobile devices
- Adjust breakpoint for sidebar behavior

---

## Testing Strategy

### Unit Tests

- `ProjectSidebar` class methods
- Project channel rendering
- Agent filtering logic
- localStorage persistence

### Integration Tests

- Projects API returns correct data
- Agent filtering by project_id works
- Project counts are accurate

### E2E Tests

- User can select project channel
- Agent list updates when project selected
- "All Agents" shows all agents
- Selected project persists across reload

---

## Dependencies and Coordination

### Prerequisites

- **SPEC-MCP-BROKER-002**: Multi-project support must be implemented

### Blocks

None - this is independent UI enhancement

### Coordination Notes

Coordinate with **SPEC-UI-I18N-001** to ensure project names are translatable.

---

## Success Metrics

### Completion Criteria

- Sidebar displays all available projects
- Project selection filters agents correctly
- "All Agents" channel works properly
- Selected project persists across sessions
- Responsive design works on mobile

### Performance Targets

- Sidebar render time < 50ms
- Project switch latency < 100ms
- No impact on initial dashboard load time

---

**END OF IMPLEMENTATION PLAN - SPEC-UI-PROJECTS-001**
