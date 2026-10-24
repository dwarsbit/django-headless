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
    lookup_fields: list[str]


# Lookup prefixes supported by DRF's SearchFilter on search_fields
SEARCH_FIELD_PREFIXES = "^=@$"


class HeadlessRegistry:
    """
    A registry to store registered Django models.
    """

    def __init__(self):
        self._models: Dict[str, ModelConfig] = {}
        # Labels of models registered again with different options; the
        # last registration replaces the earlier ones.
        self._conflicting_labels: set[str] = set()

    def register(
        self,
        model_class: Type[models.Model],
        singleton=False,
        search_fields=None,
        fields=None,
        exclude=None,
        read_only=False,
        lookup_fields=None,
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
            lookup_fields: Names of unique fields to expose a retrieve route for, at by_<field>/<value>.
        """
        if not (isinstance(model_class, type) and issubclass(model_class, models.Model)):
            raise ImproperlyConfigured(
                f"@expose can only be used on Django models, got {model_class!r}. "
                "Make sure the decorator is placed below models.Model."
            )

        for option, value in (
            ("search_fields", search_fields),
            ("fields", fields),
            ("exclude", exclude),
            ("lookup_fields", lookup_fields),
        ):
            self._validate_list_option(model_class, value, option)

        if fields is not None and exclude is not None:
            raise ImproperlyConfigured("The fields and exclude options cannot be combined.")

        if fields is not None and not fields:
            raise ImproperlyConfigured(
                f"Invalid fields for model {model_class._meta.label}: the list is empty. "
                "List the fields the API may serialize, or leave out the fields option to serialize all fields."
            )

        if not search_fields:
            search_fields = self._get_default_search_fields(model_class, fields, exclude)

        self._validate_search_fields(model_class, search_fields)
        self._validate_field_names(model_class, fields, "fields")
        self._validate_field_names(model_class, exclude, "exclude")

        if lookup_fields and singleton:
            raise ImproperlyConfigured("The lookup_fields option cannot be used on singletons.")

        self._validate_lookup_fields(model_class, lookup_fields)

        label = model_class._meta.label_lower
        config: ModelConfig = {
            "model": model_class,
            "singleton": singleton,
            "search_fields": [] if singleton else search_fields,
            "fields": fields,
            "exclude": exclude,
            "read_only": read_only,
            "lookup_fields": list(lookup_fields or []),
        }

        previous = self._models.get(label)
        if previous is not None and previous != config:
            self._conflicting_labels.add(label)

        self._models[label] = config

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

    def get_conflicting_labels(self) -> set[str]:
        """
        Get the labels of models that were registered more than once with
        different options. The last registration of each is in effect.
        """
        return set(self._conflicting_labels) & set(self._models)

    def __len__(self):
        return len(self._models)

    def get_exposed_fields(self, model: Type[models.Model]) -> Optional[set[str]]:
        """
        Get the names of the fields of a registered model that are exposed
        through the API, honoring its fields and exclude options. These are
        the fields that may be filtered on. Reverse relations are only
        included when the related model is registered as well. The primary
        key is always included.

        Must be called after the app registry is ready.

        Args:
            model: A Django model class

        Returns:
            The exposed field names, or None if the model is not registered.
        """
        config = self._models.get(model._meta.label_lower)

        if config is None:
            return None

        if config["fields"] is not None:
            return {*config["fields"], model._meta.pk.name}

        names = set()
        for field in model._meta.get_fields():
            is_reverse = field.auto_created and not field.concrete
            if is_reverse and not (field.related_model and field.related_model._meta.label_lower in self._models):
                continue
            names.add(field.name)

        return (names - set(config["exclude"] or [])) | {model._meta.pk.name}

    def _get_default_search_fields(
        self,
        model: Type[models.Model],
        fields: Optional[List[str]] = None,
        exclude: Optional[List[str]] = None,
    ) -> List[str]:
        """
        Returns the names of the fields that are searchable by default: the
        CharFields (including subclasses such as SlugField and EmailField)
        without choices. TextFields are not included. Fields hidden by the
        fields or exclude options are never searchable.

        Args:
            model: A Django model class
            fields: The fields option of the model, if any
            exclude: The exclude option of the model, if any

        Returns:
            List of names of CharFields without choices
        """
        searchable_fields = []

        for field in model._meta.fields:
            if fields is not None and field.name not in fields:
                continue
            if exclude is not None and field.name in exclude:
                continue
            if isinstance(field, models.CharField) and not getattr(field, "choices", None):
                searchable_fields.append(field.name)

        return searchable_fields

    def _get_field_names(self, model: Type[models.Model]) -> set[str]:
        """
        Return the names of the model's forward fields, including inherited
        fields and many-to-many fields.

        Args:
            model: A Django model class
        """
        # Deliberately avoid model._meta.get_fields() here: it also collects
        # reverse relations, which requires every app's models to be loaded.
        # @expose runs at model definition time, during apps.populate(), when
        # that would raise AppRegistryNotReady. The fields and many_to_many
        # properties only enumerate forward fields and are safe at that point.
        return {field.name for field in (*model._meta.fields, *model._meta.many_to_many)}

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
        field_names = self._get_field_names(model)

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

        field_names = self._get_field_names(model)

        if option == "fields":
            # Model properties can be listed in fields as read-only fields
            field_names |= {name for name in dir(model) if isinstance(getattr(model, name, None), property)}

        invalid = [name for name in names if not isinstance(name, str) or name not in field_names]

        if invalid:
            raise ImproperlyConfigured(
                f"Invalid fields in {option} for model {model._meta.label}: {invalid}. "
                f"The {option} option takes names of fields on the model."
            )

    def _validate_list_option(self, model: Type[models.Model], value, option: str):
        """
        Validate that an option that takes field names is a list or tuple.
        A string is iterable too, so without this check every character
        would be validated as a field name.

        Args:
            model: A Django model class
            value: The value of the option, or None
            option: The name of the option (for error messages)

        Raises:
            ImproperlyConfigured: If the value is not None, a list or a tuple
        """
        if value is None or isinstance(value, (list, tuple)):
            return

        message = f"Invalid {option} for model {model._meta.label}: expected a list of field names, got {value!r}."
        if isinstance(value, str):
            # A common cause is a missing comma in a one-element tuple: ("title")
            message += f' Did you mean ["{value}"]?'

        raise ImproperlyConfigured(message)

    def _validate_lookup_fields(self, model: Type[models.Model], lookup_fields: Optional[List[str]]):
        """
        Validate that the lookup fields are unique, concrete fields on the model
        other than the primary key (which already has its own detail route).

        A lookup field may be hidden by the fields or exclude options. This is
        intended: a hidden unique field, such as a token in a secret link, can
        then serve as the key to its object without the API serializing it.

        Args:
            model: A Django model class
            lookup_fields: The lookup field names to validate, or None

        Raises:
            ImproperlyConfigured: If a lookup field is not a unique field on the model
        """
        if not lookup_fields:
            return

        fields = {field.name: field for field in model._meta.fields}

        # Single-field unique constraints without a condition are as unique as unique=True
        constrained = {
            constraint.fields[0]
            for constraint in model._meta.constraints
            if isinstance(constraint, models.UniqueConstraint)
            and len(constraint.fields) == 1
            and constraint.condition is None
            and not constraint.expressions
        }

        invalid = []
        for name in lookup_fields:
            field = fields.get(name) if isinstance(name, str) else None
            if field is None or field.primary_key or not (field.unique or name in constrained):
                invalid.append(name)

        if invalid:
            raise ImproperlyConfigured(
                f"Invalid lookup_fields for model {model._meta.label}: {invalid}. "
                "Lookup fields must be names of unique fields on the model, other than the primary key."
            )


# Create a default registry
headless_registry = HeadlessRegistry()
