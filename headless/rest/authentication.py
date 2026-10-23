import hmac
from dataclasses import dataclass

from django.contrib.auth.models import User
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied
from rest_framework.permissions import SAFE_METHODS

from headless.settings import headless_settings


@dataclass(frozen=True)
class SecretKey:
    """
    The credential of a request authenticated by SecretKeyAuthentication,
    available as request.auth.
    """

    read_only: bool


class SecretKeyAuthentication(BaseAuthentication):
    """
    An authentication class that uses a secret key for authentication.
    Uses constant-time comparison to prevent timing attacks.

    Two keys can be configured: HEADLESS.AUTH_SECRET_KEY grants full access,
    HEADLESS.AUTH_READ_ONLY_SECRET_KEY only grants safe (read) methods. The
    read-only restriction is enforced here, so it holds for every view using
    this class, whatever its permission classes.

    Requests with a valid key authenticate as an (unsaved) staff user, so
    they pass the default IsAdminUser permission of the generated routes.
    request.auth is a SecretKey telling which key was used.
    """

    def __init__(self):
        super().__init__()
        secret_key = headless_settings.AUTH_SECRET_KEY
        read_only_secret_key = headless_settings.AUTH_READ_ONLY_SECRET_KEY

        if not secret_key and not read_only_secret_key:
            raise ValueError("HEADLESS.AUTH_SECRET_KEY or HEADLESS.AUTH_READ_ONLY_SECRET_KEY must be configured")

        if secret_key and secret_key == read_only_secret_key:
            raise ValueError("HEADLESS.AUTH_SECRET_KEY and HEADLESS.AUTH_READ_ONLY_SECRET_KEY must be different")

    def authenticate(self, request):
        secret_key_header = request.headers.get(headless_settings.AUTH_SECRET_KEY_HEADER, None)

        if not secret_key_header:
            return None

        # Compare bytes: compare_digest rejects non-ASCII strings with a TypeError.
        # Both keys are always compared, so timing does not reveal which one is set.
        header = secret_key_header.encode()
        is_full_access = self._matches(header, headless_settings.AUTH_SECRET_KEY)
        is_read_only = self._matches(header, headless_settings.AUTH_READ_ONLY_SECRET_KEY)

        if not (is_full_access or is_read_only):
            raise AuthenticationFailed("Authentication failed")

        if not is_full_access and request.method not in SAFE_METHODS:
            raise PermissionDenied("The read-only secret key does not allow this method.")

        return User(is_staff=True), SecretKey(read_only=not is_full_access)

    def authenticate_header(self, request):
        return f'{headless_settings.AUTH_SECRET_KEY_HEADER} realm="API"'

    @staticmethod
    def _matches(header: bytes, key) -> bool:
        return bool(key) and hmac.compare_digest(header, key.encode())
