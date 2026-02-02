# SPEC-DASHBOARD-001: Dashboard Display Issues Fix

## TAG BLOCK

```
SPEC_ID: SPEC-DASHBOARD-001
TITLE: Dashboard Display Issues Fix - Agent List and Message List
STATUS: Planned
PRIORITY: High
ASSIGNED: TBD
CREATED: 2026-02-01
RELATED: SPEC-UI-MESSAGES-001
DOMAIN: Frontend, API Integration
```

## Environment

### System Context

The AI Agent Communication System provides a web dashboard for monitoring agent status, viewing message history, and managing agents. The dashboard is a single-page application built with vanilla JavaScript that communicates with a FastAPI backend.

### Current State

- **Backend**: FastAPI endpoints return agent data with specific field names
- **Frontend**: Vanilla JavaScript dashboard expects different field names
- **Integration**: Field name mismatches causing display failures

### Problem Description

Field name mismatches between backend API responses and frontend expectations cause the following issues:

1. **Agent List Display Failure** (`dashboard.js:382`):
   - API returns: `agent_id`, `full_id`
   - Frontend expects: `display_id`
   - Result: Agent cards show undefined/empty values

2. **Agent Management Table Failure** (`dashboard.js:979`):
   - API returns: `agent_id`, `full_id`
   - Frontend expects: `id`, `display_id`
   - Result: Management table shows undefined/empty values

3. **Message Timeline Display Issues**:
   - Timeline rendering depends on agent IDs for proper display
   - Field name mismatches prevent proper agent identification

## Assumptions

### Technical Assumptions

- The API response model `AgentInfo` uses `agent_id` as the display identifier
- The `agent_id` field contains the formatted display ID (e.g., "@FrontendExpert-ef123456")
- The `full_id` field contains the complete UUID
- Frontend code was written expecting `display_id` before the API naming was finalized
- Confirmed: Backend API is correct; frontend needs alignment

### Business Assumptions

- Dashboard users need to see agent nicknames and display IDs for identification
- Agent management features require proper agent identification for delete operations
- Message timeline needs proper agent ID references for filtering and display

### Integration Assumptions

- No breaking changes to existing API contracts with other clients
- Frontend-only fixes are acceptable if they don't impact other consumers
- Backward compatibility should be maintained where possible

## Requirements (EARS Format)

### Ubiquitous Requirements

**UB-001**: The dashboard 시스템은 **항상** API에서 반환된 에이전트 데이터를 올바르게 표시해야 한다.

**UB-002**: The dashboard 시스템은 **항상** 에이전트 관리 테이블에서 에이전트를 식별 가능한 ID로 표시해야 한다.

**UB-003**: The dashboard 시스템은 **항상** 메시지 타임라인에서 에이전트 ID를 올바르게 표시해야 한다.

### Event-Driven Requirements

**ED-001**: **WHEN** 사용자가 대시보드를 로드할 때, **THEN** 시스템은 에이전트 목록을 올바른 필드 이름으로 표시해야 한다.

**ED-002**: **WHEN** 사용자가 에이전트 관리 탭을 열 때, **THEN** 시스템은 관리 테이블에 모든 에이전트 정보를 표시해야 한다.

**ED-003**: **WHEN** 사용자가 에이전트를 삭제할 때, **THEN** 시스템은 올바른 agent ID를 사용하여 삭제 요청을 보내야 한다.

**ED-004**: **WHEN** 시스템이 메시지 타임라인을 렌더링할 때, **THEN** 각 메시지의 발신자와 수신자 정보를 올바르게 표시해야 한다.

### State-Driven Requirements

**SD-001**: **IF** API 응답에 `agent_id` 필드가 포함되어 있으면, **THEN** 프론트엔드는 `agent_id`를 에이전트 식별자로 사용해야 한다.

**SD-002**: **IF** API 응답에 `full_id` 필드가 포함되어 있으면, **THEN** 프론트엔드는 `full_id`를 내부 UUID 참조로 사용해야 한다.

**SD-003**: **IF** 등록된 에이전트 목록이 비어 있으면, **THEN** 시스템은 빈 상태 메시지를 표시해야 한다.

### Unwanted Behavior Requirements

**UBW-001**: The dashboard 시스템은 에이전트 카드에 "undefined" 또는 "null"을 **표시하지 않아야 한다**.

**UBW-002**: The dashboard 시스템은 에이전트 관리 테이블에 빈 식별자를 **표시하지 않아야 한다**.

**UBW-003**: The dashboard 시스템은 메시지 타임라인에 알 수 없는 발신자 정보를 **표시하지 않아야 한다**.

### Optional Requirements

