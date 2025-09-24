"""
Device Configuration Manager - Streamlined Version

This module provides minimal device configuration management using 
bluesky-queueserver's existing device discovery capabilities.
"""

import json
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
import logging

try:
    from ._defaults import default_user_group
except ImportError:
    default_user_group = "primary"

logger = logging.getLogger(__name__)


@dataclass
class DeviceDefinition:
    """Standard device definition structure."""
    name: str
    device_class: str
    device_type: str
    module: str
    capabilities: Dict[str, bool]  # flyable, movable, readable
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DeviceDefinition':
        """Create from dictionary."""
        return cls(**data)


class DeviceConfigurationManager:
    """
    Minimal device configuration manager using bluesky-queueserver's device discovery.
    """
    
    def __init__(self):
        """Initialize Device Configuration Manager."""
        self._device_definitions: Dict[str, DeviceDefinition] = {}
        
    def load_from_profile_collection(self, profile_collection_dir: Union[str, Path]) -> Dict[str, DeviceDefinition]:
        """
        Load device definitions using bluesky-queueserver's device discovery.
        
        Parameters
        ----------
        profile_collection_dir : str or Path
            Path to the profile collection directory (contains startup/ subdirectory)
            
        Returns
        -------
        dict
            Dictionary of device name -> DeviceDefinition
        """
        profile_path = Path(profile_collection_dir)
        if not profile_path.exists():
            raise FileNotFoundError(f"Profile collection directory not found: {profile_path}")
            
        logger.info(f"Loading devices via queue server from: {profile_path}")
        
        # Clear previous definitions
        self._device_definitions.clear()
        
        try:
            from bluesky_queueserver.manager.profile_ops import load_profile_collection
            
            # Queue server expects the startup directory path
            startup_path = profile_path / "startup" if (profile_path / "startup").exists() else profile_path
            
            # Load using queue server's proven logic
            namespace = load_profile_collection(startup_path, patch_profiles=True, keep_re=False)
            
            # Extract devices from namespace
            self._extract_devices_from_namespace(namespace)
            
            logger.info(f"Loaded {len(self._device_definitions)} devices via queue server")
                    
        except ImportError as e:
            raise ImportError(f"bluesky-queueserver required but not available: {e}")
            
        except Exception as e:
            raise RuntimeError(f"Error using queue server device discovery: {e}")
        
        return self._device_definitions.copy()

    def _extract_devices_from_namespace(self, namespace: Dict[str, Any]):
        """Extract device objects from the queue server namespace."""
        
        # Try ophyd devices first
        ophyd_count = self._extract_ophyd_devices(namespace)
        
        # Then ophyd-async devices  
        ophyd_async_count = self._extract_ophyd_async_devices(namespace)
        
        total = len(self._device_definitions)
        logger.info(f"Found {total} devices ({ophyd_count} ophyd, {ophyd_async_count} ophyd-async)")
    
    def _extract_ophyd_devices(self, namespace: Dict[str, Any]) -> int:
        """Extract classic Ophyd devices."""
        count = 0
        try:
            import ophyd
            from ophyd import Device
            
            for name, obj in namespace.items():
                if name.startswith('_') or name in self._device_definitions:
                    continue
                    
                if isinstance(obj, Device):
                    device_def = self._create_ophyd_definition(name, obj)
                    if device_def:
                        self._device_definitions[name] = device_def
                        count += 1
                        
        except ImportError:
            logger.debug("Classic Ophyd not available")
            
        return count
    
    def _extract_ophyd_async_devices(self, namespace: Dict[str, Any]) -> int:
        """Extract ophyd-async devices."""
        count = 0
        try:
            import ophyd_async.core
            
            for name, obj in namespace.items():
                if name.startswith('_') or name in self._device_definitions:
                    continue
                    
                if self._is_ophyd_async_device(obj):
                    device_def = self._create_ophyd_async_definition(name, obj)
                    if device_def:
                        self._device_definitions[name] = device_def
                        count += 1
                        
        except ImportError:
            logger.debug("ophyd-async not available")
            
        return count
    
    def _create_ophyd_definition(self, name: str, device_obj) -> Optional[DeviceDefinition]:
        """Create DeviceDefinition from Ophyd device."""
        try:
            import ophyd
            
            # Get basic info
            device_class = f"{device_obj.__class__.__module__}.{device_obj.__class__.__name__}"
            module = device_obj.__class__.__module__
            
            # Determine device type
            if isinstance(device_obj, ophyd.Motor):
                device_type = 'motor'
            elif isinstance(device_obj, ophyd.Detector):
                device_type = 'detector'
            elif isinstance(device_obj, ophyd.Signal):
                device_type = 'signal'
            else:
                device_type = 'device'
            
            # Determine capabilities
            capabilities = {
                'readable': hasattr(device_obj, 'read'),
                'movable': hasattr(device_obj, 'set') or isinstance(device_obj, ophyd.Motor),
                'flyable': hasattr(device_obj, 'trigger') and hasattr(device_obj, 'stage')
            }
            
            return DeviceDefinition(
                name=name,
                device_class=device_class,
                device_type=device_type,
                module=module,
                capabilities=capabilities
            )
            
        except Exception as e:
            logger.warning(f"Failed to create definition for {name}: {e}")
            return None
    
    def _is_ophyd_async_device(self, obj) -> bool:
        """Check if object is an ophyd-async device."""
        # Check for common ophyd-async interfaces
        if hasattr(obj, 'read') and hasattr(obj, 'describe') and hasattr(obj, 'name'):
            return callable(getattr(obj, 'read'))
        if hasattr(obj, 'set') and hasattr(obj, 'read'):
            return True
        if hasattr(obj, 'prepare') and hasattr(obj, 'kickoff'):
            return True
        return False
    
    def _create_ophyd_async_definition(self, name: str, device_obj) -> Optional[DeviceDefinition]:
        """Create DeviceDefinition from ophyd-async device."""
        try:
            # Get basic info
            device_class = f"{device_obj.__class__.__module__}.{device_obj.__class__.__name__}"
            module = device_obj.__class__.__module__
            class_name = device_obj.__class__.__name__.lower()
            
            # Determine device type
            if 'motor' in class_name:
                device_type = 'motor'
            elif 'detector' in class_name or 'camera' in class_name or 'panda' in class_name:
                device_type = 'detector'
            elif 'signal' in class_name:
                device_type = 'signal'
            elif 'flyer' in class_name:
                device_type = 'flyer'
            else:
                device_type = 'device'
            
            # Determine capabilities
            capabilities = {
                'readable': hasattr(device_obj, 'read') and hasattr(device_obj, 'describe'),
                'movable': hasattr(device_obj, 'set'),
                'flyable': hasattr(device_obj, 'prepare') and hasattr(device_obj, 'kickoff')
            }
            
            return DeviceDefinition(
                name=name,
                device_class=device_class,
                device_type=device_type,
                module=module,
                capabilities=capabilities
            )
            
        except Exception as e:
            logger.warning(f"Failed to create definition for {name}: {e}")
            return None
    
    def export_for_queueserver(self, output_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Export in Queue Server format (existing_plans_and_devices.yaml format).
        """
        config = {
            'existing_devices': {},
            'existing_plans': {}
        }
        
        for name, device_def in self._device_definitions.items():
            classname = device_def.device_class.split('.')[-1] if device_def.device_class else 'Unknown'
            
            config['existing_devices'][name] = {
                'classname': classname,
                'module': device_def.module,
                'is_flyable': device_def.capabilities.get('flyable', False),
                'is_movable': device_def.capabilities.get('movable', False),
                'is_readable': device_def.capabilities.get('readable', False)
            }
        
        if output_path:
            with open(output_path, 'w') as f:
                f.write("# This file is automatically generated. Edit at your own risk.\n")
                yaml.dump(config, f, default_flow_style=False)
                
        return config
    
    def export_for_oaas(self, output_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Export in OaaS format.
        """
        config = {
            'devices': {},
            'device_registry': {
                'version': '1.0',
                'source': 'bluesky_queueserver'
            }
        }
        
        for name, device_def in self._device_definitions.items():
            config['devices'][name] = device_def.to_dict()
        
        if output_path:
            with open(output_path, 'w') as f:
                json.dump(config, f, indent=2)
                
        return config
    
    def get_device_names(self) -> List[str]:
        """Get list of all device names."""
        return list(self._device_definitions.keys())
    
    def get_device(self, name: str) -> Optional[DeviceDefinition]:
        """Get specific device definition."""
        return self._device_definitions.get(name)
    
    def get_devices_by_type(self, device_type: str) -> Dict[str, DeviceDefinition]:
        """Get devices of specific type."""
        return {
            name: device for name, device in self._device_definitions.items()
            if device.device_type == device_type
        }


def create_device_config(profile_collection_path: str, 
                        output_dir: str,
                        beamline_name: str = None) -> Dict[str, str]:
    """
    Simple function to create device configuration files.
    
    Parameters
    ----------
    profile_collection_path : str
        Path to the profile collection
    output_dir : str  
        Directory to save configuration files
    beamline_name : str, optional
        Beamline identifier for file naming
        
    Returns
    -------
    dict
        Paths to generated configuration files
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Load devices
    manager = DeviceConfigurationManager()
    devices = manager.load_from_profile_collection(profile_collection_path)
    
    # Generate file names
    prefix = f"{beamline_name}_" if beamline_name else ""
    queueserver_config = output_path / f"{prefix}devices_queueserver.yaml"
    oaas_config = output_path / f"{prefix}devices_oaas.json"
    
    # Export configurations
    manager.export_for_queueserver(str(queueserver_config))
    manager.export_for_oaas(str(oaas_config))
    
    return {
        'queueserver_config': str(queueserver_config),
        'oaas_config': str(oaas_config),
        'device_count': len(devices)
    }
