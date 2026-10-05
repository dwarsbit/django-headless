---
sidebar_position: 9
---

# 🛡️ Permissions

Generated routes inherit the permission classes from your `REST_FRAMEWORK` setting — nothing extra is required:

```python
REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAdminUser",
    ],
}
```

## Overriding for generated routes only

When you want different permissions for the headless API than for the rest of your project, set `HEADLESS.DEFAULT_PERMISSION_CLASSES`. When set, it **replaces** DRF's `DEFAULT_PERMISSION_CLASSES` for the generated routes only; your own views are untouched. Unset (the default), generated routes inherit from `REST_FRAMEWORK` as usual.

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

:::warning No authentication by default
Without any configured authentication and permission classes, generated endpoints are public for reading **and** writing. The boot log warns about this — use the options above to lock routes down.
:::
