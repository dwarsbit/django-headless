import { describe, expect, it, vi } from "vitest";

import { DjangoRestClient, DjangoRestError, type ClientOptions } from "../src/index.js";
import type { Models } from "./fixtures/models.js";

const ARTICLE = "headless_rest.docarticle";

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

function page<T>(data: T[], current: number, pages: number) {
  return {
    pagination: {
      count: data.length * pages,
      pages,
      current,
      limit: data.length,
      links: { self: "https://example.org/api/x", next: null, previous: null },
    },
    data,
  };
}

function setup(options: Partial<ClientOptions> = {}, ...responses: Response[]) {
  const fetch = vi.fn<typeof globalThis.fetch>();
  for (const response of responses) {
    fetch.mockResolvedValueOnce(response);
  }
  fetch.mockImplementation(async () => json({}));

  const api = new DjangoRestClient<Models>({ baseUrl: "https://example.org/api/", fetch, ...options });

  const request = (index = 0) => {
    const [url, init] = fetch.mock.calls[index] as [string, RequestInit];
    return { url: decodeURIComponent(url), init, headers: new Headers(init.headers) };
  };

  return { api, fetch, request };
}

describe("DjangoRestClient", () => {
  it("needs a base URL", () => {
    expect(() => new DjangoRestClient({} as ClientOptions)).toThrow("baseUrl");
  });

  it("joins the base URL and paths", () => {
    const api = new DjangoRestClient({ baseUrl: "/api" });
    expect(api.url("blog.article")).toBe("/api/blog.article");
    expect(api.url("/blog.article", new URLSearchParams({ page: "2" }))).toBe("/api/blog.article?page=2");
  });

  it("sends the secret key and the headers of the client", async () => {
    const { api, request } = setup({ secretKey: "your-secret-key", headers: { "X-Client": "site" } });

    await api.model(ARTICLE).retrieve(1);

    expect(request().headers.get("X-Secret-Key")).toBe("your-secret-key");
    expect(request().headers.get("X-Client")).toBe("site");
    expect(request().headers.get("Accept")).toBe("application/json");
  });

  it("sends the secret key in another header", async () => {
    const { api, request } = setup({ secretKey: "your-secret-key", secretKeyHeader: "X-Key" });

    await api.model(ARTICLE).retrieve(1);

    expect(request().headers.get("X-Key")).toBe("your-secret-key");
    expect(request().headers.has("X-Secret-Key")).toBe(false);
  });

  it("resolves headers from a function on every request", async () => {
    let token = "first";
    const { api, request } = setup({ headers: async () => ({ Authorization: `Token ${token}` }) });

    await api.model(ARTICLE).retrieve(1);
    token = "second";
    await api.model(ARTICLE).retrieve(1);

    expect(request(0).headers.get("Authorization")).toBe("Token first");
    expect(request(1).headers.get("Authorization")).toBe("Token second");
  });

  it("merges the options of a request with those of the client", async () => {
    const controller = new AbortController();
    const { api, request } = setup({ init: { cache: "no-store", headers: { "X-A": "client" } } });

    await api
      .model(ARTICLE)
      .retrieve(1, {}, { headers: { "X-B": "request" }, signal: controller.signal, init: { next: { revalidate: 60 } } });

    const { init, headers } = request();
    expect(init.cache).toBe("no-store");
    expect((init as { next?: unknown }).next).toEqual({ revalidate: 60 });
    expect(init.signal).toBe(controller.signal);
    expect(headers.get("X-A")).toBe("client");
    expect(headers.get("X-B")).toBe("request");
  });

  it("throws a DjangoRestError with the body of an error response", async () => {
    const { api } = setup({}, json({ detail: "Not found." }, 404));

    const error = await api
      .model(ARTICLE)
      .retrieve(9)
      .catch((error: unknown) => error);

    expect(error).toBeInstanceOf(DjangoRestError);
    expect(error).toMatchObject({
      status: 404,
      body: { detail: "Not found." },
      method: "GET",
      url: "https://example.org/api/headless_rest.docarticle/9",
    });
    expect((error as Error).message).toBe("GET https://example.org/api/headless_rest.docarticle/9 answered 404: Not found.");
  });

  it("keeps a body that is not JSON as text", async () => {
    const { api } = setup({}, new Response("Bad gateway", { status: 502, statusText: "Bad Gateway" }));

    await expect(api.model(ARTICLE).list()).rejects.toMatchObject({ status: 502, body: "Bad gateway" });
  });

  it("sends other requests", async () => {
    const { api, request } = setup({}, json({ ok: true }));

    const result = await api.request("GET", "custom/route", { query: new URLSearchParams({ a: "1" }) });

    expect(result).toEqual({ ok: true });
    expect(request().url).toBe("https://example.org/api/custom/route?a=1");
  });
});

