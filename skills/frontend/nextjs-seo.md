---
name: frontend-nextjs-seo
description: Implementing SEO for Next.js applications
---



# Next.js SEO

**Scope**: Metadata API, Open Graph, structured data (JSON-LD), sitemaps, robots.txt
**Lines**: ~280
**Last Updated**: 2025-10-18

## When to Use This Skill

Activate this skill when:
- Implementing SEO for Next.js applications
- Adding metadata and Open Graph tags
- Creating sitemaps and robots.txt
- Implementing structured data
- Optimizing for social sharing
- Improving search engine visibility

## Core Concepts

### SEO Fundamentals

**On-page SEO**:
- Title tags (50-60 characters)
- Meta descriptions (150-160 characters)
- Heading hierarchy (H1, H2, H3)
- URL structure (descriptive, kebab-case)
- Internal linking

**Technical SEO**:
- Sitemap.xml
- Robots.txt
- Canonical URLs
- Structured data (JSON-LD)
- Performance (Core Web Vitals)

---

## Metadata API

### Static Metadata

```tsx
// app/page.tsx
import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Home - My Website',
  description: 'Welcome to my website. Discover amazing products and services.',
  keywords: ['product', 'service', 'website'],
  authors: [{ name: 'John Doe', url: 'https://example.com/authors/john' }],
  creator: 'John Doe',
  publisher: 'My Company',
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      'max-video-preview': -1,
      'max-image-preview': 'large',
      'max-snippet': -1,
    },
  },
  alternates: {
    canonical: 'https://example.com',
    languages: {
      'en-US': 'https://example.com',
      'es-ES': 'https://example.com/es',
    },
  },
};

export default function HomePage() {
  return <h1>Home Page</h1>;
}
```

### Dynamic Metadata

```tsx
// app/blog/[slug]/page.tsx
import type { Metadata } from 'next';

interface Props {
  params: { slug: string };
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  // Fetch post data
  const post = await getPost(params.slug);

  return {
    title: post.title,
    description: post.excerpt,
    authors: [{ name: post.author.name }],
    openGraph: {
      title: post.title,
      description: post.excerpt,
      type: 'article',
      publishedTime: post.publishedAt,
      authors: [post.author.name],
      images: [
        {
          url: post.coverImage,
          width: 1200,
          height: 630,
          alt: post.title,
        },
      ],
    },
    twitter: {
      card: 'summary_large_image',
      title: post.title,
      description: post.excerpt,
      images: [post.coverImage],
    },
  };
}

export default function BlogPostPage({ params }: Props) {
  return <article>...</article>;
}
```

### Title Templates

```tsx
// app/layout.tsx
import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: {
    default: 'My Website',
    template: '%s | My Website', // Page title will be "About | My Website"
  },
  description: 'Default description',
};

// app/about/page.tsx
export const metadata: Metadata = {
  title: 'About', // Becomes "About | My Website"
};
```

### Viewport and Theme Color

```tsx
// app/layout.tsx
import type { Viewport } from 'next';

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  maximumScale: 1,
  themeColor: [
    { media: '(prefers-color-scheme: light)', color: '#ffffff' },
    { media: '(prefers-color-scheme: dark)', color: '#000000' },
  ],
};
```

---

## Open Graph and Twitter Cards

### Open Graph Tags

```tsx
// app/page.tsx
import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Product Name',
  description: 'Product description',
  openGraph: {
    type: 'website',
    url: 'https://example.com',
    title: 'Product Name',
    description: 'Product description',
    siteName: 'My Website',
    locale: 'en_US',
    images: [
      {
        url: 'https://example.com/og-image.jpg',
        width: 1200,
        height: 630,
        alt: 'Product preview',
        type: 'image/jpeg',
      },
    ],
  },
};
```

### Twitter Cards

```tsx
export const metadata: Metadata = {
  twitter: {
    card: 'summary_large_image', // or 'summary', 'app', 'player'
    site: '@mywebsite',
    creator: '@johndoe',
    title: 'Product Name',
    description: 'Product description',
    images: ['https://example.com/twitter-image.jpg'],
  },
};
```

### Article Metadata

