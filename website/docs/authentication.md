---
sidebar_position: 7
---

# 🔑 Authentication

Django Headless works with any DRF authentication class through `REST_FRAMEWORK`. For machine-to-machine setups (a static site rebuild hook, a frontend build runner), it also ships a simple secret key class.

## SecretKeyAuthentication

```python
# settings.py
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "headless.rest.authentication.SecretKeyAuthentication",
    ],
}

HEADLESS = {
    "AUTH_SECRET_KEY": "your-secret-key",
}
```

Requests authenticate by sending the key in a header (default `X-Secret-Key`, configurable via `AUTH_SECRET_KEY_HEADER`):

```bash
curl -H "X-Secret-Key: your-secret-key" https://example.org/api/blog.blogpost
```

The key is compared in constant time to prevent timing attacks. Requests **without** the header are treated as anonymous, so you can combine this class with other DRF authentication classes.

:::warning Set a key
The boot log warns when `SecretKeyAuthentication` is used without a configured `AUTH_SECRET_KEY`.
:::

## Permissions

Authentication identifies the request; permissions decide what it may do. See [permissions](./permissions.md).
