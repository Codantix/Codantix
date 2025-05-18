import subprocess
import tempfile
import time
from pathlib import Path
import git
import pytest

@pytest.mark.skip(reason="Integration test is not working, fix huggingface integration first")
def test_codantix_performance_large_codebase():
    """Performance test: run codantix on a large (mock) codebase and report time taken, including deletion of a function."""
    NUM_FILES = 500  # Adjust as needed for your environment
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)
        (repo_path / "README.md").write_text("# Large Project\n\nPerformance test repo.")
        (repo_path / "codantix.config.json").write_text('{"doc_style": "google", "source_paths": ["."], "languages": ["python"], "vector_db": {"type": "chroma", "path": "vecdb/"}, "embedding": "thenlper/gte-small", "provider": "huggingface", "dimensions": 384}')
        # Create many dummy Python files
        for i in range(NUM_FILES):
            (repo_path / f"file_{i}.py").write_text(f'"""Docstring for file {i}"""\n\ndef foo_{i}():\n    pass\n\ndef bar_{i}():\n    pass\n')
        # Initialize git repo
        repo = git.Repo.init(repo_path)
        repo.index.add([str(p.relative_to(repo_path)) for p in repo_path.glob("*.py")] + ["README.md", "codantix.config.json"])
        repo.index.commit("Initial commit")
        # Run codantix init
        start = time.time()
        result = subprocess.run(["codantix", "init"], cwd=repo_path, capture_output=True, text=True)
        elapsed = time.time() - start
        print(f"codantix init on {NUM_FILES} files took {elapsed:.2f} seconds")
        assert result.returncode == 0, f"codantix init failed: {result.stderr}"
        # Simulate a PR: modify one file
        (repo_path / "file_0.py").write_text('"""Docstring for file 0"""\n\ndef foo_0():\n    """Updated docstring."""\n    pass\n\ndef bar_0():\n    pass\n')
        repo.index.add(["file_0.py"])
        commit = repo.index.commit("Update foo_0 docstring")
        # Run codantix doc-pr <sha>
        start = time.time()
        result = subprocess.run(["codantix", "doc-pr", commit.hexsha], cwd=repo_path, capture_output=True, text=True)
        elapsed = time.time() - start
        print(f"codantix doc-pr on 1 file took {elapsed:.2f} seconds")
        assert result.returncode == 0, f"codantix doc-pr failed: {result.stderr}"
        assert (repo_path / "vecdb").exists(), "Vector DB directory not updated after doc-pr."
        # Simulate a PR: delete bar_0 function
        (repo_path / "file_0.py").write_text('"""Docstring for file 0"""\n\ndef foo_0():\n    """Updated docstring."""\n    pass\n')
        repo.index.add(["file_0.py"])
        commit = repo.index.commit("Delete bar_0 function")
        # Run codantix doc-pr <sha> for deletion
        start = time.time()
        result = subprocess.run(["codantix", "doc-pr", commit.hexsha], cwd=repo_path, capture_output=True, text=True)
        elapsed = time.time() - start
        print(f"codantix doc-pr (delete) on 1 file took {elapsed:.2f} seconds")
        assert result.returncode == 0, f"codantix doc-pr (delete) failed: {result.stderr}"
        assert (repo_path / "vecdb").exists(), "Vector DB directory not updated after doc-pr (delete)."
        # Run codantix update-db for completeness
        start = time.time()
        result = subprocess.run(["codantix", "update-db"], cwd=repo_path, capture_output=True, text=True)
        elapsed = time.time() - start
        print(f"codantix update-db on {NUM_FILES} files took {elapsed:.2f} seconds")
        assert result.returncode == 0, f"codantix update-db failed: {result.stderr}"
        assert (repo_path / "vecdb").exists(), "Vector DB directory not updated after update-db." 