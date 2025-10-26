---
name: wasm-browser-integration
description: Loading WebAssembly modules in browsers with JavaScript interop, DOM access, WebGL, and performance optimization
---

# WebAssembly Browser Integration

**Scope**: Loading wasm in browsers, JavaScript interop, DOM manipulation, WebGL rendering, and performance patterns
**Lines**: ~320
**Last Updated**: 2025-10-25
**Format Version**: 1.0 (Atomic)

---

## When to Use This Skill

Activate this skill when:
- Loading and instantiating wasm modules in browsers
- Passing data between JavaScript and wasm efficiently
- Accessing DOM elements from wasm code
- Rendering graphics with WebGL from wasm
- Using Web Workers with wasm for parallel processing
- Optimizing memory sharing between JS and wasm
- Implementing progressive enhancement with wasm
- Caching compiled wasm modules for faster loading

## Core Concepts

### Concept 1: Loading and Instantiation

**Methods**:
- `WebAssembly.instantiate()`: Compile + instantiate
- `WebAssembly.instantiateStreaming()`: Stream compile (faster)
- `WebAssembly.compile()`: Compile only
- `WebAssembly.compileStreaming()`: Stream compile only

```javascript
// ❌ Slower: Fetch then instantiate
async function loadWasmSlow(url) {
    const response = await fetch(url);
    const bytes = await response.arrayBuffer();
    const { instance } = await WebAssembly.instantiate(bytes);
    return instance;
}

// ✅ Faster: Streaming compilation
async function loadWasmFast(url) {
    const { instance } = await WebAssembly.instantiateStreaming(
        fetch(url)
    );
    return instance;
}

// With imports
async function loadWasmWithImports(url) {
    const importObject = {
        env: {
            log: (value) => console.log(value),
            now: () => Date.now(),
        }
    };

    const { instance } = await WebAssembly.instantiateStreaming(
        fetch(url),
        importObject
    );

    return instance;
}
```

### Concept 2: Memory Sharing

**Key points**:
- WebAssembly.Memory is shared ArrayBuffer
- JavaScript can read/write directly
- Use TypedArrays for efficient access
- Watch for memory growth invalidating views

```javascript
// Access wasm linear memory
const memory = instance.exports.memory;
const buffer = memory.buffer;

// Create typed views
const uint8View = new Uint8Array(buffer);
const int32View = new Int32Array(buffer);
const float64View = new Float64Array(buffer);

// Write data to wasm memory
function writeString(str, offset) {
    const encoder = new TextEncoder();
    const bytes = encoder.encode(str);
    uint8View.set(bytes, offset);
    return bytes.length;
}

// Read data from wasm memory
function readString(offset, length) {
    const bytes = uint8View.slice(offset, offset + length);
    const decoder = new TextDecoder();
    return decoder.decode(bytes);
}

// Handle memory growth
function safeMemoryAccess(instance) {
    let buffer = instance.exports.memory.buffer;
    let view = new Uint8Array(buffer);

    // After wasm calls memory.grow()
    if (buffer !== instance.exports.memory.buffer) {
        buffer = instance.exports.memory.buffer;
        view = new Uint8Array(buffer); // Recreate view
    }

    return view;
}
```

### Concept 3: DOM Access via web-sys

**Using web-sys crate** (Rust):

```rust
use wasm_bindgen::prelude::*;
use web_sys::{Document, Element, HtmlElement, window};

#[wasm_bindgen(start)]
pub fn main() {
    let document = window()
        .unwrap()
        .document()
        .unwrap();

    let body = document.body().unwrap();

    // Create element
    let div = document
        .create_element("div")
        .unwrap()
        .dyn_into::<HtmlElement>()
        .unwrap();

    div.set_inner_html("<h1>Hello from Rust!</h1>");
    div.style().set_property("color", "blue").unwrap();

    body.append_child(&div).unwrap();
}

// Event listeners
#[wasm_bindgen]
pub fn setup_button() {
    let document = window().unwrap().document().unwrap();
    let button = document
        .get_element_by_id("my-button")
        .unwrap()
        .dyn_into::<HtmlElement>()
        .unwrap();

    let closure = Closure::wrap(Box::new(move |_event: web_sys::MouseEvent| {
        web_sys::console::log_1(&"Button clicked!".into());
    }) as Box<dyn FnMut(_)>);

    button
        .add_event_listener_with_callback("click", closure.as_ref().unchecked_ref())
        .unwrap();

    closure.forget(); // Keep closure alive
}
```

