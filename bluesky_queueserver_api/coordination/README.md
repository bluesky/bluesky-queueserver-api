# Device Coordination Service

The Device Coordination Service is a component of the Bluesky Queue Server API that mediates device access between different services to prevent conflicts and ensure safe operations.

## Overview

This service provides:
- **Device Lock Management**: Priority-based locking system for devices
- **Conflict Prevention**: Prevents multiple services from accessing the same device simultaneously
- **Real-time Notifications**: WebSocket updates for lock status changes
- **Integration**: Seamless integration with Queue Server and Ophyd WebSocket services
- **Persistence**: Redis-backed lock persistence across service restarts

## Architecture

The coordination service consists of:
- **Service** (`service.py`): Main FastAPI application providing HTTP and WebSocket APIs
- **Client** (`client.py`): Client library for other services to interact with the coordination service
- **Models** (`models.py`): Data models and types for lock management

## Lock Types and Priorities

Locks are prioritized to handle conflicts (lower number = higher priority):

1. **MAINTENANCE** (0): System maintenance or emergency access
2. **QUEUE_EXECUTING** (1): Queue server is actively using the device
3. **MANUAL_OPERATOR** (2): Manual operator access
4. **QUEUE_QUEUED** (3): Device reserved for queued plan

Higher priority locks can override lower priority locks automatically.

## Usage

### Running the Service

#### As a Standalone Service
```bash
# From project root
python -m bluesky_queueserver_api.coordination.service --help

# Basic usage
python -m bluesky_queueserver_api.coordination.service --host 0.0.0.0 --port 60620

# With device configuration integration
python -m bluesky_queueserver_api.coordination.service \
    --profile-collection /path/to/profile_collection \
    --host 0.0.0.0 --port 60620
```

#### Using the Standalone Script
```bash
./bluesky_queueserver_api/coordination/run_coordination_service.py --help
./bluesky_queueserver_api/coordination/run_coordination_service.py --port 60620
```

#### Programmatically
```python
from bluesky_queueserver_api.coordination import DeviceCoordinationService

service = DeviceCoordinationService(profile_collection_path="/path/to/profile")
service.run(host="0.0.0.0", port=60620)
```

### Client Usage

#### Basic Client Operations
```python
from bluesky_queueserver_api.coordination import (
    DeviceCoordinationClient, 
    LockType
)

# Create client
async with DeviceCoordinationClient("http://localhost:60620") as client:
    # Request a lock
    response = await client.request_lock(
        device_name="detector1",
        lock_type=LockType.MANUAL_OPERATOR,
        user_id="operator123",
        timeout=300,
        reason="Calibration"
    )
    
    if response.success:
        print(f"Lock acquired: {response.lock_key}")
        
        # Perform operations...
        
        # Release lock
        await client.release_lock("detector1", response.lock_key, "operator123")
```

#### Context Manager (Auto-release)
```python
from bluesky_queueserver_api.coordination import (
    DeviceCoordinationContext,
    DeviceCoordinationClient,
    LockType
)

client = DeviceCoordinationClient("http://localhost:60620")
await client.connect()

# Automatic lock management
async with DeviceCoordinationContext(
    client, "detector1", LockType.MANUAL_OPERATOR, "user123"
) as lock_key:
    # Device is locked here
    print(f"Using device with lock: {lock_key}")
    # Perform operations...
# Device is automatically unlocked here
```

#### Real-time Monitoring
```python
def on_lock_update(device_name, lock, action):
    print(f"Device {device_name}: {action} - {lock.lock_type}")

client = DeviceCoordinationClient("http://localhost:60620")
await client.connect()

# Add callback for lock updates
client.add_lock_update_callback(on_lock_update)

# Start WebSocket monitoring
await client.start_websocket_monitoring()

# Monitor for some time...
await asyncio.sleep(60)

# Stop monitoring
await client.stop_websocket_monitoring()
await client.disconnect()
```

### Integration with Ophyd WebSocket

The enhanced Ophyd WebSocket Server (in `/server/ophyd_ws_server.py`) automatically integrates with the coordination service:

```python
# Ophyd server checks coordination service before device access
enhanced_server = UnifiedOphydWebSocketServer(
    coordination_url="http://localhost:60620",
    user_id="ophyd_websocket"
)
```

### Integration with Queue Server

The Queue Server can use the coordination service to prevent conflicts during plan execution:

```python
from bluesky_queueserver_api.coordination import DeviceCoordinationClient, LockType

# In queue server, before executing plan
client = DeviceCoordinationClient()
await client.connect()

# Lock devices for plan execution
devices_to_lock = ["detector1", "motor1", "motor2"] 
lock_keys = {}

for device in devices_to_lock:
    response = await client.request_lock(
        device_name=device,
        lock_type=LockType.QUEUE_EXECUTING,
        user_id="queue_server",
        plan_uid=plan_uid,
        timeout=estimated_plan_duration
    )
    if response.success:
        lock_keys[device] = response.lock_key

# Execute plan...

# Release locks after plan completion
for device, lock_key in lock_keys.items():
    await client.release_lock(device, lock_key, "queue_server")
```

## API Reference

### HTTP Endpoints

- `POST /api/lock/request` - Request a device lock
- `POST /api/lock/release` - Release a device lock  
- `GET /api/locks/status` - Get all active locks
- `GET /api/locks/device/{device_name}` - Get lock status for specific device
- `GET /api/health/live` - Liveness check
- `GET /api/health/ready` - Readiness check

### WebSocket Endpoint

- `WS /ws` - Real-time lock status updates

### WebSocket Messages

#### Incoming (Client → Service)
```json
{"type": "ping"}
{"type": "get_status"}
```

#### Outgoing (Service → Client)
```json
{
  "type": "initial_status",
  "data": {"locks": [...], "total_count": 3, "timestamp": "..."}
}

{
  "type": "lock_update", 
  "action": "acquired|released|force_released",
  "device_name": "detector1",
  "lock": {...},
  "timestamp": "..."
}

{"type": "pong", "timestamp": "..."}
```

## Configuration

### Environment Variables

- `COORDINATION_REDIS_URL`: Redis connection URL (default: `redis://localhost:60590`)
- `COORDINATION_LOG_LEVEL`: Logging level (default: `INFO`)

### Dependencies

The coordination service requires:
- `fastapi` - Web framework
- `uvicorn` - ASGI server
- `aioredis` - Redis client
- `pydantic` - Data validation
- `websockets` - WebSocket support (for client)
- `aiohttp` - HTTP client (for client)

Install with:
```bash
pip install fastapi uvicorn aioredis pydantic websockets aiohttp
```

## Deployment

### Development
```bash
python -m bluesky_queueserver_api.coordination.service --host 0.0.0.0 --port 60620
```

### Production with Uvicorn
```bash
uvicorn bluesky_queueserver_api.coordination.service:create_app --host 0.0.0.0 --port 60620
```

### Docker
```dockerfile
FROM python:3.10

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY bluesky_queueserver_api/ ./bluesky_queueserver_api/

EXPOSE 60620

CMD ["python", "-m", "bluesky_queueserver_api.coordination.service", "--host", "0.0.0.0", "--port", "60620"]
```

## Examples

See the `/server/ophyd_ws_server.py` for a complete example of coordination service integration in the enhanced Ophyd WebSocket server.
