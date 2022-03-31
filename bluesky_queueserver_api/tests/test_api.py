import asyncio

import pytest
import threading
import time as ttime

from .common import re_manager, re_manager_cmd  # noqa: F401
from .common import fastapi_server, fastapi_server_fs  # noqa: F401

from bluesky_queueserver_api.zmq import REManagerAPI as REManagerAPI_zmq_threads
from bluesky_queueserver_api.zmq.aio import REManagerAPI as REManagerAPI_zmq_async
from bluesky_queueserver_api.http import REManagerAPI as REManagerAPI_http_threads
from bluesky_queueserver_api.http.aio import REManagerAPI as REManagerAPI_http_async
from bluesky_queueserver_api import BPlan, BFunc, WaitMonitor

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
@pytest.mark.parametrize("api", ["status", "ping"])
@pytest.mark.parametrize("reload", [None, False, True])
@pytest.mark.parametrize("library", ["THREADS", "ASYNC"])
@pytest.mark.parametrize("protocol", ["ZMQ", "HTTP"])
# fmt: on
def test_status_01(re_manager, fastapi_server, protocol, library, reload, api):  # noqa: F811
    """
    ``status`` and ``ping``: basic test
    """
    rm_api_class = _select_re_manager_api(protocol, library)
    params = {"reload": reload} if (reload is not None) else {}

    if not _is_async(library):
        RM = rm_api_class()
        if api == "status":
            status = RM.status(**params)
        elif api == "ping":
            status = RM.ping(**params)
        else:
            assert False, f"Unknown api: {api}"
        assert status["manager_state"] == "idle"
        RM.close()
    else:

        async def testing():
            RM = rm_api_class()
            if api == "status":
                status = await RM.status(**params)
            elif api == "ping":
                status = await RM.ping(**params)
            else:
                assert False, f"Unknown api: {api}"
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
    add_item_params = {"item": _plan1}
    if protocol != "HTTP":
        add_item_params.update({"user": _user, "user_group": _user_group})

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
    ``item_get``: basic test
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
def test_item_remove_01(re_manager, fastapi_server, protocol, library):  # noqa: F811
    """
    ``item_remove``: basic test
    """
    rm_api_class = _select_re_manager_api(protocol, library)
    item1 = BPlan("count", ["det1", "det2"], num=1, delay=1)
    item2 = BPlan("count", ["det1", "det2"], num=2, delay=1)

    def check_status(status, items_in_queue):
        assert status["items_in_queue"] == items_in_queue

    if not _is_async(library):
        RM = rm_api_class()
        resp_item1 = RM.item_add(item1)
        RM.item_add(item2)
        check_status(RM.status(), 2)

        resp1 = RM.item_remove(pos=-1)
        assert resp1["success"] is True
        resp2 = RM.item_get(uid=resp_item1["item"]["item_uid"])
        assert resp2["success"] is True
        resp3 = RM.item_remove(uid=resp_item1["item"]["item_uid"])
        assert resp3["success"] is True
        assert resp3["qsize"] == 0

        check_status(RM.status(), 0)

        RM.close()
    else:

        async def testing():
            RM = rm_api_class()
            resp_item1 = await RM.item_add(item1)
            await RM.item_add(item2)
            check_status(await RM.status(), 2)

            resp1 = await RM.item_remove(pos=-1)
            assert resp1["success"] is True
            resp2 = await RM.item_get(uid=resp_item1["item"]["item_uid"])
            assert resp2["success"] is True
            resp3 = await RM.item_remove(uid=resp_item1["item"]["item_uid"])
            assert resp3["success"] is True
            assert resp3["qsize"] == 0

            check_status(await RM.status(), 0)

            await RM.close()

        asyncio.run(testing())


# fmt: off
@pytest.mark.parametrize("library", ["THREADS", "ASYNC"])
@pytest.mark.parametrize("protocol", ["ZMQ", "HTTP"])
# fmt: on
def test_item_remove_batch_01(re_manager, fastapi_server, protocol, library):  # noqa: F811
    """
    ``item_remove_batch``: basic test
    """
    rm_api_class = _select_re_manager_api(protocol, library)
    item1 = BPlan("count", ["det1", "det2"], num=1, delay=1)
    item2 = BPlan("count", ["det1", "det2"], num=2, delay=1)

    def check_status(status, items_in_queue):
        assert status["items_in_queue"] == items_in_queue

    if not _is_async(library):
        RM = rm_api_class()
        resp_item1 = RM.item_add(item1)
        resp_item2 = RM.item_add(item2)
        check_status(RM.status(), 2)

        resp1 = RM.item_remove_batch(uids=[resp_item1["item"]["item_uid"], resp_item2["item"]["item_uid"]])
        assert resp1["success"] is True
        assert resp1["qsize"] == 0

        # Non-existing UIDs
        RM.item_remove_batch(uids=["some-uid"])
        with pytest.raises(RM.RequestFailedError, match="The queue does not contain items"):
            RM.item_remove_batch(uids=["some-uid"], ignore_missing=False)

        check_status(RM.status(), 0)

        RM.close()
    else:

        async def testing():
            RM = rm_api_class()
            resp_item1 = await RM.item_add(item1)
            resp_item2 = await RM.item_add(item2)
            check_status(await RM.status(), 2)

            resp1 = await RM.item_remove_batch(
                uids=[resp_item1["item"]["item_uid"], resp_item2["item"]["item_uid"]]
            )
            assert resp1["success"] is True
            assert resp1["qsize"] == 0

            check_status(await RM.status(), 0)

            # Non-existing UIDs
            await RM.item_remove_batch(uids=["some-uid"])
            with pytest.raises(RM.RequestFailedError, match="The queue does not contain items"):
                await RM.item_remove_batch(uids=["some-uid"], ignore_missing=False)

            await RM.close()

        asyncio.run(testing())


