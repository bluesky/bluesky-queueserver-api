import asyncio
import json
import queue
import threading
import time as ttime

from bluesky_queueserver import ReceiveSystemInfo, ReceiveSystemInfoAsync

from .comm_base import RequestTimeoutError

_system_info_monitor_endpoint = "/api/info/ws"


_doc_SystemInfoMonitor_ZMQ = """
    System Info Monitor API (0MQ). The class implements a monitor for console output
    published by RE Manager over 0MQ. The asynchronous version of the class must
    be instantiated in the loop.

    Parameters
    ----------
    zmq_info_addr: str
        Address of 0MQ PUB socket. The SUB socket of the monitor subscribes to this address
        once the class is instantiated.
    poll_timeout: float
        Timeout used internally for polling 0MQ socket. The value does not influence performance.
        It may take longer to stop the background thread or task, if the value is too large.
    max_msgs: int
        Maximum number of messages in the buffer. New messages are ignored if the buffer
        is full. This could happen only if console monitoring is enabled, but messages
        are not read from the buffer. Setting the value to 0 disables collection of messages
        in the buffer.
"""

_doc_SystemInfoMonitor_HTTP = """
    Console Monitor API (HTTP). The class implements a monitor for console output
    published by RE Manager over HTTP. The asynchronous version of the class must
    be instantiated in the loop.

    Parameters
    ----------
    parent: class
        Reference to the parent class (or any class). The class must expose the attribute
        ``_client`` that references configured ``httpx`` client.
    poll_period: float
        Period between consecutive retries to connect to the websocket at the server.
        The value is also used as a timeout for websocket receive operation. It may take
        longer to stop background thread if the value is too large.
    max_msgs: int
        Maximum number of messages in the buffer. New messages are ignored if the buffer
        is full. This could happen only if console monitoring is enabled, but messages
        are not read from the buffer. Setting the value to 0 disables collection of messages
        in the buffer.
"""

_doc_SystemInfoMonitor_enabled = """
    Indicates if monitoring is enabled. Returns ``True`` if monitoring is enabled,
    ``False`` otherwise.

    Examples
    --------

    Synchronous and asyncronous API:

    .. code-block:: python

        is_enabled = RM.system_info_monitor.enabled
"""

_doc_SystemInfoMonitor_enable = """
    Enable monitoring of the system info. Received messages are accumulated in the buffer
    and need to be continuosly read using ``next_msg()`` to prevent buffer from overflowing.
    If the API is called when background thread or task is not running, the buffer is cleared
    and all old messages are discarded. Note, that disabling and then enabling the monitor in
    rapid sequence is unlikely to clear the buffer, because the background thread or task may
    still be running. Use ``clear()`` API to remove messages from the buffer.

    Examples
    --------

    Synchronous and asyncronous API:

    .. code-block:: python

        RM.system_info_monitor.enable()
        RM.system_info_monitor.disable()
"""

_doc_SystemInfoMonitor_disable = """
    Disable monitoring of the system info. The API does not immediately stop the background thread
    or task. If the monitor is quickly re-enabled, the background thread or task may continue running
    continously.

    Examples
    --------

    Synchronous and asyncronous API:

    .. code-block:: python

        RM.system_info_monitor.enable()
        RM.system_info_monitor.disable()
"""

_doc_SystemInfoMonitor_disable_wait = """
    Disable monitoring and wait for completion.

    Parameters
    ----------
    timeout: float
        Wait timeout.

    Raises
    ------
    TimeoutError
        Wait timeout (synchronous API)
    asyncio.TimeoutError
        Wait timeout (asynchronous API)

    Examples
    --------

    Syncronous API:

    .. code-block:: python

        RM.system_info_monitor.enable()
        RM.system_info_monitor.disable_wait()

    Asynchronous API:

    .. code-block:: python

        RM.system_info_monitor.enable()
        await RM.system_info_monitor.disable_wait()
"""

