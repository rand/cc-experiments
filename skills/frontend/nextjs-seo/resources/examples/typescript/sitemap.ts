/**
 * Next.js Sitemap Generation Examples
 *
 * Demonstrates various sitemap patterns for Next.js App Router.
 */

import { MetadataRoute } from 'next'

// =============================================================================
// EXAMPLE 1: Basic Static Sitemap
// =============================================================================

// app/sitemap.ts
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
    {
      url: 'https://example.com/contact',
      lastModified: new Date(),
      changeFrequency: 'yearly',
      priority: 0.3,
    },
  ]
}

// =============================================================================
// EXAMPLE 2: Dynamic Sitemap with Database
// =============================================================================

// Mock database - replace with your actual DB client
const db = {
  post: {
    findMany: async () => [
      { slug: 'post-1', updatedAt: new Date('2024-01-15') },
      { slug: 'post-2', updatedAt: new Date('2024-01-20') },
    ],
  },
  product: {
    findMany: async () => [
      { id: '1', updatedAt: new Date('2024-01-10') },
      { id: '2', updatedAt: new Date('2024-01-12') },
    ],
  },
}

export async function dynamicSitemap(): Promise<MetadataRoute.Sitemap> {
  const baseUrl = 'https://example.com'

  // Fetch dynamic data
  const [posts, products] = await Promise.all([
    db.post.findMany({
      select: { slug: true, updatedAt: true },
    }),
    db.product.findMany({
      select: { id: true, updatedAt: true },
    }),
  ])

  // Generate post entries
  const postEntries: MetadataRoute.Sitemap = posts.map(post => ({
    url: `${baseUrl}/blog/${post.slug}`,
    lastModified: post.updatedAt,
    changeFrequency: 'weekly',
    priority: 0.7,
  }))

  // Generate product entries
  const productEntries: MetadataRoute.Sitemap = products.map(product => ({
    url: `${baseUrl}/products/${product.id}`,
    lastModified: product.updatedAt,
    changeFrequency: 'daily',
    priority: 0.8,
  }))

  // Static pages
  const staticPages: MetadataRoute.Sitemap = [
    {
      url: baseUrl,
      lastModified: new Date(),
      changeFrequency: 'daily',
      priority: 1,
    },
    {
      url: `${baseUrl}/about`,
      lastModified: new Date(),
      changeFrequency: 'monthly',
      priority: 0.8,
    },
    {
      url: `${baseUrl}/contact`,
      lastModified: new Date(),
      changeFrequency: 'yearly',
      priority: 0.5,
    },
  ]

  return [...staticPages, ...postEntries, ...productEntries]
}

// =============================================================================
// EXAMPLE 3: Sitemap with Environment Variables
// =============================================================================

export async function environmentAwareSitemap(): Promise<MetadataRoute.Sitemap> {
  const baseUrl = process.env.NEXT_PUBLIC_BASE_URL || 'https://example.com'

  return [
    {
      url: baseUrl,
      lastModified: new Date(),
      changeFrequency: 'daily',
      priority: 1,
    },
    {
      url: `${baseUrl}/about`,
      lastModified: new Date(),
      changeFrequency: 'monthly',
      priority: 0.8,
    },
  ]
}

// =============================================================================
// EXAMPLE 4: Multi-Language Sitemap
// =============================================================================

export async function multiLanguageSitemap(): Promise<MetadataRoute.Sitemap> {
  const baseUrl = 'https://example.com'
  const languages = ['en', 'es', 'fr', 'de']
  const pages = ['', 'about', 'contact', 'blog']

  const entries: MetadataRoute.Sitemap = []

  for (const lang of languages) {
    for (const page of pages) {
      const path = page ? `/${lang}/${page}` : `/${lang}`

      entries.push({
        url: `${baseUrl}${path}`,
        lastModified: new Date(),
        changeFrequency: 'monthly',
        priority: path === `/${lang}` ? 1 : 0.8,
        alternates: {
          languages: Object.fromEntries(
            languages.map(l => [l, `${baseUrl}/${l}${page ? `/${page}` : ''}`])
          ),
        },
      })
    }
  }

  return entries
}

