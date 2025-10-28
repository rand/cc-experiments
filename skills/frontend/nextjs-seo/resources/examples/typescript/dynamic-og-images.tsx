/**
 * Dynamic Open Graph Images with next/og
 *
 * Demonstrates generating dynamic OG images using Next.js ImageResponse API.
 * These are ideal for social media sharing previews.
 */

import { ImageResponse } from 'next/og'
import { NextRequest } from 'next/server'

// =============================================================================
// EXAMPLE 1: Basic Dynamic OG Image
// =============================================================================

// app/api/og/route.tsx
export async function GET_Basic(request: NextRequest) {
  const { searchParams } = new URL(request.url)
  const title = searchParams.get('title') || 'Default Title'

  return new ImageResponse(
    (
      <div
        style={{
          fontSize: 60,
          background: 'linear-gradient(to bottom, #2563eb, #1e40af)',
          width: '100%',
          height: '100%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: 'white',
          fontWeight: 'bold',
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

// =============================================================================
// EXAMPLE 2: Blog Post OG Image with Custom Font
// =============================================================================

// app/api/og/blog/route.tsx
export async function GET_BlogPost(request: NextRequest) {
  const { searchParams } = new URL(request.url)
  const title = searchParams.get('title') || 'Blog Post Title'
  const author = searchParams.get('author') || 'Anonymous'
  const date = searchParams.get('date') || new Date().toLocaleDateString()

  // Load custom font
  const interSemiBold = fetch(
    new URL('../../../assets/Inter-SemiBold.ttf', import.meta.url)
  ).then((res) => res.arrayBuffer())

  return new ImageResponse(
    (
      <div
        style={{
          height: '100%',
          width: '100%',
          display: 'flex',
          flexDirection: 'column',
          backgroundColor: '#fff',
          padding: '60px',
        }}
      >
        {/* Header */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            marginBottom: '40px',
          }}
        >
          <div
            style={{
              fontSize: 32,
              fontWeight: 'bold',
              color: '#1f2937',
            }}
          >
            My Blog
          </div>
        </div>

        {/* Title */}
        <div
          style={{
            fontSize: 64,
            fontWeight: 'bold',
            color: '#111827',
            lineHeight: 1.2,
            marginBottom: 'auto',
            maxWidth: '90%',
          }}
        >
          {title}
        </div>

        {/* Footer */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            fontSize: 28,
            color: '#6b7280',
          }}
        >
          <span>{author}</span>
          <span style={{ margin: '0 20px' }}>•</span>
          <span>{date}</span>
        </div>
      </div>
    ),
    {
      width: 1200,
      height: 630,
      fonts: [
        {
          name: 'Inter',
          data: await interSemiBold,
          style: 'normal',
          weight: 600,
        },
      ],
    }
  )
}

// =============================================================================
// EXAMPLE 3: Product OG Image with Image Background
// =============================================================================

// app/api/og/product/route.tsx
export async function GET_Product(request: NextRequest) {
  const { searchParams } = new URL(request.url)
  const name = searchParams.get('name') || 'Product Name'
  const price = searchParams.get('price') || '$99.99'
  const imageUrl = searchParams.get('image') || ''

  return new ImageResponse(
    (
      <div
        style={{
          height: '100%',
          width: '100%',
          display: 'flex',
          backgroundColor: '#f3f4f6',
        }}
      >
        {/* Left side - Product image */}
        <div
          style={{
            width: '50%',
            height: '100%',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            backgroundColor: '#ffffff',
          }}
        >
          {imageUrl && (
            <img
              src={imageUrl}
              alt={name}
              style={{
                width: '80%',
                height: '80%',
                objectFit: 'contain',
              }}
            />
          )}
        </div>

        {/* Right side - Product info */}
        <div
          style={{
            width: '50%',
            height: '100%',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'center',
            padding: '60px',
          }}
        >
          <div
            style={{
              fontSize: 56,
              fontWeight: 'bold',
              color: '#111827',
              marginBottom: '30px',
              lineHeight: 1.2,
            }}
          >
            {name}
          </div>

          <div
            style={{
              fontSize: 72,
              fontWeight: 'bold',
              color: '#2563eb',
            }}
          >
            {price}
          </div>
        </div>
      </div>
    ),
    {
      width: 1200,
      height: 630,
    }
  )
}

// =============================================================================
// EXAMPLE 4: Author Profile OG Image
// =============================================================================

// app/api/og/author/route.tsx
export async function GET_Author(request: NextRequest) {
  const { searchParams } = new URL(request.url)
  const name = searchParams.get('name') || 'Author Name'
  const bio = searchParams.get('bio') || 'Author biography'
  const avatarUrl = searchParams.get('avatar') || ''

  return new ImageResponse(
    (
      <div
        style={{
          height: '100%',
          width: '100%',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          backgroundColor: '#1f2937',
          padding: '60px',
        }}
      >
        {/* Avatar */}
        {avatarUrl && (
          <div
            style={{
              width: '200px',
              height: '200px',
              borderRadius: '100px',
              overflow: 'hidden',
              marginBottom: '40px',
              display: 'flex',
            }}
          >
            <img
              src={avatarUrl}
              alt={name}
              style={{
                width: '100%',
                height: '100%',
                objectFit: 'cover',
              }}
            />
          </div>
        )}

        {/* Name */}
        <div
          style={{
            fontSize: 64,
            fontWeight: 'bold',
            color: '#ffffff',
            marginBottom: '20px',
          }}
        >
          {name}
        </div>

        {/* Bio */}
        <div
          style={{
            fontSize: 32,
            color: '#9ca3af',
            textAlign: 'center',
            maxWidth: '80%',
          }}
        >
          {bio}
        </div>
      </div>
    ),
    {
      width: 1200,
      height: 630,
    }
  )
}

// =============================================================================
// EXAMPLE 5: Stats/Metrics OG Image
// =============================================================================

// app/api/og/stats/route.tsx
export async function GET_Stats(request: NextRequest) {
  const { searchParams } = new URL(request.url)
  const title = searchParams.get('title') || 'Statistics'
  const stat1 = searchParams.get('stat1') || '0'
  const label1 = searchParams.get('label1') || 'Metric 1'
  const stat2 = searchParams.get('stat2') || '0'
  const label2 = searchParams.get('label2') || 'Metric 2'
  const stat3 = searchParams.get('stat3') || '0'
  const label3 = searchParams.get('label3') || 'Metric 3'

  return new ImageResponse(
    (
      <div
        style={{
          height: '100%',
          width: '100%',
          display: 'flex',
          flexDirection: 'column',
          backgroundColor: '#0f172a',
          padding: '60px',
        }}
      >
        {/* Title */}
        <div
          style={{
            fontSize: 56,
            fontWeight: 'bold',
            color: '#ffffff',
            marginBottom: '60px',
          }}
        >
          {title}
        </div>

        {/* Stats */}
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            width: '100%',
          }}
        >
          {/* Stat 1 */}
          <div
            style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
            }}
          >
            <div
              style={{
                fontSize: 72,
                fontWeight: 'bold',
                color: '#3b82f6',
              }}
            >
              {stat1}
            </div>
            <div
              style={{
                fontSize: 28,
                color: '#94a3b8',
                marginTop: '10px',
              }}
            >
              {label1}
            </div>
          </div>

          {/* Stat 2 */}
          <div
            style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
            }}
          >
            <div
              style={{
                fontSize: 72,
                fontWeight: 'bold',
                color: '#10b981',
              }}
            >
              {stat2}
            </div>
            <div
              style={{
                fontSize: 28,
                color: '#94a3b8',
                marginTop: '10px',
              }}
            >
              {label2}
            </div>
          </div>

          {/* Stat 3 */}
          <div
            style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
            }}
          >
            <div
              style={{
                fontSize: 72,
                fontWeight: 'bold',
                color: '#f59e0b',
              }}
            >
              {stat3}
            </div>
            <div
              style={{
                fontSize: 28,
                color: '#94a3b8',
                marginTop: '10px',
              }}
            >
              {label3}
            </div>
          </div>
        </div>
      </div>
    ),
    {
      width: 1200,
      height: 630,
    }
  )
}

