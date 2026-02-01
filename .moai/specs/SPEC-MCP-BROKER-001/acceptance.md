# Acceptance Criteria: SPEC-MCP-BROKER-001

## TAG BLOCK

```yaml
SPEC_ID: SPEC-MCP-BROKER-001
RELATED_SPEC: .moai/specs/SPEC-MCP-BROKER-001/spec.md
STATUS: Planned
PHASE: Plan
TRACEABILITY:
  - SPEC: .moai/specs/SPEC-MCP-BROKER-001/spec.md
  - PLAN: .moai/specs/SPEC-MCP-BROKER-001/plan.md
```

---

## Overview

This document defines detailed acceptance criteria for the MCP Broker Server using the Given-When-Then format for Behavior-Driven Development (BDD) and TRUST 5 quality validation.

---

## Component 1: Protocol Registry

### AC-PROTO-001: Protocol Registration

**GIVEN** a running MCP Broker Server
**AND** the protocol registry is initialized
**WHEN** a client registers a protocol with valid name, version, and JSON Schema
**THEN** the protocol SHALL be stored with timestamp
**AND** registration SHALL return success with protocol metadata
**AND** the protocol SHALL be discoverable by name and version

**Example**:
```gherkin
Given broker server is running
And protocol registry is initialized
When client registers protocol:
  """
  {
    "name": "chat_message",
    "version": "1.0.0",
    "schema": {
      "type": "object",
      "properties": {
        "text": {"type": "string"},
        "timestamp": {"type": "string", "format": "date-time"}
      },
      "required": ["text"]
    },
    "capabilities": ["point_to_point"]
  }
  """
Then protocol is stored with registration timestamp
And registration returns:
  """
  {
    "success": true,
    "protocol": {
      "name": "chat_message",
      "version": "1.0.0",
      "registered_at": "2026-01-31T10:00:00Z"
    }
  }
  """
And protocol "chat_message" version "1.0.0" is discoverable
```

### AC-PROTO-002: Protocol Validation

**GIVEN** a running MCP Broker Server
**WHEN** a client attempts to register a protocol with invalid JSON Schema
**THEN** registration SHALL fail with detailed validation error
**AND** error SHALL include schema path and constraint details

**Example**:
```gherkin
Given broker server is running
When client registers protocol with invalid schema:
  """
  {
    "name": "invalid_protocol",
    "version": "1.0.0",
    "schema": {"type": "invalid_type"}
  }
  """
Then registration fails with:
  """
  {
    "success": false,
    "error": "Schema validation failed",
    "details": {
      "path": "$.type",
      "constraint": "enum",
      "expected": ["object", "array", "string", ...]
    }
  }
  """
```

### AC-PROTO-003: Duplicate Protocol Prevention

**GIVEN** a protocol "chat_message" version "1.0.0" is registered
**WHEN** a client attempts to register the same protocol with same name and version
**THEN** registration SHALL fail with conflict error
**AND** error SHALL suggest version increment or name change

**Example**:
```gherkin
Given protocol "chat_message" version "1.0.0" is registered
When client registers protocol with same name and version
Then registration fails with:
  """
  {
    "success": false,
    "error": "Protocol already exists",
    "suggestion": "Increment version to 1.0.1 or use different name"
  }
  """
```

### AC-PROTO-004: Protocol Discovery

**GIVEN** multiple protocols are registered:
- "chat_message" version "1.0.0" with tags ["messaging", "text"]
- "file_transfer" version "2.1.0" with tags ["file", "binary"]
- "chat_message" version "1.1.0" with tags ["messaging", "text", "encryption"]

**WHEN** a client queries protocols with filters
**THEN** system SHALL return matching protocols

**Scenarios**:
```gherkin
Scenario: Query by name
When client calls discover_protocols(name="chat_message")
Then returns:
  """
  {
    "protocols": [
      {"name": "chat_message", "version": "1.0.0"},
      {"name": "chat_message", "version": "1.1.0"}
    ]
  }
  """

Scenario: Query by version range
When client calls discover_protocols(version_range=">=1.1.0,<2.0.0")
Then returns protocols with versions 1.1.0 only

Scenario: Query by tags
When client calls discover_protocols(tags=["file"])
Then returns only "file_transfer" protocol
```

### AC-PROTO-005: Protocol Deletion Prevention

