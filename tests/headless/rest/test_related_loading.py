"""
End-to-end tests for the number of queries of the generated routes: the
relations a response includes load with a fixed number of queries, however
many objects it holds.
"""

from django.db import connection, models
from django.test import TransactionTestCase, override_settings
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient

import headless.rest.urls as headless_urls
from headless import expose
from headless.registry import headless_registry
from headless.rest.builder import RestBuilder
from headless.rest.routers import rest_router, singleton_urls

HEADLESS_SETTINGS = {
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
    "DEFAULT_SERIALIZER_CLASS": "headless.rest.serializers.FlexibleSerializer",
    "DEFAULT_PAGINATION_CLASS": "headless.rest.pagination.PageNumberPagination",
    "PAGE_SIZE": 50,
}


@expose()
class LoadTag(models.Model):
    name = models.CharField(max_length=100)

    class Meta:
        app_label = "headless_rest"


@expose()
class LoadAuthor(models.Model):
    name = models.CharField(max_length=100)
    favorite_tags = models.ManyToManyField(LoadTag)

    class Meta:
        app_label = "headless_rest"


@expose()
class LoadPost(models.Model):
    title = models.CharField(max_length=100)
    author = models.ForeignKey(LoadAuthor, null=True, on_delete=models.SET_NULL)
    tags = models.ManyToManyField(LoadTag)

    class Meta:
        app_label = "headless_rest"


@expose(singleton=True)
class LoadHomepage(models.Model):
    featured = models.ForeignKey(LoadPost, null=True, on_delete=models.SET_NULL)
    tags = models.ManyToManyField(LoadTag)

    class Meta:
        app_label = "headless_rest"


@expose(lookup_fields=["slug"])
class LoadLanding(models.Model):
    slug = models.CharField(max_length=100, unique=True)
    tags = models.ManyToManyField(LoadTag)

    class Meta:
        app_label = "headless_rest"


@expose()
class LoadComment(models.Model):
    text = models.CharField(max_length=100)
    post = models.ForeignKey(LoadPost, on_delete=models.CASCADE, related_name="comments")

    class Meta:
        app_label = "headless_rest"


MODELS = (LoadTag, LoadAuthor, LoadPost, LoadHomepage, LoadLanding, LoadComment)
LABELS = tuple(model._meta.label_lower for model in MODELS)


def rebuild_urlpatterns():
    if hasattr(rest_router, "_urls"):
        del rest_router._urls
    headless_urls.urlpatterns = rest_router.urls + singleton_urls

    from django.urls import clear_url_caches

    clear_url_caches()


def remove_routes():
    """Remove the routes of the models of this module."""
    rest_router.registry = [entry for entry in rest_router.registry if entry[0] not in LABELS]
    singleton_urls[:] = [url for url in singleton_urls if str(url.pattern) not in LABELS]
    rebuild_urlpatterns()


def setUpModule():
    # Another module may have built routes for these models with other
    # settings (the builder registers every model in the registry)
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


