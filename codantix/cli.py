"""
Command Line Interface for Codantix.
"""
import click
from typing import Optional

@click.group()
def cli():
    """Codantix - Automated Code Documentation and Vector Database Management"""
    pass

@cli.command()
def init():
    """Initialize and document the entire repository."""
    click.echo("Initializing repository documentation...")
    # TODO: Implement full repository scan and documentation

@cli.command()
@click.argument('sha')
def doc_pr(sha: str):
    """Document changes in a pull request."""
    click.echo(f"Documenting changes in PR with SHA: {sha}")
    # TODO: Implement PR-based documentation

@cli.command()
def update_db():
    """Update the vector database with documentation."""
    click.echo("Updating vector database...")
    # TODO: Implement vector database update

if __name__ == '__main__':
    cli() 