import hmac

from django.contrib.auth.models import User
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from headless.settings import headless_settings


class SecretKeyAuthentication(BaseAuthentication):
    """
    An authentication class that uses a secret key for authentication.
    Uses constant-time comparison to prevent timing attacks.

    Requests with a valid key authenticate as an (unsaved) staff user, so
    they pass the default IsAdminUser permission of the generated routes.
    """

    def __init__(self):
        super().__init__()
        if not headless_settings.AUTH_SECRET_KEY:
            raise ValueError("HEADLESS.AUTH_SECRET_KEY must be configured")

    def authenticate(self, request):
        secret_key_header = request.headers.get(headless_settings.AUTH_SECRET_KEY_HEADER, None)

        if not secret_key_header:
            return None

        if not hmac.compare_digest(secret_key_header, headless_settings.AUTH_SECRET_KEY):
            raise AuthenticationFailed("Authentication failed")

        return User(is_staff=True), None

    def authenticate_header(self, request):
        return f'{headless_settings.AUTH_SECRET_KEY_HEADER} realm="API"'
