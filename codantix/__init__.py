"""
Codantix
--------

Codantix is an intelligent, language-agnostic tool that automates code documentation and indexes your codebase into a vector database for semantic search, code navigation, and AI-driven insights.

Features:
- LLM-powered documentation generation
- Full codebase and pull request diff documentation
- Vector embedding and search via LangChain
- Git diff processing with GitPython
- Supports Python, JavaScript, Java, and Scala

Main CLI commands:
- codantix init: Document the entire repository
- codantix doc-pr <sha>: Document only changed code in a pull request
- codantix update-db: Update the vector database with latest docs

See the README.md for configuration, installation, and usage details.
"""

__version__ = "0.1.0" 