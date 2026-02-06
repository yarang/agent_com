# Agent and Task API Quick Start Guide

**Version:** 1.0.0
**Last Updated:** 2026-02-06

---

## Overview

This guide helps you quickly get started with the Agent and Task API endpoints. You'll learn how to create agents, manage tasks, and verify data persistence.

### Prerequisites

- Running MCP Broker Server instance
- Valid JWT authentication token
- curl or similar HTTP client
- Existing project UUID

---

## Authentication

All API endpoints require JWT authentication. First, obtain your token:

```bash
# Login to get JWT token
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "your-email@example.com",
    "password": "your-password"
  }'

# Save the token for subsequent requests
export JWT_TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

---

## Agent Management

### 1. Create an Agent

Create a new AI agent in your project:

```bash
curl -X POST http://localhost:8000/api/v1/agents \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "your-project-uuid",
    "name": "FrontendExpert",
    "nickname": "Frontend Expert",
    "agent_type": "generic",
    "capabilities": ["communicate", "create_meetings", "code_review"],
    "config": {
      "model": "claude-3-opus",
      "temperature": 0.7,
      "max_tokens": 4000
    }
  }'
```

**Response (201 Created):**

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "project_id": "your-project-uuid",
  "name": "FrontendExpert",
  "nickname": "Frontend Expert",
  "agent_type": "generic",
  "status": "offline",
  "capabilities": ["communicate", "create_meetings", "code_review"],
  "config": {
    "model": "claude-3-opus",
    "temperature": 0.7,
    "max_tokens": 4000
  },
  "is_active": true,
  "created_at": "2026-02-06T12:00:00Z",
  "updated_at": "2026-02-06T12:00:00Z"
}
```

### 2. List All Agents

Retrieve all agents with pagination:

```bash
curl -X GET "http://localhost:8000/api/v1/agents?page=1&size=20" \
  -H "Authorization: Bearer $JWT_TOKEN"
```

**Filter by Project:**

```bash
curl -X GET "http://localhost:8000/api/v1/agents?project_id=your-project-uuid" \
  -H "Authorization: Bearer $JWT_TOKEN"
```

**Filter by Status:**

```bash
curl -X GET "http://localhost:8000/api/v1/agents?status=online" \
  -H "Authorization: Bearer $JWT_TOKEN"
```

**Response (200 OK):**

```json
{
  "items": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "project_id": "your-project-uuid",
      "name": "FrontendExpert",
      "nickname": "Frontend Expert",
      "agent_type": "generic",
      "status": "offline",
      "capabilities": ["communicate", "create_meetings", "code_review"],
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

### 3. Get a Specific Agent

Retrieve details of a specific agent:

```bash
curl -X GET "http://localhost:8000/api/v1/agents/550e8400-e29b-41d4-a716-446655440000" \
  -H "Authorization: Bearer $JWT_TOKEN"
```

### 4. Update an Agent

Update agent status or capabilities:

```bash
curl -X PATCH "http://localhost:8000/api/v1/agents/550e8400-e29b-41d4-a716-446655440000" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "online",
    "capabilities": ["communicate", "create_meetings", "code_review", "debugging"]
  }'
```

**Common Updates:**

```bash
# Set agent to online
curl -X PATCH "http://localhost:8000/api/v1/agents/{agent_id}" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"status": "online"}'

# Deactivate agent
curl -X PATCH "http://localhost:8000/api/v1/agents/{agent_id}" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"is_active": false}'

# Update configuration
curl -X PATCH "http://localhost:8000/api/v1/agents/{agent_id}" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"config": {"model": "claude-3-opus-20240229", "temperature": 0.5}}'
```

### 5. Delete an Agent

Delete an agent (CASCADE to API keys and chat participants):

```bash
curl -X DELETE "http://localhost:8000/api/v1/agents/550e8400-e29b-41d4-a716-446655440000" \
  -H "Authorization: Bearer $JWT_TOKEN"
