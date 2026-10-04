from unittest.mock import Mock

from django.db import models
from django.test import TestCase
from rest_framework.exceptions import ParseError
from rest_framework.request import QueryDict

from headless.rest.filters import LookupFilter


class TestModel(models.Model):
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
        self.mock_view.queryset = TestModel.objects.none()

    def test_basic_filtering(self):
        """Test basic field filtering"""
        query_params = QueryDict("name=test")
        request = Mock()
        request.query_params = query_params

        # Should not raise an exception
        try:
            result = self.filter_backend.filter_queryset(request, TestModel.objects.none(), self.mock_view)
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
                    result = self.filter_backend.filter_queryset(request, TestModel.objects.none(), self.mock_view)
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
                    result = self.filter_backend.filter_queryset(request, TestModel.objects.none(), self.mock_view)
                except Exception as e:
                    self.fail(f"Nullable boolean filtering with '{value}' raised an exception: {e}")

    def test_integer_filtering(self):
        """Test integer field filtering"""
        query_params = QueryDict("age=25")
        request = Mock()
        request.query_params = query_params

        try:
            result = self.filter_backend.filter_queryset(request, TestModel.objects.none(), self.mock_view)
        except Exception as e:
            self.fail(f"Integer filtering raised an exception: {e}")

    def test_decimal_filtering(self):
        """Test decimal field filtering"""
        query_params = QueryDict("price=19.99")
        request = Mock()
        request.query_params = query_params

        try:
            result = self.filter_backend.filter_queryset(request, TestModel.objects.none(), self.mock_view)
        except Exception as e:
            self.fail(f"Decimal filtering raised an exception: {e}")

    def test_float_filtering(self):
        """Test float field filtering"""
        query_params = QueryDict("rating=4.5")
        request = Mock()
        request.query_params = query_params

        try:
            result = self.filter_backend.filter_queryset(request, TestModel.objects.none(), self.mock_view)
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
                    result = self.filter_backend.filter_queryset(request, TestModel.objects.none(), self.mock_view)
                except Exception as e:
                    self.fail(f"Lookup filtering with '{lookup}' raised an exception: {e}")

    def test_multi_value_filtering(self):
        """Test multi-value filtering (e.g., __in lookup)"""
        query_params = QueryDict("age__in=25,30,35")
        request = Mock()
        request.query_params = query_params

        try:
            result = self.filter_backend.filter_queryset(request, TestModel.objects.none(), self.mock_view)
        except Exception as e:
            self.fail(f"Multi-value filtering raised an exception: {e}")

    def test_exclusion_filtering(self):
        """Test exclusion filtering using the exclusion symbol"""
        query_params = QueryDict("~is_active=true")
        request = Mock()
        request.query_params = query_params

        try:
            result = self.filter_backend.filter_queryset(request, TestModel.objects.none(), self.mock_view)
        except Exception as e:
            self.fail(f"Exclusion filtering raised an exception: {e}")

    def test_invalid_field_filtering(self):
        """Test that invalid field names raise ParseError"""
        query_params = QueryDict("nonexistent_field=value")
        request = Mock()
        request.query_params = query_params

        with self.assertRaises(ParseError):
            self.filter_backend.filter_queryset(request, TestModel.objects.none(), self.mock_view)

    def test_invalid_boolean_value(self):
        """Test that invalid boolean values raise ParseError"""
        query_params = QueryDict("is_active=invalid")
        request = Mock()
        request.query_params = query_params

        with self.assertRaises(ParseError):
            self.filter_backend.filter_queryset(request, TestModel.objects.none(), self.mock_view)

    def test_invalid_integer_value(self):
        """Test that invalid integer values raise ParseError"""
        query_params = QueryDict("age=not_a_number")
        request = Mock()
        request.query_params = query_params

        with self.assertRaises(ParseError):
            self.filter_backend.filter_queryset(request, TestModel.objects.none(), self.mock_view)

    def test_non_filter_fields(self):
        """Test that non-filter fields are ignored"""
        # Add some non-filter fields
        query_params = QueryDict("search=test&limit=10&name=test")
        request = Mock()
        request.query_params = query_params

        try:
            result = self.filter_backend.filter_queryset(request, TestModel.objects.none(), self.mock_view)
        except Exception as e:
            self.fail(f"Non-filter fields handling raised an exception: {e}")

    def test_get_filter_kwargs(self):
        """Test the get_filter_kwargs method directly"""
        query_params = QueryDict("name=test&age__gte=18")

        try:
            filter_kwargs, exclude_kwargs = self.filter_backend.get_filter_kwargs(
                model_class=TestModel, query_params=query_params
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
                model_class=TestModel, query_params=query_params
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

        original_queryset = TestModel.objects.none()
        result = self.filter_backend.filter_queryset(request, original_queryset, self.mock_view)

        # Should return the original queryset unchanged
        self.assertEqual(result, original_queryset)

    def test_cast_field_value_method(self):
        """Test the cast_field_value method directly"""
        # Test boolean casting
        bool_field = TestModel._meta.get_field("is_active")

        self.assertEqual(self.filter_backend.cast_field_value("true", bool_field), True)
        self.assertEqual(self.filter_backend.cast_field_value("false", bool_field), False)

        # Test integer casting
        int_field = TestModel._meta.get_field("age")
        self.assertEqual(self.filter_backend.cast_field_value("25", int_field), 25)

        # Test decimal casting
        decimal_field = TestModel._meta.get_field("price")
        from decimal import Decimal

        self.assertEqual(
            self.filter_backend.cast_field_value("19.99", decimal_field),
            Decimal("19.99"),
        )

        # Test float casting
        float_field = TestModel._meta.get_field("rating")
        self.assertEqual(self.filter_backend.cast_field_value("4.5", float_field), 4.5)

    def test_cast_field_value_invalid(self):
        """Test cast_field_value with invalid values"""
        # Test invalid boolean
        bool_field = TestModel._meta.get_field("is_active")
        with self.assertRaises(ParseError):
            self.filter_backend.cast_field_value("invalid", bool_field)

        # Test invalid integer
        int_field = TestModel._meta.get_field("age")
        with self.assertRaises(ParseError):
            self.filter_backend.cast_field_value("not_a_number", int_field)

        # Test invalid decimal
        decimal_field = TestModel._meta.get_field("price")
        with self.assertRaises(ParseError):
            self.filter_backend.cast_field_value("invalid_decimal", decimal_field)

        # Test invalid float
        float_field = TestModel._meta.get_field("rating")
        with self.assertRaises(ParseError):
            self.filter_backend.cast_field_value("not_a_float", float_field)

    def test_cast_field_value_preserves_case_for_text(self):
        """Test that text values keep their original casing"""
        field = TestModel._meta.get_field("name")

        self.assertEqual(self.filter_backend.cast_field_value("John", field), "John")
        self.assertEqual(self.filter_backend.cast_field_value("hello World", field), "hello World")

    def test_cast_field_value_strips_whitespace(self):
        """Test that values are stripped before casting"""
        name_field = TestModel._meta.get_field("name")
        int_field = TestModel._meta.get_field("age")

        self.assertEqual(self.filter_backend.cast_field_value("  John  ", name_field), "John")
        self.assertEqual(self.filter_backend.cast_field_value(" 25 ", int_field), 25)

    def test_cast_field_value_boolean_is_case_insensitive(self):
        """Test that boolean values match case-insensitively"""
        field = TestModel._meta.get_field("is_active")

        self.assertEqual(self.filter_backend.cast_field_value("TRUE", field), True)
        self.assertEqual(self.filter_backend.cast_field_value("On", field), True)
        self.assertEqual(self.filter_backend.cast_field_value("False", field), False)
        self.assertEqual(self.filter_backend.cast_field_value("OFF", field), False)

    def test_case_sensitive_text_filter_keeps_case(self):
        """Test that text filtering does not mangle the value's case"""
        query_params = QueryDict("name=John")

        filter_kwargs, exclude_kwargs = self.filter_backend.get_filter_kwargs(
            model_class=TestModel, query_params=query_params
        )

        self.assertEqual(filter_kwargs, {"name": "John"})
        self.assertEqual(exclude_kwargs, {})

    def test_isnull_lookup_is_case_insensitive(self):
        """Test that the isnull lookup accepts boolean values in any casing"""
        query_params = QueryDict("nullable_bool__isnull=TRUE")

        filter_kwargs, exclude_kwargs = self.filter_backend.get_filter_kwargs(
            model_class=TestModel, query_params=query_params
        )

        self.assertEqual(filter_kwargs, {"nullable_bool__isnull": True})

    def test_invalid_lookup_error_includes_reason(self):
        """Test that filter errors propagate their reason to the client"""
        query_params = QueryDict("name__bogus=test")
        request = Mock()
        request.query_params = query_params

        with self.assertRaises(ParseError) as context:
            self.filter_backend.filter_queryset(request, TestModel.objects.none(), self.mock_view)

        self.assertIn("Invalid filter parameters", str(context.exception.detail))
        self.assertIn("bogus", str(context.exception.detail))
