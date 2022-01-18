from ..api_threads import API_Threads_Mixin
from ..comm_threads import ReManagerComm_HTTP_Threads


from .._defaults import (
    default_allow_request_timeout_exceptions,
    default_allow_request_fail_exceptions,
    default_http_request_timeout,
    default_http_server_uri,
)


class REManagerAPI(ReManagerComm_HTTP_Threads, API_Threads_Mixin):
    def __init__(
        self,
        *,
        http_server_uri=default_http_server_uri,
        timeout=default_http_request_timeout,
        timeout_exceptions=default_allow_request_timeout_exceptions,
        request_fail_exceptions=default_allow_request_fail_exceptions,
    ):
        ReManagerComm_HTTP_Threads.__init__(
            self,
            http_server_uri=http_server_uri,
            timeout=timeout,
            timeout_exceptions=timeout_exceptions,
            request_fail_exceptions=request_fail_exceptions,
        )
        API_Threads_Mixin.__init__(self)
