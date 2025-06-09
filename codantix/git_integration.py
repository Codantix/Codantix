"""
Git integration for Codantix to handle PR-based documentation.

This module provides the GitIntegration class for extracting file changes,
diffs, and content from a Git repository, supporting PR-based and
incremental documentation workflows.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

import git


@dataclass
class FileChange:
    """
    Represents a file change in a commit.
    """

    file_path: Path
    change_type: str  # 'A' for added, 'M' for modified, 'D' for deleted
    diff: str
    hunks: List[Tuple[int, int]]  # List of (start_line, end_line) tuples


class GitIntegration:
    """
    Handles Git operations for PR-based documentation.
    Provides methods to extract changed files, diffs, file content,
    commit messages, and branch names from a repository.
    """

    def __init__(self, repo_path: Path):
        """
        Initialize Git integration with repository path.

        Args:
            repo_path (Path): Path to the root of the Git repository.
        """
        self.repo_path = repo_path
        self.repo = git.Repo(repo_path)

    def get_changed_files(self, commit_sha: str) -> List[FileChange]:
        """
        Get list of files changed in a commit.

        Args:
            commit_sha (str): The commit SHA to analyze.

        Returns:
            List[FileChange]: List of file changes in the commit.
        """
        try:
            commit = self.repo.commit(commit_sha)
            parent = commit.parents[0] if commit.parents else None

            if not parent:
                # If this is the first commit, consider all files as added
                return [
                    FileChange(
                        file_path=Path(item.a_path),
                        change_type="A",
                        diff=str(item.diff),
                        hunks=self._extract_hunks(str(item.diff)),
                    )
                    for item in commit.tree.traverse()
                    if item.type == "blob"
                ]

            # Get diff between commit and its parent
            diffs = parent.diff(commit)
            changes = []

            for diff in diffs:
                change_type = "M"  # Default to modified
                if diff.new_file:
                    change_type = "A"
                elif diff.deleted_file:
                    change_type = "D"
                    continue  # Skip deleted files for documentation

                if diff.a_path and diff.a_path.endswith((".py", ".js", ".java")):
                    # Get the diff content using GitPython's diff functionality
                    diff_content = self.repo.git.diff(
                        parent.hexsha, commit.hexsha, "--", diff.a_path
                    )

                    changes.append(
                        FileChange(
                            file_path=Path(diff.a_path),
                            change_type=change_type,
                            diff=diff_content,
                            hunks=self._extract_hunks(diff_content),
                        )
                    )

            return changes

        except (git.GitCommandError, git.BadName) as e:
            print(f"Error getting changed files: {e}")
            return []

    def _extract_hunks(self, diff: str) -> List[Tuple[int, int]]:
        """
        Extract line number ranges from diff hunks.

        Args:
            diff (str): The diff string to parse.

        Returns:
            List[Tuple[int, int]]: List of (start_line, end_line) tuples
            for each hunk.
        """
        hunks = []
        current_hunk = None
        current_start = None

        for line in diff.split("\n"):
            if line.startswith("@@"):
                # Save previous hunk if exists
                if current_hunk and current_start:
                    hunks.append((current_start, current_hunk))

                # Parse new hunk header
                try:
                    # Extract the line numbers from the hunk header
                    # Format: @@ -a,b +c,d @@
                    parts = line.split(" ")[1:3]
                    if len(parts) == 2:
                        new_line = int(parts[1].split(",")[0][1:])
                        current_start = new_line
                        current_hunk = new_line
                except (IndexError, ValueError):
                    continue
            elif line.startswith("+") and current_hunk is not None:
                current_hunk += 1
            elif line.startswith("-") and current_hunk is not None:
                current_hunk += 1

        # Add the last hunk
        if current_hunk and current_start:
            hunks.append((current_start, current_hunk))

        return hunks

    def get_file_content(self, file_path: Path, commit_sha: str) -> Optional[str]:
        """
        Get the content of a file at a specific commit.

        Args:
            file_path (Path): Path to the file.
            commit_sha (str): The commit SHA to retrieve the file from.

        Returns:
            Optional[str]: File content as a string, or None if not found.
        """
        try:
            commit = self.repo.commit(commit_sha)
            blob = commit.tree[str(file_path)]
            return blob.data_stream.read().decode("utf-8")
        except (git.GitCommandError, git.BadName, KeyError) as e:
            print(f"Error getting file content: {e}")
            return None

    def get_commit_message(self, commit_sha: str) -> Optional[str]:
        """
        Get the commit message for a specific commit.

        Args:
            commit_sha (str): The commit SHA to retrieve the message from.

        Returns:
            Optional[str]: Commit message string, or None if not found.
        """
        try:
            commit = self.repo.commit(commit_sha)
            return commit.message
        except (git.GitCommandError, git.BadName) as e:
            print(f"Error getting commit message: {e}")
            return None

    def get_branch_name(self, commit_sha: str) -> Optional[str]:
        """
        Get the branch name for a specific commit.

        Args:
            commit_sha (str): The commit SHA to retrieve the branch name from.

        Returns:
            Optional[str]: Branch name string, or None if not found.
        """
        try:
            commit = self.repo.commit(commit_sha)
            for branch in self.repo.heads:
                if branch.commit == commit:
                    return branch.name
            return None
        except (git.GitCommandError, git.BadName) as e:
            print(f"Error getting branch name: {e}")
            return None
