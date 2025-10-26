---
name: wasm-server-side
description: Server-side WebAssembly execution with Wasmtime, WASI support, edge computing, and plugin systems
---

# Server-Side WebAssembly

**Scope**: Running wasm on servers with Wasmtime runtime, WASI interfaces, edge compute, and plugin architectures
**Lines**: ~280
**Last Updated**: 2025-10-25
**Format Version**: 1.0 (Atomic)

---

## When to Use This Skill

Activate this skill when:
- Running wasm modules on server-side with Wasmtime or Wasmer
- Building plugin systems with wasm sandboxing
- Deploying to edge platforms (Cloudflare Workers, Fastly Compute@Edge)
- Using WASI for filesystem and environment access
- Enforcing resource limits on untrusted code
- Creating portable serverless functions
- Embedding wasm in Rust/Go/Python applications
- Optimizing cold start performance for functions

## Core Concepts

### Concept 1: Wasmtime Runtime

**Features**:
- JIT and AOT compilation
- WASI support built-in
- Memory limits and timeouts
- Multi-language embedding (Rust, Python, Go, C)

```rust
// Embedding Wasmtime in Rust
use wasmtime::*;

fn main() -> Result<()> {
    let engine = Engine::default();
    let mut store = Store::new(&engine, ());

    // Compile module
    let module = Module::from_file(&engine, "plugin.wasm")?;

    // Create imports
    let log_func = Func::wrap(&mut store, |param: i32| {
        println!("Log from wasm: {}", param);
    });

    let mut linker = Linker::new(&engine);
    linker.define(&store, "env", "log", log_func)?;

    // Instantiate
    let instance = linker.instantiate(&mut store, &module)?;

    // Call exported function
    let run = instance.get_typed_func::<(), ()>(&mut store, "run")?;
    run.call(&mut store, ())?;

    Ok(())
}
```

### Concept 2: WASI Filesystem Access

**Capability-based security**: Pre-open directories, sandboxed access

```rust
use wasmtime::*;
use wasmtime_wasi::{WasiCtxBuilder, sync::WasiCtx};

fn main() -> Result<()> {
    let engine = Engine::default();
    let mut linker = Linker::new(&engine);
    wasmtime_wasi::add_to_linker(&mut linker, |s| s)?;

    // Configure WASI with directory access
    let wasi = WasiCtxBuilder::new()
        .inherit_stdio()
        .preopened_dir(
            wasmtime_wasi::sync::Dir::open_ambient_dir("./data", wasmtime_wasi::sync::ambient_authority())?,
            "/data"
        )?
        .build();

    let mut store = Store::new(&engine, wasi);

    let module = Module::from_file(&engine, "app.wasm")?;
    let instance = linker.instantiate(&mut store, &module)?;

    let start = instance.get_typed_func::<(), ()>(&mut store, "_start")?;
    start.call(&mut store, ())?;

    Ok(())
}
```

```rust
// WASI guest code
use std::fs;

fn main() {
    // Reads from pre-opened /data directory
    let content = fs::read_to_string("/data/input.txt")
        .expect("Failed to read file");

    println!("File content: {}", content);

    // Write to allowed directory
    fs::write("/data/output.txt", "Hello, WASI!")
        .expect("Failed to write file");
}
```

### Concept 3: Resource Limits

**Enforce limits**: Memory, CPU time, fuel (instruction count)

```rust
use wasmtime::*;

fn main() -> Result<()> {
    // Configure with limits
    let mut config = Config::default();
    config.consume_fuel(true); // Enable fuel metering

    let engine = Engine::new(&config)?;
    let module = Module::from_file(&engine, "untrusted.wasm")?;

    let mut store = Store::new(&engine, ());

    // Set fuel limit (approx instruction count)
    store.add_fuel(10_000)?;

    // Set memory limit (pages)
    let memory_type = MemoryType::new(1, Some(10)); // 1-10 pages
    let memory = Memory::new(&mut store, memory_type)?;

    let instance = Instance::new(&mut store, &module, &[memory.into()])?;

    // Run with timeout
    match std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
        let func = instance.get_typed_func::<(), ()>(&mut store, "run")?;
        func.call(&mut store, ())
    })) {
        Ok(result) => result?,
        Err(_) => eprintln!("Function exceeded limits"),
    }

    // Check remaining fuel
    let remaining = store.fuel_consumed()?;
    println!("Instructions used: ~{}", 10_000 - remaining);

    Ok(())
}
```

### Concept 4: Edge Computing

**Cloudflare Workers example**:

```rust
// wrangler.toml
name = "my-worker"
type = "webpack"
account_id = "your-account-id"
workers_dev = true
route = ""
zone_id = ""

[build]
command = "wasm-pack build --target bundler"

[build.upload]
format = "modules"
main = "./worker.js"
```

```rust
// src/lib.rs
use wasm_bindgen::prelude::*;

#[wasm_bindgen]
pub fn handle_request(url: String, method: String) -> String {
    match method.as_str() {
        "GET" => format!("GET request to {}", url),
        "POST" => format!("POST request to {}", url),
        _ => "Unsupported method".to_string(),
    }
}
```

