"""
Command Line Interface for Codantix.

This module provides the main CLI entrypoints for Codantix, allowing users to:
- Document the entire repository (`codantix init`)
- Document only changes in a pull request (`codantix doc-pr <sha>`)
- Update the vector database with the latest documentation (`codantix update-db`)
- Generate a new configuration file (`codantix generate-config`)

All commands provide user feedback and error reporting.
"""
import click
from pathlib import Path
from codantix.config import Config, DocStyle, VectorDBType, LANGUAGE_EXTENSION_MAP
from codantix.documentation import CodebaseTraverser, ReadmeParser
from codantix.doc_generator import DocumentationGenerator
from codantix.incremental_doc import IncrementalDocumentation, DocStyle
from codantix.embedding import EmbeddingManager
import os
import sys
from tqdm import tqdm

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
        doc_style = config.doc_style
        source_paths = config.source_paths
        repo_path = Path(os.getcwd())
        generator = DocumentationGenerator(doc_style=doc_style, llm_config=config.llm)
        context = ReadmeParser().parse(repo_path / "README.md")
        context['name'] = repo_path.name
        traverser = CodebaseTraverser(config.languages)
        docs = []
        for src in source_paths:
            src_path = repo_path / src
            if not src_path.exists():
                continue
            elements = traverser.traverse(src_path)
            for element in tqdm(elements, desc=f"Processing {src}"):
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
            emb_mgr = EmbeddingManager(config.vector_db.embedding, config.vector_db.provider, 
                                       config.vector_db.vector_db_type, config.vector_db.dimensions, 
                                       config.vector_db.collection_name, config.vector_db.host, 
                                       config.vector_db.port, config.vector_db.persist_directory)
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
        inc = IncrementalDocumentation(config.name, repo_path, doc_style=config.doc_style, llm_config=config.llm)
        changes = inc.process_commit(sha)
        docs = []
        deleted_files = set()
        deleted_elements = []  # (file_path, element_name, element_type)
        for change in tqdm(changes, desc="Processing changes"):
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
        emb_mgr = EmbeddingManager(config.vector_db.embedding, config.vector_db.provider, 
                                   config.vector_db.vector_db_type, config.vector_db.dimensions, 
                                   config.vector_db.collection_name, config.vector_db.host, 
                                   config.vector_db.port, config.vector_db.persist_directory)
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
        doc_style = config.doc_style
        source_paths = config.source_paths
        generator = DocumentationGenerator(doc_style=doc_style, llm_config=config.llm)
        context = ReadmeParser().parse(repo_path / "README.md")
        context['name'] = repo_path.name
        traverser = CodebaseTraverser(config.languages)
        docs = []
        for src in source_paths:
            src_path = repo_path / src
            if not src_path.exists():
                continue
            elements = traverser.traverse(src_path)
            for element in tqdm(elements, desc=f"Processing {src}"):
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
        emb_mgr = EmbeddingManager(config.vector_db.embedding, config.vector_db.provider, 
                                   config.vector_db.vector_db_type, config.vector_db.dimensions, 
                                   config.vector_db.collection_name, config.vector_db.host, 
                                   config.vector_db.port, config.vector_db.persist_directory)
        emb_mgr.update_database(docs)
        click.echo("Vector database updated.")
    except Exception as e:
        click.echo(f"Error during vector DB update: {e}", err=True)
        sys.exit(1)

@cli.command()
def generate_config():
    """Generate a new Codantix configuration file interactively.
    
    This command will guide you through creating a new codantix.config.json file
    with all necessary settings for your project.
    """
    click.echo("Welcome to Codantix configuration generator!")
    click.echo("Let's create your configuration file step by step.\n")

    # Step 1: Project name
    name = click.prompt("Enter your project name", type=str)
    
    # Step 2: Documentation style
    doc_style = click.prompt(
        "Choose documentation style",
        type=click.Choice([style.value for style in DocStyle]),
        default=DocStyle.GOOGLE.value
    )
    
    # Step 3: Source paths
    click.echo("\nEnter source paths (one per line, press Enter twice to finish):")
    source_paths = []
    while True:
        path = click.prompt("Source path", default="", show_default=False)
        if not path and source_paths:  # Allow empty input only if we have at least one path
            break
        if path:
            source_paths.append(path)
    
    # Step 4: Languages
    supported_langs = list(LANGUAGE_EXTENSION_MAP.keys())
    click.echo(f"\nSupported languages: {', '.join(supported_langs)}")
    languages = click.prompt(
        "Choose languages (comma-separated)",
        type=str,
        default="python"
    ).split(",")
    languages = [lang.strip() for lang in languages]
    
    # Step 5: Vector DB configuration
    click.echo("\nVector Database Configuration:")
    vector_db_type = click.prompt(
        "Choose vector database type",
        type=click.Choice([db_type.value for db_type in VectorDBType]),
        default=VectorDBType.CHROMA.value
    )
    
    vector_db_provider = click.prompt(
        "Enter vector DB provider",
        type=str,
        default="openai"
    )
    
    vector_db_embedding = click.prompt(
        "Enter embedding model",
        type=str,
        default="text-embedding-3-large"
    )
    
    vector_db_dimensions = click.prompt(
        "Enter embedding dimensions",
        type=int,
        default=1024
    )
    
    # Step 6: LLM Configuration
    click.echo("\nLLM Configuration:")
    llm_provider = click.prompt(
        "Enter LLM provider",
        type=str,
        default="google_genai"
    )
    
    llm_model = click.prompt(
        "Enter LLM model",
        type=str,
        default="gemini-2.5-flash-preview-04-17"
    )
    
    max_tokens = click.prompt(
        "Enter max tokens",
        type=int,
        default=1024
    )
    
    temperature = click.prompt(
        "Enter temperature",
        type=float,
        default=0.7
    )
    
    # Create configuration
    config = {
        "name": name,
        "doc_style": doc_style,
        "source_paths": source_paths,
        "languages": languages,
        "vector_db": {
            "type": vector_db_type,
            "provider": vector_db_provider,
            "embedding": vector_db_embedding,
            "dimensions": vector_db_dimensions,
            "path": "vecdb/",
            "collection_name": "codantix_docs",
            "host": "localhost",
            "port": None,
            "persist_directory": "vecdb/"
        },
        "llm": {
            "provider": llm_provider,
            "llm_model": llm_model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": None,
            "top_k": None,
            "stop_sequences": [],
            "rate_limit": {
                "llm_requests_per_second": 0.1,
                "llm_check_every_n_seconds": 0.1,
                "llm_max_bucket_size": 10
            }
        }
    }
    
    # Save configuration
    config_path = "codantix.config.json"
    try:
        with open(config_path, 'w') as f:
            import json
            json.dump(config, f, indent=2)
        click.echo(f"\nConfiguration saved to {config_path}")
    except Exception as e:
        click.echo(f"Error saving configuration: {e}", err=True)
        sys.exit(1)

if __name__ == '__main__':
    cli() 