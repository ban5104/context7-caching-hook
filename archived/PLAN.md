Context7 AI-Optimized Cache System - Implementation Plan v3.0 (Adapted)
Overview
A phased implementation plan for a sophisticated, self-improving caching system for Claude. This plan starts with the current robust foundation and iteratively adds data collection, automated learning, and advanced intelligence, following best practices for iterative development.

Phase 1: Foundation (Current Implemented State)
Goal: Establish a robust, configurable, and secure caching hook.

1.1 Core Components (Current Scripts)
context7_cache_hook.py: The main hook that intercepts Write/Edit tools. It uses a JSON configuration for rules, includes security sanitization, performance bypasses, robust error handling, and structured JSON for communication with Claude.

database_manager.py: A simple, dedicated manager for the SQLite cache (context_cache table only).

basic_extractor.py: A focused utility for extracting sections from documentation based on rules passed to it.

operation_detector.py: A utility for detecting the framework and user intent.

context7_rules.json: A user-configurable JSON file in ~/.claude/ that defines which documentation sections to get for different tasks, externalizing logic from code.

1.2 context7_cache_hook.py
Python

#!/usr/bin/env python3
# ~/projects/cc-rag/hooks/context7_cache_hook.py
import json
import sys
import re
import signal
from pathlib import Path
from datetime import datetime

# Add project src to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from db.database_manager import DatabaseManager
from extractors.basic_extractor import BasicSectionExtractor
from detectors.operation_detector import OperationDetector

def get_extraction_rule(framework: str, operation: str) -> dict:
    """Reads rules from the JSON file and returns the appropriate one with explicit fallbacks."""
    rules_path = Path.home() / '.claude' / 'context7_rules.json'
    fallback_rule = {"sections": ["overview", "example"], "max_tokens": 2000}
    
    if not rules_path.exists():
        return fallback_rule

    with open(rules_path, 'r') as f:
        rules = json.load(f)

    framework_rules = rules.get(framework, {})
    return framework_rules.get(operation, framework_rules.get('defaults', rules.get('defaults', fallback_rule)))

class Context7CacheHook:
    """A robust hook to enforce using cached documentation via Context7."""
    
    def __init__(self):
        self.db = DatabaseManager()
        self.extractor = BasicSectionExtractor()
        self.detector = OperationDetector()

    def _sanitize_cache_key(self, key: str) -> str:
        """Sanitize cache keys to prevent injection attacks."""
        if '..' in key or key.startswith('/'):
            raise ValueError(f"Invalid cache key: path traversal attempt blocked.")
        if not re.match(r'^[a-zA-Z0-9:._-]+$', key):
            raise ValueError(f"Invalid cache key format: contains invalid characters.")
        return key

    def _should_bypass(self, tool_input: dict) -> bool:
        """Determine if context fetching should be bypassed for performance."""
        content = tool_input.get('content', '')
        file_path = tool_input.get('file_path', '')
        if len(content.strip()) < 50: return True
        if file_path and not any(file_path.endswith(ext) for ext in ['.js', '.jsx', '.ts', '.tsx', '.py', '.html', '.css']):
            return True
        return False

    def process(self, input_data: dict):
        """Processes the hook input and directs Claude using JSON output."""
        tool_name = input_data.get('tool_name')
        tool_input = input_data.get('tool_input', {})
        
        # Helper command to view rules
        if tool_input.get('command') == 'context7-rules':
            rules_path = Path.home() / '.claude' / 'context7_rules.json'
            output = rules_path.read_text() if rules_path.exists() else "No context7_rules.json file found."
            print(json.dumps({"decision": "block", "reason": output}))
            sys.exit(0)

        # Check for relevant tools, including MCP variants
        is_valid_tool = (tool_name in ['Write', 'Edit', 'MultiEdit']) or \
                        (re.match(r'mcp__.*__(write|edit|multi_edit)', tool_name or ""))
        if not is_valid_tool or self._should_bypass(tool_input):
            sys.exit(0)

        content = tool_input.get('content', '')
        file_path = tool_input.get('file_path', '')
        framework = self.detector.detect_framework(content, file_path)
        if not framework: sys.exit(0)

        operation_type = self.detector.detect_operation(content, file_path)
        component = self.detector.extract_component(content, file_path, framework)
        
        try:
            raw_key = f"{framework}:{component}" if component else framework
            cache_key = self._sanitize_cache_key(raw_key)
        except ValueError as e:
            print(json.dumps({"decision": "block", "reason": f"Error: {e}"}))
            sys.exit(0)

        cached_data = self.db.get_cache_data(cache_key)
        rule = get_extraction_rule(framework, operation_type)

        if cached_data:
            sections = json.loads(cached_data['sections'])
            extracted_content, sections_used = self.extractor.extract_relevant_sections(
                sections, rule, token_budget=rule.get('max_tokens', 2000)
            )
            reason = self._format_response(framework, extracted_content, cache_key, sections_used)
            output = {"decision": "block", "reason": reason}
        else:
            reason = self._format_fetch_instructions(framework, rule, cache_key)
            output = {"decision": "block", "reason": reason}

        print(json.dumps(output))
        sys.exit(0)

    def _format_response(self, framework: str, content: str, cache_key: str, sections_used: list) -> str:
        """Formats the response when cached content is found."""
        return f"""Using cached {framework} documentation to complete your request.
Sections retrieved: {', '.join(sections_used)}.

<context>
{content}
</context>

---
Cache Key: {cache_key}
"""

    def _format_fetch_instructions(self, framework: str, rule: dict, cache_key: str) -> str:
        """Formats instructions for Claude when documentation is not in the cache."""
        sections_to_extract = rule.get('sections', ['overview', 'example', 'usage', 'api'])
        return f"""The required {framework} documentation is not in the cache.

1. Use `Context7:get-library-docs('{framework}')`.
2. Extract the content for these sections: {', '.join(sections_to_extract)}.
3. Cache the result with `Context7:cache-context('{cache_key}', 'extracted content')`.
4. Retry your original request.
"""

