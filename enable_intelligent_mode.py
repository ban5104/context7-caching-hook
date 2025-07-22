#!/usr/bin/env python3
"""
Script to enable/disable the intelligent autonomous learning mode.
"""

import json
import shutil
from pathlib import Path
import sys

def get_hook_config_path():
    """Get the path to Claude's hook configuration."""
    # This path may vary - adjust based on your Claude installation
    config_paths = [
        Path.home() / '.claude' / 'hooks.json',
        Path.home() / '.config' / 'claude' / 'hooks.json',
        Path.home() / '.claude' / 'config' / 'hooks.json'
    ]
    
    for path in config_paths:
        if path.exists():
            return path
    
    # If no config exists, create default location
    default_path = Path.home() / '.claude' / 'hooks.json'
    default_path.parent.mkdir(parents=True, exist_ok=True)
    return default_path

def enable_intelligent_mode():
    """Switch to the intelligent PostToolUse hook."""
    
    print("🧠 Enabling Intelligent Autonomous Learning Mode")
    print("=" * 50)
    
    # Update hook configuration
    config_path = get_hook_config_path()
    
    # Load current config or create new
    if config_path.exists():
        with open(config_path, 'r') as f:
            config = json.load(f)
    else:
        config = {}
    
    # Ensure hooks structure exists
    if 'hooks' not in config:
        config['hooks'] = {}
    
    # Update PostToolUse hook
    project_root = Path(__file__).parent
    intelligent_hook_path = project_root / 'intelligent_posttooluse_hook.py'
    
    config['hooks']['PostToolUse'] = {
        'command': f'python3 {intelligent_hook_path}',
        'description': 'Intelligent autonomous learning system'
    }
    
    # Save updated config
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
    
    print(f"✅ Updated hook configuration at: {config_path}")
    print(f"✅ PostToolUse now uses: {intelligent_hook_path}")
    
    # Show what changed
    print("\n📋 New PostToolUse Hook Features:")
    print("- Analyzes full conversation context")
    print("- Uses LLM to determine if docs were helpful")
    print("- Updates rules immediately when needed")
    print("- No thresholds or waiting periods")
    
    return True

def disable_intelligent_mode():
    """Switch back to the old PostToolUse hook."""
    
    print("📊 Switching Back to Metric-Based Learning Mode")
    print("=" * 50)
    
    config_path = get_hook_config_path()
    
    if config_path.exists():
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        # Update to old hook
        project_root = Path(__file__).parent
        old_hook_path = project_root / 'session_tracker.py'
        
        if 'hooks' in config and 'PostToolUse' in config['hooks']:
            config['hooks']['PostToolUse'] = {
                'command': f'python3 {old_hook_path}',
                'description': 'Session outcome tracker'
            }
            
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)
            
            print(f"✅ Reverted to old hook: {old_hook_path}")
    
    return True

def check_current_mode():
    """Check which mode is currently active."""
    
    print("🔍 Checking Current Learning Mode")
    print("=" * 50)
    
    config_path = get_hook_config_path()
    
    if config_path.exists():
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        if 'hooks' in config and 'PostToolUse' in config['hooks']:
            command = config['hooks']['PostToolUse'].get('command', '')
            
            if 'intelligent' in command:
                print("✅ Intelligent Mode is ACTIVE")
                print("   - Learning from conversation context")
                print("   - Immediate rule updates")
                print("   - LLM-powered analysis")
            else:
                print("📊 Metric-Based Mode is ACTIVE")
                print("   - Learning from success metrics")
                print("   - Batch updates after many sessions")
                print("   - Threshold-based decisions")
            
            print(f"\nCurrent hook: {command}")
    else:
        print("❌ No hook configuration found")

def show_usage():
    """Show usage instructions."""
    
    print("\n📖 Usage:")
    print("  python3 enable_intelligent_mode.py enable   # Switch to intelligent mode")
    print("  python3 enable_intelligent_mode.py disable  # Switch to old mode")
    print("  python3 enable_intelligent_mode.py check    # Check current mode")
    print("  python3 enable_intelligent_mode.py          # Show this help")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == 'enable':
            enable_intelligent_mode()
        elif command == 'disable':
            disable_intelligent_mode()
        elif command == 'check':
            check_current_mode()
        else:
            show_usage()
    else:
        check_current_mode()
        show_usage()