---
name: debugging-gdb-fundamentals
description: Comprehensive guide to GNU Debugger (GDB) for debugging C/C++/Rust programs. Covers breakpoints, stack traces, variable inspection, TUI mode, .gdbinit customization, Python scripting, remote debugging, and core file analysis.
---

# GDB Fundamentals

**Last Updated**: 2025-10-26

## Overview

GDB (GNU Debugger) is the standard debugger for C, C++, Rust, Go, and other compiled languages. This guide covers fundamental debugging workflows, advanced features, and best practices for effective debugging.

## Core Concepts

### GDB Architecture
```
Program (debuggee)
  ↓
ptrace() system call → GDB (debugger)
  ↓
Debug symbols (DWARF) → Source mapping
  ↓
User commands → GDB commands → ptrace() actions
```

### Debug Symbols

**Compile with debug symbols**:
```bash
# C/C++
gcc -g program.c -o program
g++ -g -O0 program.cpp -o program  # -O0 disables optimization

# Rust
cargo build  # Debug build includes symbols
cargo build --release  # No debug symbols

# Zig
zig build-exe program.zig -O Debug  # Debug symbols
```

**Check if symbols present**:
```bash
file program
# program: ELF 64-bit LSB executable, x86-64, with debug_info, not stripped

nm program | grep -i debug
objdump -h program | grep debug
```

---

## Starting GDB

### Basic Launch
```bash
# Start GDB with program
gdb ./program

# Start with arguments
gdb --args ./program arg1 arg2

# Attach to running process
gdb -p <pid>
gdb attach <pid>

# Load core dump
gdb ./program core.12345

# Quiet mode (no banner)
gdb -q ./program
```

### Batch Mode
```bash
# Run commands from file
gdb -batch -x commands.gdb ./program

# Example commands.gdb:
# break main
# run
# backtrace
# quit
```

---

## Breakpoints

### Setting Breakpoints

**Function breakpoints**:
```gdb
# Break at function entry
(gdb) break main
(gdb) b calculate_sum

# Break at C++ method
(gdb) break MyClass::method

# Break at Rust function
(gdb) break my_crate::my_function

# Conditional breakpoint
(gdb) break main if argc > 1
(gdb) b process_data if count > 100

# Temporary breakpoint (auto-delete after hit)
(gdb) tbreak main
```

**Line breakpoints**:
```gdb
# Break at line number
(gdb) break file.c:42
(gdb) b 42  # Current file

# Break at all matching functions
(gdb) rbreak ^calculate.*  # Regex: all functions starting with "calculate"
```

**Address breakpoints**:
```gdb
# Break at memory address
(gdb) break *0x400567
```

### Managing Breakpoints

```gdb
# List all breakpoints
(gdb) info breakpoints
(gdb) i b

# Disable/enable breakpoint
(gdb) disable 1
(gdb) enable 1

# Delete breakpoint
(gdb) delete 1
(gdb) d 1

# Delete all breakpoints
(gdb) delete

# Ignore breakpoint N times
(gdb) ignore 1 10  # Ignore breakpoint 1 for 10 hits
```

### Watchpoints

**Monitor variable changes**:
```gdb
# Watch variable (break when value changes)
(gdb) watch my_variable

# Watch memory location
(gdb) watch *0x7fffffffe000

# Watch expression
(gdb) watch count > 100

# Read watchpoint (break on read)
(gdb) rwatch my_variable

# Access watchpoint (break on read or write)
(gdb) awatch my_variable
```

### Catchpoints

**Break on events**:
```gdb
# Catch C++ exceptions
(gdb) catch throw
(gdb) catch catch

# Catch system calls
(gdb) catch syscall open
(gdb) catch syscall write read

# Catch signals
(gdb) catch signal SIGSEGV

# Catch library loads
(gdb) catch load libcrypto.so
```

---

## Program Control

### Running Programs

