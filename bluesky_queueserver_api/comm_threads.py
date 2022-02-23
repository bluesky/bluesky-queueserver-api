import httpx

from .comm_base import ReManagerAPI_ZMQ_Base, ReManagerAPI_HTTP_Base
from bluesky_queueserver import ZMQCommSendThreads

from .api_docstrings import _doc_send_request, _doc_close


class ReManagerComm_ZMQ_Threads(ReManagerAPI_ZMQ_Base):
    def _create_client(
        self,
        *,
        zmq_server_address,
        timeout_recv,
        timeout_send,
        server_public_key,
        loop,  # Ignored in sync version
    ):
        return ZMQCommSendThreads(
            zmq_server_address=zmq_server_address,
            timeout_recv=int(timeout_recv * 1000),  # Convert to ms
            timeout_send=int(timeout_send * 1000),  # Convert to ms
            raise_exceptions=True,
            server_public_key=server_public_key,
        )

    def send_request(self, *, method, params=None):
        try:
            response = self._client.send_message(method=method, params=params)
        except Exception:
            self._process_comm_exception(method=method, params=params)
        self._check_response(response=response)

        return response

    def close(self):
        self._client.close()


class ReManagerComm_HTTP_Threads(ReManagerAPI_HTTP_Base):
    def _create_client(self, http_server_uri, timeout):
        return httpx.Client(base_url=http_server_uri, timeout=timeout)

    def send_request(self, *, method, params=None):
        try:
            client_response = None
            request_method, endpoint, payload = self._prepare_request(method=method, params=params)
            client_response = self._client.request(request_method, endpoint, json=payload)
            response = self._process_response(client_response=client_response)

        except Exception:
            response = self._process_comm_exception(method=method, params=params, client_response=client_response)

        self._check_response(response=response)

        return response

    def close(self):
        self._client.close()


ReManagerComm_ZMQ_Threads.send_request.__doc__ = _doc_send_request
ReManagerComm_HTTP_Threads.send_request.__doc__ = _doc_send_request
ReManagerComm_ZMQ_Threads.close.__doc__ = _doc_close
ReManagerComm_HTTP_Threads.close.__doc__ = _doc_close
