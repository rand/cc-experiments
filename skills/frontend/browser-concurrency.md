---
name: frontend-browser-concurrency
description: Service Workers, SharedWorkers, Worklets, and multi-threading patterns for advanced browser concurrency
---

# Browser Concurrency

**Scope**: Service Workers, SharedWorkers, Worklets, OffscreenCanvas, multi-threading patterns, concurrent JavaScript
**Lines**: ~400
**Last Updated**: 2025-10-27

## When to Use This Skill

Activate this skill when:
- Implementing offline functionality and PWAs
- Building shared worker pools across tabs
- Creating audio/animation worklets
- Managing background sync and push notifications
- Implementing advanced caching strategies
- Building real-time collaborative applications
- Need coordination between multiple browser contexts

---

## Core Concepts

### Browser Concurrency Model

**Thread Types**:

1. **Main Thread** - UI rendering, DOM manipulation
2. **Web Workers** - Dedicated background threads (see `web-workers.md`)
3. **Service Workers** - Network proxy, offline support, background sync
4. **SharedWorkers** - Shared thread across multiple tabs/windows
5. **Worklets** - Lightweight workers for rendering pipeline (Audio, Paint, Animation)

**Context Types**:
- **Window** - Main browser tab context
- **Worker** - Dedicated worker global scope
- **ServiceWorkerGlobalScope** - Service worker context
- **SharedWorkerGlobalScope** - Shared worker context
- **WorkletGlobalScope** - Worklet context

---

## Service Workers

### PWA and Offline Support

**Lifecycle**: Install → Activate → Fetch

**service-worker.ts**:
```typescript
/// <reference lib="webworker" />

declare const self: ServiceWorkerGlobalScope;

const CACHE_NAME = 'app-cache-v1';
const ASSETS = [
  '/',
  '/index.html',
  '/styles.css',
  '/app.js',
  '/manifest.json'
];

// Install: Cache assets
self.addEventListener('install', (event: ExtendableEvent) => {
  console.log('[SW] Installing...');

  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      console.log('[SW] Caching assets');
      return cache.addAll(ASSETS);
    })
  );

  // Take control immediately
  self.skipWaiting();
});

// Activate: Clean old caches
self.addEventListener('activate', (event: ExtendableEvent) => {
  console.log('[SW] Activating...');

  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames
          .filter((name) => name !== CACHE_NAME)
          .map((name) => caches.delete(name))
      );
    })
  );

  // Take control of all clients
  self.clients.claim();
});

// Fetch: Cache-first strategy
self.addEventListener('fetch', (event: FetchEvent) => {
  const { request } = event;

  event.respondWith(
    caches.match(request).then((cached) => {
      if (cached) {
        console.log('[SW] Cache hit:', request.url);
        return cached;
      }

      console.log('[SW] Fetching:', request.url);
      return fetch(request).then((response) => {
        // Cache successful responses
        if (response.ok) {
          const clone = response.clone();
          caches.open(CACHE_NAME).then((cache) => {
            cache.put(request, clone);
          });
        }

        return response;
      });
    })
  );
});
```

**Register service worker**:
```typescript
// main.ts
async function registerServiceWorker(): Promise<ServiceWorkerRegistration | null> {
  if ('serviceWorker' in navigator) {
    try {
      const registration = await navigator.serviceWorker.register('/sw.js', {
        scope: '/'
      });

      console.log('SW registered:', registration.scope);

      // Listen for updates
      registration.addEventListener('updatefound', () => {
        const newWorker = registration.installing;
        console.log('SW update found');

        newWorker?.addEventListener('statechange', () => {
          if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
            // New version available
            console.log('New SW installed, please reload');
          }
        });
      });

      return registration;
    } catch (error) {
      console.error('SW registration failed:', error);
      return null;
    }
  }

  return null;
}

// Initialize
registerServiceWorker();
```

---

## Caching Strategies

### 1. Cache First (Offline-First)

```typescript
self.addEventListener('fetch', (event: FetchEvent) => {
  event.respondWith(
    caches.match(event.request).then((cached) => {
      return cached || fetch(event.request);
    })
  );
});
```

### 2. Network First (Fresh Content Priority)

```typescript
self.addEventListener('fetch', (event: FetchEvent) => {
  event.respondWith(
    fetch(event.request)
      .then((response) => {
        // Cache successful response
        const clone = response.clone();
        caches.open(CACHE_NAME).then((cache) => {
          cache.put(event.request, clone);
        });
        return response;
      })
      .catch(() => {
        // Fallback to cache on network failure
        return caches.match(event.request);
      })
  );
});
```

