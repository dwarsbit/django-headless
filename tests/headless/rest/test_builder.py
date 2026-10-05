"""
Tests for the RestBuilder class
"""

from unittest.mock import patch, MagicMock

from django.contrib.auth.models import User
from django.db import models
from django.test import SimpleTestCase, override_settings
from rest_framework.authentication import BasicAuthentication
from rest_framework.filters import SearchFilter
from rest_framework.parsers import JSONParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.test import APIRequestFactory, force_authenticate
from rest_framework.renderers import JSONRenderer
from rest_framework.settings import api_settings
from rest_framework.viewsets import ReadOnlyModelViewSet

from headless.registry import headless_registry
from headless.rest.builder import RestBuilder
from headless.rest.filters import LookupFilter
from headless.rest.pagination import PageNumberPagination
from headless.rest.routers import rest_router, singleton_urls


class BuilderTestModel(models.Model):
    """Test model for building REST API"""

    name = models.CharField(max_length=100)
    description = models.TextField()

    class Meta:
        app_label = "test"


class BuilderSingletonModel(models.Model):
    """Test singleton model"""

    title = models.CharField(max_length=200)

    class Meta:
        app_label = "test"


class RestBuilderTests(SimpleTestCase):
    """Tests for the RestBuilder class"""

    def setUp(self):
        """Set up test environment"""
        # Clear any existing registrations
        headless_registry._registry = {}
        rest_router.registry = []
        singleton_urls.clear()

    def tearDown(self):
        """Clean up after tests"""
        headless_registry._models = {}
        rest_router.registry = []
        singleton_urls.clear()

    def test_initialization(self):
        """Test that RestBuilder initializes correctly"""
        builder = RestBuilder()
        self.assertEqual(builder._models, [])
        self.assertEqual(builder._serializer_classes, {})
        self.assertEqual(builder._viewset_classes, {})

    def test_get_serializer_creates_new_serializer(self):
        """Test that get_serializer creates a new serializer class"""
        builder = RestBuilder()

        # Mock the serializer class creation
        with patch("headless.rest.builder.headless_settings") as mock_settings:
            mock_serializer_class = MagicMock()
            mock_settings.DEFAULT_SERIALIZER_CLASS = mock_serializer_class

            serializer = builder.get_serializer(BuilderTestModel)

            # Should create a new serializer class
            self.assertIn("test.BuilderTestModel", builder._serializer_classes)
            self.assertEqual(serializer, builder._serializer_classes["test.BuilderTestModel"])

    def test_get_serializer_returns_cached_serializer(self):
        """Test that get_serializer returns cached serializer"""
        builder = RestBuilder()

        with patch("headless.rest.builder.headless_settings") as mock_settings:
            mock_serializer_class = MagicMock()
            mock_settings.DEFAULT_SERIALIZER_CLASS = mock_serializer_class

            # First call creates serializer
            serializer1 = builder.get_serializer(BuilderTestModel)

            # Second call should return the same cached instance
            serializer2 = builder.get_serializer(BuilderTestModel)

            self.assertIs(serializer1, serializer2)
            self.assertEqual(len(builder._serializer_classes), 1)

    def test_get_view_set_creates_regular_viewset(self):
        """Test that get_view_set creates a regular ModelViewSet"""
        builder = RestBuilder()

        model_config = {
            "model": BuilderTestModel,
            "singleton": False,
            "search_fields": ["name"],
        }

        with patch("headless.rest.builder.headless_settings") as mock_settings:
            mock_serializer_class = MagicMock()
            mock_settings.DEFAULT_SERIALIZER_CLASS = mock_serializer_class

            viewset = builder.get_view_set(model_config)

            # Should create a ModelViewSet
            self.assertIn("test.BuilderTestModel", builder._viewset_classes)
            self.assertEqual(viewset, builder._viewset_classes["test.BuilderTestModel"])

    def test_get_view_set_creates_singleton_viewset(self):
        """Test that get_view_set creates a SingletonViewSet"""
        builder = RestBuilder()

        model_config = {
            "model": BuilderSingletonModel,
            "singleton": True,
            "search_fields": [],
        }

        with patch("headless.rest.builder.headless_settings") as mock_settings:
            mock_serializer_class = MagicMock()
            mock_settings.DEFAULT_SERIALIZER_CLASS = mock_serializer_class

            viewset = builder.get_view_set(model_config)

            # Should create a SingletonViewSet
            self.assertIn("test.BuilderSingletonModel", builder._viewset_classes)
            self.assertEqual(viewset, builder._viewset_classes["test.BuilderSingletonModel"])

    def test_get_view_set_returns_cached_viewset(self):
        """Test that get_view_set returns cached viewset"""
        builder = RestBuilder()

        model_config = {
            "model": BuilderTestModel,
            "singleton": False,
            "search_fields": ["name"],
        }

        with patch("headless.rest.builder.headless_settings") as mock_settings:
            mock_serializer_class = MagicMock()
            mock_settings.DEFAULT_SERIALIZER_CLASS = mock_serializer_class

            # First call creates viewset
            viewset1 = builder.get_view_set(model_config)

            # Second call should return the same cached instance
            viewset2 = builder.get_view_set(model_config)

            self.assertIs(viewset1, viewset2)
            self.assertEqual(len(builder._viewset_classes), 1)

    def test_build_with_invalid_model_config(self):
        """Test that build handles invalid model configurations gracefully"""
        builder = RestBuilder()

        # Register a model with invalid config (missing required fields)
        invalid_config = {"model": BuilderTestModel}  # Missing 'singleton' and 'search_fields'
        headless_registry._models["test.buildertestmodel"] = invalid_config

        # Create builder after registering invalid model
        builder = RestBuilder()

        # Mock log to capture warning messages
        with patch("headless.rest.builder.base.log") as mock_log:
            builder.build()

            # Should log a warning about invalid config
            # Check that any warning log was called (exact format may vary)
            warning_found = any(
                ":warning:" in str(call) and "Invalid model config" in str(call) for call in mock_log.call_args_list
            )
            self.assertTrue(warning_found, "Warning log for invalid config not found")

    def test_build_registers_regular_model(self):
        """Test that build registers regular models to the router"""
        builder = RestBuilder()

        # Register a regular model
        model_config = {
            "model": BuilderTestModel,
            "singleton": False,
            "search_fields": ["name"],
        }
        headless_registry._models["test.buildertestmodel"] = model_config

        # Create builder after registering model
        builder = RestBuilder()

        with patch("headless.rest.builder.headless_settings") as mock_settings:
            mock_serializer_class = MagicMock()
            mock_settings.DEFAULT_SERIALIZER_CLASS = mock_serializer_class

            builder.build()

            # Should register to the router
            self.assertEqual(len(rest_router.registry), 1)
            self.assertEqual(len(singleton_urls), 0)

    def test_build_registers_singleton_model(self):
        """Test that build registers singleton models to singleton_urls"""
        # Register a singleton model
        model_config = {
            "model": BuilderSingletonModel,
            "singleton": True,
            "search_fields": [],
        }
        headless_registry._models["test.buildersingletonmodel"] = model_config

        # Create builder after registering model
        builder = RestBuilder()

        with patch("headless.rest.builder.headless_settings") as mock_settings:
            mock_serializer_class = MagicMock()
            mock_settings.DEFAULT_SERIALIZER_CLASS = mock_serializer_class

            builder.build()

            # Should register to singleton_urls
            self.assertEqual(len(rest_router.registry), 0)
            self.assertEqual(len(singleton_urls), 1)

    def test_build_with_mixed_models(self):
        """Test that build handles both regular and singleton models"""
        # Register both types of models
        regular_config = {
            "model": BuilderTestModel,
            "singleton": False,
            "search_fields": ["name"],
        }
        singleton_config = {
            "model": BuilderSingletonModel,
            "singleton": True,
            "search_fields": [],
        }

        headless_registry._models["test.buildertestmodel"] = regular_config
        headless_registry._models["test.buildersingletonmodel"] = singleton_config

        # Create builder after registering models
        builder = RestBuilder()

        with patch("headless.rest.builder.headless_settings") as mock_settings:
            mock_serializer_class = MagicMock()
            mock_settings.DEFAULT_SERIALIZER_CLASS = mock_serializer_class

            builder.build()

            # Should register both types correctly
            self.assertEqual(len(rest_router.registry), 1)
            self.assertEqual(len(singleton_urls), 1)

    def test_build_logs_correct_route_count(self):
        """Test that build logs the correct number of registered routes"""
        # Register models
        regular_config = {
            "model": BuilderTestModel,
            "singleton": False,
            "search_fields": ["name"],
        }
        singleton_config = {
            "model": BuilderSingletonModel,
            "singleton": True,
            "search_fields": [],
        }

        headless_registry._models["test.buildertestmodel"] = regular_config
        headless_registry._models["test.buildersingletonmodel"] = singleton_config

        # Create builder after registering models
        builder = RestBuilder()

        with patch("headless.rest.builder.headless_settings") as mock_settings:
            mock_serializer_class = MagicMock()
            mock_settings.DEFAULT_SERIALIZER_CLASS = mock_serializer_class

            with patch("headless.rest.builder.base.log") as mock_log:
                builder.build()

                # Should log the correct route count
                # Note: The router creates multiple routes per model (list, create, retrieve, etc.)
                # and singleton_urls has 1 route, so total should be more than 2
                self.assertGreater(len(rest_router.registry), 0)
                self.assertEqual(len(singleton_urls), 1)

                # Check that the log was called with the correct format (exact count may vary)
                log_calls = [str(call) for call in mock_log.call_args_list]
                route_log_found = any("routes registered" in str(call) for call in mock_log.call_args_list)
                singleton_log_found = any("singleton routes" in str(call) for call in mock_log.call_args_list)

                self.assertTrue(route_log_found, "Route count log not found")
                self.assertTrue(singleton_log_found, "Singleton routes log not found")


