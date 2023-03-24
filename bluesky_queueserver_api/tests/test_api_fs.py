import asyncio
import getpass
import pprint
import time as ttime
from io import StringIO

import pytest
from bluesky_queueserver import generate_zmq_keys

from ..comm_base import RequestParameterError
from .common import fastapi_server_fs  # noqa: F401
from .common import re_manager_cmd  # noqa: F401
from .common import (
    _is_async,
    _select_re_manager_api,
    instantiate_re_api_class,
    set_qserver_zmq_address,
    set_qserver_zmq_public_key,
    setup_server_with_config_file,
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
            # ZMQ - RequestTimeoutError, HTTP - HTTPRequestError
            with pytest.raises((RM.RequestTimeoutError, RM.HTTPRequestError)):
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

        RM.close()

    else:

        async def testing():
            RM = instantiate_re_api_class(rm_api_class, **params)
            if option == "default_addr":
                # ZMQ - RequestTimeoutError, HTTP - HTTPRequestError
                with pytest.raises((RM.RequestTimeoutError, RM.HTTPRequestError)):
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

            await RM.close()

        asyncio.run(testing())


# fmt: off
@pytest.mark.parametrize("tout, tout_login, tset, tset_login", [
    (0.5, 10, 0.5, 10),
    (None, None, 5.0, 60.0),  # Default values
    (0, 0, 0, 0),  # Disables timeout by default
])
@pytest.mark.parametrize("library", ["THREADS", "ASYNC"])
@pytest.mark.parametrize("protocol", ["HTTP"])
# fmt: on
def test_ReManagerAPI_parameters_02(protocol, library, tout, tout_login, tset, tset_login):
    """
    classes ReManagerComm_HTTP_Threads and ReManagerComm_HTTP_Async:
    Test that 'timeout' and 'timeout_login' are set correctly.
    """
    rm_api_class = _select_re_manager_api(protocol, library)

    if not _is_async(library):
        RM = instantiate_re_api_class(rm_api_class, timeout=tout, timeout_login=tout_login)
        assert RM._timeout == tset
        assert RM._timeout_login == tset_login
        RM.close()

    else:

        async def testing():
            RM = instantiate_re_api_class(rm_api_class, timeout=tout, timeout_login=tout_login)
            assert RM._timeout == tset
            assert RM._timeout_login == tset_login
            await RM.close()

        asyncio.run(testing())


# fmt: off
@pytest.mark.parametrize("library", ["THREADS", "ASYNC"])
@pytest.mark.parametrize("protocol", ["HTTP"])
# fmt: on
def test_send_request_1(re_manager_cmd, fastapi_server_fs, protocol, library):  # noqa: F811
    """
    ``send_request`` API: basic functionality and error handling (for HTTP requests).
    """
    re_manager_cmd()
    fastapi_server_fs()

    rm_api_class = _select_re_manager_api(protocol, library)

    if not _is_async(library):
        RM = instantiate_re_api_class(rm_api_class)

        status = RM.status()
        status2 = RM.send_request(method="status")
        assert status2 == status
        status3 = RM.send_request(method=("GET", "/api/status"))
        assert status3 == status

        with pytest.raises(RM.RequestParameterError, match="Unknown method"):
            RM.send_request(method="abc")

        with pytest.raises(RM.RequestParameterError, match="must be a string or an iterable"):
            RM.send_request(method=10)

        for method in (
            ("GET", "/api/status", "aaa"),
            ("GET",),
            (10, "/api/status"),
            ("GET", {}),
            (10, 20),
        ):
            print(f"Testing method: {method}")
            with pytest.raises(RM.RequestParameterError, match="must consist of 2 string elements"):
                RM.send_request(method=method)

        RM.close()
    else:

        async def testing():
            RM = instantiate_re_api_class(rm_api_class)

            status = await RM.status()
            status2 = await RM.send_request(method="status")
            assert status2 == status
            status3 = await RM.send_request(method=("GET", "/api/status"))
            assert status3 == status

            with pytest.raises(RM.RequestParameterError, match="Unknown method"):
                await RM.send_request(method="abc")

            with pytest.raises(RM.RequestParameterError, match="must be a string or an iterable"):
                await RM.send_request(method=10)

            for method in (
                ("GET", "/api/status", "aaa"),
                ("GET",),
                (10, "/api/status"),
                ("GET", {}),
                (10, 20),
            ):
                print(f"Testing method: {method}")
                with pytest.raises(RM.RequestParameterError, match="must consist of 2 string elements"):
                    await RM.send_request(method=method)

            await RM.close()

        asyncio.run(testing())


# fmt: off
@pytest.mark.parametrize("library", ["THREADS", "ASYNC"])
@pytest.mark.parametrize("protocol", ["HTTP"])
# fmt: on
def test_send_request_2(fastapi_server_fs, protocol, library):  # noqa: F811
    """
    ``send_request`` API: timeout (for HTTP requests).
    """
    fastapi_server_fs()
    rm_api_class = _select_re_manager_api(protocol, library)

    if not _is_async(library):
        RM = instantiate_re_api_class(rm_api_class)

        # No timeout
        status = RM.send_request(method=("GET", "/api/test/server/sleep"), params={"time": 3})
        assert status["success"] is True

        # Set timeout for the given request
        with pytest.raises(RM.RequestTimeoutError):
            RM.send_request(method=("GET", "/api/test/server/sleep"), params={"time": 3}, timeout=1)

        # Use the defaut timeout
        with pytest.raises(RM.RequestTimeoutError):
            RM.send_request(method=("GET", "/api/test/server/sleep"), params={"time": RM._timeout + 1})

        RM.close()
    else:

        async def testing():
            RM = instantiate_re_api_class(rm_api_class)

            # No timeout
            status = await RM.send_request(method=("GET", "/api/test/server/sleep"), params={"time": 3})
            assert status["success"] is True

            # Set timeout for the given request
            with pytest.raises(RM.RequestTimeoutError):
                await RM.send_request(method=("GET", "/api/test/server/sleep"), params={"time": 3}, timeout=1)

            # Use the defaut timeout
            with pytest.raises(RM.RequestTimeoutError):
                await RM.send_request(method=("GET", "/api/test/server/sleep"), params={"time": RM._timeout + 1})

            await RM.close()

        asyncio.run(testing())


# Configuration file for 'toy' authentication provider. The passwords are explicitly listed.
config_toy_yml = """
authentication:
  providers:
    - provider: toy
      authenticator: bluesky_httpserver.authenticators:DictionaryAuthenticator
      args:
        users_to_passwords:
          bob: bob_password
          alice: alice_password
          tom: tom_password
          cara: cara_password
api_access:
  policy: bluesky_httpserver.authorization:DictionaryAPIAccessControl
  args:
    users:
      bob:
        roles:
          - admin
          - expert
      alice:
        roles: advanced
      tom:
        roles: user
"""


# Configuration file for 'toy' authentication provider. The passwords are explicitly listed.
config_toy_yml_short_token_expiration = """
authentication:
  providers:
    - provider: toy
      authenticator: bluesky_httpserver.authenticators:DictionaryAuthenticator
      args:
        users_to_passwords:
          bob: bob_password
          alice: alice_password
          tom: tom_password
          cara: cara_password
  access_token_max_age: 2
  refresh_token_max_age: 600
  session_max_age: 1000
api_access:
  policy: bluesky_httpserver.authorization:DictionaryAPIAccessControl
  args:
    users:
      bob:
        roles:
          - admin
          - expert
      alice:
        roles: advanced
      tom:
        roles: user
"""


# fmt: off
@pytest.mark.parametrize("default_provider", [True, False])
@pytest.mark.parametrize("use_kwargs", [True, False])
@pytest.mark.parametrize("library", ["THREADS", "ASYNC"])
@pytest.mark.parametrize("protocol", ["HTTP"])
# fmt: on
def test_login_1(
    tmpdir,
    monkeypatch,
    re_manager_cmd,  # noqa: F811
    fastapi_server_fs,  # noqa: F811
    protocol,
    library,
    default_provider,
    use_kwargs,
):
    """
    ``login`` API (for HTTP requests). Basic functionality.
    """
    re_manager_cmd()
    setup_server_with_config_file(config_file_str=config_toy_yml, tmpdir=tmpdir, monkeypatch=monkeypatch)
    fastapi_server_fs()
    rm_api_class = _select_re_manager_api(protocol, library)

    if not _is_async(library):
        params = {"http_auth_provider": "/toy/token"} if default_provider else {}
        RM = instantiate_re_api_class(rm_api_class, **params)

        # Make sure access does not work without authentication
        with pytest.raises(RM.HTTPClientError, match="401"):
            RM.status()

        login_args, login_kwargs = [], {"password": "bob_password"}
        if not default_provider:
            login_kwargs.update({"provider": "/toy/token"})
        if use_kwargs:
            login_kwargs.update({"username": "bob"})
        else:
            login_args.extend(["bob"])

        token_info = RM.login(*login_args, **login_kwargs)
        auth_key = RM.auth_key
        assert isinstance(auth_key, tuple), auth_key
        assert auth_key[0] == token_info["access_token"]
        assert auth_key[1] == token_info["refresh_token"]

        # Now make sure that access works
        RM.status()

        RM.close()
    else:

        async def testing():
            params = {"http_auth_provider": "/toy/token"} if default_provider else {}
            RM = instantiate_re_api_class(rm_api_class, **params)

            # Make sure access does not work without authentication
            with pytest.raises(RM.HTTPClientError, match="401"):
                await RM.status()

            login_args, login_kwargs = [], {"password": "bob_password"}
            if not default_provider:
                login_kwargs.update({"provider": "/toy/token"})
            if use_kwargs:
                login_kwargs.update({"username": "bob"})
            else:
                login_args.extend(["bob"])

            token_info = await RM.login(*login_args, **login_kwargs)
            auth_key = RM.auth_key
            assert isinstance(auth_key, tuple), auth_key
            assert auth_key[0] == token_info["access_token"]
            assert auth_key[1] == token_info["refresh_token"]

            # Now make sure that access works
            await RM.status()

            await RM.close()

        asyncio.run(testing())


# fmt: off
@pytest.mark.parametrize("interactive_username", [False, True])
@pytest.mark.parametrize("library", ["THREADS", "ASYNC"])
@pytest.mark.parametrize("protocol", ["HTTP"])
# fmt: on
def test_login_2(
    tmpdir,
    monkeypatch,
    re_manager_cmd,  # noqa: F811
    fastapi_server_fs,  # noqa: F811
    protocol,
    library,
    interactive_username,
):
    """
    ``login`` API (for HTTP requests). Interactive input of username and password.
    """
    re_manager_cmd()
    setup_server_with_config_file(config_file_str=config_toy_yml, tmpdir=tmpdir, monkeypatch=monkeypatch)
    monkeypatch.setattr(getpass, "getpass", lambda: "bob_password")
    fastapi_server_fs()
    rm_api_class = _select_re_manager_api(protocol, library)

    if not _is_async(library):
        RM = instantiate_re_api_class(rm_api_class, http_auth_provider="/toy/token")

        # Make sure access does not work without authentication
        with pytest.raises(RM.HTTPClientError, match="401"):
            RM.status()

        if interactive_username:
            monkeypatch.setattr("sys.stdin", StringIO("bob\n"))
            RM.login()
        else:
            RM.login("bob")

        # Now make sure that access works
        RM.status()

        RM.close()
    else:

        async def testing():
            RM = instantiate_re_api_class(rm_api_class, http_auth_provider="/toy/token")

            # Make sure access does not work without authentication
            with pytest.raises(RM.HTTPClientError, match="401"):
                await RM.status()

            if interactive_username:
                monkeypatch.setattr("sys.stdin", StringIO("bob\n"))
                await RM.login()
            else:
                await RM.login("bob")

            # Now make sure that access works
            await RM.status()

            await RM.close()

        asyncio.run(testing())


# fmt: off
@pytest.mark.parametrize("library", ["THREADS", "ASYNC"])
@pytest.mark.parametrize("protocol", ["HTTP"])
# fmt: on
def test_login_3_fail(
    tmpdir,
    monkeypatch,
    re_manager_cmd,  # noqa: F811
    fastapi_server_fs,  # noqa: F811
    protocol,
    library,
):
    """
    ``login`` API (for HTTP requests). Failing cases due to invalid parameters.
    """
    re_manager_cmd()
    setup_server_with_config_file(config_file_str=config_toy_yml, tmpdir=tmpdir, monkeypatch=monkeypatch)
    fastapi_server_fs()
    rm_api_class = _select_re_manager_api(protocol, library)

    invalid_providers = [
        (10, rm_api_class.RequestParameterError, "must be a string or None"),
        ("", rm_api_class.RequestParameterError, "is an empty string"),
    ]

    invalid_username_password = [
        ("bob", 10, rm_api_class.RequestParameterError, "'password' is not string"),
        ("bob", "", rm_api_class.RequestParameterError, "'password' is an empty string"),
        (10, "bob-password", rm_api_class.RequestParameterError, "'username' is not string"),
        ("", "bob-password", rm_api_class.RequestParameterError, "'username' is an empty string"),
        ("bob", "rand_pwd", rm_api_class.HTTPClientError, "401: Incorrect username or password"),
        ("rand_user", "bob-password", rm_api_class.HTTPClientError, "401: Incorrect username or password"),
        ("rand_user", "rand_pwd", rm_api_class.HTTPClientError, "401: Incorrect username or password"),
    ]

    if not _is_async(library):
        for provider, except_type, msg in invalid_providers:
            with pytest.raises(except_type, match=msg):
                RM = instantiate_re_api_class(rm_api_class, http_auth_provider=provider)

        RM = instantiate_re_api_class(rm_api_class, http_auth_provider="/toy/token")

        # Make sure access does not work without authentication
        with pytest.raises(RM.HTTPClientError, match="401"):
            RM.status()

        # Invalid provider
        for provider, except_type, msg in invalid_providers:
            with pytest.raises(except_type, match=msg):
                RM.login("bob", password="bob_password", provider=provider)

        # Invalid username, password or both
        for username, password, except_type, msg in invalid_username_password:
            with pytest.raises(except_type, match=msg):
                RM.login(username, password=password)

        # Make sure access does not work without authentication
        with pytest.raises(RM.HTTPClientError, match="401"):
            RM.status()

        RM.close()
    else:

        async def testing():
            RM = instantiate_re_api_class(rm_api_class, http_auth_provider="/toy/token")

            for provider, except_type, msg in invalid_providers:
                with pytest.raises(except_type, match=msg):
                    RM = instantiate_re_api_class(rm_api_class, http_auth_provider=provider)

            RM = instantiate_re_api_class(rm_api_class, http_auth_provider="/toy/token")

            # Make sure access does not work without authentication
            with pytest.raises(RM.HTTPClientError, match="401"):
                await RM.status()

            # Invalid provider
            for provider, except_type, msg in invalid_providers:
                with pytest.raises(except_type, match=msg):
                    await RM.login("bob", password="bob_password", provider=provider)

            # Invalid username, password or both
            for username, password, except_type, msg in invalid_username_password:
                with pytest.raises(except_type, match=msg):
                    await RM.login(username, password=password)

            # Make sure access does not work without authentication
            with pytest.raises(RM.HTTPClientError, match="401"):
                await RM.status()

            await RM.close()

        asyncio.run(testing())


# fmt: off
@pytest.mark.parametrize("token_as_param", [False, True])
@pytest.mark.parametrize("library", ["THREADS", "ASYNC"])
@pytest.mark.parametrize("protocol", ["HTTP"])
# fmt: on
def test_session_refresh_1(
    tmpdir,
    monkeypatch,
    re_manager_cmd,  # noqa: F811
    fastapi_server_fs,  # noqa: F811
    protocol,
    library,
    token_as_param,
):
    """
    ``session_refresh`` API (for HTTP requests). Interactive input of username and password.
    """
    re_manager_cmd()
    setup_server_with_config_file(config_file_str=config_toy_yml, tmpdir=tmpdir, monkeypatch=monkeypatch)
    monkeypatch.setattr(getpass, "getpass", lambda: "bob_password")
    fastapi_server_fs()
    rm_api_class = _select_re_manager_api(protocol, library)

    if not _is_async(library):
        RM = instantiate_re_api_class(rm_api_class, http_auth_provider="/toy/token")

        # Make sure access does not work without authentication
        with pytest.raises(RM.HTTPClientError, match="401"):
            RM.status()

        RM.login("bob", password="bob_password")
        RM.status()

        if token_as_param:
            refresh_token = RM.auth_key[1]
            RM.set_authorization_key()  # Clear all tokens
            response = RM.session_refresh(refresh_token=refresh_token)
        else:
            RM.set_authorization_key(refresh_token=RM.auth_key[1])  # Clear the access token
            response = RM.session_refresh()

        assert response["access_token"] == RM.auth_key[0]
        assert response["refresh_token"] == RM.auth_key[1]

        RM.status()

        # Invalid refresh token
        if token_as_param:
            RM.set_authorization_key()  # Clear all tokens
            with pytest.raises(RM.HTTPClientError, match="401"):
                RM.session_refresh(refresh_token="invalidtoken")
        else:
            RM.set_authorization_key(refresh_token="invalidtoken")  # Clear the access token
            with pytest.raises(RM.HTTPClientError, match="401"):
                RM.session_refresh()

        RM.close()
    else:

        async def testing():
            RM = instantiate_re_api_class(rm_api_class, http_auth_provider="/toy/token")

            # Make sure access does not work without authentication
            with pytest.raises(RM.HTTPClientError, match="401"):
                await RM.status()

            await RM.login("bob", password="bob_password")
            await RM.status()

            if token_as_param:
                refresh_token = RM.auth_key[1]
                RM.set_authorization_key()  # Clear all tokens
                response = await RM.session_refresh(refresh_token=refresh_token)
            else:
                RM.set_authorization_key(refresh_token=RM.auth_key[1])  # Clear the access token
                response = await RM.session_refresh()

            assert response["access_token"] == RM.auth_key[0]
            assert response["refresh_token"] == RM.auth_key[1]

            await RM.status()

            # Invalid refresh token
            if token_as_param:
                RM.set_authorization_key()  # Clear all tokens
                with pytest.raises(RM.HTTPClientError, match="401"):
                    await RM.session_refresh(refresh_token="invalidtoken")
            else:
                RM.set_authorization_key(refresh_token="invalidtoken")  # Clear the access token
                with pytest.raises(RM.HTTPClientError, match="401"):
                    await RM.session_refresh()

            await RM.close()

        asyncio.run(testing())


# fmt: off
@pytest.mark.parametrize("token, except_type, msg", [
    (10, RequestParameterError, "'refresh_token' must be a string or None"),
    ("", RequestParameterError, "'refresh_token' is an empty string"),
    (None, RequestParameterError, "'refresh_token' is not set"),
])
@pytest.mark.parametrize("library", ["THREADS", "ASYNC"])
@pytest.mark.parametrize("protocol", ["HTTP"])
# fmt: on
def test_session_refresh_2_fail(protocol, library, token, except_type, msg):
    """
    ``session_refresh`` API (for HTTP requests). Failing cases due to invalid parameters.
    """
    rm_api_class = _select_re_manager_api(protocol, library)

    if not _is_async(library):
        RM = instantiate_re_api_class(rm_api_class, http_auth_provider="/toy/token")

        with pytest.raises(except_type, match=msg):
            RM.session_refresh(refresh_token=token)

        RM.close()
    else:

        async def testing():
            RM = instantiate_re_api_class(rm_api_class, http_auth_provider="/toy/token")

            with pytest.raises(except_type, match=msg):
                await RM.session_refresh(refresh_token=token)

            await RM.close()

        asyncio.run(testing())


# fmt: off
@pytest.mark.parametrize("library", ["THREADS", "ASYNC"])
@pytest.mark.parametrize("protocol", ["HTTP"])
# fmt: on
def test_session_refresh_3(
    tmpdir,
    monkeypatch,
    re_manager_cmd,  # noqa: F811
    fastapi_server_fs,  # noqa: F811
    protocol,
    library,
):
    """
    ``session_refresh`` API (for HTTP requests). Test that the session is automatically refreshed
    as the access token expires. Consider the server with very short session expiration time and
    then repeatedly try to load status from the server.
    """
    re_manager_cmd()
    setup_server_with_config_file(
        config_file_str=config_toy_yml_short_token_expiration, tmpdir=tmpdir, monkeypatch=monkeypatch
    )
    monkeypatch.setattr(getpass, "getpass", lambda: "bob_password")
    fastapi_server_fs()
    rm_api_class = _select_re_manager_api(protocol, library)

    if not _is_async(library):
        RM = instantiate_re_api_class(rm_api_class, http_auth_provider="/toy/token")

        RM.login("bob", password="bob_password")

        n_expirations = 0
        for _ in range(10):
            try:
                RM.send_request(method="status", auto_refresh_session=False)
            except Exception:
                n_expirations += 1

            RM.status()
            ttime.sleep(1)

        assert n_expirations > 0

        RM.close()
    else:

        async def testing():
            RM = instantiate_re_api_class(rm_api_class, http_auth_provider="/toy/token")

            await RM.login("bob", password="bob_password")

            n_expirations = 0
            for _ in range(10):
                try:
                    await RM.send_request(method="status", auto_refresh_session=False)
                except Exception:
                    n_expirations += 1

                await RM.status()
                await asyncio.sleep(1)

            await RM.close()

            assert n_expirations > 0

        asyncio.run(testing())


# fmt: off
@pytest.mark.parametrize("pass_as_param", [None, "token", "api_key"])
@pytest.mark.parametrize("library", ["THREADS", "ASYNC"])
@pytest.mark.parametrize("protocol", ["HTTP"])
# fmt: on
def test_session_revoke_1(
    tmpdir,
    monkeypatch,
    re_manager_cmd,  # noqa: F811
    fastapi_server_fs,  # noqa: F811
    protocol,
    library,
    pass_as_param,
):
    """
    ``session_revoke`` API (for HTTP requests).
    """
    re_manager_cmd()
    setup_server_with_config_file(config_file_str=config_toy_yml, tmpdir=tmpdir, monkeypatch=monkeypatch)
    fastapi_server_fs()
    rm_api_class = _select_re_manager_api(protocol, library)

    if not _is_async(library):
        RM = instantiate_re_api_class(rm_api_class, http_auth_provider="/toy/token")

        # Log into the server
        resp = RM.login("bob", password="bob_password")
        assert "access_token" in resp, pprint.pformat(resp)
        assert "refresh_token" in resp, pprint.pformat(resp)
        token = resp["access_token"]
        refresh_token = resp["refresh_token"]

        resp = RM.apikey_new(expires_in=900)
        assert "secret" in resp, pprint.pformat(resp)
        api_key = resp["secret"]

        # Make sure that 'session_refresh' works
        RM.session_refresh()

        principal_info = RM.whoami()
        assert "sessions" in principal_info, pprint.pformat(principal_info)
        sessions = principal_info["sessions"]
        assert len(sessions) == 1

        if pass_as_param == "token":
            params = {"token": token}
            RM.set_authorization_key()
        elif pass_as_param == "api_key":
            params = {"api_key": api_key}
            RM.set_authorization_key()
        elif pass_as_param is None:
            params = {}
        else:
            assert False, f"Unexpected option: pass_as_param={pass_as_param!r}"

        if params:
            with pytest.raises(RM.HTTPClientError, match="requester has insufficient permissions"):
                RM.session_revoke(session_uid=sessions[0]["uuid"])

        resp = RM.session_revoke(session_uid=sessions[0]["uuid"], **params)
        assert "success" in resp
        assert resp["success"] is True

        # Session is revoked and cannot be refreshed
        RM.set_authorization_key(token=token, refresh_token=refresh_token)
        with pytest.raises(RM.HTTPClientError, match="Session has expired"):
            RM.session_refresh()

        RM.close()
    else:

        async def testing():
            RM = instantiate_re_api_class(rm_api_class, http_auth_provider="/toy/token")

            # Log into the server
            resp = await RM.login("bob", password="bob_password")
            assert "access_token" in resp, pprint.pformat(resp)
            assert "refresh_token" in resp, pprint.pformat(resp)
            token = resp["access_token"]
            refresh_token = resp["refresh_token"]

            resp = await RM.apikey_new(expires_in=900)
            assert "secret" in resp, pprint.pformat(resp)
            api_key = resp["secret"]

            # Make sure that 'session_refresh' works
            await RM.session_refresh()

            principal_info = await RM.whoami()
            assert "sessions" in principal_info, pprint.pformat(principal_info)
            sessions = principal_info["sessions"]
            assert len(sessions) == 1

            if pass_as_param == "token":
                params = {"token": token}
                RM.set_authorization_key()
            elif pass_as_param == "api_key":
                params = {"api_key": api_key}
                RM.set_authorization_key()
            elif pass_as_param is None:
                params = {}
            else:
                assert False, f"Unexpected option: pass_as_param={pass_as_param!r}"

            if params:
                with pytest.raises(RM.HTTPClientError, match="requester has insufficient permissions"):
                    await RM.session_revoke(session_uid=sessions[0]["uuid"])

            resp = await RM.session_revoke(session_uid=sessions[0]["uuid"], **params)
            assert "success" in resp
            assert resp["success"] is True

            # Session is revoked and cannot be refreshed
            RM.set_authorization_key(token=token, refresh_token=refresh_token)
            with pytest.raises(RM.HTTPClientError, match="Session has expired"):
                await RM.session_refresh()

            await RM.close()

        asyncio.run(testing())


# fmt: off
@pytest.mark.parametrize("library", ["THREADS", "ASYNC"])
@pytest.mark.parametrize("protocol", ["HTTP"])
# fmt: on
def test_session_apikey_new_1(
    tmpdir,
    monkeypatch,
    re_manager_cmd,  # noqa: F811
    fastapi_server_fs,  # noqa: F811
    protocol,
    library,
):
    """
    ``apikey_new``, ``apikey_info`` API (for HTTP requests).
    """
    re_manager_cmd()
    setup_server_with_config_file(config_file_str=config_toy_yml, tmpdir=tmpdir, monkeypatch=monkeypatch)
    fastapi_server_fs()
    rm_api_class = _select_re_manager_api(protocol, library)

    if not _is_async(library):
        RM = instantiate_re_api_class(rm_api_class, http_auth_provider="/toy/token")

        # Log into the server
        resp = RM.login("bob", password="bob_password")
        assert "access_token" in resp, pprint.pformat(resp)
        assert "refresh_token" in resp, pprint.pformat(resp)
        token = resp["access_token"]
        refresh_token = resp["refresh_token"]

        resp = RM.apikey_new(expires_in=900)
        assert "secret" in resp, pprint.pformat(resp)
        api_key = resp["secret"]

        # Pass 'api_key' as a parameter (default authorization is by token)
        resp = RM.apikey_info(api_key=api_key)
        assert resp["note"] is None
        assert resp["scopes"] == ["inherit"]

        # Try using the default authorization (by token)
        with pytest.raises(RM.HTTPClientError, match="No API key was provided with this request"):
            RM.apikey_info()

        # Change the default authorization key and try again (now authorization is by API key)
        RM.set_authorization_key(api_key=api_key)
        resp = RM.apikey_info()
        assert resp["note"] is None
        assert resp["scopes"] == ["inherit"]

        # Restore authorization
        RM.set_authorization_key(token=token, refresh_token=refresh_token)

        # Create another key. Specify scopes and a note.
        resp = RM.apikey_new(expires_in=900, scopes=["read:status", "read:queue"], note="Some message!!!")
        assert "secret" in resp, pprint.pformat(resp)
        api_key2 = resp["secret"]

        # Verify if the scopes and the note were set correctly.
        resp = RM.apikey_info(api_key=api_key2)
        assert resp["note"] == "Some message!!!"
        assert resp["scopes"] == ["read:status", "read:queue"]

        RM.close()
    else:

        async def testing():
            RM = instantiate_re_api_class(rm_api_class, http_auth_provider="/toy/token")

            # Log into the server
            resp = await RM.login("bob", password="bob_password")
            assert "access_token" in resp, pprint.pformat(resp)
            assert "refresh_token" in resp, pprint.pformat(resp)
            token = resp["access_token"]
            refresh_token = resp["refresh_token"]

            resp = await RM.apikey_new(expires_in=900)
            assert "secret" in resp, pprint.pformat(resp)
            api_key = resp["secret"]

            # Pass 'api_key' as a parameter (default authorization is by token)
            resp = await RM.apikey_info(api_key=api_key)
            assert resp["note"] is None
            assert resp["scopes"] == ["inherit"]

            # Try using the default authorization (by token)
            with pytest.raises(RM.HTTPClientError, match="No API key was provided with this request"):
                await RM.apikey_info()

            # Change the default authorization key and try again (now authorization is by API key)
            RM.set_authorization_key(api_key=api_key)
            resp = await RM.apikey_info()
            assert resp["note"] is None
            assert resp["scopes"] == ["inherit"]

            # Restore authorization
            RM.set_authorization_key(token=token, refresh_token=refresh_token)

            # Create another key. Specify scopes and a note.
            resp = await RM.apikey_new(
                expires_in=900, scopes=["read:status", "read:queue"], note="Some message!!!"
            )
            assert "secret" in resp, pprint.pformat(resp)
            api_key2 = resp["secret"]

            # Verify if the scopes and the note were set correctly.
            resp = await RM.apikey_info(api_key=api_key2)
            assert resp["note"] == "Some message!!!"
            assert resp["scopes"] == ["read:status", "read:queue"]

            await RM.close()

        asyncio.run(testing())


# fmt: off
@pytest.mark.parametrize("library", ["THREADS", "ASYNC"])
@pytest.mark.parametrize("protocol", ["HTTP"])
# fmt: on
def test_session_apikey_new_2(
    tmpdir,
    monkeypatch,
    re_manager_cmd,  # noqa: F811
    fastapi_server_fs,  # noqa: F811
    protocol,
    library,
):
    """
    ``apikey_new``, ``apikey_info`` API (for HTTP requests). Creating API key for a different user.
    """
    re_manager_cmd()
    setup_server_with_config_file(config_file_str=config_toy_yml, tmpdir=tmpdir, monkeypatch=monkeypatch)
    fastapi_server_fs()
    rm_api_class = _select_re_manager_api(protocol, library)

    if not _is_async(library):
        RM = instantiate_re_api_class(rm_api_class, http_auth_provider="/toy/token")

        # Log into the server
        resp = RM.login("bob", password="bob_password")
        assert "access_token" in resp, pprint.pformat(resp)
        assert "refresh_token" in resp, pprint.pformat(resp)
        token = resp["access_token"]
        refresh_token = resp["refresh_token"]

        # Log in as 'tom' to create a session. Save principal UID.
        resp = RM.login("tom", password="tom_password")
        principal_info = RM.whoami()
        assert "uuid" in principal_info, pprint.pformat(principal_info)
        principal_uid = principal_info["uuid"]

        # Restore authorization for 'bob'
        RM.set_authorization_key(token=token, refresh_token=refresh_token)

        # 'bob' (an administrator) generates an API for 'tom'
        resp = RM.apikey_new(expires_in=900, principal_uid=principal_uid)
        assert "secret" in resp, pprint.pformat(resp)
        api_key = resp["secret"]

        # Check that API key exists
        resp = RM.apikey_info(api_key=api_key)
        assert resp["note"] is None
        assert resp["scopes"] == ["inherit"]

        # Check that the API key is actually for 'tom'
        resp = RM.whoami(api_key=api_key)
        assert resp["uuid"] == principal_uid

        # Make sure that 'bob' has admin privileges ...
        resp = RM.api_scopes()
        assert "admin:apikeys" in resp["scopes"]
        # ... by the API key generated for 'tom' doesn't.
        resp = RM.api_scopes(api_key=api_key)
        assert "admin:apikeys" not in resp["scopes"]

        RM.close()
    else:

        async def testing():
            RM = instantiate_re_api_class(rm_api_class, http_auth_provider="/toy/token")

            # Log into the server
            resp = await RM.login("bob", password="bob_password")
            assert "access_token" in resp, pprint.pformat(resp)
            assert "refresh_token" in resp, pprint.pformat(resp)
            token = resp["access_token"]
            refresh_token = resp["refresh_token"]

            # Log in as 'tom' to create a session. Save principal UID.
            resp = await RM.login("tom", password="tom_password")
            principal_info = await RM.whoami()
            assert "uuid" in principal_info, pprint.pformat(principal_info)
            principal_uid = principal_info["uuid"]

            # Restore authorization for 'bob'
            RM.set_authorization_key(token=token, refresh_token=refresh_token)

            # 'bob' (an administrator) generates an API for 'tom'
            resp = await RM.apikey_new(expires_in=900, principal_uid=principal_uid)
            assert "secret" in resp, pprint.pformat(resp)
            api_key = resp["secret"]

            # Check that API key exists
            resp = await RM.apikey_info(api_key=api_key)
            assert resp["note"] is None
            assert resp["scopes"] == ["inherit"]

            # Check that the API key is actually for 'tom'
            resp = await RM.whoami(api_key=api_key)
            assert resp["uuid"] == principal_uid

            # Make sure that 'bob' has admin privileges ...
            resp = await RM.api_scopes()
            assert "admin:apikeys" in resp["scopes"]
            # ... by the API key generated for 'tom' doesn't.
            resp = await RM.api_scopes(api_key=api_key)
            assert "admin:apikeys" not in resp["scopes"]

            await RM.close()

        asyncio.run(testing())


# fmt: off
@pytest.mark.parametrize("pass_as_param", [None, "token", "api_key"])
@pytest.mark.parametrize("library", ["THREADS", "ASYNC"])
@pytest.mark.parametrize("protocol", ["HTTP"])
# fmt: on
def test_session_apikey_delete_1(
    tmpdir,
    monkeypatch,
    re_manager_cmd,  # noqa: F811
    fastapi_server_fs,  # noqa: F811
    protocol,
    library,
    pass_as_param,
):
    """
    ``apikey_delete`` API (for HTTP requests).
    """
    re_manager_cmd()
    setup_server_with_config_file(config_file_str=config_toy_yml, tmpdir=tmpdir, monkeypatch=monkeypatch)
    fastapi_server_fs()
    rm_api_class = _select_re_manager_api(protocol, library)

    if not _is_async(library):
        RM = instantiate_re_api_class(rm_api_class, http_auth_provider="/toy/token")

        # Log into the server
        resp = RM.login("bob", password="bob_password")
        assert "access_token" in resp, pprint.pformat(resp)
        assert "refresh_token" in resp, pprint.pformat(resp)
        token = resp["access_token"]

        resp = RM.apikey_new(expires_in=900)
        assert "secret" in resp, pprint.pformat(resp)
        api_key = resp["secret"]

        if pass_as_param == "token":
            params = {"token": token}
            RM.set_authorization_key()
        elif pass_as_param == "api_key":
            params = {"api_key": api_key}
            RM.set_authorization_key()
        elif pass_as_param is None:
            params = {}
        else:
            assert False, f"Unexpected option: pass_as_param={pass_as_param!r}"

        resp = RM.apikey_delete(first_eight=api_key[:8], **params)
        assert resp == {"success": True, "msg": ""}

        # Check that the API does not exist
        with pytest.raises(RM.HTTPClientError, match="Invalid API key"):
            RM.apikey_info(api_key=api_key)

        RM.close()
    else:

        async def testing():
            RM = instantiate_re_api_class(rm_api_class, http_auth_provider="/toy/token")

            # Log into the server
            resp = await RM.login("bob", password="bob_password")
            assert "access_token" in resp, pprint.pformat(resp)
            assert "refresh_token" in resp, pprint.pformat(resp)
            token = resp["access_token"]

            resp = await RM.apikey_new(expires_in=900)
            assert "secret" in resp, pprint.pformat(resp)
            api_key = resp["secret"]

            if pass_as_param == "token":
                params = {"token": token}
                RM.set_authorization_key()
            elif pass_as_param == "api_key":
                params = {"api_key": api_key}
                RM.set_authorization_key()
            elif pass_as_param is None:
                params = {}
            else:
                assert False, f"Unexpected option: pass_as_param={pass_as_param!r}"

            resp = await RM.apikey_delete(first_eight=api_key[:8], **params)
            assert resp == {"success": True, "msg": ""}

            # Check that the API does not exist
            with pytest.raises(RM.HTTPClientError, match="Invalid API key"):
                await RM.apikey_info(api_key=api_key)

            await RM.close()

        asyncio.run(testing())


# fmt: off
@pytest.mark.parametrize("pass_as_param", [None, "token", "api_key"])
@pytest.mark.parametrize("library", ["THREADS", "ASYNC"])
@pytest.mark.parametrize("protocol", ["HTTP"])
# fmt: on
def test_session_whoami_1(
    tmpdir,
    monkeypatch,
    re_manager_cmd,  # noqa: F811
    fastapi_server_fs,  # noqa: F811
    protocol,
    library,
    pass_as_param,
):
    """
    ``whoami``, ``api_scopes`` API (for HTTP requests).
    """
    re_manager_cmd()
    setup_server_with_config_file(config_file_str=config_toy_yml, tmpdir=tmpdir, monkeypatch=monkeypatch)
    fastapi_server_fs()
    rm_api_class = _select_re_manager_api(protocol, library)

    if not _is_async(library):
        RM = instantiate_re_api_class(rm_api_class, http_auth_provider="/toy/token")

        # Log into the server
        resp = RM.login("bob", password="bob_password")
        assert "access_token" in resp, pprint.pformat(resp)
        assert "refresh_token" in resp, pprint.pformat(resp)
        token = resp["access_token"]

        resp = RM.apikey_new(expires_in=900)
        assert "secret" in resp, pprint.pformat(resp)
        api_key = resp["secret"]

        if pass_as_param == "token":
            params = {"token": token}
            RM.set_authorization_key()
        elif pass_as_param == "api_key":
            params = {"api_key": api_key}
            RM.set_authorization_key()
        elif pass_as_param is None:
            params = {}
        else:
            assert False, f"Unexpected option: pass_as_param={pass_as_param!r}"

        resp = RM.whoami(**params)
        assert len(resp["identities"]) == 1
        assert resp["identities"][0]["id"] == "bob"

        resp = RM.api_scopes(**params)
        assert "roles" in resp, pprint.pformat(resp)
        assert "scopes" in resp, pprint.pformat(resp)
        assert "admin" in resp["roles"]
        assert "admin:apikeys" in resp["scopes"]

        RM.close()
    else:

        async def testing():
            RM = instantiate_re_api_class(rm_api_class, http_auth_provider="/toy/token")

            # Log into the server
            resp = await RM.login("bob", password="bob_password")
            assert "access_token" in resp, pprint.pformat(resp)
            assert "refresh_token" in resp, pprint.pformat(resp)
            token = resp["access_token"]

            resp = await RM.apikey_new(expires_in=900)
            assert "secret" in resp, pprint.pformat(resp)
            api_key = resp["secret"]

            if pass_as_param == "token":
                params = {"token": token}
                RM.set_authorization_key()
            elif pass_as_param == "api_key":
                params = {"api_key": api_key}
                RM.set_authorization_key()
            elif pass_as_param is None:
                params = {}
            else:
                assert False, f"Unexpected option: pass_as_param={pass_as_param!r}"

            resp = await RM.whoami(**params)
            assert len(resp["identities"]) == 1
            assert resp["identities"][0]["id"] == "bob"

            resp = await RM.api_scopes(**params)
            assert "roles" in resp, pprint.pformat(resp)
            assert "scopes" in resp, pprint.pformat(resp)
            assert "admin" in resp["roles"]
            assert "admin:apikeys" in resp["scopes"]

            await RM.close()

        asyncio.run(testing())


# fmt: off
@pytest.mark.parametrize("library", ["THREADS", "ASYNC"])
@pytest.mark.parametrize("protocol", ["HTTP"])
# fmt: on
def test_session_logout_1(
    tmpdir,
    monkeypatch,
    re_manager_cmd,  # noqa: F811
    fastapi_server_fs,  # noqa: F811
    protocol,
    library,
):
    """
    ``logout`` API (for HTTP requests).
    """
    re_manager_cmd()
    setup_server_with_config_file(config_file_str=config_toy_yml, tmpdir=tmpdir, monkeypatch=monkeypatch)
    fastapi_server_fs()
    rm_api_class = _select_re_manager_api(protocol, library)

    if not _is_async(library):
        RM = instantiate_re_api_class(rm_api_class, http_auth_provider="/toy/token")

        # Log into the server
        resp = RM.login("bob", password="bob_password")
        assert "access_token" in resp, pprint.pformat(resp)
        assert "refresh_token" in resp, pprint.pformat(resp)

        assert RM.auth_key == (resp["access_token"], resp["refresh_token"])
        assert RM.auth_method == RM.AuthorizationMethods.TOKEN

        RM.logout()

        assert RM.auth_key is None
        assert RM.auth_method == RM.AuthorizationMethods.NONE

        RM.close()
    else:

        async def testing():
            RM = instantiate_re_api_class(rm_api_class, http_auth_provider="/toy/token")

            # Log into the server
            resp = await RM.login("bob", password="bob_password")
            assert "access_token" in resp, pprint.pformat(resp)
            assert "refresh_token" in resp, pprint.pformat(resp)

            assert RM.auth_key == (resp["access_token"], resp["refresh_token"])
            assert RM.auth_method == RM.AuthorizationMethods.TOKEN

            await RM.logout()

            assert RM.auth_key is None
            assert RM.auth_method == RM.AuthorizationMethods.NONE

            await RM.close()

        asyncio.run(testing())


# fmt: off
@pytest.mark.parametrize("library", ["THREADS", "ASYNC"])
@pytest.mark.parametrize("protocol", ["HTTP"])
# fmt: on
def test_principal_info_1(
    tmpdir,
    monkeypatch,
    re_manager_cmd,  # noqa: F811
    fastapi_server_fs,  # noqa: F811
    protocol,
    library,
):
    """
    ``principal_info`` API (for HTTP requests).
    """
    re_manager_cmd()
    setup_server_with_config_file(config_file_str=config_toy_yml, tmpdir=tmpdir, monkeypatch=monkeypatch)
    fastapi_server_fs()
    rm_api_class = _select_re_manager_api(protocol, library)

    if not _is_async(library):
        RM = instantiate_re_api_class(rm_api_class, http_auth_provider="/toy/token")

        # Log into the server: 'bob' is admin
        resp = RM.login("bob", password="bob_password")
        assert "access_token" in resp, pprint.pformat(resp)
        assert "refresh_token" in resp, pprint.pformat(resp)

        whoami_info = RM.whoami()
        assert "uuid" in whoami_info
        assert "identities" in whoami_info
        assert "sessions" in whoami_info

        principal_uid = whoami_info["uuid"]

        principal_info_all = RM.principal_info()
        assert isinstance(principal_info_all, list), pprint.pformat(principal_info_all)
        assert len(principal_info_all) == 1
        assert principal_info_all[0] == whoami_info

        principal_info = RM.principal_info(principal_uid=principal_uid)
        assert principal_info == whoami_info

        RM.close()
    else:

        async def testing():
            RM = instantiate_re_api_class(rm_api_class, http_auth_provider="/toy/token")

            # Log into the server: 'bob' is admin
            resp = await RM.login("bob", password="bob_password")
            assert "access_token" in resp, pprint.pformat(resp)
            assert "refresh_token" in resp, pprint.pformat(resp)

            whoami_info = await RM.whoami()
            assert "uuid" in whoami_info
            assert "identities" in whoami_info
            assert "sessions" in whoami_info

            principal_uid = whoami_info["uuid"]

            principal_info_all = await RM.principal_info()
            assert isinstance(principal_info_all, list), pprint.pformat(principal_info_all)
            assert len(principal_info_all) == 1
            assert principal_info_all[0] == whoami_info

            principal_info = await RM.principal_info(principal_uid=principal_uid)
            assert principal_info == whoami_info

            await RM.close()

        asyncio.run(testing())
