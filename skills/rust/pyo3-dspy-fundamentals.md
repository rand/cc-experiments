---
name: pyo3-dspy-fundamentals
description: DSPy fundamentals from Rust - environment setup, LM configuration, calling DSPy modules, prediction handling
skill_id: rust-pyo3-dspy-fundamentals
title: PyO3 DSPy Fundamentals
category: rust
subcategory: pyo3-dspy
complexity: intermediate
prerequisites:
  - rust-pyo3-fundamentals
  - rust-pyo3-classes-modules
  - ml-dspy-setup
  - ml-dspy-modules
tags:
  - rust
  - python
  - pyo3
  - dspy
  - llm
  - ai
  - integration
version: 1.0.0
last_updated: 2025-10-30
learning_outcomes:
  - Call DSPy modules from Rust with type safety
  - Configure language models across the FFI boundary
  - Handle DSPy predictions and results in Rust
  - Manage error propagation between languages
  - Build production-ready DSPy applications in Rust
  - Optimize performance with proper GIL management
related_skills:
  - rust-pyo3-fundamentals
  - rust-pyo3-type-conversion-advanced
  - ml-dspy-modules
  - ml-dspy-production
resources:
  - REFERENCE.md (700+ lines): Comprehensive guide
  - 3 Python scripts (900+ lines): Setup, configuration, inspection
  - 6 Rust+Python examples (1,200+ lines): Working code
---

# PyO3 DSPy Fundamentals

## Overview

Master calling DSPy from Rust using PyO3. Learn to configure language models, execute DSPy modules, handle predictions, and build high-performance, type-safe LLM applications that combine Rust's safety with DSPy's powerful abstractions.

## Prerequisites

**Required**:
- PyO3 fundamentals (project setup, basic Python calls)
- DSPy basics (modules, signatures, predictions)
- Rust ownership and lifetimes
- Python 3.9+ with DSPy installed

**Recommended**:
- Async Rust (Tokio) for production applications
- Error handling patterns (anyhow, thiserror)
- Experience with LLM APIs

## When to Use

**Ideal for**:
- **Performance-critical LLM applications** requiring Rust's speed
- **Type-safe AI systems** with compile-time guarantees
- **Production services** combining Rust backend + DSPy intelligence
- **Embedded LLM applications** in Rust programs
- **High-throughput AI APIs** serving thousands of requests

**Not ideal for**:
- Pure Python DSPy prototypes (overhead not justified)
- Rapid experimentation (slower development cycle)
- Simple scripts (PyO3 adds complexity)

## Learning Path

### 1. Environment Setup

Install dependencies and validate environment:

```bash
# Rust with PyO3
cargo new dspy-rust-app
cd dspy-rust-app
cargo add pyo3 --features extension-module
cargo add tokio --features full
cargo add serde --features derive
cargo add anyhow

# Python with DSPy
python -m venv venv
source venv/bin/activate
pip install dspy-ai openai anthropic

# Validate setup
python skills/rust/pyo3-dspy-fundamentals/resources/scripts/dspy_setup_validator.py
```

### 2. First DSPy Call from Rust

**Cargo.toml**:
```toml
[dependencies]
pyo3 = { version = "0.20", features = ["auto-initialize"] }
```

**src/main.rs**:
```rust
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyModule};

fn main() -> PyResult<()> {
    Python::with_gil(|py| {
        // Import DSPy
        let dspy = PyModule::import(py, "dspy")?;

        // Configure language model
        let openai = PyModule::import(py, "dspy")?
            .getattr("OpenAI")?
            .call1((("gpt-3.5-turbo",),))?;

        let settings = dspy.getattr("settings")?;
        settings.call_method1("configure", ((openai,),))?;

        // Create a simple predictor
        let predict = dspy.getattr("Predict")?;
        let signature = "question -> answer";
        let predictor = predict.call1(((signature,),))?;

        // Make prediction
        let question = "What is 2+2?";
        let result = predictor.call1(((question,),))?;

        // Extract answer
        let answer: String = result
            .getattr("answer")?
            .extract()?;

        println!("Question: {}", question);
        println!("Answer: {}", answer);

        Ok(())
    })
}
```

**Run**:
```bash
export OPENAI_API_KEY="your-key"
cargo run
```

### 3. Language Model Configuration

**Structured Configuration** (recommended):

