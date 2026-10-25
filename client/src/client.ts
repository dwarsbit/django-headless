import { DjangoRestError } from "./errors.js";
import { appendParams } from "./query.js";
import type {
  AnyModels,
  ExpandParam,
  FieldName,
  ListParams,
  ListResponse,
  ModelLabel,
  ModelMap,
  Paginated,
  ReadParams,
  RequestOptions,
  ResponseItem,
  SingletonLabel,
} from "./types.js";

type HeadersOption = HeadersInit | (() => HeadersInit | Promise<HeadersInit>);

export interface ClientOptions {
  /** The URL the API is included at, such as `https://example.org/api`. */
  baseUrl: string | URL;
  /** The secret key of `SecretKeyAuthentication`, sent in the `X-Secret-Key` header. */
  secretKey?: string;
  /** The header of the secret key, as in `HEADLESS["AUTH_SECRET_KEY_HEADER"]`. */
  secretKeyHeader?: string;
  /** Headers of every request, or a function that returns them, for example to add a token. */
  headers?: HeadersOption;
  /** The `fetch` function to use. Defaults to the global `fetch`. */
  fetch?: typeof fetch;
  /** Other options for `fetch` of every request, such as `cache` or `credentials`. */
  init?: RequestInit & { [key: string]: unknown };
  /** The symbol that starts an exclusion, as in `HEADLESS["FILTER_EXCLUSION_SYMBOL"]`. */
  exclusionSymbol?: string;
  /** The query parameter of the search term, as in `HEADLESS["SEARCH_PARAM"]`. */
  searchParam?: string;
  /** The query parameter of the ordering, as in `HEADLESS["ORDERING_PARAM"]`. */
  orderingParam?: string;
}

/** The options of `DjangoRestClient.request()`. */
export interface RawRequestOptions extends RequestOptions {
  query?: URLSearchParams;
  body?: unknown;
}

/**
 * A client for the generated routes of Django Headless.
 *
 * ```ts
 * import { DjangoRestClient } from "@django-headless/client";
 * import type { Models } from "./headless";
 *
 * const api = new DjangoRestClient<Models>({ baseUrl: "https://example.org/api" });
 * const { data } = await api.model("blog.article").list({ filters: { published: true } });
 * ```
 */
export class DjangoRestClient<Ms extends ModelMap = AnyModels> {
  readonly options: Readonly<ClientOptions>;

  constructor(options: ClientOptions) {
    if (!options?.baseUrl) {
      throw new TypeError("DjangoRestClient needs a baseUrl, such as https://example.org/api");
    }

    this.options = options;
  }

  /** The routes of a model, such as `blog.article`. */
  model<L extends ModelLabel<Ms>>(label: L): ModelResourceFor<Ms, L> {
    return new ModelResource<Ms, L>(this, label) as ModelResourceFor<Ms, L>;
  }

  /** The route of a singleton, such as `blog.sitesettings`. */
  singleton<L extends SingletonLabel<Ms>>(label: L): SingletonResourceFor<Ms, L> {
    return new SingletonResource<Ms, L>(this, label) as SingletonResourceFor<Ms, L>;
  }

  /** The full URL of a path of the API. */
  url(path: string, query?: URLSearchParams): string {
    const base = String(this.options.baseUrl).replace(/\/+$/, "");
    const search = query?.toString();

    return `${base}/${path.replace(/^\/+/, "")}${search ? `?${search}` : ""}`;
  }

  /**
   * Send a request to a path of the API and return the parsed response.
   * Throws a `DjangoRestError` when the API answers with an error status.
   */
  async request<T = unknown>(method: string, path: string, options: RawRequestOptions = {}): Promise<T> {
    const url = this.url(path, options.query);
    const headers = new Headers({ Accept: "application/json" });

    const clientHeaders =
      typeof this.options.headers === "function" ? await this.options.headers() : this.options.headers;
    mergeHeaders(headers, clientHeaders);
    mergeHeaders(headers, this.options.init?.headers);
    mergeHeaders(headers, options.init?.headers);

    if (this.options.secretKey) {
      headers.set(this.options.secretKeyHeader ?? "X-Secret-Key", this.options.secretKey);
    }

    let body: BodyInit | undefined;
    if (options.body instanceof FormData) {
      // fetch sets the multipart content type with its boundary
      body = options.body;
    } else if (options.body !== undefined) {
      body = JSON.stringify(options.body);
      headers.set("Content-Type", "application/json");
    }

    mergeHeaders(headers, options.headers);

    const fetchFunction = this.options.fetch ?? globalThis.fetch;
    const signal = options.signal ?? options.init?.signal ?? this.options.init?.signal;
    const response = await fetchFunction(url, {
      ...this.options.init,
      ...options.init,
      method,
      headers,
      ...(body === undefined ? {} : { body }),
      ...(signal ? { signal } : {}),
    });

    const data = await parseBody(response);
    if (!response.ok) {
      throw new DjangoRestError(response, data, method, url);
    }

    return data as T;
  }
}

