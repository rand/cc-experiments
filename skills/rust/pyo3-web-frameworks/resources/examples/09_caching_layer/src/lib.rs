//! Redis/in-memory caching layer

use pyo3::prelude::*;
use std::collections::HashMap;
use std::sync::{Arc, RwLock};
use std::time::{Duration, Instant};

#[pyclass]
struct Cache {
    data: Arc<RwLock<HashMap<String, (Vec<u8>, Instant)>>>,
    ttl: Duration,
}

#[pymethods]
impl Cache {
    #[new]
    fn new(ttl_seconds: u64) -> Self {
        Cache {
            data: Arc::new(RwLock::new(HashMap::new())),
            ttl: Duration::from_secs(ttl_seconds),
        }
    }

    fn get(&self, key: String) -> PyResult<Option<Vec<u8>>> {
        let data = self.data.read().unwrap();
        if let Some((value, timestamp)) = data.get(&key) {
            if timestamp.elapsed() < self.ttl {
                return Ok(Some(value.clone()));
            }
        }
        Ok(None)
    }

    fn set(&self, key: String, value: Vec<u8>) -> PyResult<()> {
        let mut data = self.data.write().unwrap();
        data.insert(key, (value, Instant::now()));
        Ok(())
    }

    fn delete(&self, key: String) -> PyResult<bool> {
        let mut data = self.data.write().unwrap();
        Ok(data.remove(&key).is_some())
    }

    fn clear(&self) -> PyResult<()> {
        self.data.write().unwrap().clear();
        Ok(())
    }

    fn cleanup_expired(&self) -> PyResult<usize> {
        let mut data = self.data.write().unwrap();
        let initial_size = data.len();

        data.retain(|_, (_, timestamp)| timestamp.elapsed() < self.ttl);

        Ok(initial_size - data.len())
    }

    fn size(&self) -> PyResult<usize> {
        Ok(self.data.read().unwrap().len())
    }
}

#[pyclass]
struct LRUCache {
    capacity: usize,
    data: Arc<RwLock<HashMap<String, Vec<u8>>>>,
    order: Arc<RwLock<Vec<String>>>,
}

#[pymethods]
impl LRUCache {
    #[new]
    fn new(capacity: usize) -> Self {
        LRUCache {
            capacity,
            data: Arc::new(RwLock::new(HashMap::new())),
            order: Arc::new(RwLock::new(Vec::new())),
        }
    }

    fn get(&self, key: String) -> PyResult<Option<Vec<u8>>> {
        let data = self.data.read().unwrap();
        if let Some(value) = data.get(&key) {
            let mut order = self.order.write().unwrap();
            order.retain(|k| k != &key);
            order.push(key);
            return Ok(Some(value.clone()));
        }
        Ok(None)
    }

    fn set(&self, key: String, value: Vec<u8>) -> PyResult<()> {
        let mut data = self.data.write().unwrap();
        let mut order = self.order.write().unwrap();

        if data.contains_key(&key) {
            order.retain(|k| k != &key);
        } else if data.len() >= self.capacity {
            if let Some(oldest) = order.first().cloned() {
                data.remove(&oldest);
                order.remove(0);
            }
        }

        data.insert(key.clone(), value);
        order.push(key);

        Ok(())
    }
}

#[pymodule]
fn caching_layer(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<Cache>()?;
    m.add_class::<LRUCache>()?;
    Ok(())
}
