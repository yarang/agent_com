# Implementation Plan: SPEC-AGENT-COMM-001

## TAG BLOCK

```yaml
SPEC_ID: SPEC-AGENT-COMM-001
RELATED_SPEC: .moai/specs/SPEC-AGENT-COMM-001/spec.md
STATUS: Planned
PHASE: Plan
TRACEABILITY:
  - SPEC: .moai/specs/SPEC-AGENT-COMM-001/spec.md
  - ACCEPTANCE: .moai/specs/SPEC-AGENT-COMM-001/acceptance.md
```

---

## Overview

This document outlines the implementation plan for the AI Agent Communication & Meeting System, following the MoAI DDD (Domain-Driven Development) workflow with ANALYZE-PRESERVE-IMPROVE cycle.

### Project Structure

```
agent_comm_system/
├── src/
│   └── agent_comm/
│       ├── __init__.py
│       ├── main.py                 # FastAPI application entry point
│       ├── core/
│       │   ├── __init__.py
│       │   ├── config.py           # Configuration management
│       │   ├── logging.py          # Structured logging setup
│       │   └── database.py         # Database connection setup
│       ├── models/
│       │   ├── __init__.py
│       │   ├── communication.py    # Communication Pydantic models
│       │   ├── meeting.py          # Meeting Pydantic models
│       │   ├── decision.py         # Decision Pydantic models
│       │   └── agent.py            # Agent Pydantic models
│       ├── repositories/
│       │   ├── __init__.py
│       │   ├── base.py             # Base repository interface
│       │   ├── communication.py    # Communication repository
│       │   ├── meeting.py          # Meeting repository
│       │   └── decision.py         # Decision repository
│       ├── services/
│       │   ├── __init__.py
│       │   ├── communication.py    # Communication service
│       │   ├── meeting.py          # Meeting service
│       │   ├── decision.py         # Decision service
│       │   ├── topic_analyzer.py   # Topic analysis service
│       │   └── discussion.py       # Sequential discussion algorithm
│       ├── api/
│       │   ├── __init__.py
│       │   ├── communications.py   # Communication API routes
│       │   ├── meetings.py         # Meeting API routes
│       │   └── decisions.py        # Decision API routes
│       ├── websocket/
│       │   ├── __init__.py
│       │   ├── manager.py          # WebSocket connection manager
│       │   ├── handler.py          # WebSocket message handler
│       │   └── events.py           # WebSocket event definitions
│       └── db/
│           └── migrations/         # Database migrations (Alembic)
├── tests/
│   ├── __init__.py
│   ├── conftest.py                 # Pytest fixtures
│   ├── unit/
│   │   ├── test_communication_service.py
│   │   ├── test_meeting_service.py
│   │   ├── test_discussion_algorithm.py
│   │   └── test_topic_analyzer.py
│   ├── integration/
│   │   ├── test_api_endpoints.py
│   │   ├── test_websocket.py
│   │   └── test_database.py
│   └── load/
│       └── test_concurrent_meetings.py
├── pyproject.toml
├── Dockerfile
├── docker-compose.yml
└── README.md
```

---

## Milestones (Priority-Based)

### Primary Goal (Priority High)

**Objective**: Core communication logging and basic meeting functionality

**Components**:
1. Database schema setup with all 5 tables
2. Communication logging API (POST, GET)
3. Basic meeting creation and management
4. WebSocket server for agent connections
5. Sequential discussion algorithm (single round)
6. Decision recording and tracking

**Completion Criteria**:
- All database tables created with proper indexes
- Communication can be logged between agents
- Meetings can be created and joined
- WebSocket connections work for agent participation
- Sequential discussion completes one round
- Decisions are recorded with meeting links
- Unit test coverage >= 85%

**Dependencies**: Python 3.13+, PostgreSQL availability

### Secondary Goal (Priority Medium)

**Objective**: Enhanced meeting features and topic analysis

**Components**:
1. Auto-generated topic selection from log analysis
2. Multi-round discussion with consensus tracking
3. Meeting status management (pending -> in_progress -> completed)
4. Enhanced WebSocket event broadcasting
5. Participant management with speaking order
6. Communication query with filters

**Completion Criteria**:
- Topics can be auto-generated from communication logs
- Multi-round discussions work with consensus detection
- Meeting state transitions are proper
- All WebSocket events are broadcast correctly
- Communication queries support all filter types
- Integration tests passing

**Dependencies**: Primary Goal completion

### Final Goal (Priority Low)

**Objective**: Production hardening and optimization

