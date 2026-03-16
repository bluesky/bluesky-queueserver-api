"""Tests for synchronous (threads) communication classes"""

import re

import pytest
from bluesky_queueserver import generate_zmq_keys

from bluesky_queueserver_api._defaults import default_http_server_uri, default_user_group
from bluesky_queueserver_api.comm_threads import ReManagerComm_HTTP_Threads, ReManagerComm_ZMQ_Threads

from .common import fastapi_server  # noqa: F401
from .common import (  # noqa: F401
    API_KEY_FOR_TESTS,
    re_manager,
    re_manager_cmd,
    set_qserver_zmq_address,
    set_qserver_zmq_encoding,
    set_qserver_zmq_public_key,
)

_plan1 = {"name": "count", "args": [["det1", "det2"]], "item_type": "plan"}
_user = "Test User"
_user_group = default_user_group


def test_ReManagerComm_ZMQ_Threads_01():
    """
    ReManagerComm_ZMQ_Threads: basic test.
    Create an object, send a request and catch timeout error (the server is not running)
    """
    params = {"item": _plan1, "user": _user, "user_group": _user_group}

    RM = ReManagerComm_ZMQ_Threads(timeout_recv=0.2)
    with pytest.raises(RM.RequestTimeoutError, match="timeout occurred"):
        RM.send_request(method="queue_item_add", params=params)
    RM.close()


def test_ReManagerComm_ZMQ_Threads_02(monkeypatch, re_manager_cmd):  # noqa: F811
    """
    ReManagerComm_ZMQ_Threads: Test if the setting
    ``zmq_server_address`` and ``server_public_address`` work as expected.
    """
    zmq_manager_addr = r"tcp://*:60650"
    zmq_server_addr = r"tcp://localhost:60650"
    params = {"item": _plan1, "user": _user, "user_group": _user_group}

    public_key, private_key = generate_zmq_keys()

    # Configure communication functions built into the test system
    set_qserver_zmq_public_key(monkeypatch, server_public_key=public_key)
    set_qserver_zmq_address(monkeypatch, zmq_server_address=zmq_server_addr)
    # Configure and start RE Manager
    monkeypatch.setenv("QSERVER_ZMQ_PRIVATE_KEY", private_key)
    re_manager_cmd(["--zmq-addr", zmq_manager_addr])

    RM = ReManagerComm_ZMQ_Threads(zmq_control_addr=zmq_server_addr, zmq_public_key=public_key)
    result = RM.send_request(method="queue_item_add", params=params)
    assert result["success"] is True
    RM.close()


# fmt: off
@pytest.mark.parametrize("zmq_encoding", ["json", "msgpack"])
# fmt: on
def test_ReManagerComm_ZMQ_Threads_03(monkeypatch, re_manager_cmd, zmq_encoding):  # noqa: F811
    """
    ReManagerComm_ZMQ_Threads: Test if the setting ``zmq_encoding`` works as expected.
    """
    params = {"item": _plan1, "user": _user, "user_group": _user_group}

    public_key, private_key = generate_zmq_keys()

    set_qserver_zmq_public_key(monkeypatch, server_public_key=public_key)
    set_qserver_zmq_encoding(monkeypatch, encoding=zmq_encoding)
    monkeypatch.setenv("QSERVER_ZMQ_PRIVATE_KEY", private_key)
    re_manager_cmd([f"--zmq-encoding={zmq_encoding}"])

    RM = ReManagerComm_ZMQ_Threads(zmq_encoding=zmq_encoding, zmq_public_key=public_key)
    result = RM.send_request(method="queue_item_add", params=params)
    assert result["success"] is True
    RM.close()


def test_ReManagerComm_HTTP_Threads_01():
    """
    ReManagerComm_HTTP_Threads: basic test.
    Create an object, send a request and catch HTTPRequestError (the server is not running)
    """
    params = {"item": _plan1}

    RM = ReManagerComm_HTTP_Threads(http_server_uri="http://127.0.0.1:1")
    with pytest.raises(RM.HTTPRequestError):
        RM.send_request(method="queue_item_add", params=params)
    RM.close()