@override_settings(HEADLESS=HEADLESS_SETTINGS)
class RelatedLoadingTests(TransactionTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        with connection.schema_editor() as editor:
            for model in MODELS:
                editor.create_model(model)

    @classmethod
    def tearDownClass(cls):
        with connection.schema_editor() as editor:
            for model in reversed(MODELS):
                editor.delete_model(model)
        super().tearDownClass()

    def setUp(self):
        self.client = APIClient()
        self.tags = [LoadTag.objects.create(name=f"tag {i}") for i in range(3)]

    def tearDown(self):
        for model in reversed(MODELS):
            model.objects.all().delete()

    def create_posts(self, count):
        posts = []
        for i in range(count):
            author = LoadAuthor.objects.create(name=f"author {i}")
            author.favorite_tags.set(self.tags[:2])
            post = LoadPost.objects.create(title=f"post {i}", author=author)
            post.tags.set(self.tags)
            posts.append(post)
        return posts

    def count_queries(self, url, **params):
        with CaptureQueriesContext(connection) as queries:
            response = self.client.get(url, params)
        self.assertEqual(response.status_code, 200, response.content)
        return len(queries), response

    def test_many_to_many_list_loads_in_constant_queries(self):
        self.create_posts(2)
        few, response = self.count_queries("/headless_rest.loadpost")
        self.assertEqual(response.data["data"][0]["tags"], [tag.pk for tag in self.tags])

        self.create_posts(4)
        many, _ = self.count_queries("/headless_rest.loadpost")

        # Pagination count, posts, and the tags of all posts
        self.assertEqual((few, many), (3, 3))

    def test_expanded_relations_load_in_constant_queries(self):
        self.create_posts(2)
        few, response = self.count_queries("/headless_rest.loadpost", expand="author")
        author = response.data["data"][0]["author"]
        self.assertEqual(author["favorite_tags"], [tag.pk for tag in self.tags[:2]])

        self.create_posts(4)
        many, _ = self.count_queries("/headless_rest.loadpost", expand="author")

        # Count, posts joined with their authors, and the tags of the posts
        # and of the authors
        self.assertEqual((few, many), (4, 4))

    def test_expanded_many_to_many_loads_in_constant_queries(self):
        self.create_posts(2)
        few, response = self.count_queries("/headless_rest.loadpost", expand="tags")
        self.assertEqual([tag["name"] for tag in response.data["data"][0]["tags"]], [tag.name for tag in self.tags])

        self.create_posts(4)
        many, _ = self.count_queries("/headless_rest.loadpost", expand="tags")

        # Count, posts, and the tags (expanded objects are the same query)
        self.assertEqual((few, many), (3, 3))

    def test_expanded_reverse_relation_loads_in_constant_queries(self):
        posts = self.create_posts(2)
        for post in posts:
            LoadComment.objects.create(post=post, text="first")
            LoadComment.objects.create(post=post, text="second")
        few, response = self.count_queries("/headless_rest.loadpost", expand="comments")
        self.assertEqual([c["text"] for c in response.data["data"][0]["comments"]], ["first", "second"])

        for post in self.create_posts(4):
            LoadComment.objects.create(post=post, text="first")
        many, _ = self.count_queries("/headless_rest.loadpost", expand="comments")

        # Count, posts, the tags of the posts, and the comments
        self.assertEqual((few, many), (4, 4))

    def test_sparse_fields_without_many_to_many_skip_the_prefetch(self):
        self.create_posts(3)
        queries, response = self.count_queries("/headless_rest.loadpost", fields="id,title")

        self.assertEqual(set(response.data["data"][0]), {"id", "title"})
        # Count and posts: the tags are not in the response, so not loaded
        self.assertEqual(queries, 2)

    def test_sparse_fields_also_as_list(self):
        self.create_posts(3)
        queries, _ = self.count_queries("/headless_rest.loadpost?fields[]=id&fields[]=title")
        self.assertEqual(queries, 2)

        queries, _ = self.count_queries("/headless_rest.loadpost?fields=id&fields=tags")
        self.assertEqual(queries, 3)

    def test_sparse_nested_fields_prefetch_the_relation(self):
        self.create_posts(3)
        queries, response = self.count_queries("/headless_rest.loadpost", fields="title,tags.name", expand="tags")

        self.assertEqual(response.data["data"][0]["tags"], [{"name": tag.name} for tag in self.tags])
        # Count, posts, and the tags
        self.assertEqual(queries, 3)

    def test_omitted_many_to_many_skips_the_prefetch(self):
        self.create_posts(3)
        queries, response = self.count_queries("/headless_rest.loadpost", omit="tags")

        self.assertNotIn("tags", response.data["data"][0])
        self.assertEqual(queries, 2)

        # Omitting a nested field keeps the relation
        queries, _ = self.count_queries("/headless_rest.loadpost", omit="tags.name", expand="tags")
        self.assertEqual(queries, 3)

    def test_sparse_fields_skip_expanded_relations(self):
        self.create_posts(3)
        queries, response = self.count_queries("/headless_rest.loadpost", fields="title", expand="author,tags")

        self.assertEqual(set(response.data["data"][0]), {"title"})
        # Neither the author (join) nor the tags of posts and authors
        self.assertEqual(queries, 2)

    def test_sparse_fields_of_an_expanded_relation(self):
        self.create_posts(3)
        queries, response = self.count_queries("/headless_rest.loadpost", fields="title,author.name", expand="author")

        self.assertEqual(response.data["data"][0], {"title": "post 0", "author": {"name": "author 0"}})
        # Count and posts joined with their authors; no tags of either
        self.assertEqual(queries, 2)

    def test_omitted_expanded_relation_skips_the_join(self):
        self.create_posts(3)
        queries, response = self.count_queries("/headless_rest.loadpost", omit="author,tags", expand="author")

        self.assertNotIn("author", response.data["data"][0])
        self.assertEqual(queries, 2)

    def test_detail_route(self):
        post = self.create_posts(1)[0]
        queries, response = self.count_queries(f"/headless_rest.loadpost/{post.pk}", expand="author")

        self.assertEqual(response.data["author"]["name"], "author 0")
        # LoadPost joined with its author, then the tags of the post and the author
        self.assertEqual(queries, 3)

    def test_singleton(self):
        post = self.create_posts(1)[0]
        homepage = LoadHomepage.objects.create(featured=post)
        homepage.tags.set(self.tags)

        queries, response = self.count_queries("/headless_rest.loadhomepage", expand="featured")

        self.assertEqual(response.data["featured"]["title"], "post 0")
        self.assertEqual(response.data["tags"], [tag.pk for tag in self.tags])
        # LoadHomepage joined with its post, then the tags of the homepage and the post
        self.assertEqual(queries, 3)

    def test_lookup_route(self):
        landing = LoadLanding.objects.create(slug="home")
        landing.tags.set(self.tags)

        queries, response = self.count_queries("/headless_rest.loadlanding/by_slug/home")

        self.assertEqual(response.data["tags"], [tag.pk for tag in self.tags])
        self.assertEqual(queries, 2)

    def test_updates_show_the_changed_relations(self):
        post = self.create_posts(1)[0]
        other = LoadAuthor.objects.create(name="other")

        response = self.client.patch(
            f"/headless_rest.loadpost/{post.pk}?expand=author",
            {"author": other.pk, "tags": [self.tags[0].pk]},
            format="json",
        )

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.data["author"]["name"], "other")
        self.assertEqual(response.data["tags"], [self.tags[0].pk])
