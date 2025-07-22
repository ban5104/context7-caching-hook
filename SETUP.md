# Context7 Setup Guide

Quick setup for the Context7 intelligent caching system.

## Current Status

✅ **Hook is active and working**  
✅ **Transcript-aware blocking implemented**  
✅ **Cache utilities consolidated**  
✅ **Analytics system ready**

## Database Location

All data is stored in: `~/.claude/context7_cache.db`

No setup required - database is created automatically on first use.

## Key Files

| File | Purpose |
|------|---------|
| `context7_cache_hook.py` | Main hook that intercepts operations |
| `scripts/cache_utils.py` | Manual cache management CLI |
| `context7_analyzer.py` | Analytics and learning system |
| `~/.claude/context7_rules.json` | Framework-specific extraction rules |

## Workflow

1. **First time**: Hook blocks operation, requests documentation fetch
2. **After caching**: Hook provides context automatically  
3. **Subsequent operations**: Transcript awareness prevents re-blocking

## Essential Commands

```bash
# View what's cached
python3 scripts/cache_utils.py list

# Check system status  
./context7_analyzer.py status

# View effectiveness analytics
./context7_analyzer.py report
```

## Rules Configuration

Create `~/.claude/context7_rules.json` to customize documentation extraction:

```json
{
  "react": {
    "component": {"sections": ["components", "hooks"], "max_tokens": 3000}
  },
  "fastapi": {
    "app": {"sections": ["getting-started", "tutorial"], "max_tokens": 2500}
  },
  "defaults": {"sections": ["overview", "example"], "max_tokens": 2000}
}
```

## Auto-Sync to Supabase

Optional: Automatically mirror cached documentation to Supabase for remote access:

1. **Create `.env` file** with Supabase credentials:
   ```bash
   cp .env.example .env
   # Edit .env with your SUPABASE_URL and SUPABASE_KEY
   ```

2. **Run schema** in Supabase SQL editor:
   ```sql
   -- Execute: scripts/supabase_cache_only_schema.sql
   ```

3. **Install dependencies**:
   ```bash
   pip install supabase python-dotenv
   ```

**That's it!** Every time documentation gets cached locally, it's automatically synced to Supabase.

## Troubleshooting

- **Hook not triggering**: Only activates for code files (.py, .js, .tsx, etc.)
- **Debug info**: Check `~/.claude/hook_debug.log`
- **System health**: Run `./context7_analyzer.py health`
- **Supabase sync**: Check that `.env` has correct credentials

The system is designed to work automatically with minimal configuration.