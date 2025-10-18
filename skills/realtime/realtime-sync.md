---
name: realtime-realtime-sync
description: Use real-time sync patterns when you need:
---


# Real-time Data Synchronization

**Scope**: Conflict resolution, CRDTs, operational transformation, and eventual consistency patterns
**Lines**: 398
**Last Updated**: 2025-10-18

## When to Use This Skill

Use real-time sync patterns when you need:
- **Collaborative editing**: Multiple users editing the same document simultaneously
- **Offline-first apps**: Apps that work offline and sync when reconnected
- **Conflict resolution**: Merging concurrent updates without data loss
- **Eventual consistency**: Distributed data that converges to same state
- **Real-time collaboration**: Shared whiteboards, multiplayer games, collaborative design

**Don't use** when:
- Single user editing with simple save/load (use optimistic updates)
- No concurrent edits possible (use last-write-wins)
- Strong consistency required (use pessimistic locking)
- Data is immutable/append-only (use event sourcing)

## Core Concepts

### Conflict Resolution Strategies

```
1. Last-Write-Wins (LWW)
   - Simplest approach
   - Use timestamp or sequence number
   - Data loss possible

2. Operational Transformation (OT)
   - Transform operations based on concurrent ops
   - Complex but preserves intent
   - Used in Google Docs

3. Conflict-Free Replicated Data Types (CRDTs)
   - Mathematical guarantees of convergence
   - No conflict resolution needed
   - Used in distributed systems

4. Three-Way Merge
   - Compare: base, local, remote
   - Identify conflicts explicitly
   - User resolves ambiguities
```

### Synchronization Patterns

```
Client A          Server          Client B
   |                 |                |
   |-- Update A ---->|                |
   |                 |-- Broadcast -->|
   |                 |                |
   |<-- Update B ----|<-- Update B ---|
   |                 |                |
   |-- Resolve ----->|                |
   |<-- Merged ------|-- Merged ----->|
```

## Patterns

### 1. Last-Write-Wins (LWW) with Vector Clocks

```typescript
// Simple LWW with timestamps
interface VersionedData<T> {
  data: T;
  version: number;
  timestamp: number;
  clientId: string;
}

class LWWStore<T> {
  private data: VersionedData<T> | null = null;

  update(newData: T, clientId: string): VersionedData<T> {
    const version = (this.data?.version ?? 0) + 1;
    const timestamp = Date.now();

    this.data = {
      data: newData,
      version,
      timestamp,
      clientId,
    };

    return this.data;
  }

  merge(remote: VersionedData<T>): boolean {
    if (!this.data) {
      this.data = remote;
      return true;
    }

    // Resolve conflicts with LWW
    if (remote.timestamp > this.data.timestamp) {
      this.data = remote;
      return true;
    } else if (remote.timestamp === this.data.timestamp) {
      // Tie-break with clientId for determinism
      if (remote.clientId > this.data.clientId) {
        this.data = remote;
        return true;
      }
    }

    return false; // No update
  }

  get(): T | null {
    return this.data?.data ?? null;
  }
}

// Usage
const store = new LWWStore<string>();
store.update('Hello', 'client-1');

// Simulate remote update
const remoteData = {
  data: 'World',
  version: 2,
  timestamp: Date.now() + 1000,
  clientId: 'client-2',
};

const updated = store.merge(remoteData);
console.log(updated); // true
console.log(store.get()); // 'World'
```

### 2. CRDT: Last-Write-Wins Register

```typescript
// LWW-Register CRDT
interface LWWRegister<T> {
  value: T;
  timestamp: number;
  clientId: string;
}

class LWWRegisterCRDT<T> {
  private register: LWWRegister<T>;

  constructor(initialValue: T, clientId: string) {
    this.register = {
      value: initialValue,
      timestamp: Date.now(),
      clientId,
    };
  }

  set(value: T, clientId: string): LWWRegister<T> {
    this.register = {
      value,
      timestamp: Date.now(),
      clientId,
    };
    return this.register;
  }

  merge(other: LWWRegister<T>): boolean {
    if (other.timestamp > this.register.timestamp ||
        (other.timestamp === this.register.timestamp &&
         other.clientId > this.register.clientId)) {
      this.register = other;
      return true;
    }
    return false;
  }

  get(): T {
    return this.register.value;
  }

  getState(): LWWRegister<T> {
    return { ...this.register };
  }
}
```

