from django.core.exceptions import FieldDoesNotExist, FieldError, ValidationError
from rest_framework.exceptions import ParseError
from rest_framework.filters import BaseFilterBackend
from rest_framework.serializers import BaseSerializer

from headless.registry import headless_registry
from headless.settings import headless_settings
from headless.utils import flatten
from .casting import cast_field_value


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

    TRUE_VALUES = headless_settings.FILTER_TRUE_VALUES

    FALSE_VALUES = headless_settings.FILTER_FALSE_VALUES

    BOOLEANS = TRUE_VALUES + FALSE_VALUES

    NULL_VALUES = headless_settings.FILTER_NULL_VALUES

    EXCLUDE_SYMBOL = headless_settings.FILTER_EXCLUSION_SYMBOL

    NON_FILTER_FIELDS = headless_settings.NON_FILTER_FIELDS

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
        exposed models, on their exposed fields.

        Returns:
            A (field, lookup) tuple, where lookup is None if the path has none.

        Raises:
            ParseError: If a field does not exist or may not be filtered on.
        """
        parts = path.split("__")

        if parts[0] not in filterable_fields:
            raise ParseError(detail=f"Field '{parts[0]}' does not exist")

        try:
            field = model_class._meta.get_field(parts[0])
        except FieldDoesNotExist:
            raise ParseError(detail=f"Field '{parts[0]}' does not exist")

        index = 1
        while index < len(parts) and field.is_relation and field.related_model is not None:
            related_model = field.related_model
            try:
                next_field = related_model._meta.get_field(parts[index])
            except FieldDoesNotExist:
                # Not a field, so a lookup or transform on the relation (e.g. author__in)
                break

            exposed_fields = headless_registry.get_exposed_fields(related_model)
            if exposed_fields is None or parts[index] not in exposed_fields:
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

    def get_filter_kwargs(self, model_class, query_params, filterable_fields=None):
        filter_kwargs = {}
        exclude_kwargs = {}

        if filterable_fields is None:
            filterable_fields = self.get_filterable_fields(model_class)

        for key, value in query_params.lists():
            if key in self.NON_FILTER_FIELDS:
                continue
            # By default Django supports repeated multi-values (e.g. `a=1&a=2`)
            # but we allow for comma-seperated multi-values as well (e.g. `a=1,2`).
            value = flatten([param.split(",") for param in value])
            is_exclude = key.startswith(self.EXCLUDE_SYMBOL)
            # Strip the exclusion symbol for field lookup
            path = key[len(self.EXCLUDE_SYMBOL) :] if is_exclude else key
            # Get the targeted model field and its lookup (if any).
            field, lookup = self.resolve_field(model_class, path, filterable_fields)

            # Some lookups allow multiple values, otherwise
            # the first value is used.
            is_multi = lookup in self.MULTI_VALUE_LOOKUPS
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