# fmt: off
@pytest.mark.parametrize("library", ["THREADS", "ASYNC"])
@pytest.mark.parametrize("protocol", ["ZMQ", "HTTP"])
# fmt: on
def test_item_move_01(re_manager, fastapi_server, protocol, library):  # noqa: F811
    """
    ``item_move``: basic test
    """
    rm_api_class = _select_re_manager_api(protocol, library)
    item1 = BPlan("count", ["det1", "det2"], num=1, delay=1)
    item2 = BPlan("count", ["det1", "det2"], num=2, delay=1)
    item3 = BPlan("count", ["det1", "det2"], num=3, delay=1)

    def check_status(status, items_in_queue):
        assert status["items_in_queue"] == items_in_queue

    if not _is_async(library):
        RM = rm_api_class()
        resp_item1 = RM.item_add(item1)
        resp_item2 = RM.item_add(item2)
        resp_item3 = RM.item_add(item3)
        check_status(RM.status(), 3)

        resp_item1["item"]["item_uid"]
        uid2 = resp_item2["item"]["item_uid"]
        uid3 = resp_item3["item"]["item_uid"]

        resp1 = RM.item_move(pos=-1, pos_dest=0)
        assert resp1["success"] is True
        resp1a = RM.item_get(pos=0)
        assert resp1a["success"] is True
        assert resp1a["item"]["item_uid"] == uid3

        resp2 = RM.item_move(uid=uid3, after_uid=uid2)
        assert resp2["success"] is True
        resp2a = RM.item_get(pos=2)
        assert resp2a["success"] is True
        assert resp2a["item"]["item_uid"] == uid3

        status = RM.status()
        plan_queue_uid = status["plan_queue_uid"]

        resp3 = RM.item_move(uid=uid3, before_uid=uid2)
        assert resp3["success"] is True
        resp3a = RM.item_get(pos=1)
        assert resp3a["success"] is True
        assert resp3a["item"]["item_uid"] == uid3

        status = RM.status()
        assert status["plan_queue_uid"] != plan_queue_uid

        check_status(RM.status(), 3)

        RM.close()
    else:

        async def testing():
            RM = rm_api_class()
            resp_item1 = await RM.item_add(item1)
            resp_item2 = await RM.item_add(item2)
            resp_item3 = await RM.item_add(item3)
            check_status(await RM.status(), 3)

            resp_item1["item"]["item_uid"]
            uid2 = resp_item2["item"]["item_uid"]
            uid3 = resp_item3["item"]["item_uid"]

            resp1 = await RM.item_move(pos=-1, pos_dest=0)
            assert resp1["success"] is True
            resp1a = await RM.item_get(pos=0)
            assert resp1a["success"] is True
            assert resp1a["item"]["item_uid"] == uid3

            resp2 = await RM.item_move(uid=uid3, after_uid=uid2)
            assert resp2["success"] is True
            resp2a = await RM.item_get(pos=2)
            assert resp2a["success"] is True
            assert resp2a["item"]["item_uid"] == uid3

            status = await RM.status()
            plan_queue_uid = status["plan_queue_uid"]

            resp3 = await RM.item_move(uid=uid3, before_uid=uid2)
            assert resp3["success"] is True
            resp3a = await RM.item_get(pos=1)
            assert resp3a["success"] is True
            assert resp3a["item"]["item_uid"] == uid3

            status = await RM.status()
            assert status["plan_queue_uid"] != plan_queue_uid

            check_status(await RM.status(), 3)

            await RM.close()

        asyncio.run(testing())


# fmt: off
@pytest.mark.parametrize("library", ["THREADS", "ASYNC"])
@pytest.mark.parametrize("protocol", ["ZMQ", "HTTP"])
# fmt: on
def test_item_move_batch_01(re_manager, fastapi_server, protocol, library):  # noqa: F811
    """
    ``item_move``: basic test
    """
    rm_api_class = _select_re_manager_api(protocol, library)
    item1 = BPlan("count", ["det1", "det2"], num=1, delay=1)
    item2 = BPlan("count", ["det1", "det2"], num=2, delay=1)
    item3 = BPlan("count", ["det1", "det2"], num=3, delay=1)

    def check_status(status, items_in_queue):
        assert status["items_in_queue"] == items_in_queue

    if not _is_async(library):
        RM = rm_api_class()
        resp_item1 = RM.item_add(item1)
        resp_item2 = RM.item_add(item2)
        resp_item3 = RM.item_add(item3)
        check_status(RM.status(), 3)

        resp_item1["item"]["item_uid"]
        uid2 = resp_item2["item"]["item_uid"]
        uid3 = resp_item3["item"]["item_uid"]

        resp1 = RM.item_move_batch(uids=[uid3], pos_dest="front")
        assert resp1["success"] is True
        resp1a = RM.item_get(pos=0)
        assert resp1a["success"] is True
        assert resp1a["item"]["item_uid"] == uid3

        resp2 = RM.item_move_batch(uids=[uid3], after_uid=uid2)
        assert resp2["success"] is True
        resp2a = RM.item_get(pos=2)
        assert resp2a["success"] is True
        assert resp2a["item"]["item_uid"] == uid3

        status = RM.status()
        plan_queue_uid = status["plan_queue_uid"]

        resp3 = RM.item_move_batch(uids=[uid3], before_uid=uid2)
        assert resp3["success"] is True
        resp3a = RM.item_get(pos=1)
        assert resp3a["success"] is True
        assert resp3a["item"]["item_uid"] == uid3

        status = RM.status()
        assert status["plan_queue_uid"] != plan_queue_uid

        check_status(RM.status(), 3)

        RM.close()
    else:

        async def testing():
            RM = rm_api_class()
            resp_item1 = await RM.item_add(item1)
            resp_item2 = await RM.item_add(item2)
            resp_item3 = await RM.item_add(item3)
            check_status(await RM.status(), 3)

            resp_item1["item"]["item_uid"]
            uid2 = resp_item2["item"]["item_uid"]
            uid3 = resp_item3["item"]["item_uid"]

            resp1 = await RM.item_move_batch(uids=[uid3], pos_dest="front")
            assert resp1["success"] is True
            resp1a = await RM.item_get(pos=0)
            assert resp1a["success"] is True
            assert resp1a["item"]["item_uid"] == uid3

            resp2 = await RM.item_move_batch(uids=[uid3], after_uid=uid2)
            assert resp2["success"] is True
            resp2a = await RM.item_get(pos=2)
            assert resp2a["success"] is True
            assert resp2a["item"]["item_uid"] == uid3

            status = await RM.status()
            plan_queue_uid = status["plan_queue_uid"]

            resp3 = await RM.item_move_batch(uids=[uid3], before_uid=uid2)
            assert resp3["success"] is True
            resp3a = await RM.item_get(pos=1)
            assert resp3a["success"] is True
            assert resp3a["item"]["item_uid"] == uid3

            status = await RM.status()
            assert status["plan_queue_uid"] != plan_queue_uid

            check_status(await RM.status(), 3)

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
@pytest.mark.parametrize("library", ["THREADS", "ASYNC"])
@pytest.mark.parametrize("protocol", ["ZMQ", "HTTP"])
# fmt: on
def test_item_add_batch_01(re_manager, fastapi_server, protocol, library):  # noqa: F811
    """
    ``item_add_batch``: basic test
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
        check_resp(RM.item_add_batch([item]))
        check_status(RM.status(), 1)
        check_resp(RM.item_add_batch([item, item]))
        check_status(RM.status(), 3)
        check_resp(RM.item_add_batch([item_dict]))
        check_status(RM.status(), 4)
        check_resp(RM.item_add_batch([item_dict, item_dict]))
        check_status(RM.status(), 6)
        RM.close()
    else:

        async def testing():
            RM = rm_api_class()
            check_status(await RM.status(), 0)
            check_resp(await RM.item_add_batch([item]))
            check_status(await RM.status(), 1)
            check_resp(await RM.item_add_batch([item, item]))
            check_status(await RM.status(), 3)
            check_resp(await RM.item_add_batch([item_dict]))
            check_status(await RM.status(), 4)
            check_resp(await RM.item_add_batch([item_dict, item_dict]))
            check_status(await RM.status(), 6)
            await RM.close()

        asyncio.run(testing())


# fmt: off
@pytest.mark.parametrize("library", ["THREADS", "ASYNC"])
@pytest.mark.parametrize("protocol", ["ZMQ", "HTTP"])
# fmt: on
def test_item_add_batch_02(re_manager, fastapi_server, protocol, library):  # noqa: F811
    """
    ``item_add_batch``: check that the parameters ``pos``, ``before_uid`` and ``after_uid``
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
        check_resp(RM.item_add_batch([item1]))
        check_resp(RM.item_add_batch([item2]))
        check_status(RM.status(), 2)

        check_resp(RM.item_add_batch([item3], pos=1))
        resp3 = RM.item_get(pos=1)
        assert resp3["item"]["kwargs"]["num"] == 3

        check_resp(RM.item_add_batch([item4], before_uid=resp3["item"]["item_uid"]))
        resp4 = RM.item_get(pos=1)
        assert resp4["item"]["kwargs"]["num"] == 4

        check_resp(RM.item_add_batch([item5], after_uid=resp3["item"]["item_uid"]))
        resp5 = RM.item_get(pos=3)
        assert resp5["item"]["kwargs"]["num"] == 5

        RM.close()
    else:

        async def testing():
            RM = rm_api_class()
            check_resp(await RM.item_add_batch([item1]))
            check_resp(await RM.item_add_batch([item2]))
            check_status(await RM.status(), 2)

            check_resp(await RM.item_add_batch([item3], pos=1))
            resp3 = await RM.item_get(pos=1)
            assert resp3["item"]["kwargs"]["num"] == 3

            check_resp(await RM.item_add_batch([item4], before_uid=resp3["item"]["item_uid"]))
            resp4 = await RM.item_get(pos=1)
            assert resp4["item"]["kwargs"]["num"] == 4

            check_resp(await RM.item_add_batch([item5], after_uid=resp3["item"]["item_uid"]))
            resp5 = await RM.item_get(pos=3)
            assert resp5["item"]["kwargs"]["num"] == 5
            await RM.close()

        asyncio.run(testing())


