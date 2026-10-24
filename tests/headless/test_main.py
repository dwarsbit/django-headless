import http.client
import json
import os
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
    is_newer_version,
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

    def assertServer(self, argv, expected, environ=None):
        # patch.dict restores os.environ afterwards
        with patch.object(sys, "argv", argv), patch.dict(os.environ):
            os.environ.pop("RUN_MAIN", None)
            os.environ.pop("WERKZEUG_RUN_MAIN", None)
            os.environ.update(environ or {})
            self.assertIs(is_runserver(), expected, argv)

    def test_is_runserver_with_runserver(self):
        # The autoreloader runs the server in a child process with RUN_MAIN set
        self.assertServer(["/path/manage.py", "runserver"], True, {"RUN_MAIN": "true"})
        self.assertServer(["/path/manage.py", "runserver", "--noreload"], True)

    def test_is_runserver_with_runserver_reloader_parent(self):
        # The parent process of the autoreloader only watches files
        self.assertServer(["/path/manage.py", "runserver"], False)

    def test_is_runserver_with_runserver_plus(self):
        self.assertServer(["/path/manage.py", "runserver_plus"], True, {"WERKZEUG_RUN_MAIN": "true"})

    def test_is_runserver_with_django_admin_and_python_m_django(self):
        self.assertServer(["/venv/bin/django-admin", "runserver", "--noreload"], True)
        self.assertServer(
            ["/venv/lib/python3.12/site-packages/django/__main__.py", "runserver"], True, {"RUN_MAIN": "true"}
        )
        self.assertServer(["/venv/bin/django-admin", "migrate"], False)

    def test_is_runserver_with_management_commands(self):
        self.assertServer(["/path/manage.py", "migrate"], False)
        self.assertServer(["/path/manage.py", "shell"], False)
        self.assertServer(["/path/manage.py"], False)

    def test_is_runserver_with_servers(self):
        for argv in (
            ["/venv/bin/gunicorn", "mysite.wsgi"],
            ["/venv/bin/uvicorn", "mysite.asgi:application"],
            ["/venv/bin/daphne", "mysite.asgi:application"],
            ["/venv/bin/hypercorn", "mysite.asgi:application"],
            ["uwsgi"],
            ["mod_wsgi"],
            ["/venv/bin/waitress-serve", "mysite.wsgi:application"],
            ["/venv/bin/granian", "mysite.wsgi:application"],
            ["/venv/lib/python3.12/site-packages/gunicorn/__main__.py", "mysite.wsgi"],
            ["C:\\venv\\Scripts\\gunicorn.exe", "mysite.wsgi"],
        ):
            with self.subTest(argv=argv):
                self.assertServer(argv, True)

    def test_is_runserver_with_other_programs(self):
        for argv in (
            ["/venv/bin/pytest"],
            ["/venv/lib/python3.12/site-packages/pytest/__main__.py"],
            ["/venv/bin/celery", "-A", "mysite", "worker"],
            ["/path/wsgi.py"],
            ["/path/import_articles.py"],
            ["-c"],
            [""],
        ):
            with self.subTest(argv=argv):
                self.assertServer(argv, False)

    def test_is_runserver_with_empty_args(self):
        self.assertServer([], False)

    def test_is_runserver_with_relative_manage_py(self):
        self.assertServer(["manage.py", "runserver"], True, {"RUN_MAIN": "true"})

    def test_is_runserver_with_windows_path(self):
        self.assertServer(["C:\\path\\manage.py", "runserver"], True, {"RUN_MAIN": "true"})
        self.assertServer(["C:\\path\\manage.py", "migrate"], False)

    def test_boot_log_setting_true(self):
        with override_settings(HEADLESS={"BOOT_LOG": True}):
            self.assertTrue(is_boot_log_enabled())

    def test_boot_log_setting_false(self):
        with override_settings(HEADLESS={"BOOT_LOG": False}):
            self.assertFalse(is_boot_log_enabled())

    def test_boot_log_defaults_to_server_detection(self):
        with override_settings(HEADLESS={}):
            with patch.object(sys, "argv", ["/path/manage.py", "runserver", "--noreload"]):
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

    def test_get_latest_version_never_raises(self):
        errors = (
            TimeoutError("timed out"),
            http.client.RemoteDisconnected("Remote end closed connection"),
            ConnectionResetError("Connection reset"),
            ValueError("unknown url type"),
        )
        for error in errors:
            with self.subTest(error=error):
                cache.clear()
                with patch("headless.utils.urlopen", side_effect=error):
                    self.assertIsNone(get_latest_version())

    def test_get_latest_version_with_failing_cache(self):
        class MockResponse:
            def read(self):
                return json.dumps({"info": {"version": "1.2.3"}}).encode("utf-8")

            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

        with (
            patch("django.core.cache.cache.get", side_effect=ConnectionError("cache down")),
            patch("django.core.cache.cache.set", side_effect=ConnectionError("cache down")),
            patch("headless.utils.urlopen", return_value=MockResponse()),
        ):
            self.assertEqual(get_latest_version(), "1.2.3")

    def test_is_newer_version(self):
        newer = [
            ("1.0.1", "1.0.0"),
            ("1.0.0", "1.0.0rc9"),
            ("1.0.0", "1.0.0-rc.9"),
            ("1.0.0rc10", "1.0.0-rc.9"),
            ("1.0.0rc1", "1.0.0b6"),
            ("1.0.0b1", "1.0.0a9"),
            ("2.0", "1.9.9"),
        ]
        not_newer = [
            ("1.0.0", "1.0.0"),
            ("1.0.0rc9", "1.0.0-rc.9"),
            ("1.0.0-rc.9", "1.0.0"),
            ("1.0.0", "1.1.0"),
            ("1.0", "1.0.0"),
            ("not-a-version", "1.0.0"),
            ("1.0.0", "unknown"),
        ]
        for latest, current in newer:
            with self.subTest(latest=latest, current=current):
                self.assertTrue(is_newer_version(latest, current))
        for latest, current in not_newer:
            with self.subTest(latest=latest, current=current):
                self.assertFalse(is_newer_version(latest, current))

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
    def test_headless_setting_must_be_a_dictionary(self):
        for value in (None, ["PAGE_SIZE", 25], "PAGE_SIZE=25"):
            with self.subTest(value=value):
                with override_settings(HEADLESS=value):
                    with self.assertRaisesMessage(ImproperlyConfigured, "The HEADLESS setting must be a dictionary"):
                        headless_settings.PAGE_SIZE

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

    def test_string_instead_of_list_rejected(self):
        for option in ("search_fields", "fields", "exclude"):
            with self.subTest(option=option):
                with self.assertRaisesMessage(
                    ImproperlyConfigured,
                    f"Invalid {option} for model registry_tests.RegistryTestModel: expected a list of field names, "
                    """got 'title'. Did you mean ["title"]?""",
                ):
                    self.registry.register(RegistryTestModel, **{option: "title"})

    def test_other_non_list_values_rejected(self):
        for value in ({"title"}, 1, {"title": True}):
            with self.subTest(value=value):
                with self.assertRaisesMessage(ImproperlyConfigured, "expected a list of field names"):
                    self.registry.register(RegistryTestModel, fields=value)

    def test_tuples_accepted(self):
        self.registry.register(RegistryTestModel, fields=("title",), search_fields=("title",))
        cfg = self.registry.get_model("registry_tests.registrytestmodel")
        self.assertEqual(cfg["fields"], ("title",))

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


