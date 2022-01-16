from ..api_asyncio import API_Asyncio_Mixin
from ..comm_asyncio import ReManagerComm_ZMQ_Asyncio
from .._defaults import (
    default_allow_request_timeout_exceptions,
    default_allow_request_fail_exceptions,
    default_zmq_request_timeout_recv,
    default_zmq_request_timeout_send,
)


class REManagerAPI(ReManagerComm_ZMQ_Asyncio, API_Asyncio_Mixin):
    def __init__(
        self,
        *,
        zmq_server_address=None,
        timeout_recv=default_zmq_request_timeout_recv,
        timeout_send=default_zmq_request_timeout_send,
        server_public_key=None,
        timeout_exceptions=default_allow_request_timeout_exceptions,
        request_fail_exceptions=default_allow_request_fail_exceptions,
        loop=None,
    ):
        ReManagerComm_ZMQ_Asyncio.__init__(
            self,
            zmq_server_address=zmq_server_address,
            timeout_recv=timeout_recv,
            timeout_send=timeout_send,
            server_public_key=server_public_key,
            timeout_exceptions=timeout_exceptions,
            request_fail_exceptions=request_fail_exceptions,
            loop=loop,
        )
        API_Asyncio_Mixin.__init__(self)
