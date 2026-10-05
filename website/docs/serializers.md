---
sidebar_position: 8
---

# 🧩 Serializers

Generated endpoints use a `ModelSerializer` with `fields = "__all__"` by default (plus any field control from `@expose()`, see [exposing models](./models.md)). The serializer class is configurable globally:

```python
HEADLESS = {
    "DEFAULT_SERIALIZER_CLASS": "headless.rest.serializers.FlexibleSerializer",
}
```

## FlexibleSerializer

The shipped `FlexibleSerializer` builds on [drf-flex-fields](https://github.com/rsinger86/drf-flex-fields) and adds two features:

- **Model properties** are exposed as read-only fields, so computed content is served without extra endpoints.
- **Relations to other exposed models** are automatically expandable.

## 🔗 Expansion

With `FlexibleSerializer` active, relations to registered models can be requested inline with `?expand=`:

```bash
# Return the related author inline
GET /api/blog.article?expand=author

# Return the articles of a category inline
GET /api/blog.category/1?expand=articles
```

Only relations whose related model is also exposed are expandable; other relations serialize as primary keys.

:::note Opt-in
Expansion and property fields are **opt-in** — they require pointing `DEFAULT_SERIALIZER_CLASS` at `FlexibleSerializer`. The default generated API uses a plain `ModelSerializer`.
:::
