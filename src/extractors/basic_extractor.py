# ~/projects/cc-rag/src/extractors/basic_extractor.py
import re
import json
from typing import Dict, List, Tuple

class BasicSectionExtractor:
    """Extracts and selects relevant sections from documentation."""

    def extract_sections(self, content: str) -> Dict[str, str]:
        """Parses content into a dictionary of named sections."""
        sections = {}
        current_section = 'overview'
        current_content = []
        for line in content.split('\n'):
            match = re.match(r'^#+\s*(.+)$', line)
            if match:
                if current_content:
                    sections[current_section] = '\n'.join(current_content).strip()
                current_section = self._normalize_section_name(match.group(1))
                current_content = []
            else:
                current_content.append(line)
        if current_content:
            sections[current_section] = '\n'.join(current_content).strip()
        return sections

    def _normalize_section_name(self, name: str) -> str:
        """Converts header names to a consistent snake_case format."""
        return re.sub(r'\s+', '_', re.sub(r'[^\w\s]', '', name)).lower()

    def extract_relevant_sections(self, sections: Dict[str, str], rule: Dict, token_budget: int) -> Tuple[str, List[str]]:
        """Selects the most relevant sections that fit within the token budget, based on the provided rule."""
        target_sections = rule.get('sections', ['overview', 'example'])
        max_tokens = min(rule.get('max_tokens', 2000), token_budget)
        
        result_content, result_sections, current_tokens = [], [], 0
        
        for section_name in target_sections:
            if section_name in sections:
                section_content = sections[section_name]
                section_tokens = len(section_content.split())
                if current_tokens + section_tokens <= max_tokens:
                    result_content.append(f"## {section_name.replace('_', ' ').title()}\n{section_content}")
                    result_sections.append(section_name)
                    current_tokens += section_tokens
        
        return '\n\n'.join(result_content), result_sections