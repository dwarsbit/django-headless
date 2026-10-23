from django.apps import AppConfig


class DjangoHeadlessRestConfig(AppConfig):
    name = "headless.rest"
    label = "headless_rest"

    def ready(self):
        from .builder import RestBuilder

        # The headless app builds the routes. Projects that also install
        # headless.rest build them here as well; building is idempotent,
        # so this only adds routes for models exposed in between.
        RestBuilder(silent=True).build()
