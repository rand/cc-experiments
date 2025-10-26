---
name: debugging-python-debugging
description: Comprehensive guide to Python debugging tools and techniques. Covers pdb (built-in debugger), ipdb (IPython integration), VSCode debugger, PyCharm debugger, pytest debugging, remote debugging with debugpy, and performance profiling with cProfile.
---

# Python Debugging

**Last Updated**: 2025-10-26

## Overview

Python provides multiple debugging tools from built-in pdb to IDE-integrated debuggers. This guide covers the full debugging toolkit for Python development.

## Core Debugging Tools

### Tool Comparison

| Tool | Use Case | Pros | Cons |
|------|----------|------|------|
| pdb | Built-in CLI debugger | No dependencies, always available | Basic interface |
| ipdb | Enhanced pdb | IPython features, tab completion | Requires ipdb package |
| VSCode | GUI debugging | Visual, breakpoints, watch | Requires VSCode |
| PyCharm | Full-featured IDE | Best GUI debugger | Heavy IDE |
| pytest --pdb | Test debugging | Drops into debugger on failure | Test context only |
| debugpy | Remote debugging | VSCode remote debugging | Setup required |

---

## pdb: Built-in Debugger

### Basic Usage

**Start pdb**:
```python
# Method 1: Insert breakpoint in code
import pdb; pdb.set_trace()

# Method 2: Python 3.7+ built-in breakpoint()
breakpoint()

# Method 3: Run script with pdb
python -m pdb script.py
```

**Example**:
```python
def calculate_sum(numbers):
    total = 0
    for num in numbers:
        breakpoint()  # Execution pauses here
        total += num
    return total

result = calculate_sum([1, 2, 3, 4, 5])
```

### pdb Commands

**Navigation**:
```python
# Step into function
(Pdb) s
(Pdb) step

# Step over (don't enter functions)
(Pdb) n
(Pdb) next

# Continue until return
(Pdb) r
(Pdb) return

# Continue execution
(Pdb) c
(Pdb) continue

# Quit debugger
(Pdb) q
(Pdb) quit
```

**Inspection**:
```python
# Print expression
(Pdb) p variable_name
(Pdb) p len(my_list)

# Pretty-print
(Pdb) pp my_dict

# List source code
(Pdb) l
(Pdb) list

# List specific lines
(Pdb) l 10, 20

# Long list (11 lines)
(Pdb) ll

# Show current location
(Pdb) w
(Pdb) where

# Show call stack
(Pdb) bt
(Pdb) backtrace
```

**Breakpoints**:
```python
# Set breakpoint at line
(Pdb) b 42
(Pdb) break script.py:42

# Set breakpoint at function
(Pdb) b function_name

# Conditional breakpoint
(Pdb) b script.py:42, count > 10

# List breakpoints
(Pdb) bl
(Pdb) break

# Clear breakpoint
(Pdb) cl 1
(Pdb) clear 1

# Disable/enable breakpoint
(Pdb) disable 1
(Pdb) enable 1
```

**Advanced**:
```python
# Execute Python code
(Pdb) !variable = 42
(Pdb) !print(f"Debug: {count}")

# Run until line
(Pdb) unt 50
(Pdb) until 50

# Jump to line (dangerous!)
(Pdb) j 50
(Pdb) jump 50

# Display expression every step
(Pdb) display count

# Run commands on breakpoint hit
(Pdb) commands 1
(com) print(f"Count: {count}")
(com) continue
(com) end
```

### Post-Mortem Debugging

**Debug after exception**:
```python
import pdb

def buggy_function():
    x = 1
    y = 0
    z = x / y  # ZeroDivisionError

try:
    buggy_function()
except:
    pdb.post_mortem()  # Drops into debugger at exception
```

**Automatic post-mortem**:
```bash
# Run with automatic post-mortem
python -m pdb -c continue script.py
```

---

## ipdb: Enhanced Debugger

### Installation & Setup

```bash
# Install via uv (recommended)
uv add --dev ipdb

# Or pip
pip install ipdb
```

### ipdb Features

**Tab completion, syntax highlighting, history**:
```python
import ipdb; ipdb.set_trace()

# Or use breakpoint with PYTHONBREAKPOINT
export PYTHONBREAKPOINT=ipdb.set_trace
```

