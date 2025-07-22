# ~/projects/cc-rag/src/analyzers/llm_effectiveness_analyzer.py
import json
import uuid
from datetime import datetime
from typing import Dict, List, Tuple
from pathlib import Path

class LLMEffectivenessAnalyzer:
    """Uses LLM analysis to determine if cached documentation was effective."""
    
    def __init__(self, db_manager):
        self.db = db_manager
    
    def analyze_session_effectiveness(self, session_data: dict) -> Tuple[float, str, float]:
        """
        Analyzes a session to determine if the cached documentation was effective.
        Returns: (effectiveness_score, reason, confidence_score)
        """
        
        # Build context for LLM analysis
        analysis_prompt = self._build_analysis_prompt(session_data)
        
        # For now, we'll simulate LLM analysis with pattern-based heuristics
        # In a real implementation, this would call an LLM API
        score, reason, confidence = self._simulate_llm_analysis(session_data)
        
        return score, reason, confidence
    
    def _build_analysis_prompt(self, session_data: dict) -> str:
        """Builds a structured prompt for LLM analysis."""
        
        tool_input = json.loads(session_data['tool_input'])
        sections_provided = json.loads(session_data['sections_provided'])
        
        prompt = f"""
Analyze this coding session to determine if the cached documentation was effective:

SESSION CONTEXT:
- Framework: {session_data['cache_key'].split(':')[0]}
- Operation: {session_data['operation_type']}
- File: {session_data['file_path'] or 'Unknown'}
- Tool: {session_data['tool_name']}
- Timestamp: {session_data['timestamp']}

DOCUMENTATION PROVIDED:
- Sections: {', '.join(sections_provided)}
- Token count: {session_data['tokens_used']}

USER'S INTENDED ACTION:
{self._extract_user_intent(tool_input)}

SESSION OUTCOME:
- Completed: {session_data.get('session_complete', 'Unknown')}
- Follow-up actions: {session_data.get('follow_up_actions', 'None recorded')}

EFFECTIVENESS CRITERIA:
1. Did the documentation match the user's intent?
2. Was the session completed successfully?
3. Were there immediate retries or error patterns?
4. Did the user proceed confidently or struggle?

Respond with JSON:
{{
    "effectiveness_score": 0.0-1.0,
    "reason": "Brief explanation of why this was/wasn't effective",
    "confidence": 0.0-1.0
}}
"""
        return prompt
    
    def _extract_user_intent(self, tool_input: dict) -> str:
        """Extracts what the user was trying to accomplish."""
        content = tool_input.get('content', '')
        file_path = tool_input.get('file_path', '')
        
        # Extract key patterns from the content
        intent_indicators = []
        
        if 'function ' in content or 'const ' in content:
            intent_indicators.append("Creating/modifying a function/component")
        if 'import ' in content:
            intent_indicators.append("Adding imports/dependencies")
        if 'style' in content.lower() or 'css' in content.lower():
            intent_indicators.append("Styling/CSS work")
        if 'api' in content.lower() or 'fetch' in content.lower():
            intent_indicators.append("API integration")
        if 'test' in content.lower():
            intent_indicators.append("Testing")
        
        intent_summary = f"File: {file_path}\nContent length: {len(content)} chars\n"
        if intent_indicators:
            intent_summary += f"Likely activities: {', '.join(intent_indicators)}\n"
        
        # Include first few lines of content for context
        content_preview = '\n'.join(content.split('\n')[:5])
        intent_summary += f"Content preview:\n{content_preview}"
        
        return intent_summary
    
    def _simulate_llm_analysis(self, session_data: dict) -> Tuple[float, str, float]:
        """
        Simulates LLM analysis with heuristic patterns.
        In production, this would be replaced with actual LLM API calls.
        """
        
        # Start with base effectiveness score
        score = 0.5
        reasons = []
        confidence = 0.7
        
        # Check session completion
        if session_data.get('session_complete') is True:
            score += 0.3
            reasons.append("session completed successfully")
        elif session_data.get('session_complete') is False:
            score -= 0.2
            reasons.append("session was not completed")
        
        # Check follow-up actions
        follow_up = session_data.get('follow_up_actions')
        if follow_up:
            follow_up_data = json.loads(follow_up) if isinstance(follow_up, str) else follow_up
            
            if any('error' in str(action).lower() for action in follow_up_data):
                score -= 0.3
                reasons.append("errors occurred after using cached context")
            
            if any('context7' in str(action).lower() for action in follow_up_data):
                score -= 0.4
                reasons.append("user immediately sought different documentation")
        
        # Check token efficiency
        tokens = session_data['tokens_used']
        if tokens > 3000:
            score -= 0.1
            reasons.append("high token usage may indicate inefficient context")
        elif tokens < 500:
            score -= 0.1
            reasons.append("very low token usage may indicate insufficient context")
        else:
            score += 0.1
            reasons.append("appropriate token usage")
        
        # Check framework/operation alignment
        cache_key = session_data['cache_key']
        operation = session_data['operation_type']
        
        # Reward common successful patterns
        if 'react:create' in cache_key and operation == 'create':
            score += 0.1
            reasons.append("good framework-operation alignment")
        
        # Ensure score is within bounds
        score = max(0.0, min(1.0, score))
        
        # Adjust confidence based on available data
        if session_data.get('session_complete') is None:
            confidence -= 0.2
        if not session_data.get('follow_up_actions'):
            confidence -= 0.1
        
        reason = f"Analysis based on: {', '.join(reasons)}"
        
        return score, reason, max(0.1, min(1.0, confidence))
    
    def process_unanalyzed_sessions(self, batch_size: int = 10) -> int:
        """Process a batch of unanalyzed sessions."""
        sessions = self.db.get_unanalyzed_sessions(batch_size)
        processed = 0
        
        for session in sessions:
            try:
                score, reason, confidence = self.analyze_session_effectiveness(session)
                self.db.update_effectiveness_analysis(
                    session['log_id'], score, reason, confidence
                )
                processed += 1
            except Exception as e:
                # Log error but continue with other sessions
                print(f"Error analyzing session {session['log_id']}: {e}")
        
        return processed
    
    def generate_effectiveness_report(self, days: int = 7) -> dict:
        """Generate a summary report of documentation effectiveness."""
        insights = self.db.get_effectiveness_insights(days)
        
        report = {
            "period_days": days,
            "timestamp": datetime.now().isoformat(),
            "framework_performance": {},
            "overall_stats": {
                "total_frameworks": len(insights),
                "avg_effectiveness": 0.0,
                "top_performing_sections": [],
                "low_performing_sections": []
            }
        }
        
        all_scores = []
        all_sections = []
        
        for framework_op, sections in insights.items():
            framework, operation = framework_op.split(':', 1)
            
            if framework not in report["framework_performance"]:
                report["framework_performance"][framework] = {}
            
            # Calculate framework-operation performance
            avg_effectiveness = sum(s['avg_effectiveness'] for s in sections) / len(sections)
            total_usage = sum(s['usage_count'] for s in sections)
            
            report["framework_performance"][framework][operation] = {
                "avg_effectiveness": round(avg_effectiveness, 3),
                "total_usage": total_usage,
                "top_sections": [s['section_name'] for s in sections[:3]]
            }
            
            all_scores.extend([s['avg_effectiveness'] for s in sections])
            all_sections.extend(sections)
        
        # Calculate overall stats
        if all_scores:
            report["overall_stats"]["avg_effectiveness"] = round(sum(all_scores) / len(all_scores), 3)
        
        # Find top and low performing sections globally
        all_sections.sort(key=lambda x: x['avg_effectiveness'], reverse=True)
        
        report["overall_stats"]["top_performing_sections"] = [
            {"section": s['section_name'], "score": round(s['avg_effectiveness'], 3), "usage": s['usage_count']}
            for s in all_sections[:5]
        ]
        
        report["overall_stats"]["low_performing_sections"] = [
            {"section": s['section_name'], "score": round(s['avg_effectiveness'], 3), "usage": s['usage_count']}
            for s in all_sections[-5:] if s['avg_effectiveness'] < 0.5
        ]
        
        return report