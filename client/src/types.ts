/**
 * Types that describe the exposed models of an API, and the types of the
 * requests and responses derived from them.
 */

/** A relation that can be expanded with `?expand=`. */
export interface ExpandableRelation {
  /** The label of the model the relation points to. */
  model: string;
  /** Whether the relation expands to a list of objects. */
  many: boolean;
  /** Whether the relation can be empty (`null`). */
  nullable: boolean;
}

/**
 * Describes one exposed model. `headless generate` writes these from
 * the OpenAPI schema; write one by hand with `ModelDefinition<Item, ...>`.
 */
export interface ModelDefinitionShape {
  /** An object as the API returns it. */
  item: object;
  /** The body of a create or update request. */
  input: object;
  /** The type of the primary key. */
  id: string | number;
  /** The filterable fields and the types of their values. */
  filters: object;
  /** The fields of the lookup routes (`by_<field>`) and the types of their values. */
  lookups: object;
  /** The relations that can be expanded. */
  expandable: { [name: string]: ExpandableRelation };
  /** Whether the model only has read routes. */
  readOnly: boolean;
  /** Whether the model is a singleton. */
  singleton: boolean;
  /** Whether list routes answer with the pagination envelope. */
  paginated: boolean;
}

/** A map of model labels to their definitions. */
export type ModelMap = { [label: string]: ModelDefinitionShape };

/**
 * Define a model by hand, for an API without a generated `Models` type.
 *
 * ```ts
 * type Models = {
 *   "blog.article": ModelDefinition<Article, { lookups: { slug: string } }>;
 * };
 * ```
 */
export type ModelDefinition<
  Item extends object,
  Options extends Partial<Omit<ModelDefinitionShape, "item">> = {},
> = {
  item: Item;
  input: Options extends { input: infer I extends object } ? I : Partial<Item>;
  id: Options extends { id: infer I extends string | number } ? I : number;
  filters: Options extends { filters: infer F extends object } ? F : Partial<Item>;
  lookups: Options extends { lookups: infer L extends object } ? L : {};
  expandable: Options extends { expandable: infer E extends { [name: string]: ExpandableRelation } } ? E : {};
  readOnly: Options extends { readOnly: infer R extends boolean } ? R : false;
  singleton: Options extends { singleton: infer S extends boolean } ? S : false;
  paginated: Options extends { paginated: infer P extends boolean } ? P : true;
};

/** Any object, the item type of a model without a definition. */
export type AnyObject = { [key: string]: unknown };

/** The definition of every model of a client without a `Models` type. */
export interface AnyModelDefinition {
  item: AnyObject;
  input: AnyObject;
  id: string | number;
  filters: AnyObject;
  lookups: AnyObject;
  expandable: { [name: string]: ExpandableRelation };
  readOnly: false;
  singleton: boolean;
  paginated: true;
}

/** The model map of a client without a `Models` type: any label is accepted. */
export type AnyModels = { [label: string]: AnyModelDefinition };

/** The labels of the models that are not singletons. */
export type ModelLabel<Ms extends ModelMap> = {
  [L in keyof Ms & string]: Ms[L]["singleton"] extends true ? never : L;
}[keyof Ms & string];

/** The labels of the singletons. */
export type SingletonLabel<Ms extends ModelMap> = {
  [L in keyof Ms & string]: Ms[L]["singleton"] extends false ? never : L;
}[keyof Ms & string];

// Filters

/** A value in the query string. Dates are sent as ISO 8601 strings. */
export type FilterValue = string | number | boolean | Date | null;

/** Lookups that take a single value of the type of the field. */
export type ValueLookup =
  | "exact"
  | "iexact"
  | "contains"
  | "icontains"
  | "startswith"
  | "istartswith"
  | "endswith"
  | "iendswith"
  | "gt"
  | "gte"
  | "lt"
  | "lte";

/** Lookups that take a list of values of the type of the field. */
export type ListLookup = "in" | "range";

type FilterFields<F> = {
  [K in keyof F & string as K | `${K}__${ValueLookup}`]?: F[K] | null;
} & {
  [K in keyof F & string as `${K}__${ListLookup}`]?: readonly F[K][];
} & {
  [K in keyof F & string as `${K}__isnull`]?: boolean;
};

/**
 * The filters of a list route: each filterable field, with or without a
 * lookup such as `__icontains` or `__in`. Other lookups (`created__year`)
 * and lookups across relations (`category__name`) are accepted as well,
 * without type checks on their values.
 */
export type Filters<F> = FilterFields<F> & {
  [key: string]: FilterValue | readonly FilterValue[] | undefined;
};

// Expansion

type Head<P extends string> = P extends `${infer H}.${string}` ? H : P;
type Tail<P extends string, H extends string> = P extends `${H}.${infer T}` ? T : never;
type Depth = [never, 0, 1, 2];

/** The paths that can be expanded, such as `category` or `category.parent`, up to three relations deep. */
export type ExpandPath<Ms extends ModelMap, L extends keyof Ms, D extends number = 3> = string extends keyof Ms[L]["expandable"]
  ? string
  : [D] extends [never]
  ? never
  : {
      [K in keyof Ms[L]["expandable"] & string]:
        | K
        | (Ms[L]["expandable"][K]["model"] extends keyof Ms
            ? `${K}.${ExpandPath<Ms, Ms[L]["expandable"][K]["model"], Depth[D]>}`
            : never);
    }[keyof Ms[L]["expandable"] & string];

