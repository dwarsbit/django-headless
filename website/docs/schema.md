---
sidebar_position: 10
---

# 📘 OpenAPI schema

Django Headless can describe the generated routes in an [OpenAPI](https://spec.openapis.org/oas/v3.0.3) 3.0 schema. Typed clients and API tools read it: a frontend generates its TypeScript types from the schema instead of writing them by hand, and the types follow the models.

## Enabling the schema

The schema needs the `uritemplate` and `inflection` packages, and PyYAML for YAML output. Install them with the `schema` extra:

```bash
pip install "django-headless[schema]"
```

Then enable the schema route with `HEADLESS["SCHEMA"]`:

```python
# mysite/settings.py
HEADLESS = {
    "SCHEMA": True,
    "SCHEMA_TITLE": "Blog API",
}
```

The schema is served next to the generated routes, at `/api/schema`:

```http
GET /api/schema
```

The default format is JSON. Add `?format=openapi` for YAML, which needs PyYAML. A request with an `Accept` header gets the format it asks for.

`python manage.py check` reports an error (`headless.E003`) when `SCHEMA` is enabled and the packages are missing; see [System checks](./checks.md#headlesse003).

## What the schema describes

The schema covers the generated routes only, not the other views of your project. For each route it lists:

- **Operations** with unique IDs such as `listBlogArticles` and `retrieveBlogArticle`, a description and a tag per model.
- **Components** named after the model, such as `BlogArticle` for `blog.Article`, with the types of its fields. Model properties are read-only fields.
- **Pagination**: the `page` and `limit` query parameters, and the `pagination` and `data` envelope of the [list response](./pagination.md#the-envelope).
- **Filters**: a query parameter for each filterable field of a list route, typed from the model field, with the choices of a field that has them. [Lookups](./filtering.md) such as `views__gte` and exclusions with `~` apply to every one of them and are mentioned in each description.
- **Expansion**: the `expand`, `fields` and `omit` query parameters of [`FlexibleSerializer`](./serializers.md), with the names of the expandable relations.
- **Lookup routes** such as `/api/blog.article/by_slug/{value}`, with the type of the field as the type of `value`.
- **Authentication**: the secret key header of [`SecretKeyAuthentication`](./authentication.md), and the token, basic and session authentication of Django REST Framework. Other authentication classes are not described.

## Access to the schema

The schema route requires what the generated routes require, which is a staff user by default; see [Permissions](./permissions.md). It lists the operations the requester may perform: with `IsAuthenticatedOrReadOnly`, an anonymous request sees the read operations and not the write operations.

Authenticate the request for the schema like any other request, for example with the `X-Secret-Key` header when you generate types in a build step.

## Settings

| Setting                     | Default  | Description                                    |
| --------------------------- | -------- | ---------------------------------------------- |
| `SCHEMA`                    | `False`  | Whether the schema route exists.               |
| `SCHEMA_TITLE`              | `"API"`  | The title of the schema.                       |
| `SCHEMA_DESCRIPTION`        | `""`     | The description of the schema.                 |
| `SCHEMA_VERSION`            | `"1.0.0"` | The version of your API, not of Django Headless. |

## Generating a file

To commit the schema or generate it in a build step, use Django REST Framework's `generateschema` command with the Django Headless generator. It needs no `SCHEMA` setting and no running server:

```bash
python manage.py generateschema \
    --generator_class headless.rest.schema.SchemaGenerator \
    --format openapi-json \
    --file openapi.json
```

A generated file describes every operation, whatever the permissions of the routes.

## Extensions

The schema adds two [extensions](https://spec.openapis.org/oas/v3.0.3#specification-extensions) for typed clients. Tools that do not know them ignore them.

- **`x-filter`** is `true` on each filter parameter of a list route.
- **`x-expandable`** on the `expand` parameter maps each expandable relation to the component of its model, and tells whether it expands to a list:

  ```json
  {
      "category": { "component": "BlogCategory", "many": false },
      "review_set": { "component": "BlogReview", "many": true }
  }
  ```

The [TypeScript client](./client.md) reads them to type filters and expanded relations.

## Limitations

- **Expanded relations** are described as primary keys, as they are without `?expand=`. A response with `?expand=` has the related object in their place. The [TypeScript client](./client.md) types the expanded objects.
- **Custom schema classes**: when `REST_FRAMEWORK["DEFAULT_SCHEMA_CLASS"]` is not Django REST Framework's `AutoSchema`, for example with [drf-spectacular](https://drf-spectacular.readthedocs.io/), the generated routes keep your class and the schema route of Django Headless does not describe them. Use the schema view of that package instead.

## Related pages

- [TypeScript client](./client.md)
- [Filtering](./filtering.md)
- [Pagination](./pagination.md)
- [Settings reference](./settings.md#schema-settings)
