---
sidebar_position: 4
---

# 💈 Singletons

A singleton is an exposed model with exactly one instance, such as site settings. Its route has no primary key: the frontend reads it from one fixed URL. Expose a model as a singleton with `singleton=True`:

```python
# blog/models.py
from django.db import models
from headless import expose


@expose(singleton=True)
class SiteSettings(models.Model):
    site_name = models.CharField(max_length=100)
    contact_email = models.EmailField()
    maintenance_mode = models.BooleanField(default=False)

    class Meta:
        verbose_name = "site settings"
```

The singleton gets one route with three methods:

| Method  | Route                     | Action                               |
| ------- | ------------------------- | ------------------------------------ |
| `GET`   | `/api/blog.sitesettings`  | Retrieve the singleton               |
| `PUT`   | `/api/blog.sitesettings`  | Update, creating it if it is missing |
| `PATCH` | `/api/blog.sitesettings`  | Partial update, creating it if it is missing |

A singleton has no list or delete route. Create and edit it through the API, the Django admin or your own code.

## Creating on first write

Until the singleton exists, `GET` answers `404 Not Found`. The first `PUT` or `PATCH` creates it and answers `201 Created`; later writes update it and answer `200 OK`.

Concurrent first writes do not create duplicates: the request that loses the race updates the row the other request created.

## Read-only singletons

Combine `singleton=True` with `read_only=True` to generate the `GET` method only. Use this for settings that editors change in the Django admin and the frontend only reads:

```python
# blog/models.py
from django.db import models
from headless import expose


@expose(singleton=True, read_only=True)
class SiteSettings(models.Model):
    site_name = models.CharField(max_length=100)
```

## Related pages

- [Exposing models](./models.md)