```rust
use pyo3::prelude::*;
use serde::{Deserialize, Serialize};

#[derive(Debug, Serialize, Deserialize)]
struct LMConfig {
    provider: String,  // "openai", "anthropic", "cohere"
    model: String,
    temperature: f32,
    max_tokens: usize,
}

impl LMConfig {
    fn configure_dspy(&self, py: Python) -> PyResult<()> {
        let dspy = PyModule::import(py, "dspy")?;

        let lm = match self.provider.as_str() {
            "openai" => {
                dspy.getattr("OpenAI")?.call1((
                    (self.model.as_str(),),
                ))?
            },
            "anthropic" => {
                dspy.getattr("Anthropic")?.call1((
                    (self.model.as_str(),),
                ))?
            },
            _ => return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                format!("Unsupported provider: {}", self.provider)
            )),
        };

        dspy.getattr("settings")?
            .call_method1("configure", ((lm,),))?;

        Ok(())
    }
}

fn main() -> PyResult<()> {
    let config = LMConfig {
        provider: "openai".to_string(),
        model: "gpt-3.5-turbo".to_string(),
        temperature: 0.7,
        max_tokens: 500,
    };

    Python::with_gil(|py| {
        config.configure_dspy(py)?;
        // Now ready to use DSPy modules
        Ok(())
    })
}
```

**Use helper script**:
```bash
# Generate config from environment
python resources/scripts/lm_config_manager.py generate > config.json

# Validate config
python resources/scripts/lm_config_manager.py validate config.json
```

### 4. Working with DSPy Modules

**Calling ChainOfThought**:

```rust
use pyo3::prelude::*;
use pyo3::types::PyDict;

#[derive(Debug)]
struct Prediction {
    answer: String,
    reasoning: Option<String>,
}

fn call_chain_of_thought(
    py: Python,
    question: &str,
) -> PyResult<Prediction> {
    let dspy = PyModule::import(py, "dspy")?;

    // Create ChainOfThought predictor
    let cot = dspy.getattr("ChainOfThought")?;
    let signature = "question -> answer";
    let predictor = cot.call1(((signature,),))?;

    // Make prediction
    let result = predictor.call1(((question,),))?;

    // Extract fields
    let answer: String = result.getattr("answer")?.extract()?;

    let reasoning: Option<String> = result
        .getattr("reasoning")
        .ok()
        .and_then(|r| r.extract().ok());

    Ok(Prediction { answer, reasoning })
}

fn main() -> PyResult<()> {
    Python::with_gil(|py| {
        // Configure DSPy first
        configure_lm(py)?;

        let prediction = call_chain_of_thought(
            py,
            "Explain the theory of relativity in simple terms"
        )?;

        println!("Answer: {}", prediction.answer);
        if let Some(reasoning) = prediction.reasoning {
            println!("Reasoning: {}", reasoning);
        }

        Ok(())
    })
}
```

### 5. Custom DSPy Modules

**Define in Python** (recommended for complex modules):

```python
# dspy_modules.py
import dspy

class QAWithContext(dspy.Module):
    def __init__(self):
        super().__init__()
        self.generate = dspy.ChainOfThought("context, question -> answer")

    def forward(self, context, question):
        return self.generate(context=context, question=question)
```

**Call from Rust**:

```rust
use pyo3::prelude::*;
use pyo3::types::PyModule;

fn call_custom_module(
    py: Python,
    context: &str,
    question: &str,
) -> PyResult<String> {
    // Import custom module
    let module = PyModule::from_code(
        py,
        include_str!("dspy_modules.py"),
        "dspy_modules.py",
        "dspy_modules",
    )?;

    let qa_class = module.getattr("QAWithContext")?;
    let qa_instance = qa_class.call0()?;

    // Call forward
    let result = qa_instance.call_method1(
        "forward",
        ((context, question),)
    )?;

    let answer: String = result.getattr("answer")?.extract()?;
    Ok(answer)
}
```

### 6. Error Handling

**Robust Error Handling Pattern**:

```rust
use anyhow::{Context, Result};
use pyo3::prelude::*;

#[derive(Debug, thiserror::Error)]
enum DSpyError {
    #[error("Python error: {0}")]
    Python(#[from] PyErr),

    #[error("DSPy module error: {0}")]
    Module(String),

    #[error("Configuration error: {0}")]
    Config(String),

    #[error("Prediction failed: {0}")]
    Prediction(String),
}

fn safe_dspy_call(question: &str) -> Result<String> {
    Python::with_gil(|py| {
        let dspy = PyModule::import(py, "dspy")
            .context("Failed to import DSPy")?;

        let predict = dspy.getattr("Predict")
            .context("Failed to get Predict class")?;

        let predictor = predict.call1((("question -> answer",),))
            .context("Failed to create predictor")?;

        let result = predictor.call1(((question,),))
            .context("Prediction failed")?;

        let answer: String = result.getattr("answer")?
            .extract()
            .context("Failed to extract answer")?;

        Ok(answer)
    })
}

fn main() {
    match safe_dspy_call("What is Rust?") {
        Ok(answer) => println!("Answer: {}", answer),
        Err(e) => eprintln!("Error: {:?}", e),
    }
}
```

