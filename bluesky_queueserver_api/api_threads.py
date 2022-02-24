import copy
import time as ttime
import threading

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


class API_Threads_Mixin(API_Base):
    def __init__(self, *, status_expiration_period, status_polling_period):
        super().__init__(
            status_expiration_period=status_expiration_period, status_polling_period=status_polling_period
        )

        self._is_closing = False

        self._event_status_get = threading.Event()
        self._status_get_cb = []  # A list of callbacks for requests to get status
        self._wait_cb = []  # A list of callbacks for 'wait' API

        self._status_get_cb_lock = threading.Lock()
        self._thread_status_get = threading.Thread(
            name="RM API: status get", target=self._thread_status_get_func, daemon=True
        )
        self._thread_status_get.start()

        self._thread_status_poll = threading.Thread(
            name="RE API: status poll", target=self._thread_status_poll_func, daemon=True
        )
        self._thread_status_poll.start()

    def _thread_status_get_func(self):
        """
        The function is run in a separate thread. It periodically checks if ``self._event_status_get``
        is set. If the event is set, then the function loads (if needed) and processes RE Manager status.
        """
        while True:
            load_status = self._event_status_get.wait(timeout=0.1)
            if load_status:
                if self._status_timestamp:
                    dt = ttime.time() - self._status_timestamp
                    dt = dt if (dt >= 0) else None
                else:
                    dt = None

                if (dt is None) or (dt > self._status_expiration_period):
                    status, raised_exception = None, None
                    try:
                        status = self._load_status()
                    except Exception as ex:
                        raised_exception = ex

                    if status is not None:
                        self._status_timestamp = ttime.time()

                    self._status_current = status
                    self._status_exception = raised_exception

                with self._status_get_cb_lock:
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

    def _thread_status_poll_func(self):
        while True:
            ttime.sleep(self._status_polling_period)

            with self._status_get_cb_lock:
                if len(self._wait_cb):
                    self._event_status_get.set()

            if self._is_closing:
                break

    def _load_status(self):
        """
        Returns status of RE Manager.
        """
        return self.send_request(method="status")

    def _wait_for_condition(self, *, condition, timeout, monitor):
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

        event = threading.Event()

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
            with self._status_get_cb_lock:
                self._wait_cb.append(cb)

            event.wait()
        finally:
            # Remove the callback if it is still in the list. This will remove the
            #   callback if the execution is interrupted with Ctrl-C (in IPython).
            with self._status_get_cb_lock:
                try:
                    n = self._wait_cb.index(cb)
                    self._wait_cb.pop(n)
                except Exception:
                    pass

        self._status(reload=True)  # Load the updated status

        if timeout_occurred:
            raise self.WaitTimeoutError("Timeout while waiting for condition")
        if wait_cancelled:
            raise self.WaitCancelError("Wait for condition was cancelled")

    def _status(self, *, reload=False):
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
        event = threading.Event()

        def cb(status, ex):
            nonlocal _status, _ex, event
            _status, _ex = status, ex
            event.set()

        with self._status_get_cb_lock:
            self._status_get_cb.append(cb)
            if reload:
                self._clear_status_timestamp()
            self._event_status_get.set()

        event.wait()
        if _ex:
            raise _ex
        else:
            return _status

    def _close_api(self):
        self._is_closing = True  # Exit all daemon threads

    def __del__(self):
        self._close_api()

    # =====================================================================================
    #                 API for monitoring and control of RE Manager

    def status(self, *, reload=False):
        # Docstring is maintained separately
        status = self._status(reload=reload)
        return copy.deepcopy(status)  # Returns copy

    def wait_for_idle(self, *, timeout=default_wait_timeout, monitor=None):
        # Docstring is maintained separately
        def condition(status):
            return status["manager_state"] == "idle"

        self._wait_for_condition(condition=condition, timeout=timeout, monitor=monitor)

    # =====================================================================================
    #                 API for monitoring and control of Queue

    def item_add(self, item, *, pos=None, before_uid=None, after_uid=None):
        # Docstring is maintained separately
        request_params = self._prepare_item_add(item=item, pos=pos, before_uid=before_uid, after_uid=after_uid)
        self._clear_status_timestamp()
        return self.send_request(method="queue_item_add", params=request_params)

    def item_get(self, *, pos=None, uid=None):
        request_params = self._prepare_item_get(pos=pos, uid=uid)
        return self.send_request(method="queue_item_get", params=request_params)

    def environment_open(self):
        self._clear_status_timestamp()
        return self.send_request(method="environment_open")

    def environment_close(self):
        self._clear_status_timestamp()
        return self.send_request(method="environment_close")

    def environment_destroy(self):
        self._clear_status_timestamp()
        return self.send_request(method="environment_destroy")

    def queue_start(self):
        self._clear_status_timestamp()
        return self.send_request(method="queue_start")


API_Threads_Mixin.status.__doc__ = _doc_api_status
API_Threads_Mixin.wait_for_idle.__doc__ = _doc_api_wait_for_idle
API_Threads_Mixin.item_add.__doc__ = _doc_api_item_add
API_Threads_Mixin.item_get.__doc__ = _doc_api_item_get
API_Threads_Mixin.queue_start.__doc__ = _doc_api_queue_start
API_Threads_Mixin.environment_open.__doc__ = _doc_api_environment_open
API_Threads_Mixin.environment_close.__doc__ = _doc_api_environment_close
API_Threads_Mixin.environment_destroy.__doc__ = _doc_api_environment_destroy
