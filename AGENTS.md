# AGENTS.md

Guidance for AI agents working in this repository.

## What this project is

`django-headless` is a Django package that automatically generates a REST API for Django models. A user decorates a model with `@expose()` and gets standard DRF endpoints (list, detail, CRUD) at `<app_label>.<model_name>` (e.g. `/api/blog.article`, under whatever prefix the project mounts `headless.rest.urls` at) with no manual serializer, viewset, or URL wiring. It also supports singleton models (settings/config objects exposed as a single resource), read-only models, field control, opt-in lookup routes by unique fields (`by_<field>/<value>`), ORM-lookup filtering, search, and (opt-in) sparse/expanded field selection.

The primary use case is running Django as the backend of a JAMstack setup: Django serves content through this generated REST API (headless CMS), while the frontend lives elsewhere (Next.js, Astro, etc.). Assume changes should keep the API predictable and read-friendly for such frontend consumers.

## Tech stack

- Python >= 3.12, Django >= 5.2 (< 7.0), DRF >= 3.18 (< 4.0); CI tests Python 3.12/3.13 against Django 5.2, 6.0 and 6.1. The minimum Django version is the oldest one that still receives security updates; DRF 3.18 is the first release supporting Django 6.1
- `drf-flex-fields` (expandable/sparse fields), `rich` (boot-time console output)
- Packaging: Poetry (`poetry-core` build backend)
- Formatting: black, line length 120, target py312
- Tests: pytest + pytest-django (`pytest.ini` points at `tests.headless.test_settings`)
- Docs site: Docusaurus (Node 22) in `website/`, deployed to djangoheadless.org

## Repository layout

```
headless/                    # The package itself
  __init__.py               # Public API: expose(), expose_model(), __version__
  registry.py               # HeadlessRegistry: model -> ModelConfig; validates all @expose() options
  settings.py               # HEADLESS-namespaced settings object (headless_settings), DRF-style
  apps.py                   # AppConfig.ready(): registers the system checks, boot log (version check, exposed models, auth status)
  checks.py                 # Django system checks (headless.E00x/W00x), documented in website/docs/checks.md
  utils.py                  # log(), is_runserver(), is_boot_log_enabled(), auth-config helpers, version check
  rest/
    apps.py                 # AppConfig.ready(): runs RestBuilder (always; only its log is tied to the boot log)
    builder/                # Dynamic API construction
      base.py               # RestBuilder: iterates registry, registers routes
      serializer.py         # get_serializer(): DEFAULT_SERIALIZER_CLASS subclass per model (fields/exclude)
      viewset.py            # get_view_set(): Model/ReadOnlyModel/SingletonViewSet subclass per model,
                            #   lookup actions, apply_drf_overrides() for HEADLESS-scoped DRF settings
    viewsets.py             # SingletonViewSet (race-safe create on update), LookupFieldsMixin
    serializers.py          # FlexibleSerializer: flex-fields + model properties as read-only fields
    filters/                # LookupFilter backend (all ORM lookups per field, ~ exclusion symbol, type casting)
    authentication.py       # SecretKeyAuthentication (X-Secret-Key header, constant-time compare)
    pagination.py           # PageNumberPagination with custom envelope {pagination: {...}, data: [...]}
    routers.py              # DefaultRouter (no trailing slash) + singleton_urls
    urls.py                 # urlpatterns = router urls + singleton urls
tests/                      # pytest suite (mirrors package layout)
  conftest.py               # Fallback minimal Django settings + django.setup()
  headless/test_settings.py # Django settings module used by pytest-django
  headless/test_main.py     # Registry, settings, utils and boot log tests
  headless/rest/            # Builder, viewsets, serializers, filters, pagination, auth and e2e tests
website/                    # Docusaurus docs site (djangoheadless.org); pages in website/docs/
STYLE.md                    # Writing style guide for README, docs website and CHANGELOG
scripts/
  test_wrapper.py           # Poetry entry points: test, test-verbose, test-cov, build, publish
.github/workflows/          # ci.yml (tests, black, docs build), docs-deploy.yml (Pages deploy on main)
```

## How it works (architecture)

