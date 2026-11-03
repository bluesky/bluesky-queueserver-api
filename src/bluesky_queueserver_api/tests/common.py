import asyncio
import time as ttime
import uuid

from bluesky_httpserver.tests.conftest import (  # noqa: F401
    API_KEY_FOR_TESTS,
    fastapi_server,
    fastapi_server_fs,
    setup_server_with_config_file,
)
from bluesky_queueserver.manager.tests.common import (  # noqa: F401
    ip_kernel_simple_client,
    re_manager,
    re_manager_cmd,
    re_manager_factory,
    set_qserver_zmq_address,
    set_qserver_zmq_encoding,
    set_qserver_zmq_public_key,
)

from bluesky_queueserver_api.http import REManagerAPI as REManagerAPI_http_threads
from bluesky_queueserver_api.http.aio import REManagerAPI as REManagerAPI_http_async
from bluesky_queueserver_api.zmq import REManagerAPI as REManagerAPI_zmq_threads
from bluesky_queueserver_api.zmq.aio import REManagerAPI as REManagerAPI_zmq_async

# from .common import re_manager, re_manager_pc_copy, re_manager_cmd, db_catalog  # noqa: F401


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


def instantiate_re_api_class(rm_api_class, **kwargs):
    RM = rm_api_class(**kwargs)
    if RM.protocol == RM.Protocols.HTTP:
        RM.set_authorization_key(api_key=API_KEY_FOR_TESTS)
    return RM


def wait_for_monitor_status(RM, *, timeout=10, **expected):
    """Wait for a matching published status, ignoring older and non-status messages."""
    deadline = ttime.monotonic() + timeout
    status = None
    while (remaining := deadline - ttime.monotonic()) > 0:
        try:
            msg = RM.system_info_monitor.next_msg(timeout=min(0.1, remaining))
        except RM.RequestTimeoutError:
            continue
        status = msg["msg"].get("status", status)
        if status is not None and all(status.get(key) == value for key, value in expected.items()):
            return status
    raise AssertionError(f"Timed out waiting for published status {expected!r}; last status: {status!r}")


async def wait_for_monitor_status_async(RM, *, timeout=10, **expected):
    """Asynchronous version of :func:`wait_for_monitor_status`."""
    deadline = ttime.monotonic() + timeout
    status = None
    while (remaining := deadline - ttime.monotonic()) > 0:
        try:
            msg = await RM.system_info_monitor.next_msg(timeout=min(0.1, remaining))
        except RM.RequestTimeoutError:
            continue
        status = msg["msg"].get("status", status)
        if status is not None and all(status.get(key) == value for key, value in expected.items()):
            return status
    raise AssertionError(f"Timed out waiting for published status {expected!r}; last status: {status!r}")


def wait_for_console_text(RM, expected, *, timeout=10):
    """Wait for delivery through the console transport, independently of manager state."""
    deadline = ttime.monotonic() + timeout
    text = ""
    while ttime.monotonic() < deadline:
        text = RM.console_monitor.text()
        if expected in text:
            return text
        ttime.sleep(0.05)
    raise AssertionError(f"Timed out waiting for console text {expected!r}; received: {text!r}")


async def wait_for_console_text_async(RM, expected, *, timeout=10):
    """Asynchronous version of :func:`wait_for_console_text`."""
    deadline = ttime.monotonic() + timeout
    text = ""
    while ttime.monotonic() < deadline:
        text = await RM.console_monitor.text()
        if expected in text:
            return text
        await asyncio.sleep(0.05)
    raise AssertionError(f"Timed out waiting for console text {expected!r}; received: {text!r}")


def wait_for_console_ready(RM, *, timeout=10):
    """Probe until the subscriber receives output; early PUB messages may be lost."""
    marker = f"console-ready-{uuid.uuid4()}"
    deadline = ttime.monotonic() + timeout
    while ttime.monotonic() < deadline:
        response = RM.script_upload(f"print({marker!r})")
        RM.wait_for_completed_task(response["task_uid"], timeout=timeout)
        if marker in RM.console_monitor.text():
            return
        ttime.sleep(0.1)
    raise AssertionError("Console monitor did not receive the readiness probe")


async def wait_for_console_ready_async(RM, *, timeout=10):
    """Asynchronous version of :func:`wait_for_console_ready`."""
    marker = f"console-ready-{uuid.uuid4()}"
    deadline = ttime.monotonic() + timeout
    while ttime.monotonic() < deadline:
        response = await RM.script_upload(f"print({marker!r})")
        await RM.wait_for_completed_task(response["task_uid"], timeout=timeout)
        if marker in await RM.console_monitor.text():
            return
        await asyncio.sleep(0.1)
    raise AssertionError("Console monitor did not receive the readiness probe")
