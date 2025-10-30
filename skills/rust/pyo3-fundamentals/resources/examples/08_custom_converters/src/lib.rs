//! Advanced FromPyObject and IntoPy implementations
//!
//! Demonstrates:
//! - Custom FromPyObject implementations
//! - Custom IntoPy implementations
//! - Type conversion protocols
//! - Complex deserialization

use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyString};

/// Custom type with FromPyObject
#[derive(Clone)]
struct Color {
    r: u8,
    g: u8,
    b: u8,
}

impl<'py> FromPyObject<'py> for Color {
    fn extract_bound(obj: &Bound<'py, PyAny>) -> PyResult<Self> {
        // Try to extract from dict
        if let Ok(dict) = obj.downcast::<PyDict>() {
            let r: u8 = dict.get_item("r")?.unwrap().extract()?;
            let g: u8 = dict.get_item("g")?.unwrap().extract()?;
            let b: u8 = dict.get_item("b")?.unwrap().extract()?;
            return Ok(Color { r, g, b });
        }

        // Try to extract from tuple
        if let Ok((r, g, b)) = obj.extract::<(u8, u8, u8)>() {
            return Ok(Color { r, g, b });
        }

        // Try to extract from hex string
        if let Ok(s) = obj.downcast::<PyString>() {
            let hex_str = s.to_str()?;
            if hex_str.starts_with('#') && hex_str.len() == 7 {
                let r = u8::from_str_radix(&hex_str[1..3], 16)
                    .map_err(|_| PyValueError::new_err("Invalid hex color"))?;
                let g = u8::from_str_radix(&hex_str[3..5], 16)
                    .map_err(|_| PyValueError::new_err("Invalid hex color"))?;
                let b = u8::from_str_radix(&hex_str[5..7], 16)
                    .map_err(|_| PyValueError::new_err("Invalid hex color"))?;
                return Ok(Color { r, g, b });
            }
        }

        Err(PyValueError::new_err(
            "Color must be dict, tuple, or hex string"
        ))
    }
}

/// Function using custom converter
#[pyfunction]
fn make_color_darker(color: Color, amount: u8) -> (u8, u8, u8) {
    (
        color.r.saturating_sub(amount),
        color.g.saturating_sub(amount),
        color.b.saturating_sub(amount),
    )
}

/// Coordinate with flexible input
#[derive(Clone)]
struct Coordinate {
    x: f64,
    y: f64,
}

impl<'py> FromPyObject<'py> for Coordinate {
    fn extract_bound(obj: &Bound<'py, PyAny>) -> PyResult<Self> {
        // From dict
        if let Ok(dict) = obj.downcast::<PyDict>() {
            let x: f64 = dict.get_item("x")?.unwrap().extract()?;
            let y: f64 = dict.get_item("y")?.unwrap().extract()?;
            return Ok(Coordinate { x, y });
        }

        // From tuple or list
        if let Ok((x, y)) = obj.extract::<(f64, f64)>() {
            return Ok(Coordinate { x, y });
        }

        Err(PyValueError::new_err("Coordinate must be dict or tuple"))
    }
}

#[pyfunction]
fn distance_between(c1: Coordinate, c2: Coordinate) -> f64 {
    let dx = c1.x - c2.x;
    let dy = c1.y - c2.y;
    (dx * dx + dy * dy).sqrt()
}

/// Custom class with IntoPy
#[pyclass]
#[derive(Clone)]
struct Range {
    start: i64,
    end: i64,
}

#[pymethods]
impl Range {
    #[new]
    fn new(start: i64, end: i64) -> Self {
        Range { start, end }
    }

    fn __repr__(&self) -> String {
        format!("Range({}, {})", self.start, self.end)
    }

    fn to_list(&self) -> Vec<i64> {
        (self.start..self.end).collect()
    }
}

/// Duration from various formats
struct Duration {
    seconds: u64,
}

impl<'py> FromPyObject<'py> for Duration {
    fn extract_bound(obj: &Bound<'py, PyAny>) -> PyResult<Self> {
        // From integer (seconds)
        if let Ok(secs) = obj.extract::<u64>() {
            return Ok(Duration { seconds: secs });
        }

        // From dict with units
        if let Ok(dict) = obj.downcast::<PyDict>() {
            let mut total_secs = 0u64;

            if let Some(hours) = dict.get_item("hours")? {
                total_secs += hours.extract::<u64>()? * 3600;
            }
            if let Some(minutes) = dict.get_item("minutes")? {
                total_secs += minutes.extract::<u64>()? * 60;
            }
            if let Some(seconds) = dict.get_item("seconds")? {
                total_secs += seconds.extract::<u64>()?;
            }

            return Ok(Duration { seconds: total_secs });
        }

        Err(PyValueError::new_err("Duration must be int or dict"))
    }
}

#[pyfunction]
fn sleep_for(duration: Duration) -> String {
    format!("Sleeping for {} seconds", duration.seconds)
}

#[pymodule]
fn custom_converters(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<Range>()?;
    m.add_function(wrap_pyfunction!(make_color_darker, m)?)?;
    m.add_function(wrap_pyfunction!(distance_between, m)?)?;
    m.add_function(wrap_pyfunction!(sleep_for, m)?)?;
    Ok(())
}
