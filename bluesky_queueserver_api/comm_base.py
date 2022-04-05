from bluesky_queueserver import CommTimeoutError
from collections.abc import Mapping
import httpx

from ._defaults import (
    default_allow_request_fail_exceptions,
    default_zmq_request_timeout_recv,
    default_zmq_request_timeout_send,
    default_http_request_timeout,
    default_http_server_uri,
    default_console_monitor_poll_timeout,
    default_console_monitor_poll_period,
    default_console_monitor_max_msgs,
)


rest_api_method_map = {
    "ping": ("GET", "/ping"),
    "status": ("GET", "/status"),
    "queue_start": ("POST", "/queue/start"),
    "queue_stop": ("POST", "/queue/stop"),
    "queue_stop_cancel": ("POST", "/queue/stop/cancel"),
    "queue_get": ("GET", "/queue/get"),
    "queue_clear": ("POST", "/queue/clear"),
    "queue_mode_set": ("POST", "/queue/mode/set"),
    "queue_item_add": ("POST", "/queue/item/add"),
    "queue_item_add_batch": ("POST", "/queue/item/add/batch"),
    "queue_item_get": ("POST", "/queue/item/get"),
    "queue_item_update": ("POST", "/queue/item/update"),
    "queue_item_remove": ("POST", "/queue/item/remove"),
    "queue_item_remove_batch": ("POST", "/queue/item/remove/batch"),
    "queue_item_move": ("POST", "/queue/item/move"),
    "queue_item_move_batch": ("POST", "/queue/item/move/batch"),
    "queue_item_execute": ("POST", "/queue/item/execute"),
    "history_get": ("GET", "/history/get"),
    "history_clear": ("POST", "/history/clear"),
    "environment_open": ("POST", "/environment/open"),
    "environment_close": ("POST", "/environment/close"),
    "environment_destroy": ("POST", "/environment/destroy"),
    "re_pause": ("POST", "/re/pause"),
    "re_resume": ("POST", "/re/resume"),
    "re_stop": ("POST", "/re/stop"),
    "re_abort": ("POST", "/re/abort"),
    "re_halt": ("POST", "/re/halt"),
    "re_runs": ("POST", "/re/runs"),
    "plans_allowed": ("GET", "/plans/allowed"),
    "devices_allowed": ("GET", "/devices/allowed"),
    "plans_existing": ("GET", "/plans/existing"),
    "devices_existing": ("GET", "/devices/existing"),
    "permissions_reload": ("POST", "/permissions/reload"),
    "permissions_get": ("POST", "/permissions/get"),
    "permissions_set": ("POST", "/permissions/set"),
    "script_upload": ("POST", "/script/upload"),
    "function_execute": ("POST", "/function/execute"),
    "task_status": ("POST", "/task/status"),
    "task_result": ("POST", "/task/result"),
    "manager_stop": ("POST", "/manager/stop"),
    "manager_kill": ("POST", "/test/manager/kill"),
}


class RequestError(httpx.RequestError):
    ...


class ClientError(httpx.HTTPStatusError):
    ...


class RequestTimeoutError(TimeoutError):
    def __init__(self, msg, request):
        msg = f"Request timeout: {msg}"
        self.request = request
        super().__init__(msg)


class RequestFailedError(Exception):
    def __init__(self, request, response):
        msg = response.get("msg", "") if isinstance(response, Mapping) else str(response)
        msg = msg or "(no error message)"
        msg = f"Request failed: {msg}"
        self.request = request
        self.response = response
        super().__init__(msg)


class ReManagerAPI_Base:

    RequestTimeoutError = RequestTimeoutError
    RequestFailedError = RequestFailedError
    RequestError = RequestError
    ClientError = ClientError

    def __init__(self, *, request_fail_exceptions=True):
        # Raise exceptions if request fails (success=False)
        self._request_fail_exceptions = request_fail_exceptions
        self._pass_user_info = True
        self._console_monitor = None

    @property
    def request_fail_exceptions_enabled(self):
        """
        Enable or disable ``RequestFailedError`` exceptions (*boolean*). The exceptions are
        raised when the request fails, i.e. the response received from the server contains
        ``'success'==False``. The property does not influence timeout errors.
        """
        return self._request_fail_exceptions

    @request_fail_exceptions_enabled.setter
    def request_fail_exceptions_enabled(self, v):
        self._request_fail_exceptions = bool(v)

    def _check_response(self, *, request, response):
        """
        Check if response is a dictionary and has ``"success": True``. Raise an exception
        if the request is considered failed and exceptions are allowed. If response is
        a dictionary and contains no ``"success"``, then it is considered successful.
        """
        if self._request_fail_exceptions:
            # If the response is mapping, but it does not have 'success' field,
            #   then consider the request successful (this only happens for 'status' requests).
            if not isinstance(response, Mapping) or not response.get("success", True):
                raise self.RequestFailedError(request, response)

    @property
    def console_monitor(self):
        """
        Reference to a ``console_monitor``. Console monitor is an instance of
        a matching ``ConsoleMonitor_...`` class and supports methods ``enable()``,
        ``disable()``, ``disable_wait()``, ``clear()``, ``next_msg()`` and
        property ``enabled``. See documentation for the appropriate class
        for more details.
        """
        return self._console_monitor

    def _init_console_monitor(self):
        raise NotImplementedError()


