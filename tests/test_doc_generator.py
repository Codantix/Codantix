"""
Tests for documentation generation.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from codantix.config import (
    ConfigValidationError,
    DocStyle,
    ElementType,
    LLMConfig,
)
from codantix.doc_generator import DocTemplate, DocumentationGenerator
from codantix.documentation import CodeElement


@pytest.fixture
def sample_context():
    """Create a sample context for testing."""
    return {
        "name": "TestProject",
        "description": "A test project for documentation generation",
        "architecture": ("Modular architecture with clear separation of concerns"),
        "purpose": "To demonstrate documentation generation capabilities",
    }


@pytest.fixture
def sample_elements():
    """Create sample code elements for testing."""
    return [
        CodeElement(
            name="test_module",
            type=ElementType.MODULE,
            file_path=Path("test.py"),
            line_number=1,
        ),
        CodeElement(
            name="TestClass",
            type=ElementType.CLASS,
            file_path=Path("test.py"),
            line_number=5,
        ),
        CodeElement(
            name="test_method",
            type=ElementType.METHOD,
            file_path=Path("test.py"),
            line_number=10,
            parent="TestClass",
        ),
        CodeElement(
            name="test_function",
            type=ElementType.FUNCTION,
            file_path=Path("test.py"),
            line_number=15,
        ),
    ]


def test_doc_generator_initialization(mock_llm):
    """Test documentation generator initialization."""
    generator = DocumentationGenerator(
        doc_style=DocStyle.GOOGLE,
        llm_config=LLMConfig(provider="openai", llm_model="gpt-4"),
        llm=mock_llm,
    )
    assert generator.doc_style == DocStyle.GOOGLE
    assert DocStyle.GOOGLE in generator.templates
    assert DocStyle.NUMPY in generator.templates
    assert DocStyle.JSDOC in generator.templates
    assert generator.llm == mock_llm


def test_doc_generator_invalid_style(mock_llm):
    """Test documentation generator with invalid style."""
    with pytest.raises(AssertionError):
        DocumentationGenerator(
            doc_style="invalid_style",
            llm_config=LLMConfig(provider="openai", llm_model="gpt-4"),
            llm=mock_llm,
        )


def test_preserve_existing_doc(sample_elements, sample_context, mock_llm):
    """Test that existing documentation is preserved."""
    element = CodeElement(
        name="test_function",
        type=ElementType.FUNCTION,
        file_path=Path("test.py"),
        line_number=1,
        existing_doc="Existing documentation",
    )
    generator = DocumentationGenerator(
        doc_style=DocStyle.GOOGLE,
        llm_config=LLMConfig(provider="openai", llm_model="gpt-4"),
        llm=mock_llm,
    )
    doc = generator.generate_doc(element, sample_context)
    assert doc == "Existing documentation"


def test_doc_templates(sample_elements, sample_context, mock_llm):
    """Test different documentation templates."""
    # Test Google style
    generator = DocumentationGenerator(
        doc_style=DocStyle.GOOGLE,
        llm_config=LLMConfig(provider="openai", llm_model="gpt-4"),
        llm=mock_llm,
    )
    doc = generator.generate_doc(sample_elements[0], sample_context)
    assert "Google docstring" in doc.generations[0].message.content
    # Test NumPy style
    generator = DocumentationGenerator(
        doc_style=DocStyle.NUMPY,
        llm_config=LLMConfig(provider="openai", llm_model="gpt-4"),
        llm=mock_llm,
    )
    doc = generator.generate_doc(sample_elements[3], sample_context)
    assert "NumPy docstring" in doc.generations[0].message.content
    # Test JSDoc style
    generator = DocumentationGenerator(
        doc_style=DocStyle.JSDOC,
        llm_config=LLMConfig(provider="openai", llm_model="gpt-4"),
        llm=mock_llm,
    )
    doc = generator.generate_doc(sample_elements[1], sample_context)
    assert "JSDoc" in doc.generations[0].message.content


def test_create_prompt(sample_elements, sample_context, mock_llm):
    """Test prompt creation for different element types."""
    generator = DocumentationGenerator(
        doc_style=DocStyle.GOOGLE,
        llm_config=LLMConfig(provider="openai", llm_model="gpt-4"),
        llm=mock_llm,
    )
    # Test module prompt
    prompt = generator._create_prompt(sample_elements[0], sample_context)
    assert "module" in prompt.lower()
    assert sample_context["description"] in prompt
    assert sample_context["architecture"] in prompt
    # Test class prompt
    prompt = generator._create_prompt(sample_elements[1], sample_context)
    assert "class" in prompt.lower()
    assert "TestClass" in prompt
    # Test method prompt
    prompt = generator._create_prompt(sample_elements[2], sample_context)
    assert "method" in prompt.lower()
    assert "TestClass" in prompt
    assert "test_method" in prompt


def test_format_doc(sample_elements, sample_context, mock_llm):
    """Test documentation formatting."""
    generator = DocumentationGenerator(
        doc_style=DocStyle.GOOGLE,
        llm_config=LLMConfig(provider="openai", llm_model="gpt-4"),
        llm=mock_llm,
    )
    content = "Test documentation content"
    # Test module formatting
    doc = generator._format_doc(
        generator.templates[DocStyle.GOOGLE].module_template,
        content,
        sample_elements[0],
        sample_context,
    )
    assert content in doc
    assert sample_context["name"] in doc
    assert sample_context["architecture"] in doc
    assert doc.startswith('"""')
    assert doc.endswith('"""')
    # Test class formatting
    doc = generator._format_doc(
        generator.templates[DocStyle.GOOGLE].class_template,
        content,
        sample_elements[1],
        sample_context,
    )
    assert "Class TestClass" in doc
    assert content in doc
    assert doc.startswith('"""')
    assert doc.endswith('"""')


def test_doc_template_structure(mock_llm):
    """Test documentation template structure."""
    generator = DocumentationGenerator(
        doc_style=DocStyle.GOOGLE,
        llm_config=LLMConfig(provider="openai", llm_model="gpt-4"),
        llm=mock_llm,
    )
    template = generator.templates[DocStyle.GOOGLE]
    assert isinstance(template, DocTemplate)
    assert template.style == DocStyle.GOOGLE
    assert "{description}" in template.module_template
    assert "{description}" in template.class_template
    assert "{description}" in template.function_template
    assert "{description}" in template.method_template


def test_error_handling(sample_elements, sample_context, mock_llm):
    """Test error handling in documentation generation."""
    generator = DocumentationGenerator(
        doc_style=DocStyle.GOOGLE,
        llm_config=LLMConfig(provider="openai", llm_model="gpt-4"),
        llm=mock_llm,
    )

    # Test with invalid element type
    with pytest.raises(AttributeError):
        generator._get_element_type(None)
