import { Helmet } from 'react-helmet-async';
import { SITE, PageMeta } from '../config/seo';

type SEOProps = Partial<PageMeta> & {
  jsonLd?: Record<string, unknown>;
};

export function SEO({ title, description, path, keywords, type, jsonLd }: SEOProps) {
  const pageTitle = title ? `${title} · ${SITE.name}` : `${SITE.name} · ${SITE.tagline}`;
  const pageDescription = description || SITE.description;
  const pageUrl = `${SITE.url}${path || '/'}`;
  const pageType = type || 'website';

  return (
    <Helmet>
      <title>{pageTitle}</title>
      <meta name="description" content={pageDescription} />
      {keywords && <meta name="keywords" content={keywords} />}
      <link rel="canonical" href={pageUrl} />

      <meta property="og:type" content={pageType} />
      <meta property="og:title" content={pageTitle} />
      <meta property="og:description" content={pageDescription} />
      <meta property="og:url" content={pageUrl} />
      <meta property="og:site_name" content={SITE.name} />
      <meta property="og:locale" content={SITE.locale} />
      <meta property="og:image" content={`${SITE.url}/assets/images/og-image.png`} />
      <meta property="og:image:width" content="1200" />
      <meta property="og:image:height" content="630" />

      <meta name="twitter:card" content="summary_large_image" />
      <meta name="twitter:site" content={SITE.twitterHandle} />
      <meta name="twitter:title" content={pageTitle} />
      <meta name="twitter:description" content={pageDescription} />
      <meta name="twitter:image" content={`${SITE.url}/assets/images/og-image.png`} />

      {jsonLd && (
        <script type="application/ld+json">{JSON.stringify(jsonLd)}</script>
      )}
    </Helmet>
  );
}

export function DefaultSEO() {
  const siteSchema = {
    '@context': 'https://schema.org',
    '@type': 'SoftwareApplication',
    name: SITE.name,
    applicationCategory: 'DeveloperApplication',
    operatingSystem: 'Cross-platform',
    description: SITE.description,
    url: SITE.url,
    author: {
      '@type': 'Organization',
      name: 'AIDLC-Factory',
    },
    offers: {
      '@type': 'Offer',
      price: '0',
      priceCurrency: 'USD',
    },
  };

  return (
    <Helmet>
      <script type="application/ld+json">{JSON.stringify(siteSchema)}</script>
    </Helmet>
  );
}

export function getDocSchema(page: PageMeta) {
  return {
    '@context': 'https://schema.org',
    '@type': 'TechArticle',
    headline: page.title,
    description: page.description,
    url: `${SITE.url}${page.path}`,
    author: {
      '@type': 'Organization',
      name: 'AIDLC-Factory',
    },
    publisher: {
      '@type': 'Organization',
      name: 'AIDLC-Factory',
    },
    mainEntityOfPage: {
      '@type': 'WebPage',
      '@id': `${SITE.url}${page.path}`,
    },
    inLanguage: SITE.language,
  };
}
