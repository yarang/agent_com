# Implementation Plan: SPEC-MCP-BROKER-001

## TAG BLOCK

```yaml
SPEC_ID: SPEC-MCP-BROKER-001
RELATED_SPEC: .moai/specs/SPEC-MCP-BROKER-001/spec.md
STATUS: Planned
PHASE: Plan
TRACEABILITY:
  - SPEC: .moai/specs/SPEC-MCP-BROKER-001/spec.md
  - ACCEPTANCE: .moai/specs/SPEC-MCP-BROKER-001/acceptance.md
```

---

## Overview

This document outlines the implementation plan for the MCP Broker Server, following the MoAI DDD (Domain-Driven Development) workflow with ANALYZE-PRESERVE-IMPROVE cycle.

### Project Structure

```
mcp-broker-server/
├── src/
│   └── mcp_broker/
│       ├── __init__.py
│       ├── main.py                 # FastAPI application entry point
│       ├── core/
│       │   ├── __init__.py
│       │   ├── config.py           # Configuration management
│       │   └── logging.py          # Structured logging setup
│       ├── protocol/
│       │   ├── __init__.py
│       │   ├── registry.py         # ProtocolRegistry implementation
│       │   ├── schema.py           # JSON Schema validation
│       │   └── version.py          # Semantic version handling
│       ├── session/
│       │   ├── __init__.py
│       │   ├── manager.py          # SessionManager implementation
│       │   ├── models.py           # Pydantic session models
│       │   └── heartbeat.py        # Heartbeat monitoring
│       ├── negotiation/
│       │   ├── __init__.py
│       │   ├── negotiator.py       # CapabilityNegotiator implementation
│       │   └── matrix.py           # Compatibility matrix computation
│       ├── routing/
│       │   ├── __init__.py
│       │   ├── router.py           # MessageRouter implementation
│       │   ├── queue.py            # Message queue management
│       │   └── adapters.py         # Protocol transformation adapters
│       ├── storage/
│       │   ├── __init__.py
│       │   ├── interface.py        # Storage abstraction layer
│       │   ├── memory.py           # In-memory storage implementation
│       │   └── redis.py            # Redis storage implementation
│       ├── mcp/
│       │   ├── __init__.py
│       │   ├── server.py           # MCP server setup
│       │   └── tools.py            # MCP tool definitions
│       └── models/
│           ├── __init__.py
│           ├── protocol.py         # Protocol Pydantic models
│           ├── session.py          # Session Pydantic models
│           └── message.py          # Message Pydantic models
├── tests/
│   ├── __init__.py
│   ├── conftest.py                 # Pytest fixtures
│   ├── unit/
│   │   ├── test_protocol_registry.py
│   │   ├── test_session_manager.py
│   │   ├── test_capability_negotiator.py
│   │   └── test_message_router.py
│   ├── integration/
│   │   ├── test_mcp_tools.py
│   │   └── test_end_to_end.py
│   └── load/
│       └── test_concurrent_sessions.py
├── pyproject.toml                  # Poetry/pyproject configuration
├── Dockerfile                      # Container image
├── docker-compose.yml              # Development environment
└── README.md
```

---

## Milestones (Priority-Based)

### Primary Goal (Priority High)

**Objective**: Core MCP Broker Server functionality with in-memory storage

**Components**:
1. Protocol Registry with JSON Schema validation
2. Session Manager with heartbeat tracking
3. Capability Negotiator with handshake
4. Message Router with point-to-point messaging
5. MCP Tools Interface (6 core tools)
6. In-memory storage implementation

**Completion Criteria**:
- All 6 MCP tools functional and testable
- Protocol registration and discovery working
- Session lifecycle management complete
- Point-to-point message delivery verified
- Unit test coverage >= 85%

**Dependencies**: Python 3.13+, MCP SDK availability

### Secondary Goal (Priority Medium)

**Objective**: Broadcast messaging and enhanced reliability

