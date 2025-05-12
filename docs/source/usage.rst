Usage
=====

Codantix provides a command-line interface for generating and updating code documentation and vector databases.

Basic commands:

.. code-block:: bash

   codantix init              # Generate docs for full repo
   codantix doc-pr <sha>      # Document only changed code in a pull request
   codantix update-db         # Update vector database with latest docs

For more CLI examples and advanced usage, see the README or run ``codantix --help``. 