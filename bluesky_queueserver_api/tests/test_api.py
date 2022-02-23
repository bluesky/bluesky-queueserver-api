import asyncio
import pytest
import threading
import time as ttime

from .common import re_manager  # noqa: F401
from .common import fastapi_server  # noqa: F401

from bluesky_queueserver_api.zmq import REManagerAPI as REManagerAPI_zmq_threads
from bluesky_queueserver_api.zmq.aio import REManagerAPI as REManagerAPI_zmq_async
from bluesky_queueserver_api.http import REManagerAPI as REManagerAPI_http_threads
from bluesky_queueserver_api.http.aio import REManagerAPI as REManagerAPI_http_async
from bluesky_queueserver_api import BPlan, WaitMonitor

_plan1 = {"name": "count", "args": [["det1", "det2"]], "item_type": "plan"}
_user = "Test User"
_user_group = "admin"


def _is_async(library):
    if library == "ASYNC":
        return True
    elif library == "THREADS":
        return False
    else:
        raise ValueError(f"Unknown library: {library!r}")


def _select_re_manager_api(protocol, library):
    if protocol == "ZMQ":
        return REManagerAPI_zmq_async if _is_async(library) else REManagerAPI_zmq_threads
    elif protocol == "HTTP":
        return REManagerAPI_http_async if _is_async(library) else REManagerAPI_http_threads
    else:
        raise ValueError(f"Unknown protocol: {protocol!r}")


# fmt: off
@pytest.mark.parametrize("reload", [None, False, True])
@pytest.mark.parametrize("library", ["THREADS", "ASYNC"])
@pytest.mark.parametrize("protocol", ["ZMQ", "HTTP"])
# fmt: on
def test_status_01(re_manager, fastapi_server, protocol, library, reload):  # noqa: F811
    """
    ``status``: basic test
    """
    rm_api_class = _select_re_manager_api(protocol, library)
    params = {"reload": reload} if (reload is not None) else {}

    if not _is_async(library):
        RM = rm_api_class()
        status = RM.status(**params)
        assert status["manager_state"] == "idle"
        RM.close()
    else:

        async def testing():
            RM = rm_api_class()
            status = await RM.status(**params)
            assert status["manager_state"] == "idle"
            await RM.close()

        asyncio.run(testing())


# fmt: off
@pytest.mark.parametrize("reload", [None, False, True])
@pytest.mark.parametrize("library", ["THREADS", "ASYNC"])
@pytest.mark.parametrize("protocol", ["ZMQ", "HTTP"])
# fmt: on
def test_status_02(re_manager, fastapi_server, protocol, library, reload):  # noqa: F811
    """
    ``status``: check if 'reload' parameter actually works.
    In a rapid sequence: read status, add item to queue (using low-level API), read status again.
    Verify if the status was reloaded if ``reload`` is ``True``.
    """
    rm_api_class = _select_re_manager_api(protocol, library)
    status_params = {"reload": reload} if (reload is not None) else {}
    add_item_params = {"item": _plan1, "user": _user, "user_group": _user_group}

    def check_resp(resp):
        assert resp["success"] is True
        assert resp["msg"] == ""

    def check_status(status, items_in_queue):
        assert status["items_in_queue"] == items_in_queue

    if not _is_async(library):
        RM = rm_api_class()
        check_status(RM.status(**status_params), 0)
        check_resp(RM.send_request(method="queue_item_add", params=add_item_params))
        check_status(RM.status(**status_params), 1 if reload else 0)
        check_status(RM.status(**status_params), 1 if reload else 0)
        RM._clear_status_timestamp()
        check_status(RM.status(**status_params), 1)
        RM.close()
    else:

        async def testing():
            RM = rm_api_class()
            check_status(await RM.status(**status_params), 0)
            check_resp(await RM.send_request(method="queue_item_add", params=add_item_params))
            check_status(await RM.status(**status_params), 1 if reload else 0)
            check_status(await RM.status(**status_params), 1 if reload else 0)
            RM._clear_status_timestamp()
            check_status(await RM.status(**status_params), 1)
            await RM.close()

        asyncio.run(testing())