**GIVEN** protocol "chat_message" version "1.0.0" is registered
**AND** active session A references this protocol version
**WHEN** admin attempts to delete the protocol
**THEN** deletion SHALL fail
**AND** error SHALL indicate active references

**Example**:
```gherkin
Given protocol "chat_message" version "1.0.0" is registered
And session A is using this protocol
When admin attempts to delete protocol
Then deletion fails with:
  """
  {
    "success": false,
    "error": "Cannot delete protocol with active references",
    "active_sessions": ["session-a-id"]
  }
  """
```

---

## Component 2: Session Manager

### AC-SESS-001: Session Creation

**GIVEN** a running MCP Broker Server
**WHEN** a new client connects and registers as a session
**THEN** system SHALL assign a unique UUID session ID
**AND** record connection timestamp
**AND** store session capabilities
**AND** return session information to client

**Example**:
```gherkin
Given broker server is running
When client connects with capabilities:
  """
  {
    "supported_protocols": {
      "chat_message": ["1.0.0", "1.1.0"],
      "file_transfer": ["2.0.0"]
    },
    "supported_features": ["point_to_point", "broadcast"]
  }
  """
Then session is created with:
  """
  {
    "session_id": "<uuid>",
    "connection_time": "2026-01-31T10:00:00Z",
    "status": "active",
    "capabilities": {...}
  }
  """
And session_id is a valid UUID v4
```

### AC-SESS-002: Heartbeat Monitoring

**GIVEN** an active session
**WHEN** session sends heartbeat within 30 seconds
**THEN** session status SHALL remain "active"
**AND** last_heartbeat timestamp SHALL be updated

**GIVEN** an active session
**WHEN** session fails to send heartbeat for 30 seconds
**THEN** session status SHALL change to "stale"

**GIVEN** a stale session
**WHEN** session fails to send heartbeat for 60 seconds total
**THEN** session SHALL be automatically disconnected

**Example**:
```gherkin
Scenario: Active heartbeat
Given session A is active
When session A sends heartbeat at T+20s
Then session A status is "active"
And last_heartbeat is T+20s

Scenario: Session becomes stale
Given session A is active at T0
And no heartbeat received for 31 seconds
When system checks session status
Then session A status is "stale"

Scenario: Session auto-disconnect
Given session A is stale at T0
And no heartbeat received for 61 seconds total
When system cleanup runs
Then session A status is "disconnected"
And session A resources are released
```

### AC-SESS-003: Duplicate Session Prevention

**GIVEN** an active session with ID "abc-123"
**WHEN** a new connection attempts to register with same session ID
**THEN** first session SHALL be terminated
**AND** new connection SHALL be assigned the session ID
**AND** termination event SHALL be logged

**Example**:
```gherkin
Given session "abc-123" is active
When new connection attempts to register with session_id "abc-123"
Then existing session "abc-123" is terminated
And new connection is assigned session_id "abc-123"
And termination is logged with:
  """
  {
    "event": "session_replaced",
    "session_id": "abc-123",
    "reason": "duplicate_registration",
    "timestamp": "2026-01-31T10:00:00Z"
  }
  """
```

### AC-SESS-004: Message Queuing for Offline Sessions

**GIVEN** session A is active
**AND** session B is disconnected
**AND** queue size limit is 100 messages
**WHEN** session A sends a message to session B
**THEN** message SHALL be queued for session B
**AND** queue size SHALL increment
**AND** sender SHALL receive "queued" status

**GIVEN** session B has 99 queued messages
**WHEN** session A sends another message to session B
**THEN** message SHALL be queued (queue size = 100)

**GIVEN** session B has 100 queued messages
**WHEN** session A sends another message to session B
**THEN** message SHALL be rejected
**AND** sender SHALL receive "queue_full" error

**Example**:
```gherkin
Scenario: Queue message for offline session
Given session A is active
And session B is disconnected
And session B queue size is 0
When session A sends message to session B
Then message is queued for session B
And session B queue size is 1
And sender receives: {"status": "queued", "queue_size": 1}

Scenario: Queue full rejection
Given session B queue has 100 messages
When session A sends message to session B
Then message is rejected
And sender receives:
  """
  {
    "status": "error",
    "error": "queue_full",
    "queue_size": 100
  }
  """
```