# fmt: off
@pytest.mark.parametrize("library", ["THREADS", "ASYNC"])
@pytest.mark.parametrize("protocol", ["ZMQ", "HTTP"])
# fmt: on
def test_item_update_01(re_manager, fastapi_server, protocol, library):  # noqa: F811
    """
    ``item_update``: basic test
    """
    rm_api_class = _select_re_manager_api(protocol, library)
    item = BPlan("count", ["det1", "det2"], num=10, delay=1)

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

        resp1 = RM.item_get()
        assert resp1["success"] is True
        current_item = BPlan(resp1["item"])

        current_item.kwargs["num"] = 20
        resp1a = RM.item_update(current_item)
        assert resp1a["success"] is True

        check_status(RM.status(), 1)
        resp1b = RM.item_get()
        assert resp1b["success"] is True
        current_item2 = BPlan(resp1b["item"])
        assert current_item2.kwargs["num"] == 20
        assert current_item2.item_uid == current_item.item_uid

        current_item.kwargs["num"] = 30
        resp2a = RM.item_update(current_item, replace=True)
        assert resp2a["success"] is True

        check_status(RM.status(), 1)
        resp2b = RM.item_get()
        assert resp2b["success"] is True
        current_item2 = BPlan(resp2b["item"])
        assert current_item2.kwargs["num"] == 30
        assert current_item2.item_uid != current_item.item_uid

        RM.close()
    else:

        async def testing():
            RM = rm_api_class()
            check_status(await RM.status(), 0)
            check_resp(await RM.item_add(item))
            check_status(await RM.status(), 1)

            resp1 = await RM.item_get()
            assert resp1["success"] is True
            current_item = BPlan(resp1["item"])

            current_item.kwargs["num"] = 20
            resp1a = await RM.item_update(current_item)
            assert resp1a["success"] is True

            check_status(await RM.status(), 1)
            resp1b = await RM.item_get()
            assert resp1b["success"] is True
            current_item2 = BPlan(resp1b["item"])
            assert current_item2.kwargs["num"] == 20
            assert current_item2.item_uid == current_item.item_uid

            current_item.kwargs["num"] = 30
            resp2a = await RM.item_update(current_item, replace=True)
            assert resp2a["success"] is True

            check_status(await RM.status(), 1)
            resp2b = await RM.item_get()
            assert resp2b["success"] is True
            current_item2 = BPlan(resp2b["item"])
            assert current_item2.kwargs["num"] == 30
            assert current_item2.item_uid != current_item.item_uid

            await RM.close()

        asyncio.run(testing())


# fmt: off
@pytest.mark.parametrize("library", ["THREADS", "ASYNC"])
@pytest.mark.parametrize("protocol", ["ZMQ", "HTTP"])
# fmt: on
def test_item_execute_01(re_manager, fastapi_server, protocol, library):  # noqa: F811
    """
    ``item_execute``: basic test
    """
    rm_api_class = _select_re_manager_api(protocol, library)
    item = BPlan("count", ["det1", "det2"], num=5, delay=0.1)
    item_dict = item.to_dict()

    def check_resp(resp):
        assert resp["success"] is True
        assert resp["msg"] == ""

    def check_status(status, items_in_queue, items_in_history, manager_states):
        assert status["items_in_queue"] == items_in_queue
        assert status["items_in_history"] == items_in_history
        assert status["manager_state"] in manager_states

    if not _is_async(library):
        RM = rm_api_class()

        check_resp(RM.environment_open())
        RM.wait_for_idle()
        check_status(RM.status(), 0, 0, ["idle"])

        check_resp(RM.item_execute(item))
        check_status(RM.status(), 0, 0, ["starting_queue", "executing_queue"])
        RM.wait_for_idle()
        check_status(RM.status(), 0, 1, ["idle"])  # One item is added to history

        check_resp(RM.item_execute(item_dict))
        check_status(RM.status(), 0, 1, ["starting_queue", "executing_queue"])
        RM.wait_for_idle()
        check_status(RM.status(), 0, 2, ["idle"])  # One item is added to history

        check_resp(RM.environment_close())
        RM.wait_for_idle()

        RM.close()
    else:

        async def testing():
            RM = rm_api_class()

            check_resp(await RM.environment_open())
            await RM.wait_for_idle()
            check_status(await RM.status(), 0, 0, ["idle"])

            check_resp(await RM.item_execute(item))
            check_status(await RM.status(), 0, 0, ["starting_queue", "executing_queue"])
            await RM.wait_for_idle()
            check_status(await RM.status(), 0, 1, ["idle"])  # One item is added to history

            check_resp(await RM.item_execute(item_dict))
            check_status(await RM.status(), 0, 1, ["starting_queue", "executing_queue"])
            await RM.wait_for_idle()
            check_status(await RM.status(), 0, 2, ["idle"])  # One item is added to history

            check_resp(await RM.environment_close())
            await RM.wait_for_idle()

            await RM.close()

        asyncio.run(testing())


