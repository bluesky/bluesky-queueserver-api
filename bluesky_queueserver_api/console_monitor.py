import asyncio
import queue
import threading
import time as ttime

from bluesky_queueserver import ReceiveConsoleOutput, ReceiveConsoleOutputAsync

from .comm_base import RequestTimeoutError

_console_monitor_http_method = "GET"
_console_monitor_http_endpoint = "console_output_update"

_doc_ConsoleMonitor_ZMQ = """
    Console Monitor API (0MQ). The class implements a monitor for console output
    published by RE Manager over 0MQ. The asynchronous version of the class must
    be instantiated in the loop.

    Parameters
    ----------
    zmq_subscribe_addr: str
        Address of 0MQ PUB socket. The SUB socket of the monitor subscribes to this address
        once the class is instantiated.
    poll_timeout: float
        Timeout used for polling 0MQ socket. The value does not influence performance.
        It may take longer to stop the background thread or task, if the value is too large.
    max_msgs: int
        Maximum number of messages in the buffer. New messages are ignored if the buffer
        is full. This could happen only if console monitoring is enabled, but messages
        are not read from the buffer.
"""

_doc_ConsoleMonitor_HTTP = """
    Console Monitor API (HTTP). The class implements a monitor for console output
    published by RE Manager over HTTP. The asynchronous version of the class must
    be instantiated in the loop.

    Parameters
    ----------
    parent: class
        Reference to the parent class (or any class). The class must expose the attribute
        ``_client`` that references configured ``httpx`` client.
    poll_period: float
        Period between consecutive requests to HTTP server.
    max_msgs: int
        Maximum number of messages in the buffer. New messages are ignored if the buffer
        is full. This could happen only if console monitoring is enabled, but messages
        are not read from the buffer.
"""

_doc_ConsoleMonitor_enabled = """
    Indicates if monitoring is enabled. Returns ``True`` if monitoring is enabled,
    ``False`` otherwise.

    Examples
    --------

    Synchronous and asyncronous API:

    .. code-block:: python

        is_enabled = RM.console_monitor.enabled
"""

_doc_ConsoleMonitor_enable = """
    Enable monitoring of the console output. Received messages are accumulated in the buffer
    and need to be continuosly read using ``next_msg()`` to prevent buffer from overflowing.
    If the API is called when background thread or task is not running, the buffer is cleared
    and all old messages are discarded. Note, that disabling and then enabling the monitor in
    rapid sequence is unlikely to clear the buffer, because the background thread or task may
    still be running. Use ``clear()`` API to remove messages from the buffer.

    Examples
    --------

    Synchronous and asyncronous API:

    .. code-block:: python

        RM.console_monitor.enable()
        RM.console_monitor.disable()
"""

_doc_ConsoleMonitor_disable = """
    Disable monitoring of the console output. The API does not immediately stop the background thread
    or task. If the monitor is quickly re-enabled, the background thread or task may continue running
    continously.

    Examples
    --------

    Synchronous and asyncronous API:

    .. code-block:: python

        RM.console_monitor.enable()
        RM.console_monitor.disable()
"""

_doc_ConsoleMonitor_disable_wait = """
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
        Wait timeout (ssynchronous API)

    Examples
    --------

    Syncronous API:

    .. code-block:: python

        RM.console_monitor.enable()
        RM.console_monitor.disable_wait()

    Asynchronous API:

    .. code-block:: python

        RM.console_monitor.enable()
        await RM.console_monitor.disable_wait()
"""

_doc_ConsoleMonitor_clear = """
    Clear the message buffer. Removes all messages from the buffer.

    Examples
    --------

    Synchronous and asyncronous API:

    .. code-block:: python

        RM.console_monitor.clear()
"""

