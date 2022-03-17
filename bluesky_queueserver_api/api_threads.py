import copy
import time as ttime
import threading

from .api_base import API_Base, WaitMonitor
from ._defaults import default_wait_timeout

from .api_docstrings import (
    _doc_api_status,
    _doc_api_ping,
    _doc_api_wait_for_idle,
    _doc_api_wait_for_idle_or_paused,
    _doc_api_item_add,
    _doc_api_item_add_batch,
    _doc_api_item_update,
    _doc_api_item_get,
    _doc_api_item_remove,
    _doc_api_item_remove_batch,
    _doc_api_item_move,
    _doc_api_item_move_batch,
    _doc_api_item_execute,
    _doc_api_queue_start,
    _doc_api_queue_stop,
    _doc_api_queue_stop_cancel,
    _doc_api_queue_clear,
    _doc_api_queue_mode_set,
    _doc_api_queue_get,
    _doc_api_history_get,
    _doc_api_history_clear,
    _doc_api_plans_allowed,
    _doc_api_devices_allowed,
    _doc_api_plans_existing,
    _doc_api_devices_existing,
    _doc_api_permissions_reload,
    _doc_api_permissions_get,
    _doc_api_permissions_set,
    _doc_api_environment_open,
    _doc_api_environment_close,
    _doc_api_environment_destroy,
    _doc_api_script_upload,
    _doc_api_function_execute,
    _doc_api_task_status,
    _doc_api_task_result,
    _doc_api_re_runs,
    _doc_api_re_pause,
    _doc_api_re_resume,
    _doc_api_re_stop,
    _doc_api_re_abort,
    _doc_api_re_halt,
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

        # Attempt to load the updated status
        try:
            self._status(reload=True)
        except Exception:
            pass

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

    def ping(self, *, reload=False):
        # Docstring is maintained separately
        return self.status(reload=reload)

    def wait_for_idle(self, *, timeout=default_wait_timeout, monitor=None):
        # Docstring is maintained separately
        def condition(status):
            return status["manager_state"] == "idle"

        self._wait_for_condition(condition=condition, timeout=timeout, monitor=monitor)

    def wait_for_idle_or_paused(self, *, timeout=default_wait_timeout, monitor=None):
        # Docstring is maintained separately
        def condition(status):
            return status["manager_state"] in ("paused", "idle")

        self._wait_for_condition(condition=condition, timeout=timeout, monitor=monitor)

    # =====================================================================================
    #                 API for monitoring and control of Queue

    def item_add(self, item, *, pos=None, before_uid=None, after_uid=None):
        # Docstring is maintained separately
        request_params = self._prepare_item_add(item=item, pos=pos, before_uid=before_uid, after_uid=after_uid)
        self._clear_status_timestamp()
        return self.send_request(method="queue_item_add", params=request_params)

    def item_add_batch(self, items, *, pos=None, before_uid=None, after_uid=None):
        # Docstring is maintained separately
        request_params = self._prepare_item_add_batch(
            items=items, pos=pos, before_uid=before_uid, after_uid=after_uid
        )
        self._clear_status_timestamp()
        return self.send_request(method="queue_item_add_batch", params=request_params)

    def item_update(self, item, *, replace=None):
        # Docstring is maintained separately
        request_params = self._prepare_item_update(item=item, replace=replace)
        self._clear_status_timestamp()
        return self.send_request(method="queue_item_update", params=request_params)

    def item_remove(self, *, pos=None, uid=None):
        request_params = self._prepare_item_get_remove(pos=pos, uid=uid)
        self._clear_status_timestamp()
        return self.send_request(method="queue_item_remove", params=request_params)

    def item_remove_batch(self, *, uids, ignore_missing=None):
        request_params = self._prepare_item_remove_batch(uids=uids, ignore_missing=ignore_missing)
        self._clear_status_timestamp()
        return self.send_request(method="queue_item_remove_batch", params=request_params)

    def item_move(self, *, pos=None, uid=None, pos_dest=None, before_uid=None, after_uid=None):
        # Docstring is maintained separately
        request_params = self._prepare_item_move(
            pos=pos, uid=uid, pos_dest=pos_dest, before_uid=before_uid, after_uid=after_uid
        )
        self._clear_status_timestamp()
        return self.send_request(method="queue_item_move", params=request_params)

    def item_move_batch(self, *, uids=None, pos_dest=None, before_uid=None, after_uid=None, reorder=None):
        # Docstring is maintained separately
        request_params = self._prepare_item_move_batch(
            uids=uids,
            pos_dest=pos_dest,
            before_uid=before_uid,
            after_uid=after_uid,
            reorder=reorder,
        )
        self._clear_status_timestamp()
        return self.send_request(method="queue_item_move_batch", params=request_params)

    def item_get(self, *, pos=None, uid=None):
        request_params = self._prepare_item_get_remove(pos=pos, uid=uid)
        return self.send_request(method="queue_item_get", params=request_params)

    def item_execute(self, item):
        # Docstring is maintained separately
        request_params = self._prepare_item_execute(item=item)
        self._clear_status_timestamp()
        return self.send_request(method="queue_item_execute", params=request_params)

    def environment_open(self):
        # Docstring is maintained separately
        self._clear_status_timestamp()
        return self.send_request(method="environment_open")

    def environment_close(self):
        # Docstring is maintained separately
        self._clear_status_timestamp()
        return self.send_request(method="environment_close")

    def environment_destroy(self):
        # Docstring is maintained separately
        self._clear_status_timestamp()
        return self.send_request(method="environment_destroy")

    def queue_start(self):
        # Docstring is maintained separately
        self._clear_status_timestamp()
        return self.send_request(method="queue_start")

    def queue_stop(self):
        # Docstring is maintained separately
        self._clear_status_timestamp()
        return self.send_request(method="queue_stop")

    def queue_stop_cancel(self):
        # Docstring is maintained separately
        self._clear_status_timestamp()
        return self.send_request(method="queue_stop_cancel")

    def queue_clear(self):
        # Docstring is maintained separately
        self._clear_status_timestamp()
        return self.send_request(method="queue_clear")

    def queue_mode_set(self, **kwargs):
        # Docstring is maintained separately
        request_params = self._prepare_queue_mode_set(**kwargs)
        self._clear_status_timestamp()
        return self.send_request(method="queue_mode_set", params=request_params)

    def queue_get(self, *, reload=False):
        # Docstring is maintained separately
        status = self._status(reload=reload)
        plan_queue_uid = status["plan_queue_uid"]
        if plan_queue_uid != self._current_plan_queue_uid:
            response = self.send_request(method="queue_get")
            self._process_response_queue_get(response)
        else:
            response = self._generate_response_queue_get()
        return response

    def history_get(self, *, reload=False):
        # Docstring is maintained separately
        status = self._status(reload=reload)
        plan_history_uid = status["plan_history_uid"]
        if plan_history_uid != self._current_plan_history_uid:
            response = self.send_request(method="history_get")
            self._process_response_history_get(response)
        else:
            response = self._generate_response_history_get()
        return response

    def history_clear(self):
        # Docstring is maintained separately
        self._clear_status_timestamp()
        return self.send_request(method="history_clear")

    def plans_allowed(self, *, reload=False):
        # Docstring is maintained separately
        status = self._status(reload=reload)
        plans_allowed_uid = status["plans_allowed_uid"]
        if plans_allowed_uid != self._current_plans_allowed_uid:
            request_params = self._prepare_plans_devices_allowed()
            response = self.send_request(method="plans_allowed", params=request_params)
            self._process_response_plans_allowed(response)
        else:
            response = self._generate_response_plans_allowed()
        return response

    def devices_allowed(self, *, reload=False):
        # Docstring is maintained separately
        status = self._status(reload=reload)
        devices_allowed_uid = status["devices_allowed_uid"]
        if devices_allowed_uid != self._current_devices_allowed_uid:
            request_params = self._prepare_plans_devices_allowed()
            response = self.send_request(method="devices_allowed", params=request_params)
            self._process_response_devices_allowed(response)
        else:
            response = self._generate_response_devices_allowed()
        return response

    def plans_existing(self, *, reload=False):
        # Docstring is maintained separately
        status = self._status(reload=reload)
        plans_existing_uid = status["plans_existing_uid"]
        if plans_existing_uid != self._current_plans_existing_uid:
            response = self.send_request(method="plans_existing")
            self._process_response_plans_existing(response)
        else:
            response = self._generate_response_plans_existing()
        return response

    def devices_existing(self, *, reload=False):
        # Docstring is maintained separately
        status = self._status(reload=reload)
        devices_existing_uid = status["devices_existing_uid"]
        if devices_existing_uid != self._current_devices_existing_uid:
            response = self.send_request(method="devices_existing")
            self._process_response_devices_existing(response)
        else:
            response = self._generate_response_devices_existing()
        return response

    def permissions_reload(self, *, restore_plans_devices=None, restore_permissions=None):
        # Docstring is maintained separately
        request_params = self._prepare_permissions_reload(
            restore_plans_devices=restore_plans_devices, restore_permissions=restore_permissions
        )
        self._clear_status_timestamp()
        return self.send_request(method="permissions_reload", params=request_params)

    def permissions_get(self):
        # Docstring is maintained separately
        return self.send_request(method="permissions_get")

    def permissions_set(self, user_group_permissions):
        # Docstring is maintained separately
        request_params = self._prepare_permissions_set(user_group_permissions=user_group_permissions)
        self._clear_status_timestamp()
        return self.send_request(method="permissions_set", params=request_params)

    def script_upload(self, script, *, update_re=None, run_in_background=None):
        # Docstring is maintained separately
        request_params = self._prepare_script_upload(
            script=script, update_re=update_re, run_in_background=run_in_background
        )
        self._clear_status_timestamp()
        return self.send_request(method="script_upload", params=request_params)

    def function_execute(self, item, *, run_in_background=None):
        # Docstring is maintained separately
        request_params = self._prepare_function_execute(item=item, run_in_background=run_in_background)
        self._clear_status_timestamp()
        return self.send_request(method="function_execute", params=request_params)

    def task_status(self, task_uid):
        # Docstring is maintained separately
        request_params = self._prepare_task_result(task_uid=task_uid)
        return self.send_request(method="task_status", params=request_params)

    def task_result(self, task_uid):
        # Docstring is maintained separately
        request_params = self._prepare_task_result(task_uid=task_uid)
        return self.send_request(method="task_result", params=request_params)

    def re_runs(self, option=None, *, reload=False):
        # Docstring is maintained separately
        self._verify_options_re_runs(option=option)
        status = self._status(reload=reload)
        run_list_uid = status["run_list_uid"]
        if run_list_uid != self._current_run_list_uid:
            response = self.send_request(method="re_runs")
            response = self._process_response_re_runs(response, option=option)
        else:
            response = self._generate_response_re_runs(option=option)
        return response

    def re_pause(self, option=None):
        # Docstring is maintained separately
        request_params = self._prepare_re_pause(option=option)
        self._clear_status_timestamp()
        return self.send_request(method="re_pause", params=request_params)

    def re_resume(self):
        # Docstring is maintained separately
        self._clear_status_timestamp()
        return self.send_request(method="re_resume")

    def re_stop(self):
        # Docstring is maintained separately
        self._clear_status_timestamp()
        return self.send_request(method="re_stop")

    def re_abort(self):
        # Docstring is maintained separately
        self._clear_status_timestamp()
        return self.send_request(method="re_abort")

    def re_halt(self):
        # Docstring is maintained separately
        self._clear_status_timestamp()
        return self.send_request(method="re_halt")

    # =======================================================================================
    #                            Console monitor
    # =======================================================================================


API_Threads_Mixin.status.__doc__ = _doc_api_status
API_Threads_Mixin.ping.__doc__ = _doc_api_ping
API_Threads_Mixin.wait_for_idle.__doc__ = _doc_api_wait_for_idle
API_Threads_Mixin.wait_for_idle_or_paused.__doc__ = _doc_api_wait_for_idle_or_paused
API_Threads_Mixin.item_add.__doc__ = _doc_api_item_add
API_Threads_Mixin.item_add_batch.__doc__ = _doc_api_item_add_batch
API_Threads_Mixin.item_update.__doc__ = _doc_api_item_update
API_Threads_Mixin.item_get.__doc__ = _doc_api_item_get
API_Threads_Mixin.item_remove.__doc__ = _doc_api_item_remove
API_Threads_Mixin.item_remove_batch.__doc__ = _doc_api_item_remove_batch
API_Threads_Mixin.item_move.__doc__ = _doc_api_item_move
API_Threads_Mixin.item_move_batch.__doc__ = _doc_api_item_move_batch
API_Threads_Mixin.item_execute.__doc__ = _doc_api_item_execute
API_Threads_Mixin.queue_start.__doc__ = _doc_api_queue_start
API_Threads_Mixin.queue_stop.__doc__ = _doc_api_queue_stop
API_Threads_Mixin.queue_stop_cancel.__doc__ = _doc_api_queue_stop_cancel
API_Threads_Mixin.queue_clear.__doc__ = _doc_api_queue_clear
API_Threads_Mixin.queue_mode_set.__doc__ = _doc_api_queue_mode_set
API_Threads_Mixin.queue_get.__doc__ = _doc_api_queue_get
API_Threads_Mixin.history_get.__doc__ = _doc_api_history_get
API_Threads_Mixin.history_clear.__doc__ = _doc_api_history_clear
API_Threads_Mixin.plans_allowed.__doc__ = _doc_api_plans_allowed
API_Threads_Mixin.devices_allowed.__doc__ = _doc_api_devices_allowed
API_Threads_Mixin.plans_existing.__doc__ = _doc_api_plans_existing
API_Threads_Mixin.devices_existing.__doc__ = _doc_api_devices_existing
API_Threads_Mixin.permissions_reload.__doc__ = _doc_api_permissions_reload
API_Threads_Mixin.permissions_get.__doc__ = _doc_api_permissions_get
API_Threads_Mixin.permissions_set.__doc__ = _doc_api_permissions_set
API_Threads_Mixin.environment_open.__doc__ = _doc_api_environment_open
API_Threads_Mixin.environment_close.__doc__ = _doc_api_environment_close
API_Threads_Mixin.environment_destroy.__doc__ = _doc_api_environment_destroy
API_Threads_Mixin.script_upload.__doc__ = _doc_api_script_upload
API_Threads_Mixin.function_execute.__doc__ = _doc_api_function_execute
API_Threads_Mixin.task_status.__doc__ = _doc_api_task_status
API_Threads_Mixin.task_result.__doc__ = _doc_api_task_result
API_Threads_Mixin.re_runs.__doc__ = _doc_api_re_runs
API_Threads_Mixin.re_pause.__doc__ = _doc_api_re_pause
API_Threads_Mixin.re_resume.__doc__ = _doc_api_re_resume
API_Threads_Mixin.re_stop.__doc__ = _doc_api_re_stop
API_Threads_Mixin.re_abort.__doc__ = _doc_api_re_abort
API_Threads_Mixin.re_halt.__doc__ = _doc_api_re_halt
