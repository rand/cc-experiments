use anyhow::Result;
use pyo3::prelude::*;
use pyo3::types::{PyAny, PyDict};
use serde::Deserialize;
use std::marker::PhantomData;

// ============================================================================
// Trait Definitions for Type Safety
// ============================================================================

/// Trait for types that can be converted to Python dictionaries.
/// This constrains what types can be used as inputs to TypedPredictor.
pub trait ToPyDict {
    fn to_py_dict<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyDict>>;
}

/// Trait for types that can be constructed from Python objects.
/// This constrains what types can be used as outputs from TypedPredictor.
pub trait FromPyAny: Sized {
    fn from_py_any(obj: &Bound<'_, PyAny>) -> PyResult<Self>;
}

// ============================================================================
// Generic TypedPredictor with PhantomData
// ============================================================================

/// Generic wrapper around DSPy predictors with compile-time type safety.
///
/// # Type Parameters
/// - `I`: Input type (must implement `ToPyDict`)
/// - `O`: Output type (must implement `FromPyAny`)
///
/// # PhantomData Usage
/// `PhantomData<(I, O)>` provides:
/// - Zero runtime size (ZST - Zero-Sized Type)
/// - Compile-time type tracking
/// - Proper variance and drop semantics
/// - Type safety without runtime overhead
pub struct TypedPredictor<I, O> {
    predictor: Py<PyAny>,
    signature: String,
    /// PhantomData tells the compiler to track I and O types even though
    /// they're not actually stored in the struct. This enables:
    /// - Type checking at compile time
    /// - Proper lifetime and variance inference
    /// - Zero-cost abstraction (no runtime storage)
    _phantom: PhantomData<(I, O)>,
}

impl<I, O> TypedPredictor<I, O>
where
    I: ToPyDict,
    O: FromPyAny,
{
    /// Create a new builder for constructing a TypedPredictor.
    ///
    /// # Example
    /// ```
    /// let predictor: TypedPredictor<QuestionInput, AnswerOutput> =
    ///     TypedPredictor::builder()
    ///         .signature("question -> answer")
    ///         .build()?;
    /// ```
    pub fn builder() -> TypedPredictorBuilder<I, O> {
        TypedPredictorBuilder {
            signature: None,
            max_retries: None,
            _phantom: PhantomData,
        }
    }

    /// Predict output from input using the configured DSPy predictor.
    ///
    /// # Type Safety
    /// The compiler enforces:
    /// - Input must be of type I (checked at compile time)
    /// - Output will be of type O (inferred from context)
    /// - No runtime type checking needed
    ///
    /// # Example
    /// ```
    /// let input = QuestionInput { question: "What is Rust?".to_string() };
    /// let output: AnswerOutput = predictor.predict(&input)?;
    /// ```
    pub fn predict(&self, input: &I) -> Result<O> {
        Python::with_gil(|py| {
            // Convert Rust input to Python dict using trait bound
            let input_dict = input.to_py_dict(py)?;

            println!("[Simulated] Calling DSPy predictor with signature: {}", self.signature);

            // In a real implementation, this would call the actual DSPy predictor
            // For this example, we simulate the call
            let result = self.predictor.call1(py, (input_dict,))?;

            // Convert Python result to Rust output using trait bound
            let result_bound = result.bind(py);
            O::from_py_any(&result_bound)
                .map_err(|e| anyhow::anyhow!("Failed to convert Python result: {}", e))
        })
    }

    /// Get the signature string for this predictor.
    pub fn signature(&self) -> &str {
        &self.signature
    }
}

// ============================================================================
// Builder Pattern for TypedPredictor Construction
// ============================================================================

/// Builder for constructing TypedPredictor instances with optional configuration.
///
/// # Type Parameters
/// The builder maintains the same generic type parameters as TypedPredictor,
/// ensuring type safety throughout the construction process.
pub struct TypedPredictorBuilder<I, O> {
    signature: Option<String>,
    max_retries: Option<u32>,
    /// PhantomData in the builder ensures type parameters flow through
    /// the entire construction chain without runtime cost
    _phantom: PhantomData<(I, O)>,
}

impl<I, O> TypedPredictorBuilder<I, O>
where
    I: ToPyDict,
    O: FromPyAny,
{
    /// Set the DSPy signature for this predictor.
    ///
    /// # Example
    /// ```
    /// builder.signature("question -> answer")
    /// ```
    pub fn signature(mut self, signature: impl Into<String>) -> Self {
        self.signature = Some(signature.into());
        self
    }

    /// Set the maximum number of retries for failed predictions.
    pub fn max_retries(mut self, retries: u32) -> Self {
        self.max_retries = Some(retries);
        self
    }

    /// Build the TypedPredictor instance.
    ///
    /// # Returns
    /// A fully configured TypedPredictor<I, O> with compile-time type guarantees.
    pub fn build(self) -> Result<TypedPredictor<I, O>> {
        let signature = self.signature
            .ok_or_else(|| anyhow::anyhow!("Signature is required"))?;

        Python::with_gil(|py| {
            // For this example, we create a mock Python callable
            // In a real implementation, this would initialize a DSPy predictor
            let mock_predictor = py.eval_bound(
                "lambda x: x",  // Identity function for simulation
                None,
                None,
            )?;

            Ok(TypedPredictor {
                predictor: mock_predictor.unbind(),
                signature,
                _phantom: PhantomData,
            })
        })
    }
}

// ============================================================================
// Example Input Types
// ============================================================================

#[derive(Debug, Clone)]
pub struct QuestionInput {
    pub question: String,
}

impl ToPyDict for QuestionInput {
    fn to_py_dict<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyDict>> {
        let dict = PyDict::new_bound(py);
        dict.set_item("question", &self.question)?;
        Ok(dict)
    }
}

#[derive(Debug, Clone)]
pub struct ClassificationInput {
    pub text: String,
    pub categories: Vec<String>,
}

impl ToPyDict for ClassificationInput {
    fn to_py_dict<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyDict>> {
        let dict = PyDict::new_bound(py);
        dict.set_item("text", &self.text)?;
        dict.set_item("categories", self.categories.clone())?;
        Ok(dict)
    }
}

// ============================================================================
// Example Output Types
// ============================================================================

#[derive(Debug, Clone, Deserialize)]
pub struct AnswerOutput {
    pub answer: String,
}

impl FromPyAny for AnswerOutput {
    fn from_py_any(_obj: &Bound<'_, PyAny>) -> PyResult<Self> {
        // For this example, we simulate the conversion
        // In a real implementation, this would extract data from the Python object
        Ok(AnswerOutput {
            answer: "Paris is the capital of France.".to_string(),
        })
    }
}

#[derive(Debug, Clone, Deserialize)]
pub struct ClassificationOutput {
    pub category: String,
    pub confidence: f64,
}

impl FromPyAny for ClassificationOutput {
    fn from_py_any(_obj: &Bound<'_, PyAny>) -> PyResult<Self> {
        // For this example, we simulate the conversion
        Ok(ClassificationOutput {
            category: "positive".to_string(),
            confidence: 0.95,
        })
    }
}

// ============================================================================
// Demonstration Functions
// ============================================================================

/// Demonstrates basic question answering with type inference.
fn demonstrate_question_answering() -> Result<()> {
    println!("\nQuestion Answering:");

    let input = QuestionInput {
        question: "What is the capital of France?".to_string(),
    };

    // Type annotation on the left guides type inference
    // Compiler knows: I = QuestionInput, O = AnswerOutput
    let predictor: TypedPredictor<QuestionInput, AnswerOutput> =
        TypedPredictor::builder()
            .signature("question -> answer")
            .build()?;

    println!("Input: {:?}", input);

    // Type inference: return type determines O = AnswerOutput
    let output: AnswerOutput = predictor.predict(&input)?;

    println!("Output: {:?}", output);

    Ok(())
}

/// Demonstrates text classification with different types.
fn demonstrate_classification() -> Result<()> {
    println!("\nText Classification:");

    let input = ClassificationInput {
        text: "This movie was absolutely fantastic!".to_string(),
        categories: vec!["positive".to_string(), "negative".to_string()],
    };

    // Different input and output types than question answering
    let predictor: TypedPredictor<ClassificationInput, ClassificationOutput> =
        TypedPredictor::builder()
            .signature("text, categories -> category, confidence")
            .build()?;

    println!("Input: {:?}", input);

    let output: ClassificationOutput = predictor.predict(&input)?;

    println!("Output: {:?}", output);

    Ok(())
}

/// Demonstrates multiple predictors with different type signatures.
fn demonstrate_multiple_predictors() -> Result<()> {
    println!("\nMultiple Predictors:");

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
    let question = QuestionInput {
        question: "What is the capital of France?".to_string(),
    };
    let qa_result = qa_predictor.predict(&question)?;

    let classification = ClassificationInput {
        text: "This movie was absolutely fantastic!".to_string(),
        categories: vec!["positive".to_string(), "negative".to_string()],
    };
    let class_result = class_predictor.predict(&classification)?;

    println!("QA Result: {:?}", qa_result.answer);
    println!("Classification Result: {} (confidence: {:.2}%)",
             class_result.category, class_result.confidence * 100.0);

    Ok(())
}

/// Generic function that works with any TypedPredictor.
///
/// # Type Parameters
/// This function is generic over the input and output types,
/// demonstrating how TypedPredictor enables generic programming.
fn process_batch<I, O>(
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

/// Demonstrates generic functions over typed predictors.
fn demonstrate_generic_processing() -> Result<()> {
    println!("\nGeneric Batch Processing:");

    let predictor: TypedPredictor<QuestionInput, AnswerOutput> =
        TypedPredictor::builder()
            .signature("question -> answer")
            .build()?;

    let questions = vec![
        QuestionInput { question: "What is Rust?".to_string() },
        QuestionInput { question: "What is Python?".to_string() },
    ];

    // Generic function works with any TypedPredictor
    let results = process_batch(&predictor, &questions)?;

    for (i, result) in results.iter().enumerate() {
        println!("Question {}: {:?}", i + 1, result.answer);
    }

    Ok(())
}

// ============================================================================
// Main Entry Point
// ============================================================================

fn main() -> Result<()> {
    println!("=== Typed Predictor Example ===");

    demonstrate_question_answering()?;
    demonstrate_classification()?;
    demonstrate_multiple_predictors()?;
    demonstrate_generic_processing()?;

    println!("\nType Safety Demonstration:");
    println!("- Each predictor enforces its input/output types at compile time");
    println!("- PhantomData provides zero-cost type tracking");
    println!("- Trait bounds ensure only compatible types can be used");
    println!("- Type inference reduces boilerplate while maintaining safety");

    println!("\nSuccess! All examples completed.");

    Ok(())
}

// ============================================================================
// Compile-Time Type Safety Examples (commented out - won't compile)
// ============================================================================

/*
// ERROR: Type mismatch - cannot use ClassificationInput with QuestionInput predictor
fn example_type_error_1() {
    let predictor: TypedPredictor<QuestionInput, AnswerOutput> =
        TypedPredictor::builder().signature("question -> answer").build().unwrap();

    let wrong_input = ClassificationInput {
        text: "test".to_string(),
        categories: vec![],
    };

    // Compilation error: expected QuestionInput, found ClassificationInput
    predictor.predict(&wrong_input).unwrap();
}

// ERROR: Type mismatch - return type doesn't match predictor output type
fn example_type_error_2() {
    let predictor: TypedPredictor<QuestionInput, AnswerOutput> =
        TypedPredictor::builder().signature("question -> answer").build().unwrap();

    let input = QuestionInput { question: "test".to_string() };

    // Compilation error: expected AnswerOutput, trying to assign to ClassificationOutput
    let result: ClassificationOutput = predictor.predict(&input).unwrap();
}

// ERROR: Cannot create TypedPredictor with types that don't implement required traits
fn example_type_error_3() {
    struct InvalidInput; // Doesn't implement ToPyDict
    struct InvalidOutput; // Doesn't implement FromPyAny

    // Compilation error: InvalidInput doesn't implement ToPyDict
    // Compilation error: InvalidOutput doesn't implement FromPyAny
    let predictor: TypedPredictor<InvalidInput, InvalidOutput> =
        TypedPredictor::builder().signature("test").build().unwrap();
}
*/
