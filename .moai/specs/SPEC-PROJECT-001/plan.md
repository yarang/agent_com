# Implementation Plan: SPEC-PROJECT-001

**SPEC ID:** SPEC-PROJECT-001
**Title:** Project Management (CRUD) and Chat-Like Message Organization
**Last Updated:** 2026-02-02

---

## Milestones (Priority-Based)

### Primary Goal (Must Have)

**P1 - Backend Project CRUD API**
- Create project management endpoints
- Implement project create, update, delete operations
- Add authentication and authorization
- Add input validation and error handling

**P1 - Agent Assignment Endpoints**
- Implement agent-to-project assignment API
- Implement agent unassignment API
- Update agent registry to track project assignments

**P1 - Project Chat Message API**
- Implement direct message sending to projects
- Implement project message list retrieval
- Add message pagination support

**P1 - Project Management UI**
- Create project list interface
- Implement project create/edit modal
- Implement project delete confirmation
- Connect to backend API endpoints

**P1 - Chat Room UI**
- Create chat room component
- Implement message list rendering
- Implement message input area
- Connect to WebSocket for real-time updates

### Secondary Goal (Should Have)

**P2 - WebSocket Integration**
- Implement project message broadcasting
- Implement project update events
- Implement agent assignment change events
- Add connection management

**P2 - Agent Assignment UI**
- Create agent assignment interface
- Implement drag-and-drop assignment
- Show assigned and available agents
- Handle unassignment actions

**P2 - Message Search**
- Implement message search API
- Add search UI to chat room
- Add search result highlighting

### Optional Goal (Nice to Have)

**P3 - Message Reactions**
- Add reaction API endpoint
- Implement reaction UI (emoji picker)
- Show reaction counts on messages

**P3 - Message Threading**
- Add reply-to functionality
- Implement threaded message view
- Add thread navigation

**P3 - File Attachments**
- Add file upload API
- Implement file attachment UI
- Handle file preview/download

---

## Technical Approach

### Architecture Design

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend Layer                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │  Project     │  │  Chat Room   │  │  Agent       │     │
│  │  Management  │  │  Interface   │  │  Assignment  │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
                            ↓ HTTP/WebSocket
