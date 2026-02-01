# Acceptance Criteria: SPEC-AGENT-COMM-001

## TAG BLOCK

```yaml
SPEC_ID: SPEC-AGENT-COMM-001
RELATED_SPEC: .moai/specs/SPEC-AGENT-COMM-001/spec.md
STATUS: Planned
PHASE: Plan
TRACEABILITY:
  - SPEC: .moai/specs/SPEC-AGENT-COMM-001/spec.md
  - PLAN: .moai/specs/SPEC-AGENT-COMM-001/plan.md
```

---

## Overview

This document defines detailed acceptance criteria for the AI Agent Communication & Meeting System using the Given-When-Then format for Behavior-Driven Development (BDD) and TRUST 5 quality validation.

---

## Component 1: Communication Logging

### AC-COMM-001: Log Communication Between Agents

**GIVEN** a running system with database connection
**WHEN** a POST request is made to /api/v1/communications with sender_id, receiver_id, and message_content
**THEN** the system SHALL store the communication in the communications table
**AND** return a 201 response with the communication record including ID and timestamp

**Example**:
```gherkin
Given system is running
And database connection is active
When POST request to /api/v1/communications:
  """
  {
    "sender_id": "550e8400-e29b-41d4-a716-446655440000",
    "receiver_id": "660e8400-e29b-41d4-a716-446655440001",
    "message_content": "Hello, Agent B!",
    "topic": "greeting"
  }
  """
Then response status is 201
And response contains:
  """
  {
    "id": "<uuid>",
    "timestamp": "2026-02-01T10:00:00Z",
    "sender_id": "550e8400-e29b-41d4-a716-446655440000",
    "receiver_id": "660e8400-e29b-41d4-a716-446655440001",
    "message_content": "Hello, Agent B!",
    "topic": "greeting"
  }
  """
And communication is stored in database
```

### AC-COMM-002: Query Communications with Filters

**GIVEN** multiple communications are stored with various senders, receivers, topics, and timestamps
**WHEN** a GET request is made to /api/v1/communications with query parameters
**THEN** the system SHALL return filtered results with pagination

**Scenarios**:
```gherkin
Scenario: Filter by sender
Given 10 communications from agent A
And 5 communications from agent B
When GET /api/v1/communications?sender_id=<agent-a-id>
Then returns 10 communications from agent A
And total count is 10

Scenario: Filter by date range
Given communications on 2026-02-01 and 2026-02-02
When GET /api/v1/communications?start_date=2026-02-01T00:00:00Z&end_date=2026-02-01T23:59:59Z
Then returns only communications from 2026-02-01

Scenario: Filter by topic
Given 7 communications with topic "coordination"
And 3 communications with topic "status"
When GET /api/v1/communications?topic=coordination
Then returns 7 communications with topic "coordination"

Scenario: Pagination
Given 100 communications stored
When GET /api/v1/communications?page=1&page_size=50
Then returns first 50 communications
And total is 100
And page is 1
And page_size is 50
```

### AC-COMM-003: Reject Oversized Messages

**GIVEN** a running system with max message size of 10MB
**WHEN** a POST request is made with message_content exceeding 10MB
**THEN** the system SHALL reject the request with 413 status
**AND** error message SHALL indicate size limit

**Example**:
```gherkin
Given system max message size is 10MB
When POST request with message_content of 11MB
Then response status is 413
And response contains:
  """
  {
    "error": "message_too_large",
    "max_size_mb": 10,
    "actual_size_mb": 11
  }
  """
```

---

## Component 2: Meeting Management

### AC-MEET-001: Create Meeting

**GIVEN** a running system
**WHEN** a POST request is made to /api/v1/meetings with topic, meeting_type, and participant_ids
**THEN** the system SHALL create a meeting with status "pending"
**AND** return 201 with meeting record

**Example**:
```gherkin
Given system is running
When POST request to /api/v1/meetings:
  """
  {
    "topic": "Coordinate task distribution",
    "meeting_type": "user_specified",
    "participant_ids": [
      "550e8400-e29b-41d4-a716-446655440000",
      "660e8400-e29b-41d4-a716-446655440001",
      "770e8400-e29b-41d4-a716-446655440002"
    ],
    "max_discussion_rounds": 3
  }
  """
Then response status is 201
And response contains:
  """
  {
    "id": "<uuid>",
    "topic": "Coordinate task distribution",
    "meeting_type": "user_specified",
    "status": "pending",
    "created_at": "2026-02-01T10:00:00Z",
    "participant_ids": [...]
  }
  """
```

