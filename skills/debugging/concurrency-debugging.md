---
name: debugging-concurrency-debugging
description: Race condition detection, deadlock debugging, and data race analysis using ThreadSanitizer and specialized tools
---

# Concurrency Debugging

**Scope**: Race condition detection, deadlock analysis, happens-before relationships, and lock-free debugging
**Lines**: ~430
**Last Updated**: 2025-10-26
**Format Version**: 1.0 (Atomic)

---

## When to Use This Skill

Activate this skill when:
- Encountering non-deterministic bugs or flaky tests
- Debugging race conditions or data races
- Investigating deadlocks or livelocks
- Validating thread safety in concurrent code
- Analyzing lock contention or performance issues
- Implementing lock-free data structures
- Debugging Go goroutines or Rust async code
- Using ThreadSanitizer, Helgrind, or Intel Inspector

---

## Core Concepts

### Concept 1: Race Conditions vs Data Races

**Definitions**:
- **Data race**: Two threads access same memory, at least one writes, no synchronization
- **Race condition**: Behavior depends on timing/ordering of events (broader concept)
- **Benign race**: Data race that doesn't cause bugs (rare, dangerous assumption)

**Key Distinction**:
```c
// Data race (undefined behavior in C/C++)
int counter = 0;
void thread1() { counter++; }  // Read-modify-write, not atomic
void thread2() { counter++; }  // Race: both may read 0, write 1

// Race condition but NOT data race (synchronized but buggy)
std::mutex mtx;
int balance = 100;

void withdraw(int amount) {
    mtx.lock();
    int current = balance;
    mtx.unlock();  // ❌ Released too early

    if (current >= amount) {
        mtx.lock();
        balance -= amount;  // ❌ Race: balance may have changed
        mtx.unlock();
    }
}
```

**Detection**:
- Data races: ThreadSanitizer, Helgrind (automatic detection)
- Race conditions: Manual analysis, invariant violations (harder to detect)

### Concept 2: Happens-Before Relationships

**Happens-Before Rules** (memory ordering):
1. **Program order**: A happens-before B if A comes before B in same thread
2. **Lock release/acquire**: Unlock happens-before subsequent lock of same mutex
3. **Thread creation/join**: Thread start happens-before thread body, body happens-before join
4. **Atomic operations**: Release-acquire semantics create happens-before

**Visualization**:
```
Thread 1:         Thread 2:
  x = 42;
  mutex.unlock();  →  mutex.lock();  // Happens-before edge
                        y = x;       // Guaranteed to see x=42
```

**No Happens-Before = Race**:
```c++
// ❌ Data race: no happens-before relationship
int data = 0;
bool ready = false;

// Thread 1
data = 42;
ready = true;  // Non-atomic write

// Thread 2
if (ready) {  // Non-atomic read
    use(data);  // May see stale data (race)
}

// ✅ Fixed with atomics (acquire-release)
std::atomic<bool> ready{false};

// Thread 1
data = 42;
ready.store(true, std::memory_order_release);  // Synchronizes

// Thread 2
if (ready.load(std::memory_order_acquire)) {  // Synchronizes
    use(data);  // Guaranteed to see data=42
}
```

### Concept 3: Deadlock Detection

**Deadlock Conditions** (all must hold):
1. **Mutual exclusion**: Resources held exclusively
2. **Hold and wait**: Thread holds resource while waiting for another
3. **No preemption**: Resources can't be forcibly taken
4. **Circular wait**: Cycle of threads waiting for each other

**Classic Deadlock Example**:
```c++
std::mutex m1, m2;

// Thread A
void thread_a() {
    m1.lock();
    // ... context switch ...
    m2.lock();  // Waits for m2 (held by B)
    // ...
    m2.unlock();
    m1.unlock();
}

// Thread B
void thread_b() {
    m2.lock();
    // ... context switch ...
    m1.lock();  // Waits for m1 (held by A) → DEADLOCK
    // ...
    m1.unlock();
    m2.unlock();
}
```

**Deadlock Prevention**:
- **Lock ordering**: Always acquire locks in same global order
- **Timeouts**: Try-lock with timeout, back off if failed
- **Deadlock detection**: Runtime cycle detection, automatic recovery

