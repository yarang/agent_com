# SPEC-MCP-BROKER-001: MCP Broker Server

## TAG BLOCK

```yaml
SPEC_ID: SPEC-MCP-BROKER-001
TITLE: MCP Broker Server - Inter-Claude Code Communication System
STATUS: Planned
PRIORITY: High
DOMAIN: MCP-BROKER
VERSION: 1.0.0
CREATED: 2026-01-31
ASSIGNED: manager-ddd
TRACEABILITY:
  - PLAN: .moai/specs/SPEC-MCP-BROKER-001/plan.md
  - ACCEPTANCE: .moai/specs/SPEC-MCP-BROKER-001/acceptance.md
```

---

## Environment

### System Context

The MCP Broker Server is a centralized communication middleware that enables multiple Claude Code instances to discover each other, negotiate communication capabilities, and exchange messages. The server implements the Model Context Protocol (MCP) standard to provide tools that Claude Code instances can invoke.

### Technical Environment

- **Language**: Python 3.13+
- **MCP SDK**: `mcp` (official Python SDK)
- **Async Framework**: asyncio with async/await patterns
- **Web Framework**: FastAPI/Starlette for HTTP/SSE endpoints
- **Data Validation**: Pydantic v2.9+ for schema validation
- **Protocol Definition**: JSON Schema based
- **Optional Message Queue**: Redis for distributed deployments

### Deployment Environment

- **Development**: Local development with SQLite-based in-memory storage
- **Production**: Containerized deployment with optional Redis cluster
- **Network**: HTTP/HTTPS with Server-Sent Events (SSE) for real-time updates

---

## Assumptions

### Technical Assumptions

| Assumption | Confidence | Evidence Basis | Risk if Wrong | Validation Method |
|------------|------------|----------------|---------------|-------------------|
| Official MCP Python SDK supports custom server implementation | High | MCP SDK documentation shows server creation patterns | Medium - May need to adapt to SDK limitations | Create prototype server with basic tools |
| FastAPI SSE can handle concurrent connection pooling | High | Industry standard for async streaming | Low - Well-established pattern | Load testing with 100+ concurrent connections |
| Pydantic v2.9 supports recursive JSON Schema validation | High | Pydantic v2 documentation confirms | Low - Core feature of Pydantic v2 | Unit test with nested protocol schemas |
| Redis optional for distributed message queue | Medium | Redis pub/sub pattern is well-documented | Medium - May require architectural changes | Implement fallback to in-memory queue |
| Claude Code instances can maintain persistent SSE connections | Medium | Based on SSE browser/client capabilities | High - May need WebSocket fallback | Test with various network conditions |

### Business Assumptions

| Assumption | Confidence | Evidence Basis | Risk if Wrong | Validation Method |
|------------|------------|----------------|---------------|-------------------|
| Multiple Claude Code instances need to coordinate on same machine | High | User workflow indicates multi-project scenarios | Low - Core use case | User survey/interview |
| Protocol versioning is critical for backward compatibility | High | Software evolution pattern | Medium - May over-engineer initially | Review MCP protocol evolution patterns |
| Message routing needs both 1:1 and 1:N patterns | High | Collaboration scenarios require both | Low - Standard messaging pattern | Prototype both routing patterns |

### Root Cause Analysis (Five Whys)

1. **Surface Problem**: Claude Code instances cannot communicate with each other
2. **First Why**: No standard communication protocol exists between instances
3. **Second Why**: Each Claude Code instance operates in isolation without shared context
4. **Third Why**: No centralized registry or discovery mechanism
5. **Root Cause**: MCP standard focuses on server-client communication, not peer-to-peer between clients

**Solution Approach**: Implement MCP Broker Server as intermediary that enables client-to-client communication via MCP tools.

---

## Requirements (EARS Format)

### 1. Protocol Registry Requirements

**UBIQUITOUS**: The system SHALL maintain a registry of all registered communication protocols with version tracking.

**WHEN** a client registers a protocol, **THEN** the system SHALL validate the protocol definition against JSON Schema standards and store it with timestamp and version information.

