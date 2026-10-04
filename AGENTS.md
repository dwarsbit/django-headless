# AGENTS.md

Guidance for AI agents working in this repository.

## What this project is

`django-headless` is a Django package that automatically generates a REST API for Django models. A user decorates a model with `@expose()` and gets standard DRF endpoints (list, detail, CRUD) at `/api/<app_label>.<model_name>/` with no manual serializer, viewset, or URL wiring. It also supports singleton models (settings/config objects exposed as a single resource) and auto-derived filtering, search, and sparse/expanded field selection.

The primary use case is running Django as the backend of a JAMstack setup: Django serves content through this generated REST API (headless CMS), while the frontend lives elsewhere (Next.js, Astro, etc.). Assume changes should keep the API predictable and read-friendly for such frontend consumers.

## Tech stack

- Python >= 3.12, Django >= 5.0 (< 7.0), DRF >= 3.16 (< 4.0)
- `drf-flex-fields` (expandable/related fields), `rich` (boot-time console output)
- Packaging: Poetry (`poetry-core` build backend)
- Formatting: black, line length 120, target py312
- Tests: pytest + pytest-django (settings in `pytest.ini`, point at `tests/headless/test_settings.py`)

## Repository layout

```
headless/                    # The package itself
  __init__.py               # Public API: expose(), expose_model(), __version__
  registry.py               # HeadlessRegistry: model -> ModelConfig (model, singleton, search_fields)
  settings.py               # HEADLESS-namespaced settings object (headless_settings), DRF-style
  apps.py                   # AppConfig.ready(): runserver-only boot log, auth/version checks
  utils.py                  # log(), is_runserver(), auth-config helpers, version check
  rest/
    apps.py                 # AppConfig.ready(): runs RestBuilder (runserver only)
    builder/                # Dynamic API construction
      base.py               # RestBuilder: iterates registry, registers routes
      serializer.py         # get_serializer(): dynamic ModelSerializer subclass per model
      viewset.py            # get_view_set(): ModelViewSet or SingletonViewSet subclass per model
    viewsets.py             # SingletonViewSet: retrieve/update/partial_update, creates on update if missing
    serializers.py          # FlexibleSerializer: flex-fields + model properties as read-only fields
    filters/                # LookupFilter backend (all ORM lookups per field, ~ exclusion symbol, type casting)
    authentication.py       # SecretKeyAuthentication (X-Secret-Key header, constant-time compare)
    pagination.py           # PageNumberPagination with custom envelope {pagination: {...}, data: [...]}
    routers.py              # DefaultRouter + singleton_urls
    urls.py                 # urlpatterns = router urls + singleton urls
tests/                      # pytest suite (mirrors package layout)
  conftest.py               # Configures minimal Django settings + django.setup()
  headless/test_settings.py # Django settings module used by pytest-django
scripts/
  test_wrapper.py           # Poetry entry points: test, test-verbose, test-cov, build, publish
```

## How it works (architecture)

1. `@expose(singleton=False, search_fields=None)` registers a model class in `headless_registry`, keyed by `model._meta.label_lower`. Without `search_fields`, all non-choice `CharField` fields become searchable.
2. On app ready (server mode only, guarded by `is_runserver()`), `RestBuilder` iterates the registry and dynamically builds a serializer class and a viewset class per model (both cached by `model._meta.label`).
3. Regular models are registered on `rest_router` at `<label_lower>/` (e.g. `blog.blogpost`). Singletons get explicit paths in `singleton_urls` mapping GET/PUT/PATCH to retrieve/update/partial_update.
4. `FlexibleSerializer` auto-adds model properties as read-only fields and exposes all relations to other registered models as expandable (via `?expand=`), so nested content is available to frontend consumers without extra endpoints.
5. All runtime configuration lives under the `HEADLESS` dict in Django settings (see `headless/settings.py` DEFAULTS); DRF-level config (filter backend, auth classes, pagination) goes in the project's `REST_FRAMEWORK` setting.

Note: builder and boot log only run in server mode; management commands and plain imports stay silent. Keep that behavior when refactoring.

## Commands

Use the Poetry scripts (they are the documented standard; `build` and `publish` run tests first as quality gates):

```bash
poetry run test          # pytest
poetry run test-verbose  # pytest -v
poetry run test-cov      # pytest --cov=headless --cov-report=term
poetry run build         # tests, then poetry build
poetry run publish       # tests, then poetry publish
```

Run tests before considering any change done. New behavior needs tests in `tests/headless/...` mirroring the existing style.

## Conventions

- Format with black (line length 120). Do not reformat unrelated code.
- Commit messages follow conventional commits: `feat:`, `fix:`, `chore:`, `docs:`, etc. (see `git log`).
- Public API is what `headless/__init__.py` and `headless/rest/filters/__init__.py` export, plus the DRF integration points (`LookupFilter`, `SecretKeyAuthentication`, pagination class, `HEADLESS` settings). Keep these stable; treat them as the package's backward-compatibility surface.
- The project's own docs (README, CHANGELOG, console output) use emoji; match that style in user-facing strings there, but keep code and commit messages plain.

## Release flow

1. Bump the version in **both** `pyproject.toml` and `headless/__init__.py` (`__version__`) — they must stay in sync.
2. Add an entry to `CHANGELOG.md` describing user-facing changes.
3. Run `poetry run build` (tests run first; it aborts on failure).
4. Publish with `poetry run publish`, then tag the release (e.g. `v1.0.0-rc.2`) and push the tag.
