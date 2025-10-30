mod types;

use anyhow::Result;
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};
use std::collections::HashMap;
use types::test_data;

/// Validates that a round-trip conversion preserves data
fn validate_roundtrip<T: PartialEq + std::fmt::Debug>(
    py: Python,
    original: &T,
    to_py: impl Fn(Python, &T) -> PyResult<PyObject>,
    from_py: impl Fn(&Bound<'_, PyAny>) -> PyResult<T>,
) -> Result<()> {
    // Convert to Python
    let py_obj = to_py(py, original)?;
    let py_any = py_obj.bind(py);

    // Convert back to Rust
    let roundtrip = from_py(py_any)?;

    // Verify equality
    assert_eq!(
        original, &roundtrip,
        "Round-trip conversion failed: original != roundtrip"
    );

    println!("✓ Round-trip validation passed");
    Ok(())
}

/// Example 1: Testing primitive types
fn example_primitive_types(py: Python) -> Result<()> {
    println!("\n=== Example 1: Primitive Types ===");

    // Integers
    println!("\n--- Integers ---");
    let int_values = vec![0, 1, -1, 42, i32::MAX, i32::MIN];
    for val in int_values {
        let py_val = val.to_object(py);
        let roundtrip: i32 = py_val.extract(py)?;
        assert_eq!(val, roundtrip);
        println!("  {} -> Python -> {} ✓", val, roundtrip);
    }

    // Floats (excluding NaN which doesn't equal itself)
    println!("\n--- Floats ---");
    let float_values = vec![0.0, 1.0, -1.0, 3.14159, f64::INFINITY, f64::NEG_INFINITY];
    for val in float_values {
        let py_val = val.to_object(py);
        let roundtrip: f64 = py_val.extract(py)?;
        assert_eq!(val, roundtrip);
        println!("  {} -> Python -> {} ✓", val, roundtrip);
    }

    // NaN special case
    println!("\n--- Special: NaN ---");
    let nan = f64::NAN;
    let py_nan = nan.to_object(py);
    let roundtrip_nan: f64 = py_nan.extract(py)?;
    assert!(roundtrip_nan.is_nan(), "NaN did not round-trip correctly");
    println!("  NaN -> Python -> NaN ✓");

    // Booleans
    println!("\n--- Booleans ---");
    for val in [true, false] {
        let py_val = val.to_object(py);
        let roundtrip: bool = py_val.extract(py)?;
        assert_eq!(val, roundtrip);
        println!("  {} -> Python -> {} ✓", val, roundtrip);
    }

    // Strings
    println!("\n--- Strings ---");
    let string_values = test_data::create_unicode_strings();
    for val in string_values {
        let py_val = val.to_object(py);
        let roundtrip: String = py_val.extract(py)?;
        assert_eq!(val, roundtrip);
        println!("  '{}' -> Python -> '{}' ✓", val, roundtrip);
    }

    Ok(())
}

/// Example 2: Testing collection types
fn example_collection_types(py: Python) -> Result<()> {
    println!("\n=== Example 2: Collection Types ===");

    // Vectors
    println!("\n--- Vectors ---");
    let vec_tests = vec![
        vec![],
        vec![1],
        vec![1, 2, 3, 4, 5],
    ];

    for vec in vec_tests {
        let py_list = PyList::new_bound(py, &vec);
        let roundtrip: Vec<i32> = py_list.extract()?;
        assert_eq!(vec, roundtrip);
        println!("  {:?} -> Python -> {:?} ✓", vec, roundtrip);
    }

    // HashMaps
    println!("\n--- HashMaps ---");
    let mut map1 = HashMap::new();
    map1.insert("a".to_string(), 1);
    map1.insert("b".to_string(), 2);
    map1.insert("c".to_string(), 3);

    let py_dict = PyDict::new_bound(py);
    for (k, v) in &map1 {
        py_dict.set_item(k, v)?;
    }
    let roundtrip: HashMap<String, i32> = py_dict.extract()?;
    assert_eq!(map1, roundtrip);
    println!("  HashMap with {} entries round-tripped ✓", map1.len());

    // Empty HashMap
    let empty_map: HashMap<String, i32> = HashMap::new();
    let py_empty_dict = PyDict::new_bound(py);
    let empty_roundtrip: HashMap<String, i32> = py_empty_dict.extract()?;
    assert_eq!(empty_map, empty_roundtrip);
    println!("  Empty HashMap -> Python -> Empty HashMap ✓");

    // Nested vectors
    println!("\n--- Nested Vectors ---");
    let nested = test_data::create_nested_vecs();
    let py_nested = types::primitives::vec_to_python(py, &nested)?;
    let nested_roundtrip: Vec<Vec<i32>> = py_nested.extract(py)?;
    assert_eq!(nested, nested_roundtrip);
    println!("  Nested Vec<Vec<i32>> round-tripped ✓");

    Ok(())
}

/// Example 3: Testing optional types
fn example_optional_types(py: Python) -> Result<()> {
    println!("\n=== Example 3: Optional Types ===");

    // Some values
    println!("\n--- Some Values ---");
    let some_int: Option<i32> = Some(42);
    let py_some = types::primitives::option_to_python(py, &some_int)?;
    let some_roundtrip: Option<i32> = py_some.extract(py)?;
    assert_eq!(some_int, some_roundtrip);
    println!("  Some(42) -> Python -> Some(42) ✓");

    // None values
    println!("\n--- None Values ---");
    let none_int: Option<i32> = None;
    let py_none = types::primitives::option_to_python(py, &none_int)?;
    let none_roundtrip: Option<i32> = py_none.extract(py)?;
    assert_eq!(none_int, none_roundtrip);
    println!("  None -> Python -> None ✓");

    // Vector with optional elements
    println!("\n--- Vec<Option<T>> ---");
    let optional_vec = test_data::create_optional_vec();
    let py_optional_vec = types::primitives::vec_to_python(py, &optional_vec)?;
    let optional_roundtrip: Vec<Option<i32>> = py_optional_vec.extract(py)?;
    assert_eq!(optional_vec, optional_roundtrip);
    println!("  Vec with {} optional elements round-tripped ✓", optional_vec.len());

    // HashMap with optional values
    println!("\n--- HashMap<K, Option<V>> ---");
    let mut optional_map: HashMap<String, Option<i32>> = HashMap::new();
    optional_map.insert("present".to_string(), Some(100));
    optional_map.insert("absent".to_string(), None);

    let py_optional_map = types::primitives::hashmap_to_python(py, &optional_map)?;
    let optional_map_roundtrip: HashMap<String, Option<i32>> = py_optional_map.bind(py).extract()?;
    assert_eq!(optional_map, optional_map_roundtrip);
    println!("  HashMap with optional values round-tripped ✓");

    Ok(())
}

/// Example 4: Testing complex struct types
fn example_struct_types(py: Python) -> Result<()> {
    println!("\n=== Example 4: Complex Struct Types ===");

    // Person with email
    println!("\n--- Person (with email) ---");
    let person1 = test_data::create_person_with_unicode();
    let py_person1 = person1.to_python(py)?;
    let person1_roundtrip = types::Person::from_python(&py_person1.bind(py))?;
    assert_eq!(person1, person1_roundtrip);
    println!("  Person '{}' (age {}) round-tripped ✓", person1.name, person1.age);

    // Person without email
    println!("\n--- Person (without email) ---");
    let person2 = test_data::create_person_without_email();
    let py_person2 = person2.to_python(py)?;
    let person2_roundtrip = types::Person::from_python(&py_person2.bind(py))?;
    assert_eq!(person2, person2_roundtrip);
    println!("  Person '{}' (no email) round-tripped ✓", person2.name);

    // Team with data
    println!("\n--- Team (with members) ---");
    let team = test_data::create_team_with_data();
    let py_team = team.to_python(py)?;
    let team_roundtrip = types::Team::from_python(&py_team.bind(py))?;
    assert_eq!(team, team_roundtrip);
    println!("  Team '{}' ({} members) round-tripped ✓", team.name, team.members.len());

    // Empty team
    println!("\n--- Team (empty) ---");
    let empty_team = test_data::create_empty_team();
    let py_empty_team = empty_team.to_python(py)?;
    let empty_team_roundtrip = types::Team::from_python(&py_empty_team.bind(py))?;
    assert_eq!(empty_team, empty_team_roundtrip);
    println!("  Empty team round-tripped ✓");

    // Configuration (full)
    println!("\n--- Configuration (full) ---");
    let config_full = test_data::create_config_full();
    let py_config_full = config_full.to_python(py)?;
    let config_full_roundtrip = types::Configuration::from_python(&py_config_full.bind(py))?;
    assert_eq!(config_full, config_full_roundtrip);
    println!("  Full configuration round-tripped ✓");

    // Configuration (minimal)
    println!("\n--- Configuration (minimal) ---");
    let config_min = test_data::create_config_minimal();
    let py_config_min = config_min.to_python(py)?;
    let config_min_roundtrip = types::Configuration::from_python(&py_config_min.bind(py))?;
    assert_eq!(config_min, config_min_roundtrip);
    println!("  Minimal configuration round-tripped ✓");

    Ok(())
}

/// Example 5: Edge cases and special values
fn example_edge_cases(py: Python) -> Result<()> {
    println!("\n=== Example 5: Edge Cases ===");

    // Empty collections
    println!("\n--- Empty Collections ---");
    let empty_vec: Vec<i32> = vec![];
    let py_empty_vec = types::primitives::vec_to_python(py, &empty_vec)?;
    let empty_vec_roundtrip: Vec<i32> = py_empty_vec.bind(py).extract()?;
    assert_eq!(empty_vec, empty_vec_roundtrip);
    println!("  Empty Vec<i32> ✓");

    let empty_map: HashMap<String, i32> = HashMap::new();
    let py_empty_map = types::primitives::hashmap_to_python(py, &empty_map)?;
    let empty_map_roundtrip: HashMap<String, i32> = py_empty_map.bind(py).extract()?;
    assert_eq!(empty_map, empty_map_roundtrip);
    println!("  Empty HashMap ✓");

    // Special float values
    println!("\n--- Special Float Values ---");
    let special_floats = test_data::create_special_floats();
    for (i, val) in special_floats.iter().enumerate() {
        let py_val = val.to_object(py);
        let roundtrip: f64 = py_val.extract(py)?;
        if val.is_nan() {
            assert!(roundtrip.is_nan());
            println!("  [{}] NaN ✓", i);
        } else {
            assert_eq!(*val, roundtrip);
            println!("  [{}] {} ✓", i, val);
        }
    }

    // Extreme integers
    println!("\n--- Extreme Integers ---");
    let extreme_ints = test_data::create_extreme_integers();
    for val in extreme_ints {
        let py_val = val.to_object(py);
        let roundtrip: i64 = py_val.extract(py)?;
        assert_eq!(val, roundtrip);
        println!("  {} ✓", val);
    }

    Ok(())
}

fn main() -> Result<()> {
    println!("=================================================");
    println!("PyO3 Type Validation and Testing Examples");
    println!("=================================================");

    Python::with_gil(|py| -> Result<()> {
        example_primitive_types(py)?;
        example_collection_types(py)?;
        example_optional_types(py)?;
        example_struct_types(py)?;
        example_edge_cases(py)?;

        println!("\n=================================================");
        println!("All validation examples completed successfully!");
        println!("=================================================\n");

        Ok(())
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_all_examples() {
        Python::with_gil(|py| {
            example_primitive_types(py).unwrap();
            example_collection_types(py).unwrap();
            example_optional_types(py).unwrap();
            example_struct_types(py).unwrap();
            example_edge_cases(py).unwrap();
        });
    }
}
