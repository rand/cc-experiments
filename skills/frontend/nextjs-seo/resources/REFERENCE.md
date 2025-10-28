# Next.js SEO Reference Guide

Comprehensive reference for implementing SEO in Next.js applications using the App Router and modern best practices.

## Table of Contents

1. [Metadata API Overview](#metadata-api-overview)
2. [Static Metadata](#static-metadata)
3. [Dynamic Metadata](#dynamic-metadata)
4. [Open Graph Protocol](#open-graph-protocol)
5. [Twitter Cards](#twitter-cards)
6. [Structured Data (JSON-LD)](#structured-data-json-ld)
7. [Sitemap Generation](#sitemap-generation)
8. [Robots.txt Configuration](#robotstxt-configuration)
9. [Canonical URLs](#canonical-urls)
10. [Meta Tags Best Practices](#meta-tags-best-practices)
11. [Core Web Vitals & Performance](#core-web-vitals--performance)
12. [Image Optimization for SEO](#image-optimization-for-seo)
13. [Internationalization (i18n) for SEO](#internationalization-i18n-for-seo)
14. [Advanced Patterns](#advanced-patterns)

---

## Metadata API Overview

Next.js 13+ App Router provides a powerful Metadata API for managing SEO tags.

### File-Based Metadata

```typescript
// app/layout.tsx or app/page.tsx
import { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'My App',
  description: 'App description',
}
```

### Function-Based Metadata

```typescript
// app/products/[id]/page.tsx
import { Metadata } from 'next'

export async function generateMetadata({ params }): Promise<Metadata> {
  const product = await fetchProduct(params.id)

  return {
    title: product.name,
    description: product.description,
  }
}
```

### Metadata Object Structure

```typescript
interface Metadata {
  // Basic metadata
  title?: string | TemplateString
  description?: string
  applicationName?: string
  authors?: Author | Author[]
  generator?: string
  keywords?: string | string[]
  referrer?: 'no-referrer' | 'origin' | 'no-referrer-when-downgrade' | 'origin-when-cross-origin' | 'same-origin' | 'strict-origin' | 'strict-origin-when-cross-origin' | 'unsafe-url'
  themeColor?: string | ThemeColorDescriptor | ThemeColorDescriptor[]
  colorScheme?: 'dark' | 'light' | 'normal'
  viewport?: string | Viewport
  creator?: string
  publisher?: string
  robots?: string | Robots

  // Icons
  icons?: Icons | IconDescriptor[]

  // Open Graph
  openGraph?: OpenGraph

  // Twitter
  twitter?: Twitter

  // Verification
  verification?: Verification

  // App links
  appLinks?: AppLinks

  // Alternate languages
  alternates?: Alternates

  // Archives
  archives?: string | string[]

  // Assets
  assets?: string | string[]

  // Bookmarks
  bookmarks?: string | string[]

  // Category
  category?: string

  // Classification
  classification?: string

  // Manifest
  manifest?: string

  // Meta base
  metadataBase?: URL | null

  // Other
  other?: Record<string, string | string[]>
}
```

---

## Static Metadata

Static metadata is defined at build time and doesn't change per request.

### Basic Page Metadata

```typescript
// app/about/page.tsx
import { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'About Us | Company Name',
  description: 'Learn about our mission, values, and team.',
  keywords: ['about us', 'company', 'mission', 'values'],
  authors: [{ name: 'Company Name', url: 'https://example.com' }],
  creator: 'Company Name',
  publisher: 'Company Name',
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
    canonical: 'https://example.com/about',
  },
}

export default function AboutPage() {
  return <div>About content</div>
}
```

### Layout Metadata (Inherited)

```typescript
// app/layout.tsx
import { Metadata } from 'next'

export const metadata: Metadata = {
  metadataBase: new URL('https://example.com'),
  title: {
    default: 'Company Name',
    template: '%s | Company Name',
  },
  description: 'Default description for all pages',
  applicationName: 'Company App',
  referrer: 'origin-when-cross-origin',
  keywords: ['nextjs', 'react', 'javascript'],
  authors: [{ name: 'Company', url: 'https://example.com' }],
  colorScheme: 'light',
  creator: 'Company Name',
  publisher: 'Company Name',
  formatDetection: {
    email: false,
    address: false,
    telephone: false,
  },
  icons: {
    icon: '/favicon.ico',
    shortcut: '/favicon-16x16.png',
    apple: '/apple-touch-icon.png',
    other: {
      rel: 'apple-touch-icon-precomposed',
      url: '/apple-touch-icon-precomposed.png',
    },
  },
  manifest: '/manifest.json',
  openGraph: {
    type: 'website',
    locale: 'en_US',
    url: 'https://example.com',
    siteName: 'Company Name',
    images: [
      {
        url: '/og-image.jpg',
        width: 1200,
        height: 630,
        alt: 'Company Name',
      },
    ],
  },
  twitter: {
    card: 'summary_large_image',
    site: '@company',
    creator: '@company',
  },
  verification: {
    google: 'google-site-verification-code',
    yandex: 'yandex-verification-code',
    yahoo: 'yahoo-verification-code',
  },
}
```

### Title Templates

```typescript
// app/layout.tsx
export const metadata: Metadata = {
  title: {
    default: 'Acme',
    template: '%s | Acme',
  },
}

// app/about/page.tsx
export const metadata: Metadata = {
  title: 'About', // Renders as "About | Acme"
}

// app/blog/[slug]/page.tsx
export async function generateMetadata({ params }): Promise<Metadata> {
  return {
    title: 'My Blog Post', // Renders as "My Blog Post | Acme"
  }
}
```

---

## Dynamic Metadata

Dynamic metadata is generated at request time based on route parameters or external data.

### Basic Dynamic Metadata

```typescript
// app/products/[id]/page.tsx
import { Metadata } from 'next'

interface Props {
  params: { id: string }
  searchParams: { [key: string]: string | string[] | undefined }
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const product = await fetch(`https://api.example.com/products/${params.id}`)
    .then((res) => res.json())

  return {
    title: product.name,
    description: product.description,
    openGraph: {
      title: product.name,
      description: product.description,
      images: [product.image],
    },
  }
}

export default async function ProductPage({ params }: Props) {
  const product = await fetch(`https://api.example.com/products/${params.id}`)
    .then((res) => res.json())

  return <div>{product.name}</div>
}
```

### With Database Queries

```typescript
// app/blog/[slug]/page.tsx
import { Metadata } from 'next'
import { db } from '@/lib/db'

interface Props {
  params: { slug: string }
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const post = await db.post.findUnique({
    where: { slug: params.slug },
    select: {
      title: true,
      excerpt: true,
      coverImage: true,
      author: { select: { name: true } },
      publishedAt: true,
      tags: true,
    },
  })

  if (!post) {
    return {
      title: 'Post Not Found',
    }
  }

  return {
    title: post.title,
    description: post.excerpt,
    authors: [{ name: post.author.name }],
    keywords: post.tags.map(tag => tag.name),
    openGraph: {
      title: post.title,
      description: post.excerpt,
      type: 'article',
      publishedTime: post.publishedAt.toISOString(),
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
  }
}
```

### With Search Params

```typescript
// app/search/page.tsx
import { Metadata } from 'next'

interface Props {
  searchParams: { q?: string; category?: string }
}

export async function generateMetadata({ searchParams }: Props): Promise<Metadata> {
  const query = searchParams.q || 'all products'
  const category = searchParams.category

  const title = category
    ? `Search results for "${query}" in ${category}`
    : `Search results for "${query}"`

  return {
    title,
    description: `Find the best products matching "${query}"`,
    robots: {
      index: false, // Don't index search results
      follow: true,
    },
  }
}
```

### Parallel Data Fetching

```typescript
// app/products/[id]/page.tsx
import { Metadata } from 'next'

async function getProduct(id: string) {
  const res = await fetch(`https://api.example.com/products/${id}`, {
    next: { revalidate: 3600 }, // Cache for 1 hour
  })
  return res.json()
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const product = await getProduct(params.id)

  return {
    title: product.name,
    description: product.description,
  }
}

export default async function ProductPage({ params }: Props) {
  // Same function is called, but Next.js deduplicates the request
  const product = await getProduct(params.id)

  return <div>{product.name}</div>
}
```

---

## Open Graph Protocol

Open Graph tags control how your content appears when shared on social media.

### Basic Open Graph

```typescript
export const metadata: Metadata = {
  openGraph: {
    type: 'website',
    url: 'https://example.com',
    title: 'My Website',
    description: 'Description of my website',
    siteName: 'Example Site',
    images: [
      {
        url: 'https://example.com/og-image.jpg',
        width: 1200,
        height: 630,
        alt: 'Example Site Preview',
        type: 'image/jpeg',
      },
    ],
    locale: 'en_US',
    localeAlternate: ['es_ES', 'fr_FR'],
  },
}
```

### Article Open Graph

```typescript
// app/blog/[slug]/page.tsx
export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const post = await getPost(params.slug)

  return {
    openGraph: {
      type: 'article',
      url: `https://example.com/blog/${params.slug}`,
      title: post.title,
      description: post.excerpt,
      siteName: 'My Blog',
      publishedTime: post.publishedAt.toISOString(),
      modifiedTime: post.updatedAt.toISOString(),
      expirationTime: post.expiresAt?.toISOString(),
      authors: post.authors.map(a => a.name),
      section: post.category,
      tags: post.tags,
      images: [
        {
          url: post.coverImage,
          width: 1200,
          height: 630,
          alt: post.title,
        },
      ],
    },
  }
}
```

### Product Open Graph

```typescript
export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const product = await getProduct(params.id)

  return {
    openGraph: {
      type: 'product',
      url: `https://example.com/products/${params.id}`,
      title: product.name,
      description: product.description,
      images: product.images.map(img => ({
        url: img.url,
        width: 1200,
        height: 630,
        alt: img.alt,
      })),
      product: {
        priceAmount: product.price,
        priceCurrency: 'USD',
        availability: product.inStock ? 'in stock' : 'out of stock',
        condition: 'new',
        retailer: 'Example Store',
      },
    },
  }
}
```

### Video Open Graph

```typescript
export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const video = await getVideo(params.id)

  return {
    openGraph: {
      type: 'video.movie',
      url: `https://example.com/videos/${params.id}`,
      title: video.title,
      description: video.description,
      videos: [
        {
          url: video.videoUrl,
          secureUrl: video.videoUrl,
          type: 'video/mp4',
          width: 1920,
          height: 1080,
        },
      ],
      images: [
        {
          url: video.thumbnail,
          width: 1200,
          height: 630,
        },
      ],
      releaseDate: video.releaseDate.toISOString(),
      duration: video.durationSeconds,
      actors: video.cast.map(a => a.name),
      directors: video.directors.map(d => d.name),
      tags: video.tags,
    },
  }
}
```

---

## Twitter Cards

Twitter Cards enhance how your content appears on Twitter/X.

### Summary Card

```typescript
export const metadata: Metadata = {
  twitter: {
    card: 'summary',
    site: '@username',
    creator: '@username',
    title: 'Page Title',
    description: 'Page description',
    images: ['https://example.com/image.jpg'],
  },
}
```

### Summary Large Image Card

```typescript
export const metadata: Metadata = {
  twitter: {
    card: 'summary_large_image',
    site: '@username',
    creator: '@username',
    title: 'Page Title',
    description: 'Page description',
    images: {
      url: 'https://example.com/image.jpg',
      alt: 'Image description',
    },
  },
}
```

### App Card

```typescript
export const metadata: Metadata = {
  twitter: {
    card: 'app',
    site: '@username',
    title: 'App Name',
    description: 'App description',
    app: {
      id: {
        iphone: 'app-id-iphone',
        ipad: 'app-id-ipad',
        googleplay: 'app-id-googleplay',
      },
      url: {
        iphone: 'app-url-iphone',
        ipad: 'app-url-ipad',
      },
      name: {
        iphone: 'App Name on iPhone',
        ipad: 'App Name on iPad',
        googleplay: 'App Name on Google Play',
      },
    },
  },
}
```

### Player Card

```typescript
export const metadata: Metadata = {
  twitter: {
    card: 'player',
    site: '@username',
    title: 'Video Title',
    description: 'Video description',
    players: {
      playerUrl: 'https://example.com/player',
      streamUrl: 'https://example.com/stream.mp4',
      width: 1280,
      height: 720,
    },
    images: {
      url: 'https://example.com/thumbnail.jpg',
      alt: 'Video thumbnail',
    },
  },
}
```

---

## Structured Data (JSON-LD)

Structured data helps search engines understand your content.

### Organization Schema

```typescript
// app/layout.tsx or components/OrganizationSchema.tsx
export default function OrganizationSchema() {
  const schema = {
    '@context': 'https://schema.org',
    '@type': 'Organization',
    name: 'Company Name',
    url: 'https://example.com',
    logo: 'https://example.com/logo.png',
    description: 'Company description',
    address: {
      '@type': 'PostalAddress',
      streetAddress: '123 Main St',
      addressLocality: 'San Francisco',
      addressRegion: 'CA',
      postalCode: '94105',
      addressCountry: 'US',
    },
    contactPoint: {
      '@type': 'ContactPoint',
      telephone: '+1-555-555-5555',
      contactType: 'Customer Service',
      areaServed: 'US',
      availableLanguage: ['English', 'Spanish'],
    },
    sameAs: [
      'https://twitter.com/company',
      'https://facebook.com/company',
      'https://linkedin.com/company/company',
    ],
  }

  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(schema) }}
    />
  )
}
```

### Article Schema

```typescript
// app/blog/[slug]/page.tsx
export default async function BlogPost({ params }: Props) {
  const post = await getPost(params.slug)

  const schema = {
    '@context': 'https://schema.org',
    '@type': 'Article',
    headline: post.title,
    description: post.excerpt,
    image: post.coverImage,
    datePublished: post.publishedAt.toISOString(),
    dateModified: post.updatedAt.toISOString(),
    author: {
      '@type': 'Person',
      name: post.author.name,
      url: `https://example.com/authors/${post.author.slug}`,
    },
    publisher: {
      '@type': 'Organization',
      name: 'Example Blog',
      logo: {
        '@type': 'ImageObject',
        url: 'https://example.com/logo.png',
      },
    },
    mainEntityOfPage: {
      '@type': 'WebPage',
      '@id': `https://example.com/blog/${params.slug}`,
    },
  }

  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(schema) }}
      />
      <article>{/* Article content */}</article>
    </>
  )
}
```

### Product Schema

```typescript
export default async function ProductPage({ params }: Props) {
  const product = await getProduct(params.id)

  const schema = {
    '@context': 'https://schema.org',
    '@type': 'Product',
    name: product.name,
    image: product.images,
    description: product.description,
    sku: product.sku,
    mpn: product.mpn,
    brand: {
      '@type': 'Brand',
      name: product.brand,
    },
    offers: {
      '@type': 'Offer',
      url: `https://example.com/products/${params.id}`,
      priceCurrency: 'USD',
      price: product.price,
      priceValidUntil: product.priceValidUntil?.toISOString(),
      availability: product.inStock
        ? 'https://schema.org/InStock'
        : 'https://schema.org/OutOfStock',
      itemCondition: 'https://schema.org/NewCondition',
      seller: {
        '@type': 'Organization',
        name: 'Example Store',
      },
    },
    aggregateRating: product.rating && {
      '@type': 'AggregateRating',
      ratingValue: product.rating.average,
      reviewCount: product.rating.count,
    },
    review: product.reviews?.map(review => ({
      '@type': 'Review',
      reviewRating: {
        '@type': 'Rating',
        ratingValue: review.rating,
        bestRating: 5,
      },
      author: {
        '@type': 'Person',
        name: review.author,
      },
      reviewBody: review.body,
      datePublished: review.date.toISOString(),
    })),
  }

  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(schema) }}
      />
      <div>{/* Product content */}</div>
    </>
  )
}
```

### Breadcrumb Schema

```typescript
export default function BreadcrumbSchema({ items }: { items: Array<{ name: string; url: string }> }) {
  const schema = {
    '@context': 'https://schema.org',
    '@type': 'BreadcrumbList',
    itemListElement: items.map((item, index) => ({
      '@type': 'ListItem',
      position: index + 1,
      name: item.name,
      item: item.url,
    })),
  }

  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(schema) }}
    />
  )
}
```

### FAQ Schema

```typescript
export default function FAQSchema({ faqs }: { faqs: Array<{ question: string; answer: string }> }) {
  const schema = {
    '@context': 'https://schema.org',
    '@type': 'FAQPage',
    mainEntity: faqs.map(faq => ({
      '@type': 'Question',
      name: faq.question,
      acceptedAnswer: {
        '@type': 'Answer',
        text: faq.answer,
      },
    })),
  }

  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(schema) }}
    />
  )
}
```

### Local Business Schema

```typescript
export default function LocalBusinessSchema() {
  const schema = {
    '@context': 'https://schema.org',
    '@type': 'Restaurant',
    name: 'Restaurant Name',
    image: 'https://example.com/restaurant.jpg',
    '@id': 'https://example.com',
    url: 'https://example.com',
    telephone: '+1-555-555-5555',
    priceRange: '$$',
    address: {
      '@type': 'PostalAddress',
      streetAddress: '123 Main St',
      addressLocality: 'San Francisco',
      addressRegion: 'CA',
      postalCode: '94105',
      addressCountry: 'US',
    },
    geo: {
      '@type': 'GeoCoordinates',
      latitude: 37.7749,
      longitude: -122.4194,
    },
    openingHoursSpecification: [
      {
        '@type': 'OpeningHoursSpecification',
        dayOfWeek: ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'],
        opens: '11:00',
        closes: '22:00',
      },
      {
        '@type': 'OpeningHoursSpecification',
        dayOfWeek: ['Saturday', 'Sunday'],
        opens: '10:00',
        closes: '23:00',
      },
    ],
    servesCuisine: 'Italian',
    acceptsReservations: 'true',
  }

  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(schema) }}
    />
  )
}
```

---

## Sitemap Generation

Next.js supports automatic sitemap generation.

### Static Sitemap

```typescript
// app/sitemap.ts
import { MetadataRoute } from 'next'