# fmt: off
@pytest.mark.parametrize("library", ["THREADS", "ASYNC"])
@pytest.mark.parametrize("protocol", ["ZMQ", "HTTP"])
# fmt: on
def test_queue_start_stop_cancel_01(re_manager, fastapi_server, protocol, library):  # noqa: F811
    """
    ``queue_start``, ``queue_stop``, ``queue_stop_cancel``: basic test
    """
    rm_api_class = _select_re_manager_api(protocol, library)
    item = BPlan("count", ["det1", "det2"], num=5, delay=1)

    def check_resp(resp):
        assert resp["success"] is True
        assert resp["msg"] == ""

    def check_status(status, items_in_queue, queue_stop_pending):
        assert status["items_in_queue"] == items_in_queue
        assert status["queue_stop_pending"] == queue_stop_pending

    if not _is_async(library):
        RM = rm_api_class()

        check_resp(RM.environment_open())
        RM.wait_for_idle()
        check_status(RM.status(), 0, False)

        check_resp(RM.item_add(item))
        check_status(RM.status(), 1, False)

        check_resp(RM.queue_start())
        ttime.sleep(1)
        check_status(RM.status(), 0, False)
        check_resp(RM.queue_stop())
        check_status(RM.status(), 0, True)
        check_resp(RM.queue_stop_cancel())
        check_status(RM.status(), 0, False)

        RM.wait_for_idle()
        check_status(RM.status(), 0, False)

        check_resp(RM.environment_close())
        RM.wait_for_idle()

        RM.close()
    else:

        async def testing():
            RM = rm_api_class()

            check_resp(await RM.environment_open())
            await RM.wait_for_idle()
            check_status(await RM.status(), 0, False)

            check_resp(await RM.item_add(item))
            check_status(await RM.status(), 1, False)

            check_resp(await RM.queue_start())
            ttime.sleep(1)
            check_status(await RM.status(), 0, False)
            check_resp(await RM.queue_stop())
            check_status(await RM.status(), 0, True)
            check_resp(await RM.queue_stop_cancel())
            check_status(await RM.status(), 0, False)

            await RM.wait_for_idle()
            check_status(await RM.status(), 0, False)

            check_resp(await RM.environment_close())
            await RM.wait_for_idle()

            await RM.close()

        asyncio.run(testing())


# fmt: off
@pytest.mark.parametrize("library", ["THREADS", "ASYNC"])
@pytest.mark.parametrize("protocol", ["ZMQ", "HTTP"])
# fmt: on
def test_queue_clear_01(re_manager, fastapi_server, protocol, library):  # noqa: F811
    """
    ``queue_clear``: basic test
    """
    rm_api_class = _select_re_manager_api(protocol, library)
    item = BPlan("count", ["det1", "det2"], num=10, delay=1)

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
        check_resp(RM.queue_clear())
        check_status(RM.status(), 0)
        RM.close()
    else:

        async def testing():
            RM = rm_api_class()
            check_status(await RM.status(), 0)
            check_resp(await RM.item_add(item))
            check_status(await RM.status(), 1)
            check_resp(await RM.queue_clear())
            check_status(await RM.status(), 0)
            await RM.close()

        asyncio.run(testing())


# fmt: off
@pytest.mark.parametrize("library", ["THREADS", "ASYNC"])
@pytest.mark.parametrize("protocol", ["ZMQ", "HTTP"])
# fmt: on
def test_queue_mode_set_01(re_manager, fastapi_server, protocol, library):  # noqa: F811
    """
    ``queue_mode_set``: basic test
    """
    rm_api_class = _select_re_manager_api(protocol, library)

    def check_resp(resp):
        assert resp["success"] is True
        assert resp["msg"] == ""

    def check_status(status, loop_mode):
        assert status["plan_queue_mode"]["loop"] == loop_mode

    if not _is_async(library):
        RM = rm_api_class()
        check_status(RM.status(), False)
        check_resp(RM.queue_mode_set(loop=True))
        check_status(RM.status(), True)
        check_resp(RM.queue_mode_set(loop=False))
        check_status(RM.status(), False)
        RM.close()
    else:

        async def testing():
            RM = rm_api_class()
            check_status(await RM.status(), False)
            check_resp(await RM.queue_mode_set(loop=True))
            check_status(await RM.status(), True)
            check_resp(await RM.queue_mode_set(loop=False))
            check_status(await RM.status(), False)
            await RM.close()

        asyncio.run(testing())


# fmt: off
@pytest.mark.parametrize("library", ["THREADS", "ASYNC"])
@pytest.mark.parametrize("protocol", ["ZMQ", "HTTP"])
# fmt: on
def test_queue_mode_set_02(re_manager, fastapi_server, protocol, library):  # noqa: F811
    """
    ``queue_mode_set``: setting mode directly, resetting mode to default
    """
    rm_api_class = _select_re_manager_api(protocol, library)

    def check_resp(resp):
        assert resp["success"] is True
        assert resp["msg"] == ""

    def check_status(status, loop_mode):
        assert status["plan_queue_mode"]["loop"] == loop_mode

    if not _is_async(library):
        RM = rm_api_class()
        check_status(RM.status(), False)
        check_resp(RM.queue_mode_set(mode={"loop": True}))
        check_status(RM.status(), True)
        check_resp(RM.queue_mode_set(mode="default"))
        check_status(RM.status(), False)
        RM.close()
    else:

        async def testing():
            RM = rm_api_class()
            check_status(await RM.status(), False)
            check_resp(await RM.queue_mode_set(mode={"loop": True}))
            check_status(await RM.status(), True)
            check_resp(await RM.queue_mode_set(mode="default"))
            check_status(await RM.status(), False)
            await RM.close()

        asyncio.run(testing())


# fmt: off
@pytest.mark.parametrize("library", ["THREADS", "ASYNC"])
@pytest.mark.parametrize("protocol", ["ZMQ", "HTTP"])
# fmt: on
def test_queue_get_01(re_manager, fastapi_server, protocol, library):  # noqa: F811
    """
    ``queue_get``: basic tests
    """
    rm_api_class = _select_re_manager_api(protocol, library)
    item = BPlan("count", ["det1", "det2"], num=10, delay=1)

    def check_resp(resp):
        assert resp["success"] is True
        assert resp["msg"] == ""

    def check_status(status, items_in_queue):
        assert status["items_in_queue"] == items_in_queue

    if not _is_async(library):
        RM = rm_api_class()
        check_status(RM.status(), 0)
        check_resp(RM.item_add(item))

        # This is supposed to return the updated queue
        response1 = RM.queue_get()
        assert response1["running_item"] == {}
        assert len(response1["items"]) == 1

        # The queue has not changed, but the response generated based on cached data must match
        response2 = RM.queue_get()
        assert response2 == response1

        RM.close()
    else:

        async def testing():
            RM = rm_api_class()
            check_status(await RM.status(), 0)
            check_resp(await RM.item_add(item))

            # This is supposed to return the updated queue
            response1 = await RM.queue_get()
            assert response1["running_item"] == {}
            assert len(response1["items"]) == 1

            # The queue has not changed, but the response generated based on cached data must match
            response2 = await RM.queue_get()
            assert response2 == response1

            await RM.close()

        asyncio.run(testing())


