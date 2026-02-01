# Implementation Plan: SPEC-UI-MESSAGES-001

**SPEC ID:** SPEC-UI-MESSAGES-001
**Title:** Message History List View Implementation Plan
**Created:** 2026-02-01

---

## Overview

This plan outlines the implementation of a message history list view for the Communication Server dashboard, enabling users to browse and filter messages similar to a chat interface.

---

## Implementation Milestones

### Primary Goal (Priority High)

**Milestone 1: Backend Message API**

Implement backend endpoints for message history.

**Tasks:**
- Create `GET /api/v1/messages` endpoint with filtering
- Create `GET /api/v1/messages/{message_id}` endpoint
- Implement message pagination and search
- Add message repository methods for history queries

**Success Criteria:**
- Messages API returns paginated message list
- Message detail endpoint returns full content
- Filtering by project_id works correctly

**Estimated Complexity:** Medium

---

### Secondary Goal (Priority High)

**Milestone 2: Message List Component**

Create the message list UI component.

**Tasks:**
- Add messages section to dashboard HTML
- Create message item rendering
- Add CSS styling for message list
- Implement empty state

**Success Criteria:**
- Message list visible on dashboard
- Messages display in chat-like format
- Empty state shows helpful message

**Estimated Complexity:** High

---

### Tertiary Goal (Priority Medium)

**Milestone 3: Message Detail Modal**

Implement message detail view.

**Tasks:**
- Create modal component for full message view
- Add click handler for message items
- Implement modal open/close logic
- Add message metadata display

**Success Criteria:**
- Clicking message opens modal
- Modal shows full message content
- Modal closes with button or overlay click

**Estimated Complexity:** Medium

---

### Final Goal (Priority Low)

**Milestone 4: Real-time Updates and Polish**

Add real-time functionality and polish features.

**Tasks:**
- Integrate with WebSocket for new messages
- Implement infinite scroll for pagination
- Add project filter dropdown
- Add search functionality (optional)
- Add timestamp grouping

**Success Criteria:**
- New messages appear without refresh
- Scroll loads older messages
- Project filter works correctly

**Estimated Complexity:** Medium

---

## Technical Approach

### Directory Structure

```
src/communication_server/
├── static/
│   ├── css/
│   │   └── styles.css (add message styles)
│   └── js/
│       ├── messages.js (new module)
│       └── api.js (add message APIs)
└── api/
    └── messages.py (new endpoint)
```

### HTML Layout

Add to dashboard main content (right column, after charts):

```html
<!-- Messages Section -->
<section class="card messages-section">
    <div class="card-header">
        <h2>Messages</h2>
        <div class="messages-controls">
            <select id="messageProjectFilter" class="select-filter">
                <option value="">All Projects</option>
            </select>
            <button class="btn-icon" id="refreshMessagesBtn" title="Refresh">
                <svg><!-- refresh icon --></svg>
            </button>
        </div>
    </div>
    <div class="card-body">
        <div class="messages-list" id="messagesList">
            <div class="loading-state">
                <div class="spinner"></div>
                <p>로딩 중...</p>
            </div>
        </div>
        <div class="messages-loading-more" id="messagesLoadingMore" style="display: none;">
            <div class="spinner-small"></div>
            <span>Load more...</span>
        </div>
    </div>
</section>

<!-- Message Detail Modal -->
<div class="modal" id="messageModal">
    <div class="modal-overlay" id="messageModalOverlay"></div>
    <div class="modal-content">
        <div class="modal-header">
            <h3>Message Details</h3>
            <button class="btn-close" id="closeMessageModal">&times;</button>
        </div>
        <div class="modal-body">
            <div class="message-detail"></div>
        </div>
    </div>
</div>
```

### CSS Styling

