Configuration
=============

Codantix can be configured via a ``codantix.config.json`` file in your project root. Example configuration:

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

Supported vector DBs: Chroma, Qdrant, Milvus, Milvus Lite.

For full details and advanced options, see the README or the ``codantix.config`` module. 