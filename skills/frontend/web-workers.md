---
name: frontend-web-workers
description: Offloading computation with Web Workers API, SharedArrayBuffer, and message passing patterns
---

# Web Workers

**Scope**: Web Workers API, Dedicated Workers, message passing, transferable objects, SharedArrayBuffer, worker lifecycle, React integration
**Lines**: ~380
**Last Updated**: 2025-10-27

## When to Use This Skill

Activate this skill when:
- Offloading heavy computation from the main thread
- Processing large datasets without blocking UI
- Implementing real-time data processing
- Building CPU-intensive features (image processing, cryptography, parsing)
- Preventing UI jank during complex operations
- Integrating workers with React applications
- Need parallel computation in the browser

---

## Core Concepts

### What Are Web Workers?

Web Workers run JavaScript in background threads separate from the main UI thread:

**Benefits**:
- Non-blocking computation
- Parallel processing
- Improved responsiveness
- Better Core Web Vitals (FID/INP)

**Limitations**:
- No DOM access
- No direct access to main thread variables
- Message passing overhead
- Separate global scope

**Use Cases**:
- Image/video processing
- Data parsing (CSV, JSON, XML)
- Cryptography and hashing
- Complex calculations
- Search and filtering large datasets
- Real-time data analysis

---

## Creating Web Workers

### Basic Worker Setup

**worker.ts**:
```typescript
// Worker code runs in separate thread
self.addEventListener('message', (event: MessageEvent) => {
  const { type, payload } = event.data;

  switch (type) {
    case 'COMPUTE':
      const result = performHeavyComputation(payload);
      self.postMessage({ type: 'RESULT', payload: result });
      break;

    case 'CANCEL':
      self.close(); // Terminate worker
      break;
  }
});

function performHeavyComputation(data: number[]): number {
  // CPU-intensive work
  return data.reduce((sum, val) => sum + Math.sqrt(val), 0);
}

// Signal worker is ready
self.postMessage({ type: 'READY' });
```

**main.ts**:
```typescript
// Create worker from file
const worker = new Worker(new URL('./worker.ts', import.meta.url), {
  type: 'module' // Enable ES modules in worker
});

// Listen for messages
worker.addEventListener('message', (event: MessageEvent) => {
  const { type, payload } = event.data;

  if (type === 'READY') {
    console.log('Worker ready');
  } else if (type === 'RESULT') {
    console.log('Result:', payload);
  }
});

// Handle errors
worker.addEventListener('error', (error: ErrorEvent) => {
  console.error('Worker error:', error.message);
});

// Send message to worker
worker.postMessage({
  type: 'COMPUTE',
  payload: [1, 2, 3, 4, 5]
});

// Cleanup
worker.terminate();
```

---

## Type-Safe Workers with TypeScript

### Strongly Typed Message Protocol

**types.ts**:
```typescript
// Define message types
export type WorkerRequest =
  | { type: 'COMPUTE'; payload: number[] }
  | { type: 'PROCESS_IMAGE'; payload: ImageData }
  | { type: 'CANCEL' };

export type WorkerResponse =
  | { type: 'READY' }
  | { type: 'RESULT'; payload: number }
  | { type: 'IMAGE_RESULT'; payload: ImageData }
  | { type: 'PROGRESS'; payload: number }
  | { type: 'ERROR'; payload: string };

// Worker context type
export interface WorkerContext {
  postMessage(message: WorkerResponse): void;
  addEventListener(type: 'message', listener: (e: MessageEvent<WorkerRequest>) => void): void;
}
```

**typed-worker.ts**:
```typescript
import type { WorkerRequest, WorkerResponse } from './types';

const ctx: Worker = self as any;

ctx.addEventListener('message', (event: MessageEvent<WorkerRequest>) => {
  const message = event.data;

  switch (message.type) {
    case 'COMPUTE':
      const result = compute(message.payload);
      ctx.postMessage({ type: 'RESULT', payload: result });
      break;

    case 'PROCESS_IMAGE':
      processImage(message.payload);
      break;

    case 'CANCEL':
      self.close();
      break;
  }
});

function compute(data: number[]): number {
  return data.reduce((sum, val) => sum + val, 0);
}

function processImage(imageData: ImageData): void {
  // Process image pixels
  for (let i = 0; i < imageData.data.length; i += 4) {
    // Apply grayscale
    const avg = (imageData.data[i] + imageData.data[i + 1] + imageData.data[i + 2]) / 3;
    imageData.data[i] = imageData.data[i + 1] = imageData.data[i + 2] = avg;
  }

  ctx.postMessage({ type: 'IMAGE_RESULT', payload: imageData });
}

ctx.postMessage({ type: 'READY' });
```

