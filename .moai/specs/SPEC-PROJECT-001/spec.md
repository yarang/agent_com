# SPEC-PROJECT-001: Project Management and Chat Interface

**SPEC ID:** SPEC-PROJECT-001
**Title:** Project Management (CRUD) and Chat-Like Message Organization
**Created:** 2026-02-02
**Status:** Planned
**Priority:** High

---

## Environment

### Context

The MCP Broker Server supports multi-project functionality (SPEC-MCP-BROKER-002) with comprehensive project models in `src/mcp_broker/models/project.py` and project registry in `src/mcp_broker/project/registry.py`. However, the Communication Server lacks:

1. **Project CRUD API endpoints** - No way to create, update, or delete projects via HTTP
2. **Agent-to-Project Assignment** - No API to assign agents to projects
3. **Chat Room Interface** - Messages exist but lack project-based chat room UI

### Current State

**Backend:**
- `ProjectDefinition` model exists with comprehensive fields (metadata, config, API keys)
- `ProjectRegistry` has CRUD methods but no HTTP API exposure
- Projects API (`src/communication_server/api/projects.py`) only has 2 read-only endpoints
- Agent registry tracks agents but lacks explicit project assignment API

**Frontend:**
- Project sidebar exists (`projects.js`) for filtering
- Message list exists (`messages.js`) with project filtering
- No project management UI (create/edit/delete)
- No chat-room style messaging interface

**Message Storage:**
- Messages stored with `project_id` in metadata
- `MeetingMessage` model exists for meeting messages
- No direct chat messaging (only meeting-based)

### Target State

**Backend:**
- Full REST API for project CRUD operations
- Agent-to-project assignment endpoints
- Direct messaging API with project context
- WebSocket support for real-time updates

**Frontend:**
- Project management interface (create/edit/delete projects)
- Chat room UI similar to Discord/Slack
- Real-time message updates per project
- Agent assignment interface

---

## Assumptions

### Technical Assumptions

- **Confidence: High** - Project models and registry are production-ready
- **Evidence Basis**: `ProjectDefinition`, `ProjectRegistry` exist in mcp_broker
- **Risk if Wrong**: May need to extend models for Communication Server specific fields
- **Validation Method**: Test project CRUD operations with existing models

### Database Assumptions

- **Confidence: Medium** - Project data persists in memory (default storage)
- **Evidence Basis**: `ProjectRegistry` uses in-memory dict storage
- **Risk if Wrong**: Projects lost on server restart
- **Validation Method**: Review storage layer, consider Redis persistence

### Chat Interface Assumptions

- **Confidence: High** - WebSocket infrastructure exists for real-time updates
- **Evidence Basis**: Communication Server has WebSocket support for agent status
- **Risk if Wrong**: May need new WebSocket message types
- **Validation Method**: Test WebSocket message broadcasting

### Agent Assignment Assumptions

- **Confidence: Medium** - Agents can be associated with projects during registration
- **Evidence Basis**: AgentInfo model can include project_id
- **Risk if Wrong**: May need explicit assignment API separate from registration
- **Validation Method**: Test agent registration with project context

---

## Requirements (EARS Format)

### Ubiquitous Requirements

**REQ-PROJ-MGT-001:** The system **shall** provide REST API endpoints for creating, reading, updating, and deleting projects.

**REQ-PROJ-MGT-002:** The system **shall** support agent-to-project assignment via dedicated API endpoints.

**REQ-PROJ-MGT-003:** The system **shall** provide a chat-like interface for project-specific messaging.

**REQ-PROJ-MGT-004:** The system **shall** support real-time message updates via WebSocket connections.

### Event-Driven Requirements

**WHEN** user creates a new project, **THEN** the system **shall** generate API keys and initialize project statistics.

**WHEN** user updates project metadata, **THEN** the system **shall** update the `last_modified` timestamp.

**WHEN** user deletes a project, **THEN** the system **shall** verify no active sessions exist before deletion.

**WHEN** agent is assigned to a project, **THEN** the system **shall** update the project's agent count.

**WHEN** user sends a message to a project chat room, **THEN** the system **shall** broadcast the message to all connected WebSocket clients for that project.

**WHEN** new message arrives via WebSocket, **THEN** the system **shall** append it to the chat room interface without page refresh.

### State-Driven Requirements

**IF** project has no agents assigned, **THEN** the system **shall** display empty state in chat room.

**IF** project is inactive, **THEN** the system **shall** prevent new message sending.

**IF** user is not authenticated, **THEN** the system **shall** deny project management operations.

**IF** project has active sessions, **THEN** the system **shall** prevent project deletion.

**IF** chat room has more than 100 messages, **THEN** the system **shall** implement pagination or lazy loading.

### Unwanted Requirements

