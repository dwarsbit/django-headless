import { api } from "../api";

// Rendered once, at build time
export const dynamic = "force-static";

export default async function Home() {
  const settings = await api.singleton("blog.sitesettings").retrieve();
  const articles = await api
    .model("blog.article")
    .all({ filters: { status: "published" }, expand: ["category"], ordering: "id" }, { init: { cache: "force-cache" } });

  return (
    <main>
      <h1>{settings.site_name}</h1>
      <ul>
        {articles.map((article) => (
          <li key={article.id}>
            {article.title}
            {article.category ? ` (${article.category.name})` : null}
          </li>
        ))}
      </ul>
    </main>
  );
}