describe("ModelResource", () => {
  it("lists objects with filters, exclusions and other parameters", async () => {
    const { api, request } = setup({}, json(page([], 1, 1)));

    await api.model(ARTICLE).list({
      filters: {
        title__icontains: "django",
        published: true,
        rating: null,
        id__in: [1, 2, 3],
        created__gte: new Date("2026-01-01T00:00:00Z"),
        status: undefined,
        category__name: "Tutorials",
      },
      exclude: { category: 3 },
      search: "getting started",
      ordering: ["-created", "title"],
      page: 2,
      limit: 20,
      expand: ["category", "tags"],
      fields: ["id", "title", "category"],
      omit: ["shout"],
      params: { format: "json" },
    });

    const url = new URL(request().url);
    expect(url.pathname).toBe("/api/headless_rest.docarticle");
    expect([...url.searchParams]).toEqual([
      ["title__icontains", "django"],
      ["published", "true"],
      ["rating", "null"],
      ["id__in", "1,2,3"],
      ["created__gte", "2026-01-01T00:00:00.000Z"],
      ["category__name", "Tutorials"],
      ["~category", "3"],
      ["search", "getting started"],
      ["ordering", "-created,title"],
      ["page", "2"],
      ["limit", "20"],
      ["expand", "category,tags"],
      ["fields", "id,title,category"],
      ["omit", "shout"],
      ["format", "json"],
    ]);
  });

  it("uses the configured parameter names and exclusion symbol", async () => {
    const { api, request } = setup({ exclusionSymbol: "exclude_", searchParam: "q", orderingParam: "sort" });

    await api.model(ARTICLE).list({ exclude: { status: "draft" }, search: "django", ordering: "title" });

    expect(request().url).toBe("https://example.org/api/headless_rest.docarticle?exclude_status=draft&q=django&sort=title");
  });

  it("retrieves objects by primary key and by lookup field", async () => {
    const { api, request } = setup();

    await api.model(ARTICLE).retrieve(1, { expand: ["category"] });
    await api.model("headless_rest.docpage").retrieveBy("slug", "hello world/2");

    expect(request(0).url).toBe("https://example.org/api/headless_rest.docarticle/1?expand=category");
    expect(request(1).url).toBe("https://example.org/api/headless_rest.docpage/by_slug/hello world/2");
  });

  it("encodes values in the path", async () => {
    const { api, fetch } = setup();

    await api.model("headless_rest.docpage").retrieveBy("slug", "a/b c");

    expect(fetch.mock.calls[0]?.[0]).toBe("https://example.org/api/headless_rest.docpage/by_slug/a%2Fb%20c");
  });

  it("creates, updates and deletes objects", async () => {
    const { api, request } = setup({}, json({ id: 1 }, 201), json({}), json({}), new Response(null, { status: 204 }));
    const articles = api.model(ARTICLE);

    expect(await articles.create({ title: "Getting started with Django", tags: [] })).toEqual({ id: 1 });
    await articles.update(1, { title: "Getting started", tags: [2] });
    await articles.partialUpdate(1, { published: true });
    expect(await articles.destroy(1)).toBeUndefined();

    expect(request(0).init.method).toBe("POST");
    expect(request(0).url).toBe("https://example.org/api/headless_rest.docarticle");
    expect(request(0).init.body).toBe('{"title":"Getting started with Django","tags":[]}');
    expect(request(0).headers.get("Content-Type")).toBe("application/json");
    expect(request(1).init.method).toBe("PUT");
    expect(request(1).url).toBe("https://example.org/api/headless_rest.docarticle/1");
    expect(request(2).init.method).toBe("PATCH");
    expect(request(2).init.body).toBe('{"published":true}');
    expect(request(3).init.method).toBe("DELETE");
    expect(request(3).init.body).toBeUndefined();
  });

  it("sends form data as it is", async () => {
    const { api, request } = setup();
    const form = new FormData();
    form.append("title", "Getting started with Django");

    await api.model(ARTICLE).create(form);

    expect(request().init.body).toBe(form);
    expect(request().headers.has("Content-Type")).toBe(false);
  });

  it("iterates over every page", async () => {
    const { api, request, fetch } = setup(
      {},
      json(page([{ id: 1 }, { id: 2 }], 1, 2)),
      json(page([{ id: 3 }, { id: 4 }], 2, 2)),
    );

    const items = await api.model(ARTICLE).all({ filters: { published: true }, limit: 2 });

    expect(items.map((item) => item.id)).toEqual([1, 2, 3, 4]);
    expect(fetch).toHaveBeenCalledTimes(2);
    expect(request(0).url).toBe("https://example.org/api/headless_rest.docarticle?published=true&page=1&limit=2");
    expect(request(1).url).toBe("https://example.org/api/headless_rest.docarticle?published=true&page=2&limit=2");
  });

  it("iterates over a list without pagination", async () => {
    const { api, fetch } = setup({}, json([{ id: 1 }, { id: 2 }]));

    const ids: number[] = [];
    for await (const item of api.model(ARTICLE).iterate()) {
      ids.push(item.id);
    }

    expect(ids).toEqual([1, 2]);
    expect(fetch).toHaveBeenCalledTimes(1);
  });

  it("stops after an empty list", async () => {
    const { api, fetch } = setup({}, json(page([], 1, 1)));

    expect(await api.model(ARTICLE).all()).toEqual([]);
    expect(fetch).toHaveBeenCalledTimes(1);
  });
});

describe("SingletonResource", () => {
  it("retrieves and updates the object", async () => {
    const { api, request } = setup();
    const settings = api.singleton("headless_rest.docsettings");

    await settings.retrieve({ fields: ["site_name"] });
    await settings.update({ site_name: "Blog" });
    await settings.partialUpdate({ site_name: "Blog" });

    expect(request(0).url).toBe("https://example.org/api/headless_rest.docsettings?fields=site_name");
    expect(request(1).init.method).toBe("PUT");
    expect(request(1).url).toBe("https://example.org/api/headless_rest.docsettings");
    expect(request(2).init.method).toBe("PATCH");
  });
});
