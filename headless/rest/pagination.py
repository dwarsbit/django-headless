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
                    "limit": self.page_size,
                    "links": {
                        "self": absolute_uri,
                        "next": self.get_next_link(),
                        "previous": self.get_previous_link(),
                    },
                },
                "data": data,
            }
        )
