__title__ = "Django Headless"
__version__ = "1.0.0-rc.2"
__author__ = "Leon van der Grient"
__license__ = "MIT"

from typing import Type

from django.db import models

from .registry import headless_registry

# Version synonym
VERSION = __version__


def expose(singleton=False, search_fields=None):
    """
    Decorator to register a Django model to the headless registry.

    Args:
        singleton: If True, the model will be treated as a singleton (single instance).
        search_fields: List of field names to enable search functionality on.

    Usage:
        @expose()
        class MyModel(models.Model):
            pass
    """

    def decorator(model_class: Type[models.Model]):
        expose_model(model_class, singleton=singleton, search_fields=search_fields)

        return model_class

    return decorator


def expose_model(model_class: Type[models.Model], singleton=False, search_fields=None):
    """
    Register a Django model to the headless registry.

    Args:
        model_class: The Django model class to expose via the REST API.
        singleton: If True, the model will be treated as a singleton (single instance).
        search_fields: List of field names to enable search functionality on.

    Usage:
        expose_model(MyModel, singleton=False, search_fields=['name', 'description'])
    """

    headless_registry.register(model_class, singleton=singleton, search_fields=search_fields)
