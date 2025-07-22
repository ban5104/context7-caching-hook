#!/usr/bin/env python3
"""
Test script to demonstrate the intelligent autonomous learning system.
Shows how it immediately learns from conversation context.
"""

import json
import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from analyzers.intelligent_session_analyzer import IntelligentSessionAnalyzer
from db.database_manager import DatabaseManager

def simulate_redis_fastapi_mismatch():
    """
    Simulates the scenario where user wants Redis setup 
    but gets FastAPI documentation.
    """
    
    print("🧪 Testing Intelligent Autonomous Learning")
    print("=" * 50)
    
    # Simulate a session where wrong docs were provided
    session_data = {
        'log_id': 999,  # Simulated
        'cache_key': 'fastapi:redis_setup',
        'operation_type': 'create',
        'sections_provided': '["overview", "example", "usage", "api"]',
        'tokens_used': 188,
        'tool_name': 'Write',
        'session_id': 'test123',
        'file_path': '/home/ben/projects/asset/backend/redis_setup.py'
    }
    
    conversation_context = {
        'user_request': 'Create a Redis setup script for the backend',
        'conversation_snippet': '''
User: Create a Redis setup script for the backend
Assistant: Let me create a Redis setup script...
[Write operation attempted]
Hook: Blocks with FastAPI web framework documentation
Assistant: The hook is providing FastAPI context but I'm creating a Redis setup script, not a FastAPI app.
        ''',
        'tool_sequence': ['Write', 'Hook-Block', 'Work-Around'],
        'llm_feedback': 'Wrong documentation provided - needed Redis client docs, not web framework docs'
    }
    
    # Create analyzer
    analyzer = IntelligentSessionAnalyzer()
    
    # Show current rule
    rules_file = Path.home() / '.claude' / 'context7_rules.json'
    if rules_file.exists():
        with open(rules_file, 'r') as f:
            rules = json.load(f)
        
        print("\n📋 Current Rule:")
        if 'fastapi' in rules and 'redis_setup' in rules.get('fastapi', {}):
            print(json.dumps(rules['fastapi']['redis_setup'], indent=2))
        else:
            print("No specific rule exists yet")
    
    # Analyze the session
    print("\n🤖 Intelligent Analysis:")
    analysis = analyzer.analyze_session_with_llm(session_data, conversation_context)
    print(json.dumps(analysis, indent=2))
    
    # Update rule if needed
    if analysis['should_update_rule']:
        print("\n✨ Updating Rule Immediately...")
        success = analyzer.update_rule_immediately(session_data['cache_key'], analysis)
        
        if success:
            print("✅ Rule updated successfully!")
            
            # Show new rule
            with open(rules_file, 'r') as f:
                rules = json.load(f)
            
            print("\n📋 New Rule:")
            print(json.dumps(rules['fastapi']['redis_setup'], indent=2))
        else:
            print("❌ Failed to update rule")
    else:
        print("\n✅ No rule update needed - documentation was effective")

def show_learning_history():
    """Shows the autonomous learning history."""
    
    log_file = Path.home() / '.claude' / 'autonomous_updates.log'
    
    print("\n\n📚 Autonomous Learning History")
    print("=" * 50)
    
    if log_file.exists():
        with open(log_file, 'r') as f:
            lines = f.readlines()
        
        for line in lines[-10:]:  # Last 10 updates
            try:
                entry = json.loads(line)
                print(f"\n⏰ {entry['timestamp']}")
                print(f"📦 Cache Key: {entry.get('cache_key', 'N/A')}")
                print(f"🎯 Action: {entry.get('action', 'N/A')}")
                
                if 'updates' in entry:
                    print(f"💡 Reasoning: {entry['updates'].get('reasoning', 'N/A')}")
                    print(f"📊 Confidence: {entry['updates'].get('confidence', 0)}")
                
            except json.JSONDecodeError:
                continue
    else:
        print("No learning history yet")

def compare_with_old_system():
    """Shows how the old system would handle this."""
    
    print("\n\n🆚 Old System vs New System")
    print("=" * 50)
    
    print("\n❌ Old System (Metric-Based):")
    print("- Would score this as 0.4 (low token count)")
    print("- Would need 73+ similar sessions before updating")
    print("- No understanding of actual conversation context")
    print("- Days or weeks before improvement")
    
    print("\n✅ New System (Intelligent):")
    print("- Immediately recognizes wrong documentation")
    print("- Updates rule on first occurrence")
    print("- Understands from LLM's own feedback")
    print("- Fixes problem for next user immediately")

if __name__ == "__main__":
    # Test the intelligent system
    simulate_redis_fastapi_mismatch()
    
    # Show learning history
    show_learning_history()
    
    # Compare systems
    compare_with_old_system()
    
    print("\n\n🎉 The system is now truly autonomous!")
    print("It learns from conversation context, not just metrics.")