from django.apps import AppConfig

from ..utils import is_boot_log_enabled


class DjangoHeadlessRestConfig(AppConfig):
    name = "headless.rest"
    label = "headless_rest"

    def ready(self):
        # Register the system checks of the REST routes
        from . import checks  # noqa: F401
        from .builder import RestBuilder

        # Build the REST routes. Every app's models have been imported by now,
        # so every model exposed with @expose() is in the registry. Routes are
        # built in every context (servers, management commands, tests); only
        # the builder's log output is tied to the boot log.
        RestBuilder(silent=not is_boot_log_enabled()).build()
