"""
Tests for the OpenAPI schema of the generated routes: the schema of the
exposed test models, and the schema route.
"""

import json
import uuid

from django.db import models
from django.test import SimpleTestCase, override_settings
from django.urls import clear_url_caches
from rest_framework.test import APIRequestFactory

import headless.rest.urls as headless_urls
from headless import expose
from headless.registry import headless_registry
from headless.rest.builder import RestBuilder
from headless.rest.routers import rest_router, singleton_urls
from headless.rest.schema import (
    SchemaGenerator,
    get_field_schema,
    get_schema_name,
    get_schema_view,
    get_security_schemes,
)

HEADLESS_SETTINGS = {
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
    "DEFAULT_SERIALIZER_CLASS": "headless.rest.serializers.FlexibleSerializer",
    "DEFAULT_PAGINATION_CLASS": "headless.rest.pagination.PageNumberPagination",
    "PAGE_SIZE": 10,
}


@expose()
class DocTag(models.Model):
    name = models.CharField(max_length=100)

    class Meta:
        app_label = "headless_rest"


@expose()
class DocArticle(models.Model):
    STATUSES = [("draft", "Draft"), ("live", "Live")]

    title = models.CharField(max_length=100)
    status = models.CharField(max_length=10, choices=STATUSES, default="draft")
    views = models.IntegerField(default=0)
    rating = models.FloatField(null=True)
    published = models.BooleanField(default=False)
    created = models.DateTimeField(null=True)
    day = models.DateField(null=True)
    tags = models.ManyToManyField(DocTag)

    class Meta:
        app_label = "headless_rest"

    @property
    def shout(self):
        return self.title.upper()


@expose(lookup_fields=["slug", "uid"])
class DocPage(models.Model):
    slug = models.CharField(max_length=100, unique=True)
    uid = models.UUIDField(unique=True, default=uuid.uuid4)

    class Meta:
        app_label = "headless_rest"


@expose(singleton=True)
class DocSettings(models.Model):
    site_name = models.CharField(max_length=100, default="")

    class Meta:
        app_label = "headless_rest"
        verbose_name = "documentation setting"


@expose()
class DocCategory(models.Model):
    name = models.CharField(max_length=100)

    class Meta:
        app_label = "headless_rest"


@expose(read_only=True)
class DocNote(models.Model):
    text = models.CharField(max_length=100)

    class Meta:
        app_label = "headless_rest"


MODELS = (DocTag, DocArticle, DocPage, DocSettings, DocNote, DocCategory)
LABELS = tuple(model._meta.label_lower for model in MODELS)


def rebuild_urlpatterns():
    if hasattr(rest_router, "_urls"):
        del rest_router._urls
    headless_urls.urlpatterns = rest_router.urls + singleton_urls
    clear_url_caches()


def remove_routes():
    rest_router.registry = [entry for entry in rest_router.registry if entry[0] not in LABELS]
    singleton_urls[:] = [url for url in singleton_urls if str(url.pattern) not in LABELS]
    rebuild_urlpatterns()


def setUpModule():
    # Another module may have built routes for these models with other settings
    remove_routes()

    with override_settings(HEADLESS=HEADLESS_SETTINGS):
        builder = RestBuilder(silent=True)
        builder._models = [config for config in builder._models if config["model"] in MODELS]
        builder.build()
    rebuild_urlpatterns()


def tearDownModule():
    remove_routes()
    for label in LABELS:
        headless_registry._models.pop(label, None)


def generate_schema(**settings_overrides):
    with override_settings(HEADLESS={**HEADLESS_SETTINGS, **settings_overrides}):
        generator = SchemaGenerator(urlconf="headless.rest.urls")
        return generator.get_schema(request=None, public=True)


class SchemaTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.schema = generate_schema()

    def operation(self, path, method):
        return self.schema["paths"][path][method]

    def parameters(self, path, method="get"):
        return {parameter["name"]: parameter for parameter in self.operation(path, method)["parameters"]}

    def test_is_valid_openapi(self):
        from openapi_spec_validator import validate

        validate(json.loads(json.dumps(self.schema)))

    def test_info_uses_the_schema_settings(self):
        self.assertEqual(self.schema["info"], {"title": "API", "version": "1.0.0"})

        schema = generate_schema(SCHEMA_TITLE="Blog", SCHEMA_DESCRIPTION="The blog.", SCHEMA_VERSION="2.1")
        self.assertEqual(schema["info"], {"title": "Blog", "description": "The blog.", "version": "2.1"})

    def test_only_generated_routes(self):
        self.assertEqual(
            sorted(self.schema["paths"]),
            [
                "/headless_rest.docarticle",
                "/headless_rest.docarticle/{id}",
                "/headless_rest.doccategory",
                "/headless_rest.doccategory/{id}",
                "/headless_rest.docnote",
                "/headless_rest.docnote/{id}",
                "/headless_rest.docpage",
                "/headless_rest.docpage/by_slug/{value}",
                "/headless_rest.docpage/by_uid/{value}",
                "/headless_rest.docpage/{id}",
                "/headless_rest.docsettings",
                "/headless_rest.doctag",
                "/headless_rest.doctag/{id}",
            ],
        )

    def test_methods(self):
        self.assertEqual(sorted(self.schema["paths"]["/headless_rest.docarticle"]), ["get", "post"])
        self.assertEqual(
            sorted(self.schema["paths"]["/headless_rest.docarticle/{id}"]), ["delete", "get", "patch", "put"]
        )
        # Read-only models and lookup routes are read only
        self.assertEqual(sorted(self.schema["paths"]["/headless_rest.docnote"]), ["get"])
        self.assertEqual(sorted(self.schema["paths"]["/headless_rest.docnote/{id}"]), ["get"])
        self.assertEqual(sorted(self.schema["paths"]["/headless_rest.docpage/by_slug/{value}"]), ["get"])
        # A singleton has no identifier and no list
        self.assertEqual(sorted(self.schema["paths"]["/headless_rest.docsettings"]), ["get", "patch", "put"])

    def test_operation_ids_are_unique(self):
        ids = [operation["operationId"] for path in self.schema["paths"].values() for operation in path.values()]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertIn("listHeadlessRestDocArticles", ids)
        self.assertIn("listHeadlessRestDocCategories", ids)
        self.assertIn("retrieveHeadlessRestDocArticle", ids)
        self.assertIn("partialUpdateHeadlessRestDocSettings", ids)
        self.assertIn("retrieveHeadlessRestDocPageBySlug", ids)
        self.assertIn("retrieveHeadlessRestDocPageByUid", ids)

    def test_components_are_named_after_the_models(self):
        self.assertEqual(
            sorted(self.schema["components"]["schemas"]),
            [
                "HeadlessRestDocArticle",
                "HeadlessRestDocCategory",
                "HeadlessRestDocNote",
                "HeadlessRestDocPage",
                "HeadlessRestDocSettings",
                "HeadlessRestDocTag",
            ],
        )
        article = self.schema["components"]["schemas"]["HeadlessRestDocArticle"]
        self.assertEqual(article["properties"]["views"]["type"], "integer")
        self.assertEqual(article["properties"]["tags"]["items"]["type"], "integer")
        # Model properties are read only fields
        self.assertTrue(article["properties"]["shout"]["readOnly"])

    def test_tags_and_descriptions(self):
        list_operation = self.operation("/headless_rest.docarticle", "get")
        self.assertEqual(list_operation["tags"], ["headless_rest.docarticle"])
        self.assertEqual(list_operation["description"], "List the doc articles.")
        self.assertEqual(
            self.operation("/headless_rest.docarticle/{id}", "get")["description"], "Retrieve a doc article."
        )
        self.assertEqual(self.operation("/headless_rest.docarticle", "post")["description"], "Create a doc article.")
        self.assertEqual(
            self.operation("/headless_rest.docarticle/{id}", "delete")["description"], "Delete a doc article."
        )
        self.assertEqual(
            self.operation("/headless_rest.docsettings", "get")["description"], "Retrieve the documentation setting."
        )
        self.assertEqual(
            self.operation("/headless_rest.docpage/by_slug/{value}", "get")["description"],
            "Retrieve a doc page by its `slug`.",
        )

    def test_list_response_is_the_pagination_envelope(self):
        response = self.operation("/headless_rest.docarticle", "get")["responses"]["200"]
        envelope = response["content"]["application/json"]["schema"]

        self.assertEqual(sorted(envelope["properties"]), ["data", "pagination"])
        self.assertEqual(
            envelope["properties"]["data"],
            {"type": "array", "items": {"$ref": "#/components/schemas/HeadlessRestDocArticle"}},
        )
        self.assertEqual(
            sorted(envelope["properties"]["pagination"]["properties"]),
            ["count", "current", "limit", "links", "pages"],
        )
        self.assertTrue(envelope["properties"]["pagination"]["properties"]["links"]["properties"]["next"]["nullable"])

    def test_pagination_parameters(self):
        parameters = self.parameters("/headless_rest.docarticle")
        self.assertEqual(parameters["page"]["schema"]["type"], "integer")
        self.assertEqual(parameters["limit"]["schema"]["type"], "integer")
        self.assertNotIn("page", self.parameters("/headless_rest.docarticle/{id}"))

    def test_filter_parameters_on_the_list_route(self):
        parameters = self.parameters("/headless_rest.docarticle")

        self.assertEqual(parameters["title"]["schema"], {"type": "string"})
        self.assertEqual(parameters["views"]["schema"], {"type": "integer"})
        self.assertEqual(parameters["rating"]["schema"], {"type": "number"})
        self.assertEqual(parameters["published"]["schema"], {"type": "boolean"})
        self.assertEqual(parameters["created"]["schema"], {"type": "string", "format": "date-time"})
        self.assertEqual(parameters["day"]["schema"], {"type": "string", "format": "date"})
        self.assertEqual(parameters["status"]["schema"], {"type": "string", "enum": ["draft", "live"]})
        # A relation filters by the primary key of the related object
        self.assertEqual(parameters["tags"]["schema"], {"type": "integer"})
        self.assertIn("`views__in`", parameters["views"]["description"])
        self.assertIn("`~`", parameters["views"]["description"])

    def test_filters_only_on_the_list_route(self):
        for path in ("/headless_rest.docarticle/{id}", "/headless_rest.docpage/by_slug/{value}"):
            self.assertNotIn("title", self.parameters(path))

    def test_expansion_parameters_of_the_flexible_serializer(self):
        for path in ("/headless_rest.docarticle", "/headless_rest.docarticle/{id}", "/headless_rest.docsettings"):
            parameters = self.parameters(path)
            self.assertEqual(
                {name for name in parameters if name in ("expand", "fields", "omit")}, {"expand", "fields", "omit"}
            )
            self.assertEqual(parameters["expand"]["schema"], {"type": "array", "items": {"type": "string"}})
            self.assertFalse(parameters["expand"]["explode"])

        self.assertIn("Expandable: `tags`.", self.parameters("/headless_rest.docarticle")["expand"]["description"])
        # Only reads take them
        post = {parameter["name"] for parameter in self.operation("/headless_rest.docarticle", "post")["parameters"]}
        self.assertNotIn("expand", post)

    def test_no_expansion_parameters_for_a_plain_serializer(self):
        from django.urls import path
        from headless.rest.builder.viewset import get_view_set

        with override_settings(
            HEADLESS={**HEADLESS_SETTINGS, "DEFAULT_SERIALIZER_CLASS": "rest_framework.serializers.ModelSerializer"}
        ):
            view_set = get_view_set(headless_registry.get_model("headless_rest.doctag"), {}, {})
            generator = SchemaGenerator(patterns=[path("tags", view_set.as_view({"get": "list"}))])
            schema = generator.get_schema(request=None, public=True)

        names = {parameter["name"] for parameter in schema["paths"]["/tags"]["get"]["parameters"]}
        self.assertIn("name", names)
        self.assertNotIn("expand", names)

    def test_lookup_route(self):
        operation = self.operation("/headless_rest.docpage/by_uid/{value}", "get")
        parameter = {p["name"]: p for p in operation["parameters"]}["value"]

        self.assertEqual(parameter["in"], "path")
        self.assertEqual(parameter["schema"], {"type": "string", "format": "uuid"})
        self.assertEqual(parameter["description"], "The `uid` of the doc page.")
        self.assertEqual(
            operation["responses"]["200"]["content"]["application/json"]["schema"],
            {"$ref": "#/components/schemas/HeadlessRestDocPage"},
        )

    def test_singleton_responses_are_single_objects(self):
        schema = self.operation("/headless_rest.docsettings", "get")["responses"]["200"]["content"]["application/json"]
        self.assertEqual(schema["schema"], {"$ref": "#/components/schemas/HeadlessRestDocSettings"})

    def test_no_security_without_authentication_classes(self):
        schema = generate_schema(DEFAULT_AUTHENTICATION_CLASSES=[])
        self.assertNotIn("security", schema)
        self.assertNotIn("securitySchemes", schema["components"])


