"""
Django system checks for Django Headless.

They run with runserver, migrate and manage.py check; the checks registered
with deploy=True only run with manage.py check --deploy. Silence a single
check with SILENCED_SYSTEM_CHECKS, e.g. ["headless.W002"].
"""

from difflib import get_close_matches

from django.conf import settings
from django.core import checks
from rest_framework.authentication import BasicAuthentication
from rest_framework.permissions import AllowAny
from rest_framework.settings import api_settings

from .registry import headless_registry
from .settings import DEFAULTS, SETTINGS_NAMESPACE, headless_settings
from .utils import get_authentication_classes, get_permission_classes

# The minimum length and number of unique characters of a secret key
SECRET_KEY_MIN_LENGTH = 32
SECRET_KEY_MIN_UNIQUE_CHARACTERS = 5

# Example values from the documentation, which must not be used as keys
EXAMPLE_SECRET_KEYS = {"your-secret-key", "your-read-only-key"}

SECRET_KEY_SETTINGS = ["AUTH_SECRET_KEY", "AUTH_READ_ONLY_SECRET_KEY"]


def _uses_secret_key_authentication():
    """Check if the generated routes or the project's own views use SecretKeyAuthentication."""
    from .rest.authentication import SecretKeyAuthentication

    auth_classes = [*get_authentication_classes(), *api_settings.DEFAULT_AUTHENTICATION_CLASSES]
    return any(isinstance(cls, type) and issubclass(cls, SecretKeyAuthentication) for cls in auth_classes)


def _labels(model_configs):
    """Return the labels of the given model configs, for messages."""
    return ", ".join(sorted(config["model"]._meta.label_lower for config in model_configs))


@checks.register()
def check_settings(app_configs=None, **kwargs):
    """W005: the HEADLESS setting has a key that is not a Django Headless setting."""
    # A HEADLESS setting that is not a dictionary raises ImproperlyConfigured
    # on first use, at startup, so it never reaches the checks.
    warnings = []
    for key in headless_settings.user_settings:
        if key in DEFAULTS:
            continue
        matches = get_close_matches(str(key), DEFAULTS, n=1)
        hint = f'Did you mean "{matches[0]}"?' if matches else "Remove it, or see the settings reference."
        warnings.append(
            checks.Warning(
                f'{SETTINGS_NAMESPACE}["{key}"] is not a Django Headless setting, so it has no effect.',
                hint=hint,
                id="headless.W005",
            )
        )

    return warnings


@checks.register(checks.Tags.security)
def check_secret_keys(app_configs=None, **kwargs):
    """
    E001: SecretKeyAuthentication is used without a key.
    E002: the full access key and the read-only key are the same.
    """
    errors = []
    secret_key = headless_settings.AUTH_SECRET_KEY
    read_only_secret_key = headless_settings.AUTH_READ_ONLY_SECRET_KEY

    if not secret_key and not read_only_secret_key and _uses_secret_key_authentication():
        errors.append(
            checks.Error(
                "SecretKeyAuthentication is used, but no secret key is set, so every request it handles fails.",
                hint='Set HEADLESS["AUTH_SECRET_KEY"], HEADLESS["AUTH_READ_ONLY_SECRET_KEY"] or both.',
                id="headless.E001",
            )
        )

    if secret_key and secret_key == read_only_secret_key:
        errors.append(
            checks.Error(
                'HEADLESS["AUTH_SECRET_KEY"] and HEADLESS["AUTH_READ_ONLY_SECRET_KEY"] are the same, '
                "so every request authenticated with SecretKeyAuthentication fails.",
                hint="Use a different value for each key.",
                id="headless.E002",
            )
        )

    return errors


