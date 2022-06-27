import asyncio
import pytest

from bluesky_queueserver import generate_zmq_keys

from .common import re_manager_cmd  # noqa: F401
from .common import fastapi_server_fs  # noqa: F401
from .common import (
    set_qserver_zmq_address,
    set_qserver_zmq_public_key,
    _is_async,
    _select_re_manager_api,
    instantiate_re_api_class,
)


# fmt: off
@pytest.mark.parametrize("option", ["params", "ev", "default_addr"])
@pytest.mark.parametrize("library", ["THREADS", "ASYNC"])
@pytest.mark.parametrize("protocol", ["ZMQ", "HTTP"])
# fmt: on
def test_ReManagerAPI_parameters_01(
    monkeypatch, re_manager_cmd, fastapi_server_fs, protocol, library, option  # noqa: F811
):
    """
    ReManagerComm_ZMQ_Threads and ReManagerComm_ZMQ_Async,
    ReManagerComm_HTTP_Threads and ReManagerComm_HTTP_Async:
    Check that the server addresses are properly set with parameters and EVs.
    ZMQ: ``zmq_control_addr``, ``zmq_info_addr``, ``QSERVER_ZMQ_CONTROL_ADDRESS``,
    ``QSERVER_ZMQ_INFO_ADDRESS``. HTTP: ``http_server_uri``, ``QSERVER_HTTP_SERVER_URI``.
    """
    zmq_control_addr_server = "tcp://*:60616"
    zmq_control_addr_client = "tcp://localhost:60616"
    zmq_info_addr_server = "tcp://*:60617"
    zmq_info_addr_client = "tcp://localhost:60617"
    http_host = "localhost"
    http_port = 60611
    http_server_uri = f"http://{http_host}:{http_port}"

    zmq_public_key, zmq_private_key = generate_zmq_keys()

    set_qserver_zmq_address(monkeypatch, zmq_server_address=zmq_control_addr_client)
    set_qserver_zmq_public_key(monkeypatch, server_public_key=zmq_public_key)
    monkeypatch.setenv("QSERVER_ZMQ_PRIVATE_KEY_FOR_SERVER", zmq_private_key)
    re_manager_cmd(
        [
            "--zmq-publish-console=ON",
            f"--zmq-control-addr={zmq_control_addr_server}",
            f"--zmq-info-addr={zmq_info_addr_server}",
        ]
    )

    if protocol == "HTTP":
        monkeypatch.setenv("QSERVER_ZMQ_CONTROL_ADDRESS", zmq_control_addr_client)
        monkeypatch.setenv("QSERVER_ZMQ_INFO_ADDRESS", zmq_info_addr_client)
        monkeypatch.setenv("QSERVER_ZMQ_PUBLIC_KEY", zmq_public_key)
        fastapi_server_fs(http_server_host=http_host, http_server_port=http_port)
        if option in "params":
            params = {"http_server_uri": http_server_uri}
        elif option == "ev":
            params = {}
            monkeypatch.setenv("QSERVER_HTTP_SERVER_URI", http_server_uri)
        elif option == "default_addr":
            params = {}
        else:
            assert False, "Unknown option: {option!r}"
    elif protocol == "ZMQ":
        if option == "params":
            params = {
                "zmq_control_addr": zmq_control_addr_client,
                "zmq_info_addr": zmq_info_addr_client,
                "zmq_public_key": zmq_public_key,
            }
        elif option == "ev":
            params = {}
            monkeypatch.setenv("QSERVER_ZMQ_CONTROL_ADDRESS", zmq_control_addr_client)
            monkeypatch.setenv("QSERVER_ZMQ_INFO_ADDRESS", zmq_info_addr_client)
            monkeypatch.setenv("QSERVER_ZMQ_PUBLIC_KEY", zmq_public_key)
        elif option == "default_addr":
            params = {}
        else:
            assert False, "Unknown option: {option!r}"
    else:
        assert False, "Unknown protocol: {protocol!r}"

    rm_api_class = _select_re_manager_api(protocol, library)

    if not _is_async(library):
        RM = instantiate_re_api_class(rm_api_class, **params)
        if option == "default_addr":
            # ZMQ - RequestTimeoutError, HTTP - RequestError
            with pytest.raises((RM.RequestTimeoutError, RM.RequestError)):
                RM.status()
        else:
            RM.status()
            RM.console_monitor.enable()
            RM.environment_open()
            RM.wait_for_idle()
            RM.environment_close()
            RM.wait_for_idle()
            RM.console_monitor.disable()

            text = RM.console_monitor.text()
            assert "RE Environment is ready" in text, text
    else:

        async def testing():
            RM = instantiate_re_api_class(rm_api_class, **params)
            if option == "default_addr":
                # ZMQ - RequestTimeoutError, HTTP - RequestError
                with pytest.raises((RM.RequestTimeoutError, RM.RequestError)):
                    await RM.status()
            else:
                await RM.status()
                RM.console_monitor.enable()
                await RM.environment_open()
                await RM.wait_for_idle()
                await RM.environment_close()
                await RM.wait_for_idle()
                RM.console_monitor.disable()

                text = await RM.console_monitor.text()
                assert "RE Environment is ready" in text, text

        asyncio.run(testing())
