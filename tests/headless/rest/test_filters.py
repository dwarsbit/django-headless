from unittest.mock import Mock

from django.db import models
from django.test import TestCase, override_settings
from rest_framework import serializers
from rest_framework.exceptions import ParseError
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.generics import GenericAPIView
from rest_framework.pagination import CursorPagination, LimitOffsetPagination
from rest_framework.request import QueryDict

from headless.registry import headless_registry
from headless.rest.builder.viewset import get_view_set
from headless.rest.filters import LookupFilter


class FilterTestModel(models.Model):
    """Test model for LookupFilter testing"""

    name = models.CharField(max_length=100)
    age = models.IntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    rating = models.FloatField()
    is_active = models.BooleanField()
    nullable_bool = models.BooleanField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "test_app"


class LookupFilterTests(TestCase):
    def setUp(self):
        self.filter_backend = LookupFilter()
        self.mock_view = Mock()
        self.mock_view.action = "list"
        self.mock_view.queryset = FilterTestModel.objects.none()

    def test_basic_filtering(self):
        """Test basic field filtering"""
        query_params = QueryDict("name=test")
        request = Mock()
        request.query_params = query_params

        # Should not raise an exception
        try:
            result = self.filter_backend.filter_queryset(request, FilterTestModel.objects.none(), self.mock_view)
        except Exception as e:
            self.fail(f"Basic filtering raised an exception: {e}")

    def test_boolean_filtering(self):
        """Test boolean field filtering with various true/false values"""
        test_cases = [
            ("true", True),
            ("on", True),
            ("1", True),
            ("false", False),
            ("off", False),
            ("0", False),
        ]

        for value, expected in test_cases:
            with self.subTest(value=value):
                query_params = QueryDict(f"is_active={value}")
                request = Mock()
                request.query_params = query_params

                try:
                    result = self.filter_backend.filter_queryset(
                        request, FilterTestModel.objects.none(), self.mock_view
                    )
                except Exception as e:
                    self.fail(f"Boolean filtering with '{value}' raised an exception: {e}")

    def test_nullable_boolean_filtering(self):
        """Test nullable boolean field filtering"""
        test_cases = [
            ("true", True),
            ("false", False),
            ("null", None),
            ("none", None),
            ("empty", None),
        ]

        for value, expected in test_cases:
            with self.subTest(value=value):
                query_params = QueryDict(f"nullable_bool={value}")
                request = Mock()
                request.query_params = query_params

                try:
                    result = self.filter_backend.filter_queryset(
                        request, FilterTestModel.objects.none(), self.mock_view
                    )
                except Exception as e:
                    self.fail(f"Nullable boolean filtering with '{value}' raised an exception: {e}")

    def test_integer_filtering(self):
        """Test integer field filtering"""
        query_params = QueryDict("age=25")
        request = Mock()
        request.query_params = query_params

        try:
            result = self.filter_backend.filter_queryset(request, FilterTestModel.objects.none(), self.mock_view)
        except Exception as e:
            self.fail(f"Integer filtering raised an exception: {e}")

    def test_decimal_filtering(self):
        """Test decimal field filtering"""
        query_params = QueryDict("price=19.99")
        request = Mock()
        request.query_params = query_params

        try:
            result = self.filter_backend.filter_queryset(request, FilterTestModel.objects.none(), self.mock_view)
        except Exception as e:
            self.fail(f"Decimal filtering raised an exception: {e}")

    def test_float_filtering(self):
        """Test float field filtering"""
        query_params = QueryDict("rating=4.5")
        request = Mock()
        request.query_params = query_params

        try:
            result = self.filter_backend.filter_queryset(request, FilterTestModel.objects.none(), self.mock_view)
        except Exception as e:
            self.fail(f"Float filtering raised an exception: {e}")

    def test_lookup_filtering(self):
        """Test field lookup filtering (e.g., __contains, __gte)"""
        lookup_cases = [
            "name__contains=test",
            "age__gte=18",
            "price__lte=100.00",
            "created_at__year=2023",
        ]

        for lookup in lookup_cases:
            with self.subTest(lookup=lookup):
                query_params = QueryDict(lookup)
                request = Mock()
                request.query_params = query_params

                try:
                    result = self.filter_backend.filter_queryset(
                        request, FilterTestModel.objects.none(), self.mock_view
                    )
                except Exception as e:
                    self.fail(f"Lookup filtering with '{lookup}' raised an exception: {e}")

    def test_multi_value_filtering(self):
        """Test multi-value filtering (e.g., __in lookup)"""
        query_params = QueryDict("age__in=25,30,35")
        request = Mock()
        request.query_params = query_params

        try:
            result = self.filter_backend.filter_queryset(request, FilterTestModel.objects.none(), self.mock_view)
        except Exception as e:
            self.fail(f"Multi-value filtering raised an exception: {e}")

    def test_exclusion_filtering(self):
        """Test exclusion filtering using the exclusion symbol"""
        query_params = QueryDict("~is_active=true")
        request = Mock()
        request.query_params = query_params

        try:
            result = self.filter_backend.filter_queryset(request, FilterTestModel.objects.none(), self.mock_view)
        except Exception as e:
            self.fail(f"Exclusion filtering raised an exception: {e}")

    def test_invalid_field_filtering(self):
        """Test that invalid field names raise ParseError"""
        query_params = QueryDict("nonexistent_field=value")
        request = Mock()
        request.query_params = query_params

        with self.assertRaises(ParseError):
            self.filter_backend.filter_queryset(request, FilterTestModel.objects.none(), self.mock_view)

    def test_invalid_boolean_value(self):
        """Test that invalid boolean values raise ParseError"""
        query_params = QueryDict("is_active=invalid")
        request = Mock()
        request.query_params = query_params

        with self.assertRaises(ParseError):
            self.filter_backend.filter_queryset(request, FilterTestModel.objects.none(), self.mock_view)

    def test_invalid_integer_value(self):
        """Test that invalid integer values raise ParseError"""
        query_params = QueryDict("age=not_a_number")
        request = Mock()
        request.query_params = query_params

        with self.assertRaises(ParseError):
            self.filter_backend.filter_queryset(request, FilterTestModel.objects.none(), self.mock_view)

    def test_non_filter_fields(self):
        """Test that non-filter fields are ignored"""
        # Add some non-filter fields
        query_params = QueryDict("search=test&limit=10&name=test")
        request = Mock()
        request.query_params = query_params

        try:
            result = self.filter_backend.filter_queryset(request, FilterTestModel.objects.none(), self.mock_view)
        except Exception as e:
            self.fail(f"Non-filter fields handling raised an exception: {e}")

    def test_get_filter_kwargs(self):
        """Test the get_filter_kwargs method directly"""
        query_params = QueryDict("name=test&age__gte=18")

        try:
            filter_kwargs, exclude_kwargs = self.filter_backend.get_filter_kwargs(
                model_class=FilterTestModel, query_params=query_params
            )

            # Should return filter kwargs and empty exclude kwargs
            self.assertIsInstance(filter_kwargs, dict)
            self.assertIsInstance(exclude_kwargs, dict)
            self.assertEqual(len(exclude_kwargs), 0)

        except Exception as e:
            self.fail(f"get_filter_kwargs raised an exception: {e}")

    def test_get_filter_kwargs_with_exclusion(self):
        """Test get_filter_kwargs with exclusion parameters"""
        query_params = QueryDict("name=test&~age__gte=18")

        try:
            filter_kwargs, exclude_kwargs = self.filter_backend.get_filter_kwargs(
                model_class=FilterTestModel, query_params=query_params
            )

            # Should return both filter and exclude kwargs
            self.assertIsInstance(filter_kwargs, dict)
            self.assertIsInstance(exclude_kwargs, dict)
            self.assertGreater(len(exclude_kwargs), 0)

        except Exception as e:
            self.fail(f"get_filter_kwargs with exclusion raised an exception: {e}")

    def test_non_list_action(self):
        """Test that non-list actions return queryset unchanged"""
        self.mock_view.action = "retrieve"  # Change to non-list action

        query_params = QueryDict("name=test")
        request = Mock()
        request.query_params = query_params

        original_queryset = FilterTestModel.objects.none()
        result = self.filter_backend.filter_queryset(request, original_queryset, self.mock_view)

        # Should return the original queryset unchanged
        self.assertEqual(result, original_queryset)

    def test_cast_field_value_method(self):
        """Test the cast_field_value method directly"""
        # Test boolean casting
        bool_field = FilterTestModel._meta.get_field("is_active")

        self.assertEqual(self.filter_backend.cast_field_value("true", bool_field), True)
        self.assertEqual(self.filter_backend.cast_field_value("false", bool_field), False)

        # Test integer casting
        int_field = FilterTestModel._meta.get_field("age")
        self.assertEqual(self.filter_backend.cast_field_value("25", int_field), 25)

        # Test decimal casting
        decimal_field = FilterTestModel._meta.get_field("price")
        from decimal import Decimal

        self.assertEqual(
            self.filter_backend.cast_field_value("19.99", decimal_field),
            Decimal("19.99"),
        )

        # Test float casting
        float_field = FilterTestModel._meta.get_field("rating")
        self.assertEqual(self.filter_backend.cast_field_value("4.5", float_field), 4.5)

    def test_cast_field_value_invalid(self):
        """Test cast_field_value with invalid values"""
        # Test invalid boolean
        bool_field = FilterTestModel._meta.get_field("is_active")
        with self.assertRaises(ParseError):
            self.filter_backend.cast_field_value("invalid", bool_field)

        # Test invalid integer
        int_field = FilterTestModel._meta.get_field("age")
        with self.assertRaises(ParseError):
            self.filter_backend.cast_field_value("not_a_number", int_field)

        # Test invalid decimal
        decimal_field = FilterTestModel._meta.get_field("price")
        with self.assertRaises(ParseError):
            self.filter_backend.cast_field_value("invalid_decimal", decimal_field)

        # Test invalid float
        float_field = FilterTestModel._meta.get_field("rating")
        with self.assertRaises(ParseError):
            self.filter_backend.cast_field_value("not_a_float", float_field)

    def test_cast_field_value_preserves_case_for_text(self):
        """Test that text values keep their original casing"""
        field = FilterTestModel._meta.get_field("name")

        self.assertEqual(self.filter_backend.cast_field_value("John", field), "John")
        self.assertEqual(self.filter_backend.cast_field_value("hello World", field), "hello World")

    def test_cast_field_value_strips_whitespace(self):
        """Test that values are stripped before casting"""
        name_field = FilterTestModel._meta.get_field("name")
        int_field = FilterTestModel._meta.get_field("age")

        self.assertEqual(self.filter_backend.cast_field_value("  John  ", name_field), "John")
        self.assertEqual(self.filter_backend.cast_field_value(" 25 ", int_field), 25)

    def test_cast_field_value_boolean_is_case_insensitive(self):
        """Test that boolean values match case-insensitively"""
        field = FilterTestModel._meta.get_field("is_active")

        self.assertEqual(self.filter_backend.cast_field_value("TRUE", field), True)
        self.assertEqual(self.filter_backend.cast_field_value("On", field), True)
        self.assertEqual(self.filter_backend.cast_field_value("False", field), False)
        self.assertEqual(self.filter_backend.cast_field_value("OFF", field), False)

    def test_case_sensitive_text_filter_keeps_case(self):
        """Test that text filtering does not mangle the value's case"""
        query_params = QueryDict("name=John")

        filter_kwargs, exclude_kwargs = self.filter_backend.get_filter_kwargs(
            model_class=FilterTestModel, query_params=query_params
        )

        self.assertEqual(filter_kwargs, {"name": "John"})
        self.assertEqual(exclude_kwargs, {})

    def test_isnull_lookup_is_case_insensitive(self):
        """Test that the isnull lookup accepts boolean values in any casing"""
        query_params = QueryDict("nullable_bool__isnull=TRUE")

        filter_kwargs, exclude_kwargs = self.filter_backend.get_filter_kwargs(
            model_class=FilterTestModel, query_params=query_params
        )

        self.assertEqual(filter_kwargs, {"nullable_bool__isnull": True})

    def test_invalid_lookup_error_includes_reason(self):
        """Test that filter errors propagate their reason to the client"""
        query_params = QueryDict("name__bogus=test")
        request = Mock()
        request.query_params = query_params

        with self.assertRaises(ParseError) as context:
            self.filter_backend.filter_queryset(request, FilterTestModel.objects.none(), self.mock_view)

        self.assertEqual(str(context.exception.detail), "Unsupported lookup in 'name__bogus'.")


