---
sidebar_position: 6
---

# 📃 Pagination

Django Headless ships a page-based pagination class with a read-friendly envelope. Enable it for the generated routes via `HEADLESS` (or via `REST_FRAMEWORK`, from which the generated routes inherit when the `HEADLESS` versions are unset):

```python
HEADLESS = {
    "DEFAULT_PAGINATION_CLASS": "headless.rest.pagination.PageNumberPagination",
    "PAGE_SIZE": 25,
}
```

Parameters: `page` for the page number, `limit` for the page size. The configured `PAGE_SIZE` is the default; the client's `limit` parameter overrides it per request.

## The envelope

List endpoints return a `pagination` object alongside the `data`:

```json
{
    "pagination": {
        "count": 42,
        "pages": 2,
        "current": 1,
        "limit": 25,
        "links": {
            "self": "https://example.org/api/blog.blogpost?limit=25",
            "next": "https://example.org/api/blog.blogpost?limit=25&page=2",
            "previous": null
        }
    },
    "data": [
        { "id": 1, "title": "Hello world", "...": "..." }
    ]
}
```

The `links.next` and `links.previous` URLs are ready to fetch: a frontend can page through content without constructing URLs itself.

## Stable ordering

Generated list endpoints are ordered by primary key, so pages are deterministic between requests.
