# Acceptance Criteria: SPEC-UI-MESSAGES-001

**SPEC ID:** SPEC-UI-MESSAGES-001
**Title:** Message History List View Acceptance Criteria
**Created:** 2026-02-01

---

## Overview

This document defines the acceptance criteria for message history list view using Given-When-Then format for test scenarios.

---

## Test Scenarios

### Functional Scenarios

#### Scenario 1: Display Message List

**Given** the system has at least one message
**When** the dashboard loads
**Then** a message list section **shall** be visible
**And** the list **shall** display messages in reverse chronological order
**And** each message **shall** show sender, recipient, timestamp, and preview

---

#### Scenario 2: Empty Message List

**Given** the system has no messages
**When** the dashboard loads
**Then** the message list **shall** display an empty state
**And** the empty state **shall** show a helpful icon and message

---

#### Scenario 3: Click Message to View Details

**Given** the message list is displaying messages
**When** the user clicks on a message item
**Then** a modal **shall** open showing full message details
**And** the modal **shall** include sender, recipient, full content, timestamp, and metadata

---

#### Scenario 4: Close Message Detail Modal

**Given** a message detail modal is open
**When** the user clicks the close button (X)
**Or** the user clicks the modal overlay
**Then** the modal **shall** close
**And** the user **shall** return to the message list

---

#### Scenario 5: Filter Messages by Project

**Given** the message list is showing messages from all projects
**And** a project filter dropdown is available
**When** the user selects "Project A" from the filter
**Then** the list **shall** display only messages involving Project A agents
**And** messages from other projects **shall** be hidden

---

#### Scenario 6: Show All Messages

**Given** the user has filtered messages by "Project A"
**When** the user selects "All Projects" from the filter
**Then** the list **shall** display messages from all projects
**And** the filter dropdown **shall** show "All Projects" as selected

---

#### Scenario 7: Load More Messages on Scroll

**Given** 50 messages are currently displayed
**And** more messages exist in history
**When** the user scrolls to the bottom of the message list
**Then** the system **shall** load and display the next 50 messages
**And** a loading indicator **shall** appear during loading

---

#### Scenario 8: No More Messages to Load

**Given** the user has scrolled through all available messages
**When** the user reaches the bottom of the list
**Then** no loading indicator **shall** appear
**And** no more messages **shall** load

---

#### Scenario 9: Refresh Message List

**Given** the message list is currently displayed
**When** the user clicks the refresh button
**Then** the list **shall** reload with the latest messages
**And** new messages **shall** appear at the top if available

---

#### Scenario 10: Real-time New Message

**Given** the user is viewing the message list
**When** a new message is sent between agents
**Then** the new message **shall** appear at the top of the list
**And** the list **shall** not scroll automatically (unless already at top)

---

### Message Display Scenarios

#### Scenario 11: Direct Message Display

**Given** a message has from_agent="@AgentA" and to_agent="@AgentB"
**When** the message renders in the list
**Then** the message **shall** show "@AgentA → @AgentB"
**And** the message type **shall** be "direct"

---

#### Scenario 12: Broadcast Message Display

**Given** a message has from_agent="@AgentA" and to_agent=null (broadcast)
**When** the message renders in the list
**Then** the message **shall** show "@AgentA → All"
**And** the message type **shall** be "broadcast"
**And** a broadcast icon **shall** be shown instead of arrow

---

#### Scenario 13: Long Content Preview

**Given** a message has content longer than 100 characters
**When** the message renders in the list
**Then** only the first 100 characters **shall** be displayed
**And** ellipsis (...) **shall** be appended to the preview
**And** the full content **shall** be visible in detail modal

---

#### Scenario 14: Timestamp Formatting

**Given** a message was sent 2 minutes ago
**When** the message renders in the list
**Then** the timestamp **shall** display as "2m ago"
**And** in the detail modal, the full timestamp **shall** be shown

---

#### Scenario 15: Project Badge Display

**Given** a message is associated with "Project A"
**When** the message renders in the list
**Then** a "Project A" badge **shall** be visible
**And** clicking the badge **shall** filter to that project (optional enhancement)

---

### API Scenarios

#### Scenario 16: List Messages API

**Given** the system has messages
**When** a client sends `GET /api/v1/messages?limit=50&offset=0`
**Then** the response **shall** have status 200
**And** the response **shall** contain a "messages" array
**And** each message **shall** include message_id, from_agent, to_agent, timestamp, content_preview

---

#### Scenario 17: Filter Messages by Project

**Given** the system has messages from multiple projects
**When** a client sends `GET /api/v1/messages?project_id=project-a`
**Then** the response **shall** contain only messages with project_id="project-a"
**And** messages from other projects **shall** be excluded

---

#### Scenario 18: Get Message Detail

**Given** a message exists with ID "msg-123"
**When** a client sends `GET /api/v1/messages/msg-123`
**Then** the response **shall** have status 200
**And** the response **shall** include the full message content
**And** the response **shall** include message metadata

---

#### Scenario 19: Search Messages

**Given** the system has messages with various content
**When** a client sends `GET /api/v1/messages?search=API`
**Then** the response **shall** include only messages containing "API" in content
**And** the search **shall** be case-insensitive

