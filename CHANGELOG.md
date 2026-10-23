# Changelog

## Unreleased (v1.0.0)

- 🎁 New `lookup_fields` decorator option: fetch an object by a unique field at `GET /api/blog.article/by_slug/<value>`, next to the detail route by primary key
- 🛡️ Lookup routes are opt-in and `GET`-only; `@expose()` raises `ImproperlyConfigured` when a lookup field is unknown, not unique, the primary key, or set on a singleton
- 🛡️ Lookup routes report `view.action == "retrieve"`, so action-based permissions, serializers and throttles apply as on the detail route; `view.lookup_by` holds the field of the lookup
- 🛡️ Filtering only targets exposed fields: the `LookupFilter` rejects fields hidden by `fields`/`exclude`, and only traverses relations into exposed models, on their exposed fields. Previously hidden values (e.g. `?author__password__startswith=`) could be probed through filters
- 🛡️ Default `search_fields` no longer include fields hidden by `fields`/`exclude`
- 🛡️ `FlexibleSerializer` honors `fields`/`exclude`: expanded relations use the related model's options instead of `__all__`, and hidden relations and properties are no longer expanded or added
- ⚠️ `LookupFilter` on custom views of models that aren't exposed only filters on the fields of the view's serializer
- 🎁 `fields` in `@expose()` may list model properties
- 🛡️ `HEADLESS["DEFAULT_PERMISSION_CLASSES"]` now defaults to `IsAdminUser`: DRF enables session and basic authentication by default, so with `IsAuthenticated` any user account could modify content
- ⚠️ Regular authenticated users get `403` on generated routes by default; set `DEFAULT_PERMISSION_CLASSES` to `IsAuthenticated` to restore the previous behavior
- 🎁 `SecretKeyAuthentication` authenticates as a staff user, so the secret key keeps working with the new default
- 🎁 The boot log reports the authentication and permission classes the generated routes actually use, including DRF's defaults
- ⚙️ New `HEADLESS["AUTH_READ_ONLY_SECRET_KEY"]`: a second secret key that only allows `GET`, `HEAD` and `OPTIONS`, so a frontend no longer needs a key that can write
- ⚠️ `request.auth` is a `SecretKey` (with `read_only`) for requests authenticated by `SecretKeyAuthentication`, instead of `None`
- 🐛 A secret key header with non-ASCII characters is rejected with `401` instead of crashing with a `500`
- ⚙️ New `HEADLESS["MAX_PAGE_SIZE"]` (default `100`): caps the page size a client can request with `?limit=` on the generated routes. `PageNumberPagination` uses a maximum of `100` on your own views as well
- ⚙️ New `HEADLESS["FILTER_DISALLOWED_LOOKUPS"]` (default `["regex", "iregex"]`): regular expression lookups answer `400`, since costly patterns can keep the database busy and invalid ones caused a `500`
- ⚙️ New `HEADLESS["MAX_EXPANSION_DEPTH"]` (default `2`): limits how deep `FlexibleSerializer` relations can be expanded
- 🐛 Expanded relations are prefetched: one query per relation instead of one per item
- 🐛 `LookupFilter` only applies `DISTINCT` when a filter crosses a to-many relation, instead of on every filtered list
- 🛡️ Filter errors no longer include Django's internal error messages: each filter is validated on its own and answers with a message about the query parameter, such as `Unsupported lookup in 'title__startwith'.`
- 🐛 A `range` lookup with other than two values answers `400` instead of `500`
- 🐛 `LookupFilter` skips the query parameters of the route's other filter backends and pagination class, DRF's `format` and drf-flex-fields' parameters. With `SEARCH_PARAM` or `ORDERING_PARAM` set, or `LimitOffsetPagination`, those parameters answered `400 Field does not exist`
- 🐛 `LookupFilter` reads the `FILTER_*` and `NON_FILTER_FIELDS` settings on every request instead of once at import, so changes to `HEADLESS` (such as `override_settings` in tests) apply. Subclasses can still override `TRUE_VALUES`, `EXCLUDE_SYMBOL` and the other class attributes
- 🐛 `LookupFilter` only splits values on commas for the `in` and `range` lookups. Other lookups take the value as sent, so `?title=Hello, world` matches `Hello, world` instead of `Hello`
- 🐛 `LookupFilter` accepts `pk` for the primary key, also across relations (`?pk__in=1,2`, `?category__pk=2`), instead of answering `400 Field 'pk' does not exist`
- 🐛 The dot in a route label only matches a dot: `/api/blogXarticle` no longer serves the `blog.article` routes
- 🐛 The `limit` in the pagination envelope is the page size the request used (after `?limit=` and `MAX_PAGE_SIZE`), not the configured `PAGE_SIZE`
- 🐛 The boot log, and its PyPI version check, only run under `runserver` and known WSGI and ASGI servers (Gunicorn, Uvicorn, Daphne, Hypercorn, uWSGI, Waitress, Granian, mod_wsgi). Tests, Celery workers, `django-admin` commands and scripts no longer show it; set `HEADLESS["BOOT_LOG"]` to `True` for other servers
- 🐛 With autoreload, `runserver` shows the boot log once instead of twice
- 🐛 The PyPI version check in the boot log never stops the project from starting: timeouts, HTTP and connection errors and cache backend errors are caught
- 🐛 The boot log only reports a new version when PyPI's version is newer than the installed one, including pre-releases, instead of whenever they differ
- ⚙️ New `HEADLESS["VERSION_CHECK"]` (default `True`): set it to `False` to never contact PyPI from the boot log
- 🐛 Reverse relations are expanded by the name they have on an object: on Django 5.0, a reverse foreign key without `related_name` (such as `review_set`) could not be expanded, and a reverse one-to-one with a `related_query_name` was expanded under that query name

