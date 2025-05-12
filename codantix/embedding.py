"""
Embedding and vector database management for Codantix.
"""
from typing import List, Dict, Any, Optional
from pathlib import Path
from .config import Config

# LangChain imports

from langchain_chroma import Chroma
from langchain_core.documents import Document
import os

try:
    from langchain_openai import OpenAIEmbeddings
except ImportError:
    OpenAIEmbeddings = None

try:
    from langchain_huggingface import HuggingFaceEmbeddings
except ImportError:
    HuggingFaceEmbeddings = None

try:
    from langchain_google_genai import GoogleGenerativeAIEmbeddings
except ImportError:
    GoogleGenerativeAIEmbeddings = None

try:
    from langchain_community.vectorstores import Qdrant as LCQdrant
except ImportError:
    LCQdrant = None

try:
    from langchain_community.vectorstores import Milvus as LCMilvus
except ImportError:
    LCMilvus = None

try:
    from langchain_community.vectorstores import MilvusLite as LCMilvusLite
except ImportError:
    LCMilvusLite = None

class EmbeddingManager:
    """
    Handles embedding generation and storage in a vector database using LangChain.
    Provider-agnostic: supports OpenAI, HuggingFace, Google (Gemini/Vertex AI), and can be extended.
    Vector DB-agnostic: supports Chroma (local), Qdrant (local/external), Milvus (external), Milvus Lite (embedded/local), and can be extended.
    """
    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config()
        self.embedding_model = self.config.config.get("embedding", "text-embedding-3-large")
        self.provider = self.config.config.get("provider", "openai")
        self.vector_db_config = self.config.get_vector_db_config()
        self.vector_db_type = self.vector_db_config.get("type", "chroma")
        self.dimensions = self.config.config.get("dimensions", 1024)
        self.persist_directory = self.vector_db_config.get("path", "vecdb/")
        self.collection_name = self.vector_db_config.get("collection", "codantix_docs")
        self.embeddings = self._init_embedding_function()
        self.db = self._init_vector_db()

    def _init_embedding_function(self):
        """
        Initialize the embedding function based on provider and config.
        """
        if self.provider == "huggingface":
            if HuggingFaceEmbeddings is None:
                raise ImportError("langchain_community.embeddings.HuggingFaceEmbeddings is not installed.")
            return HuggingFaceEmbeddings(model_name=self.embedding_model)
        elif self.provider == "openai":
            if OpenAIEmbeddings is None:
                raise ValueError("OPENAI_API_KEY environment variable not set.")
            openai_api_key = os.getenv("OPENAI_API_KEY")
            return OpenAIEmbeddings(model=self.embedding_model, openai_api_key=openai_api_key)
        elif self.provider == "google":
            if GoogleGenerativeAIEmbeddings is None:
                raise ImportError("langchain_google_genai.GoogleGenerativeAIEmbeddings is not installed.")
            google_api_key = os.getenv("GOOGLE_API_KEY")
            if not google_api_key:
                raise ValueError("GOOGLE_API_KEY environment variable not set.")
            return GoogleGenerativeAIEmbeddings(model=self.embedding_model, google_api_key=google_api_key)
        else:
            raise NotImplementedError(f"Provider '{self.provider}' not yet supported.")

    def _init_vector_db(self):
        """
        Initialize the vector database based on config. Supports Chroma (local), Qdrant (local/external), Milvus (external), Milvus Lite (embedded/local).
        Extend this method to add more vector DBs.
        """
        if self.vector_db_type == "chroma":
            return Chroma(
                persist_directory=self.persist_directory,
                embedding_function=self.embeddings,
                collection_name=self.collection_name
            )
        elif self.vector_db_type == "qdrant":
            if LCQdrant is None:
                raise ImportError("langchain_community.vectorstores.Qdrant is not installed.")
            # Qdrant config: host, port, api_key, collection_name
            host = self.vector_db_config.get("host", "localhost")
            port = self.vector_db_config.get("port", 6333)
            api_key = self.vector_db_config.get("api_key")
            url = f"http://{host}:{port}"
            return LCQdrant(
                collection_name=self.collection_name,
                url=url,
                api_key=api_key,
                embedding_function=self.embeddings,
            )
        elif self.vector_db_type == "milvus":
            if LCMilvus is None:
                raise ImportError("langchain_community.vectorstores.Milvus is not installed.")
            # Milvus config: host, port, collection_name, etc. User/password always from env
            host = self.vector_db_config.get("host", "localhost")
            port = self.vector_db_config.get("port", 19530)
            user = os.getenv("MILVUS_USER")
            password = os.getenv("MILVUS_PASSWORD")
            uri = f"http://{host}:{port}"
            # Document: user/password must be set in env as MILVUS_USER/MILVUS_PASSWORD
            return LCMilvus(
                embedding_function=self.embeddings,
                collection_name=self.collection_name,
                connection_args={
                    "host": host,
                    "port": port,
                    "user": user,
                    "password": password,
                    "uri": uri,
                },
            )
        elif self.vector_db_type == "milvus_lite":
            if LCMilvusLite is None:
                raise ImportError("langchain_community.vectorstores.MilvusLite is not installed.")
            # Milvus Lite config: persist_directory, collection_name, etc.
            persist_dir = self.vector_db_config.get("path", "vecdb/")
            return LCMilvusLite(
                embedding_function=self.embeddings,
                collection_name=self.collection_name,
                persist_directory=persist_dir,
            )
        else:
            raise NotImplementedError(f"Vector DB type '{self.vector_db_type}' not yet supported.")

    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a list of texts using the configured model/provider.
        """
        return self.embeddings.embed_documents(texts)

    def store_embeddings(self, texts: List[str], metadatas: List[Dict[str, Any]]):
        """
        Store texts and their metadata in the configured vector database.
        """
        docs = [Document(page_content=text, metadata=meta) for text, meta in zip(texts, metadatas)]
        self.db.add_documents(docs)
        # Only persist if the DB supports it (e.g., Chroma, Milvus Lite)
        if hasattr(self.db, "persist"):
            self.db.persist()

    def update_database(self, docs: List[Dict[str, Any]]):
        """
        Generate and store embeddings for a batch of documentation entries.
        Each doc should have at least a 'text' field and metadata.
        """
        texts = [doc["text"] for doc in docs]
        metadatas = [doc.get("metadata", {}) for doc in docs]
        self.store_embeddings(texts, metadatas) 