---
sidebar_position: 4
---

# 💈 Singletons

Singleton models represent a single resource — site settings, configuration objects, anything that should have exactly one instance. Expose them with `singleton=True`:

```python
from django.db import models
from headless import expose

@expose(singleton=True)
class SiteConfiguration(models.Model):
    site_name = models.CharField(max_length=100)
    maintenance_mode = models.BooleanField(default=False)
    contact_email = models.EmailField()

    class Meta:
        verbose_name = "Site Configuration"
```

A singleton is exposed as **one resource** without a primary key:

| Method  | Route                          | Action                            |
| ------- | ------------------------------ | --------------------------------- |
| `GET`   | `/api/config.siteconfiguration` | Retrieve the singleton            |
| `PUT`   | `/api/config.siteconfiguration` | Update, **creating it if missing** |
| `PATCH` | `/api/config.siteconfiguration` | Partial update                     |

## Creating on first write

`GET` on a missing singleton returns `404`. A `PUT` or `PATCH` creates the singleton when it does not exist yet (answering `201 Created`), and updates it afterwards (answering `200 OK`).

Creation is race-safe: concurrent first writes cannot create duplicate singletons — the losing request updates the winner's row instead.

## Read-only singletons

`@expose(singleton=True, read_only=True)` generates only the `GET` route, for configuration that is edited in the Django admin but served through the API.

:::tip Managing singletons
Singletons have no list or delete routes. Populate or edit them through the API (`PUT`), the Django admin, or your own code.
:::
