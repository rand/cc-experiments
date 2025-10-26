---
name: debugging-crash-debugging
description: Signal handling, crash reproduction, fuzzing for crash discovery, telemetry aggregation, and post-mortem workflows
---

# Crash Debugging

**Scope**: Signal handling (SIGSEGV, SIGABRT), backtrace generation, crash reproduction, fuzzing (AFL, libFuzzer), crash telemetry
**Lines**: ~410
**Last Updated**: 2025-10-26
**Format Version**: 1.0 (Atomic)

---

## When to Use This Skill

Activate this skill when:
- Application crashes unexpectedly (SIGSEGV, SIGABRT, SIGFPE)
- Need to reproduce crashes from bug reports
- Setting up crash telemetry and aggregation
- Implementing signal handlers for graceful crash reporting
- Using fuzzing to discover crash-inducing inputs
- Debugging null pointer dereferences or memory corruption
- Investigating stack overflow or assertion failures
- Building post-mortem debugging workflows

---

## Core Concepts

### Concept 1: Common Crash Signals

**Signal Types and Causes**:

| Signal | Name | Common Causes |
|--------|------|---------------|
| SIGSEGV | Segmentation Fault | Null pointer, invalid memory access, buffer overflow |
| SIGABRT | Abort | assert() failure, std::abort(), memory corruption detected |
| SIGFPE | Floating Point Exception | Division by zero, integer overflow (signed) |
| SIGILL | Illegal Instruction | Corrupted code, wrong architecture binary |
| SIGBUS | Bus Error | Misaligned memory access, mmap failure |
| SIGSTKFLT | Stack Fault | Stack overflow (rare on modern systems) |

**Default Signal Behavior**:
- Terminate process
- Generate core dump (if enabled)
- No cleanup or logging

```c
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>

void signal_handler(int sig) {
    fprintf(stderr, "Caught signal %d (%s)\n", sig, strsignal(sig));
    // Log crash, generate backtrace, cleanup resources
    exit(1);
}

int main() {
    // Install signal handlers
    signal(SIGSEGV, signal_handler);
    signal(SIGABRT, signal_handler);
    signal(SIGFPE, signal_handler);

    // Application code
    return 0;
}
```

### Concept 2: Stack Unwinding and Backtraces

**Backtrace Generation** (capturing call stack):

```c
// Linux: backtrace() from execinfo.h
#include <execinfo.h>
#include <stdio.h>
#include <stdlib.h>
#include <signal.h>

void print_backtrace() {
    void *array[20];
    size_t size = backtrace(array, 20);
    char **strings = backtrace_symbols(array, size);

    fprintf(stderr, "Backtrace (%zd frames):\n", size);
    for (size_t i = 0; i < size; i++) {
        fprintf(stderr, "  %s\n", strings[i]);
    }

    free(strings);
}

void crash_handler(int sig) {
    fprintf(stderr, "ERROR: Signal %d (%s)\n", sig, strsignal(sig));
    print_backtrace();
    exit(1);
}

int main() {
    signal(SIGSEGV, crash_handler);
    signal(SIGABRT, crash_handler);

    // Trigger crash for testing
    int *ptr = NULL;
    *ptr = 42;  // SIGSEGV
}
```

**C++ Stack Unwinding** (std::stacktrace in C++23):
```cpp
#include <stacktrace>
#include <iostream>

void crash_handler(int sig) {
    std::cerr << "Caught signal " << sig << "\n";
    std::cerr << std::stacktrace::current() << "\n";
    std::exit(1);
}
```

**Benefits**:
- Immediate crash context (call stack)
- Helps identify root cause quickly
- Works without debugger

### Concept 3: Crash Reproduction Strategies

**Reproduction Categories**:

1. **Deterministic crashes**: Same input always crashes
   - Example: Null pointer dereference on specific API call
   - Strategy: Capture input, replay in test

2. **Non-deterministic crashes**: Timing or state-dependent
   - Example: Race condition, uninitialized memory
   - Strategy: Stress testing, record-replay, sanitizers

3. **Environmental crashes**: Specific to environment
   - Example: Out-of-memory, file descriptor exhaustion
   - Strategy: Reproduce constraints (memory limits, resource limits)