# fmt: off
@pytest.mark.parametrize("library", ["THREADS", "ASYNC"])
@pytest.mark.parametrize("protocol", ["ZMQ", "HTTP"])
# fmt: on
def test_history_get_clear_01(re_manager, fastapi_server, protocol, library):  # noqa: F811
    """
    ``history_get``, ``history_clear``: basic tests
    """
    rm_api_class = _select_re_manager_api(protocol, library)
    item = BPlan("count", ["det1", "det2"], num=1, delay=0.1)

    def check_resp(resp):
        assert resp["success"] is True
        assert resp["msg"] == ""

    def check_status(status, items_in_queue, items_in_history):
        assert status["items_in_queue"] == items_in_queue
        assert status["items_in_history"] == items_in_history

    if not _is_async(library):
        RM = rm_api_class()

        check_resp(RM.environment_open())
        RM.wait_for_idle()

        check_resp(RM.item_add(item))
        check_status(RM.status(), 1, 0)
        check_resp(RM.queue_start())
        RM.wait_for_idle()
        check_status(RM.status(), 0, 1)

        # This is supposed to return the updated queue
        response1 = RM.history_get()
        assert len(response1["items"]) == 1

        # The history has not changed, the response generated based on cached data
        response2 = RM.history_get()
        assert response2 == response1

        RM.history_clear()
        response3 = RM.history_get()
        assert len(response3["items"]) == 0

        check_resp(RM.environment_close())
        RM.wait_for_idle()

        RM.close()
    else:

        async def testing():
            RM = rm_api_class()

            check_resp(await RM.environment_open())
            await RM.wait_for_idle()

            check_resp(await RM.item_add(item))
            check_status(await RM.status(), 1, 0)
            check_resp(await RM.queue_start())
            await RM.wait_for_idle()
            check_status(await RM.status(), 0, 1)

            # This is supposed to return the updated queue
            response1 = await RM.history_get()
            assert len(response1["items"]) == 1

            # The history has not changed, the response generated based on cached data
            response2 = await RM.history_get()
            assert response2 == response1

            await RM.history_clear()
            response3 = await RM.history_get()
            assert len(response3["items"]) == 0

            check_resp(await RM.environment_close())
            await RM.wait_for_idle()

            await RM.close()

        asyncio.run(testing())


# fmt: off
@pytest.mark.parametrize("library", ["THREADS", "ASYNC"])
@pytest.mark.parametrize("protocol", ["ZMQ", "HTTP"])
# fmt: on
def test_plans_devices_allowed_01(re_manager, fastapi_server, protocol, library):  # noqa: F811
    """
    ``plans_allowed``, ``devices_allowed``: basic tests
    """
    rm_api_class = _select_re_manager_api(protocol, library)

    if not _is_async(library):
        RM = rm_api_class()

        response = RM.plans_allowed()
        assert response["success"] is True
        assert isinstance(response["plans_allowed"], dict)
        assert len(response["plans_allowed"]) > 0

        response2 = RM.plans_allowed()
        assert response2 == response

        response = RM.devices_allowed()
        assert response["success"] is True
        assert isinstance(response["devices_allowed"], dict)
        assert len(response["devices_allowed"]) > 0

        response2 = RM.devices_allowed()
        assert response2 == response

        RM.close()
    else:

        async def testing():
            RM = rm_api_class()

            response = await RM.plans_allowed()
            assert response["success"] is True
            assert isinstance(response["plans_allowed"], dict)
            assert len(response["plans_allowed"]) > 0

            response2 = await RM.plans_allowed()
            assert response2 == response

            response = await RM.devices_allowed()
            assert response["success"] is True
            assert isinstance(response["devices_allowed"], dict)
            assert len(response["devices_allowed"]) > 0

            response2 = await RM.devices_allowed()
            assert response2 == response

            await RM.close()

        asyncio.run(testing())


# fmt: off
@pytest.mark.parametrize("library", ["THREADS", "ASYNC"])
@pytest.mark.parametrize("protocol", ["ZMQ", "HTTP"])
# fmt: on
def test_plans_devices_existing_01(re_manager, fastapi_server, protocol, library):  # noqa: F811
    """
    ``plans_existing``, ``devices_existing``: basic tests
    """
    rm_api_class = _select_re_manager_api(protocol, library)

    if not _is_async(library):
        RM = rm_api_class()

        response = RM.plans_existing()
        assert response["success"] is True
        assert isinstance(response["plans_existing"], dict)
        assert len(response["plans_existing"]) > 0

        response2 = RM.plans_existing()
        assert response2 == response

        response = RM.devices_existing()
        assert response["success"] is True
        assert isinstance(response["devices_existing"], dict)
        assert len(response["devices_existing"]) > 0

        response2 = RM.devices_existing()
        assert response2 == response

        RM.close()
    else:

        async def testing():
            RM = rm_api_class()

            response = await RM.plans_existing()
            assert response["success"] is True
            assert isinstance(response["plans_existing"], dict)
            assert len(response["plans_existing"]) > 0

            response2 = await RM.plans_existing()
            assert response2 == response

            response = await RM.devices_existing()
            assert response["success"] is True
            assert isinstance(response["devices_existing"], dict)
            assert len(response["devices_existing"]) > 0

            response2 = await RM.devices_existing()
            assert response2 == response

            await RM.close()

        asyncio.run(testing())


# fmt: off
@pytest.mark.parametrize("library", ["THREADS", "ASYNC"])
@pytest.mark.parametrize("protocol", ["ZMQ", "HTTP"])
# fmt: on
def test_permissions_get_set_01(re_manager, fastapi_server, protocol, library):  # noqa: F811
    """
    ``permissions_get``, ``permissions_set``: basic tests
    """
    rm_api_class = _select_re_manager_api(protocol, library)

    if not _is_async(library):
        RM = rm_api_class()

        resp1 = RM.permissions_get()
        assert resp1["success"] is True
        permissions = resp1["user_group_permissions"]

        # Remove allowed plans (list of allowed plans should be empty)
        del permissions["user_groups"]["admin"]["allowed_plans"]

        resp2 = RM.plans_allowed()
        assert resp2["success"] is True
        allowed_plans = resp2["plans_allowed"]

        assert allowed_plans != {}

        resp3 = RM.permissions_set(permissions)
        assert resp3["success"] is True

        resp4 = RM.plans_allowed()
        assert resp4["success"] is True
        allowed_plans = resp4["plans_allowed"]

        assert allowed_plans == {}

        # Do not reload permssions from disk
        resp5 = RM.permissions_reload(restore_permissions=False)
        assert resp5["success"] is True

        resp6 = RM.plans_allowed()
        assert resp6["success"] is True
        allowed_plans = resp6["plans_allowed"]

        assert allowed_plans == {}

        # Reload permssions from disk
        resp6 = RM.permissions_reload(restore_permissions=True)
        assert resp6["success"] is True

        resp7 = RM.plans_allowed()
        assert resp7["success"] is True
        allowed_plans = resp7["plans_allowed"]

        assert allowed_plans != {}

        RM.close()
    else:

        async def testing():
            RM = rm_api_class()

            resp1 = await RM.permissions_get()
            assert resp1["success"] is True
            permissions = resp1["user_group_permissions"]

            # Remove allowed plans (list of allowed plans should be empty)
            del permissions["user_groups"]["admin"]["allowed_plans"]

            resp2 = await RM.plans_allowed()
            assert resp2["success"] is True
            allowed_plans = resp2["plans_allowed"]

            assert allowed_plans != {}

            resp3 = await RM.permissions_set(permissions)
            assert resp3["success"] is True

            resp4 = await RM.plans_allowed()
            assert resp4["success"] is True
            allowed_plans = resp4["plans_allowed"]

            assert allowed_plans == {}

            # Do not reload permssions from disk
            resp5 = await RM.permissions_reload(restore_permissions=False)
            assert resp5["success"] is True

            resp6 = await RM.plans_allowed()
            assert resp6["success"] is True
            allowed_plans = resp6["plans_allowed"]

            assert allowed_plans == {}

            # Reload permssions from disk
            resp6 = await RM.permissions_reload(restore_permissions=True)
            assert resp6["success"] is True

            resp7 = await RM.plans_allowed()
            assert resp7["success"] is True
            allowed_plans = resp7["plans_allowed"]

            assert allowed_plans != {}

            await RM.close()

        asyncio.run(testing())


