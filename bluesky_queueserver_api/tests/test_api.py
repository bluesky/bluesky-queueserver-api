import asyncio
import getpass
import os
import pprint
import re
import threading
import time as ttime
from pathlib import Path
from threading import Thread

import pytest

from bluesky_queueserver_api import BFunc, BPlan, WaitMonitor
from bluesky_queueserver_api._defaults import default_user_group

from .common import (  # noqa: F401
    _is_async,
    _select_re_manager_api,
    fastapi_server,
    fastapi_server_fs,
    instantiate_re_api_class,
    ip_kernel_simple_client,
    re_manager,
    re_manager_cmd,
)

_user, _user_group = "Test User", default_user_group

_plan1 = {"name": "count", "args": [["det1", "det2"]], "item_type": "plan"}
_plan3 = {"name": "count", "args": [["det1", "det2"]], "kwargs": {"num": 5, "delay": 1}, "item_type": "plan"}


# fmt: off
@pytest.mark.parametrize("library", ["THREADS", "ASYNC"])
@pytest.mark.parametrize("protocol", ["ZMQ", "HTTP"])
# fmt: on
def test_instantiation_01(re_manager, fastapi_server, protocol, library):  # noqa: F811
    """
    ``REManagerAPI``: instantiation of classes. Check if ``set_user_name_to_login_name`` works as expected.
    Check that ``user`` and ``user_group`` properties work properly.
    """
    rm_api_class = _select_re_manager_api(protocol, library)
    user_name = "Queue Server API User"
    user_name_2 = getpass.getuser()
    if not _is_async(library):
        RM = instantiate_re_api_class(rm_api_class)
        assert RM.protocol == RM.Protocols(protocol)
        assert RM.user == user_name
        assert RM.user_group == default_user_group

        RM.set_user_name_to_login_name()
        assert RM.user == user_name_2

        RM.user = "TestUser"
        RM.user_group = "TestUserGroup"
        assert RM.user == "TestUser"
        assert RM.user_group == "TestUserGroup"

        RM.close()
    else:

        async def testing():
            RM = instantiate_re_api_class(rm_api_class)
            assert RM.protocol == RM.Protocols(protocol)
            assert RM.user == user_name
            assert RM.user_group == default_user_group

            RM.set_user_name_to_login_name()
            assert RM.user == user_name_2

            RM.user = "TestUser"
            RM.user_group = "TestUserGroup"
            assert RM.user == "TestUser"
            assert RM.user_group == "TestUserGroup"

            await RM.close()

        asyncio.run(testing())


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
        RM = instantiate_re_api_class(rm_api_class)
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
            RM = instantiate_re_api_class(rm_api_class)
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
        RM = instantiate_re_api_class(rm_api_class)
        check_status(RM.status(**status_params), 0)
        check_resp(RM.send_request(method="queue_item_add", params=add_item_params))
        check_status(RM.status(**status_params), 1 if reload else 0)
        check_status(RM.status(**status_params), 1 if reload else 0)
        RM._clear_status_timestamp()
        check_status(RM.status(**status_params), 1)
        RM.close()
    else:

        async def testing():
            RM = instantiate_re_api_class(rm_api_class)
            check_status(await RM.status(**status_params), 0)
            check_resp(await RM.send_request(method="queue_item_add", params=add_item_params))
            check_status(await RM.status(**status_params), 1 if reload else 0)
            check_status(await RM.status(**status_params), 1 if reload else 0)
            RM._clear_status_timestamp()
            check_status(await RM.status(**status_params), 1)
            await RM.close()

        asyncio.run(testing())


