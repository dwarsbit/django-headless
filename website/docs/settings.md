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

    # DRF-level settings for the generated routes. The permission and
    # filter backends have safe defaults; the rest inherits from
    # REST_FRAMEWORK.
    "DEFAULT_RENDERER_CLASSES": None,
    "DEFAULT_PARSER_CLASSES": None,
    "DEFAULT_AUTHENTICATION_CLASSES": None,
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_FILTER_BACKENDS": ["headless.rest.filters.LookupFilter"],
    "DEFAULT_PAGINATION_CLASS": None,
    "PAGE_SIZE": None,
    "SEARCH_PARAM": None,
    "ORDERING_PARAM": None,

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

## DRF overrides

The following settings mirror DRF's `REST_FRAMEWORK` options. When set, they **override** the `REST_FRAMEWORK` value for the generated routes only — the rest of your project's API is untouched. The permission classes and filter backends have safe defaults: generated routes require authentication and support ORM filtering out of the box:

| Setting                           | Default                                          |
| --------------------------------- | ------------------------------------------------ |
| `DEFAULT_RENDERER_CLASSES`        | None — inherit from `REST_FRAMEWORK`             |
| `DEFAULT_PARSER_CLASSES`          | None — inherit from `REST_FRAMEWORK`             |
| `DEFAULT_AUTHENTICATION_CLASSES`  | None — inherit from `REST_FRAMEWORK`            |
| `DEFAULT_PERMISSION_CLASSES`      | `["rest_framework.permissions.IsAuthenticated"]` |
| `DEFAULT_FILTER_BACKENDS`         | `["headless.rest.filters.LookupFilter"]`         |
| `DEFAULT_PAGINATION_CLASS`        | None — inherit from `REST_FRAMEWORK`             |
| `PAGE_SIZE`                       | None — no page size override                     |
| `SEARCH_PARAM`                    | None — DRF's default (`search`)                  |
| `ORDERING_PARAM`                  | None — DRF's default (`ordering`)                |

```python
HEADLESS = {
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
    "DEFAULT_FILTER_BACKENDS": ["headless.rest.filters.LookupFilter"],
    "DEFAULT_PAGINATION_CLASS": "headless.rest.pagination.PageNumberPagination",
    "PAGE_SIZE": 25,
    "SEARCH_PARAM": "q",
}
```

Notes:

- `PAGE_SIZE` requires a pagination class — either `DEFAULT_PAGINATION_CLASS` in `HEADLESS` or DRF's. Without one, it does nothing.
- `SEARCH_PARAM` / `ORDERING_PARAM` apply by substituting DRF's own `SearchFilter` / `OrderingFilter` backends with parameter-carrying subclasses. Custom filter backends (including subclasses of DRF's filters) are never touched.
- Dotted paths and already-imported classes are both accepted everywhere.

## AUTH_SECRET_KEY / AUTH_SECRET_KEY_HEADER

The secret key and header name used by [`SecretKeyAuthentication`](./authentication.md). The header defaults to `X-Secret-Key`.

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
