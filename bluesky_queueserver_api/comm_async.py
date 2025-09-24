import asyncio
import json
import logging
from typing import Any, Callable, Dict, Optional

import httpx
import websockets
from bluesky_queueserver import ZMQCommSendAsync

from .api_docstrings import (
    _doc_api_api_scopes,
    _doc_api_apikey_delete,
    _doc_api_apikey_info,
    _doc_api_apikey_new,
    _doc_api_login,
    _doc_api_logout,
    _doc_api_principal_info,
    _doc_api_session_refresh,
    _doc_api_session_revoke,
    _doc_api_whoami,
    _doc_close,
    _doc_send_request,
)
from .comm_base import ReManagerAPI_HTTP_Base, ReManagerAPI_WS_Base, ReManagerAPI_ZMQ_Base
from .console_monitor import ConsoleMonitor_HTTP_Async, ConsoleMonitor_ZMQ_Async


class ReManagerComm_ZMQ_Async(ReManagerAPI_ZMQ_Base):
    def _init_console_monitor(self):
        self._console_monitor = ConsoleMonitor_ZMQ_Async(
            zmq_info_addr=self._zmq_info_addr,
            zmq_encoding=self._zmq_encoding,
            poll_timeout=self._console_monitor_poll_timeout,
            max_msgs=self._console_monitor_max_msgs,
            max_lines=self._console_monitor_max_lines,
        )

    def _create_client(
        self,
        *,
        zmq_control_addr,
        zmq_encoding,
        timeout_recv,
        timeout_send,
        zmq_public_key,
    ):
        return ZMQCommSendAsync(
            zmq_server_address=zmq_control_addr,
            encoding=zmq_encoding,
            timeout_recv=int(timeout_recv * 1000),  # Convert to ms
            timeout_send=int(timeout_send * 1000),  # Convert to ms
            raise_exceptions=True,
            server_public_key=zmq_public_key,
        )

    async def send_request(self, *, method, params=None):
        try:
            response = await self._client.send_message(method=method, params=params)
        except Exception:
            self._process_comm_exception(method=method, params=params)
        self._check_response(request={"method": method, "params": params}, response=response)

        return response

    async def close(self):
        self._is_closing = True
        await self._console_monitor.disable_wait(timeout=self._console_monitor_poll_timeout * 10)
        self._client.close()

    def __del__(self):
        self._is_closing = True


