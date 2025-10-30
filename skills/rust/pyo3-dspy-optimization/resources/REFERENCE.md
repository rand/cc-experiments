# PyO3 DSPy Optimization - Complete Reference

Comprehensive guide to running DSPy optimization workflows from Rust, covering teleprompter execution, compiled model management, version control, evaluation frameworks, A/B testing, deployment pipelines, and progress monitoring.

## Table of Contents

1. [Teleprompter Reference](#teleprompter-reference)
2. [Model Compilation](#model-compilation)
3. [Model Registry](#model-registry)
4. [Evaluation Framework](#evaluation-framework)
5. [A/B Testing](#ab-testing)
6. [Deployment Pipelines](#deployment-pipelines)
7. [Rollback Strategies](#rollback-strategies)
8. [Progress Monitoring](#progress-monitoring)
9. [Configuration Management](#configuration-management)
10. [Best Practices Summary](#best-practices-summary)

---

## Teleprompter Reference

### BootstrapFewShot

**Purpose**: Automatically bootstrap few-shot examples from training data.

**Complete Python Implementation**:

```python
"""
BootstrapFewShot optimization implementation for DSPy modules.
"""

import dspy
from typing import List, Dict, Any, Optional, Callable


def bootstrap_fewshot_optimizer(
    module: dspy.Module,
    trainset: List[dspy.Example],
    metric: Callable,
    max_bootstrapped_demos: int = 4,
    max_labeled_demos: int = 8,
    max_rounds: int = 1,
    teacher_settings: Optional[Dict[str, Any]] = None,
) -> dspy.Module:
    """
    Run BootstrapFewShot optimization on a DSPy module.

    Args:
        module: The DSPy module to optimize
        trainset: Training examples
        metric: Evaluation metric function
        max_bootstrapped_demos: Maximum bootstrapped examples per prompt
        max_labeled_demos: Maximum labeled examples to include
        max_rounds: Number of bootstrap rounds
        teacher_settings: Optional settings for teacher model

    Returns:
        Compiled DSPy module with optimized few-shot examples
    """
    from dspy.teleprompt import BootstrapFewShot

    # Create teleprompter
    teleprompter = BootstrapFewShot(
        metric=metric,
        max_bootstrapped_demos=max_bootstrapped_demos,
        max_labeled_demos=max_labeled_demos,
        max_rounds=max_rounds,
        teacher_settings=teacher_settings or {},
    )

    # Compile the module
    print(f"Starting BootstrapFewShot with {len(trainset)} examples...")
    compiled_module = teleprompter.compile(
        student=module,
        trainset=trainset,
    )

    print("✓ BootstrapFewShot compilation complete")
    return compiled_module


def create_accuracy_metric():
    """Create simple accuracy metric for evaluation."""
    def accuracy(example, prediction, trace=None):
        """Check if prediction matches expected answer."""
        if not hasattr(prediction, 'answer'):
            return False

        expected = example.answer.lower().strip()
        predicted = prediction.answer.lower().strip()
        return expected == predicted

    return accuracy


def create_f1_metric():
    """Create F1 score metric for evaluation."""
    def f1_score(example, prediction, trace=None):
        """Calculate F1 score between expected and predicted."""
        if not hasattr(prediction, 'answer'):
            return 0.0

        expected_tokens = set(example.answer.lower().split())
        predicted_tokens = set(prediction.answer.lower().split())

        if not predicted_tokens:
            return 0.0

        precision = len(expected_tokens & predicted_tokens) / len(predicted_tokens)
        recall = len(expected_tokens & predicted_tokens) / len(expected_tokens)

        if precision + recall == 0:
            return 0.0

        return 2 * (precision * recall) / (precision + recall)

    return f1_score


# Example usage
if __name__ == "__main__":
    # Configure DSPy
    lm = dspy.OpenAI(model="gpt-3.5-turbo")
    dspy.settings.configure(lm=lm)

    # Create module
    class QA(dspy.Module):
        def __init__(self):
            super().__init__()
            self.generate = dspy.ChainOfThought("question -> answer")

        def forward(self, question):
            return self.generate(question=question)

    module = QA()

    # Create training data
    trainset = [
        dspy.Example(question="What is 2+2?", answer="4").with_inputs("question"),
        dspy.Example(question="What is the capital of France?", answer="Paris").with_inputs("question"),
    ]

    # Optimize
    metric = create_accuracy_metric()
    compiled = bootstrap_fewshot_optimizer(module, trainset, metric)

    # Test
    result = compiled(question="What is 3+3?")
    print(f"Answer: {result.answer}")
```

**Rust Wrapper**:

```rust
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};
use serde::{Deserialize, Serialize};
use anyhow::{Context, Result};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BootstrapConfig {
    pub max_bootstrapped_demos: usize,
    pub max_labeled_demos: usize,
    pub max_rounds: usize,
    pub teacher_settings: Option<serde_json::Value>,
}

impl Default for BootstrapConfig {
    fn default() -> Self {
        Self {
            max_bootstrapped_demos: 4,
            max_labeled_demos: 8,
            max_rounds: 1,
            teacher_settings: None,
        }
    }
}

#[derive(Debug, Serialize, Deserialize)]
pub struct TrainingExample {
    pub question: String,
    pub answer: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub context: Option<String>,
}

pub fn run_bootstrap_fewshot(
    py: Python,
    module: &PyAny,
    trainset: &[TrainingExample],
    metric_fn: &PyAny,
    config: BootstrapConfig,
) -> PyResult<Py<PyAny>> {
    // Import DSPy
    let dspy = PyModule::import(py, "dspy")?;
    let teleprompt = dspy.getattr("teleprompt")?;

    // Create BootstrapFewShot instance
    let kwargs = PyDict::new(py);
    kwargs.set_item("metric", metric_fn)?;
    kwargs.set_item("max_bootstrapped_demos", config.max_bootstrapped_demos)?;
    kwargs.set_item("max_labeled_demos", config.max_labeled_demos)?;
    kwargs.set_item("max_rounds", config.max_rounds)?;

    if let Some(teacher) = config.teacher_settings {
        let teacher_dict = pythonize::pythonize(py, &teacher)?;
        kwargs.set_item("teacher_settings", teacher_dict)?;
    }

    let bootstrap = teleprompt.getattr("BootstrapFewShot")?.call((), Some(kwargs))?;

    // Convert trainset to Python list of Examples
    let py_trainset = PyList::empty(py);
    let example_class = dspy.getattr("Example")?;

    for ex in trainset {
        let example_kwargs = PyDict::new(py);
        example_kwargs.set_item("question", &ex.question)?;
        example_kwargs.set_item("answer", &ex.answer)?;

        if let Some(ctx) = &ex.context {
            example_kwargs.set_item("context", ctx)?;
        }

        let example = example_class.call((), Some(example_kwargs))?;
        let with_inputs = example.call_method1("with_inputs", (("question",),))?;
        py_trainset.append(with_inputs)?;
    }

    // Compile the module
    println!("Running BootstrapFewShot optimization...");
    println!("  Training examples: {}", trainset.len());
    println!("  Max bootstrapped: {}", config.max_bootstrapped_demos);
    println!("  Max labeled: {}", config.max_labeled_demos);

    let compile_kwargs = PyDict::new(py);
    compile_kwargs.set_item("student", module)?;
    compile_kwargs.set_item("trainset", py_trainset)?;

    let compiled = bootstrap.call_method("compile", (), Some(compile_kwargs))?;

    println!("✓ Optimization complete");
    Ok(compiled.into())
}
```

**Cargo.toml Dependencies**:

```toml
[dependencies]
pyo3 = { version = "0.20", features = ["auto-initialize"] }
serde = { version = "1.0", features = ["derive"] }
serde_json = "1.0"
pythonize = "0.20"  # For converting Rust to Python types
anyhow = "1.0"
```

---

### MIPROv2

**Purpose**: Multi-prompt optimization with instruction generation.

**Complete Python Implementation**:

```python
"""
MIPROv2 (Multi-prompt Instruction Proposal) optimizer.
"""

import dspy
from typing import List, Optional, Dict, Any


def miprov2_optimizer(
    module: dspy.Module,
    trainset: List[dspy.Example],
    devset: List[dspy.Example],
    metric: callable,
    num_candidates: int = 10,
    init_temperature: float = 1.0,
    prompt_model: Optional[str] = None,
    task_model: Optional[str] = None,
    requires_permission_to_run: bool = False,
) -> dspy.Module:
    """
    Run MIPROv2 optimization on a DSPy module.

    MIPROv2 generates multiple instruction candidates and selects
    the best based on validation performance.

    Args:
        module: The DSPy module to optimize
        trainset: Training examples for bootstrapping
        devset: Development/validation set for candidate selection
        metric: Evaluation metric function
        num_candidates: Number of instruction candidates to generate
        init_temperature: Initial temperature for generation
        prompt_model: Model for generating instructions (defaults to configured)
        task_model: Model for task execution (defaults to configured)
        requires_permission_to_run: Whether to ask for permission

    Returns:
        Optimized DSPy module with best instructions
    """
    from dspy.teleprompt import MIPROv2

    # Create MIPROv2 teleprompter
    teleprompter = MIPROv2(
        metric=metric,
        num_candidates=num_candidates,
        init_temperature=init_temperature,
        prompt_model=prompt_model,
        task_model=task_model,
    )

    print(f"Starting MIPROv2 optimization...")
    print(f"  Training examples: {len(trainset)}")
    print(f"  Validation examples: {len(devset)}")
    print(f"  Candidates: {num_candidates}")
    print(f"  Temperature: {init_temperature}")

    # Compile the module
    compiled_module = teleprompter.compile(
        student=module,
        trainset=trainset,
        devset=devset,
        requires_permission_to_run=requires_permission_to_run,
    )

    print("✓ MIPROv2 optimization complete")
    return compiled_module


def create_validation_metric():
    """Create a metric suitable for MIPROv2 validation."""
    def validation_metric(example, prediction, trace=None):
        """
        Validation metric that returns a score between 0 and 1.

        MIPROv2 requires metrics that return numeric scores.
        """
        if not hasattr(prediction, 'answer'):
            return 0.0

        expected = example.answer.lower().strip()
        predicted = prediction.answer.lower().strip()

        # Exact match
        if expected == predicted:
            return 1.0

        # Partial credit for token overlap
        expected_tokens = set(expected.split())
        predicted_tokens = set(predicted.split())

        if not predicted_tokens:
            return 0.0

        overlap = len(expected_tokens & predicted_tokens)
        return overlap / max(len(expected_tokens), len(predicted_tokens))

    return validation_metric


# Example usage
if __name__ == "__main__":
    # Configure DSPy with two models
    prompt_lm = dspy.OpenAI(model="gpt-4")  # Stronger model for instruction generation
    task_lm = dspy.OpenAI(model="gpt-3.5-turbo")  # Cheaper model for task

    dspy.settings.configure(lm=task_lm)

    # Create module
    class QA(dspy.Module):
        def __init__(self):
            super().__init__()
            self.generate = dspy.ChainOfThought("question -> answer")

        def forward(self, question):
            return self.generate(question=question)

    module = QA()

    # Create datasets
    trainset = [
        dspy.Example(question="What is 2+2?", answer="4").with_inputs("question"),
        dspy.Example(question="What is 3+3?", answer="6").with_inputs("question"),
    ]

    devset = [
        dspy.Example(question="What is 4+4?", answer="8").with_inputs("question"),
    ]

    # Optimize
    metric = create_validation_metric()
    compiled = miprov2_optimizer(
        module=module,
        trainset=trainset,
        devset=devset,
        metric=metric,
        num_candidates=5,
        prompt_model="gpt-4",
        task_model="gpt-3.5-turbo",
    )

    # Test
    result = compiled(question="What is 5+5?")
    print(f"Answer: {result.answer}")
```

**Rust Wrapper**:

```rust
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};

#[derive(Debug, Clone)]
pub struct MIPROConfig {
    pub num_candidates: usize,
    pub init_temperature: f64,
    pub prompt_model: Option<String>,
    pub task_model: Option<String>,
    pub verbose: bool,
}

impl Default for MIPROConfig {
    fn default() -> Self {
        Self {
            num_candidates: 10,
            init_temperature: 1.0,
            prompt_model: None,
            task_model: None,
            verbose: true,
        }
    }
}

pub fn run_miprov2(
    py: Python,
    module: &PyAny,
    trainset: &PyAny,
    devset: &PyAny,
    metric: &PyAny,
    config: MIPROConfig,
) -> PyResult<Py<PyAny>> {
    let dspy = PyModule::import(py, "dspy")?;
    let teleprompt = dspy.getattr("teleprompt")?;

    // Create MIPROv2 instance
    let kwargs = PyDict::new(py);
    kwargs.set_item("metric", metric)?;
    kwargs.set_item("num_candidates", config.num_candidates)?;
    kwargs.set_item("init_temperature", config.init_temperature)?;

    if let Some(ref pm) = config.prompt_model {
        kwargs.set_item("prompt_model", pm)?;
    }

    if let Some(ref tm) = config.task_model {
        kwargs.set_item("task_model", tm)?;
    }

    let mipro = teleprompt.getattr("MIPROv2")?.call((), Some(kwargs))?;

    if config.verbose {
        println!("Running MIPROv2 optimization...");
        println!("  Candidates: {}", config.num_candidates);
        println!("  Temperature: {}", config.init_temperature);
    }

    // Compile
    let compile_kwargs = PyDict::new(py);
    compile_kwargs.set_item("student", module)?;
    compile_kwargs.set_item("trainset", trainset)?;
    compile_kwargs.set_item("devset", devset)?;
    compile_kwargs.set_item("requires_permission_to_run", false)?;

    let compiled = mipro.call_method("compile", (), Some(compile_kwargs))?;

    if config.verbose {
        println!("✓ MIPROv2 optimization complete");
    }

    Ok(compiled.into())
}
```

---

### COPRO

**Purpose**: Coordinate multiple prompts with task-specific optimization.

**Complete Python Implementation**:

```python
"""
COPRO (Coordinate Prompts) optimizer for multi-stage prompts.
"""

import dspy
from typing import List, Optional


def copro_optimizer(
    module: dspy.Module,
    trainset: List[dspy.Example],
    metric: callable,
    breadth: int = 10,
    depth: int = 3,
    init_temperature: float = 1.4,
) -> dspy.Module:
    """
    Run COPRO optimization on a DSPy module.

    COPRO generates and coordinates multiple prompts across
    different stages of a pipeline.

    Args:
        module: The DSPy module to optimize
        trainset: Training examples
        metric: Evaluation metric
        breadth: Number of prompt candidates per stage
        depth: Optimization depth
        init_temperature: Initial temperature for generation

    Returns:
        Optimized module with coordinated prompts
    """
    from dspy.teleprompt import COPRO

    teleprompter = COPRO(
        metric=metric,
        breadth=breadth,
        depth=depth,
        init_temperature=init_temperature,
    )

    print(f"Starting COPRO optimization...")
    print(f"  Breadth: {breadth}")
    print(f"  Depth: {depth}")
    print(f"  Temperature: {init_temperature}")

    compiled_module = teleprompter.compile(
        student=module,
        trainset=trainset,
    )

    print("✓ COPRO optimization complete")
    return compiled_module


# Example: Multi-stage module for COPRO
class MultiStageQA(dspy.Module):
    """Multi-stage QA with separate analysis and answer generation."""

    def __init__(self):
        super().__init__()
        self.analyze = dspy.ChainOfThought("question -> analysis")
        self.answer = dspy.ChainOfThought("question, analysis -> answer")

    def forward(self, question):
        # Stage 1: Analyze the question
        analysis = self.analyze(question=question)

        # Stage 2: Generate answer based on analysis
        answer = self.answer(
            question=question,
            analysis=analysis.analysis
        )

        return answer
```

**Rust Wrapper**:

```rust
#[derive(Debug, Clone)]
pub struct COPROConfig {
    pub breadth: usize,
    pub depth: usize,
    pub init_temperature: f64,
}

impl Default for COPROConfig {
    fn default() -> Self {
        Self {
            breadth: 10,
            depth: 3,
            init_temperature: 1.4,
        }
    }
}

pub fn run_copro(
    py: Python,
    module: &PyAny,
    trainset: &PyAny,
    metric: &PyAny,
    config: COPROConfig,
) -> PyResult<Py<PyAny>> {
    let dspy = PyModule::import(py, "dspy")?;
    let teleprompt = dspy.getattr("teleprompt")?;

    let kwargs = PyDict::new(py);
    kwargs.set_item("metric", metric)?;
    kwargs.set_item("breadth", config.breadth)?;
    kwargs.set_item("depth", config.depth)?;
    kwargs.set_item("init_temperature", config.init_temperature)?;

    let copro = teleprompt.getattr("COPRO")?.call((), Some(kwargs))?;

    println!("Running COPRO optimization...");
    println!("  Breadth: {}", config.breadth);
    println!("  Depth: {}", config.depth);

    let compile_kwargs = PyDict::new(py);
    compile_kwargs.set_item("student", module)?;
    compile_kwargs.set_item("trainset", trainset)?;

    let compiled = copro.call_method("compile", (), Some(compile_kwargs))?;

    println!("✓ COPRO optimization complete");
    Ok(compiled.into())
}
```

---

## Model Compilation

### Saving Compiled Models

**Complete Save Implementation**:

```python
"""
Save compiled DSPy models with metadata.
"""

import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Any
import dspy


def save_compiled_model(
    module: dspy.Module,
    output_dir: str,
    metadata: Dict[str, Any],
) -> None:
    """
    Save a compiled DSPy module with metadata.

    Args:
        module: Compiled DSPy module
        output_dir: Directory to save model
        metadata: Model metadata dictionary
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Save the model
    model_path = output_path / "model.json"
    module.save(str(model_path))
    print(f"✓ Model saved to {model_path}")

    # Add save timestamp to metadata
    metadata['saved_at'] = datetime.utcnow().isoformat()
    metadata['dspy_version'] = dspy.__version__

    # Save metadata
    metadata_path = output_path / "metadata.json"
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)
    print(f"✓ Metadata saved to {metadata_path}")

    # Save a human-readable summary
    summary_path = output_path / "README.md"
    with open(summary_path, 'w') as f:
        f.write(f"# Model: {metadata.get('model_id', 'unknown')}\n\n")
        f.write(f"**Version**: {metadata.get('version', 'unknown')}\n")
        f.write(f"**Created**: {metadata.get('created_at', 'unknown')}\n")
        f.write(f"**Optimizer**: {metadata.get('optimizer', 'unknown')}\n\n")
        f.write(f"## Performance\n\n")
        f.write(f"- Validation Score: {metadata.get('validation_score', 'N/A')}\n")
        f.write(f"- Training Examples: {metadata.get('num_training_examples', 'N/A')}\n\n")
        f.write(f"## Configuration\n\n")
        f.write(f"```json\n{json.dumps(metadata.get('hyperparameters', {}), indent=2)}\n```\n")
    print(f"✓ Summary saved to {summary_path}")


def load_compiled_model(model_dir: str) -> tuple:
    """
    Load a compiled DSPy module with metadata.

    Args:
        model_dir: Directory containing model and metadata

    Returns:
        Tuple of (module, metadata)
    """
    model_path = Path(model_dir) / "model.json"
    metadata_path = Path(model_dir) / "metadata.json"

    # Load metadata
    with open(metadata_path, 'r') as f:
        metadata = json.load(f)

    # Load model
    # Note: DSPy's load is typically class-specific
    # This is a generic example
    with open(model_path, 'r') as f:
        model_data = json.load(f)

    print(f"✓ Loaded model: {metadata.get('model_id')} v{metadata.get('version')}")
    return model_data, metadata


# Example metadata structure
def create_metadata(
    model_id: str,
    version: str,
    optimizer: str,
    base_model: str,
    num_training_examples: int,
    validation_score: float,
    hyperparameters: Dict[str, Any],
) -> Dict[str, Any]:
    """Create standard metadata structure."""
    return {
        "model_id": model_id,
        "version": version,
        "created_at": datetime.utcnow().isoformat(),
        "optimizer": optimizer,
        "base_model": base_model,
        "num_training_examples": num_training_examples,
        "validation_score": validation_score,
        "hyperparameters": hyperparameters,
        "framework": "dspy",
    }
```

**Rust Save/Load Implementation**:

```rust
use pyo3::prelude::*;
use serde::{Deserialize, Serialize};
use std::fs;
use std::path::{Path, PathBuf};
use chrono::Utc;
use anyhow::{Context, Result};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ModelMetadata {
    pub model_id: String,
    pub version: String,
    pub created_at: String,
    pub saved_at: Option<String>,
    pub optimizer: String,
    pub base_model: String,
    pub num_training_examples: usize,
    pub validation_score: f64,
    pub hyperparameters: serde_json::Value,
    pub framework: String,
    pub dspy_version: Option<String>,
}

impl ModelMetadata {
    pub fn new(
        model_id: String,
        version: String,
        optimizer: String,
        base_model: String,
        num_training_examples: usize,
        validation_score: f64,
        hyperparameters: serde_json::Value,
    ) -> Self {
        Self {
            model_id,
            version,
            created_at: Utc::now().to_rfc3339(),
            saved_at: None,
            optimizer,
            base_model,
            num_training_examples,
            validation_score,
            hyperparameters,
            framework: "dspy".to_string(),
            dspy_version: None,
        }
    }
}

pub fn save_compiled_model(
    py: Python,
    module: &PyAny,
    output_dir: &Path,
    metadata: &mut ModelMetadata,
) -> Result<()> {
    // Create output directory
    fs::create_dir_all(output_dir)
        .context("Failed to create output directory")?;

    // Save the model using DSPy's save method
    let model_path = output_dir.join("model.json");
    module.call_method1("save", (model_path.to_str().unwrap(),))
        .context("Failed to save DSPy model")?;

    println!("✓ Model saved to {}", model_path.display());

    // Update metadata with save timestamp
    metadata.saved_at = Some(Utc::now().to_rfc3339());

    // Get DSPy version
    if let Ok(dspy) = PyModule::import(py, "dspy") {
        if let Ok(version) = dspy.getattr("__version__") {
            metadata.dspy_version = version.extract().ok();
        }
    }

    // Save metadata
    let metadata_path = output_dir.join("metadata.json");
    let metadata_json = serde_json::to_string_pretty(&metadata)?;
    fs::write(&metadata_path, metadata_json)
        .context("Failed to save metadata")?;

    println!("✓ Metadata saved to {}", metadata_path.display());

    // Create README
    create_model_readme(output_dir, metadata)?;

    Ok(())
}

pub fn load_compiled_model(
    py: Python,
    model_dir: &Path,
) -> Result<(Py<PyAny>, ModelMetadata)> {
    // Load metadata
    let metadata_path = model_dir.join("metadata.json");
    let metadata_json = fs::read_to_string(&metadata_path)
        .context("Failed to read metadata file")?;
    let metadata: ModelMetadata = serde_json::from_str(&metadata_json)
        .context("Failed to parse metadata")?;

    // Load model
    let model_path = model_dir.join("model.json");

    // Note: Loading compiled models typically requires the original module class
    // This loads the raw JSON - actual loading may need the module definition
    let model_json = fs::read_to_string(&model_path)
        .context("Failed to read model file")?;

    // For now, return the path - actual loading depends on module type
    println!("✓ Loaded model: {} v{}", metadata.model_id, metadata.version);
    println!("  Score: {:.2}", metadata.validation_score);

    // In practice, you'd reconstruct the module here
    let dspy = PyModule::import(py, "dspy")?;
    let model = dspy.call_method1("load", (model_path.to_str().unwrap(),))
        .context("Failed to load DSPy model")?;

    Ok((model.into(), metadata))
}

fn create_model_readme(output_dir: &Path, metadata: &ModelMetadata) -> Result<()> {
    let readme_path = output_dir.join("README.md");
    let readme_content = format!(
        r#"# Model: {}

**Version**: {}
**Created**: {}
**Optimizer**: {}

## Performance

- Validation Score: {:.4}
- Training Examples: {}

## Configuration

```json
{}
```

## Usage

Load this model:

```python
import dspy

# Load the compiled model
model = dspy.load("model.json")

# Use the model
result = model(question="Your question here")
print(result.answer)
```

```rust
use pyo3::prelude::*;

Python::with_gil(|py| {{
    let (model, metadata) = load_compiled_model(py, Path::new("."))?;
    // Use model...
}});
```
"#,
        metadata.model_id,
        metadata.version,
        metadata.created_at,
        metadata.optimizer,
        metadata.validation_score,
        metadata.num_training_examples,
        serde_json::to_string_pretty(&metadata.hyperparameters)?
    );

    fs::write(&readme_path, readme_content)?;
    println!("✓ README saved to {}", readme_path.display());

    Ok(())
}
```

---

## Model Registry

### Version Control System

**Complete Registry Implementation**:

```rust
use semver::Version;
use std::collections::HashMap;
use std::path::PathBuf;
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub enum ModelStatus {
    Development,
    Staging,
    Production,
    Deprecated,
    Archived,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ModelVersion {
    pub version: Version,
    pub path: PathBuf,
    pub metadata: ModelMetadata,
    pub status: ModelStatus,
    pub promoted_at: Option<String>,
    pub deprecated_at: Option<String>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct ModelRegistry {
    pub base_dir: PathBuf,
    pub models: HashMap<String, Vec<ModelVersion>>,
    pub registry_path: PathBuf,
}

impl ModelRegistry {
    pub fn new(base_dir: PathBuf) -> Result<Self> {
        fs::create_dir_all(&base_dir)?;

        let registry_path = base_dir.join("registry.json");

        // Try to load existing registry
        if registry_path.exists() {
            let registry_json = fs::read_to_string(&registry_path)?;
            let mut registry: Self = serde_json::from_str(&registry_json)?;
            registry.base_dir = base_dir;
            registry.registry_path = registry_path;
            Ok(registry)
        } else {
            Ok(Self {
                base_dir,
                models: HashMap::new(),
                registry_path,
            })
        }
    }

    pub fn register_model(
        &mut self,
        model_id: &str,
        version: Version,
        metadata: ModelMetadata,
    ) -> Result<PathBuf> {
        // Create versioned directory
        let model_dir = self.base_dir
            .join(model_id)
            .join(version.to_string());

        fs::create_dir_all(&model_dir)?;

        let version_entry = ModelVersion {
            version: version.clone(),
            path: model_dir.clone(),
            metadata,
            status: ModelStatus::Development,
            promoted_at: None,
            deprecated_at: None,
        };

        // Add to registry
        self.models
            .entry(model_id.to_string())
            .or_insert_with(Vec::new)
            .push(version_entry);

        // Save registry
        self.save()?;

        println!("✓ Registered {} v{}", model_id, version);
        Ok(model_dir)
    }

    pub fn promote_to_production(
        &mut self,
        model_id: &str,
        version: &Version,
    ) -> Result<()> {
        let versions = self.models.get_mut(model_id)
            .context(format!("Model {} not found", model_id))?;

        // Demote current production version to deprecated
        for v in versions.iter_mut() {
            if v.status == ModelStatus::Production {
                v.status = ModelStatus::Deprecated;
                v.deprecated_at = Some(Utc::now().to_rfc3339());
            }
        }

        // Promote new version
        let version_entry = versions.iter_mut()
            .find(|v| &v.version == version)
            .context(format!("Version {} not found", version))?;

        version_entry.status = ModelStatus::Production;
        version_entry.promoted_at = Some(Utc::now().to_rfc3339());

        self.save()?;

        println!("✓ Promoted {} v{} to production", model_id, version);
        Ok(())
    }

    pub fn get_production_model(
        &self,
        model_id: &str,
    ) -> Option<&ModelVersion> {
        self.models.get(model_id)?
            .iter()
            .find(|v| v.status == ModelStatus::Production)
    }

    pub fn get_latest_version(
        &self,
        model_id: &str,
    ) -> Option<&ModelVersion> {
        self.models.get(model_id)?
            .iter()
            .max_by_key(|v| &v.version)
    }

    pub fn list_versions(
        &self,
        model_id: &str,
    ) -> Vec<&ModelVersion> {
        self.models.get(model_id)
            .map(|versions| {
                let mut v: Vec<_> = versions.iter().collect();
                v.sort_by(|a, b| b.version.cmp(&a.version));
                v
            })
            .unwrap_or_default()
    }

    pub fn archive_old_versions(
        &mut self,
        model_id: &str,
        keep_latest: usize,
    ) -> Result<usize> {
        let versions = self.models.get_mut(model_id)
            .context(format!("Model {} not found", model_id))?;

        // Sort by version descending
        versions.sort_by(|a, b| b.version.cmp(&a.version));

        let mut archived_count = 0;
        for (i, version) in versions.iter_mut().enumerate() {
            if i >= keep_latest && version.status != ModelStatus::Production {
                if version.status != ModelStatus::Archived {
                    version.status = ModelStatus::Archived;
                    archived_count += 1;
                }
            }
        }

        if archived_count > 0 {
            self.save()?;
            println!("✓ Archived {} old versions of {}", archived_count, model_id);
        }

        Ok(archived_count)
    }

    fn save(&self) -> Result<()> {
        let registry_json = serde_json::to_string_pretty(&self)?;
        fs::write(&self.registry_path, registry_json)?;
        Ok(())
    }
}
```

**Cargo.toml for Registry**:

```toml
[dependencies]
semver = { version = "1.0", features = ["serde"] }
chrono = { version = "0.4", features = ["serde"] }
```

---

## Evaluation Framework

### Metrics and Evaluation

**Complete Evaluation System**:

```python
"""
Comprehensive evaluation metrics for DSPy models.
"""

import dspy
from typing import List, Dict, Any, Callable
from dataclasses import dataclass
from collections import defaultdict


@dataclass
class EvaluationMetrics:
    """Container for evaluation metrics."""
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    total_examples: int
    correct: int
    latency_ms: float
    per_class_metrics: Dict[str, Dict[str, float]]


class Evaluator:
    """Evaluation harness for DSPy models."""

    def __init__(self, metric_fn: Callable):
        self.metric_fn = metric_fn

    def evaluate(
        self,
        model: dspy.Module,
        dataset: List[dspy.Example],
        display_progress: bool = True,
    ) -> EvaluationMetrics:
        """
        Evaluate model on dataset.

        Args:
            model: Compiled DSPy model
            dataset: Evaluation dataset
            display_progress: Whether to show progress

        Returns:
            EvaluationMetrics with results
        """
        correct = 0
        total = len(dataset)
        latencies = []

        true_positives = defaultdict(int)
        false_positives = defaultdict(int)
        false_negatives = defaultdict(int)

        for i, example in enumerate(dataset):
            if display_progress and i % 10 == 0:
                print(f"Evaluating: {i}/{total}")

            # Time the prediction
            import time
            start = time.time()

            try:
                prediction = model(**example.inputs())
                latency = (time.time() - start) * 1000  # ms
                latencies.append(latency)

                # Evaluate
                is_correct = self.metric_fn(example, prediction)

                if is_correct:
                    correct += 1
                    true_positives[example.answer] += 1
                else:
                    if hasattr(prediction, 'answer'):
                        false_positives[prediction.answer] += 1
                    false_negatives[example.answer] += 1

            except Exception as e:
                print(f"Error on example {i}: {e}")
                latencies.append(0.0)
                false_negatives[example.answer] += 1

        # Calculate metrics
        accuracy = correct / total if total > 0 else 0.0

        all_labels = set(true_positives.keys()) | set(false_positives.keys()) | set(false_negatives.keys())

        per_class = {}
        for label in all_labels:
            tp = true_positives[label]
            fp = false_positives[label]
            fn = false_negatives[label]

            precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

            per_class[label] = {
                "precision": precision,
                "recall": recall,
                "f1": f1,
            }

        # Macro-averaged metrics
        avg_precision = sum(m["precision"] for m in per_class.values()) / len(per_class) if per_class else 0.0
        avg_recall = sum(m["recall"] for m in per_class.values()) / len(per_class) if per_class else 0.0
        avg_f1 = sum(m["f1"] for m in per_class.values()) / len(per_class) if per_class else 0.0

        avg_latency = sum(latencies) / len(latencies) if latencies else 0.0

        return EvaluationMetrics(
            accuracy=accuracy,
            precision=avg_precision,
            recall=avg_recall,
            f1_score=avg_f1,
            total_examples=total,
            correct=correct,
            latency_ms=avg_latency,
            per_class_metrics=per_class,
        )
```

**Rust Evaluation Implementation**:

```rust
use pyo3::prelude::*;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::time::Instant;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EvaluationResult {
    pub model_id: String,
    pub version: String,
    pub total_examples: usize,
    pub correct: usize,
    pub accuracy: f64,
    pub precision: f64,
    pub recall: f64,
    pub f1_score: f64,
    pub average_latency_ms: f64,
    pub per_example_results: Vec<ExampleResult>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExampleResult {
    pub input: String,
    pub expected: String,
    pub predicted: String,
    pub correct: bool,
    pub latency_ms: f64,
}

pub async fn evaluate_model(
    py: Python,
    model: &PyAny,
    test_set: &[TrainingExample],
    metric_fn: &PyAny,
) -> Result<EvaluationResult> {
    let mut results = Vec::new();
    let mut correct_count = 0;
    let mut total_latency = 0.0;

    for (i, example) in test_set.iter().enumerate() {
        if i % 10 == 0 {
            println!("Evaluating: {}/{}", i, test_set.len());
        }

        let start = Instant::now();

        // Run prediction
        let prediction = model.call_method1(
            "forward",
            ((example.question.as_str(),),)
        )?;

        let latency = start.elapsed().as_secs_f64() * 1000.0;

        // Extract answer
        let predicted: String = prediction
            .getattr("answer")?
            .extract()?;

        // Compute metric
        let is_correct: bool = metric_fn.call1((
            (&predicted, &example.answer),
        ))?.extract()?;

        if is_correct {
            correct_count += 1;
        }

        total_latency += latency;

        results.push(ExampleResult {
            input: example.question.clone(),
            expected: example.answer.clone(),
            predicted,
            correct: is_correct,
            latency_ms: latency,
        });
    }

    let accuracy = correct_count as f64 / test_set.len() as f64;
    let avg_latency = total_latency / test_set.len() as f64;

    // Calculate precision/recall/F1
    let (precision, recall, f1) = calculate_metrics(&results);

    Ok(EvaluationResult {
        model_id: "model".to_string(),
        version: "1.0.0".to_string(),
        total_examples: test_set.len(),
        correct: correct_count,
        accuracy,
        precision,
        recall,
        f1_score: f1,
        average_latency_ms: avg_latency,
        per_example_results: results,
    })
}

fn calculate_metrics(results: &[ExampleResult]) -> (f64, f64, f64) {
    // Simplified binary classification metrics
    let correct = results.iter().filter(|r| r.correct).count() as f64;
    let total = results.len() as f64;

    let precision = if total > 0.0 { correct / total } else { 0.0 };
    let recall = precision;  // Same for exact match
    let f1 = if precision + recall > 0.0 {
        2.0 * (precision * recall) / (precision + recall)
    } else {
        0.0
    };

    (precision, recall, f1)
}

pub fn save_evaluation_report(
    result: &EvaluationResult,
    output_path: &Path,
) -> Result<()> {
    let report_json = serde_json::to_string_pretty(result)?;
    fs::write(output_path, report_json)?;

    println!("\n╔═══════════════════════════╗");
    println!("║   Evaluation Report       ║");
    println!("╚═══════════════════════════╝");
    println!("Model: {} v{}", result.model_id, result.version);
    println!("Accuracy:  {:.2}%", result.accuracy * 100.0);
    println!("Precision: {:.2}%", result.precision * 100.0);
    println!("Recall:    {:.2}%", result.recall * 100.0);
    println!("F1 Score:  {:.2}%", result.f1_score * 100.0);
    println!("Avg Latency: {:.2}ms", result.average_latency_ms);
    println!("Correct: {}/{}", result.correct, result.total_examples);
    println!("\nReport saved to: {}", output_path.display());

    Ok(())
}
```

---

## A/B Testing

### Statistical Testing

**Complete A/B Test Implementation with Statistics**:

```rust
use rand::Rng;
use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::Arc;
use tokio::sync::RwLock;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ABTestConfig {
    pub model_a_id: String,
    pub model_b_id: String,
    pub traffic_split: f64,  // 0.0 to 1.0
    pub min_sample_size: usize,
    pub confidence_level: f64,  // 0.95 for 95% confidence
}

pub struct ABTestRunner {
    model_a: Arc<RwLock<Py<PyAny>>>,
    model_b: Arc<RwLock<Py<PyAny>>>,
    config: ABTestConfig,

    // Metrics
    model_a_requests: Arc<AtomicUsize>,
    model_b_requests: Arc<AtomicUsize>,
    model_a_successes: Arc<AtomicUsize>,
    model_b_successes: Arc<AtomicUsize>,
    model_a_latencies: Arc<RwLock<Vec<f64>>>,
    model_b_latencies: Arc<RwLock<Vec<f64>>>,
}

impl ABTestRunner {
    pub fn new(
        py: Python,
        model_a_path: &Path,
        model_b_path: &Path,
        config: ABTestConfig,
    ) -> Result<Self> {
        let (model_a, _) = load_compiled_model(py, model_a_path)?;
        let (model_b, _) = load_compiled_model(py, model_b_path)?;

        Ok(Self {
            model_a: Arc::new(RwLock::new(model_a)),
            model_b: Arc::new(RwLock::new(model_b)),
            config,
            model_a_requests: Arc::new(AtomicUsize::new(0)),
            model_b_requests: Arc::new(AtomicUsize::new(0)),
            model_a_successes: Arc::new(AtomicUsize::new(0)),
            model_b_successes: Arc::new(AtomicUsize::new(0)),
            model_a_latencies: Arc::new(RwLock::new(Vec::new())),
            model_b_latencies: Arc::new(RwLock::new(Vec::new())),
        })
    }

    pub async fn predict(&self, input: &str) -> Result<(String, String)> {
        let mut rng = rand::thread_rng();
        let use_model_a = rng.gen::<f64>() < self.config.traffic_split;

        let start = Instant::now();

        let (result, model_id) = if use_model_a {
            let model = self.model_a.read().await;
            let res = Python::with_gil(|py| {
                model.as_ref(py).call_method1("forward", ((input,),))
            })?;
            self.model_a_requests.fetch_add(1, Ordering::SeqCst);
            (res, self.config.model_a_id.clone())
        } else {
            let model = self.model_b.read().await;
            let res = Python::with_gil(|py| {
                model.as_ref(py).call_method1("forward", ((input,),))
            })?;
            self.model_b_requests.fetch_add(1, Ordering::SeqCst);
            (res, self.config.model_b_id.clone())
        };

        let latency = start.elapsed().as_secs_f64() * 1000.0;

        // Record latency
        if use_model_a {
            self.model_a_latencies.write().await.push(latency);
        } else {
            self.model_b_latencies.write().await.push(latency);
        }

        let answer = Python::with_gil(|py| {
            result.as_ref(py).getattr("answer")?.extract::<String>()
        })?;

        Ok((answer, model_id))
    }

    pub fn record_success(&self, model_id: &str) {
        if model_id == self.config.model_a_id {
            self.model_a_successes.fetch_add(1, Ordering::SeqCst);
        } else if model_id == self.config.model_b_id {
            self.model_b_successes.fetch_add(1, Ordering::SeqCst);
        }
    }

    pub async fn get_statistics(&self) -> ABTestStats {
        let a_requests = self.model_a_requests.load(Ordering::SeqCst);
        let b_requests = self.model_b_requests.load(Ordering::SeqCst);
        let a_successes = self.model_a_successes.load(Ordering::SeqCst);
        let b_successes = self.model_b_successes.load(Ordering::SeqCst);

        let a_latencies = self.model_a_latencies.read().await;
        let b_latencies = self.model_b_latencies.read().await;

        let a_success_rate = if a_requests > 0 {
            a_successes as f64 / a_requests as f64
        } else {
            0.0
        };

        let b_success_rate = if b_requests > 0 {
            b_successes as f64 / b_requests as f64
        } else {
            0.0
        };

        let a_avg_latency = if !a_latencies.is_empty() {
            a_latencies.iter().sum::<f64>() / a_latencies.len() as f64
        } else {
            0.0
        };

        let b_avg_latency = if !b_latencies.is_empty() {
            b_latencies.iter().sum::<f64>() / b_latencies.len() as f64
        } else {
            0.0
        };

        // Calculate statistical significance
        let is_significant = self.is_statistically_significant(
            a_successes,
            a_requests,
            b_successes,
            b_requests,
        );

        ABTestStats {
            model_a_id: self.config.model_a_id.clone(),
            model_b_id: self.config.model_b_id.clone(),
            model_a_requests: a_requests,
            model_b_requests: b_requests,
            model_a_success_rate,
            model_b_success_rate,
            model_a_avg_latency,
            model_b_avg_latency,
            total_requests: a_requests + b_requests,
            is_statistically_significant: is_significant,
            confidence_level: self.config.confidence_level,
        }
    }

    fn is_statistically_significant(
        &self,
        a_successes: usize,
        a_total: usize,
        b_successes: usize,
        b_total: usize,
    ) -> bool {
        // Simple Z-test for proportions
        if a_total < self.config.min_sample_size || b_total < self.config.min_sample_size {
            return false;
        }

        let p_a = a_successes as f64 / a_total as f64;
        let p_b = b_successes as f64 / b_total as f64;

        let p_pool = (a_successes + b_successes) as f64 / (a_total + b_total) as f64;

        let se = (p_pool * (1.0 - p_pool) * (1.0 / a_total as f64 + 1.0 / b_total as f64)).sqrt();

        if se == 0.0 {
            return false;
        }

        let z_score = ((p_a - p_b) / se).abs();

        // For 95% confidence, critical value is ~1.96
        let critical_value = match self.config.confidence_level {
            x if x >= 0.99 => 2.576,
            x if x >= 0.95 => 1.96,
            x if x >= 0.90 => 1.645,
            _ => 1.96,
        };

        z_score > critical_value
    }
}

#[derive(Debug, Serialize, Deserialize)]
pub struct ABTestStats {
    pub model_a_id: String,
    pub model_b_id: String,
    pub model_a_requests: usize,
    pub model_b_requests: usize,
    pub model_a_success_rate: f64,
    pub model_b_success_rate: f64,
    pub model_a_avg_latency: f64,
    pub model_b_avg_latency: f64,
    pub total_requests: usize,
    pub is_statistically_significant: bool,
    pub confidence_level: f64,
}

impl ABTestStats {
    pub fn print_report(&self) {
        println!("\n╔═══════════════════════════════════╗");
        println!("║   A/B Test Results                ║");
        println!("╚═══════════════════════════════════╝");
        println!("\nModel A: {}", self.model_a_id);
        println!("  Requests: {}", self.model_a_requests);
        println!("  Success Rate: {:.2}%", self.model_a_success_rate * 100.0);
        println!("  Avg Latency: {:.2}ms", self.model_a_avg_latency);

        println!("\nModel B: {}", self.model_b_id);
        println!("  Requests: {}", self.model_b_requests);
        println!("  Success Rate: {:.2}%", self.model_b_success_rate * 100.0);
        println!("  Avg Latency: {:.2}ms", self.model_b_avg_latency);

        println!("\nStatistical Significance:");
        if self.is_statistically_significant {
            let winner = if self.model_a_success_rate > self.model_b_success_rate {
                &self.model_a_id
            } else {
                &self.model_b_id
            };
            println!("  ✓ Significant at {:.0}% confidence", self.confidence_level * 100.0);
            println!("  Winner: {}", winner);
        } else {
            println!("  ✗ Not statistically significant");
            println!("  Need more samples for conclusive results");
        }
    }
}
```

---

## Deployment Pipelines

### Complete CI/CD Pipeline Example

**GitHub Actions Workflow**:

```yaml
# .github/workflows/optimize-and-deploy.yml
name: DSPy Model Optimization and Deployment

on:
  push:
    branches: [main]
  workflow_dispatch:
    inputs:
      optimizer:
        description: 'Optimizer to use'
        required: true
        default: 'MIPROv2'
        type: choice
        options:
          - BootstrapFewShot
          - MIPROv2
          - COPRO

jobs:
  optimize:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Setup Rust
        uses: actions-rs/toolchain@v1
        with:
          toolchain: stable

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install dspy-ai openai anthropic
          cargo build --release

      - name: Run optimization
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        run: |
          cargo run --release -- optimize \
            --model-id qa-model \
            --optimizer ${{ github.event.inputs.optimizer || 'MIPROv2' }} \
            --train-data data/train.jsonl

      - name: Evaluate model
        run: |
          cargo run --release -- evaluate \
            --model-path ./models/qa-model/latest \
            --test-data data/test.jsonl

      - name: Check quality gate
        run: |
          # Parse evaluation results
          ACCURACY=$(jq '.accuracy' ./models/qa-model/latest/eval_report.json)
          if (( $(echo "$ACCURACY < 0.85" | bc -l) )); then
            echo "❌ Model accuracy $ACCURACY below threshold 0.85"
            exit 1
          fi
          echo "✓ Quality gate passed: accuracy $ACCURACY"

      - name: Upload model artifacts
        uses: actions/upload-artifact@v3
        with:
          name: optimized-model
          path: ./models/qa-model/latest/

  deploy-staging:
    needs: optimize
    runs-on: ubuntu-latest
    steps:
      - name: Download model
        uses: actions/download-artifact@v3
        with:
          name: optimized-model
          path: ./model

      - name: Deploy to staging
        run: |
          # Deploy to staging environment
          echo "Deploying to staging..."

  ab-test:
    needs: deploy-staging
    runs-on: ubuntu-latest
    steps:
      - name: Run A/B test
        run: |
          cargo run --release -- ab-test \
            --model-a ./models/production/current \
            --model-b ./model \
            --split 0.1  # 10% traffic to new model

  deploy-production:
    needs: ab-test
    runs-on: ubuntu-latest
    if: success()
    steps:
      - name: Promote to production
        run: |
          cargo run --release -- promote \
            --model-id qa-model \
            --version $(cat ./model/metadata.json | jq -r '.version')
```

---

## Rollback Strategies

### Safe Deployment with Rollback

```rust
use std::fs;
use std::path::{Path, PathBuf};

#[derive(Debug)]
pub struct DeploymentManager {
    registry: ModelRegistry,
    production_symlink: PathBuf,
    rollback_history: Vec<DeploymentRecord>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DeploymentRecord {
    pub model_id: String,
    pub version: Version,
    pub deployed_at: String,
    pub replaced_version: Option<Version>,
    pub rollback_available: bool,
}

impl DeploymentManager {
    pub fn new(registry: ModelRegistry, production_dir: PathBuf) -> Self {
        Self {
            registry,
            production_symlink: production_dir.join("current"),
            rollback_history: Vec::new(),
        }
    }

    pub fn deploy(
        &mut self,
        model_id: &str,
        version: &Version,
    ) -> Result<()> {
        // Get model to deploy
        let model_version = self.registry.models.get(model_id)
            .and_then(|versions| versions.iter().find(|v| &v.version == version))
            .context("Model version not found")?;

        // Check if there's a current production model
        let previous_version = if self.production_symlink.exists() {
            let current_path = fs::read_link(&self.production_symlink)?;
            Some(self.extract_version_from_path(&current_path)?)
        } else {
            None
        };

        // Create deployment record
        let record = DeploymentRecord {
            model_id: model_id.to_string(),
            version: version.clone(),
            deployed_at: Utc::now().to_rfc3339(),
            replaced_version: previous_version.clone(),
            rollback_available: previous_version.is_some(),
        };

        // Update symlink
        if self.production_symlink.exists() {
            fs::remove_file(&self.production_symlink)?;
        }

        std::os::unix::fs::symlink(&model_version.path, &self.production_symlink)?;

        // Record deployment
        self.rollback_history.push(record.clone());
        self.save_deployment_history()?;

        println!("✓ Deployed {} v{} to production", model_id, version);
        if let Some(prev) = previous_version {
            println!("  Replaced version: {}", prev);
            println!("  Rollback available: yes");
        }

        Ok(())
    }

    pub fn rollback(&mut self) -> Result<()> {
        // Get last two deployments
        if self.rollback_history.len() < 2 {
            anyhow::bail!("No previous deployment to rollback to");
        }

        let current = self.rollback_history.last().unwrap();
        let previous = &self.rollback_history[self.rollback_history.len() - 2];

        if let Some(ref prev_version) = current.replaced_version {
            println!("Rolling back {} from {} to {}",
                current.model_id,
                current.version,
                prev_version
            );

            // Redeploy previous version
            self.deploy(&current.model_id, prev_version)?;

            println!("✓ Rollback complete");
            Ok(())
        } else {
            anyhow::bail!("No previous version available for rollback");
        }
    }

    pub fn list_deployments(&self) -> &[DeploymentRecord] {
        &self.rollback_history
    }

    fn extract_version_from_path(&self, path: &Path) -> Result<Version> {
        let version_str = path.file_name()
            .and_then(|s| s.to_str())
            .context("Invalid path")?;
        Ok(Version::parse(version_str)?)
    }

    fn save_deployment_history(&self) -> Result<()> {
        let history_path = self.production_symlink.parent().unwrap().join("deployment_history.json");
        let history_json = serde_json::to_string_pretty(&self.rollback_history)?;
        fs::write(history_path, history_json)?;
        Ok(())
    }
}
```

---

## Progress Monitoring

### Long-Running Optimization Tracking

```rust
use std::sync::mpsc::{channel, Sender, Receiver};
use std::thread;
use std::time::{Duration, Instant};

#[derive(Debug, Clone, Serialize)]
pub enum OptimizationEvent {
    Started {
        optimizer: String,
        total_steps: Option<usize>,
        timestamp: String,
    },
    Progress {
        step: usize,
        message: String,
        metrics: Option<serde_json::Value>,
        timestamp: String,
    },
    Completed {
        score: f64,
        duration_secs: f64,
        timestamp: String,
    },
    Error {
        error: String,
        timestamp: String,
    },
}

pub struct ProgressMonitor {
    tx: Sender<OptimizationEvent>,
    rx: Receiver<OptimizationEvent>,
    log_file: Option<PathBuf>,
}

impl ProgressMonitor {
    pub fn new(log_file: Option<PathBuf>) -> Self {
        let (tx, rx) = channel();
        Self { tx, rx, log_file }
    }

    pub fn sender(&self) -> Sender<OptimizationEvent> {
        self.tx.clone()
    }

    pub fn monitor(&self) -> Result<()> {
        let start = Instant::now();
        let mut step_count = 0;

        while let Ok(event) = self.rx.recv() {
            // Log to file if configured
            if let Some(ref log_path) = self.log_file {
                let event_json = serde_json::to_string(&event)?;
                let mut file = fs::OpenOptions::new()
                    .create(true)
                    .append(true)
                    .open(log_path)?;
                writeln!(file, "{}", event_json)?;
            }

            // Display progress
            match event {
                OptimizationEvent::Started { optimizer, total_steps, .. } => {
                    println!("\n╔═══════════════════════════════════╗");
                    println!("║   Optimization Started            ║");
                    println!("╚═══════════════════════════════════╝");
                    println!("Optimizer: {}", optimizer);
                    if let Some(steps) = total_steps {
                        println!("Total steps: {}", steps);
                    }
                    println!("");
                },
                OptimizationEvent::Progress { step, message, metrics, .. } => {
                    step_count = step;
                    print!("\r[Step {}] {}", step, message);
                    if let Some(m) = metrics {
                        print!(" | Metrics: {}", m);
                    }
                    std::io::stdout().flush()?;
                },
                OptimizationEvent::Completed { score, duration_secs, .. } => {
                    println!("\n\n╔═══════════════════════════════════╗");
                    println!("║   Optimization Complete           ║");
                    println!("╚═══════════════════════════════════╝");
                    println!("Final Score: {:.4}", score);
                    println!("Duration: {:.2}s", duration_secs);
                    println!("Total Steps: {}", step_count);
                    break;
                },
                OptimizationEvent::Error { error, .. } => {
                    eprintln!("\n\n❌ Optimization Error:");
                    eprintln!("{}", error);
                    break;
                },
            }
        }

        Ok(())
    }
}

// Example usage in optimization
pub fn run_optimization_with_monitoring(
    config: OptimizationConfig,
) -> Result<Py<PyAny>> {
    let monitor = ProgressMonitor::new(Some(PathBuf::from("optimization.log")));
    let progress_tx = monitor.sender();

    // Start monitoring in background
    let monitor_handle = thread::spawn(move || {
        monitor.monitor().unwrap();
    });

    // Run optimization
    let result = Python::with_gil(|py| {
        // Send start event
        progress_tx.send(OptimizationEvent::Started {
            optimizer: config.optimizer.clone(),
            total_steps: Some(100),
            timestamp: Utc::now().to_rfc3339(),
        })?;

        let start = Instant::now();

        // Run actual optimization (simplified)
        for step in 0..100 {
            // Simulate optimization step
            thread::sleep(Duration::from_millis(100));

            progress_tx.send(OptimizationEvent::Progress {
                step,
                message: format!("Optimizing..."),
                metrics: Some(serde_json::json!({
                    "score": 0.5 + (step as f64 / 200.0)
                })),
                timestamp: Utc::now().to_rfc3339(),
            })?;
        }

        let duration = start.elapsed().as_secs_f64();

        // Send completion event
        progress_tx.send(OptimizationEvent::Completed {
            score: 0.95,
            duration_secs: duration,
            timestamp: Utc::now().to_rfc3339(),
        })?;

        Ok::<_, anyhow::Error>(py.None())
    })?;

    // Wait for monitor to finish
    monitor_handle.join().unwrap();

    Ok(result)
}
```

---

## Configuration Management

### Hyperparameter Management

```rust
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OptimizerConfig {
    pub name: String,
    pub hyperparameters: HashMap<String, serde_json::Value>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ConfigPreset {
    pub name: String,
    pub description: String,
    pub optimizer: String,
    pub hyperparameters: HashMap<String, serde_json::Value>,
    pub recommended_for: Vec<String>,
}

pub struct ConfigManager {
    presets: Vec<ConfigPreset>,
}

impl ConfigManager {
    pub fn new() -> Self {
        let presets = vec![
            ConfigPreset {
                name: "quick-bootstrap".to_string(),
                description: "Fast bootstrap for quick iterations".to_string(),
                optimizer: "BootstrapFewShot".to_string(),
                hyperparameters: {
                    let mut map = HashMap::new();
                    map.insert("max_bootstrapped_demos".to_string(), json!(2));
                    map.insert("max_labeled_demos".to_string(), json!(4));
                    map.insert("max_rounds".to_string(), json!(1));
                    map
                },
                recommended_for: vec!["development".to_string(), "prototyping".to_string()],
            },
            ConfigPreset {
                name: "production-mipro".to_string(),
                description: "Production-quality MIPROv2 optimization".to_string(),
                optimizer: "MIPROv2".to_string(),
                hyperparameters: {
                    let mut map = HashMap::new();
                    map.insert("num_candidates".to_string(), json!(20));
                    map.insert("init_temperature".to_string(), json!(1.0));
                    map
                },
                recommended_for: vec!["production".to_string(), "high-stakes".to_string()],
            },
        ];

        Self { presets }
    }

    pub fn get_preset(&self, name: &str) -> Option<&ConfigPreset> {
        self.presets.iter().find(|p| p.name == name)
    }

    pub fn list_presets(&self) -> &[ConfigPreset] {
        &self.presets
    }

    pub fn save_config(&self, config: &OptimizerConfig, path: &Path) -> Result<()> {
        let config_json = serde_json::to_string_pretty(config)?;
        fs::write(path, config_json)?;
        Ok(())
    }

    pub fn load_config(&self, path: &Path) -> Result<OptimizerConfig> {
        let config_json = fs::read_to_string(path)?;
        Ok(serde_json::from_str(&config_json)?)
    }
}
```

---

## Best Practices Summary

### Optimization Workflows

**DO**:
- ✅ Version all optimized models with semantic versioning
- ✅ Save complete metadata with every model
- ✅ Validate models before promoting to production
- ✅ Use quality gates and never skip them
- ✅ Track hyperparameters for reproducibility
- ✅ Monitor optimization progress with structured logging
- ✅ Implement A/B testing before full rollout
- ✅ Keep rollback capability for safe deployments
- ✅ Automate pipelines with CI/CD
- ✅ Document evaluation metrics and thresholds

**DON'T**:
- ❌ Skip evaluation before deployment
- ❌ Overwrite models without versioning
- ❌ Ignore quality gate failures
- ❌ Mix development and production environments
- ❌ Deploy without A/B testing critical models
- ❌ Leave optimizations running without timeouts
- ❌ Forget to save hyperparameter configurations
- ❌ Deploy without rollback strategy

### Performance

- Use async Rust for parallel evaluation
- Cache loaded models to avoid repeated loading
- Set reasonable timeouts for long-running optimizations
- Monitor memory usage during optimization
- Use progress tracking for visibility

### Production Deployment

- Implement blue-green deployments
- Use canary releases for gradual rollout
- Monitor model performance in production
- Set up alerts for quality degradation
- Maintain deployment history for auditing

---

**Version**: 1.0.0
**Last Updated**: 2025-10-30
