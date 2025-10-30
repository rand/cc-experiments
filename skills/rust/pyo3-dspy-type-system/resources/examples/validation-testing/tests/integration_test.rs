use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};
use std::collections::HashMap;

// Import the types module from the main crate
use validation_testing::types::{self, Person, Team, Configuration};
use validation_testing::types::test_data;

/// Helper macro for round-trip testing
macro_rules! assert_roundtrip {
    ($py:expr, $original:expr, $to_py:expr, $from_py:expr) => {{
        let py_obj = $to_py($py, &$original).expect("to_python failed");
        let py_any = py_obj.bind($py);
        let roundtrip = $from_py(py_any).expect("from_python failed");
        assert_eq!(
            $original, roundtrip,
            "Round-trip failed: original != roundtrip"
        );
    }};
}

#[test]
fn test_primitive_roundtrip() {
    Python::with_gil(|py| {
        // Integers
        let ints = vec![0, 1, -1, 42, i32::MAX, i32::MIN];
        for val in ints {
            let py_val = val.to_object(py);
            let roundtrip: i32 = py_val.extract(py).unwrap();
            assert_eq!(val, roundtrip);
        }

        // Floats
        let floats = vec![0.0, 1.0, -1.0, 3.14159, f64::INFINITY, f64::NEG_INFINITY];
        for val in floats {
            let py_val = val.to_object(py);
            let roundtrip: f64 = py_val.extract(py).unwrap();
            assert_eq!(val, roundtrip);
        }

        // NaN special case
        let nan = f64::NAN;
        let py_nan = nan.to_object(py);
        let roundtrip_nan: f64 = py_nan.extract(py).unwrap();
        assert!(roundtrip_nan.is_nan());

        // Booleans
        for val in [true, false] {
            let py_val = val.to_object(py);
            let roundtrip: bool = py_val.extract(py).unwrap();
            assert_eq!(val, roundtrip);
        }

        // Strings
        let strings = vec!["", "ASCII", "Hello 世界", "🦀 Rust"];
        for val in strings {
            let py_val = val.to_object(py);
            let roundtrip: String = py_val.extract(py).unwrap();
            assert_eq!(val, roundtrip);
        }
    });
}

#[test]
fn test_vector_roundtrip() {
    Python::with_gil(|py| {
        // Empty vector
        let empty: Vec<i32> = vec![];
        let py_empty = PyList::new_bound(py, &empty);
        let empty_rt: Vec<i32> = py_empty.extract().unwrap();
        assert_eq!(empty, empty_rt);

        // Single element
        let single = vec![42];
        let py_single = PyList::new_bound(py, &single);
        let single_rt: Vec<i32> = py_single.extract().unwrap();
        assert_eq!(single, single_rt);

        // Multiple elements
        let multi = vec![1, 2, 3, 4, 5];
        let py_multi = PyList::new_bound(py, &multi);
        let multi_rt: Vec<i32> = py_multi.extract().unwrap();
        assert_eq!(multi, multi_rt);

        // Different types
        let strings = vec!["a".to_string(), "b".to_string(), "c".to_string()];
        let py_strings = PyList::new_bound(py, &strings);
        let strings_rt: Vec<String> = py_strings.extract().unwrap();
        assert_eq!(strings, strings_rt);
    });
}

#[test]
fn test_hashmap_roundtrip() {
    Python::with_gil(|py| {
        // Empty HashMap
        let empty: HashMap<String, i32> = HashMap::new();
        let py_empty = PyDict::new_bound(py);
        let empty_rt: HashMap<String, i32> = py_empty.extract().unwrap();
        assert_eq!(empty, empty_rt);

        // HashMap with data
        let mut map = HashMap::new();
        map.insert("one".to_string(), 1);
        map.insert("two".to_string(), 2);
        map.insert("three".to_string(), 3);

        let py_map = PyDict::new_bound(py);
        for (k, v) in &map {
            py_map.set_item(k, v).unwrap();
        }
        let map_rt: HashMap<String, i32> = py_map.extract().unwrap();
        assert_eq!(map, map_rt);

        // HashMap with different value types
        let mut str_map = HashMap::new();
        str_map.insert("key1".to_string(), "value1".to_string());
        str_map.insert("key2".to_string(), "value2".to_string());

        let py_str_map = PyDict::new_bound(py);
        for (k, v) in &str_map {
            py_str_map.set_item(k, v).unwrap();
        }
        let str_map_rt: HashMap<String, String> = py_str_map.extract().unwrap();
        assert_eq!(str_map, str_map_rt);
    });
}