_doc_SystemInfoMonitor_clear = """
    Clear the message buffer. Removes all messages from the buffer.

    Examples
    --------

    Synchronous and asyncronous API:

    .. code-block:: python

        RM.system_info_monitor.clear()
"""

_doc_SystemInfoMonitor_next_msg = """
    Returns the next message from the buffer. If ``timeout`` is ``None`` or zero, then
    the API returns the next available message. If the buffer contains no messages, the
    function waits for the next published message for ``timeout`` period and raises
    ``RequestTimeoutError`` if no messages were received. If ``timeout is ``None`` or zero
    and the buffer contains no messages, then the function immediately raises
    ``RequestTimeoutError``.

    The returned message is a dictionary with two keys: ``"time"`` (timestamp indicating time
    when the message was sent by RE Manager) and ``"msg"`` (dictionary with one key, the key
    indicates the message type, e.g. ``"status"``, and the value is the information itself).
    For example:

    .. code-block:: python

        {"time": 1764605683.1407075, "msg": {"status": {<status info of RE Manager>}}}

    Parameters
    ----------
    timeout: float or None
        If timeout is positive floating point number, zero or ``None``.

    Raises
    ------
    RequestTimeoutError
        No messages were no messages received during timeout period.

    Examples
    --------

    Synchronous API:

    .. code-block:: python

        # Make sure RE Manager is started with option '--zmq-publish-console=ON'

        RM = REManagerAPI()
        RM.system_info_monitor.enable()

        # Run any command that generates console output
        RM.environment_open()
        RM.wait_for_idle()

        try:
            msg = RM.system_info_monitor.next_msg(timeout=1)
            print(msg["msg"])
        except RM.RequestTimeoutError:
            pass

        RM.system_info_monitor.disable()
        RM.close()

    Asynchronous API:

    .. code-block:: python

        # Make sure RE Manager is started with option '--zmq-publish-console=ON'

        RM = REManagerAPI()
        RM.system_info_monitor.enable()

        # Run any command that generates console output
        await RM.environment_open()
        await RM.wait_for_idle()

        try:
            msg = await RM.system_info_monitor.next_msg(timeout=1)
            print(msg["msg"])
        except RM.RequestTimeoutError:
            pass

        RM.system_info_monitor.disable()
        await RM.close()
"""


def _websocket_uri(uri, endpoint):
    """
    Generate websocket URI based on the base URI used for http requests
    """
    n = uri.find("://")
    if n >= 0:
        uri_base = f"ws://{uri[n + 3 :]}"
    else:
        uri_base = f"ws://{uri}"
    return f"{uri_base}{endpoint}"


class _SystemInfoMonitor:
    def __init__(self):
        self._monitor_enabled = False
        self._monitor_init()

    def _monitor_init(self):
        raise NotImplementedError()

    def _clear(self):
        raise NotImplementedError()

    def _monitor_enable(self):
        raise NotImplementedError()

    @property
    def enabled(self):
        # Docstring is maintained separately
        return self._monitor_enabled

    def enable(self):
        # Docstring is maintained separately
        if not self._monitor_enabled:
            self._monitor_enable()

    def disable(self):
        # Docstring is maintained separately
        self._monitor_enabled = False

    def clear(self):
        # Docstring is maintained separately
        self._clear()

    def __del__(self):
        self.disable()


