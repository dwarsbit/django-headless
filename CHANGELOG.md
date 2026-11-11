# Changelog

## 1.2.1 (unreleased)

- 🐛 Fix the object permissions of singletons: `PUT` and `PATCH` on a singleton route now check `has_object_permission`, like `GET` does.
- 🐛 Fix the API root view: it now uses the authentication and permission classes of the generated routes instead of the `REST_FRAMEWORK` defaults, so it no longer lists the exposed models to anonymous requests.
- 🐛 Fix reverse relations of hidden fields: a relation left out with `fields` or `exclude` on the model that defines it can no longer be filtered on or expanded from the related model.
- 🐛 Fix `exclude` for model properties: `@expose(exclude=["my_property"])` now leaves the property out of the API instead of raising `ImproperlyConfigured`.
- 🐛 `@expose()` now raises `ImproperlyConfigured` when `search_fields` name a field left out with `fields` or `exclude`. Searching such a field revealed its value.
- 🐛 Fix the error of a filter across a relation: a name the related model does not have now answers the same message as a hidden field.
- 🐛 Fix several exclusions in one request: `?~title=A&~views=2` now excludes the objects that match either one, instead of only those that match both.
- 🐛 Fix `LookupFilter` on your own views: it now filters generic views such as `ListAPIView`, and viewsets that define `get_queryset()` without a `queryset` attribute.
- 🐛 Fix a `500` for integers of more than 64 bits in the `in` and `range` lookups, and for filters on `DurationField` and `BinaryField`. Durations are now parsed; invalid values and binary fields answer `400 Bad Request`.
- 🐛 Fix the error message of an invalid boolean filter when `FILTER_TRUE_VALUES`, `FILTER_FALSE_VALUES` or `FILTER_NULL_VALUES` is a tuple.
- 🐛 Fix the routes of two exposed models with the same name in different apps, such as `blog.Article` and `news.Article`. They raised `ImproperlyConfigured` when the project started.
- 🐛 Fix the routes of a model without an `objects` manager: the generated routes now use the default manager of the model.
- 🐛 `@expose()` now raises `ImproperlyConfigured` on an abstract model, instead of failing when the routes are built.
- 🐛 Fix `HEADLESS["PAGE_SIZE"]` with `LimitOffsetPagination`: it now sets the default limit, where the list was not paginated without `?limit=`.
- 🐛 Fix `CursorPagination` on the generated routes: without a `created` field on the model, the list is ordered by primary key instead of answering `500`.
- 🐛 Fix a query per object for a wildcard below the first level, such as `?expand=author.*`.
- 🐛 Fix the boot log for `python manage.py --settings=... runserver`, `python -m waitress` and `mod_wsgi-express`.

## 1.2.0 (2026-11-06)

- 🎁 Add an agent skill for AI coding agents, in `skills/django-headless/SKILL.md`. Install it in Claude Code with `/plugin install django-headless --marketplace dwarsbit/django-headless`, or for other agents with `npx skills add dwarsbit/django-headless`.
- 🎁 Publish the documentation as Markdown for AI agents: `https://djangoheadless.org/llms.txt`, `https://djangoheadless.org/llms-full.txt` and `/docs/<page>.md` per page.

## 1.1.1 (2026-10-28)

- 🐛 Fix the prefetch of many-to-many fields and reverse relations that `?fields=` or `?omit=` leave out of the response. Expanded relations left out of the response are no longer loaded either.

## 1.1.0 (2026-10-28)

The stable release of v1.1.0-rc.1, with no changes since.

## v1.1.0-rc.1

- 🎁 Add an OpenAPI schema of the generated routes. Enable it with `HEADLESS["SCHEMA"]` for a schema route at `<prefix>/schema` (JSON, or YAML with `?format=openapi`), or generate a file with `python manage.py generateschema --generator_class headless.rest.schema.SchemaGenerator`. It describes the models, pagination envelope, filters, `expand`, `fields` and `omit` parameters, lookup routes and authentication. Install its packages with `pip install "django-headless[schema]"`.
- ⚙️ Add the `SCHEMA`, `SCHEMA_TITLE`, `SCHEMA_DESCRIPTION` and `SCHEMA_VERSION` settings.
- 🎁 Add the system check `headless.E003`, for an enabled schema without its packages.
- 🎁 Add the `@django-headless/client` npm package, a TypeScript client for the API. `DjangoRestClient` requests the routes of models and singletons, with filters, exclusions, search, ordering, pagination, `expand`, `fields` and `omit`. `npx headless generate` generates the types of the exposed models from the OpenAPI schema, including the types of expanded relations.
- 🎁 Add the `x-filter` and `x-expandable` extensions to the OpenAPI schema, and type the primary key of detail routes after the primary key field.
- 🎁 Type model properties in the OpenAPI schema after their return annotation, instead of as strings.
- 🐛 Fix the write operations in the OpenAPI schema for a request with the read-only secret key.
- 🐛 Fix a query per object for many-to-many fields on list routes. Many-to-many fields are now prefetched with or without `?expand=`, including in expanded objects.
- 🎁 Load expanded foreign keys and one-to-one relations together with the object instead of with a second query.

## v1.0.0

Initial release! 🎉
