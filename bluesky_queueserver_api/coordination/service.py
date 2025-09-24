"""
Device Coordination Service

This module provides the main Device Coordination Service that mediates device access
between the Bluesky Queue Server and other services to prevent conflicts.
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional, Set

import aioredis
import uvicorn
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from .models import (
    DeviceLock,
    LockRequest, 
    LockResponse,
    LockType,
    LockPriority,
    LockStatus,
    LocksStatusResponse
)

# Try to import device configuration API
try:
    from ..device_config_api import (
        initialize_device_manager, 
        get_device_manager,
        router as device_config_router
    )
    DEVICE_CONFIG_AVAILABLE = True
except ImportError:
    DEVICE_CONFIG_AVAILABLE = False
    device_config_router = None
    initialize_device_manager = None
    get_device_manager = None
    logging.warning("Device configuration API not available")


class DeviceCoordinationService:
    """
    Main service class that provides device coordination and lock management.
    
    This service mediates device access between different components of the
    Bluesky ecosystem to prevent conflicts and ensure safe operations.
    """
    
    def __init__(self, profile_collection_path: Optional[str] = None):
        self.app = FastAPI(title="Device Coordination Service")
        self.redis: Optional[aioredis.Redis] = None
        self.active_locks: Dict[str, DeviceLock] = {}
        self.websocket_connections: Set[WebSocket] = set()
        self.cleanup_task: Optional[asyncio.Task] = None
        self.profile_collection_path = profile_collection_path
        
        # Add CORS middleware
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Initialize device configuration if available
        if DEVICE_CONFIG_AVAILABLE and profile_collection_path:
            try:
                initialize_device_manager(profile_collection_path)
                self.app.include_router(device_config_router)
                logging.info("Device configuration API integrated successfully")
            except Exception as e:
                logging.warning(f"Failed to initialize device configuration: {e}")
        
        self._setup_routes()

    def _setup_routes(self):
        """Setup FastAPI routes"""
        
        @self.app.on_event("startup")
        async def startup():
            await self.initialize()

        @self.app.on_event("shutdown") 
        async def shutdown():
            await self.cleanup()

        @self.app.post("/api/lock/request", response_model=LockResponse)
        async def request_lock(request: LockRequest):
            return await self.request_device_lock(request)

        @self.app.post("/api/lock/release")
        async def release_lock(device_name: str, lock_key: str, user_id: str):
            return await self.release_device_lock(device_name, lock_key, user_id)

        @self.app.get("/api/locks/status", response_model=LocksStatusResponse)
        async def get_all_locks():
            return await self.get_lock_status()

        @self.app.get("/api/locks/device/{device_name}", response_model=LockStatus)
        async def get_device_lock(device_name: str):
            return await self.get_device_lock_status(device_name)

        @self.app.get("/api/health/live")
        async def health_live():
            return {"status": "alive", "timestamp": datetime.utcnow()}

        @self.app.get("/api/health/ready")
        async def health_ready():
            redis_ok = self.redis is not None
            return {
                "status": "ready" if redis_ok else "not_ready",
                "redis_connected": redis_ok,
                "active_locks": len(self.active_locks)
            }

        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            await self.handle_websocket(websocket)

    async def initialize(self):
        """Initialize the service"""
        try:
            # Connect to Redis
            self.redis = await aioredis.from_url("redis://localhost:60590")
            await self.redis.ping()
            logging.info("Connected to Redis")
            
            # Load existing locks from Redis
            await self.load_locks_from_redis()
            
            # Start cleanup task
            self.cleanup_task = asyncio.create_task(self.periodic_cleanup())
            
            logging.info("Device Coordination Service initialized")
            
        except Exception as e:
            logging.error(f"Failed to initialize service: {e}")
            raise

    async def cleanup(self):
        """Cleanup on shutdown"""
        if self.cleanup_task:
            self.cleanup_task.cancel()
        
        if self.redis:
            await self.redis.close()

    async def load_locks_from_redis(self):
        """Load existing locks from Redis on startup"""
        try:
            lock_keys = await self.redis.keys("device_lock:*")
            for key in lock_keys:
                lock_data = await self.redis.get(key)
                if lock_data:
                    lock_dict = json.loads(lock_data)
                    lock = DeviceLock(**lock_dict)
                    if not lock.is_expired:
                        self.active_locks[lock.device_name] = lock
                    else:
                        # Remove expired lock
                        await self.redis.delete(key)
            
            logging.info(f"Loaded {len(self.active_locks)} active locks from Redis")
            
        except Exception as e:
            logging.error(f"Failed to load locks from Redis: {e}")

    async def save_lock_to_redis(self, lock: DeviceLock):
        """Save lock to Redis"""
        try:
            key = f"device_lock:{lock.device_name}"
            lock_data = lock.json()
            
            if lock.expires_at:
                # Set TTL based on expiration
                ttl = int((lock.expires_at - datetime.utcnow()).total_seconds())
                if ttl > 0:
                    await self.redis.setex(key, ttl, lock_data)
                else:
                    # Already expired, don't save
                    return
            else:
                await self.redis.set(key, lock_data)
                
        except Exception as e:
            logging.error(f"Failed to save lock to Redis: {e}")

    async def remove_lock_from_redis(self, device_name: str):
        """Remove lock from Redis"""
        try:
            key = f"device_lock:{device_name}"
            await self.redis.delete(key)
        except Exception as e:
            logging.error(f"Failed to remove lock from Redis: {e}")

    async def request_device_lock(self, request: LockRequest) -> LockResponse:
        """Request a device lock"""
        device_name = request.device_name
        
        # Check if device is already locked
        existing_lock = self.active_locks.get(device_name)
        
        if existing_lock and not existing_lock.is_expired:
            # Check priority
            request_priority = LockPriority[request.lock_type.value].value
            existing_priority = existing_lock.priority
            
            if request_priority <= existing_priority:
                # Higher or equal priority, allow override
                await self.force_release_lock(device_name, 
                    reason=f"Overridden by higher priority {request.lock_type.value}")
            else:
                # Lower priority, deny request
                return LockResponse(
                    success=False,
                    message=f"Device {device_name} is locked by {existing_lock.lock_type.value} "
                           f"(expires: {existing_lock.expires_at})"
                )
        
        # Create new lock
        lock_key = str(uuid.uuid4())
        expires_at = None
        
        if request.timeout:
            expires_at = datetime.utcnow() + timedelta(seconds=request.timeout)
        
        new_lock = DeviceLock(
            device_name=device_name,
            lock_type=request.lock_type,
            user_id=request.user_id,
            lock_key=lock_key,
            acquired_at=datetime.utcnow(),
            expires_at=expires_at,
            reason=request.reason,
            plan_uid=request.plan_uid,
            priority=LockPriority[request.lock_type.value].value
        )
        
        # Store lock
        self.active_locks[device_name] = new_lock
        await self.save_lock_to_redis(new_lock)
        
        # Broadcast lock status change
        await self.broadcast_lock_update(new_lock, "acquired")
        
        logging.info(f"Lock acquired: {device_name} by {request.user_id} ({request.lock_type.value})")
        
        return LockResponse(
            success=True,
            lock_key=lock_key,
            message=f"Lock acquired for {device_name}",
            expires_at=expires_at
        )

    async def release_device_lock(self, device_name: str, lock_key: str, user_id: str):
        """Release a device lock"""
        existing_lock = self.active_locks.get(device_name)
        
        if not existing_lock:
            raise HTTPException(status_code=404, detail=f"No lock found for device {device_name}")
        
        if existing_lock.lock_key != lock_key:
            raise HTTPException(status_code=403, detail="Invalid lock key")
        
        if existing_lock.user_id != user_id:
            raise HTTPException(status_code=403, detail="Not authorized to release this lock")
        
        # Remove lock
        del self.active_locks[device_name]
        await self.remove_lock_from_redis(device_name)
        
        # Broadcast lock release
        await self.broadcast_lock_update(existing_lock, "released")
        
        logging.info(f"Lock released: {device_name} by {user_id}")
        
        return {"success": True, "message": f"Lock released for {device_name}"}

    async def force_release_lock(self, device_name: str, reason: str = "Forced release"):
        """Force release a lock (for priority override or cleanup)"""
        existing_lock = self.active_locks.get(device_name)
        
        if existing_lock:
            del self.active_locks[device_name]
            await self.remove_lock_from_redis(device_name)
            await self.broadcast_lock_update(existing_lock, "force_released", {"reason": reason})
            logging.info(f"Lock force released: {device_name} - {reason}")

    async def get_lock_status(self) -> LocksStatusResponse:
        """Get status of all locks"""
        return LocksStatusResponse(
            locks=list(self.active_locks.values()),
            total_count=len(self.active_locks),
            timestamp=datetime.utcnow()
        )

    async def get_device_lock_status(self, device_name: str) -> LockStatus:
        """Get lock status for specific device"""
        lock = self.active_locks.get(device_name)
        
        if lock and lock.is_expired:
            # Clean up expired lock
            await self.force_release_lock(device_name, "Expired")
            lock = None
        
        return LockStatus(
            device_name=device_name,
            locked=lock is not None,
            lock=lock,
            timestamp=datetime.utcnow()
        )

    async def periodic_cleanup(self):
        """Periodic cleanup of expired locks"""
        while True:
            try:
                await asyncio.sleep(60)  # Check every minute
                
                expired_devices = []
                for device_name, lock in self.active_locks.items():
                    if lock.is_expired:
                        expired_devices.append(device_name)
                
                for device_name in expired_devices:
                    await self.force_release_lock(device_name, "Expired")
                    
                if expired_devices:
                    logging.info(f"Cleaned up {len(expired_devices)} expired locks")
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logging.error(f"Error in periodic cleanup: {e}")

    async def handle_websocket(self, websocket: WebSocket):
        """Handle WebSocket connections"""
        await websocket.accept()
        self.websocket_connections.add(websocket)
        
        try:
            # Send current lock status
            status = await self.get_lock_status()
            await websocket.send_json({
                "type": "initial_status",
                "data": status.dict()
            })
            
            # Keep connection alive and handle incoming messages
            while True:
                try:
                    data = await websocket.receive_json()
                    await self.handle_websocket_message(websocket, data)
                except WebSocketDisconnect:
                    break
                    
        except WebSocketDisconnect:
            pass
        finally:
            self.websocket_connections.discard(websocket)

    async def handle_websocket_message(self, websocket: WebSocket, data: dict):
        """Handle incoming WebSocket messages"""
        message_type = data.get("type")
        
        if message_type == "ping":
            await websocket.send_json({"type": "pong", "timestamp": datetime.utcnow().isoformat()})
        elif message_type == "get_status":
            status = await self.get_lock_status()
            await websocket.send_json({"type": "status_response", "data": status.dict()})

    async def broadcast_lock_update(self, lock: DeviceLock, action: str, extra_data: dict = None):
        """Broadcast lock updates to all WebSocket connections"""
        message = {
            "type": "lock_update",
            "action": action,
            "device_name": lock.device_name,
            "lock": lock.dict(),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if extra_data:
            message.update(extra_data)
        
        # Send to all connected WebSocket clients
        disconnected = set()
        for websocket in self.websocket_connections:
            try:
                await websocket.send_json(message)
            except:
                disconnected.add(websocket)
        
        # Remove disconnected clients
        self.websocket_connections -= disconnected

    def run(self, host="0.0.0.0", port=60620):
        """Run the service"""
        logging.basicConfig(level=logging.INFO)
        uvicorn.run(self.app, host=host, port=port)


def create_app(profile_collection_path: Optional[str] = None) -> FastAPI:
    """Factory function to create the FastAPI app"""
    service = DeviceCoordinationService(profile_collection_path)
    return service.app


def main():
    """Main entry point for running the coordination service"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Device Coordination Service")
    parser.add_argument("--profile-collection", 
                       help="Path to the beamline profile collection")
    parser.add_argument("--host", default="0.0.0.0",
                       help="Host to bind to")
    parser.add_argument("--port", type=int, default=60620,
                       help="Port to bind to")
    
    args = parser.parse_args()
    
    service = DeviceCoordinationService(profile_collection_path=args.profile_collection)
    service.run(host=args.host, port=args.port)


if __name__ == "__main__":
    main()
