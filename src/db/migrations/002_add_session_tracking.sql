-- Add table for tracking context usage and automated effectiveness analysis
CREATE TABLE IF NOT EXISTS session_logs (
    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    cache_key TEXT NOT NULL,
    operation_type TEXT NOT NULL,
    sections_provided JSON NOT NULL,
    tokens_used INTEGER NOT NULL,
    tool_name TEXT NOT NULL,
    tool_input JSON NOT NULL,
    file_path TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Session outcome tracking
    session_complete BOOLEAN DEFAULT NULL,
    follow_up_actions JSON DEFAULT NULL, -- Track what user did next
    
    -- LLM effectiveness analysis (populated later)
    effectiveness_score REAL DEFAULT NULL, -- 0.0 to 1.0
    effectiveness_reason TEXT DEFAULT NULL,
    confidence_score REAL DEFAULT NULL,
    analyzed_at TIMESTAMP DEFAULT NULL
);

CREATE INDEX IF NOT EXISTS idx_session_logs_session ON session_logs(session_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_session_logs_cache_key ON session_logs(cache_key);
CREATE INDEX IF NOT EXISTS idx_session_logs_unanalyzed ON session_logs(analyzed_at) WHERE analyzed_at IS NULL;