### 3. CRDT: Grow-Only Set (G-Set)

```typescript
// G-Set: Elements can only be added, never removed
class GSet<T> {
  private elements: Set<T> = new Set();

  add(element: T): boolean {
    if (this.elements.has(element)) {
      return false;
    }
    this.elements.add(element);
    return true;
  }

  has(element: T): boolean {
    return this.elements.has(element);
  }

  merge(other: GSet<T>): void {
    other.elements.forEach((element) => {
      this.elements.add(element);
    });
  }

  toArray(): T[] {
    return Array.from(this.elements);
  }

  getState(): T[] {
    return this.toArray();
  }
}

// Usage
const set1 = new GSet<string>();
set1.add('a');
set1.add('b');

const set2 = new GSet<string>();
set2.add('b');
set2.add('c');

set1.merge(set2);
console.log(set1.toArray()); // ['a', 'b', 'c']
```

### 4. CRDT: Two-Phase Set (2P-Set)

```typescript
// 2P-Set: Elements can be added and removed (but only once each)
class TwoPhaseSet<T> {
  private addSet: Set<T> = new Set();
  private removeSet: Set<T> = new Set();

  add(element: T): boolean {
    if (this.removeSet.has(element)) {
      return false; // Cannot re-add removed element
    }
    this.addSet.add(element);
    return true;
  }

  remove(element: T): boolean {
    if (!this.addSet.has(element)) {
      return false; // Cannot remove non-existent element
    }
    this.removeSet.add(element);
    return true;
  }

  has(element: T): boolean {
    return this.addSet.has(element) && !this.removeSet.has(element);
  }

  merge(other: TwoPhaseSet<T>): void {
    other.addSet.forEach((element) => this.addSet.add(element));
    other.removeSet.forEach((element) => this.removeSet.add(element));
  }

  toArray(): T[] {
    return Array.from(this.addSet).filter((element) => !this.removeSet.has(element));
  }

  getState() {
    return {
      added: Array.from(this.addSet),
      removed: Array.from(this.removeSet),
    };
  }
}
```

### 5. CRDT: Counter (G-Counter and PN-Counter)

```typescript
// G-Counter: Grow-only counter (increment only)
class GCounter {
  private counts: Map<string, number> = new Map();

  increment(clientId: string, amount: number = 1): void {
    const current = this.counts.get(clientId) ?? 0;
    this.counts.set(clientId, current + amount);
  }

  value(): number {
    let total = 0;
    this.counts.forEach((count) => {
      total += count;
    });
    return total;
  }

  merge(other: GCounter): void {
    other.counts.forEach((count, clientId) => {
      const current = this.counts.get(clientId) ?? 0;
      this.counts.set(clientId, Math.max(current, count));
    });
  }

  getState(): Map<string, number> {
    return new Map(this.counts);
  }
}

// PN-Counter: Positive-Negative counter (increment and decrement)
class PNCounter {
  private increments: GCounter = new GCounter();
  private decrements: GCounter = new GCounter();

  increment(clientId: string, amount: number = 1): void {
    this.increments.increment(clientId, amount);
  }

  decrement(clientId: string, amount: number = 1): void {
    this.decrements.increment(clientId, amount);
  }

  value(): number {
    return this.increments.value() - this.decrements.value();
  }

  merge(other: PNCounter): void {
    this.increments.merge(other.increments);
    this.decrements.merge(other.decrements);
  }
}

// Usage
const counter = new PNCounter();
counter.increment('client-1', 5);
counter.decrement('client-1', 2);
console.log(counter.value()); // 3
```

### 6. Operational Transformation (Simple Text)

