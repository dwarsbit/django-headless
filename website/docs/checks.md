---
sidebar_position: 11
---

# 🩺 System checks

Django Headless adds checks to Django's [system check framework](https://docs.djangoproject.com/en/stable/topics/checks/) that catch risky or broken settings before a request does. They run with `runserver`, `migrate` and `python manage.py check`. Run the deployment checks as well before you deploy:

```bash
python manage.py check --deploy
```

An error stops `runserver` and other management commands until you fix it. A warning is shown but does not stop anything.

| ID              | Level   | Runs                     | Issue                                                   |
| --------------- | ------- | ------------------------ | ------------------------------------------------------- |
| `headless.E001` | Error   | Always                   | `SecretKeyAuthentication` is used without a secret key. |
| `headless.E002` | Error   | Always                   | The full access key and the read-only key are the same. |
| `headless.W001` | Warning | With `--deploy`          | A secret key is weak.                                   |
| `headless.W002` | Warning | Always                   | Anyone can change the content of exposed models.        |
| `headless.W003` | Warning | With `--deploy`          | No authentication classes are configured.               |
| `headless.W004` | Warning | With `--deploy`          | List routes are not paginated.                          |

## `headless.E001`

`SecretKeyAuthentication` is used on the generated routes or in `REST_FRAMEWORK`, but neither `HEADLESS["AUTH_SECRET_KEY"]` nor `HEADLESS["AUTH_READ_ONLY_SECRET_KEY"]` is set. Every request that the class handles fails. Set one of the keys, or both; see [Authentication](./authentication.md#secret-key-authentication).

## `headless.E002`

`AUTH_SECRET_KEY` and `AUTH_READ_ONLY_SECRET_KEY` have the same value, so the API cannot tell a full access request from a read-only one, and every request with the key fails. Use a different value for each key.

## `headless.W001`

A secret key is shorter than 32 characters, has fewer than five unique characters, or is an example value from this documentation, such as `your-secret-key`. A short key can be guessed. Generate a long random key:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

## `headless.W002`

The generated routes allow every request (`AllowAny`, or no permission classes) and at least one exposed model is not read-only, so anyone can create, change and delete its content. The warning lists those models.

To serve content publicly and accept changes only from authenticated clients, use `IsAuthenticatedOrReadOnly`, or expose models that are only read with `read_only=True`; see [Permissions](./permissions.md#public-content). If anyone may change the content on purpose, silence the warning.

## `headless.W003`

Neither `REST_FRAMEWORK` nor `HEADLESS` sets authentication classes, so the generated routes use Django REST Framework's defaults: session and basic authentication. With basic authentication, clients send a username and password with every request, and Django REST Framework does not limit failed attempts. Set the authentication classes the API needs; see [Authentication](./authentication.md#other-authentication-classes). If you configure `BasicAuthentication` yourself, the warning does not apply.

## `headless.W004`

The list routes have no pagination class, or a pagination class without a page size, so a single request returns every object of a model. Set a pagination class and a page size; see [Pagination](./pagination.md):

```python
# mysite/settings.py
HEADLESS = {
    "DEFAULT_PAGINATION_CLASS": "headless.rest.pagination.PageNumberPagination",
    "PAGE_SIZE": 25,
}
```

## Silencing a check

To accept a warning on purpose, add its ID to Django's [`SILENCED_SYSTEM_CHECKS`](https://docs.djangoproject.com/en/stable/ref/settings/#silenced-system-checks) setting:

```python
# mysite/settings.py
SILENCED_SYSTEM_CHECKS = ["headless.W002"]
```

## Related pages

- [Authentication](./authentication.md)
- [Permissions](./permissions.md)
- [Settings reference](./settings.md)
