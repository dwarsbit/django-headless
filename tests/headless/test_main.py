import json
import sys
from unittest.mock import patch, mock_open
from urllib.error import URLError

from django.core.cache import cache
from django.core.exceptions import AppRegistryNotReady, ImproperlyConfigured
from django.db import models
from django.test import SimpleTestCase, override_settings

from headless.registry import HeadlessRegistry
from headless.settings import headless_settings
from headless.utils import (
    is_jsonable,
    flatten,
    is_runserver,
    is_boot_log_enabled,
    get_latest_version,
    normalize_version,
)


class UtilsTests(SimpleTestCase):
    def setUp(self):
        # The version lookup caches its result; start each test clean.
        cache.clear()

    def test_is_jsonable(self):
        self.assertTrue(is_jsonable({"a": 1}))
        self.assertTrue(is_jsonable([1, 2, 3]))
        self.assertFalse(is_jsonable(set([1, 2, 3])))

    def test_flatten(self):
        self.assertEqual(flatten([[1, 2], [3], [], [4, 5]]), [1, 2, 3, 4, 5])

    def test_is_runserver_with_runserver(self):
        with patch.object(sys, "argv", ["/path/manage.py", "runserver"]):
            self.assertTrue(is_runserver())

    def test_is_runserver_with_runserver_plus(self):
        with patch.object(sys, "argv", ["/path/manage.py", "runserver_plus"]):
            self.assertTrue(is_runserver())

    def test_is_runserver_with_migrate(self):
        with patch.object(sys, "argv", ["/path/manage.py", "migrate"]):
            self.assertFalse(is_runserver())

    def test_is_runserver_with_wsgi(self):
        with patch.object(sys, "argv", ["/path/wsgi.py"]):
            self.assertTrue(is_runserver())

    def test_is_runserver_with_empty_args(self):
        with patch.object(sys, "argv", []):
            self.assertFalse(is_runserver())

    def test_is_runserver_with_insufficient_args(self):
        with patch.object(sys, "argv", ["/path/manage.py"]):
            self.assertFalse(is_runserver())

    def test_is_runserver_with_relative_manage_py(self):
        with patch.object(sys, "argv", ["manage.py", "runserver"]):
            self.assertTrue(is_runserver())

    def test_is_runserver_with_windows_path(self):
        with patch.object(sys, "argv", ["C:\\path\\manage.py", "runserver"]):
            self.assertTrue(is_runserver())

    def test_boot_log_setting_true(self):
        with override_settings(HEADLESS={"BOOT_LOG": True}):
            self.assertTrue(is_boot_log_enabled())

    def test_boot_log_setting_false(self):
        with override_settings(HEADLESS={"BOOT_LOG": False}):
            self.assertFalse(is_boot_log_enabled())

    def test_boot_log_defaults_to_server_detection(self):
        with override_settings(HEADLESS={}):
            with patch.object(sys, "argv", ["/path/manage.py", "runserver"]):
                self.assertTrue(is_boot_log_enabled())
            with patch.object(sys, "argv", ["/path/manage.py", "migrate"]):
                self.assertFalse(is_boot_log_enabled())

    def test_get_latest_version_success(self):
        # Mock successful response from PyPI
        class MockResponse:
            def read(self):
                return json.dumps({"info": {"version": "1.2.3"}}).encode("utf-8")

            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

        with patch("headless.utils.urlopen", return_value=MockResponse()) as mock_urlopen:
            version = get_latest_version()
            self.assertEqual(version, "1.2.3")

            # A second lookup is served from cache: PyPI is only hit once.
            version = get_latest_version()
            self.assertEqual(version, "1.2.3")
            self.assertEqual(mock_urlopen.call_count, 1)

    def test_get_latest_version_network_error(self):
        # Mock network error
        with patch("headless.utils.urlopen", side_effect=URLError("Network error")) as mock_urlopen:
            version = get_latest_version()
            self.assertIsNone(version)

            # The failure is cached briefly: PyPI is not hit again.
            version = get_latest_version()
            self.assertIsNone(version)
            self.assertEqual(mock_urlopen.call_count, 1)

    def test_get_latest_version_invalid_json(self):
        # Mock invalid JSON response
        class MockResponse:
            def read(self):
                return b"invalid json"

            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

        with patch("headless.utils.urlopen", return_value=MockResponse()):
            version = get_latest_version()
            self.assertIsNone(version)

    def test_get_latest_version_missing_fields(self):
        # Mock response with missing fields
        class MockResponse:
            def read(self):
                return json.dumps({}).encode("utf-8")

            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

        with patch("headless.utils.urlopen", return_value=MockResponse()):
            version = get_latest_version()
            self.assertIsNone(version)

    def test_normalize_version(self):
        # Test version normalization
        self.assertEqual(normalize_version("1.0.0b6"), "1.0.0-beta.6")
        self.assertEqual(normalize_version("1.0.0-beta.6"), "1.0.0-beta.6")
        self.assertEqual(normalize_version("1.0.0a1"), "1.0.0-alpha.1")
        self.assertEqual(normalize_version("1.0.0-alpha.1"), "1.0.0-alpha.1")
        self.assertEqual(normalize_version("1.0.0rc3"), "1.0.0-rc.3")
        self.assertEqual(normalize_version("1.0.0-rc.3"), "1.0.0-rc.3")
        self.assertEqual(normalize_version("1.0.0"), "1.0.0")
        self.assertEqual(normalize_version(""), "")
        self.assertEqual(normalize_version(None), None)

        # Test that equivalent versions normalize to the same string
        self.assertEqual(normalize_version("1.0.0b6"), normalize_version("1.0.0-beta.6"))
        self.assertEqual(normalize_version("1.0.0a1"), normalize_version("1.0.0-alpha.1"))
        self.assertEqual(normalize_version("1.0.0rc3"), normalize_version("1.0.0-rc.3"))


