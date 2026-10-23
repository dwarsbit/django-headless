---
sidebar_position: 3
---

# 🎯 Exposing models

Expose a model with the `@expose()` decorator to give it generated routes. Use the decorator options to make a model a singleton, limit its fields or make it read-only.

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

## Options

| Option          | Type        | Default                     | Description                                                                                       |
| --------------- | ----------- | --------------------------- | ------------------------------------------------------------------------------------------------- |
| `singleton`     | `bool`      | `False`                     | Expose the model as a single resource with `GET`, `PUT` and `PATCH`. See [Singletons](./singletons.md). |
| `search_fields` | `list[str]` | All non-choice `CharField`s | Fields searched by DRF's `SearchFilter`.                                                          |
| `fields`        | `list[str]` | All fields                  | Serialize only these fields.                                                                      |
| `exclude`       | `list[str]` | `None`                      | Serialize all fields except these.                                                                |
| `read_only`     | `bool`      | `False`                     | Generate `GET` routes only.                                                                       |

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

Excluded fields are never serialized and are ignored on create and update.

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

Without `search_fields`, every `CharField` without choices is searched. DRF's lookup prefixes (`^`, `=`, `@`, `$`) and relations (`category__name`) are supported. Search with the `search` query parameter:

```http
GET /api/blog.article?search=django
```

## Validation

`@expose()` and `expose_model()` raise `ImproperlyConfigured` when the model is defined if:

- it decorates something that is not a Django model;
- `search_fields`, `fields` or `exclude` name a field the model does not have;
- `fields` and `exclude` are combined.

## Related pages

- [Singletons](./singletons.md)
- [Serializers](./serializers.md)
