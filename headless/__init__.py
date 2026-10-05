__title__ = "Django Headless"
__version__ = "1.0.0-rc.7"
__author__ = "Leon van der Grient"
__license__ = "MIT"

from typing import Type

from django.db import models

from .registry import headless_registry

# Version synonym
VERSION = __version__


def expose(singleton=False, search_fields=None, fields=None, exclude=None, read_only=False):
    """
    Decorator to register a Django model to the headless registry.

    Args:
        singleton: If True, the model will be treated as a singleton (single instance).
        search_fields: List of field names to enable search functionality on.
        fields: Restrict the exposed serializer to these field names.
        exclude: Exclude these field names from the exposed serializer.
        read_only: If True, the model is exposed read-only (no create, update or delete).

    Usage:
        @expose()
        class MyModel(models.Model):
            pass
    """

    def decorator(model_class: Type[models.Model]):
        expose_model(
            model_class,
            singleton=singleton,
            search_fields=search_fields,
            fields=fields,
            exclude=exclude,
            read_only=read_only,
        )

        return model_class

    return decorator


def expose_model(
    model_class: Type[models.Model],
    singleton=False,
    search_fields=None,
    fields=None,
    exclude=None,
    read_only=False,
):
    """
    Register a Django model to the headless registry.

    Args:
        model_class: The Django model class to expose via the REST API.
        singleton: If True, the model will be treated as a singleton (single instance).
        search_fields: List of field names to enable search functionality on.
        fields: Restrict the exposed serializer to these field names.
        exclude: Exclude these field names from the exposed serializer.
        read_only: If True, the model is exposed read-only (no create, update or delete).

    Usage:
        expose_model(MyModel, singleton=False, search_fields=['name', 'description'])
    """

    headless_registry.register(
        model_class,
        singleton=singleton,
        search_fields=search_fields,
        fields=fields,
        exclude=exclude,
        read_only=read_only,
    )