### AC-SESS-005: Session Reconnection and Delivery

**GIVEN** session B has 5 queued messages
**WHEN** session B reconnects
**THEN** all 5 queued messages SHALL be delivered
**AND** queue SHALL be empty
**AND** delivery status SHALL be confirmed for each message

**Example**:
```gherkin
Given session B is disconnected
And session B has 5 queued messages
When session B reconnects with session_id "session-b-id"
Then 5 queued messages are delivered to session B
And session B queue size is 0
And each message delivery is confirmed
```

---

## Component 3: Capability Negotiator

### AC-NEG-001: Successful Capability Negotiation

**GIVEN** two sessions with compatible capabilities:
- Session A supports: "chat_message" ["1.0.0", "1.1.0"], features ["point_to_point"]
- Session B supports: "chat_message" ["1.0.0"], features ["point_to_point", "broadcast"]

**WHEN** capability negotiation is performed
**THEN** negotiation SHALL succeed
**AND** common protocols SHALL be identified
**AND** common features SHALL be identified
**AND** compatibility matrix SHALL be returned

**Example**:
```gherkin
Given session A capabilities:
  """
  {
    "supported_protocols": {"chat_message": ["1.0.0", "1.1.0"]},
    "supported_features": ["point_to_point"]
  }
  """
And session B capabilities:
  """
  {
    "supported_protocols": {"chat_message": ["1.0.0"]},
    "supported_features": ["point_to_point", "broadcast"]
  }
  """
When negotiation is performed between A and B
Then negotiation succeeds with:
  """
  {
    "compatible": true,
    "supported_protocols": {"chat_message": "1.0.0"},
    "feature_intersections": ["point_to_point"],
    "unsupported_features": {
      "session_a": ["broadcast"],
      "session_b": []
    }
  }
  """
```

### AC-NEG-002: Incompatible Protocol Versions

**GIVEN** two sessions with incompatible protocol versions:
- Session A supports: "chat_message" ["2.0.0"]
- Session B supports: "chat_message" ["1.0.0"]

**WHEN** capability negotiation is performed
**THEN** negotiation SHALL fail
**AND** incompatibility details SHALL be provided
**AND** suggestions SHALL be provided for resolution

**Example**:
```gherkin
Given session A supports chat_message ["2.0.0"]
And session B supports chat_message ["1.0.0"]
When negotiation is performed
Then negotiation fails with:
  """
  {
    "compatible": false,
    "reason": "No compatible protocol versions",
    "incompatibilities": [
      {
        "protocol": "chat_message",
        "session_a_versions": ["2.0.0"],
        "session_b_versions": ["1.0.0"],
        "suggestion": "Session B should upgrade to 2.0.0 or Session A should add 1.0.0 support"
      }
    ]
  }
  """
```

### AC-NEG-003: Negotiation with Required Protocols

**GIVEN** two sessions with multiple protocols
**WHEN** session A requires specific protocol versions for negotiation
**THEN** system SHALL verify required protocols are supported
**AND** return appropriate result

**Example**:
```gherkin
Given session A and session B both support multiple protocols
When session A requests negotiation with required:
  """
  {
    "required_protocols": [
      {"name": "chat_message", "version": "1.0.0"},
      {"name": "file_transfer", "version": "2.0.0"}
    ]
  }
  """
And session B supports both required versions
Then negotiation succeeds

And session B supports only chat_message 1.0.0
Then negotiation fails with missing protocol error
```

### AC-NEG-004: Capability Matrix Computation

**GIVEN** three sessions:
- Session A: protocols ["chat:1.0", "file:2.0"], features ["p2p"]
- Session B: protocols ["chat:1.0", "chat:1.1"], features ["p2p", "broadcast"]
- Session C: protocols ["file:2.0", "file:2.1"], features ["p2p"]

**WHEN** compatibility matrix is computed for all sessions
**THEN** matrix SHALL show pairwise compatibility
**AND** identify common protocols and features for each pair

**Example**:
```gherkin
Given sessions A, B, C with varied capabilities
When compatibility matrix is computed
Then matrix shows:
  """
  {
    "pairs": {
      "A-B": {
        "compatible": true,
        "common_protocols": {"chat": "1.0"},
        "common_features": ["p2p"]
      },
      "A-C": {
        "compatible": true,
        "common_protocols": {"file": "2.0"},
        "common_features": ["p2p"]
      },
      "B-C": {
        "compatible": false,
        "common_protocols": {},
        "reason": "No common protocols"
      }
    }
  }
  """
```

