"""
Tests for documentation parsing functionality.
"""

from pathlib import Path

import pytest

from codantix.config import ElementType
from codantix.documentation import CodebaseTraverser, ReadmeParser


@pytest.fixture
def sample_readme(tmp_path):
    """Create a sample README.md file for testing."""
    readme_content = """# Test Project

This project aims to demonstrate documentation parsing capabilities.

## Architecture

This project uses a modular architecture.

## Purpose

This project aims to demonstrate documentation parsing capabilities.
"""
    readme_file = tmp_path / "README.md"
    readme_file.write_text(readme_content)
    return readme_file


@pytest.fixture
def sample_python_file(tmp_path):
    """Create a sample Python file for testing."""
    python_content = '''"""
Module docstring.
"""

class TestClass:
    """Class docstring."""
    
    def test_method(self):
        """Method docstring."""
        pass

def test_function():
    """Function docstring."""
    pass
'''
    python_file = tmp_path / "test.py"
    python_file.write_text(python_content)
    return python_file


def test_readme_parser(sample_readme):
    """Test README parser functionality."""
    parser = ReadmeParser()
    context = parser.parse(sample_readme)

    assert (
        context["description"]
        == "This project aims to demonstrate documentation parsing capabilities."
    )
    assert context["architecture"] == "This project uses a modular architecture."
    assert (
        context["purpose"]
        == "This project aims to demonstrate documentation parsing capabilities."
    )


def test_readme_parser_nonexistent():
    """Test README parser with nonexistent file."""
    parser = ReadmeParser()
    context = parser.parse(Path("nonexistent.md"))
    assert context == {}


def test_codebase_traverser(sample_python_file):
    """Test codebase traverser functionality."""
    traverser = CodebaseTraverser(["python"])
    elements = traverser.traverse(sample_python_file.parent)

    # Should find 4 elements: module, class, method, function
    assert len(elements) == 4

    # Check module
    module = next(e for e in elements if e.type == ElementType.MODULE)
    assert module.name == "module"
    assert module.docstring.strip() == "Module docstring."

    # Check class
    class_elem = next(e for e in elements if e.type == ElementType.CLASS)
    assert class_elem.name == "TestClass"
    assert class_elem.docstring.strip() == "Class docstring."

    # Check function
    function = next(e for e in elements if e.type == ElementType.FUNCTION)
    assert function.name == "test_function"
    assert function.docstring.strip() == "Function docstring."

    # Check method
    method = next(e for e in elements if e.type == ElementType.METHOD)
    assert method.name == "test_method"
    assert method.docstring.strip() == "Method docstring."
    assert method.parent == "TestClass"


def test_codebase_traverser_unsupported_language(tmp_path):
    """Test codebase traverser with unsupported language."""
    js_file = tmp_path / "test.js"
    js_file.write_text("// JavaScript file")

    traverser = CodebaseTraverser(["python"])
    elements = traverser.traverse(tmp_path)
    assert len(elements) == 0


def test_codebase_traverser_nonexistent_path():
    """Test codebase traverser with nonexistent path."""
    traverser = CodebaseTraverser(["python"])
    elements = traverser.traverse(Path("nonexistent"))
    assert len(elements) == 0
