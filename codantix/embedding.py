"""
Embedding and vector database management for Codantix.

This module provides the EmbeddingManager class, which handles embedding generation and storage in a vector database using LangChain.
Supports multiple providers (OpenAI, HuggingFace, Google) and vector DBs (Chroma, Qdrant, Milvus, Milvus Lite).
"""
from typing import List, Dict, Any, Optional
from .config import Config
from .utils import _check_pkg

from langchain_core.documents import Document
import os

_check_pkg("langchain_community")

class EmbeddingManager:
    """
    Handles embedding generation and storage in a vector database using LangChain.

    Provider-agnostic: supports OpenAI, HuggingFace, Google (Gemini/Vertex AI), and can be extended.
    Vector DB-agnostic: supports Chroma (local), Qdrant (local/external), Milvus (external), Milvus Lite (embedded/local), and can be extended.
    """
    def __init__(self, embedding: str, provider: str, vector_db_type: str, dimensions: int, 
                 collection_name: str, host: str, port: Optional[int] = None, persist_directory: Optional[str] = "vecdb/"):
        """
        Initialize the EmbeddingManager.

        Args:
            embedding: str, embedding model name
            provider: str, provider name
            vector_db_type: str, vector database type
            dimensions: int, embedding dimensions
            collection_name: str, collection name
            host: str, host name
            port: int, port number
            persist_directory: str, path to the vector database, default is "vecdb/"
        """
        self.embedding_model = embedding
        self.provider = provider
        self.vector_db_type = vector_db_type
        self.dimensions = dimensions
        self.collection_name = collection_name
        self.host = host
        self.port = port
        self.persist_directory = persist_directory
        self.embeddings = self._init_embedding_function()
        self.db = self._init_vector_db()

    def _init_embedding_function(self):
        """
        Initialize the embedding function based on provider and config.

        Returns:
            Embedding function instance compatible with LangChain.

        Raises:
            ImportError: If the required embedding provider is not installed.
            ValueError: If required API keys are not set in the environment.
            NotImplementedError: If the provider is not supported.
        """
        if self.provider == "huggingface":
            _check_pkg("langchain_huggingface")
            from langchain_huggingface import HuggingFaceEmbeddings
            return HuggingFaceEmbeddings(model_name=self.embedding_model)
        elif self.provider == "openai":
            _check_pkg("langchain_openai")
            from langchain_openai import OpenAIEmbeddings
            openai_api_key = os.getenv("OPENAI_API_KEY")
            return OpenAIEmbeddings(model=self.embedding_model, openai_api_key=openai_api_key)
        elif self.provider == "google":
            _check_pkg("langchain_google_genai")
            from langchain_google_genai import GoogleGenerativeAIEmbeddings
            google_api_key = os.getenv("GOOGLE_API_KEY")
            if not google_api_key:
                raise ValueError("GOOGLE_API_KEY environment variable not set.")
            return GoogleGenerativeAIEmbeddings(model=self.embedding_model, google_api_key=google_api_key)
        else:
            raise NotImplementedError(f"Provider '{self.provider}' not yet supported.")

    def _init_vector_db(self):
        """
        Initialize the vector database based on config.

        Returns:
            Vector database instance compatible with LangChain.

        Raises:
            ImportError: If the required vector DB provider is not installed.
            NotImplementedError: If the vector DB type is not supported.
        """
        if self.vector_db_type == "chroma":
            _check_pkg("langchain_chroma.vectorstores")
            from langchain_chroma import Chroma
            return Chroma(
                persist_directory=self.persist_directory,
                embedding_function=self.embeddings,
                collection_name=self.collection_name
            )
        elif self.vector_db_type == "qdrant":
            from qdrant_client import QdrantClient
            from langchain_qdrant import QdrantVectorStore

            if self.persist_directory:
                # Local Qdrant (file-based)
                client = QdrantClient(path=self.persist_directory)
            else:
                # Cloud/remote Qdrant
                client = QdrantClient(
                    host=self.host,
                    port=self.port,
                    api_key=os.getenv("QDRANT_API_KEY"),
                )

            return QdrantVectorStore(
                client=client,
                collection_name=self.collection_name,
                embedding=self.embeddings,
            )
        elif self.vector_db_type == "milvus":
            _check_pkg("langchain_milvus")
            from langchain_milvus import Milvus
            return Milvus(
                embedding_function=self.embeddings,
                collection_name=self.collection_name,
                connection_args={
                    "host": self.host,
                    "port": self.port,
                    "user": os.getenv("MILVUS_USER"),
                    "password": os.getenv("MILVUS_PASSWORD"),
                    "uri": f"http://{self.host}:{self.port}",
                },
            )
        else:
            raise NotImplementedError(f"Vector DB type '{self.vector_db_type}' not yet supported.")

    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a list of texts using the configured model/provider.

        Args:
            texts (List[str]): List of text strings to embed.

        Returns:
            List[List[float]]: List of embedding vectors.
        """
        return self.embeddings.embed_documents(texts)

    def store_embeddings(self, texts: List[str], metadatas: List[Dict[str, Any]]):
        """
        Store texts and their metadata in the configured vector database.

        Args:
            texts (List[str]): List of text strings to store.
            metadatas (List[Dict[str, Any]]): List of metadata dictionaries for each text.
        """
        docs = [Document(page_content=text, metadata=meta) for text, meta in zip(texts, metadatas)]
        self.db.add_documents(docs)
        if hasattr(self.db, "persist"):
            self.db.persist()

    def update_database(self, docs: List[Dict[str, Any]]):
        """
        Generate and store embeddings for a batch of documentation entries.

        Args:
            docs (List[Dict[str, Any]]): List of documentation entries, each with a 'text' field and metadata.
        """
        texts = [doc["text"] for doc in docs]
        metadatas = [doc.get("metadata", {}) for doc in docs]
        self.store_embeddings(texts, metadatas) 