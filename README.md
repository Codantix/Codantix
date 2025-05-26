# Codantix

**Codantix** is an intelligent, language-agnostic tool that automates code documentation and indexes your codebase into a vector database — enabling powerful semantic search, code navigation, and AI-driven insights.

- 🧠 LLM-powered doc generation
- ⚙️ Works on full codebases and pull request diffs
- 📚 Supports Python, JavaScript, Java, and Scala
- 🔎 Vector embedding via LangChain
- 🔄 Git diff processing with GitPython

---

## ✨ Features

### 📦 Initial Project Documentation
- Scans the entire project and adds or updates documentation
- Reads context from `README.md`
- Supports user-defined doc styles and source paths
- Supports a `--freeze` mode to only extract and embed existing docstrings, without generating or updating them
- Supports a `--version` parameter to tag all indexed documents with a version identifier for later filtering or retrieval

### 🔁 Pull Request Diff Documentation
- Automatically documents only changed functions/classes in PRs
- Uses Git diff to isolate modified blocks

### 🧠 Vector DB Integration
- Embeds code/doc structure using LangChain
- Stores into a vector database with hierarchical metadata for search

### ⚙️ Interactive Configuration
- Step-by-step configuration generation
- Supports all major vector databases
- Configurable LLM settings

---

## 🛠️ Tech Stack

| Purpose        | Tool/Library       |
|----------------|--------------------|
| Git diffing    | `GitPython`        |
| Embedding & Vector DB | `LangChain` |
| Language Support | Python, JS/TS, Java, Scala |
| Doc Generation | LangChain-compatible LLM |

---

## ⚙️ Configuration

You can create a configuration file in two ways:

1. Using the interactive generator:
```bash
codantix generate-config
```

2. Manually creating a `codantix.config.json` file in your project root:

```json
{
  "name": "your-project-name",
  "doc_style": "google",
  "source_paths": ["src", "lib", "packages"],
  "languages": ["python", "javascript", "java"],
  "vector_db": {
    "type": "chroma",
    "provider": "openai",
    "embedding": "text-embedding-3-large",
    "dimensions": 1024,
    "path": "vecdb/",
    "collection_name": "codantix_docs",
    "host": "localhost",
    "port": null,
    "persist_directory": "vecdb/"
  },
  "llm": {
    "provider": "google_genai",
    "llm_model": "gemini-2.5-flash-preview-04-17",
    "max_tokens": 1024,
    "temperature": 0.7,
    "top_p": null,
    "top_k": null,
    "stop_sequences": [],
    "rate_limit": {
      "llm_requests_per_second": 0.1,
      "llm_check_every_n_seconds": 0.1,
      "llm_max_bucket_size": 10
    }
  }
}
```

### Vector Database Configuration

Codantix supports multiple vector DBs via LangChain:
- **Chroma** (local, default)
- **Qdrant** (local/external)
- **Milvus** (external, requires env for user/password)
- **Milvus Lite** (embedded/local)

#### Example config for Chroma (local)
```json
{
  "vector_db": {
    "type": "chroma",
    "provider": "openai",
    "embedding": "text-embedding-3-large",
    "dimensions": 1024,
    "path": "vecdb/",
    "collection_name": "codantix_docs",
    "host": "localhost",
    "port": null,
    "persist_directory": "vecdb/"
  }
}
```

#### Example config for Qdrant (local/external)
```json
{
  "vector_db": {
    "type": "qdrant",
    "provider": "openai",
    "embedding": "text-embedding-3-large",
    "dimensions": 1024,
    "host": "localhost",
    "port": 6333,
    "api_key": "<QDRANT_API_KEY>",
    "collection_name": "codantix_docs"
  }
}
```

#### Example config for Milvus (external)
```json
{
  "vector_db": {
    "type": "milvus",
    "provider": "openai",
    "embedding": "text-embedding-3-large",
    "dimensions": 1024,
    "host": "localhost",
    "port": 19530,
    "collection_name": "codantix_docs"
    // User and password are always taken from the environment:
    // MILVUS_USER and MILVUS_PASSWORD
  }
}
```

#### Example config for Milvus Lite (embedded/local)
```json
{
  "vector_db": {
    "type": "milvus_lite",
    "provider": "openai",
    "embedding": "text-embedding-3-large",
    "dimensions": 1024,
    "path": "vecdb/",
    "collection_name": "codantix_docs"
  }
}
```

### Milvus Credentials
For Milvus (external), set the following environment variables:
- `MILVUS_USER` (e.g., "root")
- `MILVUS_PASSWORD` (your password)

These are **never** read from the config file for security.

---

## 🚀 CLI Usage

```bash
codantix generate-config           # Generate configuration file interactively
codantix init                      # Generate docs for full repo
codantix init --freeze             # Only extract and embed existing docstrings, do not generate or update
codantix init --version v1.2.0     # Index docs and tag with version 'v1.2.0'
codantix doc-pr <sha> --version v1.2.0  # Document only changed code in a PR, tag with version
codantix update-db --version v1.2.0     # Update vector DB and tag all docs with version
```

> Codantix is designed to respect and reuse existing documentation, updating only where needed. Use `--freeze` to 
strictly preserve all existing docstrings and only embed them for search.
> Use the `--version` flag to tag all indexed documents with a version identifier. This is useful for tracking, filtering, or retrieving documentation and embeddings for a specific release or snapshot.

---

## 🧩 Supported Languages

- [x] Python
- [x] JavaScript / TypeScript
- [x] Java
- [x] Scala

More languages coming soon...

---

## 🔮 Roadmap

- ✅ Multi-language support
- ✅ PR-based documentation
- ✅ Interactive configuration
- ⏳ MCP server
- ⏳ Natural language Q&A over your codebase
- ⏳ Web dashboard for doc browsing

---

## 📄 License

MIT License — see [`LICENSE`](https://github.com/MatufA/Codantix/blob/main/LICENSE) for details.

---

## 🤝 Contributing

Pull requests are welcome! If you're adding a new feature or fixing a bug, please open an issue first to discuss.

---

## 🙌 Acknowledgements

- [LangChain](https://github.com/langchain-ai/langchain)
- [GitPython](https://github.com/gitpython-developers/GitPython)
- OpenAI and other LLM providers
