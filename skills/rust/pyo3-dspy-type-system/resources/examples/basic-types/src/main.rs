use anyhow::{anyhow, Context, Result};
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};
use std::collections::HashMap;

/// Demonstrates basic Python to Rust type conversions for DSPy integration.
///
/// This example covers the fundamental type mappings needed when extracting
/// data from DSPy predictions: strings, numbers, booleans, lists, dicts, and optionals.

fn main() -> Result<()> {
    println!("=== Basic Type Mapping Examples ===\n");

    Python::with_gil(|py| {
        // String extraction
        demonstrate_string_extraction(py)?;

        // Integer extraction
        demonstrate_integer_extraction(py)?;

        // Float extraction
        demonstrate_float_extraction(py)?;

        // Boolean extraction
        demonstrate_boolean_extraction(py)?;

        // List[str] extraction
        demonstrate_list_extraction(py)?;

        // Dict[str, int] extraction
        demonstrate_dict_extraction(py)?;

        // Optional[str] extraction
        demonstrate_optional_extraction(py)?;

        // Complex example: DSPy-style prediction
        demonstrate_prediction_extraction(py)?;

        Ok(())
    })
}

/// Example 1: String extraction (Python str → Rust String)
fn demonstrate_string_extraction(py: Python) -> Result<()> {
    println!("String Extraction:");

    // Create Python string
    let py_string = py.eval_bound("'Hello, World!'", None, None)?;
    println!("  Python: {:?}", py_string);

    // Extract to Rust String
    let rust_string: String = py_string.extract()?;
    println!("  Rust: {}\n", rust_string);

    Ok(())
}

/// Example 2: Integer extraction (Python int → Rust i64)
fn demonstrate_integer_extraction(py: Python) -> Result<()> {
    println!("Integer Extraction:");

    // Create Python int
    let py_int = py.eval_bound("42", None, None)?;
    println!("  Python: {:?}", py_int);

    // Extract to Rust i64
    let rust_int: i64 = py_int.extract()?;
    println!("  Rust: {}\n", rust_int);

    Ok(())
}

/// Example 3: Float extraction (Python float → Rust f64)
fn demonstrate_float_extraction(py: Python) -> Result<()> {
    println!("Float Extraction:");

    // Create Python float
    let py_float = py.eval_bound("3.14159", None, None)?;
    println!("  Python: {:?}", py_float);

    // Extract to Rust f64
    let rust_float: f64 = py_float.extract()?;
    println!("  Rust: {}\n", rust_float);

    Ok(())
}

/// Example 4: Boolean extraction (Python bool → Rust bool)
fn demonstrate_boolean_extraction(py: Python) -> Result<()> {
    println!("Boolean Extraction:");

    // Create Python bool
    let py_bool = py.eval_bound("True", None, None)?;
    println!("  Python: {:?}", py_bool);

    // Extract to Rust bool
    let rust_bool: bool = py_bool.extract()?;
    println!("  Rust: {}\n", rust_bool);

    Ok(())
}

/// Example 5: List[str] extraction (Python list → Rust Vec<String>)
fn demonstrate_list_extraction(py: Python) -> Result<()> {
    println!("List[str] Extraction:");

    // Create Python list
    let py_list = py.eval_bound("['apple', 'banana', 'cherry']", None, None)?;
    println!("  Python: {:?}", py_list);

    // Extract to Rust Vec<String>
    let rust_vec = extract_string_list(&py_list)?;
    println!("  Rust: {:?}\n", rust_vec);

    Ok(())
}

/// Helper: Extract Python list to Rust Vec<String>
fn extract_string_list(obj: &Bound<'_, PyAny>) -> Result<Vec<String>> {
    let list = obj.downcast::<PyList>()
        .map_err(|e| anyhow!("Expected a Python list: {}", e))?;

    let mut result = Vec::new();
    for item in list.iter() {
        result.push(item.extract::<String>()?);
    }

    Ok(result)
}

