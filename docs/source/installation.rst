============
Installation
============

Installation from PyPI
======================

Installation from PyPI::

    $ pip install bluesky-queueserver-api

Installation from `conda-forge`::

    $ conda install bluesky-queueserver-api -c conda-forge

Build and link from source
==========================

Build distribution artifacts
----------------------------

From a local checkout, build source and wheel distributions:

.. code-block:: bash

        cd bluesky-queueserver-api
        uv build

The resulting files are created in ``dist/``.

You can also build with ``pip`` tooling:

.. code-block:: bash

        cd bluesky-queueserver-api
        python -m pip install --upgrade build
        python -m build


Install or link a local checkout
--------------------------------

Install this package in editable mode from the repository root:

.. code-block:: bash

        cd bluesky-queueserver-api
        python -m pip install -e .

From another project, link to this repository as a local editable dependency
using ``uv``:

.. code-block:: bash

        uv add --editable ../bluesky-queueserver-api

Note: the directory name uses hyphens (``bluesky-queueserver-api``), not
underscores.
