---
name: wasm-fundamentals
description: WebAssembly basics including binary format, modules, linear memory, WASI, and core tooling
---

# WebAssembly Fundamentals

**Scope**: Core WebAssembly concepts, module structure, memory model, WASI, and essential tooling
**Lines**: ~300
**Last Updated**: 2025-10-25
**Format Version**: 1.0 (Atomic)

---

## When to Use This Skill

Activate this skill when:
- Starting a new WebAssembly project from any language
- Understanding wasm binary and text format structure
- Working with wasm modules, imports, and exports
- Implementing portable executables across platforms
- Using WASI for system interface access
- Converting between WAT (text) and wasm (binary) formats
- Debugging wasm module structure and layout
- Optimizing wasm module size and performance

## Core Concepts

### Concept 1: Module Structure

**Components**:
- Types: Function signatures
- Imports: External dependencies (functions, memory, tables, globals)
- Functions: Internal function definitions
- Tables: Indirect function call tables
- Memory: Linear memory blocks
- Globals: Global variables
- Exports: Public API surface
- Start: Optional initialization function

```wat
;; WAT (WebAssembly Text Format) module
(module
  ;; Import host function
  (import "env" "log" (func $log (param i32)))

  ;; Linear memory (1 page = 64KB)
  (memory (export "memory") 1)

  ;; Export function
  (func (export "add") (param $a i32) (param $b i32) (result i32)
    local.get $a
    local.get $b
    i32.add
  )

  ;; Table for indirect calls
  (table 1 funcref)
)
```

### Concept 2: Linear Memory Model

**Characteristics**:
- Contiguous byte array starting at address 0
- Grows in 64KB pages (65,536 bytes)
- Shared between wasm and host (JavaScript/runtime)
- No garbage collection (manual memory management)
- Sandboxed (cannot access outside memory)

```rust
// Rust code compiling to wasm
#[no_mangle]
pub extern "C" fn allocate(size: usize) -> *mut u8 {
    let mut buffer = Vec::with_capacity(size);
    let ptr = buffer.as_mut_ptr();
    std::mem::forget(buffer); // Prevent deallocation
    ptr
}

#[no_mangle]
pub extern "C" fn deallocate(ptr: *mut u8, size: usize) {
    unsafe {
        let _ = Vec::from_raw_parts(ptr, 0, size);
        // Automatically dropped
    }
}
```

### Concept 3: WASI (WebAssembly System Interface)

**Purpose**: Standardized system interface for non-web environments

**Capabilities**:
- Filesystem access (with capability-based security)
- Environment variables
- Command-line arguments
- Clock/time functions
- Random number generation
- Network access (preview2)

```rust
// Using WASI filesystem
use std::fs::File;
use std::io::Write;

fn main() {
    // WASI runtime provides sandboxed filesystem
    let mut file = File::create("output.txt").unwrap();
    file.write_all(b"Hello from WASI").unwrap();
}
```

### Concept 4: Binary Format

**Structure**: Efficient binary encoding for fast parsing

- Magic number: `0x00 0x61 0x73 0x6D` ("\0asm")
- Version: `0x01 0x00 0x00 0x00` (version 1)
- Sections: Type, Import, Function, Table, Memory, Global, Export, Start, Element, Code, Data, Custom

```bash
# View binary format with hexdump
hexdump -C module.wasm | head -n 5
# 00000000  00 61 73 6d 01 00 00 00  01 07 01 60 02 7f 7f 01  |.asm.......`....|

# Convert wasm to readable WAT
wasm2wat module.wasm -o module.wat

# Convert WAT back to wasm
wat2wasm module.wat -o module.wasm
```

---

## Patterns

### Pattern 1: Creating Minimal Module

**When to use**:
- Testing wasm runtime setup
- Understanding module structure
- Building from scratch without toolchains

```wat
;; Minimal valid wasm module
(module
  (func (export "answer") (result i32)
    i32.const 42
  )
)
```

```bash
# Compile and run
wat2wasm minimal.wat
# Produces minimal.wasm (~20 bytes)
```

**Benefits**:
- Smallest possible wasm file
- No dependencies
- Fast compilation and instantiation

### Pattern 2: String Passing via Memory

**Use case**: Passing strings between host and wasm

```rust
// wasm module
use std::slice;

#[no_mangle]
pub extern "C" fn process_string(ptr: *const u8, len: usize) -> usize {
    let input = unsafe { slice::from_raw_parts(ptr, len) };
    let text = std::str::from_utf8(input).unwrap();

    // Process and return length
    text.len()
}
```

```javascript
// JavaScript host
const encoder = new TextEncoder();
const str = "Hello, WebAssembly!";
const bytes = encoder.encode(str);

// Write to wasm memory
const ptr = instance.exports.allocate(bytes.length);
const memory = new Uint8Array(instance.exports.memory.buffer);
memory.set(bytes, ptr);

// Call wasm function
const result = instance.exports.process_string(ptr, bytes.length);
instance.exports.deallocate(ptr, bytes.length);
```

### Pattern 3: WASI Command-Line Tool

**Use case**: Building portable CLI tools with WASI

```rust
use std::env;
use std::fs;