# fmt: off
@pytest.mark.parametrize("destroy", [False, True])
@pytest.mark.parametrize("library", ["THREADS", "ASYNC"])
@pytest.mark.parametrize("protocol", ["ZMQ", "HTTP"])
# fmt: on
def test_environment_close_destroy_01(re_manager, fastapi_server, protocol, library, destroy):  # noqa: F811
    """
    ``environment_open``, ``environment_close`` and ``enviroment_destroy``: basic test
    """
    rm_api_class = _select_re_manager_api(protocol, library)

    def check_resp(resp):
        assert resp["success"] is True
        assert resp["msg"] == ""

    def check_status(status, manager_state, worker_environment_exists):
        assert status["manager_state"] == manager_state
        assert status["worker_environment_exists"] == worker_environment_exists

    if not _is_async(library):
        RM = rm_api_class()
        check_status(RM.status(), "idle", False)
        check_resp(RM.environment_open())
        check_status(RM.status(), "creating_environment", False)
        RM.wait_for_idle()
        check_status(RM.status(), "idle", True)
        if not destroy:
            check_resp(RM.environment_close())
        else:
            check_resp(RM.environment_destroy())
        RM.wait_for_idle()
        check_status(RM.status(), "idle", False)
        RM.close()
    else:

        async def testing():
            RM = rm_api_class()
            check_status(await RM.status(), "idle", False)
            check_resp(await RM.environment_open())
            check_status(await RM.status(), "creating_environment", False)
            await RM.wait_for_idle()
            check_status(await RM.status(), "idle", True)
            if not destroy:
                check_resp(await RM.environment_close())
            else:
                check_resp(await RM.environment_destroy())
            await RM.wait_for_idle()
            check_status(await RM.status(), "idle", False)
            await RM.close()

        asyncio.run(testing())


# fmt: off
@pytest.mark.parametrize("request_fail_exceptions", [None, True, False])
@pytest.mark.parametrize("library", ["THREADS", "ASYNC"])
@pytest.mark.parametrize("protocol", ["ZMQ", "HTTP"])
# fmt: on
def test_environment_close_destroy_02(
    re_manager, fastapi_server, protocol, library, request_fail_exceptions  # noqa: F811
):
    """
    ``environment_open``, ``environment_close``: test that ``environment_open`` is raising an exception or
    returning error message based on the value of ``request_fail_exception`` parameter.

    This test is not only related to ``environment_open``, but test functionality used with any request
    to RE Manager which may be rejected (``'success': False``). This test does not need to be repeated
    for other API, because it is expect to work the same.
    """
    rm_api_class = _select_re_manager_api(protocol, library)
    params = {"request_fail_exceptions": request_fail_exceptions} if (request_fail_exceptions is not None) else {}
    err_msg = "Request failed: RE Worker environment already exists."

    def check_resp(resp):
        assert resp["success"] is True
        assert resp["msg"] == ""

    if not _is_async(library):
        RM = rm_api_class(**params)
        check_resp(RM.environment_open())
        RM.wait_for_idle()
        if request_fail_exceptions in (True, None):
            with pytest.raises(RM.RequestFailedError, match=err_msg):
                RM.environment_open()
            # Try again, capture the exception and check that parameters are correct
            try:
                RM.environment_open()
            except RM.RequestFailedError as ex:
                assert str(ex) == err_msg
                assert ex.response["msg"] in err_msg
                assert ex.response["success"] is False
        else:
            resp = RM.environment_open()
            assert resp["msg"] in err_msg
            assert resp["success"] is False
        check_resp(RM.environment_close())
        RM.wait_for_idle()
        RM.close()
    else:

        async def testing():
            RM = rm_api_class(**params)
            check_resp(await RM.environment_open())
            await RM.wait_for_idle()
            if request_fail_exceptions in (True, None):
                with pytest.raises(RM.RequestFailedError, match=err_msg):
                    await RM.environment_open()
                # Try again, capture the exception and check that parameters are correct
                try:
                    await RM.environment_open()
                except RM.RequestFailedError as ex:
                    assert str(ex) == err_msg
                    assert ex.response["msg"] in err_msg
                    assert ex.response["success"] is False
            else:
                resp = await RM.environment_open()
                assert resp["msg"] in err_msg
                assert resp["success"] is False

            check_resp(await RM.environment_close())
            await RM.wait_for_idle()
            await RM.close()

        asyncio.run(testing())


