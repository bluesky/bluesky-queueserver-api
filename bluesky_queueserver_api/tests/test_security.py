import asyncio
import pytest

from .common import _is_async, _select_re_manager_api

# fmt: off
@pytest.mark.parametrize("method, key, success, msg", [
    ("NONE", "", True, ""),
    ("NONE", "abc", True, ""),
    ("API_KEY", "abc", True, ""),
    ("TOKEN", "abc", True, ""),
])
@pytest.mark.parametrize("library", ["THREADS", "ASYNC"])
@pytest.mark.parametrize("protocol", ["HTTP"])
# fmt: on
def test_set_authorization_key_01(protocol, library, method, key, success, msg):  # noqa: F811

    rm_api_class = _select_re_manager_api(protocol, library)

    if not _is_async(library):
        RM = rm_api_class()
        RM.set_authorization_key(method, key)

        assert RM._auth_method == RM.AuthorizationMethods(method)
        assert RM._auth_key == (key if method != "NONE" else "")

        RM.close()

    else:

        async def testing():
            RM = rm_api_class()
            RM.set_authorization_key(method, key)

            assert RM._auth_method == RM.AuthorizationMethods(method)
            assert RM._auth_key == (key if method != "NONE" else "")

            await RM.close()

        asyncio.run(testing())
