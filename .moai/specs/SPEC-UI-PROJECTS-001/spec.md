# SPEC-UI-PROJECTS-001: Project-Based Agent Filtering UI

**SPEC ID:** SPEC-UI-PROJECTS-001
**Title:** Project-Based Agent Filtering UI (Chat-Like Sidebar)
**Created:** 2026-02-01
**Status:** Planned
**Priority:** High

---

## Environment

### Context

The MCP Broker Server supports multi-project functionality (SPEC-MCP-BROKER-002), but the Communication Server dashboard does not expose project-based filtering. Users request a chat-like sidebar that groups agents by project for easier navigation and organization.

### Current State

- Dashboard displays all agents in a single list
- Projects exist in backend (`ProjectDefinition`, `ProjectRegistry`)
- AgentInfo model lacks exposed `project_id` field
- No UI for filtering or grouping by project

### Target State

- Sidebar shows projects as "channels" (similar to Discord/Slack)
- Each project channel shows agents belonging to that project
- "All Agents" global channel shows all agents
- User can switch between project channels
- Active project is visually highlighted

---

## Assumptions

### Technical Assumptions

- **Confidence: High** - Project system exists in mcp_broker models
- **Evidence Basis**: `ProjectDefinition` model exists in `src/mcp_broker/models/project.py`
- **Risk if Wrong**: Project registry may need extension for Communication Server
- **Validation Method**: Review project registry integration points

### Data Flow Assumptions

- **Confidence: Medium** - Agents can be associated with projects during registration
- **Evidence Basis**: Project system supports API key-based project association
- **Risk if Wrong**: May need to add project_id to AgentInfo model
- **Validation Method**: Test agent registration with project context

### UI/UX Assumptions

- **Confidence: High** - Chat-like sidebar is familiar pattern
- **Evidence Basis**: Discord, Slack, Teams use this pattern successfully
- **Risk if Wrong**: Users may prefer different organization method
- **Validation Method**: User feedback after implementation

---

## Requirements (EARS Format)

### Ubiquitous Requirements

**REQ-PROJ-001:** The system **shall** display a project sidebar on the left side of the dashboard.

**REQ-PROJ-002:** The system **shall** list all available projects as selectable channels in the sidebar.

**REQ-PROJ-003:** The system **shall** include an "All Agents" channel that displays all agents regardless of project.

**REQ-PROJ-004:** The system **shall** display project names and agent counts for each project channel.

### Event-Driven Requirements

**WHEN** user clicks on a project channel in the sidebar, **THEN** the system **shall** filter the agent list to show only agents from that project.

**WHEN** user clicks on "All Agents" channel, **THEN** the system **shall** display all agents from all projects.

**WHEN** a new agent registers for a project, **THEN** the system **shall** update the agent count for that project channel.

**WHEN** user hovers over a project channel, **THEN** the system **shall** display project metadata (description, tags).

### State-Driven Requirements

**IF** a project has no active agents, **THEN** the system **shall** display the project channel with a grayed-out indicator.

**IF** a project has at least one active agent, **THEN** the system **shall** display an online indicator for that project channel.

**IF** only one project exists, **THEN** the system **shall** optionally collapse the sidebar to maximize space.

### Unwanted Requirements

The system **shall not** hide the sidebar when viewing a specific project (user can manually collapse).

The system **shall not** require page refresh when switching between projects.

### Optional Requirements

**Where possible**, the system **should** remember the user's last selected project in localStorage.

**Where possible**, the system **should** support keyboard shortcuts for project switching (e.g., Cmd+1, Cmd+2).

**Where possible**, the system **should** display unread message indicators for projects with new activity.

---

## Specifications

### Frontend Specifications

**SPEC-PROJ-FE-001:** Sidebar Layout

Add project sidebar to dashboard:

```
+------------------+------------------------------------------+
| Project Sidebar  | Main Content Area                        |
|                  |                                          |
| [All Agents] (5) | [Stats Cards]                            |
| Project A (3)    |                                          |
| Project B (2)    | [Agent Grid - filtered by selected]       |
|                  |                                          |
| [Settings]       | [Charts & Timeline]                      |
+------------------+------------------------------------------+
```

