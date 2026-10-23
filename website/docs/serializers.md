---
sidebar_position: 8
---

# 🧩 Serializers

Each exposed model is serialized with a `ModelSerializer` that includes all fields, minus those left out with `fields` or `exclude` (see [Exposing models](./models.md#field-control)). To expand relations and serialize model properties, switch to `FlexibleSerializer`:

```python
# mysite/settings.py
HEADLESS = {
    "DEFAULT_SERIALIZER_CLASS": "headless.rest.serializers.FlexibleSerializer",
}
```

`HEADLESS["DEFAULT_SERIALIZER_CLASS"]` sets the base class for the serializers of all exposed models.

## FlexibleSerializer

`FlexibleSerializer` builds on [drf-flex-fields](https://github.com/rsinger86/drf-flex-fields) and adds two things to the default serializer:

- **Model properties** are serialized as read-only fields. Properties whose name starts with `_` are left out.
- **Relations to other exposed models** can be expanded inline with the `expand` query parameter.

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

    @property
    def word_count(self):
        return len(self.body.split())
```

Every article now includes `word_count`.

## Expanding relations

By default, a relation is serialized as the primary key of the related object. Name the relation in `expand` to include the related object instead:

```http
GET /api/blog.article/1?expand=category
GET /api/blog.category/1?expand=articles
```

```json
{
    "id": 1,
    "title": "Getting started with Django",
    "category": {
        "id": 2,
        "name": "Tutorials"
    },
    "word_count": 1250,
    "...": "..."
}
```

Forward relations are expanded by field name (`category`), reverse relations by their `related_name` (`articles`). Only relations to exposed models can be expanded; other relations stay primary keys.

An expanded object follows the `fields` and `exclude` options of its own model. Relations and properties left out with `fields` or `exclude` are not serialized and cannot be expanded.

## Related pages

- [Exposing models](./models.md)
- [Settings reference](./settings.md#default_serializer_class)