class SecuritySchemesTests(SimpleTestCase):
    def schemes(self, *classes):
        with override_settings(HEADLESS={"DEFAULT_AUTHENTICATION_CLASSES": list(classes)}):
            return get_security_schemes()

    def test_secret_key(self):
        schemes = self.schemes("headless.rest.authentication.SecretKeyAuthentication")
        self.assertEqual(schemes["secretKey"], {"type": "apiKey", "in": "header", "name": "X-Secret-Key"})

    def test_secret_key_header(self):
        with override_settings(
            HEADLESS={
                "DEFAULT_AUTHENTICATION_CLASSES": ["headless.rest.authentication.SecretKeyAuthentication"],
                "AUTH_SECRET_KEY_HEADER": "X-Key",
            }
        ):
            self.assertEqual(get_security_schemes()["secretKey"]["name"], "X-Key")

    def test_other_classes(self):
        schemes = self.schemes(
            "rest_framework.authentication.BasicAuthentication",
            "rest_framework.authentication.TokenAuthentication",
            "rest_framework.authentication.SessionAuthentication",
        )

        self.assertEqual(schemes["basic"], {"type": "http", "scheme": "basic"})
        self.assertEqual(schemes["token"]["name"], "Authorization")
        self.assertIn("Token", schemes["token"]["description"])
        self.assertEqual(schemes["session"], {"type": "apiKey", "in": "cookie", "name": "sessionid"})

    def test_unknown_classes_are_left_out(self):
        from rest_framework.authentication import BaseAuthentication

        class CustomAuthentication(BaseAuthentication):
            pass

        self.assertEqual(self.schemes(CustomAuthentication), {})

    def test_schema_security_requirements(self):
        with override_settings(
            HEADLESS={
                **HEADLESS_SETTINGS,
                "DEFAULT_AUTHENTICATION_CLASSES": [
                    "headless.rest.authentication.SecretKeyAuthentication",
                    "rest_framework.authentication.BasicAuthentication",
                ],
            }
        ):
            schema = SchemaGenerator(urlconf="headless.rest.urls").get_schema(request=None, public=True)

        self.assertEqual(sorted(schema["components"]["securitySchemes"]), ["basic", "secretKey"])
        self.assertEqual(schema["security"], [{"secretKey": []}, {"basic": []}])


