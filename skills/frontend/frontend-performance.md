---
name: frontend-frontend-performance
description: Optimizing application performance
---



# Frontend Performance

**Scope**: Bundle optimization, code splitting, image optimization, Core Web Vitals, lazy loading
**Lines**: ~310
**Last Updated**: 2025-10-18

## When to Use This Skill

Activate this skill when:
- Optimizing application performance
- Reducing bundle size
- Improving Core Web Vitals
- Implementing lazy loading
- Optimizing images and assets
- Diagnosing performance issues

## Core Concepts

### Core Web Vitals

**LCP** (Largest Contentful Paint) - Loading performance
- Target: < 2.5 seconds
- Measures: Time to render largest content

**FID** (First Input Delay) - Interactivity
- Target: < 100ms
- Measures: Time from interaction to response

**CLS** (Cumulative Layout Shift) - Visual stability
- Target: < 0.1
- Measures: Unexpected layout shifts

**INP** (Interaction to Next Paint) - Replacing FID
- Target: < 200ms
- Measures: Overall responsiveness

---

## Bundle Optimization

### Analyze Bundle Size

```bash
# Next.js
npm run build
# Output shows bundle sizes

# Webpack Bundle Analyzer
npm install --save-dev webpack-bundle-analyzer

# Vite
npm run build
vite-bundle-visualizer
```

### Code Splitting

**Route-based splitting** (automatic in Next.js):
```tsx
// app/dashboard/page.tsx
// Automatically code-split by route
export default function Dashboard() {
  return <div>Dashboard</div>;
}
```

**Component-based splitting**:
```tsx
import { lazy, Suspense } from 'react';

// Lazy load heavy component
const HeavyChart = lazy(() => import('./components/HeavyChart'));

function Dashboard() {
  return (
    <div>
      <Suspense fallback={<div>Loading chart...</div>}>
        <HeavyChart />
      </Suspense>
    </div>
  );
}
```

**Dynamic imports**:
```tsx
// Load library only when needed
async function handleExport() {
  const { exportToPDF } = await import('./lib/pdf-export');
  exportToPDF(data);
}
```

### Tree Shaking

```tsx
// ❌ Bad: Imports entire library
import _ from 'lodash';
_.debounce(fn, 300);

// ✅ Good: Import only what you need
import debounce from 'lodash/debounce';
debounce(fn, 300);

// ✅ Better: Use modern alternative
import { debounce } from 'es-toolkit';
```

### Remove Unused Code

```tsx
// ❌ Bad: Importing unused code
import { Button, Card, Table, Modal, Tabs } from 'ui-library';
// Only using Button

// ✅ Good: Only import what's used
import { Button } from 'ui-library';
```

**Tools**:
- ESLint `no-unused-vars`
- Webpack `sideEffects: false` in package.json
- PurgeCSS for unused CSS

---

## Image Optimization

### Next.js Image Component

```tsx
import Image from 'next/image';

// ❌ Bad: Regular img tag
<img src="/photo.jpg" alt="Photo" />

// ✅ Good: Next.js Image (automatic optimization)
<Image
  src="/photo.jpg"
  alt="Photo"
  width={800}
  height={600}
  priority // Load eagerly (above fold)
/>

// Responsive image
<Image
  src="/photo.jpg"
  alt="Photo"
  fill
  sizes="(max-width: 768px) 100vw, 50vw"
  style={{ objectFit: 'cover' }}
/>
```

**Benefits**:
- Automatic WebP/AVIF conversion
- Lazy loading by default
- Responsive images
- Blur placeholder

### Image Formats

```
Format    | Use Case           | Savings vs PNG
----------|--------------------|--------------
WebP      | General purpose    | 25-35%
AVIF      | Modern browsers    | 50%
PNG       | Transparency       | Baseline
JPEG      | Photos             | Smaller than PNG
SVG       | Icons, logos       | Scalable
```

### Lazy Loading

