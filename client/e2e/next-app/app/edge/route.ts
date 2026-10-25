import { api } from "../../lib/api";

export const runtime = "edge";
export const dynamic = "force-dynamic";

declare const EdgeRuntime: string | undefined;

export async function GET() {
  const article = await api.model("blog.article").retrieveBy("slug", "getting-started-with-django", {
    fields: ["id", "title"],
  });

  return Response.json({ runtime: typeof EdgeRuntime === "string" ? "edge" : "nodejs", title: article.title });
}