```css
/* Messages Section */
.messages-section {
    grid-column: 1 / -1;
}

.messages-controls {
    display: flex;
    gap: 8px;
    align-items: center;
}

.select-filter {
    padding: 6px 12px;
    border-radius: 6px;
    border: 1px solid var(--border-color);
    background: var(--bg-tertiary);
    color: var(--text-primary);
    font-size: 14px;
    cursor: pointer;
}

.messages-list {
    max-height: 400px;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 8px;
}

.message-item {
    padding: 12px;
    background: var(--bg-tertiary);
    border-radius: 8px;
    cursor: pointer;
    transition: background-color 0.2s;
}

.message-item:hover {
    background: var(--bg-hover);
}

.message-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 8px;
}

.message-participants {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 13px;
}

.message-sender {
    color: var(--primary-color);
    font-weight: 500;
}

.message-recipient {
    color: var(--text-secondary);
}

.message-arrow {
    width: 14px;
    height: 14px;
    color: var(--text-muted);
}

.message-timestamp {
    font-size: 12px;
    color: var(--text-muted);
}

.message-preview {
    font-size: 14px;
    color: var(--text-primary);
    line-height: 1.4;
    overflow: hidden;
    text-overflow: ellipsis;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
}

.message-meta {
    display: flex;
    gap: 8px;
    margin-top: 8px;
}

.message-project,
.message-type {
    font-size: 11px;
    padding: 2px 8px;
    border-radius: 4px;
    background: var(--bg-secondary);
    color: var(--text-secondary);
}

/* Message Detail Modal */
.modal {
    display: none;
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    z-index: 1000;
}

.modal.active {
    display: flex;
    align-items: center;
    justify-content: center;
}

.modal-overlay {
    position: absolute;
    inset: 0;
    background: rgba(0, 0, 0, 0.5);
}

.modal-content {
    position: relative;
    background: var(--bg-primary);
    border-radius: 12px;
    max-width: 600px;
    width: 90%;
    max-height: 80vh;
    overflow: hidden;
    display: flex;
    flex-direction: column;
}

.modal-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 16px 20px;
    border-bottom: 1px solid var(--border-color);
}

.modal-body {
    padding: 20px;
    overflow-y: auto;
}

.btn-close {
    background: none;
    border: none;
    font-size: 24px;
    color: var(--text-secondary);
    cursor: pointer;
    padding: 0;
    width: 32px;
    height: 32px;
}

/* Message Detail Styles */
.message-detail-header {
    display: grid;
    grid-template-columns: auto 1fr;
    gap: 8px 16px;
    margin-bottom: 16px;
}

.message-detail-participants {
    display: contents;
}

.message-detail-participants .label {
    color: var(--text-secondary);
    font-size: 13px;
}

.message-detail-participants .value {
    color: var(--text-primary);
    font-weight: 500;
}

.message-detail-timestamp {
    color: var(--text-muted);
    font-size: 13px;
    margin-bottom: 16px;
}

.message-detail-content {
    padding: 16px;
    background: var(--bg-tertiary);
    border-radius: 8px;
    font-family: monospace;
    font-size: 14px;
    line-height: 1.6;
    white-space: pre-wrap;
    word-break: break-word;
}

.message-detail-meta {
    display: flex;
    gap: 8px;
    margin-top: 16px;
}

.message-detail-meta .badge {
    padding: 4px 12px;
    border-radius: 12px;
    font-size: 12px;
    background: var(--primary-bg);
    color: var(--primary-color);
}
```

### JavaScript Module

Create `src/communication_server/static/js/messages.js`:

