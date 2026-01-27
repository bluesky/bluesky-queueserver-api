from typing import Any
from bluesky.utils import maybe_await
from bluesky import Msg
from ..zmq import REManagerAPI as ZMQ_REManagerAPI
from ..zmq.aio import REManagerAPI as ZMQ_REManagerAPI_AIO
from ..http import REManagerAPI as HTTP_REManagerAPI
from ..http.aio import REManagerAPI as HTTP_REManagerAPI_AIO
from ..console_monitor import (
    ConsoleMonitor_ZMQ_Threads,
    ConsoleMonitor_ZMQ_Async,
    ConsoleMonitor_HTTP_Threads,
    ConsoleMonitor_HTTP_Async,
)

REMOTE_QUEUE_COMMAND = "remote_queue"


def is_allowed_type(obj: Any) -> bool:
    if isinstance(
        obj,
        (
            ZMQ_REManagerAPI,
            ZMQ_REManagerAPI_AIO,
            HTTP_REManagerAPI,
            HTTP_REManagerAPI_AIO,
            ConsoleMonitor_HTTP_Threads,
            ConsoleMonitor_HTTP_Async,
            ConsoleMonitor_ZMQ_Threads,
            ConsoleMonitor_ZMQ_Async,
        ),
    ):
        return True
    return False


def is_property(obj: Any, attr_name: str) -> bool:
    attr = getattr(obj.__class__, attr_name, None)
    return isinstance(attr, property)


async def remote_queue_coroutine(msg: Msg) -> Any:
    run_manager = msg.obj

    if not is_allowed_type(run_manager):
        raise ValueError("The object is not an instance of REManagerAPI or ConsoleMonitor.")

    attr_name = msg.args[0]
    args = msg.args[1]
    kwargs = msg.args[2]
    attr = getattr(run_manager, attr_name)

    if callable(attr):
        result = await maybe_await(attr(*args, **kwargs))
    elif is_property(run_manager, attr_name):
        if args:
            if args[0] is not None:
                setattr(run_manager, attr_name, args[0])
        result = attr
    else:
        raise ValueError(f"The attribute '{attr_name}' is neither callable nor a property of REManagerAPI.")

    return result
