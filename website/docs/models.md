---
sidebar_position: 3
---

# 🎯 Exposing models

Models are exposed with the `@expose()` decorator (or the `expose_model()` function). Each exposed model gets a generated serializer and viewset, registered at the model's `app_label.model_name` label.

```python
from django.db import models
from headless import expose

@expose()
class Article(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField()
    author = models.ForeignKey("user.User", on_delete=models.CASCADE)
```

Generated routes live at `/api/<app_label>.<model_name>` — e.g. `/api/blog.article`.

## Options

| Option          | Type        | Default                    | Description                                                       |
| --------------- | ----------- | -------------------------- | ----------------------------------------------------------------- |
| `singleton`     | `bool`      | `False`                    | Treat the model as a singleton: a single GET/PUT/PATCH resource. See [singletons](./singletons.md). |
| `search_fields` | `List[str]` | All non-choice `CharField` | Fields enabled for DRF's `SearchFilter`.                           |
| `fields`        | `List[str]` | All fields                 | Restrict the exposed serializer to these field names.             |
| `exclude`       | `List[str]` | None                       | Exclude these field names from the exposed serializer.            |
| `read_only`     | `bool`      | `False`                    | Generate GET-only routes (list + retrieve). Writes return 405.    |

## 🔒 Field control

By default the generated serializer exposes all model fields. Use `fields` or `exclude` (they cannot be combined) to keep sensitive data out of the API:

```python
@expose(exclude=["internal_notes"])
class Article(models.Model):
    title = models.CharField(max_length=200)
    internal_notes = models.TextField(blank=True)
```

Excluded fields are never serialized and are ignored on create and update.

## 👁 Read-only models

Content that should be served but never mutated through the API:

```python
@expose(read_only=True)
class Page(models.Model):
    title = models.CharField(max_length=200)
    body = models.TextField()
```

Read-only models only get `GET` routes; `POST`, `PUT`, `PATCH` and `DELETE` answer `405 Method Not Allowed`.

## 🔎 Search fields

`search_fields` is passed to the viewset, so it works with DRF's `SearchFilter` if you add it to your filter backends. Without `search_fields`, all non-choice `CharField` fields are searchable. DRF lookup prefixes (`^`, `=`, `@`, `$`) and relation traversal (`author__name`) are supported.

## ⚠️ Validation

The decorator fails fast with a clear `ImproperlyConfigured` error when:

- it is applied to something that is not a Django model,
- `search_fields`, `fields` or `exclude` name fields that do not exist,
- `fields` and `exclude` are combined.
