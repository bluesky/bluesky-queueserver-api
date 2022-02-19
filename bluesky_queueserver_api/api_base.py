from .item import BItem
from collections.abc import Mapping


class WaitTimeoutError(TimeoutError):
    ...


class WaitCancelError(TimeoutError):
    ...


class WaitMonitor:
    def __init__(self):
        self._time_start = 0
        self._time_elapsed = 0
        self._timeout_period = 0
        self._cancel_callbacks = []

        self._wait_cancelled = False

    @property
    def time_start(self):
        return self._time_start

    @property
    def time_elapsed(self):
        return self._time_elapsed

    @property
    def timeout_period(self):
        return self._timeout_period

    def set_time_start(self, time_start):
        self._time_start = time_start

    def set_time_elapsed(self, time_elapsed):
        self._time_elapsed = time_elapsed

    def set_timeout_period(self, timeout_period):
        self._timeout_period = timeout_period

    def add_cancel_callback(self, cancel_callback):
        self._cancel_callbacks.append(cancel_callback)

    def cancel(self):
        for cb in self._cancel_callbacks:
            try:
                cb()
            except Exception:
                pass

        self._cancel_callbacks = []
        self._wait_cancelled = True

    @property
    def is_cancelled(self):
        return self._wait_cancelled


class API_Base:
    WaitTimeoutError = WaitTimeoutError
    WaitCancelError = WaitCancelError

    def __init__(self, *, status_min_period=0.5, status_polling_period=1.0):

        self._status_min_period = status_min_period  # seconds
        self._status_polling_period = status_polling_period  # seconds

        self._user = "Python API User"
        self._user_group = "admin"

        self._current_queue = []
        self._current_queue_uid = None
        self._current_history = []
        self._current_history_uid = None

    def _prepare_add_item(self, *, item, pos, before_uid, after_uid):
        """
        Prepare parameters for 'add_item' operation.
        """
        if not isinstance(item, BItem) and not isinstance(item, Mapping):
            raise TypeError(f"Incorrect item type {type(item)!r}. Expected type: 'BItem' or 'dict'")

        item = item.to_dict() if isinstance(item, BItem) else item.copy()

        request_params = {"item": item}
        if pos is not None:
            request_params["pos"] = pos
        if before_uid is not None:
            request_params["before_uid"] = before_uid
        if after_uid is not None:
            request_params["after_uid"] = after_uid

        if self._pass_user_info:
            request_params["user"] = self._user
            request_params["user_group"] = self._user_group

        return request_params
