---
name: debugging-core-dump-analysis
description: Core dump generation, GDB/LLDB analysis, crash reporting, and post-mortem debugging across platforms
---

# Core Dump Analysis

**Scope**: Generating core dumps, analyzing with GDB/LLDB, symbol files, automated crash reporting (Sentry, Crashlytics)
**Lines**: ~420
**Last Updated**: 2025-10-26
**Format Version**: 1.0 (Atomic)

---

## When to Use This Skill

Activate this skill when:
- Application crashed and left a core dump
- Need post-mortem debugging of production crashes
- Setting up automated crash reporting infrastructure
- Analyzing segmentation faults or unexpected terminations
- Investigating crashes from customer reports
- Configuring core dump generation on Linux/macOS
- Debugging Python crashes with faulthandler
- Integrating Sentry, Crashlytics, or similar crash telemetry

---

## Core Concepts

### Concept 1: Core Dump Basics

**What is a Core Dump?**:
- Snapshot of process memory at crash time
- Contains: stack, heap, registers, threads, open files
- Platform-specific format: ELF core (Linux), Mach-O core (macOS), minidump (Windows)

**When Core Dumps Are Generated**:
- Segmentation fault (SIGSEGV)
- Abort signal (SIGABRT)
- Floating point exception (SIGFPE)
- Illegal instruction (SIGILL)
- Manual signal: `kill -ABRT <pid>`

**Core Dump Location**:
```bash
# Linux: Check core pattern
cat /proc/sys/kernel/core_pattern
# Common values:
# core                      → core in CWD
# core.%p                   → core.<pid> in CWD
# /var/crash/core.%p.%e     → systemd-coredump location

# macOS: Core dumps in /cores/
ls -lh /cores/

# Set core size limit (0 = disabled)
ulimit -c unlimited  # Enable unlimited core dumps
ulimit -c 0          # Disable core dumps
```

### Concept 2: Debug Symbols

**Symbol Files**:
- Map binary addresses to source code locations
- Contain function names, line numbers, variable names
- Separate from binary (`.debug`, `.dSYM`, `.pdb`)

**Symbol Types**:
- **Full debug info**: Compiled with `-g`, includes all symbols
- **Stripped binaries**: Release builds, symbols removed (smaller size)
- **Separate debug info**: Symbols in separate file, binary stripped

```bash
# Check if binary has symbols (Linux)
file ./app
# with debug: ELF 64-bit LSB executable, not stripped
# without:    ELF 64-bit LSB executable, stripped

# Extract debug info (Linux)
objcopy --only-keep-debug app app.debug
objcopy --strip-debug app
objcopy --add-gnu-debuglink=app.debug app

# macOS debug symbols (.dSYM)
dsymutil app -o app.dSYM
strip app  # Remove symbols from binary

# Load symbols in GDB
(gdb) symbol-file app.debug
```

### Concept 3: Stack Unwinding

**Call Stack Reconstruction**:
- Core dump preserves stack frames
- Debugger unwinds stack to show call chain
- Requires frame pointers or DWARF debug info

**Frame Pointer Optimization**:
```bash
# Compile with frame pointers (easier unwinding)
gcc -fno-omit-frame-pointer -g app.c -o app

# Without -fno-omit-frame-pointer, debugger may fail to unwind
# (common in optimized builds: -O2, -O3)
```

**Inline Functions Challenge**:
- Optimized builds inline small functions
- Stack traces show caller, not inlined function
- Partial solution: `-Og` (optimize for debugging)

---

## Patterns

### Pattern 1: Enabling Core Dumps on Linux

**When to use**:
- Production servers (crash analysis)
- Development environments (debugging crashes)
- CI/CD for crash regression tests

```bash
# Enable core dumps for current shell session
ulimit -c unlimited

# Persist across reboots (systemd)
sudo mkdir -p /etc/systemd/system.conf.d/
cat <<EOF | sudo tee /etc/systemd/system.conf.d/coredump.conf
[Manager]
DefaultLimitCORE=infinity
EOF

sudo systemctl daemon-reexec

# Configure core pattern (where cores are saved)
echo '/var/crash/core.%e.%p.%t' | sudo tee /proc/sys/kernel/core_pattern

# Explanation:
# %e = executable name
# %p = process ID
# %t = timestamp (seconds since epoch)
# %h = hostname
# %s = signal number

# Verify configuration
ulimit -c
# unlimited

cat /proc/sys/kernel/core_pattern
# /var/crash/core.%e.%p.%t
```

