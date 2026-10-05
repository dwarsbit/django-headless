---
sidebar_position: 1
---

# 🐍 Introduction

**Django Headless** turns Django into a headless CMS backend. Decorate a model with `@expose()` and a standard Django REST Framework API appears — with list, detail and CRUD endpoints, filtering, pagination and singleton support. No serializers, viewsets or URL wiring to write.

```python
from django.db import models
from headless import expose

@expose()
class BlogPost(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField()
    published = models.BooleanField(default=False)
```

This single decorator generates:

| Method   | Route                    | Action                     |
| -------- | ------------------------ | -------------------------- |
| `GET`    | `/api/blog.blogpost`     | List (filterable)          |
| `POST`   | `/api/blog.blogpost`     | Create                    |
| `GET`    | `/api/blog.blogpost/1`   | Retrieve                   |
| `PUT`    | `/api/blog.blogpost/1`   | Update                     |
| `PATCH`  | `/api/blog.blogpost/1`   | Partial update             |
| `DELETE` | `/api/blog.blogpost/1`   | Delete                     |

## ✨ Why Django Headless?

The primary use case is running Django as the backend of a JAMstack setup: Django serves content through this generated REST API, while the frontend lives elsewhere (Next.js, Astro, etc.). The API is designed to be predictable and read-friendly for such frontend consumers:

- **🎯 Easy configuration** — a decorator is all it takes
- **🤝 Plays nice** — integrates with existing Django applications
- **💈 Singletons** — settings and configuration objects as a single resource
- **🔍 Flexible filtering** — every supported ORM lookup, straight from the query string
- **🛡️ Secure** — inherits Django's security features and DRF's permission system
- **⚡ Predictable** — stable ordering, pagination envelope, and validation with clear errors

## 🧭 What's next?

Read the [installation guide](./installation.md) to get your first headless model running in minutes.
