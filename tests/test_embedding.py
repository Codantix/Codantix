import os
import pytest
from codantix.embedding import EmbeddingManager
from codantix.config import Config
from unittest.mock import patch, MagicMock

@pytest.fixture(autouse=True)
def patch_openai_env(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "dummy-key")

@pytest.fixture
def chroma_config(tmp_path):
    return Config()

@pytest.fixture
def milvus_lite_config(tmp_path):
    config = Config()
    config.config["vector_db"]["type"] = "milvus_lite"
    config.config["vector_db"]["path"] = str(tmp_path / "vecdb/")
    return config

@pytest.fixture
def qdrant_config():
    config = Config()
    config.config["vector_db"]["type"] = "qdrant"
    config.config["vector_db"]["host"] = "localhost"
    config.config["vector_db"]["port"] = 6333
    config.config["vector_db"]["api_key"] = "dummy"
    return config

@pytest.fixture
def milvus_config():
    config = Config()
    config.config["vector_db"]["type"] = "milvus"
    config.config["vector_db"]["host"] = "localhost"
    config.config["vector_db"]["port"] = 19530
    return config

@patch("codantix.embedding.Chroma")
def test_embedding_manager_chroma_init(mock_chroma, chroma_config):
    em = EmbeddingManager(config=chroma_config)
    assert em.vector_db_type == "chroma"
    mock_chroma.assert_called()

@patch("codantix.embedding.LCMilvusLite")
def test_embedding_manager_milvus_lite_init(mock_milvus_lite, milvus_lite_config):
    em = EmbeddingManager(config=milvus_lite_config)
    assert em.vector_db_type == "milvus_lite"
    mock_milvus_lite.assert_called()

@patch("codantix.embedding.LCQdrant")
def test_embedding_manager_qdrant_init(mock_qdrant, qdrant_config):
    em = EmbeddingManager(config=qdrant_config)
    assert em.vector_db_type == "qdrant"
    mock_qdrant.assert_called()

@patch("codantix.embedding.LCMilvus")
def test_milvus_env_password(mock_milvus, milvus_config):
    os.environ["MILVUS_USER"] = "testuser"
    os.environ["MILVUS_PASSWORD"] = "testpass"
    em = EmbeddingManager(config=milvus_config)
    args = mock_milvus.call_args[1]["connection_args"]
    assert args["user"] == "testuser"
    assert args["password"] == "testpass"

@patch("codantix.embedding.Chroma")
def test_store_embeddings_and_update_database_chroma(mock_chroma, chroma_config):
    mock_db = MagicMock()
    mock_chroma.return_value = mock_db
    em = EmbeddingManager(config=chroma_config)
    texts = ["doc1", "doc2"]
    metas = [{"a": 1}, {"a": 2}]
    em.store_embeddings(texts, metas)
    mock_db.add_documents.assert_called()
    if hasattr(mock_db, "persist"):
        mock_db.persist.assert_called()
    docs = [{"text": "doc1", "metadata": {"a": 1}}, {"text": "doc2", "metadata": {"a": 2}}]
    em.update_database(docs)
    mock_db.add_documents.assert_called()

@patch("codantix.embedding.LCMilvusLite")
def test_store_embeddings_and_update_database_milvus_lite(mock_milvus_lite, milvus_lite_config):
    mock_db = MagicMock()
    mock_milvus_lite.return_value = mock_db
    em = EmbeddingManager(config=milvus_lite_config)
    texts = ["doc1", "doc2"]
    metas = [{"a": 1}, {"a": 2}]
    em.store_embeddings(texts, metas)
    mock_db.add_documents.assert_called()
    if hasattr(mock_db, "persist"):
        mock_db.persist.assert_called()
    docs = [{"text": "doc1", "metadata": {"a": 1}}, {"text": "doc2", "metadata": {"a": 2}}]
    em.update_database(docs)
    mock_db.add_documents.assert_called()

@patch("codantix.embedding.Chroma")
def test_unsupported_provider_raises(mock_chroma, chroma_config):
    chroma_config.config["provider"] = "notreal"
    with pytest.raises(NotImplementedError):
        EmbeddingManager(config=chroma_config)

@patch("codantix.embedding.Chroma")
def test_unsupported_vector_db_raises(mock_chroma, chroma_config):
    chroma_config.config["vector_db"]["type"] = "notreal"
    with pytest.raises(NotImplementedError):
        EmbeddingManager(config=chroma_config) 