#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
import json
import sys
import re
from pathlib import Path

# Add project src to the Python path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from db.database_manager import DatabaseManager

class SessionOutcomeTracker:
    """Tracks session outcomes to determine effectiveness of cached documentation."""
    
    def __init__(self):
        self.db = DatabaseManager()
    
    def process(self, input_data: dict):
        """Processes PostToolUse events to track session outcomes."""
        try:
            tool_name = input_data.get('tool_name')
            tool_response = input_data.get('tool_response', {})
            
            # Only track relevant tools
            if not self._is_relevant_tool(tool_name):
                sys.exit(0)
            
            # Extract session ID from recent context if present
            session_id = self._extract_session_id(input_data)
            if not session_id:
                sys.exit(0)
            
            # Determine session outcome
            success, follow_up_actions = self._analyze_tool_outcome(tool_name, tool_response)
            
            # Update the most recent session log for this session
            self._update_recent_session(session_id, success, follow_up_actions)
            
        except Exception:
            # Fail silently to avoid disrupting user workflow
            pass
        
        sys.exit(0)
    
    def _is_relevant_tool(self, tool_name: str) -> bool:
        """Check if this tool is relevant for session tracking."""
        if not tool_name:
            return False
        
        # Track Write/Edit operations and Context7 operations
        relevant_tools = [
            'Write', 'Edit', 'MultiEdit', 'Bash',
            'mcp__Context7__get-library-docs',
            'mcp__Context7__cache-context'
        ]
        
        return (tool_name in relevant_tools or 
                re.match(r'mcp__.*__(write|edit|multi_edit)', tool_name or ""))
    
    def _extract_session_id(self, input_data: dict) -> str:
        """Extract session ID from the tool input or context."""
        # Try to get session_id directly from input data first
        session_id = input_data.get('session_id')
        if session_id:
            # The hook creates 8-char session IDs, so truncate if needed
            return session_id[:8] if len(session_id) > 8 else session_id
        
        # Look for session ID in tool input
        tool_input = input_data.get('tool_input', {})
        
        # Check if this is a response to our hook (contains session info)
        content = tool_input.get('content', '')
        reason = tool_input.get('reason', '')
        
        # Look for session ID pattern in content or reason
        # The pattern is "Session: {8-char-id}" in the hook output
        for text in [content, reason, str(tool_input)]:
            if text:
                match = re.search(r'Session:\s*([a-f0-9-]{8})', str(text))
                if match:
                    return match.group(1)
        
        return None
    
    def _analyze_tool_outcome(self, tool_name: str, tool_response: dict) -> tuple:
        """Analyze the tool outcome to determine success and follow-up actions."""
        output = tool_response.get('output', '') or ''
        error = tool_response.get('error', '') or ''
        
        follow_up_actions = []
        
        # Check if this is actually a successful operation (even if blocked by hook)
        # The hook blocks but provides context, which is a success from tracking perspective
        if 'filePath' in str(output) or 'success' in str(output).lower():
            success = True
            follow_up_actions.append("operation_completed_with_context")
        
        # Determine success based on tool type and response
        elif tool_name in ['Write', 'Edit', 'MultiEdit'] or 'write' in tool_name.lower():
            success = not error and 'error' not in str(output).lower()
            if error:
                follow_up_actions.append(f"write_error: {error[:100]}")
            # Check if the file was actually written/edited
            if 'has been' in str(output) and ('updated' in str(output) or 'created' in str(output)):
                success = True
                follow_up_actions.append("file_operation_successful")
        
        elif tool_name == 'Bash':
            success = not error
            if error:
                follow_up_actions.append(f"bash_error: {error[:100]}")
            
            # Check for specific patterns in bash output
            if 'context7' in str(output).lower():
                follow_up_actions.append("immediate_context7_retry")
                # Don't mark as failure if it's just running context7 commands
                if 'cache' in str(output).lower() and 'successfully' in str(output).lower():
                    success = True
        
        elif 'Context7' in tool_name:
            success = not error
            follow_up_actions.append(f"context7_action: {tool_name}")
            if 'get-library-docs' in tool_name:
                follow_up_actions.append("fetching_new_documentation")
        
        else:
            success = not error
        
        # Add general success indicators
        if success and not follow_up_actions:
            follow_up_actions.append("operation_completed_successfully")
        
        return success, follow_up_actions
    
    def _update_recent_session(self, session_id: str, success: bool, follow_up_actions: list):
        """Update the most recent session log for this session ID."""
        try:
            with self.db.get_connection() as conn:
                # Find the most recent session log for this session ID
                row = conn.execute('''
                    SELECT log_id FROM session_logs 
                    WHERE session_id = ? 
                    ORDER BY timestamp DESC 
                    LIMIT 1
                ''', (session_id,)).fetchone()
                
                if row:
                    log_id = row['log_id']
                    self.db.update_session_outcome(log_id, success, follow_up_actions)
        except Exception:
            # Fail silently
            pass

def main():
    """Main entry point for the session tracker hook."""
    try:
        input_data = json.load(sys.stdin)
        tracker = SessionOutcomeTracker()
        tracker.process(input_data)
    except Exception:
        # Fail silently to avoid disrupting workflow
        sys.exit(0)

if __name__ == "__main__":
    main()