# fmt: off
@pytest.mark.parametrize("library", ["THREADS", "ASYNC"])
@pytest.mark.parametrize("protocol", ["ZMQ", "HTTP"])
# fmt: on
def test_config_get_01(re_manager, fastapi_server, protocol, library):  # noqa: F811
    """
    ``config_get``: basic test
    """
    rm_api_class = _select_re_manager_api(protocol, library)

    def check_resp(resp):
        assert resp["success"] is True, pprint.pformat(resp)
        assert resp["msg"] == "", pprint.pformat(resp)
        return resp

    if not _is_async(library):
        RM = instantiate_re_api_class(rm_api_class)
        resp = check_resp(RM.config_get())
        assert "config" in resp, pprint.pformat(resp)
        assert "ip_connect_info" in resp["config"], pprint.pformat(resp)
        # Kernel does not exist, so connect info is {}
        assert resp["config"]["ip_connect_info"] == {}
        RM.close()
    else:

        async def testing():
            RM = instantiate_re_api_class(rm_api_class)
            resp = check_resp(await RM.config_get())
            assert "config" in resp, pprint.pformat(resp)
            assert "ip_connect_info" in resp["config"], pprint.pformat(resp)
            # Kernel does not exist, so connect info is {}
            assert resp["config"]["ip_connect_info"] == {}
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
        RM = instantiate_re_api_class(rm_api_class)
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
            RM = instantiate_re_api_class(rm_api_class)
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
        RM = instantiate_re_api_class(rm_api_class, **params)
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
            RM = instantiate_re_api_class(rm_api_class, **params)
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
@pytest.mark.parametrize("run_in_background", [None, False, True])
@pytest.mark.parametrize("library", ["THREADS", "ASYNC"])
@pytest.mark.parametrize("protocol", ["ZMQ", "HTTP"])
# fmt: on
def test_environment_update_01(re_manager, fastapi_server, protocol, library, run_in_background):  # noqa: F811
    """
    Test for `environment_update` command (more of a 'smoke' test)
    """
    rm_api_class = _select_re_manager_api(protocol, library)
    params = dict()

    if not _is_async(library):
        RM = instantiate_re_api_class(rm_api_class, **params)
        RM.environment_open()
        RM.wait_for_idle()

        RM.item_add(BPlan("count", ["det1"], num=5, delay=1))
        status = RM.status()
        assert status["items_in_queue"] == 1

        env_update_params = dict()
        if run_in_background is not None:
            env_update_params.update(dict(run_in_background=run_in_background))

        RM.environment_update(**env_update_params)
        RM.wait_for_idle()

        ttime.sleep(1)

        RM.queue_start()

        ttime.sleep(2)

        status = RM.status()
        assert status["items_in_queue"] == 0
        assert status["running_item_uid"] is not None

        if not run_in_background:
            with pytest.raises(RM.RequestFailedError, match="RE Manager must be in idle state"):
                RM.environment_update(**env_update_params)
        else:
            resp = RM.environment_update(**env_update_params)
            task_uid = resp["task_uid"]
            RM.wait_for_completed_task(task_uid=task_uid, timeout=10)

        # Wait for completion of the plan execution
        RM.wait_for_idle(timeout=20)

        RM.environment_close()
        RM.wait_for_idle()
        RM.close()

    else:

        async def testing():
            RM = instantiate_re_api_class(rm_api_class, **params)
            await RM.environment_open()
            await RM.wait_for_idle()

            await RM.item_add(BPlan("count", ["det1"], num=5, delay=1))
            status = await RM.status()
            assert status["items_in_queue"] == 1

            env_update_params = dict()
            if run_in_background is not None:
                env_update_params.update(dict(run_in_background=run_in_background))

            await RM.environment_update(**env_update_params)
            await RM.wait_for_idle()

            ttime.sleep(1)

            await RM.queue_start()

            ttime.sleep(2)

            status = await RM.status()
            assert status["items_in_queue"] == 0
            assert status["running_item_uid"] is not None

            if not run_in_background:
                with pytest.raises(RM.RequestFailedError, match="RE Manager must be in idle state"):
                    await RM.environment_update(**env_update_params)
            else:
                resp = await RM.environment_update(**env_update_params)
                task_uid = resp["task_uid"]
                await RM.wait_for_completed_task(task_uid=task_uid, timeout=10)

            # Wait for completion of the plan execution
            await RM.wait_for_idle(timeout=20)

            await RM.environment_close()
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
        RM = instantiate_re_api_class(rm_api_class)
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
            RM = instantiate_re_api_class(rm_api_class)
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
        RM = instantiate_re_api_class(rm_api_class)
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
            RM = instantiate_re_api_class(rm_api_class)
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
        RM = instantiate_re_api_class(rm_api_class)
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
            RM = instantiate_re_api_class(rm_api_class)
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
        RM = instantiate_re_api_class(rm_api_class)
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
            RM = instantiate_re_api_class(rm_api_class)
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
        RM = instantiate_re_api_class(rm_api_class)
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
            RM = instantiate_re_api_class(rm_api_class)
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
        RM = instantiate_re_api_class(rm_api_class)
        check_status(RM.status(), 0)
        check_resp(RM.item_add(item))
        check_status(RM.status(), 1)
        check_resp(RM.item_add(item_dict))
        check_status(RM.status(), 2)
        RM.close()
    else:

        async def testing():
            RM = instantiate_re_api_class(rm_api_class)
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
        RM = instantiate_re_api_class(rm_api_class)
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
            RM = instantiate_re_api_class(rm_api_class)
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
def test_item_add_03(re_manager, fastapi_server, protocol, library):  # noqa: F811
    """
    ``item_add``: test that 'user' and 'user_group' parameters override defaults
    """
    rm_api_class = _select_re_manager_api(protocol, library)
    item = BPlan("count", ["det1", "det2"], num=10, delay=1)

    user, user_group = "some user", "test_user"

    def check_resp(resp):
        assert resp["success"] is True
        assert resp["msg"] == ""

    def check_status(status, items_in_queue):
        assert status["items_in_queue"] == items_in_queue

    if not _is_async(library):
        RM = instantiate_re_api_class(rm_api_class)
        check_status(RM.status(), 0)
        resp = RM.item_add(item, user=user, user_group=user_group)
        check_resp(resp)
        if protocol != "HTTP":
            assert resp["item"]["user"] == user
            assert resp["item"]["user_group"] == user_group
        else:
            assert resp["item"]["user"] != user
            assert resp["item"]["user_group"] != user_group
        check_status(RM.status(), 1)
        RM.close()
    else:

        async def testing():
            RM = instantiate_re_api_class(rm_api_class)
            check_status(await RM.status(), 0)
            resp = await RM.item_add(item, user=user, user_group=user_group)
            check_resp(resp)
            if protocol != "HTTP":
                assert resp["item"]["user"] == user
                assert resp["item"]["user_group"] == user_group
            else:
                assert resp["item"]["user"] != user
                assert resp["item"]["user_group"] != user_group
            check_status(await RM.status(), 1)
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
        RM = instantiate_re_api_class(rm_api_class)
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
            RM = instantiate_re_api_class(rm_api_class)
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
        RM = instantiate_re_api_class(rm_api_class)
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
            RM = instantiate_re_api_class(rm_api_class)
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
def test_item_add_batch_03(re_manager, fastapi_server, protocol, library):  # noqa: F811
    """
    ``item_add_batch``: test that 'user' and 'user_group' parameters override defaults
    """
    rm_api_class = _select_re_manager_api(protocol, library)
    item = BPlan("count", ["det1", "det2"], num=10, delay=1)

    user, user_group = "some user", "test_user"

    def check_resp(resp):
        assert resp["success"] is True
        assert resp["msg"] == ""

    def check_status(status, items_in_queue):
        assert status["items_in_queue"] == items_in_queue

    if not _is_async(library):
        RM = instantiate_re_api_class(rm_api_class)
        check_status(RM.status(), 0)
        resp = RM.item_add_batch([item], user=user, user_group=user_group)
        check_resp(resp)
        if protocol != "HTTP":
            assert resp["items"][0]["user"] == user
            assert resp["items"][0]["user_group"] == user_group
        else:
            assert resp["items"][0]["user"] != user
            assert resp["items"][0]["user_group"] != user_group
        check_status(RM.status(), 1)
        RM.close()
    else:

        async def testing():
            RM = instantiate_re_api_class(rm_api_class)
            check_status(await RM.status(), 0)
            resp = await RM.item_add_batch([item], user=user, user_group=user_group)
            check_resp(resp)
            if protocol != "HTTP":
                assert resp["items"][0]["user"] == user
                assert resp["items"][0]["user_group"] == user_group
            else:
                assert resp["items"][0]["user"] != user
                assert resp["items"][0]["user_group"] != user_group
            check_status(await RM.status(), 1)
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
        RM = instantiate_re_api_class(rm_api_class)
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
            RM = instantiate_re_api_class(rm_api_class)
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
def test_item_update_02(re_manager, fastapi_server, protocol, library):  # noqa: F811
    """
    ``item_update``: test that 'user' and 'user_group' parameters override defaults
    """
    rm_api_class = _select_re_manager_api(protocol, library)
    item = BPlan("count", ["det1", "det2"], num=10, delay=1)

    user, user_group = "some user", "test_user"

    def check_resp(resp):
        assert resp["success"] is True
        assert resp["msg"] == ""

    def check_status(status, items_in_queue):
        assert status["items_in_queue"] == items_in_queue

    if not _is_async(library):
        RM = instantiate_re_api_class(rm_api_class)
        check_status(RM.status(), 0)
        check_resp(RM.item_add(item))
        resp = RM.queue_get()
        check_resp(resp)
        check_status(RM.status(), 1)

        item_updated = resp["items"][0]
        resp = RM.item_update(item_updated, user=user, user_group=user_group)
        check_resp(resp)
        if protocol != "HTTP":
            assert resp["item"]["user"] == user
            assert resp["item"]["user_group"] == user_group
        else:
            assert resp["item"]["user"] != user
            assert resp["item"]["user_group"] != user_group

        check_status(RM.status(), 1)
        RM.close()
    else:

        async def testing():
            RM = instantiate_re_api_class(rm_api_class)
            check_status(await RM.status(), 0)
            check_resp(await RM.item_add(item))
            resp = await RM.queue_get()
            check_resp(resp)
            check_status(await RM.status(), 1)

            item_updated = resp["items"][0]
            resp = await RM.item_update(item_updated, user=user, user_group=user_group)
            check_resp(resp)
            if protocol != "HTTP":
                assert resp["item"]["user"] == user
                assert resp["item"]["user_group"] == user_group
            else:
                assert resp["item"]["user"] != user
                assert resp["item"]["user_group"] != user_group

            check_status(await RM.status(), 1)
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
        RM = instantiate_re_api_class(rm_api_class)

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
            RM = instantiate_re_api_class(rm_api_class)

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
def test_item_execute_02(re_manager, fastapi_server, protocol, library):  # noqa: F811
    """
    ``item_add_execute``: test that 'user' and 'user_group' parameters override defaults
    """
    rm_api_class = _select_re_manager_api(protocol, library)
    item = BPlan("count", ["det1", "det2"], num=1, delay=0.1)

    user, user_group = "some user", "test_user"

    def check_resp(resp):
        assert resp["success"] is True
        assert resp["msg"] == ""

    def check_status(status, items_in_queue):
        assert status["items_in_queue"] == items_in_queue

    if not _is_async(library):
        RM = instantiate_re_api_class(rm_api_class)
        RM.environment_open()
        RM.wait_for_idle()
        check_status(RM.status(), 0)
        resp = RM.item_execute(item, user=user, user_group=user_group)
        check_resp(resp)
        if protocol != "HTTP":
            assert resp["item"]["user"] == user
            assert resp["item"]["user_group"] == user_group
        else:
            assert resp["item"]["user"] != user
            assert resp["item"]["user_group"] != user_group
        check_status(RM.status(), 0)
        RM.wait_for_idle()
        RM.environment_close()
        RM.wait_for_idle()
        RM.close()
    else:

        async def testing():
            RM = instantiate_re_api_class(rm_api_class)
            await RM.environment_open()
            await RM.wait_for_idle()
            check_status(await RM.status(), 0)
            resp = await RM.item_execute(item, user=user, user_group=user_group)
            check_resp(resp)
            if protocol != "HTTP":
                assert resp["item"]["user"] == user
                assert resp["item"]["user_group"] == user_group
            else:
                assert resp["item"]["user"] != user
                assert resp["item"]["user_group"] != user_group
            check_status(await RM.status(), 0)
            await RM.wait_for_idle()
            await RM.environment_close()
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
        RM = instantiate_re_api_class(rm_api_class)

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
            RM = instantiate_re_api_class(rm_api_class)

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
        RM = instantiate_re_api_class(rm_api_class)
        check_status(RM.status(), 0)
        check_resp(RM.item_add(item))
        check_status(RM.status(), 1)
        check_resp(RM.queue_clear())
        check_status(RM.status(), 0)
        RM.close()
    else:

        async def testing():
            RM = instantiate_re_api_class(rm_api_class)
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
def test_queue_autostart_01(re_manager, fastapi_server, protocol, library):  # noqa: F811
    """
    ``queue_autostart``: basic test
    """
    rm_api_class = _select_re_manager_api(protocol, library)

    def check_resp(resp):
        assert resp["success"] is True
        assert resp["msg"] == ""

    def check_status(status, autostart):
        assert status["queue_autostart_enabled"] == autostart

    if not _is_async(library):
        RM = instantiate_re_api_class(rm_api_class)
        check_status(RM.status(), False)
        check_resp(RM.queue_autostart(True))
        check_status(RM.status(), True)
        check_resp(RM.queue_autostart(enable=False))
        check_status(RM.status(), False)
        RM.close()
    else:

        async def testing():
            RM = instantiate_re_api_class(rm_api_class)
            check_status(await RM.status(), False)
            check_resp(await RM.queue_autostart(True))
            check_status(await RM.status(), True)
            check_resp(await RM.queue_autostart(enable=False))
            check_status(await RM.status(), False)
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

    def check_status(status, loop_mode, ignore_failures):
        assert status["plan_queue_mode"]["loop"] == loop_mode
        assert status["plan_queue_mode"]["ignore_failures"] == ignore_failures

    if not _is_async(library):
        RM = instantiate_re_api_class(rm_api_class)
        check_status(RM.status(), False, False)
        check_resp(RM.queue_mode_set(loop=True))
        check_status(RM.status(), True, False)
        check_resp(RM.queue_mode_set(loop=False))
        check_status(RM.status(), False, False)
        check_resp(RM.queue_mode_set(ignore_failures=True))
        check_status(RM.status(), False, True)
        check_resp(RM.queue_mode_set(ignore_failures=False))
        check_status(RM.status(), False, False)
        RM.close()
    else:

        async def testing():
            RM = instantiate_re_api_class(rm_api_class)
            check_status(await RM.status(), False, False)
            check_resp(await RM.queue_mode_set(loop=True))
            check_status(await RM.status(), True, False)
            check_resp(await RM.queue_mode_set(loop=False))
            check_status(await RM.status(), False, False)
            check_resp(await RM.queue_mode_set(ignore_failures=True))
            check_status(await RM.status(), False, True)
            check_resp(await RM.queue_mode_set(ignore_failures=False))
            check_status(await RM.status(), False, False)
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

    def check_status(status, loop_mode, ignore_failures):
        assert status["plan_queue_mode"]["loop"] == loop_mode
        assert status["plan_queue_mode"]["ignore_failures"] == ignore_failures

    if not _is_async(library):
        RM = instantiate_re_api_class(rm_api_class)
        check_status(RM.status(), False, False)
        check_resp(RM.queue_mode_set(mode={"loop": True, "ignore_failures": True}))
        check_status(RM.status(), True, True)
        check_resp(RM.queue_mode_set(mode="default"))
        check_status(RM.status(), False, False)
        RM.close()
    else:

        async def testing():
            RM = instantiate_re_api_class(rm_api_class)
            check_status(await RM.status(), False, False)
            check_resp(await RM.queue_mode_set(mode={"loop": True, "ignore_failures": True}))
            check_status(await RM.status(), True, True)
            check_resp(await RM.queue_mode_set(mode="default"))
            check_status(await RM.status(), False, False)
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
        RM = instantiate_re_api_class(rm_api_class)
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
            RM = instantiate_re_api_class(rm_api_class)
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
        RM = instantiate_re_api_class(rm_api_class)

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
            RM = instantiate_re_api_class(rm_api_class)

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
        RM = instantiate_re_api_class(rm_api_class)

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
            RM = instantiate_re_api_class(rm_api_class)

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
def test_plans_devices_allowed_02(re_manager, fastapi_server, protocol, library):  # noqa: F811
    """
    ``plans_allowed``, ``devices_allowed``: test that the API can handle 'user_group' optional parameter.
    """
    rm_api_class = _select_re_manager_api(protocol, library)

    if not _is_async(library):
        RM = instantiate_re_api_class(rm_api_class)

        response = RM.plans_allowed(user_group=None)
        assert response["success"] is True
        plans_allowed = response["plans_allowed"]
        assert len(plans_allowed) > 0

        response2 = RM.plans_allowed(user_group=RM.user_group)
        assert response2["success"] is True
        plans_allowed2 = response2["plans_allowed"]
        assert plans_allowed2 == plans_allowed

        response3 = RM.plans_allowed(user_group="test_user")
        assert response3["success"] is True
        plans_allowed3 = response3["plans_allowed"]
        if protocol != "HTTP":
            assert plans_allowed3 != plans_allowed
            # Request is expected to fail for non-existing user group
            with pytest.raises(RM.RequestFailedError):
                RM.plans_allowed(user_group="non_existing_user_group")
        else:
            # Group name is managed by HTTP server. User group in parameters is ignored.
            assert plans_allowed3 == plans_allowed
            # Group name is ignored, so the request will succeed
            RM.plans_allowed(user_group="non_existing_user_group")

        response = RM.devices_allowed(user_group=None)
        assert response["success"] is True
        devices_allowed = response["devices_allowed"]
        assert len(devices_allowed) > 0

        response2 = RM.devices_allowed(user_group=RM.user_group)
        assert response2["success"] is True
        devices_allowed2 = response2["devices_allowed"]
        assert devices_allowed2 == devices_allowed

        response3 = RM.devices_allowed(user_group="test_user")
        assert response3["success"] is True
        devices_allowed3 = response3["devices_allowed"]
        if protocol != "HTTP":
            assert devices_allowed3 != devices_allowed
            # Request is expected to fail for non-existing user group
            with pytest.raises(RM.RequestFailedError):
                RM.devices_allowed(user_group="non_existing_user_group")
        else:
            # Group name is managed by HTTP server. User group in parameters is ignored.
            assert devices_allowed3 == devices_allowed
            # Group name is ignored, so the request will succeed
            RM.devices_allowed(user_group="non_existing_user_group")

        RM.close()
    else:

        async def testing():
            RM = instantiate_re_api_class(rm_api_class)

            response = await RM.plans_allowed(user_group=None)
            assert response["success"] is True
            plans_allowed = response["plans_allowed"]
            assert len(plans_allowed) > 0

            response2 = await RM.plans_allowed(user_group=RM.user_group)
            assert response2["success"] is True
            plans_allowed2 = response2["plans_allowed"]
            assert plans_allowed2 == plans_allowed

            response3 = await RM.plans_allowed(user_group="test_user")
            assert response3["success"] is True
            plans_allowed3 = response3["plans_allowed"]
            if protocol != "HTTP":
                assert plans_allowed3 != plans_allowed
                # Request is expected to fail for non-existing user group
                with pytest.raises(RM.RequestFailedError):
                    await RM.plans_allowed(user_group="non_existing_user_group")
            else:
                # Group name is managed by HTTP server. User group in parameters is ignored.
                assert plans_allowed3 == plans_allowed
                # Group name is ignored, so the request will succeed
                await RM.plans_allowed(user_group="non_existing_user_group")

            response = await RM.devices_allowed(user_group=None)
            assert response["success"] is True
            devices_allowed = response["devices_allowed"]
            assert len(devices_allowed) > 0

            response2 = await RM.devices_allowed(user_group=RM.user_group)
            assert response2["success"] is True
            devices_allowed2 = response2["devices_allowed"]
            assert devices_allowed2 == devices_allowed

            response3 = await RM.devices_allowed(user_group="test_user")
            assert response3["success"] is True
            devices_allowed3 = response3["devices_allowed"]
            if protocol != "HTTP":
                assert devices_allowed3 != devices_allowed
                # Request is expected to fail for non-existing user group
                with pytest.raises(RM.RequestFailedError):
                    await RM.devices_allowed(user_group="non_existing_user_group")
            else:
                # Group name is managed by HTTP server. User group in parameters is ignored.
                assert devices_allowed3 == devices_allowed
                # Group name is ignored, so the request will succeed
                await RM.devices_allowed(user_group="non_existing_user_group")

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
        RM = instantiate_re_api_class(rm_api_class)

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
            RM = instantiate_re_api_class(rm_api_class)

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
        RM = instantiate_re_api_class(rm_api_class)

        resp1 = RM.permissions_get()
        assert resp1["success"] is True
        permissions = resp1["user_group_permissions"]

        # Remove allowed plans (list of allowed plans should be empty)
        del permissions["user_groups"][_user_group]["allowed_plans"]

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
            RM = instantiate_re_api_class(rm_api_class)

            resp1 = await RM.permissions_get()
            assert resp1["success"] is True
            permissions = resp1["user_group_permissions"]

            # Remove allowed plans (list of allowed plans should be empty)
            del permissions["user_groups"][_user_group]["allowed_plans"]

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
@pytest.mark.parametrize("library", ["THREADS", "ASYNC"])
@pytest.mark.parametrize("protocol", ["ZMQ", "HTTP"])
# fmt: on
def test_task_status_result_01(re_manager, fastapi_server, protocol, library):  # noqa: F811
    """
    'task_status' and 'task_result' API: basic functionality and parameter type ('task_uid') validation.
    """
    rm_api_class = _select_re_manager_api(protocol, library)
    function = BFunc("function_sleep", 5)

    def check_resp(resp):
        assert resp["success"] is True
        assert resp["msg"] == ""
        return resp

    if not _is_async(library):
        RM = instantiate_re_api_class(rm_api_class)

        # Open the environment
        check_resp(RM.environment_open())
        RM.wait_for_idle()
        status = RM.status()
        assert status["worker_environment_exists"] is True

        resp_f1 = check_resp(RM.function_execute(function))
        resp_f2 = check_resp(RM.function_execute(function, run_in_background=True))

        ttime.sleep(1)
        status = RM.status()
        assert status["manager_state"] == "executing_task"
        assert status["worker_background_tasks"] == 1

        resp = check_resp(RM.task_status(resp_f1["task_uid"]))
        assert resp["status"] == "running"
        resp = check_resp(RM.task_status(resp_f2["task_uid"]))
        assert resp["status"] == "running"
        resp = check_resp(RM.task_status([resp_f1["task_uid"], resp_f2["task_uid"]]))  # List
        assert len(resp["status"]) == 2
        for _, task_uid in resp["status"].items():
            assert task_uid == "running"
        resp = check_resp(RM.task_status([resp_f1["task_uid"]]))  # List - single item
        assert len(resp["status"]) == 1
        for _, task_uid in resp["status"].items():
            assert task_uid == "running"
        resp = check_resp(RM.task_status((resp_f1["task_uid"], resp_f2["task_uid"])))  # Tuple
        for _, task_uid in resp["status"].items():
            assert task_uid == "running"
        resp = check_resp(RM.task_status({resp_f1["task_uid"], resp_f2["task_uid"]}))  # Set
        for _, task_uid in resp["status"].items():
            assert task_uid == "running"
        with pytest.raises(RM.RequestParameterError):
            RM.task_status(10)  # Invalid parameter type

        resp = check_resp(RM.task_result(resp_f1["task_uid"]))
        assert resp["status"] == "running"
        assert resp["result"]["task_uid"] == resp_f1["task_uid"]
        with pytest.raises(RM.RequestParameterError):
            RM.task_result([resp_f1["task_uid"], resp_f2["task_uid"]])  # Only single task is allowed

        RM.wait_for_idle()

        check_resp(RM.environment_close())
        RM.wait_for_idle()
        status = RM.status()
        assert status["worker_environment_exists"] is False

        RM.close()
    else:

        async def testing():
            RM = instantiate_re_api_class(rm_api_class)

            # Open the environment
            check_resp(await RM.environment_open())
            await RM.wait_for_idle()
            status = await RM.status()
            assert status["worker_environment_exists"] is True

            resp_f1 = check_resp(await RM.function_execute(function))
            resp_f2 = check_resp(await RM.function_execute(function, run_in_background=True))

            await asyncio.sleep(1)
            status = await RM.status()
            assert status["manager_state"] == "executing_task"
            assert status["worker_background_tasks"] == 1

            resp = check_resp(await RM.task_status(resp_f1["task_uid"]))
            assert resp["status"] == "running"
            resp = check_resp(await RM.task_status(resp_f2["task_uid"]))
            assert resp["status"] == "running"
            resp = check_resp(await RM.task_status([resp_f1["task_uid"], resp_f2["task_uid"]]))  # List
            assert len(resp["status"]) == 2
            for _, task_uid in resp["status"].items():
                assert task_uid == "running"
            resp = check_resp(await RM.task_status([resp_f1["task_uid"]]))  # List - single item
            assert len(resp["status"]) == 1
            for _, task_uid in resp["status"].items():
                assert task_uid == "running"
            resp = check_resp(await RM.task_status((resp_f1["task_uid"], resp_f2["task_uid"])))  # Tuple
            for _, task_uid in resp["status"].items():
                assert task_uid == "running"
            resp = check_resp(await RM.task_status({resp_f1["task_uid"], resp_f2["task_uid"]}))  # Set
            for _, task_uid in resp["status"].items():
                assert task_uid == "running"
            with pytest.raises(RM.RequestParameterError):
                await RM.task_status(10)  # Invalid parameter type

            resp = check_resp(await RM.task_result(resp_f1["task_uid"]))
            assert resp["status"] == "running"
            assert resp["result"]["task_uid"] == resp_f1["task_uid"]
            with pytest.raises(RM.RequestParameterError):
                await RM.task_result([resp_f1["task_uid"], resp_f2["task_uid"]])  # Only single task is allowed

            await RM.wait_for_idle()

            check_resp(await RM.environment_close())
            await RM.wait_for_idle()
            status = await RM.status()
            assert status["worker_environment_exists"] is False

            await RM.close()

        asyncio.run(testing())


