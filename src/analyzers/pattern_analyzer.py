# ~/projects/cc-rag/src/analyzers/pattern_analyzer.py
import json
from collections import defaultdict, Counter
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta

class OperationPatternAnalyzer:
    """Analyzes patterns in operation sequences to predict future documentation needs."""
    
    def __init__(self, db_manager):
        self.db = db_manager
    
    def analyze_operation_sequences(self, days: int = 30, min_sequence_length: int = 2) -> Dict:
        """Analyze common sequences of operations for predictive caching."""
        
        sequences = self._extract_operation_sequences(days, min_sequence_length)
        patterns = self._identify_sequence_patterns(sequences)
        predictions = self._generate_prediction_rules(patterns)
        
        return {
            "analysis_period_days": days,
            "total_sequences": len(sequences),
            "common_patterns": patterns,
            "prediction_rules": predictions,
            "timestamp": datetime.now().isoformat()
        }
    
    def _extract_operation_sequences(self, days: int, min_length: int) -> List[List[Dict]]:
        """Extract sequences of operations from session logs."""
        
        with self.db.get_connection() as conn:
            # Get sessions grouped by user activity periods (within 1 hour)
            results = conn.execute('''
                WITH session_groups AS (
                    SELECT 
                        l.*,
                        c.framework,
                        LAG(l.timestamp) OVER (ORDER BY l.timestamp) as prev_timestamp,
                        CASE 
                            WHEN julianday(l.timestamp) - julianday(LAG(l.timestamp) OVER (ORDER BY l.timestamp)) > 0.042 -- 1 hour
                            THEN 1 
                            ELSE 0 
                        END as new_group
                    FROM session_logs l
                    JOIN context_cache c ON l.cache_key = c.cache_key
                    WHERE l.timestamp > datetime('now', '-' || ? || ' days')
                    ORDER BY l.timestamp
                ),
                numbered_groups AS (
                    SELECT *,
                        SUM(new_group) OVER (ORDER BY timestamp ROWS UNBOUNDED PRECEDING) as group_id
                    FROM session_groups
                )
                SELECT 
                    group_id,
                    framework,
                    operation_type,
                    cache_key,
                    effectiveness_score,
                    timestamp,
                    ROW_NUMBER() OVER (PARTITION BY group_id ORDER BY timestamp) as sequence_position
                FROM numbered_groups
                WHERE effectiveness_score IS NOT NULL
                ORDER BY group_id, timestamp
            ''', (days,)).fetchall()
            
            # Group results by session group
            sequences = defaultdict(list)
            for row in results:
                sequences[row['group_id']].append(dict(row))
            
            # Filter for sequences meeting minimum length
            return [seq for seq in sequences.values() if len(seq) >= min_length]
    
    def _identify_sequence_patterns(self, sequences: List[List[Dict]]) -> Dict:
        """Identify common patterns in operation sequences."""
        
        # Extract different types of patterns
        operation_sequences = []
        framework_transitions = []
        effectiveness_patterns = []
        
        for sequence in sequences:
            # Operation sequence patterns
            ops = [step['operation_type'] for step in sequence]
            if len(ops) >= 2:
                for i in range(len(ops) - 1):
                    operation_sequences.append((ops[i], ops[i + 1]))
                
                # Also capture 3-step sequences
                if len(ops) >= 3:
                    for i in range(len(ops) - 2):
                        operation_sequences.append((ops[i], ops[i + 1], ops[i + 2]))
            
            # Framework transition patterns
            frameworks = [step['framework'] for step in sequence]
            prev_fw = None
            for fw in frameworks:
                if prev_fw and prev_fw != fw:
                    framework_transitions.append((prev_fw, fw))
                prev_fw = fw
            
            # Effectiveness patterns (what works well together)
            for i, step in enumerate(sequence):
                if step['effectiveness_score'] and step['effectiveness_score'] > 0.7:
                    context = []
                    # Look at previous operations for context
                    for j in range(max(0, i-2), i):
                        context.append(sequence[j]['operation_type'])
                    
                    if context:
                        effectiveness_patterns.append((
                            tuple(context), 
                            step['operation_type'], 
                            step['effectiveness_score']
                        ))
        
        # Count patterns and find most common
        op_counter = Counter(operation_sequences)
        fw_counter = Counter(framework_transitions)
        eff_patterns = defaultdict(list)
        
        for context, operation, score in effectiveness_patterns:
            eff_patterns[context].append((operation, score))
        
        return {
            "common_operation_sequences": [
                {"sequence": seq, "count": count, "confidence": count / len(sequences)}
                for seq, count in op_counter.most_common(10)
            ],
            "framework_transitions": [
                {"from": fw_from, "to": fw_to, "count": count}
                for (fw_from, fw_to), count in fw_counter.most_common(5)
            ],
            "high_effectiveness_contexts": {
                str(context): {
                    "operations": list(set(op for op, _ in ops)),
                    "avg_effectiveness": sum(score for _, score in ops) / len(ops),
                    "frequency": len(ops)
                }
                for context, ops in eff_patterns.items() if len(ops) >= 3
            }
        }
    
    def _generate_prediction_rules(self, patterns: Dict) -> Dict:
        """Generate prediction rules based on identified patterns."""
        
        prediction_rules = {
            "next_operation_predictions": {},
            "framework_specific_sequences": {},
            "preload_recommendations": []
        }
        
        # Generate next operation predictions
        for pattern_data in patterns["common_operation_sequences"]:
            sequence = pattern_data["sequence"]
            confidence = pattern_data["confidence"]
            
            if len(sequence) == 2 and confidence > 0.1:  # 10% minimum confidence
                current_op, next_op = sequence
                if current_op not in prediction_rules["next_operation_predictions"]:
                    prediction_rules["next_operation_predictions"][current_op] = []
                
                prediction_rules["next_operation_predictions"][current_op].append({
                    "operation": next_op,
                    "confidence": confidence,
                    "preload_priority": "high" if confidence > 0.3 else "medium"
                })
        
        # Generate framework-specific recommendations
        for context_str, context_data in patterns["high_effectiveness_contexts"].items():
            if context_data["avg_effectiveness"] > 0.8 and context_data["frequency"] >= 5:
                prediction_rules["preload_recommendations"].append({
                    "context": context_str,
                    "recommended_operations": context_data["operations"],
                    "effectiveness": context_data["avg_effectiveness"],
                    "priority": "high" if context_data["avg_effectiveness"] > 0.9 else "medium"
                })
        
        return prediction_rules
    
    def get_prediction_for_operation(self, current_operation: str, framework: str) -> Optional[Dict]:
        """Get prediction for what documentation to preload based on current operation."""
        
        # Get recent pattern analysis
        recent_analysis = self.analyze_operation_sequences(days=7, min_sequence_length=2)
        predictions = recent_analysis["prediction_rules"]["next_operation_predictions"]
        
        if current_operation in predictions:
            # Sort by confidence and return top prediction
            sorted_predictions = sorted(
                predictions[current_operation], 
                key=lambda x: x["confidence"], 
                reverse=True
            )
            
            if sorted_predictions and sorted_predictions[0]["confidence"] > 0.15:
                return {
                    "predicted_operation": sorted_predictions[0]["operation"],
                    "confidence": sorted_predictions[0]["confidence"],
                    "preload_priority": sorted_predictions[0]["preload_priority"],
                    "framework": framework
                }
        
        return None
    
    def analyze_user_coding_style(self, days: int = 14) -> Dict:
        """Analyze user's coding patterns and preferences."""
        
        with self.db.get_connection() as conn:
            # Get user's operation frequency
            op_frequency = conn.execute('''
                SELECT 
                    operation_type,
                    COUNT(*) as frequency,
                    AVG(effectiveness_score) as avg_effectiveness
                FROM session_logs
                WHERE timestamp > datetime('now', '-' || ? || ' days')
                  AND effectiveness_score IS NOT NULL
                GROUP BY operation_type
                ORDER BY frequency DESC
            ''', (days,)).fetchall()
            
            # Get framework preferences
            fw_preference = conn.execute('''
                SELECT 
                    c.framework,
                    COUNT(*) as usage_count,
                    AVG(l.effectiveness_score) as avg_effectiveness
                FROM session_logs l
                JOIN context_cache c ON l.cache_key = c.cache_key
                WHERE l.timestamp > datetime('now', '-' || ? || ' days')
                  AND l.effectiveness_score IS NOT NULL
                GROUP BY c.framework
                ORDER BY usage_count DESC
            ''', (days,)).fetchall()
            
            # Get token usage patterns
            token_patterns = conn.execute('''
                SELECT 
                    operation_type,
                    AVG(tokens_used) as avg_tokens,
                    MIN(tokens_used) as min_tokens,
                    MAX(tokens_used) as max_tokens
                FROM session_logs
                WHERE timestamp > datetime('now', '-' || ? || ' days')
                GROUP BY operation_type
            ''', (days,)).fetchall()
        
        return {
            "analysis_period": f"{days} days",
            "operation_preferences": [dict(row) for row in op_frequency],
            "framework_preferences": [dict(row) for row in fw_preference],
            "token_usage_patterns": [dict(row) for row in token_patterns],
            "coding_style_insights": self._generate_style_insights(op_frequency, fw_preference)
        }
    
    def _generate_style_insights(self, op_freq, fw_pref) -> Dict:
        """Generate insights about user's coding style."""
        
        insights = {
            "primary_activity": None,
            "preferred_frameworks": [],
            "documentation_preference": "balanced",  # light, balanced, comprehensive
            "workflow_pattern": "unknown"
        }
        
        if op_freq:
            # Determine primary activity
            top_operation = dict(op_freq[0])
            insights["primary_activity"] = top_operation["operation_type"]
            
            # Determine documentation preference based on effectiveness
            avg_effectiveness = sum(row["avg_effectiveness"] or 0 for row in op_freq) / len(op_freq)
            if avg_effectiveness > 0.8:
                insights["documentation_preference"] = "comprehensive"
            elif avg_effectiveness < 0.6:
                insights["documentation_preference"] = "light"
        
        if fw_pref:
            # Get top 2 frameworks
            insights["preferred_frameworks"] = [
                row["framework"] for row in fw_pref[:2]
            ]
        
        return insights