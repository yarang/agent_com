# Agent and Task API Documentation

**API Version:** v1
**Status:** Stable
**Last Updated:** 2026-02-06

---

## Overview

The Agent and Task API provides REST endpoints for managing AI agents and tasks with full database persistence. This documentation covers the complete CRUD operations for both agents and tasks, including authentication, authorization, and validation rules.

### Table of Contents

- [Authentication](#authentication)
- [Agent Endpoints](#agent-endpoints)
- [Task Endpoints](#task-endpoints)
- [Error Codes](#error-codes)
- [Data Models](#data-models)

---

## Authentication

All endpoints require JWT authentication via the `Authorization` header:

```http
Authorization: Bearer <your-jwt-token>
```

### Authorization Rules

- **Project Owners**: Full access to agents and tasks within their projects
- **Superusers**: Full access to all agents and tasks across all projects
- **Project Isolation**: Users can only view agents/tasks from their owned projects

---

## Agent Endpoints

### Create Agent

Creates a new AI agent in the specified project.

**Endpoint:** `POST /api/v1/agents`

**Authentication:** Required (JWT)

**Request Body:**

```json
{
  "project_id": "uuid-project-id",
  "name": "FrontendExpert",
  "nickname": "Frontend Expert",
  "agent_type": "generic",
  "capabilities": ["communicate", "create_meetings"],
  "config": {
    "model": "claude-3-opus",
    "temperature": 0.7
  }
}
```

**Response:** `201 Created`

```json
{
  "id": "uuid-agent-id",
  "project_id": "uuid-project-id",
  "name": "FrontendExpert",
  "nickname": "Frontend Expert",
  "agent_type": "generic",
  "status": "offline",
  "capabilities": ["communicate", "create_meetings"],
  "config": {
    "model": "claude-3-opus",
    "temperature": 0.7
  },
  "is_active": true,
  "created_at": "2026-02-06T12:00:00Z",
  "updated_at": "2026-02-06T12:00:00Z"
}
```

**Validation Rules:**

- `name` must be unique within the project
- `project_id` must exist and user must be the owner
- `capabilities` defaults to empty array if not provided
- `agent_type` defaults to "generic" if not provided

**Error Responses:**

- `403 Forbidden` - User doesn't own the project
- `404 Not Found` - Project not found
- `409 Conflict` - Agent name already exists in project

---

### List Agents

Retrieves a paginated list of agents with optional filtering.

**Endpoint:** `GET /api/v1/agents`

**Authentication:** Required (JWT)

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `project_id` | UUID | No | Filter by project UUID |
| `status` | string | No | Filter by status (online, offline, busy, error) |
| `is_active` | boolean | No | Filter by active state |
| `page` | integer | No | Page number (default: 1) |
| `size` | integer | No | Page size (default: 20, max: 100) |

**Response:** `200 OK`

```json
{
  "items": [
    {
      "id": "uuid-agent-id",
      "project_id": "uuid-project-id",
      "name": "FrontendExpert",
      "nickname": "Frontend Expert",
      "agent_type": "generic",
      "status": "online",
      "capabilities": ["communicate", "create_meetings"],
      "config": {},
      "is_active": true,
      "created_at": "2026-02-06T12:00:00Z",
      "updated_at": "2026-02-06T12:00:00Z"
    }
  ],
  "total": 1,
  "page": 1,
  "size": 20,
  "has_more": false
}
```

---

### Get Agent

Retrieves details of a specific agent by ID.

**Endpoint:** `GET /api/v1/agents/{agent_id}`

**Authentication:** Required (JWT)

**Response:** `200 OK`

```json
{
  "id": "uuid-agent-id",
  "project_id": "uuid-project-id",
  "name": "FrontendExpert",
  "nickname": "Frontend Expert",
  "agent_type": "generic",
  "status": "online",
  "capabilities": ["communicate", "create_meetings"],
  "config": {},
  "is_active": true,
  "created_at": "2026-02-06T12:00:00Z",
  "updated_at": "2026-02-06T12:00:00Z"
}
```

**Error Responses:**

- `403 Forbidden` - User doesn't own the project
- `404 Not Found` - Agent not found

---

### Update Agent

Partially updates an existing agent.

**Endpoint:** `PATCH /api/v1/agents/{agent_id}`

**Authentication:** Required (JWT)

**Request Body:** (all fields optional)

```json
{
  "nickname": "Updated Nickname",
  "status": "online",
  "capabilities": ["communicate", "create_meetings", "code_review"],
  "config": {
    "new_setting": "value"
  },
  "is_active": true
}
```

**Response:** `200 OK`

```json
{
  "id": "uuid-agent-id",
  "project_id": "uuid-project-id",
  "name": "FrontendExpert",
  "nickname": "Updated Nickname",
  "agent_type": "generic",
  "status": "online",
  "capabilities": ["communicate", "create_meetings", "code_review"],
  "config": {
    "new_setting": "value"
  },
  "is_active": true,
  "created_at": "2026-02-06T12:00:00Z",
  "updated_at": "2026-02-06T12:01:00Z"
}
```

**Error Responses:**

- `403 Forbidden` - User doesn't own the project
- `404 Not Found` - Agent not found

---

### Delete Agent

Deletes an agent and cascades to related records (API keys, chat participants).

**Endpoint:** `DELETE /api/v1/agents/{agent_id}`

**Authentication:** Required (JWT)

**Response:** `204 No Content`

**Cascade Behavior:**

- All `AgentApiKeyDB` records for this agent are deleted
- All `ChatParticipantDB` records for this agent are deleted

**Error Responses:**

- `403 Forbidden` - User doesn't own the project
- `404 Not Found` - Agent not found

---

## Task Endpoints

### Create Task

Creates a new task in the specified project.

**Endpoint:** `POST /api/v1/tasks`

**Authentication:** Required (JWT)

**Request Body:**

```json
{
  "project_id": "uuid-project-id",
  "room_id": "uuid-room-id",
  "title": "Implement authentication system",
  "description": "Add JWT-based authentication to the API",
  "priority": "high",
  "assigned_to": "uuid-agent-id",
  "assigned_to_type": "agent",
  "dependencies": [],
  "due_date": "2026-02-15T12:00:00Z"
}
```

**Response:** `201 Created`

```json
{
  "id": "uuid-task-id",
  "project_id": "uuid-project-id",
  "room_id": "uuid-room-id",
  "title": "Implement authentication system",
  "description": "Add JWT-based authentication to the API",
  "status": "pending",
  "priority": "high",
  "assigned_to": "uuid-agent-id",
  "assigned_to_type": "agent",
  "created_by": "uuid-user-id",
  "dependencies": [],
  "started_at": null,
  "completed_at": null,
  "due_date": "2026-02-15T12:00:00Z",
  "result": null,
  "created_at": "2026-02-06T12:00:00Z",
  "updated_at": "2026-02-06T12:00:00Z"
}
```

**Validation Rules:**

- `project_id` must exist and user must be the owner
- All `dependencies` must reference existing completed tasks
- `assigned_to_type` must be either "agent" or "user"

**Error Responses:**

- `400 Bad Request` - Dependencies not found or not completed
- `403 Forbidden` - User doesn't own the project
- `404 Not Found` - Project not found

---

### List Tasks

Retrieves a paginated list of tasks with optional filtering.

**Endpoint:** `GET /api/v1/tasks`

**Authentication:** Required (JWT)

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `project_id` | UUID | No | Filter by project UUID |
| `room_id` | UUID | No | Filter by chat room UUID |
| `status` | string | No | Filter by status (pending, in_progress, review, completed, blocked, cancelled) |
| `assigned_to` | UUID | No | Filter by assignee UUID |
| `page` | integer | No | Page number (default: 1) |
| `size` | integer | No | Page size (default: 20, max: 100) |

**Response:** `200 OK`

```json
{
  "items": [
    {
      "id": "uuid-task-id",
      "project_id": "uuid-project-id",
      "room_id": "uuid-room-id",
      "title": "Implement authentication system",
      "description": "Add JWT-based authentication to the API",
      "status": "pending",
      "priority": "high",
      "assigned_to": "uuid-agent-id",
      "assigned_to_type": "agent",
      "created_by": "uuid-user-id",
      "dependencies": [],
      "started_at": null,
      "completed_at": null,
      "due_date": "2026-02-15T12:00:00Z",
      "result": null,
      "created_at": "2026-02-06T12:00:00Z",
      "updated_at": "2026-02-06T12:00:00Z"
    }
  ],
  "total": 1,
  "page": 1,
  "size": 20,
  "has_more": false
}
```

---

### Get Task

Retrieves details of a specific task by ID.

**Endpoint:** `GET /api/v1/tasks/{task_id}`

**Authentication:** Required (JWT)

**Response:** `200 OK`

```json
{
  "id": "uuid-task-id",
  "project_id": "uuid-project-id",
  "room_id": "uuid-room-id",
  "title": "Implement authentication system",
  "description": "Add JWT-based authentication to the API",
  "status": "pending",
  "priority": "high",
  "assigned_to": "uuid-agent-id",
  "assigned_to_type": "agent",
  "created_by": "uuid-user-id",
  "dependencies": [],
  "started_at": null,
  "completed_at": null,
  "due_date": "2026-02-15T12:00:00Z",
  "result": null,
  "created_at": "2026-02-06T12:00:00Z",
  "updated_at": "2026-02-06T12:00:00Z"
}
```

**Error Responses:**

- `403 Forbidden` - User doesn't own the project
- `404 Not Found` - Task not found

---

### Update Task

Partially updates an existing task. Automatically manages timestamps based on status changes.

**Endpoint:** `PATCH /api/v1/tasks/{task_id}`

**Authentication:** Required (JWT)

**Request Body:** (all fields optional)

```json
{
  "title": "Updated task title",
  "status": "in_progress",
  "priority": "critical",
  "result": {
    "output": "Task results here"
  }
}
```

**Response:** `200 OK`

```json
{
  "id": "uuid-task-id",
  "project_id": "uuid-project-id",
  "room_id": "uuid-room-id",
  "title": "Updated task title",
  "description": "Add JWT-based authentication to the API",
  "status": "in_progress",
  "priority": "critical",
  "assigned_to": "uuid-agent-id",
  "assigned_to_type": "agent",
  "created_by": "uuid-user-id",
  "dependencies": [],
  "started_at": "2026-02-06T12:01:00Z",
  "completed_at": null,
  "due_date": "2026-02-15T12:00:00Z",
  "result": null,
  "created_at": "2026-02-06T12:00:00Z",
  "updated_at": "2026-02-06T12:01:00Z"
}
```

**Automatic Timestamp Management:**

- When status changes to `in_progress`: `started_at` is set automatically
- When status changes to `completed`: `started_at` and `completed_at` are set automatically

**Error Responses:**

- `400 Bad Request` - Dependencies not found or not completed
- `403 Forbidden` - User doesn't own the project
- `404 Not Found` - Task not found

---

### Delete Task

Deletes an existing task.

**Endpoint:** `DELETE /api/v1/tasks/{task_id}`

**Authentication:** Required (JWT)

**Response:** `204 No Content`

**Error Responses:**

- `403 Forbidden` - User doesn't own the project
- `404 Not Found` - Task not found

---

### Assign Task

Assigns or reassigns a task to an agent or user.

**Endpoint:** `POST /api/v1/tasks/{task_id}/assign`

**Authentication:** Required (JWT)

**Request Body:**

```json
{
  "assigned_to": "uuid-agent-id",
  "assigned_to_type": "agent"
}
```

**Response:** `200 OK`

```json
{
  "id": "uuid-task-id",
  "project_id": "uuid-project-id",
  "room_id": "uuid-room-id",
  "title": "Implement authentication system",
  "description": "Add JWT-based authentication to the API",
  "status": "pending",
  "priority": "high",
  "assigned_to": "uuid-agent-id",
  "assigned_to_type": "agent",
  "created_by": "uuid-user-id",
  "dependencies": [],
  "started_at": null,
  "completed_at": null,
  "due_date": "2026-02-15T12:00:00Z",
  "result": null,
  "created_at": "2026-02-06T12:00:00Z",
  "updated_at": "2026-02-06T12:01:00Z"
}
```

**Error Responses:**

- `403 Forbidden` - User doesn't own the project
- `404 Not Found` - Task not found

---

## Error Codes

| HTTP Code | Error Key | Description |
|-----------|-----------|-------------|
| 400 | VALIDATION_ERROR | Request validation failed |
| 400 | DEPENDENCY_NOT_FOUND | Referenced dependency task does not exist |
| 400 | DEPENDENCY_NOT_COMPLETED | Referenced dependency task is not completed |
| 403 | FORBIDDEN | User lacks permission to access the resource |
| 404 | PROJECT_NOT_FOUND | Project does not exist |
| 404 | AGENT_NOT_FOUND | Agent does not exist |
| 404 | TASK_NOT_FOUND | Task does not exist |
| 409 | DUPLICATE_AGENT_NAME | Agent name already exists in project |

**Error Response Format:**

```json
{
  "detail": "에이전트를 찾을 수 없습니다"
}
```

---

## Data Models

### AgentStatus Enum

| Value | Description |
|-------|-------------|
| `online` | Agent is actively connected |
| `offline` | Agent is not connected |
| `busy` | Agent is processing a task |
| `error` | Agent encountered an error |

### TaskStatus Enum

| Value | Description |
|-------|-------------|
| `pending` | Task is waiting to be started |
| `in_progress` | Task is currently being worked on |
| `review` | Task is under review |
| `completed` | Task has been completed |
| `blocked` | Task is blocked by dependencies |
| `cancelled` | Task was cancelled |

### TaskPriority Enum

| Value | Description |
|-------|-------------|
| `low` | Low priority task |
| `medium` | Medium priority task |
| `high` | High priority task |
| `critical` | Critical priority task |

---

## Pagination

All list endpoints support pagination:

- `page`: Page number (1-indexed, default: 1)
- `size`: Items per page (default: 20, max: 100)

**Response Fields:**

- `items`: Array of results
- `total`: Total number of items matching query
- `page`: Current page number
- `size`: Items per page
- `has_more`: Whether more items exist

---

## Related Documentation

- [Database Schema](#database-schema) - Complete database model documentation
- [Authentication Guide](/docs/SECURITY.md) - Authentication and authorization details
- [API Architecture](/docs/SYSTEM_ARCHITECTURE.md) - System architecture overview