class SettingsTests(SimpleTestCase):
    def test_defaults_available(self):
        # Ensure default settings are accessible and of expected types
        self.assertIsNone(headless_settings.AUTH_SECRET_KEY)
        self.assertIsInstance(headless_settings.AUTH_SECRET_KEY_HEADER, str)
        self.assertIsInstance(headless_settings.FILTER_EXCLUSION_SYMBOL, str)
        self.assertIsInstance(headless_settings.NON_FILTER_FIELDS, list)
        # DEFAULT_SERIALIZER_CLASS resolves to a class
        from rest_framework.serializers import ModelSerializer

        self.assertTrue(issubclass(headless_settings.DEFAULT_SERIALIZER_CLASS, ModelSerializer))


class RegistryRelatedModel(models.Model):
    name = models.CharField(max_length=100)

    class Meta:
        app_label = "registry_tests"


class RegistryTag(models.Model):
    label = models.CharField(max_length=50)

    class Meta:
        app_label = "registry_tests"


class RegistryTestModel(models.Model):
    title = models.CharField(max_length=100)
    author = models.CharField(max_length=100)
    views = models.IntegerField(default=0)
    category = models.ForeignKey(RegistryRelatedModel, null=True, on_delete=models.CASCADE)
    tags = models.ManyToManyField(RegistryTag, blank=True)

    class Meta:
        app_label = "registry_tests"


class RegistryLookupModel(models.Model):
    slug = models.SlugField(unique=True)
    code = models.CharField(max_length=20)
    sku = models.CharField(max_length=20)
    partner = models.CharField(max_length=20)
    title = models.CharField(max_length=100)

    class Meta:
        app_label = "registry_tests"
        constraints = [
            models.UniqueConstraint(fields=["code"], name="registry_lookup_unique_code"),
            models.UniqueConstraint(fields=["sku", "partner"], name="registry_lookup_unique_sku_partner"),
            models.UniqueConstraint(
                fields=["partner"], condition=models.Q(title="x"), name="registry_lookup_unique_partner_if"
            ),
        ]