```javascript
/**
 * Messages Module
 *
 * Manages message history list and detail view.
 */

class MessagesList {
    constructor() {
        this.messages = [];
        this.currentProject = null;
        this.offset = 0;
        this.limit = 50;
        this.hasMore = true;
        this.isLoading = false;
    }

    async init() {
        // Cache DOM elements
        this.messagesList = document.getElementById('messagesList');
        this.projectFilter = document.getElementById('messageProjectFilter');
        this.loadingMore = document.getElementById('messagesLoadingMore');

        // Load messages
        await this.loadMessages();

        // Set up event listeners
        this.setupEventListeners();

        // Set up infinite scroll
        this.setupInfiniteScroll();
    }

    async loadMessages(reset = true) {
        if (this.isLoading) return;

        this.isLoading = true;

        if (reset) {
            this.offset = 0;
            this.hasMore = true;
        }

        this.showLoading();

        try {
            const data = await fetchMessages({
                project_id: this.currentProject,
                limit: this.limit,
                offset: this.offset
            });

            if (reset) {
                this.messages = data.messages || [];
            } else {
                this.messages = [...this.messages, ...(data.messages || [])];
            }

            this.hasMore = data.messages?.length === this.limit;
            this.offset += data.messages?.length || 0;

            this.renderMessages();
        } catch (error) {
            console.error('Failed to load messages:', error);
            this.showError();
        } finally {
            this.isLoading = false;
            this.hideLoading();
        }
    }

    renderMessages() {
        if (!this.messagesList) return;

        if (this.messages.length === 0) {
            this.renderEmptyState();
            return;
        }

        this.messagesList.innerHTML = this.messages
            .map(msg => this.createMessageItem(msg))
            .join('');
    }

    createMessageItem(message) {
        const { message_id, from_agent, to_agent, timestamp, content_preview, project_id, message_type } = message;

        return `
            <div class="message-item" data-message-id="${escapeHtml(message_id)}">
                <div class="message-header">
                    <div class="message-participants">
                        <span class="message-sender">${escapeHtml(from_agent)}</span>
                        ${this.getMessageArrow(message_type)}
                        <span class="message-recipient">${escapeHtml(to_agent || 'All')}</span>
                    </div>
                    <span class="message-timestamp">${formatTimestamp(timestamp)}</span>
                </div>
                <div class="message-preview">${escapeHtml(content_preview)}</div>
                <div class="message-meta">
                    ${project_id ? `<span class="message-project">${escapeHtml(project_id)}</span>` : ''}
                    <span class="message-type">${message_type}</span>
                </div>
            </div>
        `;
    }

    getMessageArrow(type) {
        if (type === 'broadcast') {
            return `<svg class="message-arrow" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M12 2L2 7l10 5 10-5-10-5z"/>
                <path d="M2 17l10 5 10-5"/>
                <path d="M2 12l10 5 10-5"/>
            </svg>`;
        }
        return `<svg class="message-arrow" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="5" y1="12" x2="19" y2="12"/>
            <polyline points="12 5 19 12 12 19"/>
        </svg>`;
    }

    renderEmptyState() {
        this.messagesList.innerHTML = `
            <div class="empty-state">
                <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
                </svg>
                <p>No messages found</p>
            </div>
        `;
    }

    showLoading() {
        this.messagesList.innerHTML = `
            <div class="loading-state">
                <div class="spinner"></div>
                <p>로딩 중...</p>
            </div>
        `;
    }

    hideLoading() {
        // Loading state replaced by renderMessages
    }

    showError() {
        this.messagesList.innerHTML = `
            <div class="error-state">
                <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <circle cx="12" cy="12" r="10"/>
                    <line x1="12" y1="8" x2="12" y2="12"/>
                    <line x1="12" y1="16" x2="12.01" y2="16"/>
                </svg>
                <p>Failed to load messages</p>
                <button class="btn btn-secondary" onclick="messagesList.loadMessages()">
                    Retry
                </button>
            </div>
        `;
    }

    setProjectFilter(projectId) {
        this.currentProject = projectId;
        this.loadMessages(true);
    }

    setupEventListeners() {
        // Message item click
        this.messagesList.addEventListener('click', (e) => {
            const item = e.target.closest('.message-item');
            if (item) {
                const messageId = item.dataset.messageId;
                this.openMessageDetail(messageId);
            }
        });

        // Project filter change
        this.projectFilter?.addEventListener('change', (e) => {
            this.setProjectFilter(e.target.value || null);
        });

        // Refresh button
        document.getElementById('refreshMessagesBtn')?.addEventListener('click', () => {
            this.loadMessages(true);
        });
    }

    setupInfiniteScroll() {
        const observer = new IntersectionObserver((entries) => {
            if (entries[0].isIntersecting && this.hasMore && !this.isLoading) {
                this.loadMessages(false);
            }
        }, { threshold: 0.1 });

        observer.observe(this.loadingMore);
    }

    async openMessageDetail(messageId) {
        try {
            const message = await fetchMessageDetail(messageId);
            showMessageModal(message);
        } catch (error) {
            console.error('Failed to load message detail:', error);
        }
    }

    prependMessage(message) {
        // Add new message at the beginning
        this.messages.unshift(message);
        this.renderMessages();
    }
}

// Initialize messages list
const messagesList = new MessagesList();

// Export for dashboard integration
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { MessagesList };
}
```

### Backend API Implementation

Create `src/communication_server/api/messages.py`:

