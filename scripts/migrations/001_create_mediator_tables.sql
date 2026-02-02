-- Migration 001: Create Mediator System Tables
-- This migration creates tables for the mediator system

-- Create mediator_models table
CREATE TABLE IF NOT EXISTS mediator_models (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL UNIQUE,
    provider VARCHAR(50) NOT NULL,
    model_id VARCHAR(100) NOT NULL,
    api_endpoint VARCHAR(255),
    max_tokens INTEGER,
    supports_streaming BOOLEAN DEFAULT FALSE,
    supports_function_calling BOOLEAN DEFAULT FALSE,
    cost_per_1k_tokens VARCHAR(20),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for mediator_models
CREATE INDEX IF NOT EXISTS idx_mediator_models_provider ON mediator_models(provider);
CREATE INDEX IF NOT EXISTS idx_mediator_models_is_active ON mediator_models(is_active);

-- Create mediator_prompts table
CREATE TABLE IF NOT EXISTS mediator_prompts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    category VARCHAR(100) NOT NULL,
    system_prompt TEXT NOT NULL,
    variables JSONB,
    examples JSONB,
    is_public BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for mediator_prompts
CREATE INDEX IF NOT EXISTS idx_mediator_prompts_project ON mediator_prompts(project_id);
CREATE INDEX IF NOT EXISTS idx_mediator_prompts_category ON mediator_prompts(category);
CREATE INDEX IF NOT EXISTS idx_mediator_prompts_is_active ON mediator_prompts(is_active);

-- Create mediators table
CREATE TABLE IF NOT EXISTS mediators (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    model_id UUID NOT NULL REFERENCES mediator_models(id) ON DELETE RESTRICT,
    default_prompt_id UUID REFERENCES mediator_prompts(id) ON DELETE SET NULL,
    system_prompt TEXT,
    temperature VARCHAR(10),
    max_tokens INTEGER,
    is_active BOOLEAN DEFAULT TRUE,
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for mediators
CREATE INDEX IF NOT EXISTS idx_mediators_project ON mediators(project_id);
CREATE INDEX IF NOT EXISTS idx_mediators_model ON mediators(model_id);
CREATE INDEX IF NOT EXISTS idx_mediators_is_active ON mediators(is_active);

-- Create chat_room_mediators junction table
CREATE TABLE IF NOT EXISTS chat_room_mediators (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    room_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    mediator_id UUID NOT NULL REFERENCES mediators(id) ON DELETE CASCADE,
    prompt_id UUID REFERENCES mediator_prompts(id) ON DELETE SET NULL,
    is_active BOOLEAN DEFAULT TRUE,
    auto_trigger BOOLEAN DEFAULT FALSE,
    trigger_keywords TEXT[],
    joined_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(room_id, mediator_id)
);

-- Create indexes for chat_room_mediators
CREATE INDEX IF NOT EXISTS idx_chat_room_mediators_room ON chat_room_mediators(room_id);
CREATE INDEX IF NOT EXISTS idx_chat_room_mediators_mediator ON chat_room_mediators(mediator_id);
CREATE INDEX IF NOT EXISTS idx_chat_room_mediators_is_active ON chat_room_mediators(is_active);

-- Seed default mediator models
INSERT INTO mediator_models (name, provider, model_id, max_tokens, supports_streaming, supports_function_calling)
VALUES
    ('GPT-4 Turbo', 'openai', 'gpt-4-turbo-preview', 128000, TRUE, TRUE),
    ('GPT-4', 'openai', 'gpt-4', 8192, TRUE, TRUE),
    ('GPT-3.5 Turbo', 'openai', 'gpt-3.5-turbo', 16385, TRUE, TRUE),
    ('Claude 3 Opus', 'anthropic', 'claude-3-opus-20240229', 200000, TRUE, TRUE),
    ('Claude 3 Sonnet', 'anthropic', 'claude-3-sonnet-20240229', 200000, TRUE, TRUE),
    ('Claude 3 Haiku', 'anthropic', 'claude-3-haiku-20240307', 200000, TRUE, FALSE)
ON CONFLICT (name) DO NOTHING;

-- Create a function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at
CREATE TRIGGER update_mediator_models_updated_at
    BEFORE UPDATE ON mediator_models
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_mediator_prompts_updated_at
    BEFORE UPDATE ON mediator_prompts
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_mediators_updated_at
    BEFORE UPDATE ON mediators
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