# fmt: off
@pytest.mark.parametrize("test_option", ["script_upload", "function_execute"])
@pytest.mark.parametrize("run_in_background", [False, True])
@pytest.mark.parametrize("library", ["THREADS", "ASYNC"])
@pytest.mark.parametrize("protocol", ["ZMQ", "HTTP"])
# fmt: on
def test_script_upload_01(
    re_manager, fastapi_server, protocol, library, run_in_background, test_option  # noqa: F811
):
    """
    ``script_upload``, ``function_execute``, ``task_status``, ``task_result``: basic tests
    """
    rm_api_class = _select_re_manager_api(protocol, library)
    script = "import time as ttime\nttime.sleep(3)\n"
    function = BFunc("function_sleep", 3)

    def check_resp(resp):
        assert resp["success"] is True
        assert resp["msg"] == ""

    def check_status(status, worker_environment_exists, manager_state):
        assert status["worker_environment_exists"] == worker_environment_exists
        assert status["manager_state"] == manager_state

    if not _is_async(library):
        RM = rm_api_class()

        check_resp(RM.environment_open())
        RM.wait_for_idle()
        check_status(RM.status(), True, "idle")

        if test_option == "script_upload":
            resp1 = RM.script_upload(script, run_in_background=run_in_background)
            assert resp1["success"] is True
            task_uid = resp1["task_uid"]
        elif test_option == "function_execute":
            resp1 = RM.function_execute(function, run_in_background=run_in_background)
            assert resp1["success"] is True
            task_uid = resp1["task_uid"]
        else:
            assert False, f"Unknown test option: {test_option}"

        ttime.sleep(1)
        status = RM.status()
        assert status["worker_background_tasks"] == (1 if run_in_background else 0)

        for _ in range(10):
            resp2 = RM.task_status(task_uid)
            assert resp2["success"] is True
            if resp2["status"] == "completed":
                break
            ttime.sleep(0.5)

        resp3 = RM.task_result(task_uid)
        assert resp3["success"] is True
        assert resp3["status"] == "completed"
        assert resp3["result"]["success"] is True

        check_resp(RM.environment_close())
        RM.wait_for_idle()
        check_status(RM.status(), False, "idle")

        RM.close()
    else:

        async def testing():
            RM = rm_api_class()

            check_resp(await RM.environment_open())
            await RM.wait_for_idle()
            check_status(await RM.status(), True, "idle")

            if test_option == "script_upload":
                resp1 = await RM.script_upload(script, run_in_background=run_in_background)
                assert resp1["success"] is True
                task_uid = resp1["task_uid"]
            elif test_option == "function_execute":
                resp1 = await RM.function_execute(function, run_in_background=run_in_background)
                assert resp1["success"] is True
                task_uid = resp1["task_uid"]
            else:
                assert False, f"Unknown test option: {test_option}"

            await asyncio.sleep(1)
            status = await RM.status()
            assert status["worker_background_tasks"] == (1 if run_in_background else 0)

            for _ in range(10):
                resp2 = await RM.task_status(task_uid)
                assert resp2["success"] is True
                if resp2["status"] == "completed":
                    break
                await asyncio.sleep(0.5)

            resp2 = await RM.task_status(task_uid)
            assert resp2["success"] is True
            assert resp2["status"] == "completed"

            resp3 = await RM.task_result(task_uid)
            assert resp3["success"] is True
            assert resp3["status"] == "completed"
            assert resp3["result"]["success"] is True

            check_resp(await RM.environment_close())
            await RM.wait_for_idle()
            check_status(await RM.status(), False, "idle")

            await RM.close()

        asyncio.run(testing())


# fmt: off
@pytest.mark.parametrize("options, n_elements", [
    ({}, 1),
    ({"option": "active"}, 1),
    ({"option": "open"}, 1),
    ({"option": "closed"}, 0),
])
@pytest.mark.parametrize("library", ["THREADS", "ASYNC"])
@pytest.mark.parametrize("protocol", ["ZMQ", "HTTP"])
# fmt: on
def test_re_runs_01(re_manager, fastapi_server, protocol, library, options, n_elements):  # noqa: F811
    """
    ``re_runs``: basic tests
    """
    rm_api_class = _select_re_manager_api(protocol, library)
    plan = BPlan("count", ["det1"], num=5, delay=1)

    def check_resp(resp):
        assert resp["success"] is True
        assert resp["msg"] == ""

    def check_status(status, items_in_queue, manager_state):
        assert status["items_in_queue"] == items_in_queue
        assert status["manager_state"] == manager_state

    if not _is_async(library):
        RM = rm_api_class()

        check_resp(RM.environment_open())
        RM.wait_for_idle()
        check_status(RM.status(), 0, "idle")

        check_resp(RM.item_add(plan))
        check_status(RM.status(), 1, "idle")

        check_resp(RM.queue_start())
        ttime.sleep(1)

        resp1 = RM.re_runs(**options)
        assert resp1["success"] is True
        assert len(resp1["run_list"]) == n_elements
        resp1a = RM.re_runs(**options)
        assert resp1a["run_list"] == resp1["run_list"]

        RM.wait_for_idle()

        check_resp(RM.environment_close())
        RM.wait_for_idle()
        check_status(RM.status(), False, "idle")

        RM.close()
    else:

        async def testing():
            RM = rm_api_class()

            check_resp(await RM.environment_open())
            await RM.wait_for_idle()
            check_status(await RM.status(), 0, "idle")

            check_resp(await RM.item_add(plan))
            check_status(await RM.status(), 1, "idle")

            check_resp(await RM.queue_start())
            ttime.sleep(1)

            resp1 = await RM.re_runs(**options)
            assert resp1["success"] is True
            assert len(resp1["run_list"]) == n_elements
            resp1a = await RM.re_runs(**options)
            assert resp1a["run_list"] == resp1["run_list"]

            await RM.wait_for_idle()

            check_resp(await RM.environment_close())
            await RM.wait_for_idle()
            check_status(await RM.status(), False, "idle")

            await RM.close()

        asyncio.run(testing())