#[test]
fn test_optional_roundtrip() {
    Python::with_gil(|py| {
        // Some value
        let some_val: Option<i32> = Some(42);
        let py_some = types::primitives::option_to_python(py, &some_val).unwrap();
        let some_rt: Option<i32> = py_some.bind(py).extract().unwrap();
        assert_eq!(some_val, some_rt);

        // None value
        let none_val: Option<i32> = None;
        let py_none = types::primitives::option_to_python(py, &none_val).unwrap();
        let none_rt: Option<i32> = py_none.bind(py).extract().unwrap();
        assert_eq!(none_val, none_rt);

        // Option with String
        let some_str: Option<String> = Some("hello".to_string());
        let py_some_str = types::primitives::option_to_python(py, &some_str).unwrap();
        let some_str_rt: Option<String> = py_some_str.bind(py).extract().unwrap();
        assert_eq!(some_str, some_str_rt);

        // Vec with optional elements
        let opt_vec = vec![Some(1), None, Some(3), None, Some(5)];
        let py_opt_vec = types::primitives::vec_to_python(py, &opt_vec).unwrap();
        let opt_vec_rt: Vec<Option<i32>> = py_opt_vec.bind(py).extract().unwrap();
        assert_eq!(opt_vec, opt_vec_rt);
    });
}

#[test]
fn test_person_roundtrip() {
    Python::with_gil(|py| {
        // Person with email
        let person1 = Person::new(
            "Alice".to_string(),
            30,
            Some("alice@example.com".to_string()),
        );
        let py_person1 = person1.to_python(py).unwrap();
        let person1_rt = Person::from_python(&py_person1.bind(py)).unwrap();
        assert_eq!(person1, person1_rt);

        // Person without email
        let person2 = Person::new("Bob".to_string(), 25, None);
        let py_person2 = person2.to_python(py).unwrap();
        let person2_rt = Person::from_python(&py_person2.bind(py)).unwrap();
        assert_eq!(person2, person2_rt);

        // Person with Unicode
        let person3 = test_data::create_person_with_unicode();
        let py_person3 = person3.to_python(py).unwrap();
        let person3_rt = Person::from_python(&py_person3.bind(py)).unwrap();
        assert_eq!(person3, person3_rt);
    });
}

#[test]
fn test_team_roundtrip() {
    Python::with_gil(|py| {
        // Empty team
        let empty_team = test_data::create_empty_team();
        let py_empty = empty_team.to_python(py).unwrap();
        let empty_rt = Team::from_python(&py_empty.bind(py)).unwrap();
        assert_eq!(empty_team, empty_rt);

        // Team with data
        let team = test_data::create_team_with_data();
        let py_team = team.to_python(py).unwrap();
        let team_rt = Team::from_python(&py_team.bind(py)).unwrap();
        assert_eq!(team, team_rt);

        // Verify collections were preserved
        assert_eq!(team.members.len(), team_rt.members.len());
        assert_eq!(team.scores.len(), team_rt.scores.len());
        for member in &team.members {
            assert!(team_rt.members.contains(member));
        }
        for (key, value) in &team.scores {
            assert_eq!(team_rt.scores.get(key), Some(value));
        }
    });
}

#[test]
fn test_configuration_roundtrip() {
    Python::with_gil(|py| {
        // Minimal configuration
        let config_min = test_data::create_config_minimal();
        let py_config_min = config_min.to_python(py).unwrap();
        let config_min_rt = Configuration::from_python(&py_config_min.bind(py)).unwrap();
        assert_eq!(config_min, config_min_rt);

        // Full configuration
        let config_full = test_data::create_config_full();
        let py_config_full = config_full.to_python(py).unwrap();
        let config_full_rt = Configuration::from_python(&py_config_full.bind(py)).unwrap();
        assert_eq!(config_full, config_full_rt);

        // Verify optional fields
        assert_eq!(config_full_rt.timeout_ms, Some(5000));
        assert!(config_full_rt.metadata.is_some());
        assert_eq!(config_min_rt.timeout_ms, None);
        assert_eq!(config_min_rt.metadata, None);
    });
}

#[test]
fn test_nested_collections_roundtrip() {
    Python::with_gil(|py| {
        // Nested vectors
        let nested = test_data::create_nested_vecs();
        let py_nested = types::primitives::vec_to_python(py, &nested).unwrap();
        let nested_rt: Vec<Vec<i32>> = py_nested.bind(py).extract().unwrap();
        assert_eq!(nested, nested_rt);

        // HashMap with Vec values
        let mut map_of_vecs: HashMap<String, Vec<i32>> = HashMap::new();
        map_of_vecs.insert("first".to_string(), vec![1, 2, 3]);
        map_of_vecs.insert("second".to_string(), vec![4, 5, 6]);
        map_of_vecs.insert("empty".to_string(), vec![]);

        let py_map_of_vecs = types::primitives::hashmap_to_python(py, &map_of_vecs).unwrap();
        let map_of_vecs_rt: HashMap<String, Vec<i32>> = py_map_of_vecs.bind(py).extract().unwrap();
        assert_eq!(map_of_vecs, map_of_vecs_rt);
    });
}

