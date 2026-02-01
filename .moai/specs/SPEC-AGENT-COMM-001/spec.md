# SPEC-AGENT-COMM-001: AI Agent Communication & Meeting System

## TAG BLOCK

```yaml
SPEC_ID: SPEC-AGENT-COMM-001
TITLE: AI Agent Communication & Meeting System - Inter-Agent Collaboration with Database Storage
STATUS: Planned
PRIORITY: High
DOMAIN: AGENT-COMM
VERSION: 1.0.0
CREATED: 2026-02-01
ASSIGNED: manager-ddd
TRACEABILITY:
  - PLAN: .moai/specs/SPEC-AGENT-COMM-001/plan.md
  - ACCEPTANCE: .moai/specs/SPEC-AGENT-COMM-001/acceptance.md
```

---

## Environment

### System Context

The AI Agent Communication & Meeting System is a server-based platform that enables multiple Claude Code instances (agents) to communicate with each other, conduct AI-to-AI meetings to make decisions, and store all logs and meeting outcomes in a database. The system acts as a collaboration layer for autonomous AI agents, providing both real-time communication and structured decision-making capabilities.

### Technical Environment

- **Language**: Python 3.13+
- **Web Framework**: FastAPI 0.115+ for REST API and WebSocket support
- **Database**: PostgreSQL with asyncpg driver for async database operations
- **WebSocket**: Real-time bidirectional communication for agent meetings
- **Data Validation**: Pydantic v2.9+ for schema validation
- **Async Runtime**: asyncio with async/await patterns
- **ORM**: SQLAlchemy 2.0 with async support for database operations

### Deployment Environment

- **Development**: Local development with Docker Compose (PostgreSQL container)
- **Production**: Containerized deployment with PostgreSQL cluster
- **Network**: HTTP/HTTPS for REST API, WebSocket for real-time meetings

---

## Assumptions

### Technical Assumptions

| Assumption | Confidence | Evidence Basis | Risk if Wrong | Validation Method |
|------------|------------|----------------|---------------|-------------------|
| FastAPI WebSocket can handle concurrent agent connections | High | FastAPI WebSocket is production-proven | Medium - May need connection pooling | Load testing with 20+ concurrent agents |
| PostgreSQL with asyncpg supports async operations efficiently | High | asyncpg is the fastest PostgreSQL driver for Python | Low - Well-established technology | Performance testing with concurrent queries |
| Sequential discussion can be implemented with WebSocket state machine | Medium | WebSocket maintains session state per connection | Medium - State complexity may increase | Prototype sequential discussion flow |
| Agent participants can be identified by unique agent IDs | High | Standard UUID identification pattern | Low - Industry standard practice | Test with multiple agent types |
| Database schema can handle communication log volume | Medium | Depends on message frequency and retention | High - May require partitioning/archival | Capacity planning and stress testing |

### Business Assumptions

| Assumption | Confidence | Evidence Basis | Risk if Wrong | Validation Method |
|------------|------------|----------------|---------------|-------------------|
| Multiple agents need to make decisions through structured meetings | High | User requirements indicate collaborative decision-making | Low - Core use case | User survey/interview |
| Historical logs are valuable for context in meetings | High | Logs provide conversation history for AI context | Medium - Storage costs may be high | Define retention policies |
| User-specified and auto-generated meeting topics are both needed | Medium | Flexibility for different use cases | Low - Covers more scenarios | Prototype both topic selection methods |
| Sequential discussion is preferred over parallel conversation | Medium | User specified this requirement | Medium - May need hybrid approach | User feedback on prototype |

### Root Cause Analysis (Five Whys)

1. **Surface Problem**: Claude Code instances cannot collaborate or make decisions together
2. **First Why**: No communication channel exists between agent instances
3. **Second Why**: No central system to coordinate multi-agent discussions
4. **Third Why**: No structured mechanism for AI-to-AI decision-making meetings
5. **Root Cause**: Current tools focus on human-AI interaction, not AI-AI collaboration

**Solution Approach**: Build a server-based system with real-time communication, structured meeting protocols, and database storage for collaboration history and decision tracking.

---

## Requirements (EARS Format)

### 1. Communication Logging Requirements

**UBIQUITOUS**: The system SHALL log all messages exchanged between Claude Code instances with timestamp, sender, receiver, and content.

