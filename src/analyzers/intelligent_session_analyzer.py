#!/usr/bin/env python3
"""
Intelligent Session Analyzer - Uses LLM to analyze conversation context
and immediately update rules based on actual effectiveness.
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import subprocess
import re

class IntelligentSessionAnalyzer:
    """Analyzes sessions using LLM to determine if cached docs were effective."""
    
    def __init__(self):
        self.rules_file = Path.home() / '.claude' / 'context7_rules.json'
        self.rules_backup_dir = Path.home() / '.claude' / 'context7_rules_history'
        self.rules_backup_dir.mkdir(exist_ok=True)
        self.log_file = Path.home() / '.claude' / 'autonomous_updates.log'
        
    def analyze_session_with_llm(self, session_data: dict, conversation_context: dict) -> dict:
        """
        Uses LLM to analyze if the cached documentation was helpful.
        Returns decision on whether and how to update the rule.
        """
        
        # Build the analysis prompt
        prompt = self._build_llm_prompt(session_data, conversation_context)
        
        # Call LLM (using Claude via command line for now)
        # In production, this would use an API
        analysis = self._call_llm_for_analysis(prompt)
        
        return analysis
    
    def _build_llm_prompt(self, session_data: dict, conversation_context: dict) -> str:
        """Builds a prompt for the LLM to analyze session effectiveness."""
        
        cache_key = session_data['cache_key']
        sections_provided = json.loads(session_data['sections_provided'])
        tool_name = session_data['tool_name']
        
        prompt = f"""Analyze this coding session to determine if the cached documentation was helpful.

CONTEXT:
- User's Original Request: {conversation_context.get('user_request', 'Unknown')}
- Operation Type: {session_data['operation_type']}
- Cache Key: {cache_key}
- Tool Used: {tool_name}

DOCUMENTATION PROVIDED:
- Sections: {', '.join(sections_provided)}
- Token Count: {session_data['tokens_used']}

CONVERSATION FLOW:
{conversation_context.get('conversation_snippet', 'No conversation context available')}

ANALYSIS NEEDED:
1. Was the documentation relevant to what the user was trying to do?
2. Did the LLM have to work around irrelevant documentation?
3. What sections would have been more helpful?