### 3. Stale-While-Revalidate

```typescript
self.addEventListener('fetch', (event: FetchEvent) => {
  event.respondWith(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.match(event.request).then((cached) => {
        const fetchPromise = fetch(event.request).then((response) => {
          cache.put(event.request, response.clone());
          return response;
        });

        // Return cached immediately, update in background
        return cached || fetchPromise;
      });
    })
  );
});
```

### 4. Cache with Network Fallback and Timeout

```typescript
async function fetchWithTimeout(
  request: Request,
  timeout: number = 3000
): Promise<Response> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeout);

  try {
    const response = await fetch(request, { signal: controller.signal });
    clearTimeout(timeoutId);
    return response;
  } catch (error) {
    clearTimeout(timeoutId);
    throw error;
  }
}

self.addEventListener('fetch', (event: FetchEvent) => {
  event.respondWith(
    caches.match(event.request).then((cached) => {
      if (cached) return cached;

      return fetchWithTimeout(event.request, 3000).catch(() => {
        return new Response('Offline', { status: 503 });
      });
    })
  );
});
```

---

## Background Sync

### Reliable Network Requests

**service-worker.ts**:
```typescript
// Register sync event
self.addEventListener('sync', (event: SyncEvent) => {
  if (event.tag === 'sync-messages') {
    event.waitUntil(syncMessages());
  }
});

async function syncMessages(): Promise<void> {
  const cache = await caches.open('pending-requests');
  const requests = await cache.keys();

  for (const request of requests) {
    try {
      const response = await fetch(request);
      if (response.ok) {
        await cache.delete(request);
        console.log('Synced:', request.url);
      }
    } catch (error) {
      console.error('Sync failed:', error);
    }
  }
}
```

**Client-side request**:
```typescript
async function sendMessage(message: string): Promise<void> {
  try {
    const response = await fetch('/api/messages', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message })
    });

    if (!response.ok) throw new Error('Network error');
  } catch (error) {
    // Save for background sync
    const cache = await caches.open('pending-requests');
    await cache.put(
      new Request('/api/messages', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message })
      }),
      new Response()
    );

    // Register sync
    const registration = await navigator.serviceWorker.ready;
    await registration.sync.register('sync-messages');
  }
}
```

---

## Push Notifications

### Real-Time Updates

**service-worker.ts**:
```typescript
// Listen for push events
self.addEventListener('push', (event: PushEvent) => {
  const data = event.data?.json() ?? { title: 'Notification', body: 'New message' };

  event.waitUntil(
    self.registration.showNotification(data.title, {
      body: data.body,
      icon: '/icon.png',
      badge: '/badge.png',
      tag: 'notification-1',
      requireInteraction: false,
      actions: [
        { action: 'open', title: 'Open' },
        { action: 'close', title: 'Close' }
      ]
    })
  );
});

// Handle notification clicks
self.addEventListener('notificationclick', (event: NotificationEvent) => {
  event.notification.close();

  if (event.action === 'open') {
    event.waitUntil(
      self.clients.openWindow('/')
    );
  }
});
```

**Subscribe to push**:
```typescript
async function subscribeToPush(): Promise<PushSubscription | null> {
  const registration = await navigator.serviceWorker.ready;

  try {
    const subscription = await registration.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: urlBase64ToUint8Array(PUBLIC_VAPID_KEY)
    });

    // Send subscription to server
    await fetch('/api/push/subscribe', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(subscription)
    });

    return subscription;
  } catch (error) {
    console.error('Push subscription failed:', error);
    return null;
  }
}

function urlBase64ToUint8Array(base64String: string): Uint8Array {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
  const rawData = window.atob(base64);
  return Uint8Array.from([...rawData].map((char) => char.charCodeAt(0)));
}
```

---

## SharedWorkers

### Cross-Tab Communication

