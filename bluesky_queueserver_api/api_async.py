import asyncio
import copy
import time as ttime

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

        # Attempt to load the updated status
        try:
            await self._status(reload=True)
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

    async def ping(self, *, reload=False):
        # Docstring is maintained separately
        return await self.status(reload=reload)

    async def wait_for_idle(self, *, timeout=default_wait_timeout, monitor=None):
        # Docstring is maintained separately

        def condition(status):
            return status["manager_state"] == "idle"

        await self._wait_for_condition(condition=condition, timeout=timeout, monitor=monitor)

    async def wait_for_idle_or_paused(self, *, timeout=default_wait_timeout, monitor=None):
        # Docstring is maintained separately
        def condition(status):
            return status["manager_state"] in ("paused", "idle")

        await self._wait_for_condition(condition=condition, timeout=timeout, monitor=monitor)

    # =====================================================================================
    #                 API for monitoring and control of Queue

    async def item_add(self, item, *, pos=None, before_uid=None, after_uid=None):
        # Docstring is maintained separately
        request_params = self._prepare_item_add(item=item, pos=pos, before_uid=before_uid, after_uid=after_uid)
        self._clear_status_timestamp()
        return await self.send_request(method="queue_item_add", params=request_params)

    async def item_add_batch(self, items, *, pos=None, before_uid=None, after_uid=None):
        # Docstring is maintained separately
        request_params = self._prepare_item_add_batch(
            items=items, pos=pos, before_uid=before_uid, after_uid=after_uid
        )
        self._clear_status_timestamp()
        return await self.send_request(method="queue_item_add_batch", params=request_params)

    async def item_update(self, item, *, replace=None):
        # Docstring is maintained separately
        request_params = self._prepare_item_update(item=item, replace=replace)
        self._clear_status_timestamp()
        return await self.send_request(method="queue_item_update", params=request_params)

    async def item_remove(self, *, pos=None, uid=None):
        request_params = self._prepare_item_get_remove(pos=pos, uid=uid)
        self._clear_status_timestamp()
        return await self.send_request(method="queue_item_remove", params=request_params)

    async def item_remove_batch(self, *, uids, ignore_missing=None):
        request_params = self._prepare_item_remove_batch(uids=uids, ignore_missing=ignore_missing)
        self._clear_status_timestamp()
        return await self.send_request(method="queue_item_remove_batch", params=request_params)

    async def item_move(self, *, pos=None, uid=None, pos_dest=None, before_uid=None, after_uid=None):
        # Docstring is maintained separately
        request_params = self._prepare_item_move(
            pos=pos, uid=uid, pos_dest=pos_dest, before_uid=before_uid, after_uid=after_uid
        )
        self._clear_status_timestamp()
        return await self.send_request(method="queue_item_move", params=request_params)

    async def item_move_batch(self, *, uids=None, pos_dest=None, before_uid=None, after_uid=None, reorder=None):
        # Docstring is maintained separately
        request_params = self._prepare_item_move_batch(
            uids=uids,
            pos_dest=pos_dest,
            before_uid=before_uid,
            after_uid=after_uid,
            reorder=reorder,
        )
        self._clear_status_timestamp()
        return await self.send_request(method="queue_item_move_batch", params=request_params)

    async def item_get(self, *, pos=None, uid=None):
        request_params = self._prepare_item_get_remove(pos=pos, uid=uid)
        return await self.send_request(method="queue_item_get", params=request_params)

    async def item_execute(self, item):
        # Docstring is maintained separately
        request_params = self._prepare_item_execute(item=item)
        self._clear_status_timestamp()
        return await self.send_request(method="queue_item_execute", params=request_params)

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

    async def queue_stop(self):
        self._clear_status_timestamp()
        return await self.send_request(method="queue_stop")

    async def queue_stop_cancel(self):
        self._clear_status_timestamp()
        return await self.send_request(method="queue_stop_cancel")

    async def queue_clear(self):
        self._clear_status_timestamp()
        return await self.send_request(method="queue_clear")

    async def queue_mode_set(self, **kwargs):
        # Docstring is maintained separately
        request_params = self._prepare_queue_mode_set(**kwargs)
        self._clear_status_timestamp()
        return await self.send_request(method="queue_mode_set", params=request_params)

    async def queue_get(self, *, reload=False):
        # Docstring is maintained separately
        status = await self._status(reload=reload)
        plan_queue_uid = status["plan_queue_uid"]
        if plan_queue_uid != self._current_plan_queue_uid:
            response = await self.send_request(method="queue_get")
            self._process_response_queue_get(response)
        else:
            response = self._generate_response_queue_get()
        return response

    async def history_get(self, *, reload=False):
        # Docstring is maintained separately
        status = await self._status(reload=reload)
        plan_history_uid = status["plan_history_uid"]
        if plan_history_uid != self._current_plan_history_uid:
            response = await self.send_request(method="history_get")
            self._process_response_history_get(response)
        else:
            response = self._generate_response_history_get()
        return response

    async def history_clear(self):
        # Docstring is maintained separately
        self._clear_status_timestamp()
        return await self.send_request(method="history_clear")

    async def plans_allowed(self, *, reload=False):
        # Docstring is maintained separately
        status = await self._status(reload=reload)
        plans_allowed_uid = status["plans_allowed_uid"]
        if plans_allowed_uid != self._current_plans_allowed_uid:
            request_params = self._prepare_plans_devices_allowed()
            response = await self.send_request(method="plans_allowed", params=request_params)
            self._process_response_plans_allowed(response)
        else:
            response = self._generate_response_plans_allowed()
        return response

    async def devices_allowed(self, *, reload=False):
        # Docstring is maintained separately
        status = await self._status(reload=reload)
        devices_allowed_uid = status["devices_allowed_uid"]
        if devices_allowed_uid != self._current_devices_allowed_uid:
            request_params = self._prepare_plans_devices_allowed()
            response = await self.send_request(method="devices_allowed", params=request_params)
            self._process_response_devices_allowed(response)
        else:
            response = self._generate_response_devices_allowed()
        return response

    async def plans_existing(self, *, reload=False):
        # Docstring is maintained separately
        status = await self._status(reload=reload)
        plans_existing_uid = status["plans_existing_uid"]
        if plans_existing_uid != self._current_plans_existing_uid:
            response = await self.send_request(method="plans_existing")
            self._process_response_plans_existing(response)
        else:
            response = self._generate_response_plans_existing()
        return response

    async def devices_existing(self, *, reload=False):
        # Docstring is maintained separately
        status = await self._status(reload=reload)
        devices_existing_uid = status["devices_existing_uid"]
        if devices_existing_uid != self._current_devices_existing_uid:
            response = await self.send_request(method="devices_existing")
            self._process_response_devices_existing(response)
        else:
            response = self._generate_response_devices_existing()
        return response

    async def permissions_reload(self, *, restore_plans_devices=None, restore_permissions=None):
        # Docstring is maintained separately
        request_params = self._prepare_permissions_reload(
            restore_plans_devices=restore_plans_devices, restore_permissions=restore_permissions
        )
        self._clear_status_timestamp()
        return await self.send_request(method="permissions_reload", params=request_params)

    async def permissions_get(self):
        # Docstring is maintained separately
        return await self.send_request(method="permissions_get")

    async def permissions_set(self, user_group_permissions):
        # Docstring is maintained separately
        request_params = self._prepare_permissions_set(user_group_permissions=user_group_permissions)
        self._clear_status_timestamp()
        return await self.send_request(method="permissions_set", params=request_params)

    async def script_upload(self, script, *, update_re=None, run_in_background=None):
        # Docstring is maintained separately
        request_params = self._prepare_script_upload(
            script=script, update_re=update_re, run_in_background=run_in_background
        )
        self._clear_status_timestamp()
        return await self.send_request(method="script_upload", params=request_params)

    async def function_execute(self, item, *, run_in_background=None):
        # Docstring is maintained separately
        request_params = self._prepare_function_execute(item=item, run_in_background=run_in_background)
        self._clear_status_timestamp()
        return await self.send_request(method="function_execute", params=request_params)

    async def task_status(self, task_uid):
        # Docstring is maintained separately
        request_params = self._prepare_task_result(task_uid=task_uid)
        self._clear_status_timestamp()
        return await self.send_request(method="task_status", params=request_params)

    async def task_result(self, task_uid):
        # Docstring is maintained separately
        request_params = self._prepare_task_result(task_uid=task_uid)
        self._clear_status_timestamp()
        return await self.send_request(method="task_result", params=request_params)

    async def re_runs(self, option=None, *, reload=False):
        # Docstring is maintained separately
        self._verify_options_re_runs(option=option)
        status = await self._status(reload=reload)
        run_list_uid = status["run_list_uid"]
        if run_list_uid != self._current_run_list_uid:
            response = await self.send_request(method="re_runs")
            response = self._process_response_re_runs(response, option=option)
        else:
            response = self._generate_response_re_runs(option=option)
        return response

    async def re_pause(self, option=None):
        # Docstring is maintained separately
        request_params = self._prepare_re_pause(option=option)
        self._clear_status_timestamp()
        return await self.send_request(method="re_pause", params=request_params)

    async def re_resume(self):
        # Docstring is maintained separately
        self._clear_status_timestamp()
        return await self.send_request(method="re_resume")

    async def re_stop(self):
        # Docstring is maintained separately
        self._clear_status_timestamp()
        return await self.send_request(method="re_stop")

    async def re_abort(self):
        # Docstring is maintained separately
        self._clear_status_timestamp()
        return await self.send_request(method="re_abort")

    async def re_halt(self):
        # Docstring is maintained separately
        self._clear_status_timestamp()
        return await self.send_request(method="re_halt")


