"""
The OpenAPI schema of the generated routes.

The schema is generated with Django REST Framework's own OpenAPI support,
which needs the uritemplate and inflection packages (and PyYAML for YAML
output). Enable the schema route with HEADLESS["SCHEMA"], or generate the
schema as a file with Django REST Framework's generateschema command:

    python manage.py generateschema --generator_class headless.rest.schema.SchemaGenerator
"""

import datetime
import decimal
import types
import typing
import uuid

from django.conf import settings
from django.db import models
from rest_flex_fields import EXPAND_PARAM, FIELDS_PARAM, OMIT_PARAM
from rest_flex_fields.serializers import FlexFieldsSerializerMixin
from rest_framework.authentication import BasicAuthentication, SessionAuthentication, TokenAuthentication
from rest_framework.fields import ReadOnlyField
from rest_framework.permissions import SAFE_METHODS
from rest_framework.renderers import JSONOpenAPIRenderer, OpenAPIRenderer
from rest_framework.schemas import get_schema_view as get_drf_schema_view
from rest_framework.schemas import openapi
from rest_framework.schemas.generators import EndpointEnumerator as BaseEndpointEnumerator
from rest_framework.schemas.openapi import AutoSchema
from rest_framework.settings import api_settings

from ..settings import headless_settings
from .utils import get_authentication_classes, get_permission_classes
from .viewsets import SingletonViewSet

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

try:
    import inflection
    import uritemplate
except ImportError:  # pragma: no cover
    inflection = uritemplate = None


def is_schema_available() -> bool:
    """Check if the packages that OpenAPI schema generation needs are installed."""
    return bool(inflection and uritemplate)


def get_schema_name(model) -> str:
    """
    Return the name of a model in the schema: its app label and class name
    in PascalCase, such as BlogArticle for blog.Article. It names the
    component of the model and prefixes its operation IDs.
    """
    app_name = "".join(part[:1].upper() + part[1:] for part in model._meta.app_label.split("_"))
    return f"{app_name}{model.__name__}"


def get_field_schema(field) -> dict:
    """
    Return the schema of the values of a model field, as they appear in a
    query parameter. A relation takes the type of the primary key it points to.
    """
    while field.is_relation and field.related_model is not None:
        field = field.related_model._meta.pk

    if isinstance(field, models.BooleanField):
        schema = {"type": "boolean"}
    elif isinstance(field, models.IntegerField):
        schema = {"type": "integer"}
    elif isinstance(field, (models.FloatField, models.DecimalField)):
        schema = {"type": "number"}
    # DateTimeField is a DateField, so it comes first
    elif isinstance(field, models.DateTimeField):
        schema = {"type": "string", "format": "date-time"}
    elif isinstance(field, models.DateField):
        schema = {"type": "string", "format": "date"}
    elif isinstance(field, models.TimeField):
        schema = {"type": "string", "format": "time"}
    elif isinstance(field, models.UUIDField):
        schema = {"type": "string", "format": "uuid"}
    else:
        schema = {"type": "string"}

    if field.choices:
        schema["enum"] = [value for value, _ in field.flatchoices]

    return schema


def get_annotation_schema(function) -> dict:
    """
    Return the schema of the return annotation of a function, such as the
    getter of a model property. Without a known annotation, the schema
    allows any value.
    """
    try:
        annotation = typing.get_type_hints(function).get("return")
    except Exception:
        return {}

    return get_type_schema(annotation)


def get_type_schema(annotation) -> dict:
    """Return the schema of a type annotation, or an empty schema for an unknown type."""
    origin = typing.get_origin(annotation)

    if origin in (typing.Union, types.UnionType):
        arguments = [argument for argument in typing.get_args(annotation) if argument is not type(None)]
        schema = get_type_schema(arguments[0]) if len(arguments) == 1 else {}
        if len(arguments) < len(typing.get_args(annotation)):
            schema = {**schema, "nullable": True}
        return schema

    if origin in (list, tuple, set, frozenset):
        arguments = typing.get_args(annotation)
        return {"type": "array", "items": get_type_schema(arguments[0]) if arguments else {}}

    if origin is dict or annotation is dict:
        return {"type": "object"}

    if annotation in (list, tuple, set, frozenset):
        return {"type": "array", "items": {}}

    # bool is an int, and datetime a date, so they come first
    for annotation_type, schema in (
        (bool, {"type": "boolean"}),
        (int, {"type": "integer"}),
        (float, {"type": "number"}),
        # The JSON renderer writes a decimal as a number
        (decimal.Decimal, {"type": "number"}),
        (str, {"type": "string"}),
        (datetime.datetime, {"type": "string", "format": "date-time"}),
        (datetime.date, {"type": "string", "format": "date"}),
        (datetime.time, {"type": "string", "format": "time"}),
        (uuid.UUID, {"type": "string", "format": "uuid"}),
    ):
        if isinstance(annotation, type) and issubclass(annotation, annotation_type):
            return dict(schema)

    return {}


