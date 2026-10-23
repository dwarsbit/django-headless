---
sidebar_position: 5
---

# 🔍 Filtering

`LookupFilter` filters list routes with query parameters named after Django's [field lookups](https://docs.djangoproject.com/en/stable/ref/models/querysets/#field-lookups), such as `?title__icontains=django`. The generated routes use it by default, through `HEADLESS["DEFAULT_FILTER_BACKENDS"]`.

```http
GET /api/blog.article?published=true
GET /api/blog.article?title__icontains=django
GET /api/blog.article?created_at__gte=2026-01-01
GET /api/blog.article?category=2
```

A parameter without a lookup matches exactly. Several parameters combine with AND:

```http
GET /api/blog.article?published=true&created_at__year=2026
```

To filter your own Django REST Framework views the same way, add `LookupFilter` to DRF's settings:

```python
# mysite/settings.py
REST_FRAMEWORK = {
    "DEFAULT_FILTER_BACKENDS": [
        "headless.rest.filters.LookupFilter",
    ],
}
```

## Exposed fields

Only fields the API serializes can be filtered. A field left out with `fields` or `exclude` answers `400 Bad Request`, the same as a field that does not exist, so its values cannot be guessed through lookups such as `__startswith`.

Lookups can follow a relation to another exposed model and filter on its serialized fields. A relation to a model that is not exposed can only be filtered by primary key:

```http
GET /api/blog.article?category__name__icontains=tutorials
GET /api/blog.article?category__in=2,3
```

## Exclusions

Start a parameter with `~` to exclude the matches instead:

```http
GET /api/blog.article?~category=3
```

Change the symbol with `HEADLESS["FILTER_EXCLUSION_SYMBOL"]`; see the [settings reference](./settings.md#filter-settings).

## Multiple values

The `in` and `range` lookups take comma-separated values:

```http
GET /api/blog.article?id__in=1,2,3
GET /api/blog.article?created_at__range=2026-01-01,2026-06-30
```

Repeating the parameter works as well: `?id__in=1&id__in=2`.

## Type casting

`LookupFilter` casts each value to the type of its field:

- **Booleans**: `true`, `1` and `on` are true; `false`, `0` and `off` are false.
- **Null values**: on a nullable boolean field, `null`, `none` and `empty` match `None`. The `isnull` lookup takes a boolean.
- **Numbers**: integers, decimals and floats are parsed for their fields.
- **Text**: kept as sent, so case-sensitive lookups such as `exact` match the case.

Boolean and null values are case-insensitive. Change the recognized values with the `FILTER_*` settings.

## Errors

An unknown field, an unsupported lookup or a value that cannot be cast answers `400 Bad Request` with the reason:

```json
{
    "detail": "Field 'titel' does not exist"
}
```

## Related pages

- [Pagination](./pagination.md)
- [Settings reference](./settings.md)