def main():
    """Main entry point with robust error handling and timeout."""
    def timeout_handler(signum, frame):
        raise TimeoutError("Hook script timed out after 55 seconds.")
    
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(55)

    try:
        input_data = json.load(sys.stdin)
        hook = Context7CacheHook()
        hook.process(input_data)
    except json.JSONDecodeError as e:
        print(f"Hook Error: Invalid JSON input from stdin: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        log_path = Path.home() / '.claude' / 'hook_errors.log'
        with open(log_path, 'a') as f:
            f.write(f"[{datetime.now().isoformat()}] {type(e).__name__}: {e}\n")
        sys.exit(0)

if __name__ == "__main__":
    main()
Phase 2: Explicit Feedback & Usage Logging
Goal: Begin collecting data on how the cache is used and whether it's effective. This is the foundation for all future learning.

2.1 Database Schema Enhancement
Create a migration file to add the usage_logs table.

~/projects/cc-rag/src/db/migrations/002_add_usage_logs.sql:

SQL

-- Add table for tracking context usage and feedback
CREATE TABLE IF NOT EXISTS usage_logs (
    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    cache_key TEXT NOT NULL,
    operation_type TEXT NOT NULL,
    sections_provided JSON NOT NULL,
    tokens_used INTEGER NOT NULL,
    tool_name TEXT NOT NULL,
    file_path TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    was_successful BOOLEAN, -- Can be updated later
    user_feedback TEXT -- 'helpful', 'not_helpful', or null
);

CREATE INDEX IF NOT EXISTS idx_usage_session ON usage_logs(session_id, timestamp);
2.2 Update database_manager.py
Add methods to log usage and update feedback.

Python

# Additions to db.database_manager.py
    def log_usage(self, session_id: str, cache_key: str, 
                 operation_type: str, sections: list, 
                 tokens: int, tool_name: str, 
                 file_path: str = None) -> int:
        """Log a usage event and return the log_id."""
        with self.get_connection() as conn:
            cursor = conn.execute('''
                INSERT INTO usage_logs 
                (session_id, cache_key, operation_type, sections_provided, 
                 tokens_used, tool_name, file_path)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                session_id, cache_key, operation_type,
                json.dumps(sections), tokens, tool_name, file_path
            ))
            return cursor.lastrowid

    def update_usage_feedback(self, log_id: int, was_successful: bool,
                            user_feedback: str = None) -> None:
        """Update a usage log with explicit user feedback."""
        with self.get_connection() as conn:
            conn.execute('''
                UPDATE usage_logs 
                SET was_successful = ?, user_feedback = ?
                WHERE log_id = ?
            ''', (was_successful, user_feedback, log_id))
2.3 Create feedback_collector.py Hook
This PostToolUse hook listens for feedback commands.

~/projects/cc-rag/hooks/feedback_collector.py:

Python

#!/usr/bin/env python3
import json
import sys
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))
from db.database_manager import DatabaseManager

def main():
    try:
        input_data = json.load(sys.stdin)
        if input_data.get('tool_name') != 'Bash': sys.exit(0)
        
        output = input_data.get('tool_response', {}).get('output', '')
        feedback_match = re.search(r'/feedback\s+(helpful|not_helpful)', output)
        if not feedback_match: sys.exit(0)

        # Assumes previous turn's context is in the input to the Bash tool
        log_match = re.search(r'Session:\s*(\d+)', output)
        if log_match:
            log_id = int(log_match.group(1))
            feedback = feedback_match.group(1)
            
            db = DatabaseManager()
            db.update_usage_feedback(log_id, feedback == 'helpful', feedback)
            
            # Acknowledge feedback
            reason = f"✅ Thank you! Your feedback '{feedback}' has been recorded for log_id {log_id}."
            print(json.dumps({"decision": "block", "reason": reason}))
            sys.exit(0) # Use JSON output instead of exit 2
            
    except Exception:
        sys.exit(0) # Fail silently

if __name__ == "__main__":
    main()
2.4 Update context7_cache_hook.py to Log Usage
Modify the process and _format_response methods to log usage and ask for feedback.

Python

# In process() method, when cached_data is found:
# ...
log_id = self.db.log_usage(
    session_id, cache_key, operation_type,
    sections_used, len(extracted_content.split()),
    tool_name, file_path
)
reason = self._format_response(
    framework, extracted_content, cache_key, sections_used, log_id
)
output = {"decision": "block", "reason": reason}

# New _format_response method signature:
def _format_response(self, framework: str, content: str, cache_key: str, sections_used: list, log_id: int) -> str:
    return f"""Using cached {framework} documentation.
<context>
{content}
</context>

---
Cache Key: {cache_key} | Session: {log_id}

📝 Was this documentation helpful? Reply with `/feedback helpful` or `/feedback not_helpful` in the terminal.
"""
Phase 3: Automated Learning & Intelligence
Goal: Use the data collected in Phase 2 to automatically improve the context extraction rules.

3.1 Learning Engine
Create a LearningEngine that runs periodically (e.g., via a cron job). This engine analyzes usage_logs to determine which sections are most effective for which tasks.

~/projects/cc-rag/src/learning/learning_engine.py:

Python

import json
from collections import defaultdict

class LearningEngine:
    def __init__(self, db_manager):
        self.db = db_manager

    def run_learning_cycle(self, days: int = 7) -> dict:
        """Analyzes recent usage and updates rules."""
        insights = self._analyze_section_effectiveness(days)
        updated_rules = self._generate_new_rules(insights)
        self._apply_new_rules(updated_rules)
        return {"rules_updated": len(updated_rules)}

    def _analyze_section_effectiveness(self, days: int) -> dict:
        """Finds which sections are most helpful for each framework/operation."""
        with self.db.get_connection() as conn:
            # SQL to join usage_logs with feedback and group by framework/operation/section
            results = conn.execute("""
                SELECT
                    c.framework,
                    l.operation_type,
                    json_each.value as section_name,
                    SUM(CASE WHEN l.user_feedback = 'helpful' THEN 1 ELSE 0 END) as helpful_count,
                    SUM(CASE WHEN l.user_feedback = 'not_helpful' THEN 1 ELSE 0 END) as not_helpful_count,
                    COUNT(l.log_id) as total_count
                FROM usage_logs l
                JOIN context_cache c ON l.cache_key = c.cache_key
                JOIN json_each(l.sections_provided)
                WHERE l.timestamp > date('now', '-' || ? || ' days')
                  AND l.user_feedback IS NOT NULL
                GROUP BY 1, 2, 3
                HAVING total_count > 3 -- Minimum data points
            """, (days,)).fetchall()
            
            insights = defaultdict(list)
            for row in results:
                key = f"{row['framework']}:{row['operation_type']}"
                insights[key].append(dict(row))
            return insights

    def _generate_new_rules(self, insights: dict) -> dict:
        """Generates new rules based on effectiveness scores."""
        new_rules = {}
        for key, sections in insights.items():
            # Sort by a score (helpful - not_helpful)
            sections.sort(key=lambda s: s['helpful_count'] - s['not_helpful_count'], reverse=True)
            # Take the top 4 most effective sections
            top_sections = [s['section_name'] for s in sections if s['helpful_count'] > s['not_helpful_count']][:4]
            if top_sections:
                framework, operation = key.split(':')
                if framework not in new_rules:
                    new_rules[framework] = {}
                new_rules[framework][operation] = {"sections": top_sections, "max_tokens": 2000}
        return new_rules

    def _apply_new_rules(self, new_rules: dict):
        """Updates the context7_rules.json file with new, learned rules."""
        rules_path = Path.home() / '.claude' / 'context7_rules.json'
        # Safely merge new rules into the existing JSON file
        # ... implementation for reading, merging, and writing JSON ...
Phase 4: Advanced Operations & Prediction
Goal: Add production-grade features like predictive caching and enhanced analytics, building on the stable learning system.

4.1 Predictive Cache Warmer
Implement a PredictiveCacheWarmer that analyzes sequences of operations from usage_logs. If it detects that "create" is often followed by "style" for React components, it can pre-fetch and cache the styling documentation as soon as a "create" operation is detected.

4.2 Self-Healing
Implement a SelfHealingManager to handle common errors. If the hook fails due to a JSONDecodeError, the manager can attempt to fix common JSON issues (like trailing commas) and retry, making the system more resilient.

4.3 Advanced Analytics
Create a script that aggregates data from usage_logs and context_cache to generate a daily health report, including:

Cache hit/miss rate.

Most frequently used frameworks/operations.

Overall user satisfaction score based on feedback.

Average token count provided as context.