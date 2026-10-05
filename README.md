# Django Headless

[![PyPI version](https://badge.fury.io/py/django-headless.svg)](https://badge.fury.io/py/django-headless)
[![Python versions](https://img.shields.io/pypi/pyversions/django-headless.svg)](https://pypi.org/project/django-headless/)
[![Django versions](https://img.shields.io/badge/django-5.0%2B-blue.svg)](https://www.djangoproject.com/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

With Django Headless you quickly create a REST API for your models, making it easy to turn Django into a powerful headless CMS.

📖 **Read the full documentation at [djangoheadless.org](https://djangoheadless.org)**

## ✨ Features

- **🎯 Easy configuration**: Add `@expose` decorator to any model and get instant REST endpoints
- **🤝 Plays nice**: Seamlessly integrates with existing Django applications
- **💈 Supports singletons**: Special handling for singleton models (settings, configurations, etc.)
- **🔍 Flexible filtering**: Filtering backend based on Django ORM lookups, enabled by default
- **🛡️ Secure by default**: Generated routes require authentication until you open them up

## 🚀 Quick Start

Install the package:

```bash
pip install django-headless
```

Add `headless` to `INSTALLED_APPS`:

```python
# settings.py
INSTALLED_APPS = [
    # ...
    "rest_framework",
    "headless",
]
```

Expose a model:

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

Include the URLs:

```python
# urls.py
from django.urls import path, include

urlpatterns = [
    # ...
    path("api/", include("headless.rest.urls")),
]
```

That's it! 🎉 Your model is now available via REST API at `/api/blog.blogpost`

Note: generated routes answer `403` for unauthenticated requests by default, so freshly exposed models are never accidentally public. See the [permissions documentation](https://djangoheadless.org/docs/permissions) to open routes up.

## 📚 Documentation

All usage and configuration is documented at [djangoheadless.org](https://djangoheadless.org):

- [Installation](https://djangoheadless.org/docs/installation) — requirements, setup and first steps
- [Exposing models](https://djangoheadless.org/docs/models) — all `@expose()` options: singletons, field control, read-only models
- [Singletons](https://djangoheadless.org/docs/singletons) — single-instance resources like site settings
- [Filtering](https://djangoheadless.org/docs/filtering) — ORM lookups, exclusions and type casting
- [Pagination](https://djangoheadless.org/docs/pagination) — the read-friendly pagination envelope
- [Authentication](https://djangoheadless.org/docs/authentication) — secret key authentication and DRF classes
- [Permissions](https://djangoheadless.org/docs/permissions) — safe defaults and route-scoped overrides
- [Serializers](https://djangoheadless.org/docs/serializers) — serializer customization, field expansion and model properties
- [Settings reference](https://djangoheadless.org/docs/settings) — every `HEADLESS` option

## 🤝 Contributing

We welcome contributions! Here's how to get started:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests for your changes
5. Run the test suite (`poetry run test`)
6. Commit your changes (`git commit -m 'Add amazing feature'`)
7. Push to the branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

### Development Setup

```bash
# Clone the repository
git clone https://github.com/dwarsbit/django-headless.git
cd django-headless

# Install dependencies (Poetry creates the virtual environment)
poetry install

# Run tests
poetry run test
```

## 🐛 Issues & Support

- 🐛 **Bug Reports**: [GitHub Issues](https://github.com/dwarsbit/django-headless/issues)
- 💬 **Discussions**: [GitHub Discussions](https://github.com/dwarsbit/django-headless/discussions)
- 📧 **Email**: leon@dwarsbit.nl

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built on the shoulders of [Django](https://www.djangoproject.com/) and [Django REST Framework](https://www.django-rest-framework.org/)
- Inspired by the headless CMS and Jamstack movement
- Thanks to all contributors and the Django community

## 🔗 Links

- [Documentation](https://djangoheadless.org)
- [PyPI Package](https://pypi.org/project/django-headless/)
- [GitHub Repository](https://github.com/dwarsbit/django-headless)
- [Changelog](CHANGELOG.md)