export default function sitemap(): MetadataRoute.Sitemap {
  return [
    {
      url: 'https://example.com',
      lastModified: new Date(),
      changeFrequency: 'yearly',
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
      priority: 0.5,
    },
  ]
}
```

### Dynamic Sitemap

```typescript
// app/sitemap.ts
import { MetadataRoute } from 'next'
import { db } from '@/lib/db'

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  // Get all blog posts
  const posts = await db.post.findMany({
    select: {
      slug: true,
      updatedAt: true,
    },
    where: {
      published: true,
    },
  })

  const postEntries: MetadataRoute.Sitemap = posts.map(post => ({
    url: `https://example.com/blog/${post.slug}`,
    lastModified: post.updatedAt,
    changeFrequency: 'weekly',
    priority: 0.7,
  }))

  // Get all products
  const products = await db.product.findMany({
    select: {
      id: true,
      updatedAt: true,
    },
  })

  const productEntries: MetadataRoute.Sitemap = products.map(product => ({
    url: `https://example.com/products/${product.id}`,
    lastModified: product.updatedAt,
    changeFrequency: 'daily',
    priority: 0.8,
  }))

  // Static pages
  const staticPages: MetadataRoute.Sitemap = [
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
  ]

  return [...staticPages, ...postEntries, ...productEntries]
}
```

### Multiple Sitemaps

```typescript
// app/sitemap.ts (index sitemap)
import { MetadataRoute } from 'next'

