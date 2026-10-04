"""
Tests for the PageNumberPagination class
"""

from unittest.mock import Mock

from django.test import SimpleTestCase, RequestFactory

from headless.rest.pagination import PageNumberPagination


class PageNumberPaginationTests(SimpleTestCase):
    """Tests for the PageNumberPagination class"""

    def test_default_query_params(self):
        """Test that default query parameters are set correctly"""
        pagination = PageNumberPagination()

        self.assertEqual(pagination.page_query_param, "page")
        self.assertEqual(pagination.page_size_query_param, "limit")

    def test_get_paginated_response_structure(self):
        """Test that get_paginated_response returns the correct structure"""
        # Create a mock request
        factory = RequestFactory()
        request = factory.get("/test/?page=1&limit=10")

        # Create pagination instance and set up mock page
        pagination = PageNumberPagination()
        pagination.request = request

        # Mock the page and paginator
        mock_page = Mock()
        mock_page.number = 1
        mock_page.has_next.return_value = True
        mock_page.has_previous.return_value = False

        mock_paginator = Mock()
        mock_paginator.count = 100
        mock_paginator.num_pages = 10

        mock_page.paginator = mock_paginator
        pagination.page = mock_page
        pagination.page_size = 10

        # Mock the link methods
        pagination.get_next_link = Mock(return_value="http://testserver/test/?page=2&limit=10")
        pagination.get_previous_link = Mock(return_value=None)

        # Test data
        test_data = [{"id": 1, "name": "Item 1"}, {"id": 2, "name": "Item 2"}]

        # Call the method
        response = pagination.get_paginated_response(test_data)

        # Verify the response structure
        self.assertIn("pagination", response.data)
        self.assertIn("data", response.data)

        # Verify pagination data
        pagination_data = response.data["pagination"]
        self.assertEqual(pagination_data["count"], 100)
        self.assertEqual(pagination_data["pages"], 10)
        self.assertEqual(pagination_data["current"], 1)
        self.assertEqual(pagination_data["limit"], 10)

        # Verify links
        links = pagination_data["links"]
        self.assertIn("self", links)
        self.assertIn("next", links)
        self.assertIn("previous", links)
        self.assertEqual(links["next"], "http://testserver/test/?page=2&limit=10")
        self.assertIsNone(links["previous"])

        # Verify data
        self.assertEqual(response.data["data"], test_data)

    def test_get_paginated_response_with_previous_link(self):
        """Test paginated response when previous link is available"""
        factory = RequestFactory()
        request = factory.get("/test/?page=2&limit=10")

        pagination = PageNumberPagination()
        pagination.request = request

        # Mock the page and paginator
        mock_page = Mock()
        mock_page.number = 2
        mock_page.has_next.return_value = True
        mock_page.has_previous.return_value = True

        mock_paginator = Mock()
        mock_paginator.count = 100
        mock_paginator.num_pages = 10

        mock_page.paginator = mock_paginator
        pagination.page = mock_page
        pagination.page_size = 10

        # Mock the link methods
        pagination.get_next_link = Mock(return_value="http://testserver/test/?page=3&limit=10")
        pagination.get_previous_link = Mock(return_value="http://testserver/test/?page=1&limit=10")

        # Test data
        test_data = [{"id": 3, "name": "Item 3"}, {"id": 4, "name": "Item 4"}]

        # Call the method
        response = pagination.get_paginated_response(test_data)

        # Verify links
        links = response.data["pagination"]["links"]
        self.assertEqual(links["next"], "http://testserver/test/?page=3&limit=10")
        self.assertEqual(links["previous"], "http://testserver/test/?page=1&limit=10")

    def test_get_paginated_response_with_no_links(self):
        """Test paginated response when no next/previous links are available"""
        factory = RequestFactory()
        request = factory.get("/test/?page=5&limit=10")

        pagination = PageNumberPagination()
        pagination.request = request

        # Mock the page and paginator
        mock_page = Mock()
        mock_page.number = 5
        mock_page.has_next.return_value = False
        mock_page.has_previous.return_value = False

        mock_paginator = Mock()
        mock_paginator.count = 50
        mock_paginator.num_pages = 5

        mock_page.paginator = mock_paginator
        pagination.page = mock_page
        pagination.page_size = 10

        # Mock the link methods
        pagination.get_next_link = Mock(return_value=None)
        pagination.get_previous_link = Mock(return_value=None)

        # Test data
        test_data = [{"id": 41, "name": "Item 41"}, {"id": 42, "name": "Item 42"}]

        # Call the method
        response = pagination.get_paginated_response(test_data)

        # Verify links are None
        links = response.data["pagination"]["links"]
        self.assertIsNone(links["next"])
        self.assertIsNone(links["previous"])

    def test_get_paginated_response_empty_data(self):
        """Test paginated response with empty data"""
        factory = RequestFactory()
        request = factory.get("/test/?page=1&limit=10")

        pagination = PageNumberPagination()
        pagination.request = request

        # Mock the page and paginator
        mock_page = Mock()
        mock_page.number = 1
        mock_page.has_next.return_value = False
        mock_page.has_previous.return_value = False

        mock_paginator = Mock()
        mock_paginator.count = 0
        mock_paginator.num_pages = 1

        mock_page.paginator = mock_paginator
        pagination.page = mock_page
        pagination.page_size = 10

        # Mock the link methods
        pagination.get_next_link = Mock(return_value=None)
        pagination.get_previous_link = Mock(return_value=None)

        # Empty data
        test_data = []

        # Call the method
        response = pagination.get_paginated_response(test_data)

        # Verify response structure is maintained
        self.assertIn("pagination", response.data)
        self.assertIn("data", response.data)
        self.assertEqual(response.data["data"], [])
        self.assertEqual(response.data["pagination"]["count"], 0)

    def test_inheritance_from_base_class(self):
        """Test that PageNumberPagination properly inherits from base class"""
        pagination = PageNumberPagination()

        # Should have attributes from base class
        self.assertTrue(hasattr(pagination, "page_size"))
        self.assertTrue(hasattr(pagination, "max_page_size"))
        self.assertTrue(hasattr(pagination, "last_page_strings"))
        self.assertTrue(hasattr(pagination, "template"))

    def test_custom_query_params(self):
        """Test that custom query parameters are used instead of defaults"""
        pagination = PageNumberPagination()

        # The class uses 'page' (same as DRF default) for page parameter
        # but uses 'limit' instead of 'page_size' for page size parameter
        self.assertEqual(pagination.page_query_param, "page")
        self.assertEqual(pagination.page_size_query_param, "limit")

        # Verify it's different from the base class defaults
        from rest_framework.pagination import (
            PageNumberPagination as BasePageNumberPagination,
        )

        base_pagination = BasePageNumberPagination()

        # page_query_param should be the same as base class
        self.assertEqual(pagination.page_query_param, base_pagination.page_query_param)

        # page_size_query_param should be different from base class
        # Base class uses None by default, our class uses 'limit'
        self.assertNotEqual(pagination.page_size_query_param, base_pagination.page_size_query_param)
        self.assertIsNone(base_pagination.page_size_query_param)
        self.assertEqual(pagination.page_size_query_param, "limit")

    def test_response_includes_absolute_uri(self):
        """Test that response includes absolute URI in self link"""
        factory = RequestFactory()
        request = factory.get("/test/?page=1&limit=10")

        pagination = PageNumberPagination()
        pagination.request = request

        # Mock the page and paginator
        mock_page = Mock()
        mock_page.number = 1
        mock_page.has_next.return_value = False
        mock_page.has_previous.return_value = False

        mock_paginator = Mock()
        mock_paginator.count = 10
        mock_paginator.num_pages = 1

        mock_page.paginator = mock_paginator
        pagination.page = mock_page
        pagination.page_size = 10

        # Mock the link methods
        pagination.get_next_link = Mock(return_value=None)
        pagination.get_previous_link = Mock(return_value=None)

        # Test data
        test_data = [{"id": 1, "name": "Item 1"}]

        # Call the method
        response = pagination.get_paginated_response(test_data)

        # Verify self link contains absolute URI
        self_link = response.data["pagination"]["links"]["self"]
        self.assertTrue(self_link.startswith("http://"))
        self.assertTrue("/test/?page=1&limit=10" in self_link)