The system **shall not** allow deletion of projects with active agent sessions.

The system **shall not** expose project API keys in list responses (only in create response).

The system **shall not** allow cross-project message broadcasting without explicit permission.

The system **shall not** store messages indefinitely without cleanup policy.

### Optional Requirements

**Where possible**, the system **should** provide message search functionality within project chat.

**Where possible**, the system **should** support message threading and replies.

**Where possible**, the system **should** support file attachments in project messages.

**Where possible**, the system **should** provide message read receipts.

---

## Specifications

### Backend Specifications

**SPEC-PROJ-BE-001:** Project Create Endpoint

Create `POST /api/v1/projects` endpoint:

```python
@router.post("/projects")
async def create_project(
    project_data: ProjectCreateRequest,
    auth_context: AuthContext = Depends(get_auth_context)
) -> ProjectCreateResponse:
    """
    Create a new project with generated API keys.

    Args:
        project_data: Project creation details
        auth_context: Authentication context

    Returns:
        Created project with API keys (only shown once)
    """
```

Request model:
```python
class ProjectCreateRequest(BaseModel):
    """Request to create a project."""

    project_id: str = Field(..., pattern=r"^[a-z][a-z0-9_]*[a-z0-9]$")
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(default="", max_length=500)
    tags: list[str] = Field(default_factory=list)
    config: ProjectConfig | None = None
```

Response model:
```python
class ProjectCreateResponse(BaseModel):
    """Response after creating a project."""

    project: ProjectDefinition
    api_keys: list[ProjectAPIKey]  # Only returned on creation
```

**SPEC-PROJ-BE-002:** Project Update Endpoint

Create `PUT /api/v1/projects/{project_id}` endpoint:

```python
@router.put("/projects/{project_id}")
async def update_project(
    project_id: str,
    project_data: ProjectUpdateRequest,
    auth_context: AuthContext = Depends(get_auth_context)
) -> ProjectDefinition:
    """
    Update an existing project.

    Args:
        project_id: Project identifier
        project_data: Updated project data

    Returns:
        Updated project definition
    """
```

**SPEC-PROJ-BE-003:** Project Delete Endpoint

Create `DELETE /api/v1/projects/{project_id}` endpoint:

```python
@router.delete("/projects/{project_id}")
async def delete_project(
    project_id: str,
    force: bool = Query(False, description="Force delete (requires admin)"),
    auth_context: AuthContext = Depends(get_auth_context)
) -> dict:
    """
    Delete a project.

    Args:
        project_id: Project identifier
        force: Force delete even with active sessions (admin only)

    Returns:
        Deletion confirmation
    """
```

**SPEC-PROJ-BE-004:** Agent Assignment Endpoint

Create `POST /api/v1/projects/{project_id}/agents` endpoint:

```python
@router.post("/projects/{project_id}/agents")
async def assign_agent_to_project(
    project_id: str,
    assignment: AgentAssignmentRequest,
    auth_context: AuthContext = Depends(get_auth_context)
) -> dict:
    """
    Assign an agent to a project.

    Args:
        project_id: Target project
        assignment: Assignment details

    Returns:
        Assignment confirmation
    """
```

Request model:
```python
class AgentAssignmentRequest(BaseModel):
    """Request to assign agent to project."""

    agent_id: str
    role: str = Field(default="member", description="Agent role in project")
```

**SPEC-PROJ-BE-005:** Agent Unassignment Endpoint

Create `DELETE /api/v1/projects/{project_id}/agents/{agent_id}` endpoint:

```python
@router.delete("/projects/{project_id}/agents/{agent_id}")
async def unassign_agent_from_project(
    project_id: str,
    agent_id: str,
    auth_context: AuthContext = Depends(get_auth_context)
) -> dict:
    """
    Unassign an agent from a project.

    Args:
        project_id: Project identifier
        agent_id: Agent identifier

    Returns:
        Unassignment confirmation
    """
```

**SPEC-PROJ-BE-006:** Project Chat Messages Endpoint

Create `POST /api/v1/projects/{project_id}/messages` endpoint:

```python
@router.post("/projects/{project_id}/messages")
async def send_project_message(
    project_id: str,
    message: ProjectMessageCreate,
    auth_context: AuthContext = Depends(get_auth_context)
) -> ProjectMessage:
    """
    Send a message to a project chat room.

    Args:
        project_id: Target project
        message: Message content

    Returns:
        Created message
    """
```

Request model:
```python
class ProjectMessageCreate(BaseModel):
    """Request to send project message."""

    from_agent: str
    content: str = Field(..., min_length=1, max_length=10000)
    message_type: Literal["statement", "question", "answer", "notification"] = "statement"
    in_reply_to: str | None = None
```

**SPEC-PROJ-BE-007:** Project Messages List Endpoint

