# Django Headless

[![PyPI version](https://badge.fury.io/py/django-headless.svg)](https://badge.fury.io/py/django-headless)
[![Python versions](https://img.shields.io/pypi/pyversions/django-headless.svg)](https://pypi.org/project/django-headless/)
[![Django versions](https://img.shields.io/badge/django-5.0%2B-blue.svg)](https://www.djangoproject.com/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

Django Headless generates a REST API for your Django models, so Django can serve as the backend of a headless CMS. Decorate a model with `@expose()` and it gets list, detail, create, update and delete routes, with no serializers, viewsets or URL patterns to write.

Read the documentation at [djangoheadless.org](https://djangoheadless.org).

## Features

- **Routes per model**: one decorator generates the routes of a model.
- **Singletons**: site settings and other one-off objects as a single route.
- **Filtering**: every lookup a field supports, from the query string.
- **Lookup routes**: fetch an object by a unique field such as a slug, at `/api/blog.article/by_slug/<value>`.
- **Pagination**: a stable, paginated list envelope with ready-to-fetch links.
- **Protected by default**: generated routes only answer staff users until you open them up.

## Quick start

1. Install the package:

   ```bash
   pip install django-headless
   ```

2. Add `rest_framework` and `headless` to `INSTALLED_APPS`:

   ```python
   # mysite/settings.py
   INSTALLED_APPS = [
       # ...
       "rest_framework",
       "headless",
   ]
   ```

3. Include the API in your URL configuration:

   ```python
   # mysite/urls.py
   from django.urls import include, path

   urlpatterns = [
       # ...
       path("api/", include("headless.rest.urls")),
   ]
   ```

4. Expose a model:

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

Run `python manage.py runserver`; the article list is at `/api/blog.article`.

Generated routes answer `403 Forbidden` to everyone but staff users, so an exposed model is never public by accident. To configure authentication or open the routes up, see [Permissions](https://djangoheadless.org/docs/permissions).

## Documentation

- [Installation](https://djangoheadless.org/docs/installation): requirements and setup
- [Exposing models](https://djangoheadless.org/docs/models): the `@expose()` options
- [Singletons](https://djangoheadless.org/docs/singletons): single-instance resources such as site settings
- [Filtering](https://djangoheadless.org/docs/filtering): lookups, exclusions and type casting
- [Pagination](https://djangoheadless.org/docs/pagination): the list envelope
- [Authentication](https://djangoheadless.org/docs/authentication): secret key and DRF authentication
- [Serializers](https://djangoheadless.org/docs/serializers): expanding relations and model properties
- [Permissions](https://djangoheadless.org/docs/permissions): defaults and overrides for generated routes
- [Settings reference](https://djangoheadless.org/docs/settings): every `HEADLESS` setting

## Contributing

To contribute a change:

1. Fork the repository.
2. Create a branch: `git checkout -b fix-boolean-casting`.
3. Make the change and add tests for it.
4. Run the test suite: `poetry run test`.
5. Commit and push the branch.
6. Open a pull request.

Set up a development environment with Poetry:

```bash
git clone https://github.com/dwarsbit/django-headless.git
cd django-headless
poetry install
poetry run test
```

Writing for the README or the documentation follows [STYLE.md](STYLE.md).

## Support

- Bug reports: [GitHub Issues](https://github.com/dwarsbit/django-headless/issues)
- Questions: [GitHub Discussions](https://github.com/dwarsbit/django-headless/discussions)
- Email: leon@dwarsbit.nl

## License

Django Headless is licensed under the MIT License; see [LICENSE](LICENSE).

## Links

- [Documentation](https://djangoheadless.org)
- [PyPI](https://pypi.org/project/django-headless/)
- [GitHub](https://github.com/dwarsbit/django-headless)
- [Changelog](CHANGELOG.md)
