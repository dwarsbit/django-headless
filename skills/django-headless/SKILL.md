---
name: django-headless
description: Set up and use Django Headless (the django-headless PyPI package and the @django-headless/client npm package), which generates a Django REST Framework API from Django models decorated with @expose(). Use when a project imports `headless` or `@django-headless/client`, when the user wants to expose Django models as a REST API for a frontend (Next.js, Astro, a static site, a mobile app), use Django as a headless CMS, add singletons or lookup routes, filter, paginate or expand API responses, configure permissions or secret key authentication for the generated routes, or generate TypeScript types from the API.
---

# Django Headless

Django Headless generates a Django REST Framework (DRF) API for every model decorated with `@expose()`: list, detail, create, update and delete routes, with filtering and pagination. Do not write serializers, viewsets or URL patterns for exposed models; configure them with decorator options and the `HEADLESS` setting instead.

Full documentation in Markdown: https://djangoheadless.org/llms.txt (index) and https://djangoheadless.org/llms-full.txt (everything in one file). Read the relevant page before using a feature this file only mentions.

## Setup

1. `pip install django-headless` (Python 3.12+, Django 5.2+, DRF 3.18+). Add the `schema` extra for the OpenAPI schema: `pip install "django-headless[schema]"`.
2. Add the apps, in this order:

   ```python
   # mysite/settings.py
   INSTALLED_APPS = [
       # ...
       "rest_framework",
       "headless",
       "headless.rest",
   ]
   ```

   `headless` tracks the exposed models; `headless.rest` builds the routes. Without `headless.rest` there are no routes.
3. Include the URLs: `path("api/", include("headless.rest.urls"))` in `mysite/urls.py`.
4. Configure authentication, permissions and pagination (see below). The defaults only answer staff users and do not paginate.

## Exposing models

```python
# blog/models.py
from django.db import models
from headless import expose


@expose(lookup_fields=["slug"], exclude=["internal_notes"])
class Article(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    internal_notes = models.TextField(blank=True)
    category = models.ForeignKey("blog.Category", on_delete=models.PROTECT, related_name="articles")


@expose(singleton=True, read_only=True)
class SiteSettings(models.Model):
    site_name = models.CharField(max_length=100)
```

Routes are at `/<prefix>/<app_label>.<model_name>`, lowercase, without a trailing slash: `GET /api/blog.article`, `GET /api/blog.article/1`, `GET /api/blog.article/by_slug/getting-started`, `GET /api/blog.sitesettings`.

Decorator options (the same for `expose_model(Model, ...)`, used for models you cannot decorate, such as `django.contrib` or third-party models):

| Option | Effect |
| --- | --- |
| `singleton=True` | One route without a primary key: `GET`, plus `PUT`/`PATCH` that create the object on the first write. `GET` answers `404` until it exists. No list or delete. |
| `read_only=True` | `GET` routes only; writes answer `405`. |
| `fields=[...]` / `exclude=[...]` | Serialized fields (and model properties in `fields`). Not both. Left-out fields cannot be filtered or expanded, and are only searched when named in `search_fields` (system check `headless.W011` warns). |
| `lookup_fields=[...]` | Unique non-pk fields that get a `GET`-only `by_<field>/<value>` route. Not on singletons. |
| `search_fields=[...]` | Fields for DRF's `SearchFilter` (`?search=`). Defaults to serialized non-choice `CharField`s. `SearchFilter` itself must be added to `HEADLESS["DEFAULT_FILTER_BACKENDS"]`. |

Rules:

- Invalid options raise `ImproperlyConfigured` when the model module is imported. Pass lists or tuples: `fields=("title")` is a string.
- Call `expose_model()` in a models module, or in the `ready()` of an app listed before `headless.rest`. Later calls get no routes (`headless.W009`).
- Expose each model once.
- A user model needs a `fields` list (`headless.W007`). Exclude credential-like fields such as `api_token` (`headless.W006`).

## Permissions and authentication

The generated routes use `HEADLESS` settings that override `REST_FRAMEWORK` for those routes only:

- `HEADLESS["DEFAULT_PERMISSION_CLASSES"]` defaults to `IsAdminUser`, so everyone but staff gets `403`. It never falls back to `REST_FRAMEWORK`. For public content use `IsAuthenticatedOrReadOnly`, or `AllowAny` with `read_only=True` models (`AllowAny` with writable models triggers `headless.W002`).
- Authentication classes come from `REST_FRAMEWORK`, or from `HEADLESS["DEFAULT_AUTHENTICATION_CLASSES"]`.
- For a frontend or build step without a user, use `SecretKeyAuthentication`. A request with the key counts as staff; the read-only key only allows `GET`, `HEAD` and `OPTIONS`. Read keys from environment variables, never hard-code them:

```python
# mysite/settings.py
import os

HEADLESS = {
    "AUTH_SECRET_KEY": os.environ["HEADLESS_SECRET_KEY"],
    "AUTH_READ_ONLY_SECRET_KEY": os.environ["HEADLESS_READ_ONLY_SECRET_KEY"],
    "DEFAULT_AUTHENTICATION_CLASSES": ["headless.rest.authentication.SecretKeyAuthentication"],
    "DEFAULT_PAGINATION_CLASS": "headless.rest.pagination.PageNumberPagination",
    "PAGE_SIZE": 25,
    "DEFAULT_SERIALIZER_CLASS": "headless.rest.serializers.FlexibleSerializer",
    "SCHEMA": True,
}
```

Clients send the key in the `X-Secret-Key` header (`HEADLESS["AUTH_SECRET_KEY_HEADER"]`).

## Querying the API

- **Pagination**: with `PageNumberPagination`, lists answer `{"pagination": {"count", "pages", "current", "limit", "links": {"self", "next", "previous"}}, "data": [...]}`. Use `?page=` and `?limit=` (capped by `HEADLESS["MAX_PAGE_SIZE"]`, default 100). Lists are ordered by primary key.
- **Filtering** (`LookupFilter`, on by default): query parameters are Django field lookups: `?published=true`, `?title__icontains=django`, `?created_at__gte=2026-01-01`, `?category__name=Tutorials`, `?id__in=1,2,3`, `?created_at__range=2026-01-01,2026-06-30`. Prefix with `~` to exclude: `?~category=3`. Parameters combine with AND. `regex` and `iregex` are disallowed. Unknown fields, lookups or values answer `400` with the reason.
- **Expansion** (only with `FlexibleSerializer`): `?expand=category`, `?expand=category.articles` (max depth 2), `?fields=title,slug`, `?omit=body`. Only relations to exposed models expand; reverse relations use their `related_name` or `<model>_set`. `FlexibleSerializer` also serializes model properties as read-only fields.

## OpenAPI schema and TypeScript client

With `HEADLESS["SCHEMA"] = True` the schema is at `/api/schema` (same permissions as the routes). Without a server: `python manage.py generateschema --generator_class headless.rest.schema.SchemaGenerator --format openapi-json --file openapi.json`.

In the frontend:

```bash
npm install @django-headless/client
npx headless generate --url https://example.org/api/schema --out src/headless.ts
```

`generate` reads the key from `DJANGO_HEADLESS_SECRET_KEY` (or `--secret-key`); use a key that may write, or every model is typed read-only. Regenerate after changing exposed models.

```ts
// src/api.ts
import { DjangoRestClient } from "@django-headless/client";
import type { Models } from "./headless";

export const api = new DjangoRestClient<Models>({
    baseUrl: "https://example.org/api",
    secretKey: process.env.HEADLESS_SECRET_KEY,
});

const { data } = await api.model("blog.article").list({
    filters: { title__icontains: "django" },
    exclude: { category: 4 },
    expand: ["category"],
});
const article = await api.model("blog.article").retrieveBy("slug", "getting-started");
const settings = await api.singleton("blog.sitesettings").retrieve();
```

Models also have `retrieve`, `create`, `update`, `partialUpdate`, `destroy`, `iterate` and `all`. Errors throw `DjangoRestError` with `status` and `body`. Keep the secret key on the server side of the frontend.

## Verifying

- Run `python manage.py check` (and `check --deploy` before deploying). Fix `headless.E*` errors and read `headless.W*` warnings; `headless.W005` flags a misspelled `HEADLESS` key, which silently falls back to the default.
- `runserver` prints a boot log with the exposed models, the route count and the authentication and permission classes in use.
- Request a route with the credentials the frontend uses, for example `curl -H "X-Secret-Key: $HEADLESS_SECRET_KEY" http://localhost:8000/api/blog.article`.