**WHEN** an agent sends a message to another agent, **THEN** the system SHALL store the message in the communications table with metadata (timestamp, sender_id, receiver_id, message_content).

**IF** a message exceeds the maximum size limit (configurable, default 10MB), **THEN** the system SHALL reject the message with an error indicating the size limit.

**WHILE** the system is operational, **THEN** the system SHALL provide query capabilities for logs by date range, agent ID, and topic.

**WHERE** message content includes structured data, **THEN** the system SHALL preserve the data structure for later retrieval and analysis.

**THE SYSTEM SHALL NOT** modify message content during storage; messages SHALL be stored exactly as received.

### 2. AI Meeting System Requirements

**UBIQUITOUS**: The system SHALL support AI-to-AI meetings where agents discuss topics and reach decisions through sequential discussion.

**WHEN** a meeting is initiated (by user request OR automatic log analysis), **THEN** the system SHALL create a meeting record with unique ID, topic, participant list, and start timestamp.

**IF** meeting topic is auto-generated from log analysis, **THEN** the system SHALL analyze recent communication logs to identify topics requiring discussion and suggest meeting agenda.

**WHILE** a meeting is in progress, **THEN** the system SHALL facilitate sequential discussion where each agent presents opinions in turn: Agent A -> Agent B -> Agent C -> Consensus Phase.

**WHEN** an agent presents an opinion during a meeting, **THEN** the system SHALL record the opinion with agent_id, timestamp, content, and reference to relevant context logs.

**IF** consensus is reached, **THEN** the system SHALL record the final decision with rationale, participating agents, and decision timestamp.

**THE SYSTEM SHALL NOT** allow parallel discussion; agents SHALL speak one at a time in the defined sequence.

### 3. Meeting Topic Selection Requirements

**UBIQUITOUS**: The system SHALL support both user-specified and auto-generated meeting topics.

**WHEN** a user specifies a meeting topic, **THEN** the system SHALL create a meeting with the exact topic provided by the user.

**IF** no topic is specified by the user, **THEN** the system SHALL analyze recent communication logs to generate potential topics using frequency analysis and conflict detection.

**WHILE** analyzing logs for topic generation, **THEN** the system SHALL identify patterns such as repeated disagreements, unresolved questions, or coordination needs.

**WHERE** multiple topics are identified, **THEN** the system SHALL rank topics by priority (frequency, urgency, number of affected agents) and present to user for selection.

**THE SYSTEM SHALL NOT** automatically initiate meetings without user confirmation; generated topics SHALL require user approval.

### 4. Sequential Discussion Algorithm Requirements

**UBIQUITOUS**: The system SHALL implement a sequential discussion flow where agents present opinions in a predefined order.

**WHEN** a meeting begins, **THEN** the system SHALL determine the speaking order based on participant list and shuffle participants if configured for randomization.

**IF** it is an agent's turn to speak, **THEN** the system SHALL send a WebSocket message to that agent requesting their opinion on the current topic.

**WHILE** waiting for an agent's response, **THEN** the system SHALL enforce a timeout period (configurable, default 5 minutes) before moving to the next agent or marking as no-response.

**WHEN** all agents have presented their opinions, **THEN** the system SHALL enter the consensus phase where agents review each other's opinions and vote or agree on a final decision.

**IF** consensus is not reached after one full round, **THEN** the system MAY facilitate additional discussion rounds with a configurable maximum (default 3 rounds).

**THE SYSTEM SHALL NOT** allow agents to speak out of turn or interrupt other agents during the discussion.

### 5. Decision Tracking Requirements

**UBIQUITOUS**: The system SHALL track all meeting outcomes and decisions with links to original communication logs that prompted the meeting.

**WHEN** a meeting concludes with a decision, **THEN** the system SHALL store the decision in the decisions table with meeting_id, decision_content, rationale, and participant agreement status.

**IF** a meeting ends without a decision (deadlock or timeout), **THEN** the system SHALL record the outcome as "no_consensus" with summary of discussion points.

**WHILE** storing a decision, **THEN** the system SHALL link the decision to relevant communication logs that provided context for the meeting.

**WHERE** a decision impacts future communication, **THEN** the system SHALL update communication tags or metadata to reflect the decision context.

**THE SYSTEM SHALL NOT** delete or modify historical decisions; all decisions SHALL be immutable with timestamp and participant record.

### 6. Database Schema Requirements

