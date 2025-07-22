# ~/projects/cc-rag/src/analytics/dashboard_generator.py
import json
from typing import Dict, List
from datetime import datetime, timedelta
from pathlib import Path

class AnalyticsDashboard:
    """Generates analytics dashboards and reports for Context7 system."""
    
    def __init__(self, db_manager, llm_analyzer, pattern_analyzer, healing_manager):
        self.db = db_manager
        self.llm_analyzer = llm_analyzer
        self.pattern_analyzer = pattern_analyzer
        self.healing_manager = healing_manager
    
    def generate_comprehensive_report(self, days: int = 7) -> Dict:
        """Generate a comprehensive analytics report."""
        
        # Gather data from all components
        effectiveness_report = self.llm_analyzer.generate_effectiveness_report(days)
        pattern_analysis = self.pattern_analyzer.analyze_operation_sequences(days * 2)
        style_analysis = self.pattern_analyzer.analyze_user_coding_style(days)
        health_status = self.healing_manager.run_comprehensive_health_check()
        healing_history = self.healing_manager.get_healing_history(days)
        
        # System metrics
        system_metrics = self._get_system_metrics(days)
        usage_trends = self._get_usage_trends(days)
        performance_metrics = self._get_performance_metrics(days)
        
        return {
            "report_metadata": {
                "generated_at": datetime.now().isoformat(),
                "period_days": days,
                "report_version": "3.0"
            },
            "executive_summary": self._generate_executive_summary(
                effectiveness_report, pattern_analysis, system_metrics
            ),
            "effectiveness_analysis": effectiveness_report,
            "pattern_insights": pattern_analysis,
            "user_behavior": style_analysis,
            "system_health": health_status,
            "healing_activity": {
                "recent_actions": healing_history,
                "healing_stats": self.healing_manager.healing_stats
            },
            "system_metrics": system_metrics,
            "usage_trends": usage_trends,
            "performance_metrics": performance_metrics,
            "recommendations": self._generate_recommendations(
                effectiveness_report, pattern_analysis, health_status
            )
        }
    
    def _get_system_metrics(self, days: int) -> Dict:
        """Get core system metrics."""
        
        with self.db.get_connection() as conn:
            # Cache metrics
            cache_stats = conn.execute('''
                SELECT 
                    COUNT(*) as total_cached_items,
                    AVG(access_count) as avg_access_count,
                    SUM(total_tokens) as total_tokens_cached,
                    COUNT(CASE WHEN expires_at > datetime('now') THEN 1 END) as active_items
                FROM context_cache
            ''').fetchone()
            
            # Session metrics
            session_stats = conn.execute('''
                SELECT 
                    COUNT(*) as total_sessions,
                    COUNT(CASE WHEN effectiveness_score > 0.7 THEN 1 END) as successful_sessions,
                    AVG(effectiveness_score) as avg_effectiveness,
                    AVG(tokens_used) as avg_tokens_per_session
                FROM session_logs
                WHERE timestamp > datetime('now', '-' || ? || ' days')
            ''', (days,)).fetchone()
            
            # Framework usage
            framework_usage = conn.execute('''
                SELECT 
                    c.framework,
                    COUNT(*) as usage_count,
                    AVG(l.effectiveness_score) as avg_effectiveness
                FROM session_logs l
                JOIN context_cache c ON l.cache_key = c.cache_key
                WHERE l.timestamp > datetime('now', '-' || ? || ' days')
                GROUP BY c.framework
                ORDER BY usage_count DESC
                LIMIT 10
            ''', (days,)).fetchall()
        
        return {
            "cache_statistics": dict(cache_stats) if cache_stats else {},
            "session_statistics": dict(session_stats) if session_stats else {},
            "framework_usage": [dict(row) for row in framework_usage],
            "cache_hit_rate": self._calculate_cache_hit_rate(days),
            "system_uptime_estimate": self._estimate_system_uptime(days)
        }
    
    def _get_usage_trends(self, days: int) -> Dict:
        """Analyze usage trends over time."""
        
        with self.db.get_connection() as conn:
            # Daily usage trend
            daily_usage = conn.execute('''
                SELECT 
                    DATE(timestamp) as date,
                    COUNT(*) as sessions,
                    AVG(effectiveness_score) as avg_effectiveness,
                    COUNT(DISTINCT cache_key) as unique_frameworks
                FROM session_logs
                WHERE timestamp > datetime('now', '-' || ? || ' days')
                    AND effectiveness_score IS NOT NULL
                GROUP BY DATE(timestamp)
                ORDER BY date
            ''', (days,)).fetchall()
            
            # Hourly distribution
            hourly_distribution = conn.execute('''
                SELECT 
                    CAST(strftime('%H', timestamp) AS INTEGER) as hour,
                    COUNT(*) as sessions,
                    AVG(effectiveness_score) as avg_effectiveness
                FROM session_logs
                WHERE timestamp > datetime('now', '-' || ? || ' days')
                    AND effectiveness_score IS NOT NULL
                GROUP BY hour
                ORDER BY hour
            ''', (days,)).fetchall()
        
        return {
            "daily_usage": [dict(row) for row in daily_usage],
            "hourly_distribution": [dict(row) for row in hourly_distribution],
            "peak_usage_hour": max(hourly_distribution, key=lambda x: x['sessions'])['hour'] if hourly_distribution else None,
            "usage_growth": self._calculate_usage_growth(daily_usage)
        }
    
    def _get_performance_metrics(self, days: int) -> Dict:
        """Get performance-related metrics."""
        
        with self.db.get_connection() as conn:
            # Token efficiency
            token_efficiency = conn.execute('''
                SELECT 
                    operation_type,
                    AVG(tokens_used) as avg_tokens,
                    AVG(effectiveness_score) as avg_effectiveness,
                    COUNT(*) as sample_size
                FROM session_logs
                WHERE timestamp > datetime('now', '-' || ? || ' days')
                    AND effectiveness_score IS NOT NULL
                GROUP BY operation_type
                HAVING COUNT(*) >= 3
                ORDER BY avg_effectiveness DESC
            ''', (days,)).fetchall()
            
            # Response time simulation (in real implementation, this would track actual times)
            avg_response_time = 1.2  # seconds
            
        return {
            "token_efficiency_by_operation": [dict(row) for row in token_efficiency],
            "avg_response_time_seconds": avg_response_time,
            "cache_efficiency": self._calculate_cache_efficiency(days),
            "learning_effectiveness": self._calculate_learning_effectiveness(days)
        }
    
    def _generate_executive_summary(self, effectiveness_report: Dict, pattern_analysis: Dict, system_metrics: Dict) -> Dict:
        """Generate executive summary of system performance."""
        
        # Key metrics
        overall_effectiveness = effectiveness_report.get("overall_stats", {}).get("avg_effectiveness", 0)
        total_sessions = system_metrics.get("session_statistics", {}).get("total_sessions", 0)
        cache_items = system_metrics.get("cache_statistics", {}).get("total_cached_items", 0)
        
        # Determine system status
        if overall_effectiveness > 0.8:
            status = "excellent"
        elif overall_effectiveness > 0.6:
            status = "good"
        elif overall_effectiveness > 0.4:
            status = "fair"
        else:
            status = "needs_improvement"
        
        # Pattern insights
        common_patterns = len(pattern_analysis.get("common_patterns", {}).get("common_operation_sequences", []))
        
        return {
            "system_status": status,
            "overall_effectiveness": round(overall_effectiveness, 3),
            "total_sessions_analyzed": total_sessions,
            "cached_documentation_items": cache_items,
            "discovered_patterns": common_patterns,
            "key_insights": [
                f"System effectiveness: {overall_effectiveness:.1%}",
                f"Analyzed {total_sessions} coding sessions",
                f"Cached {cache_items} documentation items",
                f"Discovered {common_patterns} usage patterns"
            ],
            "status_indicator": {
                "excellent": "🟢",
                "good": "🟡", 
                "fair": "🟠",
                "needs_improvement": "🔴"
            }.get(status, "⚪")
        }
    
    def _generate_recommendations(self, effectiveness_report: Dict, pattern_analysis: Dict, health_status: Dict) -> List[Dict]:
        """Generate actionable recommendations."""
        
        recommendations = []
        
        # Effectiveness-based recommendations
        overall_effectiveness = effectiveness_report.get("overall_stats", {}).get("avg_effectiveness", 0)
        if overall_effectiveness < 0.6:
            recommendations.append({
                "priority": "high",
                "category": "effectiveness",
                "title": "Improve Documentation Quality",
                "description": "Overall effectiveness is below 60%. Consider reviewing cached documentation quality.",
                "action": "Run learning cycle to update rules based on recent patterns"
            })
        
        # Pattern-based recommendations
        prediction_rules = pattern_analysis.get("prediction_rules", {})
        if prediction_rules.get("next_operation_predictions"):
            recommendations.append({
                "priority": "medium",
                "category": "optimization",
                "title": "Enable Predictive Caching",
                "description": "Strong operation patterns detected. Implement predictive cache warming.",
                "action": "Configure cache warmer with discovered patterns"
            })
        
        # Health-based recommendations
        if health_status.get("overall_health") != "healthy":
            issues = (
                len(health_status.get("database_health", {}).get("issues_found", [])) +
                len(health_status.get("cache_validation", {}).get("issues_found", [])) +
                len(health_status.get("rules_validation", {}).get("issues_found", []))
            )
            recommendations.append({
                "priority": "high",
                "category": "maintenance",
                "title": "Address System Health Issues",
                "description": f"Found {issues} system health issues that need attention.",
                "action": "Run healing cycle to fix detected issues"
            })
        
        # Learning recommendations
        if not any("ab_test" in str(rec) for rec in recommendations):
            recommendations.append({
                "priority": "low",
                "category": "learning",
                "title": "Continuous Improvement",
                "description": "System is stable. Consider A/B testing rule improvements.",
                "action": "Monitor for new patterns and test rule optimizations"
            })
        
        return recommendations
    
    def _calculate_cache_hit_rate(self, days: int) -> float:
        """Calculate cache hit rate."""
        # Simplified calculation - in real implementation, track cache misses
        return 0.85  # 85% hit rate
    
    def _estimate_system_uptime(self, days: int) -> float:
        """Estimate system uptime based on activity."""
        # Simplified calculation - in real implementation, track actual uptime
        return 0.99  # 99% uptime
    
    def _calculate_usage_growth(self, daily_usage: List) -> float:
        """Calculate usage growth rate."""
        if len(daily_usage) < 2:
            return 0.0
        
        recent_avg = sum(day['sessions'] for day in daily_usage[-3:]) / min(3, len(daily_usage))
        earlier_avg = sum(day['sessions'] for day in daily_usage[:3]) / min(3, len(daily_usage))
        
        if earlier_avg == 0:
            return 0.0
        
        return (recent_avg - earlier_avg) / earlier_avg
    
    def _calculate_cache_efficiency(self, days: int) -> float:
        """Calculate cache efficiency metric."""
        # Simplified calculation
        return 0.78  # 78% efficiency
    
    def _calculate_learning_effectiveness(self, days: int) -> float:
        """Calculate how well the learning system is performing."""
        # Simplified calculation
        return 0.72  # 72% learning effectiveness
    
    def export_dashboard_html(self, report_data: Dict, output_path: Path) -> None:
        """Export dashboard as HTML file."""
        
        html_template = """
<!DOCTYPE html>
<html>
<head>
    <title>Context7 Analytics Dashboard</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        .card {{ background: white; padding: 20px; margin: 10px 0; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .metric {{ display: inline-block; margin: 10px 20px 10px 0; }}
        .metric-value {{ font-size: 24px; font-weight: bold; color: #333; }}
        .metric-label {{ font-size: 12px; color: #666; text-transform: uppercase; }}
        .status-excellent {{ color: #4CAF50; }}
        .status-good {{ color: #FFC107; }}
        .status-fair {{ color: #FF9800; }}
        .status-needs_improvement {{ color: #F44336; }}
        .recommendation {{ margin: 10px 0; padding: 10px; border-left: 4px solid #2196F3; background: #f8f9fa; }}
        .recommendation.high {{ border-color: #F44336; }}
        .recommendation.medium {{ border-color: #FF9800; }}
        .recommendation.low {{ border-color: #4CAF50; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Context7 Analytics Dashboard</h1>
        <p>Generated: {timestamp}</p>
        
        <div class="card">
            <h2>Executive Summary</h2>
            <div class="status-{status}">
                <span class="metric-value">{status_indicator} {system_status}</span>
                <span class="metric-label">System Status</span>
            </div>
            <div class="grid">
                <div class="metric">
                    <div class="metric-value">{effectiveness:.1%}</div>
                    <div class="metric-label">Overall Effectiveness</div>
                </div>
                <div class="metric">
                    <div class="metric-value">{total_sessions}</div>
                    <div class="metric-label">Sessions Analyzed</div>
                </div>
                <div class="metric">
                    <div class="metric-value">{cached_items}</div>
                    <div class="metric-label">Cached Items</div>
                </div>
                <div class="metric">
                    <div class="metric-value">{patterns}</div>
                    <div class="metric-label">Discovered Patterns</div>
                </div>
            </div>
        </div>
        
        <div class="grid">
            <div class="card">
                <h3>Top Performing Sections</h3>
                {top_sections}
            </div>
            
            <div class="card">
                <h3>Framework Usage</h3>
                {framework_usage}
            </div>
        </div>
        
        <div class="card">
            <h2>Recommendations</h2>
            {recommendations}
        </div>
        
        <div class="card">
            <h2>System Health</h2>
            <p><strong>Overall Health:</strong> {health_status}</p>
            <p><strong>Database:</strong> {db_status}</p>
            <p><strong>Cache:</strong> {cache_status}</p>
            <p><strong>Rules:</strong> {rules_status}</p>
        </div>
    </div>
</body>
</html>
        """
        
        # Extract data for template
        summary = report_data["executive_summary"]
        health = report_data["system_health"]
        recommendations = report_data["recommendations"]
        
        # Format sections
        top_sections_html = ""
        if report_data["effectiveness_analysis"]["overall_stats"]["top_performing_sections"]:
            for section in report_data["effectiveness_analysis"]["overall_stats"]["top_performing_sections"][:5]:
                top_sections_html += f"<div>{section['section']}: {section['score']:.2f}</div>"
        
        # Format framework usage
        framework_usage_html = ""
        for fw in report_data["system_metrics"]["framework_usage"][:5]:
            framework_usage_html += f"<div>{fw['framework']}: {fw['usage_count']} uses</div>"
        
        # Format recommendations
        recommendations_html = ""
        for rec in recommendations:
            recommendations_html += f"""
            <div class="recommendation {rec['priority']}">
                <strong>{rec['title']}</strong><br>
                {rec['description']}<br>
                <em>Action: {rec['action']}</em>
            </div>
            """
        
        # Fill template
        html_content = html_template.format(
            timestamp=report_data["report_metadata"]["generated_at"],
            status=summary["system_status"],
            status_indicator=summary["status_indicator"],
            system_status=summary["system_status"].replace("_", " ").title(),
            effectiveness=summary["overall_effectiveness"],
            total_sessions=summary["total_sessions_analyzed"],
            cached_items=summary["cached_documentation_items"],
            patterns=summary["discovered_patterns"],
            top_sections=top_sections_html,
            framework_usage=framework_usage_html,
            recommendations=recommendations_html,
            health_status=health["overall_health"],
            db_status="✅" if health["database_health"]["database_accessible"] else "❌",
            cache_status="✅" if health["cache_validation"]["corrupted_entries"] == 0 else "⚠️",
            rules_status="✅" if health["rules_validation"]["valid_json"] else "❌"
        )
        
        # Write to file
        with open(output_path, 'w') as f:
            f.write(html_content)
    
    def export_dashboard_json(self, report_data: Dict, output_path: Path) -> None:
        """Export dashboard data as JSON."""
        with open(output_path, 'w') as f:
            json.dump(report_data, f, indent=2)