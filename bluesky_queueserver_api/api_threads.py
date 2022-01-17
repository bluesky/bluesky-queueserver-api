from .api_base import API_Base, QueueBase, HistoryBase, ManagerBase, EnvironmentBase, RunEngineBase
import time as ttime
import threading


class QueueThreads(QueueBase):
    def add_item(self, item, *, pos=None, before_uid=None, after_uid=None):
        request_params = self._prepare_add_item(item=item, pos=pos, before_uid=before_uid, after_uid=after_uid)
        return self._rm.send_request(method="queue_item_add", params=request_params)


class HistoryThreads(HistoryBase):
    ...


class ManagerThreads(ManagerBase):
    def status(self, *, reload=False):
        return self._rm._status(reload=reload)

    def wait_for_idle(self, *, timeout=600):
        """
        The function raises ``WaitTimeoutError`` if timeout occurs.
        """

        def condition(status):
            return status["manager_state"] == "idle"

        self._rm._wait_for_condition(condition=condition, timeout=timeout)


class EnvironmentThreads(EnvironmentBase):
    ...


class RunEngineThreads(RunEngineBase):
    ...


class API_Threads_Mixin(API_Base):
    def __init__(self):
        super().__init__(
            queue_type=QueueThreads,
            history_type=HistoryThreads,
            manager_type=ManagerThreads,
            environment_type=EnvironmentThreads,
            run_engine_type=RunEngineThreads,
        )

        self._status_min_period = 0.5  # s
        self._status_poll_period = 1.0  # s

        self._is_closing = False

        self._status_timestamp = None
        self._status_current = None
        self._status_exception = None

        self._event_status_get = threading.Event()
        self._status_get_cb = []  # A list of callbacks
        self._status_get_cb_lock = threading.Lock()
        self._thread_status_get = threading.Thread(
            name="RM API: status get", target=self._thread_status_get_func, daemon=True
        )
        self._thread_status_get.start()

        self._wait_cb = []  #
        self._thread_status_poll = threading.Thread(
            name="RE API: status poll", target=self._thread_status_poll_func, daemon=True
        )
        self._thread_status_poll.start()

    def _thread_status_get_func(self):
        while True:
            load_status = self._event_status_get.wait(timeout=0.1)
            if load_status:
                dt = ttime.time() - self._status_timestamp if self._status_timestamp else 0
                # Reload status from server only if it was not requested within some
                #   preset minimum period or if it was not requested for a very long time.
                #   The latter case may happen if system time is changed and should be
                #   taken into account (otherwise API may get stuck).
                if (dt < self._status_min_period) or (dt > 5):
                    status, raised_exception = None, None
                    try:
                        status = self._load_status()
                    except Exception as ex:
                        raised_exception = ex

                    self._status_timestamp = ttime.time()

                    self._status_current = status
                    self._status_exception = raised_exception

                with self._status_get_cb_lock:
                    for cb in self._status_get_cb:
                        cb(self._status_current, self._status_exception)
                    self._status_get_cb.clear()

                    n_cb = 0
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
            ttime.sleep(self._status_poll_period)

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

    def _wait_for_condition(self, *, condition, timeout):
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
        t_started = ttime.time()

        event = threading.Event()

        def cb(status):
            nonlocal timeout_occurred, event, t_started
            result = condition(status) if status else False
            if not result and (ttime.time() - t_started > timeout):
                timeout_occurred = True
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

        if timeout_occurred:
            raise self.WaitTimeoutError("Timeout while waiting for condition")

    def _status(self, *, reload=False):
        _status, _ex = None, None
        event = threading.Event()

        def cb(status, ex):
            nonlocal _status, _ex, event
            _status, _ex = status, ex
            event.set()

        with self._status_get_cb_lock:
            self._status_get_cb.append(cb)
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
