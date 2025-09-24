"""
WebSocket-based RE Manager API implementation (async version).

This module provides an asynchronous WebSocket-based interface to the RE Manager
that allows real-time bidirectional communication for:
- Real-time queue status updates
- Plan execution progress monitoring  
- Console output streaming
- Device status coordination
- Conflict prevention with other services
"""

import asyncio
from .._defaults import (
    default_allow_request_fail_exceptions,
    default_console_monitor_max_lines,
    default_console_monitor_max_msgs,
    default_console_monitor_poll_period,
    default_status_expiration_period,
    default_status_polling_period,
    default_ws_connection_timeout,
    default_ws_heartbeat_interval,
    default_ws_max_reconnect_attempts,
    default_ws_reconnect_delay,
    default_ws_server_uri,
)
from ..api_async import API_Async_Mixin
from ..api_docstrings import _doc_REManagerAPI_WS
from ..comm_async import ReManagerComm_WS_Async


class REManagerAPI(ReManagerComm_WS_Async, API_Async_Mixin):
    """
    WebSocket-based RE Manager API (asynchronous version).
    
    This class provides real-time communication with the RE Manager through
    WebSocket connections, enabling immediate notifications of status changes
    and bidirectional command execution.
    """
    
    def __init__(
        self,
        *,
        ws_server_uri=default_ws_server_uri,
        ws_auth_provider=None,
        ws_connection_timeout=default_ws_connection_timeout,
        ws_heartbeat_interval=default_ws_heartbeat_interval,
        ws_max_reconnect_attempts=default_ws_max_reconnect_attempts,
        ws_reconnect_delay=default_ws_reconnect_delay,
        console_monitor_poll_period=default_console_monitor_poll_period,
        console_monitor_max_msgs=default_console_monitor_max_msgs,
        console_monitor_max_lines=default_console_monitor_max_lines,
        request_fail_exceptions=default_allow_request_fail_exceptions,
        status_expiration_period=default_status_expiration_period,
        status_polling_period=default_status_polling_period,
        loop=None,
    ):
        params_comm = {
            "ws_server_uri": ws_server_uri,
            "ws_auth_provider": ws_auth_provider,
            "ws_connection_timeout": ws_connection_timeout,
            "ws_heartbeat_interval": ws_heartbeat_interval,
            "ws_max_reconnect_attempts": ws_max_reconnect_attempts,
            "ws_reconnect_delay": ws_reconnect_delay,
            "console_monitor_poll_period": console_monitor_poll_period,
            "console_monitor_max_msgs": console_monitor_max_msgs,
            "console_monitor_max_lines": console_monitor_max_lines,
            "request_fail_exceptions": request_fail_exceptions,
        }
        params_api = {
            "status_expiration_period": status_expiration_period,
            "status_polling_period": status_polling_period,
        }

        try:
            # 'get_running_loop' is raising RuntimeError if running outside async context
            asyncio.get_running_loop()
            self._init(params_comm, params_api)
        except RuntimeError:
            self._validate_loop(loop)
            f = asyncio.run_coroutine_threadsafe(self._init_async(params_comm, params_api), loop)
            f.result(timeout=10)  # Use long timeout.

    def _init(self, params_comm, params_api):
        ReManagerComm_WS_Async.__init__(self, **params_comm)
        API_Async_Mixin.__init__(self, **params_api)

    async def _init_async(self, params_comm, params_api):
        self._init(params_comm, params_api)

    async def subscribe_queue_updates(self, callback=None):
        """Subscribe to real-time queue status updates."""
        return await self.subscribe("queue_status", callback)
        
    async def subscribe_execution_progress(self, callback=None):
        """Subscribe to plan execution progress updates."""
        return await self.subscribe("execution_status", callback)
        
    async def subscribe_console_output(self, callback=None):
        """Subscribe to real-time console output stream.""" 
        return await self.subscribe("console_output", callback)
        
    async def subscribe_device_status(self, callback=None, device_filter=None):
        """Subscribe to device status updates with optional filtering."""
        return await self.subscribe("device_updates", callback)
        
    async def request_device_lock(self, device_name, user_id=None, timeout=None):
        """Request exclusive lock on a device for manual control."""
        params = {
            "device_name": device_name,
            "user_id": user_id,
            "timeout": timeout
        }
        return await self.send_request(method="device_lock", params=params)
        
    async def release_device_lock(self, device_name, user_id=None, lock_key=None):
        """Release exclusive lock on a device."""
        params = {
            "device_name": device_name, 
            "user_id": user_id,
            "lock_key": lock_key
        }
        return await self.send_request(method="device_unlock", params=params)


REManagerAPI.__doc__ = _doc_REManagerAPI_WS