class ReManagerComm_HTTP_Async(ReManagerAPI_HTTP_Base):
    def _init_console_monitor(self):
        self._console_monitor = ConsoleMonitor_HTTP_Async(
            parent=self,
            poll_period=self._console_monitor_poll_period,
            max_msgs=self._console_monitor_max_msgs,
            max_lines=self._console_monitor_max_lines,
        )

    def _create_client(self, http_server_uri, timeout):
        timeout = self._adjust_timeout(timeout)
        return httpx.AsyncClient(base_url=http_server_uri, timeout=timeout)

    async def _simple_request(
        self, *, method, params=None, url_params=None, headers=None, data=None, timeout=None
    ):
        """
        The code that formats and sends a simple request.
        """
        try:
            client_response = None
            request_method, endpoint, payload = self._prepare_request(method=method, params=params)
            headers = headers or self._prepare_headers()
            kwargs = {"json": payload}
            if url_params:
                kwargs.update({"params": url_params})
            if headers:
                kwargs.update({"headers": headers})
            if data:
                kwargs.update({"data": data})
            if timeout is not None:
                kwargs.update({"timeout": self._adjust_timeout(timeout)})
            client_response = await self._client.request(request_method, endpoint, **kwargs)
            response = self._process_response(client_response=client_response)

        except Exception:
            response = self._process_comm_exception(method=method, params=params, client_response=client_response)

        self._check_response(request={"method": method, "params": params}, response=response)

        return response

    async def send_request(
        self,
        *,
        method,
        params=None,
        url_params=None,
        headers=None,
        data=None,
        timeout=None,
        auto_refresh_session=True,
    ):
        # Docstring is maintained separately
        refresh = False
        request_params = {
            "method": method,
            "params": params,
            "url_params": url_params,
            "headers": headers,
            "data": data,
            "timeout": timeout,
        }
        try:
            response = await self._simple_request(**request_params)
        except self.HTTPClientError as ex:
            # The session is supposed to be automatically refreshed only if the expired token is passed
            #   to the server. Otherwise the request is expected to fail.
            if (
                auto_refresh_session
                and ("401: Access token has expired" in str(ex))
                and (self.auth_method == self.AuthorizationMethods.TOKEN)
                and (self.auth_key[1] is not None)
            ):
                refresh = True
            else:
                raise

        if refresh:
            try:
                await self.session_refresh()
            except Exception as ex:
                print(f"Failed to refresh session: {ex}")

            # Try calling the API with the new token (or the old one if refresh failed).
            response = await self._simple_request(**request_params)

        return response

    async def login(self, username=None, *, password=None, provider=None):
        # Docstring is maintained separately
        endpoint, data = self._prepare_login(username=username, password=password, provider=provider)
        response = await self.send_request(method=("POST", endpoint), data=data, timeout=self._timeout_login)
        response = self._process_login_response(response=response)
        return response

    async def session_refresh(self, *, refresh_token=None):
        # Docstring is maintained separately
        refresh_token = self._prepare_refresh_session(refresh_token=refresh_token)
        response = await self.send_request(method="session_refresh", params={"refresh_token": refresh_token})
        response = self._process_login_response(response=response)
        return response

    async def session_revoke(self, *, session_uid, token=None, api_key=None):
        # Docstring is maintained separately
        method, headers = self._prepare_session_revoke(session_uid=session_uid, token=token, api_key=api_key)
        kwargs = {"headers": headers, "auto_refresh_session": False} if headers else {}
        response = await self.send_request(method=method, **kwargs)
        return response

    async def apikey_new(self, *, expires_in, scopes=None, note=None, principal_uid=None):
        # Docstring is maintained separately
        method, request_params = self._prepare_apikey_new(
            expires_in=expires_in, scopes=scopes, note=note, principal_uid=principal_uid
        )
        response = await self.send_request(method=method, params=request_params)
        return response

    async def apikey_info(self, *, api_key=None):
        # Docstring is maintained separately
        headers = self._prepare_apikey_info(api_key=api_key)
        kwargs = {"headers": headers, "auto_refresh_session": False} if headers else {}
        response = await self.send_request(method="apikey_info", **kwargs)
        return response

    async def apikey_delete(self, *, first_eight, token=None, api_key=None):
        # Docstring is maintained separately
        url_params, headers = self._prepare_apikey_delete(first_eight=first_eight, token=token, api_key=api_key)
        kwargs = {"headers": headers, "auto_refresh_session": False} if headers else {}
        response = await self.send_request(method="apikey_delete", url_params=url_params, **kwargs)
        return response

    async def whoami(self, *, token=None, api_key=None):
        # Docstring is maintained separately
        headers = self._prepare_whoami(token=token, api_key=api_key)
        kwargs = {"headers": headers, "auto_refresh_session": False} if headers else {}
        response = await self.send_request(method="whoami", **kwargs)
        return response

    async def principal_info(self, *, principal_uid=None):
        # Docstring is maintained separately
        method = self._prepare_principal_info(principal_uid=principal_uid)
        response = await self.send_request(method=method)
        return response

    async def api_scopes(self, *, token=None, api_key=None):
        # Docstring is maintained separately
        headers = self._prepare_whoami(token=token, api_key=api_key)
        kwargs = {"headers": headers, "auto_refresh_session": False} if headers else {}
        response = await self.send_request(method="api_scopes", **kwargs)
        return response

    async def logout(self):
        response = await self.send_request(method="logout")
        self.set_authorization_key()  # Clear authorization keys
        return response

    async def close(self):
        self._is_closing = True
        await self._console_monitor.disable_wait(timeout=self._console_monitor_poll_period * 10)
        await self._client.aclose()

    def __del__(self):
        self._is_closing = True


ReManagerComm_ZMQ_Async.send_request.__doc__ = _doc_send_request
ReManagerComm_HTTP_Async.send_request.__doc__ = _doc_send_request
ReManagerComm_ZMQ_Async.close.__doc__ = _doc_close
ReManagerComm_HTTP_Async.close.__doc__ = _doc_close
ReManagerComm_HTTP_Async.login.__doc__ = _doc_api_login
ReManagerComm_HTTP_Async.session_refresh.__doc__ = _doc_api_session_refresh
ReManagerComm_HTTP_Async.session_revoke.__doc__ = _doc_api_session_revoke
ReManagerComm_HTTP_Async.apikey_new.__doc__ = _doc_api_apikey_new
ReManagerComm_HTTP_Async.apikey_info.__doc__ = _doc_api_apikey_info
ReManagerComm_HTTP_Async.apikey_delete.__doc__ = _doc_api_apikey_delete
ReManagerComm_HTTP_Async.whoami.__doc__ = _doc_api_whoami
ReManagerComm_HTTP_Async.principal_info.__doc__ = _doc_api_principal_info
ReManagerComm_HTTP_Async.api_scopes.__doc__ = _doc_api_api_scopes
ReManagerComm_HTTP_Async.logout.__doc__ = _doc_api_logout


