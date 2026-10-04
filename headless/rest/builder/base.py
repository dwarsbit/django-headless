from typing import Type, Any

from django.db.models import Model
from django.urls import path

from headless.utils import log
from .serializer import get_serializer
from .viewset import get_view_set
from ..routers import rest_router, singleton_urls
from ...registry import ModelConfig, headless_registry


class RestBuilder:
    """
    Class for building a REST API for the models in the headless
    registry.
    """

    def __init__(self):
        self._models = headless_registry.get_models()
        self._serializer_classes = {}
        self._viewset_classes = {}

    def build(self) -> None:
        """
        Builds the REST API by creating view sets and serializers and registering them
        to the router.

        Iterates through all registered models, creates appropriate viewsets and serializers,
        and registers them with the router based on whether they are singleton models
        or regular collection models.
        """
        log("\n:building_construction:  Setting up [bold]REST[/bold] routes")

        routes = 0
        singleton_routes = 0

        for model_config in self._models:
            # Validate model config has required fields
            if not all(key in model_config for key in ["model", "singleton", "search_fields"]):
                log(
                    f":warning:  Invalid model config for {model_config.get('model', 'Unknown')}",
                )
                continue

            model_class = model_config["model"]
            singleton = model_config["singleton"]
            view_set = get_view_set(model_config, self._viewset_classes, self._serializer_classes)
            base_path = model_class._meta.label_lower

            if singleton:
                singleton_urls.append(
                    path(
                        base_path,
                        view_set.as_view(
                            {
                                "get": "retrieve",
                                "put": "update",
                                "patch": "partial_update",
                            }
                        ),
                    )
                )
                singleton_routes += 1
            else:
                rest_router.register(base_path, view_set)

            routes += 1

        log(f"   [cyan]•[/cyan] {routes} routes registered")
        log(f"     [dim]{singleton_routes} singleton routes[/dim]")

    def get_serializer(self, model_class: Type[Model]) -> Type[Any]:
        """
        Get or create a serializer class for the given model.

        Args:
            model_class: The Django model class to create serializer for

        Returns:
            A serializer class for the model
        """
        return get_serializer(model_class, self._serializer_classes)

    def get_view_set(self, model_config: ModelConfig) -> Type[Any]:
        """
        Get or create a viewset class for the given model configuration.

        Args:
            model_config: Configuration dictionary containing model and settings

        Returns:
            A viewset class configured for the model
        """
        return get_view_set(model_config, self._viewset_classes, self._serializer_classes)
