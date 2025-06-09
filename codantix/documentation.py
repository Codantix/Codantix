"""
Documentation parsing and generation for Codantix.

This module provides utilities for extracting project context from README files, traversing codebases, and representing code elements for documentation.
"""

import re
from pathlib import Path
from typing import Dict, List

from codantix.config import LANGUAGE_EXTENSION_MAP, CodeElement
from codantix.parsers import get_parser


class ReadmeParser:
    """
    Parser for README.md files to extract project context.
    """

    def __init__(self):
        """
        Initialize the README parser.
        """
        self.supported_extensions = {".md"}

    def parse(self, readme_path: Path) -> Dict[str, str]:
        """
        Parse a README.md file and extract project context.

        Args:
            readme_path (Path): Path to the README.md file.

        Returns:
            Dict[str, str]: Extracted context, including description, architecture, and purpose if found.
        """
        if (
            not readme_path.exists()
            or readme_path.suffix not in self.supported_extensions
        ):
            return {}

        content = readme_path.read_text()
        context = {}

        # Extract description (everything between title and first section)
        description_match = re.search(
            r"^# .*\n\n(.*?)(?=\n##|\Z)", content, re.DOTALL | re.MULTILINE
        )
        if description_match:
            context["description"] = description_match.group(1).strip()

        # Extract architecture
        arch_match = re.search(
            r"## Architecture\n\n(.*?)(?=\n##|\Z)", content, re.DOTALL
        )
        if arch_match:
            context["architecture"] = arch_match.group(1).strip()

        # Extract purpose
        purpose_match = re.search(r"## Purpose\n\n(.*?)(?=\n##|\Z)", content, re.DOTALL)
        if purpose_match:
            context["purpose"] = purpose_match.group(1).strip()

        return context


class CodebaseTraverser:
    """
    Traverses the codebase to find elements needing documentation.
    """

    def __init__(self, languages: List[str]):
        """
        Initialize the codebase traverser with config.
        Args:
            languages: List of languages to traverse.
        """
        assert all(
            lang.lower() in LANGUAGE_EXTENSION_MAP for lang in languages
        ), f"Invalid language: {languages}. Must be one of: {LANGUAGE_EXTENSION_MAP.keys()}"
        self.languages = languages
        self.supported_extensions = {
            ext
            for lang in languages
            for ext in LANGUAGE_EXTENSION_MAP.get(lang.lower(), set())
        }

    def traverse(self, path: Path) -> List[CodeElement]:
        """
        Traverse the codebase and find elements needing documentation.

        Args:
            path (Path): Path to the root directory to traverse.

        Returns:
            List[CodeElement]: List of code elements found in the codebase.
        """
        if not path.exists():
            return []

        elements = []
        for file_path in path.rglob("*"):
            if file_path.suffix in self.supported_extensions:
                elements.extend(self._process_file_with_parser(file_path))
        return elements

    def _process_file_with_parser(self, file_path: Path) -> List[CodeElement]:
        """
        Generic file processor using the appropriate parser for the file type.
        """
        try:
            with open(file_path, "r") as f:
                content = f.read()
                parser = get_parser(file_path)
                if parser:
                    elements = parser.parse_file(content, 1, len(content.splitlines()))
                    for e in elements:
                        e.file_path = file_path
                    return elements
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
            return []
        return []