class ExposureOwner(models.Model):
    name = models.CharField(max_length=100)
    token = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)

    class Meta:
        app_label = "test_app"


class ExposureHidden(models.Model):
    secret = models.CharField(max_length=100)

    class Meta:
        app_label = "test_app"


class ExposurePost(models.Model):
    title = models.CharField(max_length=100)
    body = models.TextField()
    owner = models.ForeignKey(ExposureOwner, null=True, on_delete=models.CASCADE)
    hidden = models.ForeignKey(ExposureHidden, null=True, on_delete=models.CASCADE)
    editors = models.ManyToManyField(ExposureOwner, related_name="edited_posts")

    class Meta:
        app_label = "test_app"


class LookupFilterExposureTests(TestCase):
    """Only fields exposed through the API can be filtered on"""

    def setUp(self):
        self._saved_registry = dict(headless_registry._models)
        headless_registry.register(ExposureOwner, exclude=["token"])
        headless_registry.register(ExposurePost)
        self.filter_backend = LookupFilter()

    def tearDown(self):
        headless_registry._models = self._saved_registry

    def get_filter_kwargs(self, model_class, query):
        return self.filter_backend.get_filter_kwargs(model_class=model_class, query_params=QueryDict(query))

    def assertRejected(self, model_class, query, field_name):
        with self.assertRaises(ParseError) as cm:
            self.get_filter_kwargs(model_class, query)
        self.assertEqual(str(cm.exception.detail), f"Field '{field_name}' does not exist")

    def test_excluded_field_rejected(self):
        self.assertRejected(ExposureOwner, "token__startswith=s", "token")

    def test_excluded_field_rejected_in_exclusion(self):
        self.assertRejected(ExposureOwner, "~token=s", "token")

    def test_fields_option_restricts_filtering(self):
        headless_registry.register(ExposurePost, fields=["title", "owner"])
        self.assertRejected(ExposurePost, "body__contains=x", "body")
        filter_kwargs, _ = self.get_filter_kwargs(ExposurePost, "title=x&id=1")
        self.assertEqual(filter_kwargs, {"title": "x", "id": 1})

    def test_traversal_into_excluded_field_rejected(self):
        self.assertRejected(ExposurePost, "owner__token__startswith=s", "owner__token")

    def test_traversal_into_unexposed_model_rejected(self):
        self.assertRejected(ExposurePost, "hidden__secret=s", "hidden__secret")

    def test_relation_to_unexposed_model_filterable_by_pk(self):
        filter_kwargs, _ = self.get_filter_kwargs(ExposurePost, "hidden=1&hidden__in=1,2")
        self.assertEqual(filter_kwargs, {"hidden": "1", "hidden__in": ["1", "2"]})

    def test_traversal_into_exposed_field(self):
        filter_kwargs, exclude_kwargs = self.get_filter_kwargs(ExposurePost, "owner__name__icontains=leon&~owner__id=2")
        self.assertEqual(filter_kwargs, {"owner__name__icontains": "leon"})
        self.assertEqual(exclude_kwargs, {"owner__id": 2})

    def test_traversal_casts_with_target_field(self):
        filter_kwargs, _ = self.get_filter_kwargs(ExposurePost, "owner__is_active=true")
        self.assertEqual(filter_kwargs, {"owner__is_active": True})

    def test_filter_queryset_rejects_hidden_field(self):
        view = Mock(action="list", queryset=ExposureOwner.objects.none())
        request = Mock(query_params=QueryDict("token=s"))
        with self.assertRaises(ParseError):
            self.filter_backend.filter_queryset(request, ExposureOwner.objects.none(), view)

    def test_unexposed_model_uses_view_serializer_fields(self):
        """Custom views on unexposed models only filter on serializer fields"""

        class HiddenSerializer(serializers.ModelSerializer):
            class Meta:
                model = ExposureHidden
                fields = ["id"]

        view = GenericAPIView(serializer_class=HiddenSerializer, queryset=ExposureHidden.objects.none())
        view.request, view.format_kwarg = None, None
        filterable_fields = self.filter_backend.get_filterable_fields(ExposureHidden, view)
        self.assertEqual(filterable_fields, {"id"})