**shared-worker.ts**:
```typescript
/// <reference lib="webworker" />

declare const self: SharedWorkerGlobalScope;

// Track all connected ports
const ports = new Set<MessagePort>();
let sharedState = { count: 0, users: [] as string[] };

self.addEventListener('connect', (event: MessageEvent) => {
  const port = event.ports[0];
  ports.add(port);

  console.log('Client connected. Total:', ports.size);

  // Send current state to new client
  port.postMessage({
    type: 'STATE',
    payload: sharedState
  });

  port.addEventListener('message', (e: MessageEvent) => {
    const { type, payload } = e.data;

    switch (type) {
      case 'INCREMENT':
        sharedState.count++;
        broadcast({ type: 'STATE', payload: sharedState });
        break;

      case 'ADD_USER':
        sharedState.users.push(payload);
        broadcast({ type: 'STATE', payload: sharedState });
        break;

      case 'RESET':
        sharedState = { count: 0, users: [] };
        broadcast({ type: 'STATE', payload: sharedState });
        break;
    }
  });

  port.start();
});

function broadcast(message: any): void {
  ports.forEach((port) => {
    port.postMessage(message);
  });
}
```

**Client usage**:
```typescript
const sharedWorker = new SharedWorker(
  new URL('./shared-worker.ts', import.meta.url),
  { type: 'module' }
);

sharedWorker.port.addEventListener('message', (event: MessageEvent) => {
  const { type, payload } = event.data;

  if (type === 'STATE') {
    console.log('Shared state:', payload);
    updateUI(payload);
  }
});

sharedWorker.port.start();

// Send messages
function increment(): void {
  sharedWorker.port.postMessage({ type: 'INCREMENT' });
}

function addUser(name: string): void {
  sharedWorker.port.postMessage({ type: 'ADD_USER', payload: name });
}
```

---

## React Integration with SharedWorker

**useSharedWorker.ts**:
```typescript
import { useEffect, useState, useRef } from 'react';

export function useSharedWorker<T>(workerUrl: string) {
  const [state, setState] = useState<T | null>(null);
  const workerRef = useRef<SharedWorker | null>(null);

  useEffect(() => {
    const worker = new SharedWorker(new URL(workerUrl, import.meta.url), {
      type: 'module'
    });
    workerRef.current = worker;

    worker.port.addEventListener('message', (event: MessageEvent) => {
      const { type, payload } = event.data;

      if (type === 'STATE') {
        setState(payload);
      }
    });

    worker.port.start();

    return () => {
      worker.port.close();
    };
  }, [workerUrl]);

  const postMessage = (message: any) => {
    if (workerRef.current) {
      workerRef.current.port.postMessage(message);
    }
  };

  return { state, postMessage };
}
```

**Component**:
```typescript
function SharedCounter() {
  const { state, postMessage } = useSharedWorker<{ count: number }>('./shared-worker.ts');

  return (
    <div>
      <p>Count (shared across tabs): {state?.count ?? 0}</p>
      <button onClick={() => postMessage({ type: 'INCREMENT' })}>
        Increment
      </button>
    </div>
  );
}
```

---

## Worklets

### Audio Worklet (High-Performance Audio)

**audio-processor.ts**:
```typescript
/// <reference lib="webworker" />

class WhiteNoiseProcessor extends AudioWorkletProcessor {
  process(
    inputs: Float32Array[][],
    outputs: Float32Array[][],
    parameters: Record<string, Float32Array>
  ): boolean {
    const output = outputs[0];

    for (let channel = 0; channel < output.length; channel++) {
      const outputChannel = output[channel];

      for (let i = 0; i < outputChannel.length; i++) {
        // Generate white noise
        outputChannel[i] = Math.random() * 2 - 1;
      }
    }

    // Return true to keep processor alive
    return true;
  }
}

registerProcessor('white-noise-processor', WhiteNoiseProcessor);
```

**Using the worklet**:
```typescript
async function playWhiteNoise(): Promise<void> {
  const audioContext = new AudioContext();

  // Load worklet module
  await audioContext.audioWorklet.addModule('./audio-processor.ts');

  // Create worklet node
  const whiteNoiseNode = new AudioWorkletNode(audioContext, 'white-noise-processor');

  // Connect to destination
  whiteNoiseNode.connect(audioContext.destination);

  // Start playback
  await audioContext.resume();
}
```

---

## OffscreenCanvas

### Rendering in Workers

**canvas-worker.ts**:
```typescript
self.addEventListener('message', (event: MessageEvent) => {
  const { type, canvas } = event.data;

  if (type === 'INIT' && canvas instanceof OffscreenCanvas) {
    const ctx = canvas.getContext('2d')!;
    let frame = 0;

    function animate(): void {
      // Clear canvas
      ctx.fillStyle = 'black';
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      // Draw animation
      ctx.fillStyle = 'white';
      ctx.beginPath();
      ctx.arc(
        canvas.width / 2 + Math.cos(frame / 50) * 100,
        canvas.height / 2 + Math.sin(frame / 50) * 100,
        20,
        0,
        Math.PI * 2
      );
      ctx.fill();

      frame++;
      requestAnimationFrame(animate);
    }

    animate();
  }
});
```

