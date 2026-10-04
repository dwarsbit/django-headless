"""
Settings for Django Headless are all namespaced in the HEADLESS setting.
For example, your project's `settings.py` file might look like this:

HEADLESS = {
    'FILTER_EXCLUSION_SYMBOL': 'exclude_'
}

This module provides the `headless_settings` object, that is used to access
Django Headless settings, checking for user settings first, then falling
back to the defaults.
"""

from django.conf import settings

from django.core.signals import setting_changed
from django.utils.module_loading import import_string

SETTINGS_NAMESPACE = "HEADLESS"

DEFAULTS = {
    # Whether to show the boot log. None (default) auto-detects server mode;
    # True always shows it, False never does.
    "BOOT_LOG": None,
    "AUTH_SECRET_KEY": None,
    "AUTH_SECRET_KEY_HEADER": "X-Secret-Key",
    "DEFAULT_PERMISSION_CLASSES": None,
    "DEFAULT_SERIALIZER_CLASS": "rest_framework.serializers.ModelSerializer",
    "FILTER_EXCLUSION_SYMBOL": "~",
    "FILTER_TRUE_VALUES": ["true", "1", "on"],
    "FILTER_FALSE_VALUES": ["false", "0", "off"],
    "FILTER_NULL_VALUES": ["null", "none", "empty"],
    "NON_FILTER_FIELDS": [
        "search",
        "limit",
        "page",
        "fields",
        "omit",
        "expand",
        "ordering",
    ],
}


# List of settings that may be in string import notation.
IMPORT_STRINGS = ["DEFAULT_SERIALIZER_CLASS", "DEFAULT_PERMISSION_CLASSES"]


# List of settings that have been removed
REMOVED_SETTINGS = []


def perform_import(val, setting_name):
    """
    If the given setting is a string import notation,
    then perform the necessary import or imports.
    """
    if val is None:
        return None
    elif isinstance(val, str):
        return import_from_string(val, setting_name)
    elif isinstance(val, (list, tuple)):
        return [import_from_string(item, setting_name) for item in val]
    return val


def import_from_string(val, setting_name):
    """
    Attempt to import a class from a string representation.
    """
    try:
        return import_string(val)
    except ImportError as e:
        msg = "Could not import '%s' for Headless setting '%s'. %s: %s." % (
            val,
            setting_name,
            e.__class__.__name__,
            e,
        )
        raise ImportError(msg)


class HeadlessSettings:
    """
    A settings object that allows Django Headless settings to be accessed as
    properties. For example:

        from headless.settings import headless_settings
        print(headless_settings.SINGLETON_ATTR)

    Any setting with string import paths will be automatically resolved
    and return the class, rather than the string literal.
    """

    def __init__(self, user_settings=None, defaults=None, import_strings=None):
        if user_settings:
            self._user_settings = self.__check_user_settings(user_settings)
        self.defaults = defaults or DEFAULTS
        self.import_strings = import_strings or IMPORT_STRINGS
        self._cached_attrs = set()

    @property
    def user_settings(self):
        if not hasattr(self, "_user_settings"):
            self._user_settings = getattr(settings, SETTINGS_NAMESPACE, {})
        return self._user_settings

    def __getattr__(self, attr):
        if attr not in self.defaults:
            raise AttributeError("Invalid Headless setting: '%s'" % attr)

        try:
            # Check if present in user settings
            val = self.user_settings[attr]
        except KeyError:
            # Fall back to defaults
            val = self.defaults[attr]

        # Coerce import strings into classes
        if attr in self.import_strings:
            val = perform_import(val, attr)

        # Cache the result
        self._cached_attrs.add(attr)
        setattr(self, attr, val)
        return val

    def __check_user_settings(self, user_settings):
        SETTINGS_DOC = "https://github.com/dwarsbit/django-headless"
        for setting in REMOVED_SETTINGS:
            if setting in user_settings:
                raise RuntimeError(
                    "The '%s' setting has been removed. Please refer to '%s' for available settings."
                    % (setting, SETTINGS_DOC)
                )
        return user_settings

    def reload(self):
        for attr in self._cached_attrs:
            delattr(self, attr)
        self._cached_attrs.clear()
        if hasattr(self, "_user_settings"):
            delattr(self, "_user_settings")


headless_settings = HeadlessSettings(None, DEFAULTS, IMPORT_STRINGS)


def reload_settings(*args, **kwargs):
    setting = kwargs["setting"]
    if setting == SETTINGS_NAMESPACE:
        headless_settings.reload()


setting_changed.connect(reload_settings)
