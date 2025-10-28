---
name: wasm-rust-toolchain
description: Rust to WebAssembly compilation using wasm-pack, wasm-bindgen, optimization, and JavaScript interop
---

# Rust WebAssembly Toolchain

**Scope**: Compiling Rust to wasm with wasm-pack, wasm-bindgen for JS interop, optimization, and debugging
**Lines**: ~340
**Last Updated**: 2025-10-25
**Format Version**: 1.0 (Atomic)

---

## When to Use This Skill

Activate this skill when:
- Building Rust libraries for browser JavaScript consumption
- Creating npm packages from Rust code
- Setting up wasm-bindgen for JS/Rust interop
- Optimizing Rust-generated wasm binaries
- Debugging Rust wasm modules in browser DevTools
- Handling errors across the Rust/JS boundary
- Publishing Rust wasm packages to npm
- Using no_std for minimal wasm output

## Core Concepts

### Concept 1: Compilation Targets

**wasm32-unknown-unknown**: Raw wasm without JS bindings
**wasm32-wasi**: WASI runtime target
**wasm-pack target**: Browser/Node.js with JS glue code

```bash
# Add wasm targets
rustup target add wasm32-unknown-unknown
rustup target add wasm32-wasi

# Raw wasm (no JS bindings)
cargo build --target wasm32-unknown-unknown --release

# With wasm-pack (generates JS bindings)
wasm-pack build --target web
```

```rust
// Cargo.toml for wasm-pack projects
[package]
name = "my-wasm-lib"
version = "0.1.0"
edition = "2021"

[lib]
crate-type = ["cdylib"]  # Dynamic library for wasm

[dependencies]
wasm-bindgen = "0.2"

[profile.release]
opt-level = "z"      # Optimize for size
lto = true           # Link-time optimization
codegen-units = 1    # Single codegen unit for smaller binary
```

### Concept 2: wasm-bindgen Fundamentals

**Purpose**: Bridge between Rust and JavaScript

**Key features**:
- Export Rust functions to JS
- Import JS functions to Rust
- Handle complex types (strings, objects, arrays)
- Generate TypeScript definitions

```rust
use wasm_bindgen::prelude::*;

// Export Rust function to JS
#[wasm_bindgen]
pub fn greet(name: &str) -> String {
    format!("Hello, {}!", name)
}

// Import JS function to Rust
#[wasm_bindgen]
extern "C" {
    #[wasm_bindgen(js_namespace = console)]
    fn log(s: &str);

    #[wasm_bindgen(js_namespace = Date, js_name = now)]
    fn date_now() -> f64;
}

// Use imported functions
#[wasm_bindgen]
pub fn log_timestamp() {
    let timestamp = date_now();
    log(&format!("Current timestamp: {}", timestamp));
}
```

### Concept 3: Type Conversions

**Supported types**:
- Primitives: i32, f64, bool
- String/str via owned conversion
- JsValue for arbitrary JS values
- Custom structs with #[wasm_bindgen]

```rust
use wasm_bindgen::prelude::*;

#[wasm_bindgen]
pub struct User {
    name: String,
    age: u32,
}

#[wasm_bindgen]
impl User {
    #[wasm_bindgen(constructor)]
    pub fn new(name: String, age: u32) -> User {
        User { name, age }
    }

    #[wasm_bindgen(getter)]
    pub fn name(&self) -> String {
        self.name.clone()
    }

    #[wasm_bindgen(getter)]
    pub fn age(&self) -> u32 {
        self.age
    }

    pub fn greet(&self) -> String {
        format!("Hi, I'm {} and I'm {} years old", self.name, self.age)
    }
}
```

```javascript
// Generated JavaScript usage
import { User } from './pkg/my_wasm_lib.js';

const user = new User("Alice", 30);
console.log(user.name);    // "Alice"
console.log(user.greet()); // "Hi, I'm Alice and I'm 30 years old"
```

### Concept 4: Error Handling

**Result types**: Converted to JS exceptions

```rust
use wasm_bindgen::prelude::*;

#[wasm_bindgen]
pub fn divide(a: f64, b: f64) -> Result<f64, JsValue> {
    if b == 0.0 {
        return Err(JsValue::from_str("Division by zero"));
    }
    Ok(a / b)
}

// Custom error type
#[wasm_bindgen]
pub fn parse_number(s: &str) -> Result<i32, JsValue> {
    s.parse::<i32>()
        .map_err(|e| JsValue::from_str(&format!("Parse error: {}", e)))
}
```

```javascript
// JS catches as exceptions
try {
    const result = divide(10, 0);
} catch (e) {
    console.error(e); // "Division by zero"
}
```

---

## Patterns

### Pattern 1: wasm-pack Project Setup

**When to use**: Starting new Rust wasm library