class _SystemInfoMonitor_Threads(_SystemInfoMonitor):
    def __init__(self, *, max_msgs):
        self._msg_queue_max = max(max_msgs, 0)
        self._msg_queue = queue.Queue(maxsize=max_msgs)

        self._monitor_enabled = False
        self._monitor_thread = None  # Thread or asyncio task
        self._monitor_thread_running = threading.Event()
        self._monitor_thread_running.set()

        self._monitor_thread_lock = threading.Lock()

        super().__init__()

    def _monitor_enable(self):
        self._monitor_thread = threading.Thread(
            target=self._thread_receive_msgs, name="QS API - Console monitoring", daemon=True
        )
        self._monitor_enabled = True
        self._monitor_thread.start()

    def _add_msg_to_queue(self, msg):
        if self._msg_queue_max:
            self._msg_queue.put_nowait(msg)

    def disable_wait(self, *, timeout=2):
        # Docstring is maintained separately
        self.disable()
        if not self._monitor_thread_running.wait(timeout=timeout):
            raise TimeoutError(f"Timeout occurred while disabling console monitor: timeout={timeout}")

    def next_msg(self, timeout=None):
        # Docstring is maintained separately
        block = bool(timeout)
        try:
            return self._msg_queue.get(block=block, timeout=timeout)
        except queue.Empty:
            raise RequestTimeoutError(f"No message was received (timeout={timeout})", request={})


class SystemInfoMonitor_ZMQ_Threads(_SystemInfoMonitor_Threads):
    # Docstring is maintained separately

    def __init__(self, *, zmq_info_addr, zmq_encoding, poll_timeout, max_msgs):
        self._zmq_subscribe_addr = zmq_info_addr
        self._zmq_encoding = zmq_encoding
        self._monitor_poll_timeout = poll_timeout
        super().__init__(max_msgs=max_msgs)

    def _monitor_init(self):
        self._rco = ReceiveSystemInfo(
            zmq_subscribe_addr=self._zmq_subscribe_addr,
            encoding=self._zmq_encoding,
            timeout=int(self._monitor_poll_timeout * 1000),
        )

    def _thread_receive_msgs(self):
        with self._monitor_thread_lock:
            if not self._monitor_thread_running.is_set():
                return
            self._monitor_thread_running.clear()
            self.clear()

        self._rco.subscribe()

        while True:
            with self._monitor_thread_lock:
                if not self._monitor_enabled:
                    self._rco.unsubscribe()
                    self._monitor_thread_running.set()
                    break
            try:
                msg = self._rco.recv()
                self._add_msg_to_queue(msg)

            except TimeoutError:
                # No published messages are detected
                pass
            except queue.Full:
                # Queue is full, ignore the new messages
                pass

    def _clear(self):
        self._msg_queue.queue.clear()


class SystemInfoMonitor_HTTP_Threads(_SystemInfoMonitor_Threads):
    # Docstring is maintained separately

    def __init__(self, *, parent, poll_period, max_msgs):
        # The parent class is must have ``_client`` attribute with
        #   active httpx client.
        self._parent = parent  # Reference to the parent class
        self._monitor_poll_period = poll_period
        super().__init__(max_msgs=max_msgs)

    def _monitor_init(self): ...

    def _thread_receive_msgs(self):
        with self._monitor_thread_lock:
            if not self._monitor_thread_running.is_set():
                return
            self._monitor_thread_running.clear()
            self.clear()

        while True:
            with self._monitor_thread_lock:
                if not self._monitor_enabled:
                    self._monitor_thread_running.set()
                    break

            auth_method = self._parent._auth_method
            auth_key = self._parent._auth_key
            api_key_first_eight = None
            use_apikey = auth_method == self._parent.AuthorizationMethods.API_KEY
            use_token = auth_method == self._parent.AuthorizationMethods.TOKEN

            def delete_api_key(use_token, api_key_first_eight):
                # Send request to delete temporary API key if it exists
                if use_token and api_key_first_eight:
                    try:
                        self._parent.send_request(
                            method="apikey_delete", url_params={"first_eight": api_key_first_eight}
                        )
                    except Exception:
                        pass

            websocket_uri = _websocket_uri(self._parent._http_server_uri, _system_info_monitor_endpoint)
            try:
                from websockets.sync.client import connect

                _api_key = None

                # Request temporary API key
                if use_apikey:
                    _api_key = auth_key
                elif use_token:
                    response = self._parent.send_request(method="apikey_new", params={"expires_in": 60})
                    _api_key = response["secret"]
                    api_key_first_eight = response["first_eight"]

                additional_headers = {}
                if _api_key:
                    additional_headers = {"Authorization": f"ApiKey {_api_key}"}

                with connect(websocket_uri, additional_headers=additional_headers) as websocket:
                    delete_api_key(use_token, api_key_first_eight)
                    api_key_first_eight = None

                    while self._monitor_enabled:
                        try:
                            msg_json = websocket.recv(timeout=self._monitor_poll_period, decode=False)
                            try:
                                msg = json.loads(msg_json)
                                self._add_msg_to_queue(msg)
                            except json.JSONDecodeError:
                                pass
                            except queue.Full:
                                # Queue is full, ignore the new messages
                                pass
                        except TimeoutError:
                            pass
            except Exception:
                # Ignore communication errors. More detailed processing may be added later.
                pass
            finally:
                delete_api_key(use_token, api_key_first_eight)

            ttime.sleep(self._monitor_poll_period)

    def _clear(self):
        self._msg_queue.queue.clear()


