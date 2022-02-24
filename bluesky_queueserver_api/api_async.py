import asyncio
import copy
import time as ttime

from .api_base import API_Base, WaitMonitor
from ._defaults import default_wait_timeout

from .api_docstrings import (
    _doc_api_status,
    _doc_api_wait_for_idle,
    _doc_api_item_add,
    _doc_api_item_get,
    _doc_api_queue_start,
    _doc_api_environment_open,
    _doc_api_environment_close,
    _doc_api_environment_destroy,
)


class API_Async_Mixin(API_Base):
    def __init__(self, *, status_expiration_period, status_polling_period):
        super().__init__(
            status_expiration_period=status_expiration_period, status_polling_period=status_polling_period
        )

        self._is_closing = False

        self._event_status_get = asyncio.Event()
        self._status_get_cb = []  # A list of callbacks
        self._status_get_cb_lock = asyncio.Lock()
        self._wait_cb = []

        # Use tasks instead of threads
        self._task_status_get = asyncio.create_task(self._task_status_get_func())
        self._task_status_get = asyncio.create_task(self._task_status_poll_func())

    async def _event_wait(self, event, timeout):
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
            load_status = await self._event_wait(self._event_status_get, timeout=0.1)
            if load_status:
                if self._status_timestamp:
                    dt = ttime.time() - self._status_timestamp
                    dt = dt if (dt >= 0) else None
                else:
                    dt = None

                if (dt is None) or (dt > self._status_expiration_period):
                    status, raised_exception = None, None
                    try:
                        status = await self._load_status()
                    except Exception as ex:
                        raised_exception = ex

                    if status is not None:
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
        monitor._time_start = t_started
        monitor.set_timeout(timeout)

        event = asyncio.Event()

        def cb(status):
            nonlocal timeout_occurred, wait_cancelled, event, monitor
            result = condition(status) if status else False
            monitor._time_elapsed = ttime.time() - monitor.time_start

            if not result and (monitor.time_elapsed > monitor.timeout):
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
        # Docstring is maintained separately
        status = await self._status(reload=reload)
        return copy.deepcopy(status)  # Returns copy

    async def wait_for_idle(self, *, timeout=default_wait_timeout, monitor=None):
        # Docstring is maintained separately

        def condition(status):
            return status["manager_state"] == "idle"

        await self._wait_for_condition(condition=condition, timeout=timeout, monitor=monitor)

    # =====================================================================================
    #                 API for monitoring and control of Queue

    async def item_add(self, item, *, pos=None, before_uid=None, after_uid=None):
        # Docstring is maintained separately
        request_params = self._prepare_item_add(item=item, pos=pos, before_uid=before_uid, after_uid=after_uid)
        self._clear_status_timestamp()
        return await self.send_request(method="queue_item_add", params=request_params)

    async def item_get(self, *, pos=None, uid=None):
        request_params = self._prepare_item_get(pos=pos, uid=uid)
        return await self.send_request(method="queue_item_get", params=request_params)

    async def environment_open(self):
        self._clear_status_timestamp()
        return await self.send_request(method="environment_open")

    async def environment_close(self):
        self._clear_status_timestamp()
        return await self.send_request(method="environment_close")

    async def environment_destroy(self):
        self._clear_status_timestamp()
        return await self.send_request(method="environment_destroy")

    async def queue_start(self):
        self._clear_status_timestamp()
        return await self.send_request(method="queue_start")


API_Async_Mixin.status.__doc__ = _doc_api_status
API_Async_Mixin.wait_for_idle.__doc__ = _doc_api_wait_for_idle
API_Async_Mixin.item_add.__doc__ = _doc_api_item_add
API_Async_Mixin.item_get.__doc__ = _doc_api_item_get
API_Async_Mixin.queue_start.__doc__ = _doc_api_queue_start
API_Async_Mixin.environment_open.__doc__ = _doc_api_environment_open
API_Async_Mixin.environment_close.__doc__ = _doc_api_environment_close
API_Async_Mixin.environment_destroy.__doc__ = _doc_api_environment_destroy
