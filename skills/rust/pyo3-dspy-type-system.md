---
name: pyo3-dspy-type-system
description: Type-safe DSPy from Rust - signature type mapping, field extraction/validation, Pydantic integration with serde
skill_id: rust-pyo3-dspy-type-system
title: PyO3 DSPy Type-Safe Signatures
category: rust
subcategory: pyo3-dspy
complexity: intermediate
prerequisites:
  - rust-pyo3-fundamentals
  - rust-pyo3-dspy-fundamentals
  - ml-dspy-signatures
tags:
  - rust
  - python
  - pyo3
  - dspy
  - types
  - serde
  - pydantic
  - type-safety
version: 1.0.0
last_updated: 2025-10-30
learning_outcomes:
  - Map DSPy signatures to strongly-typed Rust structs
  - Integrate Pydantic models with serde serialization
  - Build custom type converters for complex types
  - Extract typed predictions safely from DSPy
  - Leverage compile-time type checking for runtime safety
  - Generate Rust types automatically from Python signatures
  - Handle validation and type mismatches gracefully
related_skills:
  - rust-pyo3-type-conversion-advanced
  - rust-pyo3-dspy-fundamentals
  - ml-dspy-signatures
  - rust-serde-advanced
resources:
  - REFERENCE.md (800+ lines): Complete type mapping reference
  - 4 Python scripts (1,200+ lines): Code generation, parsing, validation
  - 8 Rust+Python examples (1,500+ lines): Type system patterns
---

# PyO3 DSPy Type-Safe Signatures

## Overview

Build type-safe DSPy integrations by mapping Python signatures to Rust's powerful type system. Learn to convert DSPy field annotations to Rust structs with serde, integrate Pydantic validation, generate code automatically, and catch errors at compile time instead of runtime.

This skill bridges the dynamic Python world with Rust's static guarantees, giving you the best of both: DSPy's ergonomic LLM interfaces with Rust's compile-time safety and performance.

## Prerequisites

**Required**:
- PyO3 fundamentals (FFI, basic type conversions)
- DSPy fundamentals from Rust (module calling, predictions)
- Rust ownership and type system fundamentals
- Serde basics (Serialize, Deserialize)

**Recommended**:
- Pydantic knowledge (models, validation)
- Experience with procedural macros
- JSON schema understanding
- Type-level programming concepts

## When to Use

**Ideal for**:
- **Production DSPy applications** requiring type safety
- **Multi-stage pipelines** where types catch integration bugs
- **API servers** with strict contracts
- **Data validation** before/after LLM calls
- **Code generation workflows** from DSPy signatures
- **Teams mixing Rust and Python** developers

**Not ideal for**:
- Quick prototypes with changing signatures
- Single-use scripts
- When Python dynamic typing is sufficient
- Performance-critical tight loops (overhead from validation)

## Learning Path

### 1. Basic Type Mapping

**Python to Rust type conversions**:

```rust
use pyo3::prelude::*;
use serde::{Deserialize, Serialize};

// Python: question -> answer
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PredictInput {
    pub question: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PredictOutput {
    pub answer: String,
}

// Type-safe prediction extraction
fn extract_prediction(result: &PyAny) -> PyResult<PredictOutput> {
    let answer: String = result.getattr("answer")?.extract()?;
    Ok(PredictOutput { answer })
}

// Example usage
fn main() -> PyResult<()> {
    Python::with_gil(|py| {
        let dspy = PyModule::import(py, "dspy")?;

        // Configure and create predictor
        configure_openai(py)?;
        let predictor = dspy
            .getattr("Predict")?
            .call1((("question -> answer",),))?;

        // Make prediction
        let input = PredictInput {
            question: "What is Rust?".to_string(),
        };

        let result = predictor.call1(((input.question,),))?;

        // Type-safe extraction
        let output = extract_prediction(result)?;

        println!("Answer: {}", output.answer);

        Ok(())
    })
}
```

**Complete type mapping table**:

| Python Type | Rust Type | Notes |
|------------|-----------|-------|
| `str` | `String` | Owned string |
| `int` | `i64` | 64-bit integer |
| `float` | `f64` | 64-bit float |
| `bool` | `bool` | Boolean |
| `List[str]` | `Vec<String>` | Dynamic vector |
| `Dict[str, str]` | `HashMap<String, String>` | Hash map |
| `Optional[str]` | `Option<String>` | Nullable |
| `Tuple[str, int]` | `(String, i64)` | Fixed tuple |
| `Set[str]` | `HashSet<String>` | Hash set |
| `Any` | `serde_json::Value` | Dynamic JSON |

