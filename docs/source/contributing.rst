============
Contributing
============

General Notes
-------------

Getting Started
===============

* Make sure you have a `GitHub account <https://github.com/signup>`_.
* Submit a ticket for your issue, assuming one does not already exist.

  * Clearly describe the issue including steps to reproduce when it is a bug.
  * Make sure you fill in the earliest version that you know has the issue.

* Fork the repository on GitHub


Making Changes
==============

* Create a topic branch from where you want to base your work.

  * This is usually the `main` branch.
  * Only target release branches if you are certain your fix must be on that
    branch.
  * To quickly create a topic branch based on `main`; ``git checkout -b
    my_branch_name main``. Please avoid working directly on the
    `main` branch.

* Make commits of logical units.
* Check for unnecessary whitespace with ``git diff --check`` before committing.
* Make sure your commit messages are in the proper format (see below)
* Make sure you have added the necessary tests for your changes.
* Run *all* the tests to assure nothing else was accidentally broken.

Writing the commit message
==========================

Commit messages should be clear and follow a few basic rules. Example::

  ENH: add functionality X to bluesky.<submodule>.

  The first line of the commit message starts with a capitalized acronym
  (options listed below) indicating what type of commit this is.  Then a blank
  line, then more text if needed.  Lines shouldn't be longer than 72
  characters.  If the commit is related to a ticket, indicate that with
  "See #3456", "See ticket 3456", "Closes #3456" or similar.

Describing the motivation for a change, the nature of a bug for bug fixes
or some details on what an enhancement does are also good to include in a
commit message. Messages should be understandable without looking at the code
changes.

Standard acronyms to start the commit message with are::

  API: an (incompatible) API change
  BLD: change related to building numpy
  BUG: bug fix
  CI : continuous integration
  DEP: deprecate something, or remove a deprecated object
  DEV: development tool or utility
  DOC: documentation
  ENH: enhancement
  MNT: maintenance commit (refactoring, typos, etc.)
  REV: revert an earlier commit
  STY: style fix (whitespace, PEP8)
  TST: addition or modification of tests
  REL: related to releases

The Pull Request
================

* Now push to your fork
* Submit a `pull request <https://help.github.com/articles/using-pull-requests>`_ to this branch. This is a start to the conversation.

At this point you're waiting on us. We like to at least comment on pull requests within three business days
(and, typically, one business day). We may suggest some changes or improvements or alternatives.

Hints to make the integration of your changes easy (and happen faster):

* Keep your pull requests small
* Don't forget your unit tests
* All algorithms need documentation, don't forget the .rst file
* Don't take changes requests to change your code personally


Installation of the Queue Server for Development
------------------------------------------------

Install Redis and create Conda environment as described
`here <https://blueskyproject.io/bluesky-queueserver/installation.html#installation-steps>`_.

Install the Queue Server in editable mode::

  $ pip install -e .

Install development dependencies::

  $ pip install -r requirements-dev.txt


Setting up `pre-commit`
-----------------------

`pre-commit`` package is installed as part of the development requirements. Install pre-commit
script by running ::

  $ pre-commit install

Once installed, `pre-commit` will perform all the checks before each commit. As the new versions
of validation packages are released, the pre-commit script can be updated by running ::

  $ pre-commit autoupdate


Running Unit Tests Locally
--------------------------

The Queue Server API is tested using the `pytest`. Use the following command in the root
of the repository to run the test locally::

  $ pytest -vvv


Run tests in parallel with Docker
---------------------------------

Use isolated containers to run test shards in parallel and avoid local port/process
interference. This reduces the total execution time of the test suite dramatically and allows
running tests on multiple Python versions locally with ease.

.. code-block:: bash

        cd bluesky-queueserver-api
        chmod +x scripts/run_ci_docker_parallel.sh scripts/docker/run_shard_in_container.sh
        ./scripts/run_ci_docker_parallel.sh

By default, the script runs with dynamic dispatch using ``3`` workers and
``9`` chunks (``CHUNK_COUNT=WORKER_COUNT*3``). As workers finish, the next
chunk is started automatically to keep utilization high.

By default, tests run on the latest supported Python version
(``--python-versions latest``, currently ``3.13``).

To run all supported CI Python versions (``3.10``, ``3.11``, ``3.12``, ``3.13``):

.. code-block:: bash

        ./scripts/run_ci_docker_parallel.sh --python-versions all --workers 8 --chunks 24

To run a specific version or list of versions:

.. code-block:: bash

        ./scripts/run_ci_docker_parallel.sh --python-versions 3.12
        ./scripts/run_ci_docker_parallel.sh --python-versions 3.11,3.13 --workers 6 --chunks 18

You can tune workers/chunks and pass extra pytest arguments:

.. code-block:: bash

        ./scripts/run_ci_docker_parallel.sh --workers 4 --chunks 16 --pytest-args "-k api --maxfail=1"

Backward compatibility: ``SHARD_COUNT`` still works as an alias for
``WORKER_COUNT``.

When filtering to a small subset (for example with ``-k``), some chunks may
have no selected tests. Those chunks are treated as successful by default.

Artifacts are written to ``.docker-test-artifacts/``:

* ``shard.<N>.log``: per-shard container output
* ``junit.<N>.xml``: per-shard JUnit reports
* ``coverage.txt`` and ``coverage.xml``: merged coverage outputs

The script also copies merged ``coverage.xml`` to the repository root.

Running Unit Tests on GitHub
----------------------------

Execution of the full test suite on CI takes too long and causes major inconvenience,
therefore it is split into multiple groups (currently 3 groups) using `pytest-split`
package. Calibration is performed by running the script ``store_test_durations.sh`` locally,
which saves execution time for each test in the ```.test_durations`` file. The file then
has to be committed and pushed to the repository.

`pytest-split` will automatically guess execution time for new tests that are not
listed in ``.test_durations`` file, so calibration may be needed rarely or after major
changes to the test suite and should be left to the package maintainers.