# fmt: off
@pytest.mark.parametrize("library", ["THREADS", "ASYNC"])
@pytest.mark.parametrize("protocol", ["ZMQ", "HTTP"])
# fmt: on
def test_wait_for_completed_task_01(re_manager, fastapi_server, protocol, library):  # noqa: F811
    """
    'wait_for_completed_task' API: basic functionality.
    """
    rm_api_class = _select_re_manager_api(protocol, library)

    def check_resp(resp):
        assert resp["success"] is True
        assert resp["msg"] == ""
        return resp

    if not _is_async(library):
        RM = instantiate_re_api_class(rm_api_class)

        # Open the environment
        check_resp(RM.environment_open())
        RM.wait_for_idle()
        status = RM.status()
        assert status["worker_environment_exists"] is True

        resp_f1 = check_resp(RM.function_execute(BFunc("function_sleep", 2), run_in_background=True))
        resp_f2 = check_resp(RM.function_execute(BFunc("function_sleep", 5), run_in_background=True))
        resp_f3 = check_resp(RM.function_execute(BFunc("function_sleep", 30), run_in_background=True))

        task_uids = [resp_f1["task_uid"], resp_f2["task_uid"], resp_f3["task_uid"]]
        task_uids_set = set(task_uids)

        ttime.sleep(0.5)
        status = RM.status()
        assert status["manager_state"] == "idle"
        assert status["worker_background_tasks"] == 3

        completed_uids = RM.wait_for_completed_task(task_uids[0])
        assert completed_uids == {task_uids[0]: "completed"}

        task_uids_set -= set(completed_uids)

        completed_uids = RM.wait_for_completed_task("non-existing-uid")
        assert completed_uids == {"non-existing-uid": "not_found"}

        completed_uids = RM.wait_for_completed_task(task_uids_set)
        assert completed_uids == {task_uids[1]: "completed"}

        # Check if the wait can be successfully cancelled
        monitor = WaitMonitor()

        def cancel_wait():
            ttime.sleep(1)
            monitor.cancel()

        thread = threading.Thread(target=cancel_wait)
        thread.start()
        with pytest.raises(RM.WaitCancelError, match="Wait for condition was cancelled"):
            RM.wait_for_completed_task([task_uids[2]], monitor=monitor)
        thread.join()

        assert monitor.is_cancelled is True

        # Check if the function times out properly
        with pytest.raises(RM.WaitTimeoutError, match="Timeout while waiting for condition"):
            RM.wait_for_completed_task([task_uids[2]], timeout=1)

        # Background tasks are still running, but we can close the environment
        check_resp(RM.environment_close())
        RM.wait_for_idle()
        status = RM.status()
        assert status["worker_environment_exists"] is False

        RM.close()
    else:

        async def testing():
            RM = instantiate_re_api_class(rm_api_class)

            # Open the environment
            check_resp(await RM.environment_open())
            await RM.wait_for_idle()
            status = await RM.status()
            assert status["worker_environment_exists"] is True

            resp_f1 = check_resp(await RM.function_execute(BFunc("function_sleep", 2), run_in_background=True))
            resp_f2 = check_resp(await RM.function_execute(BFunc("function_sleep", 5), run_in_background=True))
            resp_f3 = check_resp(await RM.function_execute(BFunc("function_sleep", 30), run_in_background=True))

            task_uids = [resp_f1["task_uid"], resp_f2["task_uid"], resp_f3["task_uid"]]
            task_uids_set = set(task_uids)

            await asyncio.sleep(0.5)
            status = await RM.status()
            assert status["manager_state"] == "idle"
            assert status["worker_background_tasks"] == 3

            completed_uids = await RM.wait_for_completed_task(task_uids[0])
            assert completed_uids == {task_uids[0]: "completed"}

            task_uids_set -= set(completed_uids)

            completed_uids = await RM.wait_for_completed_task("non-existing-uid")
            assert completed_uids == {"non-existing-uid": "not_found"}

            completed_uids = await RM.wait_for_completed_task(task_uids_set)
            assert completed_uids == {task_uids[1]: "completed"}

            # Check if the wait can be successfully cancelled
            monitor = WaitMonitor()

            async def cancel_wait():
                await asyncio.sleep(1)
                monitor.cancel()

            asyncio.create_task(cancel_wait())
            with pytest.raises(RM.WaitCancelError, match="Wait for condition was cancelled"):
                await RM.wait_for_completed_task([task_uids[2]], monitor=monitor)

            assert monitor.is_cancelled is True

            # Check if the function times out properly
            with pytest.raises(RM.WaitTimeoutError, match="Timeout while waiting for condition"):
                await RM.wait_for_completed_task([task_uids[2]], timeout=1)

            # Background tasks are still running, but we can close the environment
            check_resp(await RM.environment_close())
            await RM.wait_for_idle()
            status = await RM.status()
            assert status["worker_environment_exists"] is False

            await RM.close()

        asyncio.run(testing())


