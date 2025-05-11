"""
Tests for documentation generation functionality.
"""
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from codantix.doc_generator import DocumentationGenerator, DocStyle, DocTemplate
from codantix.documentation import CodeElement, ElementType
import openai

@pytest.fixture
def sample_context():
    """Create a sample context for testing."""
    return {
        'name': 'TestProject',
        'description': 'A test project for documentation generation',
        'architecture': 'Modular architecture with clear separation of concerns',
        'purpose': 'To demonstrate documentation generation capabilities'
    }

@pytest.fixture
def sample_elements():
    """Create sample code elements for testing."""
    return [
        CodeElement(
            name="test_module",
            type=ElementType.MODULE,
            file_path=Path("test.py"),
            line_number=1
        ),
        CodeElement(
            name="TestClass",
            type=ElementType.CLASS,
            file_path=Path("test.py"),
            line_number=5
        ),
        CodeElement(
            name="test_method",
            type=ElementType.METHOD,
            file_path=Path("test.py"),
            line_number=10,
            parent="TestClass"
        ),
        CodeElement(
            name="test_function",
            type=ElementType.FUNCTION,
            file_path=Path("test.py"),
            line_number=15
        )
    ]

def test_doc_generator_initialization():
    """Test documentation generator initialization."""
    generator = DocumentationGenerator(doc_style="google")
    assert generator.doc_style == DocStyle.GOOGLE
    assert DocStyle.GOOGLE in generator.templates
    assert DocStyle.NUMPY in generator.templates
    assert DocStyle.JSDOC in generator.templates

def test_doc_generator_invalid_style():
    """Test documentation generator with invalid style."""
    with pytest.raises(ValueError):
        DocumentationGenerator(doc_style="invalid_style")

def test_preserve_existing_doc(sample_elements, sample_context):
    """Test that existing documentation is preserved."""
    element = CodeElement(
        name="test_function",
        type=ElementType.FUNCTION,
        file_path=Path("test.py"),
        line_number=1,
        existing_doc="Existing documentation"
    )
    generator = DocumentationGenerator()
    doc = generator.generate_doc(element, sample_context)
    assert doc == "Existing documentation"

@patch('openai.ChatCompletion.create')
def test_generate_doc_with_llm(mock_openai, sample_elements, sample_context):
    """Test documentation generation with LLM."""
    # Mock OpenAI response
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Generated documentation"
    mock_openai.return_value = mock_response

    generator = DocumentationGenerator()
    doc = generator.generate_doc(sample_elements[0], sample_context)
    
    # Verify the prompt
    mock_openai.assert_called_once()
    call_args = mock_openai.call_args[1]['messages']
    assert "Generate documentation for a module" in call_args[1]['content']
    assert sample_context['description'] in call_args[1]['content']

def test_fallback_doc_generation(sample_elements, sample_context):
    """Test fallback documentation generation when LLM fails."""
    generator = DocumentationGenerator()
    
    with patch('openai.ChatCompletion.create', side_effect=Exception("API Error")):
        # Test module fallback
        doc = generator.generate_doc(sample_elements[0], sample_context)
        assert "Module test_module" in doc
        assert doc.startswith('"""')
        assert doc.endswith('"""')
        
        # Test method fallback
        doc = generator.generate_doc(sample_elements[2], sample_context)
        assert "Method test_method of class TestClass" in doc
        assert doc.startswith('"""')
        assert doc.endswith('"""')

def test_doc_templates(sample_elements, sample_context):
    """Test different documentation templates."""
    # Test Google style
    generator = DocumentationGenerator(doc_style="google")
    doc = generator.generate_doc(sample_elements[0], sample_context)
    assert "This module is part of" in doc
    assert "Args:" not in doc  # Not a function

    # Test NumPy style
    generator = DocumentationGenerator(doc_style="numpy")
    doc = generator.generate_doc(sample_elements[3], sample_context)
    assert "Parameters" in doc
    assert "Returns" in doc

    # Test JSDoc style
    generator = DocumentationGenerator(doc_style="jsdoc")
    doc = generator.generate_doc(sample_elements[1], sample_context)
    assert "@class" in doc
    assert "@classdesc" in doc

def test_create_prompt(sample_elements, sample_context):
    """Test prompt creation for different element types."""
    generator = DocumentationGenerator()
    
    # Test module prompt
    prompt = generator._create_prompt(sample_elements[0], sample_context)
    assert "module" in prompt.lower()
    assert sample_context['description'] in prompt
    assert sample_context['architecture'] in prompt
    
    # Test class prompt
    prompt = generator._create_prompt(sample_elements[1], sample_context)
    assert "class" in prompt.lower()
    assert "TestClass" in prompt
    
    # Test method prompt
    prompt = generator._create_prompt(sample_elements[2], sample_context)
    assert "method" in prompt.lower()
    assert "TestClass" in prompt
    assert "test_method" in prompt

def test_format_doc(sample_elements, sample_context):
    """Test documentation formatting."""
    generator = DocumentationGenerator()
    content = "Test documentation content"
    
    # Test module formatting
    doc = generator._format_doc(
        generator.templates[DocStyle.GOOGLE].module_template,
        content,
        sample_elements[0],
        sample_context
    )
    assert content in doc
    assert sample_context['name'] in doc
    assert sample_context['architecture'] in doc
    assert doc.startswith('"""')
    assert doc.endswith('"""')

    # Test class formatting
    doc = generator._format_doc(
        generator.templates[DocStyle.GOOGLE].class_template,
        content,
        sample_elements[1],
        sample_context
    )
    assert "Class TestClass" in doc
    assert content in doc
    assert doc.startswith('"""')
    assert doc.endswith('"""')

def test_api_key_initialization():
    """Test API key initialization."""
    test_key = "test_api_key"
    generator = DocumentationGenerator(api_key=test_key)
    assert openai.api_key == test_key

def test_doc_template_structure():
    """Test documentation template structure."""
    generator = DocumentationGenerator()
    template = generator.templates[DocStyle.GOOGLE]
    
    assert isinstance(template, DocTemplate)
    assert template.style == DocStyle.GOOGLE
    assert "{description}" in template.module_template
    assert "{description}" in template.class_template
    assert "{description}" in template.function_template
    assert "{description}" in template.method_template

def test_error_handling(sample_elements, sample_context):
    """Test error handling in documentation generation."""
    generator = DocumentationGenerator()
    
    # Test with invalid element type
    with pytest.raises(AttributeError):
        generator._get_element_type(None)
    
    # Test with missing context
    doc = generator.generate_doc(sample_elements[0], {})
    assert "the project" in doc  # Default project name 