## v1.0.0-rc.9

- 🐛 Fixes `runserver` crashing at boot when authentication classes are configured: as import paths in `REST_FRAMEWORK`, or only in `HEADLESS.DEFAULT_AUTHENTICATION_CLASSES`
- 💬 The boot log now reports the authentication classes the generated routes actually use (`HEADLESS` first, then `REST_FRAMEWORK`)

## v1.0.0-rc.8

- 🐛 Fixes `AppRegistryNotReady` during `django.setup()` / `makemigrations`: `@expose()` now validates `search_fields`, `fields` and `exclude` against the model's forward fields only, since collecting reverse relations requires all models to be loaded, which is never the case while the models module is still being imported

## v1.0.0-rc.7

- 🛡️ Safe defaults for generated routes: `HEADLESS.DEFAULT_PERMISSION_CLASSES` now defaults to `IsAuthenticated`, so freshly exposed models are never accidentally public, and `HEADLESS.DEFAULT_FILTER_BACKENDS` defaults to the `LookupFilter`
- ⚠️ Generated routes no longer inherit the permission classes and filter backends from `REST_FRAMEWORK`; set them explicitly under `HEADLESS` to customize
- 💬 The boot log recognizes `HEADLESS`-scoped authentication classes and no longer claims public endpoints by default

## v1.0.0-rc.6

- ⚙️ DRF-level settings can now be scoped to the generated routes via `HEADLESS`: `DEFAULT_RENDERER_CLASSES`, `DEFAULT_PARSER_CLASSES`, `DEFAULT_AUTHENTICATION_CLASSES`, `DEFAULT_FILTER_BACKENDS`, `DEFAULT_PAGINATION_CLASS`, `PAGE_SIZE`, `SEARCH_PARAM` and `ORDERING_PARAM` override the `REST_FRAMEWORK` value for headless routes only
- 👾 Accept already-imported classes in list-valued settings (e.g. filter backends), matching DRF's behavior

## v1.0.0-rc.5

- ⚙️ New `HEADLESS.DEFAULT_PERMISSION_CLASSES` setting to override DRF's permissions for the generated routes only
- 🎁 New `@expose()` options: `fields` / `exclude` to control exposed fields, and `read_only` for GET-only endpoints
- 🛡️ `@expose()` now fails fast with clear errors on non-models, unknown field names and conflicting options

## v1.0.0-rc.4

- 🧹 Routes are now built in every context, not just runserver — they exist under management commands, tests and WSGI/ASGI entrypoints
- ⚙️ New `HEADLESS.BOOT_LOG` setting to always show or never show the boot log (default auto-detects server mode)
- 🎁 Generated list endpoints are ordered by `pk`, so paginated pages are stable for frontend consumers
- 🧹 Cleans up the REST builder internals (removed duplicate/dead code)
- 🧪 Adds end-to-end tests covering the generated routes

## v1.0.0-rc.3

- 👾 Fixes case-sensitive text filtering: lookup values are no longer lowercased (boolean and null matching is still case-insensitive)
- 👾 Fixes singleton view sets: proper queryset contract and race-safe singleton creation, so concurrent `PUT`s can no longer create duplicate singletons
- 👾 Filter errors now include the actual reason instead of a generic message
- 🎁 The boot version check is now cached, so a slow or unreachable PyPI can stall at most one boot
- 📚 Documents `?expand=` and model properties as opt-in via `HEADLESS.DEFAULT_SERIALIZER_CLASS`

## v1.0.0-beta.6

- 🎁 Add `search_fields` setting
- 👾 Bugfixes

## v1.0.0-beta.5

- 🧹 Rename headless decorator to `expose` for better display of intent
- 🎁 Add pagination class
- 👾 Fixes issue with singleton routes not being registered

## v1.0.0-beta.4

- 🧹 Rename headless decorator to `register` in line with Django admin

## v1.0.0-beta.3

- 🧹 Refactor REST builder logic
- 🎁 Adds a new flexible serializer
- ⚙️ The default serializer can now be changed via `HEADLESS.DEFAULT_SERIALIZER_CLASS`

## v1.0.0-beta.2
- 👾 Fixes issue with singleton view sets
- 🎁 Adds a new secret key authentication class

## v1.0.0-beta.1
Initial pre-release! 🎉
