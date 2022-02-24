from ..api_async import API_Async_Mixin
from ..comm_async import ReManagerComm_ZMQ_Async
from .._defaults import (
    default_allow_request_fail_exceptions,
    default_zmq_request_timeout_recv,
    default_zmq_request_timeout_send,
    default_status_expiration_period,
    default_status_polling_period,
)

from ..api_docstrings import _doc_REManagerAPI_ZMQ


class REManagerAPI(ReManagerComm_ZMQ_Async, API_Async_Mixin):
    # docstring is maintained separately
    def __init__(
        self,
        *,
        zmq_server_address=None,
        timeout_recv=default_zmq_request_timeout_recv,
        timeout_send=default_zmq_request_timeout_send,
        server_public_key=None,
        request_fail_exceptions=default_allow_request_fail_exceptions,
        status_expiration_period=default_status_expiration_period,
        status_polling_period=default_status_polling_period,
        loop=None,
    ):
        ReManagerComm_ZMQ_Async.__init__(
            self,
            zmq_server_address=zmq_server_address,
            timeout_recv=timeout_recv,
            timeout_send=timeout_send,
            server_public_key=server_public_key,
            request_fail_exceptions=request_fail_exceptions,
            loop=loop,
        )
        API_Async_Mixin.__init__(
            self,
            status_expiration_period=status_expiration_period,
            status_polling_period=status_polling_period,
        )


REManagerAPI.__doc__ = _doc_REManagerAPI_ZMQ