**Minimal Reproduction**:
```python
# ❌ Bug report: "App crashes when processing data"
# Not reproducible (what data? what operation?)

# ✅ Minimal reproduction
import app

# Trigger crash with minimal input
data = {"user_id": None}  # Null user_id causes crash
app.process(data)  # Crashes on data["user_id"].lower()

# Root cause: No null check before string method
# Fix: Add null check or use data.get("user_id", "")
```

---

## Patterns

### Pattern 1: Comprehensive Signal Handler (Linux)

**When to use**:
- Production applications requiring crash reporting
- Need backtraces and context before process termination
- Resource cleanup before crash

```c
#include <signal.h>
#include <execinfo.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <time.h>

static void write_crash_log(int sig, void *addr) {
    char filename[256];
    time_t now = time(NULL);
    snprintf(filename, sizeof(filename), "/var/log/crash_%ld.log", (long)now);

    FILE *f = fopen(filename, "w");
    if (!f) {
        f = stderr;
    }

    fprintf(f, "=== CRASH REPORT ===\n");
    fprintf(f, "Signal: %d (%s)\n", sig, strsignal(sig));
    fprintf(f, "Fault address: %p\n", addr);
    fprintf(f, "PID: %d\n", getpid());
    fprintf(f, "Timestamp: %ld\n", now);

    // Backtrace
    void *array[50];
    size_t size = backtrace(array, 50);
    fprintf(f, "\nBacktrace (%zd frames):\n", size);
    backtrace_symbols_fd(array, size, fileno(f));

    if (f != stderr) {
        fclose(f);
    }
}

void crash_handler(int sig, siginfo_t *info, void *context) {
    // Write crash log
    write_crash_log(sig, info->si_addr);

    // Cleanup resources (be careful: limited operations safe in signal handler)
    // - Close log files
    // - Flush buffers
    // - Release critical locks (if safe)

    // Re-raise signal with default handler to generate core dump
    signal(sig, SIG_DFL);
    raise(sig);
}

void setup_crash_handlers() {
    struct sigaction sa;
    sa.sa_flags = SA_SIGINFO;
    sa.sa_sigaction = crash_handler;
    sigemptyset(&sa.sa_mask);

    sigaction(SIGSEGV, &sa, NULL);
    sigaction(SIGABRT, &sa, NULL);
    sigaction(SIGFPE, &sa, NULL);
    sigaction(SIGILL, &sa, NULL);
    sigaction(SIGBUS, &sa, NULL);
}

int main() {
    setup_crash_handlers();
    // Application code
}
```

**Signal Handler Safety**:
- Only async-signal-safe functions allowed (write, _exit, etc.)
- Avoid: malloc, printf, locks (may deadlock)
- Keep handler minimal (log and exit)

**Benefits**:
- Captures crash context automatically
- Logs to persistent storage
- Generates core dump after logging

### Pattern 2: C++ Exception to Signal Translation

**When to use**:
- C++ applications with both exceptions and crashes
- Need uniform crash handling for exceptions and signals
- Catching unhandled exceptions

```cpp
#include <exception>
#include <signal.h>
#include <execinfo.h>
#include <iostream>

void signal_handler(int sig) {
    std::cerr << "Signal " << sig << " caught\n";

    void *array[20];
    size_t size = backtrace(array, 20);
    backtrace_symbols_fd(array, size, STDERR_FILENO);

    std::abort();  // Generate core dump
}

void terminate_handler() {
    std::cerr << "Unhandled exception caught\n";

    // Rethrow to get exception details
    try {
        std::exception_ptr eptr = std::current_exception();
        if (eptr) {
            std::rethrow_exception(eptr);
        }
    } catch (const std::exception &e) {
        std::cerr << "Exception: " << e.what() << "\n";
    } catch (...) {
        std::cerr << "Unknown exception\n";
    }

    void *array[20];
    size_t size = backtrace(array, 20);
    backtrace_symbols_fd(array, size, STDERR_FILENO);

    std::abort();
}

int main() {
    // Install handlers
    std::set_terminate(terminate_handler);
    signal(SIGSEGV, signal_handler);
    signal(SIGABRT, signal_handler);

    // Application code
}
```

**Benefits**:
- Unified crash handling (exceptions + signals)
- Exception details in crash logs
- Backtrace for unhandled exceptions

### Pattern 3: Fuzzing with AFL (American Fuzzy Lop)

**When to use**:
- Discovering crash-inducing inputs
- Security testing (buffer overflows, format string bugs)
- Regression testing (ensure no new crashes)

