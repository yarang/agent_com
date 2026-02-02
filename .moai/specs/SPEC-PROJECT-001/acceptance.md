# Acceptance Criteria: SPEC-PROJECT-001

**SPEC ID:** SPEC-PROJECT-001
**Title:** Project Management (CRUD) and Chat-Like Message Organization
**Last Updated:** 2026-02-02

---

## Definition of Done

A feature is considered complete when:

1. All requirements in spec.md are implemented
2. All acceptance criteria below pass verification
3. Code coverage meets 85% threshold
4. TRUST 5 quality gates are satisfied
5. Documentation is updated

---

## Acceptance Criteria

### AC-PROJ-001: Project Creation

**Given** a user is authenticated
**When** user submits valid project creation data
**Then** system shall create the project
**And** generate API keys
**And** return the created project with API keys

**Test Scenarios:**

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Valid project | Authenticated user | Submit valid project_id, name, description | Project created with API keys returned |
| Duplicate project_id | Project "test-project" exists | Submit project_id "test-project" | Return 400 error with duplicate message |
| Invalid project_id | Authenticated user | Submit project_id "Invalid-ID!" | Return 400 validation error |
| Missing required fields | Authenticated user | Submit without name field | Return 400 validation error |

**Verification Method:**
- Automated API test for project creation endpoint
- Verify API key format: `{project_id}_{key_id}_{secret}`
- Verify project appears in project list

---

### AC-PROJ-002: Project Update

**Given** a project exists
**When** user submits valid update data
**Then** system shall update the project metadata
**And** update the `last_modified` timestamp
**And** return the updated project

**Test Scenarios:**

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Valid update | Project "test-project" exists | Submit new name and description | Project updated with new values |
| Update non-existent | No project "missing" exists | Submit update for "missing" | Return 404 error |
| Update with reserved ID | Project "default" exists | Attempt to update project_id | Return 400 validation error |

**Verification Method:**
- Automated API test for project update endpoint
- Verify timestamp is updated
- Verify old values are replaced

---

### AC-PROJ-003: Project Deletion

**Given** a project exists
**When** user requests project deletion
**And** project has no active sessions
**Then** system shall delete the project
**And** return confirmation

**Test Scenarios:**

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Delete empty project | Project exists with 0 active sessions | Submit delete request | Project deleted, confirmation returned |
| Delete with sessions | Project has active agent sessions | Submit delete request | Return 400 error with session count |
| Delete non-existent | No project exists | Submit delete request | Return 404 error |
| Force delete (admin) | Project has sessions, user is admin | Submit delete with force=true | Project deleted |

**Verification Method:**
- Automated API test for deletion scenarios
- Verify project removed from registry
- Verify active session check works

---

### AC-PROJ-004: Agent-to-Project Assignment

**Given** a project and agent both exist
**When** user assigns agent to project
**Then** system shall create assignment record
**And** update project agent count
**And** return assignment confirmation

**Test Scenarios:**

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Valid assignment | Project "A" and agent "agent-1" exist | Submit assignment request | Assignment created, agent count incremented |
| Duplicate assignment | Agent already assigned to project | Submit same assignment | Return 400 error (already assigned) |
| Assign to non-existent project | Agent exists, project does not | Submit assignment | Return 404 error |
| Assign non-existent agent | Project exists, agent does not | Submit assignment | Return 404 error |

**Verification Method:**
- Automated API test for assignment endpoint
- Verify agent appears in project agent list
- Verify agent count updates

---

### AC-PROJ-005: Agent Unassignment

**Given** an agent is assigned to a project
**When** user unassigns agent from project
**Then** system shall remove assignment record
**And** update project agent count
**And** return confirmation

**Test Scenarios:**

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Valid unassignment | Agent assigned to project | Submit unassignment request | Assignment removed, count decremented |
| Unassign not assigned | Agent not assigned to project | Submit unassignment | Return 404 error |
| Unassign from non-existent | Project does not exist | Submit unassignment | Return 404 error |