```typescript
// Simple OT for text insertion and deletion
interface Operation {
  type: 'insert' | 'delete';
  position: number;
  content?: string;
  length?: number;
}

class OperationalTransform {
  static transform(op1: Operation, op2: Operation): Operation {
    if (op1.type === 'insert' && op2.type === 'insert') {
      if (op1.position < op2.position) {
        // op2 happens after op1's insertion
        return {
          ...op2,
          position: op2.position + (op1.content?.length ?? 0),
        };
      } else if (op1.position > op2.position) {
        // op2 happens before op1, no transformation needed
        return op2;
      } else {
        // Same position, use arbitrary tie-breaker
        return {
          ...op2,
          position: op2.position + (op1.content?.length ?? 0),
        };
      }
    }

    if (op1.type === 'delete' && op2.type === 'insert') {
      if (op2.position <= op1.position) {
        // op2 before deletion
        return op2;
      } else if (op2.position >= op1.position + (op1.length ?? 0)) {
        // op2 after deletion
        return {
          ...op2,
          position: op2.position - (op1.length ?? 0),
        };
      } else {
        // op2 inside deletion range
        return {
          ...op2,
          position: op1.position,
        };
      }
    }

    if (op1.type === 'insert' && op2.type === 'delete') {
      if (op2.position < op1.position) {
        // op2 before insertion
        return op2;
      } else if (op2.position >= op1.position + (op1.content?.length ?? 0)) {
        // op2 after insertion
        return {
          ...op2,
          position: op2.position + (op1.content?.length ?? 0),
        };
      } else {
        // op2 inside insertion
        return {
          ...op2,
          position: op1.position,
          length: (op2.length ?? 0) + (op1.content?.length ?? 0),
        };
      }
    }

    if (op1.type === 'delete' && op2.type === 'delete') {
      if (op2.position < op1.position) {
        return op2;
      } else if (op2.position >= op1.position + (op1.length ?? 0)) {
        return {
          ...op2,
          position: op2.position - (op1.length ?? 0),
        };
      } else {
        // Overlapping deletes
        return {
          ...op2,
          position: op1.position,
          length: Math.max(0, (op2.length ?? 0) - (op1.length ?? 0)),
        };
      }
    }

    return op2;
  }

  static apply(text: string, op: Operation): string {
    if (op.type === 'insert') {
      return text.slice(0, op.position) + op.content + text.slice(op.position);
    } else if (op.type === 'delete') {
      return text.slice(0, op.position) + text.slice(op.position + (op.length ?? 0));
    }
    return text;
  }
}

// Usage
let text = 'Hello World';

const op1: Operation = { type: 'insert', position: 5, content: ',' };
const op2: Operation = { type: 'delete', position: 6, length: 5 };

// Client A applies op1
let textA = OperationalTransform.apply(text, op1); // "Hello, World"

// Client B applies op2 (concurrently)
let textB = OperationalTransform.apply(text, op2); // "Hello "

// Transform op2 against op1 for Client A
const op2Transformed = OperationalTransform.transform(op1, op2);
textA = OperationalTransform.apply(textA, op2Transformed); // "Hello,"

// Transform op1 against op2 for Client B
const op1Transformed = OperationalTransform.transform(op2, op1);
textB = OperationalTransform.apply(textB, op1Transformed); // "Hello,"

console.log(textA === textB); // true - convergence!
```

### 7. Sync Manager with WebSocket

```typescript
interface SyncMessage {
  type: 'update' | 'sync_request' | 'sync_response';
  clientId: string;
  data?: any;
  version?: number;
}

class SyncManager<T> {
  private ws: WebSocket;
  private clientId: string;
  private crdt: LWWRegisterCRDT<T>;
  private onUpdate: (data: T) => void;

  constructor(
    url: string,
    initialData: T,
    onUpdate: (data: T) => void
  ) {
    this.clientId = this.generateClientId();
    this.crdt = new LWWRegisterCRDT(initialData, this.clientId);
    this.onUpdate = onUpdate;
    this.ws = new WebSocket(url);
    this.setupWebSocket();
  }

  private setupWebSocket() {
    this.ws.onopen = () => {
      console.log('Connected to sync server');
      this.requestSync();
    };

    this.ws.onmessage = (event) => {
      const message: SyncMessage = JSON.parse(event.data);
      this.handleMessage(message);
    };
  }

  private handleMessage(message: SyncMessage) {
    switch (message.type) {
      case 'update':
        if (message.data && message.clientId !== this.clientId) {
          const updated = this.crdt.merge(message.data);
          if (updated) {
            this.onUpdate(this.crdt.get());
          }
        }
        break;

      case 'sync_response':
        if (message.data) {
          this.crdt.merge(message.data);
          this.onUpdate(this.crdt.get());
        }
        break;
    }
  }

  update(data: T) {
    this.crdt.set(data, this.clientId);
    this.broadcast();
    this.onUpdate(this.crdt.get());
  }

  private broadcast() {
    const message: SyncMessage = {
      type: 'update',
      clientId: this.clientId,
      data: this.crdt.getState(),
    };
    this.ws.send(JSON.stringify(message));
  }

  private requestSync() {
    const message: SyncMessage = {
      type: 'sync_request',
      clientId: this.clientId,
    };
    this.ws.send(JSON.stringify(message));
  }

  private generateClientId(): string {
    return `client_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }
}

