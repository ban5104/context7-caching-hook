-- Add session_logs table to Supabase
-- This table tracks context provision sessions and their effectiveness

-- Drop existing table if it exists (for clean setup)
DROP TABLE IF EXISTS session_logs CASCADE;

-- Session Logs table
CREATE TABLE session_logs (
    log_id SERIAL PRIMARY KEY,
    session_id TEXT NOT NULL,
    cache_key TEXT NOT NULL,
    operation_type TEXT NOT NULL,
    sections_provided JSONB NOT NULL,
    tokens_used INTEGER NOT NULL,
    tool_name TEXT NOT NULL,
    tool_input JSONB NOT NULL,
    file_path TEXT,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    
    -- Session outcome tracking
    session_complete BOOLEAN DEFAULT NULL,
    follow_up_actions JSONB DEFAULT NULL,
    
    -- LLM effectiveness analysis
    effectiveness_score REAL DEFAULT NULL CHECK (effectiveness_score IS NULL OR (effectiveness_score >= 0 AND effectiveness_score <= 1)),
    effectiveness_reason TEXT DEFAULT NULL,
    confidence_score REAL DEFAULT NULL CHECK (confidence_score IS NULL OR (confidence_score >= 0 AND confidence_score <= 1)),
    analyzed_at TIMESTAMPTZ DEFAULT NULL,
    
    -- Foreign key to context_cache
    FOREIGN KEY (cache_key) REFERENCES context_cache(cache_key) ON DELETE CASCADE
);

-- Indexes for session_logs
CREATE INDEX idx_session_logs_session ON session_logs(session_id, timestamp);
CREATE INDEX idx_session_logs_cache_key ON session_logs(cache_key);
CREATE INDEX idx_session_logs_unanalyzed ON session_logs(analyzed_at) WHERE analyzed_at IS NULL;
CREATE INDEX idx_session_logs_timestamp ON session_logs(timestamp);

-- Enable Row Level Security
ALTER TABLE session_logs ENABLE ROW LEVEL SECURITY;

-- Create policy for authenticated users
CREATE POLICY "Allow all for authenticated users" ON session_logs
    FOR ALL USING (auth.role() = 'authenticated');

-- View for effectiveness insights
CREATE OR REPLACE VIEW session_effectiveness_summary AS
SELECT 
    s.cache_key,
    c.framework,
    c.component,
    s.operation_type,
    COUNT(s.log_id) as total_sessions,
    COUNT(CASE WHEN s.session_complete = TRUE THEN 1 END) as completed_sessions,
    AVG(s.effectiveness_score) FILTER (WHERE s.effectiveness_score IS NOT NULL) as avg_effectiveness,
    AVG(s.confidence_score) FILTER (WHERE s.confidence_score IS NOT NULL) as avg_confidence,
    COUNT(CASE WHEN s.effectiveness_score IS NOT NULL THEN 1 END) as analyzed_count
FROM session_logs s
JOIN context_cache c ON s.cache_key = c.cache_key
GROUP BY s.cache_key, c.framework, c.component, s.operation_type;

-- View for recent unanalyzed sessions
CREATE OR REPLACE VIEW unanalyzed_sessions AS
SELECT 
    s.*,
    c.framework,
    c.component
FROM session_logs s
JOIN context_cache c ON s.cache_key = c.cache_key
WHERE s.analyzed_at IS NULL
    AND s.timestamp < NOW() - INTERVAL '5 minutes'
ORDER BY s.timestamp ASC;