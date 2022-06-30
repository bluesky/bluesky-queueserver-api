from ..api_threads import API_Threads_Mixin
from ..comm_threads import ReManagerComm_HTTP_Threads

from .._defaults import (
    default_allow_request_fail_exceptions,
    default_http_request_timeout,
    default_status_expiration_period,
    default_status_polling_period,
    default_console_monitor_poll_period,
    default_console_monitor_max_msgs,
    default_console_monitor_max_lines,
)

from ..api_docstrings import _doc_REManagerAPI_HTTP


class REManagerAPI(ReManagerComm_HTTP_Threads, API_Threads_Mixin):
    def __init__(
        self,
        *,
        http_server_uri=None,
        api_prefix=None,
        timeout=default_http_request_timeout,
        console_monitor_poll_period=default_console_monitor_poll_period,
        console_monitor_max_msgs=default_console_monitor_max_msgs,
        console_monitor_max_lines=default_console_monitor_max_lines,
        request_fail_exceptions=default_allow_request_fail_exceptions,
        status_expiration_period=default_status_expiration_period,
        status_polling_period=default_status_polling_period,
    ):
        ReManagerComm_HTTP_Threads.__init__(
            self,
            http_server_uri=http_server_uri,
            api_prefix=api_prefix,
            timeout=timeout,
            console_monitor_poll_period=console_monitor_poll_period,
            console_monitor_max_msgs=console_monitor_max_msgs,
            console_monitor_max_lines=console_monitor_max_lines,
            request_fail_exceptions=request_fail_exceptions,
        )
        API_Threads_Mixin.__init__(
            self,
            status_expiration_period=status_expiration_period,
            status_polling_period=status_polling_period,
        )


REManagerAPI.__doc__ = _doc_REManagerAPI_HTTP
