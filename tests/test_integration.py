import subprocess
import tempfile
import shutil
import os
from pathlib import Path
import git
from codantix.config import Config


def test_codantix_end_to_end():
    """Integration test: run codantix CLI commands on a sample repo and simulate a PR, including deletion of a function."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)
        (repo_path / "README.md").write_text("# Sample Project\n\nA test repo.")
        (repo_path / "codantix.config.json").write_text('{"doc_style": "google", "source_paths": ["."], "languages": ["python"], "vector_db": {"type": "chroma", "path": "vecdb/"}, "embedding": "thenlper/gte-small", "provider": "huggingface", "dimensions": 384}')
        (repo_path / "test.py").write_text('"""Module docstring."""\n\ndef foo():\n    pass\n\ndef bar():\n    pass\n')
        # Initialize git repo
        repo = git.Repo.init(repo_path)
        repo.index.add(["README.md", "codantix.config.json", "test.py"])
        repo.index.commit("Initial commit")
        # Run codantix init
        result = subprocess.run(["codantix", "init"], cwd=repo_path, capture_output=True, text=True)
        assert result.returncode == 0, f"codantix init failed: {result.stderr}"
        # Simulate a PR: modify test.py (update foo docstring)
        (repo_path / "test.py").write_text('"""Module docstring."""\n\ndef foo():\n    """Updated docstring."""\n    pass\n\ndef bar():\n    pass\n')
        repo.index.add(["test.py"])
        commit = repo.index.commit("Update foo docstring")
        # Run codantix doc-pr <sha>
        result = subprocess.run(["codantix", "doc-pr", commit.hexsha], cwd=repo_path, capture_output=True, text=True)
        assert result.returncode == 0, f"codantix doc-pr failed: {result.stderr}"
        assert (repo_path / "vecdb").exists(), "Vector DB directory not updated after doc-pr."
        # Simulate a PR: delete bar function
        (repo_path / "test.py").write_text('"""Module docstring."""\n\ndef foo():\n    """Updated docstring."""\n    pass\n')
        repo.index.add(["test.py"])
        commit = repo.index.commit("Delete bar function")
        # Run codantix doc-pr <sha> for deletion
        result = subprocess.run(["codantix", "doc-pr", commit.hexsha], cwd=repo_path, capture_output=True, text=True)
        assert result.returncode == 0, f"codantix doc-pr (delete) failed: {result.stderr}"
        assert (repo_path / "vecdb").exists(), "Vector DB directory not updated after doc-pr (delete)."
        # Run codantix update-db for completeness
        result = subprocess.run(["codantix", "update-db"], cwd=repo_path, capture_output=True, text=True)
        assert result.returncode == 0, f"codantix update-db failed: {result.stderr}"
        assert (repo_path / "vecdb").exists(), "Vector DB directory not updated after update-db." 