// @ts-check
// Note: type casting allows for JS/TS features in this file.

/** @type {import('@docusaurus/types').Config} */
const config = {
  title: 'Rizz Project Documentation',
  tagline: 'Enterprise-Scale Development Platform',
  favicon: 'img/favicon.ico',

  url: 'https://docs.rizz.dev',
  baseUrl: '/',
  organizationName: 'username9999-sys',
  projectName: 'Rizz',

  onBrokenLinks: 'throw',
  onBrokenMarkdownLinks: 'warn',

  i18n: {
    defaultLocale: 'en',
    locales: ['en', 'id'],
  },

  presets: [
    [
      'classic',
      /** @type {import('@docusaurus/preset-classic').Options} */
      ({
        docs: {
          sidebarPath: require.resolve('./sidebars.js'),
          editUrl: 'https://github.com/username9999-sys/Rizz/tree/main/docs/docusaurus/',
          routeBasePath: '/',
        },
        blog: {
          showReadingTime: true,
          editUrl: 'https://github.com/username9999-sys/Rizz/tree/main/docs/docusaurus/blog/',
        },
        theme: {
          customCss: require.resolve('./src/css/custom.css'),
        },
        gtag: {
          trackingID: 'G-XXXXXXXXXX',
          anonymizeIP: true,
        },
        sitemap: {
          changefreq: 'weekly',
          priority: 0.5,
          ignorePatterns: ['/tags/**'],
        },
      }),
    ],
  ],

  themeConfig:
    /** @type {import('@docusaurus/preset-classic').ThemeConfig} */
    ({
      navbar: {
        title: 'Rizz Docs',
        logo: {
          alt: 'Rizz Logo',
          src: 'img/logo.svg',
        },
        items: [
          {
            type: 'docSidebar',
            sidebarId: 'tutorialSidebar',
            position: 'left',
            label: 'Documentation',
          },
          { to: '/blog', label: 'Blog', position: 'left' },
          {
            href: 'https://github.com/username9999-sys/Rizz',
            label: 'GitHub',
            position: 'right',
          },
        ],
      },
      footer: {
        style: 'dark',
        links: [
          {
            title: 'Docs',
            items: [
              { label: 'Getting Started', to: '/docs/intro' },
              { label: 'API Reference', to: '/docs/api' },
              { label: 'Tutorials', to: '/docs/tutorials' },
            ],
          },
          {
            title: 'Community',
            items: [
              { label: 'Discord', href: 'https://discord.gg/rizz' },
              { label: 'Twitter', href: 'https://twitter.com/rizz_dev' },
            ],
          },
          {
            title: 'More',
            items: [
              { label: 'Blog', to: '/blog' },
              { label: 'GitHub', href: 'https://github.com/username9999-sys/Rizz' },
            ],
          },
        ],
        copyright: `Copyright © ${new Date().getFullYear()} Rizz Project. Built with ❤️ by username9999`,
      },
      prism: {
        theme: require('prism-react-renderer').themes.github,
        darkTheme: require('prism-react-renderer').themes.dracula,
        additionalLanguages: ['python', 'javascript', 'bash', 'json', 'yaml'],
      },
      algolia: {
        appId: 'YOUR_ALGOLIA_APP_ID',
        apiKey: 'YOUR_ALGOLIA_API_KEY',
        indexName: 'rizz',
        contextualSearch: true,
      },
      colorMode: {
        defaultMode: 'dark',
        disableSwitch: false,
        respectPrefersColorScheme: true,
      },
      docs: {
        sidebar: {
          hideable: true,
          autoCollapseCategories: true,
        },
      },
    }),
};

module.exports = config;
