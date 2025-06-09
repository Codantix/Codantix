import tempfile
import time
from pathlib import Path

import git
import pytest

from codantix.config import Config
from codantix.documentation import CodebaseTraverser
from codantix.embedding import EmbeddingManager
from codantix.incremental_doc import IncrementalDocumentation

from .test_openai_mocks import mock_openai_completion, mock_openai_embedding


@pytest.mark.usefixtures(
    "mock_openai_completion",
    "mock_openai_embedding",
    "mock_embedding_model",
)
def test_codantix_performance():
    """Performance test: measure execution time of codantix operations."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)
        (repo_path / "README.md").write_text("# Sample Project\n\nA test repo.")
        (repo_path / "codantix.config.json").write_text(
            """{
            "doc_style": "google",
            "source_paths": ["."],
            "languages": ["python"],
            "vector_db": {
                "type": "chroma",
                "path": "vecdb/",
                "embedding": "text-embedding-ada-002",
                "provider": "openai",
                "dimensions": 1536
            },
            "llm": {
                "provider": "openai",
                "llm_model": "gpt-4",
                "max_tokens": 1024,
                "temperature": 0.7
            }
        }"""
        )
        (repo_path / "test.py").write_text(
            '"""Module docstring."""\n\n'
            "def foo():\n    pass\n\n"
            "def bar():\n    pass\n"
        )
        # Initialize git repo
        repo = git.Repo.init(repo_path)
        repo.index.add(["README.md", "codantix.config.json", "test.py"])
        repo.index.commit("Initial commit")

        # Run codantix init
        start_time = time.time()
        config = Config.load(repo_path / "codantix.config.json")
        traverser = CodebaseTraverser(config.languages)
        docs = traverser.traverse(repo_path)
        # Create vector DB directory
        vecdb_path = repo_path / "vecdb"
        vecdb_path.mkdir(exist_ok=True)
        emb_mgr = EmbeddingManager(
            config.vector_db.embedding,
            config.vector_db.provider,
            config.vector_db.type,
            config.vector_db.dimensions,
            config.vector_db.collection_name,
            config.vector_db.host,
            config.vector_db.port,
            str(vecdb_path),  # Use absolute path
        )
        # Convert CodeElement objects to expected format
        doc_dicts = []
        for doc in docs:
            # Skip elements with empty docstrings
            if not doc.docstring:
                continue
            metadata = {
                k: v
                for k, v in {
                    "file_path": str(doc.file_path),
                    "element": doc.name,
                    "type": doc.type.value,
                    "line": doc.line_number,
                    "parent": doc.parent,
                }.items()
                if v is not None and isinstance(v, (str, int, float, bool))
            }
            doc_dicts.append({"text": doc.docstring, "metadata": metadata})
        if doc_dicts:  # Only update if we have documents to add
            emb_mgr.update_database(doc_dicts)
        init_time = time.time() - start_time
        print(f"Init time: {init_time:.2f}s")
        assert vecdb_path.exists(), "Vector DB not updated after init"

        # Simulate a PR: modify test.py (update foo docstring)
        (repo_path / "test.py").write_text(
            '"""Module docstring."""\n\n'
            'def foo():\n    """Updated docstring."""\n    pass\n\n'
            "def bar():\n    pass\n"
        )
        repo.index.add(["test.py"])
        commit = repo.index.commit("Update foo docstring")

        # Run codantix doc-pr <sha>
        start_time = time.time()
        inc = IncrementalDocumentation(
            config.name,
            repo_path,
            doc_style=config.doc_style,
            llm_config=config.llm,
        )
        changes = inc.process_commit(commit.hexsha)
        docs = []
        for change in changes:
            if change.change_type in ("new", "update"):
                metadata = {
                    k: v
                    for k, v in {
                        "file_path": str(change.element.file_path),
                        "element": change.element.name,
                        "type": change.element.type.value,
                        "line": change.element.line_number,
                        "parent": change.element.parent,
                    }.items()
                    if v is not None and isinstance(v, (str, int, float, bool))
                }
                docs.append({"text": change.new_doc, "metadata": metadata})
        if docs:
            emb_mgr.update_database(docs)
        doc_pr_time = time.time() - start_time
        print(f"Doc PR time: {doc_pr_time:.2f}s")
        assert vecdb_path.exists(), "Vector DB not updated after doc-pr"

        # Run codantix update-db for completeness
        start_time = time.time()
        docs = traverser.traverse()
        emb_mgr.update_database(docs)
        update_db_time = time.time() - start_time
        print(f"Update DB time: {update_db_time:.2f}s")
        assert vecdb_path.exists(), "Vector DB not updated after update-db"