**IPython features in debugger**:
```python
(ipdb) ?variable_name  # Show docstring
(ipdb) ??function_name  # Show source code
(ipdb) %timeit expression  # Benchmark expression
(ipdb) %debug  # Enhanced debugging
```

**Auto-completion**:
```python
(ipdb) my_var.<TAB>  # Shows methods/attributes
(ipdb) my_dict['ke<TAB>  # Completes dictionary keys
```

---

## VSCode Debugger

### Setup

**install.json (launch configuration)**:
```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Python: Current File",
            "type": "python",
            "request": "launch",
            "program": "${file}",
            "console": "integratedTerminal",
            "justMyCode": false
        },
        {
            "name": "Python: Module",
            "type": "python",
            "request": "launch",
            "module": "mypackage.main",
            "console": "integratedTerminal"
        },
        {
            "name": "Python: Pytest",
            "type": "python",
            "request": "launch",
            "module": "pytest",
            "args": ["tests/", "-v"],
            "console": "integratedTerminal"
        }
    ]
}
```

### Debugging Workflow

**Set breakpoints**:
1. Click left gutter to set breakpoint (red dot)
2. Right-click breakpoint → Edit Breakpoint → Add condition
3. F5 to start debugging

**Debug controls**:
```
F5: Start debugging / Continue
F10: Step over
F11: Step into
Shift+F11: Step out
Ctrl+Shift+F5: Restart
Shift+F5: Stop
```

**Debug panels**:
- **Variables**: Inspect local/global variables
- **Watch**: Add expressions to watch
- **Call Stack**: Navigate stack frames
- **Breakpoints**: Manage all breakpoints

### Conditional Breakpoints

**Expression condition**:
```python
# Break when count > 10
count > 10

# Break when username is "admin"
username == "admin"

# Break when list is empty
len(my_list) == 0
```

**Hit count**:
```
# Break on 5th hit
= 5

# Break every 10 hits
% 10 == 0
```

### Logpoints

**Log without stopping**:
1. Right-click gutter → Add Logpoint
2. Message: `Count is {count}, Total: {total}`
3. Logs to Debug Console without pausing

---

## PyCharm Debugger

### Setup & Features

**Start debugging**:
1. Set breakpoints (click gutter)
2. Right-click script → Debug 'script.py'
3. Or: Run → Debug...

**Advanced features**:
- **Smart step into**: Choose which function to step into
- **Drop frame**: Restart from previous frame
- **Evaluate expression**: Execute code in current context
- **Watches**: Persistent expression evaluation
- **Thread frames**: Multi-threaded debugging

### Remote Debugging (PyCharm Professional)

**Setup remote interpreter**:
1. Settings → Project → Python Interpreter
2. Add → SSH Interpreter
3. Configure SSH connection
4. Map paths: local ↔ remote

**Debug remotely**:
```python
# On remote machine (install pydevd-pycharm)
import pydevd_pycharm
pydevd_pycharm.settrace('localhost', port=12345, stdoutToServer=True, stderrToServer=True)
```

---

## pytest Debugging

### pytest --pdb

**Drop into debugger on failure**:
```bash
# Stop at first failure
pytest tests/ --pdb

# Stop at all failures
pytest tests/ --pdb --maxfail=5

# Use ipdb instead of pdb
pytest tests/ --pdb --pdbcls=IPython.terminal.debugger:Pdb
```

**Example**:
```python
def test_calculation():
    result = calculate(5, 0)
    assert result == 5  # Fails, drops into pdb

# Terminal shows:
# >>>>>>>>>>>>>>>>>>>> PDB set_trace >>>>>>>>>>>>>>>>>>>
# (Pdb) p result
# (Pdb) l
```

### pytest Fixtures in Debugger

```python
import pytest

@pytest.fixture
def sample_data():
    return [1, 2, 3, 4, 5]

def test_with_fixture(sample_data):
    breakpoint()  # Can inspect sample_data here
    assert sum(sample_data) == 15
```

### Debugging Test Setup/Teardown

```bash
# Show setup/teardown output
pytest tests/ --pdb --capture=no

# Or -s shorthand
pytest tests/ --pdb -s
```

