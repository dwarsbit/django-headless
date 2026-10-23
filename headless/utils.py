import json
import os
import re
import sys
from typing import List, Optional
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


# Programs that serve a Django project, by the name they are started with.
SERVER_PROGRAMS = {
    "gunicorn",
    "uvicorn",
    "daphne",
    "hypercorn",
    "uwsgi",
    "waitress-serve",
    "granian",
    "mod_wsgi",
}

# Programs that run Django management commands: manage.py, django-admin
# and python -m django.
MANAGEMENT_PROGRAMS = {"manage", "django-admin", "django"}

# Management commands that run a development server.
SERVER_COMMANDS = {"runserver", "runserver_plus", "runsslserver"}


def get_program_name(argv0: str) -> str:
    """
    Return the name of the program from sys.argv[0]: the file name without
    its .py or .exe extension, or the package name for python -m <package>.
    Handles both POSIX and Windows paths.
    """
    parts = re.split(r"[\\/]", argv0)
    name = parts[-1]
    if name == "__main__.py" and len(parts) > 1:
        name = parts[-2]
    return re.sub(r"\.(py|exe)$", "", name)


def is_runserver() -> bool:
    """
    Checks if the Django application is running as a server.

    Returns True for:
    - the development server (runserver, runserver_plus, runsslserver), in
      the process that serves requests: with autoreload, the parent process
      only watches files and runs the server in a child process;
    - known WSGI and ASGI servers, such as Gunicorn and Uvicorn.

    Returns False for everything else: other management commands, tests,
    task workers such as Celery, scripts and shells.
    """
    argv = getattr(sys, "argv", None) or []
    if not argv:
        return False

    program = get_program_name(argv[0])

    if program in MANAGEMENT_PROGRAMS:
        if len(argv) < 2 or argv[1] not in SERVER_COMMANDS:
            return False
        return (
            "--noreload" in argv
            or os.environ.get("RUN_MAIN") == "true"
            or os.environ.get("WERKZEUG_RUN_MAIN") == "true"
        )

    return program in SERVER_PROGRAMS


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

    return auth_class_paths


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


def is_auth_configured() -> bool:
    """Check if at least one authentication class is configured in REST_FRAMEWORK"""

    auth_classes = configured_auth_classes()

    return bool(auth_classes)


def is_secret_key_auth_configured() -> bool:
    """Check if a secret key (full access or read-only) is configured for SecretKeyAuthentication"""
    from headless.settings import headless_settings

    return bool(headless_settings.AUTH_SECRET_KEY or headless_settings.AUTH_READ_ONLY_SECRET_KEY)


def is_secret_key_auth_used() -> bool:
    """Check if the generated routes use SecretKeyAuthentication (or a subclass)"""
    from headless.rest.authentication import SecretKeyAuthentication

    return any(
        isinstance(auth_class, type) and issubclass(auth_class, SecretKeyAuthentication)
        for auth_class in get_authentication_classes()
    )


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


# Pre-release markers in version strings and their order; a final release
# sorts after all of them.
PRE_RELEASE_ORDER = {"a": 0, "alpha": 0, "b": 1, "beta": 1, "c": 2, "rc": 2}
FINAL_RELEASE = 3

VERSION_PATTERN = re.compile(r"^v?(\d+(?:\.\d+)*)(?:[-.]?(alpha|beta|rc|a|b|c)[-.]?(\d*))?$", re.IGNORECASE)


def parse_version(version: str) -> Optional[tuple]:
    """
    Parse a version such as "1.0.0", "1.0.0rc9" or "1.0.0-rc.9" into a
    comparable tuple. Returns None for versions that can't be parsed.
    """
    match = VERSION_PATTERN.match((version or "").strip())
    if not match:
        return None

    release, pre_release, pre_number = match.groups()
    numbers = [int(part) for part in release.split(".")]
    # Pad the release, so "1.0" and "1.0.0" compare equal
    numbers += [0] * (3 - len(numbers))
    pre_rank = PRE_RELEASE_ORDER[pre_release.lower()] if pre_release else FINAL_RELEASE

    return (*numbers, pre_rank, int(pre_number or 0))


def is_newer_version(latest: str, current: str) -> bool:
    """
    Check whether the latest version is newer than the current one. Versions
    that can't be parsed are never reported as newer.
    """
    latest_parsed = parse_version(latest)
    current_parsed = parse_version(current)
    return latest_parsed is not None and current_parsed is not None and latest_parsed > current_parsed


def get_latest_version() -> Optional[str]:
    """
    Fetch the latest version of django-headless from PyPI.
    The result is cached: successful lookups for a day, failures for a few
    minutes, so a slow or unreachable PyPI can stall at most one boot.

    The check is best-effort: any error, from the network, PyPI's response
    or the cache backend, results in None and never stops the project
    from starting.
    """
    from django.core.cache import cache

    try:
        cached = cache.get(LATEST_VERSION_CACHE_KEY)
    except Exception:
        cached = None
    if cached is not None:
        return cached or None

    version = None

    try:
        # Fetch the PyPI JSON API for django-headless
        with urlopen("https://pypi.org/pypi/django-headless/json", timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))
            version = data.get("info", {}).get("version")
    except Exception:
        # Network errors, timeouts, HTTP errors, invalid JSON: version stays None
        pass

    if not isinstance(version, str):
        version = None

    # Cache the version, or an empty sentinel on failure, so a single slow
    # or failing request doesn't repeat on every boot.
    try:
        cache.set(LATEST_VERSION_CACHE_KEY, version or "", LATEST_VERSION_TTL if version else 60 * 5)
    except Exception:
        pass

    return version
