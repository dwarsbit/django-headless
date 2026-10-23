"""
Tests for the Django Headless system checks
"""

from django.contrib.auth.models import User
from django.core import checks
from django.db import models
from django.test import SimpleTestCase, override_settings

from headless.checks import (
    check_implicit_authentication,
    check_pagination,
    check_public_writes,
    check_secret_key_strength,
    check_secret_keys,
    check_sensitive_fields,
    check_settings,
    is_sensitive_field_name,
)
from headless.registry import headless_registry

SECRET_KEY_AUTH = ["headless.rest.authentication.SecretKeyAuthentication"]
STRONG_KEY = "k3Jx9vQ2mZr7TbW1yN5cLp8HdFs4GaE6"
OTHER_STRONG_KEY = "Qw8eRt5yUi2oPa9sDf3gHj7kLz1xCv4b"


class ChecksModelArticle(models.Model):
    title = models.CharField(max_length=100)

    class Meta:
        app_label = "checks_tests"


class ChecksModelIntegration(models.Model):
    name = models.CharField(max_length=100)
    api_token = models.CharField(max_length=100)
    client_secret = models.CharField(max_length=100)

    class Meta:
        app_label = "checks_tests"


class ChecksModelSettings(models.Model):
    site_name = models.CharField(max_length=100)

    class Meta:
        app_label = "checks_tests"


def ids(messages):
    return [message.id for message in messages]


class RegistryIsolationMixin:
    """Run each check on a registry with only the models a test exposes."""

    def setUp(self):
        super().setUp()
        self._saved_models = dict(headless_registry._models)
        headless_registry._models = {}

    def tearDown(self):
        headless_registry._models = self._saved_models
        super().tearDown()


class SettingsCheckTests(SimpleTestCase):
    def test_unknown_setting_with_suggestion(self):
        with override_settings(HEADLESS={"PAGESIZE": 25, "MAX_PAGE_SIZE": 50}):
            messages = check_settings()
        self.assertEqual(ids(messages), ["headless.W005"])
        self.assertEqual(messages[0].msg, 'HEADLESS["PAGESIZE"] is not a Django Headless setting, so it has no effect.')
        self.assertEqual(messages[0].hint, 'Did you mean "PAGE_SIZE"?')

    def test_unknown_setting_without_suggestion(self):
        with override_settings(HEADLESS={"THEME": "dark"}):
            messages = check_settings()
        self.assertEqual(ids(messages), ["headless.W005"])
        self.assertEqual(messages[0].hint, "Remove it, or see the settings reference.")

    def test_known_settings(self):
        with override_settings(HEADLESS={"PAGE_SIZE": 25, "AUTH_SECRET_KEY": STRONG_KEY, "BOOT_LOG": False}):
            self.assertEqual(check_settings(), [])

        with override_settings(HEADLESS={}):
            self.assertEqual(check_settings(), [])


class SensitiveFieldsCheckTests(RegistryIsolationMixin, SimpleTestCase):
    def test_sensitive_field_names(self):
        sensitive = [
            "password",
            "password_hash",
            "Passwd",
            "pwd",
            "client_secret",
            "access_token",
            "refresh_token",
            "otp_code",
            "salt",
            "api_key",
            "apikey",
            "stripe_api_key",
            "private_key",
            "access_key_id",
        ]
        not_sensitive = ["title", "sort_key", "keywords", "tokenizer", "secretary", "passage", "key", "public_key"]
        for name in sensitive:
            with self.subTest(name=name):
                self.assertTrue(is_sensitive_field_name(name))
        for name in not_sensitive:
            with self.subTest(name=name):
                self.assertFalse(is_sensitive_field_name(name))

    def test_implicitly_serialized_sensitive_fields(self):
        headless_registry.register(ChecksModelIntegration)

        messages = check_sensitive_fields()
        self.assertEqual(ids(messages), ["headless.W006", "headless.W006"])
        self.assertEqual(messages[0].msg, "The API serializes the field api_token, which looks like a credential.")
        self.assertIs(messages[0].obj, ChecksModelIntegration)
        self.assertIn("client_secret", messages[1].msg)

    def test_excluded_sensitive_fields(self):
        # A lookup route by an excluded token serves the object without serializing the token
        headless_registry.register(ChecksModelIntegration, exclude=["client_secret"])
        self.assertEqual(
            [message.msg for message in check_sensitive_fields()],
            ["The API serializes the field api_token, which looks like a credential."],
        )

        headless_registry.register(ChecksModelIntegration, exclude=["api_token", "client_secret"])
        self.assertEqual(check_sensitive_fields(), [])

    def test_sensitive_fields_named_in_fields_are_deliberate(self):
        headless_registry.register(ChecksModelIntegration, fields=["name", "api_token"])
        self.assertEqual(check_sensitive_fields(), [])

    def test_user_model_without_fields(self):
        for options in ({}, {"exclude": ["password"]}):
            with self.subTest(options=options):
                headless_registry._models = {}
                headless_registry.register(User, **options)
                messages = check_sensitive_fields()
                self.assertEqual(ids(messages)[0], "headless.W007")
                self.assertIs(messages[0].obj, User)

        # The password hash is also reported when it is not excluded
        headless_registry._models = {}
        headless_registry.register(User)
        self.assertEqual(ids(check_sensitive_fields()), ["headless.W007", "headless.W006"])

    def test_user_model_with_fields(self):
        headless_registry.register(User, fields=["username", "first_name"])
        self.assertEqual(check_sensitive_fields(), [])