#[test]
fn test_unicode_strings() {
    Python::with_gil(|py| {
        let unicode_strings = test_data::create_unicode_strings();
        for original in unicode_strings {
            let py_str = original.to_object(py);
            let roundtrip: String = py_str.extract(py).unwrap();
            assert_eq!(
                original, roundtrip,
                "Unicode string failed: '{}'",
                original
            );
        }
    });
}

#[test]
fn test_special_float_values() {
    Python::with_gil(|py| {
        let special_floats = test_data::create_special_floats();
        for val in special_floats {
            let py_val = val.to_object(py);
            let roundtrip: f64 = py_val.extract(py).unwrap();
            if val.is_nan() {
                assert!(roundtrip.is_nan(), "NaN roundtrip failed");
            } else {
                assert_eq!(val, roundtrip, "Float {} roundtrip failed", val);
            }
        }
    });
}

#[test]
fn test_extreme_integers() {
    Python::with_gil(|py| {
        let extreme_ints = test_data::create_extreme_integers();
        for val in extreme_ints {
            let py_val = val.to_object(py);
            let roundtrip: i64 = py_val.extract(py).unwrap();
            assert_eq!(val, roundtrip, "Integer {} roundtrip failed", val);
        }
    });
}

#[test]
fn test_empty_collections() {
    Python::with_gil(|py| {
        // Empty Vec
        let empty_vec: Vec<i32> = vec![];
        let py_empty_vec = PyList::new_bound(py, &empty_vec);
        let empty_vec_rt: Vec<i32> = py_empty_vec.extract().unwrap();
        assert!(empty_vec_rt.is_empty());

        // Empty HashMap
        let empty_map: HashMap<String, i32> = HashMap::new();
        let py_empty_map = PyDict::new_bound(py);
        let empty_map_rt: HashMap<String, i32> = py_empty_map.extract().unwrap();
        assert!(empty_map_rt.is_empty());

        // Vec of empty Vecs
        let vec_of_empty: Vec<Vec<i32>> = vec![vec![], vec![], vec![]];
        let py_vec_of_empty = types::primitives::vec_to_python(py, &vec_of_empty).unwrap();
        let vec_of_empty_rt: Vec<Vec<i32>> = py_vec_of_empty.bind(py).extract().unwrap();
        assert_eq!(vec_of_empty, vec_of_empty_rt);
        for v in vec_of_empty_rt {
            assert!(v.is_empty());
        }
    });
}

#[test]
fn test_mixed_optional_collections() {
    Python::with_gil(|py| {
        // Vec with mixed Some/None
        let mixed = test_data::create_optional_vec();
        let py_mixed = types::primitives::vec_to_python(py, &mixed).unwrap();
        let mixed_rt: Vec<Option<i32>> = py_mixed.bind(py).extract().unwrap();
        assert_eq!(mixed, mixed_rt);

        // HashMap with optional values
        let mut opt_map: HashMap<String, Option<String>> = HashMap::new();
        opt_map.insert("present".to_string(), Some("value".to_string()));
        opt_map.insert("absent".to_string(), None);

        let py_opt_map = types::primitives::hashmap_to_python(py, &opt_map).unwrap();
        let opt_map_rt: HashMap<String, Option<String>> = py_opt_map.bind(py).extract().unwrap();
        assert_eq!(opt_map, opt_map_rt);
    });
}

/// Performance test: measure round-trip time for various sizes
#[test]
fn test_performance_baseline() {
    use std::time::Instant;

    Python::with_gil(|py| {
        // Small vector
        let small_vec: Vec<i32> = (0..100).collect();
        let start = Instant::now();
        for _ in 0..100 {
            let py_vec = types::primitives::vec_to_python(py, &small_vec).unwrap();
            let _: Vec<i32> = py_vec.extract(py).unwrap();
        }
        let duration = start.elapsed();
        println!("Small vec (100 elements, 100 iterations): {:?}", duration);

        // Large vector
        let large_vec: Vec<i32> = (0..10000).collect();
        let start = Instant::now();
        for _ in 0..10 {
            let py_vec = types::primitives::vec_to_python(py, &large_vec).unwrap();
            let _: Vec<i32> = py_vec.extract(py).unwrap();
        }
        let duration = start.elapsed();
        println!("Large vec (10000 elements, 10 iterations): {:?}", duration);

        // Note: This is just a baseline, not a strict performance requirement
    });
}
