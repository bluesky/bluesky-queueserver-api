"""
Device Coordination Client

This module provides a client class for external services (like ophyd-websocket)
to interact with the Device Coordination Service.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Callable, Any
from urllib.parse import urljoin

import aiohttp
import websockets

from .models import (
    DeviceLock,
    LockRequest,
    LockResponse,
    LockType,
    LockStatus,
    LocksStatusResponse
)


class DeviceCoordinationClient:
    """
    Client for interacting with the Device Coordination Service.
    
    This client provides both HTTP and WebSocket interfaces for requesting
    device locks, monitoring lock status, and receiving real-time updates.
    """
    
    def __init__(
        self, 
        base_url: str = "http://localhost:60620",
        ws_url: Optional[str] = None,
        timeout: int = 30
    ):
        """
        Initialize the coordination client.
        
        Args:
            base_url: Base URL for HTTP API (e.g., "http://localhost:60620")
            ws_url: WebSocket URL (defaults to ws://host:port/ws)
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.ws_url = ws_url or self.base_url.replace('http', 'ws') + '/ws'
        self.timeout = timeout
        self.session: Optional[aiohttp.ClientSession] = None
        self.websocket: Optional[websockets.WebSocketServerProtocol] = None
        self.websocket_task: Optional[asyncio.Task] = None
        self.lock_update_callbacks: List[Callable[[str, DeviceLock, str], None]] = []
        self._active_locks_cache: Dict[str, DeviceLock] = {}
        
    async def __aenter__(self):
        """Async context manager entry"""
        await self.connect()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.disconnect()

    async def connect(self):
        """Initialize HTTP session and optionally WebSocket connection"""
        if not self.session:
            self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout))
        
        # Test connection
        try:
            await self.health_check()
            logging.info(f"Connected to Device Coordination Service at {self.base_url}")
        except Exception as e:
            logging.error(f"Failed to connect to coordination service: {e}")
            raise
    
    async def disconnect(self):
        """Close connections and cleanup"""
        if self.websocket_task:
            self.websocket_task.cancel()
            try:
                await self.websocket_task
            except asyncio.CancelledError:
                pass
        
        if self.websocket:
            await self.websocket.close()
            self.websocket = None
        
        if self.session:
            await self.session.close()
            self.session = None

    async def health_check(self) -> Dict[str, Any]:
        """Check if the coordination service is healthy"""
        url = urljoin(self.base_url + '/', 'api/health/ready')
        async with self.session.get(url) as response:
            response.raise_for_status()
            return await response.json()

    async def request_lock(
        self,
        device_name: str,
        lock_type: LockType,
        user_id: str,
        timeout: Optional[int] = 300,
        reason: Optional[str] = None,
        plan_uid: Optional[str] = None
    ) -> LockResponse:
        """
        Request a device lock.
        
        Args:
            device_name: Name of the device to lock
            lock_type: Type of lock to request
            user_id: Identifier for the user/service requesting the lock
            timeout: Lock timeout in seconds (None for no timeout)
            reason: Optional reason for the lock
            plan_uid: Optional plan UID for queue-related locks
            
        Returns:
            LockResponse with success status and lock key
        """
        request = LockRequest(
            device_name=device_name,
            lock_type=lock_type,
            user_id=user_id,
            timeout=timeout,
            reason=reason,
            plan_uid=plan_uid
        )
        
        url = urljoin(self.base_url + '/', 'api/lock/request')
        async with self.session.post(url, json=request.dict()) as response:
            response.raise_for_status()
            data = await response.json()
            return LockResponse(**data)

    async def release_lock(
        self,
        device_name: str,
        lock_key: str,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Release a device lock.
        
        Args:
            device_name: Name of the device to unlock
            lock_key: Lock key received when lock was acquired
            user_id: User ID that acquired the lock
            
        Returns:
            Response dictionary with success status
        """
        url = urljoin(self.base_url + '/', 'api/lock/release')
        params = {
            'device_name': device_name,
            'lock_key': lock_key,
            'user_id': user_id
        }
        async with self.session.post(url, params=params) as response:
            response.raise_for_status()
            return await response.json()

    async def get_lock_status(self, device_name: Optional[str] = None) -> LockStatus:
        """
        Get lock status for a specific device.
        
        Args:
            device_name: Name of the device (required)
            
        Returns:
            LockStatus for the device
        """
        if device_name is None:
            raise ValueError("device_name is required")
            
        url = urljoin(self.base_url + '/', f'api/locks/device/{device_name}')
        async with self.session.get(url) as response:
            response.raise_for_status()
            data = await response.json()
            return LockStatus(**data)

    async def get_all_locks(self) -> LocksStatusResponse:
        """
        Get status of all active locks.
        
        Returns:
            LocksStatusResponse with all active locks
        """
        url = urljoin(self.base_url + '/', 'api/locks/status')
        async with self.session.get(url) as response:
            response.raise_for_status()
            data = await response.json()
            return LocksStatusResponse(**data)

    async def is_device_locked(self, device_name: str) -> bool:
        """
        Check if a device is currently locked.
        
        Args:
            device_name: Name of the device to check
            
        Returns:
            True if device is locked, False otherwise
        """
        try:
            status = await self.get_lock_status(device_name)
            return status.locked
        except Exception:
            return False

    async def can_access_device(
        self, 
        device_name: str, 
        requesting_lock_type: LockType
    ) -> bool:
        """
        Check if a device can be accessed with the given lock type.
        
        Args:
            device_name: Name of the device
            requesting_lock_type: Type of lock being requested
            
        Returns:
            True if device can be accessed, False otherwise
        """
        try:
            status = await self.get_lock_status(device_name)
            if not status.locked:
                return True
            
            # Check if requesting lock has higher or equal priority
            from .models import LockPriority
            requesting_priority = LockPriority[requesting_lock_type.value].value
            existing_priority = status.lock.priority
            
            return requesting_priority <= existing_priority
            
        except Exception:
            return False

    def add_lock_update_callback(self, callback: Callable[[str, DeviceLock, str], None]):
        """
        Add a callback for lock update notifications.
        
        Args:
            callback: Function called with (device_name, lock, action) when locks change
        """
        self.lock_update_callbacks.append(callback)

    def remove_lock_update_callback(self, callback: Callable[[str, DeviceLock, str], None]):
        """Remove a lock update callback"""
        if callback in self.lock_update_callbacks:
            self.lock_update_callbacks.remove(callback)

    async def start_websocket_monitoring(self):
        """Start WebSocket connection for real-time lock updates"""
        if self.websocket_task:
            return  # Already running
        
        self.websocket_task = asyncio.create_task(self._websocket_handler())

    async def stop_websocket_monitoring(self):
        """Stop WebSocket monitoring"""
        if self.websocket_task:
            self.websocket_task.cancel()
            try:
                await self.websocket_task
            except asyncio.CancelledError:
                pass
            self.websocket_task = None

    async def _websocket_handler(self):
        """Handle WebSocket connection and messages"""
        while True:
            try:
                async with websockets.connect(self.ws_url) as websocket:
                    self.websocket = websocket
                    logging.info(f"WebSocket connected to {self.ws_url}")
                    
                    async for message in websocket:
                        try:
                            data = json.loads(message)
                            await self._handle_websocket_message(data)
                        except json.JSONDecodeError:
                            logging.warning(f"Invalid JSON received: {message}")
                        except Exception as e:
                            logging.error(f"Error handling WebSocket message: {e}")
            
            except websockets.exceptions.WebSocketException as e:
                logging.warning(f"WebSocket connection lost: {e}")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logging.error(f"WebSocket error: {e}")
            
            # Wait before reconnecting
            await asyncio.sleep(5)

    async def _handle_websocket_message(self, data: Dict[str, Any]):
        """Handle incoming WebSocket messages"""
        message_type = data.get("type")
        
        if message_type == "initial_status":
            # Update cache with initial status
            status_data = data.get("data", {})
            locks = status_data.get("locks", [])
            self._active_locks_cache = {
                lock["device_name"]: DeviceLock(**lock) for lock in locks
            }
            
        elif message_type == "lock_update":
            action = data.get("action")
            device_name = data.get("device_name")
            lock_data = data.get("lock", {})
            
            if action in ["acquired", "force_released"]:
                lock = DeviceLock(**lock_data)
                if action == "acquired":
                    self._active_locks_cache[device_name] = lock
                else:  # force_released
                    self._active_locks_cache.pop(device_name, None)
            elif action == "released":
                self._active_locks_cache.pop(device_name, None)
            
            # Notify callbacks
            if lock_data:
                lock = DeviceLock(**lock_data)
                for callback in self.lock_update_callbacks:
                    try:
                        callback(device_name, lock, action)
                    except Exception as e:
                        logging.error(f"Error in lock update callback: {e}")

    def get_cached_lock_status(self, device_name: str) -> Optional[DeviceLock]:
        """
        Get cached lock status for a device (from WebSocket updates).
        
        Args:
            device_name: Name of the device
            
        Returns:
            DeviceLock if device is locked, None otherwise
        """
        return self._active_locks_cache.get(device_name)

    def get_all_cached_locks(self) -> Dict[str, DeviceLock]:
        """Get all cached device locks"""
        return self._active_locks_cache.copy()


class DeviceCoordinationContext:
    """
    Context manager for acquiring and automatically releasing device locks.
    
    Usage:
        async with DeviceCoordinationContext(
            client, "detector1", LockType.MANUAL_OPERATOR, "user123"
        ) as lock_key:
            # Device is locked, perform operations
            pass
        # Device is automatically unlocked
    """
    
    def __init__(
        self,
        client: DeviceCoordinationClient,
        device_name: str,
        lock_type: LockType,
        user_id: str,
        timeout: Optional[int] = 300,
        reason: Optional[str] = None,
        plan_uid: Optional[str] = None
    ):
        self.client = client
        self.device_name = device_name
        self.lock_type = lock_type
        self.user_id = user_id
        self.timeout = timeout
        self.reason = reason
        self.plan_uid = plan_uid
        self.lock_key: Optional[str] = None

    async def __aenter__(self) -> str:
        """Acquire the device lock"""
        response = await self.client.request_lock(
            device_name=self.device_name,
            lock_type=self.lock_type,
            user_id=self.user_id,
            timeout=self.timeout,
            reason=self.reason,
            plan_uid=self.plan_uid
        )
        
        if not response.success:
            raise RuntimeError(f"Failed to acquire lock: {response.message}")
        
        self.lock_key = response.lock_key
        return self.lock_key

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Release the device lock"""
        if self.lock_key:
            try:
                await self.client.release_lock(
                    device_name=self.device_name,
                    lock_key=self.lock_key,
                    user_id=self.user_id
                )
            except Exception as e:
                logging.error(f"Failed to release lock for {self.device_name}: {e}")
