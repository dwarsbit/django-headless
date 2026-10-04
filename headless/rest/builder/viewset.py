from typing import Type, Dict, Any

from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

from ..viewsets import SingletonViewSet
from ...registry import ModelConfig
from ...settings import headless_settings
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

        class ViewSet(ReadOnlyModelViewSet):
            # Deterministic ordering, so paginated lists are stable
            queryset = model_class.objects.all().order_by("pk")
            serializer_class = serializer
            search_fields = model_config["search_fields"]
            ordering = ["pk"]

    else:

        class ViewSet(ModelViewSet):
            # Deterministic ordering, so paginated lists are stable
            queryset = model_class.objects.all().order_by("pk")
            serializer_class = serializer
            search_fields = model_config["search_fields"]
            ordering = ["pk"]

    # When configured, override DRF's default permissions for the
    # generated routes only.
    permissions = headless_settings.DEFAULT_PERMISSION_CLASSES
    if permissions is not None:
        ViewSet.permission_classes = list(permissions)

    viewset_cache[model_name] = ViewSet
    return ViewSet
