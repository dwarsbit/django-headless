from django.db import models
from headless import expose


@expose()
class Category(models.Model):
    name = models.CharField(max_length=100)
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.SET_NULL, related_name="children")


@expose()
class Tag(models.Model):
    name = models.CharField(max_length=100)


@expose(lookup_fields=["slug"])
class Article(models.Model):
    STATUSES = [("draft", "Draft"), ("published", "Published")]

    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    body = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUSES, default="draft")
    views = models.IntegerField(default=0)
    created_at = models.DateTimeField()
    category = models.ForeignKey(Category, null=True, blank=True, on_delete=models.SET_NULL, related_name="articles")
    tags = models.ManyToManyField(Tag, blank=True)

    @property
    def word_count(self) -> int:
        return len(self.body.split())


@expose()
class Review(models.Model):
    article = models.ForeignKey(Article, on_delete=models.CASCADE)
    rating = models.IntegerField()


@expose(read_only=True)
class Page(models.Model):
    title = models.CharField(max_length=200)


@expose(singleton=True)
class SiteSettings(models.Model):
    site_name = models.CharField(max_length=100, default="")
