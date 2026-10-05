---
sidebar_position: 9
---

# 🛡️ Permissions

Generated routes **require authentication by default**: `HEADLESS.DEFAULT_PERMISSION_CLASSES` defaults to `rest_framework.permissions.IsAuthenticated`. A freshly exposed model is never accidentally public — requests must authenticate before the API answers.

```python
# This is the default; generated routes answer 403 for unauthenticated requests
HEADLESS = {
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
}
```

:::note Public content
For a public headless CMS, open the generated routes up explicitly — that decision should be visible in your settings:

```python
HEADLESS = {
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
}
```
:::

## Overriding for generated routes only

When you want different permissions for the headless API than for the rest of your project, set `HEADLESS.DEFAULT_PERMISSION_CLASSES`. It **replaces** DRF's `DEFAULT_PERMISSION_CLASSES` for the generated routes only; your own views are untouched. To use your `REST_FRAMEWORK` permission classes on the generated routes, set it to the same classes.

```python
# Public reads on the rest of your API, admin-only generated routes
REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
}

HEADLESS = {
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAdminUser"],
}
```

Both dotted paths and classes are accepted.

:::tip Not just permissions
All DRF-level settings — renderers, parsers, authentication, filter backends, pagination and more — can be scoped to the generated routes this way. See the [settings reference](./settings.md#drf-overrides).
:::

:::warning Authentication still applies
Requiring authentication only helps if requests *can* authenticate. Configure authentication classes via `REST_FRAMEWORK` or `HEADLESS.DEFAULT_AUTHENTICATION_CLASSES` — see [authentication](./authentication.md).
:::