```tsx
// Images (native)
<img src="photo.jpg" loading="lazy" alt="Photo" />

// Next.js Image (lazy by default)
<Image src="/photo.jpg" alt="Photo" width={800} height={600} />

// Eager loading (above fold)
<Image src="/hero.jpg" alt="Hero" width={1200} height={600} priority />
```

### Image Optimization Tools

```bash
# Compress images
npx @squoosh/cli --webp auto *.jpg

# Optimize SVGs
npx svgo *.svg

# Generate responsive images
npx sharp-cli resize 800 600 --input photo.jpg --output photo-800.jpg
```

---

## JavaScript Optimization

### Debouncing and Throttling

```tsx
import { debounce } from 'es-toolkit';

function SearchInput() {
  const [query, setQuery] = useState('');

  // Debounce API calls
  const debouncedSearch = useMemo(
    () => debounce((value: string) => {
      fetch(`/api/search?q=${value}`);
    }, 300),
    []
  );

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setQuery(value);
    debouncedSearch(value);
  };

  return <input value={query} onChange={handleChange} />;
}
```

```tsx
import { throttle } from 'es-toolkit';

function ScrollTracker() {
  const handleScroll = useMemo(
    () => throttle(() => {
      console.log('Scroll position:', window.scrollY);
    }, 100),
    []
  );

  useEffect(() => {
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, [handleScroll]);

  return <div>Content</div>;
}
```

### Memoization

```tsx
import { memo, useMemo, useCallback } from 'react';

// Memoize expensive component
const ExpensiveList = memo(function ExpensiveList({ items }: { items: Item[] }) {
  return (
    <ul>
      {items.map(item => (
        <li key={item.id}>{item.name}</li>
      ))}
    </ul>
  );
});

// Memoize expensive computation
function ProductList({ products }: { products: Product[] }) {
  const sortedProducts = useMemo(() => {
    return [...products].sort((a, b) => b.price - a.price);
  }, [products]);

  return <div>{sortedProducts.map(p => <div key={p.id}>{p.name}</div>)}</div>;
}

// Memoize callbacks
function TodoList({ todos }: { todos: Todo[] }) {
  const [filter, setFilter] = useState('all');

  const handleToggle = useCallback((id: string) => {
    // Toggle todo logic
  }, []);

  return (
    <div>
      {todos.map(todo => (
        <TodoItem key={todo.id} todo={todo} onToggle={handleToggle} />
      ))}
    </div>
  );
}
```

**When to memoize**:
- Expensive calculations
- Large lists
- Stable callback references for child components
- NOT for cheap operations (overhead > benefit)

### Virtual Lists

```tsx
import { useVirtualizer } from '@tanstack/react-virtual';

function VirtualList({ items }: { items: Item[] }) {
  const parentRef = useRef<HTMLDivElement>(null);

  const virtualizer = useVirtualizer({
    count: items.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 50, // Estimated row height
  });

  return (
    <div ref={parentRef} style={{ height: '400px', overflow: 'auto' }}>
      <div style={{ height: `${virtualizer.getTotalSize()}px`, position: 'relative' }}>
        {virtualizer.getVirtualItems().map(virtualItem => (
          <div
            key={virtualItem.index}
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              width: '100%',
              height: `${virtualItem.size}px`,
              transform: `translateY(${virtualItem.start}px)`,
            }}
          >
            {items[virtualItem.index].name}
          </div>
        ))}
      </div>
    </div>
  );
}
```

**Use when**:
- Rendering >100 items
- Items have consistent height
- Scrolling performance is critical

---

## CSS Optimization

### Critical CSS

```tsx
// app/layout.tsx
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html>
      <head>
        {/* Inline critical CSS */}
        <style dangerouslySetInnerHTML={{ __html: criticalCSS }} />
      </head>
      <body>{children}</body>
    </html>
  );
}
```

### CSS-in-JS Performance