---

#### Scenario 20: Pagination Limits

**Given** the system has 200 messages
**When** a client sends `GET /api/v1/messages?limit=50&offset=0`
**Then** the response **shall** return exactly 50 messages
**And** the "has_more" flag **shall** be true
**When** the client sends `GET /api/v1/messages?limit=50&offset=150`
**Then** the response **shall** return the remaining 50 messages
**And** the "has_more" flag **shall** be false

---

### UI/UX Scenarios

#### Scenario 21: Message Item Hover Effect

**Given** the user is viewing the message list
**When** the user hovers over a message item
**Then** the item **shall** display a hover background
**And** the cursor **shall** change to pointer

---

#### Scenario 22: Message Detail Modal Animation

**Given** the user clicks on a message
**When** the modal opens
**Then** the modal **shall** fade in smoothly
**And** the modal content **shall** scale in from center

---

#### Scenario 23: Modal Content Overflow

**Given** a message has very long content (e.g., 2000 characters)
**When** the modal displays the message
**Then** the modal body **shall** be scrollable
**And** the modal **shall** not exceed 80% of viewport height
**And** content **shall** wrap or scroll horizontally if needed

---

#### Scenario 24: JSON Content Formatting

**Given** a message has JSON content with content_type="application/json"
**When** the modal displays the message
**Then** the content **shall** be displayed with monospace font
**And** the content **shall** be pretty-formatted if valid JSON
**And** line breaks **shall** be preserved

---

#### Scenario 25: Keyboard Navigation

**Given** the user is viewing the message list
**When** the user presses Escape key with modal open
**Then** the modal **shall** close
**When** the user uses arrow keys on message list
**Then** the selection **shall** move up/down through messages (optional)

---

### Edge Cases

#### Scenario 26: Message with Missing Sender

**Given** a message has from_agent_id for a deleted agent
**When** the message renders
**Then** the sender **shall** display the raw agent ID
**Or** display "Unknown Agent" instead of display name

---

#### Scenario 27: Malformed Content in Preview

**Given** a message contains HTML or special characters
**When** the message renders in the list
**Then** the content **shall** be HTML-escaped
**And** no HTML **shall** be rendered

---

#### Scenario 28: Rapid Project Filter Changes

**Given** the user is viewing messages
**When** the user rapidly switches between project filters
**Then** only the last selected filter **shall** be applied
**And** no duplicate requests **shall** be sent

---

#### Scenario 29: Very Long Message List

**Given** the system has 10,000 messages
**When** the user loads the message list
**Then** initially only 50 messages **shall** load
**And** the UI **shall** remain responsive
**And** memory usage **shall** not exceed reasonable limits

---

#### Scenario 30: Network Error Loading Messages

**Given** the messages API is unreachable
**When** the dashboard attempts to load messages
**Then** an error state **shall** display
**And** a retry button **shall** be available
**And** the error **shall** be logged to console

---

## Quality Gate Criteria

### Code Quality

- [ ] Message component follows existing dashboard patterns
- [ ] Message item HTML uses semantic structure
- [ ] CSS follows existing styling conventions
- [ ] No inline styles in JavaScript

### Test Coverage

- [ ] Unit tests for MessagesList class (>80% coverage)
- [ ] Integration tests for message API endpoints
- [ ] E2E tests for message interaction
- [ ] Visual regression tests for modal states

### Accessibility

- [ ] Message items are keyboard navigable
- [ ] Modal has proper ARIA attributes
- [ ] Modal focus trap is implemented
- [ ] Close button is accessible

### Performance

- [ ] Message list render time < 100ms for 50 items
- [ ] Modal open latency < 50ms
- [ ] Infinite scroll loads without blocking UI
- [ ] No memory leaks from message updates

---

## Definition of Done

**SPEC-UI-MESSAGES-001 is complete when:**

1. Backend `/api/v1/messages` endpoints are implemented
2. Message detail endpoint returns full message content
3. Message list is visible and styled on dashboard
4. Messages display in reverse chronological order
5. Clicking message opens detail modal
6. Modal shows full message content
7. Project filter works correctly
8. Infinite scroll or pagination is functional
9. All acceptance criteria scenarios pass
10. Test coverage exceeds 80% for messages code
11. No regression in existing dashboard functionality

---

## Test Execution Plan

### Unit Tests

```bash
# Run message list unit tests
pytest tests/unit/test_messages.py -v
pytest tests/unit/test_message_api.py -v
```

### Integration Tests

```bash
# Run message integration tests
pytest tests/integration/test_message_history.py -v
```

### E2E Tests

```bash
# Run E2E tests with Playwright
pytest tests/e2e/test_message_list.py -v
```

### Manual Testing Checklist

- [ ] Verify message list displays on load
- [ ] Click message and verify modal opens
- [ ] Close modal using button and overlay
- [ ] Test project filter dropdown
- [ ] Scroll to bottom to load more
- [ ] Verify new messages appear via WebSocket
- [ ] Test with various message content types
- [ ] Verify timestamp formatting

---

**END OF ACCEPTANCE CRITERIA - SPEC-UI-MESSAGES-001**
