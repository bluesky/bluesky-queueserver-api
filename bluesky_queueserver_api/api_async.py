import asyncio
import copy
import time as ttime

from .api_base import API_Base, WaitMonitor
from ._defaults import default_wait_timeout

from .api_docstrings import _doc_api_status


class API_Async_Mixin(API_Base):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self._is_closing = False

        self._status_timestamp = None
        self._status_current = None
        self._status_exception = None

        self._event_status_get = asyncio.Event()
        self._status_get_cb = []  # A list of callbacks
        self._status_get_cb_lock = asyncio.Lock()
        self._wait_cb = []

        # Use tasks instead of threads
        self._task_status_get = asyncio.create_task(self._thread_status_get_func, name="RM API: status get")
        self._task_status_get = asyncio.create_task(self._thread_status_poll_func, name="RE API: status poll")

    async def _event_wait(event, timeout):
        """
        Emulation of ``threading.Event.wait`` with timeout.
        """
        try:
            await asyncio.wait_for(event.wait(), timeout)
            return True
        except asyncio.TimeoutError:
            return False

    async def _task_status_get_func(self):
        """
        The coroutine is run as a background task (not awaited). It periodically checks if
        ``self._event_status_get`` is set. If the event is set, then the function loads
        (if needed) and processes RE Manager status.
        """
        while True:
            load_status = self._event_wait(self._event_status_get, timeout=0.1)
            if load_status:
                dt = ttime.time() - self._status_timestamp if self._status_timestamp else 0
                # Reload status from server only if it was not requested within some
                #   preset minimum period or if it was not requested for a very long time.
                #   The latter case may happen if system time is changed and should be
                #   taken into account (otherwise API may get stuck).
                if (dt < self._status_min_period) or (dt > 5):
                    status, raised_exception = None, None
                    try:
                        status = await self._load_status()
                    except Exception as ex:
                        raised_exception = ex

                    self._status_timestamp = ttime.time()

                    self._status_current = status
                    self._status_exception = raised_exception

                async with self._status_get_cb_lock:
                    # Call each 'status_get' callback with current status/exception
                    for cb in self._status_get_cb:
                        cb(self._status_current, self._status_exception)
                    self._status_get_cb.clear()

                    # Update 'wait' callbacks. Even if the status is not reloaded,
                    #   the callbacks still check if there are timeouts.
                    n_cb = 0  # The number of wait callbacks
                    for cb in self._wait_cb.copy():
                        if cb(self._status_current):
                            self._wait_cb.pop(n_cb)
                        else:
                            n_cb += 1

                self._event_status_get.clear()

            if self._is_closing:
                break

    async def _task_status_poll_func(self):
        while True:
            await asyncio.sleep(self._status_polling_period)

            async with self._status_get_cb_lock:
                if len(self._wait_cb):
                    self._event_status_get.set()

            if self._is_closing:
                break

    async def _load_status(self):
        """
        Returns status of RE Manager.
        """
        return await self.send_request(method="status")

    async def _wait_for_condition(self, *, condition, timeout, monitor):
        """
        Blocking function, which is waiting for the returned status to satisfy
        the specified conditions. The function is raises ``WaitTimeoutError``
        if timeout occurs. The ``timeout`` parameter is mandatory, but could be
        set to a very large value if needed.

        Parameters
        ----------
        condition: callable
           Condition is a function (any callable), which is waiting for the returned
           status to satisfy certain fixed set of conditions. For example, the function
           which waits for the manager status to become idle:

           .. code-block:: python

                def condition(status):
                    return (status["manager_state"] == "idle")

        timeout: float
            timeout in seconds
        """

        timeout_occurred = False
        wait_cancelled = False
        t_started = ttime.time()

        monitor = monitor or WaitMonitor()
        monitor.set_time_start(t_started)
        monitor.set_timeout_period(timeout)

        event = asyncio.Event()

        def cb(status):
            nonlocal timeout_occurred, wait_cancelled, event, monitor
            result = condition(status) if status else False
            monitor.set_time_elapsed(ttime.time() - monitor.time_start)

            if not result and (monitor.time_elapsed > monitor.timeout_period):
                timeout_occurred = True
                result = True
            elif monitor.is_cancelled:
                wait_cancelled = True
                result = True

            if result:
                event.set()

            return result

        try:
            async with self._status_get_cb_lock:
                self._wait_cb.append(cb)

            await event.wait()
        finally:
            # Remove the callback if it is still in the list. This will remove the
            #   callback if the execution is interrupted with Ctrl-C (in IPython).
            async with self._status_get_cb_lock:
                try:
                    n = self._wait_cb.index(cb)
                    self._wait_cb.pop(n)
                except Exception:
                    pass

        if timeout_occurred:
            raise self.WaitTimeoutError("Timeout while waiting for condition")
        if wait_cancelled:
            raise self.WaitCancelError("Wait for condition was cancelled")

    async def _status(self, *, reload=False):
        """
        Load status of RE Manager. The function returns status or raises exception if
        operation failed (e.g. timeout occurred). This is not part of API.

        The function is thread-safe. It is assumed that status may be simultaneously
        requested from multiple threads. The mechanism for loading and updating
        status information is designed to reuse previously loaded data whenever possible
        prevents communication channel and the server from overload in case
        many requests are sent in rapid sequence.

        Parameters
        ----------
        reload: boolean
            Immediately reload status (``True``) or return cached status if it
            is not expired (``False``).

        Returns
        -------
        dict
            Reference to the dictionary with RE Manager status

        Raises
        ------
            Reraises the exceptions raised by ``send_request`` API.
        """
        _status, _ex = None, None
        event = asyncio.Event()

        def cb(status, ex):
            nonlocal _status, _ex, event
            _status, _ex = status, ex
            event.set()

        async with self._status_get_cb_lock:
            self._status_get_cb.append(cb)
            if reload:
                self._status_timestamp = None
            self._event_status_get.set()

        await event.wait()
        if _ex:
            raise _ex
        else:
            return _status

    def _close_api(self):
        self._is_closing = True  # Exit all tasks

    def __del__(self):
        self._close_api()

    # =====================================================================================
    #                 API for monitoring and control of RE Manager

    async def status(self, *, reload=False):
        """
        Load status of RE Manager. The function returns status or raises exception if
        operation failed (e.g. timeout occurred).

        Parameters
        ----------
        reload: boolean
            Immediately reload status (``True``) or return cached status if it
            is not expired (``False``).

        Returns
        -------
        dict
            Copy of the dictionary with RE Manager status.

        Raises
        ------
            Reraises the exceptions raised by ``send_request`` API.
        """
        status = await self._status(reload=reload)
        return copy.deepcopy(status)  # Returns copy

    async def wait_for_idle(self, *, timeout=default_wait_timeout, monitor=None):
        """
        The function raises ``WaitTimeoutError`` if timeout occurs or
        ``WaitCancelError`` if wait operation was cancelled by ``monitor.cancel()``.
        """

        def condition(status):
            return status["manager_state"] == "idle"

        self._wait_for_condition(condition=condition, timeout=timeout, monitor=monitor)

    # =====================================================================================
    #                 API for monitoring and control of Queue

    async def add_item(self, item, *, pos=None, before_uid=None, after_uid=None):
        request_params = self._prepare_add_item(item=item, pos=pos, before_uid=before_uid, after_uid=after_uid)
        return await self._rm.send_request(method="queue_item_add", params=request_params)


API_Async_Mixin.status.__doc__ = _doc_api_status