/// Example 6: Dict[str, int] extraction (Python dict → Rust HashMap)
fn demonstrate_dict_extraction(py: Python) -> Result<()> {
    println!("Dict[str, int] Extraction:");

    // Create Python dict
    let py_dict = py.eval_bound("{'x': 10, 'y': 20, 'z': 30}", None, None)?;
    println!("  Python: {:?}", py_dict);

    // Extract to Rust HashMap
    let rust_map = extract_string_int_dict(&py_dict)?;
    println!("  Rust: {:?}\n", rust_map);

    Ok(())
}

/// Helper: Extract Python dict to Rust HashMap<String, i64>
fn extract_string_int_dict(obj: &Bound<'_, PyAny>) -> Result<HashMap<String, i64>> {
    let dict = obj.downcast::<PyDict>()
        .map_err(|e| anyhow!("Expected a Python dict: {}", e))?;

    let mut map = HashMap::new();

    for (key, value) in dict.iter() {
        let k = key.extract::<String>()
            .context("Dict key must be a string")?;
        let v = value.extract::<i64>()
            .context("Dict value must be an integer")?;
        map.insert(k, v);
    }

    Ok(map)
}

/// Example 7: Optional[str] extraction (Python None/str → Rust Option<String>)
fn demonstrate_optional_extraction(py: Python) -> Result<()> {
    println!("Optional[str] Extraction:");

    // Some value
    let py_some = py.eval_bound("'some_value'", None, None)?;
    println!("  Python: {:?}", py_some);
    let rust_some = extract_optional_string(&py_some)?;
    println!("  Rust: {:?}\n", rust_some);

    // None value
    let py_none = py.eval_bound("None", None, None)?;
    println!("  Python: {:?}", py_none);
    let rust_none = extract_optional_string(&py_none)?;
    println!("  Rust: {:?}\n", rust_none);

    Ok(())
}

/// Helper: Extract Python None/str to Rust Option<String>
fn extract_optional_string(obj: &Bound<'_, PyAny>) -> Result<Option<String>> {
    if obj.is_none() {
        Ok(None)
    } else {
        Ok(Some(obj.extract::<String>()?))
    }
}

/// Example 8: DSPy-style prediction extraction
fn demonstrate_prediction_extraction(py: Python) -> Result<()> {
    println!("=== DSPy-Style Prediction Extraction ===\n");

    // Simulate a DSPy prediction object
    let prediction_code = r#"
class Prediction:
    def __init__(self):
        self.summary = "This is a generated summary"
        self.confidence = 0.95
        self.word_count = 150
        self.is_valid = True
        self.tags = ["science", "technology", "AI"]
        self.metadata = {"author": "model", "version": "1"}
        self.optional_note = None

Prediction()
"#;

    let prediction = py.eval_bound(prediction_code, None, None)?;

    // Extract all fields with proper type conversions
    let pred_data = PredictionData::from_python(&prediction)?;

    println!("Extracted Prediction Data:");
    println!("  summary: {}", pred_data.summary);
    println!("  confidence: {}", pred_data.confidence);
    println!("  word_count: {}", pred_data.word_count);
    println!("  is_valid: {}", pred_data.is_valid);
    println!("  tags: {:?}", pred_data.tags);
    println!("  metadata: {:?}", pred_data.metadata);
    println!("  optional_note: {:?}\n", pred_data.optional_note);

    Ok(())
}

/// Rust representation of a DSPy prediction with basic types
#[derive(Debug)]
struct PredictionData {
    summary: String,
    confidence: f64,
    word_count: i64,
    is_valid: bool,
    tags: Vec<String>,
    metadata: HashMap<String, String>,
    optional_note: Option<String>,
}

impl PredictionData {
    /// Extract all fields from a Python prediction object
    fn from_python(obj: &Bound<'_, PyAny>) -> Result<Self> {
        Ok(Self {
            summary: obj.getattr("summary")?
                .extract()
                .context("Failed to extract summary")?,

            confidence: obj.getattr("confidence")?
                .extract()
                .context("Failed to extract confidence")?,

            word_count: obj.getattr("word_count")?
                .extract()
                .context("Failed to extract word_count")?,

            is_valid: obj.getattr("is_valid")?
                .extract()
                .context("Failed to extract is_valid")?,

            tags: extract_string_list(&obj.getattr("tags")?)
                .context("Failed to extract tags")?,

            metadata: extract_string_string_dict(&obj.getattr("metadata")?)
                .context("Failed to extract metadata")?,

            optional_note: extract_optional_string(&obj.getattr("optional_note")?)
                .context("Failed to extract optional_note")?,
        })
    }
}

