from ..comm_asyncio import ReManagerComm_HTTP_Asyncio
from ..api_asyncio import API_Asyncio_Mixin

from .._defaults import (
    default_allow_request_timeout_exceptions,
    default_allow_request_fail_exceptions,
    default_http_request_timeout,
    default_http_server_uri,
)


class REManagerAPI(ReManagerComm_HTTP_Asyncio, API_Asyncio_Mixin):
    def __init__(
        self,
        *,
        http_server_uri=default_http_server_uri,
        timeout=default_http_request_timeout,
        timeout_exceptions=default_allow_request_timeout_exceptions,
        request_fail_exceptions=default_allow_request_fail_exceptions,
        loop=None,
    ):
        ReManagerComm_HTTP_Asyncio.__init__(
            self,
            http_server_uri=http_server_uri,
            timeout=timeout,
            timeout_exceptions=timeout_exceptions,
            request_fail_exceptions=request_fail_exceptions,
            loop=loop,
        )
        API_Asyncio_Mixin.__init__(self)
