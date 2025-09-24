"""
Device Coordination Models

This module defines the data models and types used by the Device Coordination Service
for managing device locks and preventing conflicts between services.
"""

from datetime import datetime, timedelta
from enum import Enum
from typing import Optional

from pydantic import BaseModel


class LockType(Enum):
    """Types of device locks with different purposes"""
    MAINTENANCE = "MAINTENANCE"
    QUEUE_EXECUTING = "QUEUE_EXECUTING"  
    MANUAL_OPERATOR = "MANUAL_OPERATOR"
    QUEUE_QUEUED = "QUEUE_QUEUED"


class LockPriority(Enum):
    """Priority levels for device locks (lower number = higher priority)"""
    MAINTENANCE = 0
    QUEUE_EXECUTING = 1
    MANUAL_OPERATOR = 2
    QUEUE_QUEUED = 3


class DeviceLock(BaseModel):
    """Represents an active device lock"""
    device_name: str
    lock_type: LockType
    user_id: str
    lock_key: str
    acquired_at: datetime
    expires_at: Optional[datetime] = None
    reason: Optional[str] = None
    plan_uid: Optional[str] = None
    priority: int = 3

    @property
    def is_expired(self) -> bool:
        """Check if the lock has expired"""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at


class LockRequest(BaseModel):
    """Request to acquire a device lock"""
    device_name: str
    lock_type: LockType
    user_id: str
    timeout: Optional[int] = 300  # seconds
    reason: Optional[str] = None
    plan_uid: Optional[str] = None


class LockResponse(BaseModel):
    """Response to a lock request"""
    success: bool
    lock_key: Optional[str] = None
    message: str
    expires_at: Optional[datetime] = None


class LockStatus(BaseModel):
    """Status information for a device lock"""
    device_name: str
    locked: bool
    lock: Optional[DeviceLock] = None
    timestamp: datetime


class LocksStatusResponse(BaseModel):
    """Response containing status of all locks"""
    locks: list[DeviceLock]
    total_count: int
    timestamp: datetime


# Additional utility types for client integration
class LockUpdateMessage(BaseModel):
    """WebSocket message for lock updates"""
    type: str  # "lock_update"
    action: str  # "acquired", "released", "force_released"
    device_name: str
    lock: DeviceLock
    timestamp: str
