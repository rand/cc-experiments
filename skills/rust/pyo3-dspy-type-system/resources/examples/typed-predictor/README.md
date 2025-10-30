# Typed Predictor: Generic DSPy Wrapper with Compile-Time Type Safety

This example demonstrates how to build a **generic, type-safe wrapper** around DSPy predictors using Rust's advanced type system features. The `TypedPredictor<I, O>` struct provides compile-time guarantees about input and output types while maintaining zero runtime overhead.

## Overview

The typed predictor system leverages:
- **Generic type parameters** for input and output types
- **PhantomData** for compile-time type tracking without runtime cost
- **Trait bounds** for controlled type conversions
- **Type inference** for ergonomic call sites
- **Builder pattern** for flexible construction

## Key Concepts

### 1. Generic Type Parameters

```rust
pub struct TypedPredictor<I, O> {
    predictor: Py<PyAny>,
    _phantom: PhantomData<(I, O)>,
}
```

The struct is generic over:
- `I`: Input type (must implement `ToPyDict`)
- `O`: Output type (must implement `FromPyAny`)

### 2. PhantomData for Zero-Cost Abstraction

`PhantomData<(I, O)>` tells the compiler to track types `I` and `O` without storing them:
- **Zero runtime size**: `PhantomData` is a zero-sized type
- **Compile-time safety**: Type checker enforces correct usage
- **Lifetime tracking**: Helps with variance and drop semantics

### 3. Trait Bounds for Type Safety

```rust
pub trait ToPyDict {
    fn to_py_dict(&self, py: Python) -> PyResult<&PyDict>;
}

pub trait FromPyAny: Sized {
    fn from_py_any(obj: &PyAny) -> PyResult<Self>;
}
```

These traits:
- Constrain what types can be used with `TypedPredictor`
- Enable custom serialization logic per type
- Provide clear compilation errors for unsupported types

### 4. Type Inference at Call Sites

```rust
// Compiler infers I = QuestionInput, O = AnswerOutput
let predictor = TypedPredictor::builder()
    .signature("question -> answer")
    .build()?;

let result: AnswerOutput = predictor.predict(&input)?;
```

The return type annotation guides type inference, eliminating redundant type annotations.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│  TypedPredictor<I, O>                                   │
├─────────────────────────────────────────────────────────┤
│  - predictor: Py<PyAny>        (Python object)         │
│  - _phantom: PhantomData<(I,O)> (compile-time only)    │
├─────────────────────────────────────────────────────────┤
│  + builder() -> TypedPredictorBuilder<I, O>            │
│  + predict(&I) -> Result<O>                             │
└─────────────────────────────────────────────────────────┘
                    │
                    │ uses
                    ▼
┌─────────────────────────────────────────────────────────┐
│  Trait Bounds                                           │
├─────────────────────────────────────────────────────────┤
│  I: ToPyDict       (Input → Python Dict)               │
│  O: FromPyAny      (Python Any → Output)               │
└─────────────────────────────────────────────────────────┘
```

## Implementation Details

### Builder Pattern

```rust
pub struct TypedPredictorBuilder<I, O> {
    signature: Option<String>,
    max_retries: Option<u32>,
    _phantom: PhantomData<(I, O)>,
}
```

The builder:
- Provides a fluent API for configuration
- Maintains type parameters throughout construction
- Validates configuration before creating the predictor

### Generic Implementation

```rust
impl<I, O> TypedPredictor<I, O>
where
    I: ToPyDict,
    O: FromPyAny,
{
    pub fn predict(&self, input: &I) -> Result<O> {
        Python::with_gil(|py| {
            let input_dict = input.to_py_dict(py)?;
            let result = self.predictor.call1(py, (input_dict,))?;
            O::from_py_any(result.as_ref(py))
        })
    }
}
```

Key points:
- `where` clause specifies trait bounds
- Generic implementation works for all valid `I` and `O` types
- Type safety enforced at compile time, no runtime checks needed

### Variance and Drop Semantics

`PhantomData<(I, O)>` affects how the compiler treats `TypedPredictor`:
- **Invariant** over both `I` and `O` (default for tuples)
- Drop checker considers `I` and `O` even though they're not stored
- Prevents unsafe lifetime issues in generic contexts

## Example Types

### Input Types

```rust
#[derive(Debug, Clone)]
pub struct QuestionInput {
    pub question: String,
}

#[derive(Debug, Clone)]
pub struct ClassificationInput {
    pub text: String,
    pub categories: Vec<String>,
}
```

### Output Types

```rust
#[derive(Debug, Clone, Deserialize)]
pub struct AnswerOutput {
    pub answer: String,
}

#[derive(Debug, Clone, Deserialize)]
pub struct ClassificationOutput {
    pub category: String,
    pub confidence: f64,
}
```

## Type Safety Guarantees

### Compile-Time Error Examples

```rust
// ERROR: QuestionInput doesn't implement ToPyDict
let predictor: TypedPredictor<QuestionInput, String> =
    TypedPredictor::builder().build()?;

// ERROR: Type mismatch - expected AnswerOutput, got ClassificationOutput
let predictor: TypedPredictor<QuestionInput, AnswerOutput> =
    TypedPredictor::builder().build()?;
let result: ClassificationOutput = predictor.predict(&input)?;

// ERROR: Cannot call predict with wrong input type
let question_predictor: TypedPredictor<QuestionInput, AnswerOutput> =
    TypedPredictor::builder().build()?;
let classification_input = ClassificationInput { ... };
question_predictor.predict(&classification_input)?; // Won't compile!
```

### Zero Runtime Overhead

The type parameters and `PhantomData` are erased at compile time:
- No additional memory allocation
- No runtime type checks
- No vtable lookups
- Same performance as untyped code with compile-time safety

## Usage Examples

### Basic Question Answering

```rust
let input = QuestionInput {
    question: "What is the capital of France?".to_string(),
};