---

## Transferable Objects

### Zero-Copy Message Passing

Instead of copying large data, **transfer ownership**:

```typescript
// Without transfer (copies data - slow)
worker.postMessage({ imageData: largeImageData });

// With transfer (zero-copy - fast)
worker.postMessage(
  { imageData: largeImageData },
  [largeImageData.data.buffer] // Transfer ownership
);

// After transfer, largeImageData.data.buffer is neutered (length = 0)
// Worker now owns the buffer
```

**Transferable Types**:
- `ArrayBuffer`
- `MessagePort`
- `ImageBitmap`
- `OffscreenCanvas`

**Example with ArrayBuffer**:
```typescript
const data = new Float32Array(1_000_000);
// Fill with data...

// Transfer buffer to worker
worker.postMessage(
  { type: 'PROCESS', data: data.buffer },
  [data.buffer]
);

// data.buffer is now empty (neutered)
console.log(data.byteLength); // 0
```

**Worker receives buffer**:
```typescript
self.addEventListener('message', (event) => {
  const { data } = event.data;
  const array = new Float32Array(data);

  // Process array...
  const result = processArray(array);

  // Transfer back
  self.postMessage({ result: result.buffer }, [result.buffer]);
});
```

---

## React Integration

### Custom Hook for Workers

**useWorker.ts**:
```typescript
import { useEffect, useRef, useState } from 'react';
import type { WorkerRequest, WorkerResponse } from './types';

export function useWorker<T = any>(workerUrl: string) {
  const workerRef = useRef<Worker | null>(null);
  const [isReady, setIsReady] = useState(false);
  const [result, setResult] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    // Create worker
    const worker = new Worker(new URL(workerUrl, import.meta.url), {
      type: 'module'
    });
    workerRef.current = worker;

    // Handle messages
    worker.addEventListener('message', (event: MessageEvent<WorkerResponse>) => {
      const message = event.data;

      switch (message.type) {
        case 'READY':
          setIsReady(true);
          break;
        case 'RESULT':
          setResult(message.payload as T);
          break;
        case 'PROGRESS':
          setProgress(message.payload);
          break;
        case 'ERROR':
          setError(message.payload);
          break;
      }
    });

    // Handle errors
    worker.addEventListener('error', (error: ErrorEvent) => {
      setError(error.message);
    });

    // Cleanup
    return () => {
      worker.terminate();
      workerRef.current = null;
    };
  }, [workerUrl]);

  const postMessage = (message: WorkerRequest, transfer?: Transferable[]) => {
    if (workerRef.current && isReady) {
      workerRef.current.postMessage(message, transfer || []);
    }
  };

  const terminate = () => {
    if (workerRef.current) {
      workerRef.current.terminate();
      workerRef.current = null;
      setIsReady(false);
    }
  };

  return { postMessage, terminate, isReady, result, error, progress };
}
```

**Component usage**:
```typescript
import { useWorker } from './useWorker';

export function ImageProcessor() {
  const { postMessage, result, isReady, progress } = useWorker<ImageData>('./image-worker.ts');
  const [imageData, setImageData] = useState<ImageData | null>(null);

  const handleImageUpload = async (file: File) => {
    const bitmap = await createImageBitmap(file);
    const canvas = document.createElement('canvas');
    canvas.width = bitmap.width;
    canvas.height = bitmap.height;
    const ctx = canvas.getContext('2d')!;
    ctx.drawImage(bitmap, 0, 0);

    const data = ctx.getImageData(0, 0, canvas.width, canvas.height);
    setImageData(data);

    // Send to worker with transfer
    postMessage(
      { type: 'PROCESS_IMAGE', payload: data },
      [data.data.buffer]
    );
  };

  return (
    <div>
      <input type="file" onChange={(e) => handleImageUpload(e.target.files![0])} />
      {!isReady && <p>Loading worker...</p>}
      {progress > 0 && <progress value={progress} max={100} />}
      {result && <canvas ref={(canvas) => {
        if (canvas) {
          const ctx = canvas.getContext('2d')!;
          canvas.width = result.width;
          canvas.height = result.height;
          ctx.putImageData(result, 0, 0);
        }
      }} />}
    </div>
  );
}
```