```javascript
// worker.js
import init, { handle_request } from './pkg/my_worker.js';

export default {
    async fetch(request) {
        await init();

        const response = handle_request(
            request.url,
            request.method
        );

        return new Response(response, {
            headers: { 'content-type': 'text/plain' },
        });
    },
};
```

---

## Patterns

### Pattern 1: Plugin System

**When to use**: Safe execution of user-provided code

```rust
use wasmtime::*;
use std::collections::HashMap;

pub struct PluginManager {
    engine: Engine,
    plugins: HashMap<String, Module>,
}

impl PluginManager {
    pub fn new() -> Self {
        PluginManager {
            engine: Engine::default(),
            plugins: HashMap::new(),
        }
    }

    pub fn load_plugin(&mut self, name: String, path: &str) -> Result<()> {
        let module = Module::from_file(&self.engine, path)?;
        self.plugins.insert(name, module);
        Ok(())
    }

    pub fn execute_plugin(&self, name: &str, input: i32) -> Result<i32> {
        let module = self.plugins.get(name)
            .ok_or_else(|| anyhow::anyhow!("Plugin not found"))?;

        let mut store = Store::new(&self.engine, ());
        let instance = Instance::new(&mut store, module, &[])?;

        let process = instance
            .get_typed_func::<i32, i32>(&mut store, "process")?;

        process.call(&mut store, input)
    }
}

// Usage
fn main() -> Result<()> {
    let mut manager = PluginManager::new();

    manager.load_plugin("plugin1".to_string(), "plugins/plugin1.wasm")?;
    manager.load_plugin("plugin2".to_string(), "plugins/plugin2.wasm")?;

    let result1 = manager.execute_plugin("plugin1", 42)?;
    let result2 = manager.execute_plugin("plugin2", 100)?;

    println!("Results: {}, {}", result1, result2);
    Ok(())
}
```

### Pattern 2: FastAPI + Wasmtime

**Use case**: Python web service executing wasm

```python
from fastapi import FastAPI, UploadFile
from wasmtime import Store, Module, Instance, Engine, Func, FuncType, ValType
import io

app = FastAPI()
engine = Engine()

def log_callback(val: int):
    print(f"Wasm log: {val}")

@app.post("/process")
async def process(file: UploadFile):
    # Load user-uploaded wasm
    wasm_bytes = await file.read()

    store = Store(engine)
    module = Module(engine, wasm_bytes)

    # Provide imports
    log_func_type = FuncType([ValType.i32()], [])
    log_func = Func(store, log_func_type, log_callback)

    instance = Instance(store, module, [log_func])

    # Call process function
    process_func = instance.exports(store)["process"]
    result = process_func(store, 42)

    return {"result": result}
```

### Pattern 3: AOT Compilation for Fast Startup

**When to use**: Optimize cold starts

```rust
use wasmtime::*;

fn compile_ahead_of_time() -> Result<()> {
    let engine = Engine::default();
    let module = Module::from_file(&engine, "app.wasm")?;

    // Serialize compiled module
    let compiled = module.serialize()?;
    std::fs::write("app.cwasm", compiled)?;

    Ok(())
}

fn load_precompiled() -> Result<()> {
    let engine = Engine::default();
    let compiled = std::fs::read("app.cwasm")?;

    // Deserialize (much faster than compiling)
    let module = unsafe { Module::deserialize(&engine, &compiled)? };

    let mut store = Store::new(&engine, ());
    let instance = Instance::new(&mut store, &module, &[])?;

    // Instant startup
    Ok(())
}
```

### Pattern 4: Multi-Tenant Isolation

**Use case**: Run untrusted code safely per tenant

```rust
use wasmtime::*;
use std::time::Duration;

struct Tenant {
    id: String,
    fuel_limit: u64,
    memory_limit: u32, // pages
}

fn execute_tenant_code(tenant: &Tenant, wasm_bytes: &[u8]) -> Result<String> {
    let mut config = Config::default();
    config.consume_fuel(true);

    let engine = Engine::new(&config)?;
    let module = Module::new(&engine, wasm_bytes)?;

    let mut store = Store::new(&engine, ());
    store.add_fuel(tenant.fuel_limit)?;

    // Limit memory
    let memory_type = MemoryType::new(1, Some(tenant.memory_limit));
    let memory = Memory::new(&mut store, memory_type)?;

    let instance = Instance::new(&mut store, &module, &[memory.into()])?;

    // Execute with timeout
    let result = instance
        .get_typed_func::<(), i32>(&mut store, "run")?
        .call(&mut store, ())?;

    Ok(format!("Tenant {} result: {}", tenant.id, result))
}
```

### Pattern 5: WASI Environment Variables

**Use case**: Configure wasm apps via environment

