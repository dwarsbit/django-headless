"""
Django system checks for the registry and settings of Django Headless,
whatever app serves the exposed models. The checks of the REST routes
live in headless.rest.checks.

They run with runserver, migrate and manage.py check. Silence a single
check with SILENCED_SYSTEM_CHECKS, e.g. ["headless.W005"].
"""

from difflib import get_close_matches

from django.apps import apps
from django.core import checks
from django.core.exceptions import FieldDoesNotExist

from .registry import SEARCH_FIELD_PREFIXES, headless_registry
from .settings import DEFAULTS, SETTINGS_NAMESPACE, headless_settings

# Apps that serve the exposed models
EXPOSURE_APPS = ["headless.rest"]

# Parts of a field name (split on "_") that mark it as a credential
SENSITIVE_NAME_PARTS = {"password", "passwd", "pwd", "secret", "token", "otp", "salt", "apikey"}

# Consecutive parts of a field name that mark it as a credential
SENSITIVE_NAME_PAIRS = {("api", "key"), ("private", "key"), ("access", "key")}


def is_sensitive_field_name(name: str) -> bool:
    """
    Check whether a field name looks like a credential, such as password_hash,
    access_token or api_key. Only whole parts of the name count, so names
    like sort_key or tokenizer do not match.
    """
    parts = name.lower().split("_")
    return any(part in SENSITIVE_NAME_PARTS for part in parts) or any(
        pair in SENSITIVE_NAME_PAIRS for pair in zip(parts, parts[1:])
    )


def _implicitly_serialized_fields(config):
    """
    Return the names of the fields of an exposed model that are serialized
    without being named in its fields option: all forward fields minus the
    excluded ones. Fields named in a fields option are a deliberate choice.
    """
    if config["fields"] is not None:
        return []

    model = config["model"]
    excluded = set(config["exclude"] or [])
    return [field.name for field in (*model._meta.fields, *model._meta.many_to_many) if field.name not in excluded]


@checks.register()
def check_settings(app_configs=None, **kwargs):
    """W005: the HEADLESS setting has a key that is not a Django Headless setting."""
    # A HEADLESS setting that is not a dictionary raises ImproperlyConfigured
    # on first use, at startup, so it never reaches the checks.
    warnings = []
    for key in headless_settings.user_settings:
        if key in DEFAULTS:
            continue
        matches = get_close_matches(str(key), DEFAULTS, n=1)
        hint = f'Did you mean "{matches[0]}"?' if matches else "Remove it, or see the settings reference."
        warnings.append(
            checks.Warning(
                f'{SETTINGS_NAMESPACE}["{key}"] is not a Django Headless setting, so it has no effect.',
                hint=hint,
                id="headless.W005",
            )
        )

    return warnings


@checks.register()
def check_registrations(app_configs=None, **kwargs):
    """
    W008: a model is exposed more than once with different options.
    W010: models are exposed, but no app that serves them is installed.
    """
    warnings = []

    for label in sorted(headless_registry.get_conflicting_labels()):
        warnings.append(
            checks.Warning(
                "This model is exposed more than once with different options, for example with both @expose() "
                "and expose_model(). Only the last registration is in effect.",
                hint="Expose the model once, with all its options.",
                obj=headless_registry.get_model(label)["model"],
                id="headless.W008",
            )
        )

    if headless_registry.get_models() and not any(apps.is_installed(app) for app in EXPOSURE_APPS):
        warnings.append(
            checks.Warning(
                "Models are exposed, but no app that serves them is installed, so the API has no routes.",
                hint='Add "headless.rest" to INSTALLED_APPS, after "headless".',
                id="headless.W010",
            )
        )

    return warnings


@checks.register(checks.Tags.security)
def check_sensitive_fields(app_configs=None, **kwargs):
    """
    W006: an exposed model serializes a field that looks like a credential.
    W007: a user model is exposed without a fields allowlist.
    """
    try:
        from django.contrib.auth.base_user import AbstractBaseUser
    except ImportError:  # pragma: no cover
        AbstractBaseUser = None

    warnings = []

    for config in headless_registry.get_models():
        model = config["model"]

        if AbstractBaseUser is not None and issubclass(model, AbstractBaseUser) and config["fields"] is None:
            warnings.append(
                checks.Warning(
                    "This user model is exposed without a fields option, so the API serializes every field "
                    "that is not excluded, which can include the password hash, email address and permissions.",
                    hint='List the fields the API may serialize, e.g. @expose(fields=["username", "first_name"]).',
                    obj=model,
                    id="headless.W007",
                )
            )

        for name in _implicitly_serialized_fields(config):
            if is_sensitive_field_name(name):
                warnings.append(
                    checks.Warning(
                        f"The API serializes the field {name}, which looks like a credential.",
                        hint=f'Add "{name}" to the exclude option, or list it in the fields option '
                        "if the API should serialize it.",
                        obj=model,
                        id="headless.W006",
                    )
                )

    return warnings


def _resolve_search_field(model, name):
    """
    Follow a search field (e.g. "^category__name") from a model, field by
    field, as DRF's SearchFilter does when it builds its query.

    Returns:
        An (error, hidden) tuple: error tells why the search field cannot be
        searched (or None), hidden whether it searches a field that the API
        does not serialize.
    """
    parts = name.lstrip(SEARCH_FIELD_PREFIXES).split("__")
    field = None
    hidden = False

    for index, part in enumerate(parts):
        if field is not None and not field.is_relation:
            # The rest of the path is a transform or key of the field, such as
            # a key of a JSONField, which only the database can tell
            break

        try:
            field = model._meta.pk if part == "pk" else model._meta.get_field(part)
        except FieldDoesNotExist:
            return f"{model._meta.label} has no field {part}", hidden

        # The primary key of a related model is the value of the relation itself
        exposed_fields = headless_registry.get_exposed_fields(model)
        is_related_pk = index > 0 and field.primary_key
        if not is_related_pk and (exposed_fields is None or field.name not in exposed_fields):
            hidden = True

        if field.is_relation and field.related_model is not None:
            model = field.related_model

    if field.is_relation:
        return f"{field.name} is a relation: name a field of the related model, such as {name}__name", hidden

    return None, hidden


@checks.register()
def check_search_fields(app_configs=None, **kwargs):
    """
    E004: a search field cannot be searched, so ?search= would fail.
    W011: a search field searches a field that the API does not serialize.
    """
    messages = []

    for config in headless_registry.get_models():
        model = config["model"]

        for name in config["search_fields"]:
            error, hidden = _resolve_search_field(model, name)

            if error is not None:
                messages.append(
                    checks.Error(
                        f'The search field "{name}" cannot be searched: {error}.',
                        hint="Name a field of the model, or of a related model as in category__name.",
                        obj=model,
                        id="headless.E004",
                    )
                )
            elif hidden:
                messages.append(
                    checks.Warning(
                        f'The search field "{name}" searches a field that the API does not serialize, so '
                        "anyone who may search can find out its values, one guess at a time.",
                        hint="Remove it from the search_fields option, or silence this check if the field "
                        "should be searchable without being served.",
                        obj=model,
                        id="headless.W011",
                    )
                )

    return messages
