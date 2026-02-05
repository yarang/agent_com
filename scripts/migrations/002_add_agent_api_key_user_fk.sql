-- Migration 002: Add Foreign Key to agent_api_keys.created_by_id
-- This migration adds referential integrity between agent API keys and users
--
-- SPEC: SPEC-AGENT-002 - Agent User Ownership Model
--
-- Changes:
-- 1. Validates existing created_by_id values
-- 2. Adds foreign key constraint: agent_api_keys.created_by_id -> users.id
-- 3. Sets ON DELETE SET NULL behavior
-- 4. Handles orphaned records gracefully

-- Start transaction
BEGIN;

-- Step 1: Validate existing data and identify orphaned records
DO $$
DECLARE
    orphaned_count INTEGER;
BEGIN
    -- Count orphaned records (created_by_id not in users table)
    SELECT COUNT(*) INTO orphaned_count
    FROM agent_api_keys aak
    LEFT JOIN users u ON aak.created_by_id = u.id
    WHERE u.id IS NULL AND aak.created_by_id IS NOT NULL;

    -- Log warning if orphaned records found
    IF orphaned_count > 0 THEN
        RAISE NOTICE 'Found % orphaned agent_api_keys records. Setting created_by_id to NULL.', orphaned_count;
    END IF;
END $$;

-- Step 2: Set orphaned records to NULL
UPDATE agent_api_keys
SET created_by_id = NULL
WHERE created_by_id IS NOT NULL
  AND created_by_id NOT IN (SELECT id FROM users);

-- Step 3: Add foreign key constraint
-- First, check if constraint already exists
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'fk_agent_api_keys_created_by_id_users'
    ) THEN
        ALTER TABLE agent_api_keys
        ADD CONSTRAINT fk_agent_api_keys_created_by_id_users
        FOREIGN KEY (created_by_id) REFERENCES users(id)
        ON DELETE SET NULL;

        RAISE NOTICE 'Foreign key constraint fk_agent_api_keys_created_by_id_users added successfully.';
    ELSE
        RAISE NOTICE 'Foreign key constraint fk_agent_api_keys_created_by_id_users already exists.';
    END IF;
END $$;

-- Step 4: Create index on created_by_id for better query performance
CREATE INDEX IF NOT EXISTS idx_agent_api_keys_created_by_id
ON agent_api_keys(created_by_id);

-- Step 5: Add comment to document the foreign key
COMMENT ON COLUMN agent_api_keys.created_by_id IS 'Foreign key to users.id. Tracks which user created this agent API key. SET NULL on user deletion.';

COMMIT;

-- Verification query (run separately to verify migration)
-- SELECT
--     conname AS constraint_name,
--     pg_get_constraintdef(oid) AS constraint_definition
-- FROM pg_constraint
-- WHERE conrelid = 'agent_api_keys'::regclass
-- AND contype = 'f'
-- AND conname = 'fk_agent_api_keys_created_by_id_users';

-- Rollback command (if needed):
-- ALTER TABLE agent_api_keys DROP CONSTRAINT IF EXISTS fk_agent_api_keys_created_by_id_users;
