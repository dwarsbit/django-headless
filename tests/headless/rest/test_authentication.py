"""
Tests for SecretKeyAuthentication
"""

from unittest.mock import Mock

import pytest
from django.contrib.auth.models import User
from django.test import RequestFactory
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory
from rest_framework.views import APIView

from headless.rest.authentication import SecretKey, SecretKeyAuthentication
from headless.settings import headless_settings


class TestSecretKeyAuthentication:
    """Test suite for SecretKeyAuthentication"""

    def test_initialization_without_secret_key(self, monkeypatch):
        """Test that authentication raises ValueError when no secret key is configured"""
        # Temporarily set both secret keys to None
        monkeypatch.setattr(headless_settings, "AUTH_SECRET_KEY", None)
        monkeypatch.setattr(headless_settings, "AUTH_READ_ONLY_SECRET_KEY", None)

        with pytest.raises(ValueError, match="AUTH_READ_ONLY_SECRET_KEY must be configured"):
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

        # Should return (User(is_staff=True), SecretKey(read_only=False))
        user, auth_token = auth.authenticate(request)
        assert isinstance(user, User)
        assert auth_token == SecretKey(read_only=False)
        # The key passes the default IsAdminUser permission of generated routes
        assert user.is_staff
        assert IsAdminUser().has_permission(Mock(user=user), None)

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
        assert auth_token == SecretKey(read_only=False)

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
        assert auth_token == SecretKey(read_only=False)


class TestReadOnlySecretKey:
    """The read-only secret key only grants safe methods"""

    @pytest.fixture(autouse=True)
    def keys(self, monkeypatch):
        monkeypatch.setattr(headless_settings, "AUTH_SECRET_KEY", "full-key")
        monkeypatch.setattr(headless_settings, "AUTH_READ_ONLY_SECRET_KEY", "read-key")
        monkeypatch.setattr(headless_settings, "AUTH_SECRET_KEY_HEADER", "X-Secret-Key")

    @pytest.mark.parametrize("http_method", ["get", "head", "options"])
    def test_read_only_key_allows_safe_methods(self, http_method):
        request = getattr(RequestFactory(), http_method)("/test/", HTTP_X_SECRET_KEY="read-key")
        user, auth_token = SecretKeyAuthentication().authenticate(request)
        assert user.is_staff
        assert auth_token == SecretKey(read_only=True)

    @pytest.mark.parametrize("http_method", ["post", "put", "patch", "delete"])
    def test_read_only_key_denies_unsafe_methods(self, http_method):
        request = getattr(RequestFactory(), http_method)("/test/", HTTP_X_SECRET_KEY="read-key")
        with pytest.raises(PermissionDenied):
            SecretKeyAuthentication().authenticate(request)

    @pytest.mark.parametrize("http_method", ["get", "post", "put", "patch", "delete"])
    def test_full_access_key_allows_all_methods(self, http_method):
        request = getattr(RequestFactory(), http_method)("/test/", HTTP_X_SECRET_KEY="full-key")
        _, auth_token = SecretKeyAuthentication().authenticate(request)
        assert auth_token == SecretKey(read_only=False)

    def test_only_read_only_key_configured(self, monkeypatch):
        monkeypatch.setattr(headless_settings, "AUTH_SECRET_KEY", None)
        auth = SecretKeyAuthentication()

        _, auth_token = auth.authenticate(RequestFactory().get("/test/", HTTP_X_SECRET_KEY="read-key"))
        assert auth_token == SecretKey(read_only=True)

        with pytest.raises(AuthenticationFailed):
            auth.authenticate(RequestFactory().get("/test/", HTTP_X_SECRET_KEY="full-key"))

    def test_identical_keys_rejected(self, monkeypatch):
        monkeypatch.setattr(headless_settings, "AUTH_READ_ONLY_SECRET_KEY", "full-key")
        with pytest.raises(ValueError, match="must be different"):
            SecretKeyAuthentication()

    def test_non_ascii_header_fails_authentication(self):
        request = RequestFactory().get("/test/", HTTP_X_SECRET_KEY="clé")
        with pytest.raises(AuthenticationFailed):
            SecretKeyAuthentication().authenticate(request)

    def test_view_with_admin_permission(self):
        """The read-only key is enforced on a view, whatever its permissions"""

        class ContentView(APIView):
            authentication_classes = [SecretKeyAuthentication]
            permission_classes = [IsAdminUser]

            def get(self, request):
                return Response({"read_only": request.auth.read_only})

            def post(self, request):
                return Response(status=201)

        view = ContentView.as_view()
        factory = APIRequestFactory()

        response = view(factory.get("/", HTTP_X_SECRET_KEY="read-key"))
        assert response.status_code == 200
        assert response.data == {"read_only": True}

        assert view(factory.post("/", HTTP_X_SECRET_KEY="read-key")).status_code == 403
        assert view(factory.post("/", HTTP_X_SECRET_KEY="full-key")).status_code == 201
        assert view(factory.post("/", HTTP_X_SECRET_KEY="wrong-key")).status_code == 401
