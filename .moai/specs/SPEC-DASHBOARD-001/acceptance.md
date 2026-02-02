# Acceptance Criteria: SPEC-DASHBOARD-001

## TAG BLOCK

```
SPEC_ID: SPEC-DASHBOARD-001
VERSION: 1.0
LAST_UPDATED: 2026-02-01
STATUS: Planned
```

## Overview

This document defines the acceptance criteria for fixing dashboard display issues related to field name mismatches between the backend API and frontend JavaScript code.

## Test Scenarios

### TC-ED-001: Dashboard Load - Agent List Display

**Given**: The dashboard page is loaded
**When**: The page finishes loading
**Then**: All registered agents are displayed in the agent grid

**Test Steps**:
1. Navigate to the dashboard URL
2. Wait for page to fully load
3. Observe the agent grid section

**Expected Results**:
- Agent grid displays all registered agents
- Each agent card shows:
  - Display ID (e.g., "@FrontendExpert-ef123456")
  - Nickname (e.g., "FrontendExpert")
  - Status badge (online/offline/active/idle/error)
  - Capabilities tags
  - Last seen timestamp
- No "undefined" or "null" values are visible
- Empty state message is shown if no agents are registered

**Test Data**:
```json
{
    "agents": [
        {
            "agent_id": "@FrontendExpert-ef123456",
            "full_id": "550e8400-e29b-41d4-a716-446655440000",
            "nickname": "FrontendExpert",
            "status": "online",
            "capabilities": ["ui-design", "frontend-dev"],
            "last_seen": "2026-02-01T10:30:00Z"
        }
    ]
}
```

---

### TC-ED-002: Agent Management Table Display

**Given**: The user opens the Agent Management tab
**When**: The tab content loads
**Then**: All registered agents are displayed in the management table

**Test Steps**:
1. Navigate to the dashboard
2. Click on the Agent Management tab
3. Observe the agent management table

**Expected Results**:
- Management table displays all registered agents
- Each row shows:
  - Status badge with proper color coding
  - Nickname
  - Display ID in code format
  - Delete button
- No "undefined" or "null" values are visible
- Empty state message is shown if no agents are registered

**Test Data**:
```json
{
    "agents": [
        {
            "agent_id": "@FrontendExpert-ef123456",
            "nickname": "FrontendExpert",
            "status": "online"
        }
    ]
}
```

---

### TC-ED-003: Agent Delete Operation

**Given**: The agent management table is displayed with at least one agent
**When**: The user clicks the delete button for an agent
**Then**: The agent is deleted using the correct agent ID

**Test Steps**:
1. Navigate to the dashboard
2. Open the Agent Management tab
3. Click the delete button for an agent
4. Confirm the deletion in the dialog
5. Observe the table updates

**Expected Results**:
- Delete confirmation dialog shows the correct agent nickname
- Delete API call is made with the correct `agent_id` (e.g., "@FrontendExpert-ef123456")
- Agent is removed from the table
- Success message is displayed
- Agent is also removed from the agent grid

**Test API Call**:
```
DELETE /api/v1/status/agents/@FrontendExpert-ef123456
```

---

### TC-ED-004: Message Timeline Display

**Given**: The dashboard page is loaded
**When**: The message timeline section renders
**Then**: Message events are displayed with proper agent information

**Test Steps**:
1. Navigate to the dashboard
2. Scroll to the timeline section
3. Observe the timeline items

**Expected Results**:
- Timeline displays recent message events
- Each timeline item shows:
  - Timestamp in readable format
  - Sender agent ID (e.g., "@FrontendExpert-ef123456")
  - Recipient agent ID (if applicable)
  - Event type (message, meeting, decision)
  - Event description
- No "undefined" or "null" values are visible
- Empty state message is shown if no events exist

**Test Data**:
```json
{
    "timestamp": "2026-02-01T10:30:00Z",
    "from_agent": "@FrontendExpert-ef123456",
    "to_agent": "@BackendDev-ab456789",
    "event_type": "message",
    "description": "Direct message sent"
}
```

---

### TC-SD-001: Field Name Mapping - agent_id

**Given**: The API returns agent data with `agent_id` field
**When**: The frontend processes the agent data
**Then**: The `agent_id` field is used as the primary display identifier

**Test Steps**:
1. Inspect the API response in browser DevTools
2. Verify `agent_id` field exists in response
3. Inspect the rendered HTML elements
4. Verify `agent_id` value is used in `data-agent-id` attributes

**Expected Results**:
- API response includes `"agent_id": "@FrontendExpert-ef123456"`
- HTML elements have `data-agent-id="@FrontendExpert-ef123456"`
- Display text shows the agent_id value

---

### TC-SD-002: Field Name Mapping - full_id

**Given**: The API returns agent data with `full_id` field
**When**: The frontend processes the agent data
**Then**: The `full_id` field is used for internal references

**Test Steps**:
1. Inspect the API response in browser DevTools
2. Verify `full_id` field exists in response
3. Verify `full_id` is not displayed in the UI (used internally)

**Expected Results**:
- API response includes `"full_id": "550e8400-e29b-41d4-a716-446655440000"`
- `full_id` is available for internal operations
- `full_id` is not confused with display IDs

---

### TC-SD-003: Empty Agent List State

**Given**: No agents are registered in the system
**When**: The dashboard loads
**Then**: Appropriate empty state messages are displayed

**Test Steps**:
1. Ensure no agents are registered
2. Navigate to the dashboard
3. Observe the agent grid and management table

**Expected Results**:
- Agent grid shows empty state message with icon
- Management table shows empty state row with icon
- No JavaScript errors in console
- UI remains functional for registering new agents

