_doc_BItem = """
    A helper class that generates dictionary with queue item parameters. The class
    performs validation of values to ensure that the dictionary is formatted correctly.
    A queue item can be represented as a plain Python dictionary. Using this class
    to represent is queue items is optional.

    The item can be instantiated from a dictionary that contains valid item parameters
    or by passing item type, item name, args and kwargs or from another ``BItem`` object.
    The class implements public properties that allow to access all important item
    parameters, such as ``item_type``, ``name``, ``args``, ``kwargs``, ``meta``
    and ``item_uid``.

    Parameters
    ----------
    *args: list
        The first two arguments are required and should represent item type (allowed
        values are ``'plan'``, ``'instruction'`` and ``'function'``) and item name
        (name of the plan, instruction or function represented as a string). The remaining
        arguments are optional and represent args of the plan or function. Alternatively,
        an item may be instantiated from a valid dictionary of item parameters or another
        item object. In this case the constructor should be passed a single argument that
        contains the dictionary or the object and no keyword arguments.
    **kwargs: dict
        Keyword arguments of the plan or function.

    Raises
    ------
    KeyError, ValueError, TypeError
        Missing parameter or invalid parameter types or values

    Examples
    --------

    .. code-block:: python

        plan1 = BItem("plan", "count", ["det1", "det2"], num=10, delay=1)
        plan2 = BItem(plan1)  # Creates a copy of a plan
        plan3 = BItem({
            "item_type": "plan",
            "name": "count",
            "args": [["det1", "det2]],
            "kwargs": {"num": 10, "delay": 1}
        })

        item_type = plan1.item_type  # Require, always set
        item_name = plan1.name  # Required, always set
        item_args = plan1.args  # Optional, [] if not set
        item_kwargs = plan1.kwargs  # Optional, {} if not set
        item_uid = plan1.item_uid  # Usually set by the server, None if not set
        item_meta = plan1.meta  # Optional, {} if not set

        # Convert 'plan1' into 'queue_stop' instruction (properties are writable)
        plan1.item_type = "instruction"
        plan1.name = "queue_stop"
        plan1.args = []
        plan1.kwargs = {}
        plan1.meta = {}

        plan1_dict = plan1.to_dict()  # Returns a copy of the internal dictionary
        plan2.from_dict(plan1_dict)  # Makes 'plan2' a copy of 'plan1'
        plan2.from_dict(plan1)  # Works exactly the same

        # Access to internal dictionary
        dict_ref = plan3.dict_ref
        dict_ref["args"] = [["det1"]]
"""

_doc_BPlan_BInst_BFunc_common = """
    The helper class for creating dictionary representing --ITEM--. The class functionality
    is similar to ``BItems``, but configured for operations with items that represent --ITEMS--.

    Parameters
    ----------
    *args: list
        The first argument is a name of --ITEM-- represented as a string.
        The remaining arguments are optional and represent args of --ITEM--.
        Alternatively, an item may be instantiated from a valid dictionary
        of item parameters or another object that represent an item of matching type.
        Then the constructor receives a single argument that contains the dictionary or
        the item object and no keyword arguments.
    **kwargs: dict
        Keyword arguments of --ITEM--.

    Raises
    ------
    KeyError, ValueError, TypeError
        Missing parameter or invalid parameter types or values

    Examples
    --------

    .. code-block:: python

        plan1 = BPlan("count", ["det1", "det2"], num=10, delay=1)
        inst1 = BInst("queue_stop")
        func1 = BFunc("custom_func", 10)

        plan2 = BPlan(plan1.to_dict())  # Copy of 'plan'
        plan2 = BPlan(plan1)  # Works exactly the same

        # Initialization from items of another type always fails
        BPlan(func1.to_dict())  # Fails
        BPlan(inst1)  # Fails
        plan1.from_dict(func1.to_dict())  # Fails
        plan1.from_dict(inst1)  # Fails

        # BItem can be initialized from specialized item objects
        item = BItem(inst1.to_dict)  # Works
        item = BItem(inst1)  # Works

        # The following sequence works, because item type is correct
        item1 = BItem(plan1)  # 'item1' is still a plan
        plan3 = BPlan(item1)  # Initialize a plan object with another plan object
"""

_doc_BPlan = _doc_BPlan_BInst_BFunc_common.replace("--ITEM--", "a plan").replace("--ITEMS--", "plans")
_doc_BInst = _doc_BPlan_BInst_BFunc_common.replace("--ITEM--", "an instruction").replace(
    "--ITEMS--", "instructions"
)
_doc_BFunc = _doc_BPlan_BInst_BFunc_common.replace("--ITEM--", "a function").replace("--ITEMS--", "functions")


_doc_REManagerAPI_ZMQ = """
    API for communication with RE Manager using 0MQ protocol.

    Parameters
    ----------
    zmq_server_address: str or None
        Address of control 0MQ socket of RE Manager. If ``None``,
        then the default address ``"tcp://localhost:60615"`` is used.
    timeout_recv: float
        ``recv`` timeout for 0MQ socket. Default value is 2.0 seconds.
    timeout_send: float
        ``send`` timeout for 0MQ socket. Default value is 0.5 seconds.
    server_public_key: str or None
        Public key of RE Manager if the encryption is enabled. Set to ``None``
        if encryption is not enabled
    request_fail_exceptions: boolean
        If ``True`` (default) then API functions that communicate with
        RE Manager are raising the ``RequestFailError`` exception if
        the request is rejected (the response contains ``"success": False``,
        e.g. if a submitted plan is rejected). If ``False``, then API
        functions are always returning the response and user code is
        responsible for checking and processing the ``success`` flag.
    status_expiration_period: float
        Expiration period for cached RE Manager status,
        default value: 0.5 seconds
    status_polling_period: float
        Polling period for RE Manager status used by 'wait' operations,
        default value: 1 second
    loop: asyncio.Loop
        ``asyncio`` event loop (use only with Async version of the API).

    Examples
    --------

    Synchronous API:

    .. code-block:: python

        from bluesky_queueserver_api.zmq import REManagerAPI
        RM = REManagerAPI()
        # < some useful code >
        RE.close()

    Asynchronous API:

    .. code-block:: python

        from bluesky_queueserver_api.zmq.aio import REManagerAPI

        async def testing():
            RM = REManagerAPI()
            # < some useful code >
            await RE.close()

        asyncio.run(testing())
"""

_doc_REManagerAPI_HTTP = """
    API for communication with RE Manager using HTTP (RESTful API) protocol.

    Parameters
    ----------
    http_server_uri: str or None
        URI of Bluesky HTTP Server. If ``None``, then the default URI
        `"http://localhost:60610"`` is used.
    timeout: float
        Request timeout. Default value is 5.0 seconds.
    request_fail_exceptions: boolean
        If ``True`` (default) then API functions that communicate with
        RE Manager are raising the ``RequestFailError`` exception if
        the request is rejected (the response contains ``"success": False``,
        e.g. if a submitted plan is rejected). If ``False``, then API
        functions are always returning the response and user code is
        responsible for checking and processing the ``success`` flag.
    status_expiration_period: float
        Expiration period for cached RE Manager status,
        default value: 0.5 seconds
    status_polling_period: float
        Polling period for RE Manager status used by 'wait' operations,
        default value: 1 second
    loop: asyncio.Loop
        ``asyncio`` event loop (use only with Async version of the API).
        The parameter is included only for compatibility with 0MQ version
        of the API and is ignored in HTTP version.

    Examples
    --------

    Synchronous API:

    .. code-block:: python

        from bluesky_queueserver_api.http import REManagerAPI
        RM = REManagerAPI()
        # < some useful code >
        RE.close()

    Asynchronous API:

    .. code-block:: python

        from bluesky_queueserver_api.http.aio import REManagerAPI

        async def testing():
            RM = REManagerAPI()
            # < some useful code >
            await RE.close()

        asyncio.run(testing())
"""