```gdb
# Start program
(gdb) run
(gdb) r

# Run with arguments
(gdb) run arg1 arg2
(gdb) set args arg1 arg2
(gdb) run

# Run with input redirection
(gdb) run < input.txt

# Run with environment variables
(gdb) set environment VAR=value
(gdb) run
```

### Stepping Through Code

```gdb
# Step into (enter functions)
(gdb) step
(gdb) s

# Step over (don't enter functions)
(gdb) next
(gdb) n

# Step one instruction
(gdb) stepi
(gdb) si

# Continue until function returns
(gdb) finish

# Continue until line
(gdb) until 50

# Continue execution
(gdb) continue
(gdb) c
```

### Advanced Control

```gdb
# Skip function during stepping
(gdb) skip function std::string::operator=

# List skipped functions
(gdb) info skip

# Return from function early
(gdb) return
(gdb) return 42  # Return with value
```

---

## Stack Inspection

### Backtraces

```gdb
# Full backtrace
(gdb) backtrace
(gdb) bt

# Backtrace with local variables
(gdb) bt full

# Limited backtrace
(gdb) bt 10  # Show 10 frames

# Backtrace all threads
(gdb) thread apply all bt
```

### Frame Navigation

```gdb
# Show current frame
(gdb) frame
(gdb) f

# Select frame by number
(gdb) frame 2
(gdb) f 2

# Move up/down stack
(gdb) up
(gdb) down
(gdb) up 3

# Show frame info
(gdb) info frame
(gdb) info locals
(gdb) info args
```

---

## Variable Inspection

### Print Variables

```gdb
# Print variable
(gdb) print my_variable
(gdb) p my_variable

# Print with format
(gdb) p/x my_variable  # Hexadecimal
(gdb) p/d my_variable  # Decimal
(gdb) p/t my_variable  # Binary
(gdb) p/c my_variable  # Character
(gdb) p/f my_variable  # Float

# Print pointer
(gdb) p *ptr
(gdb) p ptr[0]@10  # Print array of 10 elements

# Print structure
(gdb) p my_struct
(gdb) p my_struct.field
```

### Display (Auto-print)

```gdb
# Display variable every stop
(gdb) display count
(gdb) display expr

# List displays
(gdb) info display

# Delete display
(gdb) delete display 1
```

### Memory Examination

```gdb
# Examine memory
(gdb) x/10xw 0x7fffffffe000  # 10 words in hex
(gdb) x/10i $pc              # 10 instructions at PC
(gdb) x/s 0x400678           # String at address

# Format: x/[count][format][size] address
# Formats: x(hex) d(decimal) u(unsigned) o(octal) t(binary) a(address) c(char) s(string) i(instruction)
# Sizes: b(byte) h(halfword) w(word) g(giant, 8 bytes)
```

### Type Inspection

```gdb
# Show type
(gdb) ptype my_variable
(gdb) whatis my_variable

# Show type with size
(gdb) p sizeof(my_struct)
```

---

## TUI Mode (Text User Interface)

### Activation

```bash
# Start GDB in TUI mode
gdb -tui ./program

# Or within GDB:
(gdb) tui enable
(gdb) Ctrl-x Ctrl-a  # Toggle TUI mode
```

### TUI Layouts

```gdb
# Source + command
(gdb) layout src

# Assembly + command
(gdb) layout asm

# Source + assembly
(gdb) layout split

# Registers + source
(gdb) layout regs

# Cycle layouts
(gdb) Ctrl-x 2
```

### TUI Navigation

```
Ctrl-x o      # Switch active window
Ctrl-x 1      # Single window
Ctrl-x 2      # Split window
Ctrl-l        # Refresh screen
Ctrl-p/n      # Command history
PgUp/PgDn     # Scroll source window
```

---

## Advanced Features

### .gdbinit Customization

