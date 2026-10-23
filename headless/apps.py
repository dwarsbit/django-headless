from django.apps import AppConfig

from . import VERSION
from .utils import (
    log,
    class_path,
    is_secret_key_auth_configured,
    is_secret_key_auth_used,
    is_boot_log_enabled,
    get_authentication_classes,
    get_permission_classes,
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
