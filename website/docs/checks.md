---
sidebar_position: 13
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
| `headless.E003` | Error   | Always                   | The schema is enabled, but its packages are missing.    |
| `headless.W001` | Warning | With `--deploy`          | A secret key is weak.                                   |
| `headless.W002` | Warning | Always                   | Anyone can change the content of exposed models.        |
| `headless.W003` | Warning | With `--deploy`          | No authentication classes are configured.               |
| `headless.W004` | Warning | With `--deploy`          | List routes are not paginated.                          |
| `headless.W005` | Warning | Always                   | `HEADLESS` has a key that is not a setting.             |
| `headless.W006` | Warning | Always                   | A field that looks like a credential is serialized.     |
| `headless.W007` | Warning | Always                   | A user model is exposed without a `fields` list.        |
| `headless.W008` | Warning | Always                   | A model is exposed more than once with other options.   |
| `headless.W009` | Warning | Always                   | An exposed model has no routes.                         |
| `headless.W010` | Warning | Always                   | Models are exposed, but `headless.rest` is not installed. |

## `headless.E001`

`SecretKeyAuthentication` is used on the generated routes or in `REST_FRAMEWORK`, but neither `HEADLESS["AUTH_SECRET_KEY"]` nor `HEADLESS["AUTH_READ_ONLY_SECRET_KEY"]` is set. Every request that the class handles fails. Set one of the keys, or both; see [Authentication](./authentication.md#secret-key-authentication).

## `headless.E002`

`AUTH_SECRET_KEY` and `AUTH_READ_ONLY_SECRET_KEY` have the same value, so the API cannot tell a full access request from a read-only one, and every request with the key fails. Use a different value for each key.

## `headless.E003`

`HEADLESS["SCHEMA"]` is enabled, but the `uritemplate` or `inflection` package that generates the [OpenAPI schema](./schema.md) is not installed, so the schema route fails. Install them with the `schema` extra:

```bash
pip install "django-headless[schema]"
```

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

## `headless.W005`

`HEADLESS` has a key that is not a Django Headless setting, usually a typo such as `PAGESIZE` for `PAGE_SIZE`. The key has no effect, so the default applies instead, which matters most for settings such as `DEFAULT_PERMISSION_CLASSES`. The hint suggests the closest setting name; see the [settings reference](./settings.md) for all names.

`HEADLESS` itself must be a dictionary. Any other value raises `ImproperlyConfigured` when the project starts.

## `headless.W006`

An exposed model serializes a field whose name looks like a credential, and the field is not named in its `fields` option. A name counts when one of its parts (split on `_`) is `password`, `passwd`, `pwd`, `secret`, `token`, `otp`, `salt` or `apikey`, or when it contains `api_key`, `private_key` or `access_key`. For example, `password_hash`, `access_token` and `stripe_api_key` count, and `sort_key` and `tokenizer` do not. The warning names the model and the field.

Leave the field out with `exclude`. A field that is left out can still be a [lookup field](./models.md#lookup-routes), for example a share token that fetches an object without appearing in the response:

```python
# blog/models.py
from django.db import models
from headless import expose


@expose(exclude=["share_token"], lookup_fields=["share_token"])
class Article(models.Model):
    title = models.CharField(max_length=200)
    share_token = models.CharField(max_length=64, unique=True)
```

If the API should serialize the field, name it in `fields`: a field listed there is a deliberate choice and does not trigger the warning.

## `headless.W007`

A user model, a subclass of Django's `AbstractBaseUser` such as `django.contrib.auth.models.User`, is exposed without a `fields` option. Such a model holds the password hash, the email address, permissions and login data, and `exclude` easily misses one. List the fields the API may serialize:

```python
# blog/models.py
from django.contrib.auth.models import User
from headless import expose_model

expose_model(User, fields=["username", "first_name", "last_name"])
```

## `headless.W008`

A model is exposed more than once with different options, for example with `@expose()` on the model and `expose_model()` elsewhere. Only the last registration is in effect, so options of the earlier one are lost. Expose the model once, with all its options. Exposing a model again with the same options does not trigger the warning.

## `headless.W009`

A model is exposed but has no routes. Django Headless builds the routes when the `headless.rest` app is ready, so a model exposed after that, for example with `expose_model()` in the `ready()` method of an app listed after `headless.rest` in `INSTALLED_APPS`, is never added. Call `expose_model()` in a models module, or in the `ready()` method of an app listed before `headless.rest`; see [Exposing models](./models.md).

## `headless.W010`

Models are exposed, but `headless.rest`, the app that serves them, is not in `INSTALLED_APPS`, so the API has no routes. `headless` only keeps track of the exposed models. Add `headless.rest` after `headless`; see [Installation](./installation.md):

```python
# mysite/settings.py
INSTALLED_APPS = [
    # ...
    "rest_framework",
    "headless",
    "headless.rest",
]
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