# fmt: off
@pytest.mark.parametrize("library", ["THREADS", "ASYNC"])
@pytest.mark.parametrize("protocol", ["ZMQ", "HTTP"])
# fmt: on
def test_item_get_01(re_manager, fastapi_server, protocol, library):  # noqa: F811
    """
    ``status``: basic test
    """
    rm_api_class = _select_re_manager_api(protocol, library)
    item1 = BPlan("count", ["det1", "det2"], num=1, delay=1)
    item2 = BPlan("count", ["det1", "det2"], num=2, delay=1)

    def check_status(status, items_in_queue):
        assert status["items_in_queue"] == items_in_queue

    def check_items(resp1, resp2, resp3, resp4):
        assert resp1 == resp2
        assert resp1 == resp3
        assert resp1 == resp4
        assert resp1["success"] is True
        assert resp1["msg"] == ""
        assert resp1["item"]["kwargs"]["num"] == 2

    if not _is_async(library):
        RM = rm_api_class()
        RM.item_add(item1)
        RM.item_add(item2)
        check_status(RM.status(), 2)

        resp1 = RM.item_get()
        resp2 = RM.item_get(pos=1)
        resp3 = RM.item_get(pos=1)
        resp4 = RM.item_get(uid=resp1["item"]["item_uid"])
        check_items(resp1, resp2, resp3, resp4)
        RM.close()
    else:

        async def testing():
            RM = rm_api_class()
            await RM.item_add(item1)
            await RM.item_add(item2)
            check_status(await RM.status(), 2)

            resp1 = await RM.item_get()
            resp2 = await RM.item_get(pos=1)
            resp3 = await RM.item_get(pos=1)
            resp4 = await RM.item_get(uid=resp1["item"]["item_uid"])
            check_items(resp1, resp2, resp3, resp4)
            await RM.close()

        asyncio.run(testing())


# fmt: off
@pytest.mark.parametrize("library", ["THREADS", "ASYNC"])
@pytest.mark.parametrize("protocol", ["ZMQ", "HTTP"])
# fmt: on
def test_item_add_01(re_manager, fastapi_server, protocol, library):  # noqa: F811
    """
    ``item_add``: basic test
    """
    rm_api_class = _select_re_manager_api(protocol, library)
    item = BPlan("count", ["det1", "det2"], num=10, delay=1)
    item_dict = item.to_dict()

    def check_resp(resp):
        assert resp["success"] is True
        assert resp["msg"] == ""

    def check_status(status, items_in_queue):
        assert status["items_in_queue"] == items_in_queue

    if not _is_async(library):
        RM = rm_api_class()
        check_status(RM.status(), 0)
        check_resp(RM.item_add(item))
        check_status(RM.status(), 1)
        check_resp(RM.item_add(item_dict))
        check_status(RM.status(), 2)
        RM.close()
    else:

        async def testing():
            RM = rm_api_class()
            check_status(await RM.status(), 0)
            check_resp(await RM.item_add(item))
            check_status(await RM.status(), 1)
            check_resp(await RM.item_add(item_dict))
            check_status(await RM.status(), 2)
            await RM.close()

        asyncio.run(testing())


# fmt: off
@pytest.mark.parametrize("library", ["THREADS", "ASYNC"])
@pytest.mark.parametrize("protocol", ["ZMQ", "HTTP"])
# fmt: on
def test_item_add_02(re_manager, fastapi_server, protocol, library):  # noqa: F811
    """
    ``item_add``: check that the parameters ``pos``, ``before_uid`` and ``after_uid``
    are passed correctly.
    """
    rm_api_class = _select_re_manager_api(protocol, library)
    item1 = BPlan("count", ["det1", "det2"], num=1, delay=1)
    item2 = BPlan("count", ["det1", "det2"], num=2, delay=1)
    item3 = BPlan("count", ["det1", "det2"], num=3, delay=1)
    item4 = BPlan("count", ["det1", "det2"], num=4, delay=1)
    item5 = BPlan("count", ["det1", "det2"], num=5, delay=1)

    def check_resp(resp):
        assert resp["success"] is True
        assert resp["msg"] == ""

    def check_status(status, items_in_queue):
        assert status["items_in_queue"] == items_in_queue

    if not _is_async(library):
        RM = rm_api_class()
        check_resp(RM.item_add(item1))
        check_resp(RM.item_add(item2))
        check_status(RM.status(), 2)

        check_resp(RM.item_add(item3, pos=1))
        resp3 = RM.item_get(pos=1)
        assert resp3["item"]["kwargs"]["num"] == 3

        check_resp(RM.item_add(item4, before_uid=resp3["item"]["item_uid"]))
        resp4 = RM.item_get(pos=1)
        assert resp4["item"]["kwargs"]["num"] == 4

        check_resp(RM.item_add(item5, after_uid=resp3["item"]["item_uid"]))
        resp5 = RM.item_get(pos=3)
        assert resp5["item"]["kwargs"]["num"] == 5

        RM.close()
    else:

        async def testing():
            RM = rm_api_class()
            check_resp(await RM.item_add(item1))
            check_resp(await RM.item_add(item2))
            check_status(await RM.status(), 2)

            check_resp(await RM.item_add(item3, pos=1))
            resp3 = await RM.item_get(pos=1)
            assert resp3["item"]["kwargs"]["num"] == 3

            check_resp(await RM.item_add(item4, before_uid=resp3["item"]["item_uid"]))
            resp4 = await RM.item_get(pos=1)
            assert resp4["item"]["kwargs"]["num"] == 4

            check_resp(await RM.item_add(item5, after_uid=resp3["item"]["item_uid"]))
            resp5 = await RM.item_get(pos=3)
            assert resp5["item"]["kwargs"]["num"] == 5
            await RM.close()

        asyncio.run(testing())