**Systemd-coredump Integration**:
```bash
# Modern systems use systemd-coredump
coredumpctl list

# Show specific core dump
coredumpctl info 12345

# Extract core dump
coredumpctl dump 12345 > core.12345

# Debug directly
coredumpctl debug 12345
```

**Benefits**:
- Automatic crash capture
- Persistent configuration
- Centralized crash storage

### Pattern 2: GDB Core Dump Analysis

**When to use**:
- Analyzing core dumps from Linux crashes
- Post-mortem debugging without live process
- Extracting crash backtraces and variables

```bash
# Load core dump in GDB
gdb /path/to/app /path/to/core

# Alternative: attach core to matching binary
gdb -c core ./app

# Inside GDB session:
(gdb) bt              # Show backtrace
(gdb) bt full         # Show backtrace with local variables
(gdb) frame 3         # Switch to frame 3
(gdb) info locals     # Show local variables in current frame
(gdb) info args       # Show function arguments
(gdb) print var_name  # Print specific variable
(gdb) x/20x $rsp      # Examine stack memory (20 hex values)

# Multi-threaded crashes
(gdb) info threads    # List all threads
(gdb) thread 2        # Switch to thread 2
(gdb) thread apply all bt  # Backtrace for all threads
```

**Example Analysis Session**:
```bash
$ gdb ./myapp core.12345

Reading symbols from ./myapp...
[New LWP 12345]
Core was generated by `./myapp --config prod.conf'.
Program terminated with signal SIGSEGV, Segmentation fault.
#0  0x0000000000401234 in process_request (req=0x0) at server.c:142
142         int status = req->status;  // ❌ req is NULL

(gdb) bt
#0  0x0000000000401234 in process_request (req=0x0) at server.c:142
#1  0x0000000000401567 in handle_connection (conn=0x7f1234567890) at server.c:89
#2  0x0000000000401890 in worker_thread (arg=0x601040) at server.c:56
#3  0x00007f1234567890 in start_thread () from /lib/x86_64-linux-gnu/libpthread.so.0

(gdb) frame 1
#1  0x0000000000401567 in handle_connection (conn=0x7f1234567890) at server.c:89
89          process_request(conn->current_req);

(gdb) print conn->current_req
$1 = (Request *) 0x0  // ❌ NULL pointer, bug found!

(gdb) print conn
$2 = (Connection *) 0x7f1234567890

(gdb) print *conn
$3 = {socket_fd = 42, current_req = 0x0, state = CONNECTED}
```

**Benefits**:
- Full access to crash state
- Examine all variables and memory
- Multi-threaded crash analysis

### Pattern 3: LLDB Core Dump Analysis (macOS)

**When to use**:
- Analyzing macOS crash reports
- Debugging core dumps from Mach-O binaries
- Integration with Xcode crash logs

```bash
# macOS core dumps location
ls -lh /cores/

# Load core dump in LLDB
lldb -c /cores/core.12345 ./app

# LLDB commands (similar to GDB but different syntax)
(lldb) bt                    # Backtrace
(lldb) bt all                # All threads
(lldb) frame select 2        # Switch to frame 2
(lldb) frame variable        # Show local variables
(lldb) frame variable var_name  # Show specific variable
(lldb) thread list           # List threads
(lldb) thread select 3       # Switch to thread 3
(lldb) memory read $rsp      # Examine stack

# Image (symbol) commands
(lldb) image list            # Show loaded libraries
(lldb) image lookup -a 0x401234  # Find symbol at address
(lldb) image lookup -n main  # Find main function
```

**macOS Crash Reports** (.crash files):
```bash
# System crash reports
ls ~/Library/Logs/DiagnosticReports/
ls /Library/Logs/DiagnosticReports/

