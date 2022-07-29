from bluesky_queueserver import CommTimeoutError
from collections.abc import Mapping
import enum
import httpx
import os

from ._defaults import (
    default_allow_request_fail_exceptions,
    default_zmq_request_timeout_recv,
    default_zmq_request_timeout_send,
    default_http_request_timeout,
    default_http_server_uri,
    default_console_monitor_poll_timeout,
    default_console_monitor_poll_period,
    default_console_monitor_max_msgs,
    default_console_monitor_max_lines,
)


rest_api_method_map = {
    "ping": ("GET", "/api/ping"),
    "status": ("GET", "/api/status"),
    "queue_start": ("POST", "/api/queue/start"),
    "queue_stop": ("POST", "/api/queue/stop"),
    "queue_stop_cancel": ("POST", "/api/queue/stop/cancel"),
    "queue_get": ("GET", "/api/queue/get"),
    "queue_clear": ("POST", "/api/queue/clear"),
    "queue_mode_set": ("POST", "/api/queue/mode/set"),
    "queue_item_add": ("POST", "/api/queue/item/add"),
    "queue_item_add_batch": ("POST", "/api/queue/item/add/batch"),
    "queue_item_get": ("GET", "/api/queue/item/get"),
    "queue_item_update": ("POST", "/api/queue/item/update"),
    "queue_item_remove": ("POST", "/api/queue/item/remove"),
    "queue_item_remove_batch": ("POST", "/api/queue/item/remove/batch"),
    "queue_item_move": ("POST", "/api/queue/item/move"),
    "queue_item_move_batch": ("POST", "/api/queue/item/move/batch"),
    "queue_item_execute": ("POST", "/api/queue/item/execute"),
    "history_get": ("GET", "/api/history/get"),
    "history_clear": ("POST", "/api/history/clear"),
    "environment_open": ("POST", "/api/environment/open"),
    "environment_close": ("POST", "/api/environment/close"),
    "environment_destroy": ("POST", "/api/environment/destroy"),
    "re_pause": ("POST", "/api/re/pause"),
    "re_resume": ("POST", "/api/re/resume"),
    "re_stop": ("POST", "/api/re/stop"),
    "re_abort": ("POST", "/api/re/abort"),
    "re_halt": ("POST", "/api/re/halt"),
    "re_runs": ("POST", "/api/re/runs"),
    "plans_allowed": ("GET", "/api/plans/allowed"),
    "devices_allowed": ("GET", "/api/devices/allowed"),
    "plans_existing": ("GET", "/api/plans/existing"),
    "devices_existing": ("GET", "/api/devices/existing"),
    "permissions_reload": ("POST", "/api/permissions/reload"),
    "permissions_get": ("GET", "/api/permissions/get"),
    "permissions_set": ("POST", "/api/permissions/set"),
    "script_upload": ("POST", "/api/script/upload"),
    "function_execute": ("POST", "/api/function/execute"),
    "task_status": ("GET", "/api/task/status"),
    "task_result": ("GET", "/api/task/result"),
    "lock": ("POST", "/api/lock"),
    "unlock": ("POST", "/api/unlock"),
    "lock_info": ("GET", "/api/lock/info"),
    "manager_stop": ("POST", "/api/manager/stop"),
    "manager_kill": ("POST", "/api/test/manager/kill"),
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


class Protocols(enum.Enum):
    ZMQ = "ZMQ"
    HTTP = "HTTP"


class AuthorizationMethods(enum.Enum):
    NONE = "NONE"
    API_KEY = "API_KEY"
    TOKEN = "TOKEN"


class ReManagerAPI_Base:

    RequestTimeoutError = RequestTimeoutError
    RequestFailedError = RequestFailedError
    RequestError = RequestError
    ClientError = ClientError

    Protocols = Protocols
    AuthorizationMethods = AuthorizationMethods

    def __init__(self, *, request_fail_exceptions=True):
        # Raise exceptions if request fails (success=False)
        self._request_fail_exceptions = request_fail_exceptions
        self._console_monitor = None

        self._protocol = None
        self._pass_user_info = True

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

    @property
    def protocol(self):
        """
        Indicates the protocol used for communication (ZMQ or HTTP). The returned value is of
        ``REManagerAPI.Protocols`` enum type.
        """
        if self._protocol is None:
            raise ValueError("Protocol is not defined")
        return self._protocol


class ReManagerAPI_ZMQ_Base(ReManagerAPI_Base):
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
    ):
        super().__init__(request_fail_exceptions=request_fail_exceptions)

        self._protocol = self.Protocols.ZMQ

        zmq_control_addr = zmq_control_addr or os.environ.get("QSERVER_ZMQ_CONTROL_ADDRESS", None)
        zmq_info_addr = zmq_info_addr or os.environ.get("QSERVER_ZMQ_INFO_ADDRESS", None)
        zmq_public_key = zmq_public_key or os.environ.get("QSERVER_ZMQ_PUBLIC_KEY", None)

        self._zmq_info_addr = zmq_info_addr
        self._console_monitor_poll_timeout = console_monitor_poll_timeout
        self._console_monitor_max_msgs = console_monitor_max_msgs
        self._console_monitor_max_lines = console_monitor_max_lines

        self._client = self._create_client(
            zmq_control_addr=zmq_control_addr,
            timeout_recv=timeout_recv,
            timeout_send=timeout_send,
            zmq_public_key=zmq_public_key,
        )

        self._init_console_monitor()

    def _create_client(
        self,
        *,
        zmq_control_addr,
        timeout_recv,
        timeout_send,
        zmq_public_key,
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
        api_prefix=None,
        timeout=default_http_request_timeout,
        console_monitor_poll_period=default_console_monitor_poll_period,
        console_monitor_max_msgs=default_console_monitor_max_msgs,
        console_monitor_max_lines=default_console_monitor_max_lines,
        request_fail_exceptions=default_allow_request_fail_exceptions,
    ):
        super().__init__(request_fail_exceptions=request_fail_exceptions)

        self._protocol = self.Protocols.HTTP
        # Do not pass user info with request (e.g. user info is not required in REST API requests,
        #   because HTTP Server assigns user name and user group based on login information)
        self._pass_user_info = False

        # Default authorization type and key
        self._auth_method = AuthorizationMethods.NONE
        self._auth_key = None  # May be a token or an API key

        http_server_uri = http_server_uri or os.environ.get("QSERVER_HTTP_SERVER_URI")
        http_server_uri = http_server_uri or default_http_server_uri

        self._timeout = timeout
        self._request_fail_exceptions = request_fail_exceptions
        self._console_monitor_poll_period = console_monitor_poll_period
        self._console_monitor_max_msgs = console_monitor_max_msgs
        self._console_monitor_max_lines = console_monitor_max_lines

        self._rest_api_method_map = rest_api_method_map
        if api_prefix:
            api_prefix = api_prefix.strip()
            api_prefix = api_prefix if api_prefix.startswith("/") else f"/{api_prefix}"
        self._rest_api_prefix = api_prefix

        self._client = self._create_client(http_server_uri=http_server_uri, timeout=timeout)

        self._init_console_monitor()

    def _create_client(self, http_server_uri, timeout):
        raise NotImplementedError()

    def _prepare_headers(self):
        if self.auth_method == self.AuthorizationMethods.API_KEY:
            headers = {"Authorization": f"ApiKey {self.auth_key}"}
        else:
            headers = None
        return headers

    def _prepare_request(self, *, method, params=None):
        if method not in self._rest_api_method_map:
            raise KeyError(f"Unknown method {method!r}")
        request_method, endpoint = rest_api_method_map[method]
        endpoint = f"{self._rest_api_prefix}{endpoint}" if self._rest_api_prefix else endpoint
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

    @property
    def auth_method(self):
        """
        Returns authorization method (API key, token or none).

        Returns
        -------
        REManagerAPI.AuthorizationMethods
            Enum value that defines current authorization method.
        """
        return self._auth_method

    @property
    def auth_key(self):
        """
        Returns authorization key.

        Returns
        -------
        str, tuple(str) or None
            Depending on currently selected authorization method, returns a string (API key), tuple of strings
            with authorization token as the first element (may be ``None``) and the refresh token
            (may be ``None``) as the second element. If no authorization is used then the return value
            is ``None``.
        """
        return self._auth_key

    def set_authorization_key(self, *, api_key=None, token=None, refresh_token=None):
        """
        Set default authorization key(s) for HTTP requests. Authorization method is selected based on whether
        an API key or token(s) are passed to the API. API keys and tokens are mutually exclusive and can not
        be passed to the request simultaneously. If the API call contains no API keys, then authorization is
        disabled.

        The function configures authorization method and keys without communicating with the server or
        validation of the keys.

        Parameters
        ----------
        api_key: str
            API key for HTTP requests to the server. Default: ``None``.
        token: str
            Authorization token for HTTP requests to the server. If the token is ``None`` and the refresh token
            is specified, then the new authorization token is requested from the server during the first HTTP
            request. Default: ``None``.
        refresh_token: str
            Refresh token used to request authorization token from the server. Default: ``None``.
        """
        if api_key and (token or refresh_token):
            raise ValueError("API key and a token are mutually exclusive and can not be specified simultaneously.")

        if not isinstance(api_key, (str, type(None))):
            raise TypeError(f"API key must be a string or None: api_key={api_key} type(api_key)={type(api_key)}")
        if not isinstance(token, (str, type(None))):
            raise TypeError(f"Token must be a string or None: token={token} type(token)={type(token)}")
        if not isinstance(refresh_token, (str, type(None))):
            raise TypeError(
                f"Refresh token must be a string or None: refresh_token={refresh_token} "
                f"type(refresh_token)={type(refresh_token)}"
            )

        if api_key:
            self._auth_method = self.AuthorizationMethods.API_KEY
            self._auth_key = api_key
        elif token or refresh_token:
            self._auth_method = self.AuthorizationMethods.TOKEN
            self._auth_key = (token, refresh_token)
        else:
            self._auth_method = self.AuthorizationMethods.NONE
            self._auth_key = None
