"""
End-to-end tests for the generated REST API.

These tests build the real URL wiring (as RestBuilder does at app ready) for
exposed test models, and exercise the generated endpoints through the test
client: CRUD, relations, filtering, pagination and singletons.
"""

from django.db import connection, models
from django.test import TransactionTestCase
from django.urls import clear_url_caches
from rest_framework.test import APIClient

import headless.rest.urls as headless_urls
from headless import expose
from headless.registry import headless_registry
from headless.rest.builder import RestBuilder
from headless.rest.filters import LookupFilter
from headless.rest.pagination import PageNumberPagination
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


class E2EPagination(PageNumberPagination):
    page_size = 2


E2E_ROUTES = ("e2e_blog.article", "e2e_blog.category")
MODEL_LABELS = (
    "e2e_blog.article",
    "e2e_blog.category",
    "e2e_blog.draftnote",
    "e2e_blog.apikey",
    "e2e_config.siteconfig",
)
E2E_REGISTRY_PREFIXES = E2E_ROUTES + ("e2e_blog.draftnote", "e2e_blog.apikey")


def rebuild_urlpatterns():
    """Recompute the url patterns and clear Django's resolver caches."""
    if hasattr(rest_router, "_urls"):
        del rest_router._urls
    headless_urls.urlpatterns = rest_router.urls + singleton_urls
    clear_url_caches()


def setUpModule():
    # Build the routes for the exposed models, mirroring what happens at
    # app ready in a real project.
    RestBuilder(silent=True).build()

    # Bind pagination and filtering to the generated view sets explicitly:
    # DRF binds these from api_settings at import time, so runtime settings
    # overrides do not reach the generated classes.
    for prefix, viewset, basename in rest_router.registry:
        if prefix in E2E_ROUTES:
            viewset.pagination_class = E2EPagination
            viewset.filter_backends = [LookupFilter]

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

    @classmethod
    def tearDownClass(cls):
        with connection.schema_editor() as editor:
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
