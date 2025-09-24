"""
Device Configuration API

This module provides REST API endpoints for accessing shared device configurations.
These endpoints can be used by both Queue Server and Ophyd as a Service (OaaS)
to get consistent device information.
"""

from typing import Dict, List, Optional, Any
import json
from pathlib import Path
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from .device_config import DeviceConfigurationManager, DeviceDefinition


class DeviceInfo(BaseModel):
    """Device information response model."""
    name: str
    device_class: str
    device_type: str
    pvs: Dict[str, str]
    metadata: Dict[str, Any]
    user_groups: List[str]


class DeviceListResponse(BaseModel):
    """Response model for device list endpoints."""
    success: bool
    devices: Dict[str, DeviceInfo]
    total_count: int
    user_group: Optional[str] = None


class DeviceConfigResponse(BaseModel):
    """Response model for device configuration endpoints."""
    success: bool
    config_format: str  # 'queueserver' or 'oaas'
    config: Dict[str, Any]
    device_count: int


router = APIRouter(prefix="/api/device-config", tags=["device-config"])

# Global device manager instance
_device_manager: Optional[DeviceConfigurationManager] = None


def initialize_device_manager(profile_collection_path: str, 
                            config_cache_path: Optional[str] = None):
    """Initialize the global device configuration manager."""
    global _device_manager
    _device_manager = DeviceConfigurationManager(
        profile_collection_path=profile_collection_path,
        config_cache_path=config_cache_path
    )
    
    # Try to load from cache first, then profile collection
    startup_dir = Path(profile_collection_path) / "startup"
    if not _device_manager.load_cache():
        if startup_dir.exists():
            _device_manager.load_from_profile_collection(startup_dir)
            _device_manager.save_cache()


def get_device_manager() -> DeviceConfigurationManager:
    """Get the global device configuration manager."""
    if _device_manager is None:
        raise HTTPException(
            status_code=500, 
            detail="Device configuration manager not initialized"
        )
    return _device_manager


@router.get("/devices", response_model=DeviceListResponse)
async def list_devices(
    user_group: Optional[str] = Query(None, description="Filter devices by user group"),
    device_type: Optional[str] = Query(None, description="Filter devices by type (motor, detector, signal, etc.)")
):
    """
    List all available devices with optional filtering.
    
    Parameters
    ----------
    user_group : str, optional
        Filter devices accessible by this user group
    device_type : str, optional
        Filter devices by type
        
    Returns
    -------
    DeviceListResponse
        List of devices matching the criteria
    """
    manager = get_device_manager()
    
    # Get devices (filtered by user group if specified)
    if user_group:
        device_defs = manager.get_devices_for_user_group(user_group)
    else:
        device_defs = manager._device_definitions
    
    # Filter by device type if specified
    if device_type:
        device_defs = {
            name: dev for name, dev in device_defs.items() 
            if dev.device_type == device_type
        }
    
    # Convert to response format
    devices = {
        name: DeviceInfo(
            name=dev.name,
            device_class=dev.device_class,
            device_type=dev.device_type,
            pvs=dev.pvs,
            metadata=dev.metadata,
            user_groups=dev.user_groups
        )
        for name, dev in device_defs.items()
    }
    
    return DeviceListResponse(
        success=True,
        devices=devices,
        total_count=len(devices),
        user_group=user_group
    )


@router.get("/devices/{device_name}", response_model=DeviceInfo)
async def get_device(device_name: str):
    """
    Get detailed information about a specific device.
    
    Parameters
    ----------
    device_name : str
        Name of the device
        
    Returns
    -------
    DeviceInfo
        Device information
    """
    manager = get_device_manager()
    device_def = manager.get_device_definition(device_name)
    
    if device_def is None:
        raise HTTPException(
            status_code=404, 
            detail=f"Device '{device_name}' not found"
        )
    
    return DeviceInfo(
        name=device_def.name,
        device_class=device_def.device_class,
        device_type=device_def.device_type,
        pvs=device_def.pvs,
        metadata=device_def.metadata,
        user_groups=device_def.user_groups
    )


@router.get("/config/queueserver", response_model=DeviceConfigResponse)
async def get_queueserver_config():
    """
    Get device configuration in Queue Server format.
    
    Returns
    -------
    DeviceConfigResponse
        Device configuration for Queue Server
    """
    manager = get_device_manager()
    config = manager.export_for_queueserver()
    
    return DeviceConfigResponse(
        success=True,
        config_format="queueserver",
        config=config,
        device_count=len(manager._device_definitions)
    )


@router.get("/config/oaas", response_model=DeviceConfigResponse)
async def get_oaas_config():
    """
    Get device configuration in Ophyd as a Service format.
    
    Returns
    -------
    DeviceConfigResponse
        Device configuration for OaaS
    """
    manager = get_device_manager()
    config = manager.export_for_oaas()
    
    return DeviceConfigResponse(
        success=True,
        config_format="oaas",
        config=config,
        device_count=len(manager._device_definitions)
    )


@router.post("/reload")
async def reload_device_config():
    """
    Reload device configurations from the profile collection.
    
    This endpoint allows dynamic reloading of device configurations
    without restarting the service.
    
    Returns
    -------
    dict
        Status of the reload operation
    """
    manager = get_device_manager()
    
    try:
        startup_dir = manager.profile_collection_path / "startup"
        if not startup_dir.exists():
            raise HTTPException(
                status_code=400,
                detail=f"Startup directory not found: {startup_dir}"
            )
        
        # Reload from profile collection
        device_defs = manager.load_from_profile_collection(startup_dir)
        
        # Update cache
        manager.save_cache()
        
        return {
            "success": True,
            "message": "Device configurations reloaded successfully",
            "device_count": len(device_defs),
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to reload device configurations: {str(e)}"
        )


@router.get("/status")
async def get_status():
    """
    Get the status of the device configuration service.
    
    Returns
    -------
    dict
        Service status information
    """
    manager = get_device_manager()
    
    return {
        "success": True,
        "service": "device-configuration",
        "profile_collection_path": str(manager.profile_collection_path),
        "cache_path": str(manager.config_cache_path) if manager.config_cache_path else None,
        "device_count": len(manager._device_definitions),
        "device_types": list(set(dev.device_type for dev in manager._device_definitions.values())),
        "user_groups": list(set(
            group for dev in manager._device_definitions.values() 
            for group in dev.user_groups
        ))
    }