export default function sitemap(): MetadataRoute.Sitemap {
  return [
    {
      url: 'https://example.com/product-sitemap.xml',
      lastModified: new Date(),
    },
    {
      url: 'https://example.com/blog-sitemap.xml',
      lastModified: new Date(),
    },
  ]
}

// app/product-sitemap.xml/route.ts
import { db } from '@/lib/db'

export async function GET() {
  const products = await db.product.findMany({
    select: { id: true, updatedAt: true },
  })

  const sitemap = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  ${products
    .map(
      product => `
    <url>
      <loc>https://example.com/products/${product.id}</loc>
      <lastmod>${product.updatedAt.toISOString()}</lastmod>
      <changefreq>daily</changefreq>
      <priority>0.8</priority>
    </url>
  `
    )
    .join('')}
</urlset>`

  return new Response(sitemap, {
    headers: {
      'Content-Type': 'application/xml',
    },
  })
}
```

---

## Robots.txt Configuration

Control search engine crawler behavior.

### Static Robots.txt

```typescript
// app/robots.ts
import { MetadataRoute } from 'next'

export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: '*',
      allow: '/',
      disallow: '/private/',
    },
    sitemap: 'https://example.com/sitemap.xml',
  }
}
```

### Multiple Rules

```typescript
// app/robots.ts
import { MetadataRoute } from 'next'

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      {
        userAgent: 'Googlebot',
        allow: '/',
        disallow: ['/admin/', '/api/'],
        crawlDelay: 10,
      },
      {
        userAgent: 'Bingbot',
        allow: '/',
        disallow: '/admin/',
      },
      {
        userAgent: '*',
        allow: '/',
        disallow: ['/admin/', '/api/', '/private/'],
      },
    ],
    sitemap: [
      'https://example.com/sitemap.xml',
      'https://example.com/blog-sitemap.xml',
      'https://example.com/product-sitemap.xml',
    ],
    host: 'https://example.com',
  }
}
```

### Environment-Specific

```typescript
// app/robots.ts
import { MetadataRoute } from 'next'

export default function robots(): MetadataRoute.Robots {
  const baseUrl = process.env.NEXT_PUBLIC_BASE_URL || 'https://example.com'
  const isProduction = process.env.NODE_ENV === 'production'

  if (!isProduction) {
    // Block all crawlers in non-production
    return {
      rules: {
        userAgent: '*',
        disallow: '/',
      },
    }
  }

  return {
    rules: {
      userAgent: '*',
      allow: '/',
      disallow: ['/admin/', '/api/'],
    },
    sitemap: `${baseUrl}/sitemap.xml`,
  }
}
```

---

## Canonical URLs

Canonical URLs prevent duplicate content issues.

### Static Canonical

```typescript
export const metadata: Metadata = {
  alternates: {
    canonical: 'https://example.com/page',
  },
}
```

### Dynamic Canonical

```typescript
export async function generateMetadata({ params }: Props): Promise<Metadata> {
  return {
    alternates: {
      canonical: `https://example.com/products/${params.id}`,
    },
  }
}
```

### With Query Parameters

```typescript
// app/search/page.tsx
export async function generateMetadata({ searchParams }: Props): Promise<Metadata> {
  // Always use the base URL without query params as canonical
  return {
    alternates: {
      canonical: 'https://example.com/search',
    },
    robots: {
      index: false, // Don't index search results
    },
  }
}
```

### Multi-Language Canonicals

```typescript
export const metadata: Metadata = {
  alternates: {
    canonical: 'https://example.com/en/page',
    languages: {
      'en-US': 'https://example.com/en/page',
      'es-ES': 'https://example.com/es/page',
      'fr-FR': 'https://example.com/fr/page',
    },
  },
}
```

---

## Meta Tags Best Practices

### Essential Meta Tags Checklist

```typescript
export const metadata: Metadata = {
  // 1. Title (50-60 characters)
  title: 'Page Title - Brand Name',

  // 2. Description (150-160 characters)
  description: 'Compelling description that includes keywords and encourages clicks',

  // 3. Viewport (mobile-friendly)
  viewport: {
    width: 'device-width',
    initialScale: 1,
    maximumScale: 5,
  },

  // 4. Robots
  robots: {
    index: true,
    follow: true,
    nocache: false,
    googleBot: {
      index: true,
      follow: true,
      'max-video-preview': -1,
      'max-image-preview': 'large',
      'max-snippet': -1,
    },
  },

  // 5. Canonical URL
  alternates: {
    canonical: 'https://example.com/page',
  },

  // 6. Open Graph
  openGraph: {
    title: 'Page Title',
    description: 'Description',
    url: 'https://example.com/page',
    siteName: 'Site Name',
    images: [{ url: '/og-image.jpg', width: 1200, height: 630 }],
    locale: 'en_US',
    type: 'website',
  },

  // 7. Twitter Card
  twitter: {
    card: 'summary_large_image',
    title: 'Page Title',
    description: 'Description',
    images: ['/twitter-image.jpg'],
  },
}
```

### Character Limits

- **Title**: 50-60 characters (Google truncates at ~60)
- **Description**: 150-160 characters (Google truncates at ~160)
- **OG Title**: 60-90 characters
- **OG Description**: 200 characters
- **Twitter Title**: 70 characters
- **Twitter Description**: 200 characters

### Keywords Strategy

```typescript
// Modern SEO: Focus on natural content, not keyword stuffing
export const metadata: Metadata = {
  // Old way (not recommended)
  keywords: ['keyword1', 'keyword2', 'keyword3'],

  // Better: Use keywords naturally in title and description
  title: 'Buy Organic Coffee Beans | Fresh Roasted Coffee',
  description: 'Shop premium organic coffee beans, freshly roasted to order. Free shipping on orders over $50.',
}
```

### Author Tags

```typescript
export const metadata: Metadata = {
  authors: [
    { name: 'John Doe', url: 'https://example.com/authors/john-doe' },
    { name: 'Jane Smith', url: 'https://example.com/authors/jane-smith' },
  ],
  creator: 'John Doe',
  publisher: 'Example Publishing',
}
```

---

## Core Web Vitals & Performance

SEO is heavily influenced by page performance.

### Image Optimization

```typescript
import Image from 'next/image'