class SecretKeyChecksTests(RegistryIsolationMixin, SimpleTestCase):
    def test_secret_key_authentication_without_key(self):
        with override_settings(HEADLESS={"DEFAULT_AUTHENTICATION_CLASSES": SECRET_KEY_AUTH}):
            self.assertEqual(ids(check_secret_keys()), ["headless.E001"])

        # Also when only the project's own views use it
        with override_settings(REST_FRAMEWORK={"DEFAULT_AUTHENTICATION_CLASSES": SECRET_KEY_AUTH}):
            self.assertEqual(ids(check_secret_keys()), ["headless.E001"])

    def test_secret_key_authentication_with_a_key(self):
        for key_setting in ("AUTH_SECRET_KEY", "AUTH_READ_ONLY_SECRET_KEY"):
            with self.subTest(key_setting=key_setting):
                with override_settings(
                    HEADLESS={"DEFAULT_AUTHENTICATION_CLASSES": SECRET_KEY_AUTH, key_setting: STRONG_KEY}
                ):
                    self.assertEqual(check_secret_keys(), [])

    def test_no_secret_key_authentication(self):
        with override_settings(HEADLESS={}, REST_FRAMEWORK={}):
            self.assertEqual(check_secret_keys(), [])

    def test_identical_keys(self):
        with override_settings(HEADLESS={"AUTH_SECRET_KEY": STRONG_KEY, "AUTH_READ_ONLY_SECRET_KEY": STRONG_KEY}):
            self.assertEqual(ids(check_secret_keys()), ["headless.E002"])

        with override_settings(HEADLESS={"AUTH_SECRET_KEY": STRONG_KEY, "AUTH_READ_ONLY_SECRET_KEY": OTHER_STRONG_KEY}):
            self.assertEqual(check_secret_keys(), [])

    def test_weak_keys(self):
        for key in ("too-short", "a" * 40, "abab" * 10, "your-secret-key", "your-read-only-key"):
            with self.subTest(key=key):
                with override_settings(HEADLESS={"AUTH_SECRET_KEY": key}):
                    self.assertEqual(ids(check_secret_key_strength()), ["headless.W001"])

        with override_settings(HEADLESS={"AUTH_SECRET_KEY": "too-short", "AUTH_READ_ONLY_SECRET_KEY": "short"}):
            self.assertEqual(ids(check_secret_key_strength()), ["headless.W001", "headless.W001"])

    def test_strong_or_missing_keys(self):
        with override_settings(HEADLESS={"AUTH_SECRET_KEY": STRONG_KEY, "AUTH_READ_ONLY_SECRET_KEY": OTHER_STRONG_KEY}):
            self.assertEqual(check_secret_key_strength(), [])

        with override_settings(HEADLESS={}):
            self.assertEqual(check_secret_key_strength(), [])


