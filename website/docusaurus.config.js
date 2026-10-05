// @ts-check
/** @type {import('@docusaurus/types').DocusaurusConfig} */
const config = {
  title: 'Django Headless',
  tagline: 'Automagically create a REST API for your Django models',
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
  scripts: [],
  themes: [],
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
            label: 'Docs',
            position: 'left',
            to: 'docs/intro',
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
            ],
          },
        ],
      },
      prism: {
        additionalLanguages: ['bash', 'json', 'python', 'yaml'],
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
