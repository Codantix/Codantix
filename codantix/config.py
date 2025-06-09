"""
Configuration management for Codantix.

This module provides the Config class for loading, validating,
and saving project configuration from JSON or YAML files.
Supports default values, schema validation, and format conversion.
"""

import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import List, Optional

import yaml
from pydantic import BaseModel, Field, ValidationError, model_validator

LANGUAGE_EXTENSION_MAP = {
    "python": {".py"},
    "javascript": {".js", ".jsx", ".ts", ".tsx"},
    "java": {".java"},
}


class DocStyle(str, Enum):
    """
    Configuration for the documentation style.
    """

    GOOGLE = "google"
    NUMPY = "numpy"
    JSDOC = "jsdoc"


class VectorDBType(str, Enum):
    """
    Configuration for the vector database.
    """

    CHROMA = "chroma"
    QDRANT = "qdrant"
    MILVUS = "milvus"
    MILVUS_LITE = "milvus_lite"


class ConfigValidationError(Exception):
    """
    Raised when configuration validation fails.
    """

    pass


class RateLimitConfig(BaseModel):
    """
    Configuration for the rate limit.
    """

    llm_requests_per_second: float = Field(
        0.1, description="Max LLM requests per second"
    )
    llm_check_every_n_seconds: float = Field(
        0.1, description="How often to check if a request can be made (seconds)"
    )
    llm_max_bucket_size: int = Field(
        10, description="Maximum burst size for LLM requests"
    )


class LLMConfig(BaseModel):
    """
    Configuration for the LLM.
    """

    provider: str = Field("google_genai", description="LLM provider")
    llm_model: str = Field(
        "gemini-2.5-flash-preview-04-17", description="LLM model name"
    )
    max_tokens: int = Field(1024, description="Maximum number of tokens to generate")
    temperature: float = Field(0.7, description="Temperature for the LLM")
    top_p: Optional[float] = Field(None, description="Top-p for the LLM")
    top_k: Optional[int] = Field(None, description="Top-k for the LLM")
    stop_sequences: List[str] = Field(
        default_factory=lambda: [], description="Stop sequences for the LLM"
    )
    rate_limit: RateLimitConfig = Field(
        default_factory=RateLimitConfig, description="Rate limit configuration"
    )


class VectorDBConfig(BaseModel):
    """
    Configuration for the vector database.
    """

    type: VectorDBType = Field(VectorDBType.CHROMA, description="Vector database type")
    path: str = Field("vecdb/", description="Path to the vector database")
    provider: str = Field("huggingface", description="Provider for the vector database")
    embedding: str = Field("BAAI/bge-small-en-v1.5", description="Embedding model name")
    dimensions: int = Field(512, description="Embedding dimensions")
    collection_name: str = Field("codantix_docs", description="Collection name")
    host: str = Field("localhost", description="Host for the vector database")
    port: Optional[int] = Field(None, description="Port for the vector database")
    persist_directory: str = Field("vecdb/", description="Path to the vector database")

    @model_validator(mode="after")
    def check_vector_db_type(self):
        """
        Validate the vector database type.
        """
        valid_types = [v.value for v in VectorDBType]
        if self.type not in valid_types:
            raise ConfigValidationError(
                f"Unsupported vector_db type: {self.type}. Must be one of: {valid_types}"
            )
        return self


class Config(BaseModel):
    """
    Handles loading, validating, and saving Codantix configuration files using Pydantic.
    Supports both JSON and YAML formats, with schema validation and default values.

    Usage:
        config = Config.load()
        print(config.llm.rate_limit.llm_requests_per_second)
    """

    doc_style: DocStyle = Field(DocStyle.GOOGLE, description="Documentation style")
    source_paths: list[str] = Field(
        default_factory=lambda: ["src"], description="Paths to source code files"
    )
    languages: list[str] = Field(
        default_factory=lambda: ["python", "javascript", "java"],
        description="Programming languages to analyze",
    )
    vector_db: VectorDBConfig = Field(
        default_factory=VectorDBConfig, description="Vector database configuration"
    )
    llm: LLMConfig = Field(default_factory=LLMConfig, description="LLM configuration")
    name: Optional[str] = Field(default=None, description="Project name")
    config_path: Optional[str] = Field(
        default=None, description="Path to the configuration file"
    )

    @model_validator(mode="after")
    def check_vector_db_type(self):
        """
        Validates the configuration.
        """
        valid_types = [v.value for v in DocStyle]
        if self.doc_style not in valid_types:
            raise ConfigValidationError(
                f"Unsupported doc_style: {self.doc_style}. Must be one of: {valid_types}"
            )

        is_valid_language = [
            lang for lang in self.languages if lang in LANGUAGE_EXTENSION_MAP.keys()
        ]
        if not is_valid_language:
            raise ConfigValidationError(
                f"Unsupported language: {self.languages}. Must be one of: {LANGUAGE_EXTENSION_MAP.keys()}"
            )
        return self

    @classmethod
    def load(cls, config_path: Optional[str | Path] = None) -> "Config":
        """
        Load configuration from file (JSON or YAML) or use defaults.
        """
        import os

        path = str(config_path) if config_path else None
        if not path:
            # Try to find config in current working directory
            for candidate in [
                "codantix.config.json",
                "codantix.config.yaml",
                "codantix.config.yml",
            ]:
                if os.path.exists(candidate):
                    path = candidate
                    break
        if not path:
            data = {}
            path = None
        else:
            try:
                with open(path, "r") as f:
                    if path.endswith(".yaml") or path.endswith(".yml"):
                        data = yaml.safe_load(f)
                    else:
                        data = json.load(f)
            except FileNotFoundError:
                data = {}
        try:
            obj = cls(**data)
            obj.config_path = path
            return obj
        except ValidationError as e:
            raise ConfigValidationError(str(e))

    def save(self, path: Optional[str] = None, format: str = "json") -> None:
        """
        Save configuration to file.
        """
        save_path = path or self.config_path or "codantix.config.json"
        import enum

        def enum_to_value(obj):
            if isinstance(obj, dict):
                return {k: enum_to_value(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [enum_to_value(i) for i in obj]
            elif isinstance(obj, enum.Enum):
                return obj.value
            return obj

        data = enum_to_value(self.model_dump(exclude={"config_path"}))
        with open(save_path, "w") as f:
            if format.lower() == "yaml":
                yaml.dump(data, f)
            else:
                json.dump(data, f, indent=2)

    # Property accessors for compatibility
    def get_doc_style(self) -> str:
        return (
            self.doc_style.value
            if isinstance(self.doc_style, DocStyle)
            else self.doc_style
        )

    def get_source_paths(self) -> list[str]:
        return self.source_paths

    def get_languages(self) -> list[str]:
        return self.languages

    def get_vector_db_config(self) -> dict:
        return self.vector_db


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
