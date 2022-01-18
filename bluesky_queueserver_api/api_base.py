from .item import BItem
from collections.abc import Mapping


class WaitTimeoutError(TimeoutError):
    ...


class API_Base:
    WaitTimeoutError = WaitTimeoutError

    def __init__(self):
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
