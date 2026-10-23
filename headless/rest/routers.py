import re

from rest_framework.routers import DefaultRouter, SimpleRouter


class EscapedPrefixMixin(SimpleRouter):
    """
    Escape the registered prefixes while the route patterns are built.
    DRF formats the prefix into a regular expression as is, so the dot in
    a prefix like "blog.article" would match any character.
    """

    def get_urls(self):
        registry = self.registry
        self.registry = [(re.escape(prefix), viewset, basename) for prefix, viewset, basename in registry]
        try:
            return super().get_urls()
        finally:
            self.registry = registry


class HeadlessRouter(DefaultRouter, EscapedPrefixMixin):
    """
    The router of the generated routes. The mixin sits between DefaultRouter
    and SimpleRouter, so only the route patterns use the escaped prefixes;
    the API root view lists the prefixes as registered.
    """


rest_router = HeadlessRouter(trailing_slash=False)
singleton_urls = []
