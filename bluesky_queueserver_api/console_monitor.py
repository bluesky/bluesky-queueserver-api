import asyncio
import queue
import threading
import time as ttime
import uuid

from bluesky_queueserver import ReceiveConsoleOutput, ReceiveConsoleOutputAsync

from .comm_base import RequestTimeoutError

_console_monitor_http_method = "GET"
_console_monitor_http_endpoint = "/api/console_output_update"

_doc_ConsoleMonitor_ZMQ = """
    Console Monitor API (0MQ). The class implements a monitor for console output
    published by RE Manager over 0MQ. The asynchronous version of the class must
    be instantiated in the loop.

    Parameters
    ----------
    zmq_info_addr: str
        Address of 0MQ PUB socket. The SUB socket of the monitor subscribes to this address
        once the class is instantiated.
    poll_timeout: float
        Timeout used for polling 0MQ socket. The value does not influence performance.
        It may take longer to stop the background thread or task, if the value is too large.
    max_msgs: int
        Maximum number of messages in the buffer. New messages are ignored if the buffer
        is full. This could happen only if console monitoring is enabled, but messages
        are not read from the buffer. Setting the value to 0 disables collection of messages
        in the buffer.
    max_lines: int
        Maximum number of lines in the text buffer. Setting the value to 0 disables processing
        of text messages and generation of text output.
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
        are not read from the buffer. Setting the value to 0 disables collection of messages
        in the buffer.
    max_lines: int
        Maximum number of lines in the text buffer. Setting the value to 0 disables processing
        of text messages and generation of text output.
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

_doc_ConsoleMonitor_text_uid = """
    Returns UID of the current text buffer. UID is changed whenever the contents
    of the buffer is changed. Monitor UID to minimize the number of data reloads
    (if necessary).

    Examples
    --------
    Synchronous API

    .. code-block:: python

        RM.console_monitor.enable()

        uid = RM.console_monitor.text_uid
        while True:
            uid_new = RM.console_monitor.text_uid
            if uid_new != uid:
                uid = uid_new
                text = RM.console_monitor.text()
                # Use 'text'
            ttime.sleep(0.1)

    Asynchronous API

    .. code-block:: python

        RM.console_monitor.enable()

        uid = RM.console_monitor.text_uid
        while True:
            uid_new = RM.console_monitor.text_uid
            if uid_new != uid:
                uid = uid_new
                text = await RM.console_monitor.text()
                # Use 'text'
            asyncio.sleep(0.1)
"""

_doc_ConsoleMonitor_text_max_lines = """
    Get/set the maximum size of the text buffer. The new buffer size is
    applied to the existing buffer, removing extra messages if necessary.

    Examples
    --------
    Synchronous and asynchronous API

    .. code-block:: python

        # Get the maximum number of lines
        n_lines = RM.console_monitor.text_max_lines

        # Set the maximum number of lines
        RM.console_monitor.text_max_lines = 1000
"""

_doc_ConsoleMonitor_text = """
    Returns text representation of console output. Monitor ``text_uid``
    property to check if text buffer was modified. The parameter ``nlines``
    determines the maximum number of lines of text returned by the function.

    Parameters
    ----------
    nlines: int
        Number of lines to return. The value determines the maximum number of lines
        of text returned by the function. The function returns ``""`` (empty string)
        if the value is ``0`` or negative.

    Returns
    -------
    text: str
        String representing recent console output. The maximum number of
        lines is determined by ``text_max_lines``.

    Examples
    --------
    Synchronous API

    .. code-block:: python

        RM = REManagerAPI()
        RM.console_monitor.enable()

        # Wait for RE Manager to produce some output
        ttime.sleep(20)

        text = RM.console_monitor.text()
        print(text)

        # Return the last 10 lines
        text = RM.console_monitor.text(10)
        print(text)

        RM.console_monitor.disable()

    Asynchronous API

    .. code-block:: python

        RM = REManagerAPI()
        RM.console_monitor.enable()

        # Wait for RE Manager to produce some output
        await asyncio.sleep(20)

        text = await RM.console_monitor.text()
        print(text)

        # Return the last 10 lines
        text = await RM.console_monitor.text(10)
        print(text)

        RM.console_monitor.disable()