**UBIQUITOUS**: The system SHALL maintain a PostgreSQL database with the following tables: communications, meetings, meeting_participants, meeting_messages, and decisions.

**communications Table**:
- **WHEN** a message is logged, **THEN** the system SHALL insert a record with id (UUID), timestamp (timestamptz), sender_id (UUID), receiver_id (UUID), message_content (TEXT), and topic (VARCHAR).
- **IF** message_content exceeds TEXT limits, **THEN** the system SHALL store large content separately with reference.

**meetings Table**:
- **WHEN** a meeting is created, **THEN** the system SHALL insert a record with id (UUID), topic (VARCHAR), meeting_type (ENUM: 'user_specified', 'auto_generated'), status (ENUM: 'pending', 'in_progress', 'completed', 'failed'), created_at (timestamptz), started_at (timestamptz, nullable), completed_at (timestamptz, nullable).

**meeting_participants Table**:
- **WHEN** an agent joins a meeting, **THEN** the system SHALL insert a record with id (UUID), meeting_id (UUID foreign key), agent_id (UUID), joined_at (timestamptz), role (VARCHAR: 'moderator', 'participant').

**meeting_messages Table**:
- **WHEN** an agent speaks during a meeting, **THEN** the system SHALL insert a record with id (UUID), meeting_id (UUID foreign key), agent_id (UUID), message_content (TEXT), sequence_number (INT), message_type (ENUM: 'opinion', 'consensus', 'meta'), timestamp (timestamptz).

**decisions Table**:
- **WHEN** a decision is reached, **THEN** the system SHALL insert a record with id (UUID), meeting_id (UUID foreign key), decision_content (TEXT), rationale (TEXT), related_communication_ids (UUID[]), participant_agreement (JSONB), created_at (timestamptz).

### 7. Real-Time Communication Requirements

**UBIQUITOUS**: The system SHALL support WebSocket connections for real-time agent communication and meeting participation.

**WHEN** an agent connects via WebSocket, **THEN** the system SHALL authenticate the agent using agent_id and optionally an API token, and maintain the connection state.

**IF** an agent's WebSocket connection drops during a meeting, **THEN** the system SHALL mark the agent as disconnected and continue the meeting; the agent MAY reconnect and resume participation.

**WHILE** a meeting is active, **THEN** the system SHALL broadcast meeting events (agent joined, opinion presented, consensus reached) to all connected participants via WebSocket.

**WHERE** an agent needs to send a message outside of a meeting, **THEN** the system SHALL support direct agent-to-agent messaging via WebSocket with immediate delivery confirmation.

**THE SYSTEM SHALL NOT** allow anonymous WebSocket connections; all connections SHALL require valid agent identification.

### 8. API Endpoint Requirements

**UBIQUITOUS**: The system SHALL expose REST API endpoints for all major operations.

**POST /api/v1/communications**:
- **WHEN** called with sender_id, receiver_id, message_content, and optional topic, **THEN** the system SHALL log the communication and return the communication record with ID and timestamp.

**GET /api/v1/communications**:
- **WHEN** called with query parameters (start_date, end_date, sender_id, receiver_id, topic), **THEN** the system SHALL return filtered communication logs with pagination.

**POST /api/v1/meetings**:
- **WHEN** called with topic and participant list, **THEN** the system SHALL create a meeting and return the meeting record with ID and status.

**GET /api/v1/meetings/{meeting_id}**:
- **WHEN** called with a valid meeting_id, **THEN** the system SHALL return the meeting details including participants, messages, and decision (if any).

**POST /api/v1/meetings/{meeting_id}/join**:
- **WHEN** called by an agent with agent_id, **THEN** the system SHALL add the agent to meeting participants and establish WebSocket connection for meeting events.

**GET /api/v1/decisions**:
- **WHEN** called with optional filters (meeting_id, date_range), **THEN** the system SHALL return decisions with links to related meetings and communications.

**THE SYSTEM SHALL NOT** allow API operations without proper authentication; all endpoints SHALL require API token or agent identification.

### 9. Quality and Performance Requirements

**UBIQUITOUS**: The system SHALL log all operations with structured logging for debugging and monitoring.

**WHEN** processing API requests, **THEN** the system SHALL respond within 200ms for database queries and 100ms for cache hits (if caching is implemented).

**IF** database query performance degrades, **THEN** the system SHALL log slow queries and implement query optimization or indexing.