```bash
# Install AFL++
git clone https://github.com/AFLplusplus/AFLplusplus
cd AFLplusplus
make
sudo make install

# Compile target with AFL instrumentation
afl-gcc -g -O0 -fsanitize=address target.c -o target
# Or with afl-clang-fast for better performance:
afl-clang-fast -g -O0 -fsanitize=address target.c -o target

# Prepare input corpus (seed inputs)
mkdir input_corpus
echo "test input" > input_corpus/seed1.txt

# Run fuzzer
afl-fuzz -i input_corpus -o output -- ./target @@
# @@ is replaced with path to generated input file

# AFL output:
# - output/crashes/     → Inputs that caused crashes
# - output/hangs/       → Inputs that caused timeouts
# - output/queue/       → Interesting inputs (code coverage)

# Reproduce crash
./target output/crashes/id:000000,sig:11,src:000000,op:flip1,pos:0
```

**Example Fuzz Target**:
```c
// target.c - vulnerable program
#include <stdio.h>
#include <string.h>

int main(int argc, char **argv) {
    if (argc != 2) {
        return 1;
    }

    FILE *f = fopen(argv[1], "r");
    if (!f) {
        return 1;
    }

    char buffer[16];
    // ❌ Vulnerable: no bounds check
    fscanf(f, "%s", buffer);  // Buffer overflow if input > 15 chars

    printf("Read: %s\n", buffer);
    fclose(f);
    return 0;
}
```

**Benefits**:
- Automatic crash discovery
- Code coverage-guided fuzzing (explores code paths)
- Finds edge cases humans miss

### Pattern 4: Fuzzing with libFuzzer (LLVM)

**When to use**:
- In-process fuzzing (faster than AFL)
- C/C++ library fuzzing
- Integration with sanitizers (ASan, UBSan)

```cpp
// fuzz_target.cpp
#include <stdint.h>
#include <stddef.h>

// Fuzz entry point (called by libFuzzer)
extern "C" int LLVMFuzzerTestOneInput(const uint8_t *data, size_t size) {
    if (size < 4) {
        return 0;  // Ignore small inputs
    }

    // Call function under test
    process_data(data, size);

    return 0;  // Non-zero = error (stop fuzzing)
}
```

**Compile and Run**:
```bash
# Compile with libFuzzer and ASan
clang++ -g -O1 -fsanitize=fuzzer,address fuzz_target.cpp -o fuzz_target

# Run fuzzer
./fuzz_target

# LibFuzzer output:
# #1      INITED cov: 42 ft: 56 corp: 1/1b exec/s: 0 rss: 30Mb
# #2      NEW    cov: 45 ft: 59 corp: 2/2b exec/s: 0 rss: 30Mb
# ...
# ==12345==ERROR: AddressSanitizer: heap-buffer-overflow
# (Crash found, corpus saved)

# Reproduce crash
./fuzz_target crash-<hash>
```

**Benefits**:
- Fast (in-process, no exec overhead)
- Excellent sanitizer integration
- Built into LLVM/Clang

**Limitations**:
- Requires source code modifications
- In-process only (no stdin fuzzing)

### Pattern 5: Crash Telemetry Aggregation

**When to use**:
- Production applications with many users
- Need crash statistics and trends
- Prioritizing bug fixes by crash frequency

```python
# Using Sentry for crash aggregation
import sentry_sdk

sentry_sdk.init(
    dsn="https://example@o0.ingest.sentry.io/0",
    environment="production",
    release="myapp@1.0.0",
)

# Automatic crash reporting
def main():
    # Crashes automatically reported with:
    # - Stack trace
    # - Environment (OS, Python version)
    # - Release version
    # - User context (if set)
    risky_operation()  # If this crashes, Sentry captures it

# Sentry dashboard shows:
# - Crash count by version
# - Top crashing functions
# - User impact (unique users affected)
# - Trends (new vs. recurring crashes)
```

**Crash Grouping**:
- Sentry groups crashes by stack trace similarity
- Same bug from multiple users → one issue
- New crashes flagged as regressions

**Benefits**:
- Prioritize fixes by user impact
- Track crash-free user rate
- Identify platform-specific crashes

### Pattern 6: Deterministic Crash Reproduction

**When to use**:
- Bug reports from production crashes
- Need reliable crash reproduction for debugging
- Writing regression tests