**Components**:
1. Broadcast messaging (1:N pattern)
2. Message queuing for offline recipients
3. Graceful degradation without Redis
4. Dead-letter queue for failed messages
5. Message transformation adapters for version compatibility

**Completion Criteria**:
- Broadcast delivery to multiple recipients
- Offline message queuing and delivery
- Dead-letter queue handling
- Version transformation working

**Dependencies**: Primary Goal completion

### Final Goal (Priority Low)

**Objective**: Redis integration and production hardening

**Components**:
1. Redis storage implementation
2. Connection pooling and retry logic
3. Performance optimization (50+ concurrent sessions)
4. Security hardening (authentication, rate limiting)
5. Production deployment configuration

**Completion Criteria**:
- Redis message persistence verified
- Failover from Redis to in-memory tested
- Load test passes with 50+ concurrent sessions
- Security audit passed
- Production Docker image built

**Dependencies**: Secondary Goal completion

### Optional Goal (Priority Optional)

**Objective**: Advanced features and monitoring

**Components**:
1. Metrics and observability (Prometheus)
2. Admin dashboard for protocol/session monitoring
3. Message replay capabilities
4. Protocol migration tools
5. Multi-tenancy support

**Completion Criteria**:
- Metrics endpoint functional
- Basic admin UI available
- Message replay tested

**Dependencies**: Final Goal completion

---

## Technical Approach

### Architecture Patterns

**DDD (Domain-Driven Development)**:
- Each component represents a bounded context
- Domain models defined in `models/` with Pydantic
- Repository pattern for storage abstraction
- Service layer for business logic

**Async/Await Patterns**:
- All I/O operations use asyncio
- `async/await` for database, network, and queue operations
- `asyncio.TaskGroup` (Python 3.11+) for concurrent operations
- Proper resource cleanup with async context managers

**Dependency Injection**:
- FastAPI Depends for HTTP dependencies
- Custom DI container for MCP server initialization
- Interface-based storage layer (memory vs Redis)

### Technology Stack

**Core Dependencies**:

```toml
[tool.poetry.dependencies]
python = "^3.13"
mcp = "^1.0.0"                    # Official MCP SDK
fastapi = "^0.115.0"              # Web framework
pydantic = "^2.9.0"               # Data validation
jsonschema = "^4.0.0"             # JSON Schema validation
uvicorn = {extras = ["standard"], version = "^0.32.0"}  # ASGI server
redis = {version = "^5.0.0", optional = true}  # Optional Redis
semver = "^3.0.0"                 # Semantic version parsing

[tool.poetry.dev-dependencies]
pytest = "^8.0.0"
pytest-asyncio = "^0.24.0"
pytest-cov = "^6.0.0"
httpx = "^0.28.0"                 # Async HTTP client for testing
ruff = "^0.8.0"                   # Linter
black = "^24.0.0"                 # Formatter
mypy = "^1.0.0"                   # Type checker
```

### Design Decisions

**Decision 1: In-Memory vs Redis Storage**

Context: Need to support both development (simple) and production (distributed) deployments.

Options:
- A) In-memory only (simple, no persistence)
- B) Redis only (distributed, complex setup)
- C) Abstracted storage with both implementations

Decision: Option C - Abstracted storage with both implementations

Rationale:
- Development simplicity with in-memory
- Production scalability with Redis
- Graceful degradation when Redis unavailable
- Easy testing with mock storage

Trade-offs:
- Additional abstraction layer complexity
- Need to maintain two implementations

**Decision 2: Message Transformation Strategy**

Context: Sessions may support different protocol versions.

Options:
- A) Reject messages with version mismatch
- B) Automatic transformation adapters
- C) Sender-side version negotiation

Decision: Option B - Automatic transformation adapters

Rationale:
- Better user experience (automatic compatibility)
- Supports gradual protocol evolution
- Clear adapter pattern for maintainability

