from typing import Optional

from django.core.exceptions import ImproperlyConfigured
from django.db.models import Model
from rest_flex_fields import FlexFieldsModelSerializer
from rest_framework import serializers

from .builder.serializer import get_meta_attrs
from ..registry import headless_registry
from ..settings import headless_settings
from ..utils import log


class FlexibleSerializer(FlexFieldsModelSerializer):
    """
    The flexible serializer is based on the flex fields model serializer
    and includes property fields as read-only fields.

    The fields and exclude options of the serializer Meta are honored for
    property fields and expandable fields alike, and expanded relations
    honor the fields and exclude options of the related exposed model.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Cache the expandable fields to avoid recomputation
        self._expandable_fields_cache = None

    def get_fields(self, *args, **kwargs):
        """
        Include property fields as read-only fields.
        Fields that start with "_" are excluded.
        """
        fields = super().get_fields()

        for name in dir(self.Meta.model):
            attr = getattr(self.Meta.model, name)
            if (
                isinstance(attr, property)
                and name != "pk"
                and not name.startswith("_")
                and self._is_field_allowed(name)
            ):
                fields[name] = serializers.ReadOnlyField()
        return fields

    def _is_field_allowed(self, name: str) -> bool:
        """
        Check whether a field name is allowed by the fields and exclude
        options of the serializer Meta.
        """
        meta_fields = getattr(self.Meta, "fields", None)
        if isinstance(meta_fields, (list, tuple)) and name not in meta_fields:
            return False

        return name not in (getattr(self.Meta, "exclude", None) or ())

    @property
    def _expandable_fields(self) -> dict:
        """
        Automatically include all related fields as expandable fields.
        Results are cached for performance.
        """
        # Return cached result if available
        if self._expandable_fields_cache is not None:
            return self._expandable_fields_cache

        # Validate that Meta class exists and has model attribute
        if not hasattr(self, "Meta"):
            raise ImproperlyConfigured(f"{self.__class__.__name__} is missing Meta class")

        if not hasattr(self.Meta, "model"):
            raise ImproperlyConfigured(f"{self.__class__.__name__}.Meta is missing model attribute")

        model: Optional[Model] = self.Meta.model

        if not model:
            raise ImproperlyConfigured(f"{self.__class__.__name__}.Meta.model is None or invalid")

        # Validate that model has _meta attribute
        if not hasattr(model, "_meta"):
            raise ImproperlyConfigured(
                f"Model {model.__class__.__name__} is missing _meta attribute. "
                f"This typically indicates the model is not a proper Django model."
            )

        expandable_fields = {}

        try:
            # Use model._meta.get_fields() directly without list comprehension for better performance
            # and to avoid creating intermediate lists
            for field in model._meta.get_fields():
                if not field.is_relation:
                    continue

                try:
                    related_model = field.related_model

                    # Skip if related_model is None (can happen with some field types)
                    if related_model is None:
                        continue

                    # Do not expand if model is not in registry
                    related_config = headless_registry.get_model(related_model._meta.label_lower)
                    if related_config is None:
                        continue

                    is_many = field.many_to_many or field.one_to_many
                    name = field.name

                    if is_many:
                        # Use direct attribute access with fallbacks for better performance
                        # ManyToMany fields might not have related_name or accessor_name
                        related_name = getattr(field, "related_name", None)
                        accessor_name = getattr(field, "accessor_name", None)
                        name = related_name or accessor_name or field.name

                    # Do not expand relations hidden by the fields or exclude options
                    if not self._is_field_allowed(name):
                        continue

                    # Create serializer class dynamically, honoring the fields
                    # and exclude options of the related model
                    Serializer = type(
                        f"{related_model.__name__}Serializer",
                        (headless_settings.DEFAULT_SERIALIZER_CLASS,),
                        {
                            "Meta": type(
                                "Meta",
                                (),
                                get_meta_attrs(related_model, related_config["fields"], related_config["exclude"]),
                            )
                        },
                    )

                    expandable_fields[name] = (
                        Serializer,
                        {"many": is_many},
                    )
                except Exception as e:
                    # Log the error but continue with other fields
                    log(
                        f"[yellow]Warning: Failed to process relational field {getattr(field, 'name', 'unknown')} "
                        f"on model {model.__class__.__name__}: {str(e)}[/yellow]"
                    )
                    continue

        except AttributeError as e:
            raise ImproperlyConfigured(f"Failed to get fields from model {model.__class__.__name__}: {str(e)}") from e

        # Cache the result to avoid recomputation
        self._expandable_fields_cache = expandable_fields
        return expandable_fields
