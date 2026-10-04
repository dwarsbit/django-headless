"""
Tests for FlexibleSerializer
"""

import pytest
from django.core.exceptions import ImproperlyConfigured
from django.db import models
from rest_framework import serializers

from headless.registry import headless_registry
from headless.rest.serializers import FlexibleSerializer


@pytest.fixture(autouse=True)
def _clean_registry():
    """Keep the global headless registry isolated between tests."""
    saved = dict(headless_registry._models)
    yield
    headless_registry._models = saved


class TestFlexibleSerializer:
    """Test suite for FlexibleSerializer"""

    def test_missing_meta_class(self):
        """Test that serializer raises ImproperlyConfigured when Meta class is missing"""
        with pytest.raises(ImproperlyConfigured, match="is missing Meta class"):

            class BadSerializer(FlexibleSerializer):
                pass

            serializer = BadSerializer()
            _ = serializer._expandable_fields

    def test_missing_model_attribute(self):
        """Test that serializer raises ImproperlyConfigured when model attribute is missing"""
        with pytest.raises(ImproperlyConfigured, match="Meta is missing model attribute"):

            class BadSerializer(FlexibleSerializer):
                class Meta:
                    pass

            serializer = BadSerializer()
            _ = serializer._expandable_fields

    def test_none_model(self):
        """Test that serializer raises ImproperlyConfigured when model is None"""
        with pytest.raises(ImproperlyConfigured, match="Meta.model is None or invalid"):

            class BadSerializer(FlexibleSerializer):
                class Meta:
                    model = None

            serializer = BadSerializer()
            _ = serializer._expandable_fields

    def test_invalid_model(self):
        """Test that serializer raises ImproperlyConfigured when model is not a Django model"""
        with pytest.raises(ImproperlyConfigured, match="missing _meta attribute"):

            class FakeModel:
                pass

            class BadSerializer(FlexibleSerializer):
                class Meta:
                    model = FakeModel

            serializer = BadSerializer()
            _ = serializer._expandable_fields

    def test_simple_model_no_relations(self):
        """Test serializer with a simple model that has no relational fields"""

        class SimpleModel(models.Model):
            name = models.CharField(max_length=100)
            description = models.TextField()

            class Meta:
                app_label = "test"

        class SimpleSerializer(FlexibleSerializer):
            class Meta:
                model = SimpleModel
                fields = "__all__"

        serializer = SimpleSerializer()
        expandable_fields = serializer._expandable_fields

        assert isinstance(expandable_fields, dict)
        assert len(expandable_fields) == 0, "Simple model should have no expandable fields"

    def test_model_with_foreign_key(self):
        """Test serializer with a model that has ForeignKey relations"""

        class Author(models.Model):
            name = models.CharField(max_length=100)

            class Meta:
                app_label = "test"

        class Book(models.Model):
            title = models.CharField(max_length=200)
            author = models.ForeignKey(Author, on_delete=models.CASCADE)

            class Meta:
                app_label = "test"

        # Register the related model so it can be expanded
        headless_registry.register(Author)

        class BookSerializer(FlexibleSerializer):
            class Meta:
                model = Book
                fields = "__all__"

        serializer = BookSerializer()
        expandable_fields = serializer._expandable_fields

        assert isinstance(expandable_fields, dict)
        assert "author" in expandable_fields, "Should include ForeignKey field as expandable"
        assert len(expandable_fields) == 1, "Should have exactly one expandable field"

    def test_model_with_many_to_many(self):
        """Test serializer with a model that has ManyToMany relations"""

        class Category(models.Model):
            name = models.CharField(max_length=100)

            class Meta:
                app_label = "test"

        class Article(models.Model):
            title = models.CharField(max_length=200)
            categories = models.ManyToManyField(Category)

            class Meta:
                app_label = "test"

        # Register the related model so it can be expanded
        headless_registry.register(Category)

        class ArticleSerializer(FlexibleSerializer):
            class Meta:
                model = Article
                fields = "__all__"

        serializer = ArticleSerializer()
        expandable_fields = serializer._expandable_fields

        assert isinstance(expandable_fields, dict)
        assert "categories" in expandable_fields, "Should include ManyToMany field as expandable"
        assert len(expandable_fields) == 1, "Should have exactly one expandable field"

    def test_model_with_self_reference(self):
        """Test serializer with a model that has self-referential ForeignKey"""

        class SelfReferencingCategory(models.Model):
            name = models.CharField(max_length=100)
            parent = models.ForeignKey("self", on_delete=models.CASCADE, null=True, blank=True)

            class Meta:
                app_label = "test"

        # Register the model so it can be expanded
        headless_registry.register(SelfReferencingCategory)

        class CategorySerializer(FlexibleSerializer):
            class Meta:
                model = SelfReferencingCategory
                fields = "__all__"

        serializer = CategorySerializer()
        expandable_fields = serializer._expandable_fields

        assert isinstance(expandable_fields, dict)
        assert "parent" in expandable_fields, "Should include self-referential field as expandable"

    def test_caching_functionality(self):
        """Test that expandable fields are properly cached"""

        class CachingTestModel(models.Model):
            name = models.CharField(max_length=100)

            class Meta:
                app_label = "test"

        class TestSerializer(FlexibleSerializer):
            class Meta:
                model = CachingTestModel
                fields = "__all__"

        serializer = TestSerializer()

        # First call
        fields1 = serializer._expandable_fields
        # Second call
        fields2 = serializer._expandable_fields

        # Should return the exact same object (cached)
        assert fields1 is fields2, "Expandable fields should be cached"

    def test_property_fields_inclusion(self):
        """Test that model properties are included as read-only fields"""

        class ModelWithProperties(models.Model):
            name = models.CharField(max_length=100)

            class Meta:
                app_label = "test"

            @property
            def computed_field(self):
                return f"computed_{self.name}"

            @property
            def _private_property(self):
                return "private"

        class PropertySerializer(FlexibleSerializer):
            class Meta:
                model = ModelWithProperties
                fields = "__all__"

        serializer = PropertySerializer()
        fields = serializer.get_fields()

        # Should include public property
        assert "computed_field" in fields, "Should include public property field"
        # Should not include private property (starts with _)
        assert "_private_property" not in fields, "Should not include private property field"
        # Property field should be read-only
        assert isinstance(fields["computed_field"], serializers.ReadOnlyField), "Property field should be read-only"

    def test_multiple_serializer_instances(self):
        """Test that different serializer instances have independent caches"""

        class CacheIsolationModel(models.Model):
            name = models.CharField(max_length=100)

            class Meta:
                app_label = "test"

        class TestSerializer(FlexibleSerializer):
            class Meta:
                model = CacheIsolationModel
                fields = "__all__"

        serializer1 = TestSerializer()
        serializer2 = TestSerializer()

        fields1 = serializer1._expandable_fields
        fields2 = serializer2._expandable_fields

        # Should be different objects (instance-specific caching)
        assert fields1 is not fields2, "Different serializer instances should have different cache objects"
        # But should have the same content
        assert fields1.keys() == fields2.keys(), "Different serializer instances should have same field keys"

    def test_unregistered_related_model(self):
        """Test that unregistered related models are not included as expandable"""

        class UnregisteredModel(models.Model):
            name = models.CharField(max_length=100)

            class Meta:
                app_label = "test"

        class RelatedToUnregisteredModel(models.Model):
            name = models.CharField(max_length=100)
            unregistered = models.ForeignKey(UnregisteredModel, on_delete=models.CASCADE)

            class Meta:
                app_label = "test"

        # Don't register UnregisteredModel

        class TestSerializer(FlexibleSerializer):
            class Meta:
                model = RelatedToUnregisteredModel
                fields = "__all__"

        serializer = TestSerializer()
        expandable_fields = serializer._expandable_fields

        # Should not include unregistered model
        assert "unregistered" not in expandable_fields, "Should not include unregistered related model"
        assert len(expandable_fields) == 0, "Should have no expandable fields for unregistered models"

    def test_inheritance(self):
        """Test that FlexibleSerializer works with inheritance"""

        class BaseModel(models.Model):
            created_at = models.DateTimeField(auto_now_add=True)

            class Meta:
                app_label = "test"
                abstract = True

        class ConcreteModel(BaseModel):
            name = models.CharField(max_length=100)

            class Meta:
                app_label = "test"

        class ConcreteSerializer(FlexibleSerializer):
            class Meta:
                model = ConcreteModel
                fields = "__all__"

        serializer = ConcreteSerializer()
        expandable_fields = serializer._expandable_fields

        assert isinstance(expandable_fields, dict), "Should work with model inheritance"

    @pytest.mark.parametrize(
        "field_type,field_definition",
        [
            (
                models.ForeignKey,
                models.ForeignKey("self", on_delete=models.CASCADE, null=True),
            ),
            (
                models.OneToOneField,
                models.OneToOneField("self", on_delete=models.CASCADE, null=True),
            ),
            (models.ManyToManyField, models.ManyToManyField("self")),
        ],
    )
    def test_various_relation_types(self, field_type, field_definition):
        """Test that various types of relational fields are handled correctly"""
        # Create a model with the specific relation type, with a unique
        # name per relation so the model registry is not reloaded
        # between parametrized runs
        RelationTestModel = type(
            f"RelationTest_{field_type.__name__}",
            (models.Model,),
            {
                "name": models.CharField(max_length=100),
                "relation": field_definition,
                "Meta": type("Meta", (), {"app_label": "test"}),
                "__module__": __name__,
            },
        )

        # Register the model so it can be expanded
        headless_registry.register(RelationTestModel)

        class TestSerializer(FlexibleSerializer):
            class Meta:
                model = RelationTestModel
                fields = "__all__"

        serializer = TestSerializer()
        expandable_fields = serializer._expandable_fields

        assert isinstance(expandable_fields, dict)
        # Should include the relation field
        assert "relation" in expandable_fields, f"Should include {field_type.__name__} as expandable"
