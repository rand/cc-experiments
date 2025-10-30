# PyO3 Web Frameworks Integration - Complete Reference

**Version**: 1.0.0
**Last Updated**: 2025-10-30
**Skill**: rust-pyo3-web-frameworks

This is a comprehensive reference for integrating PyO3 with Python web frameworks. It covers FastAPI, Flask, Django, WebSocket handling, HTTP processing, response generation, authentication, caching, API development, and production deployment patterns.

---

## Table of Contents

1. [FastAPI Integration](#1-fastapi-integration)
2. [Flask Integration](#2-flask-integration)
3. [Django Integration](#3-django-integration)
4. [WebSocket Handling](#4-websocket-handling)
5. [HTTP Processing](#5-http-processing)
6. [Response Generation](#6-response-generation)
7. [Authentication](#7-authentication)
8. [Caching & Performance](#8-caching--performance)
9. [API Development](#9-api-development)
10. [Production Deployment](#10-production-deployment)

---

## 1. FastAPI Integration

### 1.1 Setup

```toml
# Cargo.toml
[dependencies]
pyo3 = { version = "0.20", features = ["extension-module"] }
serde = { version = "1.0", features = ["derive"] }
serde_json = "1.0"
tokio = { version = "1", features = ["full"] }
```

### 1.2 Async Route Handlers

```rust
use pyo3::prelude::*;
use pyo3::types::PyDict;
use serde::{Deserialize, Serialize};

#[derive(Serialize, Deserialize)]
struct User {
    id: u64,
    name: String,
    email: String,
}

#[pyfunction]
fn process_user_request(py: Python, request_data: &str) -> PyResult<String> {
    let user: User = serde_json::from_str(request_data)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))?;

    // Process user data
    let result = User {
        id: user.id,
        name: user.name.to_uppercase(),
        email: user.email.to_lowercase(),
    };

    serde_json::to_string(&result)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))
}

#[pyfunction]
fn validate_request_body(request_json: &str) -> PyResult<bool> {
    let value: serde_json::Value = serde_json::from_str(request_json)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))?;

    // Validate required fields
    let valid = value.get("id").is_some()
        && value.get("name").is_some()
        && value.get("email").is_some();

    Ok(valid)
}
```

### 1.3 Pydantic Model Integration

```rust
use pyo3::types::{PyModule, PyTuple};

#[pyclass]
#[derive(Clone)]
struct ValidationResult {
    #[pyo3(get, set)]
    valid: bool,
    #[pyo3(get, set)]
    errors: Vec<String>,
}

#[pymethods]
impl ValidationResult {
    #[new]
    fn new(valid: bool, errors: Vec<String>) -> Self {
        ValidationResult { valid, errors }
    }

    fn __repr__(&self) -> String {
        format!("ValidationResult(valid={}, errors={:?})", self.valid, self.errors)
    }
}

#[pyfunction]
fn validate_pydantic_model(py: Python, model: &PyAny) -> PyResult<ValidationResult> {
    // Extract fields from Pydantic model
    let dict = model.call_method0("dict")?;

    let mut errors = Vec::new();

    // Validate each field
    if let Ok(email) = dict.get_item("email") {
        let email_str: String = email.extract()?;
        if !email_str.contains('@') {
            errors.push("Invalid email format".to_string());
        }
    } else {
        errors.push("Missing email field".to_string());
    }

    if let Ok(age) = dict.get_item("age") {
        let age_val: i32 = age.extract()?;
        if age_val < 0 || age_val > 150 {
            errors.push("Age must be between 0 and 150".to_string());
        }
    }

    Ok(ValidationResult::new(errors.is_empty(), errors))
}
```

### 1.4 Dependency Injection Helpers

```rust
use std::collections::HashMap;
use std::sync::{Arc, RwLock};

#[pyclass]
struct DependencyContainer {
    dependencies: Arc<RwLock<HashMap<String, PyObject>>>,
}

#[pymethods]
impl DependencyContainer {
    #[new]
    fn new() -> Self {
        DependencyContainer {
            dependencies: Arc::new(RwLock::new(HashMap::new())),
        }
    }

    fn register(&self, py: Python, name: String, dependency: PyObject) -> PyResult<()> {
        let mut deps = self.dependencies.write()
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                format!("Lock error: {}", e)
            ))?;

        deps.insert(name, dependency);
        Ok(())
    }

    fn resolve(&self, py: Python, name: String) -> PyResult<PyObject> {
        let deps = self.dependencies.read()
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                format!("Lock error: {}", e)
            ))?;

        deps.get(&name)
            .cloned()
            .ok_or_else(|| PyErr::new::<pyo3::exceptions::PyKeyError, _>(
                format!("Dependency '{}' not found", name)
            ))
    }

    fn clear(&self) -> PyResult<()> {
        let mut deps = self.dependencies.write()
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                format!("Lock error: {}", e)
            ))?;

        deps.clear();
        Ok(())
    }
}
```

### 1.5 Background Tasks

```rust
use std::thread;
use std::time::Duration;

#[pyfunction]
fn schedule_background_task(py: Python, task_data: String, callback: PyObject) -> PyResult<()> {
    thread::spawn(move || {
        // Simulate long-running task
        thread::sleep(Duration::from_secs(2));

        // Process data
        let result = task_data.to_uppercase();

        // Call Python callback
        Python::with_gil(|py| {
            if let Err(e) = callback.call1(py, (result,)) {
                eprintln!("Callback error: {}", e);
            }
        });
    });

    Ok(())
}

#[pyclass]
struct TaskQueue {
    tasks: Arc<RwLock<Vec<String>>>,
}

#[pymethods]
impl TaskQueue {
    #[new]
    fn new() -> Self {
        TaskQueue {
            tasks: Arc::new(RwLock::new(Vec::new())),
        }
    }

    fn enqueue(&self, task: String) -> PyResult<()> {
        let mut tasks = self.tasks.write()
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                format!("Lock error: {}", e)
            ))?;

        tasks.push(task);
        Ok(())
    }

    fn dequeue(&self) -> PyResult<Option<String>> {
        let mut tasks = self.tasks.write()
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                format!("Lock error: {}", e)
            ))?;

        Ok(tasks.pop())
    }

    fn size(&self) -> PyResult<usize> {
        let tasks = self.tasks.read()
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                format!("Lock error: {}", e)
            ))?;

        Ok(tasks.len())
    }
}
```

---

## 2. Flask Integration

### 2.1 Request Processing

```rust
#[pyfunction]
fn process_flask_request(py: Python, request: &PyAny) -> PyResult<PyObject> {
    // Extract request data
    let method: String = request.getattr("method")?.extract()?;
    let path: String = request.getattr("path")?.extract()?;
    let headers = request.getattr("headers")?;

    // Process request
    let result = PyDict::new(py);
    result.set_item("method", method)?;
    result.set_item("path", path)?;
    result.set_item("processed", true)?;

    Ok(result.into())
}

#[pyfunction]
fn parse_form_data(form_data: HashMap<String, String>) -> PyResult<HashMap<String, String>> {
    let mut processed = HashMap::new();

    for (key, value) in form_data {
        // Sanitize and validate
        let cleaned_value = value.trim().to_string();
        if !cleaned_value.is_empty() {
            processed.insert(key, cleaned_value);
        }
    }

    Ok(processed)
}
```

### 2.2 Blueprint Integration

```rust
#[pyclass]
struct RouteHandler {
    routes: Arc<RwLock<HashMap<String, PyObject>>>,
}

#[pymethods]
impl RouteHandler {
    #[new]
    fn new() -> Self {
        RouteHandler {
            routes: Arc::new(RwLock::new(HashMap::new())),
        }
    }

    fn register_route(&self, py: Python, path: String, handler: PyObject) -> PyResult<()> {
        let mut routes = self.routes.write()
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                format!("Lock error: {}", e)
            ))?;

        routes.insert(path, handler);
        Ok(())
    }

    fn get_handler(&self, py: Python, path: String) -> PyResult<Option<PyObject>> {
        let routes = self.routes.read()
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                format!("Lock error: {}", e)
            ))?;

        Ok(routes.get(&path).cloned())
    }

    fn list_routes(&self) -> PyResult<Vec<String>> {
        let routes = self.routes.read()
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                format!("Lock error: {}", e)
            ))?;

        Ok(routes.keys().cloned().collect())
    }
}
```

### 2.3 Middleware Implementation

```rust
#[pyclass]
struct MiddlewareChain {
    middlewares: Vec<PyObject>,
}

#[pymethods]
impl MiddlewareChain {
    #[new]
    fn new() -> Self {
        MiddlewareChain {
            middlewares: Vec::new(),
        }
    }

    fn add_middleware(&mut self, middleware: PyObject) {
        self.middlewares.push(middleware);
    }

    fn process_request(&self, py: Python, request: &PyAny) -> PyResult<PyObject> {
        let mut current = request.into();

        for middleware in &self.middlewares {
            current = middleware.call1(py, (current,))?;
        }

        Ok(current)
    }

    fn len(&self) -> usize {
        self.middlewares.len()
    }
}

#[pyfunction]
fn timing_middleware(py: Python, request: &PyAny, next: PyObject) -> PyResult<PyObject> {
    use std::time::Instant;

    let start = Instant::now();

    // Call next middleware/handler
    let response = next.call1(py, (request,))?;

    let duration = start.elapsed();
    println!("Request processed in {:?}", duration);

    Ok(response)
}
```

### 2.4 Session Management

```rust
use std::time::{SystemTime, UNIX_EPOCH};

#[pyclass]
struct Session {
    #[pyo3(get)]
    id: String,
    data: Arc<RwLock<HashMap<String, String>>>,
    created_at: u64,
}

#[pymethods]
impl Session {
    #[new]
    fn new(id: String) -> Self {
        let now = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_secs();

        Session {
            id,
            data: Arc::new(RwLock::new(HashMap::new())),
            created_at: now,
        }
    }

    fn set(&self, key: String, value: String) -> PyResult<()> {
        let mut data = self.data.write()
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                format!("Lock error: {}", e)
            ))?;

        data.insert(key, value);
        Ok(())
    }

    fn get(&self, key: String) -> PyResult<Option<String>> {
        let data = self.data.read()
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                format!("Lock error: {}", e)
            ))?;

        Ok(data.get(&key).cloned())
    }

    fn delete(&self, key: String) -> PyResult<bool> {
        let mut data = self.data.write()
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                format!("Lock error: {}", e)
            ))?;

        Ok(data.remove(&key).is_some())
    }

    fn clear(&self) -> PyResult<()> {
        let mut data = self.data.write()
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                format!("Lock error: {}", e)
            ))?;

        data.clear();
        Ok(())
    }

    fn age(&self) -> u64 {
        let now = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_secs();

        now - self.created_at
    }
}
```

---

## 3. Django Integration

### 3.1 Model Processing

```rust
#[pyfunction]
fn process_django_queryset(py: Python, queryset: &PyAny) -> PyResult<Vec<HashMap<String, String>>> {
    // Convert QuerySet to list
    let items: Vec<&PyAny> = queryset.call_method0("all")?.extract()?;

    let mut results = Vec::new();

    for item in items {
        let mut record = HashMap::new();

        // Extract fields
        if let Ok(id) = item.getattr("id") {
            record.insert("id".to_string(), id.to_string());
        }

        if let Ok(name) = item.getattr("name") {
            let name_str: String = name.extract()?;
            record.insert("name".to_string(), name_str);
        }

        results.push(record);
    }

    Ok(results)
}

#[pyfunction]
fn bulk_process_models(py: Python, models: Vec<&PyAny>) -> PyResult<usize> {
    let mut count = 0;

    for model in models {
        // Process each model
        if let Ok(mut_model) = model.call_method0("save") {
            count += 1;
        }
    }

    Ok(count)
}
```

### 3.2 QuerySet Optimization

```rust
#[pyclass]
struct QueryOptimizer {
    cache: Arc<RwLock<HashMap<String, Vec<String>>>>,
}

#[pymethods]
impl QueryOptimizer {
    #[new]
    fn new() -> Self {
        QueryOptimizer {
            cache: Arc::new(RwLock::new(HashMap::new())),
        }
    }

    fn optimize_query(&self, query: String) -> PyResult<String> {
        // Analyze query and suggest optimizations
        let optimized = if query.contains("SELECT *") {
            query.replace("SELECT *", "SELECT id, name, created_at")
        } else {
            query
        };

        Ok(optimized)
    }

    fn cache_query_result(&self, query: String, results: Vec<String>) -> PyResult<()> {
        let mut cache = self.cache.write()
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                format!("Lock error: {}", e)
            ))?;

        cache.insert(query, results);
        Ok(())
    }

    fn get_cached_result(&self, query: String) -> PyResult<Option<Vec<String>>> {
        let cache = self.cache.read()
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                format!("Lock error: {}", e)
            ))?;

        Ok(cache.get(&query).cloned())
    }

    fn clear_cache(&self) -> PyResult<()> {
        let mut cache = self.cache.write()
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                format!("Lock error: {}", e)
            ))?;

        cache.clear();
        Ok(())
    }
}
```

### 3.3 Middleware Integration

```rust
#[pyfunction]
fn django_middleware_process_request(py: Python, request: &PyAny) -> PyResult<Option<PyObject>> {
    // Extract request metadata
    let method: String = request.getattr("method")?.extract()?;
    let path: String = request.getattr("path")?.extract()?;

    // Validate request
    if method == "POST" && path.contains("/admin/") {
        // Check CSRF token
        let meta = request.getattr("META")?;
        if let Ok(token) = meta.get_item("HTTP_X_CSRFTOKEN") {
            // Token exists, continue
            Ok(None)
        } else {
            // Return error response
            let response = PyDict::new(py);
            response.set_item("error", "CSRF token missing")?;
            response.set_item("status", 403)?;
            Ok(Some(response.into()))
        }
    } else {
        Ok(None)
    }
}
```

### 3.4 Signal Handlers

```rust
use std::sync::Mutex;

#[pyclass]
struct SignalDispatcher {
    handlers: Arc<Mutex<HashMap<String, Vec<PyObject>>>>,
}

#[pymethods]
impl SignalDispatcher {
    #[new]
    fn new() -> Self {
        SignalDispatcher {
            handlers: Arc::new(Mutex::new(HashMap::new())),
        }
    }

    fn register_handler(&self, signal: String, handler: PyObject) -> PyResult<()> {
        let mut handlers = self.handlers.lock()
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                format!("Lock error: {}", e)
            ))?;

        handlers.entry(signal).or_insert_with(Vec::new).push(handler);
        Ok(())
    }

    fn emit_signal(&self, py: Python, signal: String, args: &PyAny) -> PyResult<()> {
        let handlers = self.handlers.lock()
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                format!("Lock error: {}", e)
            ))?;

        if let Some(signal_handlers) = handlers.get(&signal) {
            for handler in signal_handlers {
                handler.call1(py, (args,))?;
            }
        }

        Ok(())
    }

    fn clear_handlers(&self, signal: String) -> PyResult<()> {
        let mut handlers = self.handlers.lock()
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                format!("Lock error: {}", e)
            ))?;

        handlers.remove(&signal);
        Ok(())
    }
}
```

---

## 4. WebSocket Handling

### 4.1 Connection Management

```rust
use std::sync::Arc;
use std::collections::HashMap;

#[pyclass]
struct WebSocketConnection {
    #[pyo3(get)]
    id: String,
    connected: Arc<RwLock<bool>>,
}

#[pymethods]
impl WebSocketConnection {
    #[new]
    fn new(id: String) -> Self {
        WebSocketConnection {
            id,
            connected: Arc::new(RwLock::new(true)),
        }
    }

    fn send(&self, py: Python, message: String) -> PyResult<()> {
        let connected = self.connected.read()
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                format!("Lock error: {}", e)
            ))?;

        if *connected {
            println!("Sending to {}: {}", self.id, message);
            Ok(())
        } else {
            Err(PyErr::new::<pyo3::exceptions::PyConnectionError, _>(
                "Connection closed"
            ))
        }
    }

    fn close(&self) -> PyResult<()> {
        let mut connected = self.connected.write()
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                format!("Lock error: {}", e)
            ))?;

        *connected = false;
        Ok(())
    }

    fn is_connected(&self) -> PyResult<bool> {
        let connected = self.connected.read()
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                format!("Lock error: {}", e)
            ))?;

        Ok(*connected)
    }
}
```

### 4.2 Broadcasting

```rust
#[pyclass]
struct WebSocketBroadcaster {
    connections: Arc<RwLock<HashMap<String, WebSocketConnection>>>,
}

#[pymethods]
impl WebSocketBroadcaster {
    #[new]
    fn new() -> Self {
        WebSocketBroadcaster {
            connections: Arc::new(RwLock::new(HashMap::new())),
        }
    }

    fn add_connection(&self, connection: WebSocketConnection) -> PyResult<()> {
        let mut connections = self.connections.write()
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                format!("Lock error: {}", e)
            ))?;

        connections.insert(connection.id.clone(), connection);
        Ok(())
    }

    fn remove_connection(&self, id: String) -> PyResult<bool> {
        let mut connections = self.connections.write()
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                format!("Lock error: {}", e)
            ))?;

        Ok(connections.remove(&id).is_some())
    }

    fn broadcast(&self, py: Python, message: String) -> PyResult<usize> {
        let connections = self.connections.read()
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                format!("Lock error: {}", e)
            ))?;

        let mut count = 0;

        for (id, conn) in connections.iter() {
            if conn.send(py, message.clone()).is_ok() {
                count += 1;
            }
        }

        Ok(count)
    }

    fn broadcast_to_subset(&self, py: Python, message: String, ids: Vec<String>) -> PyResult<usize> {
        let connections = self.connections.read()
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                format!("Lock error: {}", e)
            ))?;

        let mut count = 0;

        for id in ids {
            if let Some(conn) = connections.get(&id) {
                if conn.send(py, message.clone()).is_ok() {
                    count += 1;
                }
            }
        }

        Ok(count)
    }

    fn connection_count(&self) -> PyResult<usize> {
        let connections = self.connections.read()
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                format!("Lock error: {}", e)
            ))?;

        Ok(connections.len())
    }
}
```

### 4.3 Message Processing

```rust
#[derive(Serialize, Deserialize)]
struct WebSocketMessage {
    msg_type: String,
    payload: serde_json::Value,
    timestamp: u64,
}

#[pyfunction]
fn parse_websocket_message(data: String) -> PyResult<(String, String)> {
    let msg: WebSocketMessage = serde_json::from_str(&data)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))?;

    let payload_str = serde_json::to_string(&msg.payload)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;

    Ok((msg.msg_type, payload_str))
}

#[pyfunction]
fn create_websocket_message(msg_type: String, payload: String) -> PyResult<String> {
    use std::time::{SystemTime, UNIX_EPOCH};

    let timestamp = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_secs();

    let payload_value: serde_json::Value = serde_json::from_str(&payload)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))?;

    let msg = WebSocketMessage {
        msg_type,
        payload: payload_value,
        timestamp,
    };

    serde_json::to_string(&msg)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))
}
```

---

## 5. HTTP Processing

### 5.1 Header Parsing

```rust
#[pyfunction]
fn parse_headers(header_string: String) -> PyResult<HashMap<String, String>> {
    let mut headers = HashMap::new();

    for line in header_string.lines() {
        if let Some((key, value)) = line.split_once(':') {
            headers.insert(
                key.trim().to_lowercase(),
                value.trim().to_string()
            );
        }
    }

    Ok(headers)
}

#[pyfunction]
fn extract_content_type(headers: HashMap<String, String>) -> Option<String> {
    headers.get("content-type").cloned()
}

#[pyfunction]
fn validate_headers(headers: HashMap<String, String>, required: Vec<String>) -> PyResult<bool> {
    for req_header in required {
        if !headers.contains_key(&req_header.to_lowercase()) {
            return Ok(false);
        }
    }

    Ok(true)
}
```

### 5.2 URL Processing

```rust
use std::collections::HashMap;

#[pyfunction]
fn parse_query_string(query: String) -> HashMap<String, String> {
    let mut params = HashMap::new();

    for pair in query.split('&') {
        if let Some((key, value)) = pair.split_once('=') {
            params.insert(
                key.to_string(),
                urlencoding::decode(value).unwrap_or_default().to_string()
            );
        }
    }

    params
}

#[pyfunction]
fn build_query_string(params: HashMap<String, String>) -> String {
    params.iter()
        .map(|(k, v)| format!("{}={}", k, urlencoding::encode(v)))
        .collect::<Vec<_>>()
        .join("&")
}

#[pyfunction]
fn extract_path_params(pattern: String, path: String) -> PyResult<HashMap<String, String>> {
    let pattern_parts: Vec<&str> = pattern.split('/').collect();
    let path_parts: Vec<&str> = path.split('/').collect();

    if pattern_parts.len() != path_parts.len() {
        return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
            "Path does not match pattern"
        ));
    }

    let mut params = HashMap::new();

    for (pattern_part, path_part) in pattern_parts.iter().zip(path_parts.iter()) {
        if pattern_part.starts_with(':') {
            let param_name = &pattern_part[1..];
            params.insert(param_name.to_string(), path_part.to_string());
        } else if pattern_part != path_part {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                "Path does not match pattern"
            ));
        }
    }

    Ok(params)
}
```

### 5.3 Request Body Processing

```rust
#[pyfunction]
fn parse_json_body(body: String) -> PyResult<HashMap<String, serde_json::Value>> {
    let parsed: HashMap<String, serde_json::Value> = serde_json::from_str(&body)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))?;

    Ok(parsed)
}

#[pyfunction]
fn parse_multipart_form(boundary: String, body: Vec<u8>) -> PyResult<HashMap<String, Vec<u8>>> {
    let mut parts = HashMap::new();
    let boundary_bytes = format!("--{}", boundary).into_bytes();

    // Simple multipart parsing (production use: multipart crate)
    let body_str = String::from_utf8_lossy(&body);
    for part in body_str.split(&format!("--{}", boundary)) {
        if let Some((headers, content)) = part.split_once("\r\n\r\n") {
            if let Some(name) = extract_field_name(headers) {
                parts.insert(name, content.trim().as_bytes().to_vec());
            }
        }
    }

    Ok(parts)
}

fn extract_field_name(headers: &str) -> Option<String> {
    for line in headers.lines() {
        if line.to_lowercase().starts_with("content-disposition:") {
            if let Some(name_part) = line.split("name=\"").nth(1) {
                if let Some(name) = name_part.split('"').next() {
                    return Some(name.to_string());
                }
            }
        }
    }
    None
}
```

### 5.4 Streaming Support

```rust
#[pyclass]
struct StreamProcessor {
    buffer: Arc<RwLock<Vec<u8>>>,
    chunk_size: usize,
}

#[pymethods]
impl StreamProcessor {
    #[new]
    fn new(chunk_size: usize) -> Self {
        StreamProcessor {
            buffer: Arc::new(RwLock::new(Vec::new())),
            chunk_size,
        }
    }

    fn write_chunk(&self, data: Vec<u8>) -> PyResult<()> {
        let mut buffer = self.buffer.write()
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                format!("Lock error: {}", e)
            ))?;

        buffer.extend_from_slice(&data);
        Ok(())
    }

    fn read_chunk(&self) -> PyResult<Option<Vec<u8>>> {
        let mut buffer = self.buffer.write()
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                format!("Lock error: {}", e)
            ))?;

        if buffer.len() >= self.chunk_size {
            let chunk = buffer.drain(..self.chunk_size).collect();
            Ok(Some(chunk))
        } else {
            Ok(None)
        }
    }

    fn flush(&self) -> PyResult<Vec<u8>> {
        let mut buffer = self.buffer.write()
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                format!("Lock error: {}", e)
            ))?;

        Ok(buffer.drain(..).collect())
    }

    fn buffer_size(&self) -> PyResult<usize> {
        let buffer = self.buffer.read()
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                format!("Lock error: {}", e)
            ))?;

        Ok(buffer.len())
    }
}
```

---

## 6. Response Generation

### 6.1 JSON Responses

```rust
#[pyfunction]
fn create_json_response(py: Python, data: HashMap<String, String>, status: u16) -> PyResult<PyObject> {
    let response = PyDict::new(py);

    // Serialize data
    let json_str = serde_json::to_string(&data)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;

    response.set_item("body", json_str)?;
    response.set_item("status", status)?;
    response.set_item("content_type", "application/json")?;

    Ok(response.into())
}

#[pyfunction]
fn create_error_response(py: Python, message: String, status: u16) -> PyResult<PyObject> {
    let error_data = serde_json::json!({
        "error": message,
        "status": status
    });

    let json_str = serde_json::to_string(&error_data)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;

    let response = PyDict::new(py);
    response.set_item("body", json_str)?;
    response.set_item("status", status)?;
    response.set_item("content_type", "application/json")?;

    Ok(response.into())
}
```

### 6.2 Template Processing

```rust
#[pyfunction]
fn render_template(template: String, context: HashMap<String, String>) -> PyResult<String> {
    let mut result = template;

    for (key, value) in context {
        let placeholder = format!("{{{{{}}}}}", key);
        result = result.replace(&placeholder, &value);
    }

    Ok(result)
}

#[pyfunction]
fn render_template_with_escaping(template: String, context: HashMap<String, String>) -> PyResult<String> {
    let mut result = template;

    for (key, value) in context {
        let escaped_value = html_escape(&value);
        let placeholder = format!("{{{{{}}}}}", key);
        result = result.replace(&placeholder, &escaped_value);
    }

    Ok(result)
}

fn html_escape(s: &str) -> String {
    s.replace('&', "&amp;")
        .replace('<', "&lt;")
        .replace('>', "&gt;")
        .replace('"', "&quot;")
        .replace('\'', "&#x27;")
}
```

### 6.3 Streaming Responses

```rust
#[pyclass]
struct StreamingResponse {
    chunks: Arc<RwLock<Vec<Vec<u8>>>>,
    position: Arc<RwLock<usize>>,
}

#[pymethods]
impl StreamingResponse {
    #[new]
    fn new(chunks: Vec<Vec<u8>>) -> Self {
        StreamingResponse {
            chunks: Arc::new(RwLock::new(chunks)),
            position: Arc::new(RwLock::new(0)),
        }
    }

    fn next_chunk(&self) -> PyResult<Option<Vec<u8>>> {
        let chunks = self.chunks.read()
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                format!("Lock error: {}", e)
            ))?;

        let mut position = self.position.write()
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                format!("Lock error: {}", e)
            ))?;

        if *position < chunks.len() {
            let chunk = chunks[*position].clone();
            *position += 1;
            Ok(Some(chunk))
        } else {
            Ok(None)
        }
    }

    fn reset(&self) -> PyResult<()> {
        let mut position = self.position.write()
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                format!("Lock error: {}", e)
            ))?;

        *position = 0;
        Ok(())
    }

    fn remaining(&self) -> PyResult<usize> {
        let chunks = self.chunks.read()
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                format!("Lock error: {}", e)
            ))?;

        let position = self.position.read()
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                format!("Lock error: {}", e)
            ))?;

        Ok(chunks.len() - *position)
    }
}
```

### 6.4 Response Caching

```rust
use std::time::{SystemTime, Duration};

#[pyclass]
struct ResponseCache {
    cache: Arc<RwLock<HashMap<String, (String, SystemTime)>>>,
    ttl: Duration,
}

#[pymethods]
impl ResponseCache {
    #[new]
    fn new(ttl_seconds: u64) -> Self {
        ResponseCache {
            cache: Arc::new(RwLock::new(HashMap::new())),
            ttl: Duration::from_secs(ttl_seconds),
        }
    }

    fn get(&self, key: String) -> PyResult<Option<String>> {
        let cache = self.cache.read()
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                format!("Lock error: {}", e)
            ))?;

        if let Some((value, timestamp)) = cache.get(&key) {
            if timestamp.elapsed().unwrap() < self.ttl {
                return Ok(Some(value.clone()));
            }
        }

        Ok(None)
    }

    fn set(&self, key: String, value: String) -> PyResult<()> {
        let mut cache = self.cache.write()
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                format!("Lock error: {}", e)
            ))?;

        cache.insert(key, (value, SystemTime::now()));
        Ok(())
    }

    fn invalidate(&self, key: String) -> PyResult<bool> {
        let mut cache = self.cache.write()
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                format!("Lock error: {}", e)
            ))?;

        Ok(cache.remove(&key).is_some())
    }

    fn clear(&self) -> PyResult<()> {
        let mut cache = self.cache.write()
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                format!("Lock error: {}", e)
            ))?;

        cache.clear();
        Ok(())
    }

    fn cleanup_expired(&self) -> PyResult<usize> {
        let mut cache = self.cache.write()
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                format!("Lock error: {}", e)
            ))?;

        let expired_keys: Vec<String> = cache.iter()
            .filter(|(_, (_, timestamp))| timestamp.elapsed().unwrap() >= self.ttl)
            .map(|(k, _)| k.clone())
            .collect();

        let count = expired_keys.len();

        for key in expired_keys {
            cache.remove(&key);
        }

        Ok(count)
    }
}
```

---

## 7. Authentication

### 7.1 JWT Handling

```rust
use hmac::{Hmac, Mac};
use sha2::Sha256;

type HmacSha256 = Hmac<Sha256>;

#[pyfunction]
fn create_jwt_signature(header: String, payload: String, secret: String) -> PyResult<String> {
    let message = format!("{}.{}", header, payload);

    let mut mac = HmacSha256::new_from_slice(secret.as_bytes())
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;

    mac.update(message.as_bytes());

    let result = mac.finalize();
    let signature = base64::encode(result.into_bytes());

    Ok(signature)
}

#[pyfunction]
fn verify_jwt_signature(token: String, secret: String) -> PyResult<bool> {
    let parts: Vec<&str> = token.split('.').collect();

    if parts.len() != 3 {
        return Ok(false);
    }

    let message = format!("{}.{}", parts[0], parts[1]);
    let provided_signature = parts[2];

    let mut mac = HmacSha256::new_from_slice(secret.as_bytes())
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;

    mac.update(message.as_bytes());

    let expected_signature = base64::encode(mac.finalize().into_bytes());

    Ok(expected_signature == provided_signature)
}

#[pyfunction]
fn decode_jwt_payload(token: String) -> PyResult<String> {
    let parts: Vec<&str> = token.split('.').collect();

    if parts.len() != 3 {
        return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
            "Invalid JWT format"
        ));
    }

    let payload_bytes = base64::decode(parts[1])
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))?;

    String::from_utf8(payload_bytes)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))
}
```

### 7.2 Password Hashing

```rust
use argon2::{
    password_hash::{rand_core::OsRng, PasswordHash, PasswordHasher, PasswordVerifier, SaltString},
    Argon2,
};

#[pyfunction]
fn hash_password(password: String) -> PyResult<String> {
    let salt = SaltString::generate(&mut OsRng);
    let argon2 = Argon2::default();

    let password_hash = argon2.hash_password(password.as_bytes(), &salt)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;

    Ok(password_hash.to_string())
}

#[pyfunction]
fn verify_password(password: String, hash: String) -> PyResult<bool> {
    let parsed_hash = PasswordHash::new(&hash)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))?;

    let argon2 = Argon2::default();

    Ok(argon2.verify_password(password.as_bytes(), &parsed_hash).is_ok())
}
```

### 7.3 OAuth2 Flow

```rust
#[pyclass]
struct OAuth2Handler {
    client_id: String,
    client_secret: String,
    redirect_uri: String,
}

#[pymethods]
impl OAuth2Handler {
    #[new]
    fn new(client_id: String, client_secret: String, redirect_uri: String) -> Self {
        OAuth2Handler {
            client_id,
            client_secret,
            redirect_uri,
        }
    }

    fn generate_auth_url(&self, state: String, scope: Vec<String>) -> String {
        format!(
            "https://oauth.example.com/authorize?client_id={}&redirect_uri={}&state={}&scope={}",
            self.client_id,
            urlencoding::encode(&self.redirect_uri),
            state,
            scope.join("+")
        )
    }

    fn exchange_code(&self, code: String) -> PyResult<String> {
        // Simulate token exchange
        let token_request = serde_json::json!({
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "redirect_uri": self.redirect_uri,
            "grant_type": "authorization_code"
        });

        serde_json::to_string(&token_request)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))
    }

    fn validate_state(&self, received_state: String, expected_state: String) -> bool {
        received_state == expected_state
    }
}
```

### 7.4 Rate Limiting

```rust
use std::time::{SystemTime, Duration};

#[pyclass]
struct RateLimiter {
    requests: Arc<RwLock<HashMap<String, Vec<SystemTime>>>>,
    max_requests: usize,
    window: Duration,
}

#[pymethods]
impl RateLimiter {
    #[new]
    fn new(max_requests: usize, window_seconds: u64) -> Self {
        RateLimiter {
            requests: Arc::new(RwLock::new(HashMap::new())),
            max_requests,
            window: Duration::from_secs(window_seconds),
        }
    }

    fn check_rate_limit(&self, identifier: String) -> PyResult<bool> {
        let mut requests = self.requests.write()
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                format!("Lock error: {}", e)
            ))?;

        let now = SystemTime::now();
        let cutoff = now - self.window;

        // Clean up old requests
        let user_requests = requests.entry(identifier).or_insert_with(Vec::new);
        user_requests.retain(|&t| t > cutoff);

        // Check limit
        if user_requests.len() < self.max_requests {
            user_requests.push(now);
            Ok(true)
        } else {
            Ok(false)
        }
    }

    fn get_remaining(&self, identifier: String) -> PyResult<usize> {
        let requests = self.requests.read()
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                format!("Lock error: {}", e)
            ))?;

        let now = SystemTime::now();
        let cutoff = now - self.window;

        if let Some(user_requests) = requests.get(&identifier) {
            let active_requests = user_requests.iter().filter(|&&t| t > cutoff).count();
            Ok(self.max_requests.saturating_sub(active_requests))
        } else {
            Ok(self.max_requests)
        }
    }

    fn reset(&self, identifier: String) -> PyResult<()> {
        let mut requests = self.requests.write()
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                format!("Lock error: {}", e)
            ))?;

        requests.remove(&identifier);
        Ok(())
    }
}
```

---

## 8. Caching & Performance

### 8.1 Memory Caching

```rust
#[pyclass]
struct MemoryCache {
    cache: Arc<RwLock<HashMap<String, (Vec<u8>, SystemTime)>>>,
    max_size: usize,
    ttl: Duration,
}

#[pymethods]
impl MemoryCache {
    #[new]
    fn new(max_size: usize, ttl_seconds: u64) -> Self {
        MemoryCache {
            cache: Arc::new(RwLock::new(HashMap::new())),
            max_size,
            ttl: Duration::from_secs(ttl_seconds),
        }
    }

    fn get(&self, key: String) -> PyResult<Option<Vec<u8>>> {
        let cache = self.cache.read()
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                format!("Lock error: {}", e)
            ))?;

        if let Some((value, timestamp)) = cache.get(&key) {
            if timestamp.elapsed().unwrap() < self.ttl {
                return Ok(Some(value.clone()));
            }
        }

        Ok(None)
    }

    fn set(&self, key: String, value: Vec<u8>) -> PyResult<()> {
        let mut cache = self.cache.write()
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                format!("Lock error: {}", e)
            ))?;

        // Evict if at capacity
        if cache.len() >= self.max_size && !cache.contains_key(&key) {
            if let Some(oldest_key) = cache.keys().next().cloned() {
                cache.remove(&oldest_key);
            }
        }

        cache.insert(key, (value, SystemTime::now()));
        Ok(())
    }

    fn delete(&self, key: String) -> PyResult<bool> {
        let mut cache = self.cache.write()
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                format!("Lock error: {}", e)
            ))?;

        Ok(cache.remove(&key).is_some())
    }

    fn clear(&self) -> PyResult<()> {
        let mut cache = self.cache.write()
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                format!("Lock error: {}", e)
            ))?;

        cache.clear();
        Ok(())
    }

    fn size(&self) -> PyResult<usize> {
        let cache = self.cache.read()
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                format!("Lock error: {}", e)
            ))?;

        Ok(cache.len())
    }
}
```

### 8.2 Query Result Caching

```rust
#[pyclass]
struct QueryCache {
    cache: Arc<RwLock<HashMap<String, (String, SystemTime, u64)>>>,
    ttl: Duration,
    hit_count: Arc<RwLock<u64>>,
    miss_count: Arc<RwLock<u64>>,
}

#[pymethods]
impl QueryCache {
    #[new]
    fn new(ttl_seconds: u64) -> Self {
        QueryCache {
            cache: Arc::new(RwLock::new(HashMap::new())),
            ttl: Duration::from_secs(ttl_seconds),
            hit_count: Arc::new(RwLock::new(0)),
            miss_count: Arc::new(RwLock::new(0)),
        }
    }

    fn get(&self, query: String) -> PyResult<Option<String>> {
        let cache = self.cache.read()
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                format!("Lock error: {}", e)
            ))?;

        if let Some((result, timestamp, _)) = cache.get(&query) {
            if timestamp.elapsed().unwrap() < self.ttl {
                let mut hits = self.hit_count.write().unwrap();
                *hits += 1;
                return Ok(Some(result.clone()));
            }
        }

        let mut misses = self.miss_count.write().unwrap();
        *misses += 1;
        Ok(None)
    }

    fn set(&self, query: String, result: String) -> PyResult<()> {
        let mut cache = self.cache.write()
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                format!("Lock error: {}", e)
            ))?;

        cache.insert(query, (result, SystemTime::now(), 0));
        Ok(())
    }

    fn stats(&self) -> PyResult<(u64, u64, f64)> {
        let hits = *self.hit_count.read().unwrap();
        let misses = *self.miss_count.read().unwrap();
        let total = hits + misses;

        let hit_rate = if total > 0 {
            hits as f64 / total as f64
        } else {
            0.0
        };

        Ok((hits, misses, hit_rate))
    }

    fn clear_stats(&self) -> PyResult<()> {
        *self.hit_count.write().unwrap() = 0;
        *self.miss_count.write().unwrap() = 0;
        Ok(())
    }
}
```

### 8.3 Connection Pooling

```rust
use std::collections::VecDeque;

#[pyclass]
struct ConnectionPool {
    available: Arc<RwLock<VecDeque<String>>>,
    max_size: usize,
    current_size: Arc<RwLock<usize>>,
}

#[pymethods]
impl ConnectionPool {
    #[new]
    fn new(max_size: usize) -> Self {
        ConnectionPool {
            available: Arc::new(RwLock::new(VecDeque::new())),
            max_size,
            current_size: Arc::new(RwLock::new(0)),
        }
    }

    fn acquire(&self) -> PyResult<Option<String>> {
        let mut available = self.available.write()
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                format!("Lock error: {}", e)
            ))?;

        // Return existing connection if available
        if let Some(conn) = available.pop_front() {
            return Ok(Some(conn));
        }

        // Create new connection if under limit
        let mut current_size = self.current_size.write()
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                format!("Lock error: {}", e)
            ))?;

        if *current_size < self.max_size {
            *current_size += 1;
            let conn_id = format!("conn_{}", *current_size);
            Ok(Some(conn_id))
        } else {
            Ok(None)
        }
    }

    fn release(&self, connection: String) -> PyResult<()> {
        let mut available = self.available.write()
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                format!("Lock error: {}", e)
            ))?;

        available.push_back(connection);
        Ok(())
    }

    fn stats(&self) -> PyResult<(usize, usize)> {
        let available = self.available.read()
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                format!("Lock error: {}", e)
            ))?;

        let current_size = *self.current_size.read()
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                format!("Lock error: {}", e)
            ))?;

        Ok((available.len(), current_size))
    }
}
```

---

## 9. API Development

### 9.1 REST Patterns

```rust
#[pyclass]
struct RESTResource {
    #[pyo3(get)]
    id: Option<u64>,
    #[pyo3(get, set)]
    name: String,
    #[pyo3(get, set)]
    data: HashMap<String, String>,
}

#[pymethods]
impl RESTResource {
    #[new]
    fn new(name: String) -> Self {
        RESTResource {
            id: None,
            name,
            data: HashMap::new(),
        }
    }

    fn to_json(&self) -> PyResult<String> {
        let json_data = serde_json::json!({
            "id": self.id,
            "name": self.name,
            "data": self.data,
        });

        serde_json::to_string(&json_data)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))
    }

    #[staticmethod]
    fn from_json(json_str: String) -> PyResult<Self> {
        let value: serde_json::Value = serde_json::from_str(&json_str)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))?;

        let id = value.get("id").and_then(|v| v.as_u64());
        let name = value.get("name")
            .and_then(|v| v.as_str())
            .unwrap_or("").to_string();

        let data = if let Some(data_obj) = value.get("data").and_then(|v| v.as_object()) {
            data_obj.iter()
                .map(|(k, v)| (k.clone(), v.as_str().unwrap_or("").to_string()))
                .collect()
        } else {
            HashMap::new()
        };

        Ok(RESTResource { id, name, data })
    }

    fn validate(&self) -> PyResult<Vec<String>> {
        let mut errors = Vec::new();

        if self.name.is_empty() {
            errors.push("Name cannot be empty".to_string());
        }

        if self.name.len() > 100 {
            errors.push("Name too long (max 100 characters)".to_string());
        }

        Ok(errors)
    }
}
```

### 9.2 Pagination

```rust
#[pyclass]
struct Paginator {
    #[pyo3(get)]
    page: usize,
    #[pyo3(get)]
    page_size: usize,
    #[pyo3(get)]
    total_items: usize,
}

#[pymethods]
impl Paginator {
    #[new]
    fn new(page: usize, page_size: usize, total_items: usize) -> Self {
        Paginator {
            page: page.max(1),
            page_size: page_size.max(1),
            total_items,
        }
    }

    fn total_pages(&self) -> usize {
        (self.total_items + self.page_size - 1) / self.page_size
    }

    fn has_next(&self) -> bool {
        self.page < self.total_pages()
    }

    fn has_prev(&self) -> bool {
        self.page > 1
    }

    fn offset(&self) -> usize {
        (self.page - 1) * self.page_size
    }

    fn limit(&self) -> usize {
        self.page_size
    }

    fn to_dict(&self, py: Python) -> PyResult<PyObject> {
        let dict = PyDict::new(py);
        dict.set_item("page", self.page)?;
        dict.set_item("page_size", self.page_size)?;
        dict.set_item("total_items", self.total_items)?;
        dict.set_item("total_pages", self.total_pages())?;
        dict.set_item("has_next", self.has_next())?;
        dict.set_item("has_prev", self.has_prev())?;
        Ok(dict.into())
    }
}

#[pyfunction]
fn paginate_results(items: Vec<String>, page: usize, page_size: usize) -> PyResult<(Vec<String>, Paginator)> {
    let total_items = items.len();
    let paginator = Paginator::new(page, page_size, total_items);

    let start = paginator.offset();
    let end = (start + paginator.limit()).min(total_items);

    let page_items = items[start..end].to_vec();

    Ok((page_items, paginator))
}
```

### 9.3 Filtering & Sorting

```rust
#[pyfunction]
fn filter_resources(
    resources: Vec<HashMap<String, String>>,
    filters: HashMap<String, String>
) -> Vec<HashMap<String, String>> {
    resources.into_iter()
        .filter(|resource| {
            filters.iter().all(|(key, value)| {
                resource.get(key).map(|v| v == value).unwrap_or(false)
            })
        })
        .collect()
}

#[pyfunction]
fn sort_resources(
    mut resources: Vec<HashMap<String, String>>,
    sort_key: String,
    descending: bool
) -> Vec<HashMap<String, String>> {
    resources.sort_by(|a, b| {
        let a_val = a.get(&sort_key).cloned().unwrap_or_default();
        let b_val = b.get(&sort_key).cloned().unwrap_or_default();

        if descending {
            b_val.cmp(&a_val)
        } else {
            a_val.cmp(&b_val)
        }
    });

    resources
}

#[pyclass]
struct QueryBuilder {
    filters: HashMap<String, String>,
    sort_by: Option<String>,
    descending: bool,
    page: usize,
    page_size: usize,
}

#[pymethods]
impl QueryBuilder {
    #[new]
    fn new() -> Self {
        QueryBuilder {
            filters: HashMap::new(),
            sort_by: None,
            descending: false,
            page: 1,
            page_size: 20,
        }
    }

    fn filter(&mut self, key: String, value: String) -> &mut Self {
        self.filters.insert(key, value);
        self
    }

    fn sort(&mut self, key: String, descending: bool) -> &mut Self {
        self.sort_by = Some(key);
        self.descending = descending;
        self
    }

    fn paginate(&mut self, page: usize, page_size: usize) -> &mut Self {
        self.page = page;
        self.page_size = page_size;
        self
    }

    fn to_sql(&self) -> String {
        let mut query = "SELECT * FROM resources".to_string();

        if !self.filters.is_empty() {
            let conditions: Vec<String> = self.filters.iter()
                .map(|(k, v)| format!("{} = '{}'", k, v))
                .collect();
            query.push_str(&format!(" WHERE {}", conditions.join(" AND ")));
        }

        if let Some(ref sort_key) = self.sort_by {
            query.push_str(&format!(" ORDER BY {}", sort_key));
            if self.descending {
                query.push_str(" DESC");
            }
        }

        let offset = (self.page - 1) * self.page_size;
        query.push_str(&format!(" LIMIT {} OFFSET {}", self.page_size, offset));

        query
    }
}
```

---

## 10. Production Deployment

### 10.1 ASGI Integration

```rust
#[pyfunction]
fn asgi_app(py: Python, scope: &PyAny, receive: PyObject, send: PyObject) -> PyResult<PyObject> {
    // Extract scope data
    let scope_type: String = scope.get_item("type")?.extract()?;
    let path: String = scope.get_item("path")?.extract()?;

    if scope_type == "http" {
        // Handle HTTP request
        let response_body = format!("Hello from Rust! Path: {}", path);

        // Send response start
        let start_dict = PyDict::new(py);
        start_dict.set_item("type", "http.response.start")?;
        start_dict.set_item("status", 200)?;

        let headers = vec![
            (b"content-type".to_vec(), b"text/plain".to_vec()),
        ];
        start_dict.set_item("headers", headers)?;

        send.call1(py, (start_dict,))?;

        // Send response body
        let body_dict = PyDict::new(py);
        body_dict.set_item("type", "http.response.body")?;
        body_dict.set_item("body", response_body.as_bytes())?;

        send.call1(py, (body_dict,))?;
    }

    Ok(py.None())
}
```

### 10.2 Health Checks

```rust
use std::time::{SystemTime, UNIX_EPOCH};

#[pyclass]
struct HealthChecker {
    #[pyo3(get)]
    started_at: u64,
    checks: Arc<RwLock<HashMap<String, bool>>>,
}

#[pymethods]
impl HealthChecker {
    #[new]
    fn new() -> Self {
        let started_at = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_secs();

        HealthChecker {
            started_at,
            checks: Arc::new(RwLock::new(HashMap::new())),
        }
    }

    fn register_check(&self, name: String, healthy: bool) -> PyResult<()> {
        let mut checks = self.checks.write()
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                format!("Lock error: {}", e)
            ))?;

        checks.insert(name, healthy);
        Ok(())
    }

    fn is_healthy(&self) -> PyResult<bool> {
        let checks = self.checks.read()
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                format!("Lock error: {}", e)
            ))?;

        Ok(checks.values().all(|&healthy| healthy))
    }

    fn get_status(&self, py: Python) -> PyResult<PyObject> {
        let checks = self.checks.read()
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                format!("Lock error: {}", e)
            ))?;

        let now = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_secs();

        let status = PyDict::new(py);
        status.set_item("healthy", checks.values().all(|&h| h))?;
        status.set_item("uptime", now - self.started_at)?;
        status.set_item("checks", checks.clone())?;

        Ok(status.into())
    }
}
```

### 10.3 Request Logging

```rust
use std::fs::OpenOptions;
use std::io::Write;

#[pyclass]
struct RequestLogger {
    log_path: String,
}

#[pymethods]
impl RequestLogger {
    #[new]
    fn new(log_path: String) -> Self {
        RequestLogger { log_path }
    }

    fn log_request(&self, method: String, path: String, status: u16, duration_ms: f64) -> PyResult<()> {
        use std::time::{SystemTime, UNIX_EPOCH};

        let timestamp = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_secs();

        let log_entry = format!(
            "[{}] {} {} - {} - {:.2}ms\n",
            timestamp, method, path, status, duration_ms
        );

        let mut file = OpenOptions::new()
            .create(true)
            .append(true)
            .open(&self.log_path)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;

        file.write_all(log_entry.as_bytes())
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;

        Ok(())
    }

    fn log_error(&self, method: String, path: String, error: String) -> PyResult<()> {
        use std::time::{SystemTime, UNIX_EPOCH};

        let timestamp = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_secs();

        let log_entry = format!(
            "[{}] ERROR {} {} - {}\n",
            timestamp, method, path, error
        );

        let mut file = OpenOptions::new()
            .create(true)
            .append(true)
            .open(&self.log_path)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;

        file.write_all(log_entry.as_bytes())
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;

        Ok(())
    }
}
```

### 10.4 Metrics Collection

```rust
#[pyclass]
struct MetricsCollector {
    request_count: Arc<RwLock<u64>>,
    error_count: Arc<RwLock<u64>>,
    response_times: Arc<RwLock<Vec<f64>>>,
}

#[pymethods]
impl MetricsCollector {
    #[new]
    fn new() -> Self {
        MetricsCollector {
            request_count: Arc::new(RwLock::new(0)),
            error_count: Arc::new(RwLock::new(0)),
            response_times: Arc::new(RwLock::new(Vec::new())),
        }
    }

    fn record_request(&self, duration_ms: f64) -> PyResult<()> {
        *self.request_count.write().unwrap() += 1;
        self.response_times.write().unwrap().push(duration_ms);
        Ok(())
    }

    fn record_error(&self) -> PyResult<()> {
        *self.error_count.write().unwrap() += 1;
        Ok(())
    }

    fn get_metrics(&self, py: Python) -> PyResult<PyObject> {
        let request_count = *self.request_count.read().unwrap();
        let error_count = *self.error_count.read().unwrap();
        let response_times = self.response_times.read().unwrap();

        let avg_response_time = if !response_times.is_empty() {
            response_times.iter().sum::<f64>() / response_times.len() as f64
        } else {
            0.0
        };

        let max_response_time = response_times.iter()
            .fold(0.0f64, |acc, &x| acc.max(x));

        let metrics = PyDict::new(py);
        metrics.set_item("request_count", request_count)?;
        metrics.set_item("error_count", error_count)?;
        metrics.set_item("error_rate", error_count as f64 / request_count as f64)?;
        metrics.set_item("avg_response_time", avg_response_time)?;
        metrics.set_item("max_response_time", max_response_time)?;

        Ok(metrics.into())
    }

    fn reset(&self) -> PyResult<()> {
        *self.request_count.write().unwrap() = 0;
        *self.error_count.write().unwrap() = 0;
        self.response_times.write().unwrap().clear();
        Ok(())
    }
}
```

---

## Summary

This reference covers:

1. **FastAPI**: Async handlers, Pydantic models, dependency injection, background tasks
2. **Flask**: Request processing, blueprints, middleware, sessions
3. **Django**: Model/QuerySet processing, optimization, signals
4. **WebSocket**: Connection management, broadcasting, message processing
5. **HTTP**: Header/URL parsing, body processing, streaming
6. **Responses**: JSON, templates, streaming, caching
7. **Authentication**: JWT, password hashing, OAuth2, rate limiting
8. **Caching**: Memory cache, query cache, connection pooling
9. **API Development**: REST patterns, pagination, filtering
10. **Production**: ASGI integration, health checks, logging, metrics

For more information, see:
- [PyO3 Documentation](https://pyo3.rs/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Flask Documentation](https://flask.palletsprojects.com/)
- [Django Documentation](https://docs.djangoproject.com/)