export default function OptimizedImage() {
  return (
    <Image
      src="/hero.jpg"
      alt="Hero image"
      width={1200}
      height={630}
      priority // Load above the fold images first
      quality={85} // Balance quality vs. size
      placeholder="blur"
      blurDataURL="data:image/jpeg;base64,..."
    />
  )
}
```

### Font Optimization

```typescript
// app/layout.tsx
import { Inter } from 'next/font/google'

const inter = Inter({
  subsets: ['latin'],
  display: 'swap', // Prevent FOIT (Flash of Invisible Text)
  preload: true,
  variable: '--font-inter',
})

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={inter.variable}>
      <body>{children}</body>
    </html>
  )
}
```

### Script Optimization

```typescript
import Script from 'next/script'

export default function Analytics() {
  return (
    <>
      {/* Load analytics after page is interactive */}
      <Script
        src="https://www.googletagmanager.com/gtag/js?id=GA_MEASUREMENT_ID"
        strategy="afterInteractive"
      />

      {/* Load non-critical scripts lazily */}
      <Script
        src="https://example.com/widget.js"
        strategy="lazyOnload"
      />
    </>
  )
}
```

### Streaming and Suspense

```typescript
// app/products/[id]/page.tsx
import { Suspense } from 'react'

async function ProductDetails({ id }: { id: string }) {
  const product = await getProduct(id)
  return <div>{product.name}</div>
}