```python
"""
Message history API endpoints.
"""

from fastapi import APIRouter, Query
from datetime import datetime
from communication_server.dependencies import get_communication_repository
from communication_server.services.agent_registry import get_agent_registry

router = APIRouter(prefix="/messages", tags=["messages"])

@router.get("")
async def list_messages(
    project_id: str | None = Query(None, description="Filter by project ID"),
    limit: int = Query(50, ge=1, le=200, description="Messages per page"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    search: str | None = Query(None, description="Search in content"),
    comm_repo: CommunicationRepository = Depends(get_communication_repository)
) -> dict:
    """
    Get message history with optional filtering.

    Returns messages in reverse chronological order.
    """
    # Fetch messages from repository
    messages = await comm_repo.get_message_history(
        project_id=project_id,
        limit=limit,
        offset=offset,
        search=search
    )

    # Format for response
    message_items = []
    for msg in messages:
        # Get agent info for display names
        registry = get_agent_registry()
        from_agent = await registry.get_agent_by_full_id(msg.from_agent_id)
        to_agent = await registry.get_agent_by_full_id(msg.to_agent_id) if msg.to_agent_id else None

        message_items.append({
            "message_id": msg.message_id,
            "from_agent": from_agent.agent_id if from_agent else msg.from_agent_id,
            "to_agent": to_agent.agent_id if to_agent else None,
            "timestamp": msg.timestamp.isoformat(),
            "content_preview": msg.content[:100] + "..." if len(msg.content) > 100 else msg.content,
            "project_id": msg.project_id,
            "message_type": msg.message_type,
        })

    return {
        "messages": message_items,
        "count": len(message_items),
        "has_more": len(message_items) == limit
    }

@router.get("/{message_id}")
async def get_message_detail(
    message_id: str,
    comm_repo: CommunicationRepository = Depends(get_communication_repository)
) -> dict:
    """
    Get full details of a specific message.
    """
    message = await comm_repo.get_message(message_id)

    if not message:
        raise HTTPException(status_code=404, detail="Message not found")

    registry = get_agent_registry()
    from_agent = await registry.get_agent_by_full_id(message.from_agent_id)
    to_agent = await registry.get_agent_by_full_id(message.to_agent_id) if message.to_agent_id else None

    return {
        "message_id": message.message_id,
        "from_agent": from_agent.agent_id if from_agent else message.from_agent_id,
        "to_agent": to_agent.agent_id if to_agent else None,
        "timestamp": message.timestamp.isoformat(),
        "content": message.content,
        "content_type": message.content_type,
        "project_id": message.project_id,
        "message_type": message.message_type,
        "metadata": message.metadata or {},
    }
```

---

## Migration Strategy

### Phase 1: Backend Foundation

Implement message history API:
1. Add repository methods for message queries
2. Create API endpoints
3. Test with sample data
4. Document API

### Phase 2: Basic UI

Add message list to dashboard:
1. Create message list component
2. Render messages from API
3. Add empty state
4. Test with real data

### Phase 3: Detail View

Add message detail modal:
1. Create modal component
2. Add click handlers
3. Display full message content
4. Test interaction

### Phase 4: Real-time and Polish

Complete functionality:
1. Add WebSocket integration
2. Implement infinite scroll
3. Add project filtering
4. Performance optimization

---

## Risks and Response Plans

### Risk 1: Large Message Dataset

**Description:** Performance issues with many messages

**Mitigation:**
- Implement pagination from start
- Use efficient database queries
- Cache message lists

**Response Plan:**
- Add virtual scrolling if needed
- Implement message aging/archive

### Risk 2: Real-time Update Complexity

**Description:** WebSocket updates may conflict with pagination

**Mitigation:**
- Use prepend for new messages
- Maintain offset for existing pagination
- Debounce rapid updates

**Response Plan:**
- Simplify to manual refresh if needed
- Add visual indicator for new messages

### Risk 3: Sensitive Content Exposure

**Description:** Message modal may expose sensitive data

**Mitigation:**
- Ensure authentication check
- Validate message access permissions
- Sanitize HTML content

**Response Plan:**
- Add content warnings for large messages
- Implement content truncation

---

## Testing Strategy

### Unit Tests

- Message list rendering
- Message filtering logic
- Modal open/close logic
- Pagination state management

### Integration Tests

- Message API returns correct data
- Project filtering works
- Pagination works correctly

### E2E Tests

- User can browse message list
- User can open message detail
- User can filter by project
- Scroll loads more messages

---

## Dependencies and Coordination

### Prerequisites

- **SPEC-UI-PROJECTS-001**: Project sidebar for project filtering

### Blocks

None - this is independent feature

### Coordination Notes

Coordinate with **SPEC-UI-I18N-001** for message UI labels.

---

## Success Metrics

### Completion Criteria

- Message list displays messages correctly
- Message detail modal opens and closes
- Project filter works
- Infinite scroll loads older messages
- All acceptance criteria pass

### Performance Targets

- Message list render time < 100ms for 50 items
- Detail modal opens within 50ms
- Scroll loads more messages without lag

---

**END OF IMPLEMENTATION PLAN - SPEC-UI-MESSAGES-001**