class BuilderOptionsModel(models.Model):
    """Test model for builder option tests"""

    title = models.CharField(max_length=100)
    views = models.IntegerField(default=0)

    class Meta:
        app_label = "builder_options"


class BuilderOptionsSingleton(models.Model):
    """Test singleton model for builder option tests"""

    site_name = models.CharField(max_length=100)

    class Meta:
        app_label = "builder_options"


class RestBuilderOptionsTests(SimpleTestCase):
    """Tests for the fields, exclude, read_only and permission options"""

    def setUp(self):
        headless_registry._models = {}
        rest_router.registry = []
        singleton_urls.clear()

    def tearDown(self):
        headless_registry._models = {}
        rest_router.registry = []
        singleton_urls.clear()

    def test_read_only_viewset(self):
        """Test that read_only models get a viewset without write actions"""
        config = {
            "model": BuilderOptionsModel,
            "singleton": False,
            "search_fields": ["title"],
            "read_only": True,
        }

        viewset = RestBuilder().get_view_set(config)

        self.assertTrue(issubclass(viewset, ReadOnlyModelViewSet))
        self.assertFalse(hasattr(viewset, "create"))
        self.assertFalse(hasattr(viewset, "update"))
        self.assertFalse(hasattr(viewset, "destroy"))

    def test_regular_viewset_allows_writes(self):
        """Test that regular models keep their write actions"""
        config = {
            "model": BuilderOptionsModel,
            "singleton": False,
            "search_fields": ["title"],
        }

        viewset = RestBuilder().get_view_set(config)

        self.assertTrue(hasattr(viewset, "create"))
        self.assertTrue(hasattr(viewset, "update"))
        self.assertTrue(hasattr(viewset, "destroy"))

    def test_viewset_permissions_from_headless_settings(self):
        """Test that DEFAULT_PERMISSION_CLASSES overrides DRF for generated routes"""
        config = {
            "model": BuilderOptionsModel,
            "singleton": False,
            "search_fields": ["title"],
        }

        with override_settings(HEADLESS={"DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"]}):
            viewset = RestBuilder().get_view_set(config)
            self.assertEqual(viewset.permission_classes, [IsAuthenticated])

    def test_viewset_permissions_default_to_is_authenticated(self):
        """Test that generated routes require authentication by default"""
        config = {
            "model": BuilderOptionsModel,
            "singleton": False,
            "search_fields": ["title"],
        }

        viewset = RestBuilder().get_view_set(config)

        self.assertEqual(viewset.permission_classes, [IsAuthenticated])

    def test_viewset_filter_backends_default_to_lookup_filter(self):
        """Test that generated routes use the LookupFilter by default"""
        config = {
            "model": BuilderOptionsModel,
            "singleton": False,
            "search_fields": ["title"],
        }

        viewset = RestBuilder().get_view_set(config)

        self.assertEqual(viewset.filter_backends, [LookupFilter])

    def test_serializer_fields_restriction(self):
        """Test that the fields option restricts the serializer"""
        config = {
            "model": BuilderOptionsModel,
            "singleton": False,
            "search_fields": ["title"],
            "fields": ["title"],
        }

        viewset = RestBuilder().get_view_set(config)

        self.assertEqual(viewset.serializer_class.Meta.fields, ["title"])

    def test_serializer_exclude(self):
        """Test that the exclude option is passed to the serializer"""
        config = {
            "model": BuilderOptionsModel,
            "singleton": False,
            "search_fields": ["title"],
            "exclude": ["views"],
        }

        viewset = RestBuilder().get_view_set(config)

        self.assertIsNone(getattr(viewset.serializer_class.Meta, "fields", None))
        self.assertEqual(viewset.serializer_class.Meta.exclude, ["views"])

    def test_read_only_singleton_route_is_get_only(self):
        """Test that a read-only singleton only maps the GET method"""
        config = {
            "model": BuilderOptionsSingleton,
            "singleton": True,
            "search_fields": [],
            "read_only": True,
        }
        headless_registry._models["builder_options.builderoptionssingleton"] = config

        RestBuilder(silent=True).build()

        self.assertEqual(len(singleton_urls), 1)

        # The view rejects write methods without touching the database.
        # The request must be authenticated, since generated routes are
        # protected by default.
        view = singleton_urls[0].callback
        request = APIRequestFactory().put("/singleton/")
        force_authenticate(request, user=User())
        response = view(request)
        self.assertEqual(response.status_code, 405)


