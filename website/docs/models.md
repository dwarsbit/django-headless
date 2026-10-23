---
sidebar_position: 3
---

# 🎯 Exposing models

Expose a model with the `@expose()` decorator to give it generated routes. Use the decorator options to make a model a singleton, limit its fields, make it read-only or add lookup routes by a unique field.

```python
# blog/models.py
from django.db import models
from headless import expose


@expose()
class Category(models.Model):
    name = models.CharField(max_length=100)


@expose()
class Article(models.Model):
    title = models.CharField(max_length=200)
    body = models.TextField()
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="articles")
```

Each exposed model gets routes at `/api/<app_label>.<model_name>`, such as `/api/blog.article`.

To expose a model you cannot decorate, such as one from `django.contrib` or a third-party app, call `expose_model()`. It takes the model and the same options. This example needs `django.contrib.flatpages` in `INSTALLED_APPS`:

```python
# blog/models.py
from django.contrib.flatpages.models import FlatPage
from headless import expose_model

expose_model(FlatPage, read_only=True)
```

Django Headless builds the routes when the `headless.rest` app is ready, after every app's models module is imported. Call `expose_model()` in a models module, as above, or in the `ready()` method of an app listed before `headless.rest` in `INSTALLED_APPS`. A model exposed later has no routes; the [system check](./checks.md#headlessw009) `headless.W009` reports it. Expose each model once: a second registration with other options replaces the first, and `headless.W008` warns about it.

## Options

| Option          | Type        | Default                     | Description                                                                                       |
| --------------- | ----------- | --------------------------- | ------------------------------------------------------------------------------------------------- |
| `singleton`     | `bool`      | `False`                     | Expose the model as a single resource with `GET`, `PUT` and `PATCH`. See [Singletons](./singletons.md). |
| `search_fields` | `list[str]` | All serialized non-choice `CharField`s | Fields searched by DRF's `SearchFilter`.                                               |
| `fields`        | `list[str]` | All fields                  | Serialize only these fields and model properties.                                                 |
| `exclude`       | `list[str]` | `None`                      | Serialize all fields except these.                                                                |
| `read_only`     | `bool`      | `False`                     | Generate `GET` routes only.                                                                       |
| `lookup_fields` | `list[str]` | `None`                      | Unique fields to add a detail route for, at `by_<field>/<value>`. See [Lookup routes](#lookup-routes). |

## Field control

By default, every model field is serialized. Use `fields` or `exclude` to keep data such as internal notes out of the API. The two options cannot be combined.

```python
# blog/models.py
from django.db import models
from headless import expose


@expose(exclude=["internal_notes"])
class Article(models.Model):
    title = models.CharField(max_length=200)
    internal_notes = models.TextField(blank=True)
```

Excluded fields are never serialized and are ignored on create and update. They cannot be filtered, searched or expanded either.

A [system check](./checks.md#headlessw006) warns when a field that looks like a credential, such as `password_hash` or `api_token`, is serialized without being named in `fields`. Exposing a user model requires a `fields` list to pass the checks ([`headless.W007`](./checks.md#headlessw007)).

`fields` can also name model properties, which are serialized as read-only fields.

## Read-only models

Use `read_only=True` for content that the API serves but never changes:

```python
# blog/models.py
from django.db import models
from headless import expose


@expose(read_only=True)
class Category(models.Model):
    name = models.CharField(max_length=100)
```

A read-only model gets the list and detail routes only. `POST`, `PUT`, `PATCH` and `DELETE` answer `405 Method Not Allowed`.

## Lookup routes

A frontend often knows an object by a readable key, such as the slug in a page URL, rather than by its primary key. Use `lookup_fields` to add a detail route for each listed unique field:

```python
# blog/models.py
from django.db import models
from headless import expose


@expose(lookup_fields=["slug"])
class Article(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    body = models.TextField()
```

The article is then available by its slug as well as by its primary key:

```http
GET /api/blog.article/by_slug/getting-started-with-django
```

```json
{
    "id": 1,
    "title": "Getting started with Django",
    "slug": "getting-started-with-django",
    "body": "..."
}
```

A lookup route answers like the detail route:

- An unknown value, or a value that does not fit the field's type (such as a malformed UUID), answers `404 Not Found`.
- Values may contain dots, as in `by_slug/report.pdf`. URL-encode a value that contains a `/`.
- The `expand` and `fields` query parameters work as on the detail route; see [Serializers](./serializers.md).
- Only `GET` is allowed. Create, update and delete through the detail route by primary key.

Lookup routes are opt-in, so a unique field such as an email address is never exposed as a lookup by accident. A field qualifies when it has `unique=True` or a single-field `UniqueConstraint` without a `condition`. The primary key already has the detail route, and singletons cannot have lookup routes.

:::note Permissions treat lookups as retrieves
On a lookup route, DRF's `view.action` is `"retrieve"`, so permission classes that check the action apply as they do on the detail route. `view.lookup_by` holds the field of the lookup, such as `"slug"`, and is `None` on other routes.
:::

## Search fields

`search_fields` sets the fields DRF's [`SearchFilter`](https://www.django-rest-framework.org/api-guide/filtering/#searchfilter) searches. The filter is not enabled by default; add it to `HEADLESS["DEFAULT_FILTER_BACKENDS"]` next to `LookupFilter`:

```python
# mysite/settings.py
HEADLESS = {
    "DEFAULT_FILTER_BACKENDS": [
        "rest_framework.filters.SearchFilter",
        "headless.rest.filters.LookupFilter",
    ],
}
```

```python
# blog/models.py
from django.db import models
from headless import expose


@expose(search_fields=["title", "category__name"])
class Article(models.Model):
    title = models.CharField(max_length=200)
    category = models.ForeignKey("blog.Category", on_delete=models.PROTECT, related_name="articles")
```

Without `search_fields`, every serialized `CharField` without choices is searched. DRF's lookup prefixes (`^`, `=`, `@`, `$`) and relations (`category__name`) are supported. Search with the `search` query parameter:

```http
GET /api/blog.article?search=django
```

## Database constraints

The serializer validates a create or update before it is saved, but not every database constraint, such as a [`CheckConstraint`](https://docs.djangoproject.com/en/stable/ref/models/constraints/#checkconstraint). When a write violates such a constraint, the route answers `400 Bad Request` and saves nothing:

```json
{
    "non_field_errors": ["The data conflicts with a database constraint."]
}
```

The message does not name the constraint, so the database's details stay internal. To tell the frontend which field is wrong, add a validator to the model field as well.

## Validation

`@expose()` and `expose_model()` raise `ImproperlyConfigured` when the model is defined if:

- it decorates something that is not a Django model;
- `search_fields`, `fields` or `exclude` name a field the model does not have;
- `fields` and `exclude` are combined;
- `lookup_fields` is not a list of unique fields of the model, names the primary key or is set on a singleton.

## Related pages

- [Singletons](./singletons.md)
- [Serializers](./serializers.md)
