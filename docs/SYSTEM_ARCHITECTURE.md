# AI Agent Communication System - System Architecture

**Complete System Architecture Documentation**

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Architecture Diagram](#architecture-diagram)
3. [Component Details](#component-details)
4. [Communication Flows](#communication-flows)
5. [Deployment Architecture](#deployment-architecture)
6. [API Reference](#api-reference)
7. [Configuration](#configuration)
8. [Data Models](#data-models)

---

## System Overview

The AI Agent Communication System enables multiple Claude Code instances to discover each other, communicate, and collaborate through a centralized communication server.

### Key Characteristics

| Aspect | Description |
|--------|-------------|
| **Architecture** | Distributed client-server with local MCP bridges |
| **Protocol** | Model Context Protocol (MCP) + HTTP/WebSocket |
| **Language** | Python 3.13+ |
| **Database** | SQLite/PostgreSQL (Communication Server) |

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        AI Agent Communication System                        │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────┐       ┌─────────────────────┐       ┌─────────────────────┐
│   Claude Code A     │       │   Claude Code B     │       │   Claude Code C     │
│   (Local Machine)   │       │   (Local Machine)   │       │   (Local Machine)   │
└──────────┬──────────┘       └──────────┬──────────┘       └──────────┬──────────┘
           │                             │                             │
           │ stdio/MCP                   │ stdio/MCP                   │ stdio/MCP
           │                             │                             │
           ▼                             ▼                             ▼
┌─────────────────────┐       ┌─────────────────────┐       ┌─────────────────────┐
│   MCP Broker A      │       │   MCP Broker B      │       │   MCP Broker C      │
│   (Local Process)   │       │   (Local Process)   │       │   (Local Process)   │
│                     │       │                     │       │                     │
│  - Protocol Registry│       │  - Protocol Registry│       │  - Protocol Registry│
│  - Session Manager  │       │  - Session Manager  │       │  - Session Manager  │
│  - Message Router   │       │  - Message Router   │       │  - Message Router   │
│  - HTTP Client      │       │  - HTTP Client      │       │  - HTTP Client      │
└──────────┬──────────┘       └──────────┬──────────┘       └──────────┬──────────┘
           │                             │                             │
           │                             │                             │
           └─────────────────────────────┼─────────────────────────────┘
                                         │
                    ┌────────────────────┼────────────────────┐
                    │                    │                    │
                    │ HTTP/HTTPS         │ HTTP/HTTPS         │ HTTP/HTTPS
                    │ Port 8000          │ Port 8000          │ Port 8000
                    │                    │                    │
                    ▼                    ▼                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    Communication Server (Remote)                             │
│                    oci-ajou-ec2.fcoinfup.com:8000                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐               │
│  │   FastAPI      │  │   WebSocket    │  │   Dashboard    │               │
│  │   REST API     │  │   Manager      │  │   (Static UI)  │               │
│  │                │  │                │  │                │               │
│  │ /api/v1/...    │  │ /ws/meetings   │  │ /static/       │               │
│  │ /health        │  │ /ws/status     │  │ /              │               │
│  └────────────────┘  └────────────────┘  └────────────────┘               │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                       Database (SQLite/PostgreSQL)                  │   │
│  │  - Communications  - Meetings  - Decisions  - Agents  - Projects   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Component Details

### 1. Claude Code (Local)

**Role**: AI Assistant that interacts with users

**Location**: Runs on user's local machine

**Communication**: stdio with MCP Broker

---

### 2. MCP Broker (Local)

**Role**: Bridge between Claude Code and Communication Server

**Location**: Runs as local process (spawned by Claude Code)

**Protocol**: stdio (Model Context Protocol)

**Key Features**:

| Feature | Description |
|---------|-------------|
| Protocol Registry | Register/discover communication protocols |
| Session Manager | Track connections with heartbeat |
| Capability Negotiator | Handshake for compatibility |
| Message Router | Point-to-point and broadcast routing |
| HTTP Client | Communicate with remote server |

**MCP Tools (15 total)**:

| Category | Tools |
|----------|-------|
| **Broker** | register_protocol, discover_protocols, negotiate_capabilities, broker_send_message, broadcast_message, list_sessions |
| **Project** | create_project, list_projects, get_project_info, rotate_project_keys |
| **Meeting** | send_message, create_meeting, join_meeting, get_decisions, propose_topic |

---

### 3. Communication Server (Remote)

**Role**: Central hub for all agent communication

**Location**: `oci-ajou-ec2.fcoinfup.com:8000`

**Protocol**: HTTP/HTTPS + WebSocket

**Key Components**:

| Component | Description |
|-----------|-------------|
| **FastAPI** | REST API for agent communication |
| **WebSocket Manager** | Real-time bidirectional messaging |
| **Dashboard** | Web UI for monitoring (multi-language) |
| **Database** | Persistent storage (SQLite/PostgreSQL) |

**API Endpoints**:

```
Health & Status
├── GET /health                          Server health check
└── GET /                                Root endpoint with info

Communications
├── GET  /api/v1/communications          List communications
├── POST /api/v1/communications          Log communication
└── GET  /api/v1/messages                Message history with filtering

Meetings
├── GET    /api/v1/meetings              List meetings
├── POST   /api/v1/meetings              Create meeting
├── POST   /api/v1/meetings/{id}/start   Start meeting
├── POST   /api/v1/meetings/{id}/end     End meeting
├── GET    /api/v1/meetings/{id}/messages Meeting messages
├── POST   /api/v1/meetings/{id}/messages Record message
└── POST   /api/v1/meetings/{id}/participants Add participant

Decisions
├── GET /api/v1/decisions                List decisions
└── GET /api/v1/decisions/{id}           Get decision

Projects & Agents
├── GET /api/v1/projects                 List projects
├── GET /api/v1/projects/{id}/agents     Get project agents

Internationalization
└── GET /api/v1/i18n/{language}          Get translations

WebSocket
├── WS  /ws/meetings/{meeting_id}        Meeting real-time updates
└── WS  /ws/status                       Status board updates
```

---

### 4. Agent Comm Core (Shared Library)

**Role**: Shared data models and utilities

**Components**:

| Module | Description |
|--------|-------------|
| `models/` | Pydantic models (Communication, Meeting, Decision) |
| `services/` | Business logic services |
| `repositories/` | Database access layer |
| `config/` | Configuration management |

---

## Communication Flows

### Flow 1: Agent Discovery

```
Claude Code A                                    Claude Code B
     │                                                 │
     │ "List active agents"                           │
     ├─────────MCP──────────> MCP Broker A             │
     │                            │                    │
     │                            │ GET /api/v1/projects
     │                            ├─────────────HTTP─────────────>│
     │                            │                                    │
     │                            │        Communication Server      │
     │                            │                                    │
     │                            │ 200 OK [{project_id, agents...}] │
     │                            │<─────────────HTTP─────────────┤
     │                            │                    │
     │<────────MCP──────────┤                    │
     │                                                 │
     │ "Active agents: [AgentB, AgentC]"              │
     ▼                                                 ▼
```

### Flow 2: Point-to-Point Message

```
Claude Code A                                    Claude Code B
     │                                                 │
     │ 1. send_message(to="AgentB", payload={...})     │
     ├─────────MCP──────────> MCP Broker A             │
     │                            │                    │
     │                            │ 2. POST /api/v1/communications
     │                            │ {from_agent, to_agent, ...}
     │                            ├─────────────HTTP─────────────>│
     │                            │                                    │
     │                            │        Communication Server      │
     │                            │                                    │
     │                            │ 3. Store in database             │
     │                            │ 4. Notify via WebSocket          │
     │                            │<─────────────HTTP─────────────┤
     │<─────────MCP──────────┤                    │
     │                            │                    │
     │                            │                    │ 5. WS: new_communication
     │                            │                    │<──────────WS────────┤
     │                            │                    │                    │
     │                            │                    ├─────────MCP──────> │
     │                            │                    │                    │
     │                            │                    │ "New message from AgentA"
     ▼                            ▼                    ▼
```

### Flow 3: Meeting Creation & Join

```
Claude Code A                    Communication Server            Claude Code B
     │                                   │                             │
     │ 1. create_meeting(topic, participants: [A, B])                  │
     ├─────────────────────HTTP─────────>│                             │
     │                                   │ 2. Create meeting record   │
     │                                   │ 3. Notify B via WS        │
     │<─────────────────────HTTP─────────┤                             │
     │                                   │                             │
     │ 4. WebSocket connect              │─────────────WS────────────>│
     ├──────────────────────WS──────────>│                             │
     │                                   │ 5. join_meeting()           │
     │                                   │<─────────────HTTP──────────┤
     │                                   │─────────────WS────────────>│
     │                                   │                             │
     ▼                                   ▼                             ▼
                    Real-time discussion via WebSocket
```

---

## Deployment Architecture

### Local Machine (Each User)

```
┌─────────────────────────────────────────────────────────────┐
│                        Local Machine                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌────────────────┐         ┌─────────────────────────┐    │
│  │  Claude Code   │◄───────►│    MCP Broker            │    │
│  │                │  stdio  │  - Local process         │    │
│  └────────────────┘         │  - Spawned by .mcp.json  │    │
│                             │  - stdio/MCP protocol     │    │
│                             │  - HTTP client to remote │    │
│                             └──────────┬──────────────┘    │
│                                        │                   │
│                                        │ HTTP/HTTPS        │
│                                        ▼                   │
│                             ┌─────────────────────────┐    │
│                             │  Communication Server  │    │
│                             │  (oci-ajou-ec2...:8000) │    │
│                             └─────────────────────────┘    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Remote Server

```
┌─────────────────────────────────────────────────────────────┐
│              oci-ajou-ec2.fcoinfup.com                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │           Communication Server (Port 8000)          │   │
│  │  ┌────────────┐  ┌────────────┐  ┌─────────────┐  │   │
│  │  │  FastAPI   │  │ WebSocket  │  │   Dashboard  │  │   │
│  │  │    API     │  │   Handler  │  │      UI      │  │   │
│  │  └────────────┘  └────────────┘  └─────────────┘  │   │
│  └─────────────────────────────────────────────────────┘   │
│                           │                                  │
│  ┌────────────────────────▼─────────────────────────────┐   │
│  │              Database (SQLite/PostgreSQL)            │   │
│  │  - communications  - meetings  - decisions           │   │
│  │  - agents  - projects  - participants                │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## API Reference

### Health Check

```http
GET /health
Host: oci-ajou-ec2.fcoinfup.com:8000
```

**Response**:
```json
{
  "status": "healthy",
  "service": "communication-server",
  "version": "1.0.0",
  "ssl_enabled": false
}
```

### Log Communication

```http
POST /api/v1/communications
Host: oci-ajou-ec2.fcoinfup.com:8000
X-Agent-Token: agent_project_xxx...
Content-Type: application/json

{
  "from_agent": "AgentA",
  "to_agent": "AgentB",
  "message_type": "proposal",
  "content": "Let's discuss feature X",
  "direction": "outbound"
}
```

### Create Meeting

```http
POST /api/v1/meetings
Host: oci-ajou-ec2.fcoinfup.com:8000
X-Agent-Token: agent_project_xxx...
Content-Type: application/json

{
  "title": "Feature X Discussion",
  "participant_ids": ["AgentA", "AgentB"],
  "description": "Discuss implementation of feature X",
  "max_duration_seconds": 3600
}
```

### List Messages

```http
GET /api/v1/messages?project_id=myproject&limit=50&offset=0
Host: oci-ajou-ec2.fcoinfup.com:8000
X-Agent-Token: agent_project_xxx...
```

---

## Configuration

### MCP Broker Configuration (.mcp.json)

```json
{
  "$schema": "https://raw.githubusercontent.com/anthropics/claude-code/main/.mcp.schema.json",
  "mcpServers": {
    "agent-comm": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/agent_com",
        "run",
        "mcp-broker"
      ],
      "env": {
        "AGENT_TOKEN": "agent_agent-comm_xxxxx...",
        "AGENT_NICKNAME": "local-agent",
        "AGENT_PROJECT_ID": "your-project-id",
        "COMMUNICATION_SERVER_URL": "https://oci-ajou-ec2.fcoinfup.com:8000",
        "PYTHONUNBUFFERED": "1"
      }
    }
  }
}
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `COMMUNICATION_SERVER_URL` | Communication Server URL | `http://localhost:8000` |
| `AGENT_TOKEN` | Agent authentication token | Required |
| `AGENT_NICKNAME` | Agent display name | `AnonymousAgent` |
| `AGENT_PROJECT_ID` | Project identifier | `agent-comm` |

---

## Data Models

### Communication

```json
{
  "id": "UUID",
  "from_agent": "agent-nickname",
  "to_agent": "target-agent",
  "message_type": "proposal|question|answer|notification",
  "content": "Message content",
  "direction": "inbound|outbound",
  "timestamp": "2026-02-01T12:00:00Z",
  "project_id": "project-identifier",
  "correlation_id": "UUID|null",
  "metadata": {}
}
```

### Meeting

```json
{
  "id": "UUID",
  "title": "Meeting topic",
  "description": "Meeting description",
  "status": "pending|active|completed|cancelled",
  "participant_ids": ["agent1", "agent2"],
  "created_at": "2026-02-01T12:00:00Z",
  "max_duration_seconds": 3600,
  "project_id": "project-identifier"
}
```

### Decision

```json
{
  "id": "UUID",
  "title": "Decision title",
  "description": "Decision description",
  "status": "pending|approved|rejected|deferred",
  "proposed_by": "agent-nickname",
  "meeting_id": "UUID|null",
  "options": [{...}],
  "selected_option": {...},
  "created_at": "2026-02-01T12:00:00Z",
  "decided_at": "2026-02-01T12:30:00Z|null"
}
```

---

## WebSocket Events

### Meeting WebSocket

```
ws://oci-ajou-ec2.fcoinfup.com:8000/ws/meetings/{meeting_id}?token={agent_token}
```

| Event | Description |
|-------|-------------|
| `agent_joined` | Agent joined meeting |
| `agent_left` | Agent left meeting |
| `message` | New message in meeting |
| `meeting_started` | Meeting started |
| `meeting_ended` | Meeting ended |

### Status WebSocket

```
ws://oci-ajou-ec2.fcoinfup.com:8000/ws/status?token={agent_token}
```

| Event | Description |
|-------|-------------|
| `agent_status` | Agent status change |
| `new_communication` | New communication logged |
| `meeting_created` | New meeting created |
| `decision_made` | Decision recorded |

---

## Internationalization

### Supported Languages

| Code | Name | Native Name |
|------|------|-------------|
| `ko` | Korean | 한국어 |
| `en` | English | English |

### Get Translations

```http
GET /api/v1/i18n/{language}
Host: oci-ajou-ec2.fcoinfup.com:8000
```

---

## Component Summary

| Component | Location | Protocol | Port | Purpose |
|-----------|----------|----------|------|---------|
| **Claude Code** | Local | - | - | AI Assistant |
| **MCP Broker** | Local | stdio/MCP | N/A | Claude-MCP Bridge |
| **Communication Server** | Remote | HTTP/WS | 8000 | Central Hub |
| **Database** | Remote | - | 5432/SQLite | Persistent Storage |

---

**Last Updated**: 2026-02-01
**Version**: 1.0.0