class CustomSearchFilter(SearchFilter):
    """Custom filter backend to verify subclasses are left untouched"""


class BuilderDrfOverrideTests(SimpleTestCase):
    """Tests for the DRF-level HEADLESS setting overrides"""

    def setUp(self):
        headless_registry._models = {}
        rest_router.registry = []
        singleton_urls.clear()

    def tearDown(self):
        headless_registry._models = {}
        rest_router.registry = []
        singleton_urls.clear()

    def get_view_set(self):
        config = {
            "model": BuilderOptionsModel,
            "singleton": False,
            "search_fields": ["title"],
        }
        return RestBuilder().get_view_set(config)

    def test_renderer_classes_override(self):
        with override_settings(HEADLESS={"DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"]}):
            viewset = self.get_view_set()
            self.assertEqual(viewset.renderer_classes, [JSONRenderer])

    def test_parser_classes_override(self):
        with override_settings(HEADLESS={"DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"]}):
            viewset = self.get_view_set()
            self.assertEqual(viewset.parser_classes, [JSONParser])

    def test_authentication_classes_override(self):
        with override_settings(
            HEADLESS={"DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework.authentication.BasicAuthentication"]}
        ):
            viewset = self.get_view_set()
            self.assertEqual(viewset.authentication_classes, [BasicAuthentication])

    def test_filter_backends_override(self):
        with override_settings(HEADLESS={"DEFAULT_FILTER_BACKENDS": ["headless.rest.filters.LookupFilter"]}):
            viewset = self.get_view_set()
            self.assertEqual(viewset.filter_backends, [LookupFilter])

    def test_pagination_class_override(self):
        with override_settings(HEADLESS={"DEFAULT_PAGINATION_CLASS": "headless.rest.pagination.PageNumberPagination"}):
            viewset = self.get_view_set()
            self.assertTrue(issubclass(viewset.pagination_class, PageNumberPagination))

    def test_page_size_creates_pagination_subclass(self):
        with override_settings(
            HEADLESS={
                "DEFAULT_PAGINATION_CLASS": "headless.rest.pagination.PageNumberPagination",
                "PAGE_SIZE": 5,
            }
        ):
            viewset = self.get_view_set()
            self.assertTrue(issubclass(viewset.pagination_class, PageNumberPagination))
            self.assertEqual(viewset.pagination_class.page_size, 5)

    def test_page_size_without_pagination_class_is_ignored(self):
        # The test settings define no REST_FRAMEWORK pagination class
        with override_settings(HEADLESS={"PAGE_SIZE": 5}):
            viewset = self.get_view_set()
            self.assertIsNone(viewset.pagination_class)

    def test_search_param_substitutes_exact_search_filter(self):
        with override_settings(
            HEADLESS={
                "DEFAULT_FILTER_BACKENDS": [
                    "rest_framework.filters.SearchFilter",
                    "headless.rest.filters.LookupFilter",
                ],
                "SEARCH_PARAM": "q",
            }
        ):
            viewset = self.get_view_set()
            search_backend = viewset.filter_backends[0]
            self.assertEqual(search_backend.search_param, "q")
            # The other backend is untouched
            self.assertIs(viewset.filter_backends[1], LookupFilter)

    def test_ordering_param_substitutes_exact_ordering_filter(self):
        with override_settings(
            HEADLESS={
                "DEFAULT_FILTER_BACKENDS": ["rest_framework.filters.OrderingFilter"],
                "ORDERING_PARAM": "sort",
            }
        ):
            viewset = self.get_view_set()
            self.assertEqual(viewset.filter_backends[0].ordering_param, "sort")

    def test_search_param_leaves_subclasses_untouched(self):
        with override_settings(
            HEADLESS={
                "DEFAULT_FILTER_BACKENDS": [CustomSearchFilter],
                "SEARCH_PARAM": "q",
            }
        ):
            viewset = self.get_view_set()
            self.assertIs(viewset.filter_backends[0], CustomSearchFilter)

    def test_without_overrides_viewset_uses_headless_defaults(self):
        viewset = self.get_view_set()
        self.assertEqual(viewset.renderer_classes, api_settings.DEFAULT_RENDERER_CLASSES)
        self.assertEqual(viewset.authentication_classes, api_settings.DEFAULT_AUTHENTICATION_CLASSES)
        self.assertIsNone(viewset.pagination_class)
        # The permission and filter backends have safe defaults
        self.assertEqual(viewset.permission_classes, [IsAuthenticated])
        self.assertEqual(viewset.filter_backends, [LookupFilter])

    def test_generated_routes_are_protected_by_default(self):
        """Test that unauthenticated requests are rejected on generated routes"""
        viewset = self.get_view_set()
        view = viewset.as_view({"get": "list"})

        request = APIRequestFactory().get("/api/")
        response = view(request)

        self.assertEqual(response.status_code, 403)
