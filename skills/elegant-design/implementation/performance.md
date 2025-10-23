# Performance Optimization

Fast interfaces feel better. Optimize from the start.

## Core Web Vitals

Target metrics:
- **LCP** (Largest Contentful Paint): < 2.5s
- **FID** (First Input Delay): < 100ms
- **CLS** (Cumulative Layout Shift): < 0.1
- **INP** (Interaction to Next Paint): < 200ms

## Optimization Strategies

### 1. Code Splitting

Split at route level:

```typescript
// Next.js
import dynamic from 'next/dynamic';

const DashboardWidget = dynamic(() => import('./DashboardWidget'), {
  loading: () => <Skeleton />,
});

// React Router
const Dashboard = lazy(() => import('./pages/Dashboard'));
```

### 2. Lazy Loading

Defer non-critical components:

```typescript
import { lazy, Suspense } from 'react';

const HeavyChart = lazy(() => import('./HeavyChart'));

function Analytics() {
  return (
    <Suspense fallback={<Skeleton />}>
      <HeavyChart data={data} />
    </Suspense>
  );
}
```

### 3. Image Optimization

```tsx
// Next.js Image component
import Image from 'next/image';

<Image
  src="/image.jpg"
  alt="Description"
  width={800}
  height={600}
  loading="lazy"
  placeholder="blur"
/>

// Native responsive images
<img
  src="image.jpg"
  srcSet="image-400.jpg 400w, image-800.jpg 800w"
  sizes="(max-width: 640px) 100vw, 50vw"
  alt="Description"
  loading="lazy"
/>
```

### 4. Animation Performance

Animate only transform and opacity:

```css
/* Good - uses GPU */
.element {
  transition: transform 0.2s, opacity 0.2s;
}

.element:hover {
  transform: scale(1.05);
  opacity: 0.8;
}

/* Bad - triggers layout/paint */
.element {
  transition: width 0.2s, height 0.2s, top 0.2s;
}
```

### 5. Bundle Size

```bash
# Analyze bundle
npm run build -- --analyze

# Remove unused code
npm install -D webpack-bundle-analyzer
```

**Techniques:**
- Tree shaking (remove unused exports)
- Dynamic imports
- Code splitting
- Remove duplicate dependencies

### 6. Preloading Critical Resources

```html
<!-- Preload critical fonts -->
<link rel="preload" href="/fonts/geist.woff2" as="font" type="font/woff2" crossorigin>

<!-- Preconnect to external domains -->
<link rel="preconnect" href="https://api.example.com">

<!-- Prefetch next page -->
<link rel="prefetch" href="/dashboard">
```

## Best Practices

### Do:
- ✅ Lazy load below-the-fold content
- ✅ Code split at route boundaries
- ✅ Optimize images (WebP, AVIF)
- ✅ Animate with transform and opacity
- ✅ Minimize JavaScript bundle size
- ✅ Use React.memo for expensive components
- ✅ Debounce expensive operations
- ✅ Measure with Lighthouse

### Don't:
- ❌ Load all JavaScript upfront
- ❌ Animate width, height, top, left
- ❌ Serve unoptimized images
- ❌ Block rendering with large bundles
- ❌ Forget to measure performance
- ❌ Use blocking third-party scripts
