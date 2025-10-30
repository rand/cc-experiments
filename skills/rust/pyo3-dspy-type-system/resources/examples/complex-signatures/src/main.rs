use anyhow::Result;
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

/// Input structure for RAG-style queries
/// Represents: question: str, context: List[str], metadata: Dict[str, float]
#[derive(Debug, Clone, Serialize, Deserialize)]
struct RAGInput {
    question: String,
    context: Vec<String>,
    metadata: HashMap<String, f64>,
}

impl RAGInput {
    /// Convert to Python dictionary for DSPy
    fn to_py_dict(&self, py: Python) -> PyResult<PyObject> {
        let dict = PyDict::new_bound(py);

        // Add question string
        dict.set_item("question", &self.question)?;

        // Convert Vec<String> to PyList
        let context_list = PyList::new_bound(py, &self.context);
        dict.set_item("context", context_list)?;

        // Convert HashMap<String, f64> to PyDict
        let metadata_dict = PyDict::new_bound(py);
        for (key, value) in &self.metadata {
            metadata_dict.set_item(key, value)?;
        }
        dict.set_item("metadata", metadata_dict)?;

        Ok(dict.into())
    }
}

/// Output structure for RAG-style responses
/// Represents: answer: str, sources: List[int], confidence: float
#[derive(Debug, Clone, Serialize, Deserialize)]
struct RAGOutput {
    answer: String,
    sources: Vec<i64>,
    confidence: f64,
}

impl RAGOutput {
    /// Extract from Python prediction object
    fn from_py_prediction(_py: Python, prediction: &Bound<'_, PyAny>) -> PyResult<Self> {
        // Extract answer string
        let answer: String = prediction
            .getattr("answer")?
            .extract()?;

        // Extract sources list
        let sources_py = prediction.getattr("sources")?;
        let sources_list = sources_py.downcast::<PyList>()?;
        let mut sources = Vec::new();
        for item in sources_list.iter() {
            let source: i64 = item.extract()?;
            sources.push(source);
        }

        // Extract confidence float
        let confidence: f64 = prediction
            .getattr("confidence")?
            .extract()?;

        Ok(RAGOutput {
            answer,
            sources,
            confidence,
        })
    }
}

/// Execute a RAG query with complex nested types
fn execute_rag_query(input: &RAGInput) -> Result<()> {
    Python::with_gil(|py| {
        println!("\n{}", "=".repeat(60));
        println!("Query: {}", input.question);
        println!("Context passages: {}", input.context.len());
        println!("Metadata fields: {}", input.metadata.len());
        println!("{}\n", "=".repeat(60));

        // Import DSPy
        let dspy = py.import_bound("dspy")?;

        // Create mock prediction for demonstration
        // In real usage, this would come from a DSPy module
        let prediction_class = dspy.getattr("Prediction")?;

        // Build prediction with complex output
        let kwargs = PyDict::new_bound(py);

        // Mock answer based on question
        let answer = if input.question.contains("quantum") {
            "Quantum entanglement is a phenomenon where particles become correlated in such a way that the quantum state of one cannot be described independently of the others."
        } else if input.question.contains("Renaissance") {
            "The Renaissance began in 14th century Italy, particularly in Florence, marking a period of renewed interest in classical learning and arts."
        } else if input.question.contains("photosynthesis") {
            "Photosynthesis is the process by which plants convert light energy into chemical energy stored in glucose molecules."
        } else {
            "Based on the provided context, the answer requires careful analysis of multiple sources."
        };
        kwargs.set_item("answer", answer)?;

        // Mock sources (indices of relevant context passages)
        let sources = PyList::new_bound(py, &[0i64, 2i64]);
        kwargs.set_item("sources", sources)?;

        // Mock confidence based on metadata
        let avg_score = input.metadata.values().sum::<f64>() / input.metadata.len() as f64;
        kwargs.set_item("confidence", avg_score)?;

        let prediction = prediction_class.call((), Some(&kwargs))?;

        // Convert input to Python dict (for demonstration)
        let _input_dict = input.to_py_dict(py)?;
        println!("Input (serialized):");
        println!("{}", serde_json::to_string_pretty(&input)?);

        // Extract output
        let output = RAGOutput::from_py_prediction(py, &prediction)?;

        println!("\nOutput (extracted):");
        println!("{}", serde_json::to_string_pretty(&output)?);

        // Validate output
        println!("\nValidation:");
        println!("  Answer length: {} chars", output.answer.len());
        println!("  Sources referenced: {:?}", output.sources);
        println!("  Confidence score: {:.2}%", output.confidence * 100.0);

        if output.confidence > 0.8 {
            println!("  Quality: HIGH CONFIDENCE ✓");
        } else if output.confidence > 0.6 {
            println!("  Quality: MODERATE CONFIDENCE ~");
        } else {
            println!("  Quality: LOW CONFIDENCE ⚠");
        }

        Ok(())
    })
}

fn main() -> Result<()> {
    println!("\nComplex Signatures: Multi-field with Nested Types");
    println!("Signature: question: str, context: List[str], metadata: Dict[str, float] -> answer: str, sources: List[int], confidence: float\n");

    // Example 1: Scientific query with high-quality context
    let query1 = RAGInput {
        question: "What is quantum entanglement?".to_string(),
        context: vec![
            "Quantum entanglement is a physical phenomenon that occurs when pairs or groups of particles interact in ways such that the quantum state of each particle cannot be described independently.".to_string(),
            "Einstein famously called quantum entanglement 'spooky action at a distance' because it seemed to violate the principle of locality.".to_string(),
            "Entangled particles remain connected so that actions performed on one affect the other, even when separated by large distances.".to_string(),
            "The phenomenon has been experimentally verified and is now used in quantum computing and quantum cryptography.".to_string(),
        ],
        metadata: [
            ("relevance".to_string(), 0.95),
            ("recency".to_string(), 0.87),
            ("authority".to_string(), 0.92),
            ("coverage".to_string(), 0.88),
        ]
        .iter()
        .cloned()
        .collect(),
    };

    execute_rag_query(&query1)?;

    // Example 2: Historical query with moderate context
    let query2 = RAGInput {
        question: "When did the Renaissance begin?".to_string(),
        context: vec![
            "The Renaissance was a period in European history marking the transition from the Middle Ages to modernity.".to_string(),
            "The Renaissance began in 14th century Italy, centered in Florence.".to_string(),
            "Florence became a major center of Renaissance culture due to wealthy patronage and trade connections.".to_string(),
        ],
        metadata: [
            ("relevance".to_string(), 0.88),
            ("recency".to_string(), 0.45),
            ("authority".to_string(), 0.91),
            ("coverage".to_string(), 0.76),
        ]
        .iter()
        .cloned()
        .collect(),
    };

    execute_rag_query(&query2)?;

    // Example 3: Biological query with sparse context
    let query3 = RAGInput {
        question: "How does photosynthesis work?".to_string(),
        context: vec![
            "Photosynthesis is the process used by plants to convert light energy into chemical energy.".to_string(),
            "The process occurs in chloroplasts and involves chlorophyll molecules.".to_string(),
        ],
        metadata: [
            ("relevance".to_string(), 0.72),
            ("recency".to_string(), 0.65),
            ("authority".to_string(), 0.83),
            ("coverage".to_string(), 0.58),
        ]
        .iter()
        .cloned()
        .collect(),
    };

    execute_rag_query(&query3)?;

    println!("\n{}", "=".repeat(60));
    println!("Complex Signature Demonstration Complete");
    println!("{}\n", "=".repeat(60));

    Ok(())
}
