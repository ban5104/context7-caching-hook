#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "python-dotenv",
#     "supabase",
# ]
# ///
import json
import sys
import re
import signal
import uuid
from pathlib import Path
from datetime import datetime

# Add project src to the Python path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from db.database_manager import DatabaseManager
from extractors.basic_extractor import BasicSectionExtractor
from detectors.operation_detector import OperationDetector

def get_extraction_rule(framework: str, operation: str) -> dict:
    # (No changes needed here, previous version was already robust)
    rules_path = Path.home() / '.claude' / 'context7_rules.json'
    fallback_rule = {"sections": ["overview", "example"], "max_tokens": 2000}
    if not rules_path.exists():
        return fallback_rule
    with open(rules_path, 'r') as f:
        rules = json.load(f)
    framework_rules = rules.get(framework, {})
    return framework_rules.get(operation, framework_rules.get('defaults', rules.get('defaults', fallback_rule)))

class Context7CacheHook:
    """A hook to enforce using cached documentation via Context7."""
    
    def __init__(self):
        self.db = DatabaseManager()
        self.extractor = BasicSectionExtractor()
        self.detector = OperationDetector()

    def _sanitize_cache_key(self, key: str) -> str:
        """(Point 2) Sanitize cache keys to prevent injection attacks."""
        if '..' in key or key.startswith('/'):
            raise ValueError(f"Invalid cache key: path traversal attempt blocked.")
        if not re.match(r'^[a-zA-Z0-9:._-]+$', key):
            raise ValueError(f"Invalid cache key format: contains invalid characters.")
        return key

    def _should_bypass(self, tool_input: dict) -> bool:
        """(Point 6) Determine if context fetching should be bypassed."""
        content = tool_input.get('content', '')
        file_path = tool_input.get('file_path', '')
        # Bypass for very small edits
        if len(content.strip()) < 50:
            return True
        # Bypass for non-code files
        if file_path and not any(file_path.endswith(ext) for ext in ['.js', '.jsx', '.ts', '.tsx', '.py', '.html', '.css']):
            return True
        return False
    
    def _check_transcript_for_recent_context(self, transcript_path: str, cache_key: str, file_path: str) -> bool:
        """Check if we recently provided context for this exact operation."""
        try:
            if not transcript_path or not Path(transcript_path).exists():
                return False
            
            # Read the transcript (JSONL format - one JSON object per line)
            messages = []
            with open(transcript_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            messages.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue
            
            if len(messages) < 2:
                return False
            
            # Check the last 10 messages for our hook providing context
            for msg in messages[-10:]:
                # Look for user messages that contain tool_result with our hook error
                if msg.get('type') == 'user' and msg.get('message', {}).get('role') == 'user':
                    content_array = msg.get('message', {}).get('content', [])
                    if isinstance(content_array, list):
                        for content_item in content_array:
                            if (content_item.get('type') == 'tool_result' and 
                                content_item.get('is_error') == True):
                                # Check the error content
                                error_content = content_item.get('content', '')
                                if (f"Cache Key: {cache_key}" in error_content and 
                                    "I have retrieved relevant documentation" in error_content):
                                    # Debug log that we found a match
                                    debug_log = Path.home() / '.claude' / 'hook_debug.log'
                                    with open(debug_log, 'a') as f:
                                        f.write(f"[{datetime.now().isoformat()}] Found previous context provision for {cache_key}\n")
                                    return True
            
            return False
            
        except Exception as e:
            # Log error but don't block on transcript reading failures
            debug_log = Path.home() / '.claude' / 'hook_debug.log'
            with open(debug_log, 'a') as f:
                f.write(f"[{datetime.now().isoformat()}] Transcript read error: {e}\n")
            return False

    def process(self, input_data: dict):
        """Processes the hook input and directs Claude using JSON output."""
        # Debug log
        debug_log = Path.home() / '.claude' / 'hook_debug.log'
        with open(debug_log, 'a') as f:
            f.write(f"[{datetime.now().isoformat()}] Hook called with: {json.dumps(input_data)[:200]}\n")
        
        tool_name = input_data.get('tool_name')
        tool_input = input_data.get('tool_input', {})
        transcript_path = input_data.get('transcript_path')
        
        # (Point 7) Rules file management command
        if tool_input.get('command') == 'context7-rules':
            rules_path = Path.home() / '.claude' / 'context7_rules.json'
            output = rules_path.read_text() if rules_path.exists() else "No context7_rules.json file found."
            print(json.dumps({"decision": "block", "reason": output}))
            sys.exit(0)

        # (Point 5) MCP and standard tool integration
        is_valid_tool = (tool_name in ['Write', 'Edit', 'MultiEdit']) or \
                        (re.match(r'mcp__.*__(write|edit|multi_edit)', tool_name or ""))
        if not is_valid_tool:
            sys.exit(0) # Approve without changes

        # (Point 6) Performance bypass
        if self._should_bypass(tool_input):
            sys.exit(0) # Approve without changes

        content = tool_input.get('content', '')
        file_path = tool_input.get('file_path', '')

        framework = self.detector.detect_framework(content, file_path)
        if not framework:
            sys.exit(0) # Approve without changes

        operation_type = self.detector.detect_operation(content, file_path)
        component = self.detector.extract_component(content, file_path, framework)
        
        try:
            raw_key = f"{framework}:{component}" if component else framework
            cache_key = self._sanitize_cache_key(raw_key) # (Point 2)
        except ValueError as e:
            print(json.dumps({"decision": "block", "reason": f"Error: {e}"}))
            sys.exit(0)

        # Check if we recently provided context for this exact operation
        if transcript_path and self._check_transcript_for_recent_context(transcript_path, cache_key, file_path):
            # We already provided context in a recent turn, allow the operation
            debug_log = Path.home() / '.claude' / 'hook_debug.log'
            with open(debug_log, 'a') as f:
                f.write(f"[{datetime.now().isoformat()}] Allowing operation - context already provided for {cache_key}\n")
            sys.exit(0)  # Approve without changes

        cached_data = self.db.get_cache_data(cache_key)
        rule = get_extraction_rule(framework, operation_type)

        # (Point 4) Use structured JSON output for control flow
        if cached_data:
            sections = json.loads(cached_data['sections'])
            extracted_content, sections_used = self.extractor.extract_relevant_sections(
                sections, rule, token_budget=rule.get('max_tokens', 2000)
            )
            
            # If no matching sections were found, fall back to full content
            if not extracted_content and cached_data.get('full_content'):
                extracted_content = cached_data['full_content'][:rule.get('max_tokens', 2000) * 5]  # Approx 5 chars per token
                sections_used = list(sections.keys()) if sections else ['full_content']
                debug_log = Path.home() / '.claude' / 'hook_debug.log'
                with open(debug_log, 'a') as f:
                    f.write(f"[{datetime.now().isoformat()}] No matching sections found for {cache_key}, using full content\n")
            
            # Log session for effectiveness analysis
            session_id = str(uuid.uuid4())[:8]  # Short session ID
            log_id = self.db.log_session(
                session_id, cache_key, operation_type, sections_used,
                len(extracted_content.split()), tool_name, tool_input, file_path
            )
            
            # Block and provide the context in the reason for the model to use
            reason = self._format_response(framework, extracted_content, cache_key, sections_used, session_id)
            output = {"decision": "block", "reason": reason}
        else:
            # Block and request the documentation fetch
            reason = self._format_fetch_instructions(framework, rule, cache_key)
            output = {"decision": "block", "reason": reason}

        print(json.dumps(output))
        sys.exit(0)

    def _format_response(self, framework: str, content: str, cache_key: str, sections_used: list, session_id: str) -> str:
        return f"""I have retrieved relevant documentation for {framework} from the cache. Please use this context to inform your code generation.

<context>
{content}
</context>

---
Cache Key: {cache_key} | Session: {session_id}
Sections Used: {', '.join(sections_used)}
"""

    def _format_fetch_instructions(self, framework: str, rule: dict, cache_key: str) -> str:
        sections_to_extract = rule.get('sections', ['overview', 'example', 'usage', 'api'])
        cache_utils_path = Path(__file__).parent / "scripts" / "cache_utils.py"
        return f"""The required {framework} documentation is not in the cache. To proceed:

1. Use Context7:get-library-docs to fetch the documentation for '{framework}'
2. Format content with markdown headers for sections: {', '.join(sections_to_extract)}
   Example format:
   # Overview
   Content here...
   
   # Props
   Content here...
   
   # Example
   Content here...

3. Cache using one of these methods:
   - With content: uv run {cache_utils_path} cache "{cache_key}" "{framework}" --content "YOUR_CONTENT"
   - With stdin (for large content): echo "YOUR_CONTENT" | uv run {cache_utils_path} cache "{cache_key}" "{framework}"
   
4. Validate the cache: uv run {Path(__file__).parent / "scripts" / "validate_cache.py"} "{cache_key}"

5. Retry your original request

Note: The cache_utils.py script stores documentation in SQLite with section extraction and analytics tracking.
"""

def main():
    """Main entry point for the hook script with robust error handling."""
    # (Point 8) Timeout to prevent hanging
    def timeout_handler(signum, frame):
        # This error won't be seen by the user, but will be in the log.
        raise TimeoutError("Hook script timed out after 55 seconds.")
    
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(55)

    # (Point 3) Better error handling
    try:
        input_data = json.load(sys.stdin)
        hook = Context7CacheHook()
        hook.process(input_data)
    except json.JSONDecodeError as e:
        # This error indicates a problem with Claude's output to the hook.
        print(f"Hook Error: Invalid JSON input from stdin: {e}", file=sys.stderr)
        sys.exit(1)  # Non-blocking error code
    except Exception as e:
        # Log other errors to a file for debugging but don't block Claude.
        log_path = Path.home() / '.claude' / 'hook_errors.log'
        with open(log_path, 'a') as f:
            f.write(f"[{datetime.now().isoformat()}] {type(e).__name__}: {e}\n")
        sys.exit(0) # Let Claude continue without intervention

if __name__ == "__main__":
    main()