**Components**:
1. Database connection pooling optimization
2. WebSocket connection pooling for 20+ concurrent agents
3. Performance optimization (200ms API response target)
4. Security hardening (authentication, input validation)
5. Error handling and logging improvements
6. Production deployment configuration

**Completion Criteria**:
- Load test passes with 20+ concurrent WebSocket connections
- API responses under 200ms for database queries
- Security audit passed
- All error scenarios handled gracefully
- Production Docker image built
- Documentation complete

**Dependencies**: Secondary Goal completion

### Optional Goal (Priority Optional)

**Objective**: Advanced features and monitoring

**Components**:
1. Metrics and observability (Prometheus)
2. Meeting replay functionality
3. Advanced topic analysis with NLP
4. Admin dashboard for monitoring
5. Meeting templates for common scenarios

**Completion Criteria**:
- Metrics endpoint functional
- Meeting replay works for past meetings
- Advanced topic analysis provides better suggestions
- Admin UI available for monitoring

**Dependencies**: Final Goal completion

---

## Technical Approach

### Architecture Patterns

**DDD (Domain-Driven Development)**:
- Each service represents a bounded context
- Domain models defined in `models/` with Pydantic
- Repository pattern for database abstraction
- Service layer for business logic

**Async/Await Patterns**:
- All I/O operations use asyncio
- `async/await` for database, network, and WebSocket operations
- `asyncio.TaskGroup` (Python 3.11+) for concurrent operations
- Proper resource cleanup with async context managers

**WebSocket State Management**:
- Connection manager for tracking active WebSocket connections
- Per-meeting state for sequential discussion tracking
- Event-driven architecture for meeting events

### Technology Stack

**Core Dependencies**:

```toml
[tool.poetry.dependencies]
python = "^3.13"
fastapi = "^0.115.0"              # Web framework
uvicorn = {extras = ["standard"], version = "^0.32.0"}  # ASGI server
pydantic = "^2.9.0"               # Data validation
sqlalchemy = "^2.0.0"             # Async ORM
asyncpg = "^0.30.0"               # Async PostgreSQL driver
alembic = "^1.13.0"               # Database migrations
python-dotenv = "^1.0.0"          # Configuration
websockets = "^13.0.0"            # WebSocket support

[tool.poetry.dev-dependencies]
pytest = "^8.0.0"
pytest-asyncio = "^0.24.0"
pytest-cov = "^6.0.0"
httpx = "^0.28.0"                 # Async HTTP client for testing
ruff = "^0.8.0"                   # Linter
black = "^24.0.0"                 # Formatter
mypy = "^1.0.0"                   # Type checker
pytest-mock = "^3.14.0"           # Mocking
```

### Design Decisions

**Decision 1: PostgreSQL vs NoSQL**

Context: Need to store structured communication logs, meeting data, and decisions.

Options:
- A) MongoDB (document storage, flexible schema)
- B) PostgreSQL (relational, strict schema)
- C) Hybrid (PostgreSQL + document store)

Decision: Option B - PostgreSQL

Rationale:
- Structured relationships (meetings -> participants -> messages -> decisions)
- Strong consistency guarantees
- ACID transactions for meeting integrity
- Mature async driver (asyncpg)
- Better query capabilities for filtering

Trade-offs:
- Less flexible schema evolution
- May need partitioning for high volume

**Decision 2: Sequential vs Parallel Discussion**

Context: User requirements specified sequential discussion.

Options:
- A) Sequential (one agent speaks at a time)
- B) Parallel (all agents can speak simultaneously)
- C) Hybrid (structured phases)

Decision: Option A - Sequential (as per requirements)

Rationale:
- Clear structure for AI-to-AI discussion
- Prevents race conditions
- Easier to track conversation flow
- Better for consensus building

Trade-offs:
- Slower overall discussion time
- May feel artificial for some use cases

**Decision 3: WebSocket vs HTTP for Meeting Events**

Context: Real-time meeting events need to be delivered to participants.

Options:
- A) HTTP long polling
- B) WebSocket
- C) Server-Sent Events (SSE)

Decision: Option B - WebSocket

Rationale:
- Bidirectional communication (agents need to send opinions)
- Lower latency than HTTP polling
- Native support in FastAPI
- Better for real-time collaboration

Trade-offs:
- More complex state management
- Need connection handling for reconnections

---

## Component Design

### Communication Service

**Responsibilities**:
- Log messages between agents
- Query communications with filters
- Link communications to decisions

**Key Methods**:
```python
class CommunicationService:
    async def log_communication(
        self,
        sender_id: UUID,
        receiver_id: UUID,
        message_content: str,
        topic: str | None = None
    ) -> Communication
    async def query_communications(
        self,
        filters: CommunicationQueryFilters
    ) -> PaginatedResult[Communication]
    async def get_communications_by_topic(
        self,
        topic: str,
        limit: int = 100
    ) -> list[Communication]
```