// Usage
const syncManager = new SyncManager(
  'wss://sync.example.com',
  'Initial data',
  (data) => {
    console.log('Data updated:', data);
  }
);

syncManager.update('New data');
```

## Quick Reference

### CRDT Types

```typescript
// LWW-Register: Single value, last write wins
const register = new LWWRegisterCRDT('initial', 'client-1');

// G-Set: Grow-only set (add only)
const gset = new GSet<string>();

// 2P-Set: Add and remove (once each)
const tpset = new TwoPhaseSet<string>();

// G-Counter: Increment-only counter
const gcounter = new GCounter();

// PN-Counter: Increment and decrement counter
const pncounter = new PNCounter();
```

### Conflict Resolution Strategies

```typescript
// Last-Write-Wins: Use timestamp
if (remote.timestamp > local.timestamp) {
  local = remote;
}

// Version Vector: Use vector clock
if (isGreaterThan(remote.vector, local.vector)) {
  local = remote;
}

// Three-Way Merge: Compare base, local, remote
const merged = merge(base, local, remote);
```

### State Synchronization

```typescript
// Full state sync
send({ type: 'full_sync', state: crdt.getState() });

// Delta sync (changes only)
send({ type: 'delta_sync', delta: crdt.getDelta() });

// Operational sync (operations)
send({ type: 'operation', op: { type: 'insert', ... } });
```

## Anti-Patterns

### ❌ Using Timestamps Without Tie-Breakers

```typescript
// Wrong: Ties cause non-deterministic results
if (remote.timestamp > local.timestamp) {
  local = remote;
}
// What if timestamps are equal?
```

**Why it's bad**: Different clients may choose different values for concurrent updates

**Better approach**:
```typescript
if (remote.timestamp > local.timestamp ||
    (remote.timestamp === local.timestamp && remote.clientId > local.clientId)) {
  local = remote;
}
```

### ❌ Sending Full State on Every Update

```typescript
// Wrong: Inefficient for large documents
socket.send(JSON.stringify({ type: 'update', data: fullDocument }));
```

**Why it's bad**: Wastes bandwidth, especially for small changes

**Better approach**:
```typescript
// Send operations or deltas
socket.send(JSON.stringify({ type: 'operation', op: { type: 'insert', position: 5, content: 'x' } }));
```

### ❌ No Conflict Detection

```typescript
// Wrong: Blindly overwrite
function update(data) {
  this.data = data; // No version checking
}
```

**Why it's bad**: Lost updates when concurrent modifications occur

**Better approach**:
```typescript
function update(data, version) {
  if (version <= this.version) {
    throw new Error('Conflict detected');
  }
  this.data = data;
  this.version = version;
}
```

### ❌ Synchronous Merge Operations

```typescript
// Wrong: Blocking merge for large data
await merge(largeDocument); // Blocks UI
```

**Why it's bad**: UI freezes during merge

**Better approach**:
```typescript
// Merge in Web Worker or use incremental merging
worker.postMessage({ type: 'merge', data: largeDocument });
```

## Related Skills

- **websocket-implementation.md**: WebSocket protocol for sync communication
- **server-sent-events.md**: SSE for server-to-client sync updates
- **pubsub-patterns.md**: Server-side message routing for collaborative features
- **network-resilience-patterns.md**: Handling network failures during sync

---

**Last Updated**: 2025-10-18
**Format Version**: 1.0 (Atomic)
