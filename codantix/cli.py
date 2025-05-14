"""
Command Line Interface for Codantix.

This module provides the main CLI entrypoints for Codantix, allowing users to:
- Document the entire repository (`codantix init`)
- Document only changes in a pull request (`codantix doc-pr <sha>`)
- Update the vector database with the latest documentation (`codantix update-db`)

All commands provide user feedback and error reporting.
"""
import click
from pathlib import Path
from codantix.config import Config
from codantix.documentation import CodebaseTraverser, ReadmeParser
from codantix.doc_generator import DocumentationGenerator
from codantix.incremental_doc import IncrementalDocumentation, DocStyle
from codantix.embedding import EmbeddingManager
import os
import sys

@click.group()
def cli():
    """Codantix - Automated Code Documentation and Vector Database Management"""
    pass

@cli.command()
@click.option('--version', default=None, help='Version identifier for the indexed code.')
@click.option('--freeze', is_flag=True, default=False, help='Freeze documentation: only extract and embed existing docstrings, do not generate or update.')
def init(version, freeze):
    """Initialize and document the entire repository.

    Scans all configured source paths, generates or updates documentation for all code elements,
    and updates the vector database with the new documentation.

    Args:
        version (str, optional): Version identifier for the indexed code. If provided, this version will be included in the metadata for all indexed documents.
        freeze (bool, optional): If set, only extract and embed existing docstrings without generating or updating documentation.

    Raises:
        SystemExit: If an error occurs during initialization.
    """
    click.echo("Initializing repository documentation...")
    try:
        config = Config()
        doc_style = config.get_doc_style()
        source_paths = config.get_source_paths()
        repo_path = Path(os.getcwd())
        generator = DocumentationGenerator(doc_style=doc_style)
        context = ReadmeParser().parse(repo_path / "README.md")
        context['name'] = repo_path.name
        traverser = CodebaseTraverser()
        docs = []
        for src in source_paths:
            src_path = repo_path / src
            if not src_path.exists():
                continue
            elements = traverser.traverse(src_path)
            for element in elements:
                if freeze:
                    doc = element.existing_doc or ''
                else:
                    doc = generator.generate_doc(element, context)
                metadata = {
                    k: v for k, v in {
                        "file_path": str(element.file_path),
                        "element": element.name,
                        "type": element.type.value,
                        "line": element.line_number,
                        "parent": element.parent,
                    }.items() if v is not None and isinstance(v, (str, int, float, bool))
                }
                if version is not None:
                    metadata["version"] = version
                docs.append({
                    "text": doc,
                    "metadata": metadata
                })
        if docs:
            emb_mgr = EmbeddingManager(config)
            emb_mgr.update_database(docs)
        click.echo("Repository documentation and vector database update complete.")
    except Exception as e:
        click.echo(f"Error during initialization: {e}", err=True)
        sys.exit(1)

@cli.command()
@click.argument('sha')
@click.option('--version', default=None, help='Version identifier for the indexed code.')
def doc_pr(sha: str, version):
    """Document changes in a pull request.

    Args:
        sha (str): The commit SHA identifying the pull request or commit to document.
        version (str, optional): Version identifier for the indexed code. If provided, this version will be included in the metadata for all indexed documents.

    Scans the code changes in the specified commit, generates or updates documentation for changed elements,
    and updates the vector database accordingly.

    Raises:
        SystemExit: If an error occurs during PR documentation.
    """
    click.echo(f"Documenting changes in PR with SHA: {sha}")
    try:
        repo_path = Path(os.getcwd())
        config = Config()
        doc_style = config.get_doc_style()
        inc = IncrementalDocumentation(repo_path, DocStyle(doc_style))
        changes = inc.process_commit(sha)
        docs = []
        deleted_files = set()
        deleted_elements = []  # (file_path, element_name, element_type)
        for change in changes:
            click.echo(f"{change.change_type.title()}: {change.element.file_path}::{change.element.name}")
            if change.change_type in ("new", "update"):
                metadata = {
                    k: v for k, v in {
                        "file_path": str(change.element.file_path),
                        "element": change.element.name,
                        "type": change.element.type.value,
                        "line": change.element.line_number,
                        "parent": change.element.parent,
                    }.items() if v is not None and isinstance(v, (str, int, float, bool))
                }
                if version is not None:
                    metadata["version"] = version
                docs.append({
                    "text": change.new_doc,
                    "metadata": metadata
                })
            elif change.change_type == "D":
                deleted_files.add(str(change.element.file_path))
                # Track any element type for targeted removal
                deleted_elements.append((str(change.element.file_path), change.element.name, change.element.type.value))
        emb_mgr = EmbeddingManager(config)
        if docs:
            emb_mgr.update_database(docs)
        # Remove all embeddings for deleted files
        db = emb_mgr.db
        if deleted_files:
            for file_path in deleted_files:
                if hasattr(db, "delete"):
                    db.delete(filter={"file_path": file_path})
        # Remove embeddings for deleted elements (any type)
        if deleted_elements:
            for file_path, name, elem_type in deleted_elements:
                if hasattr(db, "delete"):
                    db.delete(filter={"file_path": file_path, "element": name, "type": elem_type})
        click.echo("PR documentation and vector database update complete.")
    except Exception as e:
        click.echo(f"Error during PR documentation: {e}", err=True)
        sys.exit(1)

@cli.command()
@click.option('--version', default=None, help='Version identifier for the indexed code.')
def update_db(version):
    """Update the vector database with documentation.

    Scans all configured source paths, generates documentation for all code elements, and updates the vector database.

    Args:
        version (str, optional): Version identifier for the indexed code. If provided, this version will be included in the metadata for all indexed documents.

    Raises:
        SystemExit: If an error occurs during the update.
    """
    click.echo("Updating vector database...")
    try:
        config = Config()
        repo_path = Path(os.getcwd())
        doc_style = config.get_doc_style()
        source_paths = config.get_source_paths()
        generator = DocumentationGenerator(doc_style=doc_style)
        context = ReadmeParser().parse(repo_path / "README.md")
        context['name'] = repo_path.name
        traverser = CodebaseTraverser()
        docs = []
        for src in source_paths:
            src_path = repo_path / src
            if not src_path.exists():
                continue
            elements = traverser.traverse(src_path)
            for element in elements:
                doc = generator.generate_doc(element, context)
                metadata = {
                    k: v for k, v in {
                        "file_path": str(element.file_path),
                        "element": element.name,
                        "type": element.type.value,
                        "line": element.line_number,
                        "parent": element.parent,
                    }.items() if v is not None and isinstance(v, (str, int, float, bool))
                }
                if version is not None:
                    metadata["version"] = version
                docs.append({
                    "text": doc,
                    "metadata": metadata
                })
        emb_mgr = EmbeddingManager(config)
        emb_mgr.update_database(docs)
        click.echo("Vector database updated.")
    except Exception as e:
        click.echo(f"Error during vector DB update: {e}", err=True)
        sys.exit(1)

if __name__ == '__main__':
    cli() 