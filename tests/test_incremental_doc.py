"""
Tests for incremental documentation generation.
"""
import pytest
from pathlib import Path
import git
from codantix.incremental_doc import IncrementalDocumentation, DocumentationChange
from codantix.documentation import CodeElement, ElementType
from codantix.doc_generator import DocStyle
import os

@pytest.fixture
def git_repo(tmp_path):
    """Create a test Git repository."""
    repo = git.Repo.init(tmp_path)
    
    # Create initial files
    (tmp_path / "test.py").write_text('"""Module docstring."""\n\ndef test_function():\n    pass\n')
    (tmp_path / "test.js").write_text('// JavaScript file\nfunction test() {}\n')
    
    # Initial commit
    repo.index.add(['test.py', 'test.js'])
    repo.index.commit('Initial commit')
    
    # Create a new branch
    new_branch = repo.create_head('feature-branch')
    new_branch.checkout()
    
    # Modify files in the new branch
    (tmp_path / "test.py").write_text('"""Updated module docstring."""\n\ndef test_function():\n    """Function docstring."""\n    pass\n')
    (tmp_path / "new_file.py").write_text('"""New module."""\n\ndef new_function():\n    pass\n')
    
    # Commit changes
    repo.index.add(['test.py', 'new_file.py'])
    commit = repo.index.commit('Update documentation')
    
    return tmp_path, commit.hexsha

def test_process_commit(git_repo):
    """Test processing a commit for documentation changes."""
    repo_path, commit_sha = git_repo
    incremental_doc = IncrementalDocumentation(repo_path)
    
    changes = incremental_doc.process_commit(commit_sha)
    assert len(changes) > 0
    
    # Check that we have documentation changes
    for change in changes:
        assert isinstance(change, DocumentationChange)
        assert change.element is not None
        assert change.new_doc is not None
        assert change.change_type in ['new', 'update', 'unchanged']

def test_different_doc_styles(git_repo):
    """Test documentation generation with different styles."""
    repo_path, commit_sha = git_repo
    
    # Test with Google style
    google_doc = IncrementalDocumentation(repo_path, DocStyle.GOOGLE)
    google_changes = google_doc.process_commit(commit_sha)
    assert len(google_changes) > 0
    
    # Test with NumPy style
    numpy_doc = IncrementalDocumentation(repo_path, DocStyle.NUMPY)
    numpy_changes = numpy_doc.process_commit(commit_sha)
    assert len(numpy_changes) > 0
    
    # Test with JSDoc style
    jsdoc_doc = IncrementalDocumentation(repo_path, DocStyle.JSDOC)
    jsdoc_changes = jsdoc_doc.process_commit(commit_sha)
    assert len(jsdoc_changes) > 0

def test_invalid_commit_sha(git_repo):
    """Test handling of invalid commit SHA."""
    repo_path, _ = git_repo
    incremental_doc = IncrementalDocumentation(repo_path)
    
    changes = incremental_doc.process_commit('invalid-sha')
    assert len(changes) == 0

def test_skip_deleted_files(git_repo):
    """Test that deleted files are skipped."""
    repo_path, _ = git_repo
    incremental_doc = IncrementalDocumentation(repo_path)
    
    # Create a commit that deletes a file
    repo = git.Repo(repo_path)
    (repo_path / "to_delete.py").write_text('"""To be deleted."""\n')
    repo.index.add(['to_delete.py'])
    repo.index.commit('Add file to delete')
    
    (repo_path / "to_delete.py").unlink()
    repo.index.remove(['to_delete.py'])
    delete_commit = repo.index.commit('Delete file')
    
    changes = incremental_doc.process_commit(delete_commit.hexsha)
    assert len(changes) == 0  # No documentation changes for deleted files 

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
    (tmp_path / "codantix.config.json").write_text('{"name": "MyProject", "doc_style": "google", "source_paths": ["."], "languages": ["python"], "vector_db": {"type": "chroma", "path": "vecdb/"}, "embedding": "text-embedding-3-large", "provider": "openai", "dimensions": 1024}')
    # Create a dummy repo and commit
    import git
    repo = git.Repo.init(tmp_path)
    (tmp_path / "test.py").write_text('"""Module docstring."""\n\ndef foo():\n    pass\n')
    repo.index.add(['test.py', 'README.md', 'codantix.config.json'])
    commit = repo.index.commit('Initial commit')
    # Ensure config is loaded from tmp_path
    os.chdir(tmp_path)
    # Run incremental doc
    from codantix.incremental_doc import IncrementalDocumentation
    inc = IncrementalDocumentation(tmp_path)
    context = inc._get_project_context(commit.hexsha)
    assert context['name'] == 'MyProject'
    # The description should be 'To test context extraction.'
    assert 'description' in context and context['description'] == 'To test context extraction.'
    assert 'architecture' in context and 'Layered' in context['architecture']
    assert 'purpose' in context and 'context extraction' in context['purpose']

def test_existing_doc_extraction(git_repo):
    """Test that existing documentation is detected and used."""
    repo_path, commit_sha = git_repo
    incremental_doc = IncrementalDocumentation(repo_path)
    changes = incremental_doc.process_commit(commit_sha)
    # Find a function with an existing docstring
    found = False
    for change in changes:
        if change.element.type == ElementType.FUNCTION and change.old_doc:
            assert 'Function docstring' in change.old_doc
            found = True
    assert found, "No function with existing docstring found in changes." 