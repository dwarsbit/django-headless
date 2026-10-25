from django.urls import path

from ..settings import headless_settings
from .routers import rest_router, singleton_urls


def get_urlpatterns():
    """
    Return the routes of the exposed models, plus the schema route when
    HEADLESS["SCHEMA"] is enabled.
    """
    patterns = rest_router.urls + singleton_urls

    if headless_settings.SCHEMA:
        from .schema import get_schema_view

        patterns.append(path("schema", get_schema_view(), name="headless-schema"))

    return patterns


urlpatterns = get_urlpatterns()