_doc_send_request = """
    Send request to RE Manager and receive the response. The function directly passes
    the request to low-level Queue Server API. The detailed description of available
    methods, including names, parameters and returned values, can be found in Queue
    Server API reference. The function may raise exceptions in case of request timeout
    or failure.

    Parameters
    ----------
    method: str
        Name of the API method
    params: dict or None, optional
        Dictionary of API parameters or ``None`` if no parameters are passed.

    Returns
    -------
    dict
        Dictionary with the returned results.

    Raises
    ------
    RequestTimeoutError
        Request timed out.
    RequestFailedError
        Request failed (``response["success"]==False``).
    RequestError, ClientError
        Error while processing the request or communicating with the server. Raised only
        for HTTP requests.

    Examples
    --------

    .. code-block:: python

        # Synchronous code (0MQ)
        from bluesky_queueserver_api.zmq import REManagerAPI
        RM = REManagerAPI()
        status = RM.send_request(method="status")
        RM.close()

        # Synchronous code (HTTP)
        from bluesky_queueserver_api.http import REManagerAPI
        RM = REManagerAPI()
        status = RM.send_request(method="status")
        RM.close()

        # Asynchronous code (0MQ)
        from bluesky_queueserver_api.zmq.aio import REManagerAPI
        RM = REManagerAPI()
        status = await RM.send_request(method="status")
        await RM.close()

        # Asynchronous code, (HTTP)
        from bluesky_queueserver_api.http.aio import REManagerAPI
        RM = REManagerAPI()
        status = await RM.send_request(method="status")
        await RM.close()
"""

_doc_close = """
    Close RE Manager client.

    Examples
    --------

    .. code-block:: python

        # Synchronous code (0MQ and HTTP)
        RM.close()

        # Asynchronous code (0MQ and HTTP)
        await RM.close()
"""

_doc_api_status = """
    Load status of RE Manager. The function returns status or raises exception if
    operation failed (e.g. timeout occurred).

    Parameters
    ----------
    reload: boolean
        Immediately reload status (``True``) or return cached status if it
        is not expired (``False``). Calling the API with ``reload=True`` always
        initiates communication with the server.

    Returns
    -------
    dict
        Copy of the dictionary with RE Manager status.

    Raises
    ------
        Reraises the exceptions raised by ``send_request`` API.

    Examples
    --------

    .. code-block:: python

        # Synchronous code (0MQ and HTTP)
        status = RM.status()
        assert status["manager_state"] == "idle"

        # Asynchronous code (0MQ and HTTP)
        status = await RM.status()
        assert status["manager_state"] == "idle"
"""

_doc_api_ping = """
    Current implementation of the API loads status of RE Manager, but this may change
    in future releases. The function returns status or raises exception if operation
    failed (e.g. timeout occurred). See documentation for ``status`` API.
"""

_doc_api_wait_for_idle = """
    Wait for RE Manager to return to ``idle`` state. The function performs
    periodic polling of RE Manager status and returns when ``manager_state``
    status flag is ``idle``. Polling period is determined by ``status_polling_period``
    parameter of ``REManagerAPI`` class. The function raises ``WaitTimeoutError``
    if timeout occurs or ``WaitCancelError`` if wait operation was cancelled by
    ``monitor.cancel()``. See instructions on ``WaitMonitor`` class, which allows
    cancelling wait operations (from a different thread or task), modify timeout
    and monitoring the progress.

    Synchronous version of ``wait_for_idle`` is threadsafe. Multiple instances
    may run simultanously in multiple threads (sync) or tasks (async). Results
    of polling RE Manager status are shared between multiple running instances.

    Parameters
    ----------
    timeout: float
        Timeout for the wait operation. Default timeout: 60 seconds.
    monitor: bluesky_queueserver_api.WaitMonitor or None
        Instance of ``WaitMonitor`` object. The object is created internally if
        the parameter is ``None``.

    Returns
    -------
    None

    Raises
    ------
    REManagerAPI.WaitTimeoutError, REManagerAPI.WaitCancelError

    Examples
    --------

    .. code-block:: python

        # Synchronous code (0MQ, HTTP)
        RM.queue_start()
        try:
            RM.wait_for_idle(timeout=120)  # Wait for 2 minutes
            # < queue is completed or stopped, RE Manager is idle >
        except RM.WaitTimeoutError:
            # < process timeout error, RE Manager is probably not idle >

        # Aynchronous code (0MQ, HTTP)
        await RM.queue_start()
        try:
            await RM.wait_for_idle(timeout=120)  # Wait for 2 minutes
            # < queue is completed or stopped, RE Manager is idle >
        except RM.WaitTimeoutError:
            # < process timeout error, RE Manager is probably not idle >
"""

_doc_api_wait_for_idle_or_paused = """
    Wait for RE Manager to switch to ``idle`` or ``paused`` state. See the description
    of ``wait_for_idle`` API for more details.
"""

_doc_api_item_add = """
    Add item to the queue. The item may be a plan or an instruction represented
    as a dictionary or as an instance of ``BItem``, ``BPlan`` or ``BInst`` classes.
    By default the item is added to the back of the queue. Alternatively
    the item can be placed at the desired position in the queue or before
    or after one of the existing items. The parameters ``pos``, ``before_uid`` and
    ``after_uid`` are mutually exclusive, i.e. only one of the parameters may
    have a value different from ``None``.

    Parameters
    ----------
    item: dict, BItem, BPlan or BInst
        Dictionary or an instance of ``BItem``, ``BPlan`` or ``BInst`` representing
        a plan or an instruction.
    pos: str, int or None
        Position of the item in the queue. RE Manager will attempt to insert the
        item at the specified position. The position may be positive or negative
        (counted from the back of the queue) integer. If ``pos`` value is a string
        ``"front"`` or ``"back"``, then the item is inserted at the front or the back
        of the queue. If the value is ``None``, then the position is not specified.
    before_uid, after_uid: str or None
        Insert the item before or after the item with the given item UID. If ``None``
        (default), then the parameters are not specified.

    Returns
    -------
    dict
        Dictionary with item parameters. Dictionary keys: ``success`` (*boolean*),
        ``msg`` (*str*) - error message in case the request was rejected by RE Manager,
        ``qsize`` (*int* or *None*) - new size of the queue or *None* if operation
        failed, ``item`` (*dict* or *None*) - inserted item with assigned UID.
        If the request is rejected, ``item`` may contain the copy of the submitted
        item (with assigned UID), *None* or be missing depending on the failure.

    Raises
    ------
    Reraises the exceptions raised by ``send_request`` API.

    Examples
    --------

    .. code-block:: python

        # Synchronous code (0MQ, HTTP)
        # Add an item to the back of the queue
        RM.item_add({"item_type": "plan", "name": "count", "args": [["det1"]]})
        # Add an item to the front of the queue
        RM.item_add(BItem("plan", "count", ["det1"], num=10, delay=1), pos="front")
        RM.item_add(BItem("plan", "count", ["det1"], num=10, delay=1), pos=0)
        # Insert an item to the position #5 (numbers start from 0)
        RM.item_add(BPlan("count", ["det1"], num=10, delay=1), pos=5)
        # Insert an item before the last item
        RM.item_add(BPlan("count", ["det1"], num=10, delay=1), pos=-1)

        try:
            response = RM.item_add(BPlan("count", ["det1"], num=10, delay=1))
            # No exception was raised, so the request was successful
            assert response["success"] == True
            assert response["msg"] == ""
            # Print some parameters
            print(f"qsize = {response['qsize']}")
            print(f"item = {response['item']}")

            # Insert another plan before the plan that was just inserted
            item_uid = response["item"]["item_uid"]
            RM.item_add(BPlan("count", ["det1"], num=10, delay=1), before_uid=item_uid)
        except RM.RequestFailedError as ex:
            print(f"Request was rejected: {ex}")
            # < code that processes the error >

        # Asynchronous code (0MQ, HTTP)
        # Add an item to the back of the queue
        await RM.item_add({"item_type": "plan", "name": "count", "args": [["det1"]]})
        # Add an item to the front of the queue
        await RM.item_add(BItem("plan", "count", ["det1"], num=10, delay=1), pos="front")
        await RM.item_add(BItem("plan", "count", ["det1"], num=10, delay=1), pos=0)
        # Insert an item to the position #5 (numbers start from 0)
        await RM.item_add(BPlan("count", ["det1"], num=10, delay=1), pos=5)
        # Insert an item before the last item
        await RM.item_add(BPlan("count", ["det1"], num=10, delay=1), pos=-1)
"""

