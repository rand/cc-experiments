/**
 * Structured Data (JSON-LD) Examples for Next.js
 *
 * Demonstrates implementing schema.org structured data for various content types.
 * Use these as reusable components in your Next.js app.
 */

// =============================================================================
// TYPES
// =============================================================================

interface Organization {
  name: string
  url: string
  logo: string
  description?: string
  address?: {
    streetAddress: string
    addressLocality: string
    addressRegion: string
    postalCode: string
    addressCountry: string
  }
  contactPoint?: {
    telephone: string
    contactType: string
    areaServed?: string
    availableLanguage?: string[]
  }
  sameAs?: string[]
}

interface Article {
  headline: string
  description: string
  image: string
  datePublished: string
  dateModified: string
  author: {
    name: string
    url?: string
  }
  publisher: {
    name: string
    logo: string
  }
  url: string
}

interface Product {
  name: string
  image: string[]
  description: string
  sku?: string
  mpn?: string
  brand: string
  offers: {
    url: string
    priceCurrency: string
    price: number
    priceValidUntil?: string
    availability: string
    itemCondition: string
  }
  aggregateRating?: {
    ratingValue: number
    reviewCount: number
  }
  review?: Array<{
    author: string
    rating: number
    body: string
    date: string
  }>
}

interface LocalBusiness {
  type: string // e.g., 'Restaurant', 'Store', 'Hotel'
  name: string
  image: string
  url: string
  telephone: string
  priceRange?: string
  address: {
    streetAddress: string
    addressLocality: string
    addressRegion: string
    postalCode: string
    addressCountry: string
  }
  geo?: {
    latitude: number
    longitude: number
  }
  openingHours?: Array<{
    dayOfWeek: string[]
    opens: string
    closes: string
  }>
}

interface Breadcrumb {
  name: string
  url: string
}

interface FAQItem {
  question: string
  answer: string
}

// =============================================================================
// EXAMPLE 1: Organization Schema
// =============================================================================

export function OrganizationSchema({ org }: { org: Organization }) {
  const schema = {
    '@context': 'https://schema.org',
    '@type': 'Organization',
    name: org.name,
    url: org.url,
    logo: org.logo,
    description: org.description,
    ...(org.address && {
      address: {
        '@type': 'PostalAddress',
        streetAddress: org.address.streetAddress,
        addressLocality: org.address.addressLocality,
        addressRegion: org.address.addressRegion,
        postalCode: org.address.postalCode,
        addressCountry: org.address.addressCountry,
      },
    }),
    ...(org.contactPoint && {
      contactPoint: {
        '@type': 'ContactPoint',
        telephone: org.contactPoint.telephone,
        contactType: org.contactPoint.contactType,
        areaServed: org.contactPoint.areaServed,
        availableLanguage: org.contactPoint.availableLanguage,
      },
    }),
    ...(org.sameAs && { sameAs: org.sameAs }),
  }

  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(schema) }}
    />
  )
}

// Usage in layout.tsx
export const organizationExample: Organization = {
  name: 'My Company',
  url: 'https://example.com',
  logo: 'https://example.com/logo.png',
  description: 'We build amazing products',
  address: {
    streetAddress: '123 Main St',
    addressLocality: 'San Francisco',
    addressRegion: 'CA',
    postalCode: '94105',
    addressCountry: 'US',
  },
  contactPoint: {
    telephone: '+1-555-555-5555',
    contactType: 'Customer Service',
    areaServed: 'US',
    availableLanguage: ['English', 'Spanish'],
  },
  sameAs: [
    'https://twitter.com/mycompany',
    'https://facebook.com/mycompany',
    'https://linkedin.com/company/mycompany',
  ],
}

// =============================================================================
// EXAMPLE 2: Article Schema
// =============================================================================

export function ArticleSchema({ article }: { article: Article }) {
  const schema = {
    '@context': 'https://schema.org',
    '@type': 'Article',
    headline: article.headline,
    description: article.description,
    image: article.image,
    datePublished: article.datePublished,
    dateModified: article.dateModified,
    author: {
      '@type': 'Person',
      name: article.author.name,
      ...(article.author.url && { url: article.author.url }),
    },
    publisher: {
      '@type': 'Organization',
      name: article.publisher.name,
      logo: {
        '@type': 'ImageObject',
        url: article.publisher.logo,
      },
    },
    mainEntityOfPage: {
      '@type': 'WebPage',
      '@id': article.url,
    },
  }

  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(schema) }}
    />
  )
}

