# Context7 Scripts

This directory contains utility scripts for managing the Context7 caching system.

## Scripts

### cache_utils.py
Command-line utility for managing the Context7 cache database.

**Usage:**
```bash
# Cache documentation
python3 cache_utils.py cache "framework:component" "framework" --content "documentation content"

# List cached items
python3 cache_utils.py list

# Show cache statistics
python3 cache_utils.py stats

# Clear cache (all or by framework)
python3 cache_utils.py clear [--framework FRAMEWORK]
```

### sync_to_supabase.py
Synchronizes the local SQLite cache database to Supabase for remote viewing and analytics.

**Setup:**
1. Set environment variables:
   ```bash
   export SUPABASE_URL="your-supabase-url"
   export SUPABASE_KEY="your-supabase-anon-key"
   ```

2. Run sync:
   ```bash
   # One-time sync
   python3 sync_to_supabase.py sync
   
   # Continuous monitoring (syncs every 30 seconds)
   python3 sync_to_supabase.py monitor
   
   # Full sync (overwrites all data)
   python3 sync_to_supabase.py sync --full
   ```

### supabase_schema.sql
SQL schema for creating the required tables in Supabase. Run this in your Supabase SQL editor before using sync_to_supabase.py.

## Database Location
The SQLite database is stored at: `~/.claude/context7_cache.db`

## Integration with Hooks
The Context7 hook (`../context7_cache_hook.py`) uses these scripts and will instruct you to use cache_utils.py when documentation needs to be cached.