class _SystemInfoMonitor_Async(_SystemInfoMonitor):
    def __init__(self, *, max_msgs):
        self._msg_queue_max = max_msgs
        self._msg_queue = asyncio.Queue(maxsize=max_msgs)

        self._monitor_task = None  # Thread or asyncio task
        self._monitor_task_running = asyncio.Event()
        self._monitor_task_running.set()

        self._monitor_task_lock = asyncio.Lock()

        super().__init__()

    def _add_msg_to_queue(self, msg):
        if self._msg_queue_max:
            self._msg_queue.put_nowait(msg)

    def _monitor_enable(self):
        self._monitor_task = asyncio.create_task(self._task_receive_msgs())
        self._monitor_enabled = True

    async def disable_wait(self, *, timeout=2):
        # Docstring is maintained separately
        self.disable()
        await asyncio.wait_for(self._monitor_task_running.wait(), timeout=timeout)

    async def next_msg(self, timeout=None):
        # Docstring is maintained separately
        try:
            if timeout:
                return await asyncio.wait_for(self._msg_queue.get(), timeout=timeout)
            else:
                return self._msg_queue.get_nowait()
        except (asyncio.QueueEmpty, asyncio.TimeoutError):
            raise RequestTimeoutError(f"No message was received (timeout={timeout})", request={})


class SystemInfoMonitor_ZMQ_Async(_SystemInfoMonitor_Async):
    # Docstring is maintained separately

    def __init__(self, *, zmq_info_addr, zmq_encoding, poll_timeout, max_msgs):
        self._zmq_subscribe_addr = zmq_info_addr
        self._zmq_encoding = zmq_encoding
        self._monitor_poll_timeout = poll_timeout
        super().__init__(max_msgs=max_msgs)

    def _monitor_init(self):
        self._rco = ReceiveSystemInfoAsync(
            zmq_subscribe_addr=self._zmq_subscribe_addr,
            encoding=self._zmq_encoding,
            timeout=int(self._monitor_poll_timeout * 1000),
        )

    async def _task_receive_msgs(self):
        async with self._monitor_task_lock:
            if not self._monitor_task_running.is_set():
                return
            self._monitor_task_running.clear()
            self.clear()

            self._rco.subscribe()

        while True:
            async with self._monitor_task_lock:
                if not self._monitor_enabled:
                    self._rco.unsubscribe()
                    self._monitor_task_running.set()
                    break

            try:
                msg = await self._rco.recv()
                self._add_msg_to_queue(msg)

            except TimeoutError:
                # No published messages are detected
                pass
            except asyncio.QueueFull:
                # Queue is full, ignore the new messages
                pass

    def _clear(self):
        try:
            while True:
                self._msg_queue.get_nowait()
        except asyncio.QueueEmpty:
            pass


