# ~/projects/cc-rag/src/detectors/operation_detector.py
import re
from typing import Optional

class OperationDetector:
    """Detects framework, operation type, and component from code content."""

    def detect_framework(self, content: str, file_path: str = "") -> Optional[str]:
        """Detects the framework based on imports and file patterns."""
        content_lower = content.lower()
        
        # React/Next.js detection
        if any(pattern in content_lower for pattern in ['react', 'jsx', 'usestate', 'useeffect', 'next/']):
            return 'react'
        
        # Vue detection
        if any(pattern in content_lower for pattern in ['vue', '<template>', '<script setup>', 'composition api']):
            return 'vue'
        
        # Svelte detection
        if any(pattern in content_lower for pattern in ['svelte', '$:', 'on:click']):
            return 'svelte'
        
        # FastAPI detection (check before Express since FastAPI also uses app.get/post)
        if any(pattern in content_lower for pattern in ['fastapi', '@app.get', '@app.post', 'from fastapi', 'async def', 'pydantic']):
            return 'fastapi'
        
        # Express.js detection
        if any(pattern in content_lower for pattern in ['express', 'req.', 'res.', 'router.get', 'router.post']):
            return 'express'
        
        # Django detection
        if any(pattern in content_lower for pattern in ['django', 'models.model', 'def __str__', 'admin.site']):
            return 'django'
        
        # Tailwind CSS detection
        if any(pattern in content_lower for pattern in ['tailwind', 'tw-', '@apply', '@layer']):
            return 'tailwindcss'
        
        # Supabase detection
        if any(pattern in content_lower for pattern in ['supabase', 'createclient', '.from(', '.select()']):
            return 'supabase'
        
        # shadcn/ui detection
        if any(pattern in content_lower for pattern in [
            'shadcn', '@/components/ui/', 'lucide-react', 'class-variance-authority',
            'cn(', 'cva(', '@radix-ui/', 'cmdk'
        ]) or any(component in content for component in [
            'Button', 'Card', 'Input', 'Label', 'Dialog', 'Sheet', 'Popover',
            'Select', 'Checkbox', 'RadioGroup', 'Textarea', 'Badge', 'Avatar',
            'Accordion', 'AlertDialog', 'AspectRatio', 'Calendar', 'Collapsible',
            'ContextMenu', 'DropdownMenu', 'HoverCard', 'MenuBar', 'NavigationMenu',
            'Progress', 'ScrollArea', 'Separator', 'Slider', 'Switch', 'Table',
            'Tabs', 'Toast', 'Toggle', 'Tooltip'
        ]):
            return 'shadcn'
        
        # File extension fallbacks
        if file_path:
            if file_path.endswith(('.jsx', '.tsx')):
                return 'react'
            elif file_path.endswith('.ts'):
                # Check content patterns already defined for frameworks
                # Would catch utility files, config files, type definition files
                return None  # Falls back to content-based detection
            elif file_path.endswith('.vue'):
                return 'vue'
            elif file_path.endswith('.svelte'):
                return 'svelte'
            elif file_path.endswith('.py'):
                if 'def ' in content and ('app' in content_lower or 'router' in content_lower):
                    return 'fastapi'
                elif 'class ' in content and 'model' in content_lower:
                    return 'django'
        
        return None

    def detect_operation(self, content: str, file_path: str = "") -> str:
        """Detects the type of operation being performed."""
        content_lower = content.lower()
        
        # Component creation patterns
        if any(pattern in content_lower for pattern in [
            'function ', 'const ', 'export default', 'class component',
            'def ', 'async def'
        ]):
            return 'create'
        
        # Styling operations
        if any(pattern in content_lower for pattern in [
            'styled', 'css', 'class=', 'classname=', 'style=', 
            '@apply', 'flex', 'grid', 'bg-', 'text-'
        ]):
            return 'style'
        
        # API/Database operations
        if any(pattern in content_lower for pattern in [
            'fetch', 'axios', 'api', 'get(', 'post(', 'put(', 'delete(',
            'select', 'insert', 'update', 'where', 'join'
        ]):
            return 'api'
        
        # Authentication operations
        if any(pattern in content_lower for pattern in [
            'auth', 'login', 'signup', 'signin', 'logout', 'session',
            'token', 'jwt', 'password', 'user'
        ]):
            return 'auth'
        
        # Testing operations
        if any(pattern in content_lower for pattern in [
            'test', 'spec', 'describe', 'it(', 'expect', 'assert',
            'mock', 'jest', 'vitest'
        ]):
            return 'test'
        
        return 'general'

    def extract_component(self, content: str, file_path: str, framework: str) -> Optional[str]:
        """Extracts the component name being worked on."""
        
        # Extract from file path first
        if file_path:
            file_name = file_path.split('/')[-1].split('.')[0]
            if file_name and file_name not in ['index', 'main', 'app']:
                return file_name.lower()
        
        # React component extraction
        if framework == 'react':
            # Function components
            match = re.search(r'(?:function|const)\s+([A-Z][a-zA-Z0-9]+)', content)
            if match:
                return match.group(1).lower()
            
            # Export default patterns
            match = re.search(r'export\s+default\s+([A-Z][a-zA-Z0-9]+)', content)
            if match:
                return match.group(1).lower()
        
        # Vue component extraction
        elif framework == 'vue':
            match = re.search(r'name:\s*[\'"]([^"\']+)[\'"]', content)
            if match:
                return match.group(1).lower()
        
        # API endpoint extraction
        elif framework in ['fastapi', 'express']:
            match = re.search(r'[/@]([a-zA-Z0-9_-]+)', content)
            if match:
                return match.group(1).lower()
        
        # Django model extraction
        elif framework == 'django':
            match = re.search(r'class\s+([A-Z][a-zA-Z0-9]+)\s*\(', content)
            if match:
                return match.group(1).lower()
        
        return None