**WHILE** handling WebSocket connections, **THEN** the system SHALL support at least 20 concurrent agent connections without performance degradation.

**WHERE** message volume is high, **THEN** the system SHALL implement database connection pooling with a configurable pool size (default 10 connections).

**THE SYSTEM SHALL NOT** lose messages due to system failure; all operations SHALL use database transactions with appropriate isolation levels.

### 10. Security Requirements

**UBIQUITOUS**: The system SHALL validate all input parameters through Pydantic schemas before processing.

**WHEN** an agent connects or makes an API request, **THEN** the system SHALL authenticate using API token or agent credentials.

**IF** authentication fails, **THEN** the system SHALL return a generic authentication failure without revealing whether the agent ID or token was invalid.

**WHILE** processing messages or meeting content, **THEN** the system SHALL sanitize input to prevent SQL injection and enforce maximum size limits.

**WHERE** sensitive data is logged, **THEN** the system SHALL redact API tokens and passwords from log output.

**THE SYSTEM SHALL NOT** allow unauthorized access to communication logs or meeting records; access control SHALL be enforced per agent.

---

## Specifications

### Component Architecture

```
+-----------------------------------------------------------------------+
|                  AI Agent Communication & Meeting System              |
+-----------------------------------------------------------------------+
|                                                                       |
|  +------------------+  +------------------+  +------------------+    |
|  |  REST API        |  |  WebSocket       |  |  Meeting         |    |
|  |  Interface       |  |  Server          |  |  Coordinator     |    |
|  |                  |  |                  |  |                  |    |
|  | • POST /comm     |  | • Agent connect  |  | • Sequential     |    |
|  | • GET /comm      |  | • Direct msg     |  |   discussion     |    |
|  | • POST /meetings |  | • Meeting events |  | • Consensus      |    |
|  | • GET /meetings  |  | • Broadcast      |  |   tracking       |    |
|  | • GET /decisions |  |                  |  | • Topic analysis |    |
|  +------------------+  +------------------+  +------------------+    |
|           |                     |                     |              |
|           +---------------------+---------------------+              |
|                                 |                                    |
|                        +--------▼--------+                           |
|                        |  Service Layer   |                           |
|                        |                 |                           |
|                        | • Communication |                           |
|                        |   Service       |                           |
|                        | • Meeting       |                           |
|                        |   Service       |                           |
|                        | • Decision      |                           |
|                        |   Service       |                           |
|                        | • Agent         |                           |
|                        |   Service       |                           |
|                        +--------+--------+                           |
|                                 |                                    |
|                        +--------▼--------+                           |
|                        |  Repository     |                           |
|                        |  Layer          |                           |
|                        |                 |                           |
|                        | • Communication |                           |
|                        |   Repository    |                           |
|                        | • Meeting       |                           |
|                        |   Repository    |                           |
|                        | • Decision      |                           |
|                        |   Repository    |                           |
|                        +--------+--------+                           |
|                                 |                                    |
|                        +--------▼--------+                           |
|                        |  PostgreSQL      |                           |
|                        |  Database        |                           |
|                        |                  |                           |
|                        | • communications |                           |
|                        | • meetings       |                           |
|                        | • meeting_       |                           |
|                        |   participants  |                           |
|                        | • meeting_       |                           |
|                        |   messages      |                           |
|                        | • decisions      |                           |
|                        +-----------------+                           |
+-----------------------------------------------------------------------+
                                 |
        +------------------------+------------------------+
        |                        |                        |
+-------V--------+      +--------V--------+      +--------V--------+
| Claude Code     |      | Claude Code     |      | Claude Code     |
| Instance A      |      | Instance B      |      | Instance C      |
| (Agent)         |      | (Agent)         |      | (Agent)         |
+-----------------+      +-----------------+      +-----------------+
```

### Data Model Specifications

#### Communication Log Schema (communications table)

```sql
CREATE TABLE communications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    sender_id UUID NOT NULL,
    receiver_id UUID NOT NULL,
    message_content TEXT NOT NULL,
    topic VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT idx_communications_timestamp INDEX (timestamp),
    CONSTRAINT idx_communications_sender INDEX (sender_id),
    CONSTRAINT idx_communications_receiver INDEX (receiver_id),
    CONSTRAINT idx_communications_topic INDEX (topic)
);

COMMENT ON TABLE communications IS 'Logs of all messages exchanged between agents';
```

#### Meeting Schema (meetings table)

