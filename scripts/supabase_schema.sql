-- Supabase schema for Context7 Cache System
-- This creates tables that mirror the SQLite database structure

-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Drop existing tables if they exist (for clean setup)
DROP TABLE IF EXISTS context_cache CASCADE;
DROP TABLE IF EXISTS usage_logs CASCADE;
DROP TABLE IF EXISTS extraction_rules CASCADE;
DROP TABLE IF EXISTS schema_version CASCADE;

-- Context Cache table
CREATE TABLE context_cache (
    cache_key TEXT PRIMARY KEY,
    framework TEXT NOT NULL,
    component TEXT,
    full_content TEXT NOT NULL,
    sections JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_accessed TIMESTAMPTZ DEFAULT NOW(),
    access_count INTEGER DEFAULT 0,
    total_tokens INTEGER NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL
);

-- Indexes for context_cache
CREATE INDEX idx_cache_framework ON context_cache(framework);
CREATE INDEX idx_cache_expires ON context_cache(expires_at);
CREATE INDEX idx_cache_sections ON context_cache USING gin(sections);

-- Usage Logs table
CREATE TABLE usage_logs (
    log_id SERIAL PRIMARY KEY,
    session_id TEXT NOT NULL,
    cache_key TEXT NOT NULL,
    operation_type TEXT NOT NULL,
    sections_provided JSONB NOT NULL,
    tokens_used INTEGER NOT NULL,
    tool_name TEXT NOT NULL,
    file_path TEXT,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    was_successful BOOLEAN,
    user_feedback TEXT CHECK (user_feedback IN ('helpful', 'not_helpful') OR user_feedback IS NULL),
    FOREIGN KEY (cache_key) REFERENCES context_cache(cache_key) ON DELETE CASCADE
);

-- Indexes for usage_logs
CREATE INDEX idx_usage_session ON usage_logs(session_id, timestamp);
CREATE INDEX idx_usage_success ON usage_logs(was_successful);
CREATE INDEX idx_usage_feedback ON usage_logs(user_feedback) WHERE user_feedback IS NOT NULL;

-- Extraction Rules table
CREATE TABLE extraction_rules (
    rule_id SERIAL PRIMARY KEY,
    framework TEXT NOT NULL,
    operation_type TEXT NOT NULL,
    sections JSONB NOT NULL,
    max_tokens INTEGER DEFAULT 2000,
    confidence_score REAL DEFAULT 0.7 CHECK (confidence_score >= 0 AND confidence_score <= 1),
    is_default BOOLEAN DEFAULT FALSE,
    usage_count INTEGER DEFAULT 0,
    success_count INTEGER DEFAULT 0,
    UNIQUE(framework, operation_type)
);

-- Index for extraction_rules
CREATE INDEX idx_rules_framework ON extraction_rules(framework, operation_type);

-- Schema Version table
CREATE TABLE schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TIMESTAMPTZ DEFAULT NOW()
);

-- Row Level Security (RLS)
ALTER TABLE context_cache ENABLE ROW LEVEL SECURITY;
ALTER TABLE usage_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE extraction_rules ENABLE ROW LEVEL SECURITY;
ALTER TABLE schema_version ENABLE ROW LEVEL SECURITY;

-- Create policies (adjust based on your auth strategy)
-- For now, allowing all authenticated users full access
CREATE POLICY "Allow all for authenticated users" ON context_cache
    FOR ALL USING (auth.role() = 'authenticated');

CREATE POLICY "Allow all for authenticated users" ON usage_logs
    FOR ALL USING (auth.role() = 'authenticated');

CREATE POLICY "Allow all for authenticated users" ON extraction_rules
    FOR ALL USING (auth.role() = 'authenticated');

CREATE POLICY "Allow all for authenticated users" ON schema_version
    FOR ALL USING (auth.role() = 'authenticated');

-- Useful views
CREATE OR REPLACE VIEW cache_statistics AS
SELECT 
    framework,
    COUNT(*) as total_cached,
    SUM(access_count) as total_accesses,
    AVG(total_tokens) as avg_tokens,
    MAX(last_accessed) as last_used
FROM context_cache
GROUP BY framework;

CREATE OR REPLACE VIEW feedback_summary AS
SELECT 
    c.framework,
    c.component,
    c.cache_key,
    COUNT(CASE WHEN u.user_feedback = 'helpful' THEN 1 END) as helpful_count,
    COUNT(CASE WHEN u.user_feedback = 'not_helpful' THEN 1 END) as not_helpful_count,
    COUNT(u.log_id) as total_uses
FROM context_cache c
LEFT JOIN usage_logs u ON c.cache_key = u.cache_key
GROUP BY c.framework, c.component, c.cache_key;

-- Function to update last_accessed timestamp
CREATE OR REPLACE FUNCTION update_last_accessed()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE context_cache 
    SET last_accessed = NOW(), 
        access_count = access_count + 1
    WHERE cache_key = NEW.cache_key;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to update cache stats on usage
CREATE TRIGGER update_cache_on_usage
AFTER INSERT ON usage_logs
FOR EACH ROW
EXECUTE FUNCTION update_last_accessed();