API_Async_Mixin.status.__doc__ = _doc_api_status
API_Async_Mixin.ping.__doc__ = _doc_api_ping
API_Async_Mixin.wait_for_idle.__doc__ = _doc_api_wait_for_idle
API_Async_Mixin.wait_for_idle_or_paused.__doc__ = _doc_api_wait_for_idle_or_paused
API_Async_Mixin.item_add.__doc__ = _doc_api_item_add
API_Async_Mixin.item_add_batch.__doc__ = _doc_api_item_add_batch
API_Async_Mixin.item_update.__doc__ = _doc_api_item_update
API_Async_Mixin.item_get.__doc__ = _doc_api_item_get
API_Async_Mixin.item_remove.__doc__ = _doc_api_item_remove
API_Async_Mixin.item_remove_batch.__doc__ = _doc_api_item_remove_batch
API_Async_Mixin.item_move.__doc__ = _doc_api_item_move
API_Async_Mixin.item_move_batch.__doc__ = _doc_api_item_move_batch
API_Async_Mixin.item_execute.__doc__ = _doc_api_item_execute
API_Async_Mixin.queue_start.__doc__ = _doc_api_queue_start
API_Async_Mixin.queue_stop.__doc__ = _doc_api_queue_stop
API_Async_Mixin.queue_stop_cancel.__doc__ = _doc_api_queue_stop_cancel
API_Async_Mixin.queue_clear.__doc__ = _doc_api_queue_clear
API_Async_Mixin.queue_mode_set.__doc__ = _doc_api_queue_mode_set
API_Async_Mixin.queue_get.__doc__ = _doc_api_queue_get
API_Async_Mixin.history_get.__doc__ = _doc_api_history_get
API_Async_Mixin.history_clear.__doc__ = _doc_api_history_clear
API_Async_Mixin.plans_allowed.__doc__ = _doc_api_plans_allowed
API_Async_Mixin.devices_allowed.__doc__ = _doc_api_devices_allowed
API_Async_Mixin.plans_existing.__doc__ = _doc_api_plans_existing
API_Async_Mixin.devices_existing.__doc__ = _doc_api_devices_existing
API_Async_Mixin.permissions_reload.__doc__ = _doc_api_permissions_reload
API_Async_Mixin.permissions_get.__doc__ = _doc_api_permissions_get
API_Async_Mixin.permissions_set.__doc__ = _doc_api_permissions_set
API_Async_Mixin.environment_open.__doc__ = _doc_api_environment_open
API_Async_Mixin.environment_close.__doc__ = _doc_api_environment_close
API_Async_Mixin.environment_destroy.__doc__ = _doc_api_environment_destroy
API_Async_Mixin.script_upload.__doc__ = _doc_api_script_upload
API_Async_Mixin.function_execute.__doc__ = _doc_api_function_execute
API_Async_Mixin.task_status.__doc__ = _doc_api_task_status
API_Async_Mixin.task_result.__doc__ = _doc_api_task_result
API_Async_Mixin.re_runs.__doc__ = _doc_api_re_runs
API_Async_Mixin.re_pause.__doc__ = _doc_api_re_pause
API_Async_Mixin.re_resume.__doc__ = _doc_api_re_resume
API_Async_Mixin.re_stop.__doc__ = _doc_api_re_stop
API_Async_Mixin.re_abort.__doc__ = _doc_api_re_abort
API_Async_Mixin.re_halt.__doc__ = _doc_api_re_halt
