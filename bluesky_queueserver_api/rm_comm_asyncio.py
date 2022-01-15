from collections.abc import Mapping

from .base import ReManagerAPI_Base
from bluesky_queueserver import ZMQCommSendAsync, CommTimeoutError


class ReManagerComm_Asyncio_ZMQ(ReManagerAPI_Base):
    CommTimeoutError = CommTimeoutError

    def __init__(
        self,
        *,
        loop=None,
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

        self._comm = ZMQCommSendAsync(
            loop=loop,
            zmq_server_address=zmq_server_address,
            timeout_recv=timeout_recv,
            timeout_send=timeout_send,
            raise_exceptions=timeout_exceptions,
            server_public_key=server_public_key,
        )

    @property
    def loop(self):
        return self._comm.get_loop()

    async def send_request(self, *, method, params=None):
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
            response = await self._comm.send_message(method=method, params=params)
        except CommTimeoutError as ex:
            raise self.RequestTimeoutError(ex, {"method": method, "params": params}) from ex

        if self._request_failed_exceptions:
            # If the response is mapping, but it does not have 'success' field,
            #   then consider the request successful (this only happens for 'status' requests).
            if not isinstance(response, Mapping) or not response.get("success", True):
                raise self.RequestFailedError(response)

        return response
