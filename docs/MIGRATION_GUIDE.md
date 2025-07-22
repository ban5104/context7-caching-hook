# Migration Guide: Legacy to Intelligent Learning

## Overview

This guide helps you migrate from the traditional metric-based learning system to the new intelligent conversation-aware learning system.

## Quick Migration

### 1. Test the New System

Before switching, test the intelligent system:

```bash
# Run simulation test
python3 test_intelligent_system.py
```

This shows you how the intelligent system would handle a Redis/FastAPI documentation mismatch.

### 2. Check Current Mode

```bash
# See which mode is currently active
python3 enable_intelligent_mode.py check
```

### 3. Enable Intelligent Mode

```bash
# Switch to intelligent learning
python3 enable_intelligent_mode.py enable
```

### 4. Monitor Learning

```bash
# Watch real-time autonomous updates
tail -f ~/.claude/autonomous_updates.log
```

### 5. Fallback Option

If needed, you can always switch back:

```bash
# Return to legacy mode
python3 enable_intelligent_mode.py disable
```

## Detailed Comparison

### What Changes

| Aspect | Legacy Mode | Intelligent Mode |
|--------|-------------|------------------|
| **Learning Trigger** | After 73+ sessions | Immediately on first mismatch |
| **Decision Making** | Effectiveness scores (0.4, 0.6, etc.) | Conversation analysis |
| **Update Speed** | Days/weeks | Real-time |
| **Context Understanding** | Token counts and error patterns | User intent and LLM feedback |
| **Threshold Requirements** | Multiple statistical thresholds | No thresholds |
| **Batch Processing** | Yes (batch analysis) | No (immediate) |

### What Stays the Same

| Component | Status | Notes |
|-----------|--------|-------|
| **PreToolUse Hook** | ✅ Unchanged | Still blocks and provides context |
| **Cache Storage** | ✅ Compatible | Same SQLite database |
| **Rule Format** | ✅ Compatible | JSON structure preserved |
| **Safety** | ✅ Enhanced | Still only modifies JSON config |
| **Framework Detection** | ✅ Unchanged | Same detection patterns |
| **Cache Management** | ✅ Unchanged | Same cache utilities |

## Step-by-Step Migration

### Phase 1: Preparation

1. **Backup Current Rules**:
   ```bash
   cp ~/.claude/context7_rules.json ~/.claude/context7_rules_backup.json
   ```

2. **Check System Health**:
   ```bash
   ./context7_analyzer.py health
   ```

3. **Review Current Performance**:
   ```bash
   ./context7_analyzer.py report
   ```

### Phase 2: Testing

1. **Run Intelligent System Test**:
   ```bash
   python3 test_intelligent_system.py
   ```
   
   Expected output:
   ```
   ✅ Rule updated successfully!
   📋 New Rule:
   {
     "sections": ["redis_client", "setup", "configuration", "example"],
     "max_tokens": 1500,
     "_autonomous_update": {
       "reasoning": "Cache provided web framework docs for Redis client setup"
     }
   }
   ```

2. **Verify Test Rule Creation**:
   ```bash
   jq '.fastapi.redis_setup' ~/.claude/context7_rules.json
   ```

### Phase 3: Activation

1. **Enable Intelligent Mode**:
   ```bash
   python3 enable_intelligent_mode.py enable
   ```

2. **Verify Hook Configuration**:
   ```bash
   python3 enable_intelligent_mode.py check
   ```
   
   Should show: "✅ Intelligent Mode is ACTIVE"

### Phase 4: Monitoring

1. **Watch Learning in Real-time**:
   ```bash
   tail -f ~/.claude/autonomous_updates.log
   ```

2. **Monitor Hook Activity**:
   ```bash
   tail -f ~/.claude/hook_debug.log
   ```

3. **Check for Errors**:
   ```bash
   tail -f ~/.claude/hook_errors.log
   ```

## Configuration Changes

### Hook Configuration Update

**Before (Legacy)**:
```json
{
  "hooks": {
    "PostToolUse": [
      {
        "command": "/path/to/session_tracker.py"
      }
    ]
  }
}
```

**After (Intelligent)**:
```json
{
  "hooks": {
    "PostToolUse": [
      {
        "command": "/path/to/intelligent_posttooluse_hook.py"
      }
    ]
  }
}
```

### Rule Format Evolution

**Legacy Rule**:
```json
{
  "fastapi": {
    "create": {
      "sections": ["overview", "example", "api"],
      "max_tokens": 2000,
      "_learning_metadata": {
        "confidence": 0.4,
        "based_on_sessions": 73
      }
    }
  }
}
```

