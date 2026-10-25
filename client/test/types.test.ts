/**
 * Type tests: `npm run typecheck` checks them. At run time the calls go to
 * a fetch function that is never called, so only the types are tested.
 */
import { describe, expectTypeOf, it } from "vitest";

import { DjangoRestClient, type ModelDefinition, type Paginated } from "../src/index.js";
import type {
  HeadlessRestDocArticle,
  HeadlessRestDocCategory,
  HeadlessRestDocNote,
  HeadlessRestDocSettings,
  HeadlessRestDocTag,
  Models,
} from "./fixtures/models.js";

const api = new DjangoRestClient<Models>({ baseUrl: "https://example.org/api", fetch: () => new Promise(() => {}) });
const articles = api.model("headless_rest.docarticle");

// Only build the requests, never await them
function types(check: () => unknown) {
  return check;
}

describe("types", () => {
  it("types list and detail responses", () => {
    types(async () => {
      expectTypeOf(await articles.list()).toEqualTypeOf<Paginated<HeadlessRestDocArticle>>();
      expectTypeOf(await articles.retrieve(1)).toEqualTypeOf<HeadlessRestDocArticle>();
      expectTypeOf(await articles.all()).toEqualTypeOf<HeadlessRestDocArticle[]>();
    });
  });

  it("types expanded relations", () => {
    types(async () => {
      const article = await articles.retrieve(1, { expand: ["category", "tags"] });
      expectTypeOf(article.category).toEqualTypeOf<HeadlessRestDocCategory | null>();
      expectTypeOf(article.tags).toEqualTypeOf<HeadlessRestDocTag[]>();
      expectTypeOf(article.title).toEqualTypeOf<string>();

      const nested = await articles.retrieve(1, { expand: ["tags.docarticle_set"] });
      expectTypeOf(nested.tags[0]!.docarticle_set).toEqualTypeOf<HeadlessRestDocArticle[]>();
      expectTypeOf(nested.category).toEqualTypeOf<number | null>();

      const all = await articles.retrieve(1, { expand: ["*"] });
      expectTypeOf(all.category).toEqualTypeOf<HeadlessRestDocCategory | null>();

      const { data } = await articles.list({ expand: ["category"] });
      expectTypeOf(data[0]!.category).toEqualTypeOf<HeadlessRestDocCategory | null>();

      // @ts-expect-error title is not a relation
      articles.retrieve(1, { expand: ["title"] });
    });
  });

  it("types sparse fields", () => {
    types(async () => {
      expectTypeOf(await articles.retrieve(1, { fields: ["id", "title"] })).toEqualTypeOf<{ id: number; title: string }>();
      expectTypeOf(await articles.retrieve(1, { omit: ["shout"] })).not.toHaveProperty("shout");

      // @ts-expect-error not a field
      articles.retrieve(1, { fields: ["subtitle"] });
    });
  });

  it("types filters and lookups", () => {
    types(async () => {
      articles.list({ filters: { status: "live", views__gte: 10, id__in: [1, 2], created__lt: new Date(), category__isnull: true } });
      // Other lookups and paths across relations are accepted
      articles.list({ filters: { created__year: 2026, category__name__icontains: "tutorials" } });

      // @ts-expect-error not a choice of status
      articles.list({ filters: { status: "archived" } });
      // @ts-expect-error views is a number
      articles.list({ filters: { views__gte: "ten" } });

      const pages = api.model("headless_rest.docpage");
      pages.retrieveBy("slug", "getting-started");
      // @ts-expect-error title has no lookup route
      pages.retrieveBy("title", "Getting started");
    });
  });

  it("types writes", () => {
    types(async () => {
      expectTypeOf(await articles.create({ title: "Getting started", tags: [] })).toEqualTypeOf<HeadlessRestDocArticle>();
      // @ts-expect-error title is required
      articles.create({ tags: [] });
      // @ts-expect-error shout is read-only
      articles.partialUpdate(1, { shout: "GETTING STARTED" });
      // @ts-expect-error the primary key is a number
      articles.retrieve("1");
    });
  });

  it("leaves the write methods out for read-only models", () => {
    const notes = api.model("headless_rest.docnote");
    expectTypeOf(notes).toHaveProperty("list");
    expectTypeOf(notes).not.toHaveProperty("create");
    expectTypeOf(notes).not.toHaveProperty("destroy");

    types(async () => {
      expectTypeOf(await notes.retrieve(1)).toEqualTypeOf<HeadlessRestDocNote>();
    });
  });

  it("separates models and singletons", () => {
    const settings = api.singleton("headless_rest.docsettings");
    types(async () => {
      expectTypeOf(await settings.retrieve()).toEqualTypeOf<HeadlessRestDocSettings>();
      settings.partialUpdate({ site_name: "Blog" });
    });

    // @ts-expect-error a singleton is not a model
    api.model("headless_rest.docsettings");
    // @ts-expect-error a model is not a singleton
    api.singleton("headless_rest.docarticle");
    // @ts-expect-error not an exposed model
    api.model("blog.article");
  });

  it("accepts any label without a Models type", () => {
    const untyped = new DjangoRestClient({ baseUrl: "https://example.org/api" });
    types(async () => {
      const { data } = await untyped.model("blog.article").list({ expand: ["category"], filters: { anything: 1 } });
      expectTypeOf(data[0]!).toEqualTypeOf<{ [key: string]: unknown }>();
      untyped.singleton("blog.sitesettings").retrieve();
    });
  });

  it("accepts models defined by hand", () => {
    interface Article {
      id: number;
      slug: string;
      title: string;
    }
    type HandModels = {
      "blog.article": ModelDefinition<Article, { lookups: { slug: string }; paginated: false }>;
    };

    const hand = new DjangoRestClient<HandModels>({ baseUrl: "https://example.org/api" });
    types(async () => {
      expectTypeOf(await hand.model("blog.article").list()).toEqualTypeOf<Article[]>();
      expectTypeOf(await hand.model("blog.article").retrieveBy("slug", "getting-started")).toEqualTypeOf<Article>();
    });
  });
});
