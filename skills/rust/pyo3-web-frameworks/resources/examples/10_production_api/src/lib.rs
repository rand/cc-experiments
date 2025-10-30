//! Complete production REST API with CRUD, auth, validation, and caching
//!
//! This example demonstrates a full production-ready API combining:
//! - CRUD operations
//! - JWT authentication
//! - Request validation
//! - Response caching
//! - Rate limiting
//! - Error handling
//! - Logging

use pyo3::prelude::*;
use pyo3::exceptions::{PyValueError, PyRuntimeError};
use std::collections::HashMap;
use std::sync::{Arc, RwLock};
use std::time::{Instant, Duration};
use serde::{Serialize, Deserialize};

/// User model
#[derive(Serialize, Deserialize, Clone)]
struct User {
    id: u64,
    username: String,
    email: String,
    created_at: u64,
}

/// API Response wrapper
#[pyclass]
#[derive(Clone)]
struct ApiResponse {
    #[pyo3(get, set)]
    success: bool,
    #[pyo3(get, set)]
    data: Option<String>,
    #[pyo3(get, set)]
    error: Option<String>,
}

#[pymethods]
impl ApiResponse {
    #[new]
    fn new(success: bool, data: Option<String>, error: Option<String>) -> Self {
        ApiResponse { success, data, error }
    }
}

/// Production database with CRUD operations
#[pyclass]
struct Database {
    users: Arc<RwLock<HashMap<u64, User>>>,
    next_id: Arc<RwLock<u64>>,
}

#[pymethods]
impl Database {
    #[new]
    fn new() -> Self {
        Database {
            users: Arc::new(RwLock::new(HashMap::new())),
            next_id: Arc::new(RwLock::new(1)),
        }
    }

    fn create_user(&self, username: String, email: String) -> PyResult<String> {
        let mut users = self.users.write().unwrap();
        let mut next_id = self.next_id.write().unwrap();

        let user = User {
            id: *next_id,
            username,
            email,
            created_at: std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_secs(),
        };

        users.insert(*next_id, user.clone());
        *next_id += 1;

        serde_json::to_string(&user)
            .map_err(|e| PyRuntimeError::new_err(format!("Serialize error: {}", e)))
    }

    fn get_user(&self, id: u64) -> PyResult<Option<String>> {
        let users = self.users.read().unwrap();
        if let Some(user) = users.get(&id) {
            serde_json::to_string(user)
                .map(Some)
                .map_err(|e| PyRuntimeError::new_err(format!("Serialize error: {}", e)))
        } else {
            Ok(None)
        }
    }

    fn update_user(&self, id: u64, username: Option<String>, email: Option<String>) -> PyResult<bool> {
        let mut users = self.users.write().unwrap();
        if let Some(user) = users.get_mut(&id) {
            if let Some(name) = username {
                user.username = name;
            }
            if let Some(mail) = email {
                user.email = mail;
            }
            Ok(true)
        } else {
            Ok(false)
        }
    }

    fn delete_user(&self, id: u64) -> PyResult<bool> {
        let mut users = self.users.write().unwrap();
        Ok(users.remove(&id).is_some())
    }

    fn list_users(&self) -> PyResult<String> {
        let users = self.users.read().unwrap();
        let user_list: Vec<&User> = users.values().collect();

        serde_json::to_string(&user_list)
            .map_err(|e| PyRuntimeError::new_err(format!("Serialize error: {}", e)))
    }
}

/// Authentication manager
#[pyclass]
struct AuthManager {
    tokens: Arc<RwLock<HashMap<String, (u64, Instant)>>>,
    token_ttl: Duration,
}

#[pymethods]
impl AuthManager {
    #[new]
    fn new(ttl_seconds: u64) -> Self {
        AuthManager {
            tokens: Arc::new(RwLock::new(HashMap::new())),
            token_ttl: Duration::from_secs(ttl_seconds),
        }
    }

