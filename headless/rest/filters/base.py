from django.core.exceptions import FieldDoesNotExist, FieldError, ValidationError
from rest_framework.exceptions import ParseError
from rest_framework.filters import BaseFilterBackend
from rest_framework.serializers import BaseSerializer
from rest_framework.settings import api_settings

from headless.registry import headless_registry
from headless.settings import headless_settings
from headless.utils import flatten
from .casting import cast_field_value


class SettingAttribute:
    """
    A class attribute that reads a HEADLESS setting on every access, so it
    follows changes to the settings (e.g. override_settings in tests).
    Subclasses can still override it with a plain value.
    """

    def __init__(self, setting_name):
        self.setting_name = setting_name

    def __get__(self, instance, owner=None):
        return getattr(headless_settings, self.setting_name)


class BooleanValuesAttribute:
    """
    A class attribute with all recognized boolean values: TRUE_VALUES plus
    FALSE_VALUES of the class, including any subclass overrides.
    """

    def __get__(self, instance, owner=None):
        cls = owner if owner is not None else type(instance)
        return list(cls.TRUE_VALUES) + list(cls.FALSE_VALUES)


class LookupFilter(BaseFilterBackend):
    """
    A permissive filter backend that basically allows every supported lookup
    for a given field. Automatically handles multi-value lookups and booleans.
    Also supports exclusion.

    Only exposed fields can be filtered on: fields hidden by the fields or
    exclude options of @expose() are rejected, and relations can only be
    traversed into exposed models, on their exposed fields.
    """

    MULTI_VALUE_LOOKUPS = ["in", "range"]

    TRUE_VALUES = SettingAttribute("FILTER_TRUE_VALUES")

    FALSE_VALUES = SettingAttribute("FILTER_FALSE_VALUES")

    BOOLEANS = BooleanValuesAttribute()

    NULL_VALUES = SettingAttribute("FILTER_NULL_VALUES")

    EXCLUDE_SYMBOL = SettingAttribute("FILTER_EXCLUSION_SYMBOL")

    NON_FILTER_FIELDS = SettingAttribute("NON_FILTER_FIELDS")

    # Attributes of filter backends and pagination classes that name the
    # query parameters they read.
    FILTER_BACKEND_PARAM_ATTRS = ["search_param", "ordering_param"]

    PAGINATION_PARAM_ATTRS = [
        "page_query_param",
        "page_size_query_param",
        "limit_query_param",
        "offset_query_param",
        "cursor_query_param",
    ]

    def filter_queryset(self, request, queryset, view):
        """
        Build the queryset based on the query params and the view's model.
        Only apply filters in list endpoints.
        """
        if getattr(view, "action", None) != "list":
            return queryset

        try:
            model_class = view.queryset.model
            filter_kwargs, exclude_kwargs = self.get_filter_kwargs(
                model_class=model_class,
                query_params=request.query_params,
                filterable_fields=self.get_filterable_fields(model_class, view),
                non_filter_fields=self.get_non_filter_fields(view),
            )
            queryset = queryset.filter(**filter_kwargs).exclude(**exclude_kwargs)
            # Filtering across a to-many relation can repeat rows; only then
            # is the (costly) distinct needed. Exclusions never repeat rows.
            if any(self.crosses_to_many(model_class, path) for path in filter_kwargs):
                queryset = queryset.distinct()
            return queryset
        except ParseError:
            # ParseErrors already carry a descriptive detail; pass them through.
            raise
        except Exception:
            # Each filter is validated on its own beforehand, so this is
            # unexpected. Don't pass internal error messages to the client.
            raise ParseError(detail="Invalid filter parameters.")

    def get_non_filter_fields(self, view=None):
        """
        Return the query parameters that are never read as filters: those
        in NON_FILTER_FIELDS, DRF's format parameter, drf-flex-fields'
        parameters, and the parameters of the view's other filter backends
        (e.g. SearchFilter's search_param) and pagination class.
        """
        from rest_flex_fields import EXPAND_PARAM, FIELDS_PARAM, OMIT_PARAM

        names = set(self.NON_FILTER_FIELDS)

        if api_settings.URL_FORMAT_OVERRIDE:
            names.add(api_settings.URL_FORMAT_OVERRIDE)

        for param in (EXPAND_PARAM, FIELDS_PARAM, OMIT_PARAM):
            names.update((param, f"{param}[]"))

        filter_backends = getattr(view, "filter_backends", None)
        if isinstance(filter_backends, (list, tuple)):
            for backend in filter_backends:
                names.update(self._get_param_names(backend, self.FILTER_BACKEND_PARAM_ATTRS))

        pagination_class = getattr(view, "pagination_class", None)
        if isinstance(pagination_class, type):
            names.update(self._get_param_names(pagination_class, self.PAGINATION_PARAM_ATTRS))

        return names

    @staticmethod
    def _get_param_names(source, attrs):
        """Return the query parameter names set on the given attributes of a class."""
        names = (getattr(source, attr, None) for attr in attrs)
        return {name for name in names if isinstance(name, str) and name}

    def get_filterable_fields(self, model_class, view=None):
        """
        Return the names of the fields of the model that may be filtered on.

        For exposed models these are the fields exposed through the API. For
        other models (e.g. a custom view using this backend) these are the
        model fields readable through the view's serializer, or all fields
        of the model if the view has no serializer.
        """
        exposed_fields = headless_registry.get_exposed_fields(model_class)
        if exposed_fields is not None:
            return exposed_fields

        field_names = {field.name for field in model_class._meta.get_fields()}

        serializer_class = getattr(view, "get_serializer_class", lambda: None)()
        if isinstance(serializer_class, type) and issubclass(serializer_class, BaseSerializer):
            serializer = view.get_serializer()
            readable = {field.source for field in serializer.fields.values() if not field.write_only}
            return (readable & field_names) | {model_class._meta.pk.name}

        return field_names

    def resolve_field(self, model_class, path, filterable_fields):
        """
        Resolve a filter path (e.g. "author__name__icontains") to the model
        field it targets and its lookup. Relations are only traversed into
        exposed models, on their exposed fields; the primary key of a related
        model is always allowed. "pk" is accepted as the primary key name.

        Returns:
            A (field, lookup) tuple, where lookup is None if the path has none.

        Raises:
            ParseError: If a field does not exist or may not be filtered on.
        """
        parts = path.split("__")
        # "pk" is an alias for the primary key, as in Django's own lookups
        name = model_class._meta.pk.name if parts[0] == "pk" else parts[0]

        if name not in filterable_fields:
            raise ParseError(detail=f"Field '{parts[0]}' does not exist")

        try:
            field = model_class._meta.get_field(name)
        except FieldDoesNotExist:
            raise ParseError(detail=f"Field '{parts[0]}' does not exist")

        index = 1
        while index < len(parts) and field.is_relation and field.related_model is not None:
            related_model = field.related_model
            name = related_model._meta.pk.name if parts[index] == "pk" else parts[index]
            try:
                next_field = related_model._meta.get_field(name)
            except FieldDoesNotExist:
                # Not a field, so a lookup or transform on the relation (e.g. author__in)
                break

            # The primary key is always filterable: it is the value of the relation itself
            exposed_fields = headless_registry.get_exposed_fields(related_model) or set()
            if name != related_model._meta.pk.name and name not in exposed_fields:
                raise ParseError(detail=f"Field '{'__'.join(parts[: index + 1])}' does not exist")

            field = next_field
            index += 1

        # The remaining parts are lookups and transforms.
        for part in parts[index:]:
            if part in headless_settings.FILTER_DISALLOWED_LOOKUPS:
                raise ParseError(detail=f"The '{part}' lookup is not allowed")

        # The last part of a path is considered its lookup, but it's not required.
        lookup = parts[-1] if index < len(parts) and parts[-1] in field.get_lookups() else None

        return field, lookup

    def crosses_to_many(self, model_class, path):
        """
        Check whether a (validated) filter path traverses a to-many relation,
        such as a many-to-many field or a reverse foreign key.
        """
        model = model_class
        for part in path.split("__"):
            try:
                field = model._meta.get_field(part)
            except FieldDoesNotExist:
                return False
            if field.many_to_many or field.one_to_many:
                return True
            if not field.is_relation or field.related_model is None:
                return False
            model = field.related_model
        return False

    def get_filter_kwargs(self, model_class, query_params, filterable_fields=None, non_filter_fields=None):
        filter_kwargs = {}
        exclude_kwargs = {}

        if filterable_fields is None:
            filterable_fields = self.get_filterable_fields(model_class)

        if non_filter_fields is None:
            non_filter_fields = self.get_non_filter_fields()

        for key, value in query_params.lists():
            if key in non_filter_fields:
                continue
            is_exclude = key.startswith(self.EXCLUDE_SYMBOL)
            # Strip the exclusion symbol for field lookup
            path = key[len(self.EXCLUDE_SYMBOL) :] if is_exclude else key
            # Get the targeted model field and its lookup (if any).
            field, lookup = self.resolve_field(model_class, path, filterable_fields)

            # Some lookups allow multiple values, otherwise
            # the first value is used.
            is_multi = lookup in self.MULTI_VALUE_LOOKUPS
            if is_multi:
                # Multi-value lookups take repeated parameters (e.g. `a=1&a=2`)
                # as well as comma-separated values (e.g. `a=1,2`). Other
                # lookups keep commas, so text like "Hello, world" matches.
                value = flatten([param.split(",") for param in value])
            if lookup == "range" and len(value) != 2:
                raise ParseError(detail=f"The range lookup in '{key}' takes two values.")
            # Depending on the field type we cast the value to
            # its correct type (i.e. number, boolean, etc.).
            if is_multi:
                casted_value = [cast_field_value(v, field) for v in value]
            elif lookup == "isnull":
                fvalue = value[0].strip().lower()
                if not fvalue or fvalue not in self.BOOLEANS:
                    raise ParseError(
                        detail=f"The isnull lookup can only be used with a boolean value ({', '.join(self.BOOLEANS)})."
                    )
                casted_value = fvalue in self.TRUE_VALUES
            else:
                casted_value = cast_field_value(value[0], field)

            self.validate_filter(model_class, path, casted_value, key)

            if is_exclude:
                exclude_kwargs[path] = casted_value
            else:
                filter_kwargs[key] = casted_value

        return filter_kwargs, exclude_kwargs

    def validate_filter(self, model_class, path, value, key):
        """
        Build (without running) a query for a single filter, so an invalid
        filter answers with a message about that query parameter instead of
        failing later, and Django's internal error messages stay internal.

        Raises:
            ParseError: If the filter is invalid.
        """
        try:
            model_class._base_manager.filter(**{path: value})
        except ValidationError as e:
            # Validation messages are written for users (e.g. an invalid date format)
            raise ParseError(detail=f"Invalid value for '{key}': {' '.join(e.messages)}")
        except FieldError:
            raise ParseError(detail=f"Unsupported lookup in '{key}'.")
        except (ValueError, TypeError):
            raise ParseError(detail=f"Invalid value for '{key}'.")

    def cast_field_value(self, value: str, field):
        """
        Cast a string value to the appropriate type based on the field type.
        This is a convenience method that calls the standalone cast_field_value function.
        """
        return cast_field_value(value, field)