```rust
use wasmtime::*;
use wasmtime_wasi::WasiCtxBuilder;

fn main() -> Result<()> {
    let engine = Engine::default();
    let mut linker = Linker::new(&engine);
    wasmtime_wasi::add_to_linker(&mut linker, |s| s)?;

    let wasi = WasiCtxBuilder::new()
        .inherit_stdio()
        .env("DATABASE_URL", "postgres://localhost/db")?
        .env("API_KEY", "secret-key")?
        .arg("app.wasm")?
        .arg("--verbose")?
        .build();

    let mut store = Store::new(&engine, wasi);

    let module = Module::from_file(&engine, "app.wasm")?;
    linker.instantiate(&mut store, &module)?;

    Ok(())
}
```

```rust
// Guest code accessing env vars
fn main() {
    let db_url = std::env::var("DATABASE_URL")
        .expect("DATABASE_URL not set");

    let args: Vec<String> = std::env::args().collect();
    println!("Args: {:?}", args);
}
```

### Pattern 6: Streaming Response

**Use case**: Process large data streams

```rust
use wasmtime::*;

fn process_stream(wasm_path: &str, data: &[u8]) -> Result<Vec<u8>> {
    let engine = Engine::default();
    let module = Module::from_file(&engine, wasm_path)?;
    let mut store = Store::new(&engine, ());

    let instance = Instance::new(&mut store, &module, &[])?;
    let memory = instance.get_memory(&mut store, "memory")
        .ok_or_else(|| anyhow::anyhow!("No memory export"))?;

    // Write input to wasm memory
    let alloc = instance.get_typed_func::<u32, u32>(&mut store, "alloc")?;
    let ptr = alloc.call(&mut store, data.len() as u32)?;

    memory.write(&mut store, ptr as usize, data)?;

    // Process
    let process = instance.get_typed_func::<(u32, u32), u32>(&mut store, "process")?;
    let result_len = process.call(&mut store, (ptr, data.len() as u32))?;

    // Read output
    let mut output = vec![0u8; result_len as usize];
    memory.read(&store, ptr as usize, &mut output)?;

    // Free memory
    let free = instance.get_typed_func::<(u32, u32), ()>(&mut store, "free")?;
    free.call(&mut store, (ptr, data.len() as u32))?;

    Ok(output)
}
```

---

## Quick Reference

### Wasmtime CLI

```
Command                              | Purpose
-------------------------------------|--------------------------------
wasmtime run app.wasm                | Execute wasm module
wasmtime run --dir=. app.wasm        | Grant directory access
wasmtime run --env KEY=val app.wasm  | Set environment variable
wasmtime compile app.wasm            | AOT compile to .cwasm
wasmtime run --fuel=1000 app.wasm    | Run with fuel limit
```

### Key Guidelines

```
✅ DO: Use WASI for portable system access
✅ DO: Set resource limits for untrusted code
✅ DO: Pre-compile modules for fast startup
✅ DO: Use capability-based filesystem access
✅ DO: Measure and limit fuel consumption

❌ DON'T: Run untrusted wasm without limits
❌ DON'T: Grant filesystem access to root
❌ DON'T: Ignore fuel/memory exhaustion
```

---

## Anti-Patterns

### Critical Violations

```rust
// ❌ NEVER: Run untrusted code without limits
fn unsafe_execute(wasm_bytes: &[u8]) -> Result<()> {
    let engine = Engine::default();
    let module = Module::new(&engine, wasm_bytes)?;
    let mut store = Store::new(&engine, ());
    let instance = Instance::new(&mut store, &module, &[])?;

    // No fuel limit, no timeout - can run forever!
    let func = instance.get_typed_func::<(), ()>(&mut store, "run")?;
    func.call(&mut store, ())?;
    Ok(())
}

// ✅ CORRECT: Always enforce limits
fn safe_execute(wasm_bytes: &[u8]) -> Result<()> {
    let mut config = Config::default();
    config.consume_fuel(true);

    let engine = Engine::new(&config)?;
    let module = Module::new(&engine, wasm_bytes)?;
    let mut store = Store::new(&engine, ());

    store.add_fuel(1_000_000)?; // Limit instructions

    let instance = Instance::new(&mut store, &module, &[])?;

    let func = instance.get_typed_func::<(), ()>(&mut store, "run")?;
    func.call(&mut store, ())?;

    Ok(())
}
```

❌ **No resource limits**: Infinite loops, memory exhaustion
✅ **Correct approach**: Always set fuel and memory limits

### Common Mistakes

```rust
// ❌ Don't: Grant unrestricted filesystem access
let wasi = WasiCtxBuilder::new()
    .preopened_dir(Dir::open_ambient_dir("/", ambient_authority())?, "/")?
    .build();

// ✅ Correct: Minimal necessary access
let wasi = WasiCtxBuilder::new()
    .preopened_dir(Dir::open_ambient_dir("./user_data", ambient_authority())?, "/data")?
    .build();
```

❌ **Over-permissioning**: Security vulnerability
✅ **Better**: Least-privilege principle

---

## Related Skills

- `wasm-fundamentals.md` - Core WebAssembly concepts
- `wasm-rust-toolchain.md` - Compiling Rust to wasm
- `api-security.md` - Securing API endpoints
- `container-security.md` - Sandboxing patterns

---

**Last Updated**: 2025-10-25
**Format Version**: 1.0 (Atomic)
