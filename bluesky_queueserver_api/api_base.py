import copy
import getpass
import os
import secrets
import time as ttime
from collections.abc import Iterable, Mapping
from pathlib import Path

from ._defaults import default_user_group, default_user_name
from .comm_base import RequestParameterError
from .item import BItem


class WaitTimeoutError(TimeoutError): ...


class WaitCancelError(TimeoutError): ...


class WaitMonitor:
    """
    Creates ``monitor`` object for ``wait_...`` operations, such as ``wait_for_idle``.
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
        return ttime.time() - self.time_start

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

        self._user = default_user_name  # Meaningful user name should be set in application code.
        self._user_group = default_user_group

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
        self._current_run_list = []
        self._current_run_list_uid = None
        self._current_lock_info = {}
        self._current_lock_info_uid = None

        self._lock_key = None
        self._default_lock_key_path = os.path.join(Path.home(), ".config", "qserver", "default_lock_key.txt")
        self._enable_locked_api = False

    def _check_name(self, name, name_in_msg):
        if not isinstance(name, str):
            raise ValueError(f"{name_in_msg} {name!r} is not a string: type {type(name)!r}")
        if not name:
            raise ValueError(f"{name_in_msg} is an empty string.")

    @property
    def user(self):
        """
        Get and set the default user name. The default value is used if user name is not passed
        explicitly as an API parameter (for API calls that require user name). User name is ignored
        by the HTTP version of API, since HTTP server is expected to manage user names.
        """
        return self._user

    @user.setter
    def user(self, user):
        self._check_name(user, "User name")
        self._user = user

    @property
    def user_group(self):
        """
        Get and set the default user group name. The default value is used if the group name is
        not passed explicitly as an API parameter (for API calls that require user group name).
        The group name is ignored by the HTTP version of API, since HTTP server is expected to manage
        user information including names of user group.
        """
        return self._user_group

    @user_group.setter
    def user_group(self, user_group):
        self._check_name(user_group, "User group name")
        self._user_group = user_group

    def set_user_name_to_login_name(self):
        """
        Set the default user name to 'login name'. Login name the current user of the workstation
        is used. User name is ignored by the HTTP version of the API.
        """
        self.user = getpass.getuser()

    def _clear_status_timestamp(self):
        """
        Clearing status timestamp causes status to be reloaded from the server next time it is requested.
        """
        self._status_timestamp = None

    def _get_user_group_for_allowed_plans_devices(self, *, user_group):
        """
        Returns ``user_group`` used by ``plans_allowed`` and ``devices_allowed`` API.
        """
        if self._add_request_param:
            user_group = user_group if user_group else self._user_group
        else:
            user_group = "http"  # Arbitrary group names, since it is not sent in the request
        return user_group

    def _request_params_add_user_info(self, request_params, *, user, user_group):
        if self._pass_user_info:
            request_params["user"] = user if user else self._user
            request_params["user_group"] = user_group if user_group else self._user_group

    def _add_request_param(self, request_params, name, value):
        """
        Add parameter to dictionary ``request_params`` if value is not ``None``.
        """
        if value is not None:
            request_params[name] = value

    def _add_lock_key(self, request_params, lock_key):
        """
        Add lock key to ``request_params`` if lock key is not ``None``.
        If ``lock_key`` is None, then try to use the 'current' lock key.
        If the passed and 'current' lock key is None, then do not add the key.
        """
        self._validate_lock_key(lock_key)
        if not lock_key and self._enable_locked_api:
            lock_key = self._lock_key
        if lock_key:
            request_params["lock_key"] = lock_key

    def _prepare_item_add(self, *, item, pos, before_uid, after_uid, user, user_group, lock_key):
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
        self._request_params_add_user_info(request_params, user=user, user_group=user_group)
        self._add_lock_key(request_params, lock_key)
        return request_params

    def _prepare_item_add_batch(self, *, items, pos, before_uid, after_uid, user, user_group, lock_key):
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
        self._request_params_add_user_info(request_params, user=user, user_group=user_group)
        self._add_lock_key(request_params, lock_key)
        return request_params

    def _prepare_item_update(self, *, item, replace, user, user_group, lock_key):
        """
        Prepare parameters for ``item_update`` operation.
        """
        if not isinstance(item, BItem) and not isinstance(item, Mapping):
            raise TypeError(f"Incorrect item type {type(item)!r}. Expected type: 'BItem' or 'dict'")

        item = item.to_dict() if isinstance(item, BItem) else dict(item).copy()

        request_params = {"item": item}
        self._add_request_param(request_params, "replace", replace)
        self._request_params_add_user_info(request_params, user=user, user_group=user_group)
        self._add_lock_key(request_params, lock_key)
        return request_params

    def _prepare_item_move(self, *, pos, uid, pos_dest, before_uid, after_uid, lock_key):
        """
        Prepare parameters for ``item_add`` operation.
        """
        request_params = {}
        self._add_request_param(request_params, "pos", pos)
        self._add_request_param(request_params, "uid", uid)
        self._add_request_param(request_params, "pos_dest", pos_dest)
        self._add_request_param(request_params, "before_uid", before_uid)
        self._add_request_param(request_params, "after_uid", after_uid)
        self._add_lock_key(request_params, lock_key)

        return request_params

    def _prepare_item_move_batch(self, *, uids, pos_dest, before_uid, after_uid, reorder, lock_key):
        """
        Prepare parameters for ``item_add`` operation.
        """
        request_params = {}
        self._add_request_param(request_params, "uids", uids)
        self._add_request_param(request_params, "pos_dest", pos_dest)
        self._add_request_param(request_params, "before_uid", before_uid)
        self._add_request_param(request_params, "after_uid", after_uid)
        self._add_request_param(request_params, "reorder", reorder)
        self._add_lock_key(request_params, lock_key)

        return request_params

    def _prepare_item_get(self, *, pos, uid):
        """
        Prepare parameters for ``item_get`` and ``item_remove`` operation
        """
        request_params = {}
        self._add_request_param(request_params, "pos", pos)
        self._add_request_param(request_params, "uid", uid)
        return request_params

    def _prepare_item_remove(self, *, pos, uid, lock_key):
        """
        Prepare parameters for ``item_get`` and ``item_remove`` operation
        """
        request_params = {}
        self._add_request_param(request_params, "pos", pos)
        self._add_request_param(request_params, "uid", uid)
        self._add_lock_key(request_params, lock_key)
        return request_params

    def _prepare_item_remove_batch(self, *, uids, ignore_missing, lock_key):
        """
        Prepare parameters for ``item_remove_batch`` operation
        """
        request_params = {"uids": uids}
        self._add_request_param(request_params, "ignore_missing", ignore_missing)
        self._add_lock_key(request_params, lock_key)
        return request_params

    def _prepare_item_execute(self, *, item, user, user_group, lock_key):
        """
        Prepare parameters for ``item_execute`` operation.
        """
        if not isinstance(item, BItem) and not isinstance(item, Mapping):
            raise TypeError(f"Incorrect item type {type(item)!r}. Expected type: 'BItem' or 'dict'")

        item = item.to_dict() if isinstance(item, BItem) else dict(item).copy()

        request_params = {"item": item}
        self._request_params_add_user_info(request_params, user=user, user_group=user_group)
        self._add_lock_key(request_params, lock_key)
        return request_params

    def _prepare_history_clear(self, *, lock_key):
        """
        Prepare parameters for ``history_clear``
        """
        request_params = {}
        self._add_lock_key(request_params, lock_key)
        return request_params

    def _prepare_queue_clear(self, *, lock_key):
        """
        Prepare parameters for ``queue_clear``
        """
        request_params = {}
        self._add_lock_key(request_params, lock_key)
        return request_params

    def _prepare_queue_autostart(self, *, enable, lock_key):
        """
        Prepare parameters for ``queue_autostart``.
        """
        request_params = {"enable": bool(enable)}
        self._add_lock_key(request_params, lock_key)
        return request_params

    def _prepare_queue_mode_set(self, **kwargs):
        """
        Prepare parameters for ``queue_mode_set`` operation.
        """
        lock_key = kwargs.pop("lock_key", None)
        if "mode" in kwargs:
            request_params = {"mode": kwargs["mode"]}
        else:
            request_params = {"mode": kwargs}
        self._add_lock_key(request_params, lock_key)
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

    def _prepare_plans_devices_allowed(self, *, user_group):
        """
        Prepare parameters for ``plans_allowed`` and ``devices_allowed`` operation.
        """
        request_params = {}
        self._request_params_add_user_info(request_params, user=None, user_group=user_group)

        # User name should not be includedin the request
        if "user" in request_params:
            del request_params["user"]

        return request_params

    def _invalidate_plans_allowed_cache(self):
        self._current_plans_allowed.clear()

    def _process_response_plans_allowed(self, response, *, user_group):
        """
        ``plans_allowed``: process response
        """
        if response["success"] is True:
            if response["plans_allowed_uid"] != self._current_plans_allowed_uid:
                self._invalidate_plans_allowed_cache()
                self._current_plans_allowed_uid = response["plans_allowed_uid"]
            self._current_plans_allowed[user_group] = copy.deepcopy(response["plans_allowed"])

    def _generate_response_plans_allowed(self, *, user_group):
        """
        ``plans_allowed``: generate response based on cached data
        """
        response = {
            "success": True,
            "msg": "",
            "plans_allowed_uid": self._current_plans_allowed_uid,
            "plans_allowed": copy.deepcopy(self._current_plans_allowed[user_group]),
        }
        return response

    def _invalidate_devices_allowed_cache(self):
        self._current_devices_allowed.clear()

    def _process_response_devices_allowed(self, response, *, user_group):
        """
        ``devices_allowed``: process response
        """
        if response["success"] is True:
            if response["devices_allowed_uid"] != self._current_devices_allowed_uid:
                self._invalidate_devices_allowed_cache()
                self._current_devices_allowed_uid = response["devices_allowed_uid"]
            self._current_devices_allowed[user_group] = copy.deepcopy(response["devices_allowed"])

    def _generate_response_devices_allowed(self, *, user_group):
        """
        ``devices_allowed``: generate response based on cached data
        """
        response = {
            "success": True,
            "msg": "",
            "devices_allowed_uid": self._current_devices_allowed_uid,
            "devices_allowed": copy.deepcopy(self._current_devices_allowed[user_group]),
        }
        return response

    def _process_response_plans_existing(self, response):
        """
        ``plans_existing``: process response
        """
        if response["success"] is True:
            self._current_plans_existing = copy.deepcopy(response["plans_existing"])
            self._current_plans_existing_uid = response["plans_existing_uid"]

    def _generate_response_plans_existing(self):
        """
        ``plans_existing``: generate response based on cached data
        """
        response = {
            "success": True,
            "msg": "",
            "plans_existing_uid": self._current_plans_existing_uid,
            "plans_existing": copy.deepcopy(self._current_plans_existing),
        }
        return response

    def _process_response_devices_existing(self, response):
        """
        ``devices_existing``: process response
        """
        if response["success"] is True:
            self._current_devices_existing = copy.deepcopy(response["devices_existing"])
            self._current_devices_existing_uid = response["devices_existing_uid"]

    def _generate_response_devices_existing(self):
        """
        ``devices_existing``: generate response based on cached data
        """
        response = {
            "success": True,
            "msg": "",
            "devices_existing_uid": self._current_devices_existing_uid,
            "devices_existing": copy.deepcopy(self._current_devices_existing),
        }
        return response

    def _prepare_permissions_reload(self, *, restore_plans_devices, restore_permissions, lock_key):
        """
        Prepare parameters for ``permissions_reload``
        """
        request_params = {}
        self._add_request_param(request_params, "restore_plans_devices", restore_plans_devices)
        self._add_request_param(request_params, "restore_permissions", restore_permissions)
        self._add_lock_key(request_params, lock_key)
        return request_params

    def _prepare_permissions_set(self, *, user_group_permissions, lock_key):
        """
        Prepare parameters for ``permissions_set``
        """
        request_params = {"user_group_permissions": user_group_permissions}
        self._add_lock_key(request_params, lock_key)
        return request_params

    def _prepare_environment_control(self, *, lock_key):
        """
        Prepare parameters for generic API for environment control which accepts only 'lock_key'``
        """
        request_params = {}
        self._add_lock_key(request_params, lock_key)
        return request_params

    def _prepare_environment_update(self, *, run_in_background, lock_key):
        """
        Prepare parameters for ``environment_update``
        """
        request_params = {}
        self._add_request_param(request_params, "run_in_background", run_in_background)
        self._add_lock_key(request_params, lock_key)
        return request_params

    def _prepare_script_upload(self, *, script, update_lists, update_re, run_in_background, lock_key):
        """
        Prepare parameters for ``script_upload``
        """
        request_params = {"script": script}
        self._add_request_param(request_params, "update_lists", update_lists)
        self._add_request_param(request_params, "update_re", update_re)
        self._add_request_param(request_params, "run_in_background", run_in_background)
        self._add_lock_key(request_params, lock_key)
        return request_params

    def _prepare_function_execute(self, *, item, run_in_background, user, user_group, lock_key):
        """
        Prepare parameters for ``script_upload``
        """
        if not isinstance(item, BItem) and not isinstance(item, Mapping):
            raise TypeError(f"Incorrect item type {type(item)!r}. Expected type: 'BItem' or 'dict'")

        item = item.to_dict() if isinstance(item, BItem) else dict(item).copy()

        request_params = {"item": item}
        self._add_request_param(request_params, "run_in_background", run_in_background)
        self._request_params_add_user_info(request_params, user=user, user_group=user_group)
        self._add_lock_key(request_params, lock_key)
        return request_params

    def _prepare_task_status(self, *, task_uid):
        """
        Prepare parameters for ``task_status``
        """
        if isinstance(task_uid, str):
            # A string should remain a string.
            task_uid_prepared = task_uid
        elif isinstance(task_uid, Iterable):
            # Status of multiple tasks can be fetched from the manager per a single request.
            # Iterable may be a tuple, a set etc, but it is best to convert it to a list.
            task_uid_prepared = list(task_uid)
        else:
            raise RequestParameterError(
                f"Invalid type of parameter 'task_uid' ({type(task_uid)}). String or iterable (list) is expected."
            )
        request_params = {"task_uid": task_uid_prepared}
        return request_params

    def _prepare_task_result(self, *, task_uid):
        """
        Prepare parameters for ``task_result``
        """
        if not isinstance(task_uid, str):
            # Only a result of a single task can be fetched per request.
            raise RequestParameterError(
                f"Invalid type of parameter 'task_uid' ({type(task_uid)}). String is expected."
            )
        request_params = {"task_uid": task_uid}
        return request_params

    def _verify_options_re_runs(self, option):
        """
        Options for ``re_runs`` API is processed locally, so verify that the option
        value is supported.
        """
        allowed_options = (None, "active", "open", "closed")
        if option not in allowed_options:
            raise IndexError(f"Unsupported option {option!r}. Supported options: {allowed_options}")

    def _process_response_re_runs(self, response, *, option):
        """
        ``re_runs``: process response
        """
        if response["success"] is True:
            self._current_run_list = copy.deepcopy(response["run_list"])
            self._current_run_list_uid = response["run_list_uid"]
            response["run_list"] = self._select_re_runs_items(option=option)
        return response

    def _select_re_runs_items(self, *, option):
        """
        ``re_runs``: select runs from the full list based on the option.
        """
        if option == "open":
            run_list = [_ for _ in self._current_run_list if _["is_open"]]
        elif option == "closed":
            run_list = [_ for _ in self._current_run_list if not _["is_open"]]
        else:
            run_list = copy.deepcopy(self._current_run_list)
        return run_list

    def _generate_response_re_runs(self, *, option):
        """
        ``re_runs``: generate response based on cached data
        """
        response = {
            "success": True,
            "msg": "",
            "run_list_uid": self._current_run_list_uid,
            "run_list": self._select_re_runs_items(option=option),
        }
        return response

    def _prepare_re_pause(self, *, option, lock_key):
        """
        Prepare parameters for ``re_pause`` operation
        """
        request_params = {}
        self._add_request_param(request_params, "option", option)
        self._add_lock_key(request_params, lock_key)
        return request_params

    def _prepare_wait_for_completed_task(self, *, task_uid):
        """
        Preprocessing parameters for ``wait_for_completed_task``.
        """
        params = self._prepare_task_status(task_uid=task_uid)
        task_uid = params["task_uid"]
        if not task_uid:
            # At this point, 'task_uid' is a string or a list.
            msg_type = "string" if isinstance(task_uid, str) else "list"
            raise RequestParameterError(
                f"Invalid value of parameter 'task_uid': task UID must be a non-empty {msg_type}"
            )
        return task_uid

    def _pick_completed_tasks(self, task_status_reply, *, treat_not_found_as_completed):
        """
        Returns a dictionary of completed tasks based on reply retured by ``task_status`` API.
        The dictionary maps task UID to the status. Status may be 'completed' or 'not_found'
        (if ``treat_not_found_as_completed`` is ``True``).

        Parameters
        ----------
        task_status_reply: dict
            Dictionary returned by ``REManagerAPI.task_status`` API. It is assumed, that
            the API call was successful.
        treat_not_found_as_completed: boolean
            The tasks with status 'not_found' are treated as 'completed' if ``True``.
            Typically 'not_found' means that the task was completed and then expired
            and deleted from the list of active tasks, so this assumption is valid in
            most cases.

        Returns
        -------
        dict(str: str)
            Dictionary that maps task UIDs to its status (``'completed'`` or ``'not_found'``).
            The dictionary may be empty if there are no completed tasks.
        """
        completed_status_vals = ["completed"]
        if treat_not_found_as_completed:
            completed_status_vals.append("not_found")

        task_uids = task_status_reply["task_uid"]
        task_status = task_status_reply["status"]

        if (task_uids is None) or (task_status is None):
            return {}
        elif isinstance(task_uids, str):
            return {task_uids: task_status} if task_status in completed_status_vals else []
        elif isinstance(task_uids, list):
            return {_: task_status[_] for _ in task_uids if task_status[_] in completed_status_vals}
        else:
            return {}

    def _prepare_kernel_interrupt(self, *, interrupt_task, interrupt_plan, lock_key):
        """
        Prepare parameters for ``kernel_interrupt``
        """
        request_params = {}
        self._add_request_param(request_params, "interrupt_task", interrupt_task)
        self._add_request_param(request_params, "interrupt_plan", interrupt_plan)
        self._add_lock_key(request_params, lock_key)
        return request_params

    def _validate_lock_key(self, lock_key):
        # lock key may be a non-empty string or None
        if not (lock_key is None):
            if not isinstance(lock_key, str) or not lock_key:
                raise ValueError(f"Parameter 'lock_key' must be non-empty string or None: lock_key={lock_key!r}")

    def _prepare_lock(self, *, environment, queue, lock_key, note, user):
        # Lock key may be None. Use self.lock_key in this case.
        self._validate_lock_key(lock_key)
        if not lock_key:
            lock_key = self.lock_key
        if not lock_key:
            raise RuntimeError("Failed to format the 'lock' request: Lock key is not set")

        if not isinstance(note, (str, type(None))):
            raise ValueError(f"Parameter 'note' must be a string or None: note={note!r}")
        environment, queue = bool(environment), bool(queue)

        request_params = {}
        if environment:
            request_params["environment"] = environment
        if queue:
            request_params["queue"] = queue
        request_params["lock_key"] = lock_key

        self._request_params_add_user_info(request_params, user=user, user_group=None)
        if "user_group" in request_params:
            del request_params["user_group"]

        if note:
            request_params["note"] = note

        return request_params

    def _prepare_unlock(self, *, lock_key):
        # Lock key may be None. Use self.lock_key in this case.
        self._validate_lock_key(lock_key)
        if not lock_key:
            lock_key = self.lock_key
        if not lock_key:
            raise RuntimeError("Failed to format the 'unlock' request: Lock key is not set")

        return {"lock_key": lock_key}

    def _prepare_lock_info(self, *, lock_key):
        # Lock key may be None.
        self._validate_lock_key(lock_key)
        return {"lock_key": lock_key}

    def _process_response_lock_info(self, response):
        """
        ``lock_info``: process response
        """
        if response["success"] is True:
            self._current_lock_info = copy.deepcopy(response["lock_info"])
            self._current_lock_info_uid = copy.deepcopy(response["lock_info_uid"])

    def _generate_response_lock_info(self):
        """
        ``lock_info``: generate response based on cached data
        """
        response = {
            "success": True,
            "msg": "",
            "lock_info_uid": self._current_lock_info_uid,
            "lock_info": copy.deepcopy(self._current_lock_info),
        }
        return response

    @property
    def default_lock_key_path(self):
        """
        Get/set path of the file with the default lock key. The default path is
        ``<user-home-dir>.config/qserver/default_lock_key.txt``. In some workflows
        it may be useful to set a different path.
        """
        return self._default_lock_key_path

    @default_lock_key_path.setter
    def default_lock_key_path(self, lock_key_path):
        self._default_lock_key_path = lock_key_path

    def get_default_lock_key(self, new_key=False):
        """
        Returns the default lock key. The key is stored in a file ``.config/qserver/default_lock_key.txt``.
        The key is load from disk each time the method is called. If the key (the file) does not exist
        or the method parameter ``new_key`` is ``True``, then the new key is generated and saved to file.
        A specific default key may be manually set and saved to file using ``set_default_lock_key()`` API.

        The default lock key is used for storage of the key so that it could be reused between
        sessions. The default key is not used directly by other API. Typically the initialization
        script for the session should initialize the current lock key with the default lock key::

          RM.lock_key = RM.get_default_lock_key()

        Parameters
        ----------
        new_key: boolean
            Set this parameter ``True`` to generate a new default lock key.

        Returns
        -------
        str
            The default lock key.
        """
        if not os.path.exists(self._default_lock_key_path) or new_key:
            lock_key = secrets.token_urlsafe(16)
            self.set_default_lock_key(lock_key)
        else:
            with open(self._default_lock_key_path, "rt") as f:
                lock_key = f.readlines()[0].strip()
        return lock_key

    def set_default_lock_key(self, lock_key):
        """
        Set the default lock key. The lock key must be a non-empty string. The key is saved
        to a file on disk and loaded each time ``get_default_lock_key()`` method is called.
        See the description for ``get_default_lock_key()`` for more information.

        Parameters
        ----------
        lock_key: str
            The new lock key.

        Returns
        -------
        None

        Raises
        ------
        IOError
            Error while saving the lock key to disk or the lock key is invalid.
        """
        try:
            if not lock_key or not isinstance(lock_key, str):
                raise ValueError(f"'lock_key' must be a non-empty string: lock_key={lock_key!r}")
            lock_key_path, _ = os.path.split(self._default_lock_key_path)
            if os.path.exists(lock_key_path):
                if not os.path.isdir(lock_key_path):
                    raise IOError(f"Path {lock_key_path!r} exists, but it is not a directory")
            else:
                os.makedirs(lock_key_path, exist_ok=True)
            with open(self._default_lock_key_path, "wt") as f:
                f.write(lock_key)
        except Exception as ex:
            raise IOError(f"Failed to save the default lock key: {ex}") from ex

    @property
    def lock_key(self):
        """
        Get/set current lock key. The current lock key is used for locking/unlocking RE Manager
        unless the key is explicitly passed as ``lock_key`` parameter. The current key is also
        passed with other API if locked API are enabled (``enable_locked_api`` is ``True``).
        Setting the current lock key to ``None`` clears the lock key and disables access to
        locked API. A valid current lock key must be set before access to locked API is enabled.

        Raises
        ------
        ValueError
            Invalid lock key. The key must be a non-empty string or ``None``.
        """
        return self._lock_key

    @lock_key.setter
    def lock_key(self, lock_key):
        self._validate_lock_key(lock_key)
        if not lock_key:
            self.enable_locked_api = False
        self._lock_key = lock_key

    @property
    def enable_locked_api(self):
        """
        Enable/disable access to locked API. When access to locked API is enabled, the current
        lock key (``RM.lock_key``) is automatically sent with API requests. The locked API
        may be called without enabling automatic access by explicitly sending the lock key
        with each request. A valid current lock key must be set before access could be enabled.
        The access is disabled when the lock key is cleared.

        Raises
        ------
        TypeError
            Attempt to set to a value of non-boolean type.
        RuntimeError
            Current lock key is not set.
        """
        return self._enable_locked_api

    @enable_locked_api.setter
    def enable_locked_api(self, enable_locked_api):
        if not isinstance(enable_locked_api, bool):
            raise TypeError("The property may be set only to boolean values")
        if not self.lock_key:
            raise RuntimeError("Failed to enable locked API: current lock key is not set")
        self._enable_locked_api = enable_locked_api