```python
# Crash report from production:
# Stack trace shows: process_message() → parse_json() → crash

# Step 1: Extract minimal failing input
def test_crash_reproduction():
    # From logs: "Processing message: {id:123,name:null}"
    message = '{"id": 123, "name": null}'

    # Reproduce crash
    with pytest.raises(AttributeError):
        process_message(message)  # Crashes on name.lower()

# Step 2: Fix bug
def process_message_fixed(msg):
    data = json.loads(msg)
    # ✅ Add null check
    name = data.get("name") or ""
    return name.lower()

# Step 3: Regression test
def test_null_name_handling():
    message = '{"id": 123, "name": null}'
    result = process_message_fixed(message)
    assert result == ""  # No crash
```

**Crash Reproduction Checklist**:
1. Capture input that triggers crash (from logs, telemetry)
2. Minimize input (remove irrelevant data)
3. Write failing test that reproduces crash
4. Fix bug
5. Verify test passes
6. Commit test as regression prevention

**Benefits**:
- Prevents regressions
- Documents bug and fix
- Enables debugging without production access

### Pattern 7: Stack Overflow Detection

**When to use**:
- Debugging recursive functions
- Investigating SIGSEGV from deep call stacks
- Implementing stack depth limits

```c
#include <sys/resource.h>
#include <stdio.h>

void check_stack_limit() {
    struct rlimit rl;
    getrlimit(RLIMIT_STACK, &rl);

    printf("Stack limit: %ld bytes (soft), %ld bytes (hard)\n",
           (long)rl.rlim_cur, (long)rl.rlim_max);
}

void set_stack_limit(size_t bytes) {
    struct rlimit rl;
    rl.rlim_cur = bytes;
    rl.rlim_max = bytes;

    if (setrlimit(RLIMIT_STACK, &rl) != 0) {
        perror("setrlimit");
    }
}

// Detect stack overflow before crash
#include <ucontext.h>

void recursive_function(int depth) {
    char buffer[1024];  // Consumes stack

    // Estimate stack usage
    static void *stack_start = NULL;
    if (stack_start == NULL) {
        stack_start = &buffer;
    }

    size_t used = (char*)stack_start - (char*)&buffer;
    if (used > 1024 * 1024) {  // 1MB threshold
        fprintf(stderr, "Stack overflow risk! Depth=%d, Used=%zu\n", depth, used);
        return;  // Stop recursion
    }

    recursive_function(depth + 1);
}
```

**Rust Stack Overflow** (automatic detection):
```rust
// Rust detects stack overflow and panics
fn recursive_function(depth: u32) {
    let _buffer = [0u8; 1024];  // Stack allocation

    if depth < 1_000_000 {
        recursive_function(depth + 1);
    }
}

// Stack overflow triggers panic (not SIGSEGV)
// thread 'main' has overflowed its stack
```

**Benefits**:
- Early detection (before crash)
- Configurable stack limits
- Graceful degradation

### Pattern 8: Post-Mortem Debugging Workflow

**When to use**:
- Production crash analysis
- Structured approach to crash investigation
- Team crash triage process

```
Crash Workflow:
1. Capture crash report (telemetry, logs, core dump)
2. Symbolicate stack trace (match symbols to binary version)
3. Identify crash signature (function, file, line)
4. Search for existing issues (check if known bug)
5. Reproduce crash (minimal test case)
6. Analyze root cause (memory, logic, race condition)
7. Fix and test
8. Deploy fix and verify (monitor crash rate)
9. Document (RCA, post-mortem)
```

**Crash Triage Template**:
```markdown
## Crash Report: SIGSEGV in process_request()

**Signature**: `process_request() → parse_header() → strlen(NULL)`

**Stack Trace**:
```
#0 strlen() at /lib/x86_64-linux-gnu/libc.so.6
#1 parse_header(header=0x0) at server.c:123
#2 process_request(req=0x7f1234567890) at server.c:89
```

**Root Cause**: NULL pointer passed to parse_header()

**Impact**: 142 crashes in last 24h (0.3% of requests)

**Fix**: Add null check before strlen()

**Test**: Added regression test in test_null_header()

**Deployed**: v1.2.1 (2025-10-26)

**Verification**: Zero crashes in 48h post-deployment
```

**Benefits**:
- Structured investigation
- Knowledge sharing (team-wide)
- Prevents duplicate debugging effort