# fmt: off
@pytest.mark.parametrize("library", ["THREADS", "ASYNC"])
@pytest.mark.parametrize("protocol", ["ZMQ", "HTTP"])
# fmt: on
def test_wait_for_completed_task_02(re_manager, fastapi_server, protocol, library):  # noqa: F811
    """
    'wait_for_completed_task' API: failing cases and parameter validation.
    """
    rm_api_class = _select_re_manager_api(protocol, library)

    if not _is_async(library):
        RM = instantiate_re_api_class(rm_api_class)

        with pytest.raises(RM.RequestParameterError, match="task UID must be a non-empty string"):
            RM.wait_for_completed_task("")

        with pytest.raises(RM.RequestParameterError, match="task UID must be a non-empty list"):
            RM.wait_for_completed_task([])

        with pytest.raises(RM.RequestParameterError, match="Invalid type of parameter 'task_uid'"):
            RM.wait_for_completed_task(20)

        # 'not_found' items are considered completed by default
        assert RM.wait_for_completed_task("some_uid") == {"some_uid": "not_found"}
        # This could be disabled
        with pytest.raises(RM.WaitTimeoutError):
            RM.wait_for_completed_task("some_uid", treat_not_found_as_completed=False, timeout=1)

        RM.close()
    else:

        async def testing():
            RM = instantiate_re_api_class(rm_api_class)

            with pytest.raises(RM.RequestParameterError, match="task UID must be a non-empty string"):
                await RM.wait_for_completed_task("")

            with pytest.raises(RM.RequestParameterError, match="task UID must be a non-empty list"):
                await RM.wait_for_completed_task([])

            with pytest.raises(RM.RequestParameterError, match="Invalid type of parameter 'task_uid'"):
                await RM.wait_for_completed_task(20)

            # 'not_found' items are considered completed by default
            assert (await RM.wait_for_completed_task("some_uid")) == {"some_uid": "not_found"}
            # This could be disabled
            with pytest.raises(RM.WaitTimeoutError):
                await RM.wait_for_completed_task("some_uid", treat_not_found_as_completed=False, timeout=1)

            await RM.close()

        asyncio.run(testing())


# fmt: off
@pytest.mark.parametrize("library", ["THREADS", "ASYNC"])
@pytest.mark.parametrize("protocol", ["ZMQ", "HTTP"])
# fmt: on
def test_wait_for_completed_task_03_fail(protocol, library):  # noqa: F811
    """
    'wait_for_completed_task' API: failure to communicate with the server.
    """
    rm_api_class = _select_re_manager_api(protocol, library)
    # HTTP server is running, so we want to intentionally tell the client to communicate with
    #   non-existing server by setting incorrect port (1111).
    rm_params = {"http_server_uri": "http://localhost:1111"} if (protocol == "HTTP") else {}

    def get_exception_and_match(RM):
        if protocol == "ZMQ":
            exception = RM.RequestTimeoutError
            match = "timeout occurred"
        elif protocol == "HTTP":
            exception = RM.HTTPRequestError
            match = "(All connection attempts failed)|(Connection refused)"
        else:
            assert False, f"Unknown protocol: {protocol}"
        return exception, match

    if not _is_async(library):
        RM = instantiate_re_api_class(rm_api_class, **rm_params)

        exception, match = get_exception_and_match(RM)
        with pytest.raises(exception, match=match):
            RM.wait_for_completed_task("some-uid")

        RM.close()
    else:

        async def testing():
            RM = instantiate_re_api_class(rm_api_class, **rm_params)

            exception, match = get_exception_and_match(RM)
            with pytest.raises(exception, match=match):
                await RM.wait_for_completed_task("some-uid")

            await RM.close()

        asyncio.run(testing())


# fmt: off
@pytest.mark.parametrize("library", ["THREADS", "ASYNC"])
@pytest.mark.parametrize("protocol", ["ZMQ", "HTTP"])
# fmt: on
def test_wait_for_completed_task_04(re_manager, fastapi_server, protocol, library):  # noqa: F811
    """
    'wait_for_completed_task' API: check that monitor is properly tracking timeout.
    """
    rm_api_class = _select_re_manager_api(protocol, library)

    def check_resp(resp):
        assert resp["success"] is True
        assert resp["msg"] == ""
        return resp

    if not _is_async(library):
        RM = instantiate_re_api_class(rm_api_class)

        check_resp(RM.environment_open())
        RM.wait_for_idle()
        status = RM.status()
        assert status["worker_environment_exists"] is True

        resp = check_resp(RM.function_execute(BFunc("function_sleep", 5), run_in_background=True))
        task_uid = resp["task_uid"]

        monitor = WaitMonitor()
        t_start = ttime.time()
        RM.wait_for_completed_task(task_uid, monitor=monitor, timeout=10)

        assert t_start <= monitor.time_start < t_start + 1
        assert 4 < monitor.time_elapsed < 7
        assert monitor.timeout == 10
        assert monitor.is_cancelled is False

        check_resp(RM.environment_close())
        RM.wait_for_idle()
        status = RM.status()
        assert status["worker_environment_exists"] is False

        RM.close()
    else:

        async def testing():
            RM = instantiate_re_api_class(rm_api_class)

            check_resp(await RM.environment_open())
            await RM.wait_for_idle()
            status = await RM.status()
            assert status["worker_environment_exists"] is True

            resp = check_resp(await RM.function_execute(BFunc("function_sleep", 5), run_in_background=True))
            task_uid = resp["task_uid"]

            monitor = WaitMonitor()
            t_start = ttime.time()
            await RM.wait_for_completed_task(task_uid, monitor=monitor, timeout=10)

            assert t_start <= monitor.time_start < t_start + 1
            assert 4 < monitor.time_elapsed < 7
            assert monitor.timeout == 10
            assert monitor.is_cancelled is False

            check_resp(await RM.environment_close())
            await RM.wait_for_idle()
            status = await RM.status()
            assert status["worker_environment_exists"] is False

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
        RM = instantiate_re_api_class(rm_api_class)

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
            RM = instantiate_re_api_class(rm_api_class)

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


script_upload_02 = """
# Another device
from ophyd import Device

dev_test = Device(name="dev_test")

# Trivial plan
def sleep_for_a_few_sec(tt=1):
    yield from bps.sleep(tt)
"""


# fmt: off
@pytest.mark.parametrize("update_lists", [None, True, False])
@pytest.mark.parametrize("run_in_background", [False, True])
@pytest.mark.parametrize("library", ["THREADS", "ASYNC"])
@pytest.mark.parametrize("protocol", ["ZMQ", "HTTP"])
# fmt: on
def test_script_upload_02(
    re_manager, fastapi_server, protocol, library, run_in_background, update_lists  # noqa: F811
):
    """
    ``script_upload``: test functionality for different values of ``update_lists``
    """
    rm_api_class = _select_re_manager_api(protocol, library)

    def check_resp(resp):
        assert resp["success"] is True
        assert resp["msg"] == ""

    def check_status(status, worker_environment_exists, manager_state):
        assert status["worker_environment_exists"] == worker_environment_exists
        assert status["manager_state"] == manager_state

    def check_item_in_list(name, obj_list, in_list):
        if in_list:
            assert name in obj_list
        else:
            assert name not in obj_list

    params = {"script": script_upload_02, "run_in_background": run_in_background}
    if update_lists is not None:
        params.update({"update_lists": update_lists})
    else:
        update_lists = True

    if not _is_async(library):
        RM = instantiate_re_api_class(rm_api_class)

        check_resp(RM.environment_open())
        RM.wait_for_idle()
        check_status(RM.status(), True, "idle")

        resp1 = RM.script_upload(**params)
        assert resp1["success"] is True
        task_uid = resp1["task_uid"]

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

        resp4 = RM.plans_existing()
        check_item_in_list("sleep_for_a_few_sec", resp4["plans_existing"], update_lists)
        resp5 = RM.plans_allowed()
        check_item_in_list("sleep_for_a_few_sec", resp5["plans_allowed"], update_lists)
        resp6 = RM.devices_existing()
        check_item_in_list("dev_test", resp6["devices_existing"], update_lists)
        resp7 = RM.devices_allowed()
        check_item_in_list("dev_test", resp7["devices_allowed"], update_lists)

        check_resp(RM.environment_close())
        RM.wait_for_idle()
        check_status(RM.status(), False, "idle")

        RM.close()
    else:

        async def testing():
            RM = instantiate_re_api_class(rm_api_class)

            check_resp(await RM.environment_open())
            await RM.wait_for_idle()
            check_status(await RM.status(), True, "idle")

            resp1 = await RM.script_upload(**params)
            assert resp1["success"] is True
            task_uid = resp1["task_uid"]

            for _ in range(10):
                resp2 = await RM.task_status(task_uid)
                assert resp2["success"] is True
                if resp2["status"] == "completed":
                    break
                ttime.sleep(0.5)

            resp3 = await RM.task_result(task_uid)
            assert resp3["success"] is True
            assert resp3["status"] == "completed"
            assert resp3["result"]["success"] is True

            resp4 = await RM.plans_existing()
            check_item_in_list("sleep_for_a_few_sec", resp4["plans_existing"], update_lists)
            resp5 = await RM.plans_allowed()
            check_item_in_list("sleep_for_a_few_sec", resp5["plans_allowed"], update_lists)
            resp6 = await RM.devices_existing()
            check_item_in_list("dev_test", resp6["devices_existing"], update_lists)
            resp7 = await RM.devices_allowed()
            check_item_in_list("dev_test", resp7["devices_allowed"], update_lists)

            check_resp(await RM.environment_close())
            await RM.wait_for_idle()
            check_status(await RM.status(), False, "idle")

            await RM.close()

        asyncio.run(testing())


# fmt: off
@pytest.mark.parametrize("library", ["THREADS", "ASYNC"])
@pytest.mark.parametrize("protocol", ["ZMQ", "HTTP"])
# fmt: on
def test_function_execute_01(re_manager, fastapi_server, protocol, library):  # noqa: F811
    """
    ``function_execute``: test that 'user' and 'user_group' parameters override defaults
    """
    rm_api_class = _select_re_manager_api(protocol, library)
    func = BFunc("function_sleep", 3)
    user, user_group = "some user", "test_user"

    def check_resp(resp):
        assert resp["success"] is True
        assert resp["msg"] == ""

    def check_status(status, manager_state):
        assert status["manager_state"] == manager_state

    if not _is_async(library):
        RM = instantiate_re_api_class(rm_api_class)
        RM.environment_open()
        RM.wait_for_idle()
        check_status(RM.status(), "idle")
        resp = RM.function_execute(func, user=user, user_group=user_group)
        check_resp(resp)
        if protocol != "HTTP":
            assert resp["item"]["user"] == user
            assert resp["item"]["user_group"] == user_group
        else:
            assert resp["item"]["user"] != user
            assert resp["item"]["user_group"] != user_group
        check_status(RM.status(), "executing_task")
        RM.wait_for_idle()
        check_status(RM.status(), "idle")
        RM.environment_close()
        RM.wait_for_idle()
        RM.close()
    else:

        async def testing():
            RM = instantiate_re_api_class(rm_api_class)
            await RM.environment_open()
            await RM.wait_for_idle()
            check_status(await RM.status(), "idle")
            resp = await RM.function_execute(func, user=user, user_group=user_group)
            check_resp(resp)
            if protocol != "HTTP":
                assert resp["item"]["user"] == user
                assert resp["item"]["user_group"] == user_group
            else:
                assert resp["item"]["user"] != user
                assert resp["item"]["user_group"] != user_group
            check_status(await RM.status(), "executing_task")
            await RM.wait_for_idle()
            check_status(await RM.status(), "idle")
            await RM.environment_close()
            await RM.wait_for_idle()
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
        RM = instantiate_re_api_class(rm_api_class)

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
            RM = instantiate_re_api_class(rm_api_class)

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
        RM = instantiate_re_api_class(rm_api_class)

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
        check_status(RM.status(), 0 if continue_option in ("resume", "stop") else 1, 1, "idle")

        RM.close()
    else:

        async def testing():
            RM = instantiate_re_api_class(rm_api_class)

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
            check_status(await RM.status(), 0 if continue_option in ("resume", "stop") else 1, 1, "idle")

            await RM.close()

        asyncio.run(testing())


_busy_script_01 = """
import time
for n in range(30):
    time.sleep(1)
"""


