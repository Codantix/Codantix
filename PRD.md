# Codantix - Product Requirements Document (PRD)

## Overview

**Codantix** is a language-agnostic tool that automates code documentation and indexes it into a vector database for semantic navigation and search. It supports initial documentation generation, pull request diff-based updates, and efficient vector database management.

---

## Core Features

### 1. Initial Codebase Documentation

**Goal:** Automatically scan the entire project and generate documentation where needed.

#### Steps:
- **Read `README.md`**:
  - Extract project context, architecture, and purpose.
- **Load Configuration**:
  - Read from `codantix.config.json` or `.yaml`:
    - Preferred doc style (Google, NumPy, JSDoc, etc.)
    - Source paths (e.g., `src/`, `lib/`)
    - Languages supported (Python, JS, Java/Scala)
- **Traverse Codebase**:
  - For each source file:
    - Detect functions, classes, and modules lacking documentation.
    - Reuse existing documentation where available.
    - Generate or improve documentation using LLMs, leveraging context from README and local code.

---

### 2. Pull Request-Based Documentation

**Goal:** Document only the code changes (diff) in each pull request.

#### Steps:
- Use **GitPython** to extract diffs:
  - Detect added or modified files, functions, and classes.
- For each change:
  - Generate new documentation or update existing one.
  - Ensure consistency with selected doc style.
  - Preserve any manually written documentation.

---

### 3. Vector Database Update

**Goal:** Keep the vector database in sync with the documented codebase.

#### Steps:
- Convert new/updated documentation to embeddings using **LangChain**.
- Store embeddings in a vector DB (e.g., Chroma, Pinecone) with metadata:
  - File path
  - Programming language
  - Element type (function/class/module)
  - Hierarchy (e.g., `module > class > method`)
  - Git SHA or timestamp

---

## Technical Stack

### Languages Supported
- Python
- JavaScript / TypeScript
- Java / Scala

### Core Packages
- `langchain` – Embedding generation and vector DB loading.
- `GitPython` – Detecting diffs for PR-based documentation.
- `openai`/`antropic`/`google`/`huggingface` or compatible LLM provider – For generating docstrings/comments.

### Note
consider always security espect and best practice (like using api keys from env)

---

## Configuration File: `codantix.config.json`

```json
{
  "doc_style": "google",
  "source_paths": ["src", "lib", "packages"],
  "languages": ["python", "javascript", "java"],
  "vector_db": {
    "type": "chroma",
    "path": "vecdb/"
  }, 
  "embedding": "text-embedding-3-large",
  "provider": "openai", 
  "dimensions": 1024
}

---
### 3. CLI Interface
```bash
codantix init              # Scan and document entire repo
codantix doc-pr <sha>      # Document changes in a pull request
codantix update-db         # Update the vector DB with docs
```
---

