"""
Tests for Git integration functionality.
"""
import pytest
from pathlib import Path
import git
from codantix.git_integration import GitIntegration, FileChange

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

def test_get_changed_files(git_repo):
    """Test getting changed files from a commit."""
    repo_path, commit_sha = git_repo
    git_integration = GitIntegration(repo_path)
    
    changes = git_integration.get_changed_files(commit_sha)
    assert len(changes) == 2
    
    # Check modified file
    modified_file = next(c for c in changes if c.file_path.name == 'test.py')
    assert modified_file.change_type == 'M'
    assert modified_file.diff  # Ensure diff is not empty
    assert len(modified_file.hunks) > 0
    
    # Check new file
    new_file = next(c for c in changes if c.file_path.name == 'new_file.py')
    assert new_file.change_type == 'A'
    assert new_file.diff  # Ensure diff is not empty
    assert len(new_file.hunks) > 0

def test_get_file_content(git_repo):
    """Test getting file content at a specific commit."""
    repo_path, commit_sha = git_repo
    git_integration = GitIntegration(repo_path)
    
    content = git_integration.get_file_content(Path('test.py'), commit_sha)
    assert content is not None
    assert 'Updated module docstring' in content
    assert 'Function docstring' in content

def test_get_commit_message(git_repo):
    """Test getting commit message."""
    repo_path, commit_sha = git_repo
    git_integration = GitIntegration(repo_path)
    
    message = git_integration.get_commit_message(commit_sha)
    assert message == 'Update documentation'

def test_get_branch_name(git_repo):
    """Test getting branch name."""
    repo_path, commit_sha = git_repo
    git_integration = GitIntegration(repo_path)
    
    branch_name = git_integration.get_branch_name(commit_sha)
    assert branch_name == 'feature-branch'

def test_invalid_commit_sha(git_repo):
    """Test handling of invalid commit SHA."""
    repo_path, _ = git_repo
    git_integration = GitIntegration(repo_path)
    
    changes = git_integration.get_changed_files('invalid-sha')
    assert len(changes) == 0
    
    content = git_integration.get_file_content(Path('test.py'), 'invalid-sha')
    assert content is None
    
    message = git_integration.get_commit_message('invalid-sha')
    assert message is None
    
    branch_name = git_integration.get_branch_name('invalid-sha')
    assert branch_name is None

def test_extract_hunks():
    """Test extraction of line number ranges from diff hunks."""
    diff = """@@ -1,3 +1,4 @@
 Module docstring
+New line
@@ -5,7 +6,8 @@
 def test_function():
+    # Added comment
     pass
"""
    git_integration = GitIntegration(Path('.'))
    hunks = git_integration._extract_hunks(diff)
    
    assert len(hunks) == 2
    assert hunks[0] == (1, 2)  # First hunk: line 1 to 2
    assert hunks[1] == (6, 7)  # Second hunk: line 6 to 7 