_doc_api_item_add_batch = """
    Add a batch of items to the queue. The batch is represented as a list of items.
    Each item may be a plan or an instruction represented as a dictionary or as an
    instance of ``BItem``, ``BPlan`` or ``BInst`` classes. If one of plans in
    the batch can not be added to the queue (e.g. it does not pass validation),
    then the whole batch is rejected. See documentation for ``item_add`` API
    for more detailed information.

    Parameters
    ----------
    items: list(dict), list(BItem), list(BPlan) or list(BInst)
        A list of dictionary or instances of ``BItem``, ``BPlan`` or ``BInst``
        representing a plan or an instruction.
    pos: str, int or None
        Position of the first item of the batch in the queue. RE Manager will attempt
        to insert the batch so that the first item is at the specified position.
        The position may be positive or negative (counted from the back of the queue)
        integer. If ``pos`` value is a string ``"front"`` or ``"back"``, then the item
        is inserted at the front or the back of the queue. If the value is ``None``,
        then the position is not specified.
    before_uid, after_uid: str or None
        Insert the batch of items before or after the item with the given item UID.
        If ``None`` (default), then the parameters are not specified.

    Returns
    -------
    dict
        Dictionary with item parameters. Dictionary keys: ``success`` (*boolean*),
        ``msg`` (*str*) - error message in case the request was rejected by RE Manager,
        ``qsize`` (*int* or *None*) - new size of the queue or *None* if operation
        failed, ``items`` (*list(dict)* or *None*) - the list of inserted item with
        assigned UID. If the request is rejected, ``item`` may contain the copy of
        the list of submitted items (with assigned UID), *None* or be missing depending
        on the failure.

    Raises
    ------
    Reraises the exceptions raised by ``send_request`` API.

    Examples
    --------

    .. code-block:: python

        plan1 = BPlan("count", ["det1"], num=10, delay=1)
        plan2 = BPlan("count", ["det1"], num=15, delay=1)

        # Synchronous code (0MQ, HTTP)
        RM.item_add_batch([plan1, plan2])

        # Asynchronous code (0MQ, HTTP)
        await RM.item_add_batch([plan1, plan2])
"""

_doc_api_item_update = """
    Update the existing item in the queue. The method is intended for editing queue
    items, but may be used for replacing the existing items with completely different
    ones. The updated item may be a plan or an instruction. The item parameter
    ``item_uid`` must be set to a UID of an existing queue item that is expected
    to be replaced. The method fails if the item UID is not found. By default,
    the UID of the updated item is not changed and ``user`` and ``user_group``
    parameters are set to the values provided in the request. The ``user_group``
    is also used for validation of submitted item. If it is preferable to replace
    the item UID with a new random UID (e.g. if the item is replaced with completely
    different item), the method should be called with the optional parameter
    ``replace=True``.

    Parameters
    ----------
    item: dict, BItem, BPlan or BInst
        Dictionary or an instance of ``BItem``, ``BPlan`` or ``BInst`` representing
        a plan or an instruction.
    replace: boolean
        Replace the updated item UID with the new random UID (``True``) or keep
        the original UID (``False``). Default value is (``False``).

    Returns
    -------
    dict
        Dictionary with item parameters. Dictionary keys: ``success`` (*boolean*),
        ``msg`` (*str*) - error message in case the request was rejected by RE Manager,
        ``qsize`` (*int* or *None*) - the size of the queue or *None* if operation
        failed, ``item`` (*dict* or *None*) - inserted item with assigned UID.
        If the request is rejected, ``item`` may contain the copy of the submitted
        item (with assigned UID), *None* or be missing depending on the failure.

    Raises
    ------
    Reraises the exceptions raised by ``send_request`` API.

    Examples
    --------

    .. code-block:: python

        # Synchronous code (0MQ, HTTP)
        RM.item_add(BPlan("count", ["det1"], num=10, delay=1), pos="back")
        response = RM.item_get(pos="back")
        item = BItem(response["item"])
        item.kwargs["num"] = 50
        RM.item_update(item)

        # Asynchronous code (0MQ, HTTP)
        await RM.item_add(BPlan("count", ["det1"], num=10, delay=1), pos="back")
        response = await RM.item_get(pos="back")
        item = BItem(response["item"])
        item.kwargs["num"] = 50
        await RM.item_update(item)
"""

_doc_api_item_get = """
    Load an existing queue item. Items may be addressed by position or UID.
    Bu default, the API returns the item at the back of the queue.

    Parameters
    ----------
    pos: str, int or None
        Position of the item in the queue. The position may be positive or negative
        (counted from the back of the queue) integer. If ``pos`` value is a string
        ``"front"`` or ``"back"``, then the item at the front or the back of the queue
        is returned. If the value is ``None`` (default), then the position is not specified.
    uid: str or None
        UID of the item. If ``None`` (default), then the parameter are not specified.

    Returns
    -------
    dict
        Dictionary with item parameters. Dictionary keys: ``success`` (*boolean*),
        ``msg`` (*str*) - error message in case the request was rejected by RE Manager,
        ``item`` (*dict*) - the dictionary of item parameters, which is ``{}`` if
        the operation fails.

    Raises
    ------
    Reraises the exceptions raised by ``send_request`` API.

    Examples
    --------

    .. code-block:: python

        # Synchronous code (0MQ, HTTP)
        RM.item_get()
        RM.item_get(pos="front")
        RM.item_get(pos=-2)

        # Asynchronous code (0MQ, HTTP)
        await RM.item_get()
        await RM.item_get(pos="front")
        await RM.item_get(pos=-2)
"""

_doc_api_item_remove = """
    Remove item from the queue. By default the last item in the queue is removed.
    Alternatively the position or UID of the item can be specified.

    Parameters
    ----------
    pos: str, int or None
        Position of the item in the queue. The position may be positive or negative
        (counted from the back of the queue) integer. If ``pos`` value is a string
        ``"front"`` or ``"back"``, then the item at the front or the back of the queue
        is returned. If the value is ``None`` (default), then the position is not specified.
    uid: str or None
        UID of the item. If ``None`` (default), then the parameter are not specified.

    Returns
    -------
    dict
        Dictionary with item parameters. Dictionary keys: ``success`` (*boolean*),
        ``msg`` (*str*) - error message in case the request was rejected by RE Manager,
        ``item`` (*dict*) - the dictionary of item parameters, which is ``{}`` if
        the operation fails, ``qsize`` - the size of the queue.

    Raises
    ------
    Reraises the exceptions raised by ``send_request`` API.

    Examples
    --------

    .. code-block:: python

        # Synchronous code (0MQ, HTTP)
        RM.item_remove()
        RM.item_remove(pos="front")
        RM.item_remove(pos=-1)

        # Asynchronous code (0MQ, HTTP)
        await RM.item_remove()
        await RM.item_remove(pos="front")
        await RM.item_remove(pos=-1)
"""