function mergeHeaders(headers: Headers, init: HeadersInit | undefined): void {
  if (init) {
    new Headers(init).forEach((value, name) => headers.set(name, value));
  }
}

async function parseBody(response: Response): Promise<unknown> {
  if (response.status === 204) {
    return undefined;
  }

  const text = await response.text();
  if (!text) {
    return undefined;
  }

  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

function encodeSegment(value: string | number): string {
  return encodeURIComponent(String(value));
}

/** The routes of a model. */
export class ModelResource<Ms extends ModelMap, L extends keyof Ms & string> {
  constructor(
    readonly client: DjangoRestClient<Ms>,
    readonly label: L,
  ) {}

  /** List the objects, a page at a time when the API paginates. */
  list<
    const E extends ExpandParam<Ms, L> = never,
    const F extends FieldName<Ms, L> = never,
    const O extends FieldName<Ms, L> = never,
  >(
    params: ListParams<Ms, L, E, F, O> = {},
    options: RequestOptions = {},
  ): Promise<ListResponse<Ms, L, ResponseItem<Ms, L, E, F, O>>> {
    return this.client.request("GET", this.label, { ...options, query: this.listQuery(params) });
  }

  /** Iterate over the objects of every page, requesting one page at a time. */
  async *iterate<
    const E extends ExpandParam<Ms, L> = never,
    const F extends FieldName<Ms, L> = never,
    const O extends FieldName<Ms, L> = never,
  >(
    params: Omit<ListParams<Ms, L, E, F, O>, "page"> = {},
    options: RequestOptions = {},
  ): AsyncGenerator<ResponseItem<Ms, L, E, F, O>, void, undefined> {
    for (let page = 1; ; page++) {
      const response = (await this.list<E, F, O>({ ...params, page } as ListParams<Ms, L, E, F, O>, options)) as
        | ResponseItem<Ms, L, E, F, O>[]
        | Paginated<ResponseItem<Ms, L, E, F, O>>;

      // Without pagination, the list holds every object
      if (Array.isArray(response)) {
        yield* response;
        return;
      }

      yield* response.data;
      if (page >= response.pagination.pages) {
        return;
      }
    }
  }

  /** List the objects of every page. */
  async all<
    const E extends ExpandParam<Ms, L> = never,
    const F extends FieldName<Ms, L> = never,
    const O extends FieldName<Ms, L> = never,
  >(
    params: Omit<ListParams<Ms, L, E, F, O>, "page"> = {},
    options: RequestOptions = {},
  ): Promise<ResponseItem<Ms, L, E, F, O>[]> {
    const items: ResponseItem<Ms, L, E, F, O>[] = [];
    for await (const item of this.iterate<E, F, O>(params, options)) {
      items.push(item);
    }

    return items;
  }

  /** Retrieve an object by its primary key. */
  retrieve<
    const E extends ExpandParam<Ms, L> = never,
    const F extends FieldName<Ms, L> = never,
    const O extends FieldName<Ms, L> = never,
  >(
    id: Ms[L]["id"],
    params: ReadParams<Ms, L, E, F, O> = {},
    options: RequestOptions = {},
  ): Promise<ResponseItem<Ms, L, E, F, O>> {
    return this.client.request("GET", `${this.label}/${encodeSegment(id)}`, {
      ...options,
      query: readQuery(params),
    });
  }

  /** Retrieve an object by a unique field of its lookup routes, such as `slug`. */
  retrieveBy<
    K extends keyof Ms[L]["lookups"] & string,
    const E extends ExpandParam<Ms, L> = never,
    const F extends FieldName<Ms, L> = never,
    const O extends FieldName<Ms, L> = never,
  >(
    field: K,
    value: Ms[L]["lookups"][K],
    params: ReadParams<Ms, L, E, F, O> = {},
    options: RequestOptions = {},
  ): Promise<ResponseItem<Ms, L, E, F, O>> {
    return this.client.request("GET", `${this.label}/by_${field}/${encodeSegment(value as string | number)}`, {
      ...options,
      query: readQuery(params),
    });
  }

  /** Create an object. Send a `FormData` to upload files. */
  create(data: Ms[L]["input"] | FormData, options: RequestOptions = {}): Promise<Ms[L]["item"]> {
    return this.client.request("POST", this.label, { ...options, body: data });
  }

  /** Replace an object. */
  update(id: Ms[L]["id"], data: Ms[L]["input"] | FormData, options: RequestOptions = {}): Promise<Ms[L]["item"]> {
    return this.client.request("PUT", `${this.label}/${encodeSegment(id)}`, { ...options, body: data });
  }

  /** Change fields of an object. */
  partialUpdate(
    id: Ms[L]["id"],
    data: Partial<Ms[L]["input"]> | FormData,
    options: RequestOptions = {},
  ): Promise<Ms[L]["item"]> {
    return this.client.request("PATCH", `${this.label}/${encodeSegment(id)}`, { ...options, body: data });
  }

  /** Delete an object. */
  async destroy(id: Ms[L]["id"], options: RequestOptions = {}): Promise<void> {
    await this.client.request("DELETE", `${this.label}/${encodeSegment(id)}`, options);
  }

  private listQuery(params: ListParams<Ms, L, any, any, any>): URLSearchParams {
    const { exclusionSymbol = "~", searchParam = "search", orderingParam = "ordering" } = this.client.options;
    const query = new URLSearchParams();

    appendParams(query, params.filters ?? {});
    appendParams(query, params.exclude ?? {}, exclusionSymbol);
    appendParams(query, {
      [searchParam]: params.search,
      [orderingParam]: params.ordering,
      page: params.page,
      limit: params.limit,
    });
    appendReadParams(query, params);

    return query;
  }
}

/** The route of a singleton. */
export class SingletonResource<Ms extends ModelMap, L extends keyof Ms & string> {
  constructor(
    readonly client: DjangoRestClient<Ms>,
    readonly label: L,
  ) {}

  /** Retrieve the object. */
  retrieve<
    const E extends ExpandParam<Ms, L> = never,
    const F extends FieldName<Ms, L> = never,
    const O extends FieldName<Ms, L> = never,
  >(params: ReadParams<Ms, L, E, F, O> = {}, options: RequestOptions = {}): Promise<ResponseItem<Ms, L, E, F, O>> {
    return this.client.request("GET", this.label, { ...options, query: readQuery(params) });
  }

  /** Replace the object. */
  update(data: Ms[L]["input"] | FormData, options: RequestOptions = {}): Promise<Ms[L]["item"]> {
    return this.client.request("PUT", this.label, { ...options, body: data });
  }

  /** Change fields of the object. */
  partialUpdate(data: Partial<Ms[L]["input"]> | FormData, options: RequestOptions = {}): Promise<Ms[L]["item"]> {
    return this.client.request("PATCH", this.label, { ...options, body: data });
  }
}

function readQuery(params: ReadParams<any, any, any, any, any>): URLSearchParams {
  const query = new URLSearchParams();
  appendReadParams(query, params);

  return query;
}

function appendReadParams(query: URLSearchParams, params: ReadParams<any, any, any, any, any>): void {
  appendParams(query, { expand: params.expand, fields: params.fields, omit: params.omit });
  appendParams(query, params.params ?? {});
}

type ReadMethods = "client" | "label" | "list" | "iterate" | "all" | "retrieve" | "retrieveBy";

/** The routes of a read-only model. */
export type ReadOnlyModelResource<Ms extends ModelMap, L extends keyof Ms & string> = Pick<
  ModelResource<Ms, L>,
  ReadMethods
>;

/** The route of a read-only singleton. */
export type ReadOnlySingletonResource<Ms extends ModelMap, L extends keyof Ms & string> = Pick<
  SingletonResource<Ms, L>,
  "client" | "label" | "retrieve"
>;

/** The routes of a model, without the write methods for a read-only model. */
export type ModelResourceFor<Ms extends ModelMap, L extends keyof Ms & string> = Ms[L]["readOnly"] extends true
  ? ReadOnlyModelResource<Ms, L>
  : ModelResource<Ms, L>;

/** The route of a singleton, without the write methods for a read-only singleton. */
export type SingletonResourceFor<Ms extends ModelMap, L extends keyof Ms & string> = Ms[L]["readOnly"] extends true
  ? ReadOnlySingletonResource<Ms, L>
  : SingletonResource<Ms, L>;