---

## Quick Reference

### Signal Quick Reference

```
Signal    | Meaning                  | Common Cause
----------|--------------------------|---------------------------
SIGSEGV   | Segmentation Fault       | NULL deref, buffer overflow
SIGABRT   | Abort                    | assert(), abort()
SIGFPE    | Floating Point Exception | Division by zero
SIGILL    | Illegal Instruction      | Corrupted binary
SIGBUS    | Bus Error                | Misaligned access
SIGSTKFLT | Stack Fault              | Stack overflow
```

### Fuzzing Tool Comparison

```
Tool      | Type        | Speed   | Setup      | Best For
----------|-------------|---------|------------|------------------
AFL++     | File-based  | Medium  | Easy       | Programs reading files
libFuzzer | In-process  | Fast    | Moderate   | Libraries, APIs
Honggfuzz | Hybrid      | Fast    | Easy       | Multi-threaded apps
OSS-Fuzz  | Continuous  | N/A     | Complex    | Open-source projects
```

### Key Guidelines

```
✅ DO: Install signal handlers in production (logging, cleanup)
✅ DO: Generate backtraces on crashes (execinfo.h, std::stacktrace)
✅ DO: Integrate crash telemetry (Sentry, Crashlytics)
✅ DO: Write regression tests for all crashes
✅ DO: Fuzz critical parsers and input handlers
✅ DO: Symbolicate stack traces (match binary version)
✅ DO: Set stack limits to detect overflow early

❌ DON'T: Ignore crashes in testing (fix before production)
❌ DON'T: Use unsafe operations in signal handlers (malloc, locks)
❌ DON'T: Deploy without crash reporting infrastructure
❌ DON'T: Assume crashes are user error (investigate all)
❌ DON'T: Skip fuzzing security-critical code
❌ DON'T: Delete crash logs before analysis
```

---

## Anti-Patterns

### Critical Violations

```c
// ❌ NEVER: Empty signal handler (hides crashes)
void signal_handler(int sig) {
    // Do nothing - crash ignored!
}

// ✅ CORRECT: Log and abort
void signal_handler(int sig) {
    write(STDERR_FILENO, "CRASH\n", 6);
    signal(sig, SIG_DFL);
    raise(sig);  // Re-raise to generate core dump
}
```

❌ **Ignoring crashes**: Masks bugs, leads to data corruption
✅ **Correct approach**: Log, cleanup, generate core dump

### Common Mistakes

```python
# ❌ Don't: Generic exception handling (hides crashes)
try:
    process_data(user_input)
except Exception:
    pass  # ❌ Silently ignores all errors

# ✅ Correct: Catch specific exceptions, log unknown
try:
    process_data(user_input)
except ValueError as e:
    logger.warning(f"Invalid input: {e}")
except Exception as e:
    logger.error(f"Unexpected error: {e}", exc_info=True)
    sentry_sdk.capture_exception(e)
    raise  # Re-raise unexpected errors
```

❌ **Broad exception suppression**: Hides bugs, makes debugging impossible
✅ **Better**: Catch specific exceptions, log and report unknown

```cpp
// ❌ Don't: Allocate memory in signal handler
void crash_handler(int sig) {
    std::string msg = "Crash!";  // ❌ Allocates memory (unsafe)
    std::cout << msg << std::endl;  // ❌ Not async-signal-safe
}

// ✅ Correct: Use only async-signal-safe functions
void crash_handler(int sig) {
    const char msg[] = "Crash!\n";
    write(STDERR_FILENO, msg, sizeof(msg) - 1);  // ✅ Safe
    _exit(1);  // ✅ Safe (unlike exit())
}
```

❌ **Unsafe signal handlers**: May deadlock or corrupt state
✅ **Better**: Use only async-signal-safe functions (write, _exit)

---

## Related Skills

- `debugging/core-dump-analysis.md` - Analyzing core dumps from crashes
- `debugging/memory-leak-debugging.md` - Memory corruption causes crashes
- `debugging/concurrency-debugging.md` - Race conditions cause crashes
- `testing/integration-testing.md` - Crash reproduction in tests
- `observability/structured-logging.md` - Crash context in logs
- `cicd/testing-strategy.md` - Fuzzing in CI pipelines

---

**Last Updated**: 2025-10-26
**Format Version**: 1.0 (Atomic)
