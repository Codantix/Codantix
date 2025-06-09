"""
Tests for language-specific parsers.
"""

import ast
from pathlib import Path

import pytest

from codantix.config import ElementType
from codantix.parsers import (
    BaseParser,
    JavaParser,
    JavaScriptParser,
    PythonParser,
    get_parser,
)


def test_python_parser():
    """Test Python code parsing."""
    parser = PythonParser()
    content = '''"""Module docstring."""

class TestClass:
    """Class docstring."""
    
    def test_method(self):
        """Method docstring."""
        pass

def test_function():
    """Function docstring."""
    pass
'''

    elements = parser.parse_file(content, 1, 20)
    assert len(elements) == 4

    # Check module docstring
    module = next(e for e in elements if e.type == ElementType.MODULE)
    assert module.name == "module"
    assert module.docstring == "Module docstring."

    # Check class
    class_elem = next(e for e in elements if e.type == ElementType.CLASS)
    assert class_elem.name == "TestClass"
    assert class_elem.docstring == "Class docstring."

    # Check method
    method = next(
        e for e in elements if e.type == ElementType.METHOD and e.name == "test_method"
    )
    assert method.docstring == "Method docstring."

    # Check function
    function = next(
        e
        for e in elements
        if e.type == ElementType.FUNCTION and e.name == "test_function"
    )
    assert function.docstring == "Function docstring."


def test_javascript_parser():
    """Test JavaScript code parsing."""
    parser = JavaScriptParser()
    content = """/**
 * Module docstring
 */

/**
* Class docstring
*/
class TestClass {
    /**
     * constructor docstring
     */
    constructor() {}
    
    /**
     * Method docstring
     */
    testMethod() {}
}

/**
 * Function docstring
 */
function testFunction() {}
"""

    elements = parser.parse_file(content, 1, 30)
    assert len(elements) == 5

    # Check module docstring
    module = next(e for e in elements if e.type == ElementType.MODULE)
    assert module.name == "module"
    assert "Module docstring" in module.docstring

    # Check class
    class_elem = next(e for e in elements if e.type == ElementType.CLASS)
    assert class_elem.name == "TestClass"
    assert "Class docstring" in class_elem.docstring

    # Check constructor method
    constructor = next(
        e for e in elements if e.type == ElementType.METHOD and e.name == "constructor"
    )
    assert "constructor docstring" in constructor.docstring

    # Check method
    method = next(
        e for e in elements if e.type == ElementType.METHOD and e.name == "testMethod"
    )
    assert "Method docstring" in method.docstring

    # Check function
    function = next(
        e
        for e in elements
        if e.type == ElementType.FUNCTION and e.name == "testFunction"
    )
    assert "Function docstring" in function.docstring


def test_parser_selection():
    """Test parser selection based on file extension."""
    assert isinstance(get_parser(Path("test.py")), PythonParser)
    assert isinstance(get_parser(Path("test.js")), JavaScriptParser)
    assert isinstance(get_parser(Path("test.ts")), JavaScriptParser)
    assert isinstance(get_parser(Path("test.jsx")), JavaScriptParser)
    assert isinstance(get_parser(Path("test.tsx")), JavaScriptParser)
    assert isinstance(get_parser(Path("test.java")), JavaParser)


def test_python_syntax_error():
    """Test handling of Python syntax errors."""
    parser = PythonParser()
    content = "def invalid_syntax:"
    elements = parser.parse_file(content, 1, 1)
    assert len(elements) == 0  # Should handle syntax error gracefully


def test_javascript_complex():
    """Test parsing of complex JavaScript code."""
    parser = JavaScriptParser()
    content = """export class ComplexClass {
    /**
     * Complex method with parameters
     * @param {string} param1 - First parameter
     * @param {number} param2 - Second parameter
     * @returns {boolean} Return value
     */
    async complexMethod(param1, param2) {
        return true;
    }
}"""

    elements = parser.parse_file(content, 1, 10)
    assert len(elements) == 2  # Class and method

    method = next(e for e in elements if e.type == ElementType.METHOD)
    assert method.name == "complexMethod"
    assert "Complex method with parameters" in method.docstring
    assert "@param" in method.docstring
    assert "@returns" in method.docstring