---

## Component 4: Message Router

### AC-MSG-001: Point-to-Point Message Delivery

**GIVEN** two sessions with compatible capabilities
**AND** capability negotiation is complete
**WHEN** session A sends a message to session B
**THEN** message SHALL be delivered to session B
**AND** delivery confirmation SHALL be sent to session A
**AND** message SHALL include sender ID, timestamp, and payload

**Example**:
```gherkin
Given session A and B have negotiated capabilities
When session A sends:
  """
  {
    "recipient_id": "<session-b-id>",
    "protocol_name": "chat_message",
    "protocol_version": "1.0.0",
    "payload": {"text": "Hello, World!", "timestamp": "2026-01-31T10:00:00Z"}
  }
  """
Then message is delivered to session B with:
  """
  {
    "message_id": "<uuid>",
    "sender_id": "<session-a-id>",
    "recipient_id": "<session-b-id>",
    "timestamp": "2026-01-31T10:00:00Z",
    "protocol_name": "chat_message",
    "protocol_version": "1.0.0",
    "payload": {"text": "Hello, World!", "timestamp": "2026-01-31T10:00:00Z"}
  }
  """
And session A receives: {"success": true, "delivered_at": "<timestamp>"}
```

### AC-MSG-002: Broadcast Message Delivery

**GIVEN** three active sessions: A, B, C
**AND** all sessions support "chat_message" protocol
**WHEN** session A broadcasts a message
**THEN** message SHALL be delivered to both sessions B and C
**AND** message SHALL NOT be delivered to session A (sender)
**AND** delivery summary SHALL be returned to session A

**Example**:
```gherkin
Given sessions A, B, C are active
And all support chat_message protocol
When session A broadcasts:
  """
  {
    "protocol_name": "chat_message",
    "protocol_version": "1.0.0",
    "payload": {"text": "Broadcast message", "timestamp": "..."}
  }
  """
Then message is delivered to B and C
And message is NOT delivered to A
And session A receives:
  """
  {
    "success": true,
    "recipients": {
      "delivered": ["<session-b-id>", "<session-c-id>"],
      "failed": [],
      "skipped": ["<session-a-id>"]
    },
    "delivery_count": 2
  }
  """
```

### AC-MSG-003: Broadcast with Capability Filter

**GIVEN** three active sessions:
- Session A: features ["point_to_point", "broadcast", "encryption"]
- Session B: features ["point_to_point", "broadcast"]
- Session C: features ["point_to_point"]

**WHEN** session A broadcasts with capability filter {"encryption": true}
**THEN** message SHALL be delivered only to session A (self-excluded)
**AND** sessions B and C SHALL NOT receive message
**AND** delivery summary SHALL indicate zero compatible recipients

**Example**:
```gherkin
Given sessions A, B, C with different capabilities
When session A broadcasts with filter:
  """
  {
    "protocol_name": "chat_message",
    "payload": {...},
    "capability_filter": {"encryption": true}
  }
  """
Then no recipients receive message (all lack encryption except A)
And session A receives:
  """
  {
    "success": true,
    "recipients": {
      "delivered": [],
      "failed": [],
      "skipped": ["<session-a-id>", "<session-b-id>", "<session-c-id>"]
    },
    "delivery_count": 0,
    "reason": "No compatible recipients for capability filter"
  }
  """
```

### AC-MSG-004: Message Transformation Between Versions

**GIVEN** session A supports "chat_message" version "1.1.0"
**AND** session B supports "chat_message" version "1.0.0"
**AND** version 1.1.0 adds optional "encryption" field

**WHEN** session A sends message with protocol version "1.1.0" to session B
**THEN** message SHALL be transformed to version "1.0.0"
**AND** "encryption" field SHALL be removed
**AND** delivery SHALL succeed

