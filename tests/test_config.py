"""
Tests for configuration management.
"""

import json

import pytest
import yaml
from pydantic import ValidationError

from codantix.config import (
    Config,
    ConfigValidationError,
    DocStyle,
    LLMConfig,
    VectorDBConfig,
    VectorDBType,
)


@pytest.fixture
def temp_config_file(tmp_path):
    """Create a temporary config file for testing."""
    config = {
        "doc_style": "google",
        "source_paths": ["src", "lib"],
        "languages": ["python", "javascript"],
        "vector_db": {
            "type": "chroma",
            "path": "vecdb/",
            "embedding": "text-embedding-3-large",
            "provider": "openai",
            "dimensions": 1024,
        },
    }
    config_file = tmp_path / "test_config.json"
    with open(config_file, "w") as f:
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
            "path": "vecdb/",
            "embedding": "text-embedding-3-large",
            "dimensions": 1024,
            "collection_name": "codantix_docs",
            "host": "localhost",
            "port": 8000,
            "persist_directory": "vecdb/",
            "provider": "openai",
        },
        "llm": {
            "provider": "openai",
            "llm_model": "gpt-4o-mini",
            "max_tokens": 1024,
            "temperature": 0.7,
            "top_p": 1.0,
            "top_k": 10,
            "stop_sequences": ["\n\n"],
            "rate_limit": {
                "llm_requests_per_second": 10,
                "llm_check_every_n_seconds": 1,
                "llm_max_bucket_size": 10,
            },
        },
    }
    config_file = tmp_path / "test_config.yaml"
    with open(config_file, "w") as f:
        yaml.dump(config, f)
    return config_file


def test_config_loads_default_when_file_not_found():
    """Test that default config is loaded when file doesn't exist."""
    config = Config.load("nonexistent.json")
    assert config.doc_style == DocStyle.GOOGLE
    assert "src" in config.source_paths
    assert "python" in config.languages


def test_config_loads_from_json_file(temp_config_file):
    """Test that config loads correctly from JSON file."""
    config = Config.load(str(temp_config_file))
    assert config.doc_style == DocStyle.GOOGLE
    assert config.source_paths == ["src", "lib"]
    assert config.languages == ["python", "javascript"]


def test_config_loads_from_yaml_file(temp_yaml_config_file):
    """Test that config loads correctly from YAML file."""
    config = Config.load(str(temp_yaml_config_file))
    assert config.doc_style == DocStyle.GOOGLE
    assert config.source_paths == ["src", "lib"]
    assert config.languages == ["python", "javascript"]


def test_config_loads_from_path_object(temp_config_file):
    """Test that config loads correctly from Path object."""
    config = Config.load(temp_config_file)
    assert config.doc_style == DocStyle.GOOGLE
    assert config.source_paths == ["src", "lib"]
    assert config.languages == ["python", "javascript"]


def test_config_validation():
    """Test configuration validation."""
    config = Config()
    # Test valid config
    assert config.doc_style in [DocStyle.GOOGLE, DocStyle.NUMPY, DocStyle.JSDOC]
    assert all(isinstance(path, str) for path in config.source_paths)
    assert all(isinstance(lang, str) for lang in config.languages)

    # Test vector db config
    vector_db_config = config.vector_db
    assert hasattr(vector_db_config, "type")
    assert hasattr(vector_db_config, "path")
    assert vector_db_config.type in [
        VectorDBType.CHROMA,
        VectorDBType.QDRANT,
        VectorDBType.MILVUS,
        VectorDBType.MILVUS_LITE,
    ]


def test_invalid_doc_style():
    """Test validation of invalid doc style."""
    # Should raise ValidationError on load
    bad = {"doc_style": "invalid_style"}
    with pytest.raises(Exception):
        Config(**bad)


def test_invalid_vector_db_type():
    """Test validation of invalid vector db type."""
    bad = {"vector_db": {"type": "invalid_db", "path": "vecdb/"}}
    with pytest.raises(ValidationError):
        Config(**bad)


def test_invalid_source_paths():
    """Test validation of invalid source paths."""
    bad = {"source_paths": "not_a_list"}
    with pytest.raises(ValidationError):
        Config(**bad)


