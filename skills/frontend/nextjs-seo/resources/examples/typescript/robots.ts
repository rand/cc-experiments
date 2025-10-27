/**
 * Next.js robots.txt Generation Examples
 *
 * Demonstrates various robots.txt patterns for controlling search engine crawlers.
 */

import { MetadataRoute } from 'next'

// =============================================================================
// EXAMPLE 1: Basic robots.txt
// =============================================================================

// app/robots.ts
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

// =============================================================================
// EXAMPLE 2: Multiple User Agents with Different Rules
// =============================================================================

export function multipleUserAgents(): MetadataRoute.Robots {
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
    sitemap: 'https://example.com/sitemap.xml',
  }
}

// =============================================================================
// EXAMPLE 3: Environment-Specific robots.txt
// =============================================================================

export function environmentSpecificRobots(): MetadataRoute.Robots {
  const baseUrl = process.env.NEXT_PUBLIC_BASE_URL || 'https://example.com'
  const isProduction = process.env.NODE_ENV === 'production'

  if (!isProduction) {
    // Block all crawlers in non-production environments
    return {
      rules: {
        userAgent: '*',
        disallow: '/',
      },
    }
  }

  // Allow crawlers in production
  return {
    rules: {
      userAgent: '*',
      allow: '/',
      disallow: ['/admin/', '/api/'],
    },
    sitemap: `${baseUrl}/sitemap.xml`,
  }
}

// =============================================================================
// EXAMPLE 4: Comprehensive Production robots.txt
// =============================================================================