```sql
CREATE TYPE meeting_status AS ENUM ('pending', 'in_progress', 'completed', 'failed');
CREATE TYPE meeting_type AS ENUM ('user_specified', 'auto_generated');

CREATE TABLE meetings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    topic VARCHAR(500) NOT NULL,
    meeting_type meeting_type NOT NULL,
    status meeting_status NOT NULL DEFAULT 'pending',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    max_discussion_rounds INT NOT NULL DEFAULT 3,
    current_round INT NOT NULL DEFAULT 0,

    CONSTRAINT idx_meetings_status INDEX (status),
    CONSTRAINT idx_meetings_created_at INDEX (created_at)
);

COMMENT ON TABLE meetings IS 'AI-to-AI meetings for decision making';
```

#### Meeting Participant Schema (meeting_participants table)

```sql
CREATE TABLE meeting_participants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    meeting_id UUID NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
    agent_id UUID NOT NULL,
    joined_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    role VARCHAR(50) NOT NULL DEFAULT 'participant', -- 'moderator' or 'participant'
    speaking_order INT,

    CONSTRAINT idx_meeting_participants_meeting INDEX (meeting_id),
    CONSTRAINT idx_meeting_participants_agent INDEX (agent_id),
    CONSTRAINT uq_meeting_agent UNIQUE (meeting_id, agent_id)
);

COMMENT ON TABLE meeting_participants IS 'Agents participating in meetings';
```

#### Meeting Message Schema (meeting_messages table)

```sql
CREATE TYPE message_type AS ENUM ('opinion', 'consensus', 'meta');

CREATE TABLE meeting_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    meeting_id UUID NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
    agent_id UUID NOT NULL,
    message_content TEXT NOT NULL,
    sequence_number INT NOT NULL,
    message_type message_type NOT NULL DEFAULT 'opinion',
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT idx_meeting_messages_meeting INDEX (meeting_id),
    CONSTRAINT idx_meeting_messages_sequence UNIQUE (meeting_id, sequence_number)
);

COMMENT ON TABLE meeting_messages IS 'Messages exchanged during meetings';
```

#### Decision Schema (decisions table)

```sql
CREATE TABLE decisions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    meeting_id UUID NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
    decision_content TEXT NOT NULL,
    rationale TEXT,
    related_communication_ids UUID[] DEFAULT '{}',
    participant_agreement JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT idx_decisions_meeting INDEX (meeting_id),
    CONSTRAINT idx_decisions_created_at INDEX (created_at)
);

COMMENT ON TABLE decisions IS 'Decisions reached during meetings';
```

### Sequential Discussion Algorithm

```python
class SequentialDiscussionAlgorithm:
    """
    Implements sequential discussion flow for AI-to-AI meetings.

    Flow:
    1. Initialize meeting with participants and speaking order
    2. For each discussion round:
       a. For each participant in speaking order:
          - Send topic prompt via WebSocket
          - Wait for response (with timeout)
          - Record opinion in meeting_messages
       b. Enter consensus phase:
          - Broadcast all opinions to participants
          - Request consensus vote/agreement
          - Record consensus or disagreement
    3. If consensus reached: Record decision and end meeting
    4. If no consensus and rounds < max: Start next round
    5. If no consensus after max rounds: End with no_consensus status
    """

    async def start_meeting(self, meeting_id: UUID) -> None:
        """Initialize meeting and determine speaking order."""
        participants = await self.get_participants(meeting_id)
        speaking_order = self.determine_speaking_order(participants)
        await self.update_meeting_status(meeting_id, "in_progress")

    async def run_discussion_round(self, meeting_id: UUID, round_num: int) -> bool:
        """Run one round of sequential discussion. Returns True if consensus reached."""
        participants = await self.get_participants_ordered(meeting_id)
        opinions = []

        for participant in participants:
            # Send prompt via WebSocket
            await self.send_websocket_message(
                participant.agent_id,
                {
                    "type": "opinion_request",
                    "meeting_id": str(meeting_id),
                    "round": round_num,
                    "topic": await self.get_meeting_topic(meeting_id)
                }
            )

            # Wait for response with timeout
            opinion = await self.wait_for_opinion(
                participant.agent_id,
                timeout=300  # 5 minutes
            )

            if opinion:
                await self.record_meeting_message(
                    meeting_id,
                    participant.agent_id,
                    opinion,
                    "opinion",
                    round_num
                )
                opinions.append(opinion)

        # Consensus phase
        consensus = await self.facilitate_consensus(meeting_id, opinions)
        return consensus

    async def facilitate_consensus(self, meeting_id: UUID, opinions: list) -> bool:
        """Facilitate consensus phase after opinions are collected."""
        # Broadcast all opinions to participants
        for participant in await self.get_participants(meeting_id):
            await self.send_websocket_message(
                participant.agent_id,
                {
                    "type": "consensus_request",
                    "meeting_id": str(meeting_id),
                    "opinions": opinions
                }
            )

        # Wait for consensus agreements
        agreements = []
        for participant in await self.get_participants(meeting_id):
            agreement = await self.wait_for_consensus_vote(
                participant.agent_id,
                timeout=180  # 3 minutes
            )
            agreements.append(agreement)

        # Check if all agree
        consensus_reached = all(agreements)
        await self.record_meeting_message(
            meeting_id,
            None,  # System message
            f"Consensus {'reached' if consensus_reached else 'not reached'}",
            "consensus"
        )

        return consensus_reached
```