### AC-MEET-002: Join Meeting via WebSocket

**GIVEN** a meeting exists with ID
**WHEN** an agent connects via WebSocket to ws://localhost:8000/ws/meetings/{meeting_id}?agent_id={agent_id}
**THEN** the system SHALL add the agent to meeting_participants
**AND** establish WebSocket connection
**AND** broadcast agent_joined event to other participants

**Example**:
```gherkin
Given meeting "meeting-123" exists
And meeting has participants A and B
When agent C connects to ws://localhost:8000/ws/meetings/meeting-123?agent_id=agent-c-id
Then agent C is added to meeting_participants
And agent C receives: {"type": "connected", "meeting_id": "meeting-123"}
And agents A and B receive:
  """
  {
    "type": "meeting_event",
    "event": "agent_joined",
    "meeting_id": "meeting-123",
    "data": {"agent_id": "agent-c-id"}
  }
  """
```

### AC-MEET-003: Get Meeting Details

**GIVEN** a meeting exists with participants, messages, and decision
**WHEN** a GET request is made to /api/v1/meetings/{meeting_id}
**THEN** the system SHALL return complete meeting details

**Example**:
```gherkin
Given meeting "meeting-123" exists with:
  - 3 participants
  - 5 meeting messages
  - 1 decision
When GET /api/v1/meetings/meeting-123
Then response status is 200
And response contains:
  """
  {
    "id": "meeting-123",
    "topic": "...",
    "status": "completed",
    "participants": [...],
    "messages": [...],
    "decision": {
      "decision_content": "...",
      "rationale": "...",
      "created_at": "2026-02-01T10:20:00Z"
    }
  }
  """
```

---

## Component 3: Sequential Discussion Algorithm

### AC-DISCUSS-001: Start Sequential Discussion

**GIVEN** a meeting exists with status "pending"
**AND** 3 participants are joined via WebSocket
**WHEN** the discussion is started
**THEN** the system SHALL set meeting status to "in_progress"
**AND** determine speaking order (randomized or fixed)
**AND** send opinion_request to first participant via WebSocket

**Example**:
```gherkin
Given meeting "meeting-123" has status "pending"
And participants A, B, C are connected via WebSocket
When discussion is started
Then meeting status is "in_progress"
And speaking_order is [A, B, C]
And participant A receives via WebSocket:
  """
  {
    "type": "opinion_request",
    "meeting_id": "meeting-123",
    "round": 1,
    "topic": "Coordinate task distribution"
  }
  """
```

### AC-DISCUSS-002: Collect Opinions Sequentially

**GIVEN** a discussion is in progress
**AND** participant A has provided opinion
**WHEN** participant A's opinion is received
**THEN** the system SHALL record the opinion in meeting_messages
**AND** send opinion_request to next participant (B)

**Example**:
```gherkin
Given discussion round 1 is in progress
And participant A received opinion_request
When participant A sends via WebSocket:
  """
  {
    "type": "opinion",
    "meeting_id": "meeting-123",
    "content": "I believe Agent A should handle task 1"
  }
  """
Then opinion is recorded in meeting_messages with sequence_number=1
And participant B receives opinion_request
And participant A waits for next round
```

### AC-DISCUSS-003: Handle Participant Timeout

**GIVEN** a participant has received opinion_request
**WHEN** the participant does not respond within timeout (5 minutes)
**THEN** the system SHALL record a "no_response" entry
**AND** proceed to next participant

**Example**:
```gherkin
Given participant B received opinion_request at T0
And no response received after 5 minutes
When timeout occurs
Then system records in meeting_messages:
  """
  {
    "agent_id": "participant-b-id",
    "content": "[No response - timeout]",
    "sequence_number": 2,
    "message_type": "opinion"
  }
  """
And participant C receives opinion_request
```

### AC-DISCUSS-004: Consensus Phase

**GIVEN** all participants have provided opinions in round 1
**WHEN** all opinions are collected
**THEN** the system SHALL enter consensus phase
**AND** broadcast all opinions to all participants
**AND** request consensus vote from each participant

**Example**:
```gherkin
Given all 3 participants provided opinions:
  - A: "Agent A should do task 1"
  - B: "Agent B should do task 1"
  - C: "I agree with A"
When opinions are collected
Then all participants receive via WebSocket:
  """
  {
    "type": "consensus_request",
    "meeting_id": "meeting-123",
    "opinions": [
      {"agent_id": "A", "content": "Agent A should do task 1"},
      {"agent_id": "B", "content": "Agent B should do task 1"},
      {"agent_id": "C", "content": "I agree with A"}
    ]
  }
  """
And each participant sends consensus_vote
```

