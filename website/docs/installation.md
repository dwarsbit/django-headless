---
sidebar_position: 2
---

# 🚀 Installation

This page sets up Django Headless in an existing Django project and exposes a first model. It takes four steps: install the package, add the apps, include the URLs and expose a model.

## Requirements

- Python 3.12 or later
- Django 5.2 or later, including 6.x
- Django REST Framework 3.18 or later

## Set up the project

1. Install the package:

   ```bash
   pip install django-headless
   ```

2. Add `rest_framework`, `headless` and `headless.rest` to `INSTALLED_APPS`:

   ```python
   # mysite/settings.py
   INSTALLED_APPS = [
       # ...
       "django.contrib.staticfiles",
       "rest_framework",
       "headless",
       "headless.rest",
   ]
   ```

   `headless` keeps track of the exposed models; `headless.rest` serves them as a REST API and builds its routes when the project starts. Without `headless.rest`, the API has no routes, and the [system check](./checks.md#headlessw010) `headless.W010` warns about it.

3. Configure an authentication class, so requests can authenticate, and a pagination class if you want paginated lists. Add this to the same file:

   ```python
   # mysite/settings.py
   REST_FRAMEWORK = {
       "DEFAULT_AUTHENTICATION_CLASSES": [
           "rest_framework.authentication.SessionAuthentication",
       ],
       "DEFAULT_PAGINATION_CLASS": "headless.rest.pagination.PageNumberPagination",
       "PAGE_SIZE": 25,
   }
   ```

4. Include the API in your URL configuration:

   ```python
   # mysite/urls.py
   from django.urls import include, path

   urlpatterns = [
       # ...
       path("api/", include("headless.rest.urls")),
   ]
   ```

:::note Staff users only
Generated routes answer `403 Forbidden` to everyone but staff users, because `HEADLESS["DEFAULT_PERMISSION_CLASSES"]` defaults to `IsAdminUser`. For a public API, set it to `AllowAny`; see [Permissions](./permissions.md).
:::

## Expose a model

Decorate a model with `@expose()`:

```python
# blog/models.py
from django.db import models
from headless import expose


@expose()
class Article(models.Model):
    title = models.CharField(max_length=200)
    body = models.TextField()
    published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
```

Run `python manage.py runserver`. The boot log lists the exposed models and the number of generated routes, and the article list is at `/api/blog.article`.

Routes are built whenever the project starts: under `runserver`, a WSGI or ASGI server, management commands and tests.

## Related pages

- [Exposing models](./models.md)
- [Settings reference](./settings.md)