class PageNumberPaginationIntegrationTests(SimpleTestCase):
    """Integration tests for PageNumberPagination"""

    def test_pagination_with_real_request(self):
        """Test pagination with a real Django request object"""
        factory = RequestFactory()
        request = factory.get("/api/items/?page=2&limit=5")

        pagination = PageNumberPagination()
        pagination.request = request

        # Mock the page and paginator to simulate real pagination
        mock_page = Mock()
        mock_page.number = 2
        mock_page.has_next.return_value = True
        mock_page.has_previous.return_value = True

        mock_paginator = Mock()
        mock_paginator.count = 25
        mock_paginator.num_pages = 5

        mock_page.paginator = mock_paginator
        pagination.page = mock_page
        pagination.page_size = 5

        # Mock the link methods to return realistic URLs
        pagination.get_next_link = Mock(return_value="/api/items/?page=3&limit=5")
        pagination.get_previous_link = Mock(return_value="/api/items/?page=1&limit=5")

        # Test data representing paginated items
        test_data = [
            {"id": 6, "name": "Item 6"},
            {"id": 7, "name": "Item 7"},
            {"id": 8, "name": "Item 8"},
            {"id": 9, "name": "Item 9"},
            {"id": 10, "name": "Item 10"},
        ]

        # Call the method
        response = pagination.get_paginated_response(test_data)

        # Verify the complete response structure
        expected_structure = {
            "pagination": {
                "count": 25,
                "pages": 5,
                "current": 2,
                "limit": 5,
                "links": {
                    "self": str,
                    "next": "/api/items/?page=3&limit=5",
                    "previous": "/api/items/?page=1&limit=5",
                },
            },
            "data": test_data,
        }

        # Check that all expected keys are present
        self.assertEqual(set(response.data.keys()), set(expected_structure.keys()))

        pagination_data = response.data["pagination"]
        self.assertEqual(set(pagination_data.keys()), set(expected_structure["pagination"].keys()))
        self.assertEqual(
            set(pagination_data["links"].keys()),
            set(expected_structure["pagination"]["links"].keys()),
        )

        # Check specific values
        self.assertEqual(pagination_data["count"], 25)
        self.assertEqual(pagination_data["pages"], 5)
        self.assertEqual(pagination_data["current"], 2)
        self.assertEqual(pagination_data["limit"], 5)
        self.assertEqual(pagination_data["links"]["next"], "/api/items/?page=3&limit=5")
        self.assertEqual(pagination_data["links"]["previous"], "/api/items/?page=1&limit=5")
        self.assertEqual(response.data["data"], test_data)

        # Verify self link is an absolute URI
        self.assertTrue(pagination_data["links"]["self"].startswith("http://"))
