"""
Tests for the SingletonViewSet class
"""

from contextlib import contextmanager
from unittest.mock import patch

from django.db import connection, models
from django.test import SimpleTestCase, TransactionTestCase, override_settings
from rest_framework import serializers
from rest_framework.exceptions import NotFound
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory
from rest_framework.viewsets import ModelViewSet

from headless.registry import headless_registry
from headless.rest.serializers import FlexibleSerializer
from headless.rest.viewsets import RelatedLoadingMixin, SingletonViewSet


class SingletonConfig(models.Model):
    """Test model for singleton integration tests"""

    site_name = models.CharField(max_length=100, default="")
    maintenance_mode = models.BooleanField(default=False)

    class Meta:
        app_label = "headless_tests"


class NonAutoPkSingleton(models.Model):
    """Test model with a non-auto primary key"""

    name = models.CharField(max_length=100, primary_key=True)

    class Meta:
        app_label = "headless_tests"


class SingletonConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = SingletonConfig
        fields = ["id", "site_name", "maintenance_mode"]


class NonAutoPkSingletonSerializer(serializers.ModelSerializer):
    class Meta:
        model = NonAutoPkSingleton
        fields = ["name"]


class SingletonConfigViewSet(SingletonViewSet):
    queryset = SingletonConfig.objects.all()
    serializer_class = SingletonConfigSerializer


class NonAutoPkSingletonViewSet(SingletonViewSet):
    queryset = NonAutoPkSingleton.objects.all()
    serializer_class = NonAutoPkSingletonSerializer


class SingletonViewSetTests(SimpleTestCase):
    """Unit tests for the SingletonViewSet class"""

    def test_inheritance(self):
        """Test that SingletonViewSet inherits from correct base classes"""
        from rest_framework.viewsets import GenericViewSet
        from rest_framework.mixins import (
            CreateModelMixin,
            UpdateModelMixin,
            RetrieveModelMixin,
        )

        self.assertTrue(issubclass(SingletonViewSet, GenericViewSet))
        self.assertTrue(issubclass(SingletonViewSet, CreateModelMixin))
        self.assertTrue(issubclass(SingletonViewSet, UpdateModelMixin))
        self.assertTrue(issubclass(SingletonViewSet, RetrieveModelMixin))

    def test_get_singleton_pk_auto_pk(self):
        """Test that a deterministic pk is used for auto primary keys"""
        viewset = SingletonViewSet()
        viewset.queryset = SingletonConfig.objects.all()

        self.assertEqual(viewset.get_singleton_pk(), 1)

    def test_get_singleton_pk_non_auto_pk(self):
        """Test that no deterministic pk is used for non-auto primary keys"""
        viewset = SingletonViewSet()
        viewset.queryset = NonAutoPkSingleton.objects.all()

        self.assertIsNone(viewset.get_singleton_pk())

    def test_get_singleton_queryset_ordered_by_pk(self):
        """Test that the singleton queryset is deterministically ordered"""
        viewset = SingletonViewSet()
        viewset.queryset = SingletonConfig.objects.order_by("-site_name")

        queryset = viewset.get_singleton_queryset()
        self.assertEqual(queryset.query.order_by, ("pk",))


