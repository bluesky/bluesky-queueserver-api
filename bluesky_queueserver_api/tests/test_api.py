import asyncio
import getpass
import pytest
import re
import threading
import time as ttime

from .common import re_manager, re_manager_cmd  # noqa: F401
from .common import fastapi_server, fastapi_server_fs  # noqa: F401
from .common import _is_async, _select_re_manager_api, instantiate_re_api_class

from bluesky_queueserver_api import BPlan, BFunc, WaitMonitor

_plan1 = {"name": "count", "args": [["det1", "det2"]], "item_type": "plan"}


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
        assert RM.user_group == "admin"

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
            assert RM.user_group == "admin"

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

    _user, _user_group = "Test User", "admin"

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
        RM = instantiate_re_api_class(rm_api_class)
        check_status(RM.status(), False)
        check_resp(RM.queue_mode_set(loop=True))
        check_status(RM.status(), True)
        check_resp(RM.queue_mode_set(loop=False))
        check_status(RM.status(), False)
        RM.close()
    else:

        async def testing():
            RM = instantiate_re_api_class(rm_api_class)
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
        RM = instantiate_re_api_class(rm_api_class)
        check_status(RM.status(), False)
        check_resp(RM.queue_mode_set(mode={"loop": True}))
        check_status(RM.status(), True)
        check_resp(RM.queue_mode_set(mode="default"))
        check_status(RM.status(), False)
        RM.close()
    else:

        async def testing():
            RM = instantiate_re_api_class(rm_api_class)
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
            RM = instantiate_re_api_class(rm_api_class)

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


# fmt: off
@pytest.mark.parametrize("library", ["THREADS", "ASYNC"])
@pytest.mark.parametrize("protocol", ["ZMQ", "HTTP"])
# fmt: on
def test_function_execute_01(re_manager, fastapi_server, protocol, library):  # noqa: F811
    """
    ``item_function_execute``: test that 'user' and 'user_group' parameters override defaults
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
# @pytest.mark.parametrize("protocol", ["HTTP"])
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