Trade-offs:
- Complex transformation logic
- Need to maintain version adapters

**Decision 3: SSE vs WebSocket**

Context: Real-time message delivery to connected sessions.

Options:
- A) Server-Sent Events (SSE)
- B) WebSocket
- C) Polling

Decision: Option A - Server-Sent Events

Rationale:
- Simpler implementation (unidirectional)
- Native HTTP semantics
- Better compatibility with MCP server model
- Automatic reconnection handling

Trade-offs:
- No server push from client (not needed)
- Unidirectional only (sufficient for use case)

---

## Component Design

### Protocol Registry

**Responsibilities**:
- Store protocol definitions with version tracking
- Validate protocol schemas using JSON Schema
- Support protocol discovery with filtering
- Prevent duplicate protocol registrations

**Key Methods**:
```python
class ProtocolRegistry:
    async def register(self, protocol: ProtocolDefinition) -> ProtocolInfo
    async def discover(
        self,
        name: str | None = None,
        version_range: str | None = None,
        tags: list[str] | None = None
    ) -> list[ProtocolInfo]
    async def get(self, name: str, version: str) -> ProtocolDefinition | None
    async def validate_schema(self, schema: dict) -> ValidationResult
```

**Data Model**:
```python
class ProtocolDefinition(BaseModel):
    name: str = Field(pattern="^[a-z][a-z0-9_]*[a-z0-9]$")
    version: str = Field(pattern="^[0-9]+\\.[0-9]+\\.[0-9]+$")
    schema: dict
    capabilities: list[Literal["point_to_point", "broadcast", "request_response", "streaming"]]
    metadata: ProtocolMetadata | None = None
```

### Session Manager

**Responsibilities**:
- Assign unique session IDs on connection
- Track session state (active, stale, disconnected)
- Monitor heartbeats and detect stale sessions
- Queue messages for temporarily unavailable sessions
- Manage graceful disconnection

**Key Methods**:
```python
class SessionManager:
    async def create_session(
        self,
        capabilities: SessionCapabilities
    ) -> Session
    async def get_session(self, session_id: UUID) -> Session | None
    async def update_heartbeat(self, session_id: UUID) -> None
    async def list_sessions(
        self,
        status_filter: SessionStatus | None = None
    ) -> list[Session]
    async def disconnect_session(self, session_id: UUID) -> None
    async def enqueue_message(
        self,
        recipient_id: UUID,
        message: Message
    ) -> EnqueueResult
    async def dequeue_messages(
        self,
        session_id: UUID
    ) -> list[Message]
```

**Data Model**:
```python
class Session(BaseModel):
    session_id: UUID
    connection_time: datetime
    last_heartbeat: datetime
    status: Literal["active", "stale", "disconnected"]
    capabilities: SessionCapabilities
    queue_size: int = 0
```

### Capability Negotiator

**Responsibilities**:
- Perform handshake between sessions
- Compute capability intersection
- Identify incompatibilities
- Provide compatibility reports

**Key Methods**:
```python
class CapabilityNegotiator:
    async def negotiate(
        self,
        session_a: Session,
        session_b: Session,
        required_protocols: list[ProtocolRequirement] | None = None
    ) -> NegotiationResult
    async def check_compatibility(
        self,
        session: Session,
        protocol_name: str,
        protocol_version: str
    ) -> CompatibilityStatus
    def compute_compatibility_matrix(
        self,
        sessions: list[Session]
    ) -> CompatibilityMatrix
```

**Data Model**:
```python
class NegotiationResult(BaseModel):
    compatible: bool
    supported_protocols: dict[str, str]  # name -> version
    unsupported_protocols: list[str]
    feature_intersections: list[str]
    feature_differences: dict[str, list[str]]
```

### Message Router

**Responsibilities**:
- Route point-to-point messages (1:1)
- Route broadcast messages (1:N)
- Apply transformation adapters for version differences
- Handle delivery failures and retries
- Manage dead-letter queue