### 2. Complex Signature Mapping

**Multi-field signatures with nested types**:

```rust
use pyo3::prelude::*;
use pyo3::types::PyDict;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

// Python signature:
// "context: str, question: str, examples: List[str] -> answer: str, confidence: float, sources: List[str]"

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RAGInput {
    pub context: String,
    pub question: String,
    pub examples: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RAGOutput {
    pub answer: String,
    pub confidence: f64,
    pub sources: Vec<String>,
}

impl RAGInput {
    /// Convert to PyDict for DSPy
    pub fn to_py_dict(&self, py: Python) -> PyResult<&PyDict> {
        let dict = PyDict::new(py);
        dict.set_item("context", &self.context)?;
        dict.set_item("question", &self.question)?;
        dict.set_item("examples", &self.examples)?;
        Ok(dict)
    }
}

impl RAGOutput {
    /// Extract from DSPy prediction
    pub fn from_prediction(pred: &PyAny) -> PyResult<Self> {
        Ok(Self {
            answer: pred.getattr("answer")?.extract()?,
            confidence: pred.getattr("confidence")?.extract()?,
            sources: pred.getattr("sources")?.extract()?,
        })
    }
}

// Usage
fn call_rag_module(input: RAGInput) -> PyResult<RAGOutput> {
    Python::with_gil(|py| {
        let dspy = PyModule::import(py, "dspy")?;

        let predictor = dspy
            .getattr("ChainOfThought")?
            .call1((("context, question, examples -> answer, confidence, sources",),))?;

        // Convert input to kwargs
        let kwargs = input.to_py_dict(py)?;
        let result = predictor.call((), Some(kwargs))?;

        // Type-safe extraction
        RAGOutput::from_prediction(result)
    })
}
```

### 3. Pydantic Integration

**Using Pydantic models with serde**:

```rust
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyModule as PyMod};
use serde::{Deserialize, Serialize};
use serde_json;

// Define Rust struct matching Pydantic model
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct User {
    pub name: String,
    pub email: String,
    pub age: Option<i32>,
}

// Python Pydantic model
const PYDANTIC_MODEL: &str = r#"
from pydantic import BaseModel, EmailStr
from typing import Optional

class User(BaseModel):
    name: str
    email: EmailStr
    age: Optional[int] = None
"#;

impl User {
    /// Validate using Pydantic and convert to Rust
    pub fn from_json_validated(py: Python, json_str: &str) -> PyResult<Self> {
        // Import Pydantic model
        let module = PyMod::from_code(py, PYDANTIC_MODEL, "", "")?;
        let user_class = module.getattr("User")?;

        // Parse JSON in Python (Pydantic validates)
        let json_module = PyMod::import(py, "json")?;
        let data = json_module
            .getattr("loads")?
            .call1((json_str,))?;

        // Create Pydantic instance (validates)
        let user_obj = user_class.call1((data,))?;

        // Extract to Rust (already validated)
        let name: String = user_obj.getattr("name")?.extract()?;
        let email: String = user_obj.getattr("email")?.extract()?;
        let age: Option<i32> = user_obj.getattr("age")?.extract().ok();

        Ok(User { name, email, age })
    }

    /// Convert to Pydantic dict
    pub fn to_pydantic_dict(&self, py: Python) -> PyResult<&PyDict> {
        let dict = PyDict::new(py);
        dict.set_item("name", &self.name)?;
        dict.set_item("email", &self.email)?;
        if let Some(age) = self.age {
            dict.set_item("age", age)?;
        }
        Ok(dict)
    }
}

// DSPy signature with Pydantic validation
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct UserQueryInput {
    pub query: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct UserQueryOutput {
    pub user_data: User,  // Pydantic-validated
    pub reasoning: String,
}

fn generate_user_from_query(query: &str) -> PyResult<UserQueryOutput> {
    Python::with_gil(|py| {
        let dspy = PyModule::import(py, "dspy")?;

        let predictor = dspy
            .getattr("ChainOfThought")?
            .call1((("query -> user_json, reasoning",),))?;

        let result = predictor.call1(((query,),))?;

        // Extract JSON and validate with Pydantic
        let user_json: String = result.getattr("user_json")?.extract()?;
        let user = User::from_json_validated(py, &user_json)?;

        let reasoning: String = result.getattr("reasoning")?.extract()?;

        Ok(UserQueryOutput {
            user_data: user,
            reasoning,
        })
    })
}
```

