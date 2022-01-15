from collections.abc import Mapping
import httpx

from .base import ReManagerAPI_Base, rest_api_method_map
from bluesky_queueserver import ZMQCommSendThreads, CommTimeoutError


class ReManagerComm_Threads_ZMQ(ReManagerAPI_Base):
    CommTimeoutError = CommTimeoutError

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
        super().__init__(request_fail_exceptions=request_fail_exceptions)

        # TODO: check env. variable for 'zmq_server_address'
        # TODO: check env. variable for 'server_public_key'

        self._comm = ZMQCommSendThreads(
            zmq_server_address=zmq_server_address,
            timeout_recv=timeout_recv,
            timeout_send=timeout_send,
            raise_exceptions=timeout_exceptions,
            server_public_key=server_public_key,
        )

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
            response = self._comm.send_message(method=method, params=params)
        except CommTimeoutError as ex:
            raise self.RequestTimeoutError(ex, {"method": method, "params": params}) from ex

        if self._request_failed_exceptions:
            # If the response is mapping, but it does not have 'success' field,
            #   then consider the request successful (this only happens for 'status' requests).
            if not isinstance(response, Mapping) or not response.get("success", True):
                raise ReManagerComm_Threads_ZMQ.RequestFailedError(response)

        return response


class ReManagerComm_Threads_HTTP(ReManagerAPI_Base):
    CommTimeoutError = CommTimeoutError

    def __init__(
        self,
        *,
        http_server_uri=None,
        timeout=5000,
        timeout_exceptions=True,
        request_fail_exceptions=True,
    ):
        super().__init__(request_fail_exceptions=request_fail_exceptions)

        # TODO: check env. variable for 'http_server_uri'

        http_server_uri = http_server_uri or "http://localhost:60610"

        self._timeout = timeout
        self._timeout_exceptions = timeout_exceptions
        self._request_fail_exceptions = request_fail_exceptions

        self._client = httpx.Client(base_url=http_server_uri, timeout=timeout / 1000)

        self._pass_user_info = False

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
            if method not in rest_api_method_map:
                raise IndexError(f"Unknown method {method!r}")
            request_method, endpoint = rest_api_method_map[method]
            payload = params or {}
            client_response = self._client.request(request_method, endpoint, json=payload)
            client_response.raise_for_status()
            response = client_response.json()

        except httpx.TimeoutException as ex:
            if self._timeout_exceptions:
                raise ReManagerComm_Threads_ZMQ.RequestTimeoutError(
                    ex, {"method": method, "params": params}
                ) from ex
            else:
                response = {"status": False, "msg": "Timeout occurred while communicating with HTTP Server"}

        except httpx.RequestError as ex:
            raise self.RequestError from ex

        except httpx.HTTPStatusError as exc:
            if client_response.status_code < 500:
                # Include more detail that httpx does by default.
                message = (
                    f"{exc.response.status_code}: "
                    f"{exc.response.json()['detail'] if client_response.content else ''} "
                    f"{exc.request.url}"
                )
                raise ReManagerComm_Threads_HTTP.ClientError(message, exc.request, exc.response) from exc
            else:
                raise ReManagerComm_Threads_HTTP.ClientError(exc) from exc

        if self._request_failed_exceptions:
            # If the response is mapping, but it does not have 'success' field,
            #   then consider the request successful (this only happens for 'status' requests).
            if not isinstance(response, Mapping) or not response.get("success", True):
                raise ReManagerComm_Threads_ZMQ.RequestFailedError(response)

        return response
