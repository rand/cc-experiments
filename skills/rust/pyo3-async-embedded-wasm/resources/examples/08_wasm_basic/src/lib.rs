use wasm_bindgen::prelude::*;

#[wasm_bindgen]
pub fn process_array(data: Vec<f64>) -> Vec<f64> {
    data.iter().map(|x| x * 2.0).collect()
}

#[wasm_bindgen]
pub fn compute_stats(data: Vec<f64>) -> JsValue {
    if data.is_empty() {
        return JsValue::NULL;
    }

    let sum: f64 = data.iter().sum();
    let mean = sum / data.len() as f64;
    let min = data.iter().fold(f64::INFINITY, |a, &b| a.min(b));
    let max = data.iter().fold(f64::NEG_INFINITY, |a, &b| a.max(b));

    serde_wasm_bindgen::to_value(&serde_json::json!({
        "sum": sum,
        "mean": mean,
        "min": min,
        "max": max,
        "count": data.len()
    }))
    .unwrap()
}

#[wasm_bindgen]
pub struct DataProcessor {
    multiplier: f64,
}

#[wasm_bindgen]
impl DataProcessor {
    #[wasm_bindgen(constructor)]
    pub fn new(multiplier: f64) -> Self {
        Self { multiplier }
    }

    pub fn process(&self, data: Vec<f64>) -> Vec<f64> {
        data.iter().map(|x| x * self.multiplier).collect()
    }

    pub fn set_multiplier(&mut self, multiplier: f64) {
        self.multiplier = multiplier;
    }
}

// Conditional PyO3 bindings (not for WASM)
#[cfg(not(target_arch = "wasm32"))]
use pyo3::prelude::*;

#[cfg(not(target_arch = "wasm32"))]
#[pyfunction]
fn py_process_array(data: Vec<f64>) -> Vec<f64> {
    process_array(data)
}

#[cfg(not(target_arch = "wasm32"))]
#[pymodule]
fn wasm_basic(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(py_process_array, m)?)?;
    Ok(())
}
