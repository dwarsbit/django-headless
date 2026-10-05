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

Optionally configure DRF with the filter backend and pagination that ship with Django Headless:

```python
REST_FRAMEWORK = {
    "DEFAULT_FILTER_BACKENDS": [
        "headless.rest.filters.LookupFilter",
    ],
    "DEFAULT_PAGINATION_CLASS": "headless.rest.pagination.PageNumberPagination",
    "PAGE_SIZE": 25,
}
```

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