### Concept 4: WebGL Rendering

**Pattern**: Use wasm for computation, WebGL for rendering

```rust
use wasm_bindgen::prelude::*;
use web_sys::{WebGlRenderingContext, WebGlProgram, WebGlShader};

#[wasm_bindgen]
pub struct Renderer {
    context: WebGlRenderingContext,
    program: WebGlProgram,
}

#[wasm_bindgen]
impl Renderer {
    #[wasm_bindgen(constructor)]
    pub fn new(canvas_id: &str) -> Result<Renderer, JsValue> {
        let document = web_sys::window().unwrap().document().unwrap();
        let canvas = document.get_element_by_id(canvas_id).unwrap();
        let canvas: web_sys::HtmlCanvasElement = canvas.dyn_into()?;

        let context = canvas
            .get_context("webgl")?
            .unwrap()
            .dyn_into::<WebGlRenderingContext>()?;

        let vert_shader = compile_shader(
            &context,
            WebGlRenderingContext::VERTEX_SHADER,
            r#"
            attribute vec4 position;
            void main() {
                gl_Position = position;
            }
            "#,
        )?;

        let frag_shader = compile_shader(
            &context,
            WebGlRenderingContext::FRAGMENT_SHADER,
            r#"
            void main() {
                gl_FragColor = vec4(1.0, 0.0, 0.0, 1.0);
            }
            "#,
        )?;

        let program = link_program(&context, &vert_shader, &frag_shader)?;
        context.use_program(Some(&program));

        Ok(Renderer { context, program })
    }

    pub fn render(&self) {
        self.context.clear_color(0.0, 0.0, 0.0, 1.0);
        self.context.clear(WebGlRenderingContext::COLOR_BUFFER_BIT);
        // Draw calls...
    }
}

fn compile_shader(
    context: &WebGlRenderingContext,
    shader_type: u32,
    source: &str,
) -> Result<WebGlShader, String> {
    let shader = context
        .create_shader(shader_type)
        .ok_or_else(|| String::from("Unable to create shader"))?;

    context.shader_source(&shader, source);
    context.compile_shader(&shader);

    if context
        .get_shader_parameter(&shader, WebGlRenderingContext::COMPILE_STATUS)
        .as_bool()
        .unwrap_or(false)
    {
        Ok(shader)
    } else {
        Err(context
            .get_shader_info_log(&shader)
            .unwrap_or_else(|| String::from("Unknown error")))
    }
}

fn link_program(
    context: &WebGlRenderingContext,
    vert_shader: &WebGlShader,
    frag_shader: &WebGlShader,
) -> Result<WebGlProgram, String> {
    let program = context
        .create_program()
        .ok_or_else(|| String::from("Unable to create program"))?;

    context.attach_shader(&program, vert_shader);
    context.attach_shader(&program, frag_shader);
    context.link_program(&program);

    if context
        .get_program_parameter(&program, WebGlRenderingContext::LINK_STATUS)
        .as_bool()
        .unwrap_or(false)
    {
        Ok(program)
    } else {
        Err(context
            .get_program_info_log(&program)
            .unwrap_or_else(|| String::from("Unknown error")))
    }
}
```

---

## Patterns

### Pattern 1: Progressive Enhancement

**When to use**: Graceful fallback when wasm unavailable

```javascript
async function initApp() {
    if (typeof WebAssembly !== 'object') {
        console.warn('WebAssembly not supported, using JavaScript fallback');
        return new JavaScriptImplementation();
    }

    try {
        const { instance } = await WebAssembly.instantiateStreaming(
            fetch('app.wasm')
        );
        return new WasmImplementation(instance);
    } catch (error) {
        console.error('Failed to load wasm:', error);
        return new JavaScriptImplementation();
    }
}

class WasmImplementation {
    constructor(instance) {
        this.wasm = instance.exports;
    }

    process(data) {
        // Use fast wasm implementation
        return this.wasm.process(data);
    }
}

class JavaScriptImplementation {
    process(data) {
        // Pure JS fallback (slower but compatible)
        return data.map(x => x * 2);
    }
}
```