---

## Patterns

### Pattern 1: ThreadSanitizer (TSan) for C/C++/Go

**When to use**:
- Detecting data races in C/C++ or Go code
- Integration testing with race detection
- CI/CD race detection pipelines

```bash
# C/C++: Compile with TSan
clang++ -fsanitize=thread -g -O1 app.cpp -o app
# or
g++ -fsanitize=thread -g -O1 app.cpp -o app

# Run instrumented binary
./app

# Example TSan report:
# WARNING: ThreadSanitizer: data race (pid=12345)
#   Write of size 4 at 0x7f1234567890 by thread T2:
#     #0 increment_counter app.cpp:42
#
#   Previous read of size 4 at 0x7f1234567890 by thread T1:
#     #0 read_counter app.cpp:38
#
# Thread T2 created by main thread at:
#     #0 pthread_create
#     #1 main app.cpp:56
```

**Go Race Detector**:
```bash
# Build and run with race detector
go run -race main.go

# Test with race detector
go test -race ./...

# Build with race detector for deployment (staging only)
go build -race -o app

# Example Go race report:
# WARNING: DATA RACE
# Write at 0x00c000012080 by goroutine 7:
#   main.incrementCounter()
#       /app/main.go:23 +0x44
#
# Previous read at 0x00c000012080 by goroutine 6:
#   main.readCounter()
#       /app/main.go:19 +0x38
```

**TSan Configuration**:
```bash
# Suppress false positives
export TSAN_OPTIONS="suppressions=tsan.supp:history_size=7"

# tsan.supp file:
# race:external_library_function
# race:known_benign_race
```

**Benefits**:
- Detects races with high accuracy
- Low false positive rate
- Shows exact code locations and thread stacks

**Limitations**:
- 5-15x slowdown (CI/staging only)
- Cannot run with ASan simultaneously
- May miss races in unexecuted code paths

### Pattern 2: Helgrind for Data Race Detection

**When to use**:
- Alternative to TSan for C/C++ (no recompilation)
- Debugging legacy code without build system changes
- Validating lock-based synchronization

```bash
# Run with Helgrind
valgrind --tool=helgrind ./app

# Example Helgrind report:
# ==12345== Possible data race during read of size 4 at 0x601040 by thread #2
# ==12345== Locks held: none
# ==12345==    at 0x400ABC: read_counter (app.cpp:42)
# ==12345==
# ==12345== This conflicts with a previous write of size 4 by thread #1
# ==12345== Locks held: none
# ==12345==    at 0x400DEF: write_counter (app.cpp:38)
```

**Helgrind Annotations** (reduce false positives):
```c++
#include <valgrind/helgrind.h>

// Mark benign race (use sparingly!)
ANNOTATE_BENIGN_RACE_SIZED(&var, sizeof(var), "Reason");

// Happens-before annotation for custom synchronization
ANNOTATE_HAPPENS_BEFORE(&sync_point);
ANNOTATE_HAPPENS_AFTER(&sync_point);
```

**Benefits**:
- No recompilation needed
- Works with any C/C++ code
- Detects lock-order violations

**Limitations**:
- High overhead (10-30x slowdown)
- More false positives than TSan
- Cannot detect atomics-based races

### Pattern 3: Intel Inspector for Concurrency Analysis

**When to use**:
- Windows/Linux GUI-based race and deadlock detection
- Need visual timeline and thread interaction diagrams
- Enterprise C/C++ development

```bash
# Command-line data race detection
inspxe-cl -collect ti2 -result-dir results -- ./app

# Deadlock detection
inspxe-cl -collect ti3 -result-dir results -- ./app

# View results in GUI
inspxe-gui results
```

**Inspector Analysis Types**:
- **ti1**: Detect deadlocks only (fast)
- **ti2**: Detect deadlocks and data races (moderate)
- **ti3**: Comprehensive analysis (slow, high accuracy)

**Benefits**:
- Visual timeline of thread interactions
- Detects races, deadlocks, and lock contention
- Lower false positive rate than Helgrind