**Example**:
```gherkin
Given session A uses chat_message 1.1.0 with encryption field
And session B uses chat_message 1.0.0 without encryption field
When session A sends:
  """
  {
    "recipient_id": "<session-b-id>",
    "protocol_name": "chat_message",
    "protocol_version": "1.1.0",
    "payload": {"text": "Secure message", "encryption": "aes256"}
  }
  """
Then message is transformed to 1.0.0:
  """
  {
    "payload": {"text": "Secure message"},
    "transformed_from": "1.1.0",
    "transformed_to": "1.0.0"
  }
  """
And delivery succeeds
```

### AC-MSG-005: Delivery Failure Handling

**GIVEN** session B is disconnected and queue is full (100 messages)
**WHEN** session A sends a message to session B
**THEN** delivery SHALL fail
**AND** error SHALL indicate "queue_full"
**AND** message SHALL be moved to dead-letter queue
**AND** dead-letter queue metadata SHALL be recorded

**Example**:
```gherkin
Given session B is disconnected
And session B message queue is full (100 messages)
When session A sends message to session B
Then delivery fails with:
  """
  {
    "success": false,
    "error": "queue_full",
    "recipient_id": "<session-b-id>",
    "action": "moved_to_dead_letter"
  }
  """
And message is stored in dead-letter queue with:
  """
  {
    "original_message": {...},
    "failed_at": "2026-01-31T10:00:00Z",
    "reason": "queue_full",
    "sender_id": "<session-a-id>",
    "recipient_id": "<session-b-id>"
  }
  """
```

---

## Component 5: MCP Tools Interface

### AC-MCP-001: register_protocol Tool

**GIVEN** MCP server is running
**WHEN** client calls register_protocol tool with valid parameters
**THEN** tool SHALL return success with protocol metadata

**Test Cases**:
```gherkin
Scenario: Valid protocol registration
Given MCP server is running
When client calls:
  """
  register_protocol({
    "name": "test_protocol",
    "version": "1.0.0",
    "schema": {"type": "object"},
    "capabilities": ["point_to_point"]
  })
  """
Then returns:
  """
  {
    "success": true,
    "protocol": {
      "name": "test_protocol",
      "version": "1.0.0",
      "registered_at": "<timestamp>"
    }
  }
  """

Scenario: Invalid schema format
When client calls register_protocol with invalid schema
Then returns validation error with schema path

Scenario: Missing required fields
When client calls register_protocol without name
Then returns error: "Missing required field: name"
```

### AC-MCP-002: discover_protocols Tool

**GIVEN** multiple protocols are registered
**WHEN** client calls discover_protocols with various filters
**THEN** tool SHALL return matching protocols

**Test Cases**:
```gherkin
Scenario: No filters - return all
Given protocols "chat:1.0.0", "file:2.0.0" are registered
When client calls discover_protocols({})
Then returns both protocols

Scenario: Filter by name
When client calls discover_protocols({"name": "chat"})
Then returns only "chat" protocol(s)

Scenario: Filter by version range
When client calls discover_protocols({"version_range": ">=2.0.0"})
Then returns only "file:2.0.0"

Scenario: No matches
When client calls discover_protocols({"name": "nonexistent"})
Then returns: {"protocols": [], "message": "No protocols found"}
```

### AC-MCP-003: negotiate_capabilities Tool

**GIVEN** two sessions exist
**WHEN** client calls negotiate_capabilities with target session ID
**THEN** tool SHALL perform handshake and return compatibility matrix

**Test Cases**:
```gherkin
Scenario: Compatible sessions
Given session A and B exist
When client calls:
  """
  negotiate_capabilities({"target_session_id": "<session-b-id>"})
  """
Then returns compatibility matrix with compatible=true

Scenario: Incompatible sessions
Given session A and B have no common protocols
When client calls negotiate_capabilities
Then returns compatibility matrix with compatible=false
And includes incompatibility reasons
```

### AC-MCP-004: send_message Tool

**GIVEN** two sessions exist with negotiated capabilities
**WHEN** client calls send_message with recipient ID and payload
**THEN** tool SHALL deliver message and return delivery status

**Test Cases**:
```gherkin
Scenario: Successful delivery
Given session A and B exist
When client calls:
  """
  send_message({
    "recipient_id": "<session-b-id>",
    "protocol_name": "chat_message",
    "protocol_version": "1.0.0",
    "payload": {"text": "Hello"}
  })
  """
Then returns: {"success": true, "delivered_at": "<timestamp>"}

Scenario: Recipient offline
Given session B is disconnected
And queue has space
When client calls send_message to session B
Then returns: {"success": true, "queued": true, "queue_size": 1}

Scenario: Recipient not found
When client calls send_message to non-existent session
Then returns: {"success": false, "error": "session_not_found"}
```