```tsx
// ❌ Bad: Inline styles (no caching, creates new object every render)
<div style={{ color: 'red', fontSize: 16 }}>Text</div>

// ✅ Good: CSS modules or Tailwind (cached, reusable)
<div className="text-red-500 text-base">Text</div>

// ✅ Good: Extract constant styles
const styles = { color: 'red', fontSize: 16 };
<div style={styles}>Text</div>
```

### Remove Unused CSS

```tsx
// Tailwind CSS (automatic purging)
// tailwind.config.js
module.exports = {
  content: [
    './app/**/*.{js,ts,jsx,tsx}',
    './components/**/*.{js,ts,jsx,tsx}',
  ],
  // Purges unused classes in production
};
```

---

## Network Optimization

### Prefetching

```tsx
import Link from 'next/link';

// Next.js prefetches linked pages on hover
<Link href="/dashboard" prefetch={true}>
  Dashboard
</Link>

// Manual prefetch
import { useRouter } from 'next/navigation';

function NavItem() {
  const router = useRouter();

  return (
    <button
      onMouseEnter={() => router.prefetch('/dashboard')}
      onClick={() => router.push('/dashboard')}
    >
      Dashboard
    </button>
  );
}
```

### Resource Hints

```tsx
// app/layout.tsx
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html>
      <head>
        {/* Preconnect to external domains */}
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://api.example.com" />

        {/* DNS prefetch */}
        <link rel="dns-prefetch" href="https://cdn.example.com" />

        {/* Preload critical resources */}
        <link rel="preload" href="/fonts/main.woff2" as="font" type="font/woff2" crossOrigin="anonymous" />
      </head>
      <body>{children}</body>
    </html>
  );
}
```

### Caching Strategies

```tsx
// Next.js fetch with caching
async function getData() {
  // Static (cached forever)
  const res = await fetch('https://api.example.com/data', {
    cache: 'force-cache'
  });

  // Dynamic (no cache)
  const res = await fetch('https://api.example.com/data', {
    cache: 'no-store'
  });

  // Revalidate (time-based)
  const res = await fetch('https://api.example.com/data', {
    next: { revalidate: 60 } // Revalidate every 60 seconds
  });

  return res.json();
}
```

---

## Rendering Optimization

### Server Components (Next.js)

```tsx
// ✅ Server Component (default)
async function PostList() {
  const posts = await getPosts(); // Fetches on server

  return (
    <div>
      {posts.map(post => (
        <PostCard key={post.id} post={post} />
      ))}
    </div>
  );
}

// ✅ Client Component (when needed)
'use client';

import { useState } from 'react';

function InteractiveButton() {
  const [count, setCount] = useState(0);
  return <button onClick={() => setCount(count + 1)}>{count}</button>;
}
```

**Server Components benefits**:
- Zero JavaScript sent to client
- Direct database access
- Automatic code splitting

### Streaming and Suspense

```tsx
import { Suspense } from 'react';

export default function Page() {
  return (
    <div>
      <h1>Dashboard</h1>

      {/* Fast component renders immediately */}
      <UserGreeting />

      {/* Slow component streams in */}
      <Suspense fallback={<Spinner />}>
        <SlowAnalytics />
      </Suspense>

      <Suspense fallback={<Spinner />}>
        <SlowRecentOrders />
      </Suspense>
    </div>
  );
}
```

---

## Performance Monitoring

### Web Vitals Tracking

```tsx
// app/components/WebVitals.tsx
'use client';

import { useReportWebVitals } from 'next/web-vitals';

export function WebVitals() {
  useReportWebVitals((metric) => {
    console.log(metric);

    // Send to analytics
    fetch('/api/analytics', {
      method: 'POST',
      body: JSON.stringify(metric),
    });
  });

  return null;
}

// app/layout.tsx
import { WebVitals } from './components/WebVitals';

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html>
      <body>
        {children}
        <WebVitals />
      </body>
    </html>
  );
}
```

### Performance Profiling