**Key Methods**:
```python
class MessageRouter:
    async def send_message(
        self,
        sender_id: UUID,
        recipient_id: UUID,
        message: Message
    ) -> DeliveryResult
    async def broadcast_message(
        self,
        sender_id: UUID,
        message: Message,
        capability_filter: dict | None = None
    ) -> BroadcastResult
    async def transform_message(
        self,
        message: Message,
        from_version: str,
        to_version: str
    ) -> Message
```

**Data Model**:
```python
class Message(BaseModel):
    message_id: UUID = Field(default_factory=uuid4)
    sender_id: UUID
    recipient_id: UUID | None  # None for broadcast
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    protocol_name: str
    protocol_version: str
    payload: dict
    headers: MessageHeaders | None = None

class DeliveryResult(BaseModel):
    success: bool
    delivered_at: datetime | None
    error_reason: str | None
    queued: bool = False
```

### Storage Layer

**Responsibilities**:
- Abstract storage interface
- In-memory implementation for development
- Redis implementation for production
- Automatic failover between implementations

**Interface**:
```python
class StorageBackend(Protocol):
    async def get_protocol(self, name: str, version: str) -> ProtocolDefinition | None
    async def save_protocol(self, protocol: ProtocolDefinition) -> None
    async def get_session(self, session_id: UUID) -> Session | None
    async def save_session(self, session: Session) -> None
    async def enqueue_message(self, session_id: UUID, message: Message) -> None
    async def dequeue_messages(self, session_id: UUID, limit: int) -> list[Message]
```

---

## Risk Analysis and Mitigation

### Technical Risks

| Risk | Probability | Impact | Mitigation Strategy |
|------|-------------|--------|---------------------|
| MCP SDK patterns change during development | Medium | Medium | Pin MCP SDK version, create abstraction layer |
| Redis connection instability in production | Low | High | Implement retry logic with exponential backoff, fallback to in-memory |
| Concurrent session scaling limits | Low | Medium | Load testing during development, optimize async patterns |
| JSON Schema validation performance | Medium | Low | Cache compiled validators, lazy validation |

### Operational Risks

| Risk | Probability | Impact | Mitigation Strategy |
|------|-------------|--------|---------------------|
| Message queue exhaustion under load | Medium | High | Implement queue size limits, backpressure, monitoring |
| Session state inconsistency after crash | Low | High | Implement periodic state persistence, recovery procedures |
| Security vulnerability in protocol validation | Low | High | Security audit, input fuzzing, OWASP compliance |

---

## Testing Strategy

### Unit Tests

**Coverage Target**: >= 85%

**Test Categories**:
1. Protocol validation tests (JSON Schema)
2. Session lifecycle tests (create, heartbeat, disconnect)
3. Capability negotiation tests (compatible, incompatible)
4. Message routing tests (1:1, 1:N, failures)
5. Storage abstraction tests (memory, Redis mock)

**Example Test**:
```python
@pytest.mark.asyncio
async def test_register_protocol_valid():
    registry = ProtocolRegistry(storage=InMemoryStorage())
    protocol = ProtocolDefinition(
        name="test_protocol",
        version="1.0.0",
        schema={"type": "object"},
        capabilities=["point_to_point"]
    )
    result = await registry.register(protocol)
    assert result.name == "test_protocol"
    assert result.version == "1.0.0"
```

### Integration Tests

**Coverage**: All MCP tools, end-to-end flows

**Test Scenarios**:
1. Register protocol -> Discover protocol
2. Connect session -> Negotiate capabilities -> Send message
3. Broadcast to multiple sessions
4. Session disconnect -> Message queuing -> Reconnect -> Delivery
5. Redis failover to in-memory