**IF** a protocol with the same name already exists, **THEN** the system SHALL reject registration with a descriptive error indicating conflict resolution options.

**WHILE** the broker server is running, **THEN** the system SHALL provide protocol discovery capabilities for clients to query available protocols by name, version, or capability tags.

**WHERE** a protocol definition includes semantic versioning, **THEN** the system SHALL support version range queries (e.g., ">=1.0.0,<2.0.0").

**THE SYSTEM SHALL NOT** allow protocol deletion if active sessions reference that protocol version.

### 2. Session Manager Requirements

**UBIQUITOUS**: The system SHALL assign a unique session ID to each connected Claude Code instance upon registration.

**WHEN** a session connects, **THEN** the system SHALL record connection timestamp, client capabilities, and supported protocol versions.

**IF** a session fails to send heartbeat within 30 seconds, **THEN** the system SHALL mark the session as stale and initiate graceful disconnection after 60 seconds of inactivity.

**WHILE** a session is active, **THEN** the system SHALL queue messages for disconnected recipients and deliver upon reconnection within configurable queue size limits.

**WHEN** a session disconnects gracefully, **THEN** the system SHALL release all associated resources and notify all active sessions of the departure.

**THE SYSTEM SHALL NOT** allow sessions with duplicate session IDs to coexist; second connection SHALL cause first to be terminated.

### 3. Capability Negotiator Requirements

**UBIQUITOUS**: The system SHALL perform capability negotiation when a new session connects.

**WHEN** a session connects, **THEN** the system SHALL exchange supported protocol versions and feature sets with the connecting client.

**IF** no compatible protocol version exists between sessions, **THEN** the system SHALL return clear incompatibility details and suggested version upgrades.

**WHILE** negotiating capabilities, **THEN** the system SHALL identify intersection of supported features between sessions and document unsupported features for each session.

**WHERE** optional features are requested, **THEN** the system SHALL allow sessions to operate with reduced feature sets without connection failure.

**THE SYSTEM SHALL NOT** establish message routing between sessions without successful capability negotiation.

### 4. Message Router Requirements

**UBIQUITOUS**: The system SHALL support point-to-point (1:1) and broadcast (1:N) message routing patterns.

**WHEN** a sender requests point-to-point messaging, **THEN** the system SHALL validate recipient session exists, verify capability compatibility, and deliver message with delivery confirmation.

**IF** recipient session is temporarily unavailable, **THEN** the system SHALL queue message for later delivery within queue size limits and return queued status to sender.

**WHEN** a sender requests broadcast messaging, **THEN** the system SHALL deliver message to all sessions with compatible capabilities, excluding the sender, and return delivery summary with success/failure counts.

**WHILE** routing messages, **THEN** the system SHALL apply message transformation adapters when protocol versions differ between sender and recipient.

**THE SYSTEM SHALL NOT** deliver messages to sessions that have explicitly blocked the sender or are in incompatible protocol state.

### 5. MCP Tools Interface Requirements

**UBIQUITOUS**: The system SHALL expose all functionality through standard MCP tools following the official MCP Python SDK patterns.

**register_protocol Tool**:
- **WHEN** invoked, **THEN** the system SHALL accept protocol name, version (semantic versioning), JSON Schema definition, and capability tags as parameters
- **IF** validation fails, **THEN** the system SHALL return detailed validation errors with schema path and constraint details

**discover_protocols Tool**:
- **WHEN** invoked with optional name filter and version range, **THEN** the system SHALL return list of matching protocols with metadata (owner, registration time, capability tags)
- **IF** no protocols match, **THEN** the system SHALL return empty list with descriptive message

**negotiate_capabilities Tool**:
- **WHEN** invoked with target session ID, **THEN** the system SHALL perform capability handshake and return compatibility matrix with supported/unsupported features
- **IF** negotiation fails, **THEN** the system SHALL return failure reason and suggested remediation steps

**send_message Tool**:
- **WHEN** invoked with recipient session ID, message payload, and optional protocol version, **THEN** the system SHALL deliver message and return delivery status with timestamp
- **IF** delivery fails, **THEN** the system SHALL return failure reason (offline, incompatible, queue full) and retry options