class LookupFilterCostTests(TestCase):
    """Filters that are costly for the database are limited"""

    def setUp(self):
        self._saved_registry = dict(headless_registry._models)
        headless_registry.register(ExposureOwner)
        headless_registry.register(ExposurePost)
        self.filter_backend = LookupFilter()

    def tearDown(self):
        headless_registry._models = self._saved_registry

    def filter(self, query):
        view = Mock(action="list", queryset=ExposurePost.objects.none())
        request = Mock(query_params=QueryDict(query))
        return self.filter_backend.filter_queryset(request, ExposurePost.objects.all(), view)

    def test_regex_lookups_disallowed(self):
        for query in ("title__regex=^(a+)+$", "~title__iregex=a", "owner__name__iregex=a", "title__lower__regex=a"):
            with self.subTest(query=query):
                with self.assertRaises(ParseError) as cm:
                    self.filter(query)
                self.assertIn("lookup is not allowed", str(cm.exception.detail))

    def test_disallowed_lookups_setting(self):
        with override_settings(HEADLESS={"FILTER_DISALLOWED_LOOKUPS": ["contains"]}):
            self.filter("title__regex=a")
            with self.assertRaises(ParseError):
                self.filter("title__contains=a")

    def test_distinct_only_across_to_many_relations(self):
        self.assertFalse(self.filter("title=a&owner__name=b&hidden=1").query.distinct)
        self.assertFalse(self.filter("~editors__name=a").query.distinct)
        self.assertTrue(self.filter("editors__name=a").query.distinct)
        self.assertTrue(self.filter("editors__in=1,2").query.distinct)

    def test_crosses_to_many(self):
        self.assertTrue(self.filter_backend.crosses_to_many(ExposurePost, "editors__name__icontains"))
        self.assertFalse(self.filter_backend.crosses_to_many(ExposurePost, "owner__name__icontains"))
        self.assertFalse(self.filter_backend.crosses_to_many(ExposurePost, "title__in"))