```bash
# Install wasm-pack
⚠️ **SECURITY**: Piping curl to shell is dangerous. For production:
```bash
# Download script first
curl -O https://rustwasm.github.io/wasm-pack/installer/init.sh
# Verify checksum
sha256sum init.sh
# Review content
less init.sh
# Then execute
bash init.sh
```
For development/learning only:
```bash
curl https://rustwasm.github.io/wasm-pack/installer/init.sh -sSf | sh

# Create new project
cargo new --lib my-wasm-lib
cd my-wasm-lib

# Add to Cargo.toml
# [lib]
# crate-type = ["cdylib"]
# [dependencies]
# wasm-bindgen = "0.2"

# Build for different targets
wasm-pack build --target web      # ES modules for browsers
wasm-pack build --target bundler  # For webpack/rollup
wasm-pack build --target nodejs   # Node.js
wasm-pack build --target no-modules # Script tag loading
```

**Benefits**:
- Automatic JS/TS generation
- npm-ready package structure
- Multiple deployment targets

### Pattern 2: Async Functions

**Use case**: Calling async Rust from JavaScript

```rust
use wasm_bindgen::prelude::*;
use wasm_bindgen_futures::JsFuture;
use web_sys::{Request, RequestInit, Response};

#[wasm_bindgen]
pub async fn fetch_data(url: String) -> Result<JsValue, JsValue> {
    let mut opts = RequestInit::new();
    opts.method("GET");

    let request = Request::new_with_str_and_init(&url, &opts)?;

    let window = web_sys::window().unwrap();
    let resp_value = JsFuture::from(window.fetch_with_request(&request)).await?;
    let resp: Response = resp_value.dyn_into()?;

    let json = JsFuture::from(resp.json()?).await?;
    Ok(json)
}
```

```javascript
// JavaScript calls async function
import { fetch_data } from './pkg';

async function loadData() {
    try {
        const data = await fetch_data('https://api.example.com/data');
        console.log(data);
    } catch (error) {
        console.error('Fetch failed:', error);
    }
}
```

### Pattern 3: Size Optimization Pipeline

**Use case**: Minimizing wasm bundle size

```toml
# Cargo.toml
[profile.release]
opt-level = "z"           # Optimize for size
lto = true                # Link-time optimization
codegen-units = 1         # Single codegen unit
panic = "abort"           # No panic unwinding
strip = true              # Strip symbols

[dependencies]
wasm-bindgen = "0.2"
# Avoid large dependencies
```

```bash
# Build with optimizations
wasm-pack build --release --target web

# Further optimize with wasm-opt
wasm-opt -Oz pkg/my_wasm_lib_bg.wasm \
  -o pkg/my_wasm_lib_bg.wasm

