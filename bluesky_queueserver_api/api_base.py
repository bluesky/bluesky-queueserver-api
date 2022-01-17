from .item import BItem
from collections.abc import Mapping


class WaitTimeoutError(TimeoutError):
    ...


class QueueBase:
    def __init__(self, *, rm):
        self._rm = rm

        self._current_queue = []
        self._current_queue_uid = None

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

        if self._rm.pass_user_info:
            request_params["user"] = self._rm._user
            request_params["user_group"] = self._rm._user_group

        return request_params


class HistoryBase:
    def __init__(self, *, rm):
        self._rm = rm

        self._current_history = []
        self._current_history_uid = None


class ManagerBase:
    def __init__(self, *, rm):
        self._rm = rm


class EnvironmentBase:
    def __init__(self, *, rm):
        self._rm = rm


class RunEngineBase:
    def __init__(self, *, rm):
        self._rm = rm


class API_Base:
    WaitTimeoutError = WaitTimeoutError

    def __init__(self, *, queue_type, history_type, manager_type, environment_type, run_engine_type):
        self._user = "Python API User"
        self._user_group = "admin"

        self._q = queue_type(rm=self)
        self._h = history_type(rm=self)
        self._m = manager_type(rm=self)
        self._e = environment_type(rm=self)
        self._r = run_engine_type(rm=self)

    @property
    def q(self):
        """
        API for management of plan queue.
        """
        return self._q

    @property
    def h(self):
        """
        API for management of plan history.
        """
        return self._h

    @property
    def m(self):
        """
        API for controlling RE Manager.
        """
        return self._m

    @property
    def e(self):
        """
        API for monitoring and controlling RE Environment.
        """
        return self._e

    @property
    def r(self):
        """
        API for monitoring and controlling Run Engine.
        """
        return self._r
