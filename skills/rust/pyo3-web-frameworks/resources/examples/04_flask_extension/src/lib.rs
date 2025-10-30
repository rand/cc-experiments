//! Flask extension pattern with PyO3
//!
//! This example demonstrates:
//! - Creating Flask-compatible extensions
//! - Request/response processing in Rust
//! - Data compression and encoding
//! - Header manipulation
//! - Performance optimizations for Flask

use pyo3::prelude::*;
use pyo3::exceptions::PyValueError;
use flate2::write::GzEncoder;
use flate2::read::GzDecoder;
use flate2::Compression;
use std::io::{Write, Read};

/// Compress response data with gzip
#[pyfunction]
fn compress_response(data: Vec<u8>, level: Option<u32>) -> PyResult<Vec<u8>> {
    let compression_level = level.unwrap_or(6);
    if compression_level > 9 {
        return Err(PyValueError::new_err("Compression level must be 0-9"));
    }

    let mut encoder = GzEncoder::new(Vec::new(), Compression::new(compression_level));
    encoder.write_all(&data)
        .map_err(|e| PyValueError::new_err(format!("Compression failed: {}", e)))?;

    encoder.finish()
        .map_err(|e| PyValueError::new_err(format!("Finalize failed: {}", e)))
}

/// Decompress gzipped data
#[pyfunction]
fn decompress_request(data: Vec<u8>) -> PyResult<Vec<u8>> {
    let mut decoder = GzDecoder::new(&data[..]);
    let mut result = Vec::new();

    decoder.read_to_end(&mut result)
        .map_err(|e| PyValueError::new_err(format!("Decompression failed: {}", e)))?;

    Ok(result)
}

/// Parse query string to dict-like structure
#[pyfunction]
fn parse_query_string(query: String) -> PyResult<Vec<(String, String)>> {
    let mut result = Vec::new();

    for pair in query.split('&') {
        if pair.is_empty() {
            continue;
        }

        let parts: Vec<&str> = pair.splitn(2, '=').collect();
        if parts.len() == 2 {
            let key = urlencoding::decode(parts[0])
                .map_err(|e| PyValueError::new_err(format!("Invalid key: {}", e)))?;
            let value = urlencoding::decode(parts[1])
                .map_err(|e| PyValueError::new_err(format!("Invalid value: {}", e)))?;
            result.push((key.to_string(), value.to_string()));
        }
    }

    Ok(result)
}

/// Build query string from pairs
#[pyfunction]
fn build_query_string(params: Vec<(String, String)>) -> PyResult<String> {
    let encoded: Vec<String> = params.iter()
        .map(|(k, v)| format!("{}={}",
            urlencoding::encode(k),
            urlencoding::encode(v)))
        .collect();

    Ok(encoded.join("&"))
}

/// Hash request for caching
#[pyfunction]
fn hash_request(method: String, path: String, body: Vec<u8>) -> PyResult<String> {
    use sha2::{Sha256, Digest};

    let mut hasher = Sha256::new();
    hasher.update(method.as_bytes());
    hasher.update(path.as_bytes());
    hasher.update(&body);

    let result = hasher.finalize();
    Ok(format!("{:x}", result))
}

/// Rate limiter for Flask
#[pyclass]
struct RateLimiter {
    requests: std::sync::Arc<std::sync::RwLock<std::collections::HashMap<String, Vec<std::time::Instant>>>>,
    limit: usize,
    window: std::time::Duration,
}

#[pymethods]
impl RateLimiter {
    #[new]
    fn new(limit: usize, window_seconds: u64) -> Self {
        RateLimiter {
            requests: std::sync::Arc::new(std::sync::RwLock::new(std::collections::HashMap::new())),
            limit,
            window: std::time::Duration::from_secs(window_seconds),
        }
    }

    fn check_limit(&self, key: String) -> PyResult<bool> {
        let now = std::time::Instant::now();
        let mut requests = self.requests.write()
            .map_err(|e| PyValueError::new_err(format!("Lock error: {}", e)))?;

        let entry = requests.entry(key).or_insert_with(Vec::new);

        // Remove expired entries
        entry.retain(|&t| now.duration_since(t) < self.window);

        // Check limit
        if entry.len() >= self.limit {
            Ok(false)
        } else {
            entry.push(now);
            Ok(true)
        }
    }

    fn reset(&self, key: String) -> PyResult<()> {
        let mut requests = self.requests.write()
            .map_err(|e| PyValueError::new_err(format!("Lock error: {}", e)))?;
        requests.remove(&key);
        Ok(())
    }
}

/// Response timer
#[pyclass]
struct ResponseTimer {
    timers: std::sync::Arc<std::sync::RwLock<std::collections::HashMap<u64, std::time::Instant>>>,
}

#[pymethods]
impl ResponseTimer {
    #[new]
    fn new() -> Self {
        ResponseTimer {
            timers: std::sync::Arc::new(std::sync::RwLock::new(std::collections::HashMap::new())),
        }
    }

    fn start(&self, request_id: u64) -> PyResult<()> {
        let mut timers = self.timers.write()
            .map_err(|e| PyValueError::new_err(format!("Lock error: {}", e)))?;
        timers.insert(request_id, std::time::Instant::now());
        Ok(())
    }

    fn stop(&self, request_id: u64) -> PyResult<f64> {
        let mut timers = self.timers.write()
            .map_err(|e| PyValueError::new_err(format!("Lock error: {}", e)))?;

        if let Some(start) = timers.remove(&request_id) {
            Ok(start.elapsed().as_secs_f64())
        } else {
            Err(PyValueError::new_err("Timer not found"))
        }
    }
}

/// Python module initialization
#[pymodule]
fn flask_extension(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(compress_response, m)?)?;
    m.add_function(wrap_pyfunction!(decompress_request, m)?)?;
    m.add_function(wrap_pyfunction!(parse_query_string, m)?)?;
    m.add_function(wrap_pyfunction!(build_query_string, m)?)?;
    m.add_function(wrap_pyfunction!(hash_request, m)?)?;
    m.add_class::<RateLimiter>()?;
    m.add_class::<ResponseTimer>()?;
    Ok(())
}
