from django.core.exceptions import FieldDoesNotExist
from rest_framework.exceptions import ParseError
from rest_framework.filters import BaseFilterBackend

from headless.settings import headless_settings
from headless.utils import flatten
from .casting import cast_field_value
from .lookups import get_field_lookups


class LookupFilter(BaseFilterBackend):
    """
    A permissive filter backend that basically allows every supported lookup
    for a given field. Automatically handles multi-value lookups and booleans.
    Also supports exclusion.
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
            filter_kwargs, exclude_kwargs = self.get_filter_kwargs(
                model_class=view.queryset.model,
                query_params=request.query_params,
            )
            return queryset.filter(**filter_kwargs).exclude(**exclude_kwargs).distinct()
        except Exception as e:
            print(e)
            raise ParseError(detail="Invalid filter parameters")

    def get_filter_kwargs(self, model_class, query_params):
        filter_kwargs = {}
        exclude_kwargs = {}

        field_lookups = get_field_lookups(model_class=model_class)

        for key, value in query_params.lists():
            if key in self.NON_FILTER_FIELDS:
                continue
            # By default Django supports repeated multi-values (e.g. `a=1&a=2`)
            # but we allow for comma-seperated multi-values as well (e.g. `a=1,2`).
            value = flatten([param.split(",") for param in value])
            is_exclude = key.startswith(self.EXCLUDE_SYMBOL)
            # The first part of a key is considered the field name
            # Strip the exclusion symbol for field lookup
            field_name = key.split("__")[0]
            if is_exclude:
                field_name = field_name[len(self.EXCLUDE_SYMBOL) :]
            # Get the model field.
            try:
                field = model_class._meta.get_field(field_name)
            except FieldDoesNotExist:
                raise ParseError(detail=f"Field '{field_name}' does not exist")
            # Get the allowed lookups for this field.
            lookups = field_lookups.get(field_name, [])
            try:
                # The last part of a key is considered its lookup
                # but it's not required.
                lookup = key.split("__")[-1]
                if lookup not in lookups:
                    lookup = None
            except IndexError:
                lookup = None

            # Some lookups allow multiple values, otherwise
            # the first value is used.
            is_multi = lookup in self.MULTI_VALUE_LOOKUPS
            # Depending on the field type we cast the value to
            # its correct type (i.e. number, boolean, etc.).
            if is_multi:
                casted_value = [cast_field_value(v, field) for v in value]
            elif lookup == "isnull":
                fvalue = value[0]
                if not fvalue or fvalue not in self.BOOLEANS:
                    raise ParseError(
                        detail=f"The isnull lookup can only be used with a boolean value ({', '.join(self.BOOLEANS)})."
                    )
                casted_value = fvalue in self.TRUE_VALUES
            else:
                casted_value = cast_field_value(value[0], field)

            if is_exclude:
                # Strip the exclusion symbol from the key for Django's exclude method
                exclude_key = key[len(self.EXCLUDE_SYMBOL) :] if key.startswith(self.EXCLUDE_SYMBOL) else key
                exclude_kwargs[exclude_key] = casted_value
            else:
                filter_kwargs[key] = casted_value

        return filter_kwargs, exclude_kwargs

    def cast_field_value(self, value: str, field):
        """
        Cast a string value to the appropriate type based on the field type.
        This is a convenience method that calls the standalone cast_field_value function.
        """
        return cast_field_value(value, field)
