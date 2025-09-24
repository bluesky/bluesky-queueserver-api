"""
WebSocket-based RE Manager API implementation (sync version).

This module provides a WebSocket-based interface to the RE Manager that allows
real-time bidirectional communication for:
- Real-time queue status updates
- Plan execution progress monitoring  
- Console output streaming
- Device status coordination
- Conflict prevention with other services
"""

from .._defaults import (
    default_allow_request_fail_exceptions,
    default_console_monitor_max_lines,
    default_console_monitor_max_msgs,
    default_console_monitor_poll_period,
    default_status_expiration_period,
    default_status_polling_period,
    default_ws_connect_timeout,
    default_ws_heartbeat_interval,
    default_ws_server_uri,
)
from ..api_docstrings import _doc_REManagerAPI_WS
from ..api_threads import API_Threads_Mixin
from ..comm_threads import ReManagerComm_WS_Threads


class REManagerAPI(ReManagerComm_WS_Threads, API_Threads_Mixin):
    """
    WebSocket-based RE Manager API (synchronous version).
    
    This class provides real-time communication with the RE Manager through
    WebSocket connections, enabling immediate notifications of status changes
    and bidirectional command execution.
    """
    
    def __init__(
        self,
        *,
        ws_server_uri=default_ws_server_uri,
        connect_timeout=default_ws_connect_timeout,
        heartbeat_interval=default_ws_heartbeat_interval,
        console_monitor_poll_period=default_console_monitor_poll_period,
        console_monitor_max_msgs=default_console_monitor_max_msgs,
        console_monitor_max_lines=default_console_monitor_max_lines,
        request_fail_exceptions=default_allow_request_fail_exceptions,
        status_expiration_period=default_status_expiration_period,
        status_polling_period=default_status_polling_period,
    ):
        ReManagerComm_WS_Threads.__init__(
            self,
            ws_server_uri=ws_server_uri,
            connect_timeout=connect_timeout,
            heartbeat_interval=heartbeat_interval,
            console_monitor_poll_period=console_monitor_poll_period,
            console_monitor_max_msgs=console_monitor_max_msgs,
            console_monitor_max_lines=console_monitor_max_lines,
            request_fail_exceptions=request_fail_exceptions,
        )
        API_Threads_Mixin.__init__(
            self,
            status_expiration_period=status_expiration_period,
            status_polling_period=status_polling_period,
        )

    def subscribe_queue_updates(self, callback):
        """Subscribe to real-time queue status updates."""
        return self._subscribe_topic("queue_updates", callback)
        
    def subscribe_execution_progress(self, callback):
        """Subscribe to plan execution progress updates."""
        return self._subscribe_topic("execution_progress", callback)
        
    def subscribe_console_output(self, callback):
        """Subscribe to real-time console output stream."""
        return self._subscribe_topic("console_output", callback)
        
    def subscribe_device_status(self, callback, device_filter=None):
        """Subscribe to device status updates with optional filtering."""
        return self._subscribe_topic("device_status", callback, filters={"devices": device_filter})
        
    def request_device_lock(self, device_name, user_id, timeout=None):
        """Request exclusive lock on a device for manual control."""
        params = {
            "device": device_name,
            "user_id": user_id,
            "timeout": timeout
        }
        return self.send_request(method="device_lock_request", params=params)
        
    def release_device_lock(self, device_name, user_id):
        """Release exclusive lock on a device."""
        params = {
            "device": device_name, 
            "user_id": user_id
        }
        return self.send_request(method="device_lock_release", params=params)


REManagerAPI.__doc__ = _doc_REManagerAPI_WS