---

### TC-UBW-001: No Undefined Values in Agent Cards

**Given**: The dashboard is loaded with agents
**When**: Agent cards are rendered
**Then**: No "undefined" or "null" values appear in any agent card

**Test Steps**:
1. Load the dashboard with multiple agents
2. Visually inspect each agent card
3. Check browser console for errors

**Expected Results**:
- All agent cards show valid data for all fields
- No "undefined" text visible anywhere
- No "null" text visible anywhere
- No console errors related to undefined properties

---

### TC-UBW-002: No Undefined Values in Management Table

**Given**: The agent management table is displayed
**When**: Table rows are rendered
**Then**: No "undefined" or "null" values appear in any table row

**Test Steps**:
1. Navigate to the dashboard
2. Open the Agent Management tab
3. Visually inspect each table row
4. Check browser console for errors

**Expected Results**:
- All table rows show valid data for all columns
- No "undefined" text visible anywhere
- No "null" text visible anywhere
- Delete buttons are enabled and functional

---

### TC-UBW-003: No Unknown Agent References in Timeline

**Given**: The message timeline is displayed
**When**: Timeline items are rendered
**Then**: All agent references show valid agent IDs

**Test Steps**:
1. Load the dashboard
2. Scroll to the timeline section
3. Inspect each timeline item
4. Check browser console for errors

**Expected Results**:
- All timeline items show valid sender/recipient IDs
- No "unknown" or "undefined" agent references
- Timeline items are properly formatted

---

### TC-AV-001: Agent List Visual Verification

**Given**: Multiple agents with different statuses are registered
**When**: The dashboard loads
**Then**: Each agent card displays with correct visual styling

**Test Steps**:
1. Register agents with different statuses (online, offline, active, idle, error)
2. Load the dashboard
3. Verify each agent card's visual appearance

**Expected Results**:
- Status badges have correct colors:
  - Online: Green
  - Active: Blue
  - Idle: Yellow
  - Offline: Gray
  - Error: Red
- Capability tags are properly styled
- Agent cards have consistent layout
- Last seen timestamps are formatted correctly

---

### TC-AV-002: Management Table Visual Verification

**Given**: Multiple agents are registered
**When**: The Agent Management tab is opened
**Then**: The table displays with proper formatting

**Test Steps**:
1. Register multiple agents
2. Open the Agent Management tab
3. Verify table appearance and formatting

**Expected Results**:
- Status badges have correct colors
- Nicknames are properly aligned
- Display IDs are shown in code format (monospace font)
- Delete buttons are properly aligned
- Table has proper spacing and borders

---

### TC-AV-003: Timeline Visual Verification

**Given**: Various message events exist in the system
**When**: The timeline is rendered
**Then**: Each timeline item is properly formatted

**Test Steps**:
1. Create various message events (direct, broadcast, meeting)
2. Load the dashboard
3. Scroll to the timeline section
4. Verify timeline item formatting

**Expected Results**:
- Timestamps are formatted as HH:MM:SS
- Agent IDs are clearly visible
- Event types have appropriate icons or badges
- Timeline has proper vertical spacing
- Items are in reverse chronological order (newest first)

---

## Quality Gates

### TRUST 5 Compliance

**Tested**:
- [ ] All manual test scenarios pass
- [ ] No JavaScript console errors
- [ ] All agent operations work correctly

**Readable**:
- [ ] Code follows project naming conventions
- [ ] Variable names clearly indicate their purpose
- [ ] Comments explain complex logic

**Unified**:
- [ ] Code style matches existing dashboard.js
- [ ] Consistent indentation and formatting
- [ ] No unnecessary code duplication

**Secured**:
- [ ] Agent IDs are properly escaped in HTML (prevent XSS)
- [ ] Delete operations require user confirmation
- [ ] No sensitive data exposed in console logs

**Trackable**:
- [ ] Changes follow conventional commit format
- [ ] SPEC reference included in commit message
- [ ] Test scenarios documented for future reference

### Browser Compatibility

**Tested Browsers**:
- [ ] Chrome/Edge (latest)
- [ ] Firefox (latest)
- [ ] Safari (latest)

**Compatibility Notes**:
- Vanilla JavaScript - no framework dependencies
- Uses standard DOM APIs
- No IE11 support required

### Performance Criteria

**Load Time**:
- Dashboard initial load: < 3 seconds
- Agent list rendering: < 500ms
- Management table rendering: < 500ms
- Timeline rendering: < 500ms

**Memory**:
- No memory leaks on page reload
- Proper cleanup of event listeners

## Definition of Done

The implementation is considered complete when:

1. **Functional Requirements**:
   - [ ] All agent cards display correctly with proper IDs
   - [ ] Agent management table displays correctly
   - [ ] Delete operations work with correct agent IDs
   - [ ] Message timeline displays correctly

2. **Quality Requirements**:
   - [ ] Zero console errors on page load
   - [ ] No undefined values in any display
   - [ ] All TRUST 5 principles met
   - [ ] Code follows project conventions

3. **Testing Requirements**:
   - [ ] All test scenarios pass
   - [ ] Manual testing completed
   - [ ] Cross-browser compatibility verified

4. **Documentation Requirements**:
   - [ ] Changes documented in code comments
   - [ ] SPEC reference in commit message
   - [ ] Acceptance criteria updated if needed

## References

- Main SPEC: `.moai/specs/SPEC-DASHBOARD-001/spec.md`
- Implementation Plan: `.moai/specs/SPEC-DASHBOARD-001/plan.md`
- Project Constitution: `.moai/project/tech.md`