### AC-MCP-005: broadcast_message Tool

**GIVEN** three sessions exist
**WHEN** client calls broadcast_message with payload
**THEN** tool SHALL deliver to all compatible sessions

**Test Cases**:
```gherkin
Scenario: Broadcast to all compatible
Given sessions A, B, C exist
All support chat_message protocol
When client calls:
  """
  broadcast_message({
    "protocol_name": "chat_message",
    "payload": {"text": "Broadcast"}
  })
  """
Then returns:
  """
  {
    "success": true,
    "delivery_count": 2,
    "recipients": {
      "delivered": ["<session-b-id>", "<session-c-id>"],
      "failed": [],
      "skipped": ["<session-a-id>"]
    }
  }
  """

Scenario: No compatible recipients
Given no sessions support the protocol
When client calls broadcast_message
Then returns: {"delivery_count": 0, "reason": "No compatible recipients"}
```

### AC-MCP-006: list_sessions Tool

**GIVEN** multiple sessions exist with various statuses
**WHEN** client calls list_sessions
**THEN** tool SHALL return session list with capabilities

**Test Cases**:
```gherkin
Scenario: List all active sessions
Given sessions A (active), B (stale), C (disconnected) exist
When client calls list_sessions({"status_filter": "active"})
Then returns only session A

Scenario: List all sessions
When client calls list_sessions({"status_filter": "all"})
Then returns all sessions with status

Scenario: Exclude capabilities
When client calls list_sessions({"include_capabilities": false})
Then returns sessions without capability details
```

---

## Component 6: Quality and Performance

### AC-PERF-001: Response Time

**GIVEN** MCP server is running under normal load
**WHEN** any MCP tool is invoked
**THEN** response time SHALL be under 100ms for local operations

**Measurement**:
```gherkin
Given broker server is running
And 10 active sessions
When register_protocol tool is invoked 100 times
Then P50 response time < 50ms
And P95 response time < 100ms
And P99 response time < 200ms
```

### AC-PERF-002: Concurrent Session Support

**GIVEN** broker server is running
**WHEN** 50 sessions connect concurrently
**THEN** all sessions SHALL be successfully created
**AND** message routing SHALL function correctly
**AND** no session SHALL be dropped

**Load Test**:
```gherkin
Given broker server is running
When 50 sessions connect simultaneously
And each session sends 10 messages to random recipients
Then all 50 sessions are active
And all 500 messages are delivered
And no errors occur
And P95 message latency < 100ms
```

### AC-PERF-003: Queue Size Warning

**GIVEN** session message queue has capacity of 100
**WHEN** queue size reaches 90 messages
**THEN** warning SHALL be emitted
**AND** warning SHALL include session ID and queue size

**Example**:
```gherkin
Given session B message queue capacity is 100
And queue size is 89
When another message is queued for session B
Then warning is logged:
  """
  {
    "level": "warning",
    "event": "queue_near_capacity",
    "session_id": "<session-b-id>",
    "queue_size": 90,
    "capacity": 100,
    "usage_percent": 90
  }
  """
```

---

## Component 7: Security

### AC-SEC-001: Input Validation

**GIVEN** MCP server is running
**WHEN** any tool is invoked with invalid input
**THEN** validation SHALL fail via Pydantic
**AND** error SHALL include field path and constraint

**Test Cases**:
```gherkin
Scenario: Invalid UUID format
When send_message is called with invalid recipient_id:
  """
  {"recipient_id": "not-a-uuid", ...}
  """
Then returns error:
  """
  {
    "error": "validation_error",
    "field": "recipient_id",
    "constraint": "uuid_format"
  }
  """

Scenario: Payload size exceeds limit
When message payload is 11MB (limit 10MB)
Then returns error:
  """
  {
    "error": "validation_error",
    "field": "payload",
    "constraint": "max_size",
    "max_size_mb": 10,
    "actual_size_mb": 11
  }
  """
```

### AC-SEC-002: Authentication Token Redaction

