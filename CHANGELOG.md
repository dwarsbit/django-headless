# Changelog

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

## v1.0.0-beta.1
Initial pre-release! 🎉

## v1.0.0-beta.2
- 👾 Fixes issue with singleton view sets
- 🎁 Adds a new secret key authentication class

## v1.0.0-beta.3

- 🧹 Refactor REST builder logic
- 🎁 Adds a new flexible serializer
- ⚙️ The default serializer can now be changed via `HEADLESS.DEFAULT_SERIALIZER`

## v1.0.0-beta.4

- 🧹 Rename headless decorator to `register` in line with Django admin
- 
## v1.0.0-beta.5

- 🧹 Rename headless decorator to `expose` for better display of intent
- 🎁 Add pagination class
- 👾 Fixes issue with singleton routes not being registered
- 
## v1.0.0-beta.6

- 🎁 Add `search_fields` setting
- 👾 Bugfixes