def test_save_config_json(tmp_path):
    """Test saving config to JSON file."""
    config = Config()
    save_path = tmp_path / "saved_config.json"
    config.save(str(save_path))
    assert save_path.exists()
    with open(save_path) as f:
        saved_config = json.load(f)
    # Only check a few fields for round-trip
    assert saved_config["doc_style"] == config.doc_style
    assert saved_config["source_paths"] == config.source_paths


def test_save_config_yaml(tmp_path):
    """Test saving config to YAML file."""
    config = Config()
    save_path = tmp_path / "saved_config.yaml"
    config.save(str(save_path), format="yaml")
    assert save_path.exists()
    with open(save_path) as f:
        saved_config = yaml.safe_load(f)
    assert saved_config["doc_style"] == config.doc_style
    assert saved_config["source_paths"] == config.source_paths


def test_config_constructor_all_args():
    llm = LLMConfig(provider="openai", llm_model="gpt-4o-mini", max_tokens=2048)
    vector_db = VectorDBConfig(
        type="qdrant",
        path="/tmp/vecdb",
        provider="openai",
        embedding="text-embedding-ada-002",
        dimensions=1536,
    )
    config = Config(
        doc_style=DocStyle.NUMPY,
        source_paths=["src", "lib"],
        languages=["python", "javascript"],
        vector_db=vector_db,
        llm=llm,
        name="TestProject",
    )
    assert config.doc_style == DocStyle.NUMPY
    assert config.source_paths == ["src", "lib"]
    assert config.languages == ["python", "javascript"]
    assert config.vector_db == vector_db
    assert config.llm == llm
    assert config.name == "TestProject"


def test_config_constructor_partial_args():
    config = Config(doc_style=DocStyle.JSDOC)
    assert config.doc_style == DocStyle.JSDOC
    # Defaults for others
    assert config.source_paths == ["src"]
    assert "python" in config.languages
    assert config.vector_db is not None
    assert config.llm is not None
    assert config.name is None


def test_config_constructor_defaults():
    config = Config()
    assert config.doc_style == DocStyle.GOOGLE
    assert config.source_paths == ["src"]
    assert "python" in config.languages
    assert config.vector_db is not None
    assert config.llm is not None
    assert config.name is None


def test_config_constructor_invalid_types():
    # doc_style invalid
    with pytest.raises(Exception):
        Config(doc_style=123)
    # source_paths not a list
    with pytest.raises(Exception):
        Config(source_paths="notalist")
    # languages not a list
    with pytest.raises(Exception):
        Config(languages="python")
    # vector_db wrong type
    with pytest.raises(Exception):
        Config(vector_db="notadict")
    # llm wrong type
    with pytest.raises(Exception):
        Config(llm="notadict")


def test_config_property_accessors():
    config = Config(
        doc_style=DocStyle.NUMPY, source_paths=["foo"], languages=["python"]
    )
    assert config.get_doc_style() == "numpy"
    assert config.get_source_paths() == ["foo"]
    assert config.get_languages() == ["python"]
    assert config.get_vector_db_config() == config.vector_db


def test_config_round_trip_dict_equivalence():
    d = {
        "doc_style": "google",
        "source_paths": ["src", "lib"],
        "languages": ["python", "javascript"],
        "vector_db": {
            "type": "chroma",
            "path": "vecdb/",
            "embedding": "text-embedding-3-large",
            "provider": "openai",
            "dimensions": 1024,
        },
        "llm": {
            "provider": "openai",
            "llm_model": "gpt-4o-mini",
            "max_tokens": 1024,
            "temperature": 0.7,
            "top_p": 1.0,
            "top_k": 10,
            "stop_sequences": ["\n\n"],
            "rate_limit": {
                "llm_requests_per_second": 10,
                "llm_check_every_n_seconds": 1,
                "llm_max_bucket_size": 10,
            },
        },
        "name": "RoundTrip",
    }
    config = Config(**d)
    d2 = config.dict()
    for k in ["doc_style", "source_paths", "languages", "name"]:
        assert d2[k] == d[k]
    # vector_db and llm are objects, check their dicts
    for k in d["vector_db"]:
        assert getattr(config.vector_db, k) == d["vector_db"][k]
    for k in d["llm"]:
        if k == "rate_limit":
            for rk in d["llm"]["rate_limit"]:
                assert getattr(config.llm.rate_limit, rk) == d["llm"]["rate_limit"][rk]
        else:
            assert getattr(config.llm, k) == d["llm"][k]
