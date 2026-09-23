"""
Shared pagination classes.

WHY THIS FILE EXISTS
---------------------
Before this refactor, almost none of Luma's endpoints paginated
their results — most `ListAPIView`s relied on DRF's implicit
default (no pagination at all), and every hand-rolled `APIView`
(students, attendance history, dashboard, reports, fees...) built
a Python list of every matching row and serialized ALL of it in a
single response.

For a small school that "works" today, but it means:
  * A "list all students" call loads every student row + every
    related parent/classroom row, every single time.
  * A parent scrolling attendance history for a child who has been
    enrolled for 3 years pulls every attendance record ever created.
  * Response payloads grow unboundedly as the school grows, and so
    does DB + serialization + network cost per request.

Fix: paginate EVERYTHING that returns more than one row, with a
sane, capped page size the frontend can optionally override.

`StandardResultsSetPagination` is registered as the project-wide
default in settings.py (`REST_FRAMEWORK["DEFAULT_PAGINATION_CLASS"]`),
so every `generics.ListAPIView` / `ModelViewSet.list()` in the
project is paginated automatically — no per-view code required.

Hand-rolled `APIView`s (which don't get this for free, because they
don't call DRF's `list()`) use `paginate_queryset_response()` below
to opt into the exact same behaviour with one line.
"""

from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class StandardResultsSetPagination(PageNumberPagination):
    """
    Default pagination for almost every list endpoint in the project.

    - `page_size`: sensible default so a normal list screen loads
      quickly (25 rows ~ one screen + a bit of scroll).
    - `page_size_query_param`: lets the frontend ask for a bigger or
      smaller page (e.g. `?page_size=100` for an export view) WITHOUT
      needing a new endpoint.
    - `max_page_size`: hard ceiling so a client (or a bug, or a bad
      actor) can never force the server to load/serialize an entire
      table in one request, no matter what page_size they pass.
    """

    page_size = 25
    page_size_query_param = "page_size"
    max_page_size = 100

    def get_paginated_response(self, data):
        # Extra metadata (total_pages, current page, page_size) on
        # top of DRF's default count/next/previous, because the
        # frontend needs these to render page controls without a
        # second request just to find out how many pages exist.
        return Response(
            {
                "count": self.page.paginator.count,
                "total_pages": self.page.paginator.num_pages,
                "current_page": self.page.number,
                "page_size": self.get_page_size(self.request),
                "next": self.get_next_link(),
                "previous": self.get_previous_link(),
                "results": data,
            }
        )


class LargeResultsSetPagination(StandardResultsSetPagination):
    """
    For endpoints that legitimately need bigger pages (bulk export /
    printable report style views). Still capped — "large" is not
    "unlimited".
    """

    page_size = 100
    max_page_size = 500


class SmallResultsSetPagination(StandardResultsSetPagination):
    """For dashboard "top N" / widget-style lists."""

    page_size = 10
    max_page_size = 50


def paginate_queryset_response(view, queryset, serializer_class, context=None):
    """
    Paginate + serialize a queryset from inside a plain `APIView`
    (i.e. anywhere that isn't already a `generics.ListAPIView` /
    `ModelViewSet`, which get pagination for free from settings).

    Usage inside an APIView.get():

        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        serializer = MySerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    or, more tersely, via this helper:

        return paginate_queryset_response(self, queryset, MySerializer)

    Returns None if pagination isn't configured/needed, in which case
    the caller should fall back to serializing the full queryset (this
    mirrors DRF's own `GenericAPIView.paginate_queryset` contract).
    """
    paginator = getattr(view, "pagination_class", StandardResultsSetPagination)()
    page = paginator.paginate_queryset(queryset, view.request, view=view)
    if page is None:
        return None
    serializer = serializer_class(page, many=True, context=context or {"request": view.request})
    return paginator.get_paginated_response(serializer.data)
