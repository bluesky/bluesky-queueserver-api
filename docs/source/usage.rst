=====
Usage
=====

Queue Server (``bluesky-queueserver``) package is automatically installed as a dependency
of ``bluesky-queueserver-api``. Bluesky HTTP Server (``bluesky-httpserver``) package must be
installed separately if needed.

Bluesky Queue Server API are expected to work identically when connecting directly to
Queue Server (0MQ) or via HTTP Server. Start Queue Server in a separate terminal::

    $ start-re-manager

Start HTTP Server in a separate terminal (optional)::

    $ uvicorn bluesky_httpserver.server.server:app --host localhost --port 60610

Open IPython to explore the API library. The first step is to import ``REManagerAPI`` object.
The API library supports synchronous and asynchronous (``asyncio``) models and for 0MQ and HTTP
(REST) protocols:

.. code-block:: python

    # 0MQ, synchronous
    from bluesky_queueserver_api.zmq import REManagerAPI
    # 0MQ, asynchronous
    from bluesky_queueserver_api.zmq.aio import REManagerAPI
    # HTTP, synchronous
    from bluesky_queueserver_api.http import REManagerAPI
    # HTTP, asynchronous
    from bluesky_queueserver_api.http.aio import REManagerAPI

    # Instantiate 'REManagerAPI'. Constructor parameters are different for 0MQ and HTTP API.
    RM = REManagerAPI()

Docstrings for each API may be displayed using IPython ``help()`` function::

    help(RM.status)

The following scripts are expected to run with 0MQ and HTTP versions.
Synchronous code:

.. code-block:: python

    from bluesky_queueserver_api import BPlan
    from bluesky_queueserver_api.zmq import REManagerAPI
    # from bluesky_queueserver_api.http import REManagerAPI

    RM = REManagerAPI()

    item = BPlan("count", ["det1", "det2"], num=10, delay=1)
    RM.item_add(item)

    RM.environment_open()
    RM.wait_for_idle()

    RM.queue_start()
    RM.wait_for_idle()

    status = RM.status()
    print(f"status={status}")

    RM.environment_close()
    RM.wait_for_idle()

    RM.close()

Asynchronous code:

.. code-block:: python

    import asyncio
    from bluesky_queueserver_api import BPlan
    from bluesky_queueserver_api.zmq.aio import REManagerAPI
    # from bluesky_queueserver_api.http.aio import REManagerAPI

    async def run_single_plan():
        RM = REManagerAPI()

        item = BPlan("count", ["det1", "det2"], num=10, delay=1)
        await RM.item_add(item)

        await RM.environment_open()
        await RM.wait_for_idle()

        await RM.queue_start()
        await RM.wait_for_idle()

        status = await RM.status()
        print(f"status={status}")

        await RM.environment_close()
        await RM.wait_for_idle()

        await RM.close()

    asyncio.run(run_single_plan())