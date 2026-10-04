from typing import Type, Dict, Any

from django.db.models import Model
from rest_framework.viewsets import ModelViewSet

from ..viewsets import SingletonViewSet
from ...registry import ModelConfig


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
    serializer = get_serializer(model_class, serializer_cache)

    if singleton:

        class ViewSet(SingletonViewSet):
            queryset = model_class.objects.all()
            serializer_class = serializer

    else:

        class ViewSet(ModelViewSet):
            queryset = model_class.objects.all()
            serializer_class = serializer
            search_fields = model_config["search_fields"]

    viewset_cache[model_name] = ViewSet
    return ViewSet


def get_serializer(model_class: Type[Model], serializer_cache: Dict[str, Type[Any]]) -> Type[Any]:
    """
    Get or create a serializer class for the given model.
    This is a local import to avoid circular dependencies.
    """
    from .serializer import get_serializer as get_serializer_func

    return get_serializer_func(model_class, serializer_cache)