# fmt: off
@pytest.mark.parametrize("option", ["ip_client", "script", "plan"])
@pytest.mark.parametrize("library", ["THREADS", "ASYNC"])
@pytest.mark.parametrize("protocol", ["ZMQ", "HTTP"])
# fmt: on
def test_kernel_interrupt_01(
    re_manager_cmd, fastapi_server, protocol, library, ip_kernel_simple_client, option  # noqa: F811
):
    """
    "REManagerAPI.kernel_interrupt():  basic test.
    """
    re_manager_cmd(["--use-ipython-kernel=ON"])  # Start in IPython mode
    rm_api_class = _select_re_manager_api(protocol, library)

    def check_status(status, ip_kernel_state, ip_kernel_captured):
        # Returned status may be used to do additional checks
        if isinstance(ip_kernel_state, (str, type(None))):
            ip_kernel_state = [ip_kernel_state]
        assert status["ip_kernel_state"] in ip_kernel_state
        assert status["ip_kernel_captured"] == ip_kernel_captured
        return status

    if not _is_async(library):
        RM = instantiate_re_api_class(rm_api_class)

        RM.environment_open()
        RM.wait_for_idle(timeout=20)

        kernel_int_params = {}

        if option == "ip_client":
            ip_kernel_simple_client.start()
            ip_kernel_simple_client.execute_with_check(_busy_script_01)
        elif option == "script":
            RM.script_upload(script=_busy_script_01)
            kernel_int_params.update(dict(interrupt_task=True))
        elif option == "plan":
            RM.item_add(BPlan("count", ["det1"], num=5, delay=1))
            status = RM.status()
            assert status["items_in_queue"] == 1
            RM.queue_start()
            kernel_int_params.update(dict(interrupt_plan=True))
        else:
            assert False, f"Unknown option {option!r}"

        ttime.sleep(2)

        ip_kernel_captured = option != "ip_client"
        status = RM.status()
        check_status(status, "busy", ip_kernel_captured)

        resp4 = RM.kernel_interrupt(**kernel_int_params)
        assert resp4["success"] is True, pprint.pformat(resp4)
        assert resp4["msg"] == "", pprint.pformat(resp4)

        if option == "ip_client":

            def condition(s):
                return s["ip_kernel_state"] == "idle"

            RM.wait_for_condition(condition, timeout=3)
        else:
            RM.wait_for_idle_or_paused(timeout=3)

        status = RM.status()
        check_status(status, "idle", False)
        if status["re_state"] == "paused":
            RM.re_stop()
            RM.wait_for_idle(timeout=10)

        RM.environment_close()
        RM.wait_for_idle(timeout=10)

        RM.close()

    else:

        async def testing():
            RM = instantiate_re_api_class(rm_api_class)

            await RM.environment_open()
            await RM.wait_for_idle(timeout=20)

            kernel_int_params = {}

            if option == "ip_client":
                # 'ip_kernel_simple_client.start()' creates another asyncio loop,
                #   so it needs to be run in a separate thread.
                def f():
                    ip_kernel_simple_client.start()
                    ip_kernel_simple_client.execute_with_check(_busy_script_01)

                th = Thread(target=f, daemon=True)
                th.start()
            elif option == "script":
                await RM.script_upload(script=_busy_script_01)
                kernel_int_params.update(dict(interrupt_task=True))
            elif option == "plan":
                await RM.item_add(BPlan("count", ["det1"], num=5, delay=1))
                status = await RM.status()
                assert status["items_in_queue"] == 1
                await RM.queue_start()
                kernel_int_params.update(dict(interrupt_plan=True))
            else:
                assert False, f"Unknown option {option!r}"

            ttime.sleep(2)

            ip_kernel_captured = option != "ip_client"
            status = await RM.status()
            check_status(status, "busy", ip_kernel_captured)

            resp4 = await RM.kernel_interrupt(**kernel_int_params)
            assert resp4["success"] is True, pprint.pformat(resp4)
            assert resp4["msg"] == "", pprint.pformat(resp4)

            if option == "ip_client":

                def condition(s):
                    return s["ip_kernel_state"] == "idle"

                await RM.wait_for_condition(condition, timeout=3)
            else:
                await RM.wait_for_idle_or_paused(timeout=3)

            status = await RM.status()
            check_status(status, "idle", False)
            if status["re_state"] == "paused":
                await RM.re_stop()
                await RM.wait_for_idle(timeout=10)

            await RM.environment_close()
            await RM.wait_for_idle(timeout=10)

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
        RM = instantiate_re_api_class(rm_api_class)
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
            RM = instantiate_re_api_class(rm_api_class)
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

        RM = instantiate_re_api_class(rm_api_class)
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

            RM = instantiate_re_api_class(rm_api_class)
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

        RM = instantiate_re_api_class(rm_api_class)

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

            RM = instantiate_re_api_class(rm_api_class)

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
        RM = instantiate_re_api_class(rm_api_class)

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
        text2 = RM.console_monitor.text()
        print(f"============= text=\n'{text}'")
        print(f"============= text2=\n'{text2}'")
        print(f"============= expected_output=\n'{expected_output}'")
        assert expected_output in text
        assert expected_output in text2

        RM.console_monitor.disable()
        assert RM.console_monitor.enabled is False

        RM.environment_close()
        RM.wait_for_idle(timeout=10)
        check_status(RM.status(), "idle", False)

        RM.close()

    else:

        async def testing():
            RM = instantiate_re_api_class(rm_api_class)

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
            text2 = await RM.console_monitor.text()
            print(f"============= text=\n{text}")
            print(f"============= text2=\n'{text2}'")
            print(f"============= expected_output=\n{expected_output}")
            assert expected_output in text
            assert expected_output in text2

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
        RM = instantiate_re_api_class(rm_api_class)

        RM.console_monitor.enable()
        assert RM.console_monitor.enabled is True

        t0 = ttime.time()
        with pytest.raises(RM.RequestTimeoutError):
            RM.console_monitor.next_msg()  # Raises an exception immediately
        assert ttime.time() - t0 < 0.5

        with pytest.raises(RM.RequestTimeoutError):
            RM.console_monitor.next_msg(timeout=2)  # Raises an exception after 2 sec. timeout
        assert ttime.time() - t0 > 1.9

        # There should be no accumulated output
        assert RM.console_monitor.text() == ""

        RM.close()

    else:

        async def testing():
            RM = instantiate_re_api_class(rm_api_class)

            RM.console_monitor.enable()
            assert RM.console_monitor.enabled is True

            t0 = ttime.time()
            with pytest.raises(RM.RequestTimeoutError):
                await RM.console_monitor.next_msg()  # Raises an exception immediately
            assert ttime.time() - t0 < 0.5

            with pytest.raises(RM.RequestTimeoutError):
                await RM.console_monitor.next_msg(timeout=2)  # Raises an exception after 2 sec. timeout
            assert ttime.time() - t0 > 1.9

            # There should be no accumulated output
            assert await RM.console_monitor.text() == ""

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
        RM = instantiate_re_api_class(rm_api_class)

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
            RM = instantiate_re_api_class(rm_api_class)

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
        RM = instantiate_re_api_class(rm_api_class)

        RM.console_monitor.enable()
        assert RM.console_monitor.enabled is True

        RM.console_monitor._msg_queue.put({"time": "", "msg": "Test message 1"})
        RM.console_monitor._msg_queue.put({"time": "", "msg": "Test message 2"})
        RM.console_monitor.clear()

        with pytest.raises(RM.RequestTimeoutError):
            RM.console_monitor.next_msg()
        assert RM.console_monitor.text() == ""

        RM.close()

    else:

        async def testing():
            RM = instantiate_re_api_class(rm_api_class)

            RM.console_monitor.enable()
            assert RM.console_monitor.enabled is True

            RM.console_monitor._msg_queue.put_nowait({"time": "", "msg": "Test message 1"})
            RM.console_monitor._msg_queue.put_nowait({"time": "", "msg": "Test message 2"})
            RM.console_monitor.clear()

            with pytest.raises(RM.RequestTimeoutError):
                await RM.console_monitor.next_msg()
            assert await RM.console_monitor.text() == ""

            await RM.close()

        asyncio.run(testing())


_script_special_1 = r"""
# Patterns to check
pattern_new_line = "\n"
pattern_cr = "\r"
pattern_up_one_line = "\x1B\x5B\x41"  # ESC [#A

import sys
sys.stdout.write("One two three four five\nOne two three four five")
sys.stdout.write(pattern_cr)
sys.stdout.write(f"Six {pattern_up_one_line}six\n\n")
"""

_script_special_1_text_expected = "One six three four five\nSix two three four five\n"


# fmt: off
@pytest.mark.parametrize("script, text_expected", [(_script_special_1, _script_special_1_text_expected)])
@pytest.mark.parametrize("library", ["THREADS", "ASYNC"])
@pytest.mark.parametrize("protocol", ["ZMQ", "HTTP"])
# fmt: on
def test_console_monitor_05(
    re_manager_cmd, fastapi_server, library, protocol, script, text_expected  # noqa: F811
):
    """
    RM.console_monitor: generating text output from messages that contain control characters.
    """

    rm_api_class = _select_re_manager_api(protocol, library)

    params = ["--zmq-publish-console", "ON"]
    re_manager_cmd(params)

    if not _is_async(library):
        RM = instantiate_re_api_class(rm_api_class)

        RM.console_monitor.enable()
        assert RM.console_monitor.enabled is True
        ttime.sleep(1)

        RM.environment_open()
        RM.wait_for_idle(timeout=10)

        RM.script_upload(script)
        ttime.sleep(2)
        RM.wait_for_idle(timeout=10)

        text = RM.console_monitor.text()
        print(f"===== text={text}")
        assert text_expected in text

        RM.console_monitor.disable()
        assert RM.console_monitor.enabled is False

        RM.environment_close()
        RM.wait_for_idle(timeout=10)

        RM.close()

    else:

        async def testing():
            RM = instantiate_re_api_class(rm_api_class)

            RM.console_monitor.enable()
            assert RM.console_monitor.enabled is True
            await asyncio.sleep(1)

            await RM.environment_open()
            await RM.wait_for_idle(timeout=10)

            await RM.script_upload(script)
            await asyncio.sleep(2)
            await RM.wait_for_idle(timeout=10)

            text = await RM.console_monitor.text()
            print(f"===== text={text}")
            assert text_expected in text

            RM.console_monitor.disable()
            assert RM.console_monitor.enabled is False

            await RM.environment_close()
            await RM.wait_for_idle(timeout=10)

            await RM.close()

        asyncio.run(testing())


