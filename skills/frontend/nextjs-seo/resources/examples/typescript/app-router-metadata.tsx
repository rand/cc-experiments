/**
 * Next.js App Router Metadata Examples
 *
 * Demonstrates static and dynamic metadata generation using the Next.js
 * App Router Metadata API.
 */

import { Metadata } from 'next'

// =============================================================================
// EXAMPLE 1: Static Metadata (Root Layout)
// =============================================================================

// app/layout.tsx
export const metadata: Metadata = {
  metadataBase: new URL('https://example.com'),
  title: {
    default: 'My Awesome Site',
    template: '%s | My Awesome Site',
  },
  description: 'The best site on the internet for awesome things',
  applicationName: 'My Awesome App',
  authors: [
    { name: 'John Doe', url: 'https://example.com/authors/john' },
  ],
  generator: 'Next.js',
  keywords: ['nextjs', 'react', 'seo', 'web development'],
  referrer: 'origin-when-cross-origin',
  creator: 'John Doe',
  publisher: 'My Awesome Company',
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
    siteName: 'My Awesome Site',
    title: 'My Awesome Site',
    description: 'The best site on the internet for awesome things',
    images: [
      {
        url: '/og-image.jpg',
        width: 1200,
        height: 630,
        alt: 'My Awesome Site Preview',
      },
    ],
  },
  twitter: {
    card: 'summary_large_image',
    site: '@myawesomesite',
    creator: '@johndoe',
    title: 'My Awesome Site',
    description: 'The best site on the internet for awesome things',
    images: ['/twitter-image.jpg'],
  },
  verification: {
    google: 'google-verification-code',
    yandex: 'yandex-verification-code',
  },
}

// =============================================================================
// EXAMPLE 2: Static Metadata (Static Page)
// =============================================================================

// app/about/page.tsx
export const aboutMetadata: Metadata = {
  title: 'About Us',
  description: 'Learn about our company, mission, and team',
  alternates: {
    canonical: 'https://example.com/about',
  },
  openGraph: {
    title: 'About Us | My Awesome Site',
    description: 'Learn about our company, mission, and team',
    url: 'https://example.com/about',
    images: [
      {
        url: '/about-og-image.jpg',
        width: 1200,
        height: 630,
      },
    ],
  },
}

// =============================================================================
// EXAMPLE 3: Dynamic Metadata (Blog Post)
// =============================================================================

interface BlogPostPageProps {
  params: { slug: string }
  searchParams: { [key: string]: string | string[] | undefined }
}

// Mock function - replace with actual data fetching
async function getBlogPost(slug: string) {
  return {
    title: 'Understanding Next.js SEO',
    excerpt: 'A comprehensive guide to implementing SEO in Next.js applications',
    content: 'Full article content...',
    coverImage: '/blog/nextjs-seo-cover.jpg',
    publishedAt: new Date('2024-01-15'),
    updatedAt: new Date('2024-01-20'),
    author: {
      name: 'Jane Smith',
      url: 'https://example.com/authors/jane-smith',
    },
    tags: ['nextjs', 'seo', 'web development'],
    category: 'Web Development',
  }
}

