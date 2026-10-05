---
sidebar_position: 2
---

# 🚀 Installation

## Requirements

- Python 3.12+
- Django 5.0+ (including 6.x)
- Django REST Framework 3.16+

## Install

```bash
pip install django-headless
```

## Configure Django

Add `headless` to `INSTALLED_APPS`:

```python
# settings.py
INSTALLED_APPS = [
    # ...
    "django.contrib.staticfiles",
    "rest_framework",
    "headless",  # Add this
]
```

Generated routes require authentication by default and support ORM lookup filtering out of the box. Configure authentication classes (via `REST_FRAMEWORK` or `HEADLESS.DEFAULT_AUTHENTICATION_CLASSES`) so requests can authenticate, and pagination if you want paginated lists:

```python
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PAGINATION_CLASS": "headless.rest.pagination.PageNumberPagination",
    "PAGE_SIZE": 25,
}
```

:::note Safe defaults
Generated routes answer `403` for unauthenticated requests because `HEADLESS.DEFAULT_PERMISSION_CLASSES` defaults to `IsAuthenticated`. For a public headless CMS, set it to `AllowAny` — see [permissions](./permissions.md).
:::

## Wire the URLs

```python
# urls.py
from django.urls import path, include

urlpatterns = [
    # ...
    path("api/", include("headless.rest.urls")),
]
```

Routes are built automatically when your project starts — for `runserver`, WSGI/ASGI servers and management commands alike. On start, a boot log shows the exposed models and the number of generated routes.

## Expose your first model

```python
# apps/blog/models.py
from django.db import models
from headless import expose

@expose()
class BlogPost(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField()
    published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
```

Run `python manage.py runserver` and your API is live at `/api/blog.blogpost` 🎉

## Project settings

All package-specific configuration lives in a single `HEADLESS` dict — see the [settings reference](./settings.md) for every option.