---

## Worker Pool Pattern

### Managing Multiple Workers

```typescript
class WorkerPool {
  private workers: Worker[] = [];
  private queue: Array<{ task: any; resolve: (value: any) => void; reject: (reason: any) => void }> = [];
  private busyWorkers = new Set<Worker>();

  constructor(
    private workerUrl: string,
    private poolSize: number = navigator.hardwareConcurrency || 4
  ) {
    for (let i = 0; i < poolSize; i++) {
      this.createWorker();
    }
  }

  private createWorker(): void {
    const worker = new Worker(new URL(this.workerUrl, import.meta.url), {
      type: 'module'
    });

    worker.addEventListener('message', (event) => {
      this.busyWorkers.delete(worker);

      // Process result and check queue
      this.processNext();
    });

    this.workers.push(worker);
  }

  async execute<T>(task: any): Promise<T> {
    return new Promise((resolve, reject) => {
      this.queue.push({ task, resolve, reject });
      this.processNext();
    });
  }

  private processNext(): void {
    if (this.queue.length === 0) return;

    const availableWorker = this.workers.find(w => !this.busyWorkers.has(w));
    if (!availableWorker) return;

    const { task, resolve, reject } = this.queue.shift()!;
    this.busyWorkers.add(availableWorker);

    const handler = (event: MessageEvent) => {
      availableWorker.removeEventListener('message', handler);
      resolve(event.data);
    };

    availableWorker.addEventListener('message', handler);
    availableWorker.postMessage(task);
  }

  terminate(): void {
    this.workers.forEach(w => w.terminate());
    this.workers = [];
    this.busyWorkers.clear();
    this.queue = [];
  }
}

// Usage
const pool = new WorkerPool('./compute-worker.ts', 4);

async function processBatch(items: number[][]): Promise<number[]> {
  const results = await Promise.all(
    items.map(item => pool.execute({ type: 'COMPUTE', payload: item }))
  );
  return results;
}
```

---

## Performance Comparison

### Main Thread vs Worker

**Main thread (blocking)**:
```typescript
function processDataMainThread(data: number[]): number {
  console.time('main-thread');
  const result = data.reduce((sum, val) => sum + Math.sqrt(val), 0);
  console.timeEnd('main-thread');
  return result;
}

// UI becomes unresponsive during processing
const result = processDataMainThread(new Array(10_000_000).fill(0).map((_, i) => i));
```

**Worker (non-blocking)**:
```typescript
async function processDataWorker(data: number[]): Promise<number> {
  console.time('worker');

  const worker = new Worker(new URL('./compute-worker.ts', import.meta.url), {
    type: 'module'
  });

  const result = await new Promise<number>((resolve) => {
    worker.addEventListener('message', (event) => {
      console.timeEnd('worker');
      resolve(event.data.payload);
      worker.terminate();
    });

    worker.postMessage({ type: 'COMPUTE', payload: data });
  });

  return result;
}

// UI remains responsive during processing
const result = await processDataWorker(new Array(10_000_000).fill(0).map((_, i) => i));
```

**Benchmark Results** (10M operations):
```
Main thread: 450ms (UI blocked)
Worker:      480ms (UI responsive) + ~5ms setup overhead
Worker Pool: 120ms (4 workers in parallel)
```

---

## Common Patterns

### 1. Long-Running Task with Progress