class ConsoleMonitor_WS_Async:
    """WebSocket-based console monitor for async operations"""
    
    def __init__(self, parent, poll_period=1.0, max_msgs=1000, max_lines=1000):
        self._parent = parent
        self._poll_period = poll_period
        self._max_msgs = max_msgs
        self._max_lines = max_lines
        self._enabled = False
        self._messages = []
        self._text_lines = []
    
    def _process_ws_message(self, message):
        """Process console output message from WebSocket"""
        if not self._enabled:
            return
            
        data = message.get("data", {})
        lines = data.get("lines", [])
        
        # Add to message buffer
        if len(self._messages) < self._max_msgs:
            self._messages.append(message)
        
        # Add to text buffer
        for line in lines:
            if len(self._text_lines) < self._max_lines:
                self._text_lines.append(line)
    
    def enable(self):
        """Enable console monitoring"""
        self._enabled = True
    
    def disable(self):
        """Disable console monitoring"""
        self._enabled = False
    
    async def disable_wait(self, timeout=None):
        """Disable monitoring with timeout"""
        self.disable()
    
    def clear(self):
        """Clear message and text buffers"""
        self._messages.clear()
        self._text_lines.clear()
    
    def next_msg(self):
        """Get next message from buffer"""
        if self._messages:
            return self._messages.pop(0)
        return None
    
    def text(self):
        """Get current text output"""
        return "\n".join(self._text_lines)
    
    @property
    def enabled(self):
        """Check if monitoring is enabled"""
        return self._enabled


