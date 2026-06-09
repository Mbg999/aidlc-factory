import { writeFileSync, existsSync, mkdirSync } from 'fs';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const dist = resolve(__dirname, '..', 'dist');

const SITE_URL = process.env.VITE_SITE_URL || 'https://mbg999.github.io/aidlc-factory';

const pages = [
  { path: '/', priority: '1.00', changefreq: 'weekly' },
  { path: '/installation', priority: '0.90', changefreq: 'monthly' },
  { path: '/usage', priority: '0.85', changefreq: 'monthly' },
  { path: '/commands', priority: '0.80', changefreq: 'monthly' },
  { path: '/architecture', priority: '0.90', changefreq: 'monthly' },
  { path: '/configuration', priority: '0.80', changefreq: 'monthly' },
  { path: '/examples', priority: '0.75', changefreq: 'monthly' },
];

const today = new Date().toISOString().split('T')[0];

const xml = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${pages.map(p => `  <url>
    <loc>${SITE_URL}${p.path}</loc>
    <lastmod>${today}</lastmod>
    <changefreq>${p.changefreq}</changefreq>
    <priority>${p.priority}</priority>
  </url>`).join('\n')}
</urlset>`;

if (!existsSync(dist)) mkdirSync(dist, { recursive: true });
writeFileSync(resolve(dist, 'sitemap.xml'), xml, 'utf-8');
console.log('✓ sitemap.xml generated');