class ReManagerAPI_ZMQ_Base(ReManagerAPI_Base):
    def __init__(
        self,
        *,
        zmq_server_address=None,
        zmq_subscribe_addr=None,
        timeout_recv=default_zmq_request_timeout_recv,
        timeout_send=default_zmq_request_timeout_send,
        console_monitor_poll_timeout=default_console_monitor_poll_timeout,
        console_monitor_max_msgs=default_console_monitor_max_msgs,
        server_public_key=None,
        request_fail_exceptions=default_allow_request_fail_exceptions,
    ):
        super().__init__(request_fail_exceptions=request_fail_exceptions)

        # TODO: check env. variable for 'zmq_server_address'
        # TODO: check env. variable for 'zmq_subscribe_address'
        # TODO: check env. variable for 'server_public_key'

        self._zmq_subscribe_addr = zmq_subscribe_addr
        self._console_monitor_poll_timeout = console_monitor_poll_timeout
        self._console_monitor_max_msgs = console_monitor_max_msgs

        self._client = self._create_client(
            zmq_server_address=zmq_server_address,
            timeout_recv=timeout_recv,
            timeout_send=timeout_send,
            server_public_key=server_public_key,
        )

        self._init_console_monitor()

    def _create_client(
        self,
        *,
        zmq_server_address,
        timeout_recv,
        timeout_send,
        server_public_key,
    ):
        raise NotImplementedError()

    def _process_comm_exception(self, *, method, params):
        try:
            raise
        except CommTimeoutError as ex:
            raise self.RequestTimeoutError(ex, {"method": method, "params": params}) from ex


class ReManagerAPI_HTTP_Base(ReManagerAPI_Base):
    def __init__(
        self,
        *,
        http_server_uri=None,
        timeout=default_http_request_timeout,
        console_monitor_poll_period=default_console_monitor_poll_period,
        console_monitor_max_msgs=default_console_monitor_max_msgs,
        request_fail_exceptions=default_allow_request_fail_exceptions,
    ):
        super().__init__(request_fail_exceptions=request_fail_exceptions)

        # TODO: check env. variable for 'http_server_uri'

        # Do not pass user info with request (e.g. user info is not required in REST API requests,
        #   because HTTP Server assigns user name and user group based on login information)
        self._pass_user_info = False

        http_server_uri = http_server_uri or default_http_server_uri

        self._timeout = timeout
        self._request_fail_exceptions = request_fail_exceptions
        self._console_monitor_poll_period = console_monitor_poll_period
        self._console_monitor_max_msgs = console_monitor_max_msgs

        self._rest_api_method_map = rest_api_method_map

        self._client = self._create_client(http_server_uri=http_server_uri, timeout=timeout)

        self._init_console_monitor()

    def _create_client(self, http_server_uri, timeout):
        raise NotImplementedError()

    def _prepare_request(self, *, method, params=None):
        if method not in self._rest_api_method_map:
            raise KeyError(f"Unknown method {method!r}")
        request_method, endpoint = rest_api_method_map[method]
        payload = params or {}
        return request_method, endpoint, payload

    def _process_response(self, *, client_response):
        client_response.raise_for_status()
        response = client_response.json()
        return response

    def _process_comm_exception(self, *, method, params, client_response):
        """
        The function must be called from ``except`` block and returns response with an error message
        or raises an exception.
        """
        try:
            raise

        except httpx.TimeoutException as ex:
            raise self.RequestTimeoutError(ex, {"method": method, "params": params}) from ex

        except httpx.RequestError as ex:
            raise self.RequestError(f"HTTP request error: {ex}") from ex

        except httpx.HTTPStatusError as exc:
            if client_response and (client_response.status_code < 500):
                # Include more detail that httpx does by default.
                message = (
                    f"{exc.response.status_code}: "
                    f"{exc.response.json()['detail'] if client_response.content else ''} "
                    f"{exc.request.url}"
                )
                raise self.ClientError(message, request=exc.request, response=exc.response) from exc
            else:
                raise self.ClientError(exc) from exc