### AC-DISCUSS-005: Consensus Reached

**GIVEN** all participants voted on consensus
**WHEN** all participants agree (agrees=true)
**THEN** the system SHALL record decision in decisions table
**AND** set meeting status to "completed"
**AND** broadcast consensus_reached event

**Example**:
```gherkin
Given consensus phase is in progress
When all 3 participants send: {"type": "consensus_vote", "agrees": true}
Then decision is recorded:
  """
  {
    "decision_content": "Agent A will handle task 1",
    "rationale": "Unanimous agreement after discussion",
    "participant_agreement": {"A": true, "B": true, "C": true}
  }
  """
And meeting status is "completed"
And all participants receive:
  """
  {
    "type": "meeting_event",
    "event": "consensus_reached",
    "meeting_id": "meeting-123",
    "data": {"decision_id": "..."}
  }
  """
```

### AC-DISCUSS-006: No Consensus After Max Rounds

**GIVEN** consensus was not reached in previous rounds
**AND** current round is equal to max_rounds
**WHEN** consensus phase completes without agreement
**THEN** the system SHALL set meeting status to "completed" with outcome "no_consensus"
**AND** record discussion summary

**Example**:
```gherkin
Given max_discussion_rounds is 3
And current_round is 3
And consensus was not reached in rounds 1 and 2
When consensus phase completes with agreements: [true, false, true]
Then meeting status is "completed"
And no decision is recorded
And meeting outcome is recorded as "no_consensus"
```

---

## Component 4: Topic Analysis

### AC-TOPIC-001: User-Specified Topic

**GIVEN** a user wants to create a meeting
**WHEN** POST to /api/v1/meetings with explicit topic
**THEN** the system SHALL create meeting with the exact topic provided

**Example**:
```gherkin
Given user wants to create meeting
When POST to /api/v1/meetings:
  """
  {
    "topic": "Resolve conflict on API design",
    "meeting_type": "user_specified",
    ...
  }
  """
Then meeting is created with topic "Resolve conflict on API design"
And topic is not modified or analyzed
```

### AC-TOPIC-002: Auto-Generate Topics from Logs

**GIVEN** recent communication logs exist
**WHEN** topic analysis is requested
**THEN** the system SHALL analyze logs for patterns
**AND** suggest ranked topics

**Example**:
```gherkin
Given communications from last 24 hours contain:
  - 5 messages about "database schema disagreement"
  - 3 messages about "API endpoint naming"
  - 2 messages about "deployment schedule"
When GET /api/v1/meetings/suggest-topics
Then returns:
  """
  {
    "suggested_topics": [
      {
        "topic": "Resolve database schema disagreement",
        "priority": 0.9,
        "reason": "High frequency of conflicting messages",
        "related_communications": ["comm-1", "comm-2", ...]
      },
      {
        "topic": "Decide on API endpoint naming convention",
        "priority": 0.6,
        "reason": "Multiple agents discussing without conclusion",
        "related_communications": ["comm-3", "comm-4", ...]
      }
    ]
  }
  """
```

### AC-TOPIC-003: Create Meeting with Auto-Generated Topic

**GIVEN** suggested topics are available
**WHEN** user selects a suggested topic and creates meeting
**THEN** the system SHALL create meeting with selected topic
**AND** link related communications to meeting

**Example**:
```gherkin
Given suggested topics include "Resolve database schema disagreement"
When user creates meeting with:
  """
  {
    "topic": "Resolve database schema disagreement",
    "meeting_type": "auto_generated",
    "related_communication_ids": ["comm-1", "comm-2", "comm-3"]
  }
  """
Then meeting is created
And related communications are linked to meeting
```

---

## Component 5: Decision Tracking

### AC-DECISION-001: Record Decision

**GIVEN** a meeting reaches consensus
**WHEN** decision is recorded
**THEN** the system SHALL store decision with meeting_id, content, rationale, and participant agreement
**AND** link to related communications

**Example**:
```gherkin
Given meeting "meeting-123" reached consensus
When decision is recorded
Then decision table contains:
  """
  {
    "id": "<uuid>",
    "meeting_id": "meeting-123",
    "decision_content": "Agent A will handle task 1",
    "rationale": "Unanimous agreement after discussion",
    "related_communication_ids": ["comm-1", "comm-2"],
    "participant_agreement": {"A": true, "B": true, "C": true},
    "created_at": "2026-02-01T10:20:00Z"
  }
  """
```

### AC-DECISION-002: Query Decisions

