import httpx

from .comm_base import ReManagerAPI_ZMQ_Base, ReManagerAPI_HTTP_Base
from bluesky_queueserver import ZMQCommSendAsync

from .api_docstrings import _doc_send_request, _doc_close
from .console_monitor import ConsoleMonitor_ZMQ_Async, ConsoleMonitor_HTTP_Async


class ReManagerComm_ZMQ_Async(ReManagerAPI_ZMQ_Base):
    def _init_console_monitor(self):
        self._console_monitor = ConsoleMonitor_ZMQ_Async(
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
        return ZMQCommSendAsync(
            zmq_server_address=zmq_control_addr,
            timeout_recv=int(timeout_recv * 1000),  # Convert to ms
            timeout_send=int(timeout_send * 1000),  # Convert to ms
            raise_exceptions=True,
            server_public_key=zmq_public_key,
        )

    async def send_request(self, *, method, params=None):
        try:
            response = await self._client.send_message(method=method, params=params)
        except Exception:
            self._process_comm_exception(method=method, params=params)
        self._check_response(request={"method": method, "params": params}, response=response)

        return response

    async def close(self):
        await self._console_monitor.disable_wait(timeout=self._console_monitor_poll_timeout * 10)
        self._client.close()


class ReManagerComm_HTTP_Async(ReManagerAPI_HTTP_Base):
    def _init_console_monitor(self):
        self._console_monitor = ConsoleMonitor_HTTP_Async(
            parent=self,
            poll_period=self._console_monitor_poll_period,
            max_msgs=self._console_monitor_max_msgs,
            max_lines=self._console_monitor_max_lines,
        )

    def _create_client(self, http_server_uri, timeout):
        return httpx.AsyncClient(base_url=http_server_uri, timeout=timeout)

    async def send_request(self, *, method, params=None, headers=None, data=None, timeout=None):
        # Docstring is maintained separately
        try:
            client_response = None
            request_method, endpoint, payload = self._prepare_request(method=method, params=params)
            headers = self._prepare_headers()
            kwargs = {"json": payload}
            if headers:
                kwargs.update({"headers": headers})
            if data:
                kwargs.update({"data": data})
            if timeout is not None:
                # If timeout is None, then use the default value, if timeout is 0 or negative,
                #   then disable timeout, otherwise set timeout for current request
                kwargs.update({"timeout": timeout if (timeout > 0) else None})
            client_response = await self._client.request(request_method, endpoint, **kwargs)
            response = self._process_response(client_response=client_response)

        except Exception:
            response = self._process_comm_exception(method=method, params=params, client_response=client_response)

        self._check_response(request={"method": method, "params": params}, response=response)

        return response

    async def close(self):
        await self._console_monitor.disable_wait(timeout=self._console_monitor_poll_period * 10)
        await self._client.aclose()

    async def login(self, username, password, *, provider=None):
        # Docstring is maintained separately
        endpoint, data = self._prepare_login(username=username, password=password, provider=provider)
        response = await self.send_request(method=("POST", endpoint), data=data)
        response = self._process_login_response(response=response)
        return response


ReManagerComm_ZMQ_Async.send_request.__doc__ = _doc_send_request
ReManagerComm_HTTP_Async.send_request.__doc__ = _doc_send_request
ReManagerComm_ZMQ_Async.close.__doc__ = _doc_close
ReManagerComm_HTTP_Async.close.__doc__ = _doc_close