**broadcast_message Tool**:
- **WHEN** invoked with message payload and optional capability filter, **THEN** the system SHALL deliver to all compatible sessions and return delivery summary
- **IF** no compatible recipients exist, **THEN** the system SHALL return zero recipient count with explanation

**list_sessions Tool**:
- **WHEN** invoked, **THEN** the system SHALL return list of active sessions with ID, connection time, capabilities, and status
- **IF** no sessions exist, **THEN** the system SHALL return empty list

**THE SYSTEM SHALL NOT** allow MCP tool invocation without proper session authentication.

### 6. Quality and Performance Requirements

**UBIQUITOUS**: The system SHALL log all protocol registrations, session state changes, and message routing operations with structured logging.

**WHEN** processing MCP tool invocations, **THEN** the system SHALL respond within 100ms for local operations and 500ms for distributed operations (Redis mode).

**IF** message queue exceeds 90% capacity, **THEN** the system SHALL emit warning and reject new messages until queue space is available.

**WHILE** handling concurrent connections, **THEN** the system SHALL support at least 50 simultaneous session connections without performance degradation.

**WHERE** Redis is configured, **THEN** the system SHALL implement connection pooling with retry logic and automatic reconnection.

**THE SYSTEM SHALL NOT** lose in-flight messages during graceful shutdown; messages SHALL be persisted to disk or Redis before shutdown completion.

### 7. Security Requirements

**UBIQUITOUS**: The system SHALL validate all input parameters through Pydantic schemas before processing.

**WHEN** a session connects, **THEN** the system SHALL authenticate using API token or certificate-based authentication.

**IF** authentication fails, **THEN** the system SHALL return generic authentication failure without revealing whether username or token was invalid.

**WHILE** processing messages, **THEN** the system SHALL sanitize message payloads to prevent injection attacks and enforce maximum payload size limits (configurable, default 10MB).

**WHERE** sensitive data is logged, **THEN** the system SHALL redact authentication tokens, passwords, and PII from log output.

**THE SYSTEM SHALL NOT** allow protocol registration without proper authorization; authorization level SHALL be configurable per deployment.

### 8. Reliability and Fault Tolerance Requirements

**UBIQUITOUS**: The system SHALL implement graceful degradation when optional components (Redis) are unavailable.

**WHEN** Redis connection fails, **THEN** the system SHALL fall back to in-memory message queue with degraded persistence guarantees and log the fallback event.

**IF** a malformed message is received, **THEN** the system SHALL reject the message with validation error details without crashing or affecting other sessions.

**WHILE** operating in degraded mode, **THEN** the system SHALL continue accepting new connections and processing messages with reduced capacity.

**WHERE** message delivery fails after retry attempts, **THEN** the system SHALL move message to dead-letter queue for manual inspection.

**THE SYSTEM SHALL NOT** allow single client failure to affect other active sessions or cause broker shutdown.

---

## Specifications