**~/.gdbinit** (global) or **./.gdbinit** (project):
```gdb
# Pretty printing
set print pretty on
set print array on
set print array-indexes on

# History
set history save on
set history size 10000
set history filename ~/.gdb_history

# Disable pagination
set pagination off

# Auto-load local .gdbinit
set auto-load safe-path /

# Custom commands
define hook-stop
    info registers
    x/24wx $sp
end

# Aliases
alias -a bp = break
alias -a c = continue
alias -a s = step
alias -a n = next
```

### Python Scripting

**Load Python scripts**:
```gdb
(gdb) source script.py
```

**script.py**:
```python
import gdb

class HelloCommand(gdb.Command):
    """Print hello message."""

    def __init__(self):
        super(HelloCommand, self).__init__("hello", gdb.COMMAND_USER)

    def invoke(self, arg, from_tty):
        print(f"Hello, {arg}!")

HelloCommand()

# Custom breakpoint
class CountBreakpoint(gdb.Breakpoint):
    def __init__(self, spec):
        super(CountBreakpoint, self).__init__(spec)
        self.count = 0

    def stop(self):
        self.count += 1
        print(f"Hit count: {self.count}")
        return True  # Stop execution

CountBreakpoint("main")
```

**Pretty printers**:
```python
import gdb

class MyStructPrinter:
    def __init__(self, val):
        self.val = val

    def to_string(self):
        return f"MyStruct(x={self.val['x']}, y={self.val['y']})"

def my_struct_printer(val):
    if str(val.type) == 'struct MyStruct':
        return MyStructPrinter(val)
    return None

gdb.pretty_printers.append(my_struct_printer)
```

### Remote Debugging

**Start gdbserver on target**:
```bash
# Remote machine
gdbserver :2345 ./program
gdbserver :2345 --attach <pid>
```

**Connect from GDB**:
```gdb
# Local machine
(gdb) target remote 192.168.1.100:2345
(gdb) continue
```

**SSH tunnel**:
```bash
# Local machine
ssh -L 2345:localhost:2345 user@remote
gdb ./program
(gdb) target remote localhost:2345
```

### Core Dump Analysis

**Enable core dumps**:
```bash
# Check current limit
ulimit -c

# Enable unlimited core dumps
ulimit -c unlimited

# Set core pattern (Linux)
sudo sysctl -w kernel.core_pattern=/tmp/core.%e.%p
```

**Load core dump**:
```gdb
gdb ./program core.12345

# Or within GDB:
(gdb) core-file core.12345

# Analyze crash
(gdb) bt full
(gdb) info registers
(gdb) x/10i $pc
```

---

## Multi-threaded Debugging

### Thread Commands

```gdb
# List threads
(gdb) info threads

# Switch to thread
(gdb) thread 2

# Apply command to all threads
(gdb) thread apply all bt

# Thread-specific breakpoint
(gdb) break main thread 2

# Lock scheduler (single-step one thread)
(gdb) set scheduler-locking on
(gdb) set scheduler-locking off
```

---

## Debugging Optimized Code

### Challenges

Optimized code problems:
- Variables optimized out
- Inlined functions
- Reordered instructions
- Registers used instead of stack

### Strategies

```gdb
# Compile with minimal optimization
gcc -g -O1 program.c -o program  # -O1 safer than -O2/-O3

# Use -Og (optimize for debugging)
gcc -g -Og program.c -o program

# Disable specific optimizations
gcc -g -O2 -fno-inline program.c -o program
```

**Handling optimized variables**:
```gdb
# Variable optimized out
(gdb) p my_var
$1 = <optimized out>

# Try different frame
(gdb) up
(gdb) p my_var

# Use disassembly to find value in register
(gdb) disassemble
(gdb) info registers
```

---

## Common Workflows

### Debugging Segfaults

```gdb
# Run until crash
gdb ./program
(gdb) run

# Examine crash
(gdb) bt full
(gdb) info registers
(gdb) x/10i $pc
(gdb) frame 0
(gdb) list
(gdb) info locals
```