Width: 240px
Collapsible: Yes (button to toggle)

**SPEC-PROJ-FE-002:** Project Channel Component

```html
<div class="project-channel" data-project-id="project-a">
  <div class="project-icon">
    <svg><!-- project icon --></svg>
  </div>
  <div class="project-info">
    <span class="project-name">Project A</span>
    <span class="agent-count">3</span>
  </div>
  <div class="project-status online"></div>
</div>
```

**SPEC-PROJ-FE-003:** Active State Styling

Selected project channel:
- Different background color (primary blue with 20% opacity)
- Left border indicator (3px solid blue)
- Bold project name

**SPEC-PROJ-FE-004:** API Integration

Add API calls to `js/api.js`:

```javascript
async function fetchProjects() {
    const response = await fetchWithAuth(`${API_BASE_URL}/projects`);
    return await response.json();
}

async function fetchAgentsByProject(projectId) {
    const url = projectId
        ? `${API_BASE_URL}/status/agents?project_id=${projectId}`
        : `${API_BASE_URL}/status/agents`;
    const response = await fetchWithAuth(url);
    return await response.json();
}
```

### Backend Specifications

**SPEC-PROJ-BE-001:** Project List Endpoint

Create `GET /api/v1/projects` endpoint:

```python
@router.get("/projects")
async def list_projects() -> dict:
    """
    Get list of all projects with agent counts.

    Returns:
        Dictionary with projects array containing:
        - project_id: Project identifier
        - name: Project display name
        - agent_count: Number of agents in project
        - active_count: Number of online agents
    """
```

**SPEC-PROJ-BE-002:** Agent List with Project Filter

Modify existing `GET /api/v1/status/agents` endpoint:

```python
@router.get("/status/agents")
async def get_all_agents(
    project_id: str | None = Query(None, description="Filter by project ID")
) -> dict:
    """
    Get all registered agents, optionally filtered by project.

    Args:
        project_id: Optional project ID to filter agents

    Returns:
        Dictionary with agents array
    """
```

**SPEC-PROJ-BE-003:** Agent Registration with Project

Modify agent registration to include project context:

```python
class AgentRegistration(BaseModel):
    """Agent registration request."""

    full_id: str
    nickname: str
    capabilities: list[str]
    project_id: str | None = None  # NEW: Optional project association
```

### Data Models

**SPEC-PROJ-DM-001:** Project Channel Model

```python
class ProjectChannel(BaseModel):
    """Project channel for sidebar display."""

    project_id: str
    name: str
    description: str = ""
    agent_count: int
    active_count: int
    is_online: bool
    tags: list[str] = []
```

**SPEC-PROJ-DM-002:** AgentInfo Extension

Extend `AgentInfo` to include project reference:

```python
class AgentInfo(BaseModel):
    """Agent information with project reference."""

    agent_id: str
    full_id: str
    nickname: str
    status: AgentStatus
    capabilities: list[str]
    last_seen: datetime
    current_meeting: UUID | None = None
    project_id: str | None = None  # NEW: Associated project
```

---

## Dependencies

### Internal Dependencies

- **SPEC-MCP-BROKER-002**: Multi-project support in MCP Broker (provides project models)
- **SPEC-UI-I18N-001**: Project names should be translatable

### External Dependencies

None required

---

## Quality Gates

### TRUST 5 Framework

**Tested:**
- Unit tests for project filtering logic
- Integration tests for API endpoints
- E2E tests for sidebar interaction

**Readable:**
- Clear component naming: `ProjectChannel`, `ProjectSidebar`
- Documented CSS classes for sidebar styling

**Unified:**
- Consistent with dashboard design system
- Reuses existing card and status badge components

**Secured:**
- Project access respects API key permissions
- No cross-project data leakage

**Trackable:**
- Conventional commits: `feat(sidebar):`, `fix(project-filter):`
- Component prefix: `sidebar/`

---

## Related Documents

- **PLAN:** `.moai/specs/SPEC-UI-PROJECTS-001/plan.md` - Implementation milestones
- **ACCEPTANCE:** `.moai/specs/SPEC-UI-PROJECTS-001/acceptance.md` - Test scenarios

---

**END OF SPEC-UI-PROJECTS-001**