export async function generateBlogMetadata(
  { params }: BlogPostPageProps
): Promise<Metadata> {
  const post = await getBlogPost(params.slug)

  return {
    title: post.title,
    description: post.excerpt,
    authors: [{ name: post.author.name, url: post.author.url }],
    keywords: post.tags,
    alternates: {
      canonical: `https://example.com/blog/${params.slug}`,
    },
    openGraph: {
      type: 'article',
      url: `https://example.com/blog/${params.slug}`,
      title: post.title,
      description: post.excerpt,
      publishedTime: post.publishedAt.toISOString(),
      modifiedTime: post.updatedAt.toISOString(),
      authors: [post.author.name],
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
    twitter: {
      card: 'summary_large_image',
      title: post.title,
      description: post.excerpt,
      images: [post.coverImage],
    },
  }
}

// =============================================================================
// EXAMPLE 4: Dynamic Metadata (Product Page)
// =============================================================================

interface ProductPageProps {
  params: { id: string }
}

// Mock function - replace with actual data fetching
async function getProduct(id: string) {
  return {
    id,
    name: 'Awesome Product',
    description: 'The best product you can buy',
    price: 99.99,
    currency: 'USD',
    sku: 'PROD-001',
    brand: 'My Brand',
    inStock: true,
    images: [
      '/products/awesome-product-1.jpg',
      '/products/awesome-product-2.jpg',
    ],
    rating: {
      average: 4.5,
      count: 127,
    },
  }
}

export async function generateProductMetadata(
  { params }: ProductPageProps
): Promise<Metadata> {
  const product = await getProduct(params.id)

  return {
    title: product.name,
    description: product.description,
    alternates: {
      canonical: `https://example.com/products/${params.id}`,
    },
    openGraph: {
      type: 'product',
      url: `https://example.com/products/${params.id}`,
      title: product.name,
      description: product.description,
      images: product.images.map(img => ({
        url: img,
        width: 1200,
        height: 630,
        alt: product.name,
      })),
      product: {
        priceAmount: product.price,
        priceCurrency: product.currency,
        availability: product.inStock ? 'in stock' : 'out of stock',
        condition: 'new',
      },
    },
    twitter: {
      card: 'summary_large_image',
      title: product.name,
      description: product.description,
      images: [product.images[0]],
    },
  }
}

// =============================================================================
// EXAMPLE 5: Dynamic Metadata with Error Handling
// =============================================================================

export async function generateMetadataWithErrorHandling(
  { params }: { params: { id: string } }
): Promise<Metadata> {
  try {
    const product = await getProduct(params.id)

    if (!product) {
      return {
        title: 'Product Not Found',
        description: 'The requested product could not be found',
        robots: {
          index: false,
          follow: false,
        },
      }
    }

    return {
      title: product.name,
      description: product.description,
      // ... rest of metadata
    }
  } catch (error) {
    console.error('Error generating metadata:', error)

    return {
      title: 'Error Loading Product',
      description: 'An error occurred while loading this product',
      robots: {
        index: false,
        follow: false,
      },
    }
  }
}

// =============================================================================
// EXAMPLE 6: Multi-Language Metadata
// =============================================================================

interface LocalizedPageProps {
  params: { lang: string; slug: string }
}

export async function generateLocalizedMetadata(
  { params }: LocalizedPageProps
): Promise<Metadata> {
  const translations = {
    en: { title: 'Welcome', description: 'Welcome to our site' },
    es: { title: 'Bienvenido', description: 'Bienvenido a nuestro sitio' },
    fr: { title: 'Bienvenue', description: 'Bienvenue sur notre site' },
  }

  const t = translations[params.lang as keyof typeof translations] || translations.en

  return {
    title: t.title,
    description: t.description,
    alternates: {
      canonical: `https://example.com/${params.lang}/${params.slug}`,
      languages: {
        'en-US': `https://example.com/en/${params.slug}`,
        'es-ES': `https://example.com/es/${params.slug}`,
        'fr-FR': `https://example.com/fr/${params.slug}`,
        'x-default': `https://example.com/en/${params.slug}`,
      },
    },
    openGraph: {
      locale: params.lang === 'en' ? 'en_US' : `${params.lang}_${params.lang.toUpperCase()}`,
      localeAlternate: ['en_US', 'es_ES', 'fr_FR'],
    },
  }
}

// =============================================================================
// EXAMPLE 7: Conditional Metadata (Environment-based)
// =============================================================================

export function generateEnvironmentMetadata(): Metadata {
  const isProduction = process.env.NODE_ENV === 'production'
  const baseUrl = process.env.NEXT_PUBLIC_BASE_URL || 'https://example.com'

  return {
    metadataBase: new URL(baseUrl),
    robots: {
      index: isProduction,
      follow: isProduction,
      // Don't index staging/development environments
    },
    title: isProduction ? 'My Site' : '[DEV] My Site',
  }
}

// =============================================================================
// EXAMPLE 8: Paginated Content Metadata
// =============================================================================

interface PaginatedPageProps {
  searchParams: { page?: string }
}

export async function generatePaginatedMetadata(
  { searchParams }: PaginatedPageProps
): Promise<Metadata> {
  const page = parseInt(searchParams.page || '1', 10)

  return {
    title: page > 1 ? `Blog - Page ${page}` : 'Blog',
    description: 'Read our latest articles and insights',
    robots: {
      index: page === 1, // Only index first page
      follow: true,
    },
    alternates: {
      canonical: page === 1
        ? 'https://example.com/blog'
        : `https://example.com/blog?page=${page}`,
    },
  }
}

// =============================================================================
// EXAMPLE 9: Metadata with Custom Meta Tags
// =============================================================================

export const customMetadata: Metadata = {
  title: 'Custom Meta Tags Example',
  other: {
    'theme-color': '#000000',
    'apple-mobile-web-app-capable': 'yes',
    'apple-mobile-web-app-status-bar-style': 'black-translucent',
    'format-detection': 'telephone=no',
    'mobile-web-app-capable': 'yes',
    // Custom meta tags
    'custom-tag': 'custom-value',
  },
}

// =============================================================================
// EXAMPLE 10: Viewport Configuration
// =============================================================================

export const viewportMetadata: Metadata = {
  viewport: {
    width: 'device-width',
    initialScale: 1,
    maximumScale: 5,
    userScalable: true,
  },
  themeColor: [
    { media: '(prefers-color-scheme: light)', color: '#ffffff' },
    { media: '(prefers-color-scheme: dark)', color: '#000000' },
  ],
}
