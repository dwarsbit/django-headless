from rest_framework.pagination import PageNumberPagination as BasePageNumberPagination
from rest_framework.response import Response


class PageNumberPagination(BasePageNumberPagination):
    page_query_param = "page"
    page_size_query_param = "limit"
    # The largest page size a client can request with ?limit=. On the
    # generated routes, HEADLESS["MAX_PAGE_SIZE"] takes its place.
    max_page_size = 100

    def get_paginated_response(self, data):
        absolute_uri = self.request.build_absolute_uri()
        return Response(
            {
                "pagination": {
                    "count": self.page.paginator.count,
                    "pages": self.page.paginator.num_pages,
                    "current": self.page.number,
                    "limit": self.page.paginator.per_page,
                    "links": {
                        "self": absolute_uri,
                        "next": self.get_next_link(),
                        "previous": self.get_previous_link(),
                    },
                },
                "data": data,
            }
        )

    def get_paginated_response_schema(self, schema):
        """
        The OpenAPI schema of the envelope, with schema (an array of the
        objects) as the schema of data.
        """
        nullable_uri = {"type": "string", "format": "uri", "nullable": True}

        return {
            "type": "object",
            "required": ["pagination", "data"],
            "properties": {
                "pagination": {
                    "type": "object",
                    "required": ["count", "pages", "current", "limit", "links"],
                    "properties": {
                        "count": {"type": "integer", "description": "The number of objects in all pages."},
                        "pages": {"type": "integer", "description": "The number of pages."},
                        "current": {"type": "integer", "description": "The number of the current page."},
                        "limit": {"type": "integer", "description": "The number of objects per page."},
                        "links": {
                            "type": "object",
                            "required": ["self", "next", "previous"],
                            "properties": {
                                "self": {"type": "string", "format": "uri"},
                                "next": nullable_uri,
                                "previous": nullable_uri,
                            },
                        },
                    },
                },
                "data": schema,
            },
        }