@checks.register(checks.Tags.security, deploy=True)
def check_secret_key_strength(app_configs=None, **kwargs):
    """W001: a secret key is short, has few unique characters or is an example value."""
    warnings = []

    for setting_name in SECRET_KEY_SETTINGS:
        key = getattr(headless_settings, setting_name)
        if not key:
            continue
        if (
            len(key) < SECRET_KEY_MIN_LENGTH
            or len(set(key)) < SECRET_KEY_MIN_UNIQUE_CHARACTERS
            or key in EXAMPLE_SECRET_KEYS
        ):
            warnings.append(
                checks.Warning(
                    f'HEADLESS["{setting_name}"] is weak: it is shorter than {SECRET_KEY_MIN_LENGTH} characters, '
                    f"has fewer than {SECRET_KEY_MIN_UNIQUE_CHARACTERS} unique characters, "
                    "or is an example value from the documentation.",
                    hint="Generate a long random key, e.g. with: python -c "
                    '"import secrets; print(secrets.token_urlsafe(48))"',
                    id="headless.W001",
                )
            )

    return warnings


@checks.register(checks.Tags.security)
def check_public_writes(app_configs=None, **kwargs):
    """W002: anyone can create, change and delete the content of writable exposed models."""
    permission_classes = get_permission_classes()
    is_public = not permission_classes or any(
        isinstance(cls, type) and issubclass(cls, AllowAny) for cls in permission_classes
    )
    writable = [config for config in headless_registry.get_models() if not config.get("read_only", False)]

    if not is_public or not writable:
        return []

    return [
        checks.Warning(
            "The generated routes allow every request, so anyone can create, change and delete "
            f"the content of these exposed models: {_labels(writable)}.",
            hint='Set HEADLESS["DEFAULT_PERMISSION_CLASSES"] to IsAuthenticatedOrReadOnly, '
            "or expose models that are only read with read_only=True.",
            id="headless.W002",
        )
    ]


@checks.register(checks.Tags.security, deploy=True)
def check_implicit_authentication(app_configs=None, **kwargs):
    """W003: the generated routes use DRF's default (session and basic) authentication."""
    configured_in_headless = headless_settings.DEFAULT_AUTHENTICATION_CLASSES is not None
    configured_in_drf = "DEFAULT_AUTHENTICATION_CLASSES" in getattr(settings, "REST_FRAMEWORK", {})

    if configured_in_headless or configured_in_drf or not headless_registry.get_models():
        return []

    if not any(isinstance(cls, type) and issubclass(cls, BasicAuthentication) for cls in get_authentication_classes()):
        return []

    return [
        checks.Warning(
            "No authentication classes are configured, so the generated routes use Django REST Framework's "
            "defaults, including basic authentication: clients send a username and password with every request, "
            "without rate limiting.",
            hint='Set REST_FRAMEWORK["DEFAULT_AUTHENTICATION_CLASSES"] or '
            'HEADLESS["DEFAULT_AUTHENTICATION_CLASSES"] to the classes the API needs.',
            id="headless.W003",
        )
    ]


@checks.register(checks.Tags.security, deploy=True)
def check_pagination(app_configs=None, **kwargs):
    """W004: list routes return every object in one response."""
    with_list_routes = [config for config in headless_registry.get_models() if not config["singleton"]]
    if not with_list_routes:
        return []

    pagination_class = headless_settings.DEFAULT_PAGINATION_CLASS or api_settings.DEFAULT_PAGINATION_CLASS
    page_size = None
    if pagination_class is not None:
        # The generated routes override the page size with HEADLESS["PAGE_SIZE"] when it is set.
        # DRF's pagination classes default to REST_FRAMEWORK["PAGE_SIZE"], read at import time.
        page_size = (
            headless_settings.PAGE_SIZE
            or getattr(pagination_class, "page_size", None)
            or getattr(pagination_class, "default_limit", None)
            or api_settings.PAGE_SIZE
        )

    if pagination_class is not None and page_size is not None:
        return []

    return [
        checks.Warning(
            "The list routes of the exposed models are not paginated, so a single request returns every object: "
            f"{_labels(with_list_routes)}.",
            hint='Set HEADLESS["DEFAULT_PAGINATION_CLASS"] and HEADLESS["PAGE_SIZE"], '
            "for example to headless.rest.pagination.PageNumberPagination and 25.",
            id="headless.W004",
        )
    ]