### API Endpoint Specifications

#### POST /api/v1/communications

**Description**: Log a communication between agents

**Request Body**:
```json
{
  "sender_id": "uuid",
  "receiver_id": "uuid",
  "message_content": "string",
  "topic": "string (optional)"
}
```

**Response** (201 Created):
```json
{
  "id": "uuid",
  "timestamp": "2026-02-01T10:00:00Z",
  "sender_id": "uuid",
  "receiver_id": "uuid",
  "message_content": "string",
  "topic": "string"
}
```

#### GET /api/v1/communications

**Description**: Query communication logs with filters

**Query Parameters**:
- `start_date` (optional): ISO 8601 timestamp
- `end_date` (optional): ISO 8601 timestamp
- `sender_id` (optional): UUID
- `receiver_id` (optional): UUID
- `topic` (optional): string
- `page` (optional): int, default 1
- `page_size` (optional): int, default 50

**Response** (200 OK):
```json
{
  "communications": [
    {
      "id": "uuid",
      "timestamp": "2026-02-01T10:00:00Z",
      "sender_id": "uuid",
      "receiver_id": "uuid",
      "message_content": "string",
      "topic": "string"
    }
  ],
  "total": 100,
  "page": 1,
  "page_size": 50
}
```

#### POST /api/v1/meetings

**Description**: Create a new meeting

**Request Body**:
```json
{
  "topic": "string",
  "meeting_type": "user_specified | auto_generated",
  "participant_ids": ["uuid", "uuid"],
  "max_discussion_rounds": 3
}
```

**Response** (201 Created):
```json
{
  "id": "uuid",
  "topic": "string",
  "meeting_type": "user_specified",
  "status": "pending",
  "created_at": "2026-02-01T10:00:00Z",
  "participant_ids": ["uuid", "uuid"]
}
```

#### GET /api/v1/meetings/{meeting_id}

**Description**: Get meeting details including participants, messages, and decision

**Response** (200 OK):
```json
{
  "id": "uuid",
  "topic": "string",
  "meeting_type": "user_specified",
  "status": "completed",
  "created_at": "2026-02-01T10:00:00Z",
  "started_at": "2026-02-01T10:05:00Z",
  "completed_at": "2026-02-01T10:20:00Z",
  "participants": [
    {
      "agent_id": "uuid",
      "role": "participant",
      "joined_at": "2026-02-01T10:05:00Z"
    }
  ],
  "messages": [
    {
      "agent_id": "uuid",
      "content": "string",
      "sequence_number": 1,
      "message_type": "opinion",
      "timestamp": "2026-02-01T10:06:00Z"
    }
  ],
  "decision": {
    "decision_content": "string",
    "rationale": "string",
    "created_at": "2026-02-01T10:20:00Z"
  }
}
```

#### WebSocket Connection

**Endpoint**: `ws://localhost:8000/ws/meetings/{meeting_id}?agent_id={uuid}`

**Events**:

**Client -> Server**:
```json
{
  "type": "opinion",
  "meeting_id": "uuid",
  "agent_id": "uuid",
  "content": "string"
}
```

```json
{
  "type": "consensus_vote",
  "meeting_id": "uuid",
  "agent_id": "uuid",
  "agrees": true
}
```