let predictor: TypedPredictor<QuestionInput, AnswerOutput> =
    TypedPredictor::builder()
        .signature("question -> answer")
        .build()?;

let output = predictor.predict(&input)?;
println!("Answer: {}", output.answer);
```

### Text Classification

```rust
let input = ClassificationInput {
    text: "This movie was absolutely fantastic!".to_string(),
    categories: vec!["positive".to_string(), "negative".to_string()],
};

let predictor: TypedPredictor<ClassificationInput, ClassificationOutput> =
    TypedPredictor::builder()
        .signature("text, categories -> category, confidence")
        .build()?;

let output = predictor.predict(&input)?;
println!("Category: {} (confidence: {:.2}%)",
         output.category, output.confidence * 100.0);
```

### Multiple Predictors with Different Types

```rust
// Question answering predictor
let qa_predictor: TypedPredictor<QuestionInput, AnswerOutput> =
    TypedPredictor::builder()
        .signature("question -> answer")
        .build()?;

// Classification predictor
let class_predictor: TypedPredictor<ClassificationInput, ClassificationOutput> =
    TypedPredictor::builder()
        .signature("text, categories -> category, confidence")
        .build()?;

// Each predictor maintains its own type safety
let qa_result = qa_predictor.predict(&question)?;
let class_result = class_predictor.predict(&classification)?;
```

## Advanced Features

### Type Inference

```rust
// Compiler infers types from context
fn process_question(predictor: &TypedPredictor<QuestionInput, AnswerOutput>)
    -> Result<String>
{
    let input = QuestionInput {
        question: "What is Rust?".to_string(),
    };

    // Return type guides inference - no explicit type annotation needed
    let output = predictor.predict(&input)?;
    Ok(output.answer)
}
```

### Generic Functions Over Predictors

```rust
fn predict_batch<I, O>(
    predictor: &TypedPredictor<I, O>,
    inputs: &[I],
) -> Result<Vec<O>>
where
    I: ToPyDict + Clone,
    O: FromPyAny,
{
    inputs.iter()
        .map(|input| predictor.predict(input))
        .collect()
}
```

### Trait Implementations

Custom types automatically work with `TypedPredictor` by implementing the required traits:

```rust
impl ToPyDict for CustomInput {
    fn to_py_dict(&self, py: Python) -> PyResult<&PyDict> {
        let dict = PyDict::new(py);
        // Custom serialization logic
        Ok(dict)
    }
}

impl FromPyAny for CustomOutput {
    fn from_py_any(obj: &PyAny) -> PyResult<Self> {
        // Custom deserialization logic
        Ok(CustomOutput { ... })
    }
}
```

## Benefits

1. **Compile-Time Type Safety**: Catch type errors at compile time, not runtime
2. **Zero Cost**: No runtime overhead compared to untyped code
3. **Ergonomic**: Type inference reduces boilerplate
4. **Extensible**: Easy to add new input/output types
5. **Maintainable**: Types document expected behavior
6. **Refactoring-Friendly**: Compiler helps track type changes

## Build and Run

```bash
# Check for type errors
cargo check

# Build the example
cargo build --release

# Run the example (requires Python 3.9+ in PATH)
cargo run --release

# Note: If you encounter library loading errors, ensure Python is properly installed:
# - macOS: brew install python@3.11
# - Linux: Use your package manager (apt, dnf, etc.)
# - Set PYO3_PYTHON environment variable if needed:
#   export PYO3_PYTHON=/path/to/python3
#   cargo build --release
```

## Expected Output

```
=== Typed Predictor Example ===

Question Answering:
Input: QuestionInput { question: "What is the capital of France?" }
[Simulated] Calling DSPy predictor with signature: question -> answer
Output: AnswerOutput { answer: "Paris is the capital of France." }

Text Classification:
Input: ClassificationInput { text: "This movie was absolutely fantastic!", categories: ["positive", "negative"] }
[Simulated] Calling DSPy predictor with signature: text, categories -> category, confidence
Output: ClassificationOutput { category: "positive", confidence: 0.95 }

Multiple Predictors:
QA Result: "Paris is the capital of France."
Classification Result: positive (confidence: 95.00%)

Type Safety Demonstration:
- Each predictor enforces its input/output types at compile time
- PhantomData provides zero-cost type tracking
- Trait bounds ensure only compatible types can be used
- Type inference reduces boilerplate while maintaining safety

Success! All examples completed.
```

## Learning Outcomes

After studying this example, you'll understand:

1. **Generic Programming**: How to design APIs with generic type parameters
2. **PhantomData**: When and why to use phantom types
3. **Trait Bounds**: How to constrain generic types with trait requirements
4. **Type Inference**: How Rust's type system guides inference
5. **Zero-Cost Abstractions**: Building safe APIs without runtime overhead
6. **Builder Pattern**: Fluent APIs for complex object construction
7. **Type Safety**: Leveraging the compiler to prevent runtime errors

## References

- [PhantomData documentation](https://doc.rust-lang.org/std/marker/struct.PhantomData.html)
- [Generic Types, Traits, and Lifetimes](https://doc.rust-lang.org/book/ch10-00-generics.html)
- [Advanced Types](https://doc.rust-lang.org/book/ch19-04-advanced-types.html)
- [PyO3 Guide](https://pyo3.rs/)

## Next Steps

Explore other examples:
- `phantom-lifetime/` - PhantomData for lifetime tracking
- `typed-signatures/` - Type-level DSPy signatures
- `const-generics/` - Compile-time array sizes
- `gat-patterns/` - Generic Associated Types