Create `GET /api/v1/projects/{project_id}/messages` endpoint:

```python
@router.get("/projects/{project_id}/messages")
async def get_project_messages(
    project_id: str,
    limit: int = Query(50, ge=1, le=200),
    before: str | None = Query(None, description="Cursor for pagination")
) -> dict:
    """
    Get messages from a project chat room.

    Args:
        project_id: Project identifier
        limit: Number of messages to retrieve
        before: Pagination cursor (message ID)

    Returns:
        List of messages with pagination info
    """
```

### Frontend Specifications

**SPEC-PROJ-FE-001:** Project Management Interface

```html
<section class="card project-management">
    <div class="card-header">
        <h2 data-i18n="projects.title">Projects</h2>
        <button class="btn btn-primary" id="createProjectBtn">
            <svg><!-- plus icon --></svg>
            <span data-i18n="projects.create">New Project</span>
        </button>
    </div>
    <div class="card-body">
        <div class="project-list" id="projectList">
            <!-- Projects rendered here -->
        </div>
    </div>
</section>
```

Project item template:
```html
<div class="project-item" data-project-id="project-a">
    <div class="project-info">
        <span class="project-name">Project A</span>
        <span class="project-description">Description here</span>
    </div>
    <div class="project-actions">
        <button class="btn-icon" data-action="edit" title="Edit">
            <svg><!-- edit icon --></svg>
        </button>
        <button class="btn-icon" data-action="delete" title="Delete">
            <svg><!-- delete icon --></svg>
        </button>
    </div>
    <div class="project-stats">
        <span class="agent-count">5 agents</span>
        <span class="message-count">123 messages</span>
    </div>
</div>
```

**SPEC-PROJ-FE-002:** Project Create/Edit Modal

```html
<div class="modal" id="projectModal">
    <div class="modal-overlay"></div>
    <div class="modal-content modal-lg">
        <div class="modal-header">
            <h3 id="projectModalTitle">New Project</h3>
            <button class="btn-close">&times;</button>
        </div>
        <form id="projectForm" class="modal-body">
            <div class="form-group">
                <label for="projectId" data-i18n="projects.id">Project ID</label>
                <input type="text" id="projectId" name="project_id"
                       pattern="^[a-z][a-z0-9_]*[a-z0-9]$"
                       placeholder="my-project" required>
                <small class="form-text">
                    Lowercase alphanumeric with underscores
                </small>
            </div>
            <div class="form-group">
                <label for="projectName" data-i18n="projects.name">Name</label>
                <input type="text" id="projectName" name="name"
                       placeholder="My Project" required>
            </div>
            <div class="form-group">
                <label for="projectDescription" data-i18n="projects.description">Description</label>
                <textarea id="projectDescription" name="description"
                          rows="3" maxlength="500"></textarea>
            </div>
            <div class="form-group">
                <label for="projectTags" data-i18n="projects.tags">Tags</label>
                <input type="text" id="projectTags" name="tags"
                       placeholder="tag1, tag2, tag3">
            </div>
        </form>
        <div class="modal-footer">
            <button type="button" class="btn btn-secondary" id="cancelProjectBtn">Cancel</button>
            <button type="submit" form="projectForm" class="btn btn-primary">Save Project</button>
        </div>
    </div>
</div>
```

**SPEC-PROJ-FE-003:** Chat Room Interface

```html
<div class="chat-room" data-project-id="project-a">
    <div class="chat-header">
        <div class="chat-info">
            <svg class="chat-icon"><!-- hash icon --></svg>
            <div class="chat-details">
                <h3 class="chat-title">project-a</h3>
                <span class="chat-topic">Project A Discussion</span>
            </div>
        </div>
        <div class="chat-actions">
            <button class="btn-icon" data-action="members" title="Members">
                <svg><!-- users icon --></svg>
            </button>
            <button class="btn-icon" data-action="settings" title="Settings">
                <svg><!-- settings icon --></svg>
            </button>
        </div>
    </div>

    <div class="chat-messages" id="chatMessages">
        <!-- Messages rendered here -->
        <div class="chat-divider">
            <span>Today</span>
        </div>
        <div class="chat-message" data-message-id="msg-1">
            <div class="message-avatar">FE</div>
            <div class="message-content">
                <div class="message-header">
                    <span class="message-author">@FrontendExpert</span>
                    <span class="message-time">10:30 AM</span>
                </div>
                <div class="message-body">
                    Here is the API design for the new endpoint...
                </div>
            </div>
        </div>
    </div>

    <div class="chat-input-area">
        <div class="input-wrapper">
            <button class="btn-icon input-action" data-action="attach" title="Attach file">
                <svg><!-- plus icon --></svg>
            </button>
            <input type="text" id="chatInput"
                   placeholder="Message #project-a"
                   autocomplete="off">
            <button class="btn-icon input-action" data-action="emoji" title="Emoji">
                <svg><!-- emoji icon --></svg>
            </button>
        </div>
        <button class="btn btn-primary" id="sendChatBtn">
            <svg><!-- send icon --></svg>
        </button>
    </div>
</div>
```