class LookupFilterErrorTests(TestCase):
    """Invalid filters answer with a message about the query parameter, never Django internals"""

    def setUp(self):
        self.filter_backend = LookupFilter()

    def filter(self, query):
        view = Mock(action="list", queryset=FilterTestModel.objects.none())
        request = Mock(query_params=QueryDict(query))
        return self.filter_backend.filter_queryset(request, FilterTestModel.objects.all(), view)

    def assertDetail(self, query, detail):
        with self.assertRaises(ParseError) as cm:
            self.filter(query)
        self.assertEqual(str(cm.exception.detail), detail)

    def test_unsupported_lookup(self):
        self.assertDetail("name__foo=1", "Unsupported lookup in 'name__foo'.")
        self.assertDetail("~age__lower__bar=1", "Unsupported lookup in '~age__lower__bar'.")

    def test_invalid_value_keeps_validation_message(self):
        with self.assertRaises(ParseError) as cm:
            self.filter("created_at__gte=not-a-date")
        detail = str(cm.exception.detail)
        self.assertTrue(detail.startswith("Invalid value for 'created_at__gte': "))
        self.assertIn("invalid format", detail)
        self.assertNotIn("['", detail)

    def test_invalid_value_without_details(self):
        self.assertDetail("created_at__year=abc", "Invalid value for 'created_at__year'.")

    def test_range_takes_two_values(self):
        self.assertDetail("age__range=1,2,3", "The range lookup in 'age__range' takes two values.")
        self.assertDetail("age__range=1", "The range lookup in 'age__range' takes two values.")
        self.assertIn("BETWEEN", str(self.filter("age__range=1,2").query))

    def test_unexpected_errors_are_not_exposed(self):
        queryset = Mock()
        queryset.filter.side_effect = RuntimeError("connection to 10.0.0.5 refused")
        view = Mock(action="list", queryset=FilterTestModel.objects.none())
        request = Mock(query_params=QueryDict("name=a"))

        with self.assertRaises(ParseError) as cm:
            self.filter_backend.filter_queryset(request, queryset, view)
        self.assertEqual(str(cm.exception.detail), "Invalid filter parameters.")


