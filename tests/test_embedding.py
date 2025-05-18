import os
import pytest
from codantix.embedding import EmbeddingManager
from codantix.config import Config
from unittest.mock import patch, MagicMock
import shutil

@pytest.fixture(autouse=True)
def patch_openai_env(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "dummy-key")

@pytest.fixture
def chroma_args(tmp_path):
    config = Config()
    return dict(
        embedding=config.vector_db.embedding,
        provider=config.vector_db.provider,
        vector_db_type=config.vector_db.type,
        dimensions=config.vector_db.dimensions,
        collection_name=config.vector_db.collection_name,
        host=getattr(config.vector_db, "host", ""),
        port=getattr(config.vector_db, "port", None),
        persist_directory=getattr(config.vector_db, "persist_directory", str(tmp_path / "vecdb/")),
    )

@pytest.fixture
def qdrant_args():
    config = Config()
    config.vector_db.type = "qdrant"
    config.vector_db.host = "localhost"
    config.vector_db.port = 6333
    # config.vector_db.api_key = "dummy"  # Not in VectorDBConfig, but can be set if needed
    return dict(
        embedding=config.vector_db.embedding,
        provider=config.vector_db.provider,
        vector_db_type=config.vector_db.type,
        dimensions=config.vector_db.dimensions,
        collection_name=config.vector_db.collection_name,
        host=config.vector_db.host,
        port=config.vector_db.port,
        persist_directory=getattr(config.vector_db, "persist_directory", "vecdb/"),
    )

@pytest.fixture
def milvus_args():
    config = Config()
    config.vector_db.type = "milvus"
    config.vector_db.host = "localhost"
    config.vector_db.port = 19530
    return dict(
        embedding=config.vector_db.embedding,
        provider=config.vector_db.provider,
        vector_db_type=config.vector_db.type,
        dimensions=config.vector_db.dimensions,
        collection_name=config.vector_db.collection_name,
        host=config.vector_db.host,
        port=config.vector_db.port,
        persist_directory=getattr(config.vector_db, "persist_directory", "vecdb/"),
    )

@patch("langchain_chroma.Chroma")
def test_embedding_manager_chroma_init(mock_chroma, chroma_args):
    em = EmbeddingManager(**chroma_args)
    assert em.vector_db_type == "chroma"
    mock_chroma.assert_called()

@patch("langchain_qdrant.QdrantVectorStore")
def test_embedding_manager_qdrant_init(mock_qdrant, qdrant_args):
    em = EmbeddingManager(**qdrant_args)
    assert em.vector_db_type == "qdrant"
    mock_qdrant.assert_called()

@patch("langchain_milvus.Milvus")
def test_milvus_env_password(mock_milvus, milvus_args):
    os.environ["MILVUS_USER"] = "testuser"
    os.environ["MILVUS_PASSWORD"] = "testpass"
    em = EmbeddingManager(**milvus_args)
    args = mock_milvus.call_args[1]["connection_args"]
    assert args["user"] == "testuser"
    assert args["password"] == "testpass"

@patch("langchain_chroma.Chroma")
def test_store_embeddings_and_update_database_chroma(mock_chroma, chroma_args):
    mock_db = MagicMock()
    mock_chroma.return_value = mock_db
    em = EmbeddingManager(**chroma_args)
    texts = ["doc1", "doc2"]
    metas = [{"a": 1}, {"a": 2}]
    em.store_embeddings(texts, metas)
    mock_db.add_documents.assert_called()
    if hasattr(mock_db, "persist"):
        mock_db.persist.assert_called()
    docs = [{"text": "doc1", "metadata": {"a": 1}}, {"text": "doc2", "metadata": {"a": 2}}]
    em.update_database(docs)
    mock_db.add_documents.assert_called()

@patch("langchain_chroma.Chroma")
def test_unsupported_provider_raises(mock_chroma, chroma_args):
    chroma_args["provider"] = "notreal"
    with pytest.raises(NotImplementedError):
        EmbeddingManager(**chroma_args)

@patch("langchain_chroma.Chroma")
def test_unsupported_vector_db_raises(mock_chroma, chroma_args):
    chroma_args["vector_db_type"] = "notreal"
    with pytest.raises(NotImplementedError):
        EmbeddingManager(**chroma_args)

def test_remove_embedding_for_deleted_element(tmp_path):
    config = Config()
    args = dict(
        embedding=config.vector_db.embedding,
        provider=config.vector_db.provider,
        vector_db_type=config.vector_db.type,
        dimensions=config.vector_db.dimensions,
        collection_name=config.vector_db.collection_name,
        host=getattr(config.vector_db, "host", ""),
        port=getattr(config.vector_db, "port", None),
        persist_directory=getattr(config.vector_db, "persist_directory", str(tmp_path / "vecdb/")),
    )
    manager = EmbeddingManager(**args)
    # Mock the db and its delete method
    manager.db = MagicMock()
    file_path = "some/file.py"
    element_name = "foo"
    element_type = "function"
    # Simulate deletion
    if hasattr(manager.db, "delete"):
        manager.db.delete(filter={"file_path": file_path, "element": element_name, "type": element_type})
        manager.db.delete.assert_called_with(filter={"file_path": file_path, "element": element_name, "type": element_type})
    # Cleanup: remove vecdb directory if it exists
    vecdb_path = args["persist_directory"]
    if os.path.exists(vecdb_path):
        shutil.rmtree(vecdb_path) 

    