"""


class _ConsoleMonitor:
    def __init__(self, *, max_lines):
        self._monitor_enabled = False
        self._monitor_init()

        self._buffers_modified_event = threading.Event()

        self._text = {}
        self._set_new_text_uid()

        self._text_buffer = []
        self._text_clear()
        self._text_max_lines = max(max_lines, 0)

    def _text_generate(self, nlines):
        n_text_buffer = len(self._text_buffer)
        nlines = max(nlines, 0) if (nlines is not None) else n_text_buffer

        if self._text_buffer and self._text_buffer[-1] == "":
            nlines = min(nlines, n_text_buffer - 1)
            if nlines not in self._text:
                text = "\n".join(self._text_buffer[-nlines - 1 : -1])
                self._text[nlines] = text
            else:
                text = self._text[nlines]
        else:
            nlines = min(nlines, n_text_buffer)
            if nlines not in self._text:
                text = "\n".join(self._text_buffer[-nlines:])
                self._text[nlines] = text
            else:
                text = self._text[nlines]
        return text

    def _set_new_text_uid(self):
        self._text_uid = str(uuid.uuid4())

    def _text_clear(self):
        self._text.clear()
        self._set_new_text_uid()

        self._text_line = 0
        self._text_pos = 0
        self._text_buffer.clear()

    def _add_msg_to_text_buffer(self, response):
        # Setting max number of lines to 0 disables text processing
        if not self._text_max_lines:
            return

        msg = response["msg"]

        pattern_new_line = "\n"
        pattern_cr = "\r"
        pattern_up_one_line = "\x1B\x5B\x41"  # ESC [#A

        patterns = {"new_line": pattern_new_line, "cr": pattern_cr, "one_line_up": pattern_up_one_line}

        while msg:
            indices = {k: msg.find(v) for k, v in patterns.items()}
            indices_nonzero = [_ for _ in indices.values() if (_ >= 0)]
            next_ind = min(indices_nonzero) if indices_nonzero else len(msg)

            # The following algorithm requires that there is at least one line in the list.
            if not self._text_buffer:
                self._text_buffer = [""]
                self._text_line = 0
                self._text_pos = 0

            if next_ind != 0:
                # Add a line to the current line and position
                substr = msg[:next_ind]
                msg = msg[next_ind:]

                # Extend the current line with spaces if needed
                line_len = len(self._text_buffer[self._text_line])
                if line_len < self._text_pos:
                    self._text_buffer[self._text_line] += " " * (self._text_pos - line_len)

                line = self._text_buffer[self._text_line]
                self._text_buffer[self._text_line] = (
                    line[: self._text_pos] + substr + line[self._text_pos + len(substr) :]
                )
                self._text_pos = self._text_pos + len(substr)

            elif indices["new_line"] == 0:
                self._text_line += 1
                if self._text_line >= len(self._text_buffer):
                    self._text_buffer.insert(self._text_line, "")
                self._text_pos = 0
                msg = msg[len(patterns["new_line"]) :]

            elif indices["cr"] == 0:
                self._text_pos = 0
                msg = msg[len(patterns["cr"]) :]

            elif indices["one_line_up"] == 0:
                if self._text_line:
                    self._text_line -= 1
                msg = msg[len(patterns["one_line_up"]) :]

        self._set_new_text_uid()

    def _adjust_text_buffer_size(self):
        if self._text_buffer and self._text_buffer[-1] == "":
            # Do not count an empty string at the end
            max_lines = self._text_max_lines + 1
        else:
            max_lines = self._text_max_lines

        if len(self._text_buffer) > max_lines:
            # Remove extra lines from the beginning of the list
            n_remove = len(self._text_buffer) - max_lines
            # In majority of cases only 1 (or a few) elements are removed
            for _ in range(n_remove):
                self._text_buffer.pop(0)
            self._text_line = max(self._text_line - n_remove, 0)

        self._set_new_text_uid()

    def _monitor_init(self):
        raise NotImplementedError()

    def _clear(self):
        raise NotImplementedError()

    def _monitor_enable(self):
        raise NotImplementedError()

    @property
    def text_uid(self):
        # Docstring is maintained separately
        return self._text_uid

    @property
    def text_max_lines(self):
        # Docstring is maintained separately
        return self._text_max_lines

    @text_max_lines.setter
    def text_max_lines(self, max_lines):
        # Docstring is maintained separately
        max_lines = max(max_lines, 0)
        self._text_max_lines = max_lines
        self._adjust_text_buffer_size()

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
    def __init__(self, *, max_msgs, max_lines):
        self._msg_queue_max = max(max_msgs, 0)
        self._msg_queue = queue.Queue(maxsize=max_msgs)

        self._monitor_enabled = False
        self._monitor_thread = None  # Thread or asyncio task
        self._monitor_thread_running = threading.Event()
        self._monitor_thread_running.set()

        self._monitor_thread_lock = threading.Lock()
        self._text_buffer_lock = threading.Lock()

        super().__init__(max_lines=max_lines)

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

    def text(self, nlines=None):
        # Docstring is maintained separately
        with self._text_buffer_lock:
            text = self._text_generate(nlines=nlines)
        return text


class ConsoleMonitor_ZMQ_Threads(_ConsoleMonitor_Threads):
    # Docstring is maintained separately

    def __init__(self, *, zmq_info_addr, poll_timeout, max_msgs, max_lines):
        self._zmq_subscribe_addr = zmq_info_addr
        self._monitor_poll_timeout = poll_timeout
        super().__init__(max_msgs=max_msgs, max_lines=max_lines)

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

                with self._text_buffer_lock:
                    self._add_msg_to_queue(msg)
                    self._add_msg_to_text_buffer(msg)
                    self._adjust_text_buffer_size()

            except TimeoutError:
                # No published messages are detected
                pass
            except queue.Full:
                # Queue is full, ignore the new messages
                pass

    def _clear(self):
        self._msg_queue.queue.clear()
        self._text_clear()


class ConsoleMonitor_HTTP_Threads(_ConsoleMonitor_Threads):
    # Docstring is maintained separately

    def __init__(self, *, parent, poll_period, max_msgs, max_lines):
        # The parent class is must have ``_client`` attribute with
        #   active httpx client.
        self._parent = parent  # Reference to the parent class
        self._monitor_poll_period = poll_period
        self._console_output_last_msg_uid = ""
        super().__init__(max_msgs=max_msgs, max_lines=max_lines)

    def _monitor_init(self): ...

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
                headers = self._parent._prepare_headers()
                kwargs = {"json": {"last_msg_uid": self._console_output_last_msg_uid}}
                if headers:
                    kwargs.update({"headers": headers})
                client_response = self._parent._client.request(
                    _console_monitor_http_method, _console_monitor_http_endpoint, **kwargs
                )
                client_response.raise_for_status()
                response = client_response.json()
                console_output_msgs = response.get("console_output_msgs", [])
                self._console_output_last_msg_uid = response.get("last_msg_uid", "")

                with self._text_buffer_lock:
                    for m in console_output_msgs:
                        self._add_msg_to_queue(m)
                        self._add_msg_to_text_buffer(m)
                    self._adjust_text_buffer_size()

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
        self._text_clear()


class _ConsoleMonitor_Async(_ConsoleMonitor):
    def __init__(self, *, max_msgs, max_lines):
        self._msg_queue_max = max_msgs
        self._msg_queue = asyncio.Queue(maxsize=max_msgs)

        self._monitor_task = None  # Thread or asyncio task
        self._monitor_task_running = asyncio.Event()
        self._monitor_task_running.set()

        self._monitor_task_lock = asyncio.Lock()
        self._text_buffer_lock = asyncio.Lock()

        super().__init__(max_lines=max_lines)

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

    async def text(self, nlines=None):
        # Docstring is maintained separately
        async with self._text_buffer_lock:
            text = self._text_generate(nlines=nlines)
        return text


class ConsoleMonitor_ZMQ_Async(_ConsoleMonitor_Async):
    # Docstring is maintained separately

    def __init__(self, *, zmq_info_addr, poll_timeout, max_msgs, max_lines):
        self._zmq_subscribe_addr = zmq_info_addr
        self._monitor_poll_timeout = poll_timeout
        super().__init__(max_msgs=max_msgs, max_lines=max_lines)

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

                async with self._text_buffer_lock:
                    self._add_msg_to_queue(msg)
                    self._add_msg_to_text_buffer(msg)
                    self._adjust_text_buffer_size()

            except TimeoutError:
                # No published messages are detected
                pass
            except asyncio.QueueFull:
                # Queue is full, ignore the new messages
                pass

    def _clear(self):
        self._text_clear()
        try:
            while True:
                self._msg_queue.get_nowait()
        except asyncio.QueueEmpty:
            pass


class ConsoleMonitor_HTTP_Async(_ConsoleMonitor_Async):
    # Docstring is maintained separately

    def __init__(self, *, parent, poll_period, max_msgs, max_lines):
        # The parent class is must have ``_client`` attribute with
        #   active httpx client.
        self._parent = parent  # Reference to the parent class
        self._monitor_poll_period = poll_period
        self._console_output_last_msg_uid = ""
        super().__init__(max_msgs=max_msgs, max_lines=max_lines)

    def _monitor_init(self): ...

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
                headers = self._parent._prepare_headers()
                kwargs = {"json": {"last_msg_uid": self._console_output_last_msg_uid}}
                if headers:
                    kwargs.update({"headers": headers})

                client_response = await self._parent._client.request(
                    _console_monitor_http_method, _console_monitor_http_endpoint, **kwargs
                )
                client_response.raise_for_status()
                response = client_response.json()
                console_output_msgs = response.get("console_output_msgs", [])
                self._console_output_last_msg_uid = response.get("last_msg_uid", "")

                async with self._text_buffer_lock:
                    for m in console_output_msgs:
                        self._add_msg_to_queue(m)
                        self._add_msg_to_text_buffer(m)
                    self._adjust_text_buffer_size()

                await asyncio.sleep(self._monitor_poll_period)
            except asyncio.QueueFull:
                # Queue is full, ignore the new messages
                pass
            except Exception:
                # Ignore communication errors. More detailed processing may be added later.
                pass

    def _clear(self):
        self._text_clear()
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
_ConsoleMonitor.text_uid.__doc__ = _doc_ConsoleMonitor_text_uid
_ConsoleMonitor.text_max_lines.__doc__ = _doc_ConsoleMonitor_text_max_lines

_ConsoleMonitor_Threads.disable_wait.__doc__ = _doc_ConsoleMonitor_disable_wait
_ConsoleMonitor_Threads.next_msg.__doc__ = _doc_ConsoleMonitor_next_msg
_ConsoleMonitor_Threads.text.__doc__ = _doc_ConsoleMonitor_text

ConsoleMonitor_ZMQ_Threads.__doc__ = _doc_ConsoleMonitor_ZMQ
ConsoleMonitor_HTTP_Threads.__doc__ = _doc_ConsoleMonitor_HTTP

_ConsoleMonitor_Async.disable_wait.__doc__ = _doc_ConsoleMonitor_disable_wait
_ConsoleMonitor_Async.next_msg.__doc__ = _doc_ConsoleMonitor_next_msg
_ConsoleMonitor_Async.text.__doc__ = _doc_ConsoleMonitor_text

ConsoleMonitor_ZMQ_Async.__doc__ = _doc_ConsoleMonitor_ZMQ
ConsoleMonitor_HTTP_Async.__doc__ = _doc_ConsoleMonitor_HTTP
