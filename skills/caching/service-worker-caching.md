---
name: caching-service-worker-caching
description: Progressive Web App (PWA) caching with Service Workers - offline-first architecture, caching strategies, Workbox patterns, and modern browser caching.
---
# Service Worker Caching

**Last Updated**: 2025-10-25

## When to Use This Skill

Use this skill when:
- Building Progressive Web Apps (PWAs) with offline support
- Implementing client-side caching for web applications
- Creating offline-first or resilient web experiences
- Reducing server load with aggressive client caching
- Improving performance on slow or unreliable networks
- Building installable web apps with native-like experiences

**Browser Support (2025)**: Chrome, Edge, Safari, Firefox (95%+ global coverage)

**Prerequisites**: Understanding of `http-caching.md` (HTTP caching headers complement Service Workers)

## Core Concepts

### Service Worker Overview

A **Service Worker** is a JavaScript file that runs in the background, separate from the web page:
- Intercepts network requests (acts as a programmable proxy)
- Manages a cache storage independent of HTTP cache
- Enables offline functionality
- Runs on a separate thread (doesn't block UI)

**Key difference from HTTP cache**: Service Worker cache is programmatic - you control every aspect of caching logic.

### Service Worker Lifecycle

```
Install → Activate → Fetch (intercept requests)
```

```javascript
// service-worker.js - Lifecycle events

const CACHE_VERSION = 'v1';
const CACHE_NAME = `app-cache-${CACHE_VERSION}`;

// 1. INSTALL: Cache initial resources
self.addEventListener('install', (event) => {
  console.log('[SW] Installing service worker...');

  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      console.log('[SW] Caching app shell');
      return cache.addAll([
        '/',
        '/index.html',
        '/styles/main.css',
        '/scripts/app.js',
        '/images/logo.png',
      ]);
    })
  );

  // Force new service worker to activate immediately
  self.skipWaiting();
});

// 2. ACTIVATE: Clean up old caches
self.addEventListener('activate', (event) => {
  console.log('[SW] Activating service worker...');

  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames
          .filter((name) => name !== CACHE_NAME)
          .map((name) => {
            console.log(`[SW] Deleting old cache: ${name}`);
            return caches.delete(name);
          })
      );
    })
  );

  // Take control of all pages immediately
  return self.clients.claim();
});

// 3. FETCH: Intercept network requests
self.addEventListener('fetch', (event) => {
  console.log(`[SW] Fetching: ${event.request.url}`);
  // Caching strategy goes here (see below)
});
```

### Registering Service Worker

```javascript
// main.js - Register service worker from main page

if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker
      .register('/service-worker.js')
      .then((registration) => {
        console.log('SW registered:', registration.scope);

        // Listen for updates
        registration.addEventListener('updatefound', () => {
          const newWorker = registration.installing;
          console.log('New service worker found, installing...');

          newWorker.addEventListener('statechange', () => {
            if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
              // New version available
              console.log('New version available! Reload to update.');
              showUpdateNotification();
            }
          });
        });
      })
      .catch((error) => {
        console.error('SW registration failed:', error);
      });
  });
}

function showUpdateNotification() {
  // Notify user of available update
  if (confirm('New version available! Reload to update?')) {
    window.location.reload();
  }
}
```

## Caching Strategies

### 1. Cache First (Cache Falling Back to Network)

**Best for**: Static assets (JS, CSS, images) that rarely change.

```javascript
// Strategy: Try cache first, fallback to network
self.addEventListener('fetch', (event) => {
  event.respondWith(
    caches.match(event.request).then((cachedResponse) => {
      if (cachedResponse) {
        console.log(`[SW] Cache hit: ${event.request.url}`);
        return cachedResponse;
      }

      console.log(`[SW] Cache miss, fetching: ${event.request.url}`);
      return fetch(event.request).then((networkResponse) => {
        // Cache the fetched response for future use
        return caches.open(CACHE_NAME).then((cache) => {
          cache.put(event.request, networkResponse.clone());
          return networkResponse;
        });
      });
    })
  );
});
```

### 2. Network First (Network Falling Back to Cache)

**Best for**: Dynamic content (API responses) where freshness is important.

```javascript
// Strategy: Try network first, fallback to cache if offline
function networkFirst(request) {
  return fetch(request)
    .then((networkResponse) => {
      // Update cache with fresh response
      caches.open(CACHE_NAME).then((cache) => {
        cache.put(request, networkResponse.clone());
      });
      return networkResponse;
    })
    .catch(() => {
      // Network failed, try cache
      console.log(`[SW] Network failed, using cache: ${request.url}`);
      return caches.match(request);
    });
}

self.addEventListener('fetch', (event) => {
  if (event.request.url.includes('/api/')) {
    event.respondWith(networkFirst(event.request));
  }
});
```

### 3. Stale-While-Revalidate

**Best for**: Balancing freshness and performance - serve cached, update in background.

```javascript
// Strategy: Serve from cache, fetch fresh copy in background
function staleWhileRevalidate(request) {
  return caches.open(CACHE_NAME).then((cache) => {
    return cache.match(request).then((cachedResponse) => {
      // Fetch fresh copy in background
      const fetchPromise = fetch(request).then((networkResponse) => {
        cache.put(request, networkResponse.clone());
        return networkResponse;
      });

      // Return cached response immediately, or wait for network
      return cachedResponse || fetchPromise;
    });
  });
}

self.addEventListener('fetch', (event) => {
  // Use for semi-dynamic content
  if (event.request.url.includes('/articles/')) {
    event.respondWith(staleWhileRevalidate(event.request));
  }
});
```

### 4. Network Only

**Best for**: POST requests, analytics, real-time data.

```javascript
// Strategy: Always use network, never cache
self.addEventListener('fetch', (event) => {
  if (event.request.method === 'POST') {
    event.respondWith(fetch(event.request));
  }
});
```

### 5. Cache Only

**Best for**: App shell that's guaranteed to be cached.

```javascript
// Strategy: Only serve from cache
self.addEventListener('fetch', (event) => {
  if (event.request.url.includes('/app-shell/')) {
    event.respondWith(caches.match(event.request));
  }
});
```

## Workbox Library (Google's Service Worker Framework)

**Workbox** simplifies Service Worker development with pre-built strategies.

### Basic Workbox Setup

```javascript
// service-worker.js - Using Workbox
importScripts('https://storage.googleapis.com/workbox-cdn/releases/7.0.0/workbox-sw.js');

const { registerRoute } = workbox.routing;
const { CacheFirst, NetworkFirst, StaleWhileRevalidate } = workbox.strategies;
const { CacheableResponsePlugin } = workbox.cacheableResponse;
const { ExpirationPlugin } = workbox.expiration;

// Cache page navigations (HTML) with Network First
registerRoute(
  ({ request }) => request.mode === 'navigate',
  new NetworkFirst({
    cacheName: 'pages',
    plugins: [
      new CacheableResponsePlugin({
        statuses: [0, 200],
      }),
    ],
  })
);

// Cache CSS, JS, and Web Worker requests with Stale While Revalidate
registerRoute(
  ({ request }) =>
    request.destination === 'style' ||
    request.destination === 'script' ||
    request.destination === 'worker',
  new StaleWhileRevalidate({
    cacheName: 'assets',
    plugins: [
      new CacheableResponsePlugin({
        statuses: [0, 200],
      }),
    ],
  })
);

// Cache images with Cache First and expiration
registerRoute(
  ({ request }) => request.destination === 'image',
  new CacheFirst({
    cacheName: 'images',
    plugins: [
      new CacheableResponsePlugin({
        statuses: [0, 200],
      }),
      new ExpirationPlugin({
        maxEntries: 60,
        maxAgeSeconds: 30 * 24 * 60 * 60, // 30 Days
      }),
    ],
  })
);

// Cache Google Fonts
registerRoute(
  ({ url }) => url.origin === 'https://fonts.googleapis.com',
  new StaleWhileRevalidate({
    cacheName: 'google-fonts-stylesheets',
  })
);

registerRoute(
  ({ url }) => url.origin === 'https://fonts.gstatic.com',
  new CacheFirst({
    cacheName: 'google-fonts-webfonts',
    plugins: [
      new CacheableResponsePlugin({
        statuses: [0, 200],
      }),
      new ExpirationPlugin({
        maxAgeSeconds: 60 * 60 * 24 * 365, // 1 year
        maxEntries: 30,
      }),
    ],
  })
);
```

### Workbox with Build Tools (Vite/Webpack)

```javascript
// vite.config.js - Workbox with Vite PWA Plugin
import { defineConfig } from 'vite';
import { VitePWA } from 'vite-plugin-pwa';

export default defineConfig({
  plugins: [
    VitePWA({
      registerType: 'autoUpdate',
      workbox: {
        globPatterns: ['**/*.{js,css,html,ico,png,svg}'],
        runtimeCaching: [
          {
            urlPattern: /^https:\/\/api\.example\.com\/.*/i,
            handler: 'NetworkFirst',
            options: {
              cacheName: 'api-cache',
              expiration: {
                maxEntries: 100,
                maxAgeSeconds: 60 * 60, // 1 hour
              },
              cacheableResponse: {
                statuses: [0, 200],
              },
            },
          },
        ],
      },
    }),
  ],
});
```

## Offline-First Architecture

### Offline Page Fallback

```javascript
// service-worker.js - Show offline page when network fails

const OFFLINE_PAGE = '/offline.html';

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.add(OFFLINE_PAGE);
    })
  );
});

self.addEventListener('fetch', (event) => {
  if (event.request.mode === 'navigate') {
    event.respondWith(
      fetch(event.request).catch(() => {
        return caches.match(OFFLINE_PAGE);
      })
    );
  }
});
```

### Background Sync for Failed Requests

**Queue failed requests, retry when online**.

```javascript
// service-worker.js - Background Sync API

self.addEventListener('sync', (event) => {
  if (event.tag === 'sync-posts') {
    event.waitUntil(syncPendingPosts());
  }
});

async function syncPendingPosts() {
  const cache = await caches.open('pending-posts');
  const requests = await cache.keys();

  return Promise.all(
    requests.map(async (request) => {
      try {
        const response = await fetch(request.clone());
        if (response.ok) {
          await cache.delete(request);
          console.log('Synced pending post:', request.url);
        }
      } catch (error) {
        console.error('Sync failed:', error);
      }
    })
  );
}

// main.js - Queue post when offline
async function submitPost(data) {
  try {
    const response = await fetch('/api/posts', {
      method: 'POST',
      body: JSON.stringify(data),
      headers: { 'Content-Type': 'application/json' },
    });
    return response;
  } catch (error) {
    // Offline - queue for background sync
    const cache = await caches.open('pending-posts');
    await cache.put(
      new Request('/api/posts', {
        method: 'POST',
        body: JSON.stringify(data),
      })
    );

    // Register sync event
    const registration = await navigator.serviceWorker.ready;
    await registration.sync.register('sync-posts');
    console.log('Post queued for background sync');
  }
}
```

## Cache Versioning and Migration

### Versioned Caches

```javascript
const CACHE_VERSION = 'v2';
const CACHE_NAME = `app-cache-${CACHE_VERSION}`;

// Activate: Delete old versions
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames
          .filter((name) => name.startsWith('app-cache-') && name !== CACHE_NAME)
          .map((name) => caches.delete(name))
      );
    })
  );
});
```

### Migration Between Versions

```javascript
// service-worker.js - Migrate cache data between versions

self.addEventListener('activate', (event) => {
  event.waitUntil(
    (async () => {
      const oldCacheName = 'app-cache-v1';
      const newCacheName = 'app-cache-v2';

      if (await caches.has(oldCacheName)) {
        const oldCache = await caches.open(oldCacheName);
        const newCache = await caches.open(newCacheName);

        // Migrate specific entries
        const requests = await oldCache.keys();
        for (const request of requests) {
          // Only migrate static assets
          if (request.url.includes('/static/')) {
            const response = await oldCache.match(request);
            await newCache.put(request, response);
          }
        }

        // Delete old cache
        await caches.delete(oldCacheName);
        console.log('Cache migrated from v1 to v2');
      }
    })()
  );
});
```

## Advanced Patterns

### Conditional Caching

```javascript
// Cache only successful GET requests
self.addEventListener('fetch', (event) => {
  if (event.request.method !== 'GET') {
    return; // Don't cache POST/PUT/DELETE
  }

  event.respondWith(
    caches.match(event.request).then((cached) => {
      return (
        cached ||
        fetch(event.request).then((response) => {
          // Only cache successful responses
          if (response.status === 200) {
            const responseClone = response.clone();
            caches.open(CACHE_NAME).then((cache) => {
              cache.put(event.request, responseClone);
            });
          }
          return response;
        })
      );
    })
  );
});
```

### Cache with Timeout

```javascript
// Network with timeout fallback
function fetchWithTimeout(request, timeout = 3000) {
  return Promise.race([
    fetch(request),
    new Promise((_, reject) =>
      setTimeout(() => reject(new Error('Network timeout')), timeout)
    ),
  ]);
}

self.addEventListener('fetch', (event) => {
  event.respondWith(
    fetchWithTimeout(event.request, 2000)
      .catch(() => caches.match(event.request))
      .catch(() => caches.match('/offline.html'))
  );
});
```

## Debugging Service Workers

### Chrome DevTools

```javascript
// service-worker.js - Debug logging

const DEBUG = true;

function log(...args) {
  if (DEBUG) {
    console.log('[SW]', ...args);
  }
}

self.addEventListener('fetch', (event) => {
  log('Fetch:', event.request.url);
  log('Cache strategy:', getStrategy(event.request.url));
});
```

**Chrome DevTools**:
1. Open DevTools → Application tab → Service Workers
2. Check "Update on reload" for development
3. "Unregister" to remove service worker
4. "Bypass for network" to disable temporarily
5. Application → Cache Storage to inspect cached data

### Force Update

```javascript
// main.js - Force service worker update

navigator.serviceWorker.register('/service-worker.js').then((registration) => {
  // Check for updates every hour
  setInterval(() => {
    registration.update();
  }, 60 * 60 * 1000);
});

// Manually trigger update
document.getElementById('update-btn').addEventListener('click', () => {
  navigator.serviceWorker.ready.then((registration) => {
    registration.update();
  });
});
```

## Anti-Patterns

### ❌ Caching Everything

```javascript
// WRONG: Cache all requests indiscriminately
self.addEventListener('fetch', (event) => {
  event.respondWith(caches.match(event.request) || fetch(event.request));
  // Problem: Caches POST requests, analytics, user-specific data
});

// CORRECT: Selective caching
if (event.request.method === 'GET' && !event.request.url.includes('/api/user')) {
  // Cache only appropriate requests
}
```

### ❌ Not Versioning Caches

```javascript
// WRONG: Same cache name forever
const CACHE_NAME = 'app-cache'; // Never changes

// CORRECT: Version your caches
const CACHE_VERSION = 'v2';
const CACHE_NAME = `app-cache-${CACHE_VERSION}`;
```

### ❌ Forgetting to Clean Up

```javascript
// WRONG: No activation cleanup
// Old caches accumulate, waste storage

// CORRECT: Delete old caches on activate
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((names) =>
      Promise.all(names.filter((n) => n !== CACHE_NAME).map((n) => caches.delete(n)))
    )
  );
});
```

## Quick Reference

**Caching Strategy Selection**:
```
Static assets (JS/CSS/images) → Cache First
API responses → Network First
Semi-dynamic content → Stale While Revalidate
Real-time data / POST requests → Network Only
App shell → Cache Only
```

**Cache Size Limits** (2025):
- Chrome: ~60% of free disk space
- Safari: 50MB soft limit, up to 1GB with user permission
- Firefox: Up to 50% of free disk space

**Service Worker Lifecycle**:
1. Register → `navigator.serviceWorker.register()`
2. Install → `self.addEventListener('install')`
3. Activate → `self.addEventListener('activate')`
4. Fetch → `self.addEventListener('fetch')`

**Workbox Strategies**:
- `CacheFirst`: Static assets
- `NetworkFirst`: Dynamic content
- `StaleWhileRevalidate`: Balance freshness/performance
- `NetworkOnly`: Real-time data
- `CacheOnly`: Guaranteed cached content

## Related Skills

- `http-caching.md` - HTTP caching headers (complement Service Workers)
- `frontend-performance.md` - Overall frontend performance optimization
- `web-accessibility.md` - Ensure offline pages are accessible
- `cache-invalidation-strategies.md` - Cache versioning strategies

## Summary

Service Workers provide powerful client-side caching for Progressive Web Apps:

**Key Takeaways**:
1. **Service Workers ≠ HTTP Cache** - They complement each other
2. **Choose the right strategy** - Cache First for static, Network First for dynamic
3. **Use Workbox for production** - Handles edge cases and best practices
4. **Version your caches** - Clean up old caches on activation
5. **Offline-first thinking** - Plan for network failures
6. **Background Sync** - Queue failed requests for retry when online
7. **Debug thoroughly** - Service Workers can cause hard-to-debug issues

Service Workers enable resilient, performant web applications that work offline. Combined with HTTP caching and CDN edge caching, they form a complete caching strategy from browser to origin server.