**Limitations**:
- Commercial tool (license required)
- Higher overhead than TSan
- GUI-focused (less CI/CD friendly)

### Pattern 4: GDB Thread Debugging

**When to use**:
- Investigating deadlocks in running/crashed processes
- Manual inspection of thread states
- No race detector available

```bash
# Attach to running process
gdb -p 12345

# Show all threads
(gdb) info threads
#   Id   Target Id         Frame
# * 1    Thread 0x7f123... main () at app.cpp:42
#   2    Thread 0x7f124... worker () at app.cpp:67
#   3    Thread 0x7f125... 0x00007f... in pthread_cond_wait ()

# Switch to thread
(gdb) thread 2

# Show backtrace for current thread
(gdb) bt
# #0  0x00007f1234567890 in __lll_lock_wait ()
# #1  0x00007f1234567891 in pthread_mutex_lock ()
# #2  0x0000000000400abc in acquire_lock () at app.cpp:23
# #3  0x0000000000400def in worker () at app.cpp:67

# Show backtraces for all threads
(gdb) thread apply all bt

# Detect potential deadlock (threads waiting on locks)
(gdb) thread apply all bt | grep -E "lock|wait"
```

**Deadlock Analysis**:
```bash
# Find threads blocked on mutexes
(gdb) thread apply all bt full
# Look for frames containing:
# - pthread_mutex_lock
# - pthread_cond_wait
# - __lll_lock_wait

# Identify lock holders
(gdb) p *(pthread_mutex_t*)0x601040  # Inspect mutex at address
# Shows __lock field (0 = unlocked, non-zero = locked)
```

**Benefits**:
- Works on live processes and core dumps
- No recompilation or instrumentation
- Detailed thread state inspection

### Pattern 5: Go Race Detector Best Practices

**When to use**:
- All Go concurrent code (goroutines, channels)
- CI/CD integration for race detection
- Identifying synchronization gaps

```go
// ❌ Data race: shared map access
var cache = make(map[string]string)

func set(key, value string) {
    cache[key] = value  // Race if concurrent
}

func get(key string) string {
    return cache[key]  // Race if concurrent
}

// ✅ Fixed: use sync.Map
var cache sync.Map

func set(key, value string) {
    cache.Store(key, value)
}

func get(key string) string {
    val, _ := cache.Load(key)
    if val != nil {
        return val.(string)
    }
    return ""
}
```

**Race Detection in Tests**:
```go
func TestConcurrentAccess(t *testing.T) {
    var counter int64
    var wg sync.WaitGroup

    // Spawn 100 goroutines incrementing counter
    for i := 0; i < 100; i++ {
        wg.Add(1)
        go func() {
            defer wg.Done()
            counter++  // ❌ Race detected by go test -race
        }()
    }
    wg.Wait()

    // Race detector will report:
    // WARNING: DATA RACE
    // Write at 0x00c000012080 by goroutine 7
}

// ✅ Fixed version
func TestConcurrentAccessFixed(t *testing.T) {
    var counter int64
    var wg sync.WaitGroup

    for i := 0; i < 100; i++ {
        wg.Add(1)
        go func() {
            defer wg.Done()
            atomic.AddInt64(&counter, 1)  // ✅ No race
        }()
    }
    wg.Wait()
}
```

**Benefits**:
- Built into Go toolchain
- Low overhead (2-10x slowdown)
- Excellent CI integration

### Pattern 6: Lock-Order Enforcement

**When to use**:
- Preventing deadlocks in complex locking scenarios
- Systems with multiple locks that interact
- Critical sections with nested locking