_doc_ConsoleMonitor_next_msg = """
    Returns the next message from the buffer. If ``timeout`` is ``None`` or zero, then
    the API returns the next available message. If the buffer contains no messages, the
    function waits for the next published message for ``timeout`` period and raises
    ``RequestTimeoutError`` if no messages were received. If ``timeout is ``None`` or zero
    and the buffer contains no messages, then the function immediately raises
    ``RequestTimeoutError``.

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
        RM.console_output.enable()

        # Run any command that generates console output
        RM.environment_open()
        RM.wait_for_idle()

        try:
            msg = RM.console_output.next_msg()
            print(msg["msg"], end="")
        except RM.RequestTimeoutError:
            pass

        RM.console_output.disable()
        RM.close()

    Asynchronous API:

    .. code-block:: python

        # Make sure RE Manager is started with option '--zmq-publish-console=ON'

        RM = REManagerAPI()
        RM.console_output.enable()

        # Run any command that generates console output
        await RM.environment_open()
        await RM.wait_for_idle()

        try:
            msg = await RM.console_output.next_msg()
            print(msg["msg"], end="")
        except RM.RequestTimeoutError:
            pass

        RM.console_output.disable()
        await RM.close()
"""


class _ConsoleMonitor:
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


class _ConsoleMonitor_Threads(_ConsoleMonitor):
    def __init__(self, *, max_msgs):
        self._msg_queue_max = max_msgs
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


