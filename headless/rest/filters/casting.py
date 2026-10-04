from decimal import Decimal, InvalidOperation

from django.db import models
from rest_framework.exceptions import ParseError

from headless.settings import headless_settings


def cast_field_value(value: str, field):
    """
    Cast a string value to the appropriate type based on the field type.

    Strip the value and lowercase it only for comparison purposes. The
    original (stripped) value is returned for text fields, so
    case-sensitive lookups like `exact` keep working.

    Args:
        value: String value to cast
        field: Django model field

    Returns:
        Casted value of appropriate type

    Raises:
        ParseError: If value cannot be cast to the expected type
    """
    value = value.strip()
    lowered = value.lower()

    if isinstance(field, models.BooleanField):
        if lowered in headless_settings.FILTER_TRUE_VALUES:
            return True
        if lowered in headless_settings.FILTER_FALSE_VALUES:
            return False
        if getattr(field, "null", False) and lowered in headless_settings.FILTER_NULL_VALUES:
            return None
        else:
            if getattr(field, "null", False):
                raise ParseError(
                    detail=f"Nullable boolean fields expect a boolean or none lookup value ({', '.join(headless_settings.FILTER_TRUE_VALUES + headless_settings.FILTER_FALSE_VALUES + headless_settings.FILTER_NULL_VALUES)})."
                )

            raise ParseError(
                detail=f"Boolean fields expect a boolean lookup value ({', '.join(headless_settings.FILTER_TRUE_VALUES + headless_settings.FILTER_FALSE_VALUES)})."
            )

    if isinstance(field, models.IntegerField):
        try:
            return int(value)
        except ValueError:
            raise ParseError(detail=f"Invalid integer value: {value}")

    if isinstance(field, models.DecimalField):
        try:
            return Decimal(value)
        except (ValueError, InvalidOperation):
            raise ParseError(detail=f"Invalid decimal value: {value}")

    if isinstance(field, models.FloatField):
        try:
            return float(value)
        except ValueError:
            raise ParseError(detail=f"Invalid float value: {value}")

    return value
