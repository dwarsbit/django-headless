---
sidebar_position: 9
---

# 🛡️ Permissions

Generated routes require authentication by default: `HEADLESS["DEFAULT_PERMISSION_CLASSES"]` defaults to DRF's `IsAuthenticated`. A newly exposed model is not public until you open its routes up in your settings.

## Public content

For a public headless CMS, allow every request on the generated routes:

```python
# mysite/settings.py
HEADLESS = {
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
}
```

`AllowAny` also allows writes. To serve content publicly and accept changes only from authenticated clients, use `IsAuthenticatedOrReadOnly`, or mark models that should never change through the API with `read_only=True` (see [Exposing models](./models.md#read-only-models)).

```python
# mysite/settings.py
HEADLESS = {
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticatedOrReadOnly"],
}
```

## Generated routes and your own views

`HEADLESS["DEFAULT_PERMISSION_CLASSES"]` applies to the generated routes only. It replaces `REST_FRAMEWORK["DEFAULT_PERMISSION_CLASSES"]` there and leaves your own views untouched. The generated routes do not use the `REST_FRAMEWORK` permission classes; to use the same classes on both, set them in both settings.

```python
# mysite/settings.py
# Your own views are public; the generated routes are for staff users only.
REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
}

HEADLESS = {
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAdminUser"],
}
```

Both settings take dotted paths and classes.

:::warning Configure authentication
`IsAuthenticated` only grants access to clients that can authenticate. Configure an authentication class in `REST_FRAMEWORK` or `HEADLESS["DEFAULT_AUTHENTICATION_CLASSES"]`; see [Authentication](./authentication.md).
:::

Other DRF settings, such as renderers, parsers and pagination, can be set for the generated routes in the same way; see [DRF overrides](./settings.md#drf-overrides).

## Related pages

- [Authentication](./authentication.md)
- [Settings reference](./settings.md)