async function ProductReviews({ id }: { id: string }) {
  const reviews = await getReviews(id)
  return <div>{reviews.length} reviews</div>
}

export default function ProductPage({ params }: Props) {
  return (
    <div>
      <Suspense fallback={<ProductSkeleton />}>
        <ProductDetails id={params.id} />
      </Suspense>

      <Suspense fallback={<ReviewsSkeleton />}>
        <ProductReviews id={params.id} />
      </Suspense>
    </div>
  )
}
```

### Monitoring Core Web Vitals

```typescript
// app/layout.tsx
import { SpeedInsights } from '@vercel/speed-insights/next'
import { Analytics } from '@vercel/analytics/react'

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        {children}
        <SpeedInsights />
        <Analytics />
      </body>
    </html>
  )
}
```

---

## Image Optimization for SEO

### Next.js Image Component

```typescript
import Image from 'next/image'

export default function SEOImage() {
  return (
    <Image
      src="/product.jpg"
      alt="High-quality product description with keywords"
      width={800}
      height={600}
      sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 33vw"
      quality={85}
      priority={false}
      loading="lazy"
    />
  )
}
```

### Responsive Images

```typescript
export default function ResponsiveImage() {
  return (
    <Image
      src="/hero.jpg"
      alt="Hero image"
      fill
      sizes="100vw"
      style={{ objectFit: 'cover' }}
      priority
    />
  )
}
```

### Image Alt Text Best Practices

```typescript
// Bad
<Image src="/product.jpg" alt="image" />