**Verification Method:**
- Automated API test for unassignment endpoint
- Verify agent removed from project agent list

---

### AC-PROJ-006: Project Message Sending

**Given** a project exists
**And** user is authenticated
**When** user sends a message to project chat
**Then** system shall store the message
**And** broadcast via WebSocket
**And** return the created message

**Test Scenarios:**

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Valid message | Project exists, user authenticated | Submit message content | Message stored and broadcast |
| Empty message | Project exists | Submit empty content | Return 400 validation error |
| Message too long | Project exists | Submit 10001 character content | Return 400 validation error |
| Non-existent project | - | Submit to missing project | Return 404 error |

**Verification Method:**
- Automated API test for message endpoint
- Verify message stored with correct project_id
- Verify WebSocket broadcast includes message data

---

### AC-PROJ-007: Project Message Retrieval

**Given** a project has messages
**When** user requests project messages
**Then** system shall return messages in reverse chronological order
**And** support pagination

**Test Scenarios:**

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Default page | Project has 100 messages | Request without params | Return 50 most recent messages |
| With limit | Project has messages | Request with limit=20 | Return 20 most recent messages |
| With cursor | Previous page returned cursor | Request with before=cursor | Return older messages |
| Empty project | Project has 0 messages | Request messages | Return empty array |

**Verification Method:**
- Automated API test for retrieval endpoint
- Verify message order (newest first)
- Verify pagination cursor works

---

### AC-PROJ-008: Project Management UI

**Given** user accesses dashboard
**When** user navigates to Projects section
**Then** system shall display project management interface
**And** show list of all projects
**And** provide create/edit/delete actions

**Test Scenarios:**

| Scenario | Given | When | Then |
|----------|-------|------|------|
| View projects | Dashboard loaded | Navigate to Projects | Show project list with stats |
| Create project modal | Projects section loaded | Click "New Project" | Show create project modal |
| Edit project modal | Project exists | Click edit on project | Show edit modal with current values |
| Delete confirmation | Project exists | Click delete on project | Show confirmation dialog |

**Verification Method:**
- Manual UI testing
- Automated E2E test with Playwright
- Verify modal interactions work

---

### AC-PROJ-009: Chat Room Interface

**Given** user selects a project
**When** project chat room is displayed
**Then** system shall show chat interface
**And** load recent messages
**And** provide message input

**Test Scenarios:**

| Scenario | Given | When | Then |
|----------|-------|------|------|
| View chat room | Project selected | Open chat room | Show message history |
| Send message | Chat room open | Type and send message | Message appears in list |
| Real-time update | Chat room open on 2 clients | Send message from client 1 | Message appears on client 2 |
| Empty chat room | Project with no messages | Open chat room | Show empty state message |

**Verification Method:**
- Manual UI testing
- WebSocket integration test
- Verify real-time updates work

---

### AC-PROJ-010: WebSocket Real-Time Updates

**Given** user has active WebSocket connection
**When** project event occurs (message, update, assignment)
**Then** system shall broadcast event to connected clients
**And** clients shall update UI accordingly

**Test Scenarios:**

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Message broadcast | 2 clients connected to project | Client 1 sends message | Client 2 receives message event |
| Project update | 2 clients connected | Project updated via API | Both clients receive update event |
| Assignment change | Client connected to project | Agent assigned to project | Client receives assignment event |
| Reconnection | Client disconnected | Network restored | Client reconnects and receives missed events |

**Verification Method:**
- WebSocket integration test
- Verify event format matches specification
- Test reconnection logic

---

### AC-PROJ-011: Agent Assignment UI

**Given** user accesses project settings
**When** user views agent assignment section
**Then** system shall show assigned and available agents
**And** allow assignment/unassignment actions

**Test Scenarios:**

| Scenario | Given | When | Then |
|----------|-------|------|------|
| View assignments | Project exists | Open assignment UI | Show assigned and available agents |
| Assign agent | Available agent exists | Drag agent to assigned | Agent moves to assigned list |
| Unassign agent | Agent assigned | Click remove on agent | Agent moves to available list |
| Search agents | Many agents available | Type in search box | Filter agent list |

