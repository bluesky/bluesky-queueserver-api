from .item import BItem
from collections.abc import Mapping, Iterable
import copy


class WaitTimeoutError(TimeoutError):
    ...


class WaitCancelError(TimeoutError):
    ...


class WaitMonitor:
    """
    Creates ``monitor`` object for 'wait' operations, such as ``wait_for_idle``.
    The object may be used to stop the operation from another thread or
    asynchronous task.

    Examples
    --------

    The examples illustrate how to use ``WaitMonitor`` object to cancel
    wait operations. Synchronous code (0MQ or HTTP):

    .. code-block:: python

        # Synchronous code
        from bluesky_queueserver_api import Wait Monitor
        from bluesky_queueserver_api.zmq import REManagerAPI()  # Same for HTTP
        import time
        import threading

        RM = REManagerAPI()
        monitor = WaitMonitor()

        def wait_re_manager_idle():
            try:
                print("Waiting ...")
                RM.wait_for_idle(monitor=monitor)
            except RM.WaitCancelError:
                print("Cancelled.")
            except RM.WaitTimeoutError:
                print("Timeout.")
            print("RE Manager is idle")

        # Wait until RE Manager is in 'idle' state in a background thread
        thread = threading.Thread(target=wait_re_manager_idle)
        thread.start()
        # Cancel wait after 2 seconds from main thread
        time.sleep(2)
        monitor.cancel()

        thread.join()
        RM.close()

    Asynchronous code example (0MQ or HTTP):

    .. code-block:: python

        # Asynchronous code
        import asyncio
        from bluesky_queueserver_api import Wait Monitor
        from bluesky_queueserver_api.zmq.aio import REManagerAPI()  # Same for HTTP
        import time

        async def testing():

            RM = REManagerAPI()
            monitor = WaitMonitor()

            async def wait_re_manager_idle():
                try:
                    print("Waiting ...")
                    await RM.wait_for_idle(monitor=monitor)
                except RM.WaitCancelError:
                    print("Cancelled.")
                except RM.WaitTimeoutError:
                    print("Timeout.")
                print("RE Manager is idle")

            # Wait until RE Manager is in 'idle' state in a background task
            asyncio.create_task(wait_re_manager_idle())
            # Cancel wait after 2 seconds from main thread
            await asyncio.sleep(2)
            monitor.cancel()
            await asyncio.sleep(0.5)  # Let the task to complete
            await RM.close()

        asyncio.run(testing())
    """

    def __init__(self):
        self._time_start = 0
        self._time_elapsed = 0
        self._timeout = 0
        self._cancel_callbacks = []

        self._wait_cancelled = False

    @property
    def time_start(self):
        """
        Time when the operation started (seconds).
        """
        return self._time_start

    @property
    def time_elapsed(self):
        """
        Time since the operation started (seconds).
        """
        return self._time_elapsed

    @property
    def timeout(self):
        """
        Timeout (seconds).
        """
        return self._timeout

    def set_timeout(self, timeout):
        """
        Modify timeout for the current operation (seconds).
        """
        self._timeout = timeout

    def add_cancel_callback(self, cancel_callback):
        """
        Each callbacks is called only once before the operation is cancelled.
        Callback function should accept no parameters.
        """
        self._cancel_callbacks.append(cancel_callback)

    def cancel(self):
        """
        Cancel the currently running operation. A monitor may be cancelled
        only once per lifecycle.
        """
        for cb in self._cancel_callbacks:
            try:
                cb()
            except Exception:
                pass

        self._cancel_callbacks = []
        self._wait_cancelled = True

    @property
    def is_cancelled(self):
        """
        Checks if the monitor was cancelled. The operation is either completed
        or about to be completed.
        """
        return self._wait_cancelled