```tsx
// app/blog/[slug]/page.tsx
export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const post = await getPost(params.slug);

  return {
    openGraph: {
      type: 'article',
      url: `https://example.com/blog/${params.slug}`,
      title: post.title,
      description: post.excerpt,
      publishedTime: post.publishedAt,
      modifiedTime: post.updatedAt,
      authors: [post.author.name],
      section: post.category,
      tags: post.tags,
      images: [
        {
          url: post.coverImage,
          width: 1200,
          height: 630,
        },
      ],
    },
  };
}
```

---

## Structured Data (JSON-LD)

### Organization

```tsx
// app/layout.tsx
export default function RootLayout({ children }: { children: React.ReactNode }) {
  const organizationSchema = {
    '@context': 'https://schema.org',
    '@type': 'Organization',
    name: 'My Company',
    url: 'https://example.com',
    logo: 'https://example.com/logo.png',
    sameAs: [
      'https://twitter.com/mycompany',
      'https://facebook.com/mycompany',
      'https://linkedin.com/company/mycompany',
    ],
    contactPoint: {
      '@type': 'ContactPoint',
      telephone: '+1-555-1234',
      contactType: 'Customer Service',
      email: 'support@example.com',
    },
  };

  return (
    <html>
      <head>
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(organizationSchema) }}
        />
      </head>
      <body>{children}</body>
    </html>
  );
}
```

### Article

```tsx
// app/blog/[slug]/page.tsx
export default async function BlogPostPage({ params }: Props) {
  const post = await getPost(params.slug);

  const articleSchema = {
    '@context': 'https://schema.org',
    '@type': 'Article',
    headline: post.title,
    description: post.excerpt,
    image: post.coverImage,
    datePublished: post.publishedAt,
    dateModified: post.updatedAt,
    author: {
      '@type': 'Person',
      name: post.author.name,
      url: post.author.url,
    },
    publisher: {
      '@type': 'Organization',
      name: 'My Website',
      logo: {
        '@type': 'ImageObject',
        url: 'https://example.com/logo.png',
      },
    },
    mainEntityOfPage: {
      '@type': 'WebPage',
      '@id': `https://example.com/blog/${params.slug}`,
    },
  };

  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(articleSchema) }}
      />
      <article>
        <h1>{post.title}</h1>
        <div dangerouslySetInnerHTML={{ __html: post.content }} />
      </article>
    </>
  );
}
```

### Product

```tsx
// app/products/[id]/page.tsx
export default async function ProductPage({ params }: Props) {
  const product = await getProduct(params.id);

  const productSchema = {
    '@context': 'https://schema.org',
    '@type': 'Product',
    name: product.name,
    description: product.description,
    image: product.images,
    sku: product.sku,
    brand: {
      '@type': 'Brand',
      name: product.brand,
    },
    offers: {
      '@type': 'Offer',
      url: `https://example.com/products/${params.id}`,
      priceCurrency: 'USD',
      price: product.price,
      availability: product.inStock
        ? 'https://schema.org/InStock'
        : 'https://schema.org/OutOfStock',
      priceValidUntil: '2025-12-31',
    },
    aggregateRating: {
      '@type': 'AggregateRating',
      ratingValue: product.rating,
      reviewCount: product.reviewCount,
    },
  };

  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(productSchema) }}
      />
      <div>
        <h1>{product.name}</h1>
        <p>{product.description}</p>
      </div>
    </>
  );
}
```

### Breadcrumbs

```tsx
// app/blog/[category]/[slug]/page.tsx
const breadcrumbSchema = {
  '@context': 'https://schema.org',
  '@type': 'BreadcrumbList',
  itemListElement: [
    {
      '@type': 'ListItem',
      position: 1,
      name: 'Home',
      item: 'https://example.com',
    },
    {
      '@type': 'ListItem',
      position: 2,
      name: 'Blog',
      item: 'https://example.com/blog',
    },
    {
      '@type': 'ListItem',
      position: 3,
      name: category,
      item: `https://example.com/blog/${category}`,
    },
    {
      '@type': 'ListItem',
      position: 4,
      name: post.title,
      item: `https://example.com/blog/${category}/${slug}`,
    },
  ],
};
```

---

## Sitemap

### Static Sitemap

```tsx
// app/sitemap.ts
import { MetadataRoute } from 'next';

