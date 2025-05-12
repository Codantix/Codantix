"""
Tests for language-specific parsers.
"""
import pytest
from pathlib import Path
from codantix.parsers import PythonParser, JavaScriptParser, get_parser
from codantix.documentation import ElementType

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
    method = next(e for e in elements if e.type == ElementType.FUNCTION and e.name == "test_method")
    assert method.docstring == "Method docstring."
    
    # Check function
    function = next(e for e in elements if e.type == ElementType.FUNCTION and e.name == "test_function")
    assert function.docstring == "Function docstring."

def test_javascript_parser():
    """Test JavaScript code parsing."""
    parser = JavaScriptParser()
    content = '''/**
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
'''
    
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
    constructor = next(e for e in elements if e.type == ElementType.METHOD and e.name == "constructor")
    assert "constructor docstring" in constructor.docstring
    
    # Check method
    method = next(e for e in elements if e.type == ElementType.METHOD and e.name == "testMethod")
    assert "Method docstring" in method.docstring
    
    # Check function
    function = next(e for e in elements if e.type == ElementType.FUNCTION and e.name == "testFunction")
    assert "Function docstring" in function.docstring

def test_parser_selection():
    """Test parser selection based on file extension."""
    assert isinstance(get_parser(Path("test.py")), PythonParser)
    assert isinstance(get_parser(Path("test.js")), JavaScriptParser)
    assert isinstance(get_parser(Path("test.ts")), JavaScriptParser)
    assert isinstance(get_parser(Path("test.jsx")), JavaScriptParser)
    assert isinstance(get_parser(Path("test.tsx")), JavaScriptParser)
    assert get_parser(Path("test.java")) is None

def test_python_syntax_error():
    """Test handling of Python syntax errors."""
    parser = PythonParser()
    content = "def invalid_syntax:"
    elements = parser.parse_file(content, 1, 1)
    assert len(elements) == 0  # Should handle syntax error gracefully

def test_javascript_complex():
    """Test parsing of complex JavaScript code."""
    parser = JavaScriptParser()
    content = '''export class ComplexClass {
    /**
     * Complex method with parameters
     * @param {string} param1 - First parameter
     * @param {number} param2 - Second parameter
     * @returns {boolean} Return value
     */
    async complexMethod(param1, param2) {
        return true;
    }
}'''
    
    elements = parser.parse_file(content, 1, 10)
    assert len(elements) == 2  # Class and method
    
    method = next(e for e in elements if e.type == ElementType.METHOD)
    assert method.name == "complexMethod"
    assert "Complex method with parameters" in method.docstring
    assert "@param" in method.docstring
    assert "@returns" in method.docstring 