---

## Remote Debugging

### debugpy (VSCode Remote Debugging)

**Install debugpy**:
```bash
uv add --dev debugpy
```

**Remote script setup**:
```python
# remote_app.py
import debugpy

# Wait for debugger to attach
debugpy.listen(("0.0.0.0", 5678))
print("Waiting for debugger attach...")
debugpy.wait_for_client()
print("Debugger attached!")

# Your code here
def main():
    for i in range(10):
        print(f"Iteration {i}")

if __name__ == "__main__":
    main()
```

**VSCode launch.json**:
```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Python: Attach",
            "type": "python",
            "request": "attach",
            "connect": {
                "host": "remote-server.com",
                "port": 5678
            },
            "pathMappings": [
                {
                    "localRoot": "${workspaceFolder}",
                    "remoteRoot": "/app"
                }
            ]
        }
    ]
}
```

**SSH tunnel**:
```bash
# Forward remote port to local
ssh -L 5678:localhost:5678 user@remote-server.com

# In another terminal:
# Start VSCode debug with "Python: Attach"
```

### pdb Remote Debugging

**Simple remote pdb**:
```python
# On remote machine
import pdb
import sys

class RemotePdb(pdb.Pdb):
    def __init__(self, port=4444):
        import socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind(('0.0.0.0', port))
        self.sock.listen(1)
        print(f"Waiting for connection on port {port}...")
        (clientsocket, address) = self.sock.accept()
        handle = clientsocket.makefile('rw')
        pdb.Pdb.__init__(self, stdin=handle, stdout=handle)

# Use it
RemotePdb(port=4444).set_trace()

# Connect from local machine:
# telnet remote-server.com 4444
```

---

## Performance Profiling

### cProfile

**Profile script**:
```bash
# Profile entire script
python -m cProfile -s cumulative script.py

# Save profile data
python -m cProfile -o output.prof script.py
```

**Profile in code**:
```python
import cProfile
import pstats

def profile_function():
    profiler = cProfile.Profile()
    profiler.enable()

    # Code to profile
    result = expensive_calculation()

    profiler.disable()
    stats = pstats.Stats(profiler)
    stats.sort_stats('cumulative')
    stats.print_stats(10)  # Top 10 functions

    return result
```

**Analyze profile**:
```python
import pstats

# Load profile
stats = pstats.Stats('output.prof')

# Sort and print
stats.sort_stats('cumulative').print_stats(20)
stats.sort_stats('time').print_stats(20)

# Filter by function name
stats.print_stats('my_function')
```

### line_profiler

**Install**:
```bash
uv add --dev line-profiler
```

**Usage**:
```python
# Add @profile decorator
@profile
def slow_function():
    total = 0
    for i in range(1000000):
        total += i
    return total

# Run with kernprof
# kernprof -l -v script.py
```

**Output shows line-by-line timing**:
```
Line #      Hits         Time  Per Hit   % Time  Line Contents
==============================================================
     3                                           @profile
     4                                           def slow_function():
     5         1          2.0      2.0      0.0      total = 0
     6   1000001     300000.0      0.3     50.0      for i in range(1000000):
     7   1000000     300000.0      0.3     50.0          total += i
     8         1          0.0      0.0      0.0      return total
```

### memory_profiler

**Install**:
```bash
uv add --dev memory-profiler
```

**Usage**:
```python
from memory_profiler import profile

@profile
def memory_intensive():
    big_list = [0] * (10 ** 7)
    return sum(big_list)

# Run: python -m memory_profiler script.py
```

---

## Debugging Best Practices

### Strategic Breakpoint Placement

```python
# ❌ Bad: Too many breakpoints
for i in range(1000000):
    breakpoint()  # Stops 1M times!
    process(i)

# ✅ Good: Conditional breakpoint
for i in range(1000000):
    if i == 999999:  # Last iteration only
        breakpoint()
    process(i)

# ✅ Better: Use logging for hot paths
import logging
for i in range(1000000):
    logging.debug(f"Processing {i}")
    process(i)
```

### Debugging Strategies

**Binary search for bug**:
```python
# Start with breakpoint in middle
def long_function():
    step1()
    step2()
    step3()
    breakpoint()  # Middle
    step4()
    step5()
    step6()

# If bug before breakpoint, move up
# If bug after breakpoint, move down
```