# fmt: off
@pytest.mark.parametrize("n_progress_bars", [1, 3, 5])
@pytest.mark.parametrize("library", ["THREADS", "ASYNC"])
@pytest.mark.parametrize("protocol", ["ZMQ", "HTTP"])
# fmt: on
def test_console_monitor_06(re_manager_cmd, fastapi_server, library, protocol, n_progress_bars):  # noqa: F811
    """
    RM.console_monitor: generating text output with progress bars. The test is using ``plan_test_progress_bars``
    defined in built-in simulated startup code of ``bluesky-queueserver``.
    """

    rm_api_class = _select_re_manager_api(protocol, library)

    params = ["--zmq-publish-console", "ON"]
    re_manager_cmd(params)

    def check_status(status, manager_state, items_in_queue):
        assert status["manager_state"] == manager_state
        assert status["items_in_queue"] == items_in_queue

    def check_resp(resp):
        assert resp["success"] is True
        assert resp["msg"] == ""

    if not _is_async(library):
        RM = instantiate_re_api_class(rm_api_class)

        check_resp(RM.environment_open())
        RM.wait_for_idle(timeout=10)

        RM.console_monitor.enable()
        assert RM.console_monitor.enabled is True
        ttime.sleep(1)

        check_resp(RM.item_add(BPlan("plan_test_progress_bars", n_progress_bars)))
        check_status(RM.status(), "idle", 1)

        check_resp(RM.queue_start())
        RM.wait_for_idle(timeout=30)
        check_status(RM.status(), "idle", 0)

        text = RM.console_monitor.text()
        print(f"===== text={text}")

        s_start = f"TESTING {n_progress_bars} PROGRESS BARS"
        s_stop = "TEST COMPLETED"
        assert text.count(s_start) == 1, s_start
        assert text.count(s_stop) == 1, s_stop

        match = re.search(s_start + "(.|\n)+" + s_stop, text)
        assert match
        text_substr = match[0]
        for n in range(n_progress_bars):
            s = f"TEST{n + 1}"
            assert text_substr.count(s) == 1

        RM.console_monitor.disable()
        assert RM.console_monitor.enabled is False

        RM.environment_close()
        RM.wait_for_idle(timeout=10)

        RM.close()

    else:

        async def testing():
            RM = instantiate_re_api_class(rm_api_class)

            check_resp(await RM.environment_open())
            await RM.wait_for_idle(timeout=10)

            RM.console_monitor.enable()
            assert RM.console_monitor.enabled is True
            await asyncio.sleep(1)

            check_resp(await RM.item_add(BPlan("plan_test_progress_bars", n_progress_bars)))
            check_status(await RM.status(), "idle", 1)

            check_resp(await RM.queue_start())
            await RM.wait_for_idle(timeout=30)
            check_status(await RM.status(), "idle", 0)

            text = await RM.console_monitor.text()
            print(f"===== text={text}")

            s_start = f"TESTING {n_progress_bars} PROGRESS BARS"
            s_stop = "TEST COMPLETED"
            assert text.count(s_start) == 1, s_start
            assert text.count(s_stop) == 1, s_stop

            match = re.search(s_start + "(.|\n)+" + s_stop, text)
            assert match
            text_substr = match[0]
            for n in range(n_progress_bars):
                s = f"TEST{n + 1}"
                assert text_substr.count(s) == 1

            RM.console_monitor.disable()
            assert RM.console_monitor.enabled is False

            await RM.environment_close()
            await RM.wait_for_idle(timeout=10)

            await RM.close()

        asyncio.run(testing())


# fmt: off
@pytest.mark.parametrize("zero_max_msgs, zero_max_lines", [
    (False, False),
    (False, True),
    (True, False),
    (True, True),
])
@pytest.mark.parametrize("library", ["THREADS", "ASYNC"])
@pytest.mark.parametrize("protocol", ["ZMQ", "HTTP"])
# fmt: on
def test_console_monitor_07(
    re_manager_cmd, fastapi_server, library, protocol, zero_max_msgs, zero_max_lines  # noqa: F811
):
    """
    RM.console_monitor: test if message buffer and text buffer are disabled if the respective
    buffer length is set to 0.
    """
    rm_api_class = _select_re_manager_api(protocol, library)

    params = ["--zmq-publish-console", "ON"]
    re_manager_cmd(params)

    def check_resp(resp):
        assert resp["success"] is True
        assert resp["msg"] == ""

    params = {}
    if zero_max_msgs:
        params["console_monitor_max_msgs"] = 0
    if zero_max_lines:
        params["console_monitor_max_lines"] = 0

    if not _is_async(library):
        RM = instantiate_re_api_class(rm_api_class, **params)

        RM.console_monitor.enable()
        assert RM.console_monitor.enabled is True
        ttime.sleep(1)

        check_resp(RM.environment_open())
        RM.wait_for_idle(timeout=10)
        check_resp(RM.environment_close())
        RM.wait_for_idle(timeout=10)

        if zero_max_msgs:
            with pytest.raises(RM.RequestTimeoutError):
                RM.console_monitor.next_msg()
        else:
            RM.console_monitor.next_msg()

        text = RM.console_monitor.text()
        if zero_max_lines:
            assert text == ""
        else:
            assert text != ""

            RM.console_monitor.text_max_lines = 3
            text2 = RM.console_monitor.text()
            assert len(text2.split("\n")) == 3, text2

        RM.close()

    else:

        async def testing():
            RM = instantiate_re_api_class(rm_api_class, **params)

            RM.console_monitor.enable()
            assert RM.console_monitor.enabled is True
            await asyncio.sleep(1)

            check_resp(await RM.environment_open())
            await RM.wait_for_idle(timeout=10)
            check_resp(await RM.environment_close())
            await RM.wait_for_idle(timeout=10)

            if zero_max_msgs:
                with pytest.raises(RM.RequestTimeoutError):
                    await RM.console_monitor.next_msg()
            else:
                await RM.console_monitor.next_msg()

            text = await RM.console_monitor.text()
            if zero_max_lines:
                assert text == ""
            else:
                assert text != ""

                RM.console_monitor.text_max_lines = 3
                text2 = await RM.console_monitor.text()
                assert len(text2.split("\n")) == 3, text2

            await RM.close()

        asyncio.run(testing())


# fmt: off
@pytest.mark.parametrize("library", ["THREADS", "ASYNC"])
@pytest.mark.parametrize("protocol", ["ZMQ", "HTTP"])
# fmt: on
def test_console_monitor_08(re_manager_cmd, fastapi_server, library, protocol):  # noqa: F811
    """
    RM.console_monitor.text(): test all modes of operation.
    """
    rm_api_class = _select_re_manager_api(protocol, library)

    params = ["--zmq-publish-console", "ON"]
    re_manager_cmd(params)

    def check_resp(resp):
        assert resp["success"] is True
        assert resp["msg"] == ""

    if not _is_async(library):
        RM = instantiate_re_api_class(rm_api_class)

        RM.console_monitor.enable()
        assert RM.console_monitor.enabled is True
        ttime.sleep(1)
        text_uid0 = RM.console_monitor.text_uid

        # Generate some console output
        check_resp(RM.environment_open())
        RM.wait_for_idle(timeout=10)
        check_resp(RM.environment_close())
        RM.wait_for_idle(timeout=10)
        ttime.sleep(1)  # Wait until all console output is loaded

        text_uid1 = RM.console_monitor.text_uid
        text1 = RM.console_monitor.text()
        assert text_uid1 != text_uid0
        n_text1 = len(text1.split("\n"))
        assert n_text1 > 0
        assert RM.console_monitor.text() == text1

        assert RM.console_monitor.text(n_text1) == text1
        assert RM.console_monitor.text(n_text1 + 1) == text1
        assert RM.console_monitor.text(100000) == text1

        text2 = RM.console_monitor.text(n_text1 - 1)
        assert len(text2.split("\n")) == n_text1 - 1

        text3 = RM.console_monitor.text(2)
        assert len(text3.split("\n")) == 2

        text4 = RM.console_monitor.text(1)
        assert len(text4.split("\n")) == 1

        assert RM.console_monitor.text(0) == ""
        assert RM.console_monitor.text(-1) == ""

        assert RM.console_monitor.text() == text1

        assert RM.console_monitor.text_uid == text_uid1

        RM.console_monitor.clear()
        text_uid2 = RM.console_monitor.text_uid
        assert text_uid2 != text_uid1

        assert RM.console_monitor.text() == ""
        assert RM.console_monitor.text(100000) == ""
        assert RM.console_monitor.text(0) == ""
        assert RM.console_monitor.text(-1) == ""

        assert RM.console_monitor.text_uid == text_uid2

        RM.close()

    else:

        async def testing():
            RM = instantiate_re_api_class(rm_api_class)

            RM.console_monitor.enable()
            assert RM.console_monitor.enabled is True
            await asyncio.sleep(1)
            text_uid0 = RM.console_monitor.text_uid

            # Generate some console output
            check_resp(await RM.environment_open())
            await RM.wait_for_idle(timeout=10)
            check_resp(await RM.environment_close())
            await RM.wait_for_idle(timeout=10)
            await asyncio.sleep(1)

            text_uid1 = RM.console_monitor.text_uid
            text1 = await RM.console_monitor.text()
            assert text_uid1 != text_uid0
            n_text1 = len(text1.split("\n"))
            assert n_text1 > 0
            assert await RM.console_monitor.text() == text1

            assert await RM.console_monitor.text(n_text1) == text1
            assert await RM.console_monitor.text(n_text1 + 1) == text1
            assert await RM.console_monitor.text(100000) == text1

            text2 = await RM.console_monitor.text(n_text1 - 1)
            assert len(text2.split("\n")) == n_text1 - 1

            text3 = await RM.console_monitor.text(2)
            assert len(text3.split("\n")) == 2

            text4 = await RM.console_monitor.text(1)
            assert len(text4.split("\n")) == 1

            assert await RM.console_monitor.text(0) == ""
            assert await RM.console_monitor.text(-1) == ""

            assert await RM.console_monitor.text() == text1

            assert RM.console_monitor.text_uid == text_uid1

            RM.console_monitor.clear()
            text_uid2 = RM.console_monitor.text_uid
            assert text_uid2 != text_uid1

            assert await RM.console_monitor.text() == ""
            assert await RM.console_monitor.text(100000) == ""
            assert await RM.console_monitor.text(0) == ""
            assert await RM.console_monitor.text(-1) == ""

            assert RM.console_monitor.text_uid == text_uid2

            await RM.close()

        asyncio.run(testing())


# ====================================================================================================
#                                     Locking RE Manager
# ====================================================================================================


# fmt: off
@pytest.mark.parametrize("library", ["THREADS", "ASYNC"])
@pytest.mark.parametrize("protocol", ["ZMQ", "HTTP"])
# fmt: on
def test_default_lock_key_path_1(tmp_path, library, protocol):
    """
    ``default_lock_key_path`` - basic test
    """
    default_path = os.path.join(Path.home(), ".config", "qserver", "default_lock_key.txt")
    new_default_path = os.path.join(tmp_path, ".config", "qserver", "default_lock_key.txt")

    rm_api_class = _select_re_manager_api(protocol, library)

    if not _is_async(library):
        RM = instantiate_re_api_class(rm_api_class)
        assert RM.default_lock_key_path == default_path
        RM.default_lock_key_path = new_default_path
        assert RM.default_lock_key_path == new_default_path
        RM.close()

    else:

        async def testing():
            RM = instantiate_re_api_class(rm_api_class)
            assert RM.default_lock_key_path == default_path
            RM.default_lock_key_path = new_default_path
            assert RM.default_lock_key_path == new_default_path
            await RM.close()

        asyncio.run(testing())


# fmt: off
@pytest.mark.parametrize("library", ["THREADS", "ASYNC"])
@pytest.mark.parametrize("protocol", ["ZMQ", "HTTP"])
# fmt: on
def test_default_lock_key_1(tmp_path, library, protocol):
    default_path = os.path.join(tmp_path, ".config", "qserver", "default_lock_key.txt")

    rm_api_class = _select_re_manager_api(protocol, library)

    def run_test(RM):
        # The test is the same for sync and async version.

        RM.default_lock_key_path = default_path

        lock_key = RM.get_default_lock_key()
        assert RM.get_default_lock_key() == lock_key

        lock_key2 = RM.get_default_lock_key(new_key=True)
        assert lock_key2 != lock_key
        assert RM.get_default_lock_key() == lock_key2

        lock_key3 = "test-key"
        RM.set_default_lock_key(lock_key3)
        assert RM.get_default_lock_key() == lock_key3

        assert os.path.isfile(default_path), default_path

        with pytest.raises(IOError, match="'lock_key' must be a non-empty string"):
            RM.set_default_lock_key(None)
        with pytest.raises(IOError, match="'lock_key' must be a non-empty string"):
            RM.set_default_lock_key(10)
        with pytest.raises(IOError, match="'lock_key' must be a non-empty string"):
            RM.set_default_lock_key("")

    if not _is_async(library):
        RM = instantiate_re_api_class(rm_api_class)
        run_test(RM)
        RM.close()

    else:

        async def testing():
            RM = instantiate_re_api_class(rm_api_class)
            run_test(RM)
            await RM.close()

        asyncio.run(testing())


