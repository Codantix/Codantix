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

---

## 🛠️ Tech Stack

| Purpose        | Tool/Library       |
|----------------|--------------------|
| Git diffing    | `GitPython`        |
| Embedding & Vector DB | `LangChain` |
| Language Support | Python, JS/TS, Java, Scala |
| Doc Generation | OpenAI-compatible LLM |

---

## ⚙️ Configuration

Create a `codantix.config.json` file in your project root:

```json
{
  "doc_style": "google",
  "source_paths": ["src", "lib", "packages"],
  "languages": ["python", "javascript", "java"],
  "vector_db": {
    "type": "chroma",
    "path": "vecdb/",
    "collection": "codantix_docs"
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
    "path": "vecdb/",
    "collection": "codantix_docs"
  }
}
```

#### Example config for Qdrant (local/external)
```json
{
  "vector_db": {
    "type": "qdrant",
    "host": "localhost",
    "port": 6333,
    "api_key": "<QDRANT_API_KEY>",
    "collection": "codantix_docs"
  }
}
```

#### Example config for Milvus (external)
```json
{
  "vector_db": {
    "type": "milvus",
    "host": "localhost",
    "port": 19530,
    "collection": "codantix_docs"
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
    "path": "vecdb/",
    "collection": "codantix_docs"
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
- ⏳ VSCode integration
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