1. `@expose()` (or `expose_model()`) registers a model in `headless_registry`, keyed by `model._meta.label_lower`. Options: `singleton`, `search_fields`, `fields`, `exclude`, `read_only`, `lookup_fields`. Without `search_fields`, all non-choice `CharField` fields become searchable.
2. Registration validates every option and raises `ImproperlyConfigured` on invalid input. This runs at model import time, during `django.setup()`, so misconfiguration stops the project at boot. Validation must only use forward fields (`_meta.fields` / `_meta.many_to_many`), never `_meta.get_fields()`, which raises `AppRegistryNotReady` at that point.
3. On app ready, `RestBuilder` iterates the registry and dynamically builds a serializer class and a viewset class per model (both cached by `model._meta.label`). Routes are built in every context (runserver, management commands, tests, WSGI/ASGI).
4. Regular models are registered on `rest_router` at `<label_lower>` (e.g. `blog.article`). `read_only` models get a `ReadOnlyModelViewSet`. Singletons get explicit paths in `singleton_urls` mapping GET (and PUT/PATCH unless read-only) to retrieve/update/partial_update.
5. `lookup_fields` (opt-in, unique non-pk fields only) adds GET-only `by_<field>/<value>` actions through `LookupFieldsMixin`. On those routes `view.action` is `"retrieve"` (so action-based permissions apply) and `view.lookup_by` holds the field.
6. The serializer base is `HEADLESS.DEFAULT_SERIALIZER_CLASS`, a plain `ModelSerializer` by default. Setting it to `FlexibleSerializer` enables `?expand=` / `?fields=` / `?omit=` and model properties as read-only fields; relations to other registered models become expandable.
7. All configuration lives under the `HEADLESS` dict in Django settings (see `DEFAULTS` in `headless/settings.py`). DRF-level settings (renderers, parsers, authentication, permissions, filter backends, pagination, `PAGE_SIZE`, search/ordering params) can be set there to override `REST_FRAMEWORK` for the generated routes only. Defaults are safe: `IsAuthenticated` permissions and the `LookupFilter` backend.

Note: the boot log is shown in server mode only (or as forced by `HEADLESS.BOOT_LOG`); management commands and plain imports stay silent. Keep that behavior when refactoring.

## Commands

Use the Poetry scripts (they are the documented standard; `build` and `publish` run tests first as quality gates):

```bash
poetry run test                       # pytest
poetry run test-verbose               # pytest -v
poetry run test-cov                   # pytest --cov=headless --cov-report=term
poetry run black --check headless tests  # formatting check, as in CI
poetry run build                      # tests, then poetry build
poetry run publish                    # tests, then poetry publish
cd website && npm ci && npm run build # docs site build (fails on broken links)
```

Run tests before considering any change done. New behavior needs tests in `tests/headless/...` mirroring the existing style; route behavior is best covered end to end in `tests/headless/rest/test_e2e.py`.

## Conventions

- Format with black (line length 120). Do not reformat unrelated code.
- Commit messages follow conventional commits: `feat:`, `fix:`, `chore:`, `docs:`, `test:`, etc. (see `git log`).
- Pull request titles and descriptions are always written in English, regardless of the language used in the conversation.
- Public API is what `headless/__init__.py` and `headless/rest/filters/__init__.py` export, plus the DRF integration points (`LookupFilter`, `SecretKeyAuthentication`, pagination class, `FlexibleSerializer`, `HEADLESS` settings, the `@expose()` options). Keep these stable; treat them as the package's backward-compatibility surface.
- Prefer secure, opt-in defaults: nothing should become public or exposed (routes, fields, lookups) without the user asking for it.
- User-facing changes update the docs in `website/docs/`, the README feature list where relevant, and `CHANGELOG.md`.
- User-facing text (README, docs website, CHANGELOG, console output) follows `STYLE.md`: voice, terminology, emoji use and code example conventions. Keep code and commit messages plain.

## Release flow

1. Bump the version in **both** `pyproject.toml` and `headless/__init__.py` (`__version__`) — they must stay in sync.
2. Add an entry to `CHANGELOG.md` describing user-facing changes (rename an `Unreleased` heading to the version).
3. Run `poetry run build` (tests run first; it aborts on failure).
4. Publish with `poetry run publish`, then tag the release (e.g. `v1.0.0-rc.2`) and push the tag.
