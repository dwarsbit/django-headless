from django.apps import AppConfig

from ..utils import is_boot_log_enabled


class DjangoHeadlessRestConfig(AppConfig):
    name = "headless.rest"
    label = "headless_rest"

    def ready(self):
        from .builder import RestBuilder

        # Routes are always built, so they exist outside runserver as well
        # (management commands, tests, WSGI/ASGI entrypoints). Only the
        # builder's log output is tied to the boot log.
        builder = RestBuilder(silent=not is_boot_log_enabled())
        builder.build()
