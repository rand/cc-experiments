---
name: deployment-netlify-optimization
description: Improving site load times and Core Web Vitals
---



# Netlify Optimization

**Scope**: Netlify performance optimization, CDN caching, build optimization, and cost reduction
**Lines**: ~310
**Last Updated**: 2025-10-18

## When to Use This Skill

Activate this skill when:
- Improving site load times and Core Web Vitals
- Optimizing build times and reducing CI/CD duration
- Reducing bandwidth costs and Netlify usage
- Implementing effective caching strategies
- Optimizing images, fonts, and static assets
- Leveraging Netlify CDN for global performance
- Debugging slow builds or large bundle sizes
- Setting up incremental builds (Next.js, Gatsby)

## Core Concepts

### Netlify CDN

**Global edge network**:
- 100+ edge locations worldwide
- Automatic SSL/TLS
- DDoS protection included
- HTTP/2 and HTTP/3 support

**Caching behavior**:
- Static assets cached at edge by default
- HTML pages: `Cache-Control: public, max-age=0, must-revalidate`
- Assets: Cached based on headers or defaults
- Cache invalidation on new deploy

### Build Optimization

**Build minutes are limited**:
- Starter: 300 min/month
- Pro: 1,000 min/month
- Each build counts toward limit

**Optimization strategies**:
- Enable build caching
- Use incremental builds (Next.js, Gatsby)
- Optimize dependencies (reduce install time)
- Skip builds for non-code changes
- Use build plugins efficiently

### Performance Budget

**Key metrics**:
- Time to First Byte (TTFB): <200ms
- First Contentful Paint (FCP): <1.8s
- Largest Contentful Paint (LCP): <2.5s
- Cumulative Layout Shift (CLS): <0.1
- Time to Interactive (TTI): <3.8s

---

## Patterns

### Pattern 1: Optimal Cache Headers

```toml
# netlify.toml - Cache optimization
[[headers]]
  for = "/*.html"
  [headers.values]
    Cache-Control = "public, max-age=0, must-revalidate"

[[headers]]
  for = "/assets/*"
  [headers.values]
    Cache-Control = "public, max-age=31536000, immutable"

[[headers]]
  for = "/*.js"
  [headers.values]
    Cache-Control = "public, max-age=31536000, immutable"

[[headers]]
  for = "/*.css"
  [headers.values]
    Cache-Control = "public, max-age=31536000, immutable"

[[headers]]
  for = "/*.woff2"
  [headers.values]
    Cache-Control = "public, max-age=31536000, immutable"

[[headers]]
  for = "/images/*"
  [headers.values]
    Cache-Control = "public, max-age=2592000, immutable"  # 30 days

[[headers]]
  for = "/api/*"
  [headers.values]
    Cache-Control = "no-cache, no-store, must-revalidate"
```

**Best practices**:
- **HTML**: No cache or short cache (always fresh)
- **Hashed assets** (e.g., `main.abc123.js`): 1 year + immutable
- **Non-hashed assets**: Shorter cache (1 day - 30 days)
- **API responses**: No cache or short cache with revalidation

### Pattern 2: Image Optimization

```toml
# netlify.toml - Image optimization plugin
[[plugins]]
  package = "@netlify/plugin-image-optim"

[plugins.inputs]
  # Optimize quality (0-100)
  quality = 85

  # Generate WebP versions
  formats = ["webp", "avif"]

  # Resize images
  maxWidth = 1920
  maxHeight = 1080
```

**Next.js Image Optimization**:
```javascript
// next.config.js
module.exports = {
  images: {
    domains: ['cdn.example.com'],
    formats: ['image/avif', 'image/webp'],
    deviceSizes: [640, 750, 828, 1080, 1200, 1920],
    imageSizes: [16, 32, 48, 64, 96, 128, 256, 384],
  },
};
```

**Manual optimization**:
```bash
# Use sharp for build-time optimization
npm install sharp

# Optimize during build
node scripts/optimize-images.js
```

**When to use**:
- Large image assets (>100KB)
- High-traffic sites
- Mobile-first applications

### Pattern 3: Build Caching

