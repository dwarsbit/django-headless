/**
 * End-to-end tests of the client against the Django project in e2e/django,
 * with the types the CLI generated from its schema route. Run them with
 * `npm run e2e`, which starts the server and generates the types first.
 */
import { describe, expect, expectTypeOf, it } from "vitest";

import { DjangoRestClient, DjangoRestError } from "../src/index.js";
import type { BlogArticle, BlogCategory, BlogReview, BlogTag, Models } from "./generated/headless.js";
import type { Models as ReadOnlyModels } from "./generated/read-only.js";

const baseUrl = process.env.E2E_API_URL as string;
const api = new DjangoRestClient<Models>({ baseUrl, secretKey: process.env.E2E_SECRET_KEY });
const articles = api.model("blog.article");

describe("generated types", () => {
  it("describe the models of the schema", () => {
    expectTypeOf<Models["blog.article"]["lookups"]>().toEqualTypeOf<{ slug: string }>();
    expectTypeOf<Models["blog.article"]["readOnly"]>().toEqualTypeOf<false>();
    expectTypeOf<Models["blog.page"]["readOnly"]>().toEqualTypeOf<true>();
    expectTypeOf<Models["blog.sitesettings"]["singleton"]>().toEqualTypeOf<true>();
    expectTypeOf<Models["blog.article"]["expandable"]["review_set"]["model"]>().toEqualTypeOf<"blog.review">();
    // A model property has the type of its return annotation
    expectTypeOf<BlogArticle["word_count"]>().toEqualTypeOf<number>();
  });

  it("type every model as read only for a read-only key", () => {
    expectTypeOf<ReadOnlyModels["blog.article"]["readOnly"]>().toEqualTypeOf<true>();
    expectTypeOf<ReadOnlyModels["blog.sitesettings"]["readOnly"]>().toEqualTypeOf<true>();
  });
});

describe("models", () => {
  it("lists a page of objects", async () => {
    const response = await articles.list({ ordering: "id" });

    expect(response.pagination).toMatchObject({ count: 5, pages: 3, current: 1, limit: 2 });
    expect(response.data.map((article) => article.slug)).toEqual(["getting-started-with-django", "models-in-depth"]);
    expect(response.data[0]).toMatchObject({ id: 1, category: 2, tags: [1, 2], word_count: 6 });
  });

  it("filters, excludes, searches and orders", async () => {
    const { data } = await articles.list({
      filters: { status: "published", views__gte: 40, created_at__lt: new Date("2026-03-15T00:00:00Z") },
      exclude: { category: 1 },
      ordering: ["-views"],
    });
    expect(data.map((article) => article.id)).toEqual([1, 2]);

    const { data: searched } = await articles.list({ search: "deploying" });
    expect(searched.map((article) => article.slug)).toEqual(["deploying-django"]);

    const { data: listed } = await articles.list({ filters: { id__in: [3, 5] }, ordering: "id" });
    expect(listed.map((article) => article.id)).toEqual([3, 5]);

    const { data: across } = await articles.list({ filters: { category__name: "Tutorials", category__isnull: false } });
    expect(across.map((article) => article.id).sort()).toEqual([3, 5]);
  });

  it("iterates over every page", async () => {
    const all = await articles.all({ ordering: "id" });
    expect(all.map((article) => article.id)).toEqual([1, 2, 3, 4, 5]);

    const titles: string[] = [];
    for await (const article of articles.iterate({ filters: { status: "draft" } })) {
      titles.push(article.title);
    }
    expect(titles).toEqual(["Deploying Django"]);
  });

  it("retrieves by primary key and by lookup field", async () => {
    const article = await articles.retrieve(1);
    expectTypeOf(article).toEqualTypeOf<BlogArticle>();
    expect(article.title).toBe("Getting started with Django");

    const bySlug = await articles.retrieveBy("slug", "models-in-depth");
    expect(bySlug.id).toBe(2);
  });

  it("expands relations as the types describe them", async () => {
    const article = await articles.retrieve(1, { expand: ["category.parent", "tags", "review_set"] });

    expectTypeOf(article.category).toEqualTypeOf<{ id: number; name: string; parent: BlogCategory | null } | null>();
    expectTypeOf(article.tags).toEqualTypeOf<BlogTag[]>();
    expectTypeOf(article.review_set).toEqualTypeOf<BlogReview[]>();

    expect(article.category).toMatchObject({ id: 2, name: "Django", parent: { id: 1, name: "Tutorials" } });
    expect(article.tags.map((tag) => tag.name)).toEqual(["python", "web"]);
    expect(article.review_set.map((review) => review.rating).sort()).toEqual([4, 5]);
  });

  it("selects fields", async () => {
    const article = await articles.retrieve(1, { fields: ["id", "title"] });
    expectTypeOf(article).toEqualTypeOf<{ id: number; title: string }>();
    expect(article).toEqual({ id: 1, title: "Getting started with Django" });

    const omitted = await articles.retrieve(1, { omit: ["body", "word_count"] });
    expect(omitted).not.toHaveProperty("body");
    expect(omitted).toHaveProperty("title");
  });

  it("creates, updates and deletes objects", async () => {
    const created = await articles.create({
      title: "Signals",
      slug: "signals",
      created_at: "2026-06-01T09:00:00Z",
      tags: [1],
    });
    expect(created).toMatchObject({ title: "Signals", status: "draft", tags: [1] });

    const updated = await articles.partialUpdate(created.id, { status: "published", views: 3 });
    expect(updated).toMatchObject({ status: "published", views: 3 });

    const replaced = await articles.update(created.id, {
      title: "Signals in Django",
      slug: "signals",
      created_at: "2026-06-01T09:00:00Z",
      tags: [],
    });
    expect(replaced).toMatchObject({ title: "Signals in Django", tags: [] });

    await articles.destroy(created.id);
    await expect(articles.retrieve(created.id)).rejects.toMatchObject({ status: 404 });
  });

  it("uploads form data", async () => {
    const form = new FormData();
    form.append("name", "testing");

    const tag = await api.model("blog.tag").create(form);
    expect(tag.name).toBe("testing");
    await api.model("blog.tag").destroy(tag.id);
  });

  it("reads read-only models", async () => {
    const { data } = await api.model("blog.page").list();
    expect(data.map((page) => page.title)).toEqual(["About"]);
  });
});