# Symbolicate crash report (convert addresses to symbols)
# Requires .dSYM file matching binary UUID
symbolicatecrash crash.log app.dSYM > symbolicated.log

# Atos: Address to symbol translation
atos -o app.dSYM/Contents/Resources/DWARF/app -arch x86_64 -l 0x100000000 0x100001234
# Output: main (in app) (app.c:42)
```

**Benefits**:
- Native macOS/iOS debugging
- Integration with Xcode
- Automatic crash report collection

### Pattern 4: Python Core Dumps with faulthandler

**When to use**:
- Python segmentation faults (C extension crashes)
- Debugging Python native extension issues
- Production Python crash diagnostics

```python
# Enable faulthandler at startup
import faulthandler
faulthandler.enable(file=open('/var/log/python_crashes.log', 'a'))

# Dump traceback on SIGUSR1 signal
import signal
faulthandler.register(signal.SIGUSR1, file=open('/tmp/backtrace.txt', 'w'))

# Trigger backtrace from outside process
# kill -SIGUSR1 <python_pid>

# Dump traceback after timeout (detect hangs)
faulthandler.dump_traceback_later(timeout=300, repeat=False, file=sys.stderr)

# Example crash output:
# Fatal Python error: Segmentation fault
#
# Current thread 0x00007f1234567890 (most recent call first):
#   File "mymodule.pyx", line 42 in mymodule.process_data
#   File "app.py", line 123 in main
#   File "app.py", line 156 in <module>
```

**PyStack** (Python stack trace from core dump):
```bash
# Install pystack
pip install pystack

# Analyze Python process core dump
pystack core /path/to/python /path/to/core.12345

# Attach to running Python process
sudo pystack remote --pid 12345

# Example output:
# Thread 0x7f1234567890 (most recent call first):
#     File "app.py", line 42, in process_request
#     File "app.py", line 89, in handle_connection
#     File "threading.py", line 890, in run
```

**Benefits**:
- Catches crashes from C extensions
- Works with native Python code
- Lightweight (minimal overhead)

### Pattern 5: Automated Crash Reporting (Sentry)

**When to use**:
- Production crash telemetry and aggregation
- Multi-platform applications (Python, Node, Go, Rust, etc.)
- Need dashboards and alerting for crashes

```python
# Install Sentry SDK
# pip install sentry-sdk

import sentry_sdk

# Initialize Sentry
sentry_sdk.init(
    dsn="https://examplePublicKey@o0.ingest.sentry.io/0",
    environment="production",
    release="myapp@1.2.3",
    traces_sample_rate=0.1,  # 10% of transactions traced
)

# Automatic crash reporting (unhandled exceptions)
def main():
    # Crashes automatically reported to Sentry
    raise ValueError("Something went wrong!")

# Manual error reporting
try:
    risky_operation()
except Exception as e:
    sentry_sdk.capture_exception(e)

# Add context to crashes
with sentry_sdk.configure_scope() as scope:
    scope.set_user({"id": "12345", "username": "alice"})
    scope.set_tag("server_type", "api")
    scope.set_context("request", {"url": "/api/data", "method": "POST"})

# Breadcrumbs (events leading to crash)
sentry_sdk.add_breadcrumb(
    category="auth",
    message="User authenticated",
    level="info",
)
```

**Sentry Features**:
- Automatic crash grouping by stack trace
- Source context (shows code around crash)
- Breadcrumbs (events before crash)
- Release tracking and regression detection
- Alerting (email, Slack, PagerDuty)

**Benefits**:
- Centralized crash aggregation
- Real-time alerting
- Rich context (user, tags, breadcrumbs)
- Multi-platform support

### Pattern 6: Crashlytics for Mobile Apps

**When to use**:
- iOS/Android crash reporting
- Mobile app telemetry
- Firebase integration

```swift
// iOS: Firebase Crashlytics
import FirebaseCrashlytics

// Enable Crashlytics
FirebaseApp.configure()

// Record non-fatal errors
Crashlytics.crashlytics().record(error: error)

// Set user identifier
Crashlytics.crashlytics().setUserID("12345")

// Custom keys (context)
Crashlytics.crashlytics().setCustomValue("premium", forKey: "user_tier")

