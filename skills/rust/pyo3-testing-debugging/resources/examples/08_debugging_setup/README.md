# Example 08: Debug Configuration and GDB/LLDB Setup

Complete debugging setup for PyO3 extensions with GDB/LLDB configuration.

## What You'll Learn

- Debug build configuration
- Using GDB/LLDB with PyO3
- Setting breakpoints in Rust code
- Inspecting Python objects from debugger
- Core dump analysis

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install maturin
maturin develop  # Debug build by default
```

## Debugging Commands

```bash
# GDB (Linux)
gdb python
(gdb) run -c "import debugging_setup; debugging_setup.trigger_crash()"
(gdb) break src/lib.rs:42
(gdb) continue
(gdb) print variable
(gdb) backtrace

# LLDB (macOS)
lldb python
(lldb) run -c "import debugging_setup; debugging_setup.trigger_crash()"
(lldb) breakpoint set --file lib.rs --line 42
(lldb) continue
(lldb) frame variable
(lldb) bt
```

## Files

- `.gdbinit` - GDB configuration
- `.lldbinit` - LLDB configuration
- `debug.py` - Python debug script
