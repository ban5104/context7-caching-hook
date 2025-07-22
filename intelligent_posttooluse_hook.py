#!/usr/bin/env python3
"""
Intelligent PostToolUse Hook - Analyzes conversation context and 
autonomously updates rules based on actual effectiveness.
"""

import json
import sys
import os
from pathlib import Path
from datetime import datetime

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'src'))

from db.database_manager import DatabaseManager
from analyzers.intelligent_session_analyzer import IntelligentSessionAnalyzer

class IntelligentPostToolUseHook:
    def __init__(self):
        self.db = DatabaseManager()
        self.analyzer = IntelligentSessionAnalyzer()
        self.transcript_dir = Path.home() / '.claude' / 'conversations'
        
    def process(self, input_data: dict):
        """Main processing logic for PostToolUse events."""
        
        try:
            tool_name = input_data.get('tool_name', '')
            tool_response = input_data.get('tool_response', {})
            
            # Only process relevant tools (Write, Edit, Context7 operations)
            if not self._is_relevant_tool(tool_name):
                sys.exit(0)
            
            # Extract session information
            session_data = self._extract_session_data(input_data)
            if not session_data:
                sys.exit(0)
            
            # Get conversation context
            conversation_context = self._get_conversation_context(input_data)
            
            # Add conversation context to session data
            session_data['conversation_context'] = conversation_context
            
            # Analyze and potentially update rules immediately
            analysis = self.analyzer.analyze_session_with_llm(session_data, conversation_context)
            
            # If rules were updated, log it
            if analysis.get('should_update_rule'):
                cache_key = session_data.get('cache_key', 'unknown')
                self.analyzer.update_rule_immediately(cache_key, analysis)
            
            # Also update the session log with the analysis
            self._update_session_log(session_data, analysis)
            
        except Exception as e:
            # Log error but don't disrupt workflow
            error_log = Path.home() / '.claude' / 'hook_errors.log'
            with open(error_log, 'a') as f:
                f.write(f"[{datetime.now().isoformat()}] IntelligentPostToolUse error: {e}\n")
        
        sys.exit(0)
    
    def _is_relevant_tool(self, tool_name: str) -> bool:
        """Check if this tool is relevant for intelligent analysis."""
        relevant_tools = [
            'Write', 'Edit', 'MultiEdit', 'Bash',
            'mcp__Context7__get-library-docs',
            'mcp__Context7__cache-context'
        ]
        return tool_name in relevant_tools
    
    def _extract_session_data(self, input_data: dict) -> dict:
        """Extract session data from the PostToolUse input."""
        
        # Look for session information in the tool response
        tool_response = input_data.get('tool_response', {})
        output = tool_response.get('output', '')
        
        # Try to find session ID and cache key from the output
        session_id = None
        cache_key = None
        
        # Look for patterns in the output
        if 'Session:' in str(output):
            # Extract session ID
            import re
            match = re.search(r'Session:\s*([a-f0-9-]{8})', str(output))
            if match:
                session_id = match.group(1)
        
        if 'Cache Key:' in str(output):
            # Extract cache key
            import re
            match = re.search(r'Cache Key:\s*([^\s|]+)', str(output))
            if match:
                cache_key = match.group(1)
        
        if not (session_id and cache_key):
            # Try to get from database by looking at recent sessions
            recent_session = self._get_recent_session_info()
            if recent_session:
                return recent_session
            return None
        
        # Get full session data from database
        with self.db.get_connection() as conn:
            row = conn.execute('''
                SELECT * FROM session_logs 
                WHERE session_id = ? AND cache_key = ?
                ORDER BY timestamp DESC 
                LIMIT 1
            ''', (session_id, cache_key)).fetchone()
            
            if row:
                return dict(row)
        
        return None
    
    def _get_recent_session_info(self) -> dict:
        """Get the most recent relevant session from the database."""
        try:
            with self.db.get_connection() as conn:
                # Get the most recent unanalyzed session
                row = conn.execute('''
                    SELECT * FROM session_logs 
                    WHERE session_complete IS NULL 
                    ORDER BY timestamp DESC 
                    LIMIT 1
                ''').fetchone()
                
                if row:
                    return dict(row)
        except Exception:
            pass
        
        return None
    
    def _get_conversation_context(self, input_data: dict) -> dict:
        """
        Extract conversation context from Claude's logs or input data.
        This is where we'd read actual conversation history.
        """
        
        # Check if conversation context was passed in
        if 'conversation_context' in input_data:
            return input_data['conversation_context']
        
        # Try to read from transcript if available
        transcript_path = input_data.get('transcript_path')
        if transcript_path and Path(transcript_path).exists():
            return self._parse_transcript(transcript_path)
        
        # For now, return a basic context structure
        # In production, this would read actual Claude conversation logs
        tool_input = input_data.get('tool_input', {})
        tool_name = input_data.get('tool_name', '')
        
        # Build context from available information
        context = {
            "tool_used": tool_name,
            "timestamp": datetime.now().isoformat()
        }
        
        # Try to infer user intent from tool input
        if tool_name in ['Write', 'Edit', 'MultiEdit']:
            file_path = tool_input.get('file_path', '')
            content = tool_input.get('content', '')[:200]  # First 200 chars
            
            # Infer from filename
            if 'redis' in file_path.lower():
                context['user_request'] = "Working with Redis configuration or setup"
            elif 'api' in file_path.lower():
                context['user_request'] = "Creating or modifying API endpoints"
            elif 'database' in file_path.lower():
                context['user_request'] = "Database-related operations"
            else:
                context['user_request'] = f"Working on {file_path}"
            
            context['file_path'] = file_path
            context['content_preview'] = content
        
        return context
    
    def _parse_transcript(self, transcript_path: str) -> dict:
        """Parse Claude conversation transcript for context."""
        try:
            with open(transcript_path, 'r') as f:
                content = f.read()
            
            # Extract relevant parts of conversation
            # This is a simplified version - real implementation would be more sophisticated
            lines = content.split('\n')
            
            # Look for user messages and assistant responses
            user_request = ""
            assistant_response = ""
            
            for i, line in enumerate(lines):
                if line.startswith("Human:") or line.startswith("User:"):
                    # Get the user's request
                    user_request = line + " " + lines[i+1] if i+1 < len(lines) else line
                elif line.startswith("Assistant:") and user_request:
                    # Get the assistant's response
                    assistant_response = line + " " + lines[i+1] if i+1 < len(lines) else line
                    break
            
            return {
                "user_request": user_request,
                "assistant_response": assistant_response,
                "conversation_snippet": content[-1000:]  # Last 1000 chars
            }
            
        except Exception:
            return {}
    
    def _update_session_log(self, session_data: dict, analysis: dict):
        """Update the session log with the intelligent analysis results."""
        try:
            log_id = session_data.get('log_id')
            if log_id:
                # Update with intelligent analysis instead of simple effectiveness score
                self.db.update_session_intelligence(
                    log_id,
                    was_effective=analysis.get('was_effective', False),
                    reasoning=analysis.get('reasoning', ''),
                    confidence=analysis.get('confidence', 0.5),
                    rule_updated=analysis.get('should_update_rule', False)
                )
        except Exception:
            pass

def main():
    """Main entry point for the intelligent PostToolUse hook."""
    try:
        input_data = json.load(sys.stdin)
        hook = IntelligentPostToolUseHook()
        hook.process(input_data)
    except Exception as e:
        # Log error and exit gracefully
        error_log = Path.home() / '.claude' / 'hook_errors.log'
        with open(error_log, 'a') as f:
            f.write(f"[{datetime.now().isoformat()}] Hook error: {e}\n")
        sys.exit(0)

if __name__ == "__main__":
    main()