**Data Model**:
```python
class Communication(BaseModel):
    id: UUID
    timestamp: datetime
    sender_id: UUID
    receiver_id: UUID
    message_content: str
    topic: str | None
```

### Meeting Service

**Responsibilities**:
- Create meetings with participants
- Manage meeting lifecycle (pending -> in_progress -> completed)
- Track meeting status and rounds
- Link to decisions

**Key Methods**:
```python
class MeetingService:
    async def create_meeting(
        self,
        topic: str,
        meeting_type: MeetingType,
        participant_ids: list[UUID],
        max_rounds: int = 3
    ) -> Meeting
    async def start_meeting(self, meeting_id: UUID) -> None
    async def join_meeting(
        self,
        meeting_id: UUID,
        agent_id: UUID
    ) -> MeetingParticipant
    async def get_meeting(self, meeting_id: UUID) -> MeetingDetail
    async def complete_meeting(
        self,
        meeting_id: UUID,
        status: MeetingStatus = MeetingStatus.COMPLETED
    ) -> None
```

**Data Model**:
```python
class Meeting(BaseModel):
    id: UUID
    topic: str
    meeting_type: MeetingType
    status: MeetingStatus
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    max_discussion_rounds: int
    current_round: int
```

### Sequential Discussion Algorithm

**Responsibilities**:
- Coordinate speaking order
- Facilitate opinion collection
- Manage consensus phase
- Track discussion rounds

**Key Methods**:
```python
class SequentialDiscussionAlgorithm:
    async def start_discussion(
        self,
        meeting_id: UUID
    ) -> AsyncIterator[DiscussionEvent]
    async def collect_opinions(
        self,
        meeting_id: UUID,
        round_num: int
    ) -> list[Opinion]
    async def facilitate_consensus(
        self,
        meeting_id: UUID,
        opinions: list[Opinion]
    ) -> ConsensusResult
    async def should_continue_discussion(
        self,
        meeting_id: UUID
    ) -> bool
```

**Data Model**:
```python
class Opinion(BaseModel):
    agent_id: UUID
    content: str
    timestamp: datetime
    sequence_number: int

class ConsensusResult(BaseModel):
    consensus_reached: bool
    agreements: list[bool]
    final_decision: str | None
```

### Topic Analyzer Service

**Responsibilities**:
- Analyze communication logs for topics
- Suggest meeting topics
- Rank topics by priority

**Key Methods**:
```python
class TopicAnalyzer:
    async def analyze_logs_for_topics(
        self,
        hours_back: int = 24
    ) -> list[SuggestedTopic]
    async def detect_conflicts(
        self,
        communications: list[Communication]
    ) -> list[str]
    async def rank_topics(
        self,
        topics: list[str]
    ) -> list[SuggestedTopic]
```

**Data Model**:
```python
class SuggestedTopic(BaseModel):
    topic: str
    priority: float
    reason: str
    related_communications: list[UUID]
```

### WebSocket Manager

**Responsibilities**:
- Manage active WebSocket connections
- Broadcast meeting events
- Handle connection lifecycle
- Route messages to handlers

**Key Methods**:
```python
class WebSocketManager:
    async def connect(
        self,
        websocket: WebSocket,
        meeting_id: UUID,
        agent_id: UUID
    ) -> None
    async def disconnect(
        self,
        meeting_id: UUID,
        agent_id: UUID
    ) -> None
    async def send_to_agent(
        self,
        agent_id: UUID,
        message: dict
    ) -> None
    async def broadcast_to_meeting(
        self,
        meeting_id: UUID,
        message: dict,
        exclude_agent: UUID | None = None
    ) -> None
    async def get_connected_agents(
        self,
        meeting_id: UUID
    ) -> list[UUID]
```

---

## Risk Analysis and Mitigation

### Technical Risks

| Risk | Probability | Impact | Mitigation Strategy |
|------|-------------|--------|---------------------|
| WebSocket state management complexity | High | Medium | Implement robust state machine; use connection IDs; handle reconnections |
| Database performance under high message volume | Medium | High | Implement connection pooling; add indexes; consider partitioning |
| Race conditions in sequential discussion | Medium | High | Use database locks for meeting state; implement proper queue |
| PostgreSQL connection exhaustion | Low | High | Configure connection pool limits; implement health checks |
| WebSocket memory leak with long-lived connections | Medium | Medium | Implement connection timeouts; periodic cleanup |

