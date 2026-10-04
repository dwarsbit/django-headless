import json
import sys
from unittest.mock import patch, mock_open
from urllib.error import URLError

from django.core.cache import cache
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


class RegistryTests(SimpleTestCase):
    def test_registry_register_and_get(self):
        # Create a fake model class with minimal _meta interface
        class _Meta:
            label_lower = "app.model"
            fields = []

        class FakeModel:
            _meta = _Meta()

        reg = HeadlessRegistry()
        reg.register(FakeModel, singleton=True)
        self.assertEqual(len(reg), 1)
        cfg = reg.get_model("APP.Model")
        self.assertIsNotNone(cfg)
        self.assertIs(cfg["model"], FakeModel)
        self.assertTrue(cfg["singleton"])
