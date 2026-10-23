"""
End-to-end tests for the generated REST API.

These tests build the real URL wiring (as RestBuilder does at app ready) for
exposed test models, and exercise the generated endpoints through the test
client: CRUD, relations, filtering, pagination and singletons.
"""

import uuid

from django.db import connection, models
from django.test import TransactionTestCase, override_settings
from django.urls import clear_url_caches
from rest_framework.permissions import BasePermission
from rest_framework.test import APIClient, APIRequestFactory

import headless.rest.urls as headless_urls
from headless import expose
from headless.registry import headless_registry
from headless.rest.builder import RestBuilder
from headless.rest.builder.viewset import get_view_set
from headless.rest.routers import rest_router, singleton_urls


@expose()
class Category(models.Model):
    name = models.CharField(max_length=100)

    class Meta:
        app_label = "e2e_blog"


@expose()
class Article(models.Model):
    title = models.CharField(max_length=200)
    published = models.BooleanField(default=False)
    views = models.IntegerField(default=0)
    category = models.ForeignKey(
        Category,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="articles",
    )

    class Meta:
        app_label = "e2e_blog"


@expose(singleton=True)
class SiteConfig(models.Model):
    site_name = models.CharField(max_length=100, default="")
    maintenance_mode = models.BooleanField(default=False)

    class Meta:
        app_label = "e2e_config"


@expose(read_only=True)
class DraftNote(models.Model):
    title = models.CharField(max_length=100)

    class Meta:
        app_label = "e2e_blog"


@expose(exclude=["secret"])
class ApiKey(models.Model):
    name = models.CharField(max_length=100)
    secret = models.CharField(max_length=100, default="")

    class Meta:
        app_label = "e2e_blog"