```toml
# netlify.toml - Build plugins for caching
[[plugins]]
  package = "netlify-plugin-cache"

[plugins.inputs]
  # Cache directories
  paths = [
    "node_modules",
    ".next/cache",
    ".cache",
    "public/static",
  ]
```

**Next.js incremental builds**:
```javascript
// next.config.js
module.exports = {
  // Enable Next.js cache
  experimental: {
    outputStandalone: true,
  },
};
```

**Gatsby incremental builds**:
```toml
# netlify.toml
[build.environment]
  GATSBY_EXPERIMENTAL_PAGE_BUILD_ON_DATA_CHANGES = "true"

[build]
  command = "npm run build"
  publish = "public"
```

**When to use**:
- Long build times (>5 minutes)
- Large node_modules
- Next.js or Gatsby projects

### Pattern 4: Skip Builds

```toml
# netlify.toml - Skip builds conditionally
[build]
  command = "npm run build"
  publish = "dist"

  # Skip build if no relevant changes
  ignore = "git diff --quiet $CACHED_COMMIT_REF $COMMIT_REF -- src/ public/"
```

**Skip builds for docs changes**:
```bash
# Only build if src/ or config changed, not docs/
ignore = "git diff --quiet $CACHED_COMMIT_REF $COMMIT_REF -- src/ package.json netlify.toml"
```

**When to use**:
- Monorepo with multiple projects
- Documentation-heavy repos
- Frequent non-code commits

### Pattern 5: Asset Optimization

```toml
# netlify.toml - Asset optimization
[build]
  command = "npm run build && npm run optimize"
  publish = "dist"

[build.processing]
  skip_processing = false

[build.processing.css]
  bundle = true
  minify = true

[build.processing.js]
  bundle = true
  minify = true

[build.processing.images]
  compress = true
```

**Vite bundle optimization**:
```javascript
// vite.config.js
import { defineConfig } from 'vite';

export default defineConfig({
  build: {
    minify: 'terser',
    terserOptions: {
      compress: {
        drop_console: true, // Remove console.log in production
      },
    },
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom'],
          utils: ['lodash', 'date-fns'],
        },
      },
    },
  },
});
```

**When to use**:
- Large JavaScript bundles (>500KB)
- Many dependencies
- Performance-critical applications

### Pattern 6: Prerendering and Caching

```toml
# netlify.toml - Prerender routes
[[redirects]]
  from = "/blog/*"
  to = "/blog/:splat"
  status = 200
  force = true
  # Cache prerendered pages
  headers = {Cache-Control = "public, max-age=3600, s-maxage=31536000"}

# Cache static API responses
[[redirects]]
  from = "/api/static/*"
  to = "/.netlify/functions/api-static/:splat"
  status = 200
  headers = {Cache-Control = "public, max-age=300"}  # 5 min cache
```

**On-Demand Builders** (cache until redeploy):
```javascript
// netlify/functions/expensive-page.js
import { builder } from '@netlify/functions';

export const handler = builder(async (event) => {
  // Expensive computation, cached until next deploy
  const data = await fetchExpensiveData();

  return {
    statusCode: 200,
    headers: {
      'Content-Type': 'application/json',
      'Cache-Control': 'public, max-age=0, must-revalidate',
      'Netlify-CDN-Cache-Control': 'public, max-age=31536000', // CDN cache 1 year
    },
    body: JSON.stringify(data),
  };
});
```

**When to use**:
- Semi-static content (updates infrequently)
- Expensive API calls
- Database queries that don't change often

### Pattern 7: Bundle Analysis

```bash
# Analyze Next.js bundle
npm install @next/bundle-analyzer

# next.config.js
const withBundleAnalyzer = require('@next/bundle-analyzer')({
  enabled: process.env.ANALYZE === 'true',
});

module.exports = withBundleAnalyzer({
  // Next.js config
});

# Run analysis
ANALYZE=true npm run build
```

**Vite bundle analysis**:
```bash
npm install rollup-plugin-visualizer

# vite.config.js
import { visualizer } from 'rollup-plugin-visualizer';

export default defineConfig({
  plugins: [
    visualizer({
      open: true,
      gzipSize: true,
      brotliSize: true,
    }),
  ],
});
```

**When to use**:
- Large bundle sizes (>1MB)
- Slow page loads
- High bounce rates