// =============================================================================
// EXAMPLE 5: Sitemap with Custom Priorities
// =============================================================================

function calculatePriority(path: string): number {
  if (path === '/') return 1.0
  if (path.startsWith('/blog')) return 0.7
  if (path.startsWith('/products')) return 0.8
  if (path.startsWith('/docs')) return 0.6
  return 0.5
}

function calculateChangeFrequency(path: string): MetadataRoute.Sitemap[number]['changeFrequency'] {
  if (path === '/') return 'daily'
  if (path.startsWith('/blog')) return 'weekly'
  if (path.startsWith('/products')) return 'daily'
  if (path.startsWith('/docs')) return 'monthly'
  return 'monthly'
}

export async function customPrioritySitemap(): Promise<MetadataRoute.Sitemap> {
  const baseUrl = 'https://example.com'
  const paths = [
    '/',
    '/about',
    '/blog',
    '/blog/post-1',
    '/blog/post-2',
    '/products',
    '/products/1',
    '/products/2',
    '/docs',
    '/docs/getting-started',
  ]

  return paths.map(path => ({
    url: `${baseUrl}${path}`,
    lastModified: new Date(),
    changeFrequency: calculateChangeFrequency(path),
    priority: calculatePriority(path),
  }))
}

// =============================================================================
// EXAMPLE 6: Sitemap with Exclusions
// =============================================================================

export async function sitemapWithExclusions(): Promise<MetadataRoute.Sitemap> {
  const baseUrl = 'https://example.com'

  // Get all posts
  const posts = await db.post.findMany({
    select: {
      slug: true,
      updatedAt: true,
      published: true,
      noindex: true,
    },
  })

  // Filter out unpublished or noindex posts
  const publishedPosts = posts.filter(
    post => post.published && !post.noindex
  )

  return publishedPosts.map(post => ({
    url: `${baseUrl}/blog/${post.slug}`,
    lastModified: post.updatedAt,
    changeFrequency: 'weekly',
    priority: 0.7,
  }))
}

// =============================================================================
// EXAMPLE 7: Paginated Sitemap
// =============================================================================

export async function paginatedSitemap(): Promise<MetadataRoute.Sitemap> {
  const baseUrl = 'https://example.com'
  const totalPosts = 1000
  const postsPerPage = 20
  const totalPages = Math.ceil(totalPosts / postsPerPage)

  const entries: MetadataRoute.Sitemap = []

  // Add blog index (page 1)
  entries.push({
    url: `${baseUrl}/blog`,
    lastModified: new Date(),
    changeFrequency: 'daily',
    priority: 0.8,
  })

  // Add paginated pages (don't index pages > 1)
  for (let page = 2; page <= totalPages; page++) {
    entries.push({
      url: `${baseUrl}/blog?page=${page}`,
      lastModified: new Date(),
      changeFrequency: 'daily',
      priority: 0.3,
    })
  }

  return entries
}

// =============================================================================
// EXAMPLE 8: Sitemap with Images
// =============================================================================

export async function sitemapWithImages(): Promise<MetadataRoute.Sitemap> {
  const baseUrl = 'https://example.com'

  const posts = await db.post.findMany({
    select: {
      slug: true,
      updatedAt: true,
      images: true,
    },
  })

  return posts.map(post => ({
    url: `${baseUrl}/blog/${post.slug}`,
    lastModified: post.updatedAt,
    changeFrequency: 'weekly',
    priority: 0.7,
    // Note: Next.js sitemap doesn't directly support image tags
    // You would need to implement a custom XML route for this
  }))
}

// =============================================================================
// EXAMPLE 9: Sitemap Index (for large sites)
// =============================================================================

// app/sitemap.ts (main sitemap index)
export function sitemapIndex(): MetadataRoute.Sitemap {
  const baseUrl = 'https://example.com'

  return [
    {
      url: `${baseUrl}/sitemap-pages.xml`,
      lastModified: new Date(),
    },
    {
      url: `${baseUrl}/sitemap-posts.xml`,
      lastModified: new Date(),
    },
    {
      url: `${baseUrl}/sitemap-products.xml`,
      lastModified: new Date(),
    },
  ]
}

