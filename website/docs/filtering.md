---
sidebar_position: 5
---

# 🔍 Filtering

Django Headless ships `LookupFilter`, a permissive filter backend that maps query string parameters directly to Django ORM lookups. Enable it globally:

```python
REST_FRAMEWORK = {
    "DEFAULT_FILTER_BACKENDS": [
        "headless.rest.filters.LookupFilter",
    ],
}
```

## Syntax

Any supported lookup for a field can be used as a query parameter, using the ORM's `field__lookup` naming:

```bash
# Basic filtering
GET /api/blog.blogpost?published=true

# Field lookups
GET /api/blog.blogpost?title__icontains=django
GET /api/blog.blogpost?created_at__gte=2023-01-01
GET /api/blog.blogpost?views__range=10,100

# Multiple filters combine with AND
GET /api/blog.blogpost?published=true&created_at__year=2023
```

## Exclusions

Prefix a parameter with `~` (configurable, see [settings](./settings.md)) to exclude matches:

```bash
# Everything except unpublished posts
GET /api/blog.blogpost?~published=false
```

## Multi-value lookups

Multi-value lookups (`in`, `range`) accept comma-separated values:

```bash
GET /api/blog.blogpost?id__in=1,2,3
```

Repeated parameters work as well: `?id__in=1&id__in=2`.

## Type casting

Values are cast to the field's type: booleans as `true`/`1`/`on` and `false`/`0`/`off`, integers, decimals and floats parsed accordingly, and `isnull` accepts a boolean. Boolean and null matching is case-insensitive; text values keep their original casing, so case-sensitive lookups like `exact` behave as expected.

Invalid parameters — unknown fields, unsupported lookups, bad values — answer `400 Bad Request` with the reason in the error detail:

```json
{
    "detail": "Field 'nonexistent' does not exist"
}
```
