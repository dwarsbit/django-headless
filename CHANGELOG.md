# Changelog

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
