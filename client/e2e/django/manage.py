#!/usr/bin/env python
"""The Django project the end-to-end tests of the client run against."""

import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "blogsite.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)
