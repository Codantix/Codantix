"""
Command Line Interface for Codantix.
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
def init():
    """Initialize and document the entire repository."""
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
                doc = generator.generate_doc(element, context)
                docs.append({
                    "text": doc,
                    "metadata": {
                        k: v for k, v in {
                            "file_path": str(element.file_path),
                            "element": element.name,
                            "type": element.type.value,
                            "line": element.line_number,
                            "parent": element.parent,
                        }.items() if v is not None and isinstance(v, (str, int, float, bool))
                    }
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
def doc_pr(sha: str):
    """Document changes in a pull request."""
    click.echo(f"Documenting changes in PR with SHA: {sha}")
    try:
        repo_path = Path(os.getcwd())
        config = Config()
        doc_style = config.get_doc_style()
        inc = IncrementalDocumentation(repo_path, DocStyle(doc_style))
        changes = inc.process_commit(sha)
        docs = []
        for change in changes:
            click.echo(f"{change.change_type.title()}: {change.element.file_path}::{change.element.name}")
            if change.change_type in ("new", "update"):
                docs.append({
                    "text": change.new_doc,
                    "metadata": {
                        k: v for k, v in {
                            "file_path": str(change.element.file_path),
                            "element": change.element.name,
                            "type": change.element.type.value,
                            "line": change.element.line_number,
                            "parent": change.element.parent,
                        }.items() if v is not None and isinstance(v, (str, int, float, bool))
                    }
                })
        if docs:
            emb_mgr = EmbeddingManager(config)
            emb_mgr.update_database(docs)
        click.echo("PR documentation and vector database update complete.")
    except Exception as e:
        click.echo(f"Error during PR documentation: {e}", err=True)
        sys.exit(1)

@cli.command()
def update_db():
    """Update the vector database with documentation."""
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
                docs.append({
                    "text": doc,
                    "metadata": {
                        k: v for k, v in {
                            "file_path": str(element.file_path),
                            "element": element.name,
                            "type": element.type.value,
                            "line": element.line_number,
                            "parent": element.parent,
                        }.items() if v is not None and isinstance(v, (str, int, float, bool))
                    }
                })
        emb_mgr = EmbeddingManager(config)
        emb_mgr.update_database(docs)
        click.echo("Vector database updated.")
    except Exception as e:
        click.echo(f"Error during vector DB update: {e}", err=True)
        sys.exit(1)

if __name__ == '__main__':
    cli() 