#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
# ~/projects/cc-rag/context7_analyzer.py
"""
Context7 Learning & Analysis Tool

Commands:
  analyze    - Run effectiveness analysis on unanalyzed sessions
  learn      - Run full learning cycle (analyze + update rules)
  report     - Generate effectiveness report
  status     - Show learning system status
  rules      - Show current rules
"""

import sys
import json
import argparse
from pathlib import Path

# Add project src to the Python path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from db.database_manager import DatabaseManager
from analyzers.llm_effectiveness_analyzer import LLMEffectivenessAnalyzer
from analyzers.pattern_analyzer import OperationPatternAnalyzer
from learning.learning_engine import LearningEngine
from healing.self_healing_manager import SelfHealingManager
from analytics.dashboard_generator import AnalyticsDashboard

def main():
    parser = argparse.ArgumentParser(description="Context7 Learning & Analysis Tool")
    parser.add_argument('command', choices=['analyze', 'learn', 'report', 'status', 'rules', 'tests', 'finalize', 'health', 'heal', 'dashboard'],
                       help='Command to execute')
    parser.add_argument('--days', type=int, default=7,
                       help='Number of days to analyze (default: 7)')
    parser.add_argument('--batch-size', type=int, default=50,
                       help='Batch size for analysis (default: 50)')
    parser.add_argument('--format', choices=['json', 'text'], default='text',
                       help='Output format (default: text)')
    
    args = parser.parse_args()
    
    # Initialize components
    db = DatabaseManager()
    analyzer = LLMEffectivenessAnalyzer(db)
    pattern_analyzer = OperationPatternAnalyzer(db)
    learning_engine = LearningEngine(db, analyzer)
    healing_manager = SelfHealingManager(db)
    dashboard = AnalyticsDashboard(db, analyzer, pattern_analyzer, healing_manager)
    
    try:
        if args.command == 'analyze':
            result = analyzer.process_unanalyzed_sessions(args.batch_size)
            output = {"sessions_analyzed": result}
            message = f"✅ Analyzed {result} sessions"
        
        elif args.command == 'learn':
            result = learning_engine.run_learning_cycle(args.days)
            output = result
            message = f"✅ Learning cycle complete: {result['sessions_analyzed']} sessions analyzed, {result['rules_updated']} rules updated"
        
        elif args.command == 'report':
            result = analyzer.generate_effectiveness_report(args.days)
            output = result
            message = f"📊 Effectiveness report for last {args.days} days"
        
        elif args.command == 'status':
            result = learning_engine.get_learning_status()
            output = result
            message = "📈 Learning system status"
        
        elif args.command == 'rules':
            rules_path = Path.home() / '.claude' / 'context7_rules.json'
            if rules_path.exists():
                with open(rules_path, 'r') as f:
                    result = json.load(f)
                output = result
                message = "📋 Current Context7 rules"
            else:
                output = {"error": "No rules file found"}
                message = "❌ No rules file found at ~/.claude/context7_rules.json"
        
        elif args.command == 'tests':
            result = learning_engine.get_active_ab_tests()
            output = {"active_tests": result}
            message = f"🧪 A/B Tests: {len(result)} active/completed"
        
        elif args.command == 'finalize':
            result = learning_engine.finalize_completed_tests()
            output = result
            message = f"✅ Finalized {result['tests_finalized']} tests, adopted {result['rules_adopted_from_tests']} rules"
        
        elif args.command == 'health':
            result = healing_manager.run_comprehensive_health_check()
            output = result
            health_status = result['overall_health']
            health_icon = "✅" if health_status == "healthy" else "⚠️" if health_status == "minor_issues" else "❌"
            message = f"{health_icon} System health: {health_status}"
        
        elif args.command == 'heal':
            # Run healing and get updated health status
            health_result = healing_manager.run_comprehensive_health_check()
            healing_history = healing_manager.get_healing_history(1)  # Last 1 day
            
            output = {
                "health_check": health_result,
                "recent_healing": healing_history[-5:],  # Last 5 actions
                "healing_stats": healing_manager.healing_stats
            }
            
            total_issues = (
                len(health_result["database_health"]["issues_found"]) +
                len(health_result["cache_validation"]["issues_found"]) +
                len(health_result["rules_validation"]["issues_found"])
            )
            
            message = f"🔧 Healing complete: {total_issues} issues found and addressed"
        
        elif args.command == 'dashboard':
            result = dashboard.generate_comprehensive_report(args.days)
            output = result
            
            # Export HTML dashboard
            html_path = Path.home() / '.claude' / 'context7_dashboard.html'
            dashboard.export_dashboard_html(result, html_path)
            
            message = f"📊 Dashboard generated: {html_path}"
        
        # Output results
        if args.format == 'json':
            print(json.dumps(output, indent=2))
        else:
            print(message)
            if args.command == 'status':
                print(f"  Unanalyzed sessions: {output['unanalyzed_sessions']}")
                print(f"  Recent sessions (7d): {output['recent_sessions_7d']}")
                print(f"  Average effectiveness: {output['avg_effectiveness']}")
                print(f"  Rules file exists: {output['rules_file_exists']}")
            
            elif args.command == 'report':
                print(f"  Average effectiveness: {output['overall_stats']['avg_effectiveness']}")
                print(f"  Frameworks analyzed: {output['overall_stats']['total_frameworks']}")
                
                if output['overall_stats']['top_performing_sections']:
                    print("  Top performing sections:")
                    for section in output['overall_stats']['top_performing_sections']:
                        print(f"    - {section['section']}: {section['score']} ({section['usage']} uses)")
                
                if output['overall_stats']['low_performing_sections']:
                    print("  Low performing sections:")
                    for section in output['overall_stats']['low_performing_sections']:
                        print(f"    - {section['section']}: {section['score']} ({section['usage']} uses)")
            
            elif args.command == 'learn':
                print(f"  Effectiveness report:")
                report = output['effectiveness_report']
                print(f"    - Average effectiveness: {report['overall_stats']['avg_effectiveness']}")
                print(f"    - Frameworks: {report['overall_stats']['total_frameworks']}")
                
                if output.get('validation_results', {}).get('ab_tests_started_count', 0) > 0:
                    print(f"  A/B tests started: {output['validation_results']['ab_tests_started_count']}")
            
            elif args.command == 'tests':
                active_tests = output['active_tests']
                if active_tests:
                    print(f"  Active/Completed A/B Tests:")
                    for test in active_tests[:5]:  # Show top 5
                        status_icon = "🟢" if test["status"] == "active" else "🔵"
                        print(f"    {status_icon} {test['framework']}:{test['operation']} - {test['improvement_percentage']}% improvement")
                else:
                    print("  No A/B tests found")
            
            elif args.command == 'finalize':
                print(f"  Tests finalized: {output['tests_finalized']}")
                print(f"  Rules adopted: {output['rules_adopted_from_tests']}")
                print(f"  Old tests cleaned: {output['old_tests_cleaned']}")
            
            elif args.command == 'health':
                health = output
                print(f"  Database: {'✅' if health['database_health']['database_accessible'] else '❌'}")
                print(f"  Cache: {health['cache_validation']['validated_entries']} entries, {health['cache_validation']['corrupted_entries']} corrupted")
                print(f"  Rules: {'✅' if health['rules_validation']['valid_json'] else '❌'}")
                
                total_issues = (
                    len(health["database_health"]["issues_found"]) +
                    len(health["cache_validation"]["issues_found"]) +
                    len(health["rules_validation"]["issues_found"])
                )
                if total_issues > 0:
                    print(f"  Issues found: {total_issues}")
            
            elif args.command == 'heal':
                health = output['health_check']
                stats = output['healing_stats']
                print(f"  JSON fixes: {stats['json_fixes']}")
                print(f"  Cache repairs: {stats['cache_repairs']}")
                print(f"  Rule recoveries: {stats['rule_recoveries']}")
                print(f"  Database repairs: {stats['database_repairs']}")
                
                if output['recent_healing']:
                    print(f"  Recent healing actions: {len(output['recent_healing'])}")
            
            elif args.command == 'dashboard':
                summary = output['executive_summary']
                print(f"  System Status: {summary['status_indicator']} {summary['system_status']}")
                print(f"  Overall Effectiveness: {summary['overall_effectiveness']:.1%}")
                print(f"  Sessions Analyzed: {summary['total_sessions_analyzed']}")
                print(f"  Cached Items: {summary['cached_documentation_items']}")
                print(f"  Patterns Discovered: {summary['discovered_patterns']}")
                print(f"  HTML Dashboard: ~/.claude/context7_dashboard.html")
    
    except Exception as e:
        import traceback
        if args.format == 'json':
            print(json.dumps({"error": str(e), "traceback": traceback.format_exc()}))
        else:
            print(f"❌ Error: {e}")
            if '--debug' in sys.argv:
                traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()