// Log messages (breadcrumbs)
Crashlytics.crashlytics().log("User tapped checkout button")

// Force crash for testing
fatalError("Test crash")  // Reported to Crashlytics
```

```kotlin
// Android: Firebase Crashlytics
import com.google.firebase.crashlytics.FirebaseCrashlytics

// Get Crashlytics instance
val crashlytics = FirebaseCrashlytics.getInstance()

// Record non-fatal exceptions
crashlytics.recordException(exception)

// Set user ID
crashlytics.setUserId("12345")

// Custom keys
crashlytics.setCustomKey("user_tier", "premium")

// Log messages
crashlytics.log("User tapped checkout button")

// Force crash (testing)
throw RuntimeException("Test crash")
```

**Benefits**:
- Automatic symbolication (dSYMs, ProGuard mappings)
- Crash-free user rate metrics
- Integration with Firebase ecosystem

### Pattern 7: Windows Minidumps

**When to use**:
- Windows application crash analysis
- Post-mortem debugging on Windows
- Customer crash report collection

```c++
// Generate minidump on Windows crash
#include <windows.h>
#include <dbghelp.h>

#pragma comment(lib, "dbghelp.lib")

LONG WINAPI UnhandledExceptionFilter(EXCEPTION_POINTERS* exceptionInfo) {
    HANDLE hFile = CreateFile(
        L"crash.dmp",
        GENERIC_WRITE,
        0,
        NULL,
        CREATE_ALWAYS,
        FILE_ATTRIBUTE_NORMAL,
        NULL
    );

    if (hFile != INVALID_HANDLE_VALUE) {
        MINIDUMP_EXCEPTION_INFORMATION mdei;
        mdei.ThreadId = GetCurrentThreadId();
        mdei.ExceptionPointers = exceptionInfo;
        mdei.ClientPointers = FALSE;

        MiniDumpWriteDump(
            GetCurrentProcess(),
            GetCurrentProcessId(),
            hFile,
            MiniDumpNormal,  // Or MiniDumpWithFullMemory for full dump
            &mdei,
            NULL,
            NULL
        );

        CloseHandle(hFile);
    }

    return EXCEPTION_EXECUTE_HANDLER;
}

int main() {
    SetUnhandledExceptionFilter(UnhandledExceptionFilter);
    // Application code
}
```

**Analyzing Minidumps**:
```bash
# Visual Studio: File > Open > Crash Dump
# Set symbol path: Tools > Options > Debugging > Symbols

# WinDbg analysis
windbg -z crash.dmp

# WinDbg commands:
# !analyze -v        # Automatic crash analysis
# k                  # Stack trace
# dv                 # Local variables
# lm                 # Loaded modules
```

**Benefits**:
- Compact crash dumps (customizable size)
- Integration with Windows debugging tools
- Symbol server support (automatic symbol download)

### Pattern 8: Symbol Servers

**When to use**:
- Deploying stripped binaries to production
- Storing debug symbols separately
- Team-wide symbol sharing

```bash
# Linux: GDB symbol server (debuginfod)
export DEBUGINFOD_URLS="https://debuginfod.elfutils.org/"
gdb ./app core  # Automatically fetches symbols

# macOS: Spotlight indexing for .dSYM
# Xcode automatically finds .dSYM files in Spotlight index

# Windows: Symbol server (Microsoft Symbol Server)
# .sympath SRV*c:\symbols*https://msdl.microsoft.com/download/symbols
# .reload /f  # Force symbol reload in WinDbg

# Custom symbol server (HTTP-based)
# Directory structure:
# /symbols/app.debug/BUILDID/app.debug
# /symbols/libfoo.so.debug/BUILDID/libfoo.so.debug

