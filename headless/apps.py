from django.apps import AppConfig

from . import VERSION
from .utils import (
    log,
    is_boot_log_enabled,
    get_latest_version,
    is_newer_version,
    normalize_version,
)


class DjangoHeadlessConfig(AppConfig):
    name = "headless"
    label = "headless"

    def ready(self):
        # Register the system checks of the registry and settings. The headless
        # app manages the registry; apps such as headless.rest serve the models.
        from . import checks  # noqa: F401

        if is_boot_log_enabled():
            self.log_boot()

    def log_boot(self):
        """
        Log the version and the exposed models. Exposure apps such as
        headless.rest log their own part of the boot log after this.
        """
        from headless.settings import headless_settings
        from .registry import headless_registry

        log("")
        log("[bold magenta]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold magenta]")
        log("[bold cyan]Django Headless[/bold cyan]")

        # Check for a newer version, unless the check is turned off
        latest_version = get_latest_version() if headless_settings.VERSION_CHECK else None
        if latest_version and is_newer_version(latest_version, VERSION):
            log(f"[yellow]⚠️  New version available[/yellow]")
            log(f"Current: [bold]{normalize_version(VERSION)}[/bold] → Latest: {normalize_version(latest_version)}")
        else:
            log(f"[bold]Version {normalize_version(VERSION)}[/bold]")

        log("[bold magenta]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold magenta]")
        log(f":gift:  Found [bold green]{len(headless_registry)}[/bold green] exposed models:")
        for model_config in headless_registry.get_models():
            model = model_config["model"]
            log(f"  [cyan]•[/cyan] {model._meta.verbose_name} ([dim]{model._meta.label_lower}[/dim])")