// Usage in blog/[slug]/page.tsx
export const articleExample: Article = {
  headline: 'Understanding Next.js SEO',
  description: 'A comprehensive guide to implementing SEO in Next.js',
  image: 'https://example.com/blog/nextjs-seo.jpg',
  datePublished: '2024-01-15T08:00:00.000Z',
  dateModified: '2024-01-20T10:30:00.000Z',
  author: {
    name: 'Jane Doe',
    url: 'https://example.com/authors/jane-doe',
  },
  publisher: {
    name: 'My Blog',
    logo: 'https://example.com/logo.png',
  },
  url: 'https://example.com/blog/nextjs-seo',
}

// =============================================================================
// EXAMPLE 3: Product Schema
// =============================================================================

export function ProductSchema({ product }: { product: Product }) {
  const schema = {
    '@context': 'https://schema.org',
    '@type': 'Product',
    name: product.name,
    image: product.image,
    description: product.description,
    sku: product.sku,
    mpn: product.mpn,
    brand: {
      '@type': 'Brand',
      name: product.brand,
    },
    offers: {
      '@type': 'Offer',
      url: product.offers.url,
      priceCurrency: product.offers.priceCurrency,
      price: product.offers.price,
      priceValidUntil: product.offers.priceValidUntil,
      availability: product.offers.availability,
      itemCondition: product.offers.itemCondition,
    },
    ...(product.aggregateRating && {
      aggregateRating: {
        '@type': 'AggregateRating',
        ratingValue: product.aggregateRating.ratingValue,
        reviewCount: product.aggregateRating.reviewCount,
      },
    }),
    ...(product.review && {
      review: product.review.map(r => ({
        '@type': 'Review',
        reviewRating: {
          '@type': 'Rating',
          ratingValue: r.rating,
          bestRating: 5,
        },
        author: {
          '@type': 'Person',
          name: r.author,
        },
        reviewBody: r.body,
        datePublished: r.date,
      })),
    }),
  }

  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(schema) }}
    />
  )
}

// Usage in products/[id]/page.tsx
export const productExample: Product = {
  name: 'Awesome Product',
  image: [
    'https://example.com/product-1.jpg',
    'https://example.com/product-2.jpg',
  ],
  description: 'The best product you can buy',
  sku: 'PROD-001',
  mpn: 'MPN-123',
  brand: 'My Brand',
  offers: {
    url: 'https://example.com/products/awesome-product',
    priceCurrency: 'USD',
    price: 99.99,
    priceValidUntil: '2024-12-31',
    availability: 'https://schema.org/InStock',
    itemCondition: 'https://schema.org/NewCondition',
  },
  aggregateRating: {
    ratingValue: 4.5,
    reviewCount: 127,
  },
  review: [
    {
      author: 'John Smith',
      rating: 5,
      body: 'Great product! Highly recommend.',
      date: '2024-01-10',
    },
  ],
}

// =============================================================================
// EXAMPLE 4: Breadcrumb Schema
// =============================================================================