┌─────────────────────────────────────────────────────────────┐
│                    API Layer                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │  Project     │  │  Message     │  │  Agent       │     │
│  │  Endpoints   │  │  Endpoints   │  │  Assignment  │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    Business Logic                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │  Project     │  │  Chat        │  │  Agent       │     │
│  │  Service     │  │  Service     │  │  Registry    │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    Data Layer                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │  Project     │  │  Message     │  │  Agent       │     │
│  │  Registry    │  │  Repository  │  │  Repository  │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
```

### Backend Implementation Strategy

**Phase 1: Project CRUD Endpoints**

1. Create new API router: `src/communication_server/api/project_management.py`
2. Implement `create_project()` endpoint
   - Validate project_id format
   - Call `ProjectRegistry.create_project()`
   - Return created project with API keys
3. Implement `update_project()` endpoint
   - Validate project exists
   - Update metadata and config
   - Update `last_modified` timestamp
4. Implement `delete_project()` endpoint
   - Check for active sessions
   - Call `ProjectRegistry.delete_project()`
   - Return confirmation

**Phase 2: Agent Assignment Endpoints**

1. Extend agent registry with assignment tracking
2. Implement `assign_agent_to_project()` endpoint
   - Validate agent and project exist
   - Create assignment record
   - Update project statistics
3. Implement `unassign_agent_from_project()` endpoint
   - Validate assignment exists
   - Remove assignment record
   - Update project statistics

**Phase 3: Chat Message Endpoints**

1. Create message service for project messages
2. Implement `send_project_message()` endpoint
   - Validate message content
   - Store message with project context
   - Broadcast via WebSocket
3. Implement `get_project_messages()` endpoint
   - Support pagination (cursor-based)
   - Filter by project_id
   - Return reverse chronological order

**Phase 4: WebSocket Integration**

1. Create WebSocket manager for project events
2. Implement message broadcasting
3. Implement project update events
4. Implement agent assignment events

### Frontend Implementation Strategy

**Phase 1: Project Management UI**

1. Create `static/js/project-management.js`
2. Implement project list component
3. Implement project create/edit modal
4. Implement delete confirmation dialog
5. Add API calls to `api.js`

**Phase 2: Chat Room UI**

1. Create `static/js/chat-room.js`
2. Implement chat room layout
3. Implement message list rendering
4. Implement message input handling
5. Add WebSocket connection management

**Phase 3: Agent Assignment UI**

1. Create `static/js/agent-assignment.js`
2. Implement assignment interface
3. Implement drag-and-drop functionality
4. Add assignment API integration

### Database/Storage Considerations

**Project Storage:**
- Use existing `ProjectRegistry` (in-memory by default)
- Consider Redis persistence for production
- Project data includes: metadata, config, API keys, statistics

**Message Storage:**
- Extend existing `CommunicationRepository` for project messages
- Add `project_id` field to message records
- Consider message TTL/expiry for cleanup

**Agent Assignment Storage:**
- Add assignment tracking to agent registry
- Store: agent_id, project_id, role, assigned_at
- Use in-memory storage with optional Redis

---

## File Changes Summary

### New Files

**Backend:**
- `src/communication_server/api/project_management.py` - Project CRUD endpoints
- `src/communication_server/api/project_chat.py` - Chat message endpoints
- `src/communication_server/services/project_service.py` - Project business logic
- `src/communication_server/services/chat_service.py` - Chat business logic
- `src/agent_comm_core/models/project_chat.py` - Chat message models
- `src/agent_comm_core/models/agent_assignment.py` - Assignment models

**Frontend:**
- `src/communication_server/static/js/project-management.js` - Project management UI
- `src/communication_server/static/js/chat-room.js` - Chat room UI
- `src/communication_server/static/js/agent-assignment.js` - Agent assignment UI
- `src/communication_server/static/css/chat.css` - Chat room styles
- `src/communication_server/static/css/project-management.css` - Project management styles

### Modified Files

**Backend:**
- `src/communication_server/api/projects.py` - Extend with new endpoints
- `src/communication_server/services/agent_registry.py` - Add assignment tracking
- `src/agent_comm_core/repositories/base.py` - Add project message methods

**Frontend:**
- `src/communication_server/static/js/api.js` - Add new API functions
- `src/communication_server/static/dashboard.html` - Add project management section
- `src/communication_server/static/css/main.css` - Add chat and project styles

---

## Risks and Response Plans

### Risk 1: Project Data Loss on Restart

**Probability:** Medium
**Impact:** High

**Response:**
- Enable Redis persistence for project registry
- Implement project export/import functionality
- Add warning in UI about in-memory storage

### Risk 2: WebSocket Connection Issues

**Probability:** Medium
**Impact:** Medium

**Response:**
- Implement reconnection logic with exponential backoff
- Add fallback to polling if WebSocket unavailable
- Show connection status indicator in UI

### Risk 3: Message Performance at Scale

**Probability:** Medium
**Impact:** Medium

**Response:**
- Implement cursor-based pagination from start
- Add message retention policy (e.g., 30 days)
- Consider message indexing for search

### Risk 4: Cross-Project Data Leakage

**Probability:** Low
**Impact:** High

**Response:**
- Validate project context on every request
- Use separate database namespaces per project
- Add security audit logging

---

## Dependencies and Integration Points

### External Dependencies

- **fastapi >= 0.115.0** - Already used
- **websockets** - Add for WebSocket support
- **redis (optional)** - For persistent storage

### Internal Dependencies

- **ProjectRegistry** - Use existing registry from mcp_broker
- **AgentRegistry** - Extend for assignment tracking
- **CommunicationRepository** - Extend for project messages
- **Authentication** - Reuse existing auth middleware

---

## Testing Strategy

### Unit Tests

- Project CRUD operations
- Agent assignment/unassignment
- Message creation and retrieval
- WebSocket message broadcasting

### Integration Tests

- End-to-end project creation flow
- Agent assignment with project updates
- Chat message sending and delivery
- WebSocket connection lifecycle

### E2E Tests

- User creates project and assigns agents
- User sends message to project chat room
- Real-time message updates across clients

---

## Success Criteria

### Completion Metrics

- All Primary Goal endpoints implemented and tested
- Project management UI functional
- Chat room UI functional with WebSocket updates
- 85%+ code coverage

### Performance Targets

- Project API response time < 100ms (P95)
- Message delivery latency < 500ms (P95)
- Support 50+ concurrent WebSocket connections

### Quality Gates

- Zero type errors (mypy)
- Zero lint errors (ruff)
- All tests passing
- Security review completed

---

**END OF PLAN - SPEC-PROJECT-001**
