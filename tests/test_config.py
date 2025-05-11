"""
Tests for configuration management.
"""
import json
import yaml
import pytest
from pathlib import Path
from codantix.config import Config, ConfigValidationError, DocStyle, VectorDBType

@pytest.fixture
def temp_config_file(tmp_path):
    """Create a temporary config file for testing."""
    config = {
        "doc_style": "google",
        "source_paths": ["src", "lib"],
        "languages": ["python", "javascript"],
        "vector_db": {
            "type": "chroma",
            "path": "vecdb/"
        },
        "embedding": "text-embedding-3-large",
        "provider": "openai",
        "dimensions": 1024
    }
    config_file = tmp_path / "test_config.json"
    with open(config_file, 'w') as f:
        json.dump(config, f)
    return config_file

@pytest.fixture
def temp_yaml_config_file(tmp_path):
    """Create a temporary YAML config file for testing."""
    config = {
        "doc_style": "google",
        "source_paths": ["src", "lib"],
        "languages": ["python", "javascript"],
        "vector_db": {
            "type": "chroma",
            "path": "vecdb/"
        },
        "embedding": "text-embedding-3-large",
        "provider": "openai",
        "dimensions": 1024
    }
    config_file = tmp_path / "test_config.yaml"
    with open(config_file, 'w') as f:
        yaml.dump(config, f)
    return config_file

def test_config_loads_default_when_file_not_found():
    """Test that default config is loaded when file doesn't exist."""
    config = Config("nonexistent.json")
    assert config.get_doc_style() == DocStyle.GOOGLE.value
    assert "src" in config.get_source_paths()
    assert "python" in config.get_languages()

def test_config_loads_from_json_file(temp_config_file):
    """Test that config loads correctly from JSON file."""
    config = Config(str(temp_config_file))
    assert config.get_doc_style() == DocStyle.GOOGLE.value
    assert config.get_source_paths() == ["src", "lib"]
    assert config.get_languages() == ["python", "javascript"]

def test_config_loads_from_yaml_file(temp_yaml_config_file):
    """Test that config loads correctly from YAML file."""
    config = Config(str(temp_yaml_config_file))
    assert config.get_doc_style() == DocStyle.GOOGLE.value
    assert config.get_source_paths() == ["src", "lib"]
    assert config.get_languages() == ["python", "javascript"]

def test_config_validation():
    """Test configuration validation."""
    config = Config()
    # Test valid config
    assert config.get_doc_style() in [style.value for style in DocStyle]
    assert all(isinstance(path, str) for path in config.get_source_paths())
    assert all(isinstance(lang, str) for lang in config.get_languages())
    
    # Test vector db config
    vector_db_config = config.get_vector_db_config()
    assert "type" in vector_db_config
    assert "path" in vector_db_config
    assert vector_db_config["type"] in [db.value for db in VectorDBType]

def test_invalid_doc_style():
    """Test validation of invalid doc style."""
    config = Config()
    config.config["doc_style"] = "invalid_style"
    with pytest.raises(ConfigValidationError):
        config._validate_config()

def test_invalid_vector_db_type():
    """Test validation of invalid vector db type."""
    config = Config()
    config.config["vector_db"]["type"] = "invalid_db"
    with pytest.raises(ConfigValidationError):
        config._validate_config()

def test_invalid_source_paths():
    """Test validation of invalid source paths."""
    config = Config()
    config.config["source_paths"] = "not_a_list"
    with pytest.raises(ConfigValidationError):
        config._validate_config()

def test_save_config_json(tmp_path):
    """Test saving config to JSON file."""
    config = Config()
    save_path = tmp_path / "saved_config.json"
    config.save_config(str(save_path))
    assert save_path.exists()
    with open(save_path) as f:
        saved_config = json.load(f)
    assert saved_config == config.config

def test_save_config_yaml(tmp_path):
    """Test saving config to YAML file."""
    config = Config()
    save_path = tmp_path / "saved_config.yaml"
    config.save_config(str(save_path), format="yaml")
    assert save_path.exists()
    with open(save_path) as f:
        saved_config = yaml.safe_load(f)
    assert saved_config == config.config 