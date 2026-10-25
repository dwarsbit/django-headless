# Changelog

## Unreleased

- 🎁 Add an OpenAPI schema of the generated routes. Enable it with `HEADLESS["SCHEMA"]` for a schema route at `<prefix>/schema` (JSON, or YAML with `?format=openapi`), or generate a file with `python manage.py generateschema --generator_class headless.rest.schema.SchemaGenerator`. It describes the models, pagination envelope, filters, `expand`, `fields` and `omit` parameters, lookup routes and authentication. Install its packages with `pip install "django-headless[schema]"`.
- ⚙️ Add the `SCHEMA`, `SCHEMA_TITLE`, `SCHEMA_DESCRIPTION` and `SCHEMA_VERSION` settings.
- 🎁 Add the system check `headless.E003`, for an enabled schema without its packages.
- 🎁 Add the `django-headless` npm package, a TypeScript client for the API. `DjangoRestClient` requests the routes of models and singletons, with filters, exclusions, search, ordering, pagination, `expand`, `fields` and `omit`. `npx django-headless generate` generates the types of the exposed models from the OpenAPI schema, including the types of expanded relations.
- 🎁 Add the `x-filter` and `x-expandable` extensions to the OpenAPI schema, and type the primary key of detail routes after the primary key field.
- 🐛 Fix a query per object for many-to-many fields on list routes. Many-to-many fields are now prefetched with or without `?expand=`, including in expanded objects.
- 🎁 Load expanded foreign keys and one-to-one relations together with the object instead of with a second query.

## v1.0.0

Initial release! 🎉
