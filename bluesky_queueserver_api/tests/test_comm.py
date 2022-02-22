import asyncio
import pytest
import re

from bluesky_queueserver_api.comm_base import ReManagerAPI_Base
from bluesky_queueserver_api.comm_threads import ReManagerComm_ZMQ_Threads, ReManagerComm_HTTP_Threads
from bluesky_queueserver_api.comm_async import ReManagerComm_ZMQ_Async, ReManagerComm_HTTP_Async

_plan1 = {"name": "count", "args": [["det1", "det2"]], "item_type": "plan"}
_user = "Test User"
_user_group = "admin"


def test_ReManagerAPI_Base_01():
    RM = ReManagerAPI_Base()
    assert RM.request_fail_exceptions_enabled is True

    RM.request_fail_exceptions_enabled = False
    assert RM.request_fail_exceptions_enabled is False


# fmt: off
@pytest.mark.parametrize("request_fail_exceptions", [True, False])
@pytest.mark.parametrize("response, success, msg", [
    (None, False, "Request failed: None"),
    (10, False, "Request failed: 10"),
    ({}, True, ""),
    ({"success": True}, True, ""),
    ({"success": False}, False, "Request failed: (no error message)"),
    ({"success": False, "msg": "Error occurred"}, False, "Request failed: Error occurred"),
])
# fmt: on
def test_ReManagerAPI_Base_02(request_fail_exceptions, response, success, msg):
    RM = ReManagerAPI_Base(request_fail_exceptions=request_fail_exceptions)
    if success or not request_fail_exceptions:
        RM._check_response(response=response)
    else:
        with pytest.raises(RM.RequestFailedError, match=re.escape(msg)):
            RM._check_response(response=response)

        try:
            RM._check_response(response=response)
        except RM.RequestFailedError as ex:
            assert ex.response == response
        else:
            assert False, "Exception was not raised"


def test_ReManagerComm_ZMQ_01():
    """
    ReManagerComm_ZMQ_Threads and ReManagerComm_ZMQ_Async: basic test.
    Create an object, send a request and catch timeout error (the server is not running)
    """

    params = {"item": _plan1, "user": _user, "user_group": _user_group}

    RM = ReManagerComm_ZMQ_Threads()
    with pytest.raises(RM.RequestTimeoutError, match="timeout occurred"):
        RM.send_request(method="plans_allowed", params=params)
    RM.close()

    async def testing():
        RM = ReManagerComm_ZMQ_Async()
        with pytest.raises(RM.RequestTimeoutError, match="timeout occurred"):
            await RM.send_request(method="queue_item_add", params=params)
        await RM.close()

    asyncio.run(testing())


def test_ReManagerComm_HTTP_01():
    """
    ReManagerComm_HTTP_Thread and ReManagerComm_HTTP_Async: basic test.
    Create an object, send a request and catch RequestError (the server is not running)
    """

    params = {"item": _plan1, "user": _user, "user_group": _user_group}

    RM = ReManagerComm_HTTP_Threads()
    with pytest.raises(RM.RequestError, match=re.escape("HTTP request error: [Errno 111] Connection refused")):
        RM.send_request(method="queue_item_add", params=params)
    RM.close()

    async def testing():
        RM = ReManagerComm_HTTP_Async()
        with pytest.raises(RM.RequestError, match=re.escape("HTTP request error: All connection attempts failed")):
            await RM.send_request(method="queue_item_add", params=params)
        await RM.close()

    asyncio.run(testing())


def test_ReManagerComm_HTTP_02():
    """
    ReManagerComm_HTTP_Thread and ReManagerComm_HTTP_Async: Attempt to call
    unknown method, which does not exist in the table and can not be converted to
    endpoint name.
    """

    RM = ReManagerComm_HTTP_Threads()
    with pytest.raises(KeyError, match=re.escape("Unknown method 'unknown_method'")):
        RM.send_request(method="unknown_method")
    RM.close()

    async def testing():
        RM = ReManagerComm_HTTP_Async()
        with pytest.raises(KeyError, match=re.escape("Unknown method 'unknown_method'")):
            await RM.send_request(method="unknown_method")
        await RM.close()

    asyncio.run(testing())
