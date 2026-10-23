---
sidebar_position: 7
---

# 🔑 Authentication

Generated routes only answer staff users by default (see [Permissions](./permissions.md)), so a client gets access by authenticating. Django Headless works with any Django REST Framework [authentication class](https://www.django-rest-framework.org/api-guide/authentication/), and ships `SecretKeyAuthentication` for clients that run without a user, such as a static site build.

## Secret key authentication

To let a client authenticate with a shared secret key:

1. Set the key and add `SecretKeyAuthentication` to the generated routes:

   ```python
   # mysite/settings.py
   HEADLESS = {
       "AUTH_SECRET_KEY": "your-secret-key",
       "DEFAULT_AUTHENTICATION_CLASSES": [
           "headless.rest.authentication.SecretKeyAuthentication",
       ],
   }
   ```

2. Send the key in the `X-Secret-Key` header with each request:

   ```bash
   curl -H "X-Secret-Key: your-secret-key" https://example.org/api/blog.article
   ```

Read the key from an environment variable rather than writing it in `settings.py`. Change the header name with `HEADLESS["AUTH_SECRET_KEY_HEADER"]`.

A request with a wrong key, or a key with characters outside ASCII, answers `401 Unauthorized`. A request without the header is passed on to the next authentication class, so you can combine `SecretKeyAuthentication` with session or token authentication.

To use `SecretKeyAuthentication` on your own views as well, add it to `REST_FRAMEWORK["DEFAULT_AUTHENTICATION_CLASSES"]` instead.

:::warning Set a key
Without `AUTH_SECRET_KEY` or `AUTH_READ_ONLY_SECRET_KEY`, every request to a route that uses `SecretKeyAuthentication` fails with an error. The [system check](./checks.md#headlesse001) `headless.E001` reports a missing key and stops `runserver` until you set one.
:::

A request authenticated with the secret key is not tied to a user account. It counts as a staff user, so it passes the default `IsAdminUser` permission and can read and change content on the generated routes.

### Read-only key

A frontend that only reads content does not need a key that can change it. Give it a read-only key with `HEADLESS["AUTH_READ_ONLY_SECRET_KEY"]`. This key allows `GET`, `HEAD` and `OPTIONS` requests; other methods answer `403 Forbidden`.

```python
# mysite/settings.py
HEADLESS = {
    "AUTH_SECRET_KEY": "your-secret-key",
    "AUTH_READ_ONLY_SECRET_KEY": "your-read-only-key",
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "headless.rest.authentication.SecretKeyAuthentication",
    ],
}
```

Both keys are sent in the same header. Set either key or both; they must be different. `SecretKeyAuthentication` enforces the read-only restriction itself, so it holds on every view that uses it, whatever the permission classes.

In your own permission classes, `request.auth.read_only` tells whether a request used the read-only key.

## Other authentication classes

Configure DRF's own classes the same way, in `HEADLESS["DEFAULT_AUTHENTICATION_CLASSES"]` for the generated routes only, or in `REST_FRAMEWORK` for your whole project:

```python
# mysite/settings.py
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.TokenAuthentication",
    ],
}
```

When `HEADLESS["DEFAULT_AUTHENTICATION_CLASSES"]` is not set, the generated routes use the classes in `REST_FRAMEWORK`.

## Related pages

- [Permissions](./permissions.md)
- [Settings reference](./settings.md#auth_secret_key-auth_read_only_secret_key-and-auth_secret_key_header)