class SchemaHelpersTests(SimpleTestCase):
    def test_schema_name(self):
        self.assertEqual(get_schema_name(DocArticle), "HeadlessRestDocArticle")

    def test_field_schemas(self):
        self.assertEqual(get_field_schema(models.TextField()), {"type": "string"})
        self.assertEqual(get_field_schema(models.DecimalField(max_digits=5, decimal_places=2)), {"type": "number"})
        self.assertEqual(get_field_schema(models.TimeField()), {"type": "string", "format": "time"})
        self.assertEqual(get_field_schema(DocPage._meta.get_field("uid")), {"type": "string", "format": "uuid"})
        # Auto primary keys are integers
        self.assertEqual(get_field_schema(DocPage._meta.pk), {"type": "integer"})


class SchemaViewTests(SimpleTestCase):
    def get(self, path="/schema", **settings_overrides):
        with override_settings(HEADLESS={**HEADLESS_SETTINGS, **settings_overrides}):
            view = get_schema_view()
            response = view(APIRequestFactory().get(path))
            response.render()
            return response

    def test_serves_json(self):
        response = self.get()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/json")
        self.assertIn("/headless_rest.docarticle", json.loads(response.content)["paths"])

    def test_serves_yaml(self):
        response = self.get("/schema?format=openapi")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"openapi: 3.0.2", response.content)

    def test_requires_what_the_generated_routes_require(self):
        # The default permission class requires a staff user
        response = self.get(DEFAULT_PERMISSION_CLASSES=["rest_framework.permissions.IsAdminUser"])
        self.assertIn(response.status_code, (401, 403))

    def test_shows_the_operations_the_requester_may_perform(self):
        from unittest.mock import patch
        from rest_framework.permissions import IsAuthenticatedOrReadOnly

        view_set = next(
            view_set for prefix, view_set, _ in rest_router.registry if prefix == "headless_rest.docarticle"
        )

        with patch.object(view_set, "permission_classes", [IsAuthenticatedOrReadOnly]):
            response = self.get()

        paths = json.loads(response.content)["paths"]
        self.assertEqual(sorted(paths["/headless_rest.docarticle"]), ["get"])
        self.assertEqual(sorted(paths["/headless_rest.docarticle/{id}"]), ["get"])


class SchemaRouteTests(SimpleTestCase):
    def names(self):
        return [getattr(pattern, "name", None) for pattern in headless_urls.get_urlpatterns()]

    def test_schema_route_is_opt_in(self):
        self.assertNotIn("headless-schema", self.names())

        with override_settings(HEADLESS={"SCHEMA": True}):
            patterns = headless_urls.get_urlpatterns()
            self.assertIn("headless-schema", [getattr(pattern, "name", None) for pattern in patterns])
            self.assertIn("schema", [str(pattern.pattern) for pattern in patterns])

        # The routes themselves are not changed by building them again
        self.assertNotIn("headless-schema", self.names())
