from .._defaults import (
    default_allow_request_fail_exceptions,
    default_console_monitor_max_lines,
    default_console_monitor_max_msgs,
    default_console_monitor_poll_timeout,
    default_status_expiration_period,
    default_status_polling_period,
    default_zmq_request_timeout_recv,
    default_zmq_request_timeout_send,
)
from ..api_async import API_Async_Mixin
from ..api_docstrings import _doc_REManagerAPI_ZMQ
from ..comm_async import ReManagerComm_ZMQ_Async


class REManagerAPI(ReManagerComm_ZMQ_Async, API_Async_Mixin):
    # docstring is maintained separately
    def __init__(
        self,
        *,
        zmq_control_addr=None,
        zmq_info_addr=None,
        timeout_recv=default_zmq_request_timeout_recv,
        timeout_send=default_zmq_request_timeout_send,
        console_monitor_poll_timeout=default_console_monitor_poll_timeout,
        console_monitor_max_msgs=default_console_monitor_max_msgs,
        console_monitor_max_lines=default_console_monitor_max_lines,
        zmq_public_key=None,
        request_fail_exceptions=default_allow_request_fail_exceptions,
        status_expiration_period=default_status_expiration_period,
        status_polling_period=default_status_polling_period,
    ):
        ReManagerComm_ZMQ_Async.__init__(
            self,
            zmq_control_addr=zmq_control_addr,
            zmq_info_addr=zmq_info_addr,
            timeout_recv=timeout_recv,
            timeout_send=timeout_send,
            console_monitor_poll_timeout=console_monitor_poll_timeout,
            console_monitor_max_msgs=console_monitor_max_msgs,
            console_monitor_max_lines=console_monitor_max_lines,
            zmq_public_key=zmq_public_key,
            request_fail_exceptions=request_fail_exceptions,
        )
        API_Async_Mixin.__init__(
            self,
            status_expiration_period=status_expiration_period,
            status_polling_period=status_polling_period,
        )


REManagerAPI.__doc__ = _doc_REManagerAPI_ZMQ
