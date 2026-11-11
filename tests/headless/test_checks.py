"""
Tests for the system checks of the registry and settings
"""

from django.contrib.auth.models import User
from django.core import checks
from django.db import models
from django.test import SimpleTestCase, override_settings

from headless.checks import (
    check_registrations,
    check_search_fields,
    check_sensitive_fields,
    check_settings,
    is_sensitive_field_name,
)
from headless.registry import headless_registry
from headless.rest.builder import RestBuilder
from headless.rest.routers import rest_router, singleton_urls

STRONG_KEY = "k3Jx9vQ2mZr7TbW1yN5cLp8HdFs4GaE6"


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


class ChecksModelOwner(models.Model):
    name = models.CharField(max_length=100)
    password = models.CharField(max_length=100)

    class Meta:
        app_label = "checks_tests"


class ChecksModelCategory(models.Model):
    name = models.CharField(max_length=100)
    internal_code = models.CharField(max_length=100)

    class Meta:
        app_label = "checks_tests"


class ChecksModelPost(models.Model):
    title = models.CharField(max_length=100)
    keywords = models.CharField(max_length=100)
    meta = models.JSONField(default=dict)
    category = models.ForeignKey(ChecksModelCategory, null=True, on_delete=models.CASCADE)
    owner = models.ForeignKey(ChecksModelOwner, null=True, on_delete=models.CASCADE)

    class Meta:
        app_label = "checks_tests"


def ids(messages):
    return [message.id for message in messages]


class RegistryIsolationMixin:
    """Run each check on a registry and routes with only the models a test exposes."""

    def setUp(self):
        super().setUp()
        self._saved_state = (
            dict(headless_registry._models),
            set(headless_registry._conflicting_labels),
            list(rest_router.registry),
            list(singleton_urls),
        )
        headless_registry._models = {}
        headless_registry._conflicting_labels = set()
        rest_router.registry = []
        singleton_urls.clear()

    def tearDown(self):
        models_, conflicting_labels, router_registry, singletons = self._saved_state
        headless_registry._models = models_
        headless_registry._conflicting_labels = conflicting_labels
        rest_router.registry = router_registry
        # headless.rest.urls holds a reference to this list: update it in place
        singleton_urls[:] = singletons
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


class RegistrationsCheckTests(RegistryIsolationMixin, SimpleTestCase):
    def build(self):
        with override_settings(HEADLESS={"BOOT_LOG": False}):
            RestBuilder(silent=True).build()

    def test_conflicting_registrations(self):
        headless_registry.register(ChecksModelArticle)
        headless_registry.register(ChecksModelArticle, read_only=True)
        self.build()

        messages = check_registrations()
        self.assertEqual(ids(messages), ["headless.W008"])
        self.assertIs(messages[0].obj, ChecksModelArticle)
        # The last registration is in effect
        self.assertTrue(headless_registry.get_model("checks_tests.checksmodelarticle")["read_only"])

    def test_identical_registrations(self):
        headless_registry.register(ChecksModelArticle, read_only=True)
        headless_registry.register(ChecksModelArticle, read_only=True)
        self.build()

        self.assertEqual(check_registrations(), [])

    def test_no_exposure_app_installed(self):
        headless_registry.register(ChecksModelArticle)

        with self.modify_settings(INSTALLED_APPS={"remove": "headless.rest"}):
            messages = check_registrations()
        self.assertEqual(ids(messages), ["headless.W010"])
        self.assertEqual(messages[0].hint, 'Add "headless.rest" to INSTALLED_APPS, after "headless".')

        # With headless.rest installed, or without exposed models, the warning does not apply
        self.assertEqual(check_registrations(), [])
        headless_registry._models = {}
        with self.modify_settings(INSTALLED_APPS={"remove": "headless.rest"}):
            self.assertEqual(check_registrations(), [])


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


class SearchFieldsCheckTests(RegistryIsolationMixin, SimpleTestCase):
    def check(self, search_fields, **options):
        headless_registry.register(ChecksModelCategory, exclude=["internal_code"])
        headless_registry.register(ChecksModelPost, search_fields=search_fields, **options)
        return check_search_fields()

    def test_serialized_search_fields(self):
        self.assertEqual(self.check(["title", "^keywords", "=category__name", "category__pk", "owner__id"]), [])

    def test_default_search_fields(self):
        headless_registry.register(ChecksModelPost, exclude=["keywords"])
        headless_registry.register(ChecksModelIntegration, fields=["name"])
        self.assertEqual(check_search_fields(), [])

    def test_transform_of_a_field(self):
        self.assertEqual(self.check(["meta__summary", "title__lower"]), [])

    def test_search_field_ending_on_a_relation(self):
        messages = self.check(["title", "category"])
        self.assertEqual(ids(messages), ["headless.E004"])
        self.assertIs(messages[0].obj, ChecksModelPost)
        self.assertEqual(
            messages[0].msg,
            'The search field "category" cannot be searched: category is a relation: '
            "name a field of the related model, such as category__name.",
        )

    def test_search_field_across_a_relation_that_does_not_exist(self):
        messages = self.check(["^category__nope", "category__name__nope"])
        self.assertEqual(ids(messages), ["headless.E004"])
        self.assertEqual(
            messages[0].msg,
            'The search field "^category__nope" cannot be searched: checks_tests.ChecksModelCategory has no field nope.',
        )

    def test_hidden_search_field(self):
        messages = self.check(["title", "keywords"], exclude=["keywords"])
        self.assertEqual(ids(messages), ["headless.W011"])
        self.assertIn('"keywords"', messages[0].msg)
        self.assertIs(messages[0].obj, ChecksModelPost)

        self.assertEqual(ids(self.check(["title", "@keywords"], fields=["title"])), ["headless.W011"])

    def test_search_field_across_a_hidden_relation(self):
        self.assertEqual(ids(self.check(["category__name"], exclude=["category"])), ["headless.W011"])

    def test_search_field_on_a_hidden_field_of_a_related_model(self):
        self.assertEqual(ids(self.check(["category__internal_code"])), ["headless.W011"])

    def test_search_field_on_a_model_that_is_not_exposed(self):
        messages = self.check(["owner__name", "owner__password"])
        self.assertEqual(ids(messages), ["headless.W011", "headless.W011"])

    def test_singletons_have_no_search_fields(self):
        headless_registry.register(ChecksModelSettings, singleton=True, search_fields=["site_name"])
        self.assertEqual(check_search_fields(), [])


class CheckRegistrationTests(SimpleTestCase):
    def test_checks_are_registered(self):
        registered = checks.registry.registry.get_checks(include_deployment_checks=False)
        for check in (check_settings, check_registrations, check_sensitive_fields, check_search_fields):
            self.assertIn(check, registered)