class API_Base:
    WaitTimeoutError = WaitTimeoutError
    WaitCancelError = WaitCancelError

    def __init__(self, *, status_expiration_period, status_polling_period):

        self._status_expiration_period = status_expiration_period  # seconds
        self._status_polling_period = status_polling_period  # seconds

        self._status_timestamp = None
        self._status_current = None
        self._status_exception = None

        self._user = "Python API User"
        self._user_group = "admin"

        self._current_plan_queue = []
        self._current_running_item = {}
        self._current_plan_queue_uid = None
        self._current_plan_history = []
        self._current_plan_history_uid = None
        self._current_plans_allowed = {}
        self._current_plans_allowed_uid = None
        self._current_devices_allowed = {}
        self._current_devices_allowed_uid = None
        self._current_plans_existing = {}
        self._current_plans_existing_uid = None
        self._current_devices_existing = {}
        self._current_devices_existing_uid = None

    def _clear_status_timestamp(self):
        """
        Clearing status timestamp causes status to be reloaded from the server next time it is requested.
        """
        self._status_timestamp = None

    def _request_params_add_user_info(self, request_params):
        if self._pass_user_info:
            request_params["user"] = self._user
            request_params["user_group"] = self._user_group

    def _add_request_param(self, request_params, name, value):
        """
        Add parameter to dictionary ``request_params`` if value is not ``None``.
        """
        if value is not None:
            request_params[name] = value

    def _prepare_item_add(self, *, item, pos, before_uid, after_uid):
        """
        Prepare parameters for ``item_add`` operation.
        """
        if not isinstance(item, BItem) and not isinstance(item, Mapping):
            raise TypeError(f"Incorrect item type {type(item)!r}. Expected type: 'BItem' or 'dict'")

        item = item.to_dict() if isinstance(item, BItem) else dict(item).copy()

        request_params = {"item": item}
        self._add_request_param(request_params, "pos", pos)
        self._add_request_param(request_params, "before_uid", before_uid)
        self._add_request_param(request_params, "after_uid", after_uid)
        self._request_params_add_user_info(request_params)
        return request_params

    def _prepare_item_add_batch(self, *, items, pos, before_uid, after_uid):
        """
        Prepare parameters for ``item_add_batch`` operation.
        """
        if not isinstance(items, Iterable):
            raise TypeError(f"Parameter ``items`` must be iterable: type(items)={type(items)!r}")

        for n, item in enumerate(items):
            if not isinstance(item, BItem) and not isinstance(item, Mapping):
                raise TypeError(
                    f"Incorrect type {type(item)!r} if item #{n} ({item!r}). Expected type: 'BItem' or 'dict'"
                )

        items = [_.to_dict() if isinstance(_, BItem) else dict(_).copy() for _ in items]

        request_params = {"items": items}
        self._add_request_param(request_params, "pos", pos)
        self._add_request_param(request_params, "before_uid", before_uid)
        self._add_request_param(request_params, "after_uid", after_uid)
        self._request_params_add_user_info(request_params)
        return request_params

    def _prepare_item_update(self, *, item, replace):
        """
        Prepare parameters for ``item_update`` operation.
        """
        if not isinstance(item, BItem) and not isinstance(item, Mapping):
            raise TypeError(f"Incorrect item type {type(item)!r}. Expected type: 'BItem' or 'dict'")

        item = item.to_dict() if isinstance(item, BItem) else dict(item).copy()

        request_params = {"item": item}
        self._add_request_param(request_params, "replace", replace)
        self._request_params_add_user_info(request_params)
        return request_params

    def _prepare_item_move(self, *, pos, uid, pos_dest, before_uid, after_uid):
        """
        Prepare parameters for ``item_add`` operation.
        """
        request_params = {}
        self._add_request_param(request_params, "pos", pos)
        self._add_request_param(request_params, "uid", uid)
        self._add_request_param(request_params, "pos_dest", pos_dest)
        self._add_request_param(request_params, "before_uid", before_uid)
        self._add_request_param(request_params, "after_uid", after_uid)

        return request_params

    def _prepare_item_move_batch(self, *, uids, pos_dest, before_uid, after_uid, reorder):
        """
        Prepare parameters for ``item_add`` operation.
        """
        request_params = {}
        self._add_request_param(request_params, "uids", uids)
        self._add_request_param(request_params, "pos_dest", pos_dest)
        self._add_request_param(request_params, "before_uid", before_uid)
        self._add_request_param(request_params, "after_uid", after_uid)
        self._add_request_param(request_params, "reorder", reorder)

        return request_params

    def _prepare_item_get_remove(self, *, pos, uid):
        """
        Prepare parameters for ``item_get`` and ``item_remove`` operation
        """
        request_params = {}
        self._add_request_param(request_params, "pos", pos)
        self._add_request_param(request_params, "uid", uid)
        return request_params

    def _prepare_item_remove_batch(self, *, uids, ignore_missing):
        """
        Prepare parameters for ``item_remove_batch`` operation
        """
        request_params = {"uids": uids}
        self._add_request_param(request_params, "ignore_missing", ignore_missing)
        return request_params

    def _prepare_item_execute(self, *, item):
        """
        Prepare parameters for ``item_execute`` operation.
        """
        if not isinstance(item, BItem) and not isinstance(item, Mapping):
            raise TypeError(f"Incorrect item type {type(item)!r}. Expected type: 'BItem' or 'dict'")

        item = item.to_dict() if isinstance(item, BItem) else dict(item).copy()

        request_params = {"item": item}
        self._request_params_add_user_info(request_params)
        return request_params

    def _prepare_queue_mode_set(self, **kwargs):
        """
        Prepare parameters for ``queue_mode_set`` operation.
        """
        if "mode" in kwargs:
            request_params = {"mode": kwargs["mode"]}
        else:
            request_params = {"mode": kwargs}
        return request_params

    def _process_response_queue_get(self, response):
        """
        ``queue_get``: process response
        """
        if response["success"] is True:
            self._current_plan_queue = copy.deepcopy(response["items"])
            self._current_running_item = copy.deepcopy(response["running_item"])
            self._current_plan_queue_uid = copy.deepcopy(response["plan_queue_uid"])

    def _generate_response_queue_get(self):
        """
        ``queue_get``: generate response based on cached data
        """
        response = {
            "success": True,
            "msg": "",
            "plan_queue_uid": self._current_plan_queue_uid,
            "running_item": copy.deepcopy(self._current_running_item),
            "items": copy.deepcopy(self._current_plan_queue),
        }
        return response

    def _process_response_history_get(self, response):
        """
        ``history_get``: process response
        """
        if response["success"] is True:
            self._current_plan_history = copy.deepcopy(response["items"])
            self._current_plan_history_uid = copy.deepcopy(response["plan_history_uid"])

    def _generate_response_history_get(self):
        """
        ``history_get``: generate response based on cached data
        """
        response = {
            "success": True,
            "msg": "",
            "plan_history_uid": self._current_plan_history_uid,
            "items": copy.deepcopy(self._current_plan_history),
        }
        return response

    def _prepare_plans_devices_allowed(self):
        """
        Prepare parameters for ``plans_allowed`` and ``devices_allowed`` operation.
        """
        request_params = {}
        self._request_params_add_user_info(request_params)

        # User name should not be includedin the request
        if "user" in request_params:
            del request_params["user"]

        return request_params

    def _process_response_plans_allowed(self, response):
        """
        ``plans_allowed``: process response
        """
        if response["success"] is True:
            self._current_plans_allowed = copy.deepcopy(response["plans_allowed"])
            self._current_plans_allowed_uid = copy.deepcopy(response["plans_allowed_uid"])

    def _generate_response_plans_allowed(self):
        """
        ``plans_allowed``: generate response based on cached data
        """
        response = {
            "success": True,
            "msg": "",
            "plans_allowed_uid": self._current_plans_allowed_uid,
            "plans_allowed": copy.deepcopy(self._current_plans_allowed),
        }
        return response

    def _process_response_devices_allowed(self, response):
        """
        ``devices_allowed``: process response
        """
        if response["success"] is True:
            self._current_devices_allowed = copy.deepcopy(response["devices_allowed"])
            self._current_devices_allowed_uid = copy.deepcopy(response["devices_allowed_uid"])

    def _generate_response_devices_allowed(self):
        """
        ``devices_allowed``: generate response based on cached data
        """
        response = {
            "success": True,
            "msg": "",
            "devices_allowed_uid": self._current_devices_allowed_uid,
            "devices_allowed": copy.deepcopy(self._current_devices_allowed),
        }
        return response