export function BreadcrumbSchema({ items }: { items: Breadcrumb[] }) {
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

// Usage
export const breadcrumbExample: Breadcrumb[] = [
  { name: 'Home', url: 'https://example.com' },
  { name: 'Products', url: 'https://example.com/products' },
  { name: 'Category', url: 'https://example.com/products/category' },
  { name: 'Product', url: 'https://example.com/products/category/product' },
]

// =============================================================================
// EXAMPLE 5: FAQ Schema
// =============================================================================

export function FAQSchema({ items }: { items: FAQItem[] }) {
  const schema = {
    '@context': 'https://schema.org',
    '@type': 'FAQPage',
    mainEntity: items.map(item => ({
      '@type': 'Question',
      name: item.question,
      acceptedAnswer: {
        '@type': 'Answer',
        text: item.answer,
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

// Usage
export const faqExample: FAQItem[] = [
  {
    question: 'What is your return policy?',
    answer: 'We accept returns within 30 days of purchase with original receipt.',
  },
  {
    question: 'Do you ship internationally?',
    answer: 'Yes, we ship to over 50 countries worldwide.',
  },
  {
    question: 'How long does shipping take?',
    answer: 'Standard shipping takes 5-7 business days. Express shipping is available.',
  },
]

// =============================================================================
// EXAMPLE 6: Local Business Schema
// =============================================================================

export function LocalBusinessSchema({ business }: { business: LocalBusiness }) {
  const schema = {
    '@context': 'https://schema.org',
    '@type': business.type,
    name: business.name,
    image: business.image,
    '@id': business.url,
    url: business.url,
    telephone: business.telephone,
    priceRange: business.priceRange,
    address: {
      '@type': 'PostalAddress',
      streetAddress: business.address.streetAddress,
      addressLocality: business.address.addressLocality,
      addressRegion: business.address.addressRegion,
      postalCode: business.address.postalCode,
      addressCountry: business.address.addressCountry,
    },
    ...(business.geo && {
      geo: {
        '@type': 'GeoCoordinates',
        latitude: business.geo.latitude,
        longitude: business.geo.longitude,
      },
    }),
    ...(business.openingHours && {
      openingHoursSpecification: business.openingHours.map(hours => ({
        '@type': 'OpeningHoursSpecification',
        dayOfWeek: hours.dayOfWeek,
        opens: hours.opens,
        closes: hours.closes,
      })),
    }),
  }

  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(schema) }}
    />
  )
}

// Usage
export const restaurantExample: LocalBusiness = {
  type: 'Restaurant',
  name: 'My Restaurant',
  image: 'https://example.com/restaurant.jpg',
  url: 'https://example.com',
  telephone: '+1-555-555-5555',
  priceRange: '$$',
  address: {
    streetAddress: '123 Main St',
    addressLocality: 'San Francisco',
    addressRegion: 'CA',
    postalCode: '94105',
    addressCountry: 'US',
  },
  geo: {
    latitude: 37.7749,
    longitude: -122.4194,
  },
  openingHours: [
    {
      dayOfWeek: ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'],
      opens: '11:00',
      closes: '22:00',
    },
    {
      dayOfWeek: ['Saturday', 'Sunday'],
      opens: '10:00',
      closes: '23:00',
    },
  ],
}

// =============================================================================
// EXAMPLE 7: WebSite Schema with Search Action
// =============================================================================

export function WebSiteSchema({
  name,
  url,
  searchUrl,
}: {
  name: string
  url: string
  searchUrl: string
}) {
  const schema = {
    '@context': 'https://schema.org',
    '@type': 'WebSite',
    name,
    url,
    potentialAction: {
      '@type': 'SearchAction',
      target: {
        '@type': 'EntryPoint',
        urlTemplate: `${searchUrl}?q={search_term_string}`,
      },
      'query-input': 'required name=search_term_string',
    },
  }

  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(schema) }}
    />
  )
}

// Usage in layout.tsx
export const websiteSearchExample = {
  name: 'My Website',
  url: 'https://example.com',
  searchUrl: 'https://example.com/search',
}

// =============================================================================
// EXAMPLE 8: Video Schema
// =============================================================================

export function VideoSchema({
  name,
  description,
  thumbnailUrl,
  uploadDate,
  duration,
  contentUrl,
  embedUrl,
}: {
  name: string
  description: string
  thumbnailUrl: string
  uploadDate: string
  duration: string
  contentUrl?: string
  embedUrl?: string
}) {
  const schema = {
    '@context': 'https://schema.org',
    '@type': 'VideoObject',
    name,
    description,
    thumbnailUrl,
    uploadDate,
    duration, // Format: PT1H30M (1 hour 30 minutes)
    contentUrl,
    embedUrl,
  }

  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(schema) }}
    />
  )
}

// =============================================================================
// EXAMPLE 9: Course Schema
// =============================================================================

export function CourseSchema({
  name,
  description,
  provider,
  url,
}: {
  name: string
  description: string
  provider: string
  url: string
}) {
  const schema = {
    '@context': 'https://schema.org',
    '@type': 'Course',
    name,
    description,
    provider: {
      '@type': 'Organization',
      name: provider,
    },
    url,
  }

  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(schema) }}
    />
  )
}

// =============================================================================
// EXAMPLE 10: Event Schema
// =============================================================================

export function EventSchema({
  name,
  startDate,
  endDate,
  location,
  description,
  image,
  url,
  offers,
}: {
  name: string
  startDate: string
  endDate: string
  location: {
    name: string
    address: string
  }
  description: string
  image: string
  url: string
  offers?: {
    price: number
    priceCurrency: string
    availability: string
    url: string
  }
}) {
  const schema = {
    '@context': 'https://schema.org',
    '@type': 'Event',
    name,
    startDate,
    endDate,
    location: {
      '@type': 'Place',
      name: location.name,
      address: {
        '@type': 'PostalAddress',
        streetAddress: location.address,
      },
    },
    description,
    image,
    url,
    ...(offers && {
      offers: {
        '@type': 'Offer',
        price: offers.price,
        priceCurrency: offers.priceCurrency,
        availability: offers.availability,
        url: offers.url,
      },
    }),
  }

  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(schema) }}
    />
  )
}

// =============================================================================
// EXAMPLE 11: Combining Multiple Schemas
// =============================================================================

export function CombinedSchemas() {
  return (
    <>
      <OrganizationSchema org={organizationExample} />
      <WebSiteSchema {...websiteSearchExample} />
      <BreadcrumbSchema items={breadcrumbExample} />
    </>
  )
}

// Usage in layout.tsx or page.tsx
// Place these components in the <head> or at the top of your page component
