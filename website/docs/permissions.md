---
sidebar_position: 9
---

# 🛡️ Permissions

Generated routes only answer staff users by default: `HEADLESS["DEFAULT_PERMISSION_CLASSES"]` defaults to DRF's `IsAdminUser`. A newly exposed model is not public until you open its routes up in your settings, and users without staff status cannot change content. This matters because DRF enables session and basic authentication when `REST_FRAMEWORK` sets no authentication classes, so every user account of your site can authenticate.

Requests with a valid [secret key](./authentication.md#secret-key-authentication) count as staff. The boot log shows the authentication and permission classes the generated routes use.

## Public content

For a public headless CMS, allow every request on the generated routes:

```python
# mysite/settings.py
HEADLESS = {
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
}
```

`AllowAny` also allows writes; the [system check](./checks.md#headlessw002) `headless.W002` warns about it. To serve content publicly and accept changes only from authenticated clients, use `IsAuthenticatedOrReadOnly`, or mark models that should never change through the API with `read_only=True` (see [Exposing models](./models.md#read-only-models)).

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
# Your own views are for staff users only; the generated routes are open to every authenticated user.
REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAdminUser"],
}

HEADLESS = {
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
}
```

Both settings take dotted paths and classes.

:::warning Configure authentication
Permission classes only grant access to clients that can authenticate. Configure an authentication class in `REST_FRAMEWORK` or `HEADLESS["DEFAULT_AUTHENTICATION_CLASSES"]`; see [Authentication](./authentication.md).
:::

Other DRF settings, such as renderers, parsers and pagination, can be set for the generated routes in the same way; see [DRF overrides](./settings.md#drf-overrides).

## Lookup routes

On [lookup routes](./models.md#lookup-routes), DRF's `view.action` is `"retrieve"`. A permission class that checks the action treats `GET /api/blog.article/by_slug/getting-started-with-django` like `GET /api/blog.article/1`.

## Related pages

- [Authentication](./authentication.md)
- [Settings reference](./settings.md)
