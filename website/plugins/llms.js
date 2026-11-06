// Writes llms.txt, llms-full.txt and a Markdown copy of every docs page
// (/docs/<page>.md) into the build output, for AI agents (https://llmstxt.org).
const fs = require('fs');
const path = require('path');

const DOCS_DIR = path.join(__dirname, '..', 'docs');

function parseFrontMatter(source) {
  const match = source.match(/^---\n([\s\S]*?)\n---\n/);
  if (!match) return { data: {}, body: source };
  const data = {};
  for (const line of match[1].split('\n')) {
    const [key, ...rest] = line.split(':');
    if (key && rest.length) data[key.trim()] = rest.join(':').trim();
  }
  return { data, body: source.slice(match[0].length) };
}

function readPages(siteUrl) {
  return fs
    .readdirSync(DOCS_DIR)
    .filter((file) => file.endsWith('.md'))
    .map((file) => {
      const { data, body } = parseFrontMatter(fs.readFileSync(path.join(DOCS_DIR, file), 'utf8'));
      const slug = file.replace(/\.md$/, '');
      // Relative links to other pages become absolute links to their Markdown copies.
      const markdown = body
        .replace(/\]\(\.\/([\w-]+)\.md(#[\w-]*)?\)/g, `](${siteUrl}/docs/$1.md$2)`)
        .trim();
      const heading = markdown.match(/^# (.+)$/m);
      // Page titles start with an emoji for the sidebar; drop it here.
      const title = heading ? heading[1].replace(/^[^\p{L}\p{N}`]+/u, '').trim() : slug;
      const paragraph = markdown
        .split(/\n\s*\n/)
        .find((block) => block.trim() && !/^(#|```|:::|\||-|\d+\.)/.test(block.trim()));
      const description = paragraph ? paragraph.replace(/\s+/g, ' ').trim().split(/(?<=\.)\s/)[0] : '';
      return { slug, title, description, markdown, position: Number(data.sidebar_position ?? 999) };
    })
    .sort((a, b) => a.position - b.position);
}

module.exports = function llmsPlugin(context) {
  return {
    name: 'llms-txt',
    async postBuild({ outDir }) {
      const { url, title, tagline } = context.siteConfig;
      const pages = readPages(url);

      fs.mkdirSync(path.join(outDir, 'docs'), { recursive: true });
      for (const page of pages) {
        fs.writeFileSync(path.join(outDir, 'docs', `${page.slug}.md`), `${page.markdown}\n`);
      }

      const index = [
        `# ${title}`,
        '',
        `> ${tagline}. Django Headless generates a Django REST Framework API for the Django models you decorate with \`@expose()\`, for a frontend such as Next.js or Astro.`,
        '',
        'Every page below is plain Markdown. The full documentation in one file is at ' +
          `${url}/llms-full.txt. An agent skill with the essentials is at ` +
          'https://github.com/dwarsbit/django-headless/tree/main/skills/django-headless.',
        '',
        '## Docs',
        '',
        ...pages.map((page) => `- [${page.title}](${url}/docs/${page.slug}.md): ${page.description}`),
        '',
        '## Optional',
        '',
        '- [Changelog](https://github.com/dwarsbit/django-headless/blob/main/CHANGELOG.md)',
        '- [Source code](https://github.com/dwarsbit/django-headless)',
        '',
      ].join('\n');
      fs.writeFileSync(path.join(outDir, 'llms.txt'), index);

      const full = [`# ${title}`, '', `> ${tagline}.`, '', ...pages.map((page) => page.markdown)].join('\n\n');
      fs.writeFileSync(path.join(outDir, 'llms-full.txt'), `${full}\n`);
    },
  };
};