### Component Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     MCP Broker Server                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │  MCP Tools      │  │  Session        │  │  Message        │  │
│  │  Interface      │  │  Manager        │  │  Router         │  │
│  │                 │  │                 │  │                 │  │
│  │ • register_     │  │ • Session       │  │ • Point-to-     │  │
│  │   protocol      │  │   Lifecycle     │  │   Point (1:1)   │  │
│  │ • discover_     │  │ • Heartbeat     │  │ • Broadcast     │  │
│  │   protocols     │  │ • Queue         │  │   (1:N)         │  │
│  │ • negotiate_    │  │   Management    │  │ • Transform     │  │
│  │   capabilities  │  │                 │  │   Adapters      │  │
│  │ • send_message  │  └─────────────────┘  └─────────────────┘  │
│  │ • broadcast_    │          │                    │            │
│  │ • list_sessions │          │                    │            │
│  └─────────────────┘          │                    │            │
│         │                     │                    │            │
│         └─────────────────────┴────────────────────┘            │
│                            │                                    │
│                   ┌────────▼─────────┐                          │
│                   │ Protocol         │                          │
│                   │ Registry         │                          │
│                   │                  │                          │
│                   │ • JSON Schema    │                          │
│                   │   Validation     │                          │
│                   │ • Version        │                          │
│                   │   Management     │                          │
│                   │ • Discovery      │                          │
│                   └──────────────────┘                          │
│                            │                                    │
│                   ┌────────▼─────────┐                          │
│                   │ Capability       │                          │
│                   │ Negotiator       │                          │
│                   │                  │                          │
│                   │ • Handshake      │                          │
│                   │ • Compatibility  │                          │
│                   │   Matrix         │                          │
│                   └──────────────────┘                          │
│                            │                                    │
│                   ┌────────▼─────────┐                          │
│                   │ Storage Layer    │                          │
│                   │                  │                          │
│                   │ • In-Memory      │                          │
│                   │ • Redis (opt)    │                          │
│                   └──────────────────┘                          │
└─────────────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
┌───────▼────────┐  ┌───────▼────────┐  ┌───────▼────────┐
│ Claude Code    │  │ Claude Code    │  │ Claude Code    │
│ Instance A     │  │ Instance B     │  │ Instance C     │
└────────────────┘  └────────────────┘  └────────────────┘
```

### Data Model Specifications

#### Protocol Definition Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "MCP Communication Protocol",
  "type": "object",
  "required": ["name", "version", "schema", "capabilities"],
  "properties": {
    "name": {
      "type": "string",
      "pattern": "^[a-z][a-z0-9_]*[a-z0-9]$",
      "description": "Protocol identifier in snake_case"
    },
    "version": {
      "type": "string",
      "pattern": "^[0-9]+\\.[0-9]+\\.[0-9]+$",
      "description": "Semantic version (major.minor.patch)"
    },
    "schema": {
      "type": "object",
      "description": "JSON Schema for message validation"
    },
    "capabilities": {
      "type": "array",
      "items": {
        "type": "string",
        "enum": ["point_to_point", "broadcast", "request_response", "streaming"]
      },
      "description": "Supported communication patterns"
    },
    "metadata": {
      "type": "object",
      "properties": {
        "author": {"type": "string"},
        "description": {"type": "string"},
        "tags": {
          "type": "array",
          "items": {"type": "string"}
        }
      }
    }
  }
}
```

#### Session State Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Session State",
  "type": "object",
  "required": ["session_id", "connection_time", "status"],
  "properties": {
    "session_id": {
      "type": "string",
      "format": "uuid",
      "description": "Unique session identifier"
    },
    "connection_time": {
      "type": "string",
      "format": "date-time",
      "description": "ISO 8601 timestamp of connection"
    },
    "last_heartbeat": {
      "type": "string",
      "format": "date-time",
      "description": "Last heartbeat timestamp"
    },
    "status": {
      "type": "string",
      "enum": ["active", "stale", "disconnected"],
      "description": "Current session status"
    },
    "capabilities": {
      "type": "object",
      "properties": {
        "supported_protocols": {
          "type": "object",
          "additionalProperties": {
            "type": "array",
            "items": {"type": "string"}
          }
        },
        "supported_features": {
          "type": "array",
          "items": {"type": "string"}
        }
      }
    },
    "queue_size": {
      "type": "integer",
      "minimum": 0,
      "description": "Current message queue size"
    }
  }
}
```

#### Message Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Routed Message",
  "type": "object",
  "required": ["message_id", "sender_id", "timestamp", "payload"],
  "properties": {
    "message_id": {
      "type": "string",
      "format": "uuid",
      "description": "Unique message identifier"
    },
    "sender_id": {
      "type": "string",
      "format": "uuid",
      "description": "Sender session ID"
    },
    "recipient_id": {
      "type": "string",
      "format": "uuid",
      "description": "Recipient session ID (null for broadcast)"
    },
    "timestamp": {
      "type": "string",
      "format": "date-time",
      "description": "Message creation timestamp"
    },
    "protocol_name": {
      "type": "string",
      "description": "Protocol identifier for payload validation"
    },
    "protocol_version": {
      "type": "string",
      "description": "Protocol version for payload validation"
    },
    "payload": {
      "type": "object",
      "description": "Message payload validated against protocol schema"
    },
    "headers": {
      "type": "object",
      "properties": {
        "priority": {
          "type": "string",
          "enum": ["low", "normal", "high", "urgent"]
        },
        "ttl": {
          "type": "integer",
          "minimum": 0,
          "description": "Time-to-live in seconds"
        }
      }
    }
  }
}
```