class HeadlessAutoSchema(AutoSchema):
    """
    Describes the generated routes: unique names for the models, a
    description per operation, the filters of LookupFilter, the
    parameters of FlexibleSerializer and the lookup routes.
    """

    def map_field(self, field):
        # A model property of FlexibleSerializer has the type of its return annotation
        if type(field) is ReadOnlyField:
            model = getattr(getattr(getattr(field, "parent", None), "Meta", None), "model", None)
            attribute = getattr(model, field.source, None) if model is not None else None
            if isinstance(attribute, property):
                return get_annotation_schema(attribute.fget)

        return super().map_field(field)

    def get_model(self):
        return getattr(getattr(self.view, "queryset", None), "model", None)

    def get_lookup_field(self):
        """Return the field a lookup route (by_<field>) looks up by, or None on other routes."""
        lookup_actions = getattr(self.view, "lookup_actions", None) or {}
        return lookup_actions.get(getattr(self.view, "action", None))

    def get_component_name(self, serializer):
        # Every generated serializer class has the same name, so the
        # component is named after the model instead.
        model = getattr(getattr(serializer, "Meta", None), "model", None)
        if self.component_name is None and model is not None:
            return get_schema_name(model)

        return super().get_component_name(serializer)

    def get_operation_id_base(self, path, method, action):
        model = self.get_model()
        if self.operation_id_base is None and model is not None:
            name = get_schema_name(model)
            return inflection.pluralize(name) if action == "list" else name

        return super().get_operation_id_base(path, method, action)

    def get_operation_id(self, path, method):
        lookup_field = self.get_lookup_field()
        if lookup_field is None:
            return super().get_operation_id(path, method)

        name = self.get_operation_id_base(path, method, "retrieve")
        field_name = "".join(part[:1].upper() + part[1:] for part in lookup_field.split("_"))
        return f"retrieve{name}By{field_name}"

    def get_tags(self, path, method):
        model = self.get_model()
        if self._tags is None and model is not None:
            return [model._meta.label_lower]

        return super().get_tags(path, method)

    def get_description(self, path, method):
        model = self.get_model()
        if model is None:
            return super().get_description(path, method)

        lookup_field = self.get_lookup_field()
        if lookup_field is not None:
            return f"Retrieve a {model._meta.verbose_name} by its `{lookup_field}`."

        # A singleton is the only object of its model
        name = f"{'the' if isinstance(self.view, SingletonViewSet) else 'a'} {model._meta.verbose_name}"
        descriptions = {
            "list": f"List the {self.get_plural_name(model)}.",
            "retrieve": f"Retrieve {name}.",
            "create": f"Create {name}.",
            "update": f"Replace {name}.",
            "partial_update": f"Change fields of {name}.",
            "destroy": f"Delete {name}.",
        }

        return descriptions.get(getattr(self.view, "action", None)) or super().get_description(path, method)

    @staticmethod
    def get_plural_name(model):
        """The plural of the verbose name, with a real plural where Django only appends an s."""
        name = str(model._meta.verbose_name)
        plural = str(model._meta.verbose_name_plural)

        return inflection.pluralize(name) if plural == f"{name}s" else plural

    def get_path_parameters(self, path, method):
        parameters = super().get_path_parameters(path, method)

        lookup_field = self.get_lookup_field()
        model = self.get_model()
        if model is None:
            return parameters

        for parameter in parameters:
            # The primary key in a detail route has the type of the primary key field
            if lookup_field is None and parameter["name"] == "id":
                parameter["schema"] = get_field_schema(model._meta.pk)

        if lookup_field is not None:
            for parameter in parameters:
                if parameter["name"] == "value":
                    parameter["description"] = f"The `{lookup_field}` of the {model._meta.verbose_name}."
                    parameter["schema"] = get_field_schema(model._meta.get_field(lookup_field))

        return parameters

    def get_operation(self, path, method):
        operation = super().get_operation(path, method)
        operation["parameters"] += self.get_expansion_parameters(path, method)

        return operation

    def get_expansion_parameters(self, path, method):
        """
        The expand, fields and omit parameters of FlexibleSerializer
        (drf-flex-fields). Expanded relations are inline objects instead of
        primary keys, which the schema does not describe.
        """
        if method.upper() != "GET":
            return []

        serializer = self.get_serializer(path, method)
        if not isinstance(serializer, FlexFieldsSerializerMixin):
            return []

        expandable_fields = getattr(serializer, "_expandable_fields", {})
        expandable = ", ".join(f"`{name}`" for name in expandable_fields)
        expand_description = (
            "Relations to include as objects instead of primary keys, separated by commas. "
            "Use a dot to expand deeper, such as `category.parent`, or `*` for all relations."
        )
        if expandable:
            expand_description += f" Expandable: {expandable}."

        expand_parameter = self._get_list_parameter(EXPAND_PARAM, expand_description)
        # The component of each expandable relation, for typed clients
        expand_parameter["x-expandable"] = self.get_expandable_components(expandable_fields)

        return [
            expand_parameter,
            self._get_list_parameter(FIELDS_PARAM, "Fields to include, separated by commas. Others are left out."),
            self._get_list_parameter(OMIT_PARAM, "Fields to leave out, separated by commas."),
        ]

    @staticmethod
    def get_expandable_components(expandable_fields):
        """
        Map each expandable relation to the component of the model it points
        to, and whether it expands to a list of objects.
        """
        components = {}

        for name, value in expandable_fields.items():
            # drf-flex-fields takes a serializer class, or a tuple of the class and its options
            serializer_class, options = value if isinstance(value, tuple) else (value, {})
            model = getattr(getattr(serializer_class, "Meta", None), "model", None)
            if model is not None:
                components[name] = {"component": get_schema_name(model), "many": bool(options.get("many"))}

        return components

    @staticmethod
    def _get_list_parameter(name, description):
        return {
            "name": name,
            "in": "query",
            "required": False,
            "description": description,
            "schema": {"type": "array", "items": {"type": "string"}},
            "style": "form",
            "explode": False,
        }