@patch("headless.apps.VERSION", "1.0.0-rc.9")
class BootLogVersionTests(SimpleTestCase):
    """The boot log only reports a newer version, and the check can be turned off."""

    def boot(self, latest_version, headless=None):
        from django.apps import apps

        with (
            override_settings(HEADLESS={"BOOT_LOG": True, **(headless or {})}),
            patch("headless.apps.get_latest_version", return_value=latest_version) as mock_latest,
            patch("headless.apps.log") as mock_log,
        ):
            apps.get_app_config("headless").ready()
        output = "\n".join(str(call.args[0]) for call in mock_log.call_args_list if call.args)
        return output, mock_latest

    def test_newer_version_reported(self):
        output, _ = self.boot("1.0.0")
        self.assertIn("New version available", output)
        self.assertIn("Current: [bold]1.0.0-rc.9[/bold] → Latest: 1.0.0", output)

    def test_same_or_older_version_not_reported(self):
        for latest_version in ("1.0.0rc9", "1.0.0rc8", None):
            with self.subTest(latest_version=latest_version):
                output, _ = self.boot(latest_version)
                self.assertNotIn("New version available", output)
                self.assertIn("Version 1.0.0-rc.9", output)

    def test_version_check_setting(self):
        output, mock_latest = self.boot("2.0.0", {"VERSION_CHECK": False})
        mock_latest.assert_not_called()
        self.assertNotIn("New version available", output)
        self.assertIn("Version 1.0.0-rc.9", output)


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

    def test_secret_keys_reported(self, _):
        with override_settings(
            HEADLESS={
                "BOOT_LOG": True,
                "AUTH_READ_ONLY_SECRET_KEY": "read-key",
                "DEFAULT_AUTHENTICATION_CLASSES": ["headless.rest.authentication.SecretKeyAuthentication"],
            },
        ):
            output = self.boot()
        self.assertIn("Read-only key configured", output)
        self.assertNotIn("Full access key configured", output)
        self.assertNotIn("is configured!", output)

    def test_missing_secret_keys_reported(self, _):
        with override_settings(
            HEADLESS={
                "BOOT_LOG": True,
                "DEFAULT_AUTHENTICATION_CLASSES": ["headless.rest.authentication.SecretKeyAuthentication"],
            },
        ):
            output = self.boot()
        self.assertIn("Neither HEADLESS.AUTH_SECRET_KEY nor HEADLESS.AUTH_READ_ONLY_SECRET_KEY is configured!", output)

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

    def test_drf_default_auth_reported(self, _):
        # Without explicit configuration DRF's own defaults apply
        with override_settings(HEADLESS={"BOOT_LOG": True}, REST_FRAMEWORK={}):
            output = self.boot()
        self.assertIn("rest_framework.authentication.SessionAuthentication", output)
        self.assertIn("rest_framework.authentication.BasicAuthentication", output)

    def test_no_auth_classes(self, _):
        with override_settings(HEADLESS={"BOOT_LOG": True, "DEFAULT_AUTHENTICATION_CLASSES": []}):
            output = self.boot()
        self.assertIn("No authentication classes", output)

    def test_permissions_reported(self, _):
        with override_settings(HEADLESS={"BOOT_LOG": True}):
            output = self.boot()
        self.assertIn("Permissions:[/green] rest_framework.permissions.IsAdminUser", output)

        with override_settings(HEADLESS={"BOOT_LOG": True, "DEFAULT_PERMISSION_CLASSES": []}):
            output = self.boot()
        self.assertIn("none (public)", output)


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

    def test_is_secret_key_auth_used_with_headless_auth(self):
        from headless.utils import is_secret_key_auth_used

        with override_settings(
            HEADLESS={"DEFAULT_AUTHENTICATION_CLASSES": ["headless.rest.authentication.SecretKeyAuthentication"]}
        ):
            self.assertTrue(is_secret_key_auth_used())

    def test_effective_classes_prefer_headless(self):
        from rest_framework.authentication import BasicAuthentication, TokenAuthentication
        from rest_framework.permissions import AllowAny, IsAdminUser
        from headless.utils import get_authentication_classes, get_permission_classes

        with override_settings(
            HEADLESS={"DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework.authentication.TokenAuthentication"]},
            REST_FRAMEWORK={"DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework.authentication.BasicAuthentication"]},
        ):
            self.assertEqual(get_authentication_classes(), [TokenAuthentication])
            self.assertEqual(get_permission_classes(), [IsAdminUser])

        with override_settings(
            HEADLESS={"DEFAULT_PERMISSION_CLASSES": None},
            REST_FRAMEWORK={
                "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework.authentication.BasicAuthentication"],
                "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
            },
        ):
            self.assertEqual(get_authentication_classes(), [BasicAuthentication])
            self.assertEqual(get_permission_classes(), [AllowAny])