```tsx
// React DevTools Profiler
import { Profiler } from 'react';

function onRenderCallback(
  id: string,
  phase: 'mount' | 'update',
  actualDuration: number,
  baseDuration: number,
  startTime: number,
  commitTime: number
) {
  console.log({ id, phase, actualDuration });
}

<Profiler id="Dashboard" onRender={onRenderCallback}>
  <Dashboard />
</Profiler>
```

### Browser Performance API

```tsx
// Measure custom metrics
performance.mark('data-fetch-start');
await fetchData();
performance.mark('data-fetch-end');

performance.measure('data-fetch', 'data-fetch-start', 'data-fetch-end');

const measure = performance.getEntriesByName('data-fetch')[0];
console.log('Fetch took:', measure.duration, 'ms');
```

---

## Font Optimization

### Next.js Font Optimization

```tsx
// app/layout.tsx
import { Inter, Roboto_Mono } from 'next/font/google';

const inter = Inter({
  subsets: ['latin'],
  display: 'swap',
  variable: '--font-inter',
});

const robotoMono = Roboto_Mono({
  subsets: ['latin'],
  display: 'swap',
  variable: '--font-roboto-mono',
});

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html className={`${inter.variable} ${robotoMono.variable}`}>
      <body>{children}</body>
    </html>
  );
}

// globals.css
body {
  font-family: var(--font-inter), sans-serif;
}

code {
  font-family: var(--font-roboto-mono), monospace;
}
```

**Benefits**:
- Self-hosted fonts (no external request)
- Automatic font subsetting
- Zero layout shift

### Font Loading Strategies

```css
/* font-display: swap - Show fallback, swap when loaded */
@font-face {
  font-family: 'CustomFont';
  src: url('/fonts/custom.woff2');
  font-display: swap;
}

/* font-display: optional - Use only if cached */
@font-face {
  font-family: 'OptionalFont';
  src: url('/fonts/optional.woff2');
  font-display: optional;
}
```

---

## Quick Reference

### Core Web Vitals Targets

```
LCP (Largest Contentful Paint): < 2.5s
FID (First Input Delay): < 100ms
CLS (Cumulative Layout Shift): < 0.1
INP (Interaction to Next Paint): < 200ms
```

### Optimization Checklist

```
[ ] Code splitting (route-based, component-based)
[ ] Image optimization (Next.js Image, WebP/AVIF)
[ ] Lazy loading (images, components)
[ ] Bundle size < 200KB (initial load)
[ ] Memoization (React.memo, useMemo, useCallback)
[ ] Virtual lists (for >100 items)
[ ] Remove unused code (tree shaking)
[ ] Prefetch linked pages
[ ] Resource hints (preconnect, dns-prefetch)
[ ] Font optimization (self-hosted, subsetting)
[ ] Critical CSS inlined
[ ] Streaming and Suspense
[ ] Server Components (where possible)
```

### Performance Tools

```
Chrome DevTools Lighthouse
WebPageTest
PageSpeed Insights
Next.js Bundle Analyzer
React DevTools Profiler
Web Vitals Chrome Extension
```

---

## Common Anti-Patterns

❌ **Large bundle sizes**: Split code, remove unused dependencies
✅ Analyze and optimize bundle

❌ **Unoptimized images**: Use Next.js Image component
✅ Automatic optimization

❌ **Blocking scripts**: Use async/defer or move to end of body
✅ Non-blocking script loading

❌ **No lazy loading**: Load everything upfront
✅ Lazy load non-critical content

❌ **Premature optimization**: Optimize without measuring
✅ Profile first, then optimize

---

## Related Skills

- `react-component-patterns.md` - Memoization, code splitting
- `nextjs-app-router.md` - Server Components, streaming
- `react-data-fetching.md` - Caching, prefetching
- `web-accessibility.md` - Performance affects accessibility

---

**Last Updated**: 2025-10-18
**Format Version**: 1.0 (Atomic)