class RegistryTests(SimpleTestCase):
    def setUp(self):
        self.registry = HeadlessRegistry()

    def test_registry_register_and_get(self):
        self.registry.register(RegistryTestModel, singleton=True)
        self.assertEqual(len(self.registry), 1)
        cfg = self.registry.get_model("registry_tests.RegistryTestModel")
        self.assertIsNotNone(cfg)
        self.assertIs(cfg["model"], RegistryTestModel)
        self.assertTrue(cfg["singleton"])

    def test_default_config(self):
        self.registry.register(RegistryTestModel)
        cfg = self.registry.get_model("registry_tests.registrytestmodel")

        self.assertFalse(cfg["singleton"])
        self.assertFalse(cfg["read_only"])
        # Default search fields are the CharFields without choices
        self.assertEqual(cfg["search_fields"], ["title", "author"])
        self.assertIsNone(cfg["fields"])
        self.assertIsNone(cfg["exclude"])
        # Lookup routes are opt-in
        self.assertEqual(cfg["lookup_fields"], [])

    def test_singleton_has_no_search_fields(self):
        self.registry.register(RegistryTestModel, singleton=True)
        cfg = self.registry.get_model("registry_tests.registrytestmodel")
        self.assertEqual(cfg["search_fields"], [])

    def test_read_only_config(self):
        self.registry.register(RegistryTestModel, read_only=True)
        cfg = self.registry.get_model("registry_tests.registrytestmodel")
        self.assertTrue(cfg["read_only"])

    def test_fields_and_exclude_config(self):
        self.registry.register(RegistryTestModel, fields=["title", "views"])
        cfg = self.registry.get_model("registry_tests.registrytestmodel")
        self.assertEqual(cfg["fields"], ["title", "views"])

        self.registry.register(RegistryRelatedModel, exclude=["name"])
        cfg = self.registry.get_model("registry_tests.registryrelatedmodel")
        self.assertEqual(cfg["exclude"], ["name"])

    def test_non_model_rejected(self):
        with self.assertRaises(ImproperlyConfigured):
            self.registry.register(object)

        class NotAModel:
            pass

        with self.assertRaises(ImproperlyConfigured):
            self.registry.register(NotAModel)

    def test_fields_and_exclude_conflict(self):
        with self.assertRaises(ImproperlyConfigured):
            self.registry.register(RegistryTestModel, fields=["title"], exclude=["views"])

    def test_invalid_search_fields_rejected(self):
        with self.assertRaises(ImproperlyConfigured):
            self.registry.register(RegistryTestModel, search_fields=["bogus"])

    def test_search_field_lookups_allowed(self):
        # DRF SearchFilter prefixes and relation traversal are valid
        self.registry.register(RegistryTestModel, search_fields=["^title", "=author", "category__name"])
        cfg = self.registry.get_model("registry_tests.registrytestmodel")
        self.assertEqual(cfg["search_fields"], ["^title", "=author", "category__name"])

    def test_invalid_fields_rejected(self):
        with self.assertRaises(ImproperlyConfigured):
            self.registry.register(RegistryTestModel, fields=["title", "bogus"])

        with self.assertRaises(ImproperlyConfigured):
            self.registry.register(RegistryTestModel, exclude=["bogus"])

    def test_register_while_models_not_ready(self):
        # @expose runs at model definition time, while apps.populate() is
        # still importing models. Collecting reverse relations then raises
        # AppRegistryNotReady, so registration must only rely on forward fields.
        with patch.object(RegistryTestModel._meta, "get_fields", side_effect=AppRegistryNotReady):
            self.registry.register(RegistryTestModel, search_fields=["^title", "category__name"])
            self.registry.register(RegistryRelatedModel, exclude=["name"])
        cfg = self.registry.get_model("registry_tests.registrytestmodel")
        self.assertEqual(cfg["search_fields"], ["^title", "category__name"])
        self.assertEqual(self.registry.get_model("registry_tests.registryrelatedmodel")["exclude"], ["name"])

    def test_many_to_many_fields_allowed(self):
        self.registry.register(RegistryTestModel, fields=["title", "tags"])
        cfg = self.registry.get_model("registry_tests.registrytestmodel")
        self.assertEqual(cfg["fields"], ["title", "tags"])

    def test_lookup_fields_config(self):
        # unique=True and single-field unconditional unique constraints are valid
        self.registry.register(RegistryLookupModel, lookup_fields=["slug", "code"])
        cfg = self.registry.get_model("registry_tests.registrylookupmodel")
        self.assertEqual(cfg["lookup_fields"], ["slug", "code"])

    def test_invalid_lookup_fields_rejected(self):
        invalid = [
            ["bogus"],  # Unknown field
            ["title"],  # Not unique
            ["sku"],  # Only unique together with another field
            ["partner"],  # Only unique under a condition
            ["id"],  # Primary key already has the detail route
            "slug",  # Not a list
        ]
        for lookup_fields in invalid:
            with self.subTest(lookup_fields=lookup_fields):
                with self.assertRaises(ImproperlyConfigured):
                    self.registry.register(RegistryLookupModel, lookup_fields=lookup_fields)

    def test_lookup_fields_rejected_on_singletons(self):
        with self.assertRaises(ImproperlyConfigured):
            self.registry.register(RegistryLookupModel, singleton=True, lookup_fields=["slug"])

    def test_property_names_allowed_in_fields(self):
        class RegistryPropertyModel(models.Model):
            title = models.CharField(max_length=100)

            class Meta:
                app_label = "registry_tests"

            @property
            def slug(self):
                return self.title.lower()

        self.registry.register(RegistryPropertyModel, fields=["title", "slug"])
        cfg = self.registry.get_model("registry_tests.registrypropertymodel")
        self.assertEqual(cfg["fields"], ["title", "slug"])

        # Properties cannot be excluded: DRF only accepts model fields there
        with self.assertRaises(ImproperlyConfigured):
            self.registry.register(RegistryPropertyModel, exclude=["slug"])

    def test_default_search_fields_honor_fields_and_exclude(self):
        self.registry.register(RegistryTestModel, exclude=["author"])
        cfg = self.registry.get_model("registry_tests.registrytestmodel")
        self.assertEqual(cfg["search_fields"], ["title"])

        self.registry.register(RegistryTestModel, fields=["author", "views"])
        cfg = self.registry.get_model("registry_tests.registrytestmodel")
        self.assertEqual(cfg["search_fields"], ["author"])

    def test_exposed_fields(self):
        self.registry.register(RegistryTestModel, exclude=["author"])
        self.assertEqual(
            self.registry.get_exposed_fields(RegistryTestModel),
            {"id", "title", "views", "category", "tags"},
        )

    def test_exposed_fields_with_fields_option_include_pk(self):
        self.registry.register(RegistryTestModel, fields=["title"])
        self.assertEqual(self.registry.get_exposed_fields(RegistryTestModel), {"id", "title"})

    def test_exposed_fields_reverse_relations_require_registered_model(self):
        # The test app is not installed, so Django does not collect the
        # reverse relation itself: provide it explicitly.
        reverse_relation = RegistryTestModel._meta.get_field("category").remote_field
        fields = (*RegistryRelatedModel._meta.get_fields(), reverse_relation)

        with patch.object(RegistryRelatedModel._meta, "get_fields", return_value=fields):
            self.registry.register(RegistryRelatedModel)
            self.assertEqual(self.registry.get_exposed_fields(RegistryRelatedModel), {"id", "name"})

            self.registry.register(RegistryTestModel)
            self.assertEqual(
                self.registry.get_exposed_fields(RegistryRelatedModel),
                {"id", "name", "registrytestmodel"},
            )

    def test_exposed_fields_of_unregistered_model(self):
        self.assertIsNone(self.registry.get_exposed_fields(RegistryTestModel))