**Intelligent Rule**:
```json
{
  "fastapi": {
    "redis_setup": {
      "sections": ["redis_client", "setup", "configuration"],
      "max_tokens": 1500,
      "_autonomous_update": {
        "updated_at": "2025-07-23T10:49:59.740967",
        "reasoning": "Cache provided web framework docs for Redis client setup",
        "confidence": 0.8,
        "was_effective": false
      }
    }
  }
}
```

## Expected Behavior Changes

### Learning Speed

**Legacy**: 
```
Session 1: Wrong docs → Score 0.4
Session 2: Wrong docs → Score 0.4
...
Session 73: Wrong docs → Score 0.4
Session 74: Finally enough data → Maybe update rule
```

**Intelligent**:
```
Session 1: Wrong docs → LLM says "this is wrong" → Update rule immediately
Session 2: Correct docs provided
```

### Decision Making

**Legacy**:
- Based on token counts, error rates, completion statistics
- Requires statistical significance
- Waits for patterns across many sessions

**Intelligent**:
- Based on conversation understanding
- Recognizes explicit LLM feedback
- Acts on clear mismatches immediately

## Troubleshooting Migration

### Common Issues

#### 1. Mode Switch Not Working

**Problem**: `enable_intelligent_mode.py check` shows old mode

**Solution**:
```bash
# Check if hook config file exists
ls ~/.claude/hooks.json

# Manually verify the hook command
cat ~/.claude/hooks.json | jq '.hooks.PostToolUse'
```

#### 2. No Learning Happening

**Problem**: No entries in `autonomous_updates.log`

**Debug Steps**:
```bash
# Check if hook is being called
tail -f ~/.claude/hook_debug.log

# Verify intelligent hook is executable
python3 intelligent_posttooluse_hook.py

# Check for errors
cat ~/.claude/hook_errors.log
```

#### 3. Wrong Rule Updates

**Problem**: Rules being updated incorrectly

**Solution**:
- Rules include reasoning - check `_autonomous_update.reasoning`
- Backup files available: `~/.claude/context7_rules_history/`
- Can disable and re-enable mode
- Confidence scores indicate quality

#### 4. Session Tracking Issues

**Problem**: Sessions not being tracked

**Debug**:
```bash
# Check recent sessions
sqlite3 ~/.claude/context7_cache.db "SELECT * FROM session_logs ORDER BY timestamp DESC LIMIT 5"

# Verify session ID extraction
grep "Session:" ~/.claude/hook_debug.log
```

### Rollback Procedure

If you need to revert to legacy mode:

1. **Disable Intelligent Mode**:
   ```bash
   python3 enable_intelligent_mode.py disable
   ```

2. **Restore Backup Rules** (if needed):
   ```bash
   cp ~/.claude/context7_rules_backup.json ~/.claude/context7_rules.json
   ```

3. **Verify Legacy Mode**:
   ```bash
   python3 enable_intelligent_mode.py check
   ```

4. **Clean Up Test Data**:
   ```bash
   # Remove test rules created during migration
   jq 'del(.fastapi.redis_setup)' ~/.claude/context7_rules.json > temp.json
   mv temp.json ~/.claude/context7_rules.json
   ```

## Performance Considerations

### Resource Usage

**Legacy Mode**:
- Periodic batch processing
- SQLite queries for analytics
- Statistical calculations

**Intelligent Mode**:
- Real-time analysis
- Conversation parsing
- Immediate file I/O for rule updates

### Impact on Workflow

**Legacy Mode**:
- No immediate impact
- Learning happens in background
- Improvements appear over time

**Intelligent Mode**:
- Immediate improvements
- Slightly more activity during operation
- Better responsiveness to user needs

## Validation

### Post-Migration Checks

1. **Verify Mode**:
   ```bash
   python3 enable_intelligent_mode.py check
   # Should show: "✅ Intelligent Mode is ACTIVE"
   ```

2. **Test Learning**:
   ```bash
   python3 test_intelligent_system.py
   # Should show autonomous rule creation
   ```

3. **Monitor Operations**:
   ```bash
   # Use Context7 normally and watch for learning
   tail -f ~/.claude/autonomous_updates.log
   ```

4. **Check Rule Quality**:
   ```bash
   # Look for _autonomous_update metadata in rules
   jq '[.[] | to_entries[] | select(.value._autonomous_update)] | length' ~/.claude/context7_rules.json
   ```

The migration to intelligent learning represents a fundamental improvement in how the system learns and adapts to user needs, providing immediate benefits and more accurate documentation caching.