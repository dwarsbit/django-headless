from django.apps import AppConfig

from . import VERSION
from .utils import (
    log,
    is_secret_key_auth_used,
    is_secret_key_auth_configured,
    is_boot_log_enabled,
    configured_auth_classes,
    get_latest_version,
    normalize_version,
)


class DjangoHeadlessConfig(AppConfig):
    name = "headless"
    label = "headless"

    def ready(self):
        from headless.settings import headless_settings
        from .registry import headless_registry

        if not is_boot_log_enabled():
            return

        log("")
        log("[bold magenta]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold magenta]")
        log("[bold cyan]Django Headless[/bold cyan]")

        # Check for a newer version
        latest_version = get_latest_version()
        if latest_version:
            latest_version = normalize_version(latest_version)
            current_version = normalize_version(VERSION)
            if latest_version != current_version:
                log(f"[yellow]⚠️  New version available[/yellow]")
                log(f"Current: [bold]{current_version}[/bold] → Latest: {latest_version}")
            else:
                log(f"[bold]Version {current_version}[/bold]")
        else:
            log(f"[bold]Version {VERSION}[/bold]")

        log("[bold magenta]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold magenta]")
        log(f":gift:  Found [bold green]{len(headless_registry)}[/bold green] exposed models:")
        for model_config in headless_registry.get_models():
            model = model_config["model"]
            log(f"  [cyan]•[/cyan] {model._meta.verbose_name} ([dim]{model._meta.label_lower}[/dim])")

        # Authentication status logging
        log("")

        auth_classes = configured_auth_classes() or list(headless_settings.DEFAULT_AUTHENTICATION_CLASSES or [])

        if auth_classes:
            log(":lock:  [green]An authentication class is configured.[/green]")

            from headless.rest.authentication import SecretKeyAuthentication

            uses_secret_key_auth = is_secret_key_auth_used() or any(
                issubclass(auth_class, SecretKeyAuthentication) for auth_class in auth_classes
            )

            if uses_secret_key_auth:
                log(
                    f"  [cyan]•[/cyan] Using secret key authentication. ([dim]Header: {headless_settings.AUTH_SECRET_KEY_HEADER}[/dim])"
                )

                if not is_secret_key_auth_configured():
                    log("  [yellow]• HEADLESS.AUTH_SECRET_KEY is not configured![/yellow]")
            else:
                log(
                    "  [cyan]•[/cyan] Using "
                    + ", ".join(
                        auth_class if isinstance(auth_class, str) else f"{auth_class.__module__}.{auth_class.__name__}"
                        for auth_class in auth_classes
                    )
                )

        else:
            log(
                ":lock:  [yellow]No authentication class configured. Generated routes require authenticated requests by default; configure one via REST_FRAMEWORK or HEADLESS.DEFAULT_AUTHENTICATION_CLASSES to grant access.[/yellow]"
            )