_doc_api_item_remove_batch = """
    Remove a batch of items from the queue. The batch of items is represented
    as a list of item UIDs.

    Parameters
    ----------
    uids: list(str)
        List of UIDs of the items in the batch. The list may not contain repeated UIDs.
        All UIDs must be present in the queue. The list may be empty.
    ignore_missing: boolean (optional)
        If the value is ``False``, then the method fails if the batch contains repeating
        items or some of the batch items are not found in the queue. If ``True`` (default),
        then the method attempts to remove all items in the batch and ignores missing
        items. The method returns the list of items that were removed from the queue.

    Returns
    -------
    dict
        Dictionary with item parameters. Dictionary keys: ``success`` (*boolean*),
        ``msg`` (*str*) - error message in case the request was rejected by RE Manager,
        ``items`` (*list(dict)*) - the list of removed items, which is ``[]`` if
        the operation fails, ``qsize`` - the size of the queue.

    Raises
    ------
    Reraises the exceptions raised by ``send_request`` API.

    Examples
    --------

    .. code-block:: python

        # Synchronous code (0MQ, HTTP)
        RM.item_remove_batch(["item-uid1", "item-uid2"])

        # Asynchronous code (0MQ, HTTP)
        await RM.item_remove_batch(["item-uid1", "item-uid2"])
"""

_doc_api_item_move = """
    Move item to a different position in the queue. The parameters ``pos`` and
    ``uid`` are mutually exclusive. The parameters ``pos_dest``, ``before_uid``
    and ``after_uid`` are also mutually exclusive.

    Parameters
    ----------
    pos: str, int or None
        Position of the item in the queue. The position may be positive or negative
        (counted from the back of the queue) integer. If ``pos`` value is a string
        ``"front"`` or ``"back"``, then the item at the front or the back of the queue
        is returned. If the value is ``None`` (default), then the position is not specified.
    uid: str or None
        UID of the item to move. If ``None`` (default), then the parameter are not specified.
    pos_dest: str, int or None
        New position of the item. Integer number can be negative.
    before_uid, after_uid: str or None
        UID of an existing item in the queue. The selected item is moved before
        or after this item.

    Returns
    -------
    dict
        Dictionary with item parameters. Dictionary keys: ``success`` (*boolean*),
        ``msg`` (*str*) - error message in case the request was rejected by RE Manager,
        ``item`` (*dict*) - the dictionary of item parameters, which is ``{}`` if
        the operation fails, ``qsize`` - the size of the queue.

    Raises
    ------
    Reraises the exceptions raised by ``send_request`` API.

    Examples
    --------

    .. code-block:: python

        # Synchronous code (0MQ, HTTP)
        RM.item_move(pos="front", pos_dest="5")
        RM.item_move(uid="uid-source", before_uid="uid-dest")

        # Asynchronous code (0MQ, HTTP)
        await RM.item_move(pos="front", pos_dest="5")
        await RM.item_move(uid="uid-source", before_uid="uid-dest")
"""

_doc_api_item_move_batch = """
    Move a batch of item to a different position in the queue. The method accepts
    a list of UIDs of the items included in the batch. The UIDs in the list must
    be unique (not repeated) and items with listed UIDs must exist in the queue.
    If the list is empty, then operation succeeds and the queue remains unchanged.
    The destination must be specified using one of the mutually exclusive parameters
    ``pos_dest``, ``before_uid`` or ``after_uid``. The reference item with the UID
    of passed with the parameters ``before_uid`` or ``after_uid`` must not be
    in the batch. The parameter ``reorder`` controls the order of the items in
    the moved batch and indicates whether items in the batch should be reordered
    with respect to the order of UIDs in the list ``uids``. The batch may include
    any set of non-repeated items from the queue arranged in arbitrary order.
    By default (``reorder=False``) the batch is inserted in the specified position
    as a contiguous sequence of items ordered according to the UIDs in the list
    ``uids``. If ``reorder=True``, then the inserted items are ordered according
    to their original positions in the queue. It is assumed that the method will
    be mostly used with the default ordering option and user will be responsible
    for creating properly ordered lists of items. The other option is implemented
    for the cases when the user may want to submit randomly ordered lists of UIDs,
    but preserve the original order of the moved batch.

    Parameters
    ----------
    uids: list(str)
        List of UIDs of the items in the batch. The list may not contain repeated UIDs.
        All UIDs must be present in the queue. The list may be empty.
    pos_dest: str ("front" or "back")
        New position of the item. Only string values ``'front'`` and ``'back'``
        are accepted.
    before_uid, after_uid: str or None
        UID of an existing item in the queue. The selected item will be moved before
        or after this item. The item with the specified UID may not be included
        in the batch.
    reorder: boolean
        Arrange moved items in the order of UIDs in the ``uids`` list (False, default) or
        according to the original item positions in the queue (True).

    Returns
    -------
    dict
        Dictionary with item parameters. Dictionary keys: ``success`` (*boolean*),
        ``msg`` (*str*) - error message in case the request was rejected by RE Manager,
        ``items`` (*list(dict)*) - the list of moved items, which is ``[]`` if
        the operation fails, ``qsize`` - the size of the queue.

    Raises
    ------
    Reraises the exceptions raised by ``send_request`` API.

    Examples
    --------

    .. code-block:: python

        # Synchronous code (0MQ, HTTP)
        RM.item_move_batch(uids=["uid1", "uid2"], pos_dest="front")
        RM.item_move_batch(uids=["uid1", "uid2"], before_uid="uid-dest")

        # Asynchronous code (0MQ, HTTP)
        await RM.item_move_batch(uids=["uid1", "uid2"], pos_dest="front")
        await RM.item_move_batch(uids=["uid1", "uid2"], before_uid="uid-dest")
"""


_doc_api_item_execute = """
    Immediately start execution of the submitted item. The item may be a plan or
    an instruction. The request fails if item execution can not be started immediately
    (RE Manager is not in IDLE state, RE Worker environment does not exist, etc.).
    If the request succeeds, the item is executed once. The item is not added to
    the queue if it can not be immediately started and it is not pushed back into
    the queue in case its execution fails/stops. If the queue is in the LOOP mode,
    the executed item is not added to the back of the queue after completion.
    The API request does not alter the sequence of enqueued plans.

    Parameters
    ----------
    item: dict, BItem, BPlan or BInst
        Dictionary or an instance of ``BItem``, ``BPlan`` or ``BInst`` representing
        a plan or an instruction.

    Returns
    -------
    dict
        Dictionary with item parameters. Dictionary keys: ``success`` (*boolean*),
        ``msg`` (*str*) - error message in case the request was rejected by RE Manager,
        ``item`` (*dict*) - the dictionary of item parameters, ``None`` if the
        request contains no ``item`` parameter, ``qsize`` - the size of the queue.

    Raises
    ------
    Reraises the exceptions raised by ``send_request`` API.

    Examples
    --------

    .. code-block:: python

        # Synchronous code (0MQ, HTTP)
        RM.item_execute(BPlan("count", ["det1"], num=10, delay=1))

        # Asynchronous code (0MQ, HTTP)
        await RM.item_execute(BPlan("count", ["det1"], num=10, delay=1))
"""


