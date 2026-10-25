import type { FilterValue } from "./types.js";

type QueryValue = FilterValue | readonly FilterValue[] | undefined;

/** Format one value as the API reads it from the query string. */
export function formatValue(value: FilterValue): string {
  if (value === null) {
    return "null";
  }

  if (value instanceof Date) {
    return value.toISOString();
  }

  return String(value);
}

/**
 * Add parameters to a query string. Lists are joined with commas, as
 * `__in` and `__range` lookups and `expand`, `fields` and `omit` read
 * them; undefined values are left out.
 */
export function appendParams(search: URLSearchParams, params: { [key: string]: QueryValue }, prefix = ""): void {
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined) {
      continue;
    }

    const formatted = Array.isArray(value)
      ? (value as readonly FilterValue[]).map(formatValue).join(",")
      : formatValue(value as FilterValue);
    search.append(`${prefix}${key}`, formatted);
  }
}