### MCP Tool Definitions

#### Tool: register_protocol

```python
{
    "name": "register_protocol",
    "description": "Register a new communication protocol with JSON Schema validation",
    "inputSchema": {
        "type": "object",
        "required": ["name", "version", "schema"],
        "properties": {
            "name": {
                "type": "string",
                "description": "Protocol identifier (snake_case)"
            },
            "version": {
                "type": "string",
                "description": "Semantic version (e.g., '1.0.0')"
            },
            "schema": {
                "type": "object",
                "description": "JSON Schema for message validation"
            },
            "capabilities": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Supported communication patterns"
            }
        }
    }
}
```

#### Tool: discover_protocols

```python
{
    "name": "discover_protocols",
    "description": "Query available protocols with optional filtering",
    "inputSchema": {
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "Filter by protocol name (optional)"
            },
            "version_range": {
                "type": "string",
                "description": "Semantic version range (e.g., '>=1.0.0,<2.0.0')"
            },
            "tags": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Filter by capability tags"
            }
        }
    }
}
```

#### Tool: negotiate_capabilities

```python
{
    "name": "negotiate_capabilities",
    "description": "Perform capability negotiation with target session",
    "inputSchema": {
        "type": "object",
        "required": ["target_session_id"],
        "properties": {
            "target_session_id": {
                "type": "string",
                "format": "uuid",
                "description": "Target session for negotiation"
            },
            "required_protocols": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "version": {"type": "string"}
                    }
                },
                "description": "Required protocol versions"
            }
        }
    }
}
```

#### Tool: send_message

```python
{
    "name": "send_message",
    "description": "Send point-to-point message to specific session",
    "inputSchema": {
        "type": "object",
        "required": ["recipient_id", "payload"],
        "properties": {
            "recipient_id": {
                "type": "string",
                "format": "uuid",
                "description": "Recipient session ID"
            },
            "protocol_name": {
                "type": "string",
                "description": "Protocol for payload validation"
            },
            "protocol_version": {
                "type": "string",
                "description": "Protocol version for payload validation"
            },
            "payload": {
                "type": "object",
                "description": "Message payload"
            },
            "priority": {
                "type": "string",
                "enum": ["low", "normal", "high", "urgent"],
                "default": "normal"
            },
            "ttl": {
                "type": "integer",
                "minimum": 0,
                "description": "Time-to-live in seconds"
            }
        }
    }
}
```

#### Tool: broadcast_message

```python
{
    "name": "broadcast_message",
    "description": "Broadcast message to all compatible sessions",
    "inputSchema": {
        "type": "object",
        "required": ["payload"],
        "properties": {
            "protocol_name": {
                "type": "string",
                "description": "Protocol for payload validation"
            },
            "protocol_version": {
                "type": "string",
                "description": "Protocol version for payload validation"
            },
            "payload": {
                "type": "object",
                "description": "Message payload"
            },
            "capability_filter": {
                "type": "object",
                "description": "Filter recipients by capabilities"
            },
            "priority": {
                "type": "string",
                "enum": ["low", "normal", "high", "urgent"],
                "default": "normal"
            }
        }
    }
}
```

#### Tool: list_sessions

```python
{
    "name": "list_sessions",
    "description": "List all active sessions with their capabilities",
    "inputSchema": {
        "type": "object",
        "properties": {
            "status_filter": {
                "type": "string",
                "enum": ["active", "stale", "all"],
                "default": "active",
                "description": "Filter sessions by status"
            },
            "include_capabilities": {
                "type": "boolean",
                "default": true,
                "description": "Include full capability details"
            }
        }
    }
}
```

