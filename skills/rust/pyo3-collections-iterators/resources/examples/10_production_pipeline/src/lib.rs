use pyo3::prelude::*;
use pyo3::types::PyDict;
use rayon::prelude::*;
use std::collections::HashMap;

/// Production data pipeline combining all concepts
#[pyclass]
struct DataPipeline {
    raw_data: Vec<DataRecord>,
    filters: Vec<FilterConfig>,
    transforms: Vec<TransformConfig>,
}

#[derive(Clone)]
struct DataRecord {
    id: u64,
    value: f64,
    category: String,
    timestamp: u64,
}

#[derive(Clone)]
struct FilterConfig {
    field: String,
    threshold: f64,
}

#[derive(Clone)]
struct TransformConfig {
    operation: String,
    factor: f64,
}

#[pymethods]
impl DataPipeline {
    #[new]
    fn new() -> Self {
        DataPipeline {
            raw_data: Vec::new(),
            filters: Vec::new(),
            transforms: Vec::new(),
        }
    }

    /// Add data record
    fn add_record(&mut self, id: u64, value: f64, category: String, timestamp: u64) {
        self.raw_data.push(DataRecord {
            id,
            value,
            category,
            timestamp,
        });
    }

    /// Add filter
    fn add_filter(&mut self, field: String, threshold: f64) {
        self.filters.push(FilterConfig { field, threshold });
    }

    /// Add transform
    fn add_transform(&mut self, operation: String, factor: f64) {
        self.transforms.push(TransformConfig { operation, factor });
    }

    /// Execute pipeline
    fn execute(&self, parallel: bool) -> Vec<(u64, f64, String, u64)> {
        let data = self.raw_data.clone();

        let processed = if parallel {
            data.par_iter()
                .filter(|r| self.apply_filters(r))
                .map(|r| self.apply_transforms(r))
                .collect()
        } else {
            data.iter()
                .filter(|r| self.apply_filters(r))
                .map(|r| self.apply_transforms(r))
                .collect()
        };

        processed
            .into_iter()
            .map(|r| (r.id, r.value, r.category, r.timestamp))
            .collect()
    }

    /// Get statistics
    fn statistics(&self, py: Python) -> PyResult<PyObject> {
        let dict = PyDict::new(py);

        if !self.raw_data.is_empty() {
            let values: Vec<f64> = self.raw_data.iter().map(|r| r.value).collect();
            let sum: f64 = values.iter().sum();
            let count = values.len() as f64;
            let mean = sum / count;

            dict.set_item("count", count as u64)?;
            dict.set_item("sum", sum)?;
            dict.set_item("mean", mean)?;
            dict.set_item(
                "min",
                values.iter().cloned().fold(f64::INFINITY, f64::min),
            )?;
            dict.set_item(
                "max",
                values.iter().cloned().fold(f64::NEG_INFINITY, f64::max),
            )?;
        }

        Ok(dict.into())
    }

    /// Group by category
    fn group_by_category(&self) -> HashMap<String, Vec<f64>> {
        let mut groups: HashMap<String, Vec<f64>> = HashMap::new();

        for record in &self.raw_data {
            groups
                .entry(record.category.clone())
                .or_insert_with(Vec::new)
                .push(record.value);
        }

        groups
    }

    fn __len__(&self) -> usize {
        self.raw_data.len()
    }
}

impl DataPipeline {
    fn apply_filters(&self, record: &DataRecord) -> bool {
        for filter in &self.filters {
            match filter.field.as_str() {
                "value" => {
                    if record.value <= filter.threshold {
                        return false;
                    }
                }
                _ => {}
            }
        }
        true
    }

    fn apply_transforms(&self, record: &DataRecord) -> DataRecord {
        let mut result = record.clone();

        for transform in &self.transforms {
            match transform.operation.as_str() {
                "multiply" => result.value *= transform.factor,
                "add" => result.value += transform.factor,
                "log" => result.value = result.value.ln(),
                _ => {}
            }
        }

        result
    }
}

/// Time series processor
#[pyclass]
struct TimeSeriesProcessor {
    data: Vec<(u64, f64)>,  // (timestamp, value)
}

#[pymethods]
impl TimeSeriesProcessor {
    #[new]
    fn new(data: Vec<(u64, f64)>) -> Self {
        TimeSeriesProcessor { data }
    }

    /// Moving average
    fn moving_average(&self, window_size: usize) -> Vec<(u64, f64)> {
        if window_size == 0 || self.data.is_empty() {
            return Vec::new();
        }

        self.data
            .windows(window_size)
            .map(|window| {
                let sum: f64 = window.iter().map(|(_, v)| v).sum();
                let avg = sum / window.len() as f64;
                (window[window.len() / 2].0, avg)
            })
            .collect()
    }

    /// Detect anomalies (values > threshold * stddev from mean)
    fn detect_anomalies(&self, threshold: f64) -> Vec<(u64, f64)> {
        if self.data.is_empty() {
            return Vec::new();
        }

        let values: Vec<f64> = self.data.iter().map(|(_, v)| *v).collect();
        let mean: f64 = values.iter().sum::<f64>() / values.len() as f64;
        let variance: f64 = values.iter().map(|v| (v - mean).powi(2)).sum::<f64>()
            / values.len() as f64;
        let stddev = variance.sqrt();

        self.data
            .iter()
            .filter(|(_, v)| (*v - mean).abs() > threshold * stddev)
            .copied()
            .collect()
    }

    /// Resample to fixed intervals
    fn resample(&self, interval: u64) -> Vec<(u64, f64)> {
        if self.data.is_empty() {
            return Vec::new();
        }

        let mut result = Vec::new();
        let mut current_bucket: Vec<f64> = Vec::new();
        let start_time = self.data[0].0;
        let mut bucket_idx = 0u64;

        for (ts, value) in &self.data {
            let expected_bucket = (ts - start_time) / interval;

            if expected_bucket > bucket_idx {
                if !current_bucket.is_empty() {
                    let avg = current_bucket.iter().sum::<f64>() / current_bucket.len() as f64;
                    result.push((start_time + bucket_idx * interval, avg));
                }
                current_bucket.clear();
                bucket_idx = expected_bucket;
            }

            current_bucket.push(*value);
        }

        if !current_bucket.is_empty() {
            let avg = current_bucket.iter().sum::<f64>() / current_bucket.len() as f64;
            result.push((start_time + bucket_idx * interval, avg));
        }

        result
    }
}

#[pymodule]
fn production_pipeline(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<DataPipeline>()?;
    m.add_class::<TimeSeriesProcessor>()?;
    Ok(())
}
