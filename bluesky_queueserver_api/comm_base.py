from bluesky_queueserver import CommTimeoutError
from collections.abc import Mapping
import httpx


default_allow_request_timeout_exceptions = True
default_allow_request_fail_exceptions = True

default_zmq_request_timeout_recv = 2000  # ms
default_zmq_request_timeout_send = 500  # ms

default_http_request_timeout = 5000  # ms
default_http_server_uri = "http://localhost:60610"  # Default URI (for testing and evaluation)

rest_api_method_map = {
    "status": ("GET", "/status"),
    "queue_item_add": ("POST", "/queue/item/add"),
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
    def __init__(self, response):
        msg = response.get("msg", "") if isinstance(response, Mapping) else str(response)
        msg = f"Request failed: {msg}"
        self.response = response
        super().__init__(msg)


class ReManagerAPI_Base:

    RequestTimeoutError = RequestTimeoutError
    RequestFailedError = RequestFailedError
    RequestError = RequestError
    ClientError = ClientError

    def __init__(self, *, request_fail_exceptions=True):
        # Raise exceptions if request fails (success=False)
        self._request_failed_exceptions = request_fail_exceptions
        self._pass_user_info = True

    @property
    def pass_user_info(self):
        return self._pass_user_info

    @property
    def request_failed_exception(self):
        """
        Property values ``True`` and ``False`` enable and disable ``RequestFailedError``
        exceptions raised when request fails, i.e. the response contains ``'success'==False``.
        """
        return self._request_failed_exception

    @request_failed_exception.setter
    def request_failed_exception(self, v):
        self._request_failed_exceptions = bool(v)

    def _check_response(self, *, response):
        if self._request_failed_exceptions:
            # If the response is mapping, but it does not have 'success' field,
            #   then consider the request successful (this only happens for 'status' requests).
            if not isinstance(response, Mapping) or not response.get("success", True):
                raise self.RequestFailedError(response)


class ReManagerAPI_ZMQ_Base(ReManagerAPI_Base):
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
        super().__init__(request_fail_exceptions=request_fail_exceptions)

        # TODO: check env. variable for 'zmq_server_address'
        # TODO: check env. variable for 'server_public_key'

        self._client = self._create_client(
            zmq_server_address=zmq_server_address,
            timeout_recv=timeout_recv,
            timeout_send=timeout_send,
            timeout_exceptions=timeout_exceptions,
            server_public_key=server_public_key,
            loop=loop,
        )
        # self._comm = ZMQCommSendThreads(
        #     zmq_server_address=zmq_server_address,
        #     timeout_recv=timeout_recv,
        #     timeout_send=timeout_send,
        #     raise_exceptions=timeout_exceptions,
        #     server_public_key=server_public_key,
        # )

    def _create_client(
        self,
        *,
        zmq_server_address,
        timeout_recv,
        timeout_send,
        timeout_exceptions,
        server_public_key,
        loop,
    ):
        raise NotImplementedError()

    def _process_comm_exception(self, *, method, params):
        try:
            raise
        except CommTimeoutError as ex:
            raise self.RequestTimeoutError(ex, {"method": method, "params": params}) from ex

    def send_request(self, *, method, params=None):
        """
        Send message to RE Manager and return the response. This function allows calls
        to low level Re Manager API. The function may raise exceptions in case of request
        timeout or failure.

        Parameters
        ----------
        method: str
            Name of the API method
        params: dict or None
            Dictionary of API parameters or ``None`` if no parameters are passed.

        Returns
        -------
        dict
            Dictionary which contains returned results

        Raises
        ------
        RequestTimeoutError
            Request timed out.
        RequestFailedError
            Request failed.
        """
        try:
            response = self._client.send_message(method=method, params=params)
        except Exception:
            self._process_comm_exception(method=method, params=params)
        self._check_response(response=response)

        return response


class ReManagerAPI_HTTP_Base(ReManagerAPI_Base):
    def __init__(
        self,
        *,
        http_server_uri=None,
        timeout=default_http_request_timeout,
        timeout_exceptions=default_allow_request_timeout_exceptions,
        request_fail_exceptions=default_allow_request_fail_exceptions,
    ):
        super().__init__(request_fail_exceptions=request_fail_exceptions)

        # TODO: check env. variable for 'http_server_uri'

        # Do not pass user info with request (HTTP Server will assign user name and user group)
        self._pass_user_info = False

        http_server_uri = http_server_uri or default_http_server_uri

        self._timeout = timeout
        self._timeout_exceptions = timeout_exceptions
        self._request_fail_exceptions = request_fail_exceptions

        self._rest_api_method_map = rest_api_method_map

        self._client = self._create_client(http_server_uri=http_server_uri, timeout=timeout)

    def _create_client(self, http_server_uri, timeout):
        raise NotImplementedError()

    def _prepare_request(self, *, method, params=None):
        if method not in self._rest_api_method_map:
            raise IndexError(f"Unknown method {method!r}")
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
            if self._timeout_exceptions:
                raise self.RequestTimeoutError(ex, {"method": method, "params": params}) from ex
            else:
                return {"status": False, "msg": "Timeout occurred while communicating with HTTP Server"}

        except httpx.RequestError as ex:
            raise self.RequestError from ex

        except httpx.HTTPStatusError as exc:
            if client_response and (client_response.status_code < 500):
                # Include more detail that httpx does by default.
                message = (
                    f"{exc.response.status_code}: "
                    f"{exc.response.json()['detail'] if client_response.content else ''} "
                    f"{exc.request.url}"
                )
                raise self.ClientError(message, exc.request, exc.response) from exc
            else:
                raise self.ClientError(exc) from exc
