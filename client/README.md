# @django-headless/client

A TypeScript client for the API of [Django Headless](https://djangoheadless.org), which generates a REST API for your Django models. Request the generated routes from the frontend or a static site build, with types generated from the OpenAPI schema of the API.

Read the documentation at [djangoheadless.org/docs/client](https://djangoheadless.org/docs/client).

## Features

- **Routes per model**: list, retrieve, lookup, create, update and delete, and the route of singletons.
- **Generated types**: an interface per exposed model, generated from the OpenAPI schema.
- **Typed queries**: filters, exclusions, search, ordering and pagination, with the types of the fields.
- **Typed expansion**: the response type follows `expand`, `fields` and `omit`.
- **No dependencies**: built on `fetch`, for Node.js 18 and later, browsers and edge runtimes.

## Quick start

1. Install the package:

   ```bash
   npm install @django-headless/client
   ```

2. Enable the schema of the API with `HEADLESS["SCHEMA"]`, and generate the types:

   ```bash
   npx @django-headless/client generate --url https://example.org/api/schema --out src/headless.ts
   ```

   The command reads the secret key of the schema route from the `DJANGO_HEADLESS_SECRET_KEY` environment variable.

3. Request the API:

   ```ts
   // src/api.ts
   import { DjangoRestClient } from "@django-headless/client";
   import type { Models } from "./headless";

   const api = new DjangoRestClient<Models>({
       baseUrl: "https://example.org/api",
       secretKey: process.env.HEADLESS_SECRET_KEY,
   });

   const { data } = await api.model("blog.article").list({
       filters: { published: true },
       expand: ["category"],
   });
   ```

## License

MIT
