---
name: pyo3-web-frameworks
description: PyO3 for web services and system integration including systemd, IPC, gRPC, HTTP clients/servers
skill_id: rust-pyo3-web-frameworks
title: PyO3 Web Framework Integration
category: rust
subcategory: pyo3
complexity: advanced
prerequisites:
  - rust-pyo3-basics-types-conversions
  - rust-pyo3-modules-functions-errors
  - rust-pyo3-async-embedded-wasm
tags:
  - rust
  - python
  - pyo3
  - fastapi
  - flask
  - django
  - websocket
  - async
  - web
  - http
version: 1.0.0
last_updated: 2025-10-30
learning_outcomes:
  - Integrate PyO3 extensions with FastAPI
  - Build high-performance Flask extensions
  - Create Django backends with Rust
  - Handle WebSocket connections efficiently
  - Implement async request handlers
  - Build middleware and plugins
  - Optimize web application performance
  - Deploy production web services
related_skills:
  - rust-pyo3-async-embedded-wasm
  - rust-pyo3-performance-gil-parallel
  - web-fastapi-advanced
---

# PyO3 Web Framework Integration

## Overview

Master the integration of PyO3 extensions with Python web frameworks. Learn to build high-performance backends, handle async operations, process WebSocket connections, and create production-ready web services leveraging Rust's performance.

## Prerequisites

- **Required**: PyO3 basics, async/await patterns, web framework fundamentals
- **Recommended**: FastAPI/Flask/Django experience, WebSocket knowledge, HTTP protocols
- **Tools**: pyo3, pyo3-asyncio, tokio, axum/actix-web (optional)

## Learning Path

### 1. FastAPI Integration

FastAPI is a modern, async Python web framework perfect for high-performance APIs.

#### Basic Extension

```rust
use pyo3::prelude::*;

#[pyfunction]
fn fast_compute(data: Vec<f64>) -> f64 {
    // CPU-intensive computation in Rust
    data.iter().map(|x| x.powi(2)).sum::<f64>().sqrt()
}

#[pymodule]
fn _core(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(fast_compute, m)?)?;
    Ok(())
}
```

```python
# main.py
from fastapi import FastAPI
from my_extension import fast_compute

app = FastAPI()

@app.post("/compute")
async def compute_endpoint(data: list[float]):
    # Offload computation to Rust
    result = fast_compute(data)
    return {"result": result}
```

#### Async Request Handler

```rust
use pyo3::prelude::*;
use pyo3_asyncio::tokio::future_into_py;
use tokio::time::Duration;

#[pyfunction]
fn async_process(py: Python, data: Vec<f64>) -> PyResult<&PyAny> {
    future_into_py(py, async move {
        // Async processing in Rust
        tokio::time::sleep(Duration::from_millis(100)).await;

        let result: f64 = data.iter().sum();

        Ok(Python::with_gil(|py| result.into_py(py)))
    })
}
```

```python
from fastapi import FastAPI
from my_extension import async_process

app = FastAPI()

@app.post("/async-compute")
async def async_endpoint(data: list[float]):
    result = await async_process(data)
    return {"result": result}
```

#### Pydantic Model Integration

```rust
use pyo3::prelude::*;
use pyo3::types::PyDict;

#[pyfunction]
fn process_model(py: Python, model: &PyAny) -> PyResult<PyObject> {
    // Extract Pydantic model fields
    let data: Vec<f64> = model.getattr("data")?.extract()?;
    let threshold: f64 = model.getattr("threshold")?.extract()?;

    // Process in Rust
    let filtered: Vec<f64> = data.into_iter()
        .filter(|&x| x > threshold)
        .collect();

    // Create response dict
    let result = PyDict::new(py);
    result.set_item("count", filtered.len())?;
    result.set_item("values", filtered)?;

    Ok(result.into())
}
```

```python
from fastapi import FastAPI
from pydantic import BaseModel
from my_extension import process_model

class ComputeRequest(BaseModel):
    data: list[float]
    threshold: float

@app.post("/process")
async def process_endpoint(request: ComputeRequest):
    result = process_model(request)
    return result
```

