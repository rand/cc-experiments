use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

/// Simple struct with primitive fields for testing
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Person {
    pub name: String,
    pub age: i32,
    pub email: Option<String>,
}

impl Person {
    pub fn new(name: String, age: i32, email: Option<String>) -> Self {
        Self { name, age, email }
    }

    pub fn to_python(&self, py: Python) -> PyResult<PyObject> {
        let dict = PyDict::new_bound(py);
        dict.set_item("name", &self.name)?;
        dict.set_item("age", self.age)?;
        dict.set_item("email", &self.email)?;
        Ok(dict.into())
    }

    pub fn from_python(obj: &Bound<'_, PyAny>) -> PyResult<Self> {
        let dict = obj.downcast::<PyDict>()?;
        Ok(Self {
            name: dict.get_item("name")?.unwrap().extract()?,
            age: dict.get_item("age")?.unwrap().extract()?,
            email: dict.get_item("email")?.unwrap().extract()?,
        })
    }
}

/// Struct with collection fields
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Team {
    pub name: String,
    pub members: Vec<String>,
    pub scores: HashMap<String, i32>,
}

impl Team {
    pub fn new(name: String, members: Vec<String>, scores: HashMap<String, i32>) -> Self {
        Self {
            name,
            members,
            scores,
        }
    }

    pub fn to_python(&self, py: Python) -> PyResult<PyObject> {
        let dict = PyDict::new_bound(py);
        dict.set_item("name", &self.name)?;

        let py_members = PyList::new_bound(py, &self.members);
        dict.set_item("members", py_members)?;

        let py_scores = PyDict::new_bound(py);
        for (key, value) in &self.scores {
            py_scores.set_item(key, value)?;
        }
        dict.set_item("scores", py_scores)?;

        Ok(dict.into())
    }

    pub fn from_python(obj: &Bound<'_, PyAny>) -> PyResult<Self> {
        let dict = obj.downcast::<PyDict>()?;
        Ok(Self {
            name: dict.get_item("name")?.unwrap().extract()?,
            members: dict.get_item("members")?.unwrap().extract()?,
            scores: dict.get_item("scores")?.unwrap().extract()?,
        })
    }
}

/// Struct with nested optional fields
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Configuration {
    pub enabled: bool,
    pub timeout_ms: Option<u64>,
    pub tags: Vec<String>,
    pub metadata: Option<HashMap<String, String>>,
}

impl Configuration {
    pub fn to_python(&self, py: Python) -> PyResult<PyObject> {
        let dict = PyDict::new_bound(py);
        dict.set_item("enabled", self.enabled)?;
        dict.set_item("timeout_ms", &self.timeout_ms)?;

        let py_tags = PyList::new_bound(py, &self.tags);
        dict.set_item("tags", py_tags)?;

        dict.set_item("metadata", &self.metadata)?;

        Ok(dict.into())
    }

    pub fn from_python(obj: &Bound<'_, PyAny>) -> PyResult<Self> {
        let dict = obj.downcast::<PyDict>()?;
        Ok(Self {
            enabled: dict.get_item("enabled")?.unwrap().extract()?,
            timeout_ms: dict.get_item("timeout_ms")?.unwrap().extract()?,
            tags: dict.get_item("tags")?.unwrap().extract()?,
            metadata: dict.get_item("metadata")?.unwrap().extract()?,
        })
    }
}

/// Helper functions for testing primitive types
pub mod primitives {
    use pyo3::prelude::*;

    pub fn vec_to_python<T: ToPyObject>(py: Python, vec: &[T]) -> PyResult<PyObject> {
        use pyo3::types::PyList;
        let list = PyList::new_bound(py, vec);
        Ok(list.into())
    }

    pub fn hashmap_to_python<K, V>(
        py: Python,
        map: &std::collections::HashMap<K, V>,
    ) -> PyResult<PyObject>
    where
        K: ToPyObject + std::hash::Hash + Eq,
        V: ToPyObject,
    {
        use pyo3::types::PyDict;
        let dict = PyDict::new_bound(py);
        for (key, value) in map {
            dict.set_item(key, value)?;
        }
        Ok(dict.into())
    }

