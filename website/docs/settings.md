---
sidebar_position: 10
---

# ⚙️ Settings reference

All Django Headless settings live in the `HEADLESS` dictionary in your Django settings. Every key is optional; this is the full dictionary with the defaults:

```python
# mysite/settings.py
HEADLESS = {
    "BOOT_LOG": None,
    "AUTH_SECRET_KEY": None,
    "AUTH_READ_ONLY_SECRET_KEY": None,
    "AUTH_SECRET_KEY_HEADER": "X-Secret-Key",
    "DEFAULT_RENDERER_CLASSES": None,
    "DEFAULT_PARSER_CLASSES": None,
    "DEFAULT_AUTHENTICATION_CLASSES": None,
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAdminUser"],
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

## `BOOT_LOG`

Whether the boot log is shown when the project starts. The boot log lists the exposed models, the number of generated routes, and the authentication and permission classes in use.

- `None` (default): shown under `runserver` and WSGI or ASGI servers, not for other management commands.
- `True`: always shown.
- `False`: never shown.

## DRF overrides

These settings take the same values as their Django REST Framework [counterparts](https://www.django-rest-framework.org/api-guide/settings/) in `REST_FRAMEWORK`. They apply to the generated routes only and leave your own views untouched.

| Setting                          | Default                                          |
| -------------------------------- | ------------------------------------------------ |
| `DEFAULT_RENDERER_CLASSES`       | `None`: use `REST_FRAMEWORK`                     |
| `DEFAULT_PARSER_CLASSES`         | `None`: use `REST_FRAMEWORK`                     |
| `DEFAULT_AUTHENTICATION_CLASSES` | `None`: use `REST_FRAMEWORK`                     |
| `DEFAULT_PERMISSION_CLASSES`     | `["rest_framework.permissions.IsAdminUser"]`     |
| `DEFAULT_FILTER_BACKENDS`        | `["headless.rest.filters.LookupFilter"]`         |
| `DEFAULT_PAGINATION_CLASS`       | `None`: use `REST_FRAMEWORK`                     |
| `PAGE_SIZE`                      | `None`: use `REST_FRAMEWORK`                     |
| `SEARCH_PARAM`                   | `None`: use DRF's default, `search`              |
| `ORDERING_PARAM`                 | `None`: use DRF's default, `ordering`            |

A setting set to `None` falls back to `REST_FRAMEWORK`. `DEFAULT_PERMISSION_CLASSES` and `DEFAULT_FILTER_BACKENDS` have their own defaults and never fall back: the generated routes require a staff user and support [filtering](./filtering.md) whatever `REST_FRAMEWORK` says. Set them under `HEADLESS` to change them.

```python
# mysite/settings.py
HEADLESS = {
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
    "DEFAULT_PAGINATION_CLASS": "headless.rest.pagination.PageNumberPagination",
    "PAGE_SIZE": 25,
    "SEARCH_PARAM": "q",
}
```

All these settings take dotted paths and classes.

`PAGE_SIZE` has no effect without a pagination class; set `DEFAULT_PAGINATION_CLASS` here or in `REST_FRAMEWORK`.

`SEARCH_PARAM` and `ORDERING_PARAM` apply to DRF's `SearchFilter` and `OrderingFilter` when they are in `DEFAULT_FILTER_BACKENDS`. Subclasses of those filters and other filter backends keep their own parameter names.

## `AUTH_SECRET_KEY`, `AUTH_READ_ONLY_SECRET_KEY` and `AUTH_SECRET_KEY_HEADER`

The full access key, the [read-only key](./authentication.md#read-only-key) and the header name for [`SecretKeyAuthentication`](./authentication.md). The header defaults to `X-Secret-Key`.

## `DEFAULT_SERIALIZER_CLASS`

The base class for the serializers of exposed models. Set it to `headless.rest.serializers.FlexibleSerializer` to [expand relations and serialize model properties](./serializers.md).

## Filter settings

These settings configure [`LookupFilter`](./filtering.md):

- **`FILTER_EXCLUSION_SYMBOL`**: the prefix that turns a filter into an exclusion.
- **`FILTER_TRUE_VALUES`, `FILTER_FALSE_VALUES`, `FILTER_NULL_VALUES`**: the values read as `True`, `False` and `None`.
- **`NON_FILTER_FIELDS`**: query parameters that are never read as filters. Add the parameters of your own filter backends and pagination here.

## Related pages

- [Permissions](./permissions.md)
- [Authentication](./authentication.md)
