from ..rm_comm import ReManagerComm_Threads_HTTP
from ..rm_api import API_Threads_Mixin


class REManagerAPI(ReManagerComm_Threads_HTTP, API_Threads_Mixin):
    def __init__(
        self,
        *,
        http_server_uri=None,
        timeout=5000,
        timeout_exceptions=True,
        request_fail_exceptions=True,
    ):
        ReManagerComm_Threads_HTTP.__init__(
            self,
            http_server_uri=http_server_uri,
            timeout=timeout,
            timeout_exceptions=timeout_exceptions,
            request_fail_exceptions=request_fail_exceptions,
        )
        API_Threads_Mixin.__init__(self)
