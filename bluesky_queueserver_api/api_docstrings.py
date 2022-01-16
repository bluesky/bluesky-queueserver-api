_doc_send_request = """
    Send request to RE Manager and return the response. The function directly passes
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

        # QMQ, blocking
        from bluesky_queueserver_api.zmq import REManagerAPI
        RM = REManagerAPI()
        status = RM.send_request(method="status")
        RM.close()

        # HTTP, blocking
        from bluesky_queueserver_api.http import REManagerAPI
        RM = REManagerAPI()
        status = RM.send_request(method="status")
        RM.close()

        # QMQ, asyncio
        from bluesky_queueserver_api.zmq.asyncio import REManagerAPI
        RM = REManagerAPI()
        status = await RM.send_request(method="status")
        await RM.close()

        # HTTP, asyncio
        from bluesky_queueserver_api.http.asyncio import REManagerAPI
        RM = REManagerAPI()
        status = await RM.send_request(method="status")
        await RM.close()
"""