### 4. Optional and Default Fields

**Handling optional fields safely**:

```rust
use pyo3::prelude::*;
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FlexibleInput {
    pub required_field: String,
    #[serde(default)]
    pub optional_field: Option<String>,
    #[serde(default = "default_temperature")]
    pub temperature: f32,
}

fn default_temperature() -> f32 {
    0.7
}

impl FlexibleInput {
    /// Safe extraction with defaults
    pub fn from_prediction(pred: &PyAny) -> PyResult<Self> {
        let required_field: String = pred
            .getattr("required_field")?
            .extract()?;

        let optional_field: Option<String> = pred
            .getattr("optional_field")
            .ok()
            .and_then(|attr| attr.extract().ok());

        let temperature: f32 = pred
            .getattr("temperature")
            .ok()
            .and_then(|attr| attr.extract().ok())
            .unwrap_or_else(default_temperature);

        Ok(Self {
            required_field,
            optional_field,
            temperature,
        })
    }
}

// Pattern for safe field extraction
pub trait SafeExtract: Sized {
    fn safe_extract(obj: &PyAny, field: &str) -> PyResult<Self>;
}

impl<T> SafeExtract for Option<T>
where
    T: for<'py> FromPyObject<'py>,
{
    fn safe_extract(obj: &PyAny, field: &str) -> PyResult<Self> {
        match obj.getattr(field) {
            Ok(attr) => Ok(attr.extract().ok()),
            Err(_) => Ok(None),
        }
    }
}

// Usage
fn extract_flexible(pred: &PyAny) -> PyResult<FlexibleInput> {
    Ok(FlexibleInput {
        required_field: pred.getattr("required_field")?.extract()?,
        optional_field: Option::safe_extract(pred, "optional_field")?,
        temperature: pred
            .getattr("temperature")
            .ok()
            .and_then(|a| a.extract().ok())
            .unwrap_or_else(default_temperature),
    })
}
```

### 5. Custom Type Converters

**Building converters for complex types**:

```rust
use pyo3::prelude::*;
use pyo3::types::{PyList, PyDict};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

// Custom type: Document with metadata
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Document {
    pub content: String,
    pub metadata: HashMap<String, String>,
    pub score: f64,
}

impl Document {
    /// Convert from Python dict
    pub fn from_py_dict(dict: &PyDict) -> PyResult<Self> {
        let content: String = dict.get_item("content")
            .ok_or_else(|| PyErr::new::<pyo3::exceptions::PyKeyError, _>("Missing 'content'"))?
            .extract()?;

        let metadata_dict = dict.get_item("metadata")
            .ok_or_else(|| PyErr::new::<pyo3::exceptions::PyKeyError, _>("Missing 'metadata'"))?
            .downcast::<PyDict>()?;

        let mut metadata = HashMap::new();
        for (key, value) in metadata_dict.iter() {
            let k: String = key.extract()?;
            let v: String = value.extract()?;
            metadata.insert(k, v);
        }

        let score: f64 = dict.get_item("score")
            .ok_or_else(|| PyErr::new::<pyo3::exceptions::PyKeyError, _>("Missing 'score'"))?
            .extract()?;

        Ok(Document { content, metadata, score })
    }

    /// Convert to Python dict
    pub fn to_py_dict(&self, py: Python) -> PyResult<&PyDict> {
        let dict = PyDict::new(py);
        dict.set_item("content", &self.content)?;

        let meta_dict = PyDict::new(py);
        for (key, value) in &self.metadata {
            meta_dict.set_item(key, value)?;
        }
        dict.set_item("metadata", meta_dict)?;
        dict.set_item("score", self.score)?;

        Ok(dict)
    }
}

// Signature with custom type
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RetrievalInput {
    pub query: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RetrievalOutput {
    pub documents: Vec<Document>,
    pub answer: String,
}

impl RetrievalOutput {
    pub fn from_prediction(pred: &PyAny) -> PyResult<Self> {
        // Extract documents list
        let docs_list = pred.getattr("documents")?.downcast::<PyList>()?;
        let mut documents = Vec::new();

        for item in docs_list.iter() {
            let doc_dict = item.downcast::<PyDict>()?;
            documents.push(Document::from_py_dict(doc_dict)?);
        }

        let answer: String = pred.getattr("answer")?.extract()?;

        Ok(RetrievalOutput { documents, answer })
    }
}
```

