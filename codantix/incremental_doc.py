"""
Incremental documentation generation for Codantix.
"""
from pathlib import Path
from typing import Dict, List, Optional, Set
from dataclasses import dataclass
from .git_integration import GitIntegration, FileChange
from .documentation import CodeElement, ElementType, ReadmeParser
from .doc_generator import DocumentationGenerator, DocStyle
from .parsers import get_parser
from .config import Config
import os

@dataclass
class DocumentationChange:
    """Represents a documentation change for a code element."""
    element: CodeElement
    old_doc: Optional[str]
    new_doc: str
    change_type: str  # 'new', 'update', 'unchanged'

class IncrementalDocumentation:
    """Handles incremental documentation generation for code changes."""

    def __init__(self, repo_path: Path, doc_style: DocStyle = DocStyle.GOOGLE):
        """Initialize incremental documentation generator."""
        self.git_integration = GitIntegration(repo_path)
        self.doc_generator = DocumentationGenerator(doc_style)
        self.repo_path = repo_path

    def process_commit(self, commit_sha: str) -> List[DocumentationChange]:
        """Process a commit and generate documentation changes."""
        changes = []
        file_changes = self.git_integration.get_changed_files(commit_sha)

        for file_change in file_changes:
            if file_change.change_type == 'D':
                continue  # Skip deleted files

            # Get file content at the commit
            content = self.git_integration.get_file_content(file_change.file_path, commit_sha)
            if not content:
                continue

            # Get appropriate parser for file type
            parser = get_parser(file_change.file_path)
            if not parser:
                continue  # Skip unsupported file types

            # Process each hunk in the file
            for start_line, end_line in file_change.hunks:
                # Extract code elements in the changed lines
                elements = parser.parse_file(content, start_line, end_line)
                
                # Set file path for each element
                for element in elements:
                    element.file_path = file_change.file_path
                
                for element in elements:
                    # Get existing documentation if any
                    old_doc = element.docstring
                    
                    # Generate new documentation
                    new_doc = self.doc_generator.generate_doc(
                        element,
                        self._get_project_context(commit_sha)
                    )

                    # Determine change type
                    change_type = 'new'
                    if old_doc:
                        change_type = 'update' if old_doc != new_doc else 'unchanged'

                    changes.append(DocumentationChange(
                        element=element,
                        old_doc=old_doc,
                        new_doc=new_doc,
                        change_type=change_type
                    ))

        return changes

    def _get_project_context(self, commit_sha: str) -> Dict:
        """Get project context for documentation generation."""
        # Try to get project name from config
        config = Config()
        project_name = os.path.basename(os.path.abspath(self.repo_path))
        if 'name' in config.config:
            project_name = config.config['name']

        # Try to extract context from README.md in repo root
        readme_path = Path(self.repo_path) / "README.md"
        context = ReadmeParser().parse(readme_path)
        context['name'] = project_name
        return context 