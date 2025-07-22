#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""
Validates that cached content is properly stored and retrievable
"""

import sys
import json
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.db.database_manager import DatabaseManager

def validate_cache(cache_key: str) -> bool:
    """Validates that a cache entry exists and has content"""
    try:
        db = DatabaseManager()
        cached_data = db.get_cache_data(cache_key)
        
        if not cached_data:
            print(f"❌ No cache entry found for key: {cache_key}")
            return False
        
        # Check for required fields
        if not cached_data.get('full_content'):
            print(f"❌ Cache entry has no content for key: {cache_key}")
            return False
            
        sections = json.loads(cached_data.get('sections', '{}'))
        if not sections:
            print(f"⚠️  Cache entry has no sections for key: {cache_key}")
        
        # Display cache info
        content_preview = cached_data['full_content'][:200] + "..." if len(cached_data['full_content']) > 200 else cached_data['full_content']
        print(f"✅ Cache validated for key: {cache_key}")
        print(f"📝 Framework: {cached_data.get('framework', 'unknown')}")
        print(f"📚 Sections: {', '.join(sections.keys()) if sections else 'none'}")
        print(f"📄 Content preview: {content_preview}")
        print(f"🔢 Total tokens: {cached_data.get('total_tokens', 0)}")
        return True
        
    except Exception as e:
        print(f"❌ Error validating cache: {str(e)}")
        return False

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Validate cache entry')
    parser.add_argument('cache_key', help='Cache key to validate')
    args = parser.parse_args()
    
    success = validate_cache(args.cache_key)
    sys.exit(0 if success else 1)