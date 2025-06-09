"""
Tests for incremental documentation generation.
"""

import os

import git
import pytest

from codantix.config import ElementType, LLMConfig
from codantix.doc_generator import DocStyle
from codantix.incremental_doc import DocumentationChange, IncrementalDocumentation

pytestmark = pytest.mark.usefixtures("patch_llm")


@pytest.fixture
def git_repo(tmp_path):
    """Create a test Git repository."""
    repo = git.Repo.init(tmp_path)

    # Create initial files
    (tmp_path / "test.py").write_text(
        '"""Module docstring."""\n\ndef test_function():\n    pass\n'
    )
    (tmp_path / "test.js").write_text("// JavaScript file\nfunction test() {}\n")

    # Initial commit
    repo.index.add(["test.py", "test.js"])
    repo.index.commit("Initial commit")

    # Create a new branch
    new_branch = repo.create_head("feature-branch")
    new_branch.checkout()

    # Modify files in the new branch
    (tmp_path / "test.py").write_text(
        '"""Updated module docstring."""\n\ndef test_function():\n    """Function docstring."""\n    pass\n'
    )
    (tmp_path / "new_file.py").write_text(
        '"""New module."""\n\ndef new_function():\n    pass\n'
    )

    # Commit changes
    repo.index.add(["test.py", "new_file.py"])
    commit = repo.index.commit("Update documentation")

    return tmp_path, commit.hexsha


@pytest.mark.usefixtures("patch_llm")
def test_process_commit(git_repo):
    """Test processing a commit for documentation changes."""
    repo_path, commit_sha = git_repo
    llm_config = LLMConfig(provider="openai", llm_model="gpt-4")
    incremental_doc = IncrementalDocumentation("test", repo_path, llm_config=llm_config)

    changes = incremental_doc.process_commit(commit_sha)
    assert len(changes) > 0

    # Check that we have documentation changes
    for change in changes:
        assert isinstance(change, DocumentationChange)
        assert change.element is not None
        assert change.new_doc is not None
        assert change.change_type in ["new", "update", "unchanged"]


@pytest.mark.usefixtures("patch_llm")
def test_incremental_doc_constructor_defaults(git_repo):
    repo_path, _ = git_repo
    llm_config = LLMConfig(provider="openai", llm_model="gpt-4")
    inc = IncrementalDocumentation("test", repo_path, llm_config=llm_config)
    assert inc.repo_path == repo_path
    assert inc.doc_generator.doc_style == DocStyle.GOOGLE
    assert inc.doc_generator.llm_config == llm_config


@pytest.mark.usefixtures("patch_llm")
def test_incremental_doc_constructor_doc_style(git_repo):
    repo_path, _ = git_repo
    llm_config = LLMConfig(provider="openai", llm_model="gpt-4")
    inc = IncrementalDocumentation(
        "test", repo_path, doc_style=DocStyle.NUMPY, llm_config=llm_config
    )
    assert inc.doc_generator.doc_style == DocStyle.NUMPY


@pytest.mark.usefixtures("patch_llm")
def test_incremental_doc_constructor_llm_config(git_repo):
    from codantix.config import LLMConfig

    repo_path, _ = git_repo
    llm = LLMConfig(provider="openai", llm_model="gpt-4o-mini", max_tokens=2048)
    inc = IncrementalDocumentation(
        "test", repo_path, doc_style=DocStyle.JSDOC, llm_config=llm
    )
    assert inc.doc_generator.doc_style == DocStyle.JSDOC
    assert inc.doc_generator.llm_config == llm


@pytest.mark.usefixtures("patch_llm")
def test_incremental_doc_constructor_invalid_doc_style(git_repo):
    repo_path, _ = git_repo
    with pytest.raises(Exception):
        IncrementalDocumentation("test", repo_path, doc_style="not_a_style")