export default function sitemap(): MetadataRoute.Sitemap {
  return [
    {
      url: 'https://example.com',
      lastModified: new Date(),
      changeFrequency: 'daily',
      priority: 1,
    },
    {
      url: 'https://example.com/about',
      lastModified: new Date(),
      changeFrequency: 'monthly',
      priority: 0.8,
    },
    {
      url: 'https://example.com/blog',
      lastModified: new Date(),
      changeFrequency: 'weekly',
      priority: 0.9,
    },
  ];
}
```

### Dynamic Sitemap

```tsx
// app/sitemap.ts
import { MetadataRoute } from 'next';

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  // Fetch dynamic content
  const posts = await getPosts();
  const products = await getProducts();

  const postUrls = posts.map((post) => ({
    url: `https://example.com/blog/${post.slug}`,
    lastModified: post.updatedAt,
    changeFrequency: 'weekly' as const,
    priority: 0.7,
  }));

  const productUrls = products.map((product) => ({
    url: `https://example.com/products/${product.id}`,
    lastModified: product.updatedAt,
    changeFrequency: 'daily' as const,
    priority: 0.8,
  }));

  return [
    {
      url: 'https://example.com',
      lastModified: new Date(),
      changeFrequency: 'daily',
      priority: 1,
    },
    ...postUrls,
    ...productUrls,
  ];
}
```

### Multiple Sitemaps

```tsx
// app/sitemap.ts (index sitemap)
import { MetadataRoute } from 'next';

export default function sitemap(): MetadataRoute.Sitemap {
  return [
    {
      url: 'https://example.com/sitemap/posts.xml',
    },
    {
      url: 'https://example.com/sitemap/products.xml',
    },
  ];
}

// app/sitemap/posts/sitemap.ts
export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const posts = await getPosts();
  return posts.map((post) => ({
    url: `https://example.com/blog/${post.slug}`,
    lastModified: post.updatedAt,
  }));
}
```

---

## Robots.txt

### Static Robots.txt

```tsx
// app/robots.ts
import { MetadataRoute } from 'next';

export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: '*',
      allow: '/',
      disallow: ['/api/', '/admin/', '/private/'],
    },
    sitemap: 'https://example.com/sitemap.xml',
  };
}
```

### Environment-Specific Robots.txt

```tsx
// app/robots.ts
import { MetadataRoute } from 'next';

export default function robots(): MetadataRoute.Robots {
  const isProduction = process.env.NODE_ENV === 'production';

  return {
    rules: {
      userAgent: '*',
      allow: isProduction ? '/' : [],
      disallow: isProduction ? ['/api/', '/admin/'] : ['/'],
    },
    sitemap: isProduction ? 'https://example.com/sitemap.xml' : undefined,
  };
}
```

---

## Canonical URLs

### Setting Canonical URL

```tsx
// app/blog/[slug]/page.tsx
import type { Metadata } from 'next';

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  return {
    alternates: {
      canonical: `https://example.com/blog/${params.slug}`,
    },
  };
}
```

### Handling Duplicates

```tsx
// If content exists at multiple URLs, point to primary
export const metadata: Metadata = {
  alternates: {
    canonical: 'https://example.com/primary-url',
  },
};
```

---

## URL Structure Best Practices

### SEO-Friendly URLs

```
✅ Good:
https://example.com/blog/how-to-optimize-images
https://example.com/products/laptops/macbook-pro-2024