### Pattern 2: Module Caching

**Use case**: Cache compiled wasm for instant reload

```javascript
const WASM_CACHE_NAME = 'wasm-cache-v1';

async function loadWasmCached(url) {
    // Try to get from cache
    const cache = await caches.open(WASM_CACHE_NAME);
    const cachedResponse = await cache.match(url);

    if (cachedResponse) {
        const cachedModule = await WebAssembly.compileStreaming(cachedResponse);
        const { instance } = await WebAssembly.instantiate(cachedModule);
        return instance;
    }

    // Not cached, fetch and cache
    const response = await fetch(url);
    cache.put(url, response.clone());

    const { instance } = await WebAssembly.instantiateStreaming(response);
    return instance;
}
```

### Pattern 3: Web Worker Integration

**Use case**: Run wasm in background thread

```javascript
// main.js
const worker = new Worker('wasm-worker.js');

worker.postMessage({
    type: 'init',
    wasmUrl: 'compute.wasm'
});

worker.postMessage({
    type: 'compute',
    data: largeDataset
});

worker.onmessage = (event) => {
    if (event.data.type === 'result') {
        console.log('Result:', event.data.value);
    }
};

// wasm-worker.js
let wasmInstance;

self.onmessage = async (event) => {
    if (event.data.type === 'init') {
        const { instance } = await WebAssembly.instantiateStreaming(
            fetch(event.data.wasmUrl)
        );
        wasmInstance = instance;
        self.postMessage({ type: 'ready' });
    }

    if (event.data.type === 'compute' && wasmInstance) {
        const result = wasmInstance.exports.compute(event.data.data);
        self.postMessage({
            type: 'result',
            value: result
        });
    }
};
```

### Pattern 4: Efficient Data Transfer

**Use case**: Minimize copying between JS and wasm

```rust
use wasm_bindgen::prelude::*;

#[wasm_bindgen]
pub struct ImageProcessor {
    buffer: Vec<u8>,
}

#[wasm_bindgen]
impl ImageProcessor {
    #[wasm_bindgen(constructor)]
    pub fn new(size: usize) -> ImageProcessor {
        ImageProcessor {
            buffer: vec![0; size],
        }
    }

    // Return pointer to internal buffer (zero-copy)
    pub fn get_buffer_ptr(&self) -> *const u8 {
        self.buffer.as_ptr()
    }

    pub fn process(&mut self) {
        // Process buffer in-place
        for pixel in &mut self.buffer {
            *pixel = pixel.saturating_add(10);
        }
    }
}
```

```javascript
// JavaScript side
const processor = new ImageProcessor(1000000);
const ptr = processor.get_buffer_ptr();

// Get view of wasm memory
const memory = new Uint8Array(
    processor.__wbg_get_buffer_memory().buffer,
    ptr,
    1000000
);

// Write data directly to wasm memory (zero-copy)
memory.set(imageData);

// Process in wasm
processor.process();

// Read result (zero-copy)
const result = memory.slice();
```

### Pattern 5: Animation Loop

**Use case**: Smooth 60fps rendering with wasm

```rust
use wasm_bindgen::prelude::*;

#[wasm_bindgen]
pub struct Game {
    last_timestamp: f64,
}

#[wasm_bindgen]
impl Game {
    #[wasm_bindgen(constructor)]
    pub fn new() -> Game {
        Game { last_timestamp: 0.0 }
    }

    pub fn update(&mut self, timestamp: f64) -> bool {
        let delta = timestamp - self.last_timestamp;
        self.last_timestamp = timestamp;

        // Update game state
        // Return true to continue, false to stop
        true
    }
}
```

```javascript
const game = new Game();

function gameLoop(timestamp) {
    const shouldContinue = game.update(timestamp);

    if (shouldContinue) {
        requestAnimationFrame(gameLoop);
    }
}

requestAnimationFrame(gameLoop);
```

### Pattern 6: Error Boundary

**Use case**: Graceful error handling

```javascript
class WasmErrorBoundary {
    constructor(wasmInstance) {
        this.wasm = wasmInstance;
        this.fallbackActive = false;
    }

    async execute(method, ...args) {
        if (this.fallbackActive) {
            return this.fallback(method, ...args);
        }

        try {
            return this.wasm.exports[method](...args);
        } catch (error) {
            console.error(`Wasm error in ${method}:`, error);
            this.fallbackActive = true;
            return this.fallback(method, ...args);
        }
    }

    fallback(method, ...args) {
        // Pure JavaScript implementation
        switch (method) {
            case 'add':
                return args[0] + args[1];
            default:
                throw new Error(`No fallback for ${method}`);
        }
    }
}
```

---

## Quick Reference

### Loading Methods

```
Method                        | Use Case                     | Performance
------------------------------|------------------------------|-------------
instantiateStreaming(fetch()) | Production (fastest)         | Excellent
instantiate(arrayBuffer)      | When streaming unavailable   | Good
compile() + instantiate()     | Cache compiled module        | Excellent
```

### Memory Access Patterns

```javascript
// Read primitives
const i32 = new Int32Array(memory.buffer)[offset / 4];
const f64 = new Float64Array(memory.buffer)[offset / 8];

// Read string
const bytes = new Uint8Array(memory.buffer, offset, length);
const str = new TextDecoder().decode(bytes);

// Write string
const encoded = new TextEncoder().encode(str);
new Uint8Array(memory.buffer).set(encoded, offset);
```

### Key Guidelines

```
✅ DO: Use instantiateStreaming for best performance
✅ DO: Cache compiled wasm modules
✅ DO: Use Web Workers for heavy computation
✅ DO: Recreate TypedArray views after memory growth
✅ DO: Minimize data copying between JS and wasm

❌ DON'T: Use fetch().arrayBuffer() unnecessarily
❌ DON'T: Copy large data when pointers work
❌ DON'T: Block main thread with heavy wasm work
```

---

## Anti-Patterns

### Critical Violations

```javascript
// ❌ NEVER: Ignore memory growth
const view = new Uint8Array(instance.exports.memory.buffer);
instance.exports.grow_memory(); // Invalidates view!
view[100] = 42; // May crash or write to wrong location

// ✅ CORRECT: Recreate view after growth
function safeWrite(instance, offset, value) {
    const view = new Uint8Array(instance.exports.memory.buffer);
    view[offset] = value;
}
```

❌ **Stale memory views**: Undefined behavior, crashes
✅ **Correct approach**: Recreate views or check buffer identity

### Common Mistakes

```javascript
// ❌ Don't: Excessive copying
function processImageBad(imageData) {
    const ptr = instance.exports.allocate(imageData.length);
    const memory = new Uint8Array(instance.exports.memory.buffer);

    // Copy to wasm
    memory.set(imageData, ptr);

    instance.exports.process(ptr, imageData.length);

    // Copy back
    const result = memory.slice(ptr, ptr + imageData.length);
    instance.exports.deallocate(ptr);

    return result;
}

// ✅ Correct: Process in-place
function processImageGood(imageData) {
    const ptr = instance.exports.get_shared_buffer();
    const memory = new Uint8Array(
        instance.exports.memory.buffer,
        ptr,
        imageData.length
    );

    memory.set(imageData); // Single copy
    instance.exports.process_shared(imageData.length);
    // memory already has result, no copy back needed
}
```

❌ **Multiple copies**: 2x slower, 2x memory
✅ **Better**: Use shared buffers when possible

---

## Related Skills

- `wasm-fundamentals.md` - Core WebAssembly concepts
- `wasm-rust-toolchain.md` - Compiling Rust to wasm
- `frontend-performance.md` - Web performance optimization
- `web-workers.md` - Background processing patterns

---

**Last Updated**: 2025-10-25
**Format Version**: 1.0 (Atomic)
