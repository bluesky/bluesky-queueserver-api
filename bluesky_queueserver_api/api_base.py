from .item import BItem
from collections.abc import Mapping


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

        self._current_queue = []
        self._current_queue_uid = None
        self._current_history = []
        self._current_history_uid = None

    def _clear_status_timestamp(self):
        """
        Clearing status timestamp causes status to be reloaded from the server next time it is requested.
        """
        self._status_timestamp = None

    def _prepare_item_add(self, *, item, pos, before_uid, after_uid):
        """
        Prepare parameters for ``item_add`` operation.
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

    def _prepare_item_get(self, *, pos, uid):
        """
        Prepare parameters for ``item_get`` operation
        """
        request_params = {}
        if pos:
            request_params["pos"] = pos
        if uid:
            request_params["uid"] = uid
        return request_params