**OP-001**: **가능하면** 시스템은 에이전트 ID 형식을 검증하는 사용자 친화적인 오류 메시지를 제공해야 한다.

**OP-002**: **가능하면** 시스템은 에이전트 상태 변경 시 실시간으로 업데이트되는 UI를 제공해야 한다.

## Specifications

### SP-001: Field Name Mapping

The frontend JavaScript code shall correctly map API response fields:

- `agent_id` → Used as the primary display identifier
- `full_id` → Used for internal references
- Remove references to non-existent `display_id` field
- Add `id` as an alias for `agent_id` where needed for management table

**Implementation Details:**

```javascript
// Before (incorrect):
const { display_id, nickname, status, capabilities, last_seen, current_meeting } = agent;

// After (correct):
const { agent_id, full_id, nickname, status, capabilities, last_seen, current_meeting } = agent;
// Use agent_id where display_id was expected
```

**Files to Modify:**
- `src/communication_server/static/js/dashboard.js`: Lines 382, 417, 420, 532, 724, 979, 986, 994, 996

### SP-002: Agent List Display

The agent list shall display agents with proper identification:

**Required Fields:**
- Display ID: `agent_id` (format: "@Nickname-XXXXXXXX")
- Nickname: Human-readable name
- Status: Current agent status
- Capabilities: List of agent capabilities
- Last Seen: Timestamp of last activity

**Display Format:**
```html
<div class="agent-card" data-agent-id="@FrontendExpert-ef123456">
    <div class="agent-display-id">@FrontendExpert-ef123456</div>
    <div class="agent-nickname">FrontendExpert</div>
    ...
</div>
```

### SP-003: Agent Management Table

The agent management table shall display all registered agents with actionable delete buttons:

**Required Fields:**
- ID: `agent_id` for data attributes and delete operations
- Nickname: Human-readable name
- Display ID: `agent_id` for display
- Status: Current agent status
- Actions: Delete button with proper agent ID

**Display Format:**
```html
<tr data-agent-id="@FrontendExpert-ef123456">
    <td><span class="status-badge">online</span></td>
    <td>FrontendExpert</td>
    <td><code>@FrontendExpert-ef123456</code></td>
    <td><button onclick="handleDeleteAgent('@FrontendExpert-ef123456', 'FrontendExpert')">Delete</button></td>
</tr>
```

### SP-004: Message Timeline Display

The message timeline shall properly display agent information for each event:

**Required Fields:**
- `from_agent`: Sender agent ID
- `to_agent`: Recipient agent ID (optional)
- `timestamp`: Event timestamp
- `event_type`: Type of event
- `description`: Event description

**Timeline Item Format:**
```javascript
{
    "timestamp": "2026-02-01T10:30:00Z",
    "from_agent": "@FrontendExpert-ef123456",
    "to_agent": "@BackendDev-ab456789",
    "event_type": "message",
    "description": "Direct message sent"
}
```

### SP-005: API Response Structure

The backend API `/status/agents` endpoint shall return the following structure:

```json
{
    "agents": [
        {
            "agent_id": "@FrontendExpert-ef123456",
            "full_id": "550e8400-e29b-41d4-a716-446655440000",
            "nickname": "FrontendExpert",
            "status": "online",
            "capabilities": ["ui-design", "frontend-dev"],
            "last_seen": "2026-02-01T10:30:00Z",
            "current_meeting": null,
            "project_id": "default"
        }
    ]
}
```

**Note:** The backend already returns this structure. No changes needed to the API.

## Traceability

| Requirement ID | Specification | Test Scenario |
|---------------|---------------|---------------|
| UB-001 | SP-001, SP-002 | TC-AV-001 |
| UB-002 | SP-003 | TC-AV-002 |
| UB-003 | SP-004 | TC-AV-003 |
| ED-001 | SP-001, SP-002 | TC-ED-001 |
| ED-002 | SP-003 | TC-ED-002 |
| ED-003 | SP-003 | TC-ED-003 |
| ED-004 | SP-004 | TC-ED-004 |
| SD-001 | SP-001 | TC-SD-001 |
| SD-002 | SP-001 | TC-SD-002 |
| SD-003 | SP-003 | TC-SD-003 |
| UBW-001 | SP-002 | TC-UBW-001 |
| UBW-002 | SP-003 | TC-UBW-002 |
| UBW-003 | SP-004 | TC-UBW-003 |

## References

- Backend API: `src/communication_server/api/status.py`
- Frontend Dashboard: `src/communication_server/static/js/dashboard.js`
- API Client: `src/communication_server/static/js/api.js`
- Messages API: `src/communication_server/api/messages.py`
- Status Models: `src/agent_comm_core/models/status.py`