# fmt: off
@pytest.mark.parametrize("library", ["THREADS", "ASYNC"])
@pytest.mark.parametrize("protocol", ["ZMQ", "HTTP"])
# fmt: on
def test_lock_key_1(library, protocol):
    """
    ``lock_key`` and ``enable_locked_api``: basic tests
    """
    rm_api_class = _select_re_manager_api(protocol, library)

    def run_test(RM):
        # The test is the same for sync and async version.

        assert RM.lock_key is None

        with pytest.raises(ValueError, match="'lock_key' must be non-empty string or None"):
            RM.lock_key = ""
        assert RM.lock_key is None

        RM.lock_key = "abc"
        assert RM.lock_key == "abc"

        assert RM.enable_locked_api is False
        RM.enable_locked_api = True
        assert RM.enable_locked_api is True

        with pytest.raises(TypeError, match="The property may be set only to boolean values"):
            RM.enable_locked_api = 10

        RM.lock_key = None
        assert RM.enable_locked_api is False

        with pytest.raises(RuntimeError, match="current lock key is not set"):
            RM.enable_locked_api = True
        assert RM.enable_locked_api is False

    if not _is_async(library):
        RM = instantiate_re_api_class(rm_api_class)
        run_test(RM)
        RM.close()

    else:

        async def testing():
            RM = instantiate_re_api_class(rm_api_class)
            run_test(RM)
            await RM.close()

        asyncio.run(testing())


# fmt: off
@pytest.mark.parametrize("use_current_lock_key, set_note", [
    (False, False),
    (True, False),
    (True, True),
])
@pytest.mark.parametrize("library", ["THREADS", "ASYNC"])
@pytest.mark.parametrize("protocol", ["ZMQ", "HTTP"])
# fmt: on
def test_lock_1(re_manager, fastapi_server, library, protocol, use_current_lock_key, set_note):  # noqa: F811
    """
    ``lock``, ``lock_environment``, ``lock_queue``, ``lock_all``, ``unlock``, ``lock_info``: basic tests
    Call the API with all valid combinations of parameters.
    """
    rm_api_class = _select_re_manager_api(protocol, library)
    lock_key = "abc"
    note = "This is a note ..."

    def check_lock(status, environment, queue):
        assert status["lock"]["environment"] == environment
        assert status["lock"]["queue"] == queue

    def check_lock_info(lock_info_response, environment, queue):
        assert lock_info_response["success"] is True
        assert lock_info_response["msg"] == ""
        lock_info = lock_info_response["lock_info"]
        assert lock_info["environment"] == environment
        assert lock_info["queue"] == queue
        assert lock_info["note"] == (note if set_note else None)

    if not _is_async(library):
        RM = instantiate_re_api_class(rm_api_class)

        if use_current_lock_key:
            RM.lock_key = lock_key
            param_key = {}
        else:
            param_key = {"lock_key": lock_key}
        param_note = {"note": note} if set_note else {}

        RM.lock(environment=True, **param_key, **param_note)
        check_lock(RM.status(), True, False)
        check_lock_info(RM.lock_info(**param_key), True, False)
        RM.lock(queue=True, **param_key, **param_note)
        check_lock(RM.status(), False, True)
        check_lock_info(RM.lock_info(**param_key), False, True)
        RM.lock(environment=True, queue=True, **param_key, **param_note)
        check_lock(RM.status(), True, True)
        check_lock_info(RM.lock_info(**param_key), True, True)

        RM.lock_environment(**param_key, **param_note)
        check_lock(RM.status(), True, False)
        check_lock_info(RM.lock_info(**param_key), True, False)
        RM.lock_queue(**param_key, **param_note)
        check_lock(RM.status(), False, True)
        check_lock_info(RM.lock_info(**param_key), False, True)
        RM.lock_all(**param_key, **param_note)
        check_lock(RM.status(), True, True)
        check_lock_info(RM.lock_info(**param_key), True, True)

        RM.unlock(**param_key)
        check_lock(RM.status(), False, False)

        RM.close()

    else:

        async def testing():
            RM = instantiate_re_api_class(rm_api_class)

            if use_current_lock_key:
                RM.lock_key = lock_key
                param_key = {}
            else:
                param_key = {"lock_key": lock_key}
            param_note = {"note": note} if set_note else {}

            await RM.lock(environment=True, **param_key, **param_note)
            check_lock(await RM.status(), True, False)
            check_lock_info(await RM.lock_info(**param_key), True, False)
            await RM.lock(queue=True, **param_key, **param_note)
            check_lock(await RM.status(), False, True)
            check_lock_info(await RM.lock_info(**param_key), False, True)
            await RM.lock(environment=True, queue=True, **param_key, **param_note)
            check_lock(await RM.status(), True, True)
            check_lock_info(await RM.lock_info(**param_key), True, True)

            await RM.lock_environment(**param_key, **param_note)
            check_lock(await RM.status(), True, False)
            check_lock_info(await RM.lock_info(**param_key), True, False)
            await RM.lock_queue(**param_key, **param_note)
            check_lock(await RM.status(), False, True)
            check_lock_info(await RM.lock_info(**param_key), False, True)
            await RM.lock_all(**param_key, **param_note)
            check_lock(await RM.status(), True, True)
            check_lock_info(await RM.lock_info(**param_key), True, True)

            await RM.unlock(**param_key)
            check_lock(await RM.status(), False, False)

            await RM.close()

        asyncio.run(testing())


@pytest.mark.parametrize("library", ["THREADS", "ASYNC"])
@pytest.mark.parametrize("protocol", ["ZMQ", "HTTP"])
# fmt: on
def test_lock_2(re_manager, fastapi_server, library, protocol):  # noqa: F811
    """
    ``lock``, ``lock_environment``, ``lock_queue``, ``lock_all``, ``unlock``, ``lock_info``:
    Test some edge cases and invalid parameter values.
    """
    rm_api_class = _select_re_manager_api(protocol, library)
    lock_key = "abc"

    def check_lock(status, environment, queue):
        assert status["lock"]["environment"] == environment
        assert status["lock"]["queue"] == queue

    if not _is_async(library):
        RM = instantiate_re_api_class(rm_api_class)

        # No lock option is selected.
        with pytest.raises(RM.RequestFailedError, match="environment and/or queue must be selected"):
            RM.lock(lock_key=lock_key)

        # Current lock key is not set. Try to apply lock without the lock key.
        with pytest.raises(RuntimeError, match="Lock key is not set"):
            RM.lock(environment=True)
        check_lock(RM.status(), False, False)

        # Invalid type of the lock key
        with pytest.raises(ValueError, match="'lock_key' must be non-empty string or None"):
            RM.lock(environment=True, lock_key=10)
        check_lock(RM.status(), False, False)

        # Lock the manager
        RM.lock(environment=True, lock_key=lock_key)
        check_lock(RM.status(), True, False)

        # Test validation of the lock key
        RM.lock_info(lock_key=lock_key)
        with pytest.raises(RM.RequestFailedError, match="Invalid lock key"):
            RM.lock_info(lock_key="invalid-key")

        # Try to unlock with invalid key
        with pytest.raises(ValueError, match="'lock_key' must be non-empty string or None"):
            RM.unlock(lock_key=10)
        with pytest.raises(RM.RequestFailedError, match="Invalid lock key"):
            RM.unlock(lock_key="invalid-key")

        RM.unlock(lock_key=lock_key)
        check_lock(RM.status(), False, False)

        RM.close()

    else:

        async def testing():
            RM = instantiate_re_api_class(rm_api_class)

            # No lock option is selected.
            with pytest.raises(RM.RequestFailedError, match="environment and/or queue must be selected"):
                await RM.lock(lock_key=lock_key)

            # Current lock key is not set. Try to apply lock without the lock key.
            with pytest.raises(RuntimeError, match="Lock key is not set"):
                await RM.lock(environment=True)
            check_lock(await RM.status(), False, False)

            # Invalid type of the lock key
            with pytest.raises(ValueError, match="'lock_key' must be non-empty string or None"):
                await RM.lock(environment=True, lock_key=10)
            check_lock(await RM.status(), False, False)

            # Lock the manager
            await RM.lock(environment=True, lock_key=lock_key)
            check_lock(await RM.status(), True, False)

            # Test validation of the lock key
            await RM.lock_info(lock_key=lock_key)
            with pytest.raises(RM.RequestFailedError, match="Invalid lock key"):
                await RM.lock_info(lock_key="invalid-key")

            # Try to unlock with invalid key
            with pytest.raises(ValueError, match="'lock_key' must be non-empty string or None"):
                await RM.unlock(lock_key=10)
            with pytest.raises(RM.RequestFailedError, match="Invalid lock key"):
                await RM.unlock(lock_key="invalid-key")

            await RM.unlock(lock_key=lock_key)

            check_lock(await RM.status(), False, False)

            await RM.close()

        asyncio.run(testing())


# fmt: off
@pytest.mark.parametrize("pass_user_name_as_param", [False, True])
@pytest.mark.parametrize("library", ["THREADS", "ASYNC"])
@pytest.mark.parametrize("protocol", ["ZMQ", "HTTP"])
# fmt: on
def test_lock_3(re_manager, fastapi_server, library, protocol, pass_user_name_as_param):  # noqa: F811
    """
    ``lock``, ``lock_environment``, ``lock_queue``, ``lock_all``: test proper handling of user name.
    """
    rm_api_class = _select_re_manager_api(protocol, library)
    lock_key = "abc"

    user1, user2 = "lock-test-user1", "lock-test-user2"
    param = {"user": user2} if pass_user_name_as_param else {}

    def check_lock(status, environment, queue):
        assert status["lock"]["environment"] == environment
        assert status["lock"]["queue"] == queue

    def check_user_name(lock_info):
        user_expected = user2 if pass_user_name_as_param else user1
        if protocol != "HTTP":
            assert lock_info["user"] == user_expected, pprint.pformat(lock_info)
        else:
            assert lock_info["user"] != user_expected, pprint.pformat(lock_info)

    if not _is_async(library):
        RM = instantiate_re_api_class(rm_api_class)
        RM.user = user1

        resp = RM.lock(environment=True, lock_key=lock_key, **param)
        check_lock(RM.status(), True, False)
        check_user_name(resp["lock_info"])

        resp = RM.lock_queue(lock_key=lock_key, **param)
        check_lock(RM.status(), False, True)
        check_user_name(resp["lock_info"])

        resp = RM.lock_environment(lock_key=lock_key, **param)
        check_lock(RM.status(), True, False)
        check_user_name(resp["lock_info"])

        resp = RM.lock_all(lock_key=lock_key, **param)
        check_lock(RM.status(), True, True)
        check_user_name(resp["lock_info"])

        RM.unlock(lock_key=lock_key)
        check_lock(RM.status(), False, False)

        RM.close()

    else:

        async def testing():
            RM = instantiate_re_api_class(rm_api_class)
            RM.user = user1

            resp = await RM.lock(environment=True, lock_key=lock_key, **param)
            check_lock(await RM.status(), True, False)
            check_user_name(resp["lock_info"])

            resp = await RM.lock_queue(lock_key=lock_key, **param)
            check_lock(await RM.status(), False, True)
            check_user_name(resp["lock_info"])

            resp = await RM.lock_environment(lock_key=lock_key, **param)
            check_lock(await RM.status(), True, False)
            check_user_name(resp["lock_info"])

            resp = await RM.lock_all(lock_key=lock_key, **param)
            check_lock(await RM.status(), True, True)
            check_user_name(resp["lock_info"])

            await RM.unlock(lock_key=lock_key)
            check_lock(await RM.status(), False, False)

            await RM.close()

        asyncio.run(testing())


