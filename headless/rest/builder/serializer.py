from typing import Type, Dict, Any, List, Optional

from django.db.models import Model

from ...settings import headless_settings


def get_serializer(
    model_class: Type[Model],
    serializer_cache: Dict[str, Type[Any]],
    fields: Optional[List[str]] = None,
    exclude: Optional[List[str]] = None,
) -> Type[Any]:
    """
    Get or create a serializer class for the given model.

    Args:
        model_class: The Django model class to create serializer for
        serializer_cache: Cache dictionary for storing created serializers
        fields: Restrict the serializer to these field names
        exclude: Exclude these field names from the serializer

    Returns:
        A serializer class for the model
    """
    model_name = model_class._meta.label

    # Return serializer class from cache if it exists
    if model_name in serializer_cache:
        return serializer_cache[model_name]

    Serializer = type(
        "Serializer",
        (headless_settings.DEFAULT_SERIALIZER_CLASS,),
        {"Meta": type("Meta", (), get_meta_attrs(model_class, fields, exclude))},
    )

    serializer_cache[model_name] = Serializer

    return Serializer


def get_meta_attrs(
    model_class: Type[Model],
    fields: Optional[List[str]] = None,
    exclude: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Get the serializer Meta attributes for the given model and field options.

    Args:
        model_class: The Django model class to serialize
        fields: Restrict the serializer to these field names
        exclude: Exclude these field names from the serializer

    Returns:
        A dictionary of Meta attributes
    """
    meta_attrs = {"model": model_class}
    # An empty fields list is rejected by the registry; never let it fall
    # through to "__all__"
    if fields is not None:
        meta_attrs["fields"] = fields
    elif exclude:
        # DRF does not allow setting both fields and exclude
        meta_attrs["exclude"] = exclude
    else:
        meta_attrs["fields"] = "__all__"

    return meta_attrs
