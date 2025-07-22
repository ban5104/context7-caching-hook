# ~/projects/cc-rag/src/healing/self_healing_manager.py
import json
import re
import sqlite3
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from pathlib import Path
import hashlib

class SelfHealingManager:
    """Manages self-healing capabilities for the Context7 system."""
    
    def __init__(self, db_manager):
        self.db = db_manager
        self.healing_log_path = Path.home() / '.claude' / 'healing_log.json'
        self.max_healing_attempts = 3
        self.healing_stats = {
            "json_fixes": 0,
            "cache_repairs": 0,
            "rule_recoveries": 0,
            "database_repairs": 0
        }
    
    def attempt_json_healing(self, json_string: str) -> Tuple[bool, Optional[str], str]:
        """Attempt to fix common JSON issues."""
        
        original = json_string.strip()
        fixed = original
        healing_actions = []
        
        try:
            # First, try parsing as-is
            json.loads(fixed)
            return True, fixed, "no_healing_needed"
        except json.JSONDecodeError as e:
            pass  # Continue with healing attempts
        
        # Common JSON fixes
        
        # 1. Remove trailing commas
        if ',}' in fixed or ',]' in fixed:
            fixed = re.sub(r',(\s*[}\]])', r'\1', fixed)
            healing_actions.append("removed_trailing_commas")
        
        # 2. Fix unescaped quotes in strings
        # Look for patterns like "text "quoted" text"
        fixed = re.sub(r'"([^"]*)"([^"]*)"([^"]*)"', r'"\1\"quoted\"\3"', fixed)
        if fixed != json_string:
            healing_actions.append("escaped_internal_quotes")
        
        # 3. Fix missing quotes around keys
        fixed = re.sub(r'(\w+)(\s*:\s*)', r'"\1"\2', fixed)
        if len(healing_actions) == 0 or fixed != json_string:
            healing_actions.append("quoted_keys")
        
        # 4. Fix single quotes to double quotes
        if "'" in fixed:
            # Be careful to only replace quotes that are likely JSON quotes
            fixed = re.sub(r"'([^']*)'(\s*:\s*)", r'"\1"\2', fixed)  # Keys
            fixed = re.sub(r"(\s*:\s*)'([^']*)'", r'\1"\2"', fixed)  # Values
            healing_actions.append("single_to_double_quotes")
        
        # 5. Try to fix missing closing braces/brackets
        open_braces = fixed.count('{') - fixed.count('}')
        if open_braces > 0:
            fixed += '}' * open_braces
            healing_actions.append("added_closing_braces")
        
        open_brackets = fixed.count('[') - fixed.count(']')
        if open_brackets > 0:
            fixed += ']' * open_brackets
            healing_actions.append("added_closing_brackets")
        
        # 6. Try to remove extra closing braces/brackets
        if open_braces < 0:
            for _ in range(abs(open_braces)):
                fixed = fixed.rstrip('}').rstrip()
            healing_actions.append("removed_extra_braces")
        
        if open_brackets < 0:
            for _ in range(abs(open_brackets)):
                fixed = fixed.rstrip(']').rstrip()
            healing_actions.append("removed_extra_brackets")
        
        # Test if healing worked
        try:
            json.loads(fixed)
            self.healing_stats["json_fixes"] += 1
            self._log_healing_action("json_fix", {
                "original_error": str(e),
                "actions_taken": healing_actions,
                "success": True
            })
            return True, fixed, f"healed: {', '.join(healing_actions)}"
        except json.JSONDecodeError as final_error:
            self._log_healing_action("json_fix", {
                "original_error": str(e),
                "final_error": str(final_error),
                "actions_taken": healing_actions,
                "success": False
            })
            return False, None, f"failed_healing: {', '.join(healing_actions)}"
    
    def validate_and_repair_cache(self) -> Dict:
        """Validate cache integrity and repair issues."""
        
        repair_results = {
            "validated_entries": 0,
            "corrupted_entries": 0,
            "repaired_entries": 0,
            "removed_entries": 0,
            "issues_found": []
        }
        
        try:
            with self.db.get_connection() as conn:
                # Get all cache entries
                entries = conn.execute('''
                    SELECT cache_key, framework, sections, full_content, expires_at, total_tokens
                    FROM context_cache
                ''').fetchall()
                
                for entry in entries:
                    repair_results["validated_entries"] += 1
                    entry_dict = dict(entry)
                    
                    # Check expiration
                    if datetime.fromisoformat(entry_dict["expires_at"]) < datetime.now():
                        conn.execute('DELETE FROM context_cache WHERE cache_key = ?', 
                                   (entry_dict["cache_key"],))
                        repair_results["removed_entries"] += 1
                        repair_results["issues_found"].append(f"Expired entry: {entry_dict['cache_key']}")
                        continue
                    
                    # Validate JSON structure
                    try:
                        sections = json.loads(entry_dict["sections"])
                        if not isinstance(sections, dict):
                            raise ValueError("Sections must be a dictionary")
                    except (json.JSONDecodeError, ValueError) as e:
                        repair_results["corrupted_entries"] += 1
                        repair_results["issues_found"].append(f"Corrupted sections in {entry_dict['cache_key']}: {e}")
                        
                        # Attempt to repair
                        if self._repair_cache_entry(conn, entry_dict):
                            repair_results["repaired_entries"] += 1
                        else:
                            # Remove if can't repair
                            conn.execute('DELETE FROM context_cache WHERE cache_key = ?', 
                                       (entry_dict["cache_key"],))
                            repair_results["removed_entries"] += 1
                    
                    # Validate token count
                    content_tokens = len(entry_dict["full_content"].split()) if entry_dict["full_content"] else 0
                    if abs(content_tokens - entry_dict["total_tokens"]) > content_tokens * 0.5:  # 50% difference
                        # Fix token count
                        conn.execute('''
                            UPDATE context_cache 
                            SET total_tokens = ? 
                            WHERE cache_key = ?
                        ''', (content_tokens, entry_dict["cache_key"]))
                        repair_results["repaired_entries"] += 1
                        repair_results["issues_found"].append(f"Fixed token count for {entry_dict['cache_key']}")
                
                self.healing_stats["cache_repairs"] += repair_results["repaired_entries"]
                
        except sqlite3.Error as e:
            repair_results["issues_found"].append(f"Database error: {e}")
        
        self._log_healing_action("cache_repair", repair_results)
        return repair_results
    
    def _repair_cache_entry(self, conn, entry: Dict) -> bool:
        """Attempt to repair a corrupted cache entry."""
        
        try:
            # Try to heal the JSON
            success, fixed_json, _ = self.attempt_json_healing(entry["sections"])
            
            if success:
                # Update the entry with fixed JSON
                conn.execute('''
                    UPDATE context_cache 
                    SET sections = ? 
                    WHERE cache_key = ?
                ''', (fixed_json, entry["cache_key"]))
                return True
        except Exception:
            pass
        
        return False
    
    def validate_and_repair_rules(self) -> Dict:
        """Validate and repair the rules file."""
        
        rules_path = Path.home() / '.claude' / 'context7_rules.json'
        repair_results = {
            "file_exists": rules_path.exists(),
            "valid_json": False,
            "rules_validated": 0,
            "rules_repaired": 0,
            "issues_found": [],
            "backup_created": False
        }
        
        if not rules_path.exists():
            # Create default rules file
            default_rules = {
                "defaults": {
                    "sections": ["overview", "example", "usage"],
                    "max_tokens": 2000
                },
                "react": {
                    "create": {
                        "sections": ["components", "hooks", "example"],
                        "max_tokens": 2500
                    },
                    "style": {
                        "sections": ["styling", "css", "example"],
                        "max_tokens": 2000
                    }
                }
            }
            
            try:
                rules_path.parent.mkdir(parents=True, exist_ok=True)
                with open(rules_path, 'w') as f:
                    json.dump(default_rules, f, indent=2)
                repair_results["rules_repaired"] = 1
                repair_results["issues_found"].append("Created default rules file")
                self.healing_stats["rule_recoveries"] += 1
            except Exception as e:
                repair_results["issues_found"].append(f"Failed to create default rules: {e}")
            
            return repair_results
        
        # Validate existing rules file
        try:
            with open(rules_path, 'r') as f:
                content = f.read()
            
            # Try to parse JSON
            try:
                rules = json.loads(content)
                repair_results["valid_json"] = True
            except json.JSONDecodeError:
                # Attempt to heal JSON
                success, fixed_content, _ = self.attempt_json_healing(content)
                
                if success:
                    # Create backup
                    backup_path = rules_path.with_suffix('.json.backup')
                    with open(backup_path, 'w') as f:
                        f.write(content)
                    repair_results["backup_created"] = True
                    
                    # Write fixed content
                    with open(rules_path, 'w') as f:
                        f.write(fixed_content)
                    
                    rules = json.loads(fixed_content)
                    repair_results["valid_json"] = True
                    repair_results["rules_repaired"] += 1
                    repair_results["issues_found"].append("Healed JSON syntax errors")
                    self.healing_stats["rule_recoveries"] += 1
                else:
                    repair_results["issues_found"].append("Failed to heal JSON syntax errors")
                    return repair_results
            
            # Validate rule structure
            if "defaults" not in rules:
                rules["defaults"] = {
                    "sections": ["overview", "example"],
                    "max_tokens": 2000
                }
                repair_results["rules_repaired"] += 1
                repair_results["issues_found"].append("Added missing defaults")
            
            # Validate individual rules
            for framework, operations in rules.items():
                if framework == "defaults":
                    continue
                
                if not isinstance(operations, dict):
                    continue
                
                for operation, rule in operations.items():
                    repair_results["rules_validated"] += 1
                    
                    if not isinstance(rule, dict):
                        continue
                    
                    # Ensure required fields
                    if "sections" not in rule or not rule["sections"]:
                        rule["sections"] = ["overview", "example"]
                        repair_results["rules_repaired"] += 1
                        repair_results["issues_found"].append(f"Fixed missing sections in {framework}:{operation}")
                    
                    if "max_tokens" not in rule or rule["max_tokens"] <= 0:
                        rule["max_tokens"] = 2000
                        repair_results["rules_repaired"] += 1
                        repair_results["issues_found"].append(f"Fixed invalid max_tokens in {framework}:{operation}")
            
            # Write back if repairs were made
            if repair_results["rules_repaired"] > 0:
                with open(rules_path, 'w') as f:
                    json.dump(rules, f, indent=2)
            
        except Exception as e:
            repair_results["issues_found"].append(f"Error validating rules: {e}")
        
        self._log_healing_action("rules_repair", repair_results)
        return repair_results
    
    def check_database_health(self) -> Dict:
        """Check and repair database health issues."""
        
        health_results = {
            "database_accessible": True,
            "tables_exist": True,
            "indexes_exist": True,
            "integrity_ok": True,
            "issues_found": [],
            "repairs_made": []
        }
        
        try:
            with self.db.get_connection() as conn:
                # Check if tables exist
                tables = conn.execute('''
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name IN ('context_cache', 'session_logs')
                ''').fetchall()
                
                table_names = [t['name'] for t in tables]
                
                if 'context_cache' not in table_names:
                    health_results["tables_exist"] = False
                    health_results["issues_found"].append("Missing context_cache table")
                    # Recreate table
                    self.db._init_database()
                    health_results["repairs_made"].append("Recreated context_cache table")
                    self.healing_stats["database_repairs"] += 1
                
                if 'session_logs' not in table_names:
                    health_results["tables_exist"] = False
                    health_results["issues_found"].append("Missing session_logs table")
                    # This would be recreated by init_database if the schema includes it
                    health_results["repairs_made"].append("Noted missing session_logs table")
                
                # Check indexes
                indexes = conn.execute('''
                    SELECT name FROM sqlite_master 
                    WHERE type='index' AND name LIKE 'idx_%'
                ''').fetchall()
                
                if not indexes:
                    health_results["indexes_exist"] = False
                    health_results["issues_found"].append("Missing database indexes")
                    # Indexes would be recreated by init_database
                
                # Run integrity check
                integrity = conn.execute('PRAGMA integrity_check').fetchone()
                if integrity[0] != 'ok':
                    health_results["integrity_ok"] = False
                    health_results["issues_found"].append(f"Database integrity issue: {integrity[0]}")
                
        except sqlite3.Error as e:
            health_results["database_accessible"] = False
            health_results["issues_found"].append(f"Database access error: {e}")
        
        self._log_healing_action("database_health", health_results)
        return health_results
    
    def _log_healing_action(self, action_type: str, details: Dict) -> None:
        """Log a healing action for analysis."""
        
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "action_type": action_type,
            "details": details,
            "healing_id": hashlib.md5(f"{action_type}_{datetime.now().isoformat()}".encode()).hexdigest()[:8]
        }
        
        # Load existing log
        healing_log = []
        if self.healing_log_path.exists():
            try:
                with open(self.healing_log_path, 'r') as f:
                    healing_log = json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                healing_log = []
        
        # Add new entry
        healing_log.append(log_entry)
        
        # Keep only last 100 entries
        healing_log = healing_log[-100:]
        
        # Save log
        try:
            with open(self.healing_log_path, 'w') as f:
                json.dump(healing_log, f, indent=2)
        except Exception:
            pass  # Fail silently for logging
    
    def run_comprehensive_health_check(self) -> Dict:
        """Run a comprehensive health check and repair cycle."""
        
        health_report = {
            "timestamp": datetime.now().isoformat(),
            "database_health": self.check_database_health(),
            "cache_validation": self.validate_and_repair_cache(),
            "rules_validation": self.validate_and_repair_rules(),
            "healing_stats": self.healing_stats.copy(),
            "overall_health": "unknown"
        }
        
        # Determine overall health
        issues_count = (
            len(health_report["database_health"]["issues_found"]) +
            len(health_report["cache_validation"]["issues_found"]) +
            len(health_report["rules_validation"]["issues_found"])
        )
        
        if issues_count == 0:
            health_report["overall_health"] = "healthy"
        elif issues_count <= 3:
            health_report["overall_health"] = "minor_issues"
        else:
            health_report["overall_health"] = "needs_attention"
        
        return health_report
    
    def get_healing_history(self, days: int = 7) -> List[Dict]:
        """Get healing action history."""
        
        if not self.healing_log_path.exists():
            return []
        
        try:
            with open(self.healing_log_path, 'r') as f:
                healing_log = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return []
        
        # Filter by date range
        cutoff_date = datetime.now() - timedelta(days=days)
        
        recent_log = []
        for entry in healing_log:
            try:
                entry_date = datetime.fromisoformat(entry["timestamp"])
                if entry_date >= cutoff_date:
                    recent_log.append(entry)
            except (ValueError, KeyError):
                continue
        
        return sorted(recent_log, key=lambda x: x["timestamp"], reverse=True)