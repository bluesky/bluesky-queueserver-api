"""Tests for OIDC authentication functionality"""

import asyncio

import pytest

from bluesky_queueserver_api.comm_async import ReManagerComm_HTTP_Async
from bluesky_queueserver_api.comm_threads import ReManagerComm_HTTP_Threads


class TestOIDCHelperMethods:
    """Tests for OIDC helper methods in ReManagerComm_HTTP_Threads"""

    def test_is_external_auth_with_authorize(self):
        """Test that _is_external_auth returns True for endpoints with 'authorize'"""
        RM = ReManagerComm_HTTP_Threads()
        assert RM._is_external_auth("/api/auth/provider/entra/authorize") is True
        assert RM._is_external_auth("/api/auth/provider/google/authorize") is True
        RM.close()

    def test_is_external_auth_without_authorize(self):
        """Test that _is_external_auth returns False for password endpoints"""
        RM = ReManagerComm_HTTP_Threads()
        assert RM._is_external_auth("/api/auth/provider/ldap/password") is False
        assert RM._is_external_auth("/api/auth/provider/local") is False
        RM.close()

    def test_oidc_handle_initial_response_valid(self):
        """Test _oicd_handle_initial_response with valid response"""
        RM = ReManagerComm_HTTP_Threads()
        device_response = {
            "authorization_uri": "https://login.example.com/authorize",
            "device_code": "abc123",
            "user_code": "ABCD-1234",
            "interval": 5,
            "expires_in": 300,
        }
        result = RM._oicd_handle_initial_response(device_response)
        assert result["authorization_uri"] == "https://login.example.com/authorize"
        assert result["device_code"] == "abc123"
        assert result["user_code"] == "ABCD-1234"
        assert result["interval"] == 5
        assert result["expires_in"] == 300
        RM.close()

    def test_oidc_handle_initial_response_with_verification_uri(self):
        """Test _oicd_handle_initial_response falls back to verification_uri"""
        RM = ReManagerComm_HTTP_Threads()
        device_response = {
            "verification_uri": "https://login.example.com/verify",
            "device_code": "abc123",
        }
        result = RM._oicd_handle_initial_response(device_response)
        assert result["authorization_uri"] == "https://login.example.com/verify"
        RM.close()

    def test_oidc_handle_initial_response_defaults(self):
        """Test _oicd_handle_initial_response uses defaults for missing optional fields"""
        RM = ReManagerComm_HTTP_Threads()
        device_response = {
            "authorization_uri": "https://login.example.com/authorize",
            "device_code": "abc123",
        }
        result = RM._oicd_handle_initial_response(device_response)
        assert result["user_code"] is None
        assert result["interval"] == 5  # default
        assert result["expires_in"] == 300  # default
        RM.close()

    def test_oidc_handle_initial_response_missing_authorization_uri(self):
        """Test _oicd_handle_initial_response raises error when authorization_uri is missing"""
        RM = ReManagerComm_HTTP_Threads()
        device_response = {
            "device_code": "abc123",
        }
        with pytest.raises(RM.RequestParameterError, match="missing required fields"):
            RM._oicd_handle_initial_response(device_response)
        RM.close()

    def test_oidc_handle_initial_response_missing_device_code(self):
        """Test _oicd_handle_initial_response raises error when device_code is missing"""
        RM = ReManagerComm_HTTP_Threads()
        device_response = {
            "authorization_uri": "https://login.example.com/authorize",
        }
        with pytest.raises(RM.RequestParameterError, match="missing required fields"):
            RM._oicd_handle_initial_response(device_response)
        RM.close()

    def test_oidc_handle_token_polling_response_success(self):
        """Test _oidc_handle_token_polling_response with no error returns continue signal"""
        RM = ReManagerComm_HTTP_Threads()
        token_response = {"some_field": "value"}
        result, new_interval = RM._oidc_handle_token_polling_response(token_response)
        assert result is None
        assert new_interval is None
        RM.close()

    def test_oidc_handle_token_polling_response_authorization_pending(self):
        """Test _oidc_handle_token_polling_response with authorization_pending"""
        RM = ReManagerComm_HTTP_Threads()
        token_response = {"error": "authorization_pending"}
        result, new_interval = RM._oidc_handle_token_polling_response(token_response)
        assert result is None
        assert new_interval is None
        RM.close()

    def test_oidc_handle_token_polling_response_slow_down(self):
        """Test _oidc_handle_token_polling_response with slow_down increases interval"""
        RM = ReManagerComm_HTTP_Threads()
        token_response = {"error": "slow_down"}
        result, new_interval = RM._oidc_handle_token_polling_response(token_response)
        assert result is None
        assert new_interval == 5  # Signal to add 5 seconds
        RM.close()

    def test_oidc_handle_token_polling_response_error(self):
        """Test _oidc_handle_token_polling_response raises on other errors"""
        RM = ReManagerComm_HTTP_Threads()
        token_response = {"error": "access_denied"}
        with pytest.raises(RM.RequestFailedError, match="OIDC authentication failed: access_denied"):
            RM._oidc_handle_token_polling_response(token_response)
        RM.close()

    def test_oidc_prompt_user_for_auth_with_user_code(self, capsys):
        """Test _oidc_prompt_user_for_auth prints correct messages with user_code"""
        RM = ReManagerComm_HTTP_Threads()
        device_params = {
            "authorization_uri": "https://login.example.com/authorize",
            "user_code": "ABCD-1234",
        }
        RM._oidc_prompt_user_for_auth(device_params)
        captured = capsys.readouterr()
        assert "https://login.example.com/authorize" in captured.out
        assert "ABCD-1234" in captured.out
        RM.close()

    def test_oidc_prompt_user_for_auth_without_user_code(self, capsys):
        """Test _oidc_prompt_user_for_auth only prints URI when no user_code"""
        RM = ReManagerComm_HTTP_Threads()
        device_params = {
            "authorization_uri": "https://login.example.com/authorize",
            "user_code": None,
        }
        RM._oidc_prompt_user_for_auth(device_params)
        captured = capsys.readouterr()
        assert "https://login.example.com/authorize" in captured.out
        assert "Enter this code" not in captured.out
        RM.close()


