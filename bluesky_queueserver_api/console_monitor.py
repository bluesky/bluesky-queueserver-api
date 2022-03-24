import queue
import threading

from bluesky_queueserver import ReceiveConsoleOutput

from .comm_base import RequestTimeoutError


class _ConsoleMonitor_ZMQ_Threads:
    """
    Parameters
    ----------
    zmq_subscribe_addr: str
        Address of 0MQ PUB socket. The monitor subscribes to this address once enabled.
    poll_timeout: float
        Timeout used for polling 0MQ socket. The value does not influence performance,
        except that longer timeout may require longer to disable polling.
    max_msgs: int
        Maximum number of messages in the buffer. New messages are ignored if the buffer
        is full. This could happen only if console monitoring is enabled, but messages
        are not read from the buffer.
    """

    def __init__(self, *, zmq_subscribe_addr, poll_timeout, max_msgs):
        self._zmq_subscribe_addr = zmq_subscribe_addr
        self._monitor_poll_timeout = poll_timeout

        self._msg_queue = queue.Queue(maxsize=max_msgs)

        self._monitor_enabled = False
        self._monitor_thread = None  # Thread or asyncio task
        self._monitor_thread_running = False
        self._monitor_thread_lock = threading.Lock()

        self._monitor_init()

    def _monitor_init(self):
        self._rco = ReceiveConsoleOutput(
            zmq_subscribe_addr=self._zmq_subscribe_addr, timeout=int(self._monitor_poll_timeout * 1000)
        )

    def _thread_receive_msgs(self):
        with self._monitor_thread_lock:
            if self._monitor_thread_running:
                return
            self._monitor_thread_running = True
            self.clear()

        self._rco.subscribe()

        while True:
            with self._monitor_thread_lock:
                if not self._monitor_enabled:
                    self._monitor_thread_running = False
                    self._rco.unsubscribe()
                    break
            try:
                msg = self._rco.recv()
                self._msg_queue.put(msg, block=False)
            except TimeoutError:
                # No public messages are detected
                pass
            except queue.Full:
                # Queue is full, ignore the new messages
                pass

    @property
    def enabled(self):
        """
        Returns ``True`` if monitoring is enabled, ``False`` otherwise.
        """
        return self._monitor_enabled

    def _monitor_enable(self):
        self._monitor_thread = threading.Thread(
            target=self._thread_receive_msgs, name="QS API - Console monitoring", daemon=True
        )
        self._monitor_enabled = True
        self._monitor_thread.start()

    def enable(self):
        """
        Enable monitoring of the console output. Received messages are accumulated in the buffer
        and need to be continuosly read using ``next_msg()`` to prevent buffer from overflowing.
        This method clears the buffer that contains the cached messages.
        """
        if not self._monitor_enabled:
            self._monitor_enable()

    def disable(self):
        """
        Disable monitoring of the console output. The operation is not instant. Check ``enabled``
        property to detect when the operation is completed. Monitoring can not be restarted before
        the operation is completed.
        """
        self._monitor_enabled = False

    def clear(self):
        """
        Immediately clear all messages stored in the buffer
        """
        self._msg_queue.queue.clear()

    def next_msg(self, timeout=None):
        """
        Returns the next message.

        Parameters
        ----------
        timeout: float or None
            If timeout is positive floating point number, then waits for the next message.
            Returns the message if the message is received or raises ``RequestTimeoutError` if
            no message is received. If ``timeout`` is ``None`` or 0, then returns the message
            if it is immediately available or raises ``RequestTimeoutError`` if the message is not
            available

        Raises
        ------
        RequestTimeoutError
            No messages were received during timeout period.

        Examples
        --------
        .. code-block:: python

            # Make sure RE Manager is started with option '--zmq-publish-consol=ON'

            RM = REManagerAPI()
            RM.console_output.enable()

            # Run some command that generates console output
            RM.environment_open()

            try:
                print(RM.console_output.next_msg(), end="")
            except RM.RequestTimeoutError:
                pass

            RM.console_output.disable()

        """
        block = bool(timeout)
        try:
            return self._msg_queue.get(block=block, timeout=timeout)
        except queue.Empty:
            raise RequestTimeoutError(f"No message was received (timeout={timeout})", request={})

    def __del__(self):
        self.disable()
