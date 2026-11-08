// @ts-check
// The Python package and the client share one version (set by
// scripts/bump_version.py). The Release workflow redeploys the docs after a release.
const { version } = require('../client/package.json');
const releaseUrl = `https://github.com/dwarsbit/django-headless/releases/tag/v${version}`;

/** @type {import('@docusaurus/types').DocusaurusConfig} */
const config = {
  title: 'Django Headless',
  tagline: 'A REST API for your Django models',
  favicon: 'img/favicon.svg',
  url: 'https://djangoheadless.org',
  baseUrl: '/',
  organizationName: 'dwarsbit',
  projectName: 'django-headless',
  onBrokenLinks: 'throw',
  markdown: {
    hooks: {
      onBrokenMarkdownLinks: 'warn',
    },
  },
  trailingSlash: false,
  customFields: { version, releaseUrl },
  scripts: [],
  themes: [],
  plugins: [require.resolve('./plugins/llms.js')],
  themeConfig:
    /** @type {import('@docusaurus/preset-classic').ThemeConfig} */
    ({
      colorMode: {
        defaultMode: 'light',
        respectPrefersColorScheme: true,
      },
      navbar: {
        title: 'Django Headless',
        logo: {
          alt: 'Django Headless',
          src: 'img/logo.svg',
        },
        items: [
          {
            type: 'html',
            position: 'left',
            value: `<a class="dhh-version" href="${releaseUrl}" title="Release notes for v${version}">v${version}</a>`,
          },
          {
            label: 'Docs',
            position: 'left',
            to: 'docs/intro',
          },
          {
            href: 'https://dwarsbit.github.io/django-content-studio/',
            label: 'Django Content Studio',
            position: 'right',
          },
          {
            href: 'https://djangostack.org',
            label: 'Django Stack',
            position: 'right',
          },
          {
            href: 'https://github.com/dwarsbit/django-headless',
            label: 'GitHub',
            position: 'right',
          },
          {
            href: 'https://pypi.org/project/django-headless/',
            label: 'PyPI',
            position: 'right',
          },
        ],
      },
      footer: {
        style: 'dark',
        copyright: `Copyright © ${new Date().getFullYear()} Leon van der Grient. Built with Django, REST Framework and Docusaurus.`,
        links: [
          {
            title: 'Docs',
            items: [
              { label: 'Introduction', to: '/docs/intro' },
              { label: 'Installation', to: '/docs/installation' },
              { label: 'Settings reference', to: '/docs/settings' },
            ],
          },
          {
            title: 'Project',
            items: [
              { label: 'GitHub', href: 'https://github.com/dwarsbit/django-headless' },
              { label: 'PyPI', href: 'https://pypi.org/project/django-headless/' },
              { label: 'Changelog', href: 'https://github.com/dwarsbit/django-headless/blob/main/CHANGELOG.md' },
              { label: 'Django Content Studio', href: 'https://dwarsbit.github.io/django-content-studio/' },
              { label: 'Django Stack', href: 'https://djangostack.org' },
            ],
          },
        ],
      },
      prism: {
        additionalLanguages: ['bash', 'http', 'json', 'python', 'yaml'],
      },
    }),
  presets: [
    [
      'classic',
      /** @type {import('@docusaurus/preset-classic').Options} */
      ({
        docs: {
          sidebarPath: require.resolve('./sidebars.js'),
          editUrl: 'https://github.com/dwarsbit/django-headless/edit/main/website/',
          showLastUpdateTime: true,
        },
        blog: false,
        theme: {
          customCss: require.resolve('./src/css/custom.css'),
        },
      }),
    ],
  ],
};

module.exports = config;