_doc_api_queue_start = """
    Start execution of the queue. If the request is accepted, the ``manager_state``
    status parameter is expected to change to ``starting_queue``, then ``executing_queue``
    and change back to ``idle`` when the queue is completed or stopped.

    Returns
    -------
    dict
        Dictionary keys: ``success`` (*boolean*), ``msg`` (*str*) - error message
        in case the request was rejected by RE Manager.

    Raises
    ------
    Reraises the exceptions raised by ``send_request`` API.

    Examples
    --------

    .. code-block:: python

        # Synchronous code (0MQ, HTTP)
        RM.queue_start()

        # Asynchronous code (0MQ, HTTP)
        await RM.queue_start()
"""

_doc_api_queue_stop = """
    Request RE Manager to stop execution of the queue after completion of the currently
    running plan. The request succeeds only if the queue is currently running (``manager_state``
    status field has value ``executing_queue``). The ``queue_stop_pending`` status field
    can be used at any time to verify if the request is pending.

    Returns
    -------
    dict
        Dictionary keys: ``success`` (*boolean*), ``msg`` (*str*) - error message
        in case the request was rejected by RE Manager.

    Raises
    ------
    Reraises the exceptions raised by ``send_request`` API.

    Examples
    --------

    .. code-block:: python

        # Synchronous code (0MQ, HTTP)
        RM.queue_stop()

        # Asynchronous code (0MQ, HTTP)
        await RM.queue_stop()
"""


_doc_api_queue_stop_cancel = """
    Cancel the pending request to stop execution of the queue after the currently running plan.

    Returns
    -------
    dict
        Dictionary keys: ``success`` (*boolean*), ``msg`` (*str*) - error message
        in case the request was rejected by RE Manager.

    Raises
    ------
    Reraises the exceptions raised by ``send_request`` API.

    Examples
    --------

    .. code-block:: python

        # Synchronous code (0MQ, HTTP)
        RM.queue_stop_cancel()

        # Asynchronous code (0MQ, HTTP)
        await RM.queue_stop_cancel()
"""


_doc_api_queue_clear = """
    Remove all items from the plan queue. The currently running plan does not belong
    to the queue and is not affected by this operation. If the plan fails or its
    execution is stopped, it will be pushed to the beginning of the queue.

    Returns
    -------
    dict
        Dictionary keys: ``success`` (*boolean*), ``msg`` (*str*) - error message
        in case the request was rejected by RE Manager.

    Raises
    ------
    Reraises the exceptions raised by ``send_request`` API.

    Examples
    --------

    .. code-block:: python

        # Synchronous code (0MQ, HTTP)
        RM.queue_clear()

        # Asynchronous code (0MQ, HTTP)
        await RM.queue_clear()
"""


_doc_api_queue_mode_set = """
    Sets parameters that define the mode of plan queue execution. Individual
    mode parameters may be changed by using respective kwargs (currently only
    ``loop`` parameter is supported) or passing dictionary using ``mode`` kwarg.
    The mode may be reset to default by passing ``mode="default"``. If ``mode``
    kwarg is used, other kwargs are ignored.

    Parameters
    ----------
    mode: dict or str
        Pass dictionary with mode parameters that need to be changed or ``"default"``
        to reset all mode parameters to default values. All other kwargs are
        ignored if ``mode`` kwarg is passed.
    loop: boolean
        Turns **loop** mode ON and OFF

    Returns
    -------
    dict
        Dictionary keys: ``success`` (*boolean*), ``msg`` (*str*) - error message
        in case the request was rejected by RE Manager.

    Raises
    ------
    Reraises the exceptions raised by ``send_request`` API.

    Examples
    --------

    .. code-block:: python

        # Synchronous code (0MQ, HTTP)
        RM.queue_mode_set(loop=True)
        RM.queue_mode_set(mode={"loop": True})
        RM.queue_mode_set(mode="default")

        # Asynchronous code (0MQ, HTTP)
        await RM.queue_mode_set(loop=True)
        await RM.queue_mode_set(mode={"loop": True})
        await RM.queue_mode_set(mode="default")
"""


_doc_api_queue_get = """
    Returns the list of items (plans and instructions) in the plan queue and currently running plan.
    The function downloads the queue from the server if ``plan_queue_uid`` has changed, otherwise
    the cached copy of the queue is returned.

    Parameters
    ----------
    reload: boolean
        Status data is always reloaded from the server if ``True``, otherwise the cached
        status is used to verify `plan_queue_uid`` if cache is up to date.

    Returns
    -------
    dict
        Dictionary keys: ``success`` (*boolean*), ``msg`` (*str*) - error message
        in case the request was rejected by RE Manager, ``items`` - a list of queue items,
        ``running_item`` - a dictionary with parameters of currently running plan (``{}`` if
        the queue is not running), ``plan_queue_uid`` - UID of the plan queue.

    Raises
    ------
    Reraises the exceptions raised by ``send_request`` API.

    Examples
    --------

    .. code-block:: python

        # Synchronous code (0MQ, HTTP)
        response = RM.queue_get()
        queue_items = response["items"]
        running_item = response["running_item"]
        queue_uid = response["plan_queue_uid"]

        # Asynchronous code (0MQ, HTTP)
        response = await RM.queue_get()
        queue_items = response["items"]
        running_item = response["running_item"]
        queue_uid = response["plan_queue_uid"]
"""

_doc_api_history_get = """
    Returns the list of plans in the history. The function downloads the history from the server
    if ``plan_history_uid`` has changed, otherwise the cached copy of the queue is returned.

    Parameters
    ----------
    reload: boolean
        Status data is always reloaded from the server if ``True``, otherwise the cached
        status is used to verify `plan_history_uid`` if cache is up to date.

    Returns
    -------
    dict
        Dictionary keys: ``success`` (*boolean*), ``msg`` (*str*) - error message
        in case the request was rejected by RE Manager, ``items`` - a list of history items,
        ``plan_history_uid`` - UID of the plan history.

    Raises
    ------
    Reraises the exceptions raised by ``send_request`` API.

    Examples
    --------

    .. code-block:: python

        # Synchronous code (0MQ, HTTP)
        response = RM.history_get()
        history_items = response["items"]
        history_uid = response["plan_history_uid"]

        # Asynchronous code (0MQ, HTTP)
        response = await RM.history_get()
        history_items = response["items"]
        history_uid = response["plan_history_uid"]
"""


_doc_api_history_clear = """
    Remove all items from the history.

    Returns
    -------
    dict
        Dictionary keys: ``success`` (*boolean*), ``msg`` (*str*) - error message
        in case the request was rejected by RE Manager.

    Raises
    ------
    Reraises the exceptions raised by ``send_request`` API.

    Examples
    --------

    .. code-block:: python

        # Synchronous code (0MQ, HTTP)
        RM.history_clear()

        # Asynchronous code (0MQ, HTTP)
        await RM.history_clear()
"""

