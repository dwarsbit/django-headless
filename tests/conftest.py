"""
Pytest configuration for django-headless tests
"""

import os
import sys
import django
from django.conf import settings

# Add the project directory to the Python path
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_DIR)

# Configure Django settings for testing
if not settings.configured:
    settings.configure(
        DEBUG=True,
        DATABASES={
            "default": {
                "ENGINE": "django.db.backends.sqlite3",
                "NAME": ":memory:",
            }
        },
        INSTALLED_APPS=[
            "django.contrib.contenttypes",
            "django.contrib.auth",
            "rest_framework",
            "headless",
            "headless.rest",
        ],
        SECRET_KEY="test-secret-key-for-testing-only",
        USE_TZ=True,
    )

django.setup()