def test_ReManagerComm_HTTP_Threads_02(re_manager, fastapi_server):  # noqa: F811
    """
    ReManagerComm_HTTP_Threads: Test if parameter for setting HTTP server URI works as expected
    """
    params = {"item": _plan1}

    test_cases = [
        (None, True),
        (default_http_server_uri, True),
        ("http://localhost:60660", False),
    ]

    for server_uri, success in test_cases:
        RM = ReManagerComm_HTTP_Threads(http_server_uri=server_uri)
        RM.set_authorization_key(api_key=API_KEY_FOR_TESTS)
        if success:
            result = RM.send_request(method="queue_item_add", params=params)
            assert result["success"] is True
        else:
            with pytest.raises(RM.HTTPRequestError):
                RM.send_request(method="queue_item_add", params=params)
        RM.close()


def test_ReManagerComm_HTTP_Threads_03():
    """
    ReManagerComm_HTTP_Threads: Attempt to call unknown method, which does not exist
    in the table and can not be converted to endpoint name.
    """
    RM = ReManagerComm_HTTP_Threads()
    with pytest.raises(RM.RequestParameterError, match=re.escape("Unknown method 'unknown_method'")):
        RM.send_request(method="unknown_method")
    RM.close()


def test_ReManagerComm_ZMQ_Threads_requests(re_manager, fastapi_server):  # noqa: F811
    """
    ReManagerComm_ZMQ_Threads: Send a request: successful (accepted by the server),
    rejected and raising an exception, rejected not raising an exception.
    """
    params = {"item": _plan1, "user": _user, "user_group": _user_group}
    params_invalid = {"user": _user, "user_group": _user_group}

    RM = ReManagerComm_ZMQ_Threads()
    result = RM.send_request(method="queue_item_add", params=params)
    assert result["success"] is True
    RM.close()

    RM = ReManagerComm_ZMQ_Threads()
    # Test that the exception is raised
    with pytest.raises(RM.RequestFailedError, match="request contains no item info"):
        RM.send_request(method="queue_item_add", params=params_invalid)
    # Test that the exception has the copy of request
    try:
        RM.send_request(method="queue_item_add", params=params_invalid)
    except RM.RequestFailedError as ex:
        assert ex.response["success"] is False
        assert "request contains no item info" in ex.response["msg"]
    else:
        assert False
    RM.close()

    # Do not raise the exceptions if the request fails (rejected by the server)
    RM = ReManagerComm_ZMQ_Threads(request_fail_exceptions=False)
    result = RM.send_request(method="queue_item_add", params=params_invalid)
    assert result["success"] is False
    assert "request contains no item info" in result["msg"]
    RM.close()


def test_ReManagerComm_HTTP_Threads_requests(re_manager, fastapi_server):  # noqa: F811
    """
    ReManagerComm_HTTP_Threads: Send a request: successful (accepted by the server),
    rejected and raising an exception, rejected not raising an exception.
    """
    params = {"item": _plan1}
    params_invalid = {"user": _user}

    RM = ReManagerComm_HTTP_Threads()
    RM.set_authorization_key(api_key=API_KEY_FOR_TESTS)
    result = RM.send_request(method="queue_item_add", params=params)
    assert result["success"] is True
    RM.close()

    RM = ReManagerComm_HTTP_Threads()
    RM.set_authorization_key(api_key=API_KEY_FOR_TESTS)
    # Test that the exception is raised
    with pytest.raises(RM.RequestFailedError, match="request contains no item info"):
        RM.send_request(method="queue_item_add", params=params_invalid)
    # Test that the exception has the copy of request
    try:
        RM.send_request(method="queue_item_add", params=params_invalid)
    except RM.RequestFailedError as ex:
        assert ex.response["success"] is False
        assert "request contains no item info" in ex.response["msg"]
    else:
        assert False
    RM.close()

    # Do not raise the exceptions if the request fails (rejected by the server)
    RM = ReManagerComm_HTTP_Threads(request_fail_exceptions=False)
    RM.set_authorization_key(api_key=API_KEY_FOR_TESTS)
    result = RM.send_request(method="queue_item_add", params=params_invalid)
    assert result["success"] is False
    assert "request contains no item info" in result["msg"]
    RM.close()
