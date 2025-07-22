#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""
Utility functions for manual cache management
"""

import sys
import json
import argparse
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.db.database_manager import DatabaseManager
from src.extractors.basic_extractor import BasicSectionExtractor
from src.detectors.operation_detector import OperationDetector

def cache_document(cache_key: str, framework: str, content: str):
    """Manually cache a document"""
    try:
        db = DatabaseManager()
        extractor = BasicSectionExtractor()
        
        # Extract sections from content
        sections = extractor.extract_sections(content)
        
        if not sections:
            print(f"❌ Could not extract sections from content")
            return False
        
        # Store in cache
        db.store_context(cache_key, framework, content, sections)
        
        print(f"✅ Cached {framework} documentation with key: {cache_key}")
        print(f"📝 Extracted {len(sections)} sections: {', '.join(sections.keys())}")
        return True
        
    except Exception as e:
        print(f"❌ Error caching document: {str(e)}")
        return False

def list_cache():
    """List all cached documents"""
    try:
        db = DatabaseManager()
        
        with db.get_connection() as conn:
            rows = conn.execute('''
                SELECT cache_key, framework, component, access_count, 
                       last_accessed, expires_at
                FROM context_cache 
                ORDER BY last_accessed DESC
            ''').fetchall()
        
        if not rows:
            print("📭 No cached documents found")
            return
        
        print("📚 Cached Documents:")
        print("-" * 80)
        for row in rows:
            status = "🟢" if row['expires_at'] > str(datetime.now()) else "🔴"
            component = f" ({row['component']})" if row['component'] else ""
            print(f"{status} {row['cache_key']} - {row['framework']}{component}")
            print(f"   Accessed: {row['access_count']} times, Last: {row['last_accessed']}")
            print()
            
    except Exception as e:
        print(f"❌ Error listing cache: {str(e)}")

def show_stats():
    """Show cache statistics"""
    try:
        db = DatabaseManager()
        stats = db.get_cache_stats()
        
        print("📊 Cache Statistics:")
        print("=" * 50)
        
        # Cache stats
        if stats.get('cache'):
            print("\n🗄️ Cache by Framework:")
            for item in stats['cache']:
                print(f"  {item['framework']}: {item['framework_count']} entries")
        
        # Usage stats
        if stats.get('usage'):
            print("\n📈 Usage by Operation (last 7 days):")
            for item in stats['usage']:
                success_rate = (item['successful_requests'] / item['total_requests'] * 100) if item['total_requests'] > 0 else 0
                print(f"  {item['operation_type']}: {item['total_requests']} requests ({success_rate:.1f}% success)")
        
    except Exception as e:
        print(f"❌ Error getting stats: {str(e)}")

def clear_cache(framework: str = None):
    """Clear cache entries"""
    try:
        db = DatabaseManager()
        
        with db.get_connection() as conn:
            if framework:
                conn.execute('DELETE FROM context_cache WHERE framework = ?', (framework,))
                print(f"🗑️ Cleared {framework} cache entries")
            else:
                conn.execute('DELETE FROM context_cache')
                print("🗑️ Cleared all cache entries")
                
    except Exception as e:
        print(f"❌ Error clearing cache: {str(e)}")

def main():
    parser = argparse.ArgumentParser(description='Context7 Cache Utilities')
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Cache command
    cache_parser = subparsers.add_parser('cache', help='Cache a document')
    cache_parser.add_argument('cache_key', help='Cache key (e.g., react:Button)')
    cache_parser.add_argument('framework', help='Framework name')
    cache_parser.add_argument('--content', help='Content to cache (or read from stdin)')
    
    # List command
    subparsers.add_parser('list', help='List cached documents')
    
    # Stats command
    subparsers.add_parser('stats', help='Show cache statistics')
    
    # Clear command
    clear_parser = subparsers.add_parser('clear', help='Clear cache')
    clear_parser.add_argument('--framework', help='Framework to clear (all if not specified)')
    
    args = parser.parse_args()
    
    if args.command == 'cache':
        if args.content:
            content = args.content
        else:
            print("📋 Reading content from stdin... (Ctrl+D when done)")
            content = sys.stdin.read()
        
        cache_document(args.cache_key, args.framework, content)
        
    elif args.command == 'list':
        list_cache()
        
    elif args.command == 'stats':
        show_stats()
        
    elif args.command == 'clear':
        clear_cache(args.framework)
        
    else:
        parser.print_help()

if __name__ == '__main__':
    from datetime import datetime
    main()