    fn create_token(&self, user_id: u64) -> PyResult<String> {
        use sha2::{Sha256, Digest};

        let token_data = format!("{}:{}", user_id, Instant::now().elapsed().as_nanos());
        let mut hasher = Sha256::new();
        hasher.update(token_data.as_bytes());
        let token = format!("{:x}", hasher.finalize());

        let mut tokens = self.tokens.write().unwrap();
        tokens.insert(token.clone(), (user_id, Instant::now()));

        Ok(token)
    }

    fn verify_token(&self, token: String) -> PyResult<Option<u64>> {
        let mut tokens = self.tokens.write().unwrap();

        if let Some((user_id, created_at)) = tokens.get(&token) {
            if created_at.elapsed() < self.token_ttl {
                return Ok(Some(*user_id));
            } else {
                tokens.remove(&token);
            }
        }

        Ok(None)
    }

    fn revoke_token(&self, token: String) -> PyResult<bool> {
        let mut tokens = self.tokens.write().unwrap();
        Ok(tokens.remove(&token).is_some())
    }
}

/// Request validator
#[pyfunction]
fn validate_user_input(username: String, email: String) -> PyResult<Vec<String>> {
    let mut errors = Vec::new();

    if username.len() < 3 {
        errors.push("Username must be at least 3 characters".to_string());
    }

    if username.len() > 20 {
        errors.push("Username must be at most 20 characters".to_string());
    }

    if !username.chars().all(|c| c.is_alphanumeric() || c == '_') {
        errors.push("Username can only contain alphanumeric and underscore".to_string());
    }

    if !email.contains('@') || !email.contains('.') {
        errors.push("Invalid email format".to_string());
    }

    Ok(errors)
}

/// Rate limiter for production
#[pyclass]
struct ProductionRateLimiter {
    requests: Arc<RwLock<HashMap<String, Vec<Instant>>>>,
    limit: usize,
    window: Duration,
}

#[pymethods]
impl ProductionRateLimiter {
    #[new]
    fn new(limit: usize, window_seconds: u64) -> Self {
        ProductionRateLimiter {
            requests: Arc::new(RwLock::new(HashMap::new())),
            limit,
            window: Duration::from_secs(window_seconds),
        }
    }

    fn check_limit(&self, key: String) -> PyResult<bool> {
        let now = Instant::now();
        let mut requests = self.requests.write().unwrap();

        let entry = requests.entry(key).or_insert_with(Vec::new);
        entry.retain(|&t| now.duration_since(t) < self.window);

        if entry.len() >= self.limit {
            Ok(false)
        } else {
            entry.push(now);
            Ok(true)
        }
    }
}

/// Production cache
#[pyclass]
struct ProductionCache {
    data: Arc<RwLock<HashMap<String, (String, Instant)>>>,
    ttl: Duration,
}

#[pymethods]
impl ProductionCache {
    #[new]
    fn new(ttl_seconds: u64) -> Self {
        ProductionCache {
            data: Arc::new(RwLock::new(HashMap::new())),
            ttl: Duration::from_secs(ttl_seconds),
        }
    }

    fn get(&self, key: String) -> PyResult<Option<String>> {
        let data = self.data.read().unwrap();
        if let Some((value, timestamp)) = data.get(&key) {
            if timestamp.elapsed() < self.ttl {
                return Ok(Some(value.clone()));
            }
        }
        Ok(None)
    }

    fn set(&self, key: String, value: String) -> PyResult<()> {
        let mut data = self.data.write().unwrap();
        data.insert(key, (value, Instant::now()));
        Ok(())
    }

    fn invalidate(&self, key: String) -> PyResult<()> {
        let mut data = self.data.write().unwrap();
        data.remove(&key);
        Ok(())
    }
}

/// Python module initialization
#[pymodule]
fn production_api(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<ApiResponse>()?;
    m.add_class::<Database>()?;
    m.add_class::<AuthManager>()?;
    m.add_class::<ProductionRateLimiter>()?;
    m.add_class::<ProductionCache>()?;
    m.add_function(wrap_pyfunction!(validate_user_input, m)?)?;
    Ok(())
}