**Verification Method:**
- Manual UI testing
- Verify drag-and-drop functionality
- Verify API calls on assignment changes

---

## Quality Gate Verification

### Tested Pillar

**Verification:**
- [ ] Unit tests exist for all endpoints (pytest)
- [ ] Integration tests for API workflows
- [ ] WebSocket tests for real-time features
- [ ] E2E tests for critical user flows
- [ ] Coverage report shows >= 85%

**Command:**
```bash
pytest tests/ --cov=src --cov-report=html --cov-fail-under=85
```

### Readable Pillar

**Verification:**
- [ ] All functions have type hints
- [ ] All public functions have docstrings
- [ ] Variable names follow naming conventions
- [ ] No ruff lint errors

**Command:**
```bash
ruff check src/ tests/
mypy src/
```

### Unified Pillar

**Verification:**
- [ ] Code formatted with black
- [ ] Imports sorted with isort
- [ ] Consistent error response format
- [ ] Consistent API naming conventions

**Command:**
```bash
black --check src/ tests/
isort --check-only src/ tests/
```

### Secured Pillar

**Verification:**
- [ ] All endpoints require authentication
- [ ] API keys not exposed in list responses
- [ ] Input validation on all endpoints
- [ ] Project access validated per request
- [ ] No hardcoded secrets

**Manual Check:**
- Review authentication middleware
- Test with invalid authentication
- Check API key exposure in responses

### Trackable Pillar

**Verification:**
- [ ] Conventional commit messages used
- [ ] PR references SPEC-PROJECT-001
- [ ] Changes tracked in git history
- [ ] Audit trail for project changes

**Command:**
```bash
git log --oneline --grep="SPEC-PROJECT-001"
```

---

## Performance Testing

### Response Time Targets

| Endpoint | P50 Target | P95 Target | P99 Target |
|----------|-----------|-----------|-----------|
| POST /projects | < 50ms | < 100ms | < 200ms |
| GET /projects | < 30ms | < 50ms | < 100ms |
| PUT /projects/{id} | < 50ms | < 100ms | < 200ms |
| DELETE /projects/{id} | < 50ms | < 100ms | < 200ms |
| POST /projects/{id}/messages | < 30ms | < 50ms | < 100ms |
| GET /projects/{id}/messages | < 50ms | < 100ms | < 200ms |

**Verification Method:**
- Load test with locust or pytest-benchmark
- Measure P50, P95, P99 latencies
- Verify targets are met

### WebSocket Performance

| Metric | Target |
|--------|--------|
| Message delivery latency | < 500ms (P95) |
| Concurrent connections | 50+ |
| Reconnection time | < 5 seconds |

**Verification Method:**
- WebSocket stress test
- Measure delivery latency
- Test with 50+ concurrent clients

---

## Security Testing

### Authentication Tests

- [ ] Unauthenticated requests rejected
- [ ] Invalid tokens rejected
- [ ] Expired tokens rejected
- [ ] Cross-project access denied

### Input Validation Tests

- [ ] SQL injection attempts blocked
- [ ] XSS attempts blocked
- [ ] Path traversal attempts blocked
- [ ] Malformed JSON rejected

### Authorization Tests

- [ ] Users cannot access projects they don't own
- [ ] Admin-only operations protected
- [ ] API key validation enforced

---

## User Acceptance Testing

### Test Scenarios for Manual Verification

1. **Create and manage a project:**
   - Create new project with valid data
   - Update project description
   - Delete project (verify no sessions)

2. **Assign agents to project:**
   - Assign multiple agents to project
   - Verify agent count updates
   - Unassign agent from project

3. **Send and receive messages:**
   - Open chat room for project
   - Send message
   - Verify message appears
   - Open chat room on second browser
   - Verify real-time update

4. **Test error cases:**
   - Try to create duplicate project
   - Try to delete project with active sessions
   - Try to assign non-existent agent

---

**END OF ACCEPTANCE - SPEC-PROJECT-001**
