from typing import Type, Dict, Optional, TypedDict, List

from django.core.exceptions import ImproperlyConfigured
from django.db import models


class ModelConfig(TypedDict):
    model: Type[models.Model]
    singleton: bool
    search_fields: list[str]
    fields: Optional[list[str]]
    exclude: Optional[list[str]]
    read_only: bool


# Lookup prefixes supported by DRF's SearchFilter on search_fields
SEARCH_FIELD_PREFIXES = "^=@$"


class HeadlessRegistry:
    """
    A registry to store registered Django models.
    """

    def __init__(self):
        self._models: Dict[str, ModelConfig] = {}

    def register(
        self,
        model_class: Type[models.Model],
        singleton=False,
        search_fields=None,
        fields=None,
        exclude=None,
        read_only=False,
    ):
        """
        Register a model in the registry.

        Args:
            model_class: The Django model class to register
            singleton: Whether the model should be registered as a singleton
            search_fields: A list of names of text type fields on the model, such as CharField or TextField.
            fields: Restrict the exposed serializer to these field names.
            exclude: Exclude these field names from the exposed serializer.
            read_only: Whether the model should be exposed read-only (no create, update or delete).
        """
        if not (isinstance(model_class, type) and issubclass(model_class, models.Model)):
            raise ImproperlyConfigured(
                f"@expose can only be used on Django models, got {model_class!r}. "
                "Make sure the decorator is placed below models.Model."
            )

        if fields is not None and exclude is not None:
            raise ImproperlyConfigured("The fields and exclude options cannot be combined.")

        if not search_fields:
            search_fields = self._get_default_search_fields(model_class)

        self._validate_search_fields(model_class, search_fields)
        self._validate_field_names(model_class, fields, "fields")
        self._validate_field_names(model_class, exclude, "exclude")

        self._models[model_class._meta.label_lower] = {
            "model": model_class,
            "singleton": singleton,
            "search_fields": [] if singleton else search_fields,
            "fields": fields,
            "exclude": exclude,
            "read_only": read_only,
        }

    def get_model(self, label: str) -> Optional[ModelConfig]:
        """
        Get a model by label.

        Args:
            label: The label of the model to get.
        """
        return self._models.get(label.lower())

    def get_models(self) -> list[ModelConfig]:
        """
        Get all registered models.
        """
        return list(self._models.values())

    def __len__(self):
        return len(self._models)

    def _get_default_search_fields(self, model: Type[models.Model]) -> List[str]:
        """
        Returns a list of field names that are searchable (i.e. CharField).

        Args:
            model: A Django model class

        Returns:
            List of field names that are CharField or TextField instances
        """
        searchable_fields = []

        for field in model._meta.fields:
            if isinstance(field, models.CharField) and not getattr(field, "choices", None):
                searchable_fields.append(field.name)

        return searchable_fields

    def _validate_search_fields(self, model: Type[models.Model], search_fields: List[str]):
        """
        Validate that the search fields exist on the model. Allows the lookup
        prefixes supported by DRF's SearchFilter (e.g. "^title") and traversal
        of related fields (e.g. "author__name").

        Args:
            model: A Django model class
            search_fields: The search field names to validate

        Raises:
            ImproperlyConfigured: If a search field does not exist on the model
        """
        field_names = {field.name for field in model._meta.get_fields()}

        invalid = []
        for name in search_fields:
            if not isinstance(name, str):
                invalid.append(name)
                continue
            base_name = name.lstrip(SEARCH_FIELD_PREFIXES).split("__")[0]
            if base_name not in field_names:
                invalid.append(name)

        if invalid:
            raise ImproperlyConfigured(
                f"Invalid search_fields for model {model._meta.label}: {invalid}. "
                "Search fields must be names of fields on the model."
            )

    def _validate_field_names(self, model: Type[models.Model], names: Optional[List[str]], option: str):
        """
        Validate that the given field names exist on the model.

        Args:
            model: A Django model class
            names: The field names to validate, or None
            option: The name of the option being validated (for error messages)

        Raises:
            ImproperlyConfigured: If a field name does not exist on the model
        """
        if not names:
            return

        field_names = {field.name for field in model._meta.get_fields()}

        invalid = [name for name in names if not isinstance(name, str) or name not in field_names]

        if invalid:
            raise ImproperlyConfigured(
                f"Invalid fields in {option} for model {model._meta.label}: {invalid}. "
                f"The {option} option takes names of fields on the model."
            )


# Create a default registry
headless_registry = HeadlessRegistry()
