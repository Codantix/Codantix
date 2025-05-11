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
    "path": "vecdb/"
  }
}
```

---

## 🚀 CLI Usage

```bash
codantix init              # Generate docs for full repo
codantix doc-pr <sha>      # Document only changed code in a pull request
codantix update-db         # Update vector database with latest docs
```

> Codantix is designed to respect and reuse existing documentation, updating only where needed.

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

MIT License — see [`LICENSE`](LICENSE) for details.

---

## 🤝 Contributing

Pull requests are welcome! If you're adding a new feature or fixing a bug, please open an issue first to discuss.

---

## 🙌 Acknowledgements

- [LangChain](https://github.com/langchain-ai/langchain)
- [GitPython](https://github.com/gitpython-developers/GitPython)
- OpenAI and other LLM providers
