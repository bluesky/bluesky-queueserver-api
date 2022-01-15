from collections.abc import Mapping


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

    def __init__(self, *, request_fail_exceptions=True):
        # Raise exceptions if request fails (success=False)
        self._request_failed_exceptions = request_fail_exceptions

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
