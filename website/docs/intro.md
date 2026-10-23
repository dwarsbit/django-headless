---
sidebar_position: 1
---

# 🐍 Introduction

Django Headless turns Django into the backend of a headless CMS. Decorate a model with `@expose()` and a [Django REST Framework](https://www.django-rest-framework.org/) API appears, with list, detail, create, update and delete routes, filtering, pagination and singletons. You write no serializers, viewsets or URL patterns.

```python
# blog/models.py
from django.db import models
from headless import expose


@expose()
class Article(models.Model):
    title = models.CharField(max_length=200)
    body = models.TextField()
    published = models.BooleanField(default=False)
```

This decorator generates these routes:

| Method   | Route                  | Action         |
| -------- | ---------------------- | -------------- |
| `GET`    | `/api/blog.article`    | List           |
| `POST`   | `/api/blog.article`    | Create         |
| `GET`    | `/api/blog.article/1`  | Retrieve       |
| `PUT`    | `/api/blog.article/1`  | Update         |
| `PATCH`  | `/api/blog.article/1`  | Partial update |
| `DELETE` | `/api/blog.article/1`  | Delete         |

:::note Protected by default
Generated routes answer `403 Forbidden` to requests that are not authenticated, so an exposed model is never public by accident. To open the routes up, see [Permissions](./permissions.md).
:::

## When to use it

Use Django Headless when Django holds your content and the frontend lives elsewhere: a Next.js or Astro site, a static site build, a mobile app. The API is predictable for such a frontend:

- **Routes per model**: one decorator per model, no URL patterns to maintain.
- **Singletons**: site settings and other one-off objects as a single route.
- **Filtering**: every lookup a field supports, from the query string.
- **Stable lists**: ordered by primary key, with a pagination envelope that includes ready-to-fetch links.
- **Clear errors**: invalid filters and options answer with the reason.

If your editors also need an admin to manage that content, see [Django Content Studio](https://dwarsbit.github.io/django-content-studio/).

## Next steps

Follow the [installation guide](./installation.md) to expose your first model.
