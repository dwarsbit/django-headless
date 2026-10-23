---
sidebar_position: 6
---

# 📃 Pagination

`PageNumberPagination` splits list routes into pages and wraps them in an envelope with the total count and links to the next and previous page. Enable it for the generated routes in `HEADLESS`:

```python
# mysite/settings.py
HEADLESS = {
    "DEFAULT_PAGINATION_CLASS": "headless.rest.pagination.PageNumberPagination",
    "PAGE_SIZE": 25,
}
```

When these two settings are not in `HEADLESS`, the generated routes use the ones in `REST_FRAMEWORK`.

Request a page with the `page` query parameter. The `limit` query parameter overrides `PAGE_SIZE` for one request:

```http
GET /api/blog.article?page=2&limit=10
```

## The envelope

A list route answers with a `pagination` object and the items in `data`:

```json
{
    "pagination": {
        "count": 42,
        "pages": 2,
        "current": 1,
        "limit": 25,
        "links": {
            "self": "https://example.org/api/blog.article?limit=25",
            "next": "https://example.org/api/blog.article?limit=25&page=2",
            "previous": null
        }
    },
    "data": [
        {
            "id": 1,
            "title": "Getting started with Django",
            "...": "..."
        }
    ]
}
```

`count` is the number of items in the whole list, `pages` the number of pages, `current` the page number and `limit` the number of items per page, after the `limit` query parameter and `MAX_PAGE_SIZE` are applied.

`links.next` and `links.previous` are complete URLs, so the frontend can page through a list without building URLs itself. On the first and last page, the missing link is `null`.

## Page size

A client can request up to `HEADLESS["MAX_PAGE_SIZE"]` items per page with `limit`; larger values are lowered to it. The default maximum is `100`. Without a maximum, one request can return a whole table and keep the database and the server busy.

```python
# mysite/settings.py
HEADLESS = {
    "DEFAULT_PAGINATION_CLASS": "headless.rest.pagination.PageNumberPagination",
    "PAGE_SIZE": 25,
    "MAX_PAGE_SIZE": 50,
}
```

On your own views, `PageNumberPagination` uses a maximum of `100`. Change it with a subclass that sets `max_page_size`.

## Ordering

Generated list routes are ordered by primary key, so a page holds the same items on every request.

## Related pages

- [Filtering](./filtering.md)
- [Settings reference](./settings.md#drf-overrides)