class PublicWritesCheckTests(RegistryIsolationMixin, SimpleTestCase):
    def test_allow_any_with_writable_models(self):
        headless_registry.register(ChecksModelArticle)
        headless_registry.register(ChecksModelSettings, singleton=True)

        for permission_classes in (["rest_framework.permissions.AllowAny"], []):
            with self.subTest(permission_classes=permission_classes):
                with override_settings(HEADLESS={"DEFAULT_PERMISSION_CLASSES": permission_classes}):
                    messages = check_public_writes()
                self.assertEqual(ids(messages), ["headless.W002"])
                self.assertIn("checks_tests.checksmodelarticle, checks_tests.checksmodelsettings", messages[0].msg)

    def test_allow_any_with_read_only_models(self):
        headless_registry.register(ChecksModelArticle, read_only=True)

        with override_settings(HEADLESS={"DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"]}):
            self.assertEqual(check_public_writes(), [])

    def test_protected_routes(self):
        headless_registry.register(ChecksModelArticle)

        for permission_classes in (
            None,  # The default, IsAdminUser
            ["rest_framework.permissions.IsAuthenticatedOrReadOnly"],
        ):
            with self.subTest(permission_classes=permission_classes):
                headless = {} if permission_classes is None else {"DEFAULT_PERMISSION_CLASSES": permission_classes}
                with override_settings(HEADLESS=headless):
                    self.assertEqual(check_public_writes(), [])


class ImplicitAuthenticationCheckTests(RegistryIsolationMixin, SimpleTestCase):
    def test_drf_default_authentication(self):
        headless_registry.register(ChecksModelArticle)

        with override_settings(HEADLESS={}, REST_FRAMEWORK={}):
            self.assertEqual(ids(check_implicit_authentication()), ["headless.W003"])

    def test_configured_authentication(self):
        headless_registry.register(ChecksModelArticle)
        basic = ["rest_framework.authentication.BasicAuthentication"]

        # Configuring basic authentication yourself is a deliberate choice
        with override_settings(HEADLESS={}, REST_FRAMEWORK={"DEFAULT_AUTHENTICATION_CLASSES": basic}):
            self.assertEqual(check_implicit_authentication(), [])

        with override_settings(HEADLESS={"DEFAULT_AUTHENTICATION_CLASSES": SECRET_KEY_AUTH}, REST_FRAMEWORK={}):
            self.assertEqual(check_implicit_authentication(), [])

    def test_no_exposed_models(self):
        with override_settings(HEADLESS={}, REST_FRAMEWORK={}):
            self.assertEqual(check_implicit_authentication(), [])


class PaginationCheckTests(RegistryIsolationMixin, SimpleTestCase):
    PAGINATION = "headless.rest.pagination.PageNumberPagination"

    def test_no_pagination(self):
        headless_registry.register(ChecksModelArticle)

        with override_settings(HEADLESS={}, REST_FRAMEWORK={}):
            messages = check_pagination()
        self.assertEqual(ids(messages), ["headless.W004"])
        self.assertIn("checks_tests.checksmodelarticle", messages[0].msg)

    def test_pagination_without_page_size(self):
        headless_registry.register(ChecksModelArticle)

        with override_settings(HEADLESS={"DEFAULT_PAGINATION_CLASS": self.PAGINATION}, REST_FRAMEWORK={}):
            self.assertEqual(ids(check_pagination()), ["headless.W004"])

    def test_paginated(self):
        headless_registry.register(ChecksModelArticle)

        with override_settings(HEADLESS={"DEFAULT_PAGINATION_CLASS": self.PAGINATION, "PAGE_SIZE": 25}):
            self.assertEqual(check_pagination(), [])

        with override_settings(
            HEADLESS={}, REST_FRAMEWORK={"DEFAULT_PAGINATION_CLASS": self.PAGINATION, "PAGE_SIZE": 25}
        ):
            self.assertEqual(check_pagination(), [])

    def test_only_singletons(self):
        headless_registry.register(ChecksModelSettings, singleton=True)

        with override_settings(HEADLESS={}, REST_FRAMEWORK={}):
            self.assertEqual(check_pagination(), [])


class CheckRegistrationTests(SimpleTestCase):
    def test_checks_are_registered(self):
        registered = checks.registry.registry.get_checks(include_deployment_checks=True)
        for check in (
            check_settings,
            check_secret_keys,
            check_secret_key_strength,
            check_public_writes,
            check_sensitive_fields,
            check_implicit_authentication,
            check_pagination,
        ):
            self.assertIn(check, registered)

    def test_deploy_only_checks(self):
        registered = checks.registry.registry.get_checks(include_deployment_checks=False)
        self.assertIn(check_settings, registered)
        self.assertIn(check_secret_keys, registered)
        self.assertIn(check_public_writes, registered)
        self.assertIn(check_sensitive_fields, registered)
        self.assertNotIn(check_secret_key_strength, registered)
        self.assertNotIn(check_implicit_authentication, registered)
        self.assertNotIn(check_pagination, registered)