@patch("headless.apps.get_latest_version", return_value=None)
class BootLogAuthTests(SimpleTestCase):
    """The boot log must not crash on any supported auth configuration."""

    def boot(self):
        from django.apps import apps

        with patch("headless.apps.log") as mock_log:
            apps.get_app_config("headless").ready()
        return "\n".join(str(call.args[0]) for call in mock_log.call_args_list if call.args)

    def test_rest_framework_auth_as_import_paths(self, _):
        with override_settings(
            HEADLESS={"BOOT_LOG": True},
            REST_FRAMEWORK={"DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework.authentication.TokenAuthentication"]},
        ):
            output = self.boot()
        self.assertIn("rest_framework.authentication.TokenAuthentication", output)

    def test_rest_framework_secret_key_auth_as_import_path(self, _):
        with override_settings(
            HEADLESS={"BOOT_LOG": True},
            REST_FRAMEWORK={"DEFAULT_AUTHENTICATION_CLASSES": ["headless.rest.authentication.SecretKeyAuthentication"]},
        ):
            output = self.boot()
        self.assertIn("Using secret key authentication", output)

    def test_headless_auth_without_rest_framework_auth(self, _):
        with override_settings(
            HEADLESS={
                "BOOT_LOG": True,
                "DEFAULT_AUTHENTICATION_CLASSES": ["headless.rest.authentication.SecretKeyAuthentication"],
            },
            REST_FRAMEWORK={},
        ):
            output = self.boot()
        self.assertIn("Using secret key authentication", output)

    def test_headless_auth_overrides_rest_framework_auth(self, _):
        with override_settings(
            HEADLESS={
                "BOOT_LOG": True,
                "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework.authentication.TokenAuthentication"],
            },
            REST_FRAMEWORK={"DEFAULT_AUTHENTICATION_CLASSES": ["headless.rest.authentication.SecretKeyAuthentication"]},
        ):
            output = self.boot()
        self.assertNotIn("Using secret key authentication", output)
        self.assertIn("rest_framework.authentication.TokenAuthentication", output)

    def test_no_auth_configured(self, _):
        with override_settings(HEADLESS={"BOOT_LOG": True}, REST_FRAMEWORK={}):
            output = self.boot()
        self.assertIn("No authentication class configured", output)


class AuthUtilsTests(SimpleTestCase):
    def test_configured_auth_classes_returns_paths(self):
        from rest_framework.authentication import TokenAuthentication
        from headless.utils import configured_auth_classes

        with override_settings(REST_FRAMEWORK={"DEFAULT_AUTHENTICATION_CLASSES": [TokenAuthentication]}):
            self.assertEqual(configured_auth_classes(), ["rest_framework.authentication.TokenAuthentication"])

    def test_is_secret_key_auth_used_without_rest_framework_auth(self):
        from headless.utils import is_secret_key_auth_used

        with override_settings(REST_FRAMEWORK={}):
            self.assertFalse(is_secret_key_auth_used())
