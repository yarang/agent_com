# API Reference

Complete API reference for MCP Broker Server HTTP endpoints and MCP tools.

---

## Table of Contents

- [HTTP Endpoints](#http-endpoints)
  - [Health Check](#health-check)
  - [List Sessions](#list-sessions)
  - [List Protocols](#list-protocols)
  - [Security Status](#security-status)
  - [Root Endpoint](#root-endpoint)
  - [Get Supported Languages](#get-supported-languages)
  - [Get Translations](#get-translations)
  - [List Projects](#list-projects)
  - [Get Project Agents](#get-project-agents)
  - [List Messages](#list-messages)
  - [Get Message Detail](#get-message-detail)
- [MCP Tools](#mcp-tools)
- [Error Codes](#error-codes)
- [Authentication](#authentication)

---

## HTTP Endpoints

### Base URL

```
http://localhost:8000
```

### Health Check

Check server health and status.

**Endpoint:** `GET /health`

**Authentication:** Not required

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "storage_backend": "memory",
  "active_sessions": 3,
  "authentication_enabled": false
}
```

**Status Codes:**
- `200 OK` - Server is healthy
- `503 Service Unavailable` - Server not initialized

---

### List Sessions

Retrieve all sessions with optional filtering.

**Endpoint:** `GET /sessions`

**Authentication:** Optional (depends on configuration)

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `status` | string | No | Filter by status: `active`, `stale`, `all` |
| `include_capabilities` | boolean | No | Include full capability details (default: true) |

**Response:**
```json
{
  "sessions": [
    {
      "session_id": "550e8400-e29b-41d4-a716-446655440000",
      "connection_time": "2025-01-31T10:00:00Z",
      "last_heartbeat": "2025-01-31T10:05:30Z",
      "status": "active",
      "queue_size": 2,
      "capabilities": {
        "supported_protocols": {
          "chat": ["1.0.0", "1.1.0"],
          "file_transfer": ["1.0.0"]
        },
        "supported_features": ["point_to_point", "broadcast", "streaming"]
      }
    }
  ],
  "count": 1
}
```

**Status Codes:**
- `200 OK` - Sessions retrieved successfully
- `401 Unauthorized` - Authentication required
- `503 Service Unavailable` - Server not initialized

---

### List Protocols

Retrieve registered protocols with optional filtering.

**Endpoint:** `GET /protocols`

**Authentication:** Optional (depends on configuration)

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `name` | string | No | Filter by protocol name |
| `version` | string | No | Filter by version |

**Response:**
```json
{
  "protocols": [
    {
      "name": "chat",
      "version": "1.0.0",
      "capabilities": ["point_to_point", "broadcast"],
      "metadata": {
        "author": "MCP Team",
        "description": "Chat messaging protocol",
        "tags": ["chat", "messaging"]
      },
      "registered_at": "2025-01-31T10:00:00Z"
    }
  ],
  "count": 1
}
```

**Status Codes:**
- `200 OK` - Protocols retrieved successfully
- `401 Unauthorized` - Authentication required
- `503 Service Unavailable` - Server not initialized

---

### Security Status

Get current security configuration and recommendations.

**Endpoint:** `GET /security/status`

**Authentication:** Not required

**Response:**
```json
{
  "authentication_enabled": false,
  "cors_origins": ["http://localhost:8000"],
  "recommendations": [
    "Enable authentication for production use",
    "Set a secure auth_secret when authentication is enabled",
    "Restrict CORS origins to specific domains in production"
  ]
}
```

**Status Codes:**
- `200 OK` - Security status retrieved

---

### Root Endpoint

Get server information and available endpoints.

**Endpoint:** `GET /`

**Authentication:** Not required

**Response:**
```json
{
  "name": "MCP Broker Server",
  "version": "1.0.0",
  "description": "Inter-Claude Code communication system",
  "docs": "/docs",
  "health": "/health",
  "security": "/security/status"
}
```

**Status Codes:**
- `200 OK` - Server information retrieved

---

### Get Supported Languages

Get list of available languages for dashboard UI.

**Endpoint:** `GET /api/v1/i18n/languages`

**Authentication:** Not required

**Response:**
```json
{
  "languages": [
    {"code": "ko", "name": "Korean", "native_name": "한국어"},
    {"code": "en", "name": "English", "native_name": "English"}
  ],
  "default": "ko"
}
```

**Status Codes:**
- `200 OK` - Languages retrieved successfully

---

### Get Translations

Get translation strings for a specific language.

**Endpoint:** `GET /api/v1/i18n/{language}`

**Authentication:** Not required

**Path Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `language` | string | Yes | Language code (ko, en) |

**Response:**
```json
{
  "language": "ko",
  "translations": {
    "dashboard": {
      "title": "AI Agent Communication",
      "subtitle": "Real-time Status Board"
    },
    "stats": {
      "totalAgents": "전체 에이전트",
      "activeAgents": "활성화 에이전트",
      "totalMessages": "전체 메시지"
    }
  },
  "version": "1.0.0"
}
```

**Status Codes:**
- `200 OK` - Translations retrieved successfully
- `400 Bad Request` - Invalid language code
- `404 Not Found` - Translation file not found

---

### List Projects

Get list of all projects with agent counts and status.

**Endpoint:** `GET /api/v1/projects`

**Authentication:** Optional (depends on configuration)

**Response:**
```json
{
  "projects": [
    {
      "project_id": null,
      "name": "All Agents",
      "agent_count": 10,
      "active_count": 5,
      "is_online": true
    },
    {
      "project_id": "myproject",
      "name": "My Project",
      "agent_count": 5,
      "active_count": 3,
      "is_online": true
    }
  ]
}
```

**Status Codes:**
- `200 OK` - Projects retrieved successfully
- `401 Unauthorized` - Authentication required
- `503 Service Unavailable` - Server not initialized

---

### Get Project Agents

Get agents for a specific project.

**Endpoint:** `GET /api/v1/projects/{project_id}/agents`

**Authentication:** Optional (depends on configuration)

**Path Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `project_id` | string | Yes | Project ID or "_none" for agents without a project |

**Response:**
```json
{
  "project_id": "myproject",
  "agents": [
    {
      "agent_id": "uuid",
      "full_id": "FrontendExpert",
      "nickname": "FrontendExpert",
      "status": "online",
      "capabilities": ["code", "review"],
      "last_seen": "2026-02-01T12:00:00Z",
      "current_meeting": null,
      "project_id": "myproject"
    }
  ]
}
```

**Status Codes:**
- `200 OK` - Agents retrieved successfully
- `401 Unauthorized` - Authentication required
- `503 Service Unavailable` - Server not initialized

---

### List Messages

Get message history with optional filtering.

**Endpoint:** `GET /api/v1/messages`

**Authentication:** Required

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `project_id` | string | No | Filter by project ID |
| `from_agent` | string | No | Filter by sender agent |
| `to_agent` | string | No | Filter by recipient agent |
| `limit` | integer | No | Messages per page (default: 50, max: 200) |
| `offset` | integer | No | Pagination offset (default: 0) |

**Response:**
```json
[
  {
    "message_id": "uuid",
    "from_agent": "FrontendExpert",
    "to_agent": "BackendDev",
    "timestamp": "2026-02-01T12:00:00Z",
    "content_preview": "Here is the API payload...",
    "project_id": "myproject",
    "message_type": "direct"
  }
]
```

**Status Codes:**
- `200 OK` - Messages retrieved successfully
- `401 Unauthorized` - Authentication required
- `500 Internal Server Error` - Failed to retrieve messages

---

### Get Message Detail

Get full details of a specific message.

**Endpoint:** `GET /api/v1/messages/{message_id}`

**Authentication:** Required

**Path Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `message_id` | string | Yes | Message UUID |

**Response:**
```json
{
  "message_id": "uuid",
  "from_agent": "FrontendExpert",
  "to_agent": "BackendDev",
  "timestamp": "2026-02-01T12:00:00Z",
  "content": "Full message content here...",
  "content_type": "text/plain",
  "project_id": "myproject",
  "message_type": "direct",
  "direction": "outbound",
  "correlation_id": null,
  "metadata": {}
}
```

**Status Codes:**
- `200 OK` - Message retrieved successfully
- `400 Bad Request` - Invalid message ID format
- `401 Unauthorized` - Authentication required
- `404 Not Found` - Message not found

---

## MCP Tools

MCP (Model Context Protocol) tools are invoked by Claude Code instances connected to the broker.

### Tool Invocation Pattern

Tools are invoked through the MCP server with the following structure:

```json
{
  "name": "tool_name",
  "arguments": {
    // Tool-specific parameters
  }
}
```

---

### register_protocol

Register a new communication protocol with JSON Schema validation.

**Tool Name:** `register_protocol`

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `name` | string | Yes | Protocol identifier in snake_case |
| `version` | string | Yes | Semantic version (e.g., "1.0.0") |
| `schema` | object | Yes | JSON Schema for message validation |
| `capabilities` | array | No | Supported communication patterns |
| `author` | string | No | Protocol author |
| `description` | string | No | Protocol description |
| `tags` | array | No | Searchable tags |

**Capability Options:**
- `point_to_point` - Direct 1:1 messaging
- `broadcast` - 1:N messaging to multiple recipients
- `request_response` - Request-response pattern
- `streaming` - Streaming data transfer

**Example Request:**
```json
{
  "name": "chat",
  "version": "1.0.0",
  "schema": {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "properties": {
      "message": {
        "type": "string",
        "description": "Chat message content"
      },
      "sender": {
        "type": "string",
        "description": "Sender identifier"
      },
      "timestamp": {
        "type": "string",
        "format": "date-time",
        "description": "Message timestamp"
      }
    },
    "required": ["message", "sender"]
  },
  "capabilities": ["point_to_point", "broadcast"],
  "author": "MCP Team",
  "description": "Simple chat messaging protocol",
  "tags": ["chat", "messaging", "v1"]
}
```

**Response:**
```json
{
  "success": true,
  "protocol": {
    "name": "chat",
    "version": "1.0.0",
    "registered_at": "2025-01-31T10:00:00Z",
    "capabilities": ["point_to_point", "broadcast"]
  }
}
```

**Error Response:**
```json
{
  "success": false,
  "error": "Protocol already exists",
  "detail": "A protocol named 'chat' with version '1.0.0' is already registered"
}
```

---

### discover_protocols

Query available protocols with optional filtering.

**Tool Name:** `discover_protocols`

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `name` | string | No | Filter by protocol name |
| `version_range` | string | No | Semantic version range (e.g., ">=1.0.0,<2.0.0") |
| `tags` | array | No | Filter by tags |

**Example Request:**
```json
{
  "name": "chat",
  "version_range": ">=1.0.0,<2.0.0",
  "tags": ["messaging"]
}
```

**Response:**
```json
{
  "protocols": [
    {
      "name": "chat",
      "version": "1.0.0",
      "capabilities": ["point_to_point", "broadcast"],
      "metadata": {
        "author": "MCP Team",
        "description": "Simple chat messaging protocol",
        "tags": ["chat", "messaging", "v1"]
      }
    },
    {
      "name": "chat",
      "version": "1.1.0",
      "capabilities": ["point_to_point", "broadcast", "streaming"],
      "metadata": {
        "author": "MCP Team",
        "description": "Enhanced chat messaging protocol",
        "tags": ["chat", "messaging", "v1"]
      }
    }
  ],
  "count": 2
}
```

---

### negotiate_capabilities

Perform capability negotiation handshake with a target session.

**Tool Name:** `negotiate_capabilities`

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `target_session_id` | string | Yes | Target session UUID |
| `required_protocols` | array | No | Required protocol versions |

**Example Request:**
```json
{
  "target_session_id": "550e8400-e29b-41d4-a716-446655440000",
  "required_protocols": [
    {"name": "chat", "version": "1.0.0"},
    {"name": "file_transfer", "version": "1.0.0"}
  ]
}
```

**Response (Compatible):**
```json
{
  "compatible": true,
  "supported_protocols": {
    "chat": "1.1.0",
    "file_transfer": "1.0.0"
  },
  "feature_intersections": ["point_to_point", "broadcast"],
  "unsupported_features": ["streaming"],
  "incompatibilities": [],
  "suggestion": null
}
```

**Response (Incompatible):**
```json
{
  "compatible": false,
  "supported_protocols": {
    "chat": "1.0.0"
  },
  "feature_intersections": ["point_to_point"],
  "unsupported_features": ["broadcast", "streaming"],
  "incompatibilities": [
    {
      "protocol": "file_transfer",
      "reason": "Protocol not supported by target session"
    }
  ],
  "suggestion": "Target session does not support file_transfer protocol. Consider using only chat protocol."
}
```

---

### send_message

Send a point-to-point message to a specific session.

**Tool Name:** `send_message`

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `recipient_id` | string | Yes | Recipient session UUID |
| `protocol_name` | string | Yes | Protocol for payload validation |
| `protocol_version` | string | No | Protocol version (default: "1.0.0") |
| `payload` | object | Yes | Message payload (validated against protocol schema) |
| `priority` | string | No | Message priority: `low`, `normal`, `high`, `urgent` |
| `ttl` | integer | No | Time-to-live in seconds |

**Example Request:**
```json
{
  "recipient_id": "550e8400-e29b-41d4-a716-446655440000",
  "protocol_name": "chat",
  "protocol_version": "1.0.0",
  "payload": {
    "message": "Hello from Session A!",
    "sender": "Session A",
    "timestamp": "2025-01-31T10:00:00Z"
  },
  "priority": "normal",
  "ttl": 3600
}
```

**Response (Delivered):**
```json
{
  "success": true,
  "message_id": "a7f8b9c0-d1e2-4f3g-5h6i-7j8k9l0m1n2o",
  "delivered_at": "2025-01-31T10:00:01Z"
}
```

**Response (Queued):**
```json
{
  "success": true,
  "message_id": "a7f8b9c0-d1e2-4f3g-5h6i-7j8k9l0m1n2o",
  "queued": true,
  "queue_size": 3
}
```

**Response (Failed):**
```json
{
  "success": false,
  "error": "Session not found",
  "detail": "Recipient session does not exist or is disconnected"
}
```

---

### broadcast_message

Broadcast a message to all compatible sessions.

**Tool Name:** `broadcast_message`

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `protocol_name` | string | Yes | Protocol for payload validation |
| `protocol_version` | string | No | Protocol version (default: "1.0.0") |
| `payload` | object | Yes | Message payload |
| `capability_filter` | object | No | Filter recipients by capabilities |
| `priority` | string | No | Message priority |

**Example Request:**
```json
{
  "protocol_name": "chat",
  "protocol_version": "1.0.0",
  "payload": {
    "message": "System announcement",
    "sender": "System",
    "timestamp": "2025-01-31T10:00:00Z"
  },
  "capability_filter": {
    "supports_broadcast": true
  },
  "priority": "high"
}
```

**Response:**
```json
{
  "success": true,
  "delivery_count": 3,
  "recipients": {
    "delivered": [
      "550e8400-e29b-41d4-a716-446655440001",
      "550e8400-e29b-41d4-a716-446655440002",
      "550e8400-e29b-41d4-a716-446655440003"
    ],
    "failed": [],
    "skipped": []
  },
  "reason": null
}
```

**Response (Partial Failure):**
```json
{
  "success": true,
  "delivery_count": 2,
  "recipients": {
    "delivered": [
      "550e8400-e29b-41d4-a716-446655440001",
      "550e8400-e29b-41d4-a716-446655440002"
    ],
    "failed": [
      "550e8400-e29b-41d4-a716-446655440003"
    ],
    "skipped": [
      "550e8400-e29b-41d4-a716-446655440004"
    ]
  },
  "reason": "1 session failed due to queue full, 1 session skipped due to incompatible protocol"
}
```

---

### list_sessions

List all active sessions with their capabilities.

**Tool Name:** `list_sessions`

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `status_filter` | string | No | Filter by status: `active`, `stale`, `all` |
| `include_capabilities` | boolean | No | Include full capability details |

**Example Request:**
```json
{
  "status_filter": "active",
  "include_capabilities": true
}
```

**Response:**
```json
{
  "sessions": [
    {
      "session_id": "550e8400-e29b-41d4-a716-446655440000",
      "connection_time": "2025-01-31T10:00:00Z",
      "last_heartbeat": "2025-01-31T10:05:30Z",
      "status": "active",
      "queue_size": 0,
      "capabilities": {
        "supported_protocols": {
          "chat": ["1.0.0", "1.1.0"],
          "file_transfer": ["1.0.0"]
        },
        "supported_features": ["point_to_point", "broadcast"]
      }
    },
    {
      "session_id": "550e8400-e29b-41d4-a716-446655440001",
      "connection_time": "2025-01-31T10:01:00Z",
      "last_heartbeat": "2025-01-31T10:05:25Z",
      "status": "active",
      "queue_size": 1,
      "capabilities": {
        "supported_protocols": {
          "chat": ["1.0.0"]
        },
        "supported_features": ["point_to_point"]
      }
    }
  ],
  "count": 2
}
```

---

### create_project

Create a new isolated project with its own namespace for sessions, protocols, and messages.

**Tool Name:** `create_project`

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `project_id` | string | Yes | Unique project identifier (snake_case) |
| `name` | string | Yes | Human-readable project name |
| `description` | string | No | Project description |
| `config` | object | No | Project configuration |
| `config.allow_cross_project` | boolean | No | Enable cross-project communication (default: false) |
| `config.discoverable` | boolean | No | Allow project discovery (default: true) |
| `tags` | array | No | Searchable tags |

**Example Request:**
```json
{
  "project_id": "team_alpha",
  "name": "Team Alpha Workspace",
  "description": "Collaboration workspace for Team Alpha",
  "config": {
    "allow_cross_project": true,
    "discoverable": true
  },
  "tags": ["team-alpha", "production"]
}
```

**Response:**
```json
{
  "success": true,
  "project": {
    "project_id": "team_alpha",
    "name": "Team Alpha Workspace",
    "description": "Collaboration workspace for Team Alpha",
    "metadata": {
      "created_at": "2025-01-31T10:00:00Z",
      "tags": ["team-alpha", "production"]
    },
    "config": {
      "allow_cross_project": true,
      "discoverable": true
    }
  },
  "api_keys": [
    {
      "key_id": "key1",
      "api_key": "team_alpha_key1_abc123def456...",
      "created_at": "2025-01-31T10:00:00Z"
    }
  ],
  "warning": "Store API keys securely. They will not be shown again."
}
```

**Error Response:**
```json
{
  "success": false,
  "error": "Project already exists",
  "detail": "A project with ID 'team_alpha' already exists"
}
```

---

### list_projects

List all discoverable projects.

**Tool Name:** `list_projects`

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `include_inactive` | boolean | No | Include inactive projects (default: false) |

**Example Request:**
```json
{
  "include_inactive": false
}
```

**Response:**
```json
{
  "success": true,
  "projects": [
    {
      "project_id": "team_alpha",
      "name": "Team Alpha Workspace",
      "description": "Collaboration workspace for Team Alpha",
      "metadata": {
        "created_at": "2025-01-31T10:00:00Z",
        "tags": ["team-alpha", "production"]
      },
      "is_active": true
    },
    {
      "project_id": "team_beta",
      "name": "Team Beta Workspace",
      "description": "Collaboration workspace for Team Beta",
      "metadata": {
        "created_at": "2025-01-31T11:00:00Z",
        "tags": ["team-beta"]
      },
      "is_active": true
    }
  ],
  "count": 2
}
```

---

### get_project_info

Get detailed information about a specific project.

**Tool Name:** `get_project_info`

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `project_id` | string | Yes | Project identifier |

**Example Request:**
```json
{
  "project_id": "team_alpha"
}
```

**Response:**
```json
{
  "success": true,
  "project": {
    "project_id": "team_alpha",
    "name": "Team Alpha Workspace",
    "description": "Collaboration workspace for Team Alpha",
    "metadata": {
      "created_at": "2025-01-31T10:00:00Z",
      "tags": ["team-alpha", "production"]
    },
    "config": {
      "allow_cross_project": true,
      "discoverable": true
    },
    "api_keys": [
      {
        "key_id": "key1",
        "created_at": "2025-01-31T10:00:00Z"
      }
    ],
    "cross_project_permissions": [
      {
        "target_project_id": "team_beta",
        "allowed_protocols": ["chat"],
        "message_rate_limit": 60
      }
    ],
    "is_active": true,
    "session_count": 3,
    "protocol_count": 2
  }
}
```

**Error Response:**
```json
{
  "success": false,
  "error": "Project not found",
  "detail": "Project 'team_alpha' does not exist or is not discoverable"
}
```

---

### rotate_project_keys

Rotate API keys for a project (invalidate old keys and generate new ones).

**Tool Name:** `rotate_project_keys`

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `project_id` | string | Yes | Project identifier |
| `key_id` | string | No | Specific key ID to rotate (rotates all if omitted) |

**Example Request (All Keys):**
```json
{
  "project_id": "team_alpha"
}
```

**Example Request (Specific Key):**
```json
{
  "project_id": "team_alpha",
  "key_id": "key1"
}
```

**Response:**
```json
{
  "success": true,
  "rotated_keys": ["key1"],
  "new_api_keys": [
    {
      "key_id": "key1",
      "api_key": "team_alpha_key1_xyz789abc012...",
      "created_at": "2025-01-31T12:00:00Z"
    }
  ],
  "warning": "Old keys have been invalidated. Update all clients immediately."
}
```

**Error Response:**
```json
{
  "success": false,
  "error": "Project not found",
  "detail": "Project 'team_alpha' does not exist"
}
```

---

## Error Codes

### HTTP Status Codes

| Code | Description |
|------|-------------|
| `200 OK` | Request successful |
| `400 Bad Request` | Invalid request parameters |
| `401 Unauthorized` | Authentication required or failed |
| `403 Forbidden` | Access denied |
| `404 Not Found` | Resource not found |
| `500 Internal Server Error` | Server error |
| `503 Service Unavailable` | Server not initialized |

### MCP Tool Error Responses

All MCP tools return errors in a consistent format:

```json
{
  "success": false,
  "error": "Error type",
  "detail": "Detailed error message"
}
```

**Common Error Types:**

| Error Type | Description |
|------------|-------------|
| `Authentication failed` | Invalid or missing credentials |
| `Session not found` | Target session does not exist |
| `Protocol not found` | Requested protocol is not registered |
| `Protocol already exists` | Attempting to register duplicate protocol |
| `Invalid schema` | JSON Schema validation failed |
| `Payload validation failed` | Message payload does not match protocol schema |
| `Queue full` | Recipient message queue is at capacity |
| `Incompatible protocol` | Protocol version mismatch |
| `Invalid session ID` | Malformed or invalid UUID |

---

## Authentication

### Enabling Authentication

Set the following environment variables:

```bash
MCP_BROKER_ENABLE_AUTH=true
MCP_BROKER_AUTH_SECRET=<your-secure-secret>
```

### Generating a Secure Secret

```python
import secrets
print(secrets.token_urlsafe(32))
```

### Making Authenticated Requests

**Using X-API-Key Header:**
```bash
curl -H "X-API-Key: your-secret" http://localhost:8000/sessions
```

**Using Cookie:**
```bash
curl --cookie "api_key=your-secret" http://localhost:8000/sessions
```

### Authentication Flow

1. Client includes API key in request (header or cookie)
2. Server validates key against configured secret
3. Request proceeds if valid, returns 401/403 if invalid
4. Public endpoints (`/`, `/health`, `/docs`) bypass authentication

### Security Best Practices

1. **Use strong, randomly generated secrets** (32+ bytes)
2. **Rotate secrets periodically** in production
3. **Never log authentication tokens**
4. **Use HTTPS in production** to prevent token interception
5. **Restrict CORS origins** to specific domains
6. **Monitor failed authentication attempts** in logs

---

## Multi-Project Support

### Enabling Multi-Project Mode

Set the following environment variable:

```bash
MCP_BROKER_ENABLE_MULTI_PROJECT=true
```

When enabled, the broker supports project isolation with the following features:
- Project-scoped sessions, protocols, and messages
- Cross-project communication with explicit permission
- Project-specific API keys
- Backward compatibility with existing deployments

### Project Identification

Projects are identified using two methods (priority order):

**Method 1: X-Project-ID Header (Highest Priority)**
```bash
curl -H "X-Project-ID: team_alpha" http://localhost:8000/sessions
```

**Method 2: API Key Prefix**
```bash
# API key format: {project_id}_{key_id}_{secret}
curl -H "X-API-Key: team_alpha_key1_abc123..." http://localhost:8000/sessions
```

**Method 3: Default Project (Fallback)**
- When no project identification is provided
- Uses "default" project
- Maintains backward compatibility

### Cross-Project Communication

Cross-project communication requires explicit permission from both projects:

**Configuration:**
```python
# In ProjectConfig
allow_cross_project: bool = True  # Both projects must enable

# In CrossProjectPermission
target_project_id: str  # Allowed target project
allowed_protocols: list[str]  # Protocol whitelist (empty = all)
message_rate_limit: int  # Messages per minute (0 = unlimited)
```

**Permission Check Flow:**
1. Sender project must have `allow_cross_project = True`
2. Recipient project must have `allow_cross_project = True`
3. At least one project must have permission for the target
4. Protocol must be in allowed_protocols whitelist (if specified)
5. Rate limit must not be exceeded (if configured)

### Project API Keys

Each project has its own API keys with the format:

```
Format: {project_id}_{key_id}_{secret}
Example: team_alpha_key1_abc123def456...
```

**Benefits:**
- Automatic project identification
- Project-specific access control
- Key rotation per project
- Audit trail by project

### Backward Compatibility

Multi-project mode is fully backward compatible:

- **Existing Deployments:** Automatically use "default" project
- **No Code Changes:** Existing MCP tools work without modification
- **Gradual Migration:** Create new projects incrementally
- **Single-Project Mode:** Leave `MCP_BROKER_ENABLE_MULTI_PROJECT` unset or false

---

## Rate Limiting

Currently, rate limiting is not enforced by default. This feature is planned for future releases.

For production deployments, consider implementing rate limiting at the reverse proxy level (e.g., Nginx, HAProxy).

---

## Versioning

The API follows semantic versioning. Major version changes may include breaking changes, while minor and patch versions should be backward compatible.

Current API Version: `1.0.0`

---

## Related Documentation

- [README.md](../README.md) - Project overview and quick start
- [Architecture](architecture.md) - System architecture and design
- [MCP Specification](https://modelcontextprotocol.io/) - Official MCP documentation
