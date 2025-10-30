# PyO3 DSPy Type-Safe Signatures - Complete Reference

Comprehensive technical reference for building type-safe DSPy integrations in Rust, covering complete type mappings, Pydantic integration, custom converters, code generation, validation, and production patterns.

## Table of Contents

1. [Type Mapping Reference](#type-mapping-reference)
2. [Signature Extraction](#signature-extraction)
3. [Pydantic Integration](#pydantic-integration)
4. [Custom Type Converters](#custom-type-converters)
5. [Generic Wrappers](#generic-wrappers)
6. [Error Handling](#error-handling)
7. [Code Generation](#code-generation)
8. [Testing Strategies](#testing-strategies)
9. [Best Practices Summary](#best-practices-summary)

---

## Type Mapping Reference

### Primitive Types

**Complete mapping table**:

| Python Type | Rust Type | PyO3 Extract | Notes |
|------------|-----------|--------------|-------|
| `str` | `String` | `extract::<String>()` | Owned UTF-8 string |
| `int` | `i64` | `extract::<i64>()` | 64-bit signed |
| `int` | `i32` | `extract::<i32>()` | 32-bit signed |
| `int` | `usize` | `extract::<usize>()` | Platform-dependent |
| `float` | `f64` | `extract::<f64>()` | 64-bit float |
| `float` | `f32` | `extract::<f32>()` | 32-bit float |
| `bool` | `bool` | `extract::<bool>()` | Boolean |
| `None` | `()` | `extract::<()>()` | Unit type |
| `bytes` | `Vec<u8>` | `extract::<Vec<u8>>()` | Binary data |

**Example: Primitive extraction**:

```rust
use pyo3::prelude::*;

fn extract_primitives(pred: &PyAny) -> PyResult<()> {
    // String
    let text: String = pred.getattr("text")?.extract()?;

    // Integer
    let count: i64 = pred.getattr("count")?.extract()?;

    // Float
    let score: f64 = pred.getattr("score")?.extract()?;

    // Boolean
    let is_valid: bool = pred.getattr("is_valid")?.extract()?;

    println!("text={}, count={}, score={}, valid={}",
             text, count, score, is_valid);

    Ok(())
}
```

### Collection Types

**List/Vec mapping**:

| Python Type | Rust Type | Example |
|------------|-----------|---------|
| `List[str]` | `Vec<String>` | `extract::<Vec<String>>()` |
| `List[int]` | `Vec<i64>` | `extract::<Vec<i64>>()` |
| `List[float]` | `Vec<f64>` | `extract::<Vec<f64>>()` |
| `List[bool]` | `Vec<bool>` | `extract::<Vec<bool>>()` |
| `List[List[str]]` | `Vec<Vec<String>>` | Nested vectors |

**Example: List extraction**:

```rust
use pyo3::prelude::*;
use pyo3::types::PyList;

fn extract_list_safe(pred: &PyAny) -> PyResult<Vec<String>> {
    let sources = pred.getattr("sources")?;

    // Method 1: Direct extraction (simplest)
    let items: Vec<String> = sources.extract()?;

    // Method 2: Manual iteration (more control)
    let py_list = sources.downcast::<PyList>()?;
    let mut result = Vec::new();
    for item in py_list.iter() {
        result.push(item.extract()?);
    }

    Ok(result)
}

// Nested lists
fn extract_nested_list(pred: &PyAny) -> PyResult<Vec<Vec<String>>> {
    let nested: Vec<Vec<String>> = pred.getattr("nested_data")?.extract()?;
    Ok(nested)
}
```

**Dict/HashMap mapping**:

| Python Type | Rust Type | Example |
|------------|-----------|---------|
| `Dict[str, str]` | `HashMap<String, String>` | `extract::<HashMap<_, _>>()` |
| `Dict[str, int]` | `HashMap<String, i64>` | String keys, int values |
| `Dict[str, Any]` | `HashMap<String, Py<PyAny>>` | Heterogeneous values |

**Example: Dict extraction**:

```rust
use pyo3::prelude::*;
use pyo3::types::PyDict;
use std::collections::HashMap;

fn extract_dict(pred: &PyAny) -> PyResult<HashMap<String, String>> {
    // Method 1: Direct extraction
    let metadata: HashMap<String, String> = pred.getattr("metadata")?.extract()?;

    // Method 2: Manual iteration with validation
    let py_dict = pred.getattr("metadata")?.downcast::<PyDict>()?;
    let mut result = HashMap::new();

    for (key, value) in py_dict.iter() {
        let k: String = key.extract()?;
        let v: String = value.extract()?;
        result.insert(k, v);
    }

    Ok(result)
}

// Mixed value types
fn extract_heterogeneous_dict(py: Python, pred: &PyAny) -> PyResult<HashMap<String, Py<PyAny>>> {
    let py_dict = pred.getattr("data")?.downcast::<PyDict>()?;
    let mut result = HashMap::new();

    for (key, value) in py_dict.iter() {
        let k: String = key.extract()?;
        result.insert(k, value.into());
    }

    Ok(result)
}
```

**Tuple mapping**:

| Python Type | Rust Type | Example |
|------------|-----------|---------|
| `Tuple[str, int]` | `(String, i64)` | Fixed-size tuple |
| `Tuple[str, str, float]` | `(String, String, f64)` | Three elements |

**Example: Tuple extraction**:

```rust
use pyo3::prelude::*;

fn extract_tuple(pred: &PyAny) -> PyResult<(String, i64, f64)> {
    // Direct extraction
    let tuple: (String, i64, f64) = pred.getattr("coordinates")?.extract()?;
    Ok(tuple)
}

// Variable-length tuples as Vec
fn extract_var_tuple(pred: &PyAny) -> PyResult<Vec<String>> {
    // Python tuple -> Rust Vec for variable length
    let items: Vec<String> = pred.getattr("items")?.extract()?;
    Ok(items)
}
```

**Set/HashSet mapping**:

```rust
use pyo3::prelude::*;
use std::collections::HashSet;

fn extract_set(pred: &PyAny) -> PyResult<HashSet<String>> {
    let tags: HashSet<String> = pred.getattr("tags")?.extract()?;
    Ok(tags)
}
```

### Optional Types

**Option<T> mapping**:

| Python Type | Rust Type | Handling |
|------------|-----------|----------|
| `Optional[str]` | `Option<String>` | May be None |
| `Optional[int]` | `Option<i64>` | May be None |
| `str \| None` | `Option<String>` | Union syntax |

**Example: Safe optional extraction**:

```rust
use pyo3::prelude::*;

fn extract_optional(pred: &PyAny) -> PyResult<Option<String>> {
    // Method 1: ok() + and_then (recommended)
    let reasoning: Option<String> = pred
        .getattr("reasoning")
        .ok()
        .and_then(|attr| attr.extract().ok());

    Ok(reasoning)
}

// Multiple optional fields
#[derive(Debug)]
struct OptionalFields {
    required: String,
    optional_str: Option<String>,
    optional_int: Option<i64>,
    optional_float: Option<f64>,
}

impl OptionalFields {
    fn from_prediction(pred: &PyAny) -> PyResult<Self> {
        Ok(Self {
            required: pred.getattr("required")?.extract()?,
            optional_str: pred.getattr("optional_str")
                .ok()
                .and_then(|a| a.extract().ok()),
            optional_int: pred.getattr("optional_int")
                .ok()
                .and_then(|a| a.extract().ok()),
            optional_float: pred.getattr("optional_float")
                .ok()
                .and_then(|a| a.extract().ok()),
        })
    }
}
```

**Default values pattern**:

```rust
use pyo3::prelude::*;
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
struct ConfigWithDefaults {
    pub model: String,
    #[serde(default = "default_temperature")]
    pub temperature: f32,
    #[serde(default = "default_max_tokens")]
    pub max_tokens: usize,
    #[serde(default)]
    pub system_prompt: Option<String>,
}

fn default_temperature() -> f32 { 0.7 }
fn default_max_tokens() -> usize { 1000 }

impl ConfigWithDefaults {
    fn from_prediction(pred: &PyAny) -> PyResult<Self> {
        Ok(Self {
            model: pred.getattr("model")?.extract()?,
            temperature: pred.getattr("temperature")
                .ok()
                .and_then(|a| a.extract().ok())
                .unwrap_or_else(default_temperature),
            max_tokens: pred.getattr("max_tokens")
                .ok()
                .and_then(|a| a.extract().ok())
                .unwrap_or_else(default_max_tokens),
            system_prompt: pred.getattr("system_prompt")
                .ok()
                .and_then(|a| a.extract().ok()),
        })
    }
}
```

### Complex Types

**serde_json::Value for dynamic types**:

```rust
use pyo3::prelude::*;
use serde_json::Value;

fn extract_dynamic(pred: &PyAny) -> PyResult<Value> {
    // Convert Python object to JSON
    let json_module = pred.py().import("json")?;
    let json_str: String = json_module
        .getattr("dumps")?
        .call1((pred,))?
        .extract()?;

    let value: Value = serde_json::from_str(&json_str)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(
            format!("JSON parse error: {}", e)
        ))?;

    Ok(value)
}
```

**Type decision tree**:

```
Is field always present?
├─ Yes: Use T
└─ No: Use Option<T>

Is field type known?
├─ Yes: Use specific type (String, i64, etc.)
└─ No: Use serde_json::Value

Is field a collection?
├─ List: Use Vec<T>
├─ Dict: Use HashMap<K, V>
├─ Set: Use HashSet<T>
└─ Tuple: Use (T1, T2, ...)

Does field need validation?
├─ Yes: Use Pydantic
└─ No: Direct extraction
```

---

## Signature Extraction

### Basic Signature Parsing

**DSPy signature format**:
```
"input1, input2, input3 -> output1, output2"
```

**Example: Manual signature parsing**:

```rust
use pyo3::prelude::*;
use pyo3::types::PyDict;

#[derive(Debug)]
struct Signature {
    input_fields: Vec<String>,
    output_fields: Vec<String>,
}

impl Signature {
    fn parse(signature: &str) -> Option<Self> {
        let parts: Vec<&str> = signature.split("->").collect();
        if parts.len() != 2 {
            return None;
        }

        let input_fields = parts[0]
            .split(',')
            .map(|s| s.trim().to_string())
            .collect();

        let output_fields = parts[1]
            .split(',')
            .map(|s| s.trim().to_string())
            .collect();

        Some(Self { input_fields, output_fields })
    }
}

// Usage
fn extract_signature_fields(py: Python, signature: &str) -> PyResult<()> {
    let sig = Signature::parse(signature)
        .ok_or_else(|| PyErr::new::<pyo3::exceptions::PyValueError, _>(
            "Invalid signature format"
        ))?;

    println!("Inputs: {:?}", sig.input_fields);
    println!("Outputs: {:?}", sig.output_fields);

    Ok(())
}
```

### Introspecting DSPy Modules

**Extract signature from module instance**:

```rust
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};

fn inspect_module_signature(py: Python, module: &PyAny) -> PyResult<()> {
    // Get signature attribute
    let signature = module.getattr("signature")?;

    // Extract signature string
    let sig_str: String = signature.to_string();
    println!("Signature: {}", sig_str);

    // Get input fields if available
    if let Ok(input_fields) = signature.getattr("input_fields") {
        let inputs = input_fields.downcast::<PyDict>()?;
        println!("\nInput fields:");
        for (key, value) in inputs.iter() {
            let field_name: String = key.extract()?;
            println!("  - {}", field_name);

            // Try to get type annotation
            if let Ok(annotation) = value.getattr("annotation") {
                let type_str: String = annotation.to_string();
                println!("    Type: {}", type_str);
            }
        }
    }

    // Get output fields
    if let Ok(output_fields) = signature.getattr("output_fields") {
        let outputs = output_fields.downcast::<PyDict>()?;
        println!("\nOutput fields:");
        for (key, _) in outputs.iter() {
            let field_name: String = key.extract()?;
            println!("  - {}", field_name);
        }
    }

    Ok(())
}
```

### Field Type Extraction

**Using module_inspector.py for automated extraction**:

```rust
use pyo3::prelude::*;
use pyo3::types::PyModule as PyMod;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

#[derive(Debug, Deserialize)]
struct FieldInfo {
    name: String,
    python_type: String,
    is_input: bool,
    is_output: bool,
    description: Option<String>,
}

#[derive(Debug, Deserialize)]
struct ModuleFields {
    inputs: Vec<FieldInfo>,
    outputs: Vec<FieldInfo>,
}

fn extract_fields_with_inspector(
    py: Python,
    module_name: &str
) -> PyResult<ModuleFields> {
    // Load module_inspector.py
    let inspector_code = include_str!("../../pyo3-dspy-fundamentals/resources/scripts/module_inspector.py");
    let inspector_module = PyMod::from_code(
        py,
        inspector_code,
        "module_inspector.py",
        "module_inspector"
    )?;

    // Create inspector instance
    let inspector_class = inspector_module.getattr("ModuleInspector")?;
    let inspector = inspector_class.call0()?;

    // Import target module
    let target_module = py.import(module_name)?;

    // Inspect module
    let info = inspector.call_method1("inspect_from_object", (target_module,))?;

    // Extract fields as JSON
    let json_module = py.import("json")?;
    let fields_dict = info.getattr("input_fields")?;
    let json_str: String = json_module
        .getattr("dumps")?
        .call1((fields_dict,))?
        .extract()?;

    // Parse to Rust
    let fields: ModuleFields = serde_json::from_str(&json_str)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(
            format!("JSON parse error: {}", e)
        ))?;

    Ok(fields)
}
```

### Type Annotation Parsing

**Pattern matching for complex types**:

```rust
#[derive(Debug, Clone)]
enum PythonType {
    Str,
    Int,
    Float,
    Bool,
    List(Box<PythonType>),
    Dict(Box<PythonType>, Box<PythonType>),
    Optional(Box<PythonType>),
    Tuple(Vec<PythonType>),
    Any,
}

impl PythonType {
    fn parse(type_str: &str) -> Self {
        let type_str = type_str.trim();

        // Basic types
        match type_str {
            "str" => Self::Str,
            "int" => Self::Int,
            "float" => Self::Float,
            "bool" => Self::Bool,
            "Any" => Self::Any,
            _ => {
                // Complex types
                if type_str.starts_with("Optional[") {
                    let inner = &type_str[9..type_str.len()-1];
                    Self::Optional(Box::new(Self::parse(inner)))
                } else if type_str.starts_with("List[") {
                    let inner = &type_str[5..type_str.len()-1];
                    Self::List(Box::new(Self::parse(inner)))
                } else if type_str.starts_with("Dict[") {
                    let inner = &type_str[5..type_str.len()-1];
                    let parts: Vec<&str> = inner.split(',').collect();
                    if parts.len() == 2 {
                        Self::Dict(
                            Box::new(Self::parse(parts[0].trim())),
                            Box::new(Self::parse(parts[1].trim()))
                        )
                    } else {
                        Self::Any
                    }
                } else {
                    Self::Any
                }
            }
        }
    }

    fn to_rust_type(&self) -> String {
        match self {
            Self::Str => "String".to_string(),
            Self::Int => "i64".to_string(),
            Self::Float => "f64".to_string(),
            Self::Bool => "bool".to_string(),
            Self::List(inner) => format!("Vec<{}>", inner.to_rust_type()),
            Self::Dict(key, val) => {
                format!("HashMap<{}, {}>", key.to_rust_type(), val.to_rust_type())
            }
            Self::Optional(inner) => format!("Option<{}>", inner.to_rust_type()),
            Self::Tuple(types) => {
                let rust_types: Vec<String> = types.iter()
                    .map(|t| t.to_rust_type())
                    .collect();
                format!("({})", rust_types.join(", "))
            }
            Self::Any => "serde_json::Value".to_string(),
        }
    }
}

// Usage
fn demonstrate_type_parsing() {
    let type_str = "Optional[List[str]]";
    let py_type = PythonType::parse(type_str);
    let rust_type = py_type.to_rust_type();
    println!("{} -> {}", type_str, rust_type);
    // Output: Optional[List[str]] -> Option<Vec<String>>
}
```

---

## Pydantic Integration

### Basic Pydantic Validation

**Rust struct with Pydantic validation**:

```rust
use pyo3::prelude::*;
use pyo3::types::PyModule as PyMod;
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
struct User {
    username: String,
    email: String,
    age: i32,
}

const USER_MODEL: &str = r#"
from pydantic import BaseModel, EmailStr, Field

class User(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    age: int = Field(ge=0, le=150)
"#;

impl User {
    fn validate(py: Python, data: &str) -> PyResult<Self> {
        // Import Pydantic model
        let model_module = PyMod::from_code(py, USER_MODEL, "", "")?;
        let user_class = model_module.getattr("User")?;

        // Parse JSON
        let json_module = py.import("json")?;
        let parsed_data = json_module.getattr("loads")?.call1((data,))?;

        // Validate with Pydantic (will raise if invalid)
        let user_obj = user_class.call1((parsed_data,))?;

        // Extract to Rust
        Ok(Self {
            username: user_obj.getattr("username")?.extract()?,
            email: user_obj.getattr("email")?.extract()?,
            age: user_obj.getattr("age")?.extract()?,
        })
    }

    fn to_pydantic_json(&self, py: Python) -> PyResult<String> {
        // Import model
        let model_module = PyMod::from_code(py, USER_MODEL, "", "")?;
        let user_class = model_module.getattr("User")?;

        // Create instance
        let kwargs = pyo3::types::PyDict::new(py);
        kwargs.set_item("username", &self.username)?;
        kwargs.set_item("email", &self.email)?;
        kwargs.set_item("age", self.age)?;

        let user_obj = user_class.call((), Some(kwargs))?;

        // Serialize to JSON
        let json_str: String = user_obj.call_method0("model_dump_json")?.extract()?;

        Ok(json_str)
    }
}
```

### Pydantic with DSPy

**DSPy module returning Pydantic-validated data**:

```python
# dspy_pydantic_module.py
import dspy
from pydantic import BaseModel, Field
from typing import List

class Answer(BaseModel):
    """Structured answer with validation."""
    text: str = Field(min_length=10)
    confidence: float = Field(ge=0.0, le=1.0)
    sources: List[str] = Field(default_factory=list)

class QAWithValidation(dspy.Module):
    def __init__(self):
        super().__init__()
        self.generate = dspy.ChainOfThought("question -> answer_json")

    def forward(self, question: str) -> Answer:
        result = self.generate(question=question)
        # Parse and validate
        answer = Answer.model_validate_json(result.answer_json)
        return answer
```

**Rust integration**:

```rust
use pyo3::prelude::*;
use pyo3::types::PyModule as PyMod;
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
struct Answer {
    text: String,
    confidence: f64,
    sources: Vec<String>,
}

struct QAWithValidation {
    instance: Py<PyAny>,
}

impl QAWithValidation {
    fn new(py: Python) -> PyResult<Self> {
        let code = include_str!("dspy_pydantic_module.py");
        let module = PyMod::from_code(py, code, "dspy_pydantic_module.py", "dspy_pydantic_module")?;

        let class = module.getattr("QAWithValidation")?;
        let instance = class.call0()?;

        Ok(Self {
            instance: instance.into(),
        })
    }

    fn ask(&self, py: Python, question: &str) -> PyResult<Answer> {
        // Call forward method - Pydantic validates in Python
        let result = self.instance.as_ref(py).call_method1("forward", (question,))?;

        // Extract validated data
        Ok(Answer {
            text: result.getattr("text")?.extract()?,
            confidence: result.getattr("confidence")?.extract()?,
            sources: result.getattr("sources")?.extract()?,
        })
    }
}
```

### Validation Error Handling

**Catching and converting Pydantic errors**:

```rust
use pyo3::prelude::*;
use thiserror::Error;

#[derive(Debug, Error)]
enum ValidationError {
    #[error("Pydantic validation failed: {message}")]
    PydanticError { message: String, errors: Vec<String> },

    #[error("Python error: {0}")]
    Python(#[from] PyErr),
}

fn validate_with_pydantic(
    py: Python,
    model_code: &str,
    class_name: &str,
    data_json: &str,
) -> Result<Py<PyAny>, ValidationError> {
    // Import model
    let module = PyModule::from_code(py, model_code, "", "")
        .map_err(|e| ValidationError::Python(e))?;

    let model_class = module.getattr(class_name)
        .map_err(|e| ValidationError::Python(e))?;

    // Parse JSON
    let json_module = py.import("json")
        .map_err(|e| ValidationError::Python(e))?;
    let data = json_module.getattr("loads")?.call1((data_json,))?;

    // Try to validate
    match model_class.call1((data,)) {
        Ok(instance) => Ok(instance.into()),
        Err(e) => {
            // Extract Pydantic validation errors
            let err_str = e.value(py).to_string();

            // Try to get structured errors
            let mut errors = Vec::new();
            if let Ok(pydantic_err) = e.value(py).getattr("errors") {
                if let Ok(err_list) = pydantic_err.call0() {
                    // Parse error list
                    for item in err_list.iter()? {
                        if let Ok(err_dict) = item.downcast::<pyo3::types::PyDict>() {
                            if let Ok(msg) = err_dict.get_item("msg") {
                                errors.push(msg.to_string());
                            }
                        }
                    }
                }
            }

            Err(ValidationError::PydanticError {
                message: err_str,
                errors,
            })
        }
    }
}
```

### Bidirectional Conversion

**Rust ↔ Pydantic round-trip**:

```rust
use pyo3::prelude::*;
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
struct Product {
    name: String,
    price: f64,
    quantity: i32,
}

const PRODUCT_MODEL: &str = r#"
from pydantic import BaseModel, Field

class Product(BaseModel):
    name: str = Field(min_length=1)
    price: float = Field(gt=0)
    quantity: int = Field(ge=0)
"#;

impl Product {
    // Rust -> Pydantic -> JSON
    fn to_validated_json(&self, py: Python) -> PyResult<String> {
        let module = PyModule::from_code(py, PRODUCT_MODEL, "", "")?;
        let product_class = module.getattr("Product")?;

        // Create Pydantic instance (validates)
        let kwargs = pyo3::types::PyDict::new(py);
        kwargs.set_item("name", &self.name)?;
        kwargs.set_item("price", self.price)?;
        kwargs.set_item("quantity", self.quantity)?;

        let instance = product_class.call((), Some(kwargs))?;
        let json: String = instance.call_method0("model_dump_json")?.extract()?;

        Ok(json)
    }

    // JSON -> Pydantic -> Rust
    fn from_validated_json(py: Python, json: &str) -> PyResult<Self> {
        let module = PyModule::from_code(py, PRODUCT_MODEL, "", "")?;
        let product_class = module.getattr("Product")?;

        // Validate with Pydantic
        let instance = product_class.call_method1("model_validate_json", (json,))?;

        // Extract to Rust
        Ok(Self {
            name: instance.getattr("name")?.extract()?,
            price: instance.getattr("price")?.extract()?,
            quantity: instance.getattr("quantity")?.extract()?,
        })
    }

    // Test round-trip
    fn test_roundtrip(&self, py: Python) -> PyResult<bool> {
        let json = self.to_validated_json(py)?;
        let restored = Self::from_validated_json(py, &json)?;

        Ok(self.name == restored.name
            && (self.price - restored.price).abs() < 0.01
            && self.quantity == restored.quantity)
    }
}
```

---

## Custom Type Converters

### ToKwargs Trait

**Generic trait for converting to Python kwargs**:

```rust
use pyo3::prelude::*;
use pyo3::types::PyDict;

pub trait ToKwargs {
    fn to_kwargs(&self, py: Python) -> PyResult<&PyDict>;
}

// Example implementation
#[derive(Debug, Clone)]
struct QueryInput {
    question: String,
    context: Option<String>,
    max_tokens: usize,
}

impl ToKwargs for QueryInput {
    fn to_kwargs(&self, py: Python) -> PyResult<&PyDict> {
        let dict = PyDict::new(py);

        dict.set_item("question", &self.question)?;

        if let Some(ref ctx) = self.context {
            dict.set_item("context", ctx)?;
        }

        dict.set_item("max_tokens", self.max_tokens)?;

        Ok(dict)
    }
}
```

### FromPrediction Trait

**Generic trait for extracting from predictions**:

```rust
use pyo3::prelude::*;

pub trait FromPrediction: Sized {
    fn from_prediction(pred: &PyAny) -> PyResult<Self>;
}

// Example implementation
#[derive(Debug, Clone)]
struct QueryOutput {
    answer: String,
    reasoning: Option<String>,
    confidence: f64,
}

impl FromPrediction for QueryOutput {
    fn from_prediction(pred: &PyAny) -> PyResult<Self> {
        Ok(Self {
            answer: pred.getattr("answer")?.extract()?,
            reasoning: pred.getattr("reasoning")
                .ok()
                .and_then(|r| r.extract().ok()),
            confidence: pred.getattr("confidence")
                .ok()
                .and_then(|c| c.extract().ok())
                .unwrap_or(0.0),
        })
    }
}
```

### Complex Document Type

**Custom converter for document with metadata**:

```rust
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Document {
    pub id: String,
    pub content: String,
    pub metadata: HashMap<String, String>,
    pub embedding: Option<Vec<f32>>,
    pub score: f64,
}

impl ToKwargs for Document {
    fn to_kwargs(&self, py: Python) -> PyResult<&PyDict> {
        let dict = PyDict::new(py);

        dict.set_item("id", &self.id)?;
        dict.set_item("content", &self.content)?;

        // Convert metadata
        let meta_dict = PyDict::new(py);
        for (k, v) in &self.metadata {
            meta_dict.set_item(k, v)?;
        }
        dict.set_item("metadata", meta_dict)?;

        // Convert embedding if present
        if let Some(ref emb) = self.embedding {
            dict.set_item("embedding", emb)?;
        }

        dict.set_item("score", self.score)?;

        Ok(dict)
    }
}

impl FromPrediction for Document {
    fn from_prediction(pred: &PyAny) -> PyResult<Self> {
        // Extract required fields
        let id: String = pred.getattr("id")?.extract()?;
        let content: String = pred.getattr("content")?.extract()?;
        let score: f64 = pred.getattr("score")?.extract()?;

        // Extract metadata dict
        let meta_dict = pred.getattr("metadata")?.downcast::<PyDict>()?;
        let mut metadata = HashMap::new();
        for (k, v) in meta_dict.iter() {
            metadata.insert(k.extract()?, v.extract()?);
        }

        // Extract optional embedding
        let embedding: Option<Vec<f32>> = pred.getattr("embedding")
            .ok()
            .and_then(|e| e.extract().ok());

        Ok(Self {
            id,
            content,
            metadata,
            embedding,
            score,
        })
    }
}

// Convert list of documents
impl Document {
    pub fn vec_from_prediction(pred: &PyAny, field: &str) -> PyResult<Vec<Self>> {
        let docs_list = pred.getattr(field)?.downcast::<PyList>()?;
        let mut result = Vec::new();

        for item in docs_list.iter() {
            result.push(Self::from_prediction(item)?);
        }

        Ok(result)
    }

    pub fn vec_to_kwargs(docs: &[Self], py: Python) -> PyResult<Py<PyAny>> {
        let list = PyList::empty(py);

        for doc in docs {
            let dict = doc.to_kwargs(py)?;
            list.append(dict)?;
        }

        Ok(list.into())
    }
}
```

### Enum Converters

**Converting between Rust enums and Python strings**:

```rust
use pyo3::prelude::*;
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Copy, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum ModelProvider {
    OpenAI,
    Anthropic,
    Cohere,
    Together,
}

impl ModelProvider {
    pub fn to_py_str(&self) -> &str {
        match self {
            Self::OpenAI => "openai",
            Self::Anthropic => "anthropic",
            Self::Cohere => "cohere",
            Self::Together => "together",
        }
    }

    pub fn from_py_str(s: &str) -> Option<Self> {
        match s.to_lowercase().as_str() {
            "openai" => Some(Self::OpenAI),
            "anthropic" => Some(Self::Anthropic),
            "cohere" => Some(Self::Cohere),
            "together" => Some(Self::Together),
            _ => None,
        }
    }
}

impl ToPyObject for ModelProvider {
    fn to_object(&self, py: Python) -> PyObject {
        self.to_py_str().to_object(py)
    }
}

impl<'source> FromPyObject<'source> for ModelProvider {
    fn extract(ob: &'source PyAny) -> PyResult<Self> {
        let s: String = ob.extract()?;
        Self::from_py_str(&s)
            .ok_or_else(|| PyErr::new::<pyo3::exceptions::PyValueError, _>(
                format!("Invalid provider: {}", s)
            ))
    }
}
```

---

## Generic Wrappers

### TypedPredictor

**Generic type-safe predictor wrapper**:

```rust
use pyo3::prelude::*;
use std::marker::PhantomData;

pub struct TypedPredictor<I, O> {
    predictor: Py<PyAny>,
    signature: String,
    _input: PhantomData<I>,
    _output: PhantomData<O>,
}

impl<I, O> TypedPredictor<I, O>
where
    I: ToKwargs,
    O: FromPrediction,
{
    pub fn new(py: Python, module_type: &str, signature: &str) -> PyResult<Self> {
        let dspy = PyModule::import(py, "dspy")?;
        let predictor_class = dspy.getattr(module_type)?;
        let predictor = predictor_class.call1(((signature,),))?;

        Ok(Self {
            predictor: predictor.into(),
            signature: signature.to_string(),
            _input: PhantomData,
            _output: PhantomData,
        })
    }

    pub fn predict(&self, py: Python, input: &I) -> PyResult<O> {
        let kwargs = input.to_kwargs(py)?;
        let result = self.predictor.as_ref(py).call((), Some(kwargs))?;
        O::from_prediction(result)
    }

    pub fn signature(&self) -> &str {
        &self.signature
    }
}

// Example usage
fn typed_predictor_example() -> PyResult<()> {
    Python::with_gil(|py| {
        // Create typed predictor
        let predictor: TypedPredictor<QueryInput, QueryOutput> =
            TypedPredictor::new(
                py,
                "ChainOfThought",
                "question, context -> answer, reasoning, confidence"
            )?;

        // Type-safe prediction
        let input = QueryInput {
            question: "What is Rust?".to_string(),
            context: Some("Rust is a systems language".to_string()),
            max_tokens: 1000,
        };

        let output: QueryOutput = predictor.predict(py, &input)?;

        println!("Answer: {}", output.answer);
        if let Some(reasoning) = output.reasoning {
            println!("Reasoning: {}", reasoning);
        }
        println!("Confidence: {}", output.confidence);

        Ok(())
    })
}
```

### TypedModule

**Generic wrapper for custom DSPy modules**:

```rust
use pyo3::prelude::*;
use std::marker::PhantomData;

pub struct TypedModule<I, O> {
    instance: Py<PyAny>,
    _input: PhantomData<I>,
    _output: PhantomData<O>,
}

impl<I, O> TypedModule<I, O>
where
    I: ToKwargs,
    O: FromPrediction,
{
    pub fn from_python_code(
        py: Python,
        code: &str,
        class_name: &str,
    ) -> PyResult<Self> {
        let module = PyModule::from_code(py, code, "module.py", "module")?;
        let class = module.getattr(class_name)?;
        let instance = class.call0()?;

        Ok(Self {
            instance: instance.into(),
            _input: PhantomData,
            _output: PhantomData,
        })
    }

    pub fn from_file(
        py: Python,
        path: &str,
        class_name: &str,
    ) -> PyResult<Self> {
        let code = std::fs::read_to_string(path)?;
        Self::from_python_code(py, &code, class_name)
    }

    pub fn forward(&self, py: Python, input: &I) -> PyResult<O> {
        let kwargs = input.to_kwargs(py)?;
        let result = self.instance.as_ref(py).call_method("forward", (), Some(kwargs))?;
        O::from_prediction(result)
    }

    pub fn __call__(&self, py: Python, input: &I) -> PyResult<O> {
        self.forward(py, input)
    }
}

// Example usage
const QA_MODULE: &str = r#"
import dspy

class QAModule(dspy.Module):
    def __init__(self):
        super().__init__()
        self.generate = dspy.ChainOfThought("question, context -> answer, confidence")

    def forward(self, question, context):
        return self.generate(question=question, context=context)
"#;

fn typed_module_example() -> PyResult<()> {
    Python::with_gil(|py| {
        let module: TypedModule<QueryInput, QueryOutput> =
            TypedModule::from_python_code(py, QA_MODULE, "QAModule")?;

        let input = QueryInput {
            question: "What is DSPy?".to_string(),
            context: Some("DSPy is a framework".to_string()),
            max_tokens: 500,
        };

        let output = module.forward(py, &input)?;
        println!("Answer: {}", output.answer);

        Ok(())
    })
}
```

### Builder Pattern

**Type-safe builder for predictors**:

```rust
use pyo3::prelude::*;

pub struct PredictorBuilder<I, O> {
    module_type: String,
    signature: String,
    _marker: PhantomData<(I, O)>,
}

impl<I, O> PredictorBuilder<I, O> {
    pub fn new(signature: &str) -> Self {
        Self {
            module_type: "Predict".to_string(),
            signature: signature.to_string(),
            _marker: PhantomData,
        }
    }

    pub fn with_chain_of_thought(mut self) -> Self {
        self.module_type = "ChainOfThought".to_string();
        self
    }

    pub fn with_program_of_thought(mut self) -> Self {
        self.module_type = "ProgramOfThought".to_string();
        self
    }

    pub fn with_react(mut self) -> Self {
        self.module_type = "ReAct".to_string();
        self
    }

    pub fn build(self, py: Python) -> PyResult<TypedPredictor<I, O>>
    where
        I: ToKwargs,
        O: FromPrediction,
    {
        TypedPredictor::new(py, &self.module_type, &self.signature)
    }
}

// Usage
fn builder_example() -> PyResult<()> {
    Python::with_gil(|py| {
        let predictor = PredictorBuilder::<QueryInput, QueryOutput>::new(
            "question -> answer, confidence"
        )
        .with_chain_of_thought()
        .build(py)?;

        // Use predictor...
        Ok(())
    })
}
```

---

## Error Handling

### Comprehensive Error Types

```rust
use pyo3::prelude::*;
use thiserror::Error;

#[derive(Debug, Error)]
pub enum TypeConversionError {
    #[error("Missing required field: {field}")]
    MissingField {
        field: String,
    },

    #[error("Type mismatch for field '{field}': expected {expected}, got {actual}")]
    TypeMismatch {
        field: String,
        expected: String,
        actual: String,
    },

    #[error("Validation failed for field '{field}': {message}")]
    ValidationFailed {
        field: String,
        message: String,
    },

    #[error("List extraction failed: {0}")]
    ListError(String),

    #[error("Dict extraction failed: {0}")]
    DictError(String),

    #[error("Pydantic validation error: {0}")]
    PydanticError(String),

    #[error("Python runtime error: {0}")]
    PythonError(#[from] PyErr),

    #[error("JSON serialization error: {0}")]
    JsonError(#[from] serde_json::Error),

    #[error("IO error: {0}")]
    IoError(#[from] std::io::Error),
}

pub type Result<T> = std::result::Result<T, TypeConversionError>;
```

### Validated Extraction

**Safe extraction with detailed errors**:

```rust
pub trait ValidatedExtract: Sized {
    fn extract_validated(obj: &PyAny, field: &str) -> Result<Self>;
}

impl ValidatedExtract for String {
    fn extract_validated(obj: &PyAny, field: &str) -> Result<Self> {
        let attr = obj.getattr(field)
            .map_err(|_| TypeConversionError::MissingField {
                field: field.to_string(),
            })?;

        // Check type
        let type_name = attr.get_type().name()
            .map_err(|e| TypeConversionError::PythonError(e))?;

        if type_name != "str" {
            return Err(TypeConversionError::TypeMismatch {
                field: field.to_string(),
                expected: "str".to_string(),
                actual: type_name.to_string(),
            });
        }

        attr.extract()
            .map_err(|e| TypeConversionError::PythonError(e))
    }
}

impl ValidatedExtract for f64 {
    fn extract_validated(obj: &PyAny, field: &str) -> Result<Self> {
        let attr = obj.getattr(field)
            .map_err(|_| TypeConversionError::MissingField {
                field: field.to_string(),
            })?;

        attr.extract()
            .map_err(|_| TypeConversionError::TypeMismatch {
                field: field.to_string(),
                expected: "float".to_string(),
                actual: attr.get_type().name().unwrap_or("unknown").to_string(),
            })
    }
}

impl<T: ValidatedExtract> ValidatedExtract for Option<T> {
    fn extract_validated(obj: &PyAny, field: &str) -> Result<Self> {
        match T::extract_validated(obj, field) {
            Ok(val) => Ok(Some(val)),
            Err(TypeConversionError::MissingField { .. }) => Ok(None),
            Err(e) => Err(e),
        }
    }
}

impl<T: ValidatedExtract> ValidatedExtract for Vec<T> {
    fn extract_validated(obj: &PyAny, field: &str) -> Result<Self> {
        let attr = obj.getattr(field)
            .map_err(|_| TypeConversionError::MissingField {
                field: field.to_string(),
            })?;

        let list = attr.downcast::<pyo3::types::PyList>()
            .map_err(|_| TypeConversionError::TypeMismatch {
                field: field.to_string(),
                expected: "list".to_string(),
                actual: attr.get_type().name().unwrap_or("unknown").to_string(),
            })?;

        let mut result = Vec::new();
        for (i, item) in list.iter().enumerate() {
            // Create synthetic field name for error reporting
            let item_field = format!("{}[{}]", field, i);
            // We can't use ValidatedExtract directly on items, so use extract
            let val: T = item.extract()
                .map_err(|e| TypeConversionError::ListError(
                    format!("{}: {}", item_field, e)
                ))?;
            result.push(val);
        }

        Ok(result)
    }
}
```

### Error Recovery

**Strategies for handling type errors**:

```rust
pub struct ExtractionStrategy;

impl ExtractionStrategy {
    /// Try multiple extraction strategies in order
    pub fn try_extract_string(obj: &PyAny, field: &str) -> Result<String> {
        // Strategy 1: Direct extraction
        if let Ok(s) = String::extract_validated(obj, field) {
            return Ok(s);
        }

        // Strategy 2: Try to_string()
        if let Ok(attr) = obj.getattr(field) {
            if let Ok(s) = attr.str() {
                return Ok(s.to_string());
            }
        }

        // Strategy 3: Check if it's bytes and decode
        if let Ok(attr) = obj.getattr(field) {
            if let Ok(bytes) = attr.extract::<Vec<u8>>() {
                if let Ok(s) = String::from_utf8(bytes) {
                    return Ok(s);
                }
            }
        }

        Err(TypeConversionError::TypeMismatch {
            field: field.to_string(),
            expected: "str".to_string(),
            actual: "unknown".to_string(),
        })
    }

    /// Extract with default fallback
    pub fn extract_or_default<T>(obj: &PyAny, field: &str, default: T) -> T
    where
        T: for<'a> FromPyObject<'a>,
    {
        obj.getattr(field)
            .ok()
            .and_then(|attr| attr.extract().ok())
            .unwrap_or(default)
    }

    /// Extract with type coercion
    pub fn extract_coerced_f64(obj: &PyAny, field: &str) -> Result<f64> {
        let attr = obj.getattr(field)
            .map_err(|_| TypeConversionError::MissingField {
                field: field.to_string(),
            })?;

        // Try direct extraction
        if let Ok(f) = attr.extract::<f64>() {
            return Ok(f);
        }

        // Try from int
        if let Ok(i) = attr.extract::<i64>() {
            return Ok(i as f64);
        }

        // Try from string
        if let Ok(s) = attr.extract::<String>() {
            if let Ok(f) = s.parse::<f64>() {
                return Ok(f);
            }
        }

        Err(TypeConversionError::TypeMismatch {
            field: field.to_string(),
            expected: "float".to_string(),
            actual: "incompatible type".to_string(),
        })
    }
}
```

---

## Code Generation

### Automated Rust Type Generation

**Using module_inspector.py**:

```bash
# Generate types from signature
python module_inspector.py codegen \
    --source custom_module.py \
    QAModule > generated_types.rs

# Output:
# generated_types.rs with Input/Output structs
```

**Generated code template**:

```rust
// Generated by module_inspector.py
// DO NOT EDIT

use pyo3::prelude::*;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct QAModuleInput {
    pub question: String,
    pub context: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct QAModuleOutput {
    pub answer: String,
    pub confidence: f64,
    pub sources: Vec<String>,
}

impl QAModuleInput {
    pub fn to_py_dict(&self, py: Python) -> PyResult<Py<PyAny>> {
        let dict = pyo3::types::PyDict::new(py);
        dict.set_item("question", &self.question)?;
        dict.set_item("context", &self.context)?;
        Ok(dict.into())
    }
}

impl QAModuleOutput {
    pub fn from_py_prediction(prediction: &PyAny) -> PyResult<Self> {
        Ok(Self {
            answer: prediction.getattr("answer")?.extract()?,
            confidence: prediction.getattr("confidence")?.extract()?,
            sources: prediction.getattr("sources")?.extract()?,
        })
    }
}
```

### Build Script Integration

**Cargo build.rs for automatic generation**:

```rust
// build.rs
use std::process::Command;
use std::path::Path;

fn main() {
    let module_path = "python/dspy_modules.py";
    let output_path = "src/generated/mod.rs";

    // Only regenerate if source changed
    println!("cargo:rerun-if-changed={}", module_path);

    // Run code generator
    let output = Command::new("python")
        .arg("scripts/module_inspector.py")
        .arg("codegen")
        .arg("--source")
        .arg(module_path)
        .arg("QAModule")
        .output()
        .expect("Failed to run code generator");

    if !output.status.success() {
        panic!("Code generation failed: {}",
               String::from_utf8_lossy(&output.stderr));
    }

    // Write generated code
    std::fs::create_dir_all("src/generated")
        .expect("Failed to create generated directory");

    std::fs::write(output_path, output.stdout)
        .expect("Failed to write generated code");

    println!("Generated types written to {}", output_path);
}
```

### Template-Based Generation

**Custom code generation templates**:

```rust
// Simple template engine
fn generate_struct(name: &str, fields: &[(String, String)]) -> String {
    let mut code = String::new();

    code.push_str(&format!("#[derive(Debug, Clone, Serialize, Deserialize)]\n"));
    code.push_str(&format!("pub struct {} {{\n", name));

    for (field_name, field_type) in fields {
        code.push_str(&format!("    pub {}: {},\n", field_name, field_type));
    }

    code.push_str("}\n");
    code
}

// Usage
fn generate_types_example() {
    let input_fields = vec![
        ("question".to_string(), "String".to_string()),
        ("context".to_string(), "String".to_string()),
    ];

    let input_struct = generate_struct("QueryInput", &input_fields);
    println!("{}", input_struct);
}
```

---

## Testing Strategies

### Unit Tests for Type Conversions

```rust
#[cfg(test)]
mod tests {
    use super::*;
    use pyo3::types::PyDict;

    #[test]
    fn test_string_extraction() {
        Python::with_gil(|py| {
            let dict = PyDict::new(py);
            dict.set_item("text", "Hello").unwrap();

            let text: String = dict.get_item("text")
                .unwrap()
                .extract()
                .unwrap();

            assert_eq!(text, "Hello");
        });
    }

    #[test]
    fn test_optional_extraction() {
        Python::with_gil(|py| {
            let dict = PyDict::new(py);
            dict.set_item("present", "value").unwrap();

            let present: Option<String> = dict.get_item("present")
                .ok()
                .and_then(|v| v.extract().ok());

            let missing: Option<String> = dict.get_item("missing")
                .ok()
                .and_then(|v| v.extract().ok());

            assert_eq!(present, Some("value".to_string()));
            assert_eq!(missing, None);
        });
    }

    #[test]
    fn test_list_extraction() {
        Python::with_gil(|py| {
            let dict = PyDict::new(py);
            let list = pyo3::types::PyList::new(py, &["a", "b", "c"]);
            dict.set_item("items", list).unwrap();

            let items: Vec<String> = dict.get_item("items")
                .unwrap()
                .extract()
                .unwrap();

            assert_eq!(items, vec!["a", "b", "c"]);
        });
    }

    #[test]
    fn test_nested_extraction() {
        Python::with_gil(|py| {
            let dict = PyDict::new(py);

            let nested_dict = PyDict::new(py);
            nested_dict.set_item("key", "value").unwrap();

            dict.set_item("nested", nested_dict).unwrap();

            let nested: HashMap<String, String> = dict
                .get_item("nested")
                .unwrap()
                .extract()
                .unwrap();

            assert_eq!(nested.get("key"), Some(&"value".to_string()));
        });
    }
}
```

### Integration Tests with DSPy

```rust
#[cfg(test)]
mod integration_tests {
    use super::*;

    #[test]
    fn test_dspy_prediction_extraction() {
        Python::with_gil(|py| {
            // Setup DSPy
            let dspy = PyModule::import(py, "dspy").unwrap();

            // Create predictor
            let predictor = dspy
                .getattr("Predict").unwrap()
                .call1((("question -> answer",),)).unwrap();

            // Mock prediction (in real test, would call LM)
            // For testing, create a mock result
            let result_dict = PyDict::new(py);
            result_dict.set_item("answer", "Test answer").unwrap();

            // Extract
            let output = PredictOutput::from_prediction(result_dict.as_ref()).unwrap();

            assert_eq!(output.answer, "Test answer");
        });
    }
}
```

### Property-Based Tests

```rust
#[cfg(test)]
mod property_tests {
    use super::*;
    use quickcheck::{Arbitrary, Gen, QuickCheck};
    use quickcheck_macros::quickcheck;

    #[quickcheck]
    fn test_roundtrip_string(s: String) -> bool {
        Python::with_gil(|py| {
            let dict = PyDict::new(py);
            dict.set_item("value", &s).unwrap();

            let extracted: String = dict.get_item("value")
                .unwrap()
                .extract()
                .unwrap();

            extracted == s
        })
    }

    #[quickcheck]
    fn test_roundtrip_vec(v: Vec<i64>) -> bool {
        Python::with_gil(|py| {
            let dict = PyDict::new(py);
            dict.set_item("values", &v).unwrap();

            let extracted: Vec<i64> = dict.get_item("values")
                .unwrap()
                .extract()
                .unwrap();

            extracted == v
        })
    }
}
```

---

## Best Practices Summary

### Type Safety

**DO**:
- ✅ Use explicit type annotations everywhere
- ✅ Leverage compile-time type checking with generics
- ✅ Validate types at Python/Rust boundary
- ✅ Use Option<T> for truly optional fields
- ✅ Generate types from Python signatures
- ✅ Test type conversions thoroughly

**DON'T**:
- ❌ Use `Any` or `Value` unless absolutely necessary
- ❌ Skip validation assuming Python types are correct
- ❌ Panic on type mismatches (return Result)
- ❌ Hand-write large type definitions (use code generation)
- ❌ Ignore type hints in Python code

### Pydantic Integration

**DO**:
- ✅ Use Pydantic for complex validation logic
- ✅ Validate at entry points (API boundaries)
- ✅ Cache Pydantic model definitions
- ✅ Handle validation errors gracefully
- ✅ Use Pydantic for JSON schema validation

**DON'T**:
- ❌ Bypass Pydantic validation
- ❌ Ignore validation error details
- ❌ Mix validated and unvalidated data
- ❌ Recreate model classes repeatedly

### Error Handling

**DO**:
- ✅ Define custom error types with thiserror
- ✅ Provide context in error messages
- ✅ Handle specific error cases explicitly
- ✅ Return Result<T, E> from all fallible functions
- ✅ Log errors with structured logging

**DON'T**:
- ❌ Use unwrap() in production code
- ❌ Swallow errors silently
- ❌ Use panic! for recoverable errors
- ❌ Return generic error messages

### Code Generation

**DO**:
- ✅ Generate types from authoritative source (Python)
- ✅ Integrate generation into build process
- ✅ Mark generated code as "DO NOT EDIT"
- ✅ Version control generator scripts
- ✅ Validate generated code compiles

**DON'T**:
- ❌ Edit generated code manually
- ❌ Check in generated code (unless necessary)
- ❌ Use outdated generator versions
- ❌ Generate code without validation

### Testing

**DO**:
- ✅ Test all type conversions with unit tests
- ✅ Test round-trip conversions (Rust -> Python -> Rust)
- ✅ Use property-based testing for conversions
- ✅ Test error cases and edge conditions
- ✅ Integration test with real DSPy modules

**DON'T**:
- ❌ Skip testing generated code
- ❌ Only test happy paths
- ❌ Assume type conversions always work
- ❌ Test only with mock data

### Performance

**DO**:
- ✅ Cache Python objects when possible
- ✅ Minimize GIL acquisition
- ✅ Use batch operations for multiple conversions
- ✅ Profile type conversion overhead
- ✅ Reuse allocations where possible

**DON'T**:
- ❌ Convert types unnecessarily
- ❌ Hold GIL during Rust operations
- ❌ Create Python objects in tight loops
- ❌ Ignore conversion overhead

---

**Version**: 1.0.0
**Last Updated**: 2025-10-30
