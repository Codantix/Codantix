"""
Documentation generation for Codantix.

This module provides the DocumentationGenerator class, which generates documentation for code elements using LLMs and customizable templates.
Supports Google, NumPy, and JSDoc styles.
"""

import logging
from dataclasses import dataclass
from typing import Dict, Optional

from langchain.chat_models import init_chat_model
from langchain_core.callbacks import get_usage_metadata_callback
from langchain_core.language_models import BaseChatModel

from codantix.config import DocStyle, ElementType, LLMConfig
from codantix.documentation import CodeElement


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

    def __init__(
        self,
        doc_style: DocStyle = DocStyle.GOOGLE,
        llm_config: Optional[LLMConfig] = None,
        llm: Optional[BaseChatModel] = None,
    ):
        """
        Initialize the DocumentationGenerator.

        Args:
            doc_style (DocStyle): The documentation style to use.
            llm_config (LLMConfig): The configuration for the LLM.
            llm (BaseChatModel): The LLM to use.

        Config options for rate limiting (all optional, with defaults):
            llm_requests_per_second: float, default 0.1
            llm_check_every_n_seconds: float, default 0.1
            llm_max_bucket_size: int, default 10
        """
        assert doc_style in DocStyle, f"Invalid doc_style: {doc_style}. Must be one of: {DocStyle}"
        self.doc_style = doc_style
        self.llm_config = llm_config or LLMConfig()
        self.templates = self._get_templates()
        self.llm = llm or self._init_llm()

    def _init_llm(self):
        """
        Initialize the LLM based on provider and config.
        Returns:
            LLM instance compatible with LangChain.
        Raises:
            ImportError: If the required LLM provider is not installed.
            ValueError: If required API keys are not set in the environment.
            NotImplementedError: If the provider is not supported.
        """
        provider = self.llm_config.provider
        llm_model = self.llm_config.llm_model
        try:
            return init_chat_model(
                model_provider=provider,
                model=llm_model,
                temperature=self.llm_config.temperature,
                max_tokens=self.llm_config.max_tokens,
                top_p=self.llm_config.top_p,
                top_k=self.llm_config.top_k,
            )
        except Exception as e:
            raise RuntimeError(
                f"Failed to initialize chat model for provider '{provider}' and model '{llm_model}': {e}"
            )

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
\"\"\"""",
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
\"\"\"""",
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
 */""",
            ),
        }

    def generate_doc(self, element: CodeElement, context: Dict[str, str]) -> str:
        """
        Generate documentation for a code element.

        Args:
            element (CodeElement): The code element to document.
            context (Dict[str, str]): Project context for documentation (e.g., description, architecture).

        Returns:
            str: The generated documentation string.
        Raises:
            RuntimeError: If the LLM is not available or fails for a known reason.
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
            if self.llm:
                messages = [
                    {
                        "role": "system",
                        "content": "You are a documentation expert. Generate clear and concise documentation.",
                    },
                    {"role": "user", "content": prompt},
                ]
                with get_usage_metadata_callback() as cb:
                    response = self.llm.invoke(messages)
                    logging.info(cb.usage_metadata)
                return response
            else:
                raise RuntimeError("No LLM available.")
        except Exception as e:
            # LangChain and provider-specific error handling
            import traceback

            tb = traceback.format_exc()
            msg = str(e).lower()
            if "rate limit" in msg or "429" in msg:
                raise RuntimeError(
                    "LLM rate limit exceeded. Please wait and try again. See: https://python.langchain.com/docs/how_to/chat_model_rate_limiting/"
                ) from e
            elif "quota" in msg or "exceeded your current quota" in msg:
                raise RuntimeError(
                    "LLM quota exceeded for your API key/account. Please check your provider dashboard."
                ) from e
            elif "not found" in msg or "model not found" in msg or "downloaded" in msg:
                raise RuntimeError(
                    "Requested LLM model not found or not downloaded. Please check your model name and provider."
                ) from e
            elif "permission" in msg or "unauthorized" in msg or "forbidden" in msg:
                raise RuntimeError(
                    "Permission denied or unauthorized to use the selected LLM/model. Please check your API key and permissions."
                ) from e
            else:
                raise RuntimeError(f"LLM error: {e}\nTraceback:\n{tb}") from e

    def _get_hierarchy_context(self, element: CodeElement, context: Dict[str, str]) -> str:
        """
        Build a minimal hierarchy context for the code element.

        For example, for a method in package/module/class/method:
        - Package: short purpose (from context)
        - Module: short purpose and role in package (from module docstring or context)
        - Class: short purpose and role in module (from class docstring)

        Args:
            element (CodeElement): The code element to document.
            context (Dict[str, str]): Project context for documentation.

        Returns:
            str: Hierarchy context as minimal one-line rows, most general first.
        """
        lines = []
        # Package/project context
        pkg_purpose = context.get("purpose") or context.get("description")
        if pkg_purpose:
            lines.append(f"Package: {pkg_purpose.splitlines()[0].strip()}")
        # Module context
        module_doc = None
        if element.type in {
            ElementType.MODULE,
            ElementType.CLASS,
            ElementType.FUNCTION,
            ElementType.METHOD,
        }:
            # Try to get module docstring from context if available
            module_doc = context.get("module_doc")
            if not module_doc and hasattr(element, "file_path") and element.file_path:
                # Try to extract from context['module_docs'] if present (dict of file_path->doc)
                module_docs = context.get("module_docs")
                if module_docs and str(element.file_path) in module_docs:
                    module_doc = module_docs[str(element.file_path)]
        if module_doc:
            lines.append(f"Module: {module_doc.splitlines()[0].strip()}")
        # Class context
        if element.type in {ElementType.CLASS, ElementType.METHOD} and hasattr(element, "parent"):
            class_doc = None
            # Try to get class docstring from context if available
            class_docs = context.get("class_docs")
            if class_docs and element.parent in class_docs:
                class_doc = class_docs[element.parent]
            # Fallback: if this is a class, use its own docstring
            if element.type == ElementType.CLASS and element.existing_doc:
                class_doc = element.existing_doc
            if class_doc:
                lines.append(f"Class: {class_doc.splitlines()[0].strip()}")
        return "\n".join(lines)

    def _create_prompt(self, element: CodeElement, context: Dict[str, str]) -> str:
        """
        Create a prompt for the LLM, including hierarchy context.
        """
        # Add hierarchy context at the top
        hierarchy_context = self._get_hierarchy_context(element, context)
        prompt = ""
        if hierarchy_context:
            prompt += f"Hierarchy context:\n{hierarchy_context}\n\n"
        prompt += f"Generate documentation for a {element.type.value} named '{element.name}'"
        if element.parent:
            prompt += f" in class '{element.parent}'"
        prompt += f"\nDocumentation style: {self.doc_style.value}"
        if context.get("description"):
            prompt += f"\nProject description: {context['description']}"
        if context.get("architecture"):
            prompt += f"\nArchitecture context: {context['architecture']}"
        if context.get("purpose"):
            prompt += f"\nProject purpose: {context['purpose']}"
        prompt += "\n\nPlease provide a clear and concise description of what this code element does, with at least one example of usage."
        return prompt

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
            "description": content,
            "project_name": context.get("name", "the project"),
            "architecture_context": context.get("architecture", ""),
            "module_name": element.name if element.type == ElementType.MODULE else "",
            "class_name": element.name if element.type == ElementType.CLASS else "",
            "function_name": (element.name if element.type == ElementType.FUNCTION else ""),
            "method_name": element.name if element.type == ElementType.METHOD else "",
            "args": "",  # These would be extracted from the code
            "returns": "",
            "raises": "",
            "attributes": "",
            "methods": "",
            "properties": "",
            "params": "",
            "throws": "",
        }

        # Add parent class context for methods
        if element.type == ElementType.METHOD and element.parent:
            format_args["description"] = f"{content}\n\nPart of class: {element.parent}"

        try:
            # For Google style, ensure proper docstring formatting
            if self.doc_style == DocStyle.GOOGLE:
                # Add class name to description for class elements
                if element.type == ElementType.CLASS:
                    format_args["description"] = f"Class {element.name}\n\n{content}"
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
