"""
Tests for the REST part of the boot log and the REST helpers
"""

from unittest.mock import patch

from django.test import SimpleTestCase, override_settings


class BootLogHeadlessAppTests(SimpleTestCase):
    """The headless app logs the registry; the REST classes are logged by headless.rest"""

    def test_headless_boot_log_has_no_rest_part(self):
        from django.apps import apps

        with (
            override_settings(HEADLESS={"BOOT_LOG": True, "VERSION_CHECK": False}),
            patch("headless.apps.log") as mock_log,
        ):
            apps.get_app_config("headless").ready()
        output = "\n".join(str(call.args[0]) for call in mock_log.call_args_list if call.args)

        self.assertIn("exposed models", output)
        self.assertNotIn("Authentication", output)
        self.assertNotIn("Permissions", output)


class BootLogAuthTests(SimpleTestCase):
    """The REST part of the boot log must not crash on any supported auth configuration."""

    def boot(self):
        from django.apps import apps

        with patch("headless.rest.apps.log") as mock_log:
            apps.get_app_config("headless_rest").log_boot()
        return "\n".join(str(call.args[0]) for call in mock_log.call_args_list if call.args)

    def test_rest_framework_auth_as_import_paths(self):
        with override_settings(
            HEADLESS={"BOOT_LOG": True},
            REST_FRAMEWORK={"DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework.authentication.TokenAuthentication"]},
        ):
            output = self.boot()
        self.assertIn("rest_framework.authentication.TokenAuthentication", output)

    def test_rest_framework_secret_key_auth_as_import_path(self):
        with override_settings(
            HEADLESS={"BOOT_LOG": True},
            REST_FRAMEWORK={"DEFAULT_AUTHENTICATION_CLASSES": ["headless.rest.authentication.SecretKeyAuthentication"]},
        ):
            output = self.boot()
        self.assertIn("Using secret key authentication", output)

    def test_headless_auth_without_rest_framework_auth(self):
        with override_settings(
            HEADLESS={
                "BOOT_LOG": True,
                "DEFAULT_AUTHENTICATION_CLASSES": ["headless.rest.authentication.SecretKeyAuthentication"],
            },
            REST_FRAMEWORK={},
        ):
            output = self.boot()
        self.assertIn("Using secret key authentication", output)

    def test_secret_keys_reported(self):
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

    def test_missing_secret_keys_reported(self):
        with override_settings(
            HEADLESS={
                "BOOT_LOG": True,
                "DEFAULT_AUTHENTICATION_CLASSES": ["headless.rest.authentication.SecretKeyAuthentication"],
            },
        ):
            output = self.boot()
        self.assertIn("Neither HEADLESS.AUTH_SECRET_KEY nor HEADLESS.AUTH_READ_ONLY_SECRET_KEY is configured!", output)

    def test_headless_auth_overrides_rest_framework_auth(self):
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

    def test_drf_default_auth_reported(self):
        # Without explicit configuration DRF's own defaults apply
        with override_settings(HEADLESS={"BOOT_LOG": True}, REST_FRAMEWORK={}):
            output = self.boot()
        self.assertIn("rest_framework.authentication.SessionAuthentication", output)
        self.assertIn("rest_framework.authentication.BasicAuthentication", output)

    def test_no_auth_classes(self):
        with override_settings(HEADLESS={"BOOT_LOG": True, "DEFAULT_AUTHENTICATION_CLASSES": []}):
            output = self.boot()
        self.assertIn("No authentication classes", output)

    def test_permissions_reported(self):
        with override_settings(HEADLESS={"BOOT_LOG": True}):
            output = self.boot()
        self.assertIn("Permissions:[/green] rest_framework.permissions.IsAdminUser", output)

        with override_settings(HEADLESS={"BOOT_LOG": True, "DEFAULT_PERMISSION_CLASSES": []}):
            output = self.boot()
        self.assertIn("none (public)", output)


class AuthUtilsTests(SimpleTestCase):
    def test_is_secret_key_auth_used_without_rest_framework_auth(self):
        from headless.rest.utils import is_secret_key_auth_used

        with override_settings(REST_FRAMEWORK={}):
            self.assertFalse(is_secret_key_auth_used())

    def test_is_secret_key_auth_used_with_headless_auth(self):
        from headless.rest.utils import is_secret_key_auth_used

        with override_settings(
            HEADLESS={"DEFAULT_AUTHENTICATION_CLASSES": ["headless.rest.authentication.SecretKeyAuthentication"]}
        ):
            self.assertTrue(is_secret_key_auth_used())

    def test_effective_classes_prefer_headless(self):
        from rest_framework.authentication import BasicAuthentication, TokenAuthentication
        from rest_framework.permissions import AllowAny, IsAdminUser
        from headless.rest.utils import get_authentication_classes, get_permission_classes

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
