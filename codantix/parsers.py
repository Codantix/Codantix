"""
Language-specific code parsers for Codantix.

This module provides parsers for Python and JavaScript/TypeScript code, extracting code elements and their docstrings for documentation generation.
"""
from pathlib import Path
from typing import List, Optional, Dict, Any
import ast
import esprima
from .documentation import CodeElement, ElementType
import logging

class BaseParser:
    """
    Base class for language-specific parsers.
    """
    
    def __init__(self):
        """
        Initialize the parser.
        """
        self.supported_extensions: List[str] = []

    def parse_file(self, content: str, start_line: int, end_line: int) -> List[CodeElement]:
        """
        Parse file content and extract code elements.

        Args:
            content (str): File content as a string.
            start_line (int): Start line number for parsing.
            end_line (int): End line number for parsing.

        Returns:
            List[CodeElement]: List of code elements found in the file.
        """
        raise NotImplementedError

    def extract_docstring(self, content: str, element_type: ElementType) -> Optional[str]:
        """
        Extract docstring from code element.

        Args:
            content (str): Code element content as a string.
            element_type (ElementType): Type of code element.

        Returns:
            Optional[str]: Extracted docstring, if found.
        """
        raise NotImplementedError

class PythonParser(BaseParser):
    """
    Parser for Python code.
    """

    def __init__(self):
        """
        Initialize Python parser.
        """
        super().__init__()
        self.supported_extensions = ['.py']

    def parse_file(self, content: str, start_line: int, end_line: int) -> List[CodeElement]:
        """
        Parse Python file content and extract code elements.

        Args:
            content (str): File content as a string.
            start_line (int): Start line number for parsing.
            end_line (int): End line number for parsing.

        Returns:
            List[CodeElement]: List of code elements found in the file.
        """
        elements = []
        try:
            tree = ast.parse(content)
            
            # Handle module docstring
            if tree.body and isinstance(tree.body[0], ast.Expr) and isinstance(tree.body[0].value, ast.Constant):
                elements.append(CodeElement(
                    name="module",
                    type=ElementType.MODULE,
                    file_path=Path(""),  # Will be set by caller
                    line_number=1,
                    docstring=tree.body[0].value.value
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
            logging.warning("Syntax error encountered while parsing Python file. Returning empty element list.")
            pass

        return elements

    def _get_docstring(self, node: ast.AST) -> Optional[str]:
        """
        Extract docstring from an AST node.

        Args:
            node (ast.AST): AST node representing a function or class.

        Returns:
            Optional[str]: Extracted docstring, if found.
        """
        if not isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            return None

        if not node.body:
            return None

        first_node = node.body[0]
        if isinstance(first_node, ast.Expr) and isinstance(first_node.value, ast.Constant):
            return first_node.value.value

        return None

class JavaScriptParser(BaseParser):
    """
    Parser for JavaScript and TypeScript code.
    """

    def __init__(self):
        """
        Initialize JavaScript parser.
        """
        super().__init__()
        self.supported_extensions = ['.js', '.jsx', '.ts', '.tsx']

    def _get_jsdoc(self, node: Any, block_comments_by_end_line: dict = None, source_lines: list = None) -> Optional[str]:
        """
        Extract JSDoc-style docstring from a JavaScript AST node.

        Args:
            node (Any): JavaScript AST node.
            block_comments_by_end_line (dict, optional): Mapping of end lines to block comments.
            source_lines (list, optional): Source lines of the file.

        Returns:
            Optional[str]: Extracted JSDoc docstring, if found.
        """
        # Try leadingComments first
        if leading_comments := getattr(node, 'leadingComments', None):
            for comment_obj in reversed(leading_comments):
                if hasattr(comment_obj, 'type') and comment_obj.type == 'Block' and \
                   hasattr(comment_obj, 'value') and isinstance(comment_obj.value, str) and \
                   comment_obj.value.startswith('*'):
                    return self._clean_jsdoc(comment_obj.value)
        # Fallback: try block_comments_by_end_line if provided
        if block_comments_by_end_line is not None and source_lines is not None:
            node_start_line = getattr(getattr(getattr(node, 'loc', {}), 'start', {}), 'line', None)
            if node_start_line is not None:
                comment = block_comments_by_end_line.get(node_start_line - 1)
                if comment:
                    # Check that only whitespace/newlines between comment and node
                    comment_end = comment.loc.end.line
                    for l in range(comment_end, node_start_line - 1):
                        if l < len(source_lines):
                            if source_lines[l].strip() != '':
                                return None  # There is code between comment and node
                    return self._clean_jsdoc(comment.value)
        return None

    def _clean_jsdoc(self, value: str) -> Optional[str]:
        """
        Clean and normalize a JSDoc comment string.

        Args:
            value (str): Raw JSDoc comment string.

        Returns:
            Optional[str]: Cleaned docstring, if found.
        """
        if not isinstance(value, str) or not value:
            return None 
        lines = value.split('\n')
        cleaned_lines = []
        for line in lines:
            line = line.strip()
            if line.startswith('*'):
                line = line[1:].strip()
            if line:
                cleaned_lines.append(line)
        return '\n'.join(cleaned_lines) if cleaned_lines else None

    def _collect_elements_recursive(self, node: Any, visited_nodes: set, elements_list: List[CodeElement], file_path: Path, start_line_filter: int, end_line_filter: int, block_comments_by_end_line: dict = None, source_lines: list = None) -> List[CodeElement]:
        """
        Recursively collect code elements from a JavaScript AST node.

        Args:
            node (Any): JavaScript AST node.
            visited_nodes (set): Set of visited node IDs to avoid cycles.
            elements_list (List[CodeElement]): Accumulated list of code elements.
            file_path (Path): Path to the file being parsed.
            start_line_filter (int): Start line number for filtering.
            end_line_filter (int): End line number for filtering.
            block_comments_by_end_line (dict, optional): Mapping of end lines to block comments.
            source_lines (list, optional): Source lines of the file.

        Returns:
            List[CodeElement]: List of code elements found in the AST.
        """
        if node is None or id(node) in visited_nodes:
            return elements_list
        
        visited_nodes.add(id(node))

        node_type = getattr(node, 'type', None)
        current_node_line = getattr(getattr(getattr(node, 'loc', {}), 'start', {}), 'line')

        # Process current node if it's a recognized element type and within line range
        if node_type in ['FunctionDeclaration', 'ClassDeclaration', 'MethodDefinition']:
            if current_node_line and (start_line_filter <= current_node_line <= end_line_filter):
                docstring = self._get_jsdoc(node, block_comments_by_end_line, source_lines)
                node_name = None
                element_type_enum = None

                if node_type == 'FunctionDeclaration':
                    node_name = getattr(getattr(node, 'id', None), 'name', None)
                    element_type_enum = ElementType.FUNCTION
                elif node_type == 'ClassDeclaration':
                    node_name = getattr(getattr(node, 'id', None), 'name', None)
                    element_type_enum = ElementType.CLASS
                elif node_type == 'MethodDefinition':
                    node_name = getattr(getattr(node, 'key', None), 'name', None)
                    element_type_enum = ElementType.METHOD
                
                if node_name and element_type_enum:
                    elements_list.append(CodeElement(
                        name=node_name, type=element_type_enum, file_path=file_path,
                        line_number=current_node_line, docstring=docstring
                    ))
        
        # Recursively traverse children based on node type
        if node_type == 'Program':
            body_list = getattr(node, 'body', None)
            if isinstance(body_list, list):
                for child in body_list:
                    elements_list = self._collect_elements_recursive(child, visited_nodes, elements_list, file_path, start_line_filter, end_line_filter, block_comments_by_end_line, source_lines)
        
        elif node_type in ['ExportNamedDeclaration', 'ExportDefaultDeclaration']:
            declaration = getattr(node, 'declaration', None)
            if declaration:
                elements_list = self._collect_elements_recursive(declaration, visited_nodes, elements_list, file_path, start_line_filter, end_line_filter, block_comments_by_end_line, source_lines)
        
        elif node_type == 'ClassDeclaration':
            class_body_node = getattr(node, 'body', None) # This is the ClassBody node
            if class_body_node:
                elements_list = self._collect_elements_recursive(class_body_node, visited_nodes, elements_list, file_path, start_line_filter, end_line_filter, block_comments_by_end_line, source_lines)
        
        elif node_type == 'ClassBody': # Its body is a list of MethodDefinitions
            method_definitions_list = getattr(node, 'body', None)
            if isinstance(method_definitions_list, list):
                for method_def in method_definitions_list:
                    elements_list = self._collect_elements_recursive(method_def, visited_nodes, elements_list, file_path, start_line_filter, end_line_filter, block_comments_by_end_line, source_lines)
        
        elif node_type in ['FunctionDeclaration', 'FunctionExpression']:
            # The body of a function is a BlockStatement
            block_statement_node = getattr(node, 'body', None)
            if block_statement_node: 
                 # We don't typically find new top-level elements inside a function's block statement for now
                 # self._collect_elements_recursive(block_statement_node, visited_nodes, elements_list, file_path, start_line_filter, end_line_filter, block_comments_by_end_line, source_lines)
                 pass 
        
        elif node_type == 'MethodDefinition': # Its value is a FunctionExpression
            func_expr_node = getattr(node, 'value', None)
            if func_expr_node:
                elements_list = self._collect_elements_recursive(func_expr_node, visited_nodes, elements_list, file_path, start_line_filter, end_line_filter, block_comments_by_end_line, source_lines)

        elif node_type == 'VariableDeclaration':
            declarations_list = getattr(node, 'declarations', None)
            if isinstance(declarations_list, list):
                for declarator in declarations_list:
                    if getattr(declarator, 'type', None) == 'VariableDeclarator':
                        init_node = getattr(declarator, 'init', None)
                        if init_node: # Could be FunctionExpression, ClassExpression, etc.
                            elements_list = self._collect_elements_recursive(init_node, visited_nodes, elements_list, file_path, start_line_filter, end_line_filter, block_comments_by_end_line, source_lines)
        
        # Fallback for BlockStatement if we decide to parse inner elements
        elif node_type == 'BlockStatement':
            body_list = getattr(node, 'body', None)
            if isinstance(body_list, list):
                for stmt in body_list:
                    elements_list = self._collect_elements_recursive(stmt, visited_nodes, elements_list, file_path, start_line_filter, end_line_filter, block_comments_by_end_line, source_lines)

        return elements_list

    def parse_file(self, content: str, start_line: int, end_line: int) -> List[CodeElement]:
        """
        Parse JavaScript/TypeScript file content and extract code elements.

        Args:
            content (str): File content as a string.
            start_line (int): Start line number for parsing.
            end_line (int): End line number for parsing.

        Returns:
            List[CodeElement]: List of code elements found in the file.
        """
        elements: List[CodeElement] = []
        try:
            tree = esprima.parseScript(content, {
                'loc': True, 'comment': True, 'range': True, 
                'tokens': True, 'tolerant': True, 'jsx': True
            })

            # Module docstring: from top-level comments array attached to the tree
            if hasattr(tree, 'comments') and tree.comments is not None:
                for comment_obj in tree.comments:
                    if hasattr(comment_obj, 'loc') and comment_obj.loc.start.line == 1 and \
                       hasattr(comment_obj, 'type') and comment_obj.type == 'Block' and \
                       hasattr(comment_obj, 'value') and isinstance(comment_obj.value, str) and \
                       comment_obj.value.startswith('*'):
                        elements.append(CodeElement(
                            name="module", type=ElementType.MODULE,
                            file_path=Path(""), line_number=1,
                            docstring=self._clean_jsdoc(comment_obj.value)
                        ))
                        break # Found first top-level block comment at line 1
            
            # Build a map of block comments by their end line
            block_comments_by_end_line = {}
            if hasattr(tree, 'comments') and tree.comments is not None:
                for comment_obj in tree.comments:
                    if hasattr(comment_obj, 'type') and comment_obj.type == 'Block' and \
                       hasattr(comment_obj, 'loc') and hasattr(comment_obj.loc, 'end') and \
                       hasattr(comment_obj.loc.end, 'line'):
                        block_comments_by_end_line[comment_obj.loc.end.line] = comment_obj

            # Split source into lines for whitespace checking
            source_lines = content.splitlines()

            # Initialize file_path (ideally, this would be the actual file path)
            current_file_path = Path("") # Placeholder
            elements = self._collect_elements_recursive(tree, set(), elements, current_file_path, start_line, end_line, block_comments_by_end_line, source_lines)

        except (esprima.Error, AttributeError, TypeError) as e:
            print(f"Error parsing JavaScript content: {str(e)}")
            pass # Graceful exit
        
        return elements

def get_parser(file_path: Path) -> Optional[BaseParser]:
    """
    Get appropriate parser for file type.

    Args:
        file_path (Path): Path to the file.

    Returns:
        Optional[BaseParser]: Parser instance for the file type, or None if unsupported.
    """
    extension = file_path.suffix.lower()
    
    if extension in ['.py']:
        return PythonParser()
    elif extension in ['.js', '.jsx', '.ts', '.tsx']:
        return JavaScriptParser()
    
    return None 