```

**Warning:** This will also delete:
- All API keys associated with the agent
- All chat participant records for the agent

---

## Task Management

### 1. Create a Task

Create a new task in your project:

```bash
curl -X POST http://localhost:8000/api/v1/tasks \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "your-project-uuid",
    "title": "Implement user authentication",
    "description": "Add JWT-based authentication to the API endpoints",
    "priority": "high",
    "dependencies": [],
    "due_date": "2026-02-15T12:00:00Z"
  }'
```

**Response (201 Created):**

```json
{
  "id": "660e8400-e29b-41d4-a716-446655440000",
  "project_id": "your-project-uuid",
  "room_id": null,
  "title": "Implement user authentication",
  "description": "Add JWT-based authentication to the API endpoints",
  "status": "pending",
  "priority": "high",
  "assigned_to": null,
  "assigned_to_type": null,
  "created_by": "user-uuid",
  "dependencies": [],
  "started_at": null,
  "completed_at": null,
  "due_date": "2026-02-15T12:00:00Z",
  "result": null,
  "created_at": "2026-02-06T12:00:00Z",
  "updated_at": "2026-02-06T12:00:00Z"
}
```

### 2. Create a Task with Dependencies

Create a task that depends on other tasks:

```bash
# First create the dependency task
curl -X POST http://localhost:8000/api/v1/tasks \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "your-project-uuid",
    "title": "Design database schema",
    "status": "completed"
  }'

# Then create a task that depends on it
curl -X POST http://localhost:8000/api/v1/tasks \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "your-project-uuid",
    "title": "Implement database models",
    "dependencies": ["660e8400-e29b-41d4-a716-446655440000"]
  }'
```

**Note:** All dependency tasks must exist and be completed before creating the dependent task.

### 3. List All Tasks

Retrieve all tasks with pagination:

```bash
curl -X GET "http://localhost:8000/api/v1/tasks?page=1&size=20" \
  -H "Authorization: Bearer $JWT_TOKEN"
```

**Filter by Status:**

```bash
curl -X GET "http://localhost:8000/api/v1/tasks?status=pending" \
  -H "Authorization: Bearer $JWT_TOKEN"
```

**Filter by Assignee:**

```bash
curl -X GET "http://localhost:8000/api/v1/tasks?assigned_to=agent-uuid" \
  -H "Authorization: Bearer $JWT_TOKEN"
```

### 4. Update a Task

Update task status or other fields:

```bash
curl -X PATCH "http://localhost:8000/api/v1/tasks/660e8400-e29b-41d4-a716-446655440000" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "in_progress"
  }'
```

**Automatic Timestamps:**

When you update the status:
- `pending` → `in_progress`: `started_at` is set automatically
- `in_progress` → `completed`: `completed_at` is set automatically

**Complete a Task:**

```bash
curl -X PATCH "http://localhost:8000/api/v1/tasks/{task_id}" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "completed",
    "result": {
      "output": "Task completed successfully",
      "metrics": {"time_spent": "2 hours"}
    }
  }'
```

### 5. Assign a Task

Assign a task to an agent or user:

```bash
curl -X POST "http://localhost:8000/api/v1/tasks/660e8400-e29b-41d4-a716-446655440000/assign" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "assigned_to": "550e8400-e29b-41d4-a716-446655440000",
    "assigned_to_type": "agent"
  }'
```

**Assign to a User:**

```bash
curl -X POST "http://localhost:8000/api/v1/tasks/{task_id}/assign" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "assigned_to": "user-uuid",
    "assigned_to_type": "user"
  }'
```

### 6. Delete a Task

Delete a task:

```bash
curl -X DELETE "http://localhost:8000/api/v1/tasks/660e8400-e29b-41d4-a716-446655440000" \
  -H "Authorization: Bearer $JWT_TOKEN"
```

---

## Verifying Data Persistence

### Test Agent Persistence

1. Create an agent
2. Restart the application
3. List agents - the agent should still exist

```bash
# 1. Create agent
curl -X POST http://localhost:8000/api/v1/agents \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"project_id": "your-project-uuid", "name": "TestAgent"}'

