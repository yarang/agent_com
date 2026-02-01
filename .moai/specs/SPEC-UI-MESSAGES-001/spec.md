# SPEC-UI-MESSAGES-001: Message History List View

**SPEC ID:** SPEC-UI-MESSAGES-001
**Title:** Message History List View with Project Filtering
**Created:** 2026-02-01
**Status:** Planned
**Priority:** High

---

## Environment

### Context

The Communication Server dashboard currently displays agent status and activity timeline, but does not provide a dedicated view for browsing message history. Users request a message history list similar to a chat interface, with the ability to filter by project.

### Current State

- Timeline exists but shows mixed event types (status changes, meetings, decisions)
- No dedicated message-only view
- No message filtering by project
- Message data exists in communication repository

### Target State

- Dedicated message history panel/section
- Chat-like message list with sender, recipient, timestamp, content preview
- Project-based filtering for messages
- Real-time updates via WebSocket
- Message detail modal/view

---

## Assumptions

### Technical Assumptions

- **Confidence: High** - Message data exists in CommunicationRepository
- **Evidence Basis**: Communication repository interfaces are defined
- **Risk if Wrong**: May need to extend repository for message history queries
- **Validation Method**: Review repository implementation

### UI/UX Assumptions

- **Confidence: High** - Chat-like interface is familiar pattern
- **Evidence Basis**: Messaging apps (Slack, Discord, Teams) use this pattern
- **Risk if Wrong**: Users may prefer different message organization
- **Validation Method**: User feedback after implementation

### Performance Assumptions

- **Confidence: Medium** - Message history could grow large
- **Evidence Basis**: Active agents could generate thousands of messages
- **Risk if Wrong**: Performance degradation with many messages
- **Validation Method**: Load test with 1000+ messages

---

## Requirements (EARS Format)

### Ubiquitous Requirements

**REQ-MSG-001:** The system **shall** provide a message history section in the dashboard.

**REQ-MSG-002:** The system **shall** display messages in reverse chronological order (newest first).

**REQ-MSG-003:** The system **shall** show sender, recipient, timestamp, and content preview for each message.

**REQ-MSG-004:** The system **shall** support filtering messages by project.

### Event-Driven Requirements

**WHEN** user clicks on a message in the history list, **THEN** the system **shall** display full message content in a modal.

**WHEN** a new message is sent/received, **THEN** the system **shall** add it to the top of the message list.

**WHEN** user selects a project filter, **THEN** the system **shall** filter messages to show only those involving agents from that project.

**WHEN** user scrolls to bottom of message list, **THEN** the system **shall** load older messages (infinite scroll).

### State-Driven Requirements

**IF** message list is empty, **THEN** the system **shall** display an empty state with helpful message.

**IF** message content exceeds preview length, **THEN** the system **shall** truncate with ellipsis.

**IF** message list contains more than 50 messages, **THEN** the system **shall** implement pagination or infinite scroll.

### Unwanted Requirements

The system **shall not** auto-refresh the entire message list on every new message (use prepend instead).

The system **shall not** expose sensitive message content without proper authentication.

### Optional Requirements

**Where possible**, the system **should** provide search functionality to filter messages by content.

**Where possible**, the system **should** show message direction indicators (sent/received).

**Where possible**, the system **should** support message timestamp grouping (Today, Yesterday, etc.).

---

## Specifications

### Frontend Specifications

**SPEC-MSG-FE-001:** Message List Component

```html
<section class="card messages-section">
    <div class="card-header">
        <h2>Messages</h2>
        <div class="messages-controls">
            <select id="messageProjectFilter" class="select-filter">
                <option value="">All Projects</option>
                <!-- Project options populated dynamically -->
            </select>
            <button class="btn-icon" id="refreshMessagesBtn" title="Refresh">
                <svg><!-- refresh icon --></svg>
            </button>
        </div>
    </div>
    <div class="card-body">
        <div class="messages-list" id="messagesList">
            <!-- Messages rendered here -->
        </div>
        <div class="messages-loading" id="messagesLoading" style="display: none;">
            <div class="spinner-small"></div>
        </div>
    </div>
</section>
```

**SPEC-MSG-FE-002:** Message Item Template

```html
<div class="message-item" data-message-id="msg-123">
    <div class="message-header">
        <div class="message-participants">
            <span class="message-sender">@FrontendExpert</span>
            <svg class="message-arrow"><!-- arrow icon --></svg>
            <span class="message-recipient">@BackendDev</span>
        </div>
        <span class="message-timestamp">2 minutes ago</span>
    </div>
    <div class="message-preview">
        Here is the API payload for the new endpoint...
    </div>
    <div class="message-meta">
        <span class="message-project">Project A</span>
        <span class="message-type">direct</span>
    </div>
</div>
```

**SPEC-MSG-FE-003:** Message Detail Modal