**Rubber duck debugging**:
```python
# Explain code to debugger
def calculate(a, b):
    breakpoint()
    # "So a is 5, b is 0, and I'm dividing..."
    # "Oh! Division by zero!"
    return a / b
```

---

## Common Debugging Workflows

### Debugging Import Errors

```python
# Check import paths
import sys
print(sys.path)

# Debug module import
import importlib
spec = importlib.util.find_spec('mymodule')
print(spec)  # None = not found
```

### Debugging Async Code

```python
import asyncio

async def debug_async():
    await asyncio.sleep(1)
    breakpoint()  # Works in async functions
    result = await fetch_data()
    return result

# VSCode/PyCharm handle async debugging automatically
```

### Debugging Decorators

```python
from functools import wraps

def my_decorator(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        breakpoint()  # Debug decorator logic
        result = func(*args, **kwargs)
        return result
    return wrapper

@my_decorator
def my_function():
    pass
```

### Debugging Comprehensions

```python
# ❌ Hard to debug
result = [process(x) for x in data if x > 10]

# ✅ Easier to debug
result = []
for x in data:
    if x > 10:
        breakpoint()  # Can inspect x
        processed = process(x)
        result.append(processed)
```

---

## Anti-Patterns

### Common Mistakes

```
❌ NEVER: Leave breakpoint() in production code
   → Pauses production app, user sees debugger

❌ NEVER: Use print() instead of logging
   → Can't disable, pollutes output

❌ NEVER: Debug without reproducing bug first
   → Wastes time on wrong code path

❌ NEVER: Modify code while debugging without restarting
   → Changes not reflected, confusing state

❌ NEVER: Use debugger for performance issues
   → Use profiler instead (cProfile, line_profiler)

❌ NEVER: Debug optimized bytecode (.pyc)
   → Use source code (.py) for accurate debugging
```

### Best Practices

```
✅ ALWAYS: Use breakpoint() instead of pdb.set_trace() (Python 3.7+)
✅ ALWAYS: Set PYTHONBREAKPOINT=ipdb.set_trace for enhanced debugging
✅ ALWAYS: Use conditional breakpoints in hot paths
✅ ALWAYS: Profile before optimizing (measure, don't guess)
✅ ALWAYS: Use logging for production debugging
✅ ALWAYS: Clean up debug code before committing
```

---

## Environment Variables

### Useful Python Debug Variables

```bash
# Set default breakpoint implementation
export PYTHONBREAKPOINT=ipdb.set_trace

# Disable all breakpoint() calls
export PYTHONBREAKPOINT=0

# Enable asyncio debug mode
export PYTHONASYNCIODEBUG=1

# Show warnings
export PYTHONWARNINGS=default

# Enable development mode (extra checks)
export PYTHONDEVMODE=1

# Show full tracebacks
export PYTHONFAULTHANDLER=1
```

---

## Related Skills

- **gdb-fundamentals.md**: GDB for C/C++/Rust debugging
- **lldb-macos-debugging.md**: LLDB for macOS/iOS
- **browser-devtools.md**: Browser debugging tools
- **remote-debugging.md**: Remote debugging techniques
- **test-debugging-strategies.md**: Debugging test failures

---

## Summary

Python provides comprehensive debugging tools for all scenarios:

1. **pdb/ipdb**: Built-in CLI debugging with post-mortem support
2. **VSCode/PyCharm**: GUI debugging with breakpoints, watches, call stack
3. **pytest --pdb**: Drop into debugger on test failures
4. **debugpy**: Remote debugging for distributed systems
5. **cProfile/line_profiler**: Performance profiling and optimization
6. **Async debugging**: Native support in modern debuggers

**Quick start**:
```python
# Simple debugging
def my_function(x):
    breakpoint()  # Pause here
    return x * 2

# VSCode debugging
# 1. Set breakpoint (click gutter)
# 2. Press F5
# 3. Use F10 (step over), F11 (step into)

# Test debugging
pytest tests/ --pdb --pdbcls=IPython.terminal.debugger:Pdb
```

Master Python debugging for efficient development and troubleshooting.