❌ Bad:
https://example.com/blog?id=12345
https://example.com/p/1a2b3c
```

**Guidelines**:
- Use hyphens (not underscores)
- Lowercase only
- Descriptive keywords
- Short and readable
- Avoid parameters when possible

---

## Quick Reference

### Metadata Checklist

```
[ ] Title (50-60 characters)
[ ] Description (150-160 characters)
[ ] Open Graph tags (og:title, og:description, og:image)
[ ] Twitter Card tags
[ ] Canonical URL
[ ] Robots meta tag
[ ] Structured data (JSON-LD)
[ ] Sitemap.xml
[ ] Robots.txt
[ ] Alt text for images
[ ] Heading hierarchy (H1 → H6)
```

### Essential Meta Tags

```tsx
export const metadata: Metadata = {
  title: 'Page Title',
  description: 'Page description',
  openGraph: {
    title: 'Page Title',
    description: 'Page description',
    images: ['/og-image.jpg'],
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Page Title',
    description: 'Page description',
    images: ['/twitter-image.jpg'],
  },
  alternates: {
    canonical: 'https://example.com/page',
  },
};
```

### Structured Data Types

```
Organization - Company info
Article - Blog posts
Product - E-commerce products
BreadcrumbList - Navigation breadcrumbs
FAQPage - FAQ pages
LocalBusiness - Local business info
Recipe - Recipe content
Review - Product/service reviews
Event - Event listings
VideoObject - Video content
```

---

## SEO Testing Tools

**Google Tools**:
- Google Search Console
- Google Rich Results Test
- PageSpeed Insights

**Third-party Tools**:
- Screaming Frog SEO Spider
- Ahrefs Site Audit
- SEMrush Site Audit
- Lighthouse (Chrome DevTools)

---

## Common Anti-Patterns

❌ **Missing title/description**: Search engines generate own (poor quality)
✅ Always provide custom metadata

❌ **Duplicate content**: Multiple URLs with same content
✅ Use canonical URLs

❌ **Blocking crawlers**: robots.txt blocks important pages
✅ Only block admin/API routes

❌ **Missing structured data**: Reduced search visibility
✅ Implement JSON-LD for content types

❌ **Poor URL structure**: Non-descriptive, parameter-heavy URLs
✅ Use clean, keyword-rich URLs

---

## Level 3: Resources

This skill includes comprehensive Level 3 resources in `skills/frontend/nextjs-seo/resources/`:

### Reference Documentation

**REFERENCE.md** (~1000 lines): Comprehensive reference guide covering:
- Metadata API (static and dynamic)
- Open Graph Protocol (website, article, product, video)
- Twitter Cards (all card types)
- Structured data (JSON-LD schemas for all content types)
- Sitemap generation (static, dynamic, multi-language)
- Robots.txt configuration
- Canonical URLs
- Meta tags best practices
- Core Web Vitals and performance
- Image optimization for SEO
- Internationalization (i18n) for SEO
- Advanced patterns and testing

### Executable Scripts

Located in `resources/scripts/`:

1. **check_seo.py** - SEO tag validation tool
   - Validates meta tags, Open Graph, Twitter Cards, structured data
   - Checks title/description lengths
   - Verifies canonical URLs and robots directives
   - Reports issues, warnings, and successes
   - JSON output support
   - Usage: `./check_seo.py <url> [--json] [--output file.json]`

2. **generate_sitemap.py** - Next.js sitemap generator
   - Scans App Router directory structure
   - Supports dynamic routes ([param], [...slug], [[...slug]])
   - Auto-assigns priorities based on path depth
   - Customizable exclusions
   - XML and JSON output
   - Usage: `./generate_sitemap.py [--app-dir ./app] [--base-url https://example.com] [--output public/sitemap.xml]`

3. **test_metadata.js** - Metadata validation utility
   - Analyzes Next.js page files for metadata exports
   - Validates static and dynamic metadata
   - Checks for required fields
   - TypeScript type checking
   - Error handling validation
   - Usage: `./test_metadata.js <path-to-page> [--json] [--params id=123]`

### TypeScript Examples

Located in `resources/examples/typescript/`:

1. **app-router-metadata.tsx** - Complete metadata examples
   - Static metadata (layouts and pages)
   - Dynamic metadata with database queries
   - Multi-language metadata
   - Environment-based metadata
   - Paginated content
   - Error handling patterns

2. **dynamic-og-images.tsx** - Dynamic OG image generation
   - Basic dynamic images with next/og
   - Blog post images with custom fonts
   - Product images with layouts
   - Author profile images
   - Stats/metrics images
   - Multi-style images based on category
   - Branded images with logos

3. **structured-data.ts** - JSON-LD schema examples
   - Organization schema
   - Article schema
   - Product schema (with reviews and ratings)
   - Breadcrumb schema
   - FAQ schema
   - Local business schema
   - WebSite search action
   - Video schema
   - Course schema
   - Event schema
   - Reusable TypeScript types and components

4. **sitemap.ts** - Sitemap generation patterns
   - Static sitemaps
   - Dynamic sitemaps with database
   - Multi-language sitemaps
   - Custom priority calculations
   - Exclusion filters
   - Paginated content
   - Sitemap indexes for large sites
   - Caching strategies
   - Error handling

5. **robots.ts** - robots.txt patterns
   - Basic robots.txt
   - Multiple user agents
   - Environment-specific rules
   - E-commerce configurations
   - Blog/content site rules
   - SaaS application rules
   - Custom crawl delays
   - Block specific bots
   - Regional configurations
   - Helper functions

All scripts are executable with `--help` flags and support `--json` output for automation.

---

## Related Skills

- `nextjs-app-router.md` - Metadata API, generateMetadata
- `frontend-performance.md` - Core Web Vitals (affects SEO)
- `web-accessibility.md` - Semantic HTML, alt text

---

**Last Updated**: 2025-10-27
**Format Version**: 1.0 (Atomic)
