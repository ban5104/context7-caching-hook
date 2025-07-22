# Context7 Documentation

## Overview

This directory contains comprehensive documentation for the Context7 intelligent hook system.

## Documentation Structure

### Core Documentation

- **[README.md](../README.md)** - Main project overview and quick start guide
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - Detailed system architecture and component design
- **[INTELLIGENT_LEARNING.md](INTELLIGENT_LEARNING.md)** - New LLM-powered autonomous learning system
- **[MIGRATION_GUIDE.md](MIGRATION_GUIDE.md)** - How to migrate from legacy to intelligent learning

### Key Features

#### Intelligent Autonomous Learning (NEW)
The Context7 system now features **conversation-aware learning** that:
- Analyzes full conversation context using LLM reasoning
- Detects documentation mismatches immediately 
- Updates rules on first occurrence, not after 73+ sessions
- Understands user intent from conversation flow
- Recognizes when LLM explicitly states documentation is wrong

#### Traditional Features
- Claude Code hook integration with PreToolUse/PostToolUse events
- Framework detection for React, FastAPI, Supabase, and 10+ frameworks
- Intelligent caching with transcript awareness
- Self-healing and error recovery
- Comprehensive analytics and reporting

## Quick Start

1. **Enable Intelligent Learning**:
   ```bash
   python3 enable_intelligent_mode.py enable
   ```

2. **Test the System**:
   ```bash
   python3 test_intelligent_system.py
   ```

3. **Monitor Learning**:
   ```bash
   tail -f ~/.claude/autonomous_updates.log
   ```

## Learning Modes

### Intelligent Mode (Recommended)
- **Learning**: Immediate from conversation context
- **Decision Making**: LLM-powered analysis
- **Updates**: Real-time rule modifications
- **Understanding**: Contextual user intent

### Legacy Mode
- **Learning**: Statistical effectiveness analysis
- **Decision Making**: Metric-based thresholds
- **Updates**: Batch processing after multiple sessions
- **Understanding**: Token counts and error patterns

## File Structure

```
docs/
├── README.md              # This file
├── ARCHITECTURE.md        # System design and components
├── INTELLIGENT_LEARNING.md # New conversation-aware learning
└── MIGRATION_GUIDE.md     # Legacy to intelligent migration
```

## Key Concepts

### Conversation-Aware Learning
The intelligent system analyzes conversation patterns like:
- "The hook is providing X but I need Y"
- "This documentation is for the wrong purpose"
- Multiple attempts with different approaches
- Explicit LLM feedback about relevance

### Immediate Rule Updates
Instead of waiting for statistical significance:
```json
{
  "fastapi": {
    "redis_setup": {
      "sections": ["redis_client", "setup", "configuration"],
      "_autonomous_update": {
        "reasoning": "Cache provided web framework docs for Redis client setup",
        "confidence": 0.8
      }
    }
  }
}
```

### Safety First
- Only modifies JSON configuration, never Python code
- Complete backup system with timestamped history
- Graceful error handling that never disrupts workflow
- Audit trail of all autonomous decisions

## Advanced Topics

### Custom Framework Detection
See [ARCHITECTURE.md](ARCHITECTURE.md#extension-points) for adding new frameworks.

### External Integration
The system supports:
- Supabase sync for distributed caching
- Custom analytics exports
- API integration for remote management

### Performance Optimization
- SQLite with optimized indexes
- Lazy loading of components
- Background processing for non-critical operations
- Token budget management

## Troubleshooting

### Common Issues

1. **Learning Not Happening**: Check mode with `python3 enable_intelligent_mode.py check`
2. **Wrong Documentation**: Monitor `~/.claude/autonomous_updates.log` for learning
3. **Hook Not Activating**: Verify file extensions and operation size
4. **Performance Issues**: Check `~/.claude/hook_debug.log` for timing

### Debug Commands

```bash
# System health check
./context7_analyzer.py health

# Current learning mode
python3 enable_intelligent_mode.py check

# Recent autonomous updates
tail ~/.claude/autonomous_updates.log

# Hook activity
tail ~/.claude/hook_debug.log

# Rule backup history
ls ~/.claude/context7_rules_history/
```

## Contributing

When modifying the system:

1. **Test First**: Always run `python3 test_intelligent_system.py`
2. **Document Changes**: Update relevant documentation
3. **Preserve Safety**: Never modify the JSON-only rule update policy
4. **Monitor Impact**: Watch logs during and after changes

## Migration

For existing users, see [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md) for step-by-step instructions to migrate from legacy to intelligent learning mode.

The intelligent learning system represents a fundamental advancement in autonomous documentation caching, providing immediate improvements and contextual understanding of user needs.