// Good
<Image
  src="/product.jpg"
  alt="Red leather sofa with wooden legs in modern living room"
/>

// Context matters
function ProductImage({ product }: { product: Product }) {
  return (
    <Image
      src={product.image}
      alt={`${product.name} - ${product.category} - ${product.color}`}
      width={600}
      height={400}
    />
  )
}
```

### OG Images

```typescript
// Static OG image
export const metadata: Metadata = {
  openGraph: {
    images: [
      {
        url: '/og-image.jpg',
        width: 1200,
        height: 630,
        alt: 'Site preview',
      },
    ],
  },
}

// Dynamic OG image with next/og
// app/api/og/route.tsx
import { ImageResponse } from 'next/og'

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url)
  const title = searchParams.get('title') || 'Default Title'

  return new ImageResponse(
    (
      <div
        style={{
          fontSize: 60,
          background: 'white',
          width: '100%',
          height: '100%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        {title}
      </div>
    ),
    {
      width: 1200,
      height: 630,
    }
  )
}

// Usage in metadata
export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const post = await getPost(params.slug)

  return {
    openGraph: {
      images: [
        {
          url: `/api/og?title=${encodeURIComponent(post.title)}`,
          width: 1200,
          height: 630,
        },
      ],
    },
  }
}
```

---

## Internationalization (i18n) for SEO

### Multi-Language Metadata

```typescript
// app/[lang]/layout.tsx
import { Metadata } from 'next'