// app/sitemap-posts.xml/route.ts
export async function GET_PostsSitemap() {
  const baseUrl = 'https://example.com'
  const posts = await db.post.findMany({
    select: { slug: true, updatedAt: true },
  })

  const sitemap = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  ${posts
    .map(
      post => `
    <url>
      <loc>${baseUrl}/blog/${post.slug}</loc>
      <lastmod>${post.updatedAt.toISOString()}</lastmod>
      <changefreq>weekly</changefreq>
      <priority>0.7</priority>
    </url>
  `
    )
    .join('')}
</urlset>`

  return new Response(sitemap, {
    headers: {
      'Content-Type': 'application/xml',
      'Cache-Control': 'public, s-maxage=3600, stale-while-revalidate=86400',
    },
  })
}

// =============================================================================
// EXAMPLE 10: Dynamic Sitemap with Caching
// =============================================================================

// Cache sitemap data for better performance
let cachedSitemap: MetadataRoute.Sitemap | null = null
let cacheTime: number = 0
const CACHE_DURATION = 3600000 // 1 hour in milliseconds

export async function cachedSitemap(): Promise<MetadataRoute.Sitemap> {
  const now = Date.now()

  // Return cached version if still valid
  if (cachedSitemap && now - cacheTime < CACHE_DURATION) {
    return cachedSitemap
  }

  // Fetch fresh data
  const sitemap = await dynamicSitemap()

  // Update cache
  cachedSitemap = sitemap
  cacheTime = now

  return sitemap
}

// =============================================================================
// EXAMPLE 11: Sitemap with TypeScript Helpers
// =============================================================================

interface SitemapEntry {
  path: string
  lastModified?: Date
  changeFrequency?: 'always' | 'hourly' | 'daily' | 'weekly' | 'monthly' | 'yearly' | 'never'
  priority?: number
}

function createSitemapEntry(
  baseUrl: string,
  entry: SitemapEntry
): MetadataRoute.Sitemap[number] {
  return {
    url: `${baseUrl}${entry.path}`,
    lastModified: entry.lastModified || new Date(),
    changeFrequency: entry.changeFrequency || 'monthly',
    priority: entry.priority || 0.5,
  }
}

export async function typedSitemap(): Promise<MetadataRoute.Sitemap> {
  const baseUrl = 'https://example.com'

  const entries: SitemapEntry[] = [
    { path: '/', priority: 1, changeFrequency: 'daily' },
    { path: '/about', priority: 0.8, changeFrequency: 'monthly' },
    { path: '/blog', priority: 0.7, changeFrequency: 'daily' },
  ]

  return entries.map(entry => createSitemapEntry(baseUrl, entry))
}

// =============================================================================
// EXAMPLE 12: Conditional Sitemap (Production Only)
// =============================================================================

export async function productionOnlySitemap(): Promise<MetadataRoute.Sitemap> {
  const baseUrl = process.env.NEXT_PUBLIC_BASE_URL || 'https://example.com'
  const isProduction = process.env.NODE_ENV === 'production'

  if (!isProduction) {
    // Return minimal sitemap for non-production
    return [
      {
        url: baseUrl,
        lastModified: new Date(),
      },
    ]
  }

  // Full sitemap for production
  return await dynamicSitemap()
}

// =============================================================================
// EXAMPLE 13: Sitemap with Error Handling
// =============================================================================

export async function safeSitemap(): Promise<MetadataRoute.Sitemap> {
  const baseUrl = 'https://example.com'

  try {
    const posts = await db.post.findMany({
      select: { slug: true, updatedAt: true },
    })

    return posts.map(post => ({
      url: `${baseUrl}/blog/${post.slug}`,
      lastModified: post.updatedAt,
      changeFrequency: 'weekly' as const,
      priority: 0.7,
    }))
  } catch (error) {
    console.error('Error generating sitemap:', error)

    // Return fallback sitemap
    return [
      {
        url: baseUrl,
        lastModified: new Date(),
        changeFrequency: 'daily',
        priority: 1,
      },
    ]
  }
}