class SystemInfoMonitor_HTTP_Async(_SystemInfoMonitor_Async):
    # Docstring is maintained separately

    def __init__(self, *, parent, poll_period, max_msgs):
        # The parent class is must have ``_client`` attribute with
        #   active httpx client.
        self._parent = parent  # Reference to the parent class
        self._monitor_poll_period = poll_period
        super().__init__(max_msgs=max_msgs)

    def _monitor_init(self): ...

    async def _task_receive_msgs(self):
        async with self._monitor_task_lock:
            if not self._monitor_task_running.is_set():
                return
            self._monitor_task_running.clear()
            self.clear()

        while True:
            async with self._monitor_task_lock:
                if not self._monitor_enabled:
                    self._monitor_task_running.set()
                    break

            auth_method = self._parent._auth_method
            auth_key = self._parent._auth_key
            api_key_first_eight = None
            use_apikey = auth_method == self._parent.AuthorizationMethods.API_KEY
            use_token = auth_method == self._parent.AuthorizationMethods.TOKEN

            async def delete_api_key(use_token, api_key_first_eight):
                # Send request to delete temporary API key if it exists
                if use_token and api_key_first_eight:
                    try:
                        await self._parent.send_request(
                            method="apikey_delete", url_params={"first_eight": api_key_first_eight}
                        )
                    except Exception:
                        pass

            websocket_uri = _websocket_uri(self._parent._http_server_uri, _system_info_monitor_endpoint)
            try:
                from websockets.asyncio.client import connect

                _api_key = None

                # Request temporary API key
                if use_apikey:
                    _api_key = auth_key
                elif use_token:
                    response = await self._parent.send_request(method="apikey_new", params={"expires_in": 60})
                    _api_key = response["secret"]
                    api_key_first_eight = response["first_eight"]

                additional_headers = {}
                if _api_key:
                    additional_headers = {"Authorization": f"ApiKey {_api_key}"}

                async with connect(websocket_uri, additional_headers=additional_headers) as websocket:
                    await delete_api_key(use_token, api_key_first_eight)
                    api_key_first_eight = None

                    while self._monitor_enabled:
                        try:
                            msg_json = await asyncio.wait_for(
                                websocket.recv(decode=False), timeout=self._monitor_poll_period
                            )
                            try:
                                msg = json.loads(msg_json)
                                self._add_msg_to_queue(msg)
                            except json.JSONDecodeError:
                                pass
                            except asyncio.QueueFull:
                                # Queue is full, ignore the new messages
                                pass
                        except asyncio.TimeoutError:
                            pass
            except Exception:
                # Ignore communication errors. More detailed processing may be added later.
                pass
            finally:
                await delete_api_key(use_token, api_key_first_eight)
            await asyncio.sleep(self._monitor_poll_period)

    def _clear(self):
        try:
            while True:
                self._msg_queue.get_nowait()
        except asyncio.QueueEmpty:
            pass


_SystemInfoMonitor.enabled.__doc__ = _doc_SystemInfoMonitor_enabled
_SystemInfoMonitor.enable.__doc__ = _doc_SystemInfoMonitor_enable
_SystemInfoMonitor.disable.__doc__ = _doc_SystemInfoMonitor_disable
_SystemInfoMonitor.clear.__doc__ = _doc_SystemInfoMonitor_clear

_SystemInfoMonitor_Threads.disable_wait.__doc__ = _doc_SystemInfoMonitor_disable_wait
_SystemInfoMonitor_Threads.next_msg.__doc__ = _doc_SystemInfoMonitor_next_msg

SystemInfoMonitor_ZMQ_Threads.__doc__ = _doc_SystemInfoMonitor_ZMQ
SystemInfoMonitor_HTTP_Threads.__doc__ = _doc_SystemInfoMonitor_HTTP

_SystemInfoMonitor_Async.disable_wait.__doc__ = _doc_SystemInfoMonitor_disable_wait
_SystemInfoMonitor_Async.next_msg.__doc__ = _doc_SystemInfoMonitor_next_msg

SystemInfoMonitor_ZMQ_Async.__doc__ = _doc_SystemInfoMonitor_ZMQ
SystemInfoMonitor_HTTP_Async.__doc__ = _doc_SystemInfoMonitor_HTTP
