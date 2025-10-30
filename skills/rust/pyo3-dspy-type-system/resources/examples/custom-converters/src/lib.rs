use anyhow::Context;
use chrono::{DateTime, Utc};
use pyo3::exceptions::{PyTypeError, PyValueError};
use pyo3::prelude::*;
use pyo3::types::{PyAnyMethods, PyDict, PyDictMethods, PyList, PyListMethods, PyModuleMethods};
use std::collections::HashMap;

/// Custom trait for converting Rust types to Python dictionaries
pub trait ToPyDict {
    fn to_py_dict(&self, py: Python) -> PyResult<Py<PyDict>>;
}

/// Custom trait for converting Python objects to Rust types
pub trait FromPyAny: Sized {
    fn from_py_any(obj: &Bound<'_, PyAny>) -> PyResult<Self>;
}

/// Document type with metadata and timestamp
#[derive(Debug, Clone)]
pub struct Document {
    pub title: String,
    pub content: String,
    pub source: String,
    pub timestamp: DateTime<Utc>,
    pub metadata: HashMap<String, String>,
}

impl Document {
    pub fn new(
        title: impl Into<String>,
        content: impl Into<String>,
        source: impl Into<String>,
    ) -> Self {
        Self {
            title: title.into(),
            content: content.into(),
            source: source.into(),
            timestamp: Utc::now(),
            metadata: HashMap::new(),
        }
    }

    pub fn with_metadata(mut self, key: impl Into<String>, value: impl Into<String>) -> Self {
        self.metadata.insert(key.into(), value.into());
        self
    }
}

/// Citation type with references to documents
#[derive(Debug, Clone)]
pub struct Citation {
    pub text: String,
    pub documents: Vec<Document>,
    pub citation_style: String,
    pub page_numbers: Option<Vec<u32>>,
}

impl Citation {
    pub fn new(text: impl Into<String>, citation_style: impl Into<String>) -> Self {
        Self {
            text: text.into(),
            documents: Vec::new(),
            citation_style: citation_style.into(),
            page_numbers: None,
        }
    }

    pub fn with_document(mut self, doc: Document) -> Self {
        self.documents.push(doc);
        self
    }

    pub fn with_page_numbers(mut self, pages: Vec<u32>) -> Self {
        self.page_numbers = Some(pages);
        self
    }
}

/// Convert Document to Python dictionary
impl ToPyDict for Document {
    fn to_py_dict(&self, py: Python) -> PyResult<Py<PyDict>> {
        let dict = PyDict::new_bound(py);
        dict.set_item("title", &self.title)?;
        dict.set_item("content", &self.content)?;
        dict.set_item("source", &self.source)?;
        dict.set_item("timestamp", self.timestamp.to_rfc3339())?;

        // Convert metadata HashMap to Python dict
        let metadata_dict = PyDict::new_bound(py);
        for (key, value) in &self.metadata {
            metadata_dict.set_item(key, value)?;
        }
        dict.set_item("metadata", metadata_dict)?;

        Ok(dict.unbind())
    }
}

/// Convert Python dictionary to Document
impl FromPyAny for Document {
    fn from_py_any(obj: &Bound<'_, PyAny>) -> PyResult<Self> {
        let title = obj
            .get_item("title")?
            .extract::<String>()
            .context("Failed to extract 'title' field")
            .map_err(|e| PyErr::new::<PyValueError, _>(e.to_string()))?;

        let content = obj
            .get_item("content")?
            .extract::<String>()
            .context("Failed to extract 'content' field")
            .map_err(|e| PyErr::new::<PyValueError, _>(e.to_string()))?;

        let source = obj
            .get_item("source")?
            .extract::<String>()
            .context("Failed to extract 'source' field")
            .map_err(|e| PyErr::new::<PyValueError, _>(e.to_string()))?;

        // Parse timestamp with custom logic
        let timestamp_obj = obj.get_item("timestamp")?;
        let timestamp = parse_timestamp(&timestamp_obj)?;

        // Parse metadata as HashMap
        let metadata_obj = obj.get_item("metadata")?;
        let metadata = metadata_obj
            .extract::<HashMap<String, String>>()
            .context("Failed to extract 'metadata' field")
            .map_err(|e| PyErr::new::<PyValueError, _>(e.to_string()))?;

        Ok(Document {
            title,
            content,
            source,
            timestamp,
            metadata,
        })
    }
}

/// Convert Citation to Python dictionary
impl ToPyDict for Citation {
    fn to_py_dict(&self, py: Python) -> PyResult<Py<PyDict>> {
        let dict = PyDict::new_bound(py);
        dict.set_item("text", &self.text)?;
        dict.set_item("citation_style", &self.citation_style)?;

        // Convert nested documents
        let docs_list = PyList::empty_bound(py);
        for doc in &self.documents {
            let doc_dict = doc.to_py_dict(py)?;
            docs_list.append(doc_dict)?;
        }
        dict.set_item("documents", docs_list)?;

        // Handle optional page numbers
        if let Some(ref pages) = self.page_numbers {
            dict.set_item("page_numbers", pages.clone())?;
        } else {
            dict.set_item("page_numbers", py.None())?;
        }

        Ok(dict.unbind())
    }
}

/// Convert Python dictionary to Citation
impl FromPyAny for Citation {
    fn from_py_any(obj: &Bound<'_, PyAny>) -> PyResult<Self> {
        let text = obj
            .get_item("text")?
            .extract::<String>()
            .context("Failed to extract 'text' field")
            .map_err(|e| PyErr::new::<PyValueError, _>(e.to_string()))?;

        let citation_style = obj
            .get_item("citation_style")?
            .extract::<String>()
            .context("Failed to extract 'citation_style' field")
            .map_err(|e| PyErr::new::<PyValueError, _>(e.to_string()))?;

        // Parse nested documents
        let docs_obj = obj.get_item("documents")?;
        let docs_list = docs_obj
            .downcast::<PyList>()
            .map_err(|_| PyErr::new::<PyTypeError, _>("'documents' must be a list"))?;

        let mut documents = Vec::new();
        for doc_obj in docs_list.iter() {
            let doc = Document::from_py_any(&doc_obj)?;
            documents.push(doc);
        }

        // Parse optional page numbers
        let page_numbers = if let Ok(pages_obj) = obj.get_item("page_numbers") {
            if !pages_obj.is_none() {
                Some(
                    pages_obj
                        .extract::<Vec<u32>>()
                        .context("Failed to extract 'page_numbers' field")
                        .map_err(|e| PyErr::new::<PyValueError, _>(e.to_string()))?,
                )
            } else {
                None
            }
        } else {
            None
        };

        Ok(Citation {
            text,
            documents,
            citation_style,
            page_numbers,
        })
    }
}

/// Parse timestamp from Python object (string or float)
pub fn parse_timestamp(obj: &Bound<'_, PyAny>) -> PyResult<DateTime<Utc>> {
    // Try parsing as ISO 8601 string
    if let Ok(s) = obj.extract::<String>() {
        return DateTime::parse_from_rfc3339(&s)
            .map(|dt| dt.with_timezone(&Utc))
            .map_err(|e| {
                PyErr::new::<PyValueError, _>(format!("Invalid ISO 8601 timestamp: {}", e))
            });
    }

    // Try parsing as Unix timestamp (float)
    if let Ok(timestamp) = obj.extract::<f64>() {
        let secs = timestamp.trunc() as i64;
        let nsecs = (timestamp.fract() * 1_000_000_000.0) as u32;
        return DateTime::from_timestamp(secs, nsecs).ok_or_else(|| {
            PyErr::new::<PyValueError, _>(format!("Invalid Unix timestamp: {}", timestamp))
        });
    }

    Err(PyErr::new::<PyTypeError, _>(
        "timestamp must be string (ISO 8601) or float (Unix timestamp)",
    ))
}

/// Create a sample document for testing
#[pyfunction]
pub fn create_sample_document(py: Python) -> PyResult<Py<PyDict>> {
    let doc = Document::new(
        "Sample Document",
        "This is a sample document demonstrating custom type conversion in PyO3.",
        "https://example.com/doc1",
    )
    .with_metadata("author", "John Doe")
    .with_metadata("category", "example")
    .with_metadata("language", "en");

    doc.to_py_dict(py)
}

/// Create a citation from a Python document dictionary
#[pyfunction]
pub fn create_citation_from_doc<'py>(
    py: Python<'py>,
    doc_dict: &Bound<'py, PyAny>,
) -> PyResult<Py<PyDict>> {
    let doc = Document::from_py_any(doc_dict)?;

    let citation = Citation::new(
        format!("See {} for more information.", doc.title),
        "APA",
    )
    .with_document(doc)
    .with_page_numbers(vec![42, 43, 44]);

    citation.to_py_dict(py)
}