describe("singletons", () => {
  it("retrieves and updates the object", async () => {
    const settings = api.singleton("blog.sitesettings");

    expect(await settings.retrieve()).toMatchObject({ site_name: "The Django blog" });
    expect(await settings.partialUpdate({ site_name: "Another blog" })).toMatchObject({ site_name: "Another blog" });
    expect(await settings.update({ site_name: "The Django blog" })).toMatchObject({ site_name: "The Django blog" });
  });
});

describe("errors", () => {
  it("answers validation errors per field", async () => {
    // @ts-expect-error title and slug are required
    const error = await articles.create({ created_at: "2026-06-01T09:00:00Z", tags: [] }).catch((error) => error);

    expect(error).toBeInstanceOf(DjangoRestError);
    expect(error.status).toBe(400);
    expect(error.body).toHaveProperty("title");
    expect(error.body).toHaveProperty("slug");
  });

  it("answers 404 for a missing object", async () => {
    await expect(articles.retrieveBy("slug", "missing")).rejects.toMatchObject({
      status: 404,
      body: { detail: expect.any(String) },
    });
  });

  it("answers 400 for an invalid filter", async () => {
    await expect(articles.list({ filters: { views__gte: "many" as unknown as number } })).rejects.toMatchObject({
      status: 400,
    });
  });

  it("refuses requests without a key", async () => {
    const anonymous = new DjangoRestClient<Models>({ baseUrl });
    await expect(anonymous.model("blog.article").list()).rejects.toMatchObject({ status: 401 });
  });

  it("refuses writes with the read-only key", async () => {
    const readOnly = new DjangoRestClient<Models>({ baseUrl, secretKey: process.env.E2E_READ_ONLY_SECRET_KEY });

    expect((await readOnly.model("blog.article").list()).data).toHaveLength(2);
    await expect(readOnly.singleton("blog.sitesettings").partialUpdate({ site_name: "No" })).rejects.toMatchObject({
      status: 403,
    });
  });
});
