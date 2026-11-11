import re

from rest_framework.routers import APIRootView, DefaultRouter, SimpleRouter

from .utils import get_authentication_classes, get_permission_classes


class HeadlessAPIRootView(APIRootView):
    """
    The API root view lists the generated routes, so it uses their
    authentication and permission classes instead of DRF's global defaults.
    """

    def get_authenticators(self):
        return [auth() for auth in get_authentication_classes()]

    def get_permissions(self):
        return [permission() for permission in get_permission_classes()]


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

    APIRootView = HeadlessAPIRootView


rest_router = HeadlessRouter(trailing_slash=False)
singleton_urls = []