/// Merge multiple documents into a single document
#[pyfunction]
pub fn merge_documents<'py>(
    py: Python<'py>,
    docs: &Bound<'py, PyList>,
) -> PyResult<Py<PyDict>> {
    let mut rust_docs = Vec::new();
    for doc_obj in docs.iter() {
        let doc = Document::from_py_any(&doc_obj)?;
        rust_docs.push(doc);
    }

    if rust_docs.is_empty() {
        return Err(PyErr::new::<PyValueError, _>(
            "Cannot merge empty document list",
        ));
    }

    let merged_title = rust_docs
        .iter()
        .map(|d| d.title.as_str())
        .collect::<Vec<_>>()
        .join(" + ");

    let merged_content = rust_docs
        .iter()
        .map(|d| d.content.as_str())
        .collect::<Vec<_>>()
        .join("\n\n---\n\n");

    let sources = rust_docs
        .iter()
        .map(|d| d.source.as_str())
        .collect::<Vec<_>>()
        .join(", ");

    let mut merged = Document::new(merged_title, merged_content, sources);

    // Merge all metadata
    for doc in rust_docs {
        merged.metadata.extend(doc.metadata);
    }

    merged.to_py_dict(py)
}

/// Validate citation format
#[pyfunction]
pub fn validate_citation(citation_dict: &Bound<'_, PyAny>) -> PyResult<bool> {
    let citation = Citation::from_py_any(citation_dict)?;

    // Validation rules
    if citation.text.is_empty() {
        return Err(PyErr::new::<PyValueError, _>("Citation text cannot be empty"));
    }

    if citation.documents.is_empty() {
        return Err(PyErr::new::<PyValueError, _>(
            "Citation must reference at least one document",
        ));
    }

    let valid_styles = ["APA", "MLA", "Chicago", "IEEE", "Harvard"];
    if !valid_styles.contains(&citation.citation_style.as_str()) {
        return Err(PyErr::new::<PyValueError, _>(format!(
            "Invalid citation style '{}'. Must be one of: {}",
            citation.citation_style,
            valid_styles.join(", ")
        )));
    }

    Ok(true)
}

/// PyO3 module definition
#[pymodule]
fn custom_converters(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(create_sample_document, m)?)?;
    m.add_function(wrap_pyfunction!(create_citation_from_doc, m)?)?;
    m.add_function(wrap_pyfunction!(merge_documents, m)?)?;
    m.add_function(wrap_pyfunction!(validate_citation, m)?)?;
    Ok(())
}