### 6. Compile-Time Type Safety

**Leveraging Rust's type system for safety**:

```rust
use pyo3::prelude::*;
use serde::{Deserialize, Serialize};
use std::marker::PhantomData;

// Type-safe DSPy module wrapper
pub struct TypedPredictor<I, O> {
    predictor: Py<PyAny>,
    _input: PhantomData<I>,
    _output: PhantomData<O>,
}

impl<I, O> TypedPredictor<I, O>
where
    I: Serialize + ToKwargs,
    O: for<'py> FromPrediction<'py>,
{
    pub fn new(py: Python, signature: &str) -> PyResult<Self> {
        let dspy = PyModule::import(py, "dspy")?;
        let predict = dspy.getattr("Predict")?;
        let predictor = predict.call1(((signature,),))?;

        Ok(Self {
            predictor: predictor.into(),
            _input: PhantomData,
            _output: PhantomData,
        })
    }

    pub fn predict(&self, py: Python, input: &I) -> PyResult<O> {
        let kwargs = input.to_kwargs(py)?;
        let result = self.predictor.as_ref(py).call((), Some(kwargs))?;
        O::from_prediction(result)
    }
}

// Trait for converting to kwargs
pub trait ToKwargs {
    fn to_kwargs(&self, py: Python) -> PyResult<&PyDict>;
}

// Trait for extracting from predictions
pub trait FromPrediction<'py>: Sized {
    fn from_prediction(pred: &'py PyAny) -> PyResult<Self>;
}

// Implement for our types
impl ToKwargs for RAGInput {
    fn to_kwargs(&self, py: Python) -> PyResult<&PyDict> {
        self.to_py_dict(py)
    }
}

impl FromPrediction<'_> for RAGOutput {
    fn from_prediction(pred: &PyAny) -> PyResult<Self> {
        Self::from_prediction(pred)
    }
}

// Type-safe usage - compiler ensures type correctness
fn typed_example() -> PyResult<()> {
    Python::with_gil(|py| {
        let predictor: TypedPredictor<RAGInput, RAGOutput> =
            TypedPredictor::new(py, "context, question, examples -> answer, confidence, sources")?;

        let input = RAGInput {
            context: "Rust is a systems language".to_string(),
            question: "What is Rust?".to_string(),
            examples: vec!["Example 1".to_string()],
        };

        // Type-safe prediction - input/output types guaranteed by compiler
        let output: RAGOutput = predictor.predict(py, &input)?;

        println!("Answer: {}", output.answer);
        println!("Confidence: {}", output.confidence);

        Ok(())
    })
}
```

### 7. Error Handling and Validation

**Type-safe error handling for mismatches**:

```rust
use pyo3::prelude::*;
use thiserror::Error;
use serde::{Deserialize, Serialize};

#[derive(Debug, Error)]
pub enum TypeConversionError {
    #[error("Missing required field: {field}")]
    MissingField { field: String },

    #[error("Type mismatch for field {field}: expected {expected}, got {actual}")]
    TypeMismatch {
        field: String,
        expected: String,
        actual: String,
    },

    #[error("Validation failed: {message}")]
    ValidationError { message: String },

    #[error("Python error: {0}")]
    PythonError(#[from] PyErr),
}

pub type TypeResult<T> = Result<T, TypeConversionError>;

// Validated extraction
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ValidatedOutput {
    pub answer: String,
    pub confidence: f64,
}

impl ValidatedOutput {
    pub fn from_prediction_validated(pred: &PyAny) -> TypeResult<Self> {
        // Extract answer
        let answer: String = pred
            .getattr("answer")
            .map_err(|_| TypeConversionError::MissingField {
                field: "answer".to_string(),
            })?
            .extract()
            .map_err(|_| TypeConversionError::TypeMismatch {
                field: "answer".to_string(),
                expected: "String".to_string(),
                actual: "unknown".to_string(),
            })?;

        // Extract and validate confidence
        let confidence: f64 = pred
            .getattr("confidence")
            .map_err(|_| TypeConversionError::MissingField {
                field: "confidence".to_string(),
            })?
            .extract()
            .map_err(|_| TypeConversionError::TypeMismatch {
                field: "confidence".to_string(),
                expected: "f64".to_string(),
                actual: "unknown".to_string(),
            })?;

        // Validate confidence range
        if !(0.0..=1.0).contains(&confidence) {
            return Err(TypeConversionError::ValidationError {
                message: format!("Confidence {} not in range [0, 1]", confidence),
            });
        }

        Ok(Self { answer, confidence })
    }
}

// Generic validated extractor
pub trait ValidatedExtract: Sized {
    fn extract_validated(obj: &PyAny, field: &str) -> TypeResult<Self>;
}

impl ValidatedExtract for String {
    fn extract_validated(obj: &PyAny, field: &str) -> TypeResult<Self> {
        obj.getattr(field)
            .map_err(|_| TypeConversionError::MissingField {
                field: field.to_string(),
            })?
            .extract()
            .map_err(|_| TypeConversionError::TypeMismatch {
                field: field.to_string(),
                expected: "String".to_string(),
                actual: "unknown".to_string(),
            })
    }
}

impl ValidatedExtract for f64 {
    fn extract_validated(obj: &PyAny, field: &str) -> TypeResult<Self> {
        obj.getattr(field)
            .map_err(|_| TypeConversionError::MissingField {
                field: field.to_string(),
            })?
            .extract()
            .map_err(|_| TypeConversionError::TypeMismatch {
                field: field.to_string(),
                expected: "f64".to_string(),
                actual: "unknown".to_string(),
            })
    }
}

// Usage with clean error handling
fn safe_prediction(query: &str) -> TypeResult<ValidatedOutput> {
    Python::with_gil(|py| {
        let dspy = PyModule::import(py, "dspy")?;
        let predictor = dspy
            .getattr("Predict")?
            .call1((("query -> answer, confidence",),))?;

        let result = predictor.call1(((query,),))?;

        ValidatedOutput::from_prediction_validated(result)
    })
}
```

### 8. Automated Code Generation

**Using module_inspector.py for type generation**:

```bash
# Inspect a custom DSPy module
python skills/rust/pyo3-dspy-fundamentals/resources/scripts/module_inspector.py \
    inspect QAModule

# Generate Rust types automatically
python skills/rust/pyo3-dspy-fundamentals/resources/scripts/module_inspector.py \
    codegen QAModule > src/generated_types.rs

# Validate PyO3 compatibility
python skills/rust/pyo3-dspy-fundamentals/resources/scripts/module_inspector.py \
    validate QAModule
```

**Generated code example**:

```python
# custom_module.py
import dspy

class QAWithContext(dspy.Module):
    def __init__(self):
        super().__init__()
        self.generate = dspy.ChainOfThought("context, question -> answer, sources")

    def forward(self, context, question):
        return self.generate(context=context, question=question)
```

**Generated Rust types**:

```rust
// Generated by module_inspector.py
// DO NOT EDIT

use pyo3::prelude::*;
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct QAWithContextInput {
    pub context: String,
    pub question: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct QAWithContextOutput {
    pub answer: String,
    pub sources: Vec<String>,
}

impl QAWithContextInput {
    /// Convert to Python dict for DSPy
    pub fn to_py_dict(&self, py: Python) -> PyResult<Py<PyAny>> {
        let dict = pyo3::types::PyDict::new(py);
        dict.set_item("context", &self.context)?;
        dict.set_item("question", &self.question)?;
        Ok(dict.into())
    }
}

impl QAWithContextOutput {
    /// Extract from Python prediction
    pub fn from_py_prediction(prediction: &PyAny) -> PyResult<Self> {
        Ok(Self {
            answer: prediction.getattr("answer")?.extract()?,
            sources: prediction.getattr("sources")?.extract()?,
        })
    }
}
```

**Integration workflow**:

```rust
// src/main.rs
mod generated_types;
use generated_types::{QAWithContextInput, QAWithContextOutput};

fn main() -> PyResult<()> {
    Python::with_gil(|py| {
        // Load custom module
        let module = PyModule::from_code(
            py,
            include_str!("custom_module.py"),
            "custom_module.py",
            "custom_module",
        )?;

        let qa_class = module.getattr("QAWithContext")?;
        let qa_instance = qa_class.call0()?;

        // Type-safe input
        let input = QAWithContextInput {
            context: "Rust is a systems programming language.".to_string(),
            question: "What is Rust?".to_string(),
        };

        // Call with type safety
        let kwargs = input.to_py_dict(py)?;
        let result = qa_instance.call_method("forward", (), Some(kwargs.as_ref(py)))?;

        // Type-safe output
        let output = QAWithContextOutput::from_py_prediction(result)?;

        println!("Answer: {}", output.answer);
        println!("Sources: {:?}", output.sources);

        Ok(())
    })
}
```

## Resources

### REFERENCE.md

Comprehensive 800+ line guide covering:
- Complete type mapping tables (primitives, collections, custom types)
- Serde integration patterns (serialize, deserialize, custom serializers)
- Pydantic model integration (validation, coercion, error handling)
- Optional and default field handling
- Custom converter implementations
- Code generation workflows
- Type safety patterns and guarantees
- Error handling strategies for type mismatches
- Performance considerations for type conversions
- Testing type conversions
- Migration guide from dynamic to typed

**Load**: `cat skills/rust/pyo3-dspy-type-system/resources/REFERENCE.md`

### Scripts

**1. signature_codegen.py** (~350 lines)
- Parse DSPy signatures and generate Rust struct definitions
- Support for nested types, optional fields, default values
- Generate ToKwargs and FromPrediction trait implementations
- Configurable code generation templates
- Integration with existing Rust projects

**Usage**:
```bash
# Generate from signature string
python resources/scripts/signature_codegen.py generate \
    "context, question -> answer, confidence"

# Generate from Python module file
python resources/scripts/signature_codegen.py from-module \
    custom_module.py QAModule > types.rs

# Generate with custom template
python resources/scripts/signature_codegen.py generate \
    "query -> result" --template custom.j2
```

**2. prediction_parser.py** (~300 lines)
- Safe parsing of DSPy prediction objects
- Type validation and coercion
- Field presence checking
- Error reporting with context
- Integration with Pydantic validation

**Usage**:
```bash
# Parse prediction from JSON
python resources/scripts/prediction_parser.py parse prediction.json

# Validate against schema
python resources/scripts/prediction_parser.py validate \
    prediction.json schema.json

# Extract specific fields
python resources/scripts/prediction_parser.py extract \
    prediction.json answer confidence
```

**3. type_validator.py** (~250 lines)
- Validate type conversions work correctly
- Test round-trip conversions (Rust -> Python -> Rust)
- Generate test cases for type mappings
- Benchmark conversion performance
- Detect type compatibility issues

**Usage**:
```bash
# Validate type mapping
python resources/scripts/type_validator.py validate \
    "List[str]" "Vec<String>"

# Test round-trip conversion
python resources/scripts/type_validator.py roundtrip types.json

# Generate test cases
python resources/scripts/type_validator.py generate-tests \
    types.json > tests.rs
```

**4. pydantic_bridge.py** (~300 lines)
- Bridge Pydantic models to Rust serde types
- Generate serde-compatible types from Pydantic models
- Validate Rust data against Pydantic schemas
- Handle Pydantic validation errors in Rust
- Support for Pydantic v1 and v2

**Usage**:
```bash
# Generate Rust types from Pydantic model
python resources/scripts/pydantic_bridge.py generate \
    models.py User > user.rs

# Validate JSON against Pydantic model
python resources/scripts/pydantic_bridge.py validate \
    models.py User data.json

# Test bidirectional conversion
python resources/scripts/pydantic_bridge.py test \
    models.py User test_data.json
```

### Examples