# fmt: off
@pytest.mark.parametrize("pause_option, continue_option", [
    (None, "resume"),
    ("deferred", "resume"),
    ("immediate", "resume"),
    (None, "stop"),
    (None, "abort"),
    (None, "halt"),
])
@pytest.mark.parametrize("library", ["THREADS", "ASYNC"])
@pytest.mark.parametrize("protocol", ["ZMQ", "HTTP"])
# fmt: on
def test_re_pause_01(re_manager, fastapi_server, protocol, library, pause_option, continue_option):  # noqa: F811
    """
    ``re_pause``, ``re_resume``, ``re_stop``, ``re_abort``, ``re_halt``: basic tests
    """
    rm_api_class = _select_re_manager_api(protocol, library)
    plan = BPlan("count", ["det1"], num=5, delay=1)

    def check_resp(resp):
        assert resp["success"] is True
        assert resp["msg"] == ""

    def check_status(status, items_in_queue, items_in_history, manager_state):
        assert status["items_in_queue"] == items_in_queue
        assert status["items_in_history"] == items_in_history
        assert status["manager_state"] == manager_state

    if not _is_async(library):
        RM = rm_api_class()

        check_resp(RM.environment_open())
        RM.wait_for_idle()
        check_status(RM.status(), 0, 0, "idle")

        check_resp(RM.item_add(plan))
        check_status(RM.status(), 1, 0, "idle")

        check_resp(RM.queue_start())
        ttime.sleep(1)

        params = [] if pause_option is None else [pause_option]
        check_resp(RM.re_pause(*params))

        RM.wait_for_idle_or_paused()
        check_status(RM.status(), 0, 0, "paused")

        if continue_option == "resume":
            check_resp(RM.re_resume())
        elif continue_option == "stop":
            check_resp(RM.re_stop())
        elif continue_option == "abort":
            check_resp(RM.re_abort())
        elif continue_option == "halt":
            check_resp(RM.re_halt())
        else:
            assert False, f"Unknown option: {continue_option!r}"

        RM.wait_for_idle()

        check_resp(RM.environment_close())
        RM.wait_for_idle()
        check_status(RM.status(), 0 if continue_option == "resume" else 1, 1, "idle")

        RM.close()
    else:

        async def testing():
            RM = rm_api_class()

            check_resp(await RM.environment_open())
            await RM.wait_for_idle()
            check_status(await RM.status(), 0, 0, "idle")

            check_resp(await RM.item_add(plan))
            check_status(await RM.status(), 1, 0, "idle")

            check_resp(await RM.queue_start())
            ttime.sleep(1)

            params = [] if pause_option is None else [pause_option]
            check_resp(await RM.re_pause(*params))

            await RM.wait_for_idle_or_paused()
            check_status(await RM.status(), 0, 0, "paused")

            if continue_option == "resume":
                check_resp(await RM.re_resume())
            elif continue_option == "stop":
                check_resp(await RM.re_stop())
            elif continue_option == "abort":
                check_resp(await RM.re_abort())
            elif continue_option == "halt":
                check_resp(await RM.re_halt())
            else:
                assert False, f"Unknown option: {continue_option!r}"

            await RM.wait_for_idle()

            check_resp(await RM.environment_close())
            await RM.wait_for_idle()
            check_status(await RM.status(), 0 if continue_option == "resume" else 1, 1, "idle")

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
                await asyncio.sleep(timeout)
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


# fmt: off
@pytest.mark.parametrize("library", ["THREADS", "ASYNC"])
@pytest.mark.parametrize("protocol", ["ZMQ", "HTTP"])
# fmt: on
def test_wait_for_idle_03(protocol, library):  # noqa: F811
    """
    ``wait_for_idle``: run the API without servers
    """

    rm_api_class = _select_re_manager_api(protocol, library)

    monitor = WaitMonitor()
    timeout = 2

    if not _is_async(library):

        def cancel_wait():
            ttime.sleep(timeout)
            monitor.cancel()

        RM = rm_api_class()

        t = ttime.time()
        with pytest.raises(RM.WaitTimeoutError):
            RM.wait_for_idle(timeout=5)
        assert ttime.time() - t < 10

        thread = threading.Thread(target=cancel_wait)
        thread.start()
        with pytest.raises(RM.WaitCancelError, match="Wait for condition was cancelled"):
            RM.wait_for_idle(monitor=monitor)
        thread.join()

        RM.close()

    else:

        async def testing():
            async def cancel_wait():
                await asyncio.sleep(timeout)
                monitor.cancel()

            RM = rm_api_class()

            t = ttime.time()
            with pytest.raises(RM.WaitTimeoutError):
                await RM.wait_for_idle(timeout=5)
            assert ttime.time() - t < 10

            asyncio.create_task(cancel_wait())
            with pytest.raises(RM.WaitCancelError, match="Wait for condition was cancelled"):
                await RM.wait_for_idle(monitor=monitor)

            await RM.close()

        asyncio.run(testing())


# ====================================================================================================
#                                       Console monitoring
# ====================================================================================================

_script1 = r"""
ttime.sleep(0.5)  # Leave some time for other messages to be printed
print("=====")
print("Beginning of the line. ", end="")
print("End of the line.")
print("Print\n multiple\n\nlines\n\n"),
"""

_script1_output = """=====
Beginning of the line. End of the line.
Print
 multiple

lines

"""


