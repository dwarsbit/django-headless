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