type Props = {
  params: { lang: string }
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const dict = await getDictionary(params.lang)

  return {
    title: {
      default: dict.seo.title,
      template: `%s | ${dict.seo.siteName}`,
    },
    description: dict.seo.description,
    alternates: {
      canonical: `https://example.com/${params.lang}`,
      languages: {
        'en-US': 'https://example.com/en',
        'es-ES': 'https://example.com/es',
        'fr-FR': 'https://example.com/fr',
        'de-DE': 'https://example.com/de',
        'x-default': 'https://example.com/en',
      },
    },
    openGraph: {
      locale: params.lang === 'en' ? 'en_US' : `${params.lang}_${params.lang.toUpperCase()}`,
      localeAlternate: ['en_US', 'es_ES', 'fr_FR', 'de_DE'],
    },
  }
}
```

### Hreflang Tags

```typescript
export const metadata: Metadata = {
  alternates: {
    canonical: 'https://example.com/en/page',
    languages: {
      'en-US': 'https://example.com/en/page',
      'en-GB': 'https://example.com/en-gb/page',
      'es-ES': 'https://example.com/es/page',
      'es-MX': 'https://example.com/es-mx/page',
      'fr-FR': 'https://example.com/fr/page',
      'de-DE': 'https://example.com/de/page',
      'ja-JP': 'https://example.com/ja/page',
      'x-default': 'https://example.com/en/page',
    },
  },
}
```

### Multi-Region Sitemap

```typescript
// app/sitemap.ts
import { MetadataRoute } from 'next'

