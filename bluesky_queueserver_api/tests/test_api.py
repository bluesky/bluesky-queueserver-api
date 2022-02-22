import asyncio
import pytest

from .common import re_manager  # noqa: F401
from .common import fastapi_server  # noqa: F401

from bluesky_queueserver_api.zmq import REManagerAPI as REManagerAPI_zmq_threads
from bluesky_queueserver_api.zmq.aio import REManagerAPI as REManagerAPI_zmq_async
from bluesky_queueserver_api.http import REManagerAPI as REManagerAPI_http_threads
from bluesky_queueserver_api.http.aio import REManagerAPI as REManagerAPI_http_async
from bluesky_queueserver_api import BPlan

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
def test_environment_close_01(re_manager, fastapi_server, protocol, library, destroy):  # noqa: F811
    """
    ``environment_open`` and ``environment_close``: basic test
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
        pass

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
@pytest.mark.parametrize("library", ["THREADS", "ASYNC"])
@pytest.mark.parametrize("protocol", ["ZMQ", "HTTP"])
# fmt: on
def test_add_item_01(re_manager, fastapi_server, protocol, library):  # noqa: F811
    """
    ``status``: basic test
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
        check_resp(RM.add_item(item))
        check_status(RM.status(), 1)
        check_resp(RM.add_item(item_dict))
        check_status(RM.status(), 2)
        RM.close()
    else:

        async def testing():
            RM = rm_api_class()
            check_status(await RM.status(), 0)
            check_resp(await RM.add_item(item))
            check_status(await RM.status(), 1)
            check_resp(await RM.add_item(item_dict))
            check_status(await RM.status(), 2)
            await RM.close()

        asyncio.run(testing())