type ExpandedKeys<Ms extends ModelMap, L extends keyof Ms, E extends string> = "*" extends E
  ? keyof Ms[L]["expandable"] & string
  : Head<E> & keyof Ms[L]["expandable"] & string;

type ExpandRelation<Ms extends ModelMap, R, E extends string> = R extends {
  model: infer T;
  many: infer Many;
  nullable: infer Nullable;
}
  ? T extends keyof Ms
    ? Many extends true
      ? Expanded<Ms, T, E>[]
      : Expanded<Ms, T, E> | (Nullable extends true ? null : never)
    : unknown
  : unknown;

/** The item type of a model with the relations in `E` expanded. */
export type Expanded<Ms extends ModelMap, L extends keyof Ms, E extends string> = [E] extends [never]
  ? Ms[L]["item"]
  : string extends keyof Ms[L]["expandable"]
  ? Ms[L]["item"]
  : Simplify<
      Omit<Ms[L]["item"], ExpandedKeys<Ms, L, E>> & {
        [K in ExpandedKeys<Ms, L, E>]: ExpandRelation<Ms, Ms[L]["expandable"][K], Tail<E, K>>;
      }
    >;

type Simplify<T> = { [K in keyof T]: T[K] } & {};

/** Leave out all but the fields in `F` (top-level fields only), or the fields in `O`. */
export type Sparse<T, F extends string, O extends string> = [F | O] extends [never]
  ? T
  : Simplify<Omit<[F] extends [never] ? T : Pick<T, Head<F> & keyof T>, O & keyof T>>;

/** The field names of a model, for `fields` and `omit`. */
export type FieldName<Ms extends ModelMap, L extends keyof Ms> =
  | (keyof Ms[L]["item"] & string)
  | (keyof Ms[L]["expandable"] & string)
  | `${keyof Ms[L]["expandable"] & string}.${string}`;

// Requests and responses

/** Options for one request, merged with those of the client. */
export interface RequestOptions {
  /** Headers of this request. */
  headers?: HeadersInit;
  /** Abort the request with an `AbortController`. */
  signal?: AbortSignal;
  /**
   * Other options for `fetch`, such as `cache`, or `next: { revalidate: 60 }`
   * in Next.js.
   */
  init?: RequestInit & { [key: string]: unknown };
}

/** What `expand` accepts. */
export type ExpandParam<Ms extends ModelMap, L extends keyof Ms> = ExpandPath<Ms, L> | "*";

/** The query parameters of a detail route, singleton or lookup route. */
export interface ReadParams<
  Ms extends ModelMap,
  L extends keyof Ms,
  E extends ExpandParam<Ms, L> = ExpandParam<Ms, L>,
  F extends FieldName<Ms, L> = FieldName<Ms, L>,
  O extends FieldName<Ms, L> = FieldName<Ms, L>,
> {
  /** Relations to include as objects instead of primary keys. Needs `FlexibleSerializer`. */
  expand?: readonly E[];
  /** Fields to include. Others are left out. Needs `FlexibleSerializer`. */
  fields?: readonly F[];
  /** Fields to leave out. Needs `FlexibleSerializer`. */
  omit?: readonly O[];
  /** Other query parameters, sent as they are. */
  params?: { [key: string]: FilterValue | readonly FilterValue[] | undefined };
}

/** The query parameters of a list route. */
export interface ListParams<
  Ms extends ModelMap,
  L extends keyof Ms,
  E extends ExpandParam<Ms, L> = ExpandParam<Ms, L>,
  F extends FieldName<Ms, L> = FieldName<Ms, L>,
  O extends FieldName<Ms, L> = FieldName<Ms, L>,
> extends ReadParams<Ms, L, E, F, O> {
  /** Objects to include, by field and lookup. */
  filters?: Filters<Ms[L]["filters"]>;
  /** Objects to leave out, by field and lookup (`?~field=`). */
  exclude?: Filters<Ms[L]["filters"]>;
  /** A search term. Needs a search filter backend. */
  search?: string;
  /** Fields to order by, with `-` for descending order. Needs an ordering filter backend. */
  ordering?: string | readonly string[];
  /** The page number, starting at 1. */
  page?: number;
  /** The number of objects per page. */
  limit?: number;
}

/** The links of a page. */
export interface PaginationLinks {
  self: string;
  next: string | null;
  previous: string | null;
}

/** The pagination envelope of a list route. */
export interface Paginated<T> {
  pagination: {
    /** The number of objects in all pages. */
    count: number;
    /** The number of pages. */
    pages: number;
    /** The number of the current page. */
    current: number;
    /** The number of objects per page. */
    limit: number;
    links: PaginationLinks;
  };
  data: T[];
}

/** The response of a list route: the envelope, or a plain list without pagination. */
export type ListResponse<Ms extends ModelMap, L extends keyof Ms, T> = Ms[L]["paginated"] extends false
  ? T[]
  : Paginated<T>;

/** The item type of a request with `expand`, `fields` and `omit`. */
export type ResponseItem<Ms extends ModelMap, L extends keyof Ms, E extends string, F extends string, O extends string> =
  Sparse<Expanded<Ms, L, E>, F, O>;