**Server -> Client**:
```json
{
  "type": "opinion_request",
  "meeting_id": "uuid",
  "round": 1,
  "topic": "string"
}
```

```json
{
  "type": "consensus_request",
  "meeting_id": "uuid",
  "opinions": [
    {"agent_id": "uuid", "content": "string"}
  ]
}
```

```json
{
  "type": "meeting_event",
  "event": "agent_joined | agent_left | opinion_presented | consensus_reached",
  "meeting_id": "uuid",
  "data": {}
}
```

---

## Traceability

### Requirement to Component Mapping

| Requirement Category | Component | Traceability ID |
|---------------------|-----------|-----------------|
| Communication Logging | CommunicationService | REQ-COMM-001 |
| AI Meeting System | MeetingCoordinator | REQ-MEET-001 |
| Topic Selection | TopicAnalyzer | REQ-TOPIC-001 |
| Sequential Discussion | SequentialDiscussionAlgorithm | REQ-DISCUSS-001 |
| Decision Tracking | DecisionService | REQ-DECISION-001 |
| Database Schema | Database Layer | REQ-DB-001 |
| Real-Time Communication | WebSocketServer | REQ-WS-001 |
| API Endpoints | RESTAPI | REQ-API-001 |
| Quality and Performance | All Components | REQ-PERF-001 |
| Security | All Components | REQ-SEC-001 |

### Acceptance Criteria Reference

See `.moai/specs/SPEC-AGENT-COMM-001/acceptance.md` for detailed acceptance criteria in Given-When-Then format.

### Implementation Plan Reference

See `.moai/specs/SPEC-AGENT-COMM-001/plan.md` for implementation milestones and technical approach.

---

## Dependencies

### External Dependencies

- **fastapi** >= 0.115.0 - Web framework for REST API and WebSocket
- **uvicorn** >= 0.32.0 - ASGI server
- **pydantic** >= 2.9.0 - Data validation
- **sqlalchemy** >= 2.0.0 - Async ORM
- **asyncpg** >= 0.30.0 - Async PostgreSQL driver
- **python-dotenv** >= 1.0.0 - Configuration management

### Internal Dependencies

- None (standalone system)

### System Dependencies

- Python 3.13+
- PostgreSQL 15+ (for database)
- Docker/Podman (for containerized deployment)

---

## Constraints

### Technical Constraints

- MUST use Python 3.13+ async patterns
- MUST support PostgreSQL with asyncpg for database operations
- MUST NOT use synchronous database operations in main request handlers
- MUST maintain backward compatibility within major version

### Business Constraints

- Initial release MUST support at least 20 concurrent WebSocket connections
- Message logging latency MUST be under 200ms for database writes
- Meeting coordinator MUST handle sequential discussion without race conditions

### Security Constraints

- All API endpoints MUST require authentication
- WebSocket connections MUST be authenticated
- Maximum message size of 10MB (configurable)
- SQL injection prevention through parameterized queries

---

## Quality Attributes

### TRUST 5 Framework Compliance

**Tested**:
- Unit test coverage >= 85% for all components
- Integration tests for API endpoints
- WebSocket connection testing
- Database transaction testing

**Readable**:
- Type hints on all public functions
- Docstrings following Google style
- Clear variable naming

**Unified**:
- Consistent async/await patterns
- Pydantic models for all data structures
- Structured logging with JSON format

**Secured**:
- Input validation via Pydantic
- Authentication for all operations
- SQL injection prevention
- Sensitive data redaction

**Trackable**:
- All communications logged with timestamps
- All meetings logged with full history
- All decisions linked to communications
- Structured logging for debugging

---

## Appendix

### Glossary

- **Agent**: A Claude Code instance with unique identifier
- **Communication**: A message exchanged between two agents
- **Meeting**: A structured discussion between multiple agents to reach a decision
- **Sequential Discussion**: A discussion format where agents speak one at a time in a predefined order
- **Consensus**: Agreement among all meeting participants on a decision
- **Topic**: The subject of a meeting or communication
- **Decision**: The outcome of a meeting, recorded with rationale

### References

- [FastAPI WebSocket Documentation](https://fastapi.tiangolo.com/advanced/websockets/)
- [SQLAlchemy 2.0 Async](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
- [asyncpg Documentation](https://magicstack.github.io/asyncpg/)
- [Pydantic v2 Documentation](https://docs.pydantic.dev/)

---

**END OF SPEC-AGENT-COMM-001**