# fmt: off
@pytest.mark.parametrize("read_timeout", [None, 1.0])
@pytest.mark.parametrize("option", ["single_enable", "disable", "disable_with_pause"])
@pytest.mark.parametrize("library", ["THREADS", "ASYNC"])
@pytest.mark.parametrize("protocol", ["ZMQ", "HTTP"])
# fmt: on
def test_console_monitor_01(re_manager_cmd, fastapi_server, read_timeout, option, library, protocol):  # noqa: F811

    script = _script1
    expected_output = _script1_output

    params = ["--zmq-publish-console", "ON"]
    re_manager_cmd(params)

    rm_api_class = _select_re_manager_api(protocol, library)

    def check_status(status, manager_state, worker_environment_exists):
        assert status["manager_state"] == manager_state
        assert status["worker_environment_exists"] == worker_environment_exists

    if not _is_async(library):

        RM = rm_api_class()

        RM.environment_open()
        RM.wait_for_idle(timeout=10)
        check_status(RM.status(), "idle", True)

        assert RM.console_monitor.enabled is False

        if option == "single_enable":
            pass
        elif option == "disable":
            RM.console_monitor.enable()
            ttime.sleep(1)
            RM.console_monitor.disable()
        elif option == "disable_with_pause":
            RM.console_monitor.enable()
            ttime.sleep(1)
            RM.console_monitor.disable()
            ttime.sleep(2)
        else:
            assert False, f"Unknown option {option!r}"

        RM.console_monitor.enable()
        assert RM.console_monitor.enabled is True

        RM.script_upload(script)
        ttime.sleep(2)
        RM.wait_for_idle(timeout=10)
        check_status(RM.status(), "idle", True)

        text = []
        while True:
            try:
                params = {"timeout": read_timeout} if read_timeout else {}
                text.append(RM.console_monitor.next_msg(**params)["msg"])
            except RM.RequestTimeoutError:
                break

        text = "".join(text)
        print(f"============= text=\n'{text}'")
        print(f"============= expected_output=\n'{expected_output}'")
        assert expected_output in text

        RM.console_monitor.disable()
        assert RM.console_monitor.enabled is False

        RM.environment_close()
        RM.wait_for_idle(timeout=10)
        check_status(RM.status(), "idle", False)

        RM.close()

    else:

        async def testing():

            RM = rm_api_class()

            await RM.environment_open()
            await RM.wait_for_idle(timeout=10)
            check_status(await RM.status(), "idle", True)

            assert RM.console_monitor.enabled is False

            if option == "single_enable":
                pass
            elif option == "disable":
                RM.console_monitor.enable()
                await asyncio.sleep(1)
                RM.console_monitor.disable()
            elif option == "disable_with_pause":
                RM.console_monitor.enable()
                await asyncio.sleep(1)
                RM.console_monitor.disable()
                await asyncio.sleep(2)
            else:
                assert False, f"Unknown option {option!r}"

            RM.console_monitor.enable()
            assert RM.console_monitor.enabled is True

            await RM.script_upload(script)
            await asyncio.sleep(2)
            await RM.wait_for_idle(timeout=10)
            check_status(await RM.status(), "idle", True)

            text = []
            while True:
                try:
                    params = {"timeout": read_timeout} if read_timeout else {}
                    msg = await RM.console_monitor.next_msg(**params)
                    text.append(msg["msg"])
                except RM.RequestTimeoutError:
                    break

            text = "".join(text)
            print(f"============= text=\n{text}")
            print(f"============= expected_output=\n{expected_output}")
            assert expected_output in text

            RM.console_monitor.disable()
            assert RM.console_monitor.enabled is False

            await RM.environment_close()
            await RM.wait_for_idle(timeout=10)
            check_status(await RM.status(), "idle", False)

            await RM.close()

        asyncio.run(testing())


# fmt: off
@pytest.mark.parametrize("library", ["THREADS", "ASYNC"])
@pytest.mark.parametrize("protocol", ["ZMQ", "HTTP"])
# fmt: on
def test_console_monitor_02(re_manager_cmd, fastapi_server, library, protocol):  # noqa: F811
    """
    RM.console_monitor.next_msg(): test that timeout works.
    """

    rm_api_class = _select_re_manager_api(protocol, library)

    if not _is_async(library):

        RM = rm_api_class()

        RM.console_monitor.enable()
        assert RM.console_monitor.enabled is True

        t0 = ttime.time()
        with pytest.raises(RM.RequestTimeoutError):
            RM.console_monitor.next_msg()  # Raises an exception immediately
        assert ttime.time() - t0 < 0.5

        with pytest.raises(RM.RequestTimeoutError):
            RM.console_monitor.next_msg(timeout=2)  # Raises an exception after 2 sec. timeout
        assert ttime.time() - t0 > 1.9

        RM.close()

    else:

        async def testing():

            RM = rm_api_class()

            RM.console_monitor.enable()
            assert RM.console_monitor.enabled is True

            t0 = ttime.time()
            with pytest.raises(RM.RequestTimeoutError):
                await RM.console_monitor.next_msg()  # Raises an exception immediately
            assert ttime.time() - t0 < 0.5

            with pytest.raises(RM.RequestTimeoutError):
                await RM.console_monitor.next_msg(timeout=2)  # Raises an exception after 2 sec. timeout
            assert ttime.time() - t0 > 1.9

            await RM.close()

        asyncio.run(testing())


# fmt: off
@pytest.mark.parametrize("pause_before_enable", [False, True])
@pytest.mark.parametrize("library", ["THREADS", "ASYNC"])
@pytest.mark.parametrize("protocol", ["ZMQ", "HTTP"])
# fmt: on
def test_console_monitor_03(re_manager_cmd, fastapi_server, pause_before_enable, library, protocol):  # noqa: F811
    """
    RM.console_monitor: test that the message buffer is properly cleared when the queue is enabled.
    """

    rm_api_class = _select_re_manager_api(protocol, library)

    if not _is_async(library):

        RM = rm_api_class()

        RM.console_monitor.enable()
        assert RM.console_monitor.enabled is True

        RM.console_monitor._msg_queue.put({"time": "", "msg": "Test message 1"})
        RM.console_monitor._msg_queue.put({"time": "", "msg": "Test message 2"})
        RM.console_monitor.disable()
        if pause_before_enable:
            # Wait until the thread stops. The buffer will be cleared.
            ttime.sleep(2)
        RM.console_monitor.enable()

        if pause_before_enable:
            # The buffer is empty. The request should time out.
            with pytest.raises(RM.RequestTimeoutError):
                RM.console_monitor.next_msg()
        else:
            RM.console_monitor.next_msg()

        RM.close()

    else:

        async def testing():

            RM = rm_api_class()

            RM.console_monitor.enable()
            assert RM.console_monitor.enabled is True

            RM.console_monitor._msg_queue.put_nowait({"time": "", "msg": "Test message 1"})
            RM.console_monitor._msg_queue.put_nowait({"time": "", "msg": "Test message 2"})
            RM.console_monitor.disable()
            if pause_before_enable:
                # Wait until the thread stops. The buffer will be cleared.
                await asyncio.sleep(2)
            RM.console_monitor.enable()

            if pause_before_enable:
                # The buffer is empty. The request should time out.
                with pytest.raises(RM.RequestTimeoutError):
                    await RM.console_monitor.next_msg()
            else:
                await RM.console_monitor.next_msg()

            await RM.close()

        asyncio.run(testing())


# fmt: off
@pytest.mark.parametrize("library", ["THREADS", "ASYNC"])
@pytest.mark.parametrize("protocol", ["ZMQ", "HTTP"])
# fmt: on
def test_console_monitor_04(re_manager_cmd, fastapi_server, library, protocol):  # noqa: F811
    """
    RM.console_monitor.clear()
    """

    rm_api_class = _select_re_manager_api(protocol, library)

    if not _is_async(library):

        RM = rm_api_class()

        RM.console_monitor.enable()
        assert RM.console_monitor.enabled is True

        RM.console_monitor._msg_queue.put({"time": "", "msg": "Test message 1"})
        RM.console_monitor._msg_queue.put({"time": "", "msg": "Test message 2"})
        RM.console_monitor.clear()

        with pytest.raises(RM.RequestTimeoutError):
            RM.console_monitor.next_msg()

        RM.close()

    else:

        async def testing():

            RM = rm_api_class()

            RM.console_monitor.enable()
            assert RM.console_monitor.enabled is True

            RM.console_monitor._msg_queue.put_nowait({"time": "", "msg": "Test message 1"})
            RM.console_monitor._msg_queue.put_nowait({"time": "", "msg": "Test message 2"})
            RM.console_monitor.clear()

            with pytest.raises(RM.RequestTimeoutError):
                await RM.console_monitor.next_msg()

            await RM.close()

        asyncio.run(testing())
