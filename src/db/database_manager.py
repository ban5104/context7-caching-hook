# ~/projects/cc-rag/src/db/database_manager.py
import sqlite3
import json
import os
from pathlib import Path
from datetime import datetime, timedelta
from contextlib import contextmanager
from typing import Dict, Optional, Any


class DatabaseManager:
    """Manages the SQLite database for context caching."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or (Path.home() / '.claude' / 'context7_cache.db')
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()

    @contextmanager
    def get_connection(self):
        """Provides a transactional database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_database(self):
        """Initializes the cache table if it doesn't exist."""
        with self.get_connection() as conn:
            conn.executescript('''
                CREATE TABLE IF NOT EXISTS context_cache (
                    cache_key TEXT PRIMARY KEY,
                    framework TEXT NOT NULL,
                    component TEXT,
                    full_content TEXT NOT NULL,
                    sections JSON NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    access_count INTEGER DEFAULT 0,
                    total_tokens INTEGER NOT NULL,
                    expires_at TIMESTAMP NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_cache_framework ON context_cache(framework);
                
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
                    
                    session_complete BOOLEAN DEFAULT NULL,
                    follow_up_actions JSON DEFAULT NULL,
                    
                    effectiveness_score REAL DEFAULT NULL,
                    effectiveness_reason TEXT DEFAULT NULL,
                    confidence_score REAL DEFAULT NULL,
                    analyzed_at TIMESTAMP DEFAULT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_session_logs_session ON session_logs(session_id, timestamp);
                CREATE INDEX IF NOT EXISTS idx_session_logs_cache_key ON session_logs(cache_key);
                CREATE INDEX IF NOT EXISTS idx_session_logs_unanalyzed ON session_logs(analyzed_at) WHERE analyzed_at IS NULL;
            ''')

    def store_context(self, cache_key: str, framework: str, content: str, sections: Dict[str, str]):
        """Stores or replaces documentation in the cache."""
        with self.get_connection() as conn:
            expires_at = datetime.now() + timedelta(hours=24)
            conn.execute('''
                INSERT OR REPLACE INTO context_cache
                (cache_key, framework, component, full_content, sections, total_tokens, expires_at, access_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, COALESCE((SELECT access_count FROM context_cache WHERE cache_key = ?), 0))
            ''', (
                cache_key, framework, cache_key.split(':')[1] if ':' in cache_key else None,
                content, json.dumps(sections), len(content.split()), expires_at, cache_key
            ))
            
            # Auto-sync to Supabase if configured (async, non-blocking)
            self._sync_cache_to_supabase_async(cache_key)

    def get_cache_data(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Retrieves cached data, updating access metrics."""
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM context_cache WHERE cache_key = ? AND expires_at > ?",
                (cache_key, datetime.now())
            ).fetchone()

            if row:
                conn.execute(
                    "UPDATE context_cache SET last_accessed = ?, access_count = access_count + 1 WHERE cache_key = ?",
                    (datetime.now(), cache_key)
                )
                return dict(row)
        return None

    def log_session(self, session_id: str, cache_key: str, operation_type: str, 
                   sections: list, tokens: int, tool_name: str, 
                   tool_input: dict, file_path: str = None) -> int:
        """Log a session event and return the log_id."""
        with self.get_connection() as conn:
            cursor = conn.execute('''
                INSERT INTO session_logs 
                (session_id, cache_key, operation_type, sections_provided, 
                 tokens_used, tool_name, tool_input, file_path)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                session_id, cache_key, operation_type,
                json.dumps(sections), tokens, tool_name, 
                json.dumps(tool_input), file_path
            ))
            return cursor.lastrowid

    def update_session_outcome(self, log_id: int, session_complete: bool, 
                              follow_up_actions: list = None) -> None:
        """Update a session log with outcome data."""
        with self.get_connection() as conn:
            conn.execute('''
                UPDATE session_logs 
                SET session_complete = ?, follow_up_actions = ?
                WHERE log_id = ?
            ''', (session_complete, json.dumps(follow_up_actions) if follow_up_actions else None, log_id))

    def update_effectiveness_analysis(self, log_id: int, effectiveness_score: float,
                                    effectiveness_reason: str, confidence_score: float) -> None:
        """Update a session log with LLM effectiveness analysis."""
        with self.get_connection() as conn:
            conn.execute('''
                UPDATE session_logs 
                SET effectiveness_score = ?, effectiveness_reason = ?, 
                    confidence_score = ?, analyzed_at = ?
                WHERE log_id = ?
            ''', (effectiveness_score, effectiveness_reason, confidence_score, datetime.now(), log_id))
    
    def update_session_intelligence(self, log_id: int, was_effective: bool, 
                                  reasoning: str, confidence: float, rule_updated: bool):
        """Update a session log with intelligent analysis results."""
        # Convert boolean to effectiveness score for backward compatibility
        effectiveness_score = 0.8 if was_effective else 0.2
        
        # Add rule update info to reasoning
        if rule_updated:
            reasoning = f"{reasoning} [RULE UPDATED]"
        
        with self.get_connection() as conn:
            conn.execute('''
                UPDATE session_logs 
                SET effectiveness_score = ?, 
                    effectiveness_reason = ?,
                    confidence_score = ?,
                    analyzed_at = CURRENT_TIMESTAMP,
                    session_complete = ?
                WHERE log_id = ?
            ''', (effectiveness_score, reasoning, confidence, was_effective, log_id))

    def get_unanalyzed_sessions(self, limit: int = 50) -> list:
        """Get sessions that haven't been analyzed by LLM yet."""
        with self.get_connection() as conn:
            rows = conn.execute('''
                SELECT * FROM session_logs 
                WHERE analyzed_at IS NULL 
                AND timestamp < datetime('now', '-5 minutes')
                ORDER BY timestamp ASC 
                LIMIT ?
            ''', (limit,)).fetchall()
            return [dict(row) for row in rows]

    def get_effectiveness_insights(self, days: int = 7) -> dict:
        """Get aggregated effectiveness data for learning."""
        with self.get_connection() as conn:
            results = conn.execute('''
                SELECT 
                    c.framework,
                    l.operation_type,
                    json_each.value as section_name,
                    AVG(l.effectiveness_score) as avg_effectiveness,
                    COUNT(l.log_id) as usage_count,
                    AVG(l.confidence_score) as avg_confidence
                FROM session_logs l
                JOIN context_cache c ON l.cache_key = c.cache_key
                JOIN json_each(l.sections_provided)
                WHERE l.timestamp > datetime('now', '-' || ? || ' days')
                  AND l.effectiveness_score IS NOT NULL
                GROUP BY 1, 2, 3
                HAVING usage_count >= 3
                ORDER BY avg_effectiveness DESC
            ''', (days,)).fetchall()
            
            insights = {}
            for row in results:
                key = f"{row['framework']}:{row['operation_type']}"
                if key not in insights:
                    insights[key] = []
                insights[key].append(dict(row))
            return insights
    
    
    def _sync_cache_to_supabase_async(self, cache_key: str):
        """Sync cache entry to Supabase asynchronously (non-blocking)"""
        import threading
        import subprocess
        
        def sync_in_background():
            try:
                # Call the dedicated sync script using uv
                script_path = Path(__file__).parent.parent.parent / 'scripts' / 'sync_to_supabase.py'
                subprocess.run(['uv', 'run', str(script_path)], 
                             capture_output=True, 
                             text=True,
                             cwd=str(script_path.parent.parent))
            except Exception:
                # Silently fail - don't break the main workflow
                pass
        
        # Start sync in background thread - won't block main process
        thread = threading.Thread(target=sync_in_background, daemon=True)
        thread.start()