**GIVEN** multiple decisions exist
**WHEN** GET /api/v1/decisions with filters
**THEN** the system SHALL return matching decisions

**Scenarios**:
```gherkin
Scenario: Filter by meeting
Given 3 decisions from different meetings
When GET /api/v1/decisions?meeting_id=meeting-123
Then returns only decision from meeting-123

Scenario: Filter by date range
Given decisions on various dates
When GET /api/v1/decisions?start_date=2026-02-01&end_date=2026-02-01
Then returns only decisions from 2026-02-01

Scenario: Include related communications
Given decision has related_communication_ids
When GET /api/v1/decisions/{decision_id}
Then response includes related communications details
```

---

## Component 6: WebSocket Communication

### AC-WS-001: Agent Connection

**GIVEN** an agent wants to connect
**WHEN** WebSocket connection is established
**THEN** the system SHALL authenticate the agent
**AND** track the connection

**Example**:
```gherkin
Given agent A wants to connect
When WebSocket connection to ws://localhost:8000/ws/meetings/meeting-123?agent_id=agent-a-id
Then connection is established
And agent is authenticated
And connection is tracked in connection manager
```

### AC-WS-002: Direct Agent-to-Agent Messaging

**GIVEN** two agents have WebSocket connections
**WHEN** agent A sends a direct message to agent B
**THEN** the system SHALL deliver message to agent B
**AND** log the communication

**Example**:
```gherkin
Given agents A and B have WebSocket connections
When agent A sends:
  """
  {
    "type": "direct_message",
    "receiver_id": "agent-b-id",
    "content": "Are you available?"
  }
  """
Then message is delivered to agent B
And communication is logged in database
And agent B receives:
  """
  {
    "type": "direct_message",
    "sender_id": "agent-a-id",
    "content": "Are you available?"
  }
  """
```

### AC-WS-003: Broadcast Meeting Events

**GIVEN** a meeting is in progress
**WHEN** a meeting event occurs (opinion, consensus, etc.)
**THEN** the system SHALL broadcast event to all connected participants

**Example**:
```gherkin
Given meeting "meeting-123" is in progress
And agents A, B, C are connected
When agent A presents opinion
Then agents B and C receive:
  """
  {
    "type": "meeting_event",
    "event": "opinion_presented",
    "meeting_id": "meeting-123",
    "data": {
      "agent_id": "agent-a-id",
      "content": "I believe..."
    }
  }
  """
And agent A does not receive their own event (optional)
```

### AC-WS-004: Handle Disconnection

**GIVEN** an agent is connected to a meeting
**WHEN** the agent's WebSocket connection drops
**THEN** the system SHALL mark agent as disconnected
**AND** continue meeting if possible
**AND** allow agent to reconnect

**Example**:
```gherkin
Given agent B is connected to meeting "meeting-123"
When agent B connection drops
Then agent B is marked as disconnected
And meeting continues with other participants
And other participants receive:
  """
  {
    "type": "meeting_event",
    "event": "agent_left",
    "meeting_id": "meeting-123",
    "data": {"agent_id": "agent-b-id"}
  }
  """
When agent B reconnects
Then agent B can resume participation
```

---

## Component 7: Quality and Performance

### AC-PERF-001: API Response Time

**GIVEN** system is under normal load
**WHEN** API requests are made
**THEN** response time SHALL be under 200ms for database queries

**Measurement**:
```gherkin
Given system is running
And 10 communications exist
When POST /api/v1/communications is called 100 times
Then P50 response time < 100ms
And P95 response time < 200ms
And P99 response time < 500ms
```

### AC-PERF-002: Concurrent WebSocket Connections

**GIVEN** system is running
**WHEN** 20 agents connect via WebSocket simultaneously
**THEN** all connections SHALL be established successfully
**AND** system SHALL handle message routing correctly

**Load Test**:
```gherkin
Given system is running
When 20 WebSocket connections are established simultaneously
And each connection sends 10 messages
Then all 20 connections remain active
And all 200 messages are delivered correctly
And no errors occur
```

### AC-PERF-003: Database Connection Pool

**GIVEN** system is configured with connection pool size 10
**WHEN** concurrent requests exceed pool size
**THEN** system SHALL queue requests
**AND** not drop connections

**Example**:
```gherkin
Given connection pool size is 10
When 15 concurrent database requests are made
Then first 10 requests acquire connections
And remaining 5 requests wait in queue
And all 15 requests complete successfully
```

---

## Component 8: Security

### AC-SEC-001: API Authentication

**GIVEN** API endpoints require authentication
**WHEN** request is made without valid credentials
**THEN** system SHALL return 401 Unauthorized