// =============================================================================
// EXAMPLE 6: Using Dynamic OG Image in Metadata
// =============================================================================

// app/blog/[slug]/page.tsx
import { Metadata } from 'next'

interface BlogPageProps {
  params: { slug: string }
}

async function getBlogPost(slug: string) {
  // Mock data
  return {
    title: 'My Blog Post',
    author: 'John Doe',
    date: '2024-01-15',
  }
}

export async function generateMetadata_WithDynamicOG(
  { params }: BlogPageProps
): Promise<Metadata> {
  const post = await getBlogPost(params.slug)

  const ogImageUrl = new URL('/api/og/blog', 'https://example.com')
  ogImageUrl.searchParams.set('title', post.title)
  ogImageUrl.searchParams.set('author', post.author)
  ogImageUrl.searchParams.set('date', post.date)

  return {
    title: post.title,
    openGraph: {
      images: [
        {
          url: ogImageUrl.toString(),
          width: 1200,
          height: 630,
          alt: post.title,
        },
      ],
    },
    twitter: {
      images: [ogImageUrl.toString()],
    },
  }
}

// =============================================================================
// EXAMPLE 7: Multi-Style OG Image (Based on Category)
// =============================================================================

// app/api/og/route.tsx
export async function GET_MultiStyle(request: NextRequest) {
  const { searchParams } = new URL(request.url)
  const title = searchParams.get('title') || 'Title'
  const category = searchParams.get('category') || 'default'

  const styles = {
    tech: {
      bg: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
      color: '#ffffff',
    },
    business: {
      bg: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
      color: '#ffffff',
    },
    design: {
      bg: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
      color: '#1f2937',
    },
    default: {
      bg: '#1f2937',
      color: '#ffffff',
    },
  }

  const style = styles[category as keyof typeof styles] || styles.default

  return new ImageResponse(
    (
      <div
        style={{
          height: '100%',
          width: '100%',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          background: style.bg,
          padding: '60px',
        }}
      >
        <div
          style={{
            fontSize: 72,
            fontWeight: 'bold',
            color: style.color,
            textAlign: 'center',
            maxWidth: '90%',
            lineHeight: 1.2,
          }}
        >
          {title}
        </div>

        <div
          style={{
            fontSize: 32,
            color: style.color,
            opacity: 0.8,
            marginTop: '30px',
            textTransform: 'uppercase',
            letterSpacing: '2px',
          }}
        >
          {category}
        </div>
      </div>
    ),
    {
      width: 1200,
      height: 630,
    }
  )
}

