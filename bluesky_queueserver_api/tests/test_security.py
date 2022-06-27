import asyncio
import pytest

from .common import _is_async, _select_re_manager_api

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
    ("some_api_key", None, "some_refresh_token", "NONE", None, False, "API key and a token are mutually exclusive"),
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
            with pytest.raises((TypeError, ValueError), match=msg):
                RM.set_authorization_key(api_key=api_key, token=token, refresh_token=refresh_token)

        assert RM.auth_method == RM.AuthorizationMethods(res_auth_method)
        assert RM.auth_key == res_auth_key

        # Check that all default values are set to 'None' and calling the function with default parameters
        #   disables authorization
        RM.set_authorization_key()
        assert RM.auth_method == RM.AuthorizationMethods.NONE
        assert RM.auth_key == None

        RM.close()

    else:

        async def testing():
            RM = rm_api_class()
            if success:
                RM.set_authorization_key(api_key=api_key, token=token, refresh_token=refresh_token)
            else:
                with pytest.raises((TypeError, ValueError), match=msg):
                    RM.set_authorization_key(api_key=api_key, token=token, refresh_token=refresh_token)


            assert RM.auth_method == RM.AuthorizationMethods(res_auth_method)
            assert RM.auth_key == res_auth_key

            # Check that all default values are set to 'None' and calling the function with default parameters
            #   disables authorization
            RM.set_authorization_key()
            assert RM.auth_method == RM.AuthorizationMethods.NONE
            assert RM.auth_key == None

            await RM.close()

        asyncio.run(testing())
