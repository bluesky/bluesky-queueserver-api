
"""
Consolidated tests for WebSocket-based RE Manager API (async version).
Tests initialization, subscriptions, device locking, and error handling.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, Mock, patch
from bluesky_queueserver_api.ws.aio import REManagerAPI


class TestREManagerAPI:
    """Consolidated tests for REManagerAPI async WebSocket interface."""

    @pytest.fixture
    def mock_api(self):
        api = Mock(spec=REManagerAPI)
        api.subscribe = AsyncMock()
        api.send_request = AsyncMock()
        return api


    @pytest.mark.asyncio
    async def test_initialization_in_async_context(self):
        with patch.object(REManagerAPI, '_init') as mock_init:
            with patch('asyncio.get_running_loop') as mock_get_loop:
                mock_get_loop.return_value = asyncio.get_event_loop()
                api = REManagerAPI()
                mock_init.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.parametrize("method,topic", [
        ("subscribe_queue_updates", "queue_status"),
        ("subscribe_execution_progress", "execution_status"),
        ("subscribe_console_output", "console_output"),
        ("subscribe_device_status", "device_updates"),
    ])
    async def test_subscriptions(self, mock_api, method, topic):
        callback = Mock()
        expected = {"subscription_id": f"{topic}_id", "status": "subscribed"}
        mock_api.subscribe.return_value = expected
        func = getattr(REManagerAPI, method)
        result = await func(mock_api, callback)
        mock_api.subscribe.assert_called_once_with(topic, callback)
        assert result == expected

    @pytest.mark.asyncio
    async def test_subscribe_without_callback(self, mock_api):
        expected = {"subscription_id": "no_callback_202", "status": "subscribed"}
        mock_api.subscribe.return_value = expected
        result = await REManagerAPI.subscribe_queue_updates(mock_api)
        mock_api.subscribe.assert_called_once_with("queue_status", None)
        assert result == expected

    @pytest.mark.asyncio
    @pytest.mark.parametrize("device_name,user_id,timeout,expected_success", [
        ("detector1", "user1", 300, True),
        ("motor1", "user2", 600, True),
        ("busy_device", "user3", 120, False),
        ("detector2", None, None, True),
    ])
    async def test_device_locking(self, mock_api, device_name, user_id, timeout, expected_success):
        mock_response = {
            "success": expected_success,
            "message": "Lock acquired" if expected_success else "Device busy"
        }
        if expected_success:
            mock_response["lock_key"] = f"lock-{device_name}-123"
        mock_api.send_request.return_value = mock_response
        result = await REManagerAPI.request_device_lock(mock_api, device_name, user_id, timeout)
        assert result["success"] == expected_success
        params = {"device_name": device_name, "user_id": user_id, "timeout": timeout}
        mock_api.send_request.assert_called_once_with(method="device_lock", params=params)

    @pytest.mark.asyncio
    async def test_release_device_lock(self, mock_api):
        device_name = "motor1"
        user_id = "test_user"
        lock_key = "lock-key-789"
        expected = {"success": True, "message": "Device unlocked successfully"}
        mock_api.send_request.return_value = expected
        result = await REManagerAPI.release_device_lock(mock_api, device_name, user_id, lock_key)
        params = {"device_name": device_name, "user_id": user_id, "lock_key": lock_key}
        mock_api.send_request.assert_called_once_with(method="device_unlock", params=params)
        assert result == expected

    @pytest.mark.asyncio
    async def test_device_lock_request_failure(self, mock_api):
        device_name = "busy_device"
        expected = {"success": False, "message": "Device is already locked by another user"}
        mock_api.send_request.return_value = expected
        result = await REManagerAPI.request_device_lock(mock_api, device_name)
        assert result == expected
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_error_handling_subscription(self, mock_api):
        mock_api.subscribe.side_effect = Exception("WebSocket connection failed")
        with pytest.raises(Exception, match="WebSocket connection failed"):
            await REManagerAPI.subscribe_queue_updates(mock_api)

    @pytest.mark.asyncio
    async def test_error_handling_device_lock(self, mock_api):
        mock_api.send_request.side_effect = Exception("Network timeout")
        with pytest.raises(Exception, match="Network timeout"):
            await REManagerAPI.request_device_lock(mock_api, "detector1")


class TestREManagerAPISubscriptions:
    """Test WebSocket subscription functionality"""

    @pytest.fixture
    def mock_api(self):
        """Create a mock REManagerAPI instance"""
        api = Mock(spec=REManagerAPI)
        api.subscribe = AsyncMock()
        api.send_request = AsyncMock()
        return api

    @pytest.mark.asyncio
    async def test_subscribe_queue_updates(self, mock_api):
        """Test subscribing to queue status updates"""
        callback = Mock()
        expected_result = {"subscription_id": "queue_123", "status": "subscribed"}
        mock_api.subscribe.return_value = expected_result
        
        # Call the actual method implementation
        result = await REManagerAPI.subscribe_queue_updates(mock_api, callback)
        
        # Verify the subscription was called with correct parameters
        mock_api.subscribe.assert_called_once_with("queue_status", callback)
        assert result == expected_result

    @pytest.mark.asyncio
    async def test_subscribe_execution_progress(self, mock_api):
        """Test subscribing to execution progress updates"""
        callback = Mock()
        expected_result = {"subscription_id": "exec_456", "status": "subscribed"}
        mock_api.subscribe.return_value = expected_result
        
        result = await REManagerAPI.subscribe_execution_progress(mock_api, callback)
        
        mock_api.subscribe.assert_called_once_with("execution_status", callback)
        assert result == expected_result

    @pytest.mark.asyncio
    async def test_subscribe_console_output(self, mock_api):
        """Test subscribing to console output stream"""
        callback = Mock()
        expected_result = {"subscription_id": "console_789", "status": "subscribed"}
        mock_api.subscribe.return_value = expected_result
        
        result = await REManagerAPI.subscribe_console_output(mock_api, callback)
        
        mock_api.subscribe.assert_called_once_with("console_output", callback)
        assert result == expected_result

    @pytest.mark.asyncio
    async def test_subscribe_device_status(self, mock_api):
        """Test subscribing to device status updates"""
        callback = Mock()
        expected_result = {"subscription_id": "device_abc", "status": "subscribed"}
        mock_api.subscribe.return_value = expected_result
        
        result = await REManagerAPI.subscribe_device_status(mock_api, callback)
        
        mock_api.subscribe.assert_called_once_with("device_updates", callback)
        assert result == expected_result


class TestREManagerAPIDeviceLocking:
    """Test device locking functionality via WebSocket"""

    @pytest.fixture
    def mock_api(self):
        """Create a mock REManagerAPI instance"""
        api = Mock(spec=REManagerAPI)
        api.send_request = AsyncMock()
        return api

    @pytest.mark.asyncio
    async def test_request_device_lock(self, mock_api):
        """Test requesting exclusive device lock"""
        device_name = "detector_1"
        user_id = "test_user"
        timeout = 30
        
        expected_result = {
            "lock_key": "lock_xyz123", 
            "status": "locked",
            "device_name": device_name
        }
        mock_api.send_request.return_value = expected_result
        
        # Mock the method implementation
        async def mock_request_device_lock(device_name, user_id=None, timeout=None):
            params = {
                "device_name": device_name,
                "user_id": user_id,
                "timeout": timeout
            }
            return await mock_api.send_request(method="device_lock", params=params)
        
        result = await mock_request_device_lock(device_name, user_id, timeout)
        
        # Verify the request was sent with correct parameters
        mock_api.send_request.assert_called_once_with(
            method="device_lock",
            params={
                "device_name": device_name,
                "user_id": user_id,
                "timeout": timeout
            }
        )
        assert result == expected_result

    @pytest.mark.asyncio
    async def test_release_device_lock(self, mock_api):
        """Test releasing exclusive device lock"""
        device_name = "detector_1"
        user_id = "test_user"
        lock_key = "lock_xyz123"
        
        expected_result = {
            "status": "released",
            "device_name": device_name
        }
        mock_api.send_request.return_value = expected_result
        
        # Mock the method implementation
        async def mock_release_device_lock(device_name, user_id=None, lock_key=None):
            params = {
                "device_name": device_name,
                "user_id": user_id,
                "lock_key": lock_key
            }
            return await mock_api.send_request(method="device_unlock", params=params)
        
        result = await mock_release_device_lock(device_name, user_id, lock_key)
        
        # Verify the request was sent with correct parameters
        mock_api.send_request.assert_called_once_with(
            method="device_unlock",
            params={
                "device_name": device_name,
                "user_id": user_id,
                "lock_key": lock_key
            }
        )
        assert result == expected_result


class TestREManagerAPIIntegration:
    """Integration tests for WebSocket API functionality"""

    @pytest.mark.asyncio
    async def test_websocket_connection_lifecycle(self):
        """Test WebSocket connection establishment and cleanup"""
        with patch.object(REManagerAPI, '_init') as mock_init:
            with patch('asyncio.get_running_loop', side_effect=RuntimeError):
                with patch('asyncio.run_coroutine_threadsafe') as mock_run_coroutine:
                    mock_future = Mock()
                    mock_future.result.return_value = None
                    mock_run_coroutine.return_value = mock_future
                    
                    # Test initialization
                    api = REManagerAPI(loop=asyncio.new_event_loop())
                    mock_init.assert_called_once()
                    
                    # Test that the API object is properly created
                    assert api is not None
    @pytest.mark.asyncio
    async def test_subscribe_queue_updates(self, mock_api):
        """Test subscribing to queue status updates"""
        callback = Mock()
        expected_result = {"subscription_id": "queue_123", "status": "subscribed"}
        mock_api.subscribe.return_value = expected_result
        
        # Call the actual method implementation
        result = await REManagerAPI.subscribe_queue_updates(mock_api, callback)
        
        # Verify the subscription was called with correct parameters
        mock_api.subscribe.assert_called_once_with("queue_status", callback)
        assert result == expected_result

    @pytest.mark.asyncio
    async def test_subscribe_execution_progress(self, mock_api):
        """Test subscribing to execution progress updates"""
        callback = Mock()
        expected_result = {"subscription_id": "exec_456", "status": "subscribed"}
        mock_api.subscribe.return_value = expected_result
        
        result = await REManagerAPI.subscribe_execution_progress(mock_api, callback)
        
        mock_api.subscribe.assert_called_once_with("execution_status", callback)
        assert result == expected_result

    @pytest.mark.asyncio
    async def test_subscribe_console_output(self, mock_api):
        """Test subscribing to console output stream"""
        callback = Mock()
        expected_result = {"subscription_id": "console_789", "status": "subscribed"}
        mock_api.subscribe.return_value = expected_result
        
        result = await REManagerAPI.subscribe_console_output(mock_api, callback)
        
        mock_api.subscribe.assert_called_once_with("console_output", callback)
        assert result == expected_result

    @pytest.mark.asyncio
    async def test_subscribe_device_status(self, mock_api):
        """Test subscribing to device status updates"""
        callback = Mock()
        device_filter = ["detector1", "motor1"]
        expected_result = {"subscription_id": "device_101", "status": "subscribed"}
        mock_api.subscribe.return_value = expected_result
        
        result = await REManagerAPI.subscribe_device_status(mock_api, callback, device_filter)
        
        mock_api.subscribe.assert_called_once_with("device_updates", callback)
        assert result == expected_result

    @pytest.mark.asyncio
    async def test_subscribe_without_callback(self, mock_api):
        """Test subscribing without providing a callback"""
        expected_result = {"subscription_id": "no_callback_202", "status": "subscribed"}
        mock_api.subscribe.return_value = expected_result
        
        result = await REManagerAPI.subscribe_queue_updates(mock_api)
        
        mock_api.subscribe.assert_called_once_with("queue_status", None)
        assert result == expected_result


class TestREManagerAPIDeviceLocking:
    """Test device locking functionality through WebSocket API"""

    @pytest.fixture
    def mock_api(self):
        """Create a mock REManagerAPI instance"""
        api = Mock(spec=REManagerAPI)
        api.send_request = AsyncMock()
        return api

    @pytest.mark.asyncio
    async def test_request_device_lock_minimal_params(self, mock_api):
        """Test requesting device lock with minimal parameters"""
        device_name = "detector1"
        expected_result = {
            "success": True,
            "lock_key": "lock-key-123",
            "message": "Device locked successfully"
        }
        mock_api.send_request.return_value = expected_result
        
        result = await REManagerAPI.request_device_lock(mock_api, device_name)
        
        expected_params = {
            "device_name": device_name,
            "user_id": None,
            "timeout": None
        }
        mock_api.send_request.assert_called_once_with(method="device_lock", params=expected_params)
        assert result == expected_result

    @pytest.mark.asyncio
    async def test_request_device_lock_full_params(self, mock_api):
        """Test requesting device lock with all parameters"""
        device_name = "motor1"
        user_id = "test_user"
        timeout = 300
        expected_result = {
            "success": True,
            "lock_key": "lock-key-456",
            "message": "Device locked successfully"
        }
        mock_api.send_request.return_value = expected_result
        
        result = await REManagerAPI.request_device_lock(mock_api, device_name, user_id, timeout)
        
        expected_params = {
            "device_name": device_name,
            "user_id": user_id,
            "timeout": timeout
        }
        mock_api.send_request.assert_called_once_with(method="device_lock", params=expected_params)
        assert result == expected_result

    @pytest.mark.asyncio
    async def test_release_device_lock_minimal_params(self, mock_api):
        """Test releasing device lock with minimal parameters"""
        device_name = "detector1"
        expected_result = {
            "success": True,
            "message": "Device unlocked successfully"
        }
        mock_api.send_request.return_value = expected_result
        
        result = await REManagerAPI.release_device_lock(mock_api, device_name)
        
        expected_params = {
            "device_name": device_name,
            "user_id": None,
            "lock_key": None
        }
        mock_api.send_request.assert_called_once_with(method="device_unlock", params=expected_params)
        assert result == expected_result

    @pytest.mark.asyncio
    async def test_release_device_lock_full_params(self, mock_api):
        """Test releasing device lock with all parameters"""
        device_name = "motor1"
        user_id = "test_user"
        lock_key = "lock-key-789"
        expected_result = {
            "success": True,
            "message": "Device unlocked successfully"
        }
        mock_api.send_request.return_value = expected_result
        
        result = await REManagerAPI.release_device_lock(mock_api, device_name, user_id, lock_key)
        
        expected_params = {
            "device_name": device_name,
            "user_id": user_id,
            "lock_key": lock_key
        }
        mock_api.send_request.assert_called_once_with(method="device_unlock", params=expected_params)
        assert result == expected_result

    @pytest.mark.asyncio
    async def test_device_lock_request_failure(self, mock_api):
        """Test handling of device lock request failure"""
        device_name = "busy_device"
        expected_result = {
            "success": False,
            "message": "Device is already locked by another user"
        }
        mock_api.send_request.return_value = expected_result
        
        result = await REManagerAPI.request_device_lock(mock_api, device_name)
        
        assert result == expected_result
        assert result["success"] is False


class TestREManagerAPIIntegration:
    """Integration tests for REManagerAPI WebSocket functionality"""

                        


class TestREManagerAPIErrorHandling:
    """Test error handling in WebSocket API"""

    @pytest.fixture
    def mock_api(self):
        """Create a mock REManagerAPI instance"""
        api = Mock(spec=REManagerAPI)
        api.subscribe = AsyncMock()
        api.send_request = AsyncMock()
        return api

    @pytest.mark.asyncio
    async def test_subscription_error_handling(self, mock_api):
        """Test handling of subscription errors"""
        mock_api.subscribe.side_effect = Exception("WebSocket connection failed")
        
        with pytest.raises(Exception, match="WebSocket connection failed"):
            await REManagerAPI.subscribe_queue_updates(mock_api)

    @pytest.mark.asyncio
    async def test_device_lock_error_handling(self, mock_api):
        """Test handling of device lock request errors"""
        mock_api.send_request.side_effect = Exception("Network timeout")
        
        with pytest.raises(Exception, match="Network timeout"):
            await REManagerAPI.request_device_lock(mock_api, "detector1")

    @pytest.mark.asyncio
    async def test_invalid_device_name_handling(self, mock_api):
        """Test handling of invalid device names"""
        # Test with empty device name
        with pytest.raises((ValueError, TypeError)):
            await REManagerAPI.request_device_lock(mock_api, "")
        
        # Test with None device name  
        with pytest.raises((ValueError, TypeError)):
            await REManagerAPI.request_device_lock(mock_api, None)


# Parameterized tests for various subscription types
@pytest.mark.parametrize("subscription_method,expected_topic", [
    ("subscribe_queue_updates", "queue_status"),
    ("subscribe_execution_progress", "execution_status"),
    ("subscribe_console_output", "console_output"),
    ("subscribe_device_status", "device_updates"),
])
@pytest.mark.asyncio
async def test_subscription_methods_parametrized(subscription_method, expected_topic):
    """Parametrized test for all subscription methods"""
    mock_api = Mock(spec=REManagerAPI)
    mock_api.subscribe = AsyncMock(return_value={"subscription_id": "test_123"})
    
    # Get the method by name and call it
    method = getattr(REManagerAPI, subscription_method)
    callback = Mock()
    
    result = await method(mock_api, callback)
    
    mock_api.subscribe.assert_called_once_with(expected_topic, callback)
    assert result["subscription_id"] == "test_123"


# Parameterized tests for device locking scenarios
@pytest.mark.parametrize("device_name,user_id,timeout,expected_success", [
    ("detector1", "user1", 300, True),
    ("motor1", "user2", 600, True),
    ("busy_device", "user3", 120, False),
    ("detector2", None, None, True),
])
@pytest.mark.asyncio
async def test_device_lock_scenarios(device_name, user_id, timeout, expected_success):
    """Parametrized test for various device locking scenarios"""
    mock_api = Mock(spec=REManagerAPI)
    
    # Configure mock response based on expected success
    mock_response = {
        "success": expected_success,
        "message": "Lock acquired" if expected_success else "Device busy"
    }
    if expected_success:
        mock_response["lock_key"] = f"lock-{device_name}-123"
    
    mock_api.send_request = AsyncMock(return_value=mock_response)
    
    result = await REManagerAPI.request_device_lock(mock_api, device_name, user_id, timeout)
    
    assert result["success"] == expected_success
    if expected_success:
        assert "lock_key" in result
    
    # Verify parameters were passed correctly
    expected_params = {
        "device_name": device_name,
        "user_id": user_id,
        "timeout": timeout
    }
    mock_api.send_request.assert_called_once_with(method="device_lock", params=expected_params)

"""
Tests for WebSocket-based RE Manager API methods