### Pattern 8: Netlify Edge for Performance

```typescript
// netlify/edge-functions/cache-control.ts
import { Context } from "https://edge.netlify.com";

export default async (request: Request, context: Context) => {
  const response = await context.next();

  // Add caching to specific routes
  if (request.url.includes('/blog/')) {
    const headers = new Headers(response.headers);
    headers.set('Cache-Control', 'public, max-age=3600, s-maxage=86400');

    return new Response(response.body, {
      status: response.status,
      headers,
    });
  }

  return response;
};

export const config = {
  path: "/*",
};
```

**When to use**:
- Dynamic cache control
- A/B testing without rebuilds
- Personalization with caching

---

## Quick Reference

### Cache Control Values

```
Pattern                                    | Use Case
-------------------------------------------|---------------------------
public, max-age=0, must-revalidate        | HTML pages (always fresh)
public, max-age=31536000, immutable       | Hashed assets (1 year)
public, max-age=3600                      | Semi-static content (1 hour)
no-cache, no-store, must-revalidate       | Private/dynamic data
s-maxage=86400                            | CDN cache (1 day)
```

### Build Optimization Checklist

```
✅ Enable build caching (node_modules, framework caches)
✅ Use incremental builds (Next.js, Gatsby)
✅ Skip builds for non-code changes
✅ Optimize dependencies (prune unused packages)
✅ Use build plugins efficiently
✅ Cache build artifacts between deploys
✅ Analyze bundle size regularly
✅ Remove console.log in production
```

### Performance Metrics Targets

```
Metric     | Good    | Needs Improvement | Poor
-----------|---------|-------------------|-------
TTFB       | <200ms  | 200-600ms        | >600ms
FCP        | <1.8s   | 1.8-3.0s         | >3.0s
LCP        | <2.5s   | 2.5-4.0s         | >4.0s
CLS        | <0.1    | 0.1-0.25         | >0.25
TTI        | <3.8s   | 3.8-7.3s         | >7.3s
```

### Asset Optimization Tools

```
Asset Type | Tool                  | Command
-----------|------------------------|---------------------------
Images     | sharp                 | npm install sharp
Images     | imagemin              | npm install imagemin
CSS        | cssnano               | npm install cssnano
JS         | terser                | npm install terser
Fonts      | subset-font           | npm install subset-font
SVG        | svgo                  | npm install svgo
```

### Build Plugin Recommendations

```
Plugin                          | Purpose
--------------------------------|---------------------------
@netlify/plugin-image-optim     | Image optimization
netlify-plugin-cache            | Cache node_modules
@netlify/plugin-lighthouse      | Performance audits
netlify-plugin-inline-critical  | Inline critical CSS
@netlify/plugin-nextjs          | Next.js optimization
```

---

## Anti-Patterns

❌ **No cache headers**: Static assets fetched every time
✅ Set long cache for hashed assets, short for HTML

❌ **Large bundle sizes**: Slow page loads, poor UX
✅ Code split, tree shake, analyze bundles

❌ **Unoptimized images**: Large file sizes, slow loads
✅ Use WebP/AVIF, resize, compress, lazy load

❌ **No build caching**: Slow builds, wasted build minutes
✅ Cache node_modules and framework caches

❌ **Building for every commit**: Wasted resources
✅ Skip builds for docs/non-code changes

❌ **No bundle analysis**: Unknown performance bottlenecks
✅ Regularly analyze with tools (bundle-analyzer, lighthouse)

❌ **Synchronous loading**: Blocking render
✅ Async/defer scripts, lazy load images/components

❌ **No performance monitoring**: Issues go unnoticed
✅ Use Netlify Analytics, Lighthouse CI, Real User Monitoring

---

## Related Skills

- `netlify-deployment.md` - Site deployment, build configuration, continuous deployment
- `netlify-functions.md` - Serverless functions, Edge Functions, API optimization
- `frontend-performance.md` - General frontend performance patterns
- `nextjs-seo.md` - Next.js SEO and performance optimization
- `cdn-configuration.md` - CDN strategies and caching patterns
- `web-vitals-optimization.md` - Core Web Vitals improvement techniques

---

**Last Updated**: 2025-10-18
**Format Version**: 1.0 (Atomic)
