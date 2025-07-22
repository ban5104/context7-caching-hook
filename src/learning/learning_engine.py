# ~/projects/cc-rag/src/learning/learning_engine.py
import json
from pathlib import Path
from typing import Dict, Tuple, List
from datetime import datetime
import sys

# Add analyzers and validation to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'analyzers'))
sys.path.insert(0, str(Path(__file__).parent.parent / 'validation'))
from pattern_analyzer import OperationPatternAnalyzer
from rule_validator import RuleValidator

class LearningEngine:
    """Learns from effectiveness data to improve context extraction rules."""
    
    def __init__(self, db_manager, llm_analyzer):
        self.db = db_manager
        self.analyzer = llm_analyzer
        self.pattern_analyzer = OperationPatternAnalyzer(db_manager)
        self.rule_validator = RuleValidator(db_manager)
    
    def run_learning_cycle(self, days: int = 7) -> dict:
        """Runs a complete learning cycle: analyze sessions → update rules."""
        
        # First, process any unanalyzed sessions
        processed_sessions = self.analyzer.process_unanalyzed_sessions(50)
        
        # Analyze operation patterns for predictive insights
        pattern_analysis = self.pattern_analyzer.analyze_operation_sequences(days * 2)  # Longer period for patterns
        
        # Analyze user coding style
        style_analysis = self.pattern_analyzer.analyze_user_coding_style(days)
        
        # Generate effectiveness insights
        insights = self.db.get_effectiveness_insights(days)
        
        # Update rules based on insights and patterns
        updated_rules = self._generate_optimized_rules(insights, pattern_analysis, style_analysis)
        
        # Validate and apply new rules
        rules_updated, validation_results = self._validate_and_apply_rules(updated_rules)
        
        # Generate comprehensive report
        report = self.analyzer.generate_effectiveness_report(days)
        
        return {
            "sessions_analyzed": processed_sessions,
            "rules_updated": rules_updated,
            "total_insights": len(insights),
            "pattern_analysis": pattern_analysis,
            "style_analysis": style_analysis,
            "validation_results": validation_results,
            "effectiveness_report": report,
            "timestamp": datetime.now().isoformat()
        }
    
    def _generate_optimized_rules(self, insights: Dict, pattern_analysis: Dict = None, style_analysis: Dict = None) -> Dict:
        """Generate optimized rules based on effectiveness insights, patterns, and user style."""
        new_rules = {}
        
        for framework_op, sections_data in insights.items():
            framework, operation = framework_op.split(':', 1)
            
            # Filter for high-performing sections (lowered threshold temporarily)
            # TODO: Raise back to 0.6 once we have better effectiveness data
            effective_sections = [
                s for s in sections_data 
                if s['avg_effectiveness'] > 0.3 and s['usage_count'] >= 2
            ]
            
            if effective_sections:
                # Sort by effectiveness score
                effective_sections.sort(key=lambda x: x['avg_effectiveness'], reverse=True)
                
                # Take top performing sections, but ensure we have at least 2
                top_sections = [s['section_name'] for s in effective_sections[:6]]
                
                # If we don't have enough effective sections, add some defaults
                if len(top_sections) < 2:
                    defaults = ['overview', 'example', 'usage', 'api']
                    for default in defaults:
                        if default not in top_sections:
                            top_sections.append(default)
                            if len(top_sections) >= 4:
                                break
                
                # Determine optimal token budget based on average usage and user style
                avg_tokens = sum(s['usage_count'] for s in effective_sections) / len(effective_sections)
                base_budget = min(3000, max(1500, int(avg_tokens * 1.2)))
                
                # Adjust based on user preferences
                if style_analysis:
                    doc_pref = style_analysis.get("coding_style_insights", {}).get("documentation_preference", "balanced")
                    if doc_pref == "comprehensive":
                        base_budget = min(4000, int(base_budget * 1.3))
                    elif doc_pref == "light":
                        base_budget = max(1000, int(base_budget * 0.8))
                
                token_budget = base_budget
                
                # Store the optimized rule
                if framework not in new_rules:
                    new_rules[framework] = {}
                
                # Build rule with pattern-based enhancements
                rule = {
                    "sections": top_sections,
                    "max_tokens": token_budget,
                    "confidence": round(sum(s['avg_confidence'] for s in effective_sections) / len(effective_sections), 2),
                    "based_on_sessions": sum(s['usage_count'] for s in effective_sections)
                }
                
                # Add pattern-based enhancements
                if pattern_analysis:
                    # Check if this operation appears in common sequences
                    next_ops = pattern_analysis.get("prediction_rules", {}).get("next_operation_predictions", {})
                    if operation in next_ops:
                        rule["predicted_next_operations"] = next_ops[operation]
                    
                    # Add preload recommendations if this context appears in high-effectiveness patterns
                    preload_recs = pattern_analysis.get("prediction_rules", {}).get("preload_recommendations", [])
                    relevant_preloads = [
                        rec for rec in preload_recs 
                        if operation in rec.get("recommended_operations", [])
                    ]
                    if relevant_preloads:
                        rule["high_effectiveness_context"] = True
                        rule["preload_priority"] = "high"
                
                new_rules[framework][operation] = rule
        
        return new_rules
    
    def _validate_and_apply_rules(self, new_rules: Dict) -> Tuple[int, Dict]:
        """Validate new rules and apply them with A/B testing for significant changes."""
        
        # Load existing rules
        rules_path = Path.home() / '.claude' / 'context7_rules.json'
        existing_rules = {}
        if rules_path.exists():
            try:
                with open(rules_path, 'r') as f:
                    existing_rules = json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                existing_rules = {}
        
        # Validate the new rules
        validation_results = self.rule_validator.validate_rule_changes(existing_rules, new_rules)
        
        if not validation_results["valid"]:
            return 0, validation_results
        
        # Apply rules with A/B testing for significant changes
        rules_updated = 0
        ab_tests_started = 0
        
        for framework, operations in new_rules.items():
            if framework not in existing_rules:
                existing_rules[framework] = {}
            
            for operation, rule_data in operations.items():
                old_rule = existing_rules[framework].get(operation, {})
                
                if self._should_ab_test_rule(old_rule, rule_data):
                    # Start A/B test for significant changes
                    test_id = self.rule_validator.setup_ab_test(
                        framework, operation, old_rule, rule_data, test_duration_days=7
                    )
                    ab_tests_started += 1
                    validation_results.setdefault("ab_tests_started", []).append({
                        "framework": framework,
                        "operation": operation,
                        "test_id": test_id
                    })
                elif self._should_update_rule(old_rule, rule_data):
                    # Apply rule directly for minor changes
                    existing_rules[framework][operation] = {
                        "sections": rule_data["sections"],
                        "max_tokens": rule_data["max_tokens"],
                        "_learning_metadata": {
                            "confidence": rule_data["confidence"],
                            "based_on_sessions": rule_data["based_on_sessions"],
                            "last_updated": datetime.now().isoformat(),
                            "pattern_enhanced": bool(rule_data.get("predicted_next_operations"))
                        }
                    }
                    
                    # Copy pattern data if present
                    if "predicted_next_operations" in rule_data:
                        existing_rules[framework][operation]["_pattern_data"] = {
                            "predicted_next_operations": rule_data["predicted_next_operations"],
                            "preload_priority": rule_data.get("preload_priority", "medium")
                        }
                    
                    rules_updated += 1
        
        # Ensure defaults exist
        if 'defaults' not in existing_rules:
            existing_rules['defaults'] = {
                "sections": ["overview", "example", "usage"],
                "max_tokens": 2000
            }
        
        # Write updated rules back to file
        rules_path.parent.mkdir(parents=True, exist_ok=True)
        with open(rules_path, 'w') as f:
            json.dump(existing_rules, f, indent=2)
        
        validation_results["ab_tests_started_count"] = ab_tests_started
        return rules_updated, validation_results
    
    def _should_ab_test_rule(self, old_rule: Dict, new_rule: Dict) -> bool:
        """Determine if a rule change is significant enough to warrant A/B testing."""
        
        if not old_rule:
            return False  # New rules don't need A/B testing
        
        # Check for significant token budget changes
        old_tokens = old_rule.get("max_tokens", 2000)
        new_tokens = new_rule.get("max_tokens", 2000)
        
        if abs(new_tokens - old_tokens) > old_tokens * 0.3:  # 30% change
            return True
        
        # Check for significant section changes
        old_sections = set(old_rule.get("sections", []))
        new_sections = set(new_rule.get("sections", []))
        
        # If more than half the sections changed
        if len(old_sections.symmetric_difference(new_sections)) > len(old_sections) * 0.5:
            return True
        
        # Check if this is a high-confidence rule with enough data
        confidence = new_rule.get("confidence", 0.5)
        sessions = new_rule.get("based_on_sessions", 0)
        
        if confidence > 0.8 and sessions >= 10:
            return True
        
        return False
    
    def _should_update_rule(self, old_rule: Dict, new_rule: Dict) -> bool:
        """Determine if a rule should be updated based on confidence and data."""
        
        # Always update if no old rule exists
        if not old_rule:
            return True
        
        # Don't update if new rule has low confidence (lowered threshold)
        # TODO: Raise back to 0.6 once we have better data
        if new_rule.get("confidence", 0) < 0.3:
            return False
        
        # Update if new rule has significantly more data
        old_sessions = old_rule.get("_learning_metadata", {}).get("based_on_sessions", 0)
        new_sessions = new_rule.get("based_on_sessions", 0)
        
        if new_sessions > old_sessions * 1.5:  # 50% more data
            return True
        
        # Update if new rule has higher confidence with decent data
        old_confidence = old_rule.get("_learning_metadata", {}).get("confidence", 0.5)
        new_confidence = new_rule.get("confidence", 0)
        
        if new_confidence > old_confidence + 0.1 and new_sessions >= 5:
            return True
        
        return False
    
    def get_learning_status(self) -> Dict:
        """Get current learning system status."""
        with self.db.get_connection() as conn:
            # Count unanalyzed sessions
            unanalyzed_count = conn.execute(
                "SELECT COUNT(*) as count FROM session_logs WHERE analyzed_at IS NULL"
            ).fetchone()['count']
            
            # Count total sessions in last 7 days
            recent_sessions = conn.execute(
                "SELECT COUNT(*) as count FROM session_logs WHERE timestamp > datetime('now', '-7 days')"
            ).fetchone()['count']
            
            # Average effectiveness score
            avg_effectiveness = conn.execute(
                "SELECT AVG(effectiveness_score) as avg FROM session_logs WHERE effectiveness_score IS NOT NULL"
            ).fetchone()['avg'] or 0
        
        rules_path = Path.home() / '.claude' / 'context7_rules.json'
        rules_exist = rules_path.exists()
        
        return {
            "unanalyzed_sessions": unanalyzed_count,
            "recent_sessions_7d": recent_sessions,
            "avg_effectiveness": round(avg_effectiveness, 3),
            "rules_file_exists": rules_exist,
            "last_learning_cycle": "Never" if not rules_exist else "Unknown"  # Could track this in metadata
        }
    
    def get_active_ab_tests(self) -> List[Dict]:
        """Get information about currently active A/B tests."""
        return self.rule_validator.get_all_test_results()
    
    def finalize_completed_tests(self) -> Dict:
        """Finalize A/B tests that have completed and apply winning rules."""
        
        test_results = self.rule_validator.get_all_test_results()
        finalized = 0
        rules_adopted = 0
        
        for test in test_results:
            if (test["status"] == "completed" and 
                test["sufficient_data"] and 
                test["recommendation"] == "adopt_test_rule"):
                
                # Apply the winning test rule
                rules_path = Path.home() / '.claude' / 'context7_rules.json'
                existing_rules = {}
                
                if rules_path.exists():
                    try:
                        with open(rules_path, 'r') as f:
                            existing_rules = json.load(f)
                    except (json.JSONDecodeError, FileNotFoundError):
                        existing_rules = {}
                
                # Get the test configuration to extract the winning rule
                test_file = self.rule_validator.test_results_path / f"{test['test_id']}.json"
                if test_file.exists():
                    try:
                        with open(test_file, 'r') as f:
                            test_config = json.load(f)
                        
                        framework = test_config["framework"]
                        operation = test_config["operation"]
                        winning_rule = test_config["test_rule"]
                        
                        if framework not in existing_rules:
                            existing_rules[framework] = {}
                        
                        existing_rules[framework][operation] = {
                            "sections": winning_rule["sections"],
                            "max_tokens": winning_rule["max_tokens"],
                            "_learning_metadata": {
                                "confidence": winning_rule.get("confidence", 0.8),
                                "based_on_sessions": winning_rule.get("based_on_sessions", 0),
                                "last_updated": datetime.now().isoformat(),
                                "ab_test_winner": True,
                                "test_id": test["test_id"],
                                "improvement_pct": test["improvement_percentage"]
                            }
                        }
                        
                        # Write updated rules
                        with open(rules_path, 'w') as f:
                            json.dump(existing_rules, f, indent=2)
                        
                        rules_adopted += 1
                        
                    except (json.JSONDecodeError, FileNotFoundError):
                        pass
                
                finalized += 1
        
        # Clean up old tests
        cleaned = self.rule_validator.cleanup_old_tests(30)
        
        return {
            "tests_finalized": finalized,
            "rules_adopted_from_tests": rules_adopted,
            "old_tests_cleaned": cleaned
        }