**1. basic-types/** - Basic type mappings
- Simple signature with primitives
- String, int, float conversions
- Type-safe extraction

**2. optional-fields/** - Optional and default fields
- Handling Option<T> types
- Default value patterns
- Safe extraction with fallbacks

**3. nested-structures/** - Complex nested types
- Lists, dicts, tuples
- Nested struct definitions
- Recursive type handling

**4. pydantic-integration/** - Pydantic + Rust
- Pydantic model validation
- Serde serialization
- Error handling for validation failures

**5. custom-converters/** - Custom type converters
- Building ToKwargs implementations
- FromPrediction trait implementations
- Complex custom types

**6. typed-predictor/** - Compile-time type safety
- Generic typed wrapper
- PhantomData usage
- Type-safe API

**7. code-generation/** - Automated code gen
- Using module_inspector.py
- Integrating generated code
- Build script integration

**8. validation-errors/** - Error handling
- Type mismatch errors
- Missing field errors
- Validation error propagation

## Best Practices

### DO

✅ **Generate types** from Python signatures using tools
✅ **Validate at boundaries** between Rust and Python
✅ **Use Option<T>** for truly optional fields
✅ **Implement Default** for structs with optional fields
✅ **Test round-trip** conversions (Rust -> Python -> Rust)
✅ **Document** type mappings in comments
✅ **Use Pydantic** for complex validation logic
✅ **Leverage serde** for serialization consistency

### DON'T

❌ **Skip validation** assuming Python types are correct
❌ **Use Any/Value** everywhere (defeats purpose of type safety)
❌ **Panic** on type mismatches (return Result instead)
❌ **Forget** to handle missing fields gracefully
❌ **Ignore** Pydantic validation errors
❌ **Hand-write** large type definitions (use code generation)
❌ **Mix** validated and unvalidated extraction patterns

## Common Pitfalls

### 1. Type Mismatch Panics

**Problem**: Extracting without checking type compatibility
```rust
// ❌ Bad: Panics on type mismatch
let answer: String = result.getattr("answer")?.extract()?;
```

**Solution**: Validate types before extraction
```rust
// ✅ Good: Validate type first
let answer_attr = result.getattr("answer")?;
if answer_attr.get_type().name()? != "str" {
    return Err(TypeConversionError::TypeMismatch {
        field: "answer".to_string(),
        expected: "str".to_string(),
        actual: answer_attr.get_type().name()?.to_string(),
    });
}
let answer: String = answer_attr.extract()?;
```

### 2. Missing Optional Field Handling

**Problem**: Not handling optional fields gracefully
```rust
// ❌ Bad: Crashes if field missing
let metadata: String = result.getattr("metadata")?.extract()?;
```

**Solution**: Use Option<T> and safe extraction
```rust
// ✅ Good: Safely handle missing field
let metadata: Option<String> = result
    .getattr("metadata")
    .ok()
    .and_then(|attr| attr.extract().ok());
```

### 3. Ignoring Pydantic Validation

**Problem**: Bypassing Pydantic validation
```rust
// ❌ Bad: Direct extraction skips validation
let email: String = result.getattr("email")?.extract()?;
```

**Solution**: Use Pydantic for validation first
```rust
// ✅ Good: Validate with Pydantic
let email = User::from_json_validated(py, &json_str)?
    .email;  // Already validated as EmailStr
```

## Troubleshooting

### Issue: Type Conversion Fails Silently

**Symptom**: Wrong types extracted without errors

**Solution**: Use explicit type annotations and validation:
```rust
let value: Result<String, _> = obj.extract();
match value {
    Ok(s) => println!("Got string: {}", s),
    Err(e) => eprintln!("Type error: {}", e),
}
```

### Issue: Pydantic Validation Not Running

**Symptom**: Invalid data accepted by Rust

**Solution**: Ensure Pydantic model is used for validation:
```python
# In Python
user = User(**data)  # Validates
user_dict = user.dict()  # Send to Rust
```

### Issue: Generated Code Doesn't Compile

**Symptom**: Code generator produces invalid Rust

**Solutions**:
- Check Python type annotations are valid
- Update code generator templates
- Manually fix generated code as needed
- Report issue to code generator

## Next Steps

**After mastering type system**:
1. **pyo3-dspy-rag-pipelines**: Build typed RAG systems
2. **pyo3-dspy-agents**: Type-safe agent implementations
3. **pyo3-dspy-async-streaming**: Async type-safe predictions
4. **pyo3-dspy-production**: Production type safety patterns
5. **rust-serde-advanced**: Advanced serialization patterns
6. **rust-procedural-macros**: Build custom derive macros for types

## References

- [PyO3 Type Conversions](https://pyo3.rs/latest/conversions/tables.html)
- [Serde Documentation](https://serde.rs/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [DSPy Signatures](https://dspy-docs.vercel.app/docs/building-blocks/signatures)
- [Rust Type System](https://doc.rust-lang.org/book/ch10-00-generics.html)

---

**Version**: 1.0.0
**Last Updated**: 2025-10-30
**Maintainer**: DSPy-PyO3 Integration Team