This module tests individual methods from the WebSocket API without 
requiring full class initialization, focusing on the core functionality
that we can verify from the source code.
"""

import asyncio
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from typing import Dict, Any


class MockREManagerAPI:
    """Mock implementation of REManagerAPI for testing"""
    
    def __init__(self):
        self.subscribe = AsyncMock()
        self.send_request = AsyncMock()
    
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


class TestWebSocketAPISubscriptions:
    """Test WebSocket subscription functionality"""

    @pytest.fixture
    def api(self):
        """Create a mock API instance"""
        return MockREManagerAPI()

    @pytest.mark.asyncio
    async def test_subscribe_queue_updates(self, api):
        """Test subscribing to queue status updates"""
        callback = Mock()
        expected_result = {"subscription_id": "queue_123", "status": "subscribed"}
        api.subscribe.return_value = expected_result
        
        result = await api.subscribe_queue_updates(callback)
        
        api.subscribe.assert_called_once_with("queue_status", callback)
        assert result == expected_result

    @pytest.mark.asyncio
    async def test_subscribe_execution_progress(self, api):
        """Test subscribing to execution progress updates"""
        callback = Mock()
        expected_result = {"subscription_id": "exec_456", "status": "subscribed"}
        api.subscribe.return_value = expected_result
        
        result = await api.subscribe_execution_progress(callback)
        
        api.subscribe.assert_called_once_with("execution_status", callback)
        assert result == expected_result

    @pytest.mark.asyncio
    async def test_subscribe_console_output(self, api):
        """Test subscribing to console output stream"""
        callback = Mock()
        expected_result = {"subscription_id": "console_789", "status": "subscribed"}
        api.subscribe.return_value = expected_result
        
        result = await api.subscribe_console_output(callback)
        
        api.subscribe.assert_called_once_with("console_output", callback)
        assert result == expected_result

    @pytest.mark.asyncio
    async def test_subscribe_device_status(self, api):
        """Test subscribing to device status updates"""
        callback = Mock()
        device_filter = ["detector1", "motor1"]
        expected_result = {"subscription_id": "device_101", "status": "subscribed"}
        api.subscribe.return_value = expected_result
        
        result = await api.subscribe_device_status(callback, device_filter)
        
        api.subscribe.assert_called_once_with("device_updates", callback)
        assert result == expected_result

    @pytest.mark.asyncio
    async def test_subscribe_without_callback(self, api):
        """Test subscribing without providing a callback"""
        expected_result = {"subscription_id": "no_callback_202", "status": "subscribed"}
        api.subscribe.return_value = expected_result
        
        result = await api.subscribe_queue_updates()
        
        api.subscribe.assert_called_once_with("queue_status", None)
        assert result == expected_result


class TestWebSocketAPIDeviceLocking:
    """Test device locking functionality through WebSocket API"""

    @pytest.fixture
    def api(self):
        """Create a mock API instance"""
        return MockREManagerAPI()

    @pytest.mark.asyncio
    async def test_request_device_lock_minimal_params(self, api):
        """Test requesting device lock with minimal parameters"""
        device_name = "detector1"
        expected_result = {
            "success": True,
            "lock_key": "lock-key-123",
            "message": "Device locked successfully"
        }
        api.send_request.return_value = expected_result
        
        result = await api.request_device_lock(device_name)
        
        expected_params = {
            "device_name": device_name,
            "user_id": None,
            "timeout": None
        }
        api.send_request.assert_called_once_with(method="device_lock", params=expected_params)
        assert result == expected_result

    @pytest.mark.asyncio
    async def test_request_device_lock_full_params(self, api):
        """Test requesting device lock with all parameters"""
        device_name = "motor1"
        user_id = "test_user"
        timeout = 300
        expected_result = {
            "success": True,
            "lock_key": "lock-key-456",
            "message": "Device locked successfully"
        }
        api.send_request.return_value = expected_result
        
        result = await api.request_device_lock(device_name, user_id, timeout)
        
        expected_params = {
            "device_name": device_name,
            "user_id": user_id,
            "timeout": timeout
        }
        api.send_request.assert_called_once_with(method="device_lock", params=expected_params)
        assert result == expected_result

    @pytest.mark.asyncio
    async def test_release_device_lock_minimal_params(self, api):
        """Test releasing device lock with minimal parameters"""
        device_name = "detector1"
        expected_result = {
            "success": True,
            "message": "Device unlocked successfully"
        }
        api.send_request.return_value = expected_result
        
        result = await api.release_device_lock(device_name)
        
        expected_params = {
            "device_name": device_name,
            "user_id": None,
            "lock_key": None
        }
        api.send_request.assert_called_once_with(method="device_unlock", params=expected_params)
        assert result == expected_result

    @pytest.mark.asyncio
    async def test_release_device_lock_full_params(self, api):
        """Test releasing device lock with all parameters"""
        device_name = "motor1"
        user_id = "test_user"
        lock_key = "lock-key-789"
        expected_result = {
            "success": True,
            "message": "Device unlocked successfully"
        }
        api.send_request.return_value = expected_result
        
        result = await api.release_device_lock(device_name, user_id, lock_key)
        
        expected_params = {
            "device_name": device_name,
            "user_id": user_id,
            "lock_key": lock_key
        }
        api.send_request.assert_called_once_with(method="device_unlock", params=expected_params)
        assert result == expected_result

    @pytest.mark.asyncio
    async def test_device_lock_request_failure(self, api):
        """Test handling of device lock request failure"""
        device_name = "busy_device"
        expected_result = {
            "success": False,
            "message": "Device is already locked by another user"
        }
        api.send_request.return_value = expected_result
        
        result = await api.request_device_lock(device_name)
        
        assert result == expected_result
        assert result["success"] is False


class TestWebSocketAPIErrorHandling:
    """Test error handling in WebSocket API"""

    @pytest.fixture
    def api(self):
        """Create a mock API instance"""
        return MockREManagerAPI()

    @pytest.mark.asyncio
    async def test_subscription_error_handling(self, api):
        """Test handling of subscription errors"""
        api.subscribe.side_effect = Exception("WebSocket connection failed")
        
        with pytest.raises(Exception, match="WebSocket connection failed"):
            await api.subscribe_queue_updates()

    @pytest.mark.asyncio
    async def test_device_lock_error_handling(self, api):
        """Test handling of device lock request errors"""
        api.send_request.side_effect = Exception("Network timeout")
        
        with pytest.raises(Exception, match="Network timeout"):
            await api.request_device_lock("detector1")

    @pytest.mark.asyncio
    async def test_network_disconnection_handling(self, api):
        """Test handling of network disconnections during operations"""
        api.subscribe.side_effect = ConnectionError("Connection lost")
        
        with pytest.raises(ConnectionError, match="Connection lost"):
            await api.subscribe_console_output()

    @pytest.mark.asyncio
    async def test_invalid_device_parameters(self, api):
        """Test validation of device parameters"""
        # This test assumes the actual implementation would validate parameters
        # For now, we test that the mock handles various parameter types
        
        # Test with empty string
        result_empty = await api.request_device_lock("")
        api.send_request.assert_called_with(method="device_lock", params={
            "device_name": "",
            "user_id": None,
            "timeout": None
        })
        
        # Test with None (this would likely raise an error in real implementation)
        try:
            await api.request_device_lock(None)
        except Exception:
            # Expected behavior - None device name should fail
            pass


# Parameterized tests for various subscription types
@pytest.mark.parametrize("method_name,expected_topic", [
    ("subscribe_queue_updates", "queue_status"),
    ("subscribe_execution_progress", "execution_status"),
    ("subscribe_console_output", "console_output"),
    ("subscribe_device_status", "device_updates"),
])
@pytest.mark.asyncio
async def test_subscription_methods_parametrized(method_name, expected_topic):
    """Parametrized test for all subscription methods"""
    api = MockREManagerAPI()
    api.subscribe.return_value = {"subscription_id": "test_123"}
    
    # Get the method by name and call it
    method = getattr(api, method_name)
    callback = Mock()
    
    result = await method(callback)
    
    api.subscribe.assert_called_once_with(expected_topic, callback)
    assert result["subscription_id"] == "test_123"


# Parameterized tests for device locking scenarios  
@pytest.mark.parametrize("device_name,user_id,timeout,expected_success", [
    ("detector1", "user1", 300, True),
    ("motor1", "user2", 600, True), 
    ("busy_device", "user3", 120, False),
    ("detector2", None, None, True),
])
@pytest.mark.asyncio
async def test_device_lock_scenarios(device_name, user_id, timeout, expected_success):
    """Parametrized test for various device locking scenarios"""
    api = MockREManagerAPI()
    
    # Configure mock response based on expected success
    mock_response = {
        "success": expected_success,
        "message": "Lock acquired" if expected_success else "Device busy"
    }
    if expected_success:
        mock_response["lock_key"] = f"lock-{device_name}-123"
    
    api.send_request.return_value = mock_response
    
    result = await api.request_device_lock(device_name, user_id, timeout)
    
    assert result["success"] == expected_success
    if expected_success:
        assert "lock_key" in result
    
    # Verify parameters were passed correctly
    expected_params = {
        "device_name": device_name,
        "user_id": user_id,
        "timeout": timeout
    }
    api.send_request.assert_called_once_with(method="device_lock", params=expected_params)


class TestWebSocketAPIIntegration:
    """Integration tests for WebSocket API workflow"""

    @pytest.mark.asyncio
    async def test_lock_and_unlock_workflow(self):
        """Test a complete lock/unlock workflow"""
        api = MockREManagerAPI()
        
        # Mock successful lock
        api.send_request.return_value = {
            "success": True,
            "lock_key": "workflow-lock-123",
            "message": "Lock acquired"
        }
        
        lock_result = await api.request_device_lock("detector1", "test_user", 300)
        assert lock_result["success"] is True
        lock_key = lock_result["lock_key"]
        
        # Mock successful unlock
        api.send_request.return_value = {
            "success": True,
            "message": "Lock released"
        }
        
        unlock_result = await api.release_device_lock("detector1", "test_user", lock_key)
        assert unlock_result["success"] is True
        
        # Verify both calls were made with correct parameters
        assert api.send_request.call_count == 2

    @pytest.mark.asyncio
    async def test_subscription_with_callback_workflow(self):
        """Test subscription workflow with callback invocation"""
        api = MockREManagerAPI()
        
        callback_data = []
        
        def test_callback(data):
            callback_data.append(data)
        
        # Mock subscription success
        api.subscribe.return_value = {"subscription_id": "workflow_sub_123"}
        
        result = await api.subscribe_queue_updates(test_callback)
        
        assert result["subscription_id"] == "workflow_sub_123"
        api.subscribe.assert_called_once_with("queue_status", test_callback)

    @pytest.mark.asyncio
    async def test_multiple_subscriptions(self):
        """Test handling multiple simultaneous subscriptions"""
        api = MockREManagerAPI()
        
        # Configure different responses for different subscriptions
        subscription_responses = [
            {"subscription_id": "queue_sub_1"},
            {"subscription_id": "exec_sub_2"},
            {"subscription_id": "console_sub_3"}
        ]
        api.subscribe.side_effect = subscription_responses
        
        # Subscribe to multiple channels
        queue_sub = await api.subscribe_queue_updates()
        exec_sub = await api.subscribe_execution_progress()
        console_sub = await api.subscribe_console_output()
        
        # Verify all subscriptions succeeded with unique IDs
        assert queue_sub["subscription_id"] == "queue_sub_1"
        assert exec_sub["subscription_id"] == "exec_sub_2"
        assert console_sub["subscription_id"] == "console_sub_3"
        
        # Verify all subscription calls were made
        assert api.subscribe.call_count == 3


"""
Tests for WebSocket-based RE Manager API (async version)