---

## Traceability

### Requirement to Component Mapping

| Requirement Category | Component | Traceability ID |
|---------------------|-----------|-----------------|
| Protocol Registry | ProtocolRegistry | REQ-PROTO-001 |
| Session Management | SessionManager | REQ-SESS-001 |
| Capability Negotiation | CapabilityNegotiator | REQ-NEG-001 |
| Message Routing (1:1) | MessageRouter | REQ-MSG-001 |
| Message Routing (1:N) | MessageRouter | REQ-MSG-002 |
| MCP Tool Interface | MCPToolsInterface | REQ-MCP-001 |
| Performance | All Components | REQ-PERF-001 |
| Security | All Components | REQ-SEC-001 |
| Reliability | All Components | REQ-REL-001 |

### Acceptance Criteria Reference

See `.moai/specs/SPEC-MCP-BROKER-001/acceptance.md` for detailed acceptance criteria in Given-When-Then format.

### Implementation Plan Reference

See `.moai/specs/SPEC-MCP-BROKER-001/plan.md` for implementation milestones and technical approach.

---

## Dependencies

### External Dependencies

- **mcp** (Official MCP Python SDK) - Model Context Protocol implementation
- **fastapi** >= 0.115.0 - Web framework for HTTP/SSE endpoints
- **pydantic** >= 2.9.0 - Data validation and schema management
- **asyncio** (Python stdlib) - Async runtime
- **jsonschema** >= 4.0.0 - JSON Schema validation
- **redis** (optional) >= 5.0.0 - Distributed message queue

### Internal Dependencies

- None (standalone system)

### System Dependencies

- Python 3.13+
- Redis (optional, for distributed deployments)
- Container runtime (Docker/Podman) for production deployments

---

## Constraints

### Technical Constraints

- MUST use official MCP Python SDK patterns for tool implementation
- MUST support Python 3.13+ (GIL-free mode compatibility)
- MUST NOT rely on synchronous I/O for core message handling
- MUST maintain backward compatibility within major version
- MUST support both in-memory and Redis-based message queuing

### Business Constraints

- Initial release MUST support at least 50 concurrent sessions
- Message delivery latency MUST be under 100ms for local operations
- System MUST gracefully degrade when Redis is unavailable

### Security Constraints

- All protocol registrations MUST be validated against JSON Schema
- Authentication tokens MUST NOT be logged
- Maximum message payload size of 10MB (configurable)
- Rate limiting on MCP tool invocations (configurable)

---

## Quality Attributes

### TRUST 5 Framework Compliance

**Tested**:
- Unit test coverage >= 85% for all components
- Integration tests for MCP tool invocations
- Load tests for concurrent session handling

**Readable**:
- Type hints on all public functions
- Docstrings following Google style
- Clear variable naming (no abbreviations)

**Unified**:
- Consistent async/await patterns
- Pydantic models for all data structures
- Structured logging with JSON format

**Secured**:
- Input validation via Pydantic schemas
- Authentication required for all operations
- Sensitive data redaction in logs

**Trackable**:
- All protocol registrations logged with metadata
- Message routing traced with unique message IDs
- Session state changes logged with timestamps

---

## Appendix

### Glossary

- **MCP**: Model Context Protocol - Standard for AI model tool integration
- **Session**: A connected Claude Code instance with unique identifier
- **Protocol**: Versioned communication contract with JSON Schema definition
- **Capability**: Feature or pattern supported by a session or protocol
- **Point-to-Point**: 1:1 messaging pattern between specific sessions
- **Broadcast**: 1:N messaging pattern from sender to multiple recipients

### References

- [Model Context Protocol Specification](https://modelcontextprotocol.io/)
- [JSON Schema Draft 7](https://json-schema.org/specification-links.html)
- [Semantic Versioning 2.0.0](https://semver.org/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Pydantic v2 Documentation](https://docs.pydantic.dev/)

---

**END OF SPEC-MCP-BROKER-001**