    pub fn option_to_python<T: ToPyObject>(py: Python, opt: &Option<T>) -> PyResult<PyObject> {
        match opt {
            Some(val) => Ok(val.to_object(py)),
            None => Ok(py.None()),
        }
    }

    pub fn tuple_to_python<T1, T2>(py: Python, tuple: &(T1, T2)) -> PyResult<PyObject>
    where
        T1: ToPyObject,
        T2: ToPyObject,
    {
        use pyo3::types::PyTuple;
        let py_tuple = PyTuple::new_bound(py, &[tuple.0.to_object(py), tuple.1.to_object(py)]);
        Ok(py_tuple.into())
    }
}

/// Edge case test data generators
pub mod test_data {
    use super::*;

    pub fn create_person_with_unicode() -> Person {
        Person::new(
            "张伟 🦀".to_string(),
            30,
            Some("zhang.wei@example.com".to_string()),
        )
    }

    pub fn create_person_without_email() -> Person {
        Person::new("Alice".to_string(), 25, None)
    }

    pub fn create_empty_team() -> Team {
        Team::new("Empty Team".to_string(), vec![], HashMap::new())
    }

    pub fn create_team_with_data() -> Team {
        let mut scores = HashMap::new();
        scores.insert("alice".to_string(), 100);
        scores.insert("bob".to_string(), 95);
        scores.insert("charlie".to_string(), 88);

        Team::new(
            "Dev Team".to_string(),
            vec![
                "alice".to_string(),
                "bob".to_string(),
                "charlie".to_string(),
            ],
            scores,
        )
    }

    pub fn create_config_minimal() -> Configuration {
        Configuration {
            enabled: true,
            timeout_ms: None,
            tags: vec![],
            metadata: None,
        }
    }

    pub fn create_config_full() -> Configuration {
        let mut metadata = HashMap::new();
        metadata.insert("env".to_string(), "production".to_string());
        metadata.insert("region".to_string(), "us-west-2".to_string());

        Configuration {
            enabled: true,
            timeout_ms: Some(5000),
            tags: vec!["critical".to_string(), "monitored".to_string()],
            metadata: Some(metadata),
        }
    }

    pub fn create_special_floats() -> Vec<f64> {
        vec![
            0.0,
            -0.0,
            1.0,
            -1.0,
            f64::INFINITY,
            f64::NEG_INFINITY,
            f64::MAX,
            f64::MIN,
            std::f64::consts::PI,
            std::f64::consts::E,
        ]
    }

    pub fn create_extreme_integers() -> Vec<i64> {
        vec![0, 1, -1, i64::MAX, i64::MIN, 1000000, -1000000]
    }

    pub fn create_unicode_strings() -> Vec<String> {
        vec![
            "".to_string(),
            "ASCII only".to_string(),
            "Hello 世界".to_string(),
            "Emoji: 🦀 🐍 ❤️ 🌍".to_string(),
            "Русский язык".to_string(),
            "العربية".to_string(),
            "🔥 Mixed ASCII 中文 123 🎉".to_string(),
        ]
    }

    pub fn create_nested_vecs() -> Vec<Vec<i32>> {
        vec![
            vec![],
            vec![1],
            vec![1, 2, 3],
            vec![1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
        ]
    }

    pub fn create_optional_vec() -> Vec<Option<i32>> {
        vec![None, Some(1), None, Some(3), Some(4), None]
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_person_creation() {
        let person = Person::new("Alice".to_string(), 30, Some("alice@example.com".to_string()));
        assert_eq!(person.name, "Alice");
        assert_eq!(person.age, 30);
        assert_eq!(person.email, Some("alice@example.com".to_string()));
    }

    #[test]
    fn test_team_creation() {
        let team = test_data::create_team_with_data();
        assert_eq!(team.name, "Dev Team");
        assert_eq!(team.members.len(), 3);
        assert_eq!(team.scores.len(), 3);
    }

    #[test]
    fn test_configuration_creation() {
        let config = test_data::create_config_full();
        assert!(config.enabled);
        assert_eq!(config.timeout_ms, Some(5000));
        assert_eq!(config.tags.len(), 2);
        assert!(config.metadata.is_some());
    }
}