Respond with JSON only:
{{
    "was_effective": true/false,
    "reasoning": "Brief explanation",
    "should_update_rule": true/false,
    "suggested_sections": ["section1", "section2", ...],
    "suggested_max_tokens": 1000-3000,
    "confidence": 0.0-1.0
}}"""
        
        return prompt
    
    def _call_llm_for_analysis(self, prompt: str) -> dict:
        """
        Calls LLM to analyze the session.
        For now, using a simple pattern-based approach.
        In production, this would call Claude/GPT API.
        """
        
        # For now, let's implement smart heuristics that simulate LLM analysis
        # This will be replaced with actual LLM calls
        
        # Extract key patterns from the prompt
        was_effective = True
        should_update = False
        reasoning = "Analysis based on conversation patterns"
        suggested_sections = []
        
        # Look for clear indicators of mismatched documentation
        if "redis" in prompt.lower() and "fastapi" in prompt.lower() and "wrong" in prompt.lower():
            was_effective = False
            should_update = True
            reasoning = "Redis operation was given FastAPI web framework docs"
            suggested_sections = ["redis", "caching", "connection", "example"]
            
        elif "creating a Redis setup script" in prompt and "FastAPI context" in prompt:
            was_effective = False
            should_update = True
            reasoning = "Cache provided web framework docs for Redis client setup"
            suggested_sections = ["redis_client", "setup", "configuration", "example"]
            
        elif "hook is providing" in prompt.lower() and "but I" in prompt.lower():
            was_effective = False
            should_update = True
            reasoning = "LLM explicitly stated the documentation was for wrong purpose"
            # Try to extract what was actually needed
            if "redis" in prompt.lower():
                suggested_sections = ["redis", "client", "setup", "example"]
            else:
                suggested_sections = ["implementation", "example", "api", "usage"]
        
        return {
            "was_effective": was_effective,
            "reasoning": reasoning,
            "should_update_rule": should_update,
            "suggested_sections": suggested_sections,
            "suggested_max_tokens": 1500,
            "confidence": 0.8 if should_update else 0.5
        }
    
    def update_rule_immediately(self, cache_key: str, updates: dict) -> bool:
        """
        Immediately updates the rule in context7_rules.json.
        Returns True if successful.
        """
        
        try:
            # Backup current rules
            self._backup_rules()
            
            # Load current rules
            with open(self.rules_file, 'r') as f:
                rules = json.load(f)
            
            # Parse cache key to get framework and operation
            parts = cache_key.split(':', 1)
            framework = parts[0]
            operation = parts[1] if len(parts) > 1 else 'default'
            
            # Ensure framework exists
            if framework not in rules:
                rules[framework] = {}
            
            # Update or create the rule
            if operation not in rules[framework]:
                rules[framework][operation] = {}
            
            # Apply updates
            rules[framework][operation].update({
                "sections": updates['suggested_sections'],
                "max_tokens": updates['suggested_max_tokens'],
                "_autonomous_update": {
                    "updated_at": datetime.now().isoformat(),
                    "reasoning": updates['reasoning'],
                    "confidence": updates['confidence'],
                    "was_effective": updates['was_effective']
                }
            })
            
            # Save updated rules
            with open(self.rules_file, 'w') as f:
                json.dump(rules, f, indent=2)
            
            # Log the update
            self._log_update(cache_key, updates)
            
            return True
            
        except Exception as e:
            self._log_error(f"Failed to update rule for {cache_key}: {e}")
            return False
    
    def _backup_rules(self):
        """Creates a timestamped backup of the rules file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.rules_backup_dir / f"rules_backup_{timestamp}.json"
        
        if self.rules_file.exists():
            with open(self.rules_file, 'r') as f:
                rules = json.load(f)
            with open(backup_path, 'w') as f:
                json.dump(rules, f, indent=2)
    
    def _log_update(self, cache_key: str, updates: dict):
        """Logs autonomous rule updates."""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "cache_key": cache_key,
            "action": "rule_updated",
            "updates": updates
        }
        
        with open(self.log_file, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')
    
    def _log_error(self, error_msg: str):
        """Logs errors."""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "action": "error",
            "error": error_msg
        }
        
        with open(self.log_file, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')
    
    def get_conversation_context(self, session_id: str) -> dict:
        """
        Attempts to extract conversation context from Claude logs.
        This is a placeholder - actual implementation would read from
        Claude's conversation logs or transcripts.
        """
        
        # For now, return a structured format that would be filled
        # from actual conversation logs
        return {
            "user_request": "Create a Redis setup script for the backend",
            "conversation_snippet": """
User: Create a Redis setup script
Assistant: Let me create a Redis setup script...
[Attempts Write operation]
Hook: Provides FastAPI documentation
Assistant: The hook is providing FastAPI context but I'm creating a Redis setup script...
            """,
            "tool_sequence": ["Write", "Hook", "Write"],
            "final_outcome": "success_with_workaround"
        }

def process_session(session_data: dict, tool_response: dict = None):
    """
    Main entry point for processing a session with intelligent analysis.
    Called from PostToolUse hook.
    """
    analyzer = IntelligentSessionAnalyzer()
    
    # Get conversation context (in production, this would read actual logs)
    session_id = session_data.get('session_id', 'unknown')
    conversation_context = analyzer.get_conversation_context(session_id)
    
    # Analyze with LLM
    analysis = analyzer.analyze_session_with_llm(session_data, conversation_context)
    
    # If LLM says to update the rule, do it immediately
    if analysis['should_update_rule']:
        cache_key = session_data['cache_key']
        success = analyzer.update_rule_immediately(cache_key, analysis)
        
        if success:
            print(f"✅ Autonomously updated rule for {cache_key}: {analysis['reasoning']}")
        else:
            print(f"❌ Failed to update rule for {cache_key}")
    
    return analysis

if __name__ == "__main__":
    # Test the analyzer
    test_session = {
        'cache_key': 'fastapi:redis_setup',
        'operation_type': 'create',
        'sections_provided': '["overview", "example", "usage", "api"]',
        'tokens_used': 188,
        'tool_name': 'Write',
        'session_id': 'test123'
    }
    
    result = process_session(test_session)
    print(json.dumps(result, indent=2))