**Example Test**:
```python
@pytest.mark.asyncio
async def test_end_to_end_messaging():
    broker = MCPBrokerServer()
    await broker.start()

    # Session A registers protocol
    await broker.mcp_server.call_tool(
        "register_protocol",
        {"name": "chat", "version": "1.0.0", "schema": {...}}
    )

    # Sessions connect and negotiate
    session_a = await broker.session_manager.create_session(...)
    session_b = await broker.session_manager.create_session(...)
    await broker.negotiator.negotiate(session_a, session_b)

    # Send message
    result = await broker.mcp_server.call_tool(
        "send_message",
        {"recipient_id": str(session_b.session_id), "payload": {...}}
    )

    assert result["success"] is True
```

### Load Tests

**Tools**: Locust or custom pytest-asyncio

**Test Scenarios**:
1. 50 concurrent sessions
2. 100 messages/second throughput
3. Broadcast to 50 recipients
4. Session reconnection churn

**Acceptance Criteria**:
- P50 latency < 50ms
- P95 latency < 100ms
- P99 latency < 500ms
- Zero message loss (with queuing)

---

## Development Workflow

### Phase 1: Foundation (Primary Goal)

1. **Setup Project**
   - Create directory structure
   - Configure pyproject.toml
   - Setup pre-commit hooks (ruff, black)

2. **Implement Core Models**
   - Pydantic models for Protocol, Session, Message
   - JSON Schema validation utilities

3. **Implement Protocol Registry**
   - In-memory storage backend
   - Register/discover functionality
   - Unit tests

4. **Implement Session Manager**
   - Session lifecycle
   - Heartbeat monitoring
   - Message queuing
   - Unit tests

5. **Implement Capability Negotiator**
   - Handshake logic
   - Compatibility matrix
   - Unit tests

6. **Implement Message Router**
   - Point-to-point routing
   - Basic broadcast (no version transformation)
   - Unit tests

7. **Implement MCP Server**
   - Tool definitions
   - Server setup with MCP SDK
   - Integration tests

8. **Quality Gates**
   - TRUST 5 validation
   - Coverage report
   - Documentation

### Phase 2: Enhanced Features (Secondary Goal)

1. **Broadcast with Transformation**
   - Version transformation adapters
   - Capability filtering

2. **Reliability Features**
   - Dead-letter queue
   - Offline queuing
   - Graceful degradation

3. **Integration Testing**
   - End-to-end scenarios
   - Failure scenarios

### Phase 3: Production Hardening (Final Goal)

1. **Redis Integration**
   - Redis storage implementation
   - Connection pooling
   - Failover logic

2. **Security**
   - Authentication middleware
   - Rate limiting
   - Input sanitization audit

3. **Performance**
   - Load testing
   - Optimization
   - Profiling

4. **Deployment**
   - Docker image
   - Docker Compose for development
   - Production configuration

---

## Success Criteria

### Functional Requirements

- [ ] All 6 MCP tools functional
- [ ] Protocol registration and discovery working
- [ ] Session lifecycle management complete
- [ ] Point-to-point message delivery verified
- [ ] Broadcast message delivery verified
- [ ] Offline message queuing tested

### Quality Requirements

- [ ] Unit test coverage >= 85%
- [ ] All integration tests passing
- [ ] Load test passes (50+ concurrent sessions)
- [ ] Zero ruff lint errors
- [ ] Zero mypy type errors
- [ ] Security audit passed

### Documentation Requirements

- [ ] README with quick start
- [ ] API documentation for MCP tools
- [ ] Architecture diagram
- [ ] Deployment guide
- [ ] Troubleshooting guide

---

## Next Steps

1. **Execute `/moai:2-run SPEC-MCP-BROKER-001`** to begin implementation
2. **Review acceptance criteria** in `acceptance.md`
3. **Setup development environment** with Docker Compose
4. **Implement Primary Goal** components in order
5. **Validate quality gates** before proceeding to Secondary Goal

---

**END OF PLAN - SPEC-MCP-BROKER-001**