# GDB configuration:
(gdb) set debug-file-directory /path/to/symbols
(gdb) set solib-search-path /path/to/libs
```

**Benefits**:
- Smaller production binaries
- Centralized symbol storage
- Version-matched symbols

---

## Quick Reference

### Core Dump Commands

```
Platform   | Enable Cores         | Location                   | Analyzer
-----------|----------------------|----------------------------|----------
Linux      | ulimit -c unlimited  | /var/crash or CWD          | GDB
macOS      | ulimit -c unlimited  | /cores/                    | LLDB
Windows    | MiniDumpWriteDump()  | Custom (app-defined)       | WinDbg
Python     | faulthandler.enable()| /var/log or custom         | PyStack
```

### GDB/LLDB Quick Commands

```
Task                  | GDB Command            | LLDB Command
----------------------|------------------------|-------------------------
Load core dump        | gdb app core           | lldb -c core app
Show backtrace        | bt                     | bt
Backtrace all threads | thread apply all bt    | bt all
Switch frame          | frame 3                | frame select 3
Show locals           | info locals            | frame variable
Print variable        | print var              | frame variable var
Examine memory        | x/20x $rsp             | memory read $rsp
List threads          | info threads           | thread list
Switch thread         | thread 2               | thread select 2
```

### Key Guidelines

```
✅ DO: Enable core dumps in dev and production (with size limits)
✅ DO: Store symbols separately (stripped production binaries)
✅ DO: Set up automated crash reporting (Sentry, Crashlytics)
✅ DO: Preserve debug symbols for all releases
✅ DO: Use systemd-coredump for centralized crash management
✅ DO: Configure core_pattern to include PID and timestamp
✅ DO: Test crash reporting in staging before production

❌ DON'T: Ship full debug symbols to production (binary size)
❌ DON'T: Ignore crashes without symbolicated stack traces
❌ DON'T: Delete core dumps before analysis
❌ DON'T: Rely on optimized builds for debugging (use -Og)
❌ DON'T: Forget to set ulimit in production init scripts
❌ DON'T: Ignore core dumps filling disk (set size limits)
```

---

## Anti-Patterns

### Critical Violations

```bash
# ❌ NEVER: Disable core dumps globally in production
ulimit -c 0  # ❌ No crash analysis possible

# ✅ CORRECT: Enable with size limit
ulimit -c 102400  # Limit to 100MB per core
echo '/var/crash/core.%e.%p.%t' | sudo tee /proc/sys/kernel/core_pattern
```

❌ **Disabled core dumps**: No post-mortem analysis, blind to crashes
✅ **Correct approach**: Enable with size limits and rotation

### Common Mistakes

```c++
// ❌ Don't: Compile without debug symbols
g++ -O2 app.cpp -o app  // ❌ No symbols, hard to debug

// ✅ Correct: Keep symbols separate
g++ -g -O2 app.cpp -o app
objcopy --only-keep-debug app app.debug
strip app
# Deploy: app (stripped), store: app.debug (symbols)
```

❌ **No debug symbols**: Stack traces show addresses, not function names
✅ **Better**: Generate symbols, strip binary, store symbols separately

```python
# ❌ Don't: Ignore Python C extension crashes
# Crashes from C extensions produce no Python traceback

# ✅ Correct: Enable faulthandler
import faulthandler
import sys

faulthandler.enable(file=sys.stderr)
# Now crashes from C extensions show Python stack
```

❌ **No faulthandler**: C extension crashes show no Python context
✅ **Better**: Enable faulthandler at startup, log to file

```bash
# ❌ Don't: Analyze core dump without matching symbols
gdb app core.old  # ❌ Symbols don't match binary version

# ✅ Correct: Use matching binary and symbols
gdb app.v1.2.3 core.v1.2.3.12345
# Or load separate symbols:
(gdb) symbol-file app.v1.2.3.debug
```

❌ **Mismatched symbols**: Wrong line numbers, missing variables
✅ **Better**: Archive binaries and symbols per release, match by build ID

---

## Related Skills

- `debugging/crash-debugging.md` - Signal handling, crash reproduction strategies
- `observability/structured-logging.md` - Logs complement crash analysis
- `cicd/deployment-patterns.md` - Symbol archival in deployment pipelines
- `debugging/memory-leak-debugging.md` - Core dumps show heap state
- `debugging/concurrency-debugging.md` - Multi-threaded crash analysis
- `containers/docker-optimization.md` - Core dumps in containers

---

**Last Updated**: 2025-10-26
**Format Version**: 1.0 (Atomic)