**GIVEN** authentication is enabled
**WHEN** session connects with token
**THEN** token SHALL NOT appear in logs
**AND** token SHALL be redacted in all log entries

**Example**:
```gherkin
Given authentication is enabled
When session connects with token "secret-token-123"
And connection is logged
Then log contains:
  """
  {
    "event": "session_connected",
    "session_id": "<uuid>",
    "auth_token": "[REDACTED]"
  }
  """
And token "secret-token-123" does not appear in logs
```

### AC-SEC-003: Protocol Registration Authorization

**GIVEN** protocol registration requires authorization
**WHEN** unauthorized client attempts to register protocol
**THEN** registration SHALL fail
**AND** error SHALL be generic (not reveal authorization requirements)

**Example**:
```gherkin
Given protocol registration requires "admin" role
When client with "user" role calls register_protocol
Then returns error:
  """
  {
    "success": false,
    "error": "Unauthorized"
  }
  """
And error does not mention admin role requirement
```

---

## Component 8: Reliability

### AC-REL-001: Redis Failover

**GIVEN** broker server is configured with Redis
**WHEN** Redis connection fails
**THEN** server SHALL fall back to in-memory storage
**AND** fallback event SHALL be logged
**AND** server SHALL continue accepting connections

**Example**:
```gherkin
Given broker server uses Redis storage
When Redis connection fails
Then fallback event is logged:
  """
  {
    "event": "storage_fallback",
    "from": "redis",
    "to": "memory",
    "reason": "connection_failed",
    "timestamp": "<timestamp>"
  }
  """
And server continues operating with in-memory storage
And new sessions can be created
And messages can be routed
```

### AC-REL-002: Malformed Message Handling

**GIVEN** broker server is running
**WHEN** malformed message is received
**THEN** message SHALL be rejected
**AND** error details SHALL be returned
**AND** server SHALL continue processing other messages
**AND** other sessions SHALL NOT be affected

**Example**:
```gherkin
Given sessions A and B are active
When session A sends malformed message:
  """
  {
    "recipient_id": "<session-b-id>",
    "payload": "this-is-not-a-dict"
  }
  """
Then message is rejected with:
  """
  {
    "success": false,
    "error": "validation_error",
    "details": "payload must be object"
  }
  """
And sessions A and B remain active
And server continues processing
```

### AC-REL-003: Graceful Shutdown

**GIVEN** broker server is running with active sessions and queued messages
**WHEN** shutdown signal is received
**THEN** server SHALL stop accepting new connections
**AND** in-flight messages SHALL be delivered
**AND** queued messages SHALL be persisted to disk/Redis
**AND** sessions SHALL be notified of shutdown

**Example**:
```gherkin
Given server has 5 active sessions
And 10 messages are in queues
When shutdown signal received
Then server:
  1. Stops accepting new connections
  2. Delivers in-flight messages
  3. Persists queued messages to storage
  4. Notifies sessions: {"event": "server_shutdown", "grace_period_seconds": 30}
  5. Waits for graceful disconnect or timeout
  6. Shuts down
And no messages are lost
```

---

## TRUST 5 Quality Gates

### Tested

**Definition**: Unit test coverage >= 85%, integration tests for all MCP tools

**Acceptance Criteria**:
```gherkin
Given all components are implemented
When pytest is executed with coverage
Then coverage report shows >= 85% for all modules
And all integration tests pass
And load tests pass with 50+ concurrent sessions
```

### Readable

**Definition**: Clear naming, type hints, docstrings

**Acceptance Criteria**:
```gherkin
Given all source files
When code is reviewed
Then all public functions have type hints
And all classes have docstrings
And variable names are descriptive (no abbreviations)
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

**Definition**: Input validation, authentication, sensitive data redaction

**Acceptance Criteria**:
```gherkin
Given security audit is performed
Then all inputs are validated via Pydantic
And authentication is required for all operations
And sensitive data is redacted from logs
And security audit passes with no critical findings
```

### Trackable

**Definition**: Structured logging, message IDs, session tracking

**Acceptance Criteria**:
```gherkin
Given server is running
When events occur
Then all protocol registrations are logged with metadata
And all messages have unique message IDs
And all session state changes are logged with timestamps
And logs can be queried by session_id, message_id, or protocol_name
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

**END OF ACCEPTANCE CRITERIA - SPEC-MCP-BROKER-001**