# fmt: off
@pytest.mark.parametrize("unlock_with_param", [None, False, True])  # None - do not unlock
@pytest.mark.parametrize("lock_options, is_locked", [
    ({}, False),
    ({"environment": True}, False),
    ({"queue": True}, True),  # Queue is locked
    ({"environment": True, "queue": True}, True),  # Queue is locked
])
@pytest.mark.parametrize("library", ["THREADS", "ASYNC"])
@pytest.mark.parametrize("protocol", ["ZMQ", "HTTP"])
# fmt: on
def test_zmq_api_lock_4(
    re_manager, fastapi_server, lock_options, is_locked, unlock_with_param, library, protocol  # noqa: F811
):
    """
    ``lock`` API: check the API for queue control are properly locked and unlocked
    """
    rm_api_class = _select_re_manager_api(protocol, library)
    lock_key = "custom-key"

    unlock_params = {"lock_key": lock_key} if unlock_with_param is True else {}
    plan3 = BPlan("count", ["det1", "det2"], num=5, delay=1)

    if not _is_async(library):
        RM = instantiate_re_api_class(rm_api_class)
        if unlock_with_param is False:
            RM.lock_key = lock_key
            RM.enable_locked_api = True
        else:
            RM.lock_key = "invalid-key"

        # Add 4 plans to the queue
        resp0 = RM.item_add_batch(items=[plan3, plan3, plan3, plan3])
        assert resp0["success"] is True

        def call_api(method_name, *args, **kwargs):
            success_expected = not is_locked or (unlock_with_param is not None)
            if success_expected:
                return getattr(RM, method_name)(*args, **kwargs)
            else:
                with pytest.raises(RM.RequestFailedError, match="Invalid lock key"):
                    getattr(RM, method_name)(*args, **kwargs)

        if lock_options:
            RM.lock(**lock_options, lock_key=lock_key)

        # API for uploading permissions
        call_api("permissions_reload", **unlock_params)
        resp = RM.permissions_get()
        permissions = resp["user_group_permissions"]
        call_api("permissions_set", user_group_permissions=permissions, **unlock_params)

        # Setting queue mode
        call_api("queue_mode_set", mode={"loop": False}, **unlock_params)

        # Adding items to the queue
        call_api("item_add", item=plan3, **unlock_params)
        call_api("item_add_batch", items=[plan3, plan3, plan3], **unlock_params)

        # Read the plan queue
        resp = RM.queue_get()
        plan_queue = resp["items"]
        assert len(plan_queue) >= 4  # It must contain at least 4 plans

        # Updating a queue item
        plan = plan_queue[0]
        call_api("item_update", item=plan, **unlock_params)

        # Move queue items
        call_api("item_move", pos=0, pos_dest=1, **unlock_params)
        uids = [_["item_uid"] for _ in plan_queue[2:4]]
        call_api("item_move_batch", uids=uids, pos_dest="front", **unlock_params)

        # Remove queue items
        call_api("item_remove", pos=3, **unlock_params)
        call_api("item_remove_batch", uids=uids, **unlock_params)

        # Clearing the history and the queue
        call_api("history_clear", **unlock_params)
        call_api("queue_clear", **unlock_params)

        RM.unlock(lock_key=lock_key)

        RM.close()
    else:

        async def testing():
            RM = instantiate_re_api_class(rm_api_class)

            if unlock_with_param is False:
                RM.lock_key = lock_key
                RM.enable_locked_api = True
            else:
                RM.lock_key = "invalid-key"

            # Add 4 plans to the queue
            resp0 = await RM.item_add_batch(items=[plan3, plan3, plan3, plan3])
            assert resp0["success"] is True

            async def call_api(method_name, *args, **kwargs):
                success_expected = not is_locked or (unlock_with_param is not None)
                if success_expected:
                    return await getattr(RM, method_name)(*args, **kwargs)
                else:
                    with pytest.raises(RM.RequestFailedError, match="Invalid lock key"):
                        await getattr(RM, method_name)(*args, **kwargs)

            if lock_options:
                await RM.lock(**lock_options, lock_key=lock_key)

            # API for uploading permissions
            await call_api("permissions_reload", **unlock_params)
            resp = await RM.permissions_get()
            permissions = resp["user_group_permissions"]
            await call_api("permissions_set", user_group_permissions=permissions, **unlock_params)

            # Setting queue mode
            await call_api("queue_mode_set", mode={"loop": False}, **unlock_params)

            # Adding items to the queue
            await call_api("item_add", item=plan3, **unlock_params)
            await call_api("item_add_batch", items=[plan3, plan3, plan3], **unlock_params)

            # Read the plan queue
            resp = await RM.queue_get()
            plan_queue = resp["items"]
            assert len(plan_queue) >= 4  # It must contain at least 4 plans

            # Updating a queue item
            plan = plan_queue[0]
            await call_api("item_update", item=plan, **unlock_params)

            # Move queue items
            await call_api("item_move", pos=0, pos_dest=1, **unlock_params)
            uids = [_["item_uid"] for _ in plan_queue[2:4]]
            await call_api("item_move_batch", uids=uids, pos_dest="front", **unlock_params)

            # Remove queue items
            await call_api("item_remove", pos=3, **unlock_params)
            await call_api("item_remove_batch", uids=uids, **unlock_params)

            # Clearing the history and the queue
            await call_api("history_clear", **unlock_params)
            await call_api("queue_clear", **unlock_params)

            await RM.unlock(lock_key=lock_key)

            await RM.close()

        asyncio.run(testing())


# fmt: off
@pytest.mark.parametrize("unlock_with_param", [None, False, True])  # None - do not unlock
@pytest.mark.parametrize("lock_options, is_locked", [
    ({}, False),
    ({"queue": True}, False),
    ({"environment": True}, True),  # Queue is locked
    ({"environment": True, "queue": True}, True),  # Queue is locked
])
@pytest.mark.parametrize("library", ["THREADS", "ASYNC"])
@pytest.mark.parametrize("protocol", ["ZMQ", "HTTP"])
# fmt: on
def test_zmq_api_lock_5(
    re_manager, fastapi_server, lock_options, is_locked, unlock_with_param, library, protocol  # noqa: F811
):
    """
    ``lock`` API: check the API for environment control are properly locked and unlocked
    """
    rm_api_class = _select_re_manager_api(protocol, library)
    lock_key = "custom-key"

    unlock_params = {"lock_key": lock_key} if unlock_with_param is True else {}
    plan1 = BPlan("count", ["det1", "det2"], num=1)
    plan3 = BPlan("count", ["det1", "det2"], num=5, delay=1)
    func = BFunc("function_sleep", 0.5)

    if not _is_async(library):
        RM = instantiate_re_api_class(rm_api_class)
        if unlock_with_param is False:
            RM.lock_key = lock_key
            RM.enable_locked_api = True
        else:
            RM.lock_key = "invalid-key"

        def call_api(method_name, *args, **kwargs):
            success_expected = not is_locked or (unlock_with_param is not None)
            if success_expected:
                return getattr(RM, method_name)(*args, **kwargs)
            else:
                with pytest.raises(RM.RequestFailedError, match="Invalid lock key"):
                    getattr(RM, method_name)(*args, **kwargs)

        if lock_options:
            RM.lock(**lock_options, lock_key=lock_key)

        # Open and destroy the environment
        call_api("environment_open", **unlock_params)
        RM.wait_for_idle(timeout=20)
        assert RM.status()["worker_environment_exists"] == (not is_locked or unlock_with_param is not None)
        call_api("environment_destroy", **unlock_params)
        RM.wait_for_idle(timeout=20)
        assert RM.status()["worker_environment_exists"] is False

        # Open the environment again
        call_api("environment_open", **unlock_params)
        RM.wait_for_idle(timeout=20)
        assert RM.status()["worker_environment_exists"] == (not is_locked or unlock_with_param is not None)

        for api_to_test in ("re_resume", "re_stop", "re_abort", "re_halt"):
            print("=======================================================================")
            print(f"                       TESTING {api_to_test!r}")
            print("=======================================================================")
            # Always add the plan (not part of the test, but necessary for the test to complete)
            RM.item_add(item=plan3, lock_key=lock_key)

            call_api("queue_start", **unlock_params)

            # Wait until the queue starts. Otherwise 'queue_stop' may stop the queue
            #   before execution of the first plan is started and the test will fail
            ttime.sleep(0.5)

            call_api("queue_stop", **unlock_params)
            call_api("queue_stop_cancel", **unlock_params)

            ttime.sleep(1)

            call_api("re_pause", **unlock_params)
            RM.wait_for_idle_or_paused(timeout=20)
            manager_state = "paused" if not is_locked or (unlock_with_param is not None) else "idle"
            assert RM.status()["manager_state"] == manager_state

            call_api(api_to_test, **unlock_params)

            RM.wait_for_idle(timeout=20)

        call_api("item_execute", item=plan1, **unlock_params)
        RM.wait_for_idle(timeout=20)

        call_api("script_upload", script="", **unlock_params)
        RM.wait_for_idle(timeout=20)

        call_api("function_execute", item=func, **unlock_params)
        RM.wait_for_idle(timeout=20)

        # Close the environment
        call_api("environment_close", **unlock_params)
        RM.wait_for_idle(timeout=20)
        assert RM.status()["worker_environment_exists"] is False

        RM.unlock(lock_key=lock_key)

        RM.close()
    else:

        async def testing():
            RM = instantiate_re_api_class(rm_api_class)

            if unlock_with_param is False:
                RM.lock_key = lock_key
                RM.enable_locked_api = True
            else:
                RM.lock_key = "invalid-key"

            async def call_api(method_name, *args, **kwargs):
                success_expected = not is_locked or (unlock_with_param is not None)
                if success_expected:
                    return await getattr(RM, method_name)(*args, **kwargs)
                else:
                    with pytest.raises(RM.RequestFailedError, match="Invalid lock key"):
                        await getattr(RM, method_name)(*args, **kwargs)

            if lock_options:
                await RM.lock(**lock_options, lock_key=lock_key)

            # Open and destroy the environment
            await call_api("environment_open", **unlock_params)
            await RM.wait_for_idle(timeout=20)
            status = await RM.status()
            assert status["worker_environment_exists"] == (not is_locked or unlock_with_param is not None)
            await call_api("environment_destroy", **unlock_params)
            await RM.wait_for_idle(timeout=20)
            status = await RM.status()
            assert status["worker_environment_exists"] is False

            # Open the environment again
            await call_api("environment_open", **unlock_params)
            await RM.wait_for_idle(timeout=20)
            status = await RM.status()
            assert status["worker_environment_exists"] == (not is_locked or unlock_with_param is not None)

            for api_to_test in ("re_resume", "re_stop", "re_abort", "re_halt"):
                print("=======================================================================")
                print(f"                       TESTING {api_to_test!r}")
                print("=======================================================================")
                # Always add the plan (not part of the test, but necessary for the test to complete)
                await RM.item_add(item=plan3, lock_key=lock_key)

                await call_api("queue_start", **unlock_params)

                # Wait until the queue starts. Otherwise 'queue_stop' may stop the queue
                #   before execution of the first plan is started and the test will fail
                await asyncio.sleep(0.5)

                await call_api("queue_stop", **unlock_params)
                await call_api("queue_stop_cancel", **unlock_params)

                await asyncio.sleep(1)

                await call_api("re_pause", **unlock_params)
                await RM.wait_for_idle_or_paused(timeout=20)
                manager_state = "paused" if not is_locked or (unlock_with_param is not None) else "idle"
                status = await RM.status()
                assert status["manager_state"] == manager_state

                await call_api(api_to_test, **unlock_params)

                await RM.wait_for_idle(timeout=20)

            await call_api("item_execute", item=plan1, **unlock_params)
            await RM.wait_for_idle(timeout=20)

            await call_api("script_upload", script="", **unlock_params)
            await RM.wait_for_idle(timeout=20)

            await call_api("function_execute", item=func, **unlock_params)
            await RM.wait_for_idle(timeout=20)

            # Close the environment
            await call_api("environment_close", **unlock_params)
            await RM.wait_for_idle(timeout=20)
            status = await RM.status()
            assert status["worker_environment_exists"] is False

            await RM.close()

        asyncio.run(testing())
