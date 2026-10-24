"""
Helpers for the REST routes: the authentication and permission classes they
use, and the state of SecretKeyAuthentication.
"""


def get_authentication_classes() -> list:
    """
    Return the authentication classes the generated routes actually use:
    HEADLESS.DEFAULT_AUTHENTICATION_CLASSES when set, otherwise DRF's
    resolved DEFAULT_AUTHENTICATION_CLASSES (including DRF's own defaults
    when REST_FRAMEWORK does not set them).
    """
    from rest_framework.settings import api_settings
    from headless.settings import headless_settings

    auth_classes = headless_settings.DEFAULT_AUTHENTICATION_CLASSES
    if auth_classes is None:
        auth_classes = api_settings.DEFAULT_AUTHENTICATION_CLASSES

    return list(auth_classes)


def get_permission_classes() -> list:
    """
    Return the permission classes the generated routes actually use:
    HEADLESS.DEFAULT_PERMISSION_CLASSES when set, otherwise DRF's resolved
    DEFAULT_PERMISSION_CLASSES.
    """
    from rest_framework.settings import api_settings
    from headless.settings import headless_settings

    permission_classes = headless_settings.DEFAULT_PERMISSION_CLASSES
    if permission_classes is None:
        permission_classes = api_settings.DEFAULT_PERMISSION_CLASSES

    return list(permission_classes)


def class_path(cls) -> str:
    """Return the dotted import path of a class."""
    return f"{cls.__module__}.{cls.__qualname__}"


def is_secret_key_auth_configured() -> bool:
    """Check if a secret key (full access or read-only) is configured for SecretKeyAuthentication"""
    from headless.settings import headless_settings

    return bool(headless_settings.AUTH_SECRET_KEY or headless_settings.AUTH_READ_ONLY_SECRET_KEY)


def is_secret_key_auth_used() -> bool:
    """Check if the generated routes use SecretKeyAuthentication (or a subclass)"""
    from .authentication import SecretKeyAuthentication

    return any(
        isinstance(auth_class, type) and issubclass(auth_class, SecretKeyAuthentication)
        for auth_class in get_authentication_classes()
    )