# Check size reduction
ls -lh pkg/*.wasm
```

**Results**: Often 50-80% size reduction

### Pattern 4: Console Logging

**Use case**: Debugging wasm in browser

```rust
use wasm_bindgen::prelude::*;

// Simple console.log
#[wasm_bindgen]
extern "C" {
    #[wasm_bindgen(js_namespace = console)]
    fn log(s: &str);

    #[wasm_bindgen(js_namespace = console, js_name = log)]
    fn log_u32(a: u32);

    #[wasm_bindgen(js_namespace = console, js_name = log)]
    fn log_many(a: &str, b: &str);
}

// Helper macro
macro_rules! console_log {
    ($($t:tt)*) => {
        log(&format!($($t)*))
    }
}

#[wasm_bindgen]
pub fn debug_example(value: i32) {
    console_log!("Debug value: {}", value);
}
```

### Pattern 5: Working with Arrays

**Use case**: Passing arrays between Rust and JS

```rust
use wasm_bindgen::prelude::*;

// JS array to Rust Vec
#[wasm_bindgen]
pub fn sum_array(arr: &[i32]) -> i32 {
    arr.iter().sum()
}

// Return Rust Vec as JS array (requires serde)
#[wasm_bindgen]
pub fn create_range(n: i32) -> Vec<i32> {
    (0..n).collect()
}

// Typed arrays for performance
use js_sys::Uint8Array;

#[wasm_bindgen]
pub fn process_bytes(data: Uint8Array) -> Uint8Array {
    let mut bytes = data.to_vec();
    // Process bytes
    for byte in &mut bytes {
        *byte = byte.wrapping_add(1);
    }
    // Return as Uint8Array
    Uint8Array::from(&bytes[..])
}
```

### Pattern 6: Source Maps for Debugging

**Use case**: Debugging Rust code in browser DevTools

```bash
# Build with source maps
RUSTFLAGS="-C debuginfo=2" wasm-pack build --dev --target web

# DevTools will show original Rust source
# Set breakpoints in .rs files
```

```rust
// Rust source visible in browser
#[wasm_bindgen]
pub fn complex_calculation(x: f64) -> f64 {
    let step1 = x * 2.0;  // Breakpoint here shows x value
    let step2 = step1 + 10.0;
    step2.sqrt()
}
```

### Pattern 7: no_std for Minimal Binaries

**When to use**: Extremely size-constrained environments

```rust
#![no_std]

extern crate alloc;
use alloc::string::String;
use alloc::format;
use wasm_bindgen::prelude::*;

#[wasm_bindgen]
pub fn minimal_greet(name: &str) -> String {
    format!("Hello, {}!", name)
}
```

**Benefits**:
- Smaller binary size (no std library)
- Faster compilation
- Explicit allocation control

### Pattern 8: Testing wasm Code

**Use case**: Unit testing Rust wasm modules

```rust
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_greet() {
        assert_eq!(greet("World"), "Hello, World!");
    }
}

// Browser tests with wasm-pack
#[cfg(test)]
mod wasm_tests {
    use wasm_bindgen_test::*;

    #[wasm_bindgen_test]
    fn test_in_browser() {
        assert_eq!(1 + 1, 2);
    }
}
```

```bash
# Run native tests
cargo test

# Run in headless browser
wasm-pack test --headless --firefox
wasm-pack test --headless --chrome
```

---

## Quick Reference

### wasm-pack Commands

```
Command                          | Purpose
---------------------------------|----------------------------------
wasm-pack new my-lib             | Create new project
wasm-pack build                  | Build for bundler target
wasm-pack build --target web     | Build for ES modules
wasm-pack build --target nodejs  | Build for Node.js
wasm-pack test --headless --firefox | Run browser tests
wasm-pack publish                | Publish to npm
```

### Build Targets

```
Target      | Use Case                  | Import Style
------------|---------------------------|---------------------------
web         | ES modules in browsers    | import * from './pkg'
bundler     | Webpack/Rollup/Parcel     | import * from 'pkg'
nodejs      | Node.js applications      | const pkg = require('pkg')
no-modules  | Script tag (legacy)       | <script src="pkg.js">
```

### Key Guidelines

```
✅ DO: Use wasm-pack for browser projects
✅ DO: Enable LTO and size optimization in release
✅ DO: Use wasm-opt for production builds
✅ DO: Return Result<T, JsValue> for fallible functions
✅ DO: Use console logging for debugging

❌ DON'T: Include large dependencies unnecessarily
❌ DON'T: Forget to handle errors from JS boundary
❌ DON'T: Use blocking operations in async contexts
```

---

## Anti-Patterns

### Critical Violations

```rust
// ❌ NEVER: Block async execution
#[wasm_bindgen]
pub async fn bad_async() -> Result<(), JsValue> {
    std::thread::sleep(std::time::Duration::from_secs(5)); // Blocks!
    Ok(())
}

// ✅ CORRECT: Use web timers
use wasm_bindgen_futures::JsFuture;
use web_sys::window;

#[wasm_bindgen]
pub async fn good_async() -> Result<(), JsValue> {
    let promise = js_sys::Promise::new(&mut |resolve, _| {
        window()
            .unwrap()
            .set_timeout_with_callback_and_timeout_and_arguments_0(&resolve, 5000)
            .unwrap();
    });
    JsFuture::from(promise).await?;
    Ok(())
}
```

❌ **Blocking in wasm**: Freezes browser, terrible UX
✅ **Correct approach**: Use browser APIs and async

### Common Mistakes

```rust
// ❌ Don't: Clone strings excessively
#[wasm_bindgen]
pub fn process_many_strings(input: String) -> String {
    let copy1 = input.clone(); // Unnecessary allocation
    let copy2 = copy1.clone(); // Another allocation
    copy2.to_uppercase()
}

// ✅ Correct: Use references
#[wasm_bindgen]
pub fn process_strings_efficiently(input: &str) -> String {
    input.to_uppercase() // Single allocation for result
}
```

❌ **Excessive cloning**: Slower, uses more memory
✅ **Better**: Use string slices (&str) when possible

### Size Bloat Anti-Pattern

```toml
# ❌ Don't: Include heavy dependencies
[dependencies]
wasm-bindgen = "0.2"
tokio = { version = "1", features = ["full"] }  # Huge!
serde_json = "1"                                 # Large
regex = "1"                                      # Large

# ✅ Correct: Minimal dependencies
[dependencies]
wasm-bindgen = "0.2"
serde-wasm-bindgen = "0.5"  # Lighter than serde_json
```

❌ **Heavy dependencies**: 500KB+ wasm files
✅ **Better**: Use lightweight, wasm-specific crates

---

## Related Skills

- `wasm-fundamentals.md` - Core WebAssembly concepts and module structure
- `wasm-browser-integration.md` - Loading and using wasm in browsers
- `rust-memory-management.md` - Understanding ownership for wasm
- `frontend-state-management.md` - Managing state with Rust wasm
- `test-unit.md` - Unit testing strategies for Rust code

---

**Last Updated**: 2025-10-25
**Format Version**: 1.0 (Atomic)