export function productionRobots(): MetadataRoute.Robots {
  return {
    rules: [
      {
        userAgent: 'Googlebot',
        allow: '/',
        disallow: [
          '/admin/',
          '/api/',
          '/private/',
          '/*?*', // Query parameters
          '/search',
          '/checkout',
          '/cart',
          '/account/',
        ],
      },
      {
        userAgent: 'Googlebot-Image',
        allow: '/',
        disallow: ['/admin/', '/private/'],
      },
      {
        userAgent: 'Bingbot',
        allow: '/',
        disallow: ['/admin/', '/api/', '/private/'],
        crawlDelay: 10,
      },
      {
        userAgent: '*',
        allow: '/',
        disallow: [
          '/admin/',
          '/api/',
          '/private/',
          '/account/',
          '/checkout',
          '/cart',
        ],
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

// =============================================================================
// EXAMPLE 5: Block Specific Bots
// =============================================================================

export function blockSpecificBots(): MetadataRoute.Robots {
  return {
    rules: [
      {
        userAgent: 'Googlebot',
        allow: '/',
        disallow: '/admin/',
      },
      // Block bad bots
      {
        userAgent: 'AhrefsBot',
        disallow: '/',
      },
      {
        userAgent: 'SemrushBot',
        disallow: '/',
      },
      {
        userAgent: 'DotBot',
        disallow: '/',
      },
      // Allow other bots with restrictions
      {
        userAgent: '*',
        allow: '/',
        disallow: ['/admin/', '/api/'],
      },
    ],
    sitemap: 'https://example.com/sitemap.xml',
  }
}

// =============================================================================
// EXAMPLE 6: E-commerce robots.txt
// =============================================================================

export function ecommerceRobots(): MetadataRoute.Robots {
  return {
    rules: [
      {
        userAgent: 'Googlebot',
        allow: [
          '/',
          '/products/',
          '/categories/',
        ],
        disallow: [
          '/admin/',
          '/api/',
          '/checkout',
          '/cart',
          '/account/',
          '/wishlist',
          '/*?sort=', // Don't index sorted pages
          '/*?filter=', // Don't index filtered pages
          '/*?page=', // Don't index paginated pages
        ],
      },
      {
        userAgent: '*',
        allow: '/',
        disallow: [
          '/admin/',
          '/api/',
          '/checkout',
          '/cart',
          '/account/',
        ],
      },
    ],
    sitemap: [
      'https://example.com/sitemap.xml',
      'https://example.com/product-sitemap.xml',
      'https://example.com/category-sitemap.xml',
    ],
  }
}

// =============================================================================
// EXAMPLE 7: Blog/Content Site robots.txt
// =============================================================================

export function blogRobots(): MetadataRoute.Robots {
  return {
    rules: [
      {
        userAgent: 'Googlebot',
        allow: '/',
        disallow: [
          '/admin/',
          '/api/',
          '/draft/',
          '/preview/',
          '/*?utm_*', // Don't index UTM tracking URLs
        ],
      },
      {
        userAgent: 'Googlebot-Image',
        allow: '/',
      },
      {
        userAgent: '*',
        allow: '/',
        disallow: ['/admin/', '/api/', '/draft/', '/preview/'],
      },
    ],
    sitemap: [
      'https://example.com/sitemap.xml',
      'https://example.com/blog-sitemap.xml',
      'https://example.com/author-sitemap.xml',
    ],
  }
}

// =============================================================================
// EXAMPLE 8: SaaS Application robots.txt
// =============================================================================

export function saasRobots(): MetadataRoute.Robots {
  return {
    rules: [
      {
        userAgent: 'Googlebot',
        allow: [
          '/',
          '/features/',
          '/pricing',
          '/blog/',
          '/docs/',
        ],
        disallow: [
          '/admin/',
          '/api/',
          '/app/',
          '/dashboard/',
          '/settings/',
          '/auth/',
        ],
      },
      {
        userAgent: '*',
        allow: [
          '/',
          '/features/',
          '/pricing',
          '/blog/',
        ],
        disallow: [
          '/admin/',
          '/api/',
          '/app/',
          '/dashboard/',
        ],
      },
    ],
    sitemap: [
      'https://example.com/sitemap.xml',
      'https://example.com/blog-sitemap.xml',
      'https://example.com/docs-sitemap.xml',
    ],
  }
}

// =============================================================================
// EXAMPLE 9: Staging/Development robots.txt
// =============================================================================

export function stagingRobots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: '*',
      disallow: '/',
    },
  }
}

// =============================================================================
// EXAMPLE 10: Custom Crawl Delays
// =============================================================================

export function customCrawlDelays(): MetadataRoute.Robots {
  return {
    rules: [
      {
        userAgent: 'Googlebot',
        allow: '/',
        disallow: '/admin/',
        crawlDelay: 0, // No delay for Google
      },
      {
        userAgent: 'Bingbot',
        allow: '/',
        disallow: '/admin/',
        crawlDelay: 10, // 10 second delay for Bing
      },
      {
        userAgent: '*',
        allow: '/',
        disallow: '/admin/',
        crawlDelay: 30, // 30 second delay for others
      },
    ],
    sitemap: 'https://example.com/sitemap.xml',
  }
}

// =============================================================================
// EXAMPLE 11: Multi-Domain robots.txt
// =============================================================================

export function multiDomainRobots(): MetadataRoute.Robots {
  const domain = process.env.NEXT_PUBLIC_DOMAIN || 'example.com'

  return {
    rules: {
      userAgent: '*',
      allow: '/',
      disallow: ['/admin/', '/api/'],
    },
    sitemap: `https://${domain}/sitemap.xml`,
    host: `https://${domain}`,
  }
}

// =============================================================================
// EXAMPLE 12: Regional robots.txt
// =============================================================================

export function regionalRobots(): MetadataRoute.Robots {
  return {
    rules: [
      {
        userAgent: 'Googlebot',
        allow: '/',
        disallow: ['/admin/', '/api/'],
      },
      {
        userAgent: 'Googlebot',
        allow: '/en/',
        disallow: ['/admin/', '/api/'],
      },
      {
        userAgent: '*',
        allow: '/',
        disallow: ['/admin/', '/api/'],
      },
    ],
    sitemap: [
      'https://example.com/sitemap-en.xml',
      'https://example.com/sitemap-es.xml',
      'https://example.com/sitemap-fr.xml',
    ],
  }
}

// =============================================================================
// EXAMPLE 13: Allow Common Resources
// =============================================================================

export function allowCommonResources(): MetadataRoute.Robots {
  return {
    rules: [
      {
        userAgent: '*',
        allow: [
          '/',
          '/*.css$',
          '/*.js$',
          '/*.png$',
          '/*.jpg$',
          '/*.gif$',
          '/*.svg$',
          '/*.woff$',
          '/*.woff2$',
        ],
        disallow: [
          '/admin/',
          '/api/',
          '/private/',
        ],
      },
    ],
    sitemap: 'https://example.com/sitemap.xml',
  }
}

// =============================================================================
// EXAMPLE 14: Conditional Rules Based on Feature Flags
// =============================================================================

export function featureFlagRobots(): MetadataRoute.Robots {
  const allowBeta = process.env.ALLOW_BETA_INDEXING === 'true'

  return {
    rules: {
      userAgent: '*',
      allow: '/',
      disallow: [
        '/admin/',
        '/api/',
        ...(allowBeta ? [] : ['/beta/']),
      ],
    },
    sitemap: 'https://example.com/sitemap.xml',
  }
}

// =============================================================================
// EXAMPLE 15: Documentation Site robots.txt
// =============================================================================

export function docsRobots(): MetadataRoute.Robots {
  return {
    rules: [
      {
        userAgent: 'Googlebot',
        allow: '/',
        disallow: [
          '/admin/',
          '/api/',
          '/search',
          '/*?*', // Don't index search results
        ],
      },
      {
        userAgent: '*',
        allow: '/',
        disallow: ['/admin/', '/api/'],
      },
    ],
    sitemap: [
      'https://example.com/sitemap.xml',
      'https://example.com/docs-sitemap.xml',
    ],
  }
}

// =============================================================================
// EXAMPLE 16: Helper Function for Dynamic robots.txt
// =============================================================================

interface RobotsConfig {
  allowedPaths?: string[]
  disallowedPaths?: string[]
  sitemaps?: string[]
  crawlDelay?: number
  blockBadBots?: boolean
}

export function generateRobots(config: RobotsConfig): MetadataRoute.Robots {
  const {
    allowedPaths = ['/'],
    disallowedPaths = ['/admin/', '/api/'],
    sitemaps = ['https://example.com/sitemap.xml'],
    crawlDelay,
    blockBadBots = false,
  } = config

  const rules: MetadataRoute.Robots['rules'] = []

  // Block bad bots if enabled
  if (blockBadBots) {
    const badBots = ['AhrefsBot', 'SemrushBot', 'DotBot', 'MJ12bot']
    badBots.forEach(bot => {
      rules.push({
        userAgent: bot,
        disallow: '/',
      })
    })
  }

  // Main rules
  rules.push({
    userAgent: '*',
    allow: allowedPaths,
    disallow: disallowedPaths,
    ...(crawlDelay && { crawlDelay }),
  })

  return {
    rules: rules.length === 1 ? rules[0] : rules,
    sitemap: sitemaps.length === 1 ? sitemaps[0] : sitemaps,
  }
}

// Usage
export const customRobots = generateRobots({
  disallowedPaths: ['/admin/', '/api/', '/private/'],
  sitemaps: [
    'https://example.com/sitemap.xml',
    'https://example.com/blog-sitemap.xml',
  ],
  blockBadBots: true,
})