### Debugging Memory Leaks

Use Valgrind instead of GDB:
```bash
valgrind --leak-check=full --show-leak-kinds=all ./program
```

### Debugging Race Conditions

```gdb
# Break on thread creation
(gdb) catch syscall clone

# Enable scheduler debugging
(gdb) set scheduler-locking step

# Record execution for reverse debugging
(gdb) record
(gdb) reverse-continue
(gdb) reverse-step
```

---

## GDB with Rust

### Rust-specific Commands

```gdb
# Break at Rust function
(gdb) break my_crate::my_module::my_function

# Pretty-print Rust types
(gdb) set language rust
(gdb) p my_vec

# Load Rust pretty printers
(gdb) source /path/to/rust-gdb
```

**Use rust-gdb wrapper**:
```bash
rust-gdb ./target/debug/my_program
```

---

## GDB with C++

### C++-specific Features

```gdb
# Break at method
(gdb) break MyClass::myMethod

# Print STL containers
(gdb) p my_vector
(gdb) p my_map

# Catch exceptions
(gdb) catch throw
(gdb) catch catch

# Demangle symbols
(gdb) set print asm-demangle on
```

---

## Performance Tips

### Faster Debugging

```gdb
# Disable pagination for scripts
set pagination off

# Disable confirmation prompts
set confirm off

# Reduce output
set print elements 10  # Limit array elements

# Use hardware breakpoints (limited, but faster)
(gdb) hbreak main
```

### Logging

```gdb
# Enable logging
(gdb) set logging on
(gdb) set logging file gdb.log

# Log overwrite vs append
(gdb) set logging overwrite on
```

---

## Anti-Patterns

### Common Mistakes

```
❌ NEVER: Debug optimized code without trying -Og first
   → Variables optimized out, inaccurate stepping

❌ NEVER: Forget to compile with -g
   → No source mapping, only assembly

❌ NEVER: Set too many breakpoints in hot loops
   → Massive slowdown, unusable debugging

❌ NEVER: Use GDB for memory leak detection
   → Use Valgrind, AddressSanitizer instead

❌ NEVER: Attach to production process without understanding impact
   → Process paused = downtime

❌ NEVER: Modify variables in production debugging
   → Undefined behavior, data corruption
```

### Best Practices

```
✅ ALWAYS: Compile with -g -O0 for debug builds
✅ ALWAYS: Use conditional breakpoints in hot paths
✅ ALWAYS: Save .gdbinit for project-specific commands
✅ ALWAYS: Use TUI mode for visual debugging
✅ ALWAYS: Test core dump analysis before production issues
✅ ALWAYS: Use gdbserver for remote/embedded debugging
```

---

## Related Skills

- **lldb-macos-debugging.md**: LLDB debugger for macOS/iOS
- **python-debugging.md**: Python-specific debugging tools
- **browser-devtools.md**: Browser debugging for web applications
- **remote-debugging.md**: Remote debugging techniques
- **test-debugging-strategies.md**: Debugging test failures

---

## Summary

GDB is the standard debugger for compiled languages. Key capabilities:

1. **Breakpoints**: Function, line, conditional, watchpoints, catchpoints
2. **Stack inspection**: Backtraces, frame navigation, variable inspection
3. **TUI mode**: Visual interface for source/assembly viewing
4. **Python scripting**: Custom commands, pretty printers, automation
5. **Remote debugging**: gdbserver for remote/embedded targets
6. **Core dumps**: Post-mortem analysis of crashes
7. **Multi-threading**: Thread-aware debugging, scheduler control

**Quick start**:
```bash
gcc -g -O0 program.c -o program
gdb -tui ./program
(gdb) break main
(gdb) run
(gdb) step
(gdb) print my_variable
(gdb) backtrace
```

Master GDB for efficient low-level debugging across C, C++, Rust, and Go.