/// Helper: Extract Python dict to Rust HashMap<String, String>
fn extract_string_string_dict(obj: &Bound<'_, PyAny>) -> Result<HashMap<String, String>> {
    let dict = obj.downcast::<PyDict>()
        .map_err(|e| anyhow!("Expected a Python dict: {}", e))?;

    let mut map = HashMap::new();

    for (key, value) in dict.iter() {
        let k = key.extract::<String>()
            .context("Dict key must be a string")?;
        let v = value.extract::<String>()
            .context("Dict value must be a string")?;
        map.insert(k, v);
    }

    Ok(map)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_string_extraction() {
        Python::with_gil(|py| {
            let py_string = py.eval_bound("'test'", None, None).unwrap();
            let rust_string: String = py_string.extract().unwrap();
            assert_eq!(rust_string, "test");
        });
    }

    #[test]
    fn test_integer_extraction() {
        Python::with_gil(|py| {
            let py_int = py.eval_bound("42", None, None).unwrap();
            let rust_int: i64 = py_int.extract().unwrap();
            assert_eq!(rust_int, 42);
        });
    }

    #[test]
    fn test_float_extraction() {
        Python::with_gil(|py| {
            let py_float = py.eval_bound("3.14", None, None).unwrap();
            let rust_float: f64 = py_float.extract().unwrap();
            assert!((rust_float - 3.14).abs() < 0.001);
        });
    }

    #[test]
    fn test_boolean_extraction() {
        Python::with_gil(|py| {
            let py_bool = py.eval_bound("True", None, None).unwrap();
            let rust_bool: bool = py_bool.extract().unwrap();
            assert_eq!(rust_bool, true);
        });
    }

    #[test]
    fn test_list_extraction() {
        Python::with_gil(|py| {
            let py_list = py.eval_bound("['a', 'b', 'c']", None, None).unwrap();
            let rust_vec = extract_string_list(&py_list).unwrap();
            assert_eq!(rust_vec, vec!["a", "b", "c"]);
        });
    }

    #[test]
    fn test_dict_extraction() {
        Python::with_gil(|py| {
            let py_dict = py.eval_bound("{'x': 1, 'y': 2}", None, None).unwrap();
            let rust_map = extract_string_int_dict(&py_dict).unwrap();
            assert_eq!(rust_map.get("x"), Some(&1));
            assert_eq!(rust_map.get("y"), Some(&2));
        });
    }

    #[test]
    fn test_optional_some() {
        Python::with_gil(|py| {
            let py_value = py.eval_bound("'value'", None, None).unwrap();
            let rust_opt = extract_optional_string(&py_value).unwrap();
            assert_eq!(rust_opt, Some("value".to_string()));
        });
    }

    #[test]
    fn test_optional_none() {
        Python::with_gil(|py| {
            let py_none = py.eval_bound("None", None, None).unwrap();
            let rust_opt = extract_optional_string(&py_none).unwrap();
            assert_eq!(rust_opt, None);
        });
    }

    #[test]
    fn test_prediction_extraction() {
        Python::with_gil(|py| {
            let prediction_code = r#"
class Prediction:
    def __init__(self):
        self.summary = "test"
        self.confidence = 0.9
        self.word_count = 100
        self.is_valid = True
        self.tags = ["tag1"]
        self.metadata = {"key": "value"}
        self.optional_note = None

Prediction()
"#;
            let prediction = py.eval_bound(prediction_code, None, None).unwrap();
            let data = PredictionData::from_python(&prediction).unwrap();

            assert_eq!(data.summary, "test");
            assert!((data.confidence - 0.9).abs() < 0.001);
            assert_eq!(data.word_count, 100);
            assert_eq!(data.is_valid, true);
            assert_eq!(data.tags, vec!["tag1"]);
            assert_eq!(data.metadata.get("key"), Some(&"value".to_string()));
            assert_eq!(data.optional_note, None);
        });
    }
}
