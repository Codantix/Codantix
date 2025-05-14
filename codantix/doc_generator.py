"""
Documentation generation for Codantix.

This module provides the DocumentationGenerator class, which generates documentation for code elements using LLMs and customizable templates.
Supports Google, NumPy, and JSDoc styles.
"""
from typing import Dict, Optional
from dataclasses import dataclass
import openai
from pathlib import Path
from .documentation import CodeElement, ElementType
from .config import DocStyle


@dataclass
class DocTemplate:
    """Template for different documentation styles."""
    style: DocStyle
    module_template: str
    class_template: str
    function_template: str
    method_template: str

class DocumentationGenerator:
    """
    Generates documentation for code elements.

    Uses LLMs and customizable templates to generate docstrings for modules, classes, functions, and methods.
    Supports Google, NumPy, and JSDoc documentation styles.
    """

    def __init__(self, doc_style: str = "google", api_key: Optional[str] = None):
        """
        Initialize the DocumentationGenerator.

        Args:
            doc_style (str): The documentation style to use ("google", "numpy", or "jsdoc").
            api_key (Optional[str]): Optional API key for the LLM provider.
        """
        self.doc_style = DocStyle(doc_style)
        self.templates = self._get_templates()
        if api_key:
            openai.api_key = api_key

    def _get_templates(self) -> Dict[DocStyle, DocTemplate]:
        """
        Get documentation templates for different styles.

        Returns:
            Dict[DocStyle, DocTemplate]: Mapping of documentation styles to their templates.
        """
        return {
            DocStyle.GOOGLE: DocTemplate(
                style=DocStyle.GOOGLE,
                module_template="""\"\"\"
{description}

This module is part of {project_name}.

{architecture_context}
\"\"\"""",
                class_template="""\"\"\"
{description}

{attributes}

{methods}
\"\"\"""",
                function_template="""\"\"\"
{description}

Args:
{args}

Returns:
{returns}

Raises:
{raises}
\"\"\"""",
                method_template="""\"\"\"
{description}

Args:
{args}

Returns:
{returns}

Raises:
{raises}
\"\"\""""
            ),
            DocStyle.NUMPY: DocTemplate(
                style=DocStyle.NUMPY,
                module_template="""\"\"\"
{description}

This module is part of {project_name}.

{architecture_context}
\"\"\"""",
                class_template="""\"\"\"
{description}

Attributes
----------
{attributes}

Methods
-------
{methods}
\"\"\"""",
                function_template="""\"\"\"
{description}

Parameters
----------
{args}

Returns
-------
{returns}

Raises
------
{raises}
\"\"\"""",
                method_template="""\"\"\"
{description}

Parameters
----------
{args}

Returns
-------
{returns}

Raises
------
{raises}
\"\"\""""
            ),
            DocStyle.JSDOC: DocTemplate(
                style=DocStyle.JSDOC,
                module_template="""/**
 * {description}
 *
 * @module {module_name}
 * @partof {project_name}
 *
 * {architecture_context}
 */""",
                class_template="""/**
 * {description}
 *
 * @class {class_name}
 * @classdesc {description}
 *
 * @property {properties}
 */""",
                function_template="""/**
 * {description}
 *
 * @function {function_name}
 * @param {params}
 * @returns {returns}
 * @throws {throws}
 */""",
                method_template="""/**
 * {description}
 *
 * @method {method_name}
 * @param {params}
 * @returns {returns}
 * @throws {throws}
 */"""
            )
        }

    def generate_doc(self, element: CodeElement, context: Dict[str, str]) -> str:
        """
        Generate documentation for a code element.

        Args:
            element (CodeElement): The code element to document.
            context (Dict[str, str]): Project context for documentation (e.g., description, architecture).

        Returns:
            str: The generated documentation string.
        """
        if element.existing_doc:
            return element.existing_doc

        template = self.templates[self.doc_style]
        
        # Get the appropriate template based on element type
        if element.type == ElementType.MODULE:
            doc_template = template.module_template
        elif element.type == ElementType.CLASS:
            doc_template = template.class_template
        elif element.type == ElementType.FUNCTION:
            doc_template = template.function_template
        else:  # METHOD
            doc_template = template.method_template

        # Generate documentation using LLM
        prompt = self._create_prompt(element, context)
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a documentation expert. Generate clear and concise documentation."},
                    {"role": "user", "content": prompt}
                ]
            )
            doc_content = response.choices[0].message.content
        except Exception as e:
            print(f"Error generating documentation: {e}")
            return self._format_doc(doc_template, self._generate_fallback_doc(element), element, context)

        # Format the documentation using the template
        return self._format_doc(doc_template, doc_content, element, context)

    def _create_prompt(self, element: CodeElement, context: Dict[str, str]) -> str:
        """
        Create a prompt for the LLM.

        Args:
            element (CodeElement): The code element to document.
            context (Dict[str, str]): Project context for documentation.

        Returns:
            str: The prompt string for the LLM.
        """
        prompt = f"""Generate documentation for a {element.type.value} named '{element.name}'"""
        if element.parent:
            prompt += f" in class '{element.parent}'"
        
        if context.get('description'):
            prompt += f"\nProject description: {context['description']}"
        if context.get('architecture'):
            prompt += f"\nArchitecture context: {context['architecture']}"
        if context.get('purpose'):
            prompt += f"\nProject purpose: {context['purpose']}"

        prompt += "\n\nPlease provide a clear and concise description of what this code element does."
        return prompt

    def _generate_fallback_doc(self, element: CodeElement) -> str:
        """
        Generate a simple fallback documentation when LLM is not available.

        Args:
            element (CodeElement): The code element to document.

        Returns:
            str: Fallback documentation string.
        """
        if element.type == ElementType.MODULE:
            return f"Module {element.name}"
        elif element.type == ElementType.CLASS:
            return f"Class {element.name}"
        elif element.type == ElementType.FUNCTION:
            return f"Function {element.name}"
        else:  # METHOD
            return f"Method {element.name} of class {element.parent}"

    def _format_doc(self, template: str, content: str, element: CodeElement, context: Dict[str, str]) -> str:
        """
        Format the documentation using the template.

        Args:
            template (str): The documentation template string.
            content (str): The generated or fallback documentation content.
            element (CodeElement): The code element being documented.
            context (Dict[str, str]): Project context for documentation.

        Returns:
            str: The formatted documentation string.
        """
        # Basic formatting
        format_args = {
            'description': content,
            'project_name': context.get('name', 'the project'),
            'architecture_context': context.get('architecture', ''),
            'module_name': element.name if element.type == ElementType.MODULE else '',
            'class_name': element.name if element.type == ElementType.CLASS else '',
            'function_name': element.name if element.type == ElementType.FUNCTION else '',
            'method_name': element.name if element.type == ElementType.METHOD else '',
            'args': "",  # These would be extracted from the code
            'returns': "",
            'raises': "",
            'attributes': "",
            'methods': "",
            'properties': "",
            'params': "",
            'throws': ""
        }

        # Add parent class context for methods
        if element.type == ElementType.METHOD and element.parent:
            format_args['description'] = f"{content}\n\nPart of class: {element.parent}"

        try:
            # For Google style, ensure proper docstring formatting
            if self.doc_style == DocStyle.GOOGLE:
                # Add class name to description for class elements
                if element.type == ElementType.CLASS:
                    format_args['description'] = f"Class {element.name}\n\n{content}"
                doc = template.format(**format_args)
                if not doc.startswith('"""'):
                    doc = '"""\n' + doc
                if not doc.endswith('"""'):
                    doc = doc + '\n"""'
            else:
                doc = template.format(**format_args)
            return doc.strip()
        except KeyError as e:
            print(f"Error formatting documentation: {e}")
            return content 