### 7. Performance Optimization

**GIL Management**:

```rust
use pyo3::prelude::*;
use std::sync::Arc;

// Store Python objects across GIL releases
struct DSpyPredictor {
    predictor: Py<PyAny>,
}

impl DSpyPredictor {
    fn new(signature: &str) -> PyResult<Self> {
        Python::with_gil(|py| {
            let dspy = PyModule::import(py, "dspy")?;
            let predict = dspy.getattr("Predict")?;
            let predictor = predict.call1(((signature,),))?;

            Ok(Self {
                predictor: predictor.into(),
            })
        })
    }

    fn predict(&self, question: &str) -> PyResult<String> {
        Python::with_gil(|py| {
            let result = self.predictor
                .as_ref(py)
                .call1(((question,),))?;

            result.getattr("answer")?.extract()
        })
    }
}

// Use across multiple threads
fn parallel_predictions(questions: Vec<String>) -> Vec<PyResult<String>> {
    let predictor = Arc::new(
        DSpyPredictor::new("question -> answer").unwrap()
    );

    questions.into_iter()
        .map(|q| {
            let pred = Arc::clone(&predictor);
            // Each thread acquires GIL independently
            pred.predict(&q)
        })
        .collect()
}
```

### 8. Production Patterns

**Service Structure**:

```rust
use pyo3::prelude::*;
use std::sync::Arc;
use tokio::sync::Mutex;

pub struct DSpyService {
    predictor: Arc<Mutex<Py<PyAny>>>,
}

impl DSpyService {
    pub fn new(signature: &str) -> PyResult<Self> {
        let predictor = Python::with_gil(|py| {
            let dspy = PyModule::import(py, "dspy")?;
            let predict = dspy.getattr("Predict")?;
            let pred = predict.call1(((signature,),))?;
            Ok::<_, PyErr>(pred.into())
        })?;

        Ok(Self {
            predictor: Arc::new(Mutex::new(predictor)),
        })
    }

    pub async fn predict(&self, input: String) -> PyResult<String> {
        let predictor = self.predictor.lock().await;

        Python::with_gil(|py| {
            let result = predictor.as_ref(py).call1(((input,),))?;
            result.getattr("answer")?.extract()
        })
    }
}

#[tokio::main]
async fn main() -> PyResult<()> {
    let service = DSpyService::new("question -> answer")?;

    let answer = service.predict(
        "What is machine learning?".to_string()
    ).await?;

    println!("Answer: {}", answer);
    Ok(())
}
```

## Resources

### REFERENCE.md

Comprehensive 700+ line guide covering:
- Complete environment setup and validation
- All LM provider configurations (OpenAI, Anthropic, Cohere, Together, Ollama)
- Module calling patterns (Predict, ChainOfThought, ReAct, Retrieve)
- Prediction handling and field extraction
- Error handling strategies
- GIL management and threading
- Performance optimization techniques
- Production deployment patterns
- Memory management best practices
- Debugging cross-language issues

**Load**: `cat skills/rust/pyo3-dspy-fundamentals/resources/REFERENCE.md`

### Scripts

**1. dspy_setup_validator.py** (~300 lines)
- Validates PyO3 + DSPy environment
- Checks Rust toolchain, Python version, DSPy installation
- Tests LM provider connections
- Verifies cross-language calls work
- Generates setup report with recommendations

**Usage**:
```bash
python resources/scripts/dspy_setup_validator.py
python resources/scripts/dspy_setup_validator.py --fix  # Auto-fix issues
```

**2. lm_config_manager.py** (~300 lines)
- Manage LM configurations from Rust
- Generate configs from environment variables
- Validate config files
- Switch between providers easily
- Test LM connections

**Usage**:
```bash
# Generate config
python resources/scripts/lm_config_manager.py generate > config.json

# Validate
python resources/scripts/lm_config_manager.py validate config.json

# Test connection
python resources/scripts/lm_config_manager.py test config.json
```

**3. module_inspector.py** (~300 lines)
- Inspect DSPy module structure
- Generate Rust type definitions from Python signatures
- Analyze prediction fields
- Validate module compatibility with PyO3
- Generate binding code

**Usage**:
```bash
# Inspect module
python resources/scripts/module_inspector.py inspect QAModule

# Generate Rust types
python resources/scripts/module_inspector.py codegen QAModule > types.rs
```

