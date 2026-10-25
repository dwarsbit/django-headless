---
sidebar_position: 11
---

# 🔌 TypeScript client

The `@django-headless/client` npm package is a client for the API, written in TypeScript. It requests the generated routes from the frontend or a static site build, and generates the types of your exposed models from the [OpenAPI schema](./schema.md), so a typo in a field, filter or relation fails the type check instead of the request.

The client uses the global `fetch` and has no dependencies. It runs in Node.js 18 and later, in browsers and in edge runtimes.

## Installation

```bash
npm install @django-headless/client
```

## Requesting the API

Create a client with the URL the API is included at, and request the routes of a model by its label:

```ts
// src/api.ts
import { DjangoRestClient } from "@django-headless/client";

export const api = new DjangoRestClient({
    baseUrl: "https://example.org/api",
    secretKey: process.env.HEADLESS_SECRET_KEY,
});

const { pagination, data } = await api.model("blog.article").list({
    filters: { published: true },
});
```

`secretKey` is sent in the `X-Secret-Key` header of [`SecretKeyAuthentication`](./authentication.md). Without the generated types, every label is accepted and objects have the type `{ [key: string]: unknown }`.

## Generating the types

The client types the routes from the OpenAPI schema of the API. To generate the types:

1. Enable the schema route; see [Enabling the schema](./schema.md#enabling-the-schema).

2. Generate the types into a file of the frontend:

   ```bash
   npx headless generate --url https://example.org/api/schema --out src/headless.ts
   ```

   The command reads the secret key of the schema route from the `DJANGO_HEADLESS_SECRET_KEY` environment variable, or from `--secret-key`. Send other headers with `--header "Authorization: Token your-token"`.

3. Pass the `Models` type of the file to the client:

   ```ts
   // src/api.ts
   import { DjangoRestClient } from "@django-headless/client";
   import type { Models } from "./headless";

   export const api = new DjangoRestClient<Models>({
       baseUrl: "https://example.org/api",
       secretKey: process.env.HEADLESS_SECRET_KEY,
   });
   ```

Without a schema route, generate the types from a schema file of `generateschema`; see [Generating a file](./schema.md#generating-a-file):

```bash
npx headless generate --file openapi.json --out src/headless.ts
```

The file has an interface per model, such as `BlogArticle` for `blog.Article`, and a `BlogArticleInput` for the body of a create or update request. Run the command again when the exposed models change, for example in a script of the frontend:

```json
{
    "scripts": {
        "generate": "headless generate --url https://example.org/api/schema --out src/headless.ts"
    }
}
```

The schema lists the operations the requester may perform. Generate the types with a key that may write, or the client types every model as read only.

## Models

`api.model(label)` has a method per route:

```ts
const articles = api.model("blog.article");

await articles.list({ filters: { published: true }, page: 2 });
await articles.retrieve(1);
await articles.retrieveBy("slug", "getting-started-with-django");
await articles.create({ title: "Getting started with Django", category: 2 });
await articles.update(1, { title: "Getting started with Django", category: 2 });
await articles.partialUpdate(1, { title: "Getting started" });
await articles.destroy(1);
```

- `list()` answers the [pagination envelope](./pagination.md#the-envelope), with the objects in `data`. Without a pagination class, it answers the list of objects.
- `retrieveBy()` requests a [lookup route](./models.md#lookup-routes) such as `/api/blog.article/by_slug/<value>`. The generated types only accept the fields of the lookup routes.
- `create()`, `update()` and `partialUpdate()` send JSON. Pass a `FormData` instead to upload files.
- A read-only model has the read methods only.

To request every page, iterate over the objects or collect them with `all()`. Both request one page at a time:

```ts
for await (const article of api.model("blog.article").iterate({ filters: { published: true } })) {
    console.log(article.title);
}

const articles = await api.model("blog.article").all({ limit: 100 });
```

## Singletons

`api.singleton(label)` requests the route of a [singleton](./singletons.md):

```ts
const settings = api.singleton("blog.sitesettings");

await settings.retrieve();
await settings.partialUpdate({ site_name: "The Django blog" });
```

## Filtering and searching

`filters` takes the [lookups](./filtering.md) of the list route, and `exclude` the [exclusions](./filtering.md#exclusions):

```ts
await api.model("blog.article").list({
    filters: {
        title__icontains: "django",
        created_at__gte: new Date("2026-01-01"),
        category__in: [2, 3],
    },
    exclude: { category: 4 },
    search: "getting started",
    ordering: ["-created_at"],
    limit: 20,
});
```

```http
GET /api/blog.article?title__icontains=django&created_at__gte=2026-01-01T00:00:00.000Z&category__in=2,3&~category=4&search=getting+started&ordering=-created_at&limit=20
```

Lists are sent as comma-separated values, dates as ISO 8601 strings and `null` as `null`. With the generated types, the value of each field and lookup is type-checked. Other lookups, such as `created_at__year`, and lookups across relations, such as `category__name__icontains`, are accepted without type checks on their values.

`search` and `ordering` need a search and an ordering filter backend; see [DRF overrides](./settings.md#drf-overrides).

## Expanding relations

With [`FlexibleSerializer`](./serializers.md), `expand` includes related objects instead of primary keys, and `fields` and `omit` select the fields. The generated types follow them: the type of the response has the expanded objects and only the selected fields.

```ts
const article = await api.model("blog.article").retrieve(1, {
    expand: ["category", "review_set"],
    omit: ["body"],
});

article.category.name; // a BlogCategory, not a primary key
article.review_set[0].rating; // a list of BlogReview
```

Paths such as `category.articles` expand deeper. `fields` and `omit` type the top-level fields only: `fields: ["category.name"]` keeps all fields in the type of `category`.

## Options

| Option            | Default          | Description                                                                                               |
| ----------------- | ---------------- | --------------------------------------------------------------------------------------------------------- |
| `baseUrl`         | required         | The URL the API is included at.                                                                           |
| `secretKey`       | none             | The secret key of `SecretKeyAuthentication`.                                                              |
| `secretKeyHeader` | `"X-Secret-Key"` | The header of the secret key, as in `HEADLESS["AUTH_SECRET_KEY_HEADER"]`.                                 |
| `headers`         | none             | Headers of every request, or a function that returns them, for example with a token.                     |
| `fetch`           | global `fetch`   | The `fetch` function to use.                                                                              |
| `init`            | none             | Other options for `fetch` of every request, such as `cache` or `credentials`.                            |
| `exclusionSymbol` | `"~"`            | The symbol of exclusions, as in `HEADLESS["FILTER_EXCLUSION_SYMBOL"]`.                                    |
| `searchParam`     | `"search"`       | The query parameter of `search`, as in `HEADLESS["SEARCH_PARAM"]`.                                        |
| `orderingParam`   | `"ordering"`     | The query parameter of `ordering`, as in `HEADLESS["ORDERING_PARAM"]`.                                    |

Every method takes the options of one request as its last argument: `headers`, `signal` to cancel the request with an `AbortController`, and `init` for other options of `fetch`. In Next.js, pass the cache options of a request in `init`:

```ts
const { data } = await api.model("blog.article").list({ filters: { published: true } }, { init: { next: { revalidate: 60 } } });
```

## Errors

A response with an error status throws a `DjangoRestError`, with the status and the parsed body:

```ts
import { DjangoRestError } from "@django-headless/client";

try {
    await api.model("blog.article").retrieveBy("slug", "missing");
} catch (error) {
    if (error instanceof DjangoRestError && error.status === 404) {
        // Show the not found page
    }
    throw error;
}
```

`body` holds the JSON of the response, such as `{ "detail": "Not found." }`, or the validation errors per field of a `400 Bad Request`.

## Other routes

`api.request()` sends a request to any path of the API and parses the JSON response:

```ts
const result = await api.request("GET", "blog.article/1");
```

## Related pages

- [OpenAPI schema](./schema.md)
- [Authentication](./authentication.md)
- [Filtering](./filtering.md)
- [Serializers](./serializers.md)