// =============================================================================
// EXAMPLE 8: OG Image with Logo and Branding
// =============================================================================

// app/api/og/branded/route.tsx
export async function GET_Branded(request: NextRequest) {
  const { searchParams } = new URL(request.url)
  const title = searchParams.get('title') || 'Page Title'
  const subtitle = searchParams.get('subtitle') || ''

  return new ImageResponse(
    (
      <div
        style={{
          height: '100%',
          width: '100%',
          display: 'flex',
          flexDirection: 'column',
          backgroundColor: '#ffffff',
        }}
      >
        {/* Header with logo */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            padding: '40px 60px',
            borderBottom: '2px solid #e5e7eb',
          }}
        >
          <div
            style={{
              fontSize: 36,
              fontWeight: 'bold',
              color: '#2563eb',
            }}
          >
            My Brand
          </div>
        </div>

        {/* Content */}
        <div
          style={{
            flex: 1,
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'center',
            padding: '0 60px',
          }}
        >
          <div
            style={{
              fontSize: 64,
              fontWeight: 'bold',
              color: '#111827',
              lineHeight: 1.2,
              marginBottom: subtitle ? '20px' : '0',
            }}
          >
            {title}
          </div>

          {subtitle && (
            <div
              style={{
                fontSize: 36,
                color: '#6b7280',
                lineHeight: 1.4,
              }}
            >
              {subtitle}
            </div>
          )}
        </div>

        {/* Footer */}
        <div
          style={{
            display: 'flex',
            padding: '40px 60px',
            backgroundColor: '#f9fafb',
            fontSize: 28,
            color: '#9ca3af',
          }}
        >
          example.com
        </div>
      </div>
    ),
    {
      width: 1200,
      height: 630,
    }
  )
}