class ConsoleMonitor_ZMQ_Threads(_ConsoleMonitor_Threads):
    # Docstring is maintained separately

    def __init__(self, *, zmq_subscribe_addr, poll_timeout, max_msgs):
        self._zmq_subscribe_addr = zmq_subscribe_addr
        self._monitor_poll_timeout = poll_timeout
        super().__init__(max_msgs=max_msgs)

    def _monitor_init(self):
        self._rco = ReceiveConsoleOutput(
            zmq_subscribe_addr=self._zmq_subscribe_addr, timeout=int(self._monitor_poll_timeout * 1000)
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
                self._msg_queue.put(msg, block=False)
            except TimeoutError:
                # No published messages are detected
                pass
            except queue.Full:
                # Queue is full, ignore the new messages
                pass

    def _clear(self):
        self._msg_queue.queue.clear()


class ConsoleMonitor_HTTP_Threads(_ConsoleMonitor_Threads):
    # Docstring is maintained separately

    def __init__(self, *, parent, poll_period, max_msgs):
        # The parent class is must have ``_client`` attribute with
        #   active httpx client.
        self._parent = parent  # Reference to the parent class
        self._monitor_poll_period = poll_period
        self._console_output_last_msg_uid = ""
        super().__init__(max_msgs=max_msgs)

    def _monitor_init(self):
        ...

    def _thread_receive_msgs(self):
        with self._monitor_thread_lock:
            if not self._monitor_thread_running.is_set():
                return
            self._monitor_thread_running.clear()
            self.clear()
            self._console_output_last_msg_uid = ""

        while True:
            with self._monitor_thread_lock:
                if not self._monitor_enabled:
                    self._monitor_thread_running.set()
                    break
            try:
                client_response = self._parent._client.request(
                    _console_monitor_http_method,
                    _console_monitor_http_endpoint,
                    json={"last_msg_uid": self._console_output_last_msg_uid},
                )
                client_response.raise_for_status()
                response = client_response.json()
                console_output_msgs = response.get("console_output_msgs", [])
                self._console_output_last_msg_uid = response.get("last_msg_uid", "")
                for m in console_output_msgs:
                    self._msg_queue.put(m, block=False)
                ttime.sleep(self._monitor_poll_period)
            except queue.Full:
                # Queue is full, ignore the new messages
                pass
            except Exception:
                # Ignore communication errors. More detailed processing may be added later.
                pass

    def _clear(self):
        self._console_output_last_msg_uid = ""
        self._msg_queue.queue.clear()


class _ConsoleMonitor_Async(_ConsoleMonitor):
    def __init__(self, *, max_msgs):
        self._msg_queue_max = max_msgs
        self._msg_queue = asyncio.Queue(maxsize=max_msgs)

        self._monitor_enabled = False
        self._monitor_task = None  # Thread or asyncio task
        self._monitor_task_running = asyncio.Event()
        self._monitor_task_running.set()

        self._monitor_task_lock = asyncio.Lock()

        self._monitor_init()

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


class ConsoleMonitor_ZMQ_Async(_ConsoleMonitor_Async):
    # Docstring is maintained separately

    def __init__(self, *, zmq_subscribe_addr, poll_timeout, max_msgs):
        self._zmq_subscribe_addr = zmq_subscribe_addr
        self._monitor_poll_timeout = poll_timeout
        super().__init__(max_msgs=max_msgs)

    def _monitor_init(self):
        self._rco = ReceiveConsoleOutputAsync(
            zmq_subscribe_addr=self._zmq_subscribe_addr, timeout=int(self._monitor_poll_timeout * 1000)
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
                self._msg_queue.put_nowait(msg)
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


class ConsoleMonitor_HTTP_Async(_ConsoleMonitor_Async):
    # Docstring is maintained separately

    def __init__(self, *, parent, poll_period, max_msgs):
        # The parent class is must have ``_client`` attribute with
        #   active httpx client.
        self._parent = parent  # Reference to the parent class
        self._monitor_poll_period = poll_period
        self._console_output_last_msg_uid = ""
        super().__init__(max_msgs=max_msgs)

    def _monitor_init(self):
        ...

    async def _task_receive_msgs(self):
        async with self._monitor_task_lock:
            if not self._monitor_task_running.is_set():
                return
            self._monitor_task_running.clear()
            self.clear()
            self._console_output_last_msg_uid = ""

        while True:
            async with self._monitor_task_lock:
                if not self._monitor_enabled:
                    self._monitor_task_running.set()
                    break

            try:
                client_response = await self._parent._client.request(
                    _console_monitor_http_method,
                    _console_monitor_http_endpoint,
                    json={"last_msg_uid": self._console_output_last_msg_uid},
                )
                client_response.raise_for_status()
                response = client_response.json()
                console_output_msgs = response.get("console_output_msgs", [])
                self._console_output_last_msg_uid = response.get("last_msg_uid", "")
                for m in console_output_msgs:
                    self._msg_queue.put_nowait(m)
                await asyncio.sleep(self._monitor_poll_period)
            except asyncio.QueueFull:
                # Queue is full, ignore the new messages
                pass
            except Exception:
                # Ignore communication errors. More detailed processing may be added later.
                pass

    def _clear(self):
        try:
            self._console_output_last_msg_uid = ""
            while True:
                self._msg_queue.get_nowait()
        except asyncio.QueueEmpty:
            pass


_ConsoleMonitor.enabled.__doc__ = _doc_ConsoleMonitor_enabled
_ConsoleMonitor.enable.__doc__ = _doc_ConsoleMonitor_enable
_ConsoleMonitor.disable.__doc__ = _doc_ConsoleMonitor_disable
_ConsoleMonitor.clear.__doc__ = _doc_ConsoleMonitor_clear

_ConsoleMonitor_Threads.disable_wait.__doc__ = _doc_ConsoleMonitor_disable_wait
_ConsoleMonitor_Threads.next_msg.__doc__ = _doc_ConsoleMonitor_next_msg

ConsoleMonitor_ZMQ_Threads.__doc__ = _doc_ConsoleMonitor_ZMQ
ConsoleMonitor_HTTP_Threads.__doc__ = _doc_ConsoleMonitor_HTTP

_ConsoleMonitor_Async.disable_wait.__doc__ = _doc_ConsoleMonitor_disable_wait
_ConsoleMonitor_Async.next_msg.__doc__ = _doc_ConsoleMonitor_next_msg

ConsoleMonitor_ZMQ_Async.__doc__ = _doc_ConsoleMonitor_ZMQ
ConsoleMonitor_HTTP_Async.__doc__ = _doc_ConsoleMonitor_HTTP
