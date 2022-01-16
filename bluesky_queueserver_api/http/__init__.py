from ..comm_threads import ReManagerComm_HTTP_Threads
from ..api_threads import API_Threads_Mixin


class REManagerAPI(ReManagerComm_HTTP_Threads, API_Threads_Mixin):
    def __init__(
        self,
        *,
        http_server_uri=None,
        timeout=5000,
        timeout_exceptions=True,
        request_fail_exceptions=True,
    ):
        ReManagerComm_HTTP_Threads.__init__(
            self,
            http_server_uri=http_server_uri,
            timeout=timeout,
            timeout_exceptions=timeout_exceptions,
            request_fail_exceptions=request_fail_exceptions,
        )
        API_Threads_Mixin.__init__(self)
