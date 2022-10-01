import httpx

from .comm_base import ReManagerAPI_ZMQ_Base, ReManagerAPI_HTTP_Base
from bluesky_queueserver import ZMQCommSendThreads

from .api_docstrings import _doc_send_request, _doc_close, _doc_api_login, _doc_api_session_refresh
from .console_monitor import ConsoleMonitor_ZMQ_Threads, ConsoleMonitor_HTTP_Threads


class ReManagerComm_ZMQ_Threads(ReManagerAPI_ZMQ_Base):
    def _init_console_monitor(self):
        self._console_monitor = ConsoleMonitor_ZMQ_Threads(
            zmq_info_addr=self._zmq_info_addr,
            poll_timeout=self._console_monitor_poll_timeout,
            max_msgs=self._console_monitor_max_msgs,
            max_lines=self._console_monitor_max_lines,
        )

    def _create_client(
        self,
        *,
        zmq_control_addr,
        timeout_recv,
        timeout_send,
        zmq_public_key,
    ):
        return ZMQCommSendThreads(
            zmq_server_address=zmq_control_addr,
            timeout_recv=int(timeout_recv * 1000),  # Convert to ms
            timeout_send=int(timeout_send * 1000),  # Convert to ms
            raise_exceptions=True,
            server_public_key=zmq_public_key,
        )

    def send_request(self, *, method, params=None):
        try:
            response = self._client.send_message(method=method, params=params)
        except Exception:
            self._process_comm_exception(method=method, params=params)
        self._check_response(request={"method": method, "params": params}, response=response)

        return response

    def close(self):
        self._is_closing = True
        self._console_monitor.disable_wait(timeout=self._console_monitor_poll_timeout * 10)
        self._client.close()

    def __del__(self):
        self._is_closing = True


class ReManagerComm_HTTP_Threads(ReManagerAPI_HTTP_Base):
    def _init_console_monitor(self):
        self._console_monitor = ConsoleMonitor_HTTP_Threads(
            parent=self,
            poll_period=self._console_monitor_poll_period,
            max_msgs=self._console_monitor_max_msgs,
            max_lines=self._console_monitor_max_lines,
        )

    def _create_client(self, http_server_uri, timeout):
        timeout = self._adjust_timeout(timeout)
        return httpx.Client(base_url=http_server_uri, timeout=timeout)

    def _simple_request(self, *, method, params=None, headers=None, data=None, timeout=None):
        """
        The code that formats and sends a simple request.
        """
        try:
            client_response = None
            request_method, endpoint, payload = self._prepare_request(method=method, params=params)
            headers = headers or self._prepare_headers()
            kwargs = {"json": payload}
            if headers:
                kwargs.update({"headers": headers})
            if data:
                kwargs.update({"data": data})
            if timeout is not None:
                kwargs.update({"timeout": self._adjust_timeout(timeout)})
            client_response = self._client.request(request_method, endpoint, **kwargs)
            response = self._process_response(client_response=client_response)

        except Exception:
            response = self._process_comm_exception(method=method, params=params, client_response=client_response)

        self._check_response(request={"method": method, "params": params}, response=response)

        return response

    def send_request(
        self, *, method, params=None, headers=None, data=None, timeout=None, auto_refresh_session=True
    ):
        # Docstring is maintained separately
        refresh = False
        request_params = {"method": method, "params": params, "headers": headers, "data": data, "timeout": timeout}
        try:
            response = self._simple_request(**request_params)
        except self.HTTPClientError as ex:
            # The session is supposed to be automatically refreshed only if the expired token is passed
            #   to the server. Otherwise the request is expected to fail.
            if (
                auto_refresh_session
                and ("401: Access token has expired" in str(ex))
                and (self.auth_method == self.AuthorizationMethods.TOKEN)
                and (self.auth_key[1] is not None)
            ):
                refresh = True
            else:
                raise

        if refresh:
            try:
                self.session_refresh()
            except Exception as ex:
                print(f"Failed to refresh session: {ex}")

            # Try calling the API with the new token (or the old one if refresh failed).
            response = self._simple_request(**request_params)

        return response

    def login(self, username=None, *, password=None, provider=None):
        # Docstring is maintained separately
        endpoint, data = self._prepare_login(username=username, password=password, provider=provider)
        response = self.send_request(
            method=("POST", endpoint), data=data, timeout=self._timeout_login, auto_refresh_session=False
        )
        response = self._process_login_response(response=response)
        return response

    def session_refresh(self, *, refresh_token=None):
        # Docstring is maintained separately
        refresh_token = self._prepare_refresh_session(refresh_token=refresh_token)
        response = self.send_request(
            method="session_refresh", params={"refresh_token": refresh_token}, auto_refresh_session=False
        )
        response = self._process_login_response(response=response)
        return response

    def session_revoke(self, *, session_uid):
        # Docstring is maintained separately
        raise NotImplementedError()

    def apikey_new(self, *, expires_in, scopes=None, note=None, principal_uid=None):
        # Docstring is maintained separately
        raise NotImplementedError()

    def apikey_info(self, *, api_key=None):
        # Docstring is maintained separately
        raise NotImplementedError()

    def whoami(self, *, token=None, api_key=None):
        # Docstring is maintained separately
        raise NotImplementedError()

    def principal_info(self, *, principal_uid=None):
        # Docstring is maintained separately
        raise NotImplementedError()

    def api_scopes(self, *, token=None, api_key=None):
        # Docstring is maintained separately
        raise NotImplementedError()

    def apikey_delete(self, *, first_eight):
        # Docstring is maintained separately
        raise NotImplementedError()

    def logout(self):
        raise NotImplementedError()

    def close(self):
        self._is_closing = True
        self._console_monitor.disable_wait(timeout=self._console_monitor_poll_period * 10)
        self._client.close()

    def __del__(self):
        self._is_closing = True


ReManagerComm_ZMQ_Threads.send_request.__doc__ = _doc_send_request
ReManagerComm_HTTP_Threads.send_request.__doc__ = _doc_send_request
ReManagerComm_ZMQ_Threads.close.__doc__ = _doc_close
ReManagerComm_HTTP_Threads.close.__doc__ = _doc_close
ReManagerComm_HTTP_Threads.login.__doc__ = _doc_api_login
ReManagerComm_HTTP_Threads.session_refresh.__doc__ = _doc_api_session_refresh
