"""
Configuration management for Codantix.
"""
import json
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Union
from enum import Enum

class DocStyle(str, Enum):
    """Supported documentation styles."""
    GOOGLE = "google"
    NUMPY = "numpy"
    JSDOC = "jsdoc"

class VectorDBType(str, Enum):
    """Supported vector database types."""
    CHROMA = "chroma"
    PINECONE = "pinecone"

class ConfigValidationError(Exception):
    """Raised when configuration validation fails."""
    pass

class Config:
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or "codantix.config.json"
        self.config: Dict = self._load_config()
        self._validate_config()

    def _load_config(self) -> Dict:
        """Load configuration from file."""
        try:
            with open(self.config_path, 'r') as f:
                if self.config_path.endswith('.yaml') or self.config_path.endswith('.yml'):
                    return yaml.safe_load(f)
                return json.load(f)
        except FileNotFoundError:
            return self._get_default_config()

    def _get_default_config(self) -> Dict:
        """Return default configuration."""
        return {
            "doc_style": DocStyle.GOOGLE.value,
            "source_paths": ["src", "lib", "packages"],
            "languages": ["python", "javascript", "java"],
            "vector_db": {
                "type": VectorDBType.CHROMA.value,
                "path": "vecdb/"
            },
            "embedding": "thenlper/gte-base",
            "provider": "huggingface",
            "dimensions": 512
        }

    def _validate_config(self) -> None:
        """Validate configuration values."""
        # Validate doc_style
        if self.config["doc_style"] not in [style.value for style in DocStyle]:
            raise ConfigValidationError(f"Invalid doc_style: {self.config['doc_style']}")

        # Validate source_paths
        if not isinstance(self.config["source_paths"], list):
            raise ConfigValidationError("source_paths must be a list")
        if not all(isinstance(path, str) for path in self.config["source_paths"]):
            raise ConfigValidationError("All source_paths must be strings")

        # Validate languages
        if not isinstance(self.config["languages"], list):
            raise ConfigValidationError("languages must be a list")
        if not all(isinstance(lang, str) for lang in self.config["languages"]):
            raise ConfigValidationError("All languages must be strings")

        # Validate vector_db
        if not isinstance(self.config["vector_db"], dict):
            raise ConfigValidationError("vector_db must be a dictionary")
        if "type" not in self.config["vector_db"]:
            raise ConfigValidationError("vector_db must have a 'type' field")
        if self.config["vector_db"]["type"] not in [db.value for db in VectorDBType]:
            raise ConfigValidationError(f"Invalid vector_db type: {self.config['vector_db']['type']}")
        if "path" not in self.config["vector_db"]:
            raise ConfigValidationError("vector_db must have a 'path' field")
        if not isinstance(self.config["vector_db"]["path"], str):
            raise ConfigValidationError("vector_db path must be a string")

    def get_doc_style(self) -> str:
        """Get the documentation style."""
        return self.config["doc_style"]

    def get_source_paths(self) -> List[str]:
        """Get the source paths to scan."""
        return self.config["source_paths"]

    def get_languages(self) -> List[str]:
        """Get the supported languages."""
        return self.config["languages"]

    def get_vector_db_config(self) -> Dict:
        """Get the vector database configuration."""
        return self.config["vector_db"]

    def save_config(self, path: Optional[str] = None, format: str = "json") -> None:
        """Save configuration to file."""
        save_path = path or self.config_path
        with open(save_path, 'w') as f:
            if format.lower() == "yaml":
                yaml.dump(self.config, f)
            else:
                json.dump(self.config, f, indent=2) 