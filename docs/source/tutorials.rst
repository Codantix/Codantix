Tutorials
=========

This section provides step-by-step tutorials for using Codantix, from initial setup to advanced workflows.

.. contents::
   :local:
   :depth: 2

Initial Setup
-------------

1. **Install dependencies**

   .. code-block:: bash

      make install
      make sync

2. **Configure your project**

   Create a `codantix.config.json` file in your project root. Example:

   .. code-block:: json

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

3. **Set up environment variables** (if using external APIs)

   - For OpenAI: `export OPENAI_API_KEY=...`
   - For Milvus: `export MILVUS_USER=...` and `export MILVUS_PASSWORD=...`


Basic CLI Usage
---------------

1. **Document the entire repository**

   .. code-block:: bash

      codantix init

   This scans all configured source paths, generates or updates documentation, and updates the vector database.

2. **Freeze documentation: only embed existing docstrings**

   .. code-block:: bash

      codantix init --freeze

   This will only extract and embed existing docstrings, without generating or updating any documentation. Use this if you want to preserve all current docstrings and just index them for search.

3. **Tag documentation with a version identifier**

   .. code-block:: bash

      codantix init --version v1.2.0
      codantix doc-pr <sha> --version v1.2.0
      codantix update-db --version v1.2.0

   Use the `--version` flag to tag all indexed documents with a version identifier. This is useful for tracking, filtering, or retrieving documentation and embeddings for a specific release or snapshot.

4. **Document only changes in a pull request**

   .. code-block:: bash

      codantix doc-pr <sha>

   Replace `<sha>` with the commit SHA for the PR. Only changed code elements will be documented and indexed.

5. **Update the vector database**

   .. code-block:: bash

      codantix update-db

   This regenerates embeddings and updates the vector database with the latest documentation.


Advanced Workflow: Custom Embedding Provider
--------------------------------------------

1. **Edit your config to use a different embedding provider**

   .. code-block:: json
      :caption: Partial config (only relevant fields shown)

      {
        "provider": "huggingface",
        "embedding": "thenlper/gte-base"
      }

2. **Set up any required environment variables**

   - For HuggingFace: 

   .. code-block:: bash

      export HUGGINGFACE_API_KEY=...

3. **Run the CLI as usual**

   .. code-block:: bash

      codantix init

   Codantix will use the specified provider and model for embedding generation. 