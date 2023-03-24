import asyncio
import pprint
import time as ttime

import pytest

from .common import fastapi_server_fs  # noqa: F401
from .common import _is_async, _select_re_manager_api, re_manager, re_manager_cmd  # noqa: F401


# fmt: off
@pytest.mark.parametrize("api_key, token, refresh_token, res_auth_method, res_auth_key, success, msg", [
    (None, None, None, "NONE", None, True, ""),
    ("some_api_key", None, None, "API_KEY", "some_api_key", True, ""),
    (None, "some_token", None, "TOKEN", ("some_token", None), True, ""),
    (None, None, "some_refresh_token", "TOKEN", (None, "some_refresh_token"), True, ""),
    (None, "some_token", "some_refresh_token", "TOKEN", ("some_token", "some_refresh_token"), True, ""),
    (10, None, None, "NONE", None, False, "API key must be a string or None"),
    (None, 10, None, "NONE", None, False, "Token must be a string or None"),
    (None, None, 10, "NONE", None, False, "Refresh token must be a string or None"),
    ("some_api_key", "some_token", None, "NONE", None, False, "API key and a token are mutually exclusive"),
    ("some_api_key", None, "some_refresh_token", "NONE", None, False,
     "API key and a token are mutually exclusive"),
])
@pytest.mark.parametrize("library", ["THREADS", "ASYNC"])
@pytest.mark.parametrize("protocol", ["HTTP"])
# fmt: on
def test_set_authorization_key_01(
    protocol, library, api_key, token, refresh_token, res_auth_method, res_auth_key, success, msg
):  # noqa: F811
    """
    ``set_authorization_key`` API, ``auth_method``, ``auth_key`` properties.
    """

    rm_api_class = _select_re_manager_api(protocol, library)

    if not _is_async(library):
        RM = rm_api_class()

        if success:
            RM.set_authorization_key(api_key=api_key, token=token, refresh_token=refresh_token)
        else:
            with pytest.raises(RM.RequestParameterError, match=msg):
                RM.set_authorization_key(api_key=api_key, token=token, refresh_token=refresh_token)

        assert RM.auth_method == RM.AuthorizationMethods(res_auth_method)
        assert RM.auth_key == res_auth_key

        # Check that all default values are set to 'None' and calling the function with default parameters
        #   disables authorization
        RM.set_authorization_key()
        assert RM.auth_method == RM.AuthorizationMethods.NONE
        assert RM.auth_key is None

        RM.close()

    else:

        async def testing():
            RM = rm_api_class()
            if success:
                RM.set_authorization_key(api_key=api_key, token=token, refresh_token=refresh_token)
            else:
                with pytest.raises(RM.RequestParameterError, match=msg):
                    RM.set_authorization_key(api_key=api_key, token=token, refresh_token=refresh_token)

            assert RM.auth_method == RM.AuthorizationMethods(res_auth_method)
            assert RM.auth_key == res_auth_key

            # Check that all default values are set to 'None' and calling the function with default parameters
            #   disables authorization
            RM.set_authorization_key()
            assert RM.auth_method == RM.AuthorizationMethods.NONE
            assert RM.auth_key is None

            await RM.close()

        asyncio.run(testing())


valid_api_key_test_1 = "validapikey"


# fmt: off
@pytest.mark.parametrize("api_key, success, msg", [
    (valid_api_key_test_1, True, ""),
    ("invalidkey", False, "401: Invalid API key"),
    (None, False, "401: Not enough permissions."),
])
@pytest.mark.parametrize("library", ["THREADS", "ASYNC"])
@pytest.mark.parametrize("protocol", ["HTTP"])
# fmt: on
def test_ReManagerAPI_authorization_api_key_01(
    monkeypatch, re_manager, fastapi_server_fs, protocol, library, api_key, success, msg  # noqa: F811
):
    """
    Test if authorization failure exceptions are properly processed during typical API calls.
    """
    if protocol != "HTTP":
        raise RuntimeError("Protocol {protocol!r} is not supported in this test.")

    # monkeypatch.setenv("QSERVER_HTTP_SERVER_SINGLE_USER_API_KEY", test_valid_api_key_1)
    fastapi_server_fs(api_key=valid_api_key_test_1)

    rm_api_class = _select_re_manager_api(protocol, library)

    if not _is_async(library):
        RM = rm_api_class()
        RM.set_authorization_key(api_key=api_key, token=None, refresh_token=None)

        if success:
            RM.wait_for_idle(timeout=3)  # Wait returns immediately
            status = RM.status()
            assert status["msg"].startswith("RE Manager"), pprint.pformat(status)
        else:
            # Wait functions do not check for communication errors and are expected to timeout.
            t0 = ttime.time()
            with pytest.raises(RM.WaitTimeoutError):
                RM.wait_for_idle(timeout=3)
            assert ttime.time() - t0 > 2

            with pytest.raises(RM.HTTPClientError, match="401"):
                RM.status()

        # Now repeat the test with valid API key
        RM.set_authorization_key(api_key=valid_api_key_test_1, token=None, refresh_token=None)
        RM.wait_for_idle(timeout=3)  # Wait returns immediately
        status = RM.status()
        assert status["msg"].startswith("RE Manager"), pprint.pformat(status)

        RM.close()

    else:

        async def testing():
            RM = rm_api_class()
            RM.set_authorization_key(api_key=api_key, token=None, refresh_token=None)

            if success:
                await RM.wait_for_idle(timeout=3)  # Wait returns immediately
                status = await RM.status()
                assert status["msg"].startswith("RE Manager"), pprint.pformat(status)
            else:
                # Wait functions do not check for communication errors and are expected to timeout.
                t0 = ttime.time()
                with pytest.raises(RM.WaitTimeoutError):
                    await RM.wait_for_idle(timeout=3)
                assert ttime.time() - t0 > 2

                with pytest.raises(RM.HTTPClientError, match="401"):
                    await RM.status()

            # Now repeat the test with valid API key
            RM.set_authorization_key(api_key=valid_api_key_test_1, token=None, refresh_token=None)
            await RM.wait_for_idle(timeout=3)  # Wait returns immediately
            status = await RM.status()
            assert status["msg"].startswith("RE Manager"), pprint.pformat(status)

            await RM.close()

        asyncio.run(testing())