```c++
// Define global lock ordering
enum LockOrder {
    LOCK_DATABASE = 1,
    LOCK_CACHE = 2,
    LOCK_NETWORK = 3
};

class OrderedMutex {
    std::mutex mtx;
    LockOrder order;

public:
    OrderedMutex(LockOrder o) : order(o) {}

    void lock() {
        // Check thread's current lock level
        thread_local LockOrder current_level = LOCK_DATABASE;
        if (order <= current_level) {
            throw std::runtime_error("Lock order violation!");
        }
        mtx.lock();
        current_level = order;
    }

    void unlock() {
        mtx.unlock();
    }
};

// Usage
OrderedMutex db_lock(LOCK_DATABASE);
OrderedMutex cache_lock(LOCK_CACHE);

void safe_function() {
    db_lock.lock();     // ✅ OK: lowest level
    cache_lock.lock();  // ✅ OK: higher level
    // ...
    cache_lock.unlock();
    db_lock.unlock();
}

void unsafe_function() {
    cache_lock.lock();  // Acquired first
    db_lock.lock();     // ❌ EXCEPTION: violates ordering
}
```

**Rust Lock Ordering** (compile-time):
```rust
// Use type system to enforce lock order
struct DatabaseLock(Mutex<Database>);
struct CacheLock<'db>(Mutex<Cache>, PhantomData<&'db DatabaseLock>);

// Lifetime ensures database locked before cache
fn access_both<'db>(db: &'db DatabaseLock) -> CacheLock<'db> {
    let db_guard = db.0.lock().unwrap();
    // Can only create CacheLock if db is locked
    CacheLock(Mutex::new(Cache::new()), PhantomData)
}
```

**Benefits**:
- Prevents deadlocks statically or at runtime
- Clear documentation of lock hierarchy
- Easier to reason about locking

### Pattern 7: Happens-Before Visualization

**When to use**:
- Understanding complex synchronization patterns
- Debugging subtle race conditions
- Teaching concurrency concepts

```python
# Lamport timestamps for happens-before tracking
import threading

class LamportClock:
    def __init__(self):
        self.time = 0
        self.lock = threading.Lock()

    def increment(self):
        with self.lock:
            self.time += 1
            return self.time

    def update(self, received_time):
        with self.lock:
            self.time = max(self.time, received_time) + 1
            return self.time

# Usage in distributed system or multi-threaded app
clock = LamportClock()

def thread_a():
    timestamp = clock.increment()
    print(f"Thread A event at time {timestamp}")
    send_message(timestamp)

def thread_b():
    received_time = receive_message()
    timestamp = clock.update(received_time)
    print(f"Thread B event at time {timestamp}")
    # If timestamp_b > timestamp_a, A happened-before B
```

**Visualization Tools**:
- **ThreadSanitizer reports**: Show conflicting access backtraces
- **Chrome Trace Viewer**: JSON trace format for timeline visualization
- **Perfetto**: Advanced trace visualization for performance and concurrency

**Benefits**:
- Makes implicit synchronization explicit
- Helps identify missing synchronization
- Useful for distributed systems debugging

### Pattern 8: Rust Async Concurrency Debugging

**When to use**:
- Debugging Rust async/await code (Tokio, async-std)
- Detecting data races in async contexts
- Analyzing task scheduling issues

```rust
// ❌ Data race in async code
use std::sync::Arc;

async fn buggy_counter(counter: Arc<i32>) {
    // ❌ Arc provides shared ownership, not synchronization
    let val = *counter;
    tokio::time::sleep(tokio::time::Duration::from_millis(1)).await;
    // Race: multiple tasks may read/write simultaneously
}

// ✅ Fixed with Mutex
use tokio::sync::Mutex;

async fn safe_counter(counter: Arc<Mutex<i32>>) {
    let mut val = counter.lock().await;
    *val += 1;
    // Lock released when `val` goes out of scope
}
```

**Tokio Console** (runtime inspection):
```bash
# Add to Cargo.toml
# [dependencies]
# console-subscriber = "0.1"

# In main.rs
console_subscriber::init();

# Run tokio-console
tokio-console
```

**Benefits**:
- Real-time task inspection
- Detects blocking in async contexts
- Shows task spawn/completion timeline

---

## Quick Reference

### Tool Selection by Use Case

