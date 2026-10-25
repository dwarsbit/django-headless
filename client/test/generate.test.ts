import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

import { generate, renderType, type OpenAPIDocument } from "../src/generate.js";

const schema = JSON.parse(readFileSync(new URL("./fixtures/schema.json", import.meta.url), "utf8")) as OpenAPIDocument;

function model(source: string, label: string): string {
  const start = source.indexOf(`  ${JSON.stringify(label)}: {`);
  return source.slice(start, source.indexOf("\n  };", start));
}

describe("generate", () => {
  const source = generate(schema);

  it("matches the generated types of the test models", async () => {
    // The types tests import this file, so it is type-checked as well
    await expect(source).toMatchFileSnapshot("./fixtures/models.ts");
  });

  it("generates an interface per model and an input for writable models", () => {
    expect(source).toContain("export interface HeadlessRestDocArticle {");
    expect(source).toContain("export interface HeadlessRestDocArticleInput {");
    expect(source).toContain("export interface HeadlessRestDocNote {");
    expect(source).not.toContain("export interface HeadlessRestDocNoteInput {");
  });

  it("leaves read-only fields out of the input and makes fields without a requirement optional", () => {
    const input = source.slice(source.indexOf("export interface HeadlessRestDocArticleInput {"));
    const body = input.slice(0, input.indexOf("}"));

    expect(body).not.toContain("id:");
    expect(body).not.toContain("shout:");
    expect(body).toContain("  title: string;");
    expect(body).toContain('  status?: "draft" | "live";');
    expect(body).toContain("  category?: number | null;");
  });

  it("describes regular models", () => {
    const article = model(source, "headless_rest.docarticle");

    expect(article).toContain("item: HeadlessRestDocArticle;");
    expect(article).toContain("id: number;");
    expect(article).toContain('status: "draft" | "live";');
    expect(article).toContain("readOnly: false;");
    expect(article).toContain("singleton: false;");
    expect(article).toContain("paginated: true;");
    // Pagination and expansion parameters are not filters
    expect(article).not.toContain("page:");
    expect(article).not.toContain("expand:");
  });

  it("describes expandable relations", () => {
    expect(model(source, "headless_rest.docarticle")).toContain(
      'category: { model: "headless_rest.doccategory"; many: false; nullable: true };',
    );
    expect(model(source, "headless_rest.docarticle")).toContain(
      'tags: { model: "headless_rest.doctag"; many: true; nullable: false };',
    );
    expect(model(source, "headless_rest.doccategory")).toContain(
      'docarticle_set: { model: "headless_rest.docarticle"; many: true; nullable: false };',
    );
  });

  it("describes lookup routes", () => {
    const page = model(source, "headless_rest.docpage");
    expect(page).toMatch(/lookups: \{\s+slug: string;\s+uid: string;\s+\};/);
  });

  it("describes read-only models and singletons", () => {
    expect(model(source, "headless_rest.docnote")).toContain("input: never;");
    expect(model(source, "headless_rest.docnote")).toContain("readOnly: true;");

    const settings = model(source, "headless_rest.docsettings");
    expect(settings).toContain("singleton: true;");
    expect(settings).toContain("readOnly: false;");
  });

  it("detects lists without pagination", () => {
    const unpaginated = structuredClone(schema);
    const list = unpaginated.paths!["/headless_rest.doctag"]!.get!;
    list.responses!["200"]!.content!["application/json"]!.schema = {
      type: "array",
      items: { $ref: "#/components/schemas/HeadlessRestDocTag" },
    };

    expect(model(generate(unpaginated), "headless_rest.doctag")).toContain("paginated: false;");
  });

  it("reads filters from schemas without the x-filter extension", () => {
    const legacy = structuredClone(schema);
    for (const item of Object.values(legacy.paths!)) {
      for (const operation of Object.values(item)) {
        for (const parameter of operation.parameters ?? []) {
          delete parameter["x-filter"];
        }
      }
    }

    expect(model(generate(legacy), "headless_rest.doctag")).toMatch(/filters: \{[^}]*name: string;/);
  });

  it("rejects schemas without routes of exposed models", () => {
    expect(() => generate({} as OpenAPIDocument)).toThrow("no paths");
    expect(() => generate({ paths: {} })).toThrow("no routes");
  });
});

describe("renderType", () => {
  it.each([
    [{ type: "string" }, "string"],
    [{ type: "integer", nullable: true }, "number | null"],
    [{ type: "array", items: { type: "string", nullable: true } }, "(string | null)[]"],
    [{ enum: ["a", "b", null], nullable: true }, '"a" | "b" | null'],
    [{ $ref: "#/components/schemas/BlogArticle" }, "BlogArticle"],
    [{ type: "object" }, "{ [key: string]: unknown }"],
    [{ type: "object", additionalProperties: { type: "number" } }, "{ [key: string]: number }"],
    [{ type: "object", properties: { "a-b": { type: "boolean" } }, required: ["a-b"] }, '{ "a-b": boolean }'],
    [{ oneOf: [{ type: "string" }, { type: "integer" }] }, "string | number"],
    [{}, "unknown"],
  ])("renders %j as %s", (schema, type) => {
    expect(renderType(schema)).toBe(type);
  });
});
