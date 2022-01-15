from ..rm_comm_asyncio import ReManagerComm_Asyncio_HTTP
from ..rm_api_asyncio import API_Asyncio_Mixin


class REManagerAPI(ReManagerComm_Asyncio_HTTP, API_Asyncio_Mixin):
    def __init__(
        self,
        *,
        http_server_uri=None,
        timeout=5000,
        timeout_exceptions=True,
        request_fail_exceptions=True,
    ):
        ReManagerComm_Asyncio_HTTP.__init__(
            self,
            http_server_uri=http_server_uri,
            timeout=timeout,
            timeout_exceptions=timeout_exceptions,
            request_fail_exceptions=request_fail_exceptions,
        )
        API_Asyncio_Mixin.__init__(self)