@pytest.mark.usefixtures("patch_llm")
def test_different_doc_styles(git_repo):
    """Test documentation generation with different styles."""
    repo_path, commit_sha = git_repo
    llm_config = LLMConfig(provider="openai", llm_model="gpt-4")

    # Test with Google style
    google_doc = IncrementalDocumentation(
        "test", repo_path, doc_style=DocStyle.GOOGLE, llm_config=llm_config
    )
    google_changes = google_doc.process_commit(commit_sha)
    assert len(google_changes) > 0

    # Test with NumPy style
    numpy_doc = IncrementalDocumentation(
        "test", repo_path, doc_style=DocStyle.NUMPY, llm_config=llm_config
    )
    numpy_changes = numpy_doc.process_commit(commit_sha)
    assert len(numpy_changes) > 0

    # Test with JSDoc style
    jsdoc_doc = IncrementalDocumentation(
        "test", repo_path, doc_style=DocStyle.JSDOC, llm_config=llm_config
    )
    jsdoc_changes = jsdoc_doc.process_commit(commit_sha)
    assert len(jsdoc_changes) > 0


@pytest.mark.usefixtures("patch_llm")
def test_invalid_commit_sha(git_repo):
    """Test handling of invalid commit SHA."""
    repo_path, _ = git_repo
    llm_config = LLMConfig(provider="openai", llm_model="gpt-4")
    incremental_doc = IncrementalDocumentation("test", repo_path, llm_config=llm_config)

    changes = incremental_doc.process_commit("invalid-sha")
    assert len(changes) == 0


@pytest.mark.usefixtures("patch_llm")
def test_skip_deleted_files(git_repo):
    """Test that deleted files are skipped."""
    repo_path, _ = git_repo
    llm_config = LLMConfig(provider="openai", llm_model="gpt-4")
    incremental_doc = IncrementalDocumentation("test", repo_path, llm_config=llm_config)

    # Create a commit that deletes a file
    repo = git.Repo(repo_path)
    (repo_path / "to_delete.py").write_text('"""To be deleted."""\n')
    repo.index.add(["to_delete.py"])
    repo.index.commit("Add file to delete")

    (repo_path / "to_delete.py").unlink()
    repo.index.remove(["to_delete.py"])
    delete_commit = repo.index.commit("Delete file")

    changes = incremental_doc.process_commit(delete_commit.hexsha)
    assert len(changes) == 0  # No documentation changes for deleted files


@pytest.mark.usefixtures("patch_llm")
def test_project_context_extraction(tmp_path):
    """Test that project context is extracted from README.md and config."""
    # Write a README.md with context
    readme_content = (
        "# MyProject\n\n"
        "This is a test project.\n\n"
        "## Architecture\n\nLayered architecture.\n\n"
        "## Purpose\n\nTo test context extraction.\n"
    )
    (tmp_path / "README.md").write_text(readme_content)
    # Write a config file with a project name
    (tmp_path / "codantix.config.json").write_text(
        '{"name": "MyProject", "doc_style": "google", "source_paths": ["."], "languages": ["python"], "vector_db": {"type": "chroma", "path": "vecdb/"}, "embedding": "text-embedding-3-large", "provider": "openai", "dimensions": 1024}'
    )
    # Create a dummy repo and commit
    import git

    repo = git.Repo.init(tmp_path)
    (tmp_path / "test.py").write_text(
        '"""Module docstring."""\n\ndef foo():\n    pass\n'
    )
    repo.index.add(["test.py", "README.md", "codantix.config.json"])
    commit = repo.index.commit("Initial commit")
    os.chdir(tmp_path)
    from codantix.incremental_doc import IncrementalDocumentation

    llm_config = LLMConfig(provider="openai", llm_model="gpt-4")
    inc = IncrementalDocumentation("MyProject", tmp_path, llm_config=llm_config)
    context = inc._get_project_context(commit.hexsha)
    assert context["name"] == "MyProject"
    assert (
        "description" in context
        and context["description"] == "To test context extraction."
    )
    assert "architecture" in context and "Layered" in context["architecture"]
    assert "purpose" in context and "context extraction" in context["purpose"]


@pytest.mark.usefixtures("patch_llm")
def test_existing_doc_extraction(git_repo):
    """Test that existing documentation is detected and used."""
    repo_path, commit_sha = git_repo
    llm_config = LLMConfig(provider="openai", llm_model="gpt-4")
    incremental_doc = IncrementalDocumentation("test", repo_path, llm_config=llm_config)
    changes = incremental_doc.process_commit(commit_sha)
    # Find a function with an existing docstring
    found = False
    for change in changes:
        if change.element.type == ElementType.FUNCTION and change.old_doc:
            assert "Function docstring" in change.old_doc
            found = True
    assert found, "No function with existing docstring found in changes."