```typescript
// worker.ts
self.addEventListener('message', (event) => {
  const { type, payload } = event.data;

  if (type === 'PROCESS') {
    const total = payload.length;
    let processed = 0;

    const results = payload.map((item: any) => {
      const result = processItem(item);
      processed++;

      // Report progress every 1000 items
      if (processed % 1000 === 0) {
        self.postMessage({
          type: 'PROGRESS',
          payload: Math.floor((processed / total) * 100)
        });
      }

      return result;
    });

    self.postMessage({ type: 'RESULT', payload: results });
  }
});
```

### 2. Cancellable Worker

```typescript
// worker.ts
let cancelled = false;

self.addEventListener('message', (event) => {
  const { type, payload } = event.data;

  if (type === 'CANCEL') {
    cancelled = true;
    return;
  }

  if (type === 'COMPUTE') {
    cancelled = false;

    for (let i = 0; i < payload.length; i++) {
      if (cancelled) {
        self.postMessage({ type: 'CANCELLED' });
        return;
      }

      // Process item...
    }

    self.postMessage({ type: 'RESULT', payload: results });
  }
});
```

### 3. Worker with Initialization

```typescript
// worker.ts
let initialized = false;
let wasmModule: any = null;

self.addEventListener('message', async (event) => {
  const { type, payload } = event.data;

  if (type === 'INIT') {
    // Load WASM or other resources
    wasmModule = await loadWasm(payload.wasmUrl);
    initialized = true;
    self.postMessage({ type: 'READY' });
    return;
  }

  if (!initialized) {
    self.postMessage({ type: 'ERROR', payload: 'Not initialized' });
    return;
  }

  // Process with WASM...
});
```

---

## Anti-Patterns

**Bad: Creating workers repeatedly**
```typescript
❌ // Creates new worker on every call
function process(data: any) {
  const worker = new Worker('./worker.ts');
  worker.postMessage(data);
}
```

**Good: Reuse workers or use pool**
```typescript
✅ const worker = new Worker('./worker.ts');

function process(data: any) {
  worker.postMessage(data);
}

// Or use worker pool for multiple parallel tasks
```

**Bad: Passing large objects by copy**
```typescript
❌ worker.postMessage({ data: largeArrayBuffer });
```

**Good: Use transferable objects**
```typescript
✅ worker.postMessage({ data: largeArrayBuffer }, [largeArrayBuffer]);
```

**Bad: Accessing DOM in worker**
```typescript
❌ // Worker context - NO DOM ACCESS
document.getElementById('result'); // ERROR
```

**Good: Pass results to main thread**
```typescript
✅ // Worker sends data
self.postMessage({ result: computedValue });

// Main thread updates DOM
worker.addEventListener('message', (e) => {
  document.getElementById('result').textContent = e.data.result;
});
```

---

## Browser Compatibility

| Feature | Chrome | Firefox | Safari | Edge |
|---------|--------|---------|--------|------|
| Web Workers | 4+ | 3.5+ | 4+ | 12+ |
| Module Workers | 80+ | 114+ | 15+ | 80+ |
| Transferable Objects | 13+ | 18+ | 6+ | 12+ |
| SharedArrayBuffer | 68+ | 79+ | 15.2+ | 79+ |

**Feature Detection**:
```typescript
if (typeof Worker !== 'undefined') {
  // Workers supported
  const worker = new Worker('./worker.ts', { type: 'module' });
} else {
  // Fallback to main thread
  const result = processSync(data);
}
```

---

## Related Skills

- **browser-concurrency.md** - Service Workers, SharedWorkers, advanced concurrency
- **frontend-performance.md** - Overall performance optimization strategies
- **react-component-patterns.md** - React patterns and hooks for worker integration
- **wasm-basics.md** - Combining WebAssembly with workers for maximum performance

---

## Summary

Web Workers enable non-blocking computation in the browser:

**Key Takeaways**:
- Use workers for CPU-intensive tasks (>50ms)
- Transfer large data instead of copying
- Implement type-safe message protocols
- Use worker pools for parallel processing
- Integrate with React through custom hooks
- Always handle errors and cleanup properly
- Measure actual performance impact

**When to Use**:
- Image/video processing
- Large dataset parsing
- Cryptography
- Search/filtering
- Real-time analytics
- Any computation >50ms

**When NOT to Use**:
- Simple, fast operations (<50ms)
- When you need DOM access
- Frequent small messages (overhead > benefit)
