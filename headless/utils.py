import json
import os
import sys
from typing import List, Optional
from urllib.error import URLError
from urllib.request import urlopen

from rich.console import Console

console = Console()

# Cache key and TTL for the PyPI version lookup in get_latest_version().
LATEST_VERSION_CACHE_KEY = "headless:latest_version"
LATEST_VERSION_TTL = 60 * 60 * 24


def log(*args, **kwargs):
    console.print(*args, **kwargs)


def is_jsonable(x):
    try:
        json.dumps(x)
        return True
    except (TypeError, OverflowError):
        return False


def is_runserver():
    """
    Checks if the Django application is running as a server.

    Returns True if:
    - Django is started via WSGI/ASGI (not using manage.py)
    - Using manage.py with server commands like runserver, runserver_plus, etc.
    - Running in a context that suggests server mode (e.g., DJANGO_RUNSERVER env var)

    Returns False for management commands like migrate, makemigrations, etc.
    """
    try:
        # Check if we're using manage.py
        if os.path.basename(sys.argv[0]) == "manage.py":
            # If using manage.py, we need at least 2 arguments to have a command
            if len(sys.argv) > 1:
                # Common server commands
                server_commands = {"runserver", "runserver_plus", "runsslserver"}
                return sys.argv[1] in server_commands
            else:
                # manage.py without a command - not a server
                return False
        else:
            # If not using manage.py, assume it's a server (WSGI/ASGI)
            return True

    except IndexError:
        # If sys.argv is malformed, default to False to be safe
        return False


def is_boot_log_enabled() -> bool:
    """
    Check if the boot log should be displayed.

    The HEADLESS.BOOT_LOG setting takes precedence: True always shows the
    boot log, False never does. When unset (None), it falls back to
    automatic server-mode detection via is_runserver().
    """
    from headless.settings import headless_settings

    boot_log = headless_settings.BOOT_LOG

    if boot_log is None:
        return is_runserver()

    return bool(boot_log)


def flatten(xss):
    return [x for xs in xss for x in xs]


def configured_auth_classes() -> List[str] | None:
    """Return the authentication class configured in REST_FRAMEWORK"""
    from django.conf import settings

    if not hasattr(settings, "REST_FRAMEWORK"):
        return None

    auth_classes = settings.REST_FRAMEWORK.get("DEFAULT_AUTHENTICATION_CLASSES", [])

    if not auth_classes:
        return None

    auth_class_paths = []

    for auth_class in auth_classes:
        try:
            if hasattr(auth_class, "__module__") and hasattr(auth_class, "__name__"):
                full_path = auth_class.__module__ + "." + auth_class.__name__
                auth_class_paths.append(full_path)
            else:
                auth_class_paths.append(auth_class)
        except:
            pass

    return auth_classes


def is_auth_configured() -> bool:
    """Check if at least one authentication class is configured in REST_FRAMEWORK"""

    auth_classes = configured_auth_classes()

    return bool(auth_classes)


def is_secret_key_auth_configured() -> bool:
    """Check if SecretKeyAuthentication is configured"""
    from headless.settings import headless_settings

    return bool(headless_settings.AUTH_SECRET_KEY)


def is_secret_key_auth_used():
    """Check if SecretKeyAuthentication is in REST_FRAMEWORK.DEFAULT_AUTHENTICATION_CLASSES"""
    from headless.rest.authentication import SecretKeyAuthentication

    auth_classes = configured_auth_classes()
    secret_key_class_path = SecretKeyAuthentication.__module__ + "." + SecretKeyAuthentication.__name__

    for auth_class in auth_classes:
        if auth_class == secret_key_class_path:
            return True

    return False


def normalize_version(version: str) -> str:
    """Normalize version strings for comparison (e.g., '1.0.0b6' -> '1.0.0-beta.6')"""
    if not version:
        return version

    # Handle prerelease versions: b6 -> beta.6, a6 -> alpha.6, rc6 -> rc.6
    # Use regex to avoid overlapping replacements
    import re

    # Replace bX with -beta.X (but not if already in beta format)
    version = re.sub(r"\b(\d+\.\d+\.\d+)b(\d+)", r"\1-beta.\2", version)
    # Replace aX with -alpha.X
    version = re.sub(r"\b(\d+\.\d+\.\d+)a(\d+)", r"\1-alpha.\2", version)
    # Replace rcX with -rc.X
    version = re.sub(r"\b(\d+\.\d+\.\d+)rc(\d+)", r"\1-rc.\2", version)

    return version


def get_latest_version() -> Optional[str]:
    """
    Fetch the latest version of django-headless from PyPI.
    The result is cached: successful lookups for a day, failures for a few
    minutes, so a slow or unreachable PyPI can stall at most one boot.
    """
    from django.core.cache import cache

    cached = cache.get(LATEST_VERSION_CACHE_KEY)
    if cached is not None:
        return cached or None

    version = None

    try:
        # Fetch the PyPI JSON API for django-headless
        with urlopen("https://pypi.org/pypi/django-headless/json", timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))
            version = data.get("info", {}).get("version")
    except (URLError, json.JSONDecodeError, KeyError):
        # If there's any error (network, JSON parsing, etc.), version stays None
        pass

    # Cache the version, or an empty sentinel on failure, so a single slow
    # or failing request doesn't repeat on every boot.
    cache.set(LATEST_VERSION_CACHE_KEY, version or "", LATEST_VERSION_TTL if version else 60 * 5)

    return version