class ReManagerComm_WS_Async(ReManagerAPI_WS_Base):
    """Async WebSocket communication for REManager"""
    
    def _init_console_monitor(self):
        self._console_monitor = ConsoleMonitor_WS_Async(
            parent=self,
            poll_period=self._console_monitor_poll_period,
            max_msgs=self._console_monitor_max_msgs,
            max_lines=self._console_monitor_max_lines,
        )

    def _create_websocket_client(self):
        """Create WebSocket client (websockets library)"""
        # Return connection parameters for websockets.connect()
        extra_headers = self._prepare_auth_headers()
        return {
            "uri": self._ws_server_uri,
            "extra_headers": extra_headers,
            "ping_interval": self._ws_heartbeat_interval,
            "ping_timeout": self._ws_heartbeat_interval / 2,
            "close_timeout": 10,
        }

    async def connect(self):
        """Establish WebSocket connection"""
        if self._connected:
            return
        
        connection_params = self._create_websocket_client()
        self._reconnect_attempts = 0
        
        while self._reconnect_attempts < self._ws_max_reconnect_attempts:
            try:
                self._websocket = await websockets.connect(**connection_params)
                self._connected = True
                self._reconnect_attempts = 0
                
                # Start message receiving task
                self._receive_task = asyncio.create_task(self._receive_messages())
                
                # Send initial subscription requests if any
                await self._resubscribe_all()
                
                logging.info(f"WebSocket connected to {self._ws_server_uri}")
                break
                
            except Exception as e:
                self._reconnect_attempts += 1
                logging.warning(
                    f"WebSocket connection attempt {self._reconnect_attempts} failed: {e}"
                )
                
                if self._reconnect_attempts < self._ws_max_reconnect_attempts:
                    await asyncio.sleep(self._ws_reconnect_delay)
                else:
                    raise self.WebSocketConnectionError(
                        f"Failed to connect after {self._ws_max_reconnect_attempts} attempts"
                    )

    async def disconnect(self):
        """Disconnect WebSocket"""
        if not self._connected:
            return
        
        self._connected = False
        
        # Cancel receive task
        if hasattr(self, '_receive_task') and not self._receive_task.done():
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass
        
        # Close WebSocket connection
        if self._websocket:
            await self._websocket.close()
            self._websocket = None
        
        logging.info("WebSocket disconnected")

    async def _receive_messages(self):
        """Background task to receive and process WebSocket messages"""
        try:
            async for message in self._websocket:
                if not self._connected:
                    break
                
                try:
                    if isinstance(message, str):
                        data = json.loads(message)
                    else:
                        data = message
                    
                    self._process_incoming_message(data)
                    
                except Exception as e:
                    logging.error(f"Error processing WebSocket message: {e}")
                    
        except websockets.exceptions.ConnectionClosed:
            logging.info("WebSocket connection closed by server")
            self._connected = False
            await self._handle_disconnect()
            
        except Exception as e:
            logging.error(f"WebSocket receive error: {e}")
            self._connected = False
            await self._handle_disconnect()

    async def _handle_disconnect(self):
        """Handle unexpected disconnection and attempt reconnect"""
        if self._is_closing:
            return
        
        logging.info("Attempting to reconnect WebSocket...")
        try:
            await asyncio.sleep(self._ws_reconnect_delay)
            await self.connect()
        except Exception as e:
            logging.error(f"Reconnection failed: {e}")

    async def _resubscribe_all(self):
        """Resubscribe to all topics after reconnection"""
        for topic in list(self._subscriptions.keys()):
            try:
                subscribe_msg = self._prepare_message("subscribe", topic=topic)
                await self._send_message(subscribe_msg)
            except Exception as e:
                logging.error(f"Failed to resubscribe to topic '{topic}': {e}")

    async def _send_message(self, message: dict):
        """Send message via WebSocket"""
        if not self._connected or not self._websocket:
            raise self.WebSocketDisconnectError("WebSocket not connected")
        
        try:
            message_str = json.dumps(message)
            await self._websocket.send(message_str)
        except Exception as e:
            logging.error(f"Failed to send WebSocket message: {e}")
            raise

    async def subscribe(self, topic: str, callback: Optional[Callable] = None):
        """Subscribe to WebSocket topic updates"""
        if topic in self._subscriptions:
            logging.warning(f"Already subscribed to topic: {topic}")
            return
        
        self._subscriptions[topic] = callback
        
        if self._connected:
            subscribe_msg = self._prepare_message("subscribe", topic=topic)
            await self._send_message(subscribe_msg)
        
        logging.info(f"Subscribed to topic: {topic}")

    async def unsubscribe(self, topic: str):
        """Unsubscribe from WebSocket topic"""
        if topic not in self._subscriptions:
            logging.warning(f"Not subscribed to topic: {topic}")
            return
        
        del self._subscriptions[topic]
        
        if self._connected:
            unsubscribe_msg = self._prepare_message("unsubscribe", topic=topic)
            await self._send_message(unsubscribe_msg)
        
        logging.info(f"Unsubscribed from topic: {topic}")

    async def send_request(self, method: str, params: Optional[Dict[str, Any]] = None):
        """Send request via WebSocket and wait for response"""
        if not self._connected:
            await self.connect()
        
        request_msg = self._prepare_message("request", method=method, params=params or {})
        message_id = request_msg["id"]
        
        # Create future for response
        future = asyncio.Future()
        self._pending_requests[message_id] = future
        
        try:
            await self._send_message(request_msg)
            
            # Wait for response with timeout
            response = await asyncio.wait_for(
                future, timeout=self._ws_connection_timeout
            )
            
            return response
            
        except asyncio.TimeoutError:
            # Clean up pending request
            self._pending_requests.pop(message_id, None)
            raise self.RequestTimeoutError(
                f"WebSocket request timeout for method: {method}", 
                {"method": method, "params": params}
            )
        except Exception as e:
            # Clean up pending request
            self._pending_requests.pop(message_id, None)
            raise

    async def close(self):
        """Close WebSocket connection and cleanup"""
        self._is_closing = True
        
        # Disable console monitor
        if self._console_monitor:
            await self._console_monitor.disable_wait(timeout=self._console_monitor_poll_period * 10)
        
        # Disconnect WebSocket
        await self.disconnect()
        
        # Clear pending requests
        for future in self._pending_requests.values():
            if not future.done():
                future.cancel()
        self._pending_requests.clear()
        
        # Clear subscriptions
        self._subscriptions.clear()

    def __del__(self):
        self._is_closing = True


# Docstring assignments
ReManagerComm_WS_Async.send_request.__doc__ = _doc_send_request
ReManagerComm_WS_Async.close.__doc__ = _doc_close
