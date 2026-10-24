from django.apps import AppConfig

from ..utils import is_boot_log_enabled, log
from .utils import (
    class_path,
    get_authentication_classes,
    get_permission_classes,
    is_secret_key_auth_configured,
    is_secret_key_auth_used,
)


class DjangoHeadlessRestConfig(AppConfig):
    name = "headless.rest"
    label = "headless_rest"

    def ready(self):
        # Register the system checks of the REST routes
        from . import checks  # noqa: F401
        from .builder import RestBuilder

        boot_log_enabled = is_boot_log_enabled()
        if boot_log_enabled:
            self.log_boot()

        # Build the REST routes. Every app's models have been imported by now,
        # so every model exposed with @expose() is in the registry. Routes are
        # built in every context (servers, management commands, tests); only
        # the builder's log output is tied to the boot log.
        RestBuilder(silent=not boot_log_enabled).build()

    def log_boot(self):
        """
        Log the REST part of the boot log: the authentication and permission
        classes the generated routes use.
        """
        from headless.settings import headless_settings

        log("")

        # The classes the generated routes actually use: HEADLESS first,
        # then REST_FRAMEWORK, including DRF's own defaults.
        auth_classes = get_authentication_classes()

        if auth_classes:
            log(":lock:  [green]Authentication:[/green] " + ", ".join(class_path(cls) for cls in auth_classes))

            if is_secret_key_auth_used():
                log(
                    f"  [cyan]•[/cyan] Using secret key authentication. ([dim]Header: {headless_settings.AUTH_SECRET_KEY_HEADER}[/dim])"
                )

                if not is_secret_key_auth_configured():
                    log(
                        "  [yellow]• Neither HEADLESS.AUTH_SECRET_KEY nor HEADLESS.AUTH_READ_ONLY_SECRET_KEY is configured![/yellow]"
                    )
                else:
                    if headless_settings.AUTH_SECRET_KEY:
                        log("  [cyan]•[/cyan] Full access key configured")
                    if headless_settings.AUTH_READ_ONLY_SECRET_KEY:
                        log("  [cyan]•[/cyan] Read-only key configured")
        else:
            log(
                ":lock:  [yellow]No authentication classes: every request to the generated routes is anonymous.[/yellow]"
            )

        permission_classes = get_permission_classes()
        log(
            ":shield:  [green]Permissions:[/green] "
            + (", ".join(class_path(cls) for cls in permission_classes) or "[yellow]none (public)[/yellow]")
        )
