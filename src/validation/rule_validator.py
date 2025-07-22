# ~/projects/cc-rag/src/validation/rule_validator.py
import json
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import random

class RuleValidator:
    """Validates and A/B tests rule changes before applying them."""
    
    def __init__(self, db_manager):
        self.db = db_manager
        self.test_results_path = Path.home() / '.claude' / 'rule_tests'
        self.test_results_path.mkdir(parents=True, exist_ok=True)
    
    def validate_rule_changes(self, old_rules: Dict, new_rules: Dict) -> Dict:
        """Validate that new rules are reasonable compared to old rules."""
        
        validation_results = {
            "valid": True,
            "warnings": [],
            "errors": [],
            "recommendations": [],
            "summary": {}
        }
        
        # Check for dramatic changes that might indicate problems
        for framework, operations in new_rules.items():
            for operation, rule in operations.items():
                old_rule = old_rules.get(framework, {}).get(operation, {})
                
                # Validate token budget changes
                old_tokens = old_rule.get("max_tokens", 2000)
                new_tokens = rule.get("max_tokens", 2000)
                
                if new_tokens > old_tokens * 2:
                    validation_results["warnings"].append(
                        f"{framework}:{operation} token budget increased dramatically: {old_tokens} → {new_tokens}"
                    )
                elif new_tokens < old_tokens * 0.5:
                    validation_results["warnings"].append(
                        f"{framework}:{operation} token budget decreased significantly: {old_tokens} → {new_tokens}"
                    )
                
                # Validate section changes
                old_sections = set(old_rule.get("sections", []))
                new_sections = set(rule.get("sections", []))
                
                if len(new_sections) == 0:
                    validation_results["errors"].append(
                        f"{framework}:{operation} has no sections defined"
                    )
                    validation_results["valid"] = False
                
                removed_sections = old_sections - new_sections
                if len(removed_sections) > 2:
                    validation_results["warnings"].append(
                        f"{framework}:{operation} removed many sections: {list(removed_sections)}"
                    )
                
                # Check confidence scores
                confidence = rule.get("confidence", 0.5)
                if confidence < 0.3:
                    validation_results["warnings"].append(
                        f"{framework}:{operation} has low confidence: {confidence}"
                    )
                
                # Check data sufficiency
                sessions = rule.get("based_on_sessions", 0)
                if sessions < 3:
                    validation_results["warnings"].append(
                        f"{framework}:{operation} based on few sessions: {sessions}"
                    )
        
        # Generate summary
        validation_results["summary"] = {
            "total_rules": sum(len(ops) for ops in new_rules.values()),
            "frameworks_affected": len(new_rules),
            "warning_count": len(validation_results["warnings"]),
            "error_count": len(validation_results["errors"])
        }
        
        return validation_results
    
    def setup_ab_test(self, framework: str, operation: str, 
                     control_rule: Dict, test_rule: Dict, 
                     test_duration_days: int = 7) -> str:
        """Set up an A/B test between two rules."""
        
        test_id = self._generate_test_id(framework, operation)
        
        test_config = {
            "test_id": test_id,
            "framework": framework,
            "operation": operation,
            "control_rule": control_rule,
            "test_rule": test_rule,
            "start_date": datetime.now().isoformat(),
            "end_date": (datetime.now() + timedelta(days=test_duration_days)).isoformat(),
            "test_duration_days": test_duration_days,
            "traffic_split": 0.5,  # 50/50 split
            "status": "active",
            "results": {
                "control_sessions": 0,
                "test_sessions": 0,
                "control_effectiveness": [],
                "test_effectiveness": []
            }
        }
        
        # Save test configuration
        test_file = self.test_results_path / f"{test_id}.json"
        with open(test_file, 'w') as f:
            json.dump(test_config, f, indent=2)
        
        return test_id
    
    def _generate_test_id(self, framework: str, operation: str) -> str:
        """Generate a unique test ID."""
        content = f"{framework}:{operation}:{datetime.now().isoformat()}"
        return "test_" + hashlib.md5(content.encode()).hexdigest()[:8]
    
    def should_use_test_rule(self, framework: str, operation: str) -> Tuple[bool, Optional[str]]:
        """Determine if a test rule should be used for this request."""
        
        # Find active test for this framework/operation
        active_test = self._get_active_test(framework, operation)
        
        if not active_test:
            return False, None
        
        # Check if test has expired
        end_date = datetime.fromisoformat(active_test["end_date"])
        if datetime.now() > end_date:
            self._mark_test_completed(active_test["test_id"])
            return False, None
        
        # Determine group assignment (consistent per session)
        use_test = random.random() < active_test["traffic_split"]
        
        return use_test, active_test["test_id"]
    
    def _get_active_test(self, framework: str, operation: str) -> Optional[Dict]:
        """Get active test for framework/operation combination."""
        
        for test_file in self.test_results_path.glob("test_*.json"):
            try:
                with open(test_file, 'r') as f:
                    test_config = json.load(f)
                
                if (test_config["framework"] == framework and 
                    test_config["operation"] == operation and 
                    test_config["status"] == "active"):
                    return test_config
            except (json.JSONDecodeError, KeyError):
                continue
        
        return None
    
    def record_test_result(self, test_id: str, is_test_group: bool, 
                          effectiveness_score: float) -> None:
        """Record the result of an A/B test session."""
        
        test_file = self.test_results_path / f"{test_id}.json"
        if not test_file.exists():
            return
        
        try:
            with open(test_file, 'r') as f:
                test_config = json.load(f)
            
            if is_test_group:
                test_config["results"]["test_sessions"] += 1
                test_config["results"]["test_effectiveness"].append(effectiveness_score)
            else:
                test_config["results"]["control_sessions"] += 1
                test_config["results"]["control_effectiveness"].append(effectiveness_score)
            
            with open(test_file, 'w') as f:
                json.dump(test_config, f, indent=2)
                
        except (json.JSONDecodeError, KeyError, FileNotFoundError):
            pass
    
    def _mark_test_completed(self, test_id: str) -> None:
        """Mark a test as completed."""
        
        test_file = self.test_results_path / f"{test_id}.json"
        if not test_file.exists():
            return
        
        try:
            with open(test_file, 'r') as f:
                test_config = json.load(f)
            
            test_config["status"] = "completed"
            test_config["completion_date"] = datetime.now().isoformat()
            
            with open(test_file, 'w') as f:
                json.dump(test_config, f, indent=2)
                
        except (json.JSONDecodeError, KeyError):
            pass
    
    def analyze_test_results(self, test_id: str) -> Dict:
        """Analyze the results of an A/B test."""
        
        test_file = self.test_results_path / f"{test_id}.json"
        if not test_file.exists():
            return {"error": "Test not found"}
        
        try:
            with open(test_file, 'r') as f:
                test_config = json.load(f)
        except json.JSONDecodeError:
            return {"error": "Invalid test file"}
        
        results = test_config["results"]
        
        # Calculate statistics
        control_avg = (sum(results["control_effectiveness"]) / len(results["control_effectiveness"]) 
                      if results["control_effectiveness"] else 0)
        test_avg = (sum(results["test_effectiveness"]) / len(results["test_effectiveness"]) 
                   if results["test_effectiveness"] else 0)
        
        # Simple statistical significance check (basic)
        min_sessions = 20  # Minimum sessions for significance
        control_sufficient = results["control_sessions"] >= min_sessions
        test_sufficient = results["test_sessions"] >= min_sessions
        
        improvement = test_avg - control_avg if control_avg > 0 else 0
        improvement_pct = (improvement / control_avg * 100) if control_avg > 0 else 0
        
        # Determine recommendation
        recommendation = "inconclusive"
        if control_sufficient and test_sufficient:
            if improvement_pct > 5:  # 5% improvement threshold
                recommendation = "adopt_test_rule"
            elif improvement_pct < -5:
                recommendation = "keep_control_rule"
            else:
                recommendation = "no_significant_difference"
        
        return {
            "test_id": test_id,
            "framework": test_config["framework"],
            "operation": test_config["operation"],
            "status": test_config["status"],
            "control_sessions": results["control_sessions"],
            "test_sessions": results["test_sessions"],
            "control_avg_effectiveness": round(control_avg, 3),
            "test_avg_effectiveness": round(test_avg, 3),
            "improvement": round(improvement, 3),
            "improvement_percentage": round(improvement_pct, 1),
            "recommendation": recommendation,
            "sufficient_data": control_sufficient and test_sufficient,
            "test_duration": test_config["test_duration_days"]
        }
    
    def get_all_test_results(self) -> List[Dict]:
        """Get results for all tests."""
        
        results = []
        for test_file in self.test_results_path.glob("test_*.json"):
            test_id = test_file.stem
            result = self.analyze_test_results(test_id)
            if "error" not in result:
                results.append(result)
        
        return sorted(results, key=lambda x: x.get("improvement_percentage", 0), reverse=True)
    
    def cleanup_old_tests(self, days_old: int = 30) -> int:
        """Clean up test files older than specified days."""
        
        cutoff_date = datetime.now() - timedelta(days=days_old)
        cleaned = 0
        
        for test_file in self.test_results_path.glob("test_*.json"):
            try:
                with open(test_file, 'r') as f:
                    test_config = json.load(f)
                
                start_date = datetime.fromisoformat(test_config["start_date"])
                if start_date < cutoff_date:
                    test_file.unlink()
                    cleaned += 1
                    
            except (json.JSONDecodeError, KeyError, FileNotFoundError):
                # Remove corrupted files
                test_file.unlink()
                cleaned += 1
        
        return cleaned