**Example**:
```gherkin
Given POST /api/v1/meetings requires authentication
When request is made without Authorization header
Then response status is 401
And response contains:
  """
  {
    "error": "authentication_required"
  }
  """
```

### AC-SEC-002: Input Validation

**GIVEN** API endpoint receives input
**WHEN** input is invalid (wrong type, missing fields, etc.)
**THEN** system SHALL return 400 with validation errors

**Example**:
```gherkin
Given POST /api/v1/communications expects sender_id, receiver_id, message_content
When request is made with invalid sender_id:
  """
  {
    "sender_id": "not-a-uuid",
    "receiver_id": "<valid-uuid>",
    "message_content": "test"
  }
  """
Then response status is 400
And response contains:
  """
  {
    "error": "validation_error",
    "details": {
      "sender_id": ["Invalid UUID format"]
    }
  }
  """
```

### AC-SEC-003: SQL Injection Prevention

**GIVEN** user input is used in database queries
**WHEN** input contains SQL injection attempts
**THEN** system SHALL sanitize input
**AND** execute query safely

**Example**:
```gherkin
Given GET /api/v1/communications?topic=xyz
When topic parameter is: "'; DROP TABLE communications; --"
Then system treats input as literal string
And no SQL injection occurs
And communications table remains intact
```

---

## Component 9: Database Operations

### AC-DB-001: Transaction Consistency

**GIVEN** a meeting is being created
**WHEN** database error occurs during participant insertion
**THEN** entire transaction SHALL be rolled back
**AND** no partial data SHALL be stored

**Example**:
```gherkin
Given meeting creation is in progress
And meeting record is inserted
When participant insertion fails (e.g., duplicate key)
Then meeting record is rolled back
And no meeting record exists
And error is returned to client
```

### AC-DB-002: Database Constraints

**GIVEN** database tables have constraints
**WHEN** constraint is violated
**THEN** system SHALL return meaningful error

**Scenarios**:
```gherkin
Scenario: Duplicate meeting participant
Given meeting "meeting-123" exists
And agent A is already a participant
When agent A attempts to join again
Then error is returned: "Agent is already a participant"

Scenario: Invalid meeting status
Given meeting exists with status "completed"
When attempt to update status to "invalid_status"
Then constraint violation occurs
And error is returned
```

---

## TRUST 5 Quality Gates

### Tested

**Definition**: Unit test coverage >= 85%, integration tests for all components

**Acceptance Criteria**:
```gherkin
Given all components are implemented
When pytest is executed with coverage
Then coverage report shows >= 85% for all modules
And all integration tests pass
And load tests pass with 20+ concurrent WebSocket connections
```

### Readable

**Definition**: Clear naming, type hints, docstrings

**Acceptance Criteria**:
```gherkin
Given all source files
When code is reviewed
Then all public functions have type hints
And all classes have docstrings
And variable names are descriptive
And ruff linter shows zero warnings
```

### Unified

**Definition**: Consistent formatting, Pydantic models

**Acceptance Criteria**:
```gherkin
Given all source files
When black formatter is run
Then no formatting changes are required
And all data structures use Pydantic models
And logging is structured JSON format
```

### Secured

**Definition**: Input validation, authentication, SQL injection prevention

**Acceptance Criteria**:
```gherkin
Given security audit is performed
Then all inputs are validated via Pydantic
And authentication is required for all operations
And SQL injection is prevented via parameterized queries
And security audit passes with no critical findings
```

### Trackable

**Definition**: Structured logging, message IDs, meeting tracking

**Acceptance Criteria**:
```gherkin
Given system is running
When events occur
Then all communications are logged with timestamps and IDs
And all meetings have full history logged
And all decisions are linked to meetings and communications
And logs can be queried by agent_id, meeting_id, or topic
```

---

## Definition of Done

A feature is considered complete when:

- [ ] All acceptance criteria for the feature are met
- [ ] Unit tests are written and passing (>= 85% coverage)
- [ ] Integration tests are written and passing
- [ ] Code passes ruff linting (zero errors)
- [ ] Code passes black formatting
- [ ] Code passes mypy type checking
- [ ] Documentation is updated (API docs, architecture)
- [ ] TRUST 5 quality gates are validated
- [ ] Security review is completed (for security-sensitive features)
- [ ] Performance benchmarks meet requirements
- [ ] Code is reviewed and approved
- [ ] Changes are committed with conventional commit message

---

**END OF ACCEPTANCE CRITERIA - SPEC-AGENT-COMM-001**