# fmt: off
@pytest.mark.parametrize("timeout", [None, 2])
@pytest.mark.parametrize("library", ["THREADS", "ASYNC"])
@pytest.mark.parametrize("protocol", ["ZMQ", "HTTP"])
# fmt: on
def test_wait_for_idle_01(re_manager, fastapi_server, protocol, library, timeout):  # noqa: F811
    """
    ``wait_for_idle``: basic test. Check if timeout parameter works as expected.
    """

    rm_api_class = _select_re_manager_api(protocol, library)
    item = BPlan("count", ["det1", "det2"], num=5, delay=1)

    def check_status(status, manager_states):
        assert status["manager_state"] in manager_states

    if not _is_async(library):
        RM = rm_api_class()
        RM.item_add(item)
        RM.environment_open()
        RM.wait_for_idle()
        RM.queue_start()
        check_status(RM.status(), ["starting_queue", "executing_queue"])
        if timeout is None:
            RM.wait_for_idle()
            check_status(RM.status(), ["idle"])
        else:
            with pytest.raises(RM.WaitTimeoutError, match="Timeout while waiting for condition"):
                RM.wait_for_idle(timeout=timeout)
            check_status(RM.status(), ["executing_queue"])
        RM.wait_for_idle()
        check_status(RM.status(), ["idle"])
        RM.environment_close()
        RM.wait_for_idle()
        RM.close()

    else:

        async def testing():
            RM = rm_api_class()
            await RM.item_add(item)
            await RM.environment_open()
            await RM.wait_for_idle()
            await RM.queue_start()
            check_status(await RM.status(), ["starting_queue", "executing_queue"])
            if timeout is None:
                await RM.wait_for_idle()
                check_status(await RM.status(), ["idle"])
            else:
                with pytest.raises(RM.WaitTimeoutError, match="Timeout while waiting for condition"):
                    await RM.wait_for_idle(timeout=timeout)
                check_status(await RM.status(), ["executing_queue"])
            await RM.wait_for_idle()
            check_status(await RM.status(), ["idle"])
            await RM.environment_close()
            await RM.wait_for_idle()
            await RM.close()

        asyncio.run(testing())


# fmt: off
@pytest.mark.parametrize("library", ["THREADS", "ASYNC"])
@pytest.mark.parametrize("protocol", ["ZMQ", "HTTP"])
# fmt: on
def test_wait_for_idle_02(re_manager, fastapi_server, protocol, library):  # noqa: F811
    """
    ``wait_for_idle``: Check if ``WaitMonitor`` object may be used to cancel the wait.
    """

    rm_api_class = _select_re_manager_api(protocol, library)
    item = BPlan("count", ["det1", "det2"], num=5, delay=1)

    def check_status(status, manager_states):
        assert status["manager_state"] in manager_states

    monitor = WaitMonitor()
    timeout = 2

    if not _is_async(library):

        def cancel_wait():
            ttime.sleep(timeout)
            monitor.cancel()

        RM = rm_api_class()
        RM.item_add(item)
        RM.environment_open()
        RM.wait_for_idle()
        RM.queue_start()
        check_status(RM.status(), ["starting_queue", "executing_queue"])

        thread = threading.Thread(target=cancel_wait)
        thread.start()
        with pytest.raises(RM.WaitCancelError, match="Wait for condition was cancelled"):
            RM.wait_for_idle(monitor=monitor)
        thread.join()
        check_status(RM.status(), ["executing_queue"])

        RM.wait_for_idle()
        check_status(RM.status(), ["idle"])
        RM.environment_close()
        RM.wait_for_idle()
        RM.close()

    else:

        async def testing():
            async def cancel_wait():
                asyncio.sleep(timeout)
                monitor.cancel()

            RM = rm_api_class()
            await RM.item_add(item)
            await RM.environment_open()
            await RM.wait_for_idle()
            await RM.queue_start()
            check_status(await RM.status(), ["starting_queue", "executing_queue"])

            asyncio.create_task(cancel_wait())
            with pytest.raises(RM.WaitCancelError, match="Wait for condition was cancelled"):
                await RM.wait_for_idle(monitor=monitor)
            check_status(await RM.status(), ["executing_queue"])

            await RM.wait_for_idle()
            check_status(await RM.status(), ["idle"])
            await RM.environment_close()
            await RM.wait_for_idle()
            await RM.close()

        asyncio.run(testing())