fn main() {
    let args: Vec<String> = env::args().collect();

    if args.len() < 2 {
        eprintln!("Usage: {} <filename>", args[0]);
        std::process::exit(1);
    }

    let content = fs::read_to_string(&args[1])
        .expect("Failed to read file");

    println!("File length: {}", content.len());
}
```

```bash
# Compile with WASI target
rustup target add wasm32-wasi
cargo build --target wasm32-wasi --release

# Run with wasmtime (WASI runtime)
wasmtime target/wasm32-wasi/release/tool.wasm -- input.txt
```

### Pattern 4: Module Inspection

**Use case**: Understanding wasm module contents

```bash
# Show module structure
wasm-objdump -x module.wasm

# Show function disassembly
wasm-objdump -d module.wasm

# Validate module
wasm-validate module.wasm

# Optimize module
wasm-opt -O3 module.wasm -o optimized.wasm
```

### Pattern 5: Multi-Memory Modules (wasm 2.0)

**When to use**: Isolating memory regions

```wat
(module
  ;; Multiple memories
  (memory $data (export "data") 1 10)
  (memory $scratch (export "scratch") 1 1)

  (func (export "use_memories")
    ;; Write to data memory
    (i32.store (memory $data) (i32.const 0) (i32.const 42))

    ;; Write to scratch memory
    (i32.store (memory $scratch) (i32.const 0) (i32.const 99))
  )
)
```

### Pattern 6: Error Handling with Result Types

**Use case**: Safe error propagation from wasm

```rust
// Return error codes via i32
#[no_mangle]
pub extern "C" fn divide(a: i32, b: i32, result: *mut i32) -> i32 {
    if b == 0 {
        return -1; // Error code
    }

    unsafe {
        *result = a / b;
    }
    0 // Success code
}
```

---

## Quick Reference

### Essential Tools

```
Tool          | Purpose                    | Example
--------------|----------------------------|---------------------------
wat2wasm      | Compile WAT to binary      | wat2wasm module.wat
wasm2wat      | Decompile binary to WAT    | wasm2wat module.wasm
wasm-objdump  | Inspect module structure   | wasm-objdump -x module.wasm
wasm-validate | Validate wasm module       | wasm-validate module.wasm
wasm-opt      | Optimize binary size       | wasm-opt -O3 in.wasm -o out.wasm
wasmtime      | WASI runtime               | wasmtime module.wasm
```

### Value Types

```
Type  | Description        | Size
------|--------------------|---------
i32   | 32-bit integer     | 4 bytes
i64   | 64-bit integer     | 8 bytes
f32   | 32-bit float       | 4 bytes
f64   | 64-bit float       | 8 bytes
v128  | 128-bit vector     | 16 bytes (SIMD)
funcref | Function reference | opaque
externref | External reference | opaque
```

### Key Guidelines

```
✅ DO: Use WASI for portable system access
✅ DO: Validate modules before deployment
✅ DO: Use wasm-opt to minimize binary size
✅ DO: Export memory for host interaction
✅ DO: Handle out-of-bounds memory access

❌ DON'T: Assume garbage collection exists
❌ DON'T: Access memory outside bounds
❌ DON'T: Use platform-specific syscalls directly
```

---

## Anti-Patterns

### Critical Violations

```rust
// ❌ NEVER: Access uninitialized memory
#[no_mangle]
pub extern "C" fn unsafe_read(ptr: *const u8, len: usize) -> u8 {
    unsafe {
        *ptr // May be uninitialized or out of bounds
    }
}

// ✅ CORRECT: Validate before access
#[no_mangle]
pub extern "C" fn safe_read(ptr: *const u8, len: usize) -> i32 {
    if ptr.is_null() || len == 0 {
        return -1; // Error
    }

    unsafe {
        let slice = std::slice::from_raw_parts(ptr, len);
        slice[0] as i32
    }
}
```

❌ **Memory leaks**: Forgetting to deallocate wasm-allocated memory from host
✅ **Correct approach**: Pair every allocate call with deallocate

### Common Mistakes

```wat
;; ❌ Don't: Grow memory without checking result
(func $grow_unchecked
  i32.const 10
  memory.grow
  drop  ;; Ignoring result (-1 on failure)
)

;; ✅ Correct: Check growth success
(func $grow_checked (result i32)
  i32.const 10
  memory.grow
  i32.const -1
  i32.eq
  if
    i32.const 0  ;; Failed
    return
  end
  i32.const 1  ;; Success
)
```

❌ **Ignoring memory growth failures**: Can cause crashes
✅ **Better**: Always check memory.grow return value

### Module Size Anti-Pattern

```bash
# ❌ Don't: Ship unoptimized debug builds
cargo build --target wasm32-unknown-unknown
# Produces large binary with debug info

# ✅ Correct: Use release mode + optimization
cargo build --target wasm32-unknown-unknown --release
wasm-opt -O3 target/wasm32-unknown-unknown/release/app.wasm \
  -o optimized.wasm
```

❌ **Large binaries**: Slow network transfer, parsing
✅ **Better**: Always optimize production wasm

---

## Related Skills

- `wasm-rust-toolchain.md` - Rust-specific wasm compilation and tooling
- `wasm-browser-integration.md` - Loading and using wasm in browsers
- `wasm-server-side.md` - Server-side wasm execution with Wasmtime
- `rust-memory-management.md` - Understanding Rust ownership for wasm
- `zig-memory-management.md` - Manual memory management patterns

---

**Last Updated**: 2025-10-25
**Format Version**: 1.0 (Atomic)