# 2. Restart application (in another terminal)
pkill -f "python -m communication_server" && python -m communication_server

# 3. Verify agent persists
curl -X GET "http://localhost:8000/api/v1/agents?project_id=your-project-uuid" \
  -H "Authorization: Bearer $JWT_TOKEN"
```

### Test Task Persistence

1. Create a task
2. Refresh the page or restart the application
3. List tasks - the task should still exist

```bash
# 1. Create task
curl -X POST http://localhost:8000/api/v1/tasks \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"project_id": "your-project-uuid", "title": "Test Task"}'

# 2. Restart application
pkill -f "python -m communication_server" && python -m communication_server

# 3. Verify task persists
curl -X GET "http://localhost:8000/api/v1/tasks?project_id=your-project-uuid" \
  -H "Authorization: Bearer $JWT_TOKEN"
```

---

## Common Use Cases

### Use Case 1: Onboard a New Agent

```bash
# 1. Create the agent
curl -X POST http://localhost:8000/api/v1/agents \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "your-project-uuid",
    "name": "BackendDev",
    "nickname": "Backend Developer",
    "capabilities": ["api-development", "database-design"]
  }'

# 2. Create tasks for the agent
curl -X POST http://localhost:8000/api/v1/tasks \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "your-project-uuid",
    "title": "Design REST API",
    "description": "Create REST API endpoints for user management"
  }'

# 3. Assign the task to the agent
curl -X POST "http://localhost:8000/api/v1/tasks/{task_id}/assign" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "assigned_to": "agent-uuid",
    "assigned_to_type": "agent"
  }'

# 4. Set agent to online
curl -X PATCH "http://localhost:8000/api/v1/agents/{agent_id}" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"status": "online"}'
```

### Use Case 2: Create a Task Workflow

```bash
# 1. Create first task (no dependencies)
TASK1=$(curl -s -X POST http://localhost:8000/api/v1/tasks \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "your-project-uuid",
    "title": "Design database schema",
    "status": "completed"
  }' | jq -r '.id')

# 2. Create second task (depends on first)
TASK2=$(curl -s -X POST http://localhost:8000/api/v1/tasks \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"project_id\": \"your-project-uuid\",
    \"title\": \"Implement database models\",
    \"dependencies\": [\"$TASK1\"]
  }" | jq -r '.id')

# 3. Create third task (depends on second)
curl -X POST http://localhost:8000/api/v1/tasks \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"project_id\": \"your-project-uuid\",
    \"title\": \"Create API endpoints\",
    \"dependencies\": [\"$TASK2\"]
  }"
```

### Use Case 3: Monitor Agent Status

```bash
# Get all online agents
curl -X GET "http://localhost:8000/api/v1/agents?status=online" \
  -H "Authorization: Bearer $JWT_TOKEN"

# Get all busy agents
curl -X GET "http://localhost:8000/api/v1/agents?status=busy" \
  -H "Authorization: Bearer $JWT_TOKEN"

# Get all active agents
curl -X GET "http://localhost:8000/api/v1/agents?is_active=true" \
  -H "Authorization: Bearer $JWT_TOKEN"
```

---

## Error Handling

### Common Error Codes

| Code | Description | Solution |
|------|-------------|----------|
| 400 | Bad Request | Check request body format |
| 403 | Forbidden | Verify you own the project |
| 404 | Not Found | Check the resource ID |
| 409 | Conflict | Agent name already exists in project |

### Example Error Response

```json
{
  "detail": "프로젝트에 이미 'FrontendExpert' 이름의 에이전트가 존재습니다"
}
```

---

## Next Steps

- Read the complete [Agent and Task API Documentation](AGENT_TASK_API.md)
- Review the [Agent and Task Architecture](AGENT_TASK_ARCHITECTURE.md)
- Check the [Migration Guide](AGENT_TASK_MIGRATION.md) if upgrading

---

**Last Updated:** 2026-02-06
**Version:** 1.0.0
