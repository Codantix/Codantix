"""
Language-specific code parsers for Codantix.
"""
from pathlib import Path
from typing import List, Optional, Dict
import ast
import re
from .documentation import CodeElement, ElementType

class BaseParser:
    """Base class for language-specific parsers."""
    
    def __init__(self):
        """Initialize the parser."""
        self.supported_extensions: List[str] = []

    def parse_file(self, content: str, start_line: int, end_line: int) -> List[CodeElement]:
        """Parse file content and extract code elements."""
        raise NotImplementedError

    def extract_docstring(self, content: str, element_type: ElementType) -> Optional[str]:
        """Extract docstring from code element."""
        raise NotImplementedError

class PythonParser(BaseParser):
    """Parser for Python code."""

    def __init__(self):
        """Initialize Python parser."""
        super().__init__()
        self.supported_extensions = ['.py']

    def parse_file(self, content: str, start_line: int, end_line: int) -> List[CodeElement]:
        """Parse Python file content and extract code elements."""
        elements = []
        try:
            tree = ast.parse(content)
            
            # Handle module docstring
            if tree.body and isinstance(tree.body[0], ast.Expr) and isinstance(tree.body[0].value, ast.Str):
                elements.append(CodeElement(
                    name="module",
                    type=ElementType.MODULE,
                    file_path=Path(""),  # Will be set by caller
                    line_number=1,
                    docstring=tree.body[0].value.s
                ))

            # Handle other elements
            for node in ast.walk(tree):
                if not hasattr(node, 'lineno') or not (start_line <= node.lineno <= end_line):
                    continue

                if isinstance(node, ast.FunctionDef):
                    elements.append(CodeElement(
                        name=node.name,
                        type=ElementType.FUNCTION,
                        file_path=Path(""),  # Will be set by caller
                        line_number=node.lineno,
                        docstring=self._get_docstring(node)
                    ))
                elif isinstance(node, ast.ClassDef):
                    elements.append(CodeElement(
                        name=node.name,
                        type=ElementType.CLASS,
                        file_path=Path(""),  # Will be set by caller
                        line_number=node.lineno,
                        docstring=self._get_docstring(node)
                    ))

        except SyntaxError:
            # Handle syntax errors gracefully
            pass

        return elements

    def _get_docstring(self, node: ast.AST) -> Optional[str]:
        """Extract docstring from an AST node."""
        if not isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            return None

        if not node.body:
            return None

        first_node = node.body[0]
        if isinstance(first_node, ast.Expr) and isinstance(first_node.value, ast.Str):
            return first_node.value.s

        return None

class JavaScriptParser(BaseParser):
    """Parser for JavaScript code."""

    def __init__(self):
        """Initialize JavaScript parser."""
        super().__init__()
        self.supported_extensions = ['.js', '.jsx', '.ts', '.tsx']

    def parse_file(self, content: str, start_line: int, end_line: int) -> List[CodeElement]:
        """Parse JavaScript file content and extract code elements."""
        elements = []
        lines = content.split('\n')
        
        # Simple regex-based parsing for now
        # TODO: Use proper JavaScript parser (e.g., esprima)
        function_pattern = r'^(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\('
        class_pattern = r'^(?:export\s+)?class\s+(\w+)'
        method_pattern = r'^\s*(?:async\s+)?(\w+)\s*\([^)]*\)\s*{'
        
        for i, line in enumerate(lines, 1):
            if not (start_line <= i <= end_line):
                continue

            # Check for functions
            if match := re.match(function_pattern, line):
                docstring = self._extract_jsdoc(lines, i)
                elements.append(CodeElement(
                    name=match.group(1),
                    type=ElementType.FUNCTION,
                    file_path=Path(""),  # Will be set by caller
                    line_number=i,
                    docstring=docstring
                ))
            
            # Check for classes
            elif match := re.match(class_pattern, line):
                docstring = self._extract_jsdoc(lines, i)
                elements.append(CodeElement(
                    name=match.group(1),
                    type=ElementType.CLASS,
                    file_path=Path(""),  # Will be set by caller
                    line_number=i,
                    docstring=docstring
                ))
            
            # Check for methods (inside classes)
            elif match := re.match(method_pattern, line):
                docstring = self._extract_jsdoc(lines, i)
                elements.append(CodeElement(
                    name=match.group(1),
                    type=ElementType.METHOD,
                    file_path=Path(""),  # Will be set by caller
                    line_number=i,
                    docstring=docstring
                ))

        return elements

    def _extract_jsdoc(self, lines: List[str], line_num: int) -> Optional[str]:
        """Extract JSDoc comment from code."""
        if line_num <= 1:
            return None

        doc_lines = []
        current_line = line_num - 1
        found_start = False
        
        # Look for JSDoc comment above the code element
        while current_line >= 0:
            line = lines[current_line].strip()
            
            if line.startswith('*/'):
                found_start = True
                continue
                
            if found_start:
                if line.startswith('/**'):
                    doc_lines.insert(0, line[3:].strip())
                    break
                elif line.startswith('*'):
                    doc_lines.insert(0, line[1:].strip())
                elif not line:
                    break
            
            current_line -= 1

        return '\n'.join(doc_lines) if doc_lines else None

def get_parser(file_path: Path) -> Optional[BaseParser]:
    """Get appropriate parser for file type."""
    extension = file_path.suffix.lower()
    
    if extension in ['.py']:
        return PythonParser()
    elif extension in ['.js', '.jsx', '.ts', '.tsx']:
        return JavaScriptParser()
    
    return None 