class SingletonViewSetIntegrationTests(TransactionTestCase):
    """Integration tests running the singleton view set against a real table"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        with connection.schema_editor() as editor:
            editor.create_model(SingletonConfig)
            editor.create_model(NonAutoPkSingleton)

    @classmethod
    def tearDownClass(cls):
        with connection.schema_editor() as editor:
            editor.delete_model(NonAutoPkSingleton)
            editor.delete_model(SingletonConfig)
        super().tearDownClass()

    def setUp(self):
        self.factory = APIRequestFactory()
        self.view = SingletonConfigViewSet.as_view(
            {
                "get": "retrieve",
                "put": "update",
                "patch": "partial_update",
            }
        )

    def tearDown(self):
        # The tables are not known to the test flush; clean them up explicitly.
        SingletonConfig.objects.all().delete()
        NonAutoPkSingleton.objects.all().delete()

    def test_retrieve_missing_singleton_returns_404(self):
        """Test that retrieving a missing singleton raises NotFound"""
        request = self.factory.get("/singleton/")
        response = self.view(request)

        self.assertEqual(response.status_code, 404)

    def test_retrieve_returns_singleton(self):
        """Test that retrieve returns the existing singleton"""
        SingletonConfig.objects.create(site_name="My Site")

        request = self.factory.get("/singleton/")
        response = self.view(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["site_name"], "My Site")

    def test_retrieve_checks_object_permissions(self):
        """Test that object permissions are checked on retrieve"""
        SingletonConfig.objects.create(site_name="My Site")

        with patch.object(SingletonViewSet, "check_object_permissions") as mock_check:
            request = self.factory.get("/singleton/")
            self.view(request)
            mock_check.assert_called_once()

    def test_put_creates_singleton_when_missing(self):
        """Test that PUT creates the singleton when it does not exist"""
        request = self.factory.put("/singleton/", {"site_name": "My Site", "maintenance_mode": True}, format="json")
        response = self.view(request)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(SingletonConfig.objects.count(), 1)

        singleton = SingletonConfig.objects.get()
        self.assertEqual(singleton.site_name, "My Site")
        self.assertTrue(singleton.maintenance_mode)

    def test_put_creates_singleton_with_deterministic_pk(self):
        """Test that the singleton is created with the deterministic pk"""
        request = self.factory.put("/singleton/", {"site_name": "My Site"}, format="json")
        response = self.view(request)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(SingletonConfig.objects.get().pk, 1)

    def test_put_updates_existing_singleton(self):
        """Test that PUT updates the singleton without creating duplicates"""
        SingletonConfig.objects.create(site_name="Old Name")

        request = self.factory.put("/singleton/", {"site_name": "New Name"}, format="json")
        response = self.view(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(SingletonConfig.objects.count(), 1)
        self.assertEqual(SingletonConfig.objects.get().site_name, "New Name")

    def test_patch_partially_updates_singleton(self):
        """Test that PATCH updates only the provided fields"""
        SingletonConfig.objects.create(site_name="My Site", maintenance_mode=False)

        request = self.factory.patch("/singleton/", {"maintenance_mode": True}, format="json")
        response = self.view(request)

        self.assertEqual(response.status_code, 200)
        singleton = SingletonConfig.objects.get()
        self.assertEqual(singleton.site_name, "My Site")
        self.assertTrue(singleton.maintenance_mode)

    def test_concurrent_create_falls_back_to_update(self):
        """Test the race fallback: a lost create updates the winner instead"""
        # Simulate a concurrent request winning the create race: the row
        # appears between our lock check and our insert.
        SingletonConfig.objects.create(pk=1, site_name="Winner")
        winner = SingletonConfig.objects.get(pk=1)

        with patch.object(SingletonConfigViewSet, "get_locked_singleton", side_effect=[None, winner]):
            request = self.factory.put("/singleton/", {"site_name": "Loser"}, format="json")
            response = self.view(request)

        # The concurrent insert fails the deterministic pk constraint, after
        # which the existing singleton is updated instead of duplicated.
        self.assertEqual(response.status_code, 200)
        self.assertEqual(SingletonConfig.objects.count(), 1)
        self.assertEqual(SingletonConfig.objects.get().site_name, "Loser")

    def test_create_with_non_auto_pk(self):
        """Test that singletons with non-auto primary keys are still created"""
        view = NonAutoPkSingletonViewSet.as_view(
            {
                "get": "retrieve",
                "put": "update",
                "patch": "partial_update",
            }
        )

        request = self.factory.put("/singleton/", {"name": "settings"}, format="json")
        response = view(request)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(NonAutoPkSingleton.objects.count(), 1)
        self.assertEqual(NonAutoPkSingleton.objects.get().name, "settings")

    def test_get_object_raises_not_found_when_queryset_empty(self):
        """Test that get_object raises NotFound when no singleton exists"""
        viewset = SingletonConfigViewSet()
        viewset.request = self.factory.get("/singleton/")

        with self.assertRaises(NotFound):
            viewset.get_object()


class PrefetchTag(models.Model):
    name = models.CharField(max_length=100)

    class Meta:
        app_label = "headless_tests"


class PrefetchCategory(models.Model):
    name = models.CharField(max_length=100)
    parent = models.ForeignKey("self", null=True, on_delete=models.CASCADE)
    tags = models.ManyToManyField(PrefetchTag)

    class Meta:
        app_label = "headless_tests"


class PrefetchArticle(models.Model):
    title = models.CharField(max_length=100)
    category = models.ForeignKey(PrefetchCategory, on_delete=models.CASCADE, related_name="articles")

    class Meta:
        app_label = "headless_tests"


class PrefetchArticleSerializer(FlexibleSerializer):
    class Meta:
        model = PrefetchArticle
        fields = "__all__"


class PrefetchCategorySerializer(FlexibleSerializer):
    class Meta:
        model = PrefetchCategory
        fields = "__all__"


class RelatedLoadingMixinTests(SimpleTestCase):
    """Relations are joined or prefetched instead of queried per object"""

    def setUp(self):
        self._saved_registry = dict(headless_registry._models)
        headless_registry.register(PrefetchTag)
        headless_registry.register(PrefetchCategory)
        headless_registry.register(PrefetchArticle)

    def tearDown(self):
        headless_registry._models = self._saved_registry

    def get_queryset(self, query, serializer_class=PrefetchArticleSerializer, method="get"):
        model = serializer_class.Meta.model

        class ModelViewSetUnderTest(RelatedLoadingMixin, ModelViewSet):
            queryset = model.objects.all()

        ModelViewSetUnderTest.serializer_class = serializer_class
        viewset = ModelViewSetUnderTest()
        viewset.request = Request(getattr(APIRequestFactory(), method)(f"/?{query}"))
        viewset.format_kwarg = None
        return viewset.get_queryset()

    def get_prefetch_lookups(self, query, serializer_class=PrefetchArticleSerializer):
        return self.get_queryset(query, serializer_class)._prefetch_related_lookups

    def get_select_related(self, query, serializer_class=PrefetchArticleSerializer):
        select_related = self.get_queryset(query, serializer_class).query.select_related
        return select_related if select_related is False else _flatten_select_related(select_related)

    def test_expanded_foreign_key_joined(self):
        self.assertEqual(self.get_select_related("expand=category"), ["category"])
        # The tags of the joined category are prefetched
        self.assertEqual(self.get_prefetch_lookups("expand=category"), ("category__tags",))

    @contextmanager
    def reverse_relations(self):
        # Models of an app that is not installed get no reverse relations
        # from get_fields; provide the reverse foreign key explicitly.
        reverse = PrefetchArticle._meta.get_field("category").remote_field
        fields = (*PrefetchCategory._meta.get_fields(), reverse)
        with patch.object(PrefetchCategory._meta, "get_fields", return_value=fields):
            yield

    def test_expanded_to_many_relation_prefetched(self):
        with self.reverse_relations():
            self.assertEqual(self.get_select_related("expand=articles", PrefetchCategorySerializer), False)
            self.assertEqual(
                self.get_prefetch_lookups("expand=articles", PrefetchCategorySerializer),
                ("tags", "articles"),
            )

    def test_nested_expansion(self):
        # Expanded objects only expand further with FlexibleSerializer as the default serializer
        with override_settings(HEADLESS={"DEFAULT_SERIALIZER_CLASS": "headless.rest.serializers.FlexibleSerializer"}):
            self.assertEqual(self.get_select_related("expand=category.parent"), ["category", "category__parent"])
            # Nothing past a to-many relation can be joined
            with self.reverse_relations():
                self.assertEqual(self.get_select_related("expand=articles.category", PrefetchCategorySerializer), False)
                self.assertEqual(
                    self.get_prefetch_lookups("expand=articles.category", PrefetchCategorySerializer),
                    ("tags", "articles", "articles__category", "articles__category__tags"),
                )

        self.assertEqual(self.get_select_related("expand=category.parent"), ["category"])

    def test_wildcard_expansion(self):
        self.assertEqual(self.get_select_related("expand=*"), ["category"])

    def test_unknown_names_ignored(self):
        self.assertEqual(self.get_select_related("expand=bogus,category"), ["category"])
        self.assertEqual(self.get_select_related("expand=category.bogus"), ["category"])

    def test_no_expansion(self):
        self.assertEqual(self.get_select_related("title=a"), False)
        self.assertEqual(self.get_prefetch_lookups("title=a"), ())

    def test_many_to_many_prefetched_without_expansion(self):
        self.assertEqual(self.get_prefetch_lookups("", PrefetchCategorySerializer), ("tags",))

    def test_writes_are_left_alone(self):
        queryset = self.get_queryset("expand=category", method="patch")
        self.assertIs(queryset.query.select_related, False)
        self.assertEqual(queryset._prefetch_related_lookups, ())

        queryset = self.get_queryset("", PrefetchCategorySerializer, method="put")
        self.assertEqual(queryset._prefetch_related_lookups, ())

    def test_serializer_without_expandable_fields(self):
        class PlainSerializer(serializers.ModelSerializer):
            class Meta:
                model = PrefetchArticle
                fields = "__all__"

        self.assertEqual(self.get_select_related("expand=category", PlainSerializer), False)
        self.assertEqual(self.get_prefetch_lookups("expand=category", PlainSerializer), ())

    def test_write_only_and_hidden_fields_not_prefetched(self):
        class HiddenTagsSerializer(serializers.ModelSerializer):
            class Meta:
                model = PrefetchCategory
                exclude = ["tags"]

        self.assertEqual(self.get_prefetch_lookups("", HiddenTagsSerializer), ())


def _flatten_select_related(tree, prefix=""):
    """Turn Django's nested select_related dict into a list of paths."""
    paths = []
    for name, children in tree.items():
        paths.append(f"{prefix}{name}")
        paths.extend(_flatten_select_related(children, f"{prefix}{name}__"))
    return paths