_doc_api_plans_allowed = """
    Returns the list (dictionary) of allowed plans. The function downloads the list of allowed plans
    from the server if ``plans_allowed_uid`` has changed, otherwise the cached copy is returned.

    Parameters
    ----------
    reload: boolean
        Status data is always reloaded from the server if ``True``, otherwise the cached
        status is used to verify `plans_allowed_uid`` if cache is up to date.

    Returns
    -------
    dict
        Dictionary keys: ``success`` (*boolean*), ``msg`` (*str*) - error message
        in case the request was rejected by RE Manager, ``plans_allowed`` - a dictionary of
        allowed plans, `plans_allowed_uid`` - UID of the dictionary of allowed plans.

    Raises
    ------
    Reraises the exceptions raised by ``send_request`` API.

    Examples
    --------

    .. code-block:: python

        # Synchronous code (0MQ, HTTP)
        response = RM.plans_allowed()
        plans_allowed = response["plans_allowed"]

        # Asynchronous code (0MQ, HTTP)
        response = await RM.plans_allowed()
        plans_allowed = response["plans_allowed"]
"""

_doc_api_devices_allowed = """
    Returns the list (dictionary) of allowed devices. The function downloads the list of allowed
    devices the server if ``devices_allowed_uid`` has changed, otherwise the cached copy is returned.

    Parameters
    ----------
    reload: boolean
        Status data is always reloaded from the server if ``True``, otherwise the cached
        status is used to verify `plans_allowed_uid`` if cache is up to date.

    Returns
    -------
    dict
        Dictionary keys: ``success`` (*boolean*), ``msg`` (*str*) - error message
        in case the request was rejected by RE Manager, ``devices_allowed`` - a dictionary of
        allowed devices, `devices_allowed_uid`` - UID of the dictionary of allowed devices.

    Raises
    ------
    Reraises the exceptions raised by ``send_request`` API.

    Examples
    --------

    .. code-block:: python

        # Synchronous code (0MQ, HTTP)
        response = RM.devices_allowed()
        devices_allowed = response["devices_allowed"]

        # Asynchronous code (0MQ, HTTP)
        response = await RM.devices_allowed()
        devices_allowed = response["devices_allowed"]
"""

_doc_api_plans_existing = """
    Returns the list (dictionary) of existing plans. The function downloads the list of existing plans
    from the server if ``plans_allowed_uid`` has changed, otherwise the cached copy is returned.

    Parameters
    ----------
    reload: boolean
        Status data is always reloaded from the server if ``True``, otherwise the cached
        status is used to verify `plans_existing_uid`` if cache is up to date.

    Returns
    -------
    dict
        Dictionary keys: ``success`` (*boolean*), ``msg`` (*str*) - error message
        in case the request was rejected by RE Manager, ``plans_existing`` - a dictionary of
        existing plans, `plans_existing_uid`` - UID of the dictionary of allowed plans.

    Raises
    ------
    Reraises the exceptions raised by ``send_request`` API.

    Examples
    --------

    .. code-block:: python

        # Synchronous code (0MQ, HTTP)
        response = RM.plans_existing()
        plans_existing = response["plans_existing"]

        # Asynchronous code (0MQ, HTTP)
        response = await RM.plans_existing()
        plans_existing = response["plans_existing"]
"""

_doc_api_devices_existing = """
    Returns the list (dictionary) of existing devices. The function downloads the list of existing
    devices the server if ``devices_existing_uid`` has changed, otherwise the cached copy is returned.

    Parameters
    ----------
    reload: boolean
        Status data is always reloaded from the server if ``True``, otherwise the cached
        status is used to verify `plans_existing_uid`` if cache is up to date.

    Returns
    -------
    dict
        Dictionary keys: ``success`` (*boolean*), ``msg`` (*str*) - error message
        in case the request was rejected by RE Manager, ``devices_existing`` - a dictionary of
        existing devices, `devices_existing_uid`` - UID of the dictionary of existing devices.

    Raises
    ------
    Reraises the exceptions raised by ``send_request`` API.

    Examples
    --------

    .. code-block:: python

        # Synchronous code (0MQ, HTTP)
        response = RM.devices_existing()
        devices_existing = response["devices_existing"]

        # Asynchronous code (0MQ, HTTP)
        response = await RM.devices_existing()
        devices_existing = response["devices_existing"]
"""

_doc_api_permissions_reload = """
    Reload user group permissions from the default location or the location set using
    command line parameters and generate lists of allowed plans and devices based on
    the lists of existing plans and devices. By default, the method will use current
    lists of existing plans and devices stored in memory. Optionally the method can
    reload the lists from the disk file (see reload_plans_devices parameter).
    The method always updates UIDs of the lists of allowed plans and devices even
    if the contents remain the same.

    Parameters
    ----------
    reload_plans_devices: boolean (optional)
        Reload the lists of existing plans and devices from disk if True, otherwise
        use current lists stored in memory. Default: False.
    reload_permissions: boolean (optional)
        Reload user group permissions from disk if True, otherwise use current
        permissions. Default: True.

    Returns
    -------
    dict
        Dictionary keys: ``success`` (*boolean*), ``msg`` (*str*) - error message
        in case the request was rejected by RE Manager.

    Raises
    ------
    Reraises the exceptions raised by ``send_request`` API.

    Examples
    --------

    .. code-block:: python

        # Synchronous code (0MQ, HTTP)
        RM.permissions_reload()

        # Asynchronous code (0MQ, HTTP)
        await RM.permissions_reload()
"""


_doc_api_permissions_get = """
    Download the dictionary of user group permissions currently used by RE Manager.

    Returns
    -------
    dict
        Dictionary keys: ``success`` (*boolean*), ``msg`` (*str*) - error message
        in case the request was rejected by RE Manager, ``user_group_permission`` -
        the dictionary of user group permissions.

    Raises
    ------
    Reraises the exceptions raised by ``send_request`` API.

    Examples
    --------

    .. code-block:: python

        # Synchronous code (0MQ, HTTP)
        response = RM.permissions_get()
        permissions = response["user_group_permissions"]

        # Asynchronous code (0MQ, HTTP)
        response = await RM.permissions_get()
        permissions = response["user_group_permissions"]
"""


_doc_api_permissions_set = """
    Uploads the dictionary of user group permissions. If the uploaded dictionary
    contains a valid set of permissions different from currently used one,
    the new permissions are set as current and the updated lists of allowed
    plans and devices are generated. The method does nothing if the uploaded
    permissions are identical to currently used permissions. The API request fails
    if the uploaded dictionary does not pass validation.

    Parameters
    ----------
    user_group_permissions: dict
        Dictionary, which contains user group permissions.

    Returns
    -------
    dict
        Dictionary keys: ``success`` (*boolean*), ``msg`` (*str*) - error message
        in case the request was rejected by RE Manager.

    Raises
    ------
    Reraises the exceptions raised by ``send_request`` API.

    Examples
    --------

    .. code-block:: python

        # Synchronous code (0MQ, HTTP)
        response = RM.permissions_get()
        permissions = response["user_group_permissions"]
        # < modify permissions >
        RM.permissions_get(permissions)

        # Asynchronous code (0MQ, HTTP)
        response = await RM.permissions_get()
        permissions = response["user_group_permissions"]
        # < modify permissions >
        await RM.permissions_get(permissions)
"""


_doc_api_environment_open = """
    Open RE Worker environment. The API request only initiates the operation of
    opening an environment. If the request is accepted, the ``manager_state``
    status parameter is expected to change to ``creating_environment`` and then
    changed back to ``idle`` when the operation is completed. Check
    ``worker_environment_exists`` to see if the environment was opened successfully.

    Returns
    -------
    dict
        Dictionary keys: ``success`` (*boolean*), ``msg`` (*str*) - error message
        in case the request was rejected by RE Manager.

    Raises
    ------
    Reraises the exceptions raised by ``send_request`` API.

    Examples
    --------

    .. code-block:: python

        # Synchronous code (0MQ, HTTP)
        RM.environment_open()

        # Asynchronous code (0MQ, HTTP)
        await RM.environment_open()
"""

