"""
Documentation parsing and generation for Codantix.
"""
import re
from pathlib import Path
from typing import Dict, List, Optional, Set
import ast
from dataclasses import dataclass
from enum import Enum

class ElementType(Enum):
    """Types of code elements that need documentation."""
    MODULE = "module"
    CLASS = "class"
    FUNCTION = "function"
    METHOD = "method"

@dataclass
class CodeElement:
    """Represents a code element that needs documentation."""
    name: str
    type: ElementType
    file_path: Path
    line_number: int
    docstring: Optional[str] = None
    existing_doc: Optional[str] = None
    parent: Optional[str] = None

class ReadmeParser:
    """Parser for README.md files to extract project context."""

    def __init__(self):
        """Initialize the README parser."""
        self.supported_extensions = {'.md'}

    def parse(self, readme_path: Path) -> Dict[str, str]:
        """Parse a README.md file and extract project context."""
        if not readme_path.exists() or readme_path.suffix not in self.supported_extensions:
            return {}

        content = readme_path.read_text()
        context = {}

        # Extract description (everything between title and first section)
        description_match = re.search(r'^# .*\n\n(.*?)(?=\n##|\Z)', content, re.DOTALL | re.MULTILINE)
        if description_match:
            context['description'] = description_match.group(1).strip()

        # Extract architecture
        arch_match = re.search(r'## Architecture\n\n(.*?)(?=\n##|\Z)', content, re.DOTALL)
        if arch_match:
            context['architecture'] = arch_match.group(1).strip()

        # Extract purpose
        purpose_match = re.search(r'## Purpose\n\n(.*?)(?=\n##|\Z)', content, re.DOTALL)
        if purpose_match:
            context['purpose'] = purpose_match.group(1).strip()

        return context

class CodebaseTraverser:
    """Traverses the codebase to find elements needing documentation."""

    def __init__(self):
        """Initialize the codebase traverser."""
        self.supported_extensions = {'.py'}

    def traverse(self, path: Path) -> List[CodeElement]:
        """Traverse the codebase and find elements needing documentation."""
        if not path.exists():
            return []

        elements = []
        for file_path in path.rglob('*'):
            if file_path.suffix in self.supported_extensions:
                elements.extend(self._process_file(file_path))
        return elements

    def _process_file(self, file_path: Path) -> List[CodeElement]:
        """Process a single file and extract code elements."""
        if file_path.suffix == '.py':
            return self._process_python_file(file_path)
        return []

    def _process_python_file(self, file_path: Path) -> List[CodeElement]:
        """Process a Python file and extract code elements."""
        elements = []
        try:
            with open(file_path, 'r') as f:
                content = f.read()
                tree = ast.parse(content)
                
                # Get module docstring
                module_doc = ast.get_docstring(tree)
                elements.append(CodeElement(
                    name=file_path.stem,
                    type=ElementType.MODULE,
                    file_path=file_path,
                    line_number=1,
                    existing_doc=module_doc
                ))

                # Process classes and their methods
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        class_doc = ast.get_docstring(node)
                        elements.append(CodeElement(
                            name=node.name,
                            type=ElementType.CLASS,
                            file_path=file_path,
                            line_number=node.lineno,
                            existing_doc=class_doc
                        ))
                        
                        # Process methods
                        for method in node.body:
                            if isinstance(method, ast.FunctionDef):
                                method_doc = ast.get_docstring(method)
                                elements.append(CodeElement(
                                    name=method.name,
                                    type=ElementType.METHOD,
                                    file_path=file_path,
                                    line_number=method.lineno,
                                    existing_doc=method_doc,
                                    parent=node.name
                                ))
                    
                    # Process standalone functions
                    elif isinstance(node, ast.FunctionDef):
                        func_doc = ast.get_docstring(node)
                        elements.append(CodeElement(
                            name=node.name,
                            type=ElementType.FUNCTION,
                            file_path=file_path,
                            line_number=node.lineno,
                            existing_doc=func_doc
                        ))

        except Exception as e:
            print(f"Error processing {file_path}: {e}")
            return []

        return elements 