from ..api_async import API_Async_Mixin
from ..comm_async import ReManagerComm_HTTP_Async

from .._defaults import (
    default_allow_request_fail_exceptions,
    default_http_request_timeout,
    default_status_expiration_period,
    default_status_polling_period,
)

from ..api_docstrings import _doc_REManagerAPI_HTTP


class REManagerAPI(ReManagerComm_HTTP_Async, API_Async_Mixin):
    def __init__(
        self,
        *,
        http_server_uri=None,
        timeout=default_http_request_timeout,
        request_fail_exceptions=default_allow_request_fail_exceptions,
        status_expiration_period=default_status_expiration_period,
        status_polling_period=default_status_polling_period,
        loop=None,  # Ignored, used here for compatibility with 0MQ asyncio API
    ):
        ReManagerComm_HTTP_Async.__init__(
            self,
            http_server_uri=http_server_uri,
            timeout=timeout,
            request_fail_exceptions=request_fail_exceptions,
        )
        API_Async_Mixin.__init__(
            self,
            status_expiration_period=status_expiration_period,
            status_polling_period=status_polling_period,
        )


REManagerAPI.__doc__ = _doc_REManagerAPI_HTTP