**Main thread**:
```typescript
const canvas = document.getElementById('canvas') as HTMLCanvasElement;
const offscreen = canvas.transferControlToOffscreen();

const worker = new Worker(new URL('./canvas-worker.ts', import.meta.url), {
  type: 'module'
});

worker.postMessage({ type: 'INIT', canvas: offscreen }, [offscreen]);
```

---

## Communication Patterns

### 1. Broadcast Channel (Cross-Tab)

```typescript
// Create channel
const channel = new BroadcastChannel('app-channel');

// Listen for messages
channel.addEventListener('message', (event: MessageEvent) => {
  console.log('Received:', event.data);
  updateUI(event.data);
});

// Send message to all tabs
channel.postMessage({ type: 'UPDATE', payload: { count: 42 } });

// Cleanup
channel.close();
```

### 2. MessageChannel (Point-to-Point)

```typescript
// Create channel
const channel = new MessageChannel();

// Send port to worker
worker.postMessage({ port: channel.port2 }, [channel.port2]);

// Communicate through port
channel.port1.addEventListener('message', (event: MessageEvent) => {
  console.log('Response:', event.data);
});

channel.port1.start();
channel.port1.postMessage({ type: 'REQUEST', payload: 'data' });
```

---

## Performance Considerations

### Worker Overhead

**Creation cost**:
- Web Worker: ~5-10ms
- Service Worker: ~10-20ms (first activation)
- SharedWorker: ~10-15ms
- Worklet: ~1-5ms

**Message passing cost**:
- Simple object: <1ms
- Large object (1MB): 5-20ms
- Transferable (1MB): <1ms

**Best Practices**:
- Reuse workers (don't create per-task)
- Use transferable objects for large data
- Batch messages when possible
- Use SharedWorker for cross-tab state
- Use Worklets for real-time audio/animation

---

## Anti-Patterns

**Bad: Creating service worker per request**
```typescript
❌ async function fetchData() {
  await navigator.serviceWorker.register('/sw.js');
  return fetch('/api/data');
}
```

**Good: Register once at app start**
```typescript
✅ // Register on app initialization
navigator.serviceWorker.register('/sw.js');

// Use normally
async function fetchData() {
  return fetch('/api/data'); // Service worker intercepts
}
```

**Bad: SharedWorker without cleanup**
```typescript
❌ const worker = new SharedWorker('./worker.js');
// Never closed, leaks resources
```

**Good: Cleanup on unmount**
```typescript
✅ useEffect(() => {
  const worker = new SharedWorker('./worker.js');
  worker.port.start();

  return () => {
    worker.port.close(); // Cleanup
  };
}, []);
```

---

## Browser Compatibility

| Feature | Chrome | Firefox | Safari | Edge |
|---------|--------|---------|--------|------|
| Service Workers | 40+ | 44+ | 11.1+ | 17+ |
| SharedWorkers | 4+ | 29+ | 16.4+ | 79+ |
| BroadcastChannel | 54+ | 38+ | 15.4+ | 79+ |
| Audio Worklet | 66+ | 76+ | 14.1+ | 79+ |
| OffscreenCanvas | 69+ | 105+ | 16.4+ | 79+ |
| Background Sync | 49+ | ❌ | ❌ | 79+ |
| Push API | 50+ | 44+ | 16.4+ | 79+ |

---

## Related Skills

- **web-workers.md** - Dedicated Web Workers fundamentals
- **frontend-performance.md** - Overall performance optimization
- **react-state-management.md** - State management patterns
- **nextjs-app-router.md** - Next.js PWA configuration

---

## Summary

Browser concurrency enables powerful multi-threaded web applications:

**Key Takeaways**:
- Service Workers for offline support and PWAs
- SharedWorkers for cross-tab state sharing
- Worklets for real-time audio/animation
- BroadcastChannel for simple cross-tab messaging
- Choose the right worker type for your use case
- Handle lifecycle and cleanup properly
- Test across browsers for compatibility

**Decision Tree**:
- **Offline/PWA** → Service Worker
- **Cross-tab state** → SharedWorker or BroadcastChannel
- **CPU-intensive** → Web Worker (see web-workers.md)
- **Audio processing** → Audio Worklet
- **Canvas in background** → OffscreenCanvas + Web Worker
- **Simple messaging** → BroadcastChannel