```
Use Case                    | Tool                | Overhead  | Recompile | Platform
----------------------------|---------------------|-----------|-----------|----------
C/C++ race detection        | ThreadSanitizer     | 5-15x     | Yes       | All
C/C++ no recompile          | Helgrind            | 10-30x    | No        | Linux
Go race detection           | go run -race        | 2-10x     | No        | All
Rust race detection         | cargo test          | <2x       | No        | All
Windows/Linux GUI           | Intel Inspector     | 10-20x    | No        | Win/Linux
Deadlock analysis           | GDB, thread dumps   | N/A       | No        | All
Async Rust debugging        | Tokio Console       | Low       | No        | All
Lock ordering               | Custom framework    | Minimal   | Yes       | All
```

### Key Guidelines

```
✅ DO: Use -race in all Go tests (go test -race)
✅ DO: Enable TSan in CI for C/C++ projects
✅ DO: Enforce global lock ordering to prevent deadlocks
✅ DO: Use atomic operations for simple counters/flags
✅ DO: Prefer channels/message-passing over shared memory
✅ DO: Test concurrent code with thread count > CPU cores
✅ DO: Use happens-before annotations for custom sync primitives

❌ DON'T: Ignore race warnings (even if tests pass)
❌ DON'T: Use sleep() to "fix" race conditions
❌ DON'T: Assume data races are benign
❌ DON'T: Disable race detector to speed up tests
❌ DON'T: Mix TSan and ASan (incompatible)
❌ DON'T: Use raw atomics without understanding memory ordering
❌ DON'T: Deploy race detector builds to production (overhead)
```

---

## Anti-Patterns

### Critical Violations

```c++
// ❌ NEVER: Use sleep to avoid races
void broken_sync() {
    shared_data = 42;
    std::this_thread::sleep_for(std::chrono::milliseconds(10));
    // ❌ Race: another thread may access before sleep completes
}

// ✅ CORRECT: Use proper synchronization
std::mutex mtx;
void correct_sync() {
    std::lock_guard<std::mutex> lock(mtx);
    shared_data = 42;  // Protected by mutex
}
```

❌ **Sleep-based synchronization**: Hides races, doesn't fix them
✅ **Correct approach**: Use mutexes, atomics, or channels

### Common Mistakes

```go
// ❌ Don't: Ignore race detector warnings
// $ go test -race
// WARNING: DATA RACE
// ... but tests pass, so ship it ❌

// ✅ Correct: Fix all races before merge
// Races are undefined behavior, may manifest in production
```

❌ **Ignoring race warnings**: "Works on my machine" until production
✅ **Better**: Treat race warnings as build failures

```c++
// ❌ Don't: Assume volatile fixes races
volatile int flag = 0;  // ❌ Doesn't prevent race

void thread1() { flag = 1; }
void thread2() { if (flag) { /* ... */ } }

// ✅ Correct: Use std::atomic
std::atomic<int> flag{0};

void thread1() { flag.store(1, std::memory_order_release); }
void thread2() {
    if (flag.load(std::memory_order_acquire)) { /* ... */ }
}
```

❌ **Volatile for synchronization**: Doesn't provide atomicity or ordering
✅ **Better**: Use std::atomic with memory ordering semantics

```python
# ❌ Don't: Assume Python GIL prevents all races
shared_list = []

def thread1():
    shared_list.append(1)  # ❌ Not atomic despite GIL

def thread2():
    shared_list.append(2)  # ❌ Race on internal list state

# ✅ Correct: Use thread-safe structures
import queue
shared_queue = queue.Queue()

def thread1():
    shared_queue.put(1)  # ✅ Thread-safe

def thread2():
    shared_queue.put(2)  # ✅ Thread-safe
```

❌ **Assuming GIL prevents races**: GIL doesn't protect data structures
✅ **Better**: Use queue.Queue, threading.Lock, or concurrent.futures

---

## Related Skills

- `testing/integration-testing.md` - Race detectors integrate into integration tests
- `observability/distributed-tracing.md` - Happens-before in distributed systems
- `plt/rust-memory-safety.md` - Rust ownership prevents many races at compile-time
- `debugging/memory-leak-debugging.md` - Races can cause memory leaks
- `debugging/crash-debugging.md` - Races often manifest as crashes
- `cicd/testing-strategy.md` - Enable race detection in CI pipelines

---

**Last Updated**: 2025-10-26
**Format Version**: 1.0 (Atomic)