```html
<div class="modal" id="messageModal" style="display: none;">
    <div class="modal-overlay"></div>
    <div class="modal-content">
        <div class="modal-header">
            <h3>Message Details</h3>
            <button class="btn-close" id="closeMessageModal">&times;</button>
        </div>
        <div class="modal-body">
            <div class="message-detail-header">
                <div class="message-detail-participants">
                    <span class="label">From:</span>
                    <span class="value" id="modalSender">@FrontendExpert</span>
                </div>
                <div class="message-detail-participants">
                    <span class="label">To:</span>
                    <span class="value" id="modalRecipient">@BackendDev</span>
                </div>
            </div>
            <div class="message-detail-timestamp" id="modalTimestamp">
                2026-02-01 14:30:15 UTC
            </div>
            <div class="message-detail-content" id="modalContent">
                <!-- Full message content here -->
            </div>
            <div class="message-detail-meta" id="modalMeta">
                <span class="badge" id="modalProject">Project A</span>
                <span class="badge" id="modalType">direct</span>
            </div>
        </div>
    </div>
</div>
```

**SPEC-MSG-FE-004:** API Integration

Add to `js/api.js`:

```javascript
async function fetchMessages(options = {}) {
    const {
        project_id = null,
        limit = 50,
        offset = 0,
        search = null
    } = options;

    const params = new URLSearchParams({ limit, offset });
    if (project_id) params.append('project_id', project_id);
    if (search) params.append('search', search);

    const response = await fetchWithAuth(`${API_BASE_URL}/messages?${params}`);
    return await response.json();
}

async function fetchMessageDetail(messageId) {
    const response = await fetchWithAuth(`${API_BASE_URL}/messages/${messageId}`);
    return await response.json();
}
```

### Backend Specifications

**SPEC-MSG-BE-001:** Message List Endpoint

Create `GET /api/v1/messages` endpoint:

```python
@router.get("/messages")
async def list_messages(
    project_id: str | None = Query(None, description="Filter by project ID"),
    limit: int = Query(50, ge=1, le=200, description="Messages per page"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    search: str | None = Query(None, description="Search in content")
) -> dict:
    """
    Get message history with optional filtering.

    Returns messages in reverse chronological order.
    """
```

**SPEC-MSG-BE-002:** Message Detail Endpoint

Create `GET /api/v1/messages/{message_id}` endpoint:

```python
@router.get("/messages/{message_id}")
async def get_message_detail(message_id: str) -> dict:
    """
    Get full details of a specific message.

    Includes complete content, metadata, and related info.
    """
```

**SPEC-MSG-BE-003:** Project Message Count

Add to project response:

```python
@router.get("/projects")
async def list_projects() -> dict:
    """
    Get projects with message counts included.
    """
```

### Data Models

**SPEC-MSG-DM-001:** Message List Item Model

```python
class MessageListItem(BaseModel):
    """Message item for list view."""

    message_id: str
    from_agent: str  # Agent display ID
    to_agent: str | None  # Recipient (null for broadcast)
    timestamp: datetime
    content_preview: str  # Truncated content
    project_id: str | None
    message_type: Literal["direct", "broadcast", "reply"]
```

**SPEC-MSG-DM-002:** Message Detail Model

```python
class MessageDetail(BaseModel):
    """Full message details."""

    message_id: str
    from_agent: str
    to_agent: str | None
    timestamp: datetime
    content: str  # Full content
    content_type: str  # e.g., "text/plain", "application/json"
    project_id: str | None
    message_type: Literal["direct", "broadcast", "reply"]
    metadata: dict[str, Any] = {}
```

---

## Dependencies

### Internal Dependencies

- **SPEC-MCP-BROKER-002**: Multi-project support for filtering
- **SPEC-UI-PROJECTS-001**: Project sidebar integration
- **SPEC-UI-I18N-001**: Translatable message labels

### External Dependencies

None required

---

## Quality Gates

### TRUST 5 Framework

**Tested:**
- Unit tests for message filtering logic
- Integration tests for message API endpoints
- E2E tests for message list interaction

**Readable:**
- Clear component naming: `MessageList`, `MessageItem`, `MessageModal`
- Documented message data structure

**Unified:**
- Consistent with dashboard card styling
- Reuses existing modal component pattern

**Secured:**
- Message access respects authentication
- No sensitive data in URL parameters

**Trackable:**
- Conventional commits: `feat(messages):`, `fix(message-list):`
- Component prefix: `messages/`

---

## Related Documents

- **PLAN:** `.moai/specs/SPEC-UI-MESSAGES-001/plan.md` - Implementation milestones
- **ACCEPTANCE:** `.moai/specs/SPEC-UI-MESSAGES-001/acceptance.md` - Test scenarios

---

**END OF SPEC-UI-MESSAGES-001**
