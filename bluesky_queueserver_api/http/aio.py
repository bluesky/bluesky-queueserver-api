from ..api_async import API_Async_Mixin
from ..comm_async import ReManagerComm_HTTP_Async


from .._defaults import (
    default_allow_request_fail_exceptions,
    default_http_request_timeout,
    default_http_server_uri,
)


class REManagerAPI(ReManagerComm_HTTP_Async, API_Async_Mixin):
    def __init__(
        self,
        *,
        http_server_uri=default_http_server_uri,
        timeout=default_http_request_timeout,
        request_fail_exceptions=default_allow_request_fail_exceptions,
        loop=None,  # Ignored, used here for compatibility with 0MQ asyncio API
    ):
        ReManagerComm_HTTP_Async.__init__(
            self,
            http_server_uri=http_server_uri,
            timeout=timeout,
            request_fail_exceptions=request_fail_exceptions,
        )
        API_Async_Mixin.__init__(self)