class LookupFilterNonFilterFieldsTests(TestCase):
    """Query parameters of other filter backends, pagination and DRF are never read as filters"""

    def setUp(self):
        self.filter_backend = LookupFilter()

    def get_filter_kwargs(self, query, view):
        filter_kwargs, _ = self.filter_backend.get_filter_kwargs(
            model_class=FilterTestModel,
            query_params=QueryDict(query),
            non_filter_fields=self.filter_backend.get_non_filter_fields(view),
        )
        return filter_kwargs

    def test_custom_search_and_ordering_params(self):
        class QSearchFilter(SearchFilter):
            search_param = "q"

        class SortOrderingFilter(OrderingFilter):
            ordering_param = "sort"

        view = Mock(filter_backends=[LookupFilter, QSearchFilter, SortOrderingFilter], pagination_class=None)
        self.assertEqual(self.get_filter_kwargs("q=django&sort=-age&name=a", view), {"name": "a"})

    def test_pagination_params(self):
        view = Mock(filter_backends=[LookupFilter], pagination_class=LimitOffsetPagination)
        self.assertEqual(self.get_filter_kwargs("limit=10&offset=20&name=a", view), {"name": "a"})

        view = Mock(filter_backends=[LookupFilter], pagination_class=CursorPagination)
        self.assertEqual(self.get_filter_kwargs("cursor=abc&name=a", view), {"name": "a"})

    def test_format_and_flex_fields_params(self):
        view = Mock(filter_backends=[LookupFilter], pagination_class=None)
        self.assertEqual(self.get_filter_kwargs("format=json&expand[]=a&omit=b&name=a", view), {"name": "a"})

    def test_non_filter_fields_setting_still_applies(self):
        self.assertEqual(self.get_filter_kwargs("search=django&page=2&name=a", None), {"name": "a"})

    def test_generated_route_with_search_param(self):
        with override_settings(
            HEADLESS={
                "DEFAULT_FILTER_BACKENDS": [
                    "headless.rest.filters.LookupFilter",
                    "rest_framework.filters.SearchFilter",
                ],
                "SEARCH_PARAM": "q",
                "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.LimitOffsetPagination",
            }
        ):
            viewset = get_view_set({"model": FilterTestModel, "singleton": False, "search_fields": ["name"]}, {}, {})

        self.assertTrue({"q", "limit", "offset"} <= self.filter_backend.get_non_filter_fields(viewset))
