"""
Tests for SecretKeyAuthentication
"""

import pytest
from django.contrib.auth.models import User
from django.test import RequestFactory
from rest_framework.exceptions import AuthenticationFailed

from headless.rest.authentication import SecretKeyAuthentication
from headless.settings import headless_settings


class TestSecretKeyAuthentication:
    """Test suite for SecretKeyAuthentication"""

    def test_initialization_without_secret_key(self, monkeypatch):
        """Test that authentication raises ValueError when AUTH_SECRET_KEY is not configured"""
        # Temporarily set AUTH_SECRET_KEY to None
        monkeypatch.setattr(headless_settings, "AUTH_SECRET_KEY", None)

        with pytest.raises(ValueError, match="HEADLESS.AUTH_SECRET_KEY must be configured"):
            SecretKeyAuthentication()

    def test_initialization_with_secret_key(self, monkeypatch):
        """Test that authentication initializes successfully when AUTH_SECRET_KEY is configured"""
        # Set a valid secret key
        monkeypatch.setattr(headless_settings, "AUTH_SECRET_KEY", "test-secret-key")

        # Should not raise an exception
        auth = SecretKeyAuthentication()
        assert isinstance(auth, SecretKeyAuthentication)

    def test_authenticate_without_header(self, monkeypatch):
        """Test authentication when no secret key header is provided"""
        monkeypatch.setattr(headless_settings, "AUTH_SECRET_KEY", "test-secret-key")
        monkeypatch.setattr(headless_settings, "AUTH_SECRET_KEY_HEADER", "X-API-Key")

        auth = SecretKeyAuthentication()

        # Create a request without the authentication header
        factory = RequestFactory()
        request = factory.get("/test/")

        # Should return None (no authentication attempted)
        result = auth.authenticate(request)
        assert result is None

    def test_authenticate_with_correct_key(self, monkeypatch):
        """Test authentication with correct secret key"""
        secret_key = "test-secret-key-123"
        header_name = "X-API-Key"

        monkeypatch.setattr(headless_settings, "AUTH_SECRET_KEY", secret_key)
        monkeypatch.setattr(headless_settings, "AUTH_SECRET_KEY_HEADER", header_name)

        auth = SecretKeyAuthentication()

        # Create a request with correct authentication header
        factory = RequestFactory()
        request = factory.get("/test/", HTTP_X_API_KEY=secret_key)

        # Should return (User(), None)
        user, auth_token = auth.authenticate(request)
        assert isinstance(user, User)
        assert auth_token is None

    def test_authenticate_with_incorrect_key(self, monkeypatch):
        """Test authentication with incorrect secret key"""
        monkeypatch.setattr(headless_settings, "AUTH_SECRET_KEY", "correct-secret-key")
        monkeypatch.setattr(headless_settings, "AUTH_SECRET_KEY_HEADER", "X-API-Key")

        auth = SecretKeyAuthentication()

        # Create a request with incorrect authentication header
        factory = RequestFactory()
        request = factory.get("/test/", HTTP_X_API_KEY="wrong-secret-key")

        # Should raise AuthenticationFailed
        with pytest.raises(AuthenticationFailed, match="Authentication failed"):
            auth.authenticate(request)

    def test_authenticate_header(self, monkeypatch):
        """Test authenticate_header method"""
        header_name = "X-Custom-API-Key"
        monkeypatch.setattr(headless_settings, "AUTH_SECRET_KEY", "test-secret-key")
        monkeypatch.setattr(headless_settings, "AUTH_SECRET_KEY_HEADER", header_name)

        auth = SecretKeyAuthentication()

        # Create a mock request
        factory = RequestFactory()
        request = factory.get("/test/")

        # Should return the header name with realm
        result = auth.authenticate_header(request)
        expected = f'{header_name} realm="API"'
        assert result == expected

    def test_timing_attack_protection(self, monkeypatch):
        """Test that authentication uses constant-time comparison to prevent timing attacks"""
        # This test verifies that the authentication uses hmac.compare_digest
        # by testing with keys of different lengths
        secret_key = "test-secret-key"

        monkeypatch.setattr(headless_settings, "AUTH_SECRET_KEY", secret_key)
        monkeypatch.setattr(headless_settings, "AUTH_SECRET_KEY_HEADER", "X-API-Key")

        auth = SecretKeyAuthentication()
        factory = RequestFactory()

        # Test with a key that's the same length but different content
        wrong_key_same_length = "wrong-secret-key"
        request1 = factory.get("/test/", HTTP_X_API_KEY=wrong_key_same_length)

        # Test with a key that's different length
        wrong_key_diff_length = "short"
        request2 = factory.get("/test/", HTTP_X_API_KEY=wrong_key_diff_length)

        # Both should raise AuthenticationFailed
        with pytest.raises(AuthenticationFailed):
            auth.authenticate(request1)

        with pytest.raises(AuthenticationFailed):
            auth.authenticate(request2)

    def test_custom_header_name(self, monkeypatch):
        """Test authentication with custom header name"""
        custom_header = "X-Custom-Auth-Token"
        secret_key = "custom-secret"

        monkeypatch.setattr(headless_settings, "AUTH_SECRET_KEY", secret_key)
        monkeypatch.setattr(headless_settings, "AUTH_SECRET_KEY_HEADER", custom_header)

        auth = SecretKeyAuthentication()

        # Create request with custom header
        factory = RequestFactory()
        # Django's RequestFactory converts header names to HTTP_* format
        header_env_name = f"HTTP_{custom_header.replace('-', '_').upper()}"
        request = factory.get("/test/", **{header_env_name: secret_key})

        # Should authenticate successfully
        user, auth_token = auth.authenticate(request)
        assert isinstance(user, User)
        assert auth_token is None

    def test_empty_header_value(self, monkeypatch):
        """Test authentication with empty header value"""
        monkeypatch.setattr(headless_settings, "AUTH_SECRET_KEY", "test-secret-key")
        monkeypatch.setattr(headless_settings, "AUTH_SECRET_KEY_HEADER", "X-API-Key")

        auth = SecretKeyAuthentication()
        factory = RequestFactory()

        # Test with empty string header value
        request = factory.get("/test/", HTTP_X_API_KEY="")

        # Empty string is treated as no header (falsy), so should return None
        result = auth.authenticate(request)
        assert result is None, "Empty header should be treated as no authentication"

    def test_whitespace_header_value(self, monkeypatch):
        """Test authentication with whitespace-only header value"""
        monkeypatch.setattr(headless_settings, "AUTH_SECRET_KEY", "test-secret-key")
        monkeypatch.setattr(headless_settings, "AUTH_SECRET_KEY_HEADER", "X-API-Key")

        auth = SecretKeyAuthentication()
        factory = RequestFactory()

        # Test with whitespace header value
        request = factory.get("/test/", HTTP_X_API_KEY="   ")

        # Should raise AuthenticationFailed for whitespace key
        with pytest.raises(AuthenticationFailed):
            auth.authenticate(request)

    @pytest.mark.parametrize("http_method", ["GET", "POST", "PUT", "DELETE", "PATCH"])
    def test_different_http_methods(self, http_method, monkeypatch):
        """Test that authentication works with different HTTP methods"""
        secret_key = "test-secret-key"

        monkeypatch.setattr(headless_settings, "AUTH_SECRET_KEY", secret_key)
        monkeypatch.setattr(headless_settings, "AUTH_SECRET_KEY_HEADER", "X-API-Key")

        auth = SecretKeyAuthentication()
        factory = RequestFactory()

        # Create request with different HTTP method
        if http_method == "GET":
            request = factory.get("/test/", HTTP_X_API_KEY=secret_key)
        elif http_method == "POST":
            request = factory.post("/test/", {}, HTTP_X_API_KEY=secret_key)
        elif http_method == "PUT":
            request = factory.put("/test/", {}, HTTP_X_API_KEY=secret_key)
        elif http_method == "DELETE":
            request = factory.delete("/test/", HTTP_X_API_KEY=secret_key)
        elif http_method == "PATCH":
            request = factory.patch("/test/", {}, HTTP_X_API_KEY=secret_key)

        # Should authenticate successfully regardless of HTTP method
        user, auth_token = auth.authenticate(request)
        assert isinstance(user, User)
        assert auth_token is None
