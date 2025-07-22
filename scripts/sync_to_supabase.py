#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "supabase",
#     "python-dotenv",
# ]
# ///
"""
Sync SQLite Context7 Cache to Supabase
Supports both one-time sync and continuous monitoring
"""

import os
import sys
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import argparse

# Add project to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load .env file if it exists
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # python-dotenv not installed, skip
    pass

try:
    from supabase import create_client, Client
except ImportError:
    print("❌ Supabase client not installed. Run: pip install supabase")
    sys.exit(1)

class SupabaseSync:
    """Sync SQLite database to Supabase"""
    
    def __init__(self, supabase_url: str, supabase_key: str):
        """Initialize with Supabase credentials"""
        self.supabase: Client = create_client(supabase_url, supabase_key)
        self.sqlite_path = Path.home() / '.claude' / 'context7_cache.db'
        
        if not self.sqlite_path.exists():
            raise FileNotFoundError(f"SQLite database not found at {self.sqlite_path}")
    
    def get_sqlite_connection(self):
        """Get SQLite connection with row factory"""
        conn = sqlite3.connect(self.sqlite_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def sync_context_cache(self, full_sync: bool = False) -> Dict[str, int]:
        """Sync context_cache table"""
        conn = self.get_sqlite_connection()
        stats = {'inserted': 0, 'updated': 0, 'errors': 0}
        
        try:
            # Get all records from SQLite
            cursor = conn.execute("SELECT * FROM context_cache")
            records = cursor.fetchall()
            
            for record in records:
                try:
                    # Convert record to dict
                    data = {
                        'cache_key': record['cache_key'],
                        'framework': record['framework'],
                        'component': record['component'],
                        'full_content': record['full_content'],
                        'sections': json.loads(record['sections']),
                        'created_at': record['created_at'],
                        'last_accessed': record['last_accessed'],
                        'access_count': record['access_count'],
                        'total_tokens': record['total_tokens'],
                        'expires_at': record['expires_at']
                    }
                    
                    # Try to upsert (insert or update)
                    response = self.supabase.table('context_cache').upsert(
                        data, 
                        on_conflict='cache_key'
                    ).execute()
                    
                    stats['updated'] += 1
                    
                except Exception as e:
                    print(f"❌ Error syncing cache key {record['cache_key']}: {e}")
                    stats['errors'] += 1
            
        finally:
            conn.close()
        
        return stats
    
    def sync_usage_logs(self, since_timestamp: Optional[str] = None) -> Dict[str, int]:
        """Sync usage_logs table"""
        conn = self.get_sqlite_connection()
        stats = {'inserted': 0, 'errors': 0}
        
        try:
            # Build query
            query = "SELECT * FROM usage_logs"
            params = []
            
            if since_timestamp:
                query += " WHERE timestamp > ?"
                params.append(since_timestamp)
            
            query += " ORDER BY timestamp ASC"
            
            cursor = conn.execute(query, params)
            records = cursor.fetchall()
            
            for record in records:
                try:
                    # Convert record to dict
                    data = {
                        'log_id': record['log_id'],
                        'session_id': record['session_id'],
                        'cache_key': record['cache_key'],
                        'operation_type': record['operation_type'],
                        'sections_provided': json.loads(record['sections_provided']),
                        'tokens_used': record['tokens_used'],
                        'tool_name': record['tool_name'],
                        'file_path': record['file_path'],
                        'timestamp': record['timestamp'],
                        'was_successful': record['was_successful'],
                        'user_feedback': record['user_feedback']
                    }
                    
                    # Insert (don't update existing logs)
                    response = self.supabase.table('usage_logs').insert(data).execute()
                    stats['inserted'] += 1
                    
                except Exception as e:
                    # Check if it's a duplicate key error
                    if 'duplicate key' in str(e).lower():
                        # Skip duplicates silently
                        pass
                    else:
                        print(f"❌ Error syncing log {record['log_id']}: {e}")
                        stats['errors'] += 1
            
        finally:
            conn.close()
        
        return stats
    
    def sync_extraction_rules(self) -> Dict[str, int]:
        """Sync extraction_rules table"""
        conn = self.get_sqlite_connection()
        stats = {'synced': 0, 'errors': 0}
        
        try:
            cursor = conn.execute("SELECT * FROM extraction_rules")
            records = cursor.fetchall()
            
            for record in records:
                try:
                    data = {
                        'rule_id': record['rule_id'],
                        'framework': record['framework'],
                        'operation_type': record['operation_type'],
                        'sections': json.loads(record['sections']),
                        'max_tokens': record['max_tokens'],
                        'confidence_score': record['confidence_score'],
                        'is_default': bool(record['is_default']),
                        'usage_count': record['usage_count'],
                        'success_count': record['success_count']
                    }
                    
                    # Upsert rules
                    response = self.supabase.table('extraction_rules').upsert(
                        data,
                        on_conflict='framework,operation_type'
                    ).execute()
                    
                    stats['synced'] += 1
                    
                except Exception as e:
                    print(f"❌ Error syncing rule {record['rule_id']}: {e}")
                    stats['errors'] += 1
            
        finally:
            conn.close()
        
        return stats
    
    def sync_session_logs(self, since_timestamp: Optional[str] = None) -> Dict[str, int]:
        """Sync session_logs table"""
        conn = self.get_sqlite_connection()
        stats = {'inserted': 0, 'errors': 0}
        
        try:
            # Build query
            query = "SELECT * FROM session_logs"
            params = []
            
            if since_timestamp:
                query += " WHERE timestamp > ?"
                params.append(since_timestamp)
            
            query += " ORDER BY timestamp ASC"
            
            cursor = conn.execute(query, params)
            records = cursor.fetchall()
            
            for record in records:
                try:
                    # Convert record to dict
                    data = {
                        'log_id': record['log_id'],
                        'session_id': record['session_id'],
                        'cache_key': record['cache_key'],
                        'operation_type': record['operation_type'],
                        'sections_provided': json.loads(record['sections_provided']),
                        'tokens_used': record['tokens_used'],
                        'tool_name': record['tool_name'],
                        'tool_input': json.loads(record['tool_input']),
                        'file_path': record['file_path'],
                        'timestamp': record['timestamp'],
                        'session_complete': record['session_complete'],
                        'follow_up_actions': json.loads(record['follow_up_actions']) if record['follow_up_actions'] else None,
                        'effectiveness_score': record['effectiveness_score'],
                        'effectiveness_reason': record['effectiveness_reason'],
                        'confidence_score': record['confidence_score'],
                        'analyzed_at': record['analyzed_at']
                    }
                    
                    # Insert (don't update existing logs)
                    response = self.supabase.table('session_logs').insert(data).execute()
                    stats['inserted'] += 1
                    
                except Exception as e:
                    # Check if it's a duplicate key error
                    if 'duplicate key' in str(e).lower():
                        # Skip duplicates silently
                        pass
                    else:
                        print(f"❌ Error syncing session log {record['log_id']}: {e}")
                        stats['errors'] += 1
            
        finally:
            conn.close()
        
        return stats
    
    def get_last_sync_timestamp(self) -> Optional[str]:
        """Get the timestamp of the last synced log (from either usage_logs or session_logs)"""
        last_usage_log = None
        last_session_log = None
        
        try:
            # Get last usage log timestamp
            response = self.supabase.table('usage_logs')\
                .select('timestamp')\
                .order('timestamp', desc=True)\
                .limit(1)\
                .execute()
            
            if response.data:
                last_usage_log = response.data[0]['timestamp']
            
        except Exception:
            pass
        
        try:
            # Get last session log timestamp
            response = self.supabase.table('session_logs')\
                .select('timestamp')\
                .order('timestamp', desc=True)\
                .limit(1)\
                .execute()
            
            if response.data:
                last_session_log = response.data[0]['timestamp']
            
        except Exception:
            pass
        
        # Return the most recent timestamp
        if last_usage_log and last_session_log:
            return max(last_usage_log, last_session_log)
        elif last_usage_log:
            return last_usage_log
        elif last_session_log:
            return last_session_log
        
        return None
    
    def full_sync(self):
        """Perform a full sync of all tables"""
        print("🔄 Starting full sync to Supabase...")
        
        # Sync context cache
        print("\n📦 Syncing context cache...")
        cache_stats = self.sync_context_cache(full_sync=True)
        print(f"  ✓ Updated: {cache_stats['updated']}, Errors: {cache_stats['errors']}")
        
        # Sync extraction rules
        print("\n📋 Syncing extraction rules...")
        rules_stats = self.sync_extraction_rules()
        print(f"  ✓ Synced: {rules_stats['synced']}, Errors: {rules_stats['errors']}")
        
        # Sync usage logs
        print("\n📊 Syncing usage logs...")
        logs_stats = self.sync_usage_logs()
        print(f"  ✓ Inserted: {logs_stats['inserted']}, Errors: {logs_stats['errors']}")
        
        # Sync session logs
        print("\n📈 Syncing session logs...")
        session_stats = self.sync_session_logs()
        print(f"  ✓ Inserted: {session_stats['inserted']}, Errors: {session_stats['errors']}")
        
        print("\n✅ Full sync completed!")
    
    def incremental_sync(self):
        """Perform incremental sync (new usage logs only)"""
        print("🔄 Starting incremental sync...")
        
        # Get last sync timestamp
        last_sync = self.get_last_sync_timestamp()
        
        if last_sync:
            print(f"  📅 Last sync: {last_sync}")
        
        # Sync new usage logs
        logs_stats = self.sync_usage_logs(since_timestamp=last_sync)
        print(f"  ✓ New logs: {logs_stats['inserted']}, Errors: {logs_stats['errors']}")
        
        # Always sync cache and rules in case they changed
        cache_stats = self.sync_context_cache()
        print(f"  ✓ Cache updates: {cache_stats['updated']}")
        
        # Sync new session logs
        session_stats = self.sync_session_logs(since_timestamp=last_sync)
        print(f"  ✓ New session logs: {session_stats['inserted']}, Errors: {session_stats['errors']}")
        
        print("\n✅ Incremental sync completed!")

def main():
    parser = argparse.ArgumentParser(description='Sync Context7 Cache to Supabase')
    parser.add_argument('--url', help='Supabase URL (or set SUPABASE_URL env var)')
    parser.add_argument('--key', help='Supabase anon key (or set SUPABASE_KEY env var)')
    parser.add_argument('--full', action='store_true', help='Perform full sync')
    parser.add_argument('--watch', action='store_true', help='Watch for changes and sync continuously')
    parser.add_argument('--interval', type=int, default=300, help='Watch interval in seconds (default: 300)')
    
    args = parser.parse_args()
    
    # Get credentials
    supabase_url = args.url or os.getenv('SUPABASE_URL')
    supabase_key = args.key or os.getenv('SUPABASE_KEY')
    
    if not supabase_url or not supabase_key:
        print("❌ Supabase credentials required!")
        print("   Set SUPABASE_URL and SUPABASE_KEY environment variables")
        print("   or use --url and --key arguments")
        sys.exit(1)
    
    # Create sync instance
    try:
        sync = SupabaseSync(supabase_url, supabase_key)
    except Exception as e:
        print(f"❌ Failed to initialize: {e}")
        sys.exit(1)
    
    # Perform sync
    try:
        if args.watch:
            print(f"👀 Watching for changes (interval: {args.interval}s)...")
            print("   Press Ctrl+C to stop")
            
            import time
            while True:
                sync.incremental_sync()
                time.sleep(args.interval)
        
        elif args.full:
            sync.full_sync()
        else:
            sync.incremental_sync()
            
    except KeyboardInterrupt:
        print("\n👋 Sync stopped by user")
    except Exception as e:
        print(f"\n❌ Sync failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()