**SPEC-PROJ-FE-004:** Agent Assignment Interface

```html
<div class="agent-assignment" data-project-id="project-a">
    <div class="assignment-header">
        <h3>Assign Agents</h3>
        <button class="btn-icon" data-action="add-agent" title="Add Agent">
            <svg><!-- plus icon --></svg>
        </button>
    </div>
    <div class="assigned-agents" id="assignedAgents">
        <!-- Assigned agents rendered here -->
    </div>
    <div class="available-agents" id="availableAgents">
        <!-- Available agents for assignment -->
    </div>
</div>
```

### WebSocket Specifications

**SPEC-PROJ-WS-001:** Message Broadcast

When a message is sent to a project, broadcast via WebSocket:

```json
{
    "type": "project_message",
    "project_id": "project-a",
    "data": {
        "message_id": "msg-123",
        "from_agent": "@FrontendExpert",
        "content": "Here is the design...",
        "timestamp": "2026-02-02T10:30:15Z"
    }
}
```

**SPEC-PROJ-WS-002:** Project Update Events

When project is updated, broadcast to all connected clients:

```json
{
    "type": "project_updated",
    "project_id": "project-a",
    "data": {
        "name": "Updated Project Name",
        "description": "New description"
    }
}
```

**SPEC-PROJ-WS-003:** Agent Assignment Events

When agent is assigned/unassigned, broadcast:

```json
{
    "type": "agent_assignment_changed",
    "project_id": "project-a",
    "data": {
        "agent_id": "agent-123",
        "action": "assigned"
    }
}
```

### Data Models

**SPEC-PROJ-DM-001:** Project Message Model

```python
class ProjectMessage(BaseModel):
    """Message in a project chat room."""

    message_id: str = Field(default_factory=lambda: f"msg-{uuid4()}")
    project_id: str
    from_agent: str
    content: str
    message_type: Literal["statement", "question", "answer", "notification"]
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    in_reply_to: str | None = None
    reactions: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
```

**SPEC-PROJ-DM-002:** Agent Assignment Model

```python
class AgentAssignment(BaseModel):
    """Agent-to-project assignment."""

    agent_id: str
    project_id: str
    role: Literal["owner", "admin", "member", "guest"]
    assigned_at: datetime = Field(default_factory=datetime.utcnow)
    assigned_by: str
```

**SPEC-PROJ-DM-003:** Project Chat Room State

```python
class ProjectChatRoom(BaseModel):
    """State of a project chat room."""

    project_id: str
    messages: list[ProjectMessage]
    participants: list[str]  # Connected agent IDs
    last_activity: datetime
    unread_count: int = 0
```

---

## Dependencies

### Internal Dependencies

- **SPEC-MCP-BROKER-002**: Multi-project support (provides project models and registry)
- **SPEC-UI-PROJECTS-001**: Project sidebar integration (already specified)
- **SPEC-UI-MESSAGES-001**: Message list view (already specified)
- **SPEC-UI-I18N-001**: Translatable project labels

### External Dependencies

- **fastapi >= 0.115.0**: For REST API endpoints
- **websockets**: For WebSocket support
- **Existing storage layer**: In-memory or Redis for persistence

---

## Quality Gates

### TRUST 5 Framework

**Tested:**
- Unit tests for project CRUD operations
- Unit tests for agent assignment/unassignment
- Integration tests for chat room message flow
- WebSocket message broadcast tests
- 85%+ code coverage requirement

**Readable:**
- Clear endpoint naming: `/projects`, `/projects/{id}/agents`, `/projects/{id}/messages`
- Consistent request/response model naming
- Documented WebSocket message types

**Unified:**
- Consistent with existing API patterns
- Reuses existing authentication and error handling
- Follows established frontend component patterns

**Secured:**
- All management endpoints require authentication
- API keys only shown on creation, not in list responses
- Project access validated per request
- Cross-project message permissions enforced

**Trackable:**
- Conventional commits: `feat(project):`, `fix(chat):`
- Component prefixes: `project/`, `chat/`
- Audit trail for project changes (created_at, last_modified)

---

## Related Documents

- **PLAN:** `.moai/specs/SPEC-PROJECT-001/plan.md` - Implementation milestones
- **ACCEPTANCE:** `.moai/specs/SPEC-PROJECT-001/acceptance.md` - Test scenarios

---

**END OF SPEC-PROJECT-001**
