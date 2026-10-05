---
sidebar_position: 10
---

# ⚙️ Settings reference

All Django Headless configuration lives in the `HEADLESS` dict in your Django settings:

```python
HEADLESS = {
    # True always shows the boot log, False never does.
    # The default (None) shows it automatically in server mode.
    "BOOT_LOG": None,

    "AUTH_SECRET_KEY": None,
    "AUTH_SECRET_KEY_HEADER": "X-Secret-Key",

    # When set, overrides DRF's DEFAULT_PERMISSION_CLASSES for
    # generated routes only. Unset inherits from REST_FRAMEWORK.
    "DEFAULT_PERMISSION_CLASSES": None,

    "DEFAULT_SERIALIZER_CLASS": "rest_framework.serializers.ModelSerializer",

    "FILTER_EXCLUSION_SYMBOL": "~",
    "FILTER_TRUE_VALUES": ["true", "1", "on"],
    "FILTER_FALSE_VALUES": ["false", "0", "off"],
    "FILTER_NULL_VALUES": ["null", "none", "empty"],

    "NON_FILTER_FIELDS": [
        "search",
        "limit",
        "page",
        "fields",
        "omit",
        "expand",
        "ordering",
    ],
}
```

## BOOT_LOG

Controls the boot log shown when the project starts. `None` (default) auto-detects server mode — the log appears under `runserver` and WSGI/ASGI servers, and stays silent for management commands. `True` always shows it, `False` never does.

## AUTH_SECRET_KEY / AUTH_SECRET_KEY_HEADER

The secret key and header name used by [`SecretKeyAuthentication`](./authentication.md). The header defaults to `X-Secret-Key`.

## DEFAULT_PERMISSION_CLASSES

Route-level [permission override](./permissions.md) for generated routes only.

## DEFAULT_SERIALIZER_CLASS

The base class for generated serializers — point it at `headless.rest.serializers.FlexibleSerializer` for [expansion and property fields](./serializers.md).

## FILTER_* options

Configure the [`LookupFilter`](./filtering.md) backend: the exclusion symbol, the recognized boolean/null values, and query parameters that are never treated as filters.

## REST_FRAMEWORK

DRF-level configuration (filter backends, pagination, authentication, permissions) lives in the standard `REST_FRAMEWORK` setting:

```python
REST_FRAMEWORK = {
    "DEFAULT_FILTER_BACKENDS": ["headless.rest.filters.LookupFilter"],
    "DEFAULT_PAGINATION_CLASS": "headless.rest.pagination.PageNumberPagination",
    "PAGE_SIZE": 25,
}
```