def test_baseparser_notimplemented():
    base = BaseParser()
    with pytest.raises(NotImplementedError):
        base.parse_file("", 1, 1)
    with pytest.raises(NotImplementedError):
        base.extract_docstring("", ElementType.FUNCTION)


def test_pythonparser_get_docstring():
    parser = PythonParser()
    # Not a function/class
    assert parser._get_docstring(ast.parse("x = 1").body[0]) is None
    # Function with no body
    func = ast.FunctionDef(
        name="f",
        args=ast.arguments(
            posonlyargs=[], args=[], kwonlyargs=[], kw_defaults=[], defaults=[]
        ),
        body=[],
        decorator_list=[],
    )
    assert parser._get_docstring(func) is None
    # Function with non-docstring first node
    func.body = [ast.Pass()]
    assert parser._get_docstring(func) is None
    # Function with docstring
    func.body = [ast.Expr(value=ast.Constant(value="doc"))]
    assert parser._get_docstring(func) == "doc"


def test_javascriptparser_clean_jsdoc():
    parser = JavaScriptParser()
    # None or empty
    assert parser._clean_jsdoc(None) is None
    assert parser._clean_jsdoc("") is None
    # No stars
    assert parser._clean_jsdoc("Just a line") == "Just a line"
    # With stars and whitespace
    jsdoc = """*
 * Foo
 * Bar
 """
    assert parser._clean_jsdoc(jsdoc) == "Foo\nBar"


def test_javascriptparser_get_jsdoc_leading():
    parser = JavaScriptParser()

    class Dummy:
        pass

    comment = type("Comment", (), {"type": "Block", "value": "* JSDoc"})()
    node = Dummy()
    node.leadingComments = [comment]
    assert parser._get_jsdoc(node) == "JSDoc"


def test_javascriptparser_get_jsdoc_block_comments():
    parser = JavaScriptParser()

    class Dummy:
        pass

    # Set up a comment ending at line 2, node starting at line 3
    comment = type(
        "Comment",
        (),
        {
            "type": "Block",
            "value": "* JSDoc",
            "loc": type("Loc", (), {"end": type("End", (), {"line": 2})()})(),
        },
    )()
    node = Dummy()
    node.loc = type("Loc", (), {"start": type("Start", (), {"line": 3})()})()
    block_comments = {2: comment}
    # No code between comment and node
    source_lines = ["", "", ""]
    assert parser._get_jsdoc(node, block_comments, source_lines) == "JSDoc"


def test_javascriptparser_collect_elements_recursive_none():
    parser = JavaScriptParser()
    # Should not fail on None
    out = parser._collect_elements_recursive(None, set(), [], Path(""), 1, 10)
    assert out == []


def test_java_parser():
    """Test Java code parsing."""
    parser = JavaParser()
    content = """/**
 * Class docstring
 */
public class TestClass {
    /**
     * Method docstring
     */
    public void testMethod() {}
    
    // No doc
    private int helper() { return 0; }
}
"""
    elements = parser.parse_file(content, 1, len(content.splitlines()))
    # Should find one class and two methods
    class_elem = next(e for e in elements if e.type == ElementType.CLASS)
    assert class_elem.name == "TestClass"
    assert "Class docstring" in class_elem.docstring
    method = next(
        e for e in elements if e.type == ElementType.METHOD and e.name == "testMethod"
    )
    assert "Method docstring" in method.docstring
    helper = next(
        e for e in elements if e.type == ElementType.METHOD and e.name == "helper"
    )
    assert helper.docstring is None or helper.docstring == ""
