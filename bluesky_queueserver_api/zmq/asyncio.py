from ..comm_asyncio import ReManagerComm_ZMQ_Asyncio
from ..api_asyncio import API_Asyncio_Mixin


class REManagerAPI(ReManagerComm_ZMQ_Asyncio, API_Asyncio_Mixin):
    def __init__(
        self,
        *,
        zmq_server_address=None,
        timeout_recv=2000,
        timeout_send=500,
        server_public_key=None,
        timeout_exceptions=True,
        request_fail_exceptions=True,
    ):
        ReManagerComm_ZMQ_Asyncio.__init__(
            self,
            zmq_server_address=zmq_server_address,
            timeout_recv=timeout_recv,
            timeout_send=timeout_send,
            server_public_key=server_public_key,
            timeout_exceptions=timeout_exceptions,
            request_fail_exceptions=request_fail_exceptions,
        )
        API_Asyncio_Mixin.__init__(self)