### Operational Risks

| Risk | Probability | Impact | Mitigation Strategy |
|------|-------------|--------|---------------------|
| Meeting deadlock (no consensus after max rounds) | Medium | Low | Configurable max rounds; record no-consensus outcome |
| Agent disconnection during meeting | High | Medium | Graceful reconnection; state recovery; timeout handling |
| Database migration failures | Low | High | Version-controlled migrations; rollback capability |

---

## Testing Strategy

### Unit Tests

**Coverage Target**: >= 85%

**Test Categories**:
1. Communication logging tests
2. Meeting lifecycle tests
3. Sequential discussion algorithm tests
4. Topic analyzer tests
5. Repository layer tests

**Example Test**:
```python
@pytest.mark.asyncio
async def test_log_communication():
    service = CommunicationService(db_session)
    comm = await service.log_communication(
        sender_id=uuid4(),
        receiver_id=uuid4(),
        message_content="Test message",
        topic="test"
    )
    assert comm.id is not None
    assert comm.message_content == "Test message"
```

### Integration Tests

**Coverage**: All API endpoints, WebSocket flows

**Test Scenarios**:
1. Log communication -> Query communication
2. Create meeting -> Join meeting -> Start discussion
3. Sequential discussion flow (one round)
4. Multi-round discussion with consensus
5. WebSocket connection lifecycle
6. Topic generation from logs

### Load Tests

**Tools**: Locust or pytest-asyncio

**Test Scenarios**:
1. 20 concurrent WebSocket connections
2. 100 messages/second logging rate
3. 5 simultaneous meetings
4. Reconnection churn

**Acceptance Criteria**:
- P50 latency < 100ms
- P95 latency < 200ms
- Zero message loss

---

## Development Workflow

### Phase 1: Foundation (Primary Goal)

1. **Setup Project**
   - Create directory structure
   - Configure pyproject.toml
   - Setup pre-commit hooks

2. **Database Setup**
   - Create database schema
   - Setup Alembic migrations
   - Create base repository class

3. **Implement Communication Logging**
   - Communication model and repository
   - Communication service
   - API endpoints (POST, GET)
   - Unit tests

4. **Implement Meeting Management**
   - Meeting model and repository
   - Meeting service
   - API endpoints
   - Unit tests

5. **Implement WebSocket Server**
   - WebSocket manager
   - Connection handling
   - Basic event broadcasting
   - Unit tests

6. **Implement Sequential Discussion**
   - Discussion algorithm service
   - Opinion collection
   - Basic consensus phase
   - Unit tests

7. **Implement Decision Recording**
   - Decision model and repository
   - Decision service
   - Link decisions to communications
   - Unit tests

8. **Quality Gates**
   - TRUST 5 validation
   - Coverage report
   - Documentation

### Phase 2: Enhanced Features (Secondary Goal)

1. **Topic Analyzer**
   - Log analysis algorithms
   - Topic suggestion
   - Priority ranking

2. **Multi-Round Discussion**
   - Round tracking
   - Enhanced consensus
   - Meeting state management

3. **Enhanced WebSocket**
   - Event types
   - Broadcasting improvements
   - Reconnection handling

4. **Integration Testing**
   - End-to-end scenarios
   - WebSocket flow tests

### Phase 3: Production Hardening (Final Goal)

1. **Performance Optimization**
   - Connection pooling
   - Query optimization
   - Index tuning

2. **Security**
   - Authentication middleware
   - Input validation audit
   - SQL injection prevention

3. **Deployment**
   - Docker image
   - Docker Compose for development
   - Production configuration

---

## Success Criteria

### Functional Requirements

- [ ] All API endpoints functional
- [ ] Communication logging working
- [ ] Meeting creation and management complete
- [ ] Sequential discussion algorithm working
- [ ] Decision recording with links
- [ ] WebSocket connections stable

### Quality Requirements

- [ ] Unit test coverage >= 85%
- [ ] All integration tests passing
- [ ] Load test passes (20+ concurrent WebSocket)
- [ ] Zero ruff lint errors
- [ ] Zero mypy type errors

### Documentation Requirements

- [ ] README with quick start
- [ ] API documentation
- [ ] Architecture diagram
- [ ] Deployment guide

---

## Next Steps

1. **Execute `/moai:2-run SPEC-AGENT-COMM-001`** to begin implementation
2. **Review acceptance criteria** in `acceptance.md`
3. **Setup development environment** with Docker Compose
4. **Implement Primary Goal** components in order
5. **Validate quality gates** before proceeding to Secondary Goal

---

**END OF PLAN - SPEC-AGENT-COMM-001**
