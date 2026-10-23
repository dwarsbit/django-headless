from typing import Type, Dict, Any

from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.settings import api_settings
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

from ..viewsets import ConstraintErrorMixin, ExpandPrefetchMixin, LookupFieldsMixin, SingletonViewSet
from ...registry import ModelConfig
from ...settings import headless_settings
from ...utils import get_authentication_classes, get_permission_classes
from .serializer import get_serializer


def get_view_set(
    model_config: ModelConfig,
    viewset_cache: Dict[str, Type[Any]],
    serializer_cache: Dict[str, Type[Any]],
) -> Type[Any]:
    """
    Get or create a viewset class for the given model configuration.

    Args:
        model_config: Configuration dictionary containing model and settings
        viewset_cache: Cache dictionary for storing created viewsets
        serializer_cache: Cache dictionary for storing created serializers

    Returns:
        A viewset class configured for the model
    """
    model_class = model_config["model"]
    model_name = model_class._meta.label

    # Return cached viewset if it exists
    if model_name in viewset_cache:
        return viewset_cache[model_name]

    singleton = model_config["singleton"]
    read_only = model_config.get("read_only", False)
    serializer = get_serializer(
        model_class,
        serializer_cache,
        fields=model_config.get("fields"),
        exclude=model_config.get("exclude"),
    )

    if singleton:

        class ViewSet(SingletonViewSet):
            queryset = model_class.objects.all()
            serializer_class = serializer

    elif read_only:

        class ViewSet(ExpandPrefetchMixin, ReadOnlyModelViewSet):
            # Deterministic ordering, so paginated lists are stable
            queryset = model_class.objects.all().order_by("pk")
            serializer_class = serializer
            search_fields = model_config["search_fields"]
            ordering = ["pk"]

    else:

        class ViewSet(ConstraintErrorMixin, ExpandPrefetchMixin, ModelViewSet):
            # Deterministic ordering, so paginated lists are stable
            queryset = model_class.objects.all().order_by("pk")
            serializer_class = serializer
            search_fields = model_config["search_fields"]
            ordering = ["pk"]

    lookup_fields = model_config.get("lookup_fields") or []
    if lookup_fields:
        attrs = {"lookup_actions": {f"by_{field_name}": field_name for field_name in lookup_fields}}
        for field_name in lookup_fields:
            attrs[f"by_{field_name}"] = _make_lookup_action(field_name)
        ViewSet = type("ViewSet", (LookupFieldsMixin, ViewSet), attrs)

    # Apply any DRF-level HEADLESS overrides to the generated route.
    apply_drf_overrides(ViewSet)

    viewset_cache[model_name] = ViewSet
    return ViewSet


def _make_lookup_action(field_name: str):
    """
    Create a GET-only route that retrieves a single object by a unique
    field, at <model>/by_<field>/<value>.
    """

    def retrieve_by(self, request, value=None):
        return self.retrieve_by_lookup(request, value)

    retrieve_by.__name__ = f"by_{field_name}"

    return action(
        detail=False,
        methods=["get"],
        # Unlike DRF's default lookup pattern, dots are allowed in values
        url_path=rf"by_{field_name}/(?P<value>[^/]+)",
        url_name=f"by-{field_name}",
    )(retrieve_by)


def apply_drf_overrides(viewset: Type[Any]) -> None:
    """
    Apply the DRF-level HEADLESS settings to a generated viewset class.

    DRF resolves renderer, parser, authentication, permission, filter and
    pagination classes from api_settings at import time, so runtime changes
    to REST_FRAMEWORK never reach already-defined viewsets. Setting the
    class attributes here gives the generated routes their own values,
    leaving the rest of the project's API untouched. Unset settings
    leave the viewset with the DRF defaults it inherited.
    """
    if headless_settings.DEFAULT_RENDERER_CLASSES is not None:
        viewset.renderer_classes = list(headless_settings.DEFAULT_RENDERER_CLASSES)

    if headless_settings.DEFAULT_PARSER_CLASSES is not None:
        viewset.parser_classes = list(headless_settings.DEFAULT_PARSER_CLASSES)

    # Resolved by the same helpers the boot log uses, so it reports the
    # classes the generated routes actually use.
    viewset.authentication_classes = get_authentication_classes()
    viewset.permission_classes = get_permission_classes()

    pagination_class = headless_settings.DEFAULT_PAGINATION_CLASS
    base_class = pagination_class if pagination_class is not None else api_settings.DEFAULT_PAGINATION_CLASS
    if base_class is not None:
        # PAGE_SIZE and MAX_PAGE_SIZE live on the pagination class, not the
        # viewset, so they require a subclass of the effective pagination class.
        attrs = {}
        if headless_settings.PAGE_SIZE is not None:
            attrs["page_size"] = headless_settings.PAGE_SIZE
        # max_page_size caps page number and cursor pagination, max_limit
        # caps limit/offset pagination. None removes the cap.
        attrs["max_page_size"] = headless_settings.MAX_PAGE_SIZE
        attrs["max_limit"] = headless_settings.MAX_PAGE_SIZE
        viewset.pagination_class = type("HeadlessPagination", (base_class,), attrs)

    if headless_settings.DEFAULT_FILTER_BACKENDS is not None:
        viewset.filter_backends = list(headless_settings.DEFAULT_FILTER_BACKENDS)

    search_param = headless_settings.SEARCH_PARAM
    ordering_param = headless_settings.ORDERING_PARAM
    if search_param is not None or ordering_param is not None:
        # The parameters live on the filter backend classes. Substitute
        # exact DRF SearchFilter/OrderingFilter backends with subclasses
        # carrying the overridden parameter; custom backends are untouched.
        viewset.filter_backends = [
            _patch_filter_backend(backend, search_param, ordering_param) for backend in viewset.filter_backends
        ]


def _patch_filter_backend(backend: Type[Any], search_param, ordering_param) -> Type[Any]:
    if search_param is not None and backend is SearchFilter:
        return type("HeadlessSearchFilter", (SearchFilter,), {"search_param": search_param})

    if ordering_param is not None and backend is OrderingFilter:
        return type("HeadlessOrderingFilter", (OrderingFilter,), {"ordering_param": ordering_param})

    return backend