const languages = ['en', 'es', 'fr', 'de', 'ja']

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const posts = await getPosts()

  const postEntries = posts.flatMap(post =>
    languages.map(lang => ({
      url: `https://example.com/${lang}/blog/${post.slug}`,
      lastModified: post.updatedAt,
      alternates: {
        languages: Object.fromEntries(
          languages.map(l => [l, `https://example.com/${l}/blog/${post.slug}`])
        ),
      },
    }))
  )

  return postEntries
}
```

---

## Advanced Patterns

### Noindex for Specific Pages

```typescript
// Don't index staging/preview environments
export async function generateMetadata(): Promise<Metadata> {
  const isProduction = process.env.NODE_ENV === 'production'

  return {
    robots: {
      index: isProduction,
      follow: isProduction,
    },
  }
}
```

### Conditional Metadata

```typescript
export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const product = await getProduct(params.id)

  if (!product) {
    return {
      title: 'Product Not Found',
      robots: { index: false, follow: false },
    }
  }

  if (product.isDiscontinued) {
    return {
      title: `${product.name} (Discontinued)`,
      robots: { index: false, follow: true },
    }
  }

  return {
    title: product.name,
    description: product.description,
    robots: { index: true, follow: true },
  }
}
```

### Metadata Inheritance

```typescript
// app/layout.tsx (root)
export const metadata: Metadata = {
  metadataBase: new URL('https://example.com'),
  title: {
    default: 'My Site',
    template: '%s | My Site',
  },
}

// app/blog/layout.tsx (nested)
export const metadata: Metadata = {
  title: {
    default: 'Blog',
    template: '%s | Blog | My Site',
  },
}

// app/blog/[slug]/page.tsx
export async function generateMetadata({ params }: Props): Promise<Metadata> {
  return {
    title: 'My Post', // Renders as "My Post | Blog | My Site"
  }
}
```

### Dynamic Robots Meta

```typescript
export async function generateMetadata({ params, searchParams }: Props): Promise<Metadata> {
  const page = parseInt(searchParams.page as string) || 1

  return {
    robots: {
      index: page === 1, // Only index first page of pagination
      follow: true,
    },
  }
}
```

### Metadata for API Routes

```typescript
// app/api/data/route.ts
export async function GET() {
  return Response.json({ data: 'value' }, {
    headers: {
      'Cache-Control': 'public, s-maxage=3600, stale-while-revalidate=86400',
    },
  })
}
```

### Testing Metadata

```typescript
// __tests__/metadata.test.ts
import { generateMetadata } from '@/app/products/[id]/page'

describe('Product Metadata', () => {
  it('generates correct metadata for product', async () => {
    const metadata = await generateMetadata({
      params: { id: '123' },
      searchParams: {},
    })

    expect(metadata.title).toBe('Product Name')
    expect(metadata.description).toBeDefined()
    expect(metadata.openGraph?.images?.[0]).toBeDefined()
  })

  it('handles missing product', async () => {
    const metadata = await generateMetadata({
      params: { id: 'invalid' },
      searchParams: {},
    })

    expect(metadata.title).toBe('Product Not Found')
    expect(metadata.robots?.index).toBe(false)
  })
})
```

---

## SEO Checklist

### Pre-Launch

- [ ] All pages have unique titles (50-60 chars)
- [ ] All pages have unique descriptions (150-160 chars)
- [ ] Canonical URLs set correctly
- [ ] Open Graph tags present
- [ ] Twitter Card tags present
- [ ] Structured data implemented
- [ ] Sitemap.xml generated
- [ ] Robots.txt configured
- [ ] 404 page with helpful content
- [ ] All images have descriptive alt text
- [ ] Mobile-friendly (responsive)
- [ ] Fast loading (Core Web Vitals)
- [ ] HTTPS enabled
- [ ] No broken links
- [ ] Breadcrumbs implemented
- [ ] Schema markup validated
- [ ] Search Console set up
- [ ] Analytics tracking set up

### Ongoing

- [ ] Monitor search rankings
- [ ] Track Core Web Vitals
- [ ] Update sitemap regularly
- [ ] Fix crawl errors
- [ ] Optimize slow pages
- [ ] Update outdated content
- [ ] Build quality backlinks
- [ ] Monitor competitor SEO

---

## Additional Resources

### Tools

- **Google Search Console**: Monitor search performance
- **Lighthouse**: Audit SEO and performance
- **Schema.org**: Structured data reference
- **Open Graph Debugger**: Test OG tags
- **Twitter Card Validator**: Test Twitter cards
- **Rich Results Test**: Validate structured data
- **PageSpeed Insights**: Performance metrics
- **Mobile-Friendly Test**: Mobile optimization

### Next.js Documentation

- [Metadata API](https://nextjs.org/docs/app/building-your-application/optimizing/metadata)
- [Sitemap](https://nextjs.org/docs/app/api-reference/file-conventions/metadata/sitemap)
- [Robots.txt](https://nextjs.org/docs/app/api-reference/file-conventions/metadata/robots)
- [Open Graph Images](https://nextjs.org/docs/app/api-reference/file-conventions/metadata/opengraph-image)
- [Image Optimization](https://nextjs.org/docs/app/building-your-application/optimizing/images)
