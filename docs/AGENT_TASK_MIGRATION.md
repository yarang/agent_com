# Agent and Task Persistence Migration Guide

**Version:** 1.0.0
**Last Updated:** 2026-02-06
**SPEC:** SPEC-AGENT-PERSISTENCE-001

---

## Overview

This guide helps you migrate from the previous in-memory agent and task system to the new database-backed persistence system. The migration ensures no data loss while adding proper referential integrity.

### What Changed?

**Before Migration:**
- Agents only existed implicitly through API keys
- Tasks were only stored in memory (lost on refresh)
- Orphaned `agent_id` fields without foreign key constraints
- No referential integrity for agent references

**After Migration:**
- Complete AgentDB model with full persistence
- Complete TaskDB model with dependency tracking
- Foreign key constraints on all agent_id references
- Full data persistence across application restarts

---

## Pre-Migration Checklist

### 1. Backup Your Database

Before running the migration, create a backup:

```bash
# PostgreSQL
pg_dump -U username -d database_name > backup_before_migration.sql

# SQLite
cp database.db backup_before_migration.db
```

### 2. Verify Current State

Check for orphaned agent_id records:

```sql
-- Check chat_participants for orphaned agent_ids
SELECT DISTINCT agent_id
FROM chat_participants
WHERE agent_id IS NOT NULL
  AND agent_id NOT IN (SELECT id FROM agents);  -- Will be all records before migration

-- Check agent_api_keys for orphaned agent_ids
SELECT DISTINCT agent_id
FROM agent_api_keys
WHERE agent_id IS NOT NULL
  AND agent_id NOT IN (SELECT id FROM agents);  -- Will be all records before migration
```

### 3. Stop Application

Stop the application before running the migration:

```bash
# Stop the server
pkill -f "python -m communication_server"
# or
systemctl stop mcp-broker
```

---

## Migration Steps

### Step 1: Upgrade Database

Run the Alembic migration:

```bash
# Activate virtual environment
source .venv/bin/activate

# Run migration
alembic upgrade head
```

**What the migration does:**

1. Creates `agents` table with all columns and indexes
2. Creates `tasks` table with all columns and indexes
3. Scans for orphaned `agent_id` values in existing tables
4. Creates placeholder `AgentDB` records for valid orphaned IDs
5. Adds FK constraints to `chat_participants.agent_id`
6. Adds FK constraints to `agent_api_keys.agent_id`
7. Verifies all references are valid

**Expected Output:**

```
INFO  [alembic.runtime.migration] Running upgrade 002_add_agent_api_key_user_fk -> 003_create_agent_and_task_tables
INFO  [alembic.runtime.migration] Creating agents table...
INFO  [alembic.runtime.migration] Creating tasks table...
INFO  [alembic.runtime.migration] Processing orphaned agent_ids...
INFO  [alembic.runtime.migration] Created 3 placeholder agents
INFO  [alembic.runtime.migration] Adding foreign key constraints...
INFO  [alembic.runtime.migration] Migration complete
```

### Step 2: Verify Migration

Check that the migration was successful:

```sql
-- Verify agents table exists
\d agents

-- Verify tasks table exists
\d tasks

-- Check foreign key constraints
SELECT
    conname AS constraint_name,
    conrelid::regclass AS table_name,
    confrelid::regclass AS referenced_table
FROM pg_constraint
WHERE conrelid::regclass IN ('chat_participants', 'agent_api_keys')
  AND contype = 'f';

-- Verify placeholder agents were created
SELECT id, name, status, is_active
FROM agents
WHERE name LIKE 'Migrated Agent%';
```

### Step 3: Update Application Code

If you have any code that references agents, update it:

**Before:**

```python
# Old way - agent only existed implicitly
agent_id = some_uuid_from_api_key
```

**After:**

```python
# New way - agent exists in database
from agent_comm_core.db.models.agent import AgentDB
from sqlalchemy import select

agent = await session.execute(
    select(AgentDB).where(AgentDB.id == agent_id)
)
agent = agent.scalar_one_or_none()
```

### Step 4: Restart Application

Start the application:

```bash
# Development
python -m communication_server

# Production
systemctl start mcp-broker
```

---

## Post-Migration Tasks

### 1. Update Agent Names

Placeholder agents created during migration have names like "Migrated Agent {uuid}". Update these to meaningful names:

```bash
# Update agent names via API
curl -X PATCH http://localhost:8000/api/v1/agents/{agent_id} \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "FrontendExpert",
    "nickname": "Frontend Expert"
  }'
```

### 2. Verify Data Integrity

Check that all data is intact:

```sql
-- Verify no orphaned agent_ids remain
SELECT COUNT(*) FROM chat_participants
WHERE agent_id IS NOT NULL
  AND agent_id NOT IN (SELECT id FROM agents);

-- Should return 0

-- Verify agent_api_keys have valid agent references
SELECT COUNT(*) FROM agent_api_keys
WHERE agent_id NOT IN (SELECT id FROM agents);

-- Should return 0
```

### 3. Test Functionality

Test the new API endpoints:

```bash
# Test creating an agent
curl -X POST http://localhost:8000/api/v1/agents \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "your-project-uuid",
    "name": "TestAgent",
    "capabilities": ["test"]
  }'

# Test creating a task
curl -X POST http://localhost:8000/api/v1/tasks \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "your-project-uuid",
    "title": "Test task",
    "description": "Testing task persistence"
  }'

# Test listing agents
curl -X GET http://localhost:8000/api/v1/agents \
  -H "Authorization: Bearer $JWT_TOKEN"

# Test listing tasks
curl -X GET http://localhost:8000/api/v1/tasks \
  -H "Authorization: Bearer $JWT_TOKEN"
```

---

## Rollback Procedure

If you need to rollback the migration:

### 1. Stop Application

```bash
pkill -f "python -m communication_server"
```

### 2. Downgrade Database

```bash
alembic downgrade -1
```

**What the rollback does:**

1. Removes FK constraints from `chat_participants.agent_id`
2. Removes FK constraints from `agent_api_keys.agent_id`
3. Drops `agents` table
4. Drops `tasks` table

### 3. Restore Backup (if needed)

```bash
# PostgreSQL
psql -U username -d database_name < backup_before_migration.sql

# SQLite
cp backup_before_migration.db database.db
```

### 4. Restart Application

```bash
python -m communication_server
```

---

## Common Issues

### Issue 1: Migration Fails with "Orphaned Records"

**Problem:** Migration fails due to invalid UUID formats in orphaned records.

**Solution:** The migration automatically handles this by setting invalid `agent_id` values to NULL:

```sql
-- Manually fix invalid UUIDs if needed
UPDATE chat_participants
SET agent_id = NULL
WHERE agent_id IS NOT NULL
  AND agent_id::text !~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$';
```

### Issue 2: Foreign Key Constraint Violations

**Problem:** Application throws FK constraint violations after migration.

**Solution:** Verify all agent_ids reference valid agents:

```sql
-- Find invalid references
SELECT cp.id, cp.agent_id
FROM chat_participants cp
LEFT JOIN agents a ON cp.agent_id = a.id
WHERE cp.agent_id IS NOT NULL
  AND a.id IS NULL;

-- Set them to NULL
UPDATE chat_participants
SET agent_id = NULL
WHERE agent_id NOT IN (SELECT id FROM agents);
```

### Issue 3: Agent Name Conflicts

**Problem:** Error "Agent name already exists in project" during agent creation.

**Solution:** Agent names must be unique within a project. Use a different name or update the existing agent:

```bash
# List existing agents
curl -X GET "http://localhost:8000/api/v1/agents?project_id=your-project-uuid" \
  -H "Authorization: Bearer $JWT_TOKEN"

# Update existing agent instead of creating new
curl -X PATCH "http://localhost:8000/api/v1/agents/{existing-agent-id}" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"status": "online"}'
```

---

## Performance Considerations

### Database Indexes

The migration creates indexes for performance:

- `idx_agents_project_id` - Fast project-based queries
- `idx_agents_status` - Fast status filtering
- `idx_agents_is_active` - Fast active state filtering
- `idx_tasks_project_id` - Fast project-based queries
- `idx_tasks_status` - Fast status filtering
- `idx_tasks_assigned_to` - Fast assignee queries

### Query Optimization

For large datasets, consider:

1. **Pagination** - Always use pagination for list endpoints
2. **Filtering** - Apply filters early to reduce result set
3. **Selective Loading** - Only query fields needed for response

---

## Support

If you encounter issues during migration:

1. Check the [Agent and Task API Documentation](AGENT_TASK_API.md)
2. Review the [Agent and Task Architecture](AGENT_TASK_ARCHITECTURE.md)
3. Check application logs for detailed error messages
4. Open an issue on [GitHub](https://github.com/yarang/agent_com/issues)

---

## Checklist

Use this checklist to ensure a successful migration:

- [ ] Database backup created
- [ ] Application stopped
- [ ] Migration script executed successfully
- [ ] Agents table created
- [ ] Tasks table created
- [ ] Foreign key constraints applied
- [ ] No orphaned agent_id references
- [ ] Application restarted successfully
- [ ] Agent creation tested
- [ ] Task creation tested
- [ ] Data persistence verified (restart application)
- [ ] Placeholder agent names updated

---

**Last Updated:** 2026-02-06
**Version:** 1.0.0