### Examples

**1. hello-world/** - Minimal DSPy call
- Basic Rust + PyO3 setup
- Simple Predict call
- Extract and print result

**2. basic-qa/** - Question answering
- ChainOfThought integration
- Error handling
- Structured output

**3. lm-configuration/** - Configure providers
- OpenAI, Anthropic, Cohere setups
- Environment variable configuration
- Config file loading

**4. error-handling/** - Robust error handling
- Custom error types
- Error propagation
- Graceful degradation

**5. module-state/** - Stateful modules
- Maintain module state across calls
- Thread-safe access
- Memory management

**6. benchmarking/** - Performance measurement
- Benchmark DSPy calls
- Compare with pure Python
- GIL impact analysis

## Best Practices

### DO

✅ **Release GIL** during CPU-bound Rust work
✅ **Validate inputs** before crossing language boundary
✅ **Use anyhow/thiserror** for rich error context
✅ **Cache Python objects** (Py<PyAny>) to avoid repeated imports
✅ **Test error paths** thoroughly
✅ **Profile** GIL acquisition patterns
✅ **Document** Python version requirements

### DON'T

❌ **Hold GIL** longer than necessary
❌ **Panic** in Rust code called from Python
❌ **Assume** Python objects are thread-safe
❌ **Forget** to handle Python exceptions
❌ **Mix** Python and Rust error handling
❌ **Skip** environment validation
❌ **Ignore** memory leaks across FFI boundary

## Common Pitfalls

### 1. GIL Deadlocks

**Problem**: Holding GIL while waiting for Rust work
```rust
// ❌ Bad: GIL held during expensive work
Python::with_gil(|py| {
    let result = predictor.call()?;
    expensive_rust_computation(&result);  // GIL still held!
    Ok(())
})
```

**Solution**: Release GIL during Rust work
```rust
// ✅ Good: Release GIL
let result = Python::with_gil(|py| {
    predictor.call()
})?;

// GIL released here
expensive_rust_computation(&result);
```

### 2. Memory Leaks

**Problem**: Python objects not properly released
```rust
// ❌ Bad: Py<PyAny> not dropped
let mut cache: Vec<Py<PyAny>> = Vec::new();
// cache grows forever
```

**Solution**: Explicit cleanup
```rust
// ✅ Good: Clear cache periodically
if cache.len() > 1000 {
    Python::with_gil(|py| {
        cache.clear();  // Properly drops Python refs
    });
}
```

### 3. Error Handling

**Problem**: Silent Python exceptions
```rust
// ❌ Bad: Exception lost
let _ = predictor.call();
```

**Solution**: Propagate errors properly
```rust
// ✅ Good: Handle or propagate
match predictor.call() {
    Ok(result) => process(result),
    Err(e) => {
        eprintln!("DSPy error: {}", e);
        return Err(e.into());
    }
}
```

## Troubleshooting

### Issue: Import Error

**Symptom**: `ModuleNotFoundError: No module named 'dspy'`

**Solution**:
```bash
# Ensure Python environment activated
source venv/bin/activate

# Install DSPy
pip install dspy-ai

# Verify
python -c "import dspy; print(dspy.__version__)"
```

### Issue: GIL Panic

**Symptom**: `PanicException: GIL is not held`

**Solution**: All Python calls must be in `with_gil` block:
```rust
Python::with_gil(|py| {
    // All Python operations here
})
```

### Issue: Segfault

**Symptom**: Rust code crashes with segmentation fault

**Solutions**:
- Check Python object lifetimes
- Don't access Python objects outside `with_gil`
- Verify no use-after-free of Py<PyAny>
- Run with `RUST_BACKTRACE=1`

## Next Steps

**After mastering fundamentals**:
1. **pyo3-dspy-type-system**: Advanced type conversions and safety
2. **pyo3-dspy-rag-pipelines**: Build RAG systems
3. **pyo3-dspy-agents**: Implement agent patterns
4. **pyo3-dspy-async-streaming**: Async and streaming
5. **pyo3-dspy-production**: Production deployment
6. **pyo3-dspy-optimization**: Model optimization workflows

## References

- [PyO3 User Guide](https://pyo3.rs)
- [DSPy Documentation](https://dspy-docs.vercel.app)
- [PyO3 Performance](https://pyo3.rs/latest/performance.html)
- [DSPy Examples](https://github.com/stanfordnlp/dspy/tree/main/examples)

---

**Version**: 1.0.0
**Last Updated**: 2025-10-30
**Maintainer**: DSPy-PyO3 Integration Team
