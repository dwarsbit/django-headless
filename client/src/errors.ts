/**
 * The error of a request the API answers with a status outside 200-299.
 * `body` holds the parsed JSON body, such as `{ detail: "Not found." }` or
 * the validation errors per field, or the text of a body that is not JSON.
 */
export class DjangoRestError extends Error {
  readonly status: number;
  readonly statusText: string;
  readonly body: unknown;
  readonly method: string;
  readonly url: string;

  constructor(response: { status: number; statusText: string }, body: unknown, method: string, url: string) {
    super(DjangoRestError.getMessage(response, body, method, url));
    this.name = "DjangoRestError";
    this.status = response.status;
    this.statusText = response.statusText;
    this.body = body;
    this.method = method;
    this.url = url;
  }

  private static getMessage(
    response: { status: number; statusText: string },
    body: unknown,
    method: string,
    url: string,
  ): string {
    const status = `${response.status}${response.statusText ? ` ${response.statusText}` : ""}`;
    const detail =
      body && typeof body === "object" && "detail" in body && typeof body.detail === "string" ? `: ${body.detail}` : "";

    return `${method} ${url} answered ${status}${detail}`;
  }
}