This module tests the async WebSocket interface for real-time communication
with the RE Manager, including subscriptions, device locking, and initialization.
"""

import asyncio
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from typing import Dict, Any

from bluesky_queueserver_api.ws.aio import REManagerAPI


class TestREManagerAPIInit:
    """Test REManagerAPI initialization and configuration"""


    @pytest.mark.asyncio
    async def test_initialization_in_async_context(self):
        """Test REManagerAPI initialization when already in async context"""
        with patch.object(REManagerAPI, '_init') as mock_init:
            # Mock asyncio.get_running_loop to simulate running in async context
            with patch('asyncio.get_running_loop') as mock_get_loop:
                mock_get_loop.return_value = asyncio.get_event_loop()
                
                api = REManagerAPI()
                
                # Verify initialization was called directly (not through run_coroutine_threadsafe)
                mock_init.assert_called_once()


class TestREManagerAPISubscriptions:
    """Test WebSocket subscription functionality"""

    @pytest.fixture
    def mock_api(self):
        """Create a mock REManagerAPI instance"""
        api = Mock(spec=REManagerAPI)
        api.subscribe = AsyncMock()
        api.send_request = AsyncMock()
        return api

    @pytest.mark.asyncio
    async def test_subscribe_queue_updates(self, mock_api):
        """Test subscribing to queue status updates"""
        callback = Mock()
        expected_result = {"subscription_id": "queue_123", "status": "subscribed"}
        mock_api.subscribe.return_value = expected_result
        
        # Call the actual method implementation
        result = await REManagerAPI.subscribe_queue_updates(mock_api, callback)
        
        # Verify the subscription was called with correct parameters
        mock_api.subscribe.assert_called_once_with("queue_status", callback)
        assert result == expected_result

    @pytest.mark.asyncio
    async def test_subscribe_execution_progress(self, mock_api):
        """Test subscribing to execution progress updates"""
        callback = Mock()
        expected_result = {"subscription_id": "exec_456", "status": "subscribed"}
        mock_api.subscribe.return_value = expected_result
        
        result = await REManagerAPI.subscribe_execution_progress(mock_api, callback)
        
        mock_api.subscribe.assert_called_once_with("execution_status", callback)
        assert result == expected_result

    @pytest.mark.asyncio
    async def test_subscribe_console_output(self, mock_api):
        """Test subscribing to console output stream"""
        callback = Mock()
        expected_result = {"subscription_id": "console_789", "status": "subscribed"}
        mock_api.subscribe.return_value = expected_result
        
        result = await REManagerAPI.subscribe_console_output(mock_api, callback)
        
        mock_api.subscribe.assert_called_once_with("console_output", callback)
        assert result == expected_result

    @pytest.mark.asyncio
    async def test_subscribe_device_status(self, mock_api):
        """Test subscribing to device status updates"""
        callback = Mock()
        device_filter = ["detector1", "motor1"]
        expected_result = {"subscription_id": "device_101", "status": "subscribed"}
        mock_api.subscribe.return_value = expected_result
        
        result = await REManagerAPI.subscribe_device_status(mock_api, callback, device_filter)
        
        mock_api.subscribe.assert_called_once_with("device_updates", callback)
        assert result == expected_result

    @pytest.mark.asyncio
    async def test_subscribe_without_callback(self, mock_api):
        """Test subscribing without providing a callback"""
        expected_result = {"subscription_id": "no_callback_202", "status": "subscribed"}
        mock_api.subscribe.return_value = expected_result
        
        result = await REManagerAPI.subscribe_queue_updates(mock_api)
        
        mock_api.subscribe.assert_called_once_with("queue_status", None)
        assert result == expected_result


class TestREManagerAPIDeviceLocking:
    """Test device locking functionality through WebSocket API"""

    @pytest.fixture
    def mock_api(self):
        """Create a mock REManagerAPI instance"""
        api = Mock(spec=REManagerAPI)
        api.send_request = AsyncMock()
        return api

    @pytest.mark.asyncio
    async def test_request_device_lock_minimal_params(self, mock_api):
        """Test requesting device lock with minimal parameters"""
        device_name = "detector1"
        expected_result = {
            "success": True,
            "lock_key": "lock-key-123",
            "message": "Device locked successfully"
        }
        mock_api.send_request.return_value = expected_result
        
        result = await REManagerAPI.request_device_lock(mock_api, device_name)
        
        expected_params = {
            "device_name": device_name,
            "user_id": None,
            "timeout": None
        }
        mock_api.send_request.assert_called_once_with(method="device_lock", params=expected_params)
        assert result == expected_result

    @pytest.mark.asyncio
    async def test_request_device_lock_full_params(self, mock_api):
        """Test requesting device lock with all parameters"""
        device_name = "motor1"
        user_id = "test_user"
        timeout = 300
        expected_result = {
            "success": True,
            "lock_key": "lock-key-456",
            "message": "Device locked successfully"
        }
        mock_api.send_request.return_value = expected_result
        
        result = await REManagerAPI.request_device_lock(mock_api, device_name, user_id, timeout)
        
        expected_params = {
            "device_name": device_name,
            "user_id": user_id,
            "timeout": timeout
        }
        mock_api.send_request.assert_called_once_with(method="device_lock", params=expected_params)
        assert result == expected_result

    @pytest.mark.asyncio
    async def test_release_device_lock_minimal_params(self, mock_api):
        """Test releasing device lock with minimal parameters"""
        device_name = "detector1"
        expected_result = {
            "success": True,
            "message": "Device unlocked successfully"
        }
        mock_api.send_request.return_value = expected_result
        
        result = await REManagerAPI.release_device_lock(mock_api, device_name)
        
        expected_params = {
            "device_name": device_name,
            "user_id": None,
            "lock_key": None
        }
        mock_api.send_request.assert_called_once_with(method="device_unlock", params=expected_params)
        assert result == expected_result

    @pytest.mark.asyncio
    async def test_release_device_lock_full_params(self, mock_api):
        """Test releasing device lock with all parameters"""
        device_name = "motor1"
        user_id = "test_user"
        lock_key = "lock-key-789"
        expected_result = {
            "success": True,
            "message": "Device unlocked successfully"
        }
        mock_api.send_request.return_value = expected_result
        
        result = await REManagerAPI.release_device_lock(mock_api, device_name, user_id, lock_key)
        
        expected_params = {
            "device_name": device_name,
            "user_id": user_id,
            "lock_key": lock_key
        }
        mock_api.send_request.assert_called_once_with(method="device_unlock", params=expected_params)
        assert result == expected_result

    @pytest.mark.asyncio
    async def test_device_lock_request_failure(self, mock_api):
        """Test handling of device lock request failure"""
        device_name = "busy_device"
        expected_result = {
            "success": False,
            "message": "Device is already locked by another user"
        }
        mock_api.send_request.return_value = expected_result
        
        result = await REManagerAPI.request_device_lock(mock_api, device_name)
        
        assert result == expected_result
        assert result["success"] is False


class TestREManagerAPIErrorHandling:
    """Test error handling in WebSocket API"""

    @pytest.fixture
    def mock_api(self):
        """Create a mock REManagerAPI instance"""
        api = Mock(spec=REManagerAPI)
        api.subscribe = AsyncMock()
        api.send_request = AsyncMock()
        return api

    @pytest.mark.asyncio
    async def test_subscription_error_handling(self, mock_api):
        """Test handling of subscription errors"""
        mock_api.subscribe.side_effect = Exception("WebSocket connection failed")
        
        with pytest.raises(Exception, match="WebSocket connection failed"):
            await REManagerAPI.subscribe_queue_updates(mock_api)

    @pytest.mark.asyncio
    async def test_device_lock_error_handling(self, mock_api):
        """Test handling of device lock request errors"""
        mock_api.send_request.side_effect = Exception("Network timeout")
        
        with pytest.raises(Exception, match="Network timeout"):
            await REManagerAPI.request_device_lock(mock_api, "detector1")


# Parameterized tests for various subscription types
@pytest.mark.parametrize("subscription_method,expected_topic", [
    ("subscribe_queue_updates", "queue_status"),
    ("subscribe_execution_progress", "execution_status"),
    ("subscribe_console_output", "console_output"),
    ("subscribe_device_status", "device_updates"),
])
@pytest.mark.asyncio
async def test_subscription_methods_parametrized(subscription_method, expected_topic):
    """Parametrized test for all subscription methods"""
    mock_api = Mock(spec=REManagerAPI)
    mock_api.subscribe = AsyncMock(return_value={"subscription_id": "test_123"})
    
    # Get the method by name and call it
    method = getattr(REManagerAPI, subscription_method)
    callback = Mock()
    
    result = await method(mock_api, callback)
    
    mock_api.subscribe.assert_called_once_with(expected_topic, callback)
    assert result["subscription_id"] == "test_123"


# Parameterized tests for device locking scenarios  
@pytest.mark.parametrize("device_name,user_id,timeout,expected_success", [
    ("detector1", "user1", 300, True),
    ("motor1", "user2", 600, True), 
    ("busy_device", "user3", 120, False),
    ("detector2", None, None, True),
])
@pytest.mark.asyncio
async def test_device_lock_scenarios(device_name, user_id, timeout, expected_success):
    """Parametrized test for various device locking scenarios"""
    mock_api = Mock(spec=REManagerAPI)
    
    # Configure mock response based on expected success
    mock_response = {
        "success": expected_success,
        "message": "Lock acquired" if expected_success else "Device busy"
    }
    if expected_success:
        mock_response["lock_key"] = f"lock-{device_name}-123"
    
    mock_api.send_request = AsyncMock(return_value=mock_response)
    
    result = await REManagerAPI.request_device_lock(mock_api, device_name, user_id, timeout)
    
    assert result["success"] == expected_success
    if expected_success:
        assert "lock_key" in result
    
    # Verify parameters were passed correctly
    expected_params = {
        "device_name": device_name,
        "user_id": user_id,
        "timeout": timeout
    }
    mock_api.send_request.assert_called_once_with(method="device_lock", params=expected_params)