_doc_api_environment_close = """
    Close RE Worker environment. The API request only initiates the operation of
    opening an environment. The environment can not be closed if any plans or
    foreground tasks are running. If the request is accepted, the ``manager_state``
    status parameter is expected to change to ``closing_environment`` and then
    back to ``idle`` when the operation is completed. Check ``worker_environment_exists``
    status flag to see if the environment was closed.

    Returns
    -------
    dict
        Dictionary keys: ``success`` (*boolean*), ``msg`` (*str*) - error message
        in case the request was rejected by RE Manager.

    Raises
    ------
    Reraises the exceptions raised by ``send_request`` API.

    Examples
    --------

    .. code-block:: python

        # Synchronous code (0MQ, HTTP)
        RM.environment_close()

        # Asynchronous code (0MQ, HTTP)
        await RM.environment_close()
"""

_doc_api_environment_destroy = """
    Destroy RE Worker environment. This is the last-resort operation that allows to
    recover the Queue Server if RE Worker environment becomes unresponsive and needs
    to be shut down. The operation kills RE Worker process, therefore it can be executed
    with the environment in any state. The operation may be dangerous, since it kills any
    running plans or tasks. After the operation is completed, a new environment
    may be opened and operations countinued. The API request only initiates the operation
    of destroying an environment. If the request is accepted, the ``manager_state``
    status parameter is expected to change to ``destroying_environment`` and then
    back to ``idle`` when the operation is completed. Check ``worker_environment_exists``
    status flag to see if the environment was destroyed.

    Returns
    -------
    dict
        Dictionary keys: ``success`` (*boolean*), ``msg`` (*str*) - error message
        in case the request was rejected by RE Manager.

    Raises
    ------
    Reraises the exceptions raised by ``send_request`` API.

    Examples
    --------

    .. code-block:: python

        # Synchronous code (0MQ, HTTP)
        RM.environment_destroy()

        # Asynchronous code (0MQ, HTTP)
        await RM.environment_destroy()
"""

_doc_api_script_upload = r"""
    Upload and execute script in RE Worker namespace. The script may add, change or
    replace objects defined in the namespace, including plans and devices. Dynamic
    modification of the worker namespace may be used to implement more flexible workflows.
    The API call updates the lists of existing and allowed plans and devices if necessary.
    Changes in the lists will be indicated by changed list UIDs. Use ``task_result`` API
    to check if the script was loaded correctly. Note, that if the task fails, the script
    is still executed to the point where the exception is raised and the respective changes
    to the environment are applied.

    Parameters
    ----------
    script: str
        The string that contains the Python script. The rules for the script are the same
        as for Bluesky startup scripts. The script can use objects already existing in
        the RE Worker namespace.
    update_re: boolean (optional, default False)
        The uploaded scripts may replace Run Engine (``RE``) and Data Broker (``db``)
        instances in the namespace. In most cases this operation should not be allowed,
        therefore it is disabled by default (``update_re`` is ``False``), i.e. if the script
        creates new ``RE`` and ``db`` objects, those objects are discarded. Set this parameter
        True to allow the server to replace RE and db objects. This parameter has no
        effect if the script is not creating new instances of ``RE`` and/or ``db``.
    run_in_background: boolean (optional, default False)
        Set this parameter True to upload and execute the script in the background
        (while a plan or another foreground task is running). Generally, it is not
        recommended to update RE Worker namespace in the background. Background tasks
        are executed in separate threads and only thread-safe scripts should be uploaded
        in the background. **Developers of data acquisition workflows and/or user specific
        code are responsible for thread safety.**

    Returns
    -------
    dict
        Dictionary keys: ``success`` (*boolean*), ``msg`` (*str*) - error message
        in case the request was rejected by RE Manager, ``task_uid`` - UID of the started
        task.

    Raises
    ------
    Reraises the exceptions raised by ``send_request`` API.

    Examples
    --------

    .. code-block:: python

        script = "def test_sleep():\n    yield from bps.sleep(5)\n"

        # Synchronous code (0MQ, HTTP)
        RM.script_upload(script)

        # Asynchronous code (0MQ, HTTP)
        await RM.script_upload(script)
"""

_doc_api_function_execute = """
    Start execution of a function in RE Worker namespace. The function must be defined in the
    namespace (in startup code or a script uploaded using *script_upload* method. The function
    may be executed as a foreground task (only if RE Manager and RE Worker environment are idle)
    or as a background task. Background tasks are executed in separate threads and may
    consume processing or memory resources and interfere with running plans or other tasks.
    RE Manager does not guarantee thread safety of the user code running in the background.
    Developers of startup code are fully responsible for preventing threading issues.

    The method allows to pass parameters (*args* and *kwargs*) to the function. Once the task
    is completed, the results of the function execution, including the return value, can be
    loaded using *task_result* method. If the task fails, the return value is a string
    with full traceback of the raised exception. The data types of parameters and return
    values must be JSON serializable. The task fails if the return value can not be serialized.

    The method only **initiates** execution of the function. If the request is successful
    (*success=True*), the server starts the task, which attempts to execute the function
    with given name and parameters. The function may still fail start (e.g. if the user is
    permitted to execute function with the given name, but the function is not defined
    in the namespace). Use *'task_result'* method with the returned *task_uid* to
    check the status of the tasks and load the result upon completion.

    Parameters
    ----------
    item: BItem, BFunc or dict
        BItem, BFunc or dictionary with function name, *args* and *kwargs*. The structure of
        dictionary is identical to item representing a plan or an instruction, except that
        ``item_type`` is ``"function"``.
    run_in_background: boolean (optional, default False)
        Set this parameter True to upload and execute the script in the background
        (while a plan or another foreground task is running). Generally, it is not
        recommended to update RE Worker namespace in the background. Background tasks
        are executed in separate threads and only thread-safe scripts should be uploaded
        in the background. **Developers of data acquisition workflows and/or user specific
        code are responsible for thread safety.**

    Returns
    -------
    dict
        Dictionary keys: ``success`` (*boolean*), ``msg`` (*str*) - error message
        in case the request was rejected by RE Manager, ``item`` - dictionary of function
        parameters (may be ``None`` if operation fails), ``task_uid`` - UID of the started task.

    Raises
    ------
    Reraises the exceptions raised by ``send_request`` API.

    Examples
    --------

    .. code-block:: python

        function = BFunc("function_sleep", 10)

        # Synchronous code (0MQ, HTTP)
        RM.function_execute(function)

        # Asynchronous code (0MQ, HTTP)
        await RM.function_execute(function)
"""


