-- Supabase schema for Context7 Cache System (Cache Only)
-- This creates only the context_cache table for documentation storage

-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Drop existing table if it exists (for clean setup)
DROP TABLE IF EXISTS context_cache CASCADE;

-- Context Cache table - stores cached documentation
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
CREATE INDEX idx_cache_component ON context_cache(component) WHERE component IS NOT NULL;

-- Row Level Security (RLS)
ALTER TABLE context_cache ENABLE ROW LEVEL SECURITY;

-- Create policies (adjust based on your auth strategy)
-- For now, allowing all authenticated users full access
CREATE POLICY "Allow all for authenticated users" ON context_cache
    FOR ALL USING (auth.role() = 'authenticated');

-- Useful view for cache statistics
CREATE OR REPLACE VIEW cache_statistics AS
SELECT 
    framework,
    COUNT(*) as total_cached,
    SUM(access_count) as total_accesses,
    AVG(total_tokens) as avg_tokens,
    MAX(last_accessed) as last_used,
    COUNT(CASE WHEN expires_at > NOW() THEN 1 END) as active_entries,
    COUNT(CASE WHEN expires_at <= NOW() THEN 1 END) as expired_entries
FROM context_cache
GROUP BY framework
ORDER BY total_accesses DESC;

-- View for framework usage overview
CREATE OR REPLACE VIEW framework_overview AS
SELECT 
    framework,
    component,
    cache_key,
    total_tokens,
    access_count,
    last_accessed,
    expires_at,
    CASE 
        WHEN expires_at > NOW() THEN 'active'
        ELSE 'expired'
    END as status
FROM context_cache
ORDER BY framework, access_count DESC;