### 2. Flask Integration

Flask is a lightweight, synchronous web framework.

#### Flask Extension

```rust
use pyo3::prelude::*;

#[pyfunction]
fn process_request(headers: Vec<(String, String)>, body: Vec<u8>) -> PyResult<Vec<u8>> {
    // Fast request processing in Rust
    Ok(body)  // Echo for now
}

#[pyfunction]
fn compress_response(data: Vec<u8>) -> PyResult<Vec<u8>> {
    // Compress response data
    use flate2::write::GzEncoder;
    use flate2::Compression;
    use std::io::Write;

    let mut encoder = GzEncoder::new(Vec::new(), Compression::default());
    encoder.write_all(&data)?;
    Ok(encoder.finish()?)
}
```

```python
from flask import Flask, request, Response
from my_extension import process_request, compress_response

app = Flask(__name__)

@app.route("/api/data", methods=["POST"])
def handle_data():
    # Extract request data
    headers = list(request.headers.items())
    body = request.data

    # Process in Rust
    result = process_request(headers, body)

    # Compress response
    compressed = compress_response(result)

    return Response(compressed, mimetype="application/octet-stream")
```

#### Flask Middleware

```rust
#[pyclass]
struct RequestTimer {
    start_times: std::collections::HashMap<u64, std::time::Instant>,
}

#[pymethods]
impl RequestTimer {
    #[new]
    fn new() -> Self {
        RequestTimer {
            start_times: std::collections::HashMap::new(),
        }
    }

    fn start_request(&mut self, request_id: u64) {
        self.start_times.insert(request_id, std::time::Instant::now());
    }

    fn end_request(&mut self, request_id: u64) -> f64 {
        if let Some(start) = self.start_times.remove(&request_id) {
            start.elapsed().as_secs_f64()
        } else {
            0.0
        }
    }
}
```

```python
from flask import Flask, g
from my_extension import RequestTimer
import time

app = Flask(__name__)
timer = RequestTimer()

@app.before_request
def before_request():
    g.request_id = id(request)
    timer.start_request(g.request_id)

@app.after_request
def after_request(response):
    duration = timer.end_request(g.request_id)
    response.headers["X-Request-Duration"] = str(duration)
    return response
```

### 3. Django Integration

Django is a full-featured web framework with ORM.

#### Django Extension Module

```rust
use pyo3::prelude::*;

#[pyfunction]
fn validate_data(data: &PyAny) -> PyResult<bool> {
    // Fast validation logic
    Ok(true)
}

#[pyfunction]
fn serialize_queryset(py: Python, queryset: &PyAny) -> PyResult<Vec<PyObject>> {
    // Fast queryset serialization
    let items: Vec<PyObject> = queryset.call_method0("all")?
        .iter()?
        .map(|item| item.unwrap().into())
        .collect();

    Ok(items)
}
```

```python
# views.py
from django.http import JsonResponse
from my_extension import validate_data, serialize_queryset
from .models import MyModel

def api_view(request):
    data = request.POST

    # Fast validation
    if not validate_data(data):
        return JsonResponse({"error": "Invalid data"}, status=400)

    # Fast queryset processing
    queryset = MyModel.objects.filter(active=True)
    results = serialize_queryset(queryset)

    return JsonResponse({"results": results})
```

#### Django Middleware

```rust
#[pyclass]
struct RateLimiter {
    requests: std::collections::HashMap<String, Vec<std::time::Instant>>,
    limit: usize,
    window: std::time::Duration,
}

#[pymethods]
impl RateLimiter {
    #[new]
    fn new(limit: usize, window_seconds: u64) -> Self {
        RateLimiter {
            requests: std::collections::HashMap::new(),
            limit,
            window: std::time::Duration::from_secs(window_seconds),
        }
    }

    fn check_rate_limit(&mut self, ip: String) -> bool {
        let now = std::time::Instant::now();
        let entry = self.requests.entry(ip).or_insert_with(Vec::new);

        // Remove old requests
        entry.retain(|&t| now.duration_since(t) < self.window);

        // Check limit
        if entry.len() >= self.limit {
            false
        } else {
            entry.push(now);
            true
        }
    }
}
```

```python
# middleware.py
from django.http import HttpResponse
from my_extension import RateLimiter

rate_limiter = RateLimiter(limit=100, window_seconds=60)

class RateLimitMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        ip = request.META.get('REMOTE_ADDR')

        if not rate_limiter.check_rate_limit(ip):
            return HttpResponse("Rate limit exceeded", status=429)

        response = self.get_response(request)
        return response
```

### 4. WebSocket Handling

```rust
use pyo3::prelude::*;
use tokio::sync::mpsc;

#[pyclass]
struct WebSocketHandler {
    sender: mpsc::UnboundedSender<Vec<u8>>,
}

#[pymethods]
impl WebSocketHandler {
    #[new]
    fn new() -> Self {
        let (sender, mut receiver) = mpsc::unbounded_channel();

        // Spawn background task
        tokio::spawn(async move {
            while let Some(msg) = receiver.recv().await {
                // Process WebSocket messages
                println!("Received: {} bytes", msg.len());
            }
        });

        WebSocketHandler { sender }
    }

    fn send_message(&self, data: Vec<u8>) -> PyResult<()> {
        self.sender.send(data)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                format!("Failed to send: {}", e)
            ))
    }
}
```

```python
# FastAPI WebSocket
from fastapi import FastAPI, WebSocket
from my_extension import WebSocketHandler

app = FastAPI()
handler = WebSocketHandler()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    while True:
        data = await websocket.receive_bytes()
        handler.send_message(data)
        await websocket.send_text("Processed")
```

### 5. High-Performance Request Processing

```rust
use pyo3::prelude::*;
use rayon::prelude::*;

#[pyfunction]
fn batch_process(py: Python, requests: Vec<Vec<u8>>) -> Vec<Vec<u8>> {
    // Release GIL for parallel processing
    py.allow_threads(|| {
        requests.par_iter()
            .map(|req| {
                // Process each request in parallel
                process_single_request(req)
            })
            .collect()
    })
}

fn process_single_request(data: &[u8]) -> Vec<u8> {
    // Fast request processing
    data.to_vec()
}

#[pyfunction]
fn parse_json(data: Vec<u8>) -> PyResult<PyObject> {
    // Fast JSON parsing with serde_json
    use serde_json::Value;

    let value: Value = serde_json::from_slice(&data)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))?;

    Python::with_gil(|py| {
        // Convert to Python object
        Ok(py.None())  // Simplified
    })
}
```

### 6. Caching Layer

```rust
use pyo3::prelude::*;
use std::collections::HashMap;
use std::sync::{Arc, RwLock};

#[pyclass]
struct Cache {
    data: Arc<RwLock<HashMap<String, Vec<u8>>>>,
}

#[pymethods]
impl Cache {
    #[new]
    fn new() -> Self {
        Cache {
            data: Arc::new(RwLock::new(HashMap::new())),
        }
    }

    fn get(&self, key: String) -> Option<Vec<u8>> {
        self.data.read().unwrap().get(&key).cloned()
    }

    fn set(&self, key: String, value: Vec<u8>) {
        self.data.write().unwrap().insert(key, value);
    }

    fn clear(&self) {
        self.data.write().unwrap().clear();
    }
}
```

```python
from my_extension import Cache

cache = Cache()

@app.get("/data/{key}")
async def get_data(key: str):
    # Check cache first
    cached = cache.get(key)
    if cached:
        return Response(cached)

    # Compute if not cached
    data = expensive_computation(key)
    cache.set(key, data)

    return Response(data)
```

### 7. Authentication & Security

```rust
use pyo3::prelude::*;
use hmac::{Hmac, Mac};
use sha2::Sha256;

type HmacSha256 = Hmac<Sha256>;

#[pyfunction]
fn verify_signature(message: Vec<u8>, signature: Vec<u8>, key: Vec<u8>) -> bool {
    let mut mac = HmacSha256::new_from_slice(&key).unwrap();
    mac.update(&message);

    mac.verify_slice(&signature).is_ok()
}

#[pyfunction]
fn hash_password(password: String) -> PyResult<String> {
    use argon2::{Argon2, PasswordHasher};
    use argon2::password_hash::SaltString;

    let salt = SaltString::generate(&mut rand::thread_rng());
    let argon2 = Argon2::default();

    Ok(argon2.hash_password(password.as_bytes(), &salt)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?
        .to_string())
}

#[pyfunction]
fn verify_password(password: String, hash: String) -> PyResult<bool> {
    use argon2::{Argon2, PasswordVerifier, PasswordHash};

    let parsed_hash = PasswordHash::new(&hash)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))?;

    Ok(Argon2::default()
        .verify_password(password.as_bytes(), &parsed_hash)
        .is_ok())
}
```

### 8. API Response Serialization

```rust
use pyo3::prelude::*;
use serde::{Serialize, Deserialize};

#[derive(Serialize, Deserialize)]
struct ApiResponse {
    status: String,
    data: Vec<f64>,
    count: usize,
}

#[pyfunction]
fn serialize_response(data: Vec<f64>) -> PyResult<Vec<u8>> {
    let response = ApiResponse {
        status: "success".to_string(),
        count: data.len(),
        data,
    };

    serde_json::to_vec(&response)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))
}

#[pyfunction]
fn deserialize_request(data: Vec<u8>) -> PyResult<Vec<f64>> {
    let response: ApiResponse = serde_json::from_slice(&data)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))?;

    Ok(response.data)
}
```

## Common Patterns

### Async Handler Pattern

```rust
#[pyfunction]
fn async_handler(py: Python, data: Vec<u8>) -> PyResult<&PyAny> {
    future_into_py(py, async move {
        // Async work
        tokio::time::sleep(Duration::from_millis(10)).await;

        // Process data
        let result = process_data(&data);

        Ok(Python::with_gil(|py| result.into_py(py)))
    })
}
```

### Middleware Pattern

```python
class RustMiddleware:
    def __init__(self, app):
        self.app = app
        self.processor = RustProcessor()

    async def __call__(self, scope, receive, send):
        # Pre-process with Rust
        scope = self.processor.process_scope(scope)

        # Call next middleware/app
        await self.app(scope, receive, send)
```

## Anti-Patterns

### ❌ Incorrect: Holding GIL During I/O

```rust
#[pyfunction]
fn bad_handler(url: String) -> PyResult<Vec<u8>> {
    // Blocks Python while waiting for I/O
    let response = reqwest::blocking::get(&url)?;
    Ok(response.bytes()?.to_vec())
}
```

### ✅ Correct: Release GIL

```rust
#[pyfunction]
fn good_handler(py: Python, url: String) -> PyResult<Vec<u8>> {
    py.allow_threads(|| {
        let response = reqwest::blocking::get(&url)?;
        Ok(response.bytes()?.to_vec())
    })
}
```

## Resources

### Crates
- **pyo3**: Python bindings
- **pyo3-asyncio**: Async integration
- **tokio**: Async runtime
- **serde_json**: JSON serialization
- **axum/actix-web**: Optional Rust web frameworks

### Documentation
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Flask Documentation](https://flask.palletsprojects.com/)
- [Django Documentation](https://docs.djangoproject.com/)

### Related Skills
- [pyo3-async-embedded-wasm.md](pyo3-async-embedded-wasm.md)
- [pyo3-performance-gil-parallel.md](pyo3-performance-gil-parallel.md)

## Examples

See `resources/examples/` for:
1. FastAPI integration
2. Flask extension
3. Django backend
4. WebSocket handler
5. Async request processing
6. Caching layer
7. Authentication system
8. Rate limiting
9. Request batching
10. Production web service

## Additional Resources

- **REFERENCE.md**: Comprehensive patterns and examples
- **Scripts**:
  - `api_benchmark.py`: API performance benchmarking
  - `middleware_generator.py`: Middleware boilerplate generation
  - `websocket_tester.py`: WebSocket connection testing