_doc_api_task_status = """
    Returns the status of one or more tasks executed by the worker process. The request
    must contain one or more valid task UIDs, returned by one of APIs that starts tasks.
    A single UID may be passed as a string, multiple UIDs must be passed as as a list
    of strings. If a UID is passed as a string, then the returned status is also a string,
    if a list of one or more UIDs is passed, then the status is a dictionary that maps
    task UIDs and their status. The completed tasks are stored at the server at least
    for the period determined by retention time (currently 120 seconds after completion
    of the task). The expired results could be automatically deleted at any time and
    the method will return the task status as ``"not_found"``.

    Parameters
    ----------
    task_uid: str or list(str)
        A single task UID (*str*) or a list of one or multiple UIDs.

    Returns
    -------
    dict
        Dictionary keys: ``success`` (*boolean*), ``msg`` (*str*) - error message
        in case the request was rejected by RE Manager, ``task_uid`` - returns UID(s)
        passed as input parameter, ``status`` - status of the task(s) or ``None``
        if the request (not task) failed. If task_uid is a string representing single UID,
        then status is a string that may be one of ``running``, ``completed`` or
        ``not_found``. If task_uid is a list of strings, then ``status`` is a dictionary
        that maps task UIDs to status of the respective tasks.

    Raises
    ------
    Reraises the exceptions raised by ``send_request`` API.

    Examples
    --------

    .. code-block:: python

        function = BFunc("function_sleep", 10)

        # Synchronous code (0MQ, HTTP)
        reply = RM.function_execute(function)
        task_uid = reply["task_uid"]
        # Status of a single task
        reply = RM.task_status(task_uid)
        task_status = reply["status"]
        # Same result, but allows to submit multiple task UIDs
        reply = RM.task_status([task_uid])
        task_status = reply["status"][task_uid]

        # Asynchronous code (0MQ, HTTP)
        await RM.function_execute(function)
        reply = await RM.function_execute(function)
        task_uid = reply["task_uid"]
        # Status of a single task
        reply = await RM.task_status(task_uid)
        task_status = reply["status"]
        # Same result, but allows to submit multiple task UIDs
        reply = await RM.task_status([task_uid])
        task_status = reply["status"][task_uid]
"""

_doc_api_task_result = """
    Get the status and results of task execution. The completed tasks are stored at
    the server at least for the period determined by retention time (currently
    120 seconds after completion of the task). The expired results could be
    automatically deleted at any time and the method will return the task status
    as ``not_found``.

    Parameters
    ----------
    task_uid: str
        A single task UID.

    Returns
    -------
    dict
        Dictionary keys:

        - **success**: *boolean* - success of the request.

        - **msg**: *str* - error message in case the request is rejected by RE Manager.

        - **task_uid**: *str* - task UID.

        - **status**: *str ("running", "completed", "not_found") or None* - status of the task
          or *None* if the request (not task) fails.

        - **result**: *dict or None* - dictionary containing the information on a running task,
          results of execution of the completed task or *None* if the request failed.
          The contents of the dictionary depends on the returned **status**: "running"
          (keys: **task_uid**, **start_time** and **run_in_background**), **completed** (keys:
          **task_uid**, **success** - True/False, **msg** - error message, **return_value** -
          value returned by the function or a string with full traceback if the task failed,
          **time_start** and **time_stop**), **not_found** - empty dictionary.

    Raises
    ------
    Exception
        Reraises the exceptions from ``send_request`` API.

    Examples
    --------

    .. code-block:: python

        function = BFunc("function_sleep", 10)

        # Synchronous code (0MQ, HTTP)
        reply = RM.function_execute(function)
        task_uid = reply["task_uid"]
        reply = RM.task_result(task_uid)
        task_status = reply["status"]
        task_result = reply["result"]

        # Asynchronous code (0MQ, HTTP)
        await RM.function_execute(function)
        reply = await RM.function_execute(function)
        task_uid = reply["task_uid"]
        reply = await RM.task_result(task_uid)
        task_status = reply["status"]
        task_result = reply["result"]
"""

_doc_api_re_runs = """
    Request the list of active runs generated by the currently executed plans. The full list
    of active runs includes the runs that are currently open (``open`` runs) and the runs
    that were already closed (``closed`` runs). Simple single-run plans will have at most one
    run in the list. Monitor ``run_list_uid`` RE Manager status field and retrieve the updated
    list once UID is changed. The UID of the retrieved list is included in the returned parameters

    Parameters
    ----------
    option: str (optional, 'active', 'open' or 'closed')
        Select between full list of ``active`` (default) runs, the list of ``open`` or
        ``closed`` runs.

    Returns
    -------
    dict
        Dictionary keys:

        - **success**: *boolean* - success of the request.

        - **msg**: *str* - error message in case the request is rejected by RE Manager.

        - **run_list**: *list(dict)* - the requested list of runs. List items are dictionaries
          with the following keys: **uid** (*str*), **is_open** (*boolean*) and **exit_status**
          (*str* or *None*). See Bluesky documentation for values of *exit_status*.

        - **run_list_uid**: *str*
          Run list UID.

    Raises
    ------
    Exception
        Reraises the exceptions from ``send_request`` API.

    Examples
    --------

    .. code-block:: python

        function = BFunc("function_sleep", 10)

        # Synchronous code (0MQ, HTTP)
        reply = RM.re_runs()          # Returns all active runs
        runs = reply["run_list"]

        reply = RM.re_runs("active")  # Returns all active runs
        reply = RM.re_runs("open")    # Returns open runs
        reply = RM.re_runs("closed")  # Returns closed runs

        # Asynchronous code (0MQ, HTTP)
        reply = await RM.re_runs()          # Returns all active runs
        runs = reply["run_list"]

        reply = await RM.re_runs("active")  # Returns all active runs
        reply = await RM.re_runs("open")    # Returns open runs
        reply = await RM.re_runs("closed")  # Returns closed runs
"""

_doc_api_re_pause = """
    Request Run Engine to pause currently running plan. The request fails if RE Worker
    environment does not exist or no plan is currently running. The request only initates
    the sequence of pausing the plan.

    If deferred pause is requested past the last checkpoint of the plan, the plan is run
    to completion and the queue is stopped. The stopped queue can not be resumed using
    **re_resume** method, instead queue_start method should be used to restart the queue.
    Check manager_state status flag to determine if the queue is stopped (*'idle'* state)
    or Run Engine is paused (*'paused'* state).

    The pause_pending status flag is set if pause request is successfully passed to Run Engine.
    It may take significant time for deferred pause to be processed. The flag is cleared once
    the pending pause request is processed (the plan is paused or plan is completed and
    the queue is stopped).

    Parameters
    ----------
    option: str ('immediate' or 'deferred', optional)
        Pause the plan immediately (roll back to the previous checkpoint) or continue to
        the next checkpoint. Default: *'deferred'*.

    Returns
    -------
    dict
        Dictionary keys:

        - **success**: *boolean* - success of the request.

        - **msg**: *str* - error message in case the request is rejected by RE Manager.

    Raises
    ------
    Exception
        Reraises the exceptions from ``send_request`` API.

    Examples
    --------

    .. code-block:: python

        # Synchronous code (0MQ, HTTP)
        RM.re_pause()             # Initiate deferred pause
        RM.re_pause("deferred")   # Initiate deferred pause
        RM.re_pause("immediate")  # Initiate immediate pause

        RM.wait_for_idle_or_paused()

        RM.re_resume()
        RM.re_stop()
        RM.re_abort()
        RM.re_halt()

        # Asynchronous code (0MQ, HTTP)
        await RM.re_pause()             # Initiate deferred pause
        await RM.re_pause("deferred")   # Initiate deferred pause
        await RM.re_pause("immediate")  # Initiate immediate pause

        await RM.wait_for_idle_or_paused()

        await RM.re_resume()
        await RM.re_stop()
        await RM.re_abort()
        await RM.re_halt()
"""

_doc_api_re_resume = """
    Request Run Engine to resume paused plan. See documentation for ``re_pause`` API
    for more detailed information.
"""

_doc_api_re_stop = """
    Request Run Engine to stop paused plan. See documentation for ``re_pause`` API
    for more detailed information.
"""

_doc_api_re_abort = """
    Request Run Engine to abort paused plan. See documentation for ``re_pause`` API
    for more detailed information.
"""

_doc_api_re_halt = """
    Request Run Engine to halt paused plan. See documentation for ``re_pause`` API
    for more detailed information.
"""