class TestOIDCHelperMethodsAsync:
    """Tests for OIDC helper methods in ReManagerComm_HTTP_Async"""

    def test_is_external_auth_with_authorize(self):
        """Test that _is_external_auth returns True for endpoints with 'authorize'"""

        async def testing():
            RM = ReManagerComm_HTTP_Async()
            assert RM._is_external_auth("/api/auth/provider/entra/authorize") is True
            await RM.close()

        asyncio.run(testing())

    def test_oidc_handle_initial_response_valid(self):
        """Test _oicd_handle_initial_response with valid response (async version)"""

        async def testing():
            RM = ReManagerComm_HTTP_Async()
            device_response = {
                "authorization_uri": "https://login.example.com/authorize",
                "device_code": "abc123",
                "user_code": "ABCD-1234",
                "interval": 5,
                "expires_in": 300,
            }
            result = RM._oicd_handle_initial_response(device_response)
            assert result["authorization_uri"] == "https://login.example.com/authorize"
            assert result["device_code"] == "abc123"
            await RM.close()

        asyncio.run(testing())

    def test_oidc_handle_token_polling_response_error(self):
        """Test _oidc_handle_token_polling_response raises on errors (async version)"""

        async def testing():
            RM = ReManagerComm_HTTP_Async()
            token_response = {"error": "access_denied"}
            with pytest.raises(RM.RequestFailedError, match="OIDC authentication failed"):
                RM._oidc_handle_token_polling_response(token_response)
            await RM.close()

        asyncio.run(testing())


# fmt: off
@pytest.mark.parametrize("endpoint, expected", [
    ("/api/auth/provider/entra/authorize", True),
    ("/api/auth/provider/google/authorize", True),
    ("/api/auth/provider/ldap/password", False),
    ("/api/auth/provider/local", False),
    ("/authorize", True),
    ("/password", False),
])
# fmt: on
def test_is_external_auth_parametrized(endpoint, expected):
    """Parametrized test for _is_external_auth across various endpoints"""
    RM = ReManagerComm_HTTP_Threads()
    assert RM._is_external_auth(endpoint) is expected
    RM.close()
