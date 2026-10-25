import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = "e2e-only-secret-key"
DEBUG = False
ALLOWED_HOSTS = ["127.0.0.1", "localhost"]
USE_TZ = True
TIME_ZONE = "UTC"

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "rest_framework",
    "headless",
    "headless.rest",
    "blog",
]

MIDDLEWARE = ["django.middleware.common.CommonMiddleware"]
ROOT_URLCONF = "blogsite.urls"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.environ.get("E2E_DATABASE", BASE_DIR / "db.sqlite3"),
    }
}

HEADLESS = {
    "BOOT_LOG": False,
    "VERSION_CHECK": False,
    "SCHEMA": True,
    "SCHEMA_TITLE": "Blog API",
    "AUTH_SECRET_KEY": "e2e-secret-key",
    "AUTH_READ_ONLY_SECRET_KEY": "e2e-read-only-secret-key",
    "DEFAULT_AUTHENTICATION_CLASSES": ["headless.rest.authentication.SecretKeyAuthentication"],
    "DEFAULT_SERIALIZER_CLASS": "headless.rest.serializers.FlexibleSerializer",
    "DEFAULT_PAGINATION_CLASS": "headless.rest.pagination.PageNumberPagination",
    "PAGE_SIZE": 2,
    "DEFAULT_FILTER_BACKENDS": [
        "headless.rest.filters.LookupFilter",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
}
