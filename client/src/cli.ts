#!/usr/bin/env node
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { dirname } from "node:path";
import { parseArgs } from "node:util";

import { generate, type OpenAPIDocument } from "./generate.js";

const USAGE = `Usage: django-headless generate (--url <schema url> | --file <schema.json>) [options]

Generate TypeScript types of the exposed models from the OpenAPI schema of Django Headless.

Options:
  --url <url>            The schema route, such as https://example.org/api/schema
  --file <path>          A schema file, from manage.py generateschema --format openapi-json
  --out <path>           The file to write (default: prints to standard output)
  --secret-key <key>     The secret key of the schema route. Defaults to DJANGO_HEADLESS_SECRET_KEY
  --secret-key-header    The header of the secret key (default: X-Secret-Key)
  --header <header>      Another request header, such as "Authorization: Token abc". Repeatable
  -h, --help             Show this help
`;

async function main(argv: string[]): Promise<void> {
  const { values, positionals } = parseArgs({
    args: argv,
    allowPositionals: true,
    options: {
      url: { type: "string" },
      file: { type: "string" },
      out: { type: "string" },
      "secret-key": { type: "string" },
      "secret-key-header": { type: "string" },
      header: { type: "string", multiple: true },
      help: { type: "boolean", short: "h" },
    },
  });

  if (values.help || positionals[0] !== "generate" || positionals.length !== 1) {
    process.stdout.write(USAGE);
    process.exitCode = values.help ? 0 : 1;
    return;
  }

  if (Boolean(values.url) === Boolean(values.file)) {
    throw new Error("Pass either --url or --file.");
  }

  const document = values.url
    ? await fetchSchema(values.url, {
        secretKey: values["secret-key"] ?? process.env.DJANGO_HEADLESS_SECRET_KEY,
        secretKeyHeader: values["secret-key-header"] ?? "X-Secret-Key",
        headers: values.header ?? [],
      })
    : (JSON.parse(await readFile(values.file as string, "utf8")) as OpenAPIDocument);

  const source = generate(document);

  if (values.out) {
    await mkdir(dirname(values.out), { recursive: true });
    await writeFile(values.out, source);
    process.stderr.write(`Wrote the types of ${countModels(source)} models to ${values.out}\n`);
  } else {
    process.stdout.write(source);
  }
}

async function fetchSchema(
  url: string,
  options: { secretKey: string | undefined; secretKeyHeader: string; headers: string[] },
): Promise<OpenAPIDocument> {
  const headers = new Headers({ Accept: "application/json" });
  for (const header of options.headers) {
    const index = header.indexOf(":");
    if (index === -1) {
      throw new Error(`The header "${header}" has no colon. Write it as "Name: value".`);
    }
    headers.set(header.slice(0, index).trim(), header.slice(index + 1).trim());
  }
  if (options.secretKey) {
    headers.set(options.secretKeyHeader, options.secretKey);
  }

  const response = await fetch(url, { headers });
  if (!response.ok) {
    throw new Error(`GET ${url} answered ${response.status} ${response.statusText}`.trim());
  }

  return (await response.json()) as OpenAPIDocument;
}

function countModels(source: string): number {
  const models = source.slice(source.indexOf("export type Models = {"));
  return (models.match(/^ {2}"[^"]+": \{$/gm) ?? []).length;
}

main(process.argv.slice(2)).catch((error: unknown) => {
  process.stderr.write(`django-headless: ${error instanceof Error ? error.message : String(error)}\n`);
  process.exitCode = 1;
});