class EndpointEnumerator(BaseEndpointEnumerator):
    def get_path_from_regex(self, path_regex):
        # The router escapes the dot of a route like blog.article in its pattern
        return super().get_path_from_regex(path_regex).replace("\\.", ".")


class SchemaGenerator(openapi.SchemaGenerator):
    """
    Generates the OpenAPI schema of the generated routes only, not of
    the other views of the project. The title, description and version
    default to HEADLESS["SCHEMA_TITLE"], HEADLESS["SCHEMA_DESCRIPTION"]
    and HEADLESS["SCHEMA_VERSION"].
    """

    endpoint_inspector_cls = EndpointEnumerator

    def __init__(self, title=None, url=None, description=None, patterns=None, urlconf=None, version=None):
        super().__init__(
            title=title or headless_settings.SCHEMA_TITLE,
            url=url,
            description=description or headless_settings.SCHEMA_DESCRIPTION or None,
            patterns=patterns,
            urlconf=urlconf,
            version=version or headless_settings.SCHEMA_VERSION,
        )

    def has_view_permissions(self, path, method, view):
        from .authentication import SecretKey

        # Only the generated routes are part of the schema
        if getattr(view, "headless_model", None) is None:
            return False

        # The read-only secret key is checked when a request is authenticated,
        # which the requests of the other methods are not: they reuse the
        # authentication of the request for the schema.
        auth = getattr(getattr(view, "request", None), "auth", None)
        if isinstance(auth, SecretKey) and auth.read_only and method.upper() not in SAFE_METHODS:
            return False

        return super().has_view_permissions(path, method, view)

    def get_schema(self, request=None, public=False):
        schema = super().get_schema(request, public)

        security_schemes = get_security_schemes()
        if security_schemes:
            schema.setdefault("components", {})["securitySchemes"] = security_schemes
            # Any one of the schemes grants access
            schema["security"] = [{name: []} for name in security_schemes]

        return schema


def get_security_schemes() -> dict:
    """
    Describe the authentication classes of the generated routes that have
    an OpenAPI equivalent: secret key, token, basic and session
    authentication. Other classes are left out of the schema.
    """
    from .authentication import SecretKeyAuthentication

    schemes = {}

    for auth_class in get_authentication_classes():
        if not isinstance(auth_class, type):
            continue

        if issubclass(auth_class, SecretKeyAuthentication):
            schemes["secretKey"] = {
                "type": "apiKey",
                "in": "header",
                "name": headless_settings.AUTH_SECRET_KEY_HEADER,
            }
        elif issubclass(auth_class, TokenAuthentication):
            schemes["token"] = {
                "type": "apiKey",
                "in": "header",
                "name": "Authorization",
                "description": f"The word `{auth_class.keyword}`, a space and the token.",
            }
        elif issubclass(auth_class, BasicAuthentication):
            schemes["basic"] = {"type": "http", "scheme": "basic"}
        elif issubclass(auth_class, SessionAuthentication):
            schemes["session"] = {"type": "apiKey", "in": "cookie", "name": settings.SESSION_COOKIE_NAME}

    return schemes


class JSONSchemaRenderer(JSONOpenAPIRenderer):
    """Renders the schema as JSON, for the application/json media type and ?format=json."""

    media_type = "application/json"
    format = "json"


def get_schema_view():
    """
    Return the view of the schema route. It requires what the generated
    routes require, and shows the operations the requester may perform.
    JSON is the default format; YAML (?format=openapi) needs PyYAML.
    """
    renderer_classes = [JSONSchemaRenderer]
    if yaml is not None:
        renderer_classes.append(OpenAPIRenderer)

    return get_drf_schema_view(
        generator_class=SchemaGenerator,
        renderer_classes=renderer_classes,
        authentication_classes=get_authentication_classes(),
        permission_classes=get_permission_classes(),
    )


def uses_default_schema_class() -> bool:
    """
    Check if the project leaves DRF's schema class at its default, so the
    generated routes can use HeadlessAutoSchema. A project that configures
    another class (such as the one of drf-spectacular) keeps it.
    """
    return api_settings.DEFAULT_SCHEMA_CLASS is AutoSchema
