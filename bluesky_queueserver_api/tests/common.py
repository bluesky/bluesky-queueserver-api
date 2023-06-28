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
    set_qserver_zmq_address,
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