@expose(lookup_fields=["slug", "uid"])
class Page(models.Model):
    slug = models.CharField(max_length=100, unique=True)
    uid = models.UUIDField(unique=True, default=uuid.uuid4)
    title = models.CharField(max_length=100)
    published = models.BooleanField(default=True)
    category = models.ForeignKey(Category, null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        app_label = "e2e_blog"


class DenyRetrieve(BasePermission):
    """Denies retrieves, recording the action and lookup field it saw."""

    seen = []

    def has_permission(self, request, view):
        self.seen.append((view.action, getattr(view, "lookup_by", None)))
        return view.action != "retrieve"


E2E_REGISTRY_PREFIXES = (
    "e2e_blog.article",
    "e2e_blog.category",
    "e2e_blog.draftnote",
    "e2e_blog.apikey",
    "e2e_blog.page",
)
MODEL_LABELS = E2E_REGISTRY_PREFIXES + ("e2e_config.siteconfig",)


def rebuild_urlpatterns():
    """Recompute the url patterns and clear Django's resolver caches."""
    if hasattr(rest_router, "_urls"):
        del rest_router._urls
    headless_urls.urlpatterns = rest_router.urls + singleton_urls
    clear_url_caches()


def setUpModule():
    # Build the routes for the exposed models, mirroring what happens at
    # app ready in a real project. Configure pagination and filtering
    # through the HEADLESS-scoped DRF settings, exercising the scoped
    # overrides end to end.
    with override_settings(
        HEADLESS={
            # The suite tests the public surface; generated routes require
            # authentication by default
            "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
            "DEFAULT_FILTER_BACKENDS": ["headless.rest.filters.LookupFilter"],
            "DEFAULT_PAGINATION_CLASS": "headless.rest.pagination.PageNumberPagination",
            "PAGE_SIZE": 2,
        }
    ):
        RestBuilder(silent=True).build()

    rebuild_urlpatterns()


def tearDownModule():
    # Unregister the e2e routes so other test modules run against a clean slate.
    rest_router.registry = [entry for entry in rest_router.registry if entry[0] not in E2E_REGISTRY_PREFIXES]
    singleton_urls.clear()
    for label in MODEL_LABELS:
        headless_registry._models.pop(label, None)
    rebuild_urlpatterns()


class EndToEndApiTests(TransactionTestCase):
    """Exercises the generated endpoints through the URL resolver"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        with connection.schema_editor() as editor:
            editor.create_model(Category)
            editor.create_model(Article)
            editor.create_model(SiteConfig)
            editor.create_model(DraftNote)
            editor.create_model(ApiKey)
            editor.create_model(Page)

    @classmethod
    def tearDownClass(cls):
        with connection.schema_editor() as editor:
            editor.delete_model(Page)
            editor.delete_model(ApiKey)
            editor.delete_model(DraftNote)
            editor.delete_model(SiteConfig)
            editor.delete_model(Article)
            editor.delete_model(Category)
        super().tearDownClass()

    def setUp(self):
        self.client = APIClient()

    def tearDown(self):
        # The tables are not known to the test flush; clean them up explicitly.
        Page.objects.all().delete()
        Article.objects.all().delete()
        Category.objects.all().delete()
        SiteConfig.objects.all().delete()
        DraftNote.objects.all().delete()
        ApiKey.objects.all().delete()

    def test_crud_flow(self):
        """Test create, list, detail, update and delete on a generated route"""
        # Create
        response = self.client.post("/e2e_blog.article", {"title": "First post", "published": True, "views": 10})
        self.assertEqual(response.status_code, 201)
        article_id = response.data["id"]

        # List
        response = self.client.get("/e2e_blog.article")
        self.assertEqual(response.status_code, 200)

        # Detail
        response = self.client.get(f"/e2e_blog.article/{article_id}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["title"], "First post")

        # Partial update
        response = self.client.patch(f"/e2e_blog.article/{article_id}", {"views": 20})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["views"], 20)

        # Delete
        response = self.client.delete(f"/e2e_blog.article/{article_id}")
        self.assertEqual(response.status_code, 204)

        # Detail after delete
        response = self.client.get(f"/e2e_blog.article/{article_id}")
        self.assertEqual(response.status_code, 404)

    def test_relations(self):
        """Test that related exposed models are serialized by primary key"""
        category = Category.objects.create(name="News")

        response = self.client.post("/e2e_blog.article", {"title": "Hello", "category": category.id})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["category"], category.id)

    def test_filtering(self):
        """Test the LookupFilter backend through a generated list route"""
        a1 = Article.objects.create(title="Hello World", published=True, views=10)
        a2 = Article.objects.create(title="Django Tips", published=False, views=5)

        def list_ids(**params):
            response = self.client.get("/e2e_blog.article", params)
            self.assertEqual(response.status_code, 200)
            return sorted(article["id"] for article in response.data["data"])

        # Boolean filter
        self.assertEqual(list_ids(published="true"), [a1.id])

        # Numeric lookup
        self.assertEqual(list_ids(views__gte="6"), [a1.id])

        # Exclusion
        self.assertEqual(list_ids(**{"~published": "true"}), [a2.id])

        # Case-sensitive text filtering (values are not lowercased)
        self.assertEqual(list_ids(title="Hello World"), [a1.id])
        self.assertEqual(list_ids(title="hello world"), [])

        # Multi-value lookup
        self.assertEqual(list_ids(id__in=f"{a1.id},{a2.id}"), sorted([a1.id, a2.id]))

        # Unknown field
        response = self.client.get("/e2e_blog.article", {"bogus": "1"})
        self.assertEqual(response.status_code, 400)

    def test_pagination_envelope(self):
        """Test the pagination envelope on a generated list route"""
        ids = [Article.objects.create(title=f"Post {i}").id for i in range(3)]

        response = self.client.get("/e2e_blog.article", {"limit": "2"})
        self.assertEqual(response.status_code, 200)

        pagination = response.data["pagination"]
        self.assertEqual(pagination["count"], 3)
        self.assertEqual(pagination["pages"], 2)
        self.assertEqual(pagination["current"], 1)
        self.assertEqual(pagination["limit"], 2)

        # Lists are ordered by pk, so pages are deterministic
        self.assertEqual([article["id"] for article in response.data["data"]], sorted(ids)[:2])

        # The next link points at the second page
        next_url = pagination["links"]["next"]
        self.assertIsNotNone(next_url)

        response = self.client.get(next_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["pagination"]["current"], 2)
        self.assertEqual([article["id"] for article in response.data["data"]], sorted(ids)[2:])

    def test_singleton_flow(self):
        """Test the generated singleton route end to end"""
        # Missing singleton
        response = self.client.get("/e2e_config.siteconfig")
        self.assertEqual(response.status_code, 404)

        # PUT creates the singleton
        response = self.client.put("/e2e_config.siteconfig", {"site_name": "My Site"})
        self.assertEqual(response.status_code, 201)

        # GET returns it
        response = self.client.get("/e2e_config.siteconfig")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["site_name"], "My Site")

        # PATCH updates partially
        response = self.client.patch("/e2e_config.siteconfig", {"maintenance_mode": True})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["maintenance_mode"])

        # PUT updates without creating duplicates
        response = self.client.put("/e2e_config.siteconfig", {"site_name": "New Site"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(SiteConfig.objects.count(), 1)

    def test_read_only_routes_reject_writes(self):
        """Test that read-only models only serve GET requests"""
        note = DraftNote.objects.create(title="Note")

        response = self.client.get("/e2e_blog.draftnote")
        self.assertEqual(response.status_code, 200)

        response = self.client.get(f"/e2e_blog.draftnote/{note.id}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["title"], "Note")

        response = self.client.post("/e2e_blog.draftnote", {"title": "Nope"})
        self.assertEqual(response.status_code, 405)

        response = self.client.patch(f"/e2e_blog.draftnote/{note.id}", {"title": "Nope"})
        self.assertEqual(response.status_code, 405)

        response = self.client.delete(f"/e2e_blog.draftnote/{note.id}")
        self.assertEqual(response.status_code, 405)

    def test_excluded_fields_are_not_exposed(self):
        """Test that the exclude option keeps fields out of the API"""
        response = self.client.post("/e2e_blog.apikey", {"name": "frontend", "secret": "hunter2"})
        self.assertEqual(response.status_code, 201)
        self.assertNotIn("secret", response.data)
        key_id = response.data["id"]

        # The excluded field is ignored on create
        self.assertEqual(ApiKey.objects.get().secret, "")

        response = self.client.get(f"/e2e_blog.apikey/{key_id}")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("secret", response.data)

    def test_api_root_lists_generated_routes(self):
        """Test that the API root lists the generated routes"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("e2e_blog.article", response.data)
        self.assertIn("e2e_blog.category", response.data)

    def test_lookup_field_routes(self):
        """Test retrieving an object by its opt-in unique lookup fields"""
        category = Category.objects.create(name="News")
        page = Page.objects.create(slug="about-us", title="About", category=category)

        response = self.client.get("/e2e_blog.page/by_slug/about-us")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], page.id)

        response = self.client.get(f"/e2e_blog.page/by_uid/{page.uid}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], page.id)

        # Unknown values
        response = self.client.get("/e2e_blog.page/by_slug/missing")
        self.assertEqual(response.status_code, 404)

        # Values that cannot be cast to the field type are not found, not errors
        response = self.client.get("/e2e_blog.page/by_uid/not-a-uuid")
        self.assertEqual(response.status_code, 404)

        # Fields that were not opted in have no route
        response = self.client.get("/e2e_blog.page/by_title/About")
        self.assertEqual(response.status_code, 404)

    def test_lookup_field_value_with_dots(self):
        """Test that lookup values may contain dots"""
        page = Page.objects.create(slug="report.pdf", title="Report")

        response = self.client.get("/e2e_blog.page/by_slug/report.pdf")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], page.id)

    def test_lookup_field_routes_are_get_only(self):
        """Test that lookup routes reject writes; those go through the detail route"""
        Page.objects.create(slug="about-us", title="About")

        response = self.client.patch("/e2e_blog.page/by_slug/about-us", {"title": "Nope"})
        self.assertEqual(response.status_code, 405)

        response = self.client.delete("/e2e_blog.page/by_slug/about-us")
        self.assertEqual(response.status_code, 405)

    def test_lookup_field_routes_ignore_list_filters(self):
        """Test that list filters do not apply to lookup routes, like they don't to retrieve"""
        Page.objects.create(slug="about-us", title="About", published=False)

        response = self.client.get("/e2e_blog.page/by_slug/about-us", {"published": "true"})
        self.assertEqual(response.status_code, 200)

    def test_lookup_field_routes_support_flexible_serializer(self):
        """Test that ?expand= and ?fields= work on lookup routes like on retrieve"""
        category = Category.objects.create(name="News")
        page = Page.objects.create(slug="about-us", title="About", category=category)

        # Expansion is opt-in through the serializer class; build a fresh viewset with it
        with override_settings(
            HEADLESS={
                "DEFAULT_SERIALIZER_CLASS": "headless.rest.serializers.FlexibleSerializer",
                "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
            }
        ):
            view_set = get_view_set(headless_registry.get_model("e2e_blog.page"), {}, {})

        factory = APIRequestFactory()
        query = "?expand=category&fields=id,category"
        expected = {"id": page.id, "category": {"id": category.id, "name": "News"}}

        response = view_set.as_view({"get": "retrieve"})(factory.get(query), pk=page.id)
        self.assertEqual(response.data, expected)

        response = view_set.as_view({"get": "by_slug"})(factory.get(query), value="about-us")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, expected)

    def test_lookup_field_routes_act_as_retrieve(self):
        """Test that lookup routes have the retrieve action, so action-based permissions cover them"""
        page = Page.objects.create(slug="about-us", title="About")

        with override_settings(HEADLESS={"DEFAULT_PERMISSION_CLASSES": [DenyRetrieve]}):
            view_set = get_view_set(headless_registry.get_model("e2e_blog.page"), {}, {})

        factory = APIRequestFactory()
        DenyRetrieve.seen.clear()

        response = view_set.as_view({"get": "by_slug"})(factory.get("/"), value="about-us")
        self.assertEqual(response.status_code, 403)

        response = view_set.as_view({"get": "retrieve"})(factory.get("/"), pk=page.id)
        self.assertEqual(response.status_code, 403)

        response = view_set.as_view({"get": "list"})(factory.get("/"))
        self.assertEqual(response.status_code, 200)

        self.assertEqual(DenyRetrieve.seen, [("retrieve", "slug"), ("retrieve", None), ("list", None)])
