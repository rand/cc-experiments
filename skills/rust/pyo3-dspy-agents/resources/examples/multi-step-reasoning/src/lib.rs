//! Multi-Step Reasoning with DSPy
//!
//! This module implements complex reasoning through problem decomposition,
//! sub-question generation and solving, and answer synthesis.
//!
//! # Architecture
//!
//! The reasoning system follows a three-phase approach:
//! 1. **Decompose**: Break complex questions into manageable sub-questions
//! 2. **Solve**: Answer each sub-question using ReAct reasoning
//! 3. **Synthesize**: Combine sub-answers into a coherent final answer
//!
//! # Example
//!
//! ```no_run
//! use multi_step_reasoning::{MultiStepReasoner, ReasoningConfig};
//!
//! let reasoner = MultiStepReasoner::new(ReasoningConfig::default())?;
//! let chain = reasoner.reason(
//!     "What factors contributed to the fall of the Roman Empire \
//!      and how did they interact?"
//! )?;
//! println!("{}", chain.visualize());
//! ```

use pyo3::prelude::*;
use pyo3::types::PyDict;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::fmt;
use thiserror::Error;

/// Errors that can occur during reasoning
#[derive(Error, Debug)]
pub enum ReasoningError {
    #[error("Python error: {0}")]
    PythonError(#[from] PyErr),

    #[error("Invalid reasoning step: {0}")]
    InvalidStep(String),

    #[error("Max depth exceeded: {0}")]
    MaxDepthExceeded(usize),

    #[error("No conclusion reached")]
    NoConclusion,

    #[error("Decomposition failed: {0}")]
    DecompositionFailed(String),

    #[error("Synthesis failed: {0}")]
    SynthesisFailed(String),
}

/// Result type for reasoning operations
pub type Result<T> = std::result::Result<T, ReasoningError>;

/// A single step in the reasoning chain
///
/// Each step represents either a decomposition, a sub-question solution,
/// or a synthesis operation.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ReasoningStep {
    /// Sequential step number (1-indexed)
    pub step_number: usize,

    /// The question or sub-question being addressed
    pub question: String,

    /// The reasoning thought process
    pub thought: String,

    /// Optional action taken (e.g., "solve", "decompose", "synthesize")
    pub action: Option<String>,

    /// Observation from executing the action
    pub observation: Option<String>,

    /// Conclusion drawn from this step
    pub conclusion: Option<String>,

    /// Confidence score (0.0-1.0)
    pub confidence: Option<f64>,

    /// Metadata for this step
    pub metadata: HashMap<String, String>,
}

impl ReasoningStep {
    /// Create a new reasoning step
    pub fn new(step_number: usize, question: String) -> Self {
        Self {
            step_number,
            question,
            thought: String::new(),
            action: None,
            observation: None,
            conclusion: None,
            confidence: None,
            metadata: HashMap::new(),
        }
    }

    /// Add a thought to this step
    pub fn with_thought(mut self, thought: impl Into<String>) -> Self {
        self.thought = thought.into();
        self
    }

    /// Add an action to this step
    pub fn with_action(mut self, action: impl Into<String>) -> Self {
        self.action = Some(action.into());
        self
    }

    /// Add an observation to this step
    pub fn with_observation(mut self, observation: impl Into<String>) -> Self {
        self.observation = Some(observation.into());
        self
    }

    /// Add a conclusion to this step
    pub fn with_conclusion(mut self, conclusion: impl Into<String>) -> Self {
        self.conclusion = Some(conclusion.into());
        self
    }

    /// Add a confidence score
    pub fn with_confidence(mut self, confidence: f64) -> Self {
        self.confidence = Some(confidence.clamp(0.0, 1.0));
        self
    }

    /// Add metadata
    pub fn with_metadata(mut self, key: impl Into<String>, value: impl Into<String>) -> Self {
        self.metadata.insert(key.into(), value.into());
        self
    }

    /// Format this step as a string
    pub fn format(&self) -> String {
        let mut output = format!("Step {}: {}\n", self.step_number, self.question);

        if !self.thought.is_empty() {
            output.push_str(&format!("  Thought: {}\n", self.thought));
        }

        if let Some(action) = &self.action {
            output.push_str(&format!("  Action: {}\n", action));
        }

        if let Some(observation) = &self.observation {
            output.push_str(&format!("  Observation: {}\n", observation));
        }

        if let Some(conclusion) = &self.conclusion {
            output.push_str(&format!("  Conclusion: {}\n", conclusion));
        }

        if let Some(confidence) = self.confidence {
            output.push_str(&format!("  Confidence: {:.2}%\n", confidence * 100.0));
        }

        output
    }
}

/// Complete reasoning chain with all steps and final conclusion
///
/// The chain tracks the entire reasoning process from initial question
/// through decomposition, solving, and synthesis.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ReasoningChain {
    /// All reasoning steps in order
    pub steps: Vec<ReasoningStep>,

    /// The final synthesized conclusion
    pub final_conclusion: Option<String>,

    /// Overall confidence in the conclusion
    pub overall_confidence: Option<f64>,

    /// Metadata about the reasoning process
    pub metadata: HashMap<String, String>,
}

impl ReasoningChain {
    /// Create a new empty reasoning chain
    pub fn new() -> Self {
        Self {
            steps: Vec::new(),
            final_conclusion: None,
            overall_confidence: None,
            metadata: HashMap::new(),
        }
    }

    /// Add a step to the chain
    pub fn add_step(&mut self, step: ReasoningStep) {
        self.steps.push(step);
    }

    /// Set the final conclusion
    pub fn set_conclusion(&mut self, conclusion: impl Into<String>) {
        self.final_conclusion = Some(conclusion.into());
    }

    /// Set overall confidence
    pub fn set_confidence(&mut self, confidence: f64) {
        self.overall_confidence = Some(confidence.clamp(0.0, 1.0));
    }

    /// Add metadata
    pub fn add_metadata(&mut self, key: impl Into<String>, value: impl Into<String>) {
        self.metadata.insert(key.into(), value.into());
    }

    /// Get the number of steps
    pub fn len(&self) -> usize {
        self.steps.len()
    }

    /// Check if the chain is empty
    pub fn is_empty(&self) -> bool {
        self.steps.is_empty()
    }

    /// Visualize the reasoning chain as a formatted string
    pub fn visualize(&self) -> String {
        let mut output = String::from("=== REASONING CHAIN ===\n\n");

        for step in &self.steps {
            output.push_str(&step.format());
            output.push('\n');
        }

        output.push_str("=== FINAL CONCLUSION ===\n");
        if let Some(conclusion) = &self.final_conclusion {
            output.push_str(conclusion);
            output.push('\n');
        } else {
            output.push_str("(No conclusion reached)\n");
        }

        if let Some(confidence) = self.overall_confidence {
            output.push_str(&format!("\nOverall Confidence: {:.2}%\n", confidence * 100.0));
        }

        output
    }

    /// Export to JSON
    pub fn to_json(&self) -> Result<String> {
        serde_json::to_string_pretty(self)
            .map_err(|e| ReasoningError::InvalidStep(format!("JSON serialization failed: {}", e)))
    }

    /// Import from JSON
    pub fn from_json(json: &str) -> Result<Self> {
        serde_json::from_str(json)
            .map_err(|e| ReasoningError::InvalidStep(format!("JSON deserialization failed: {}", e)))
    }

    /// Validate the chain
    pub fn validate(&self) -> Result<()> {
        if self.steps.is_empty() {
            return Err(ReasoningError::InvalidStep("Chain has no steps".to_string()));
        }

        if self.final_conclusion.is_none() {
            return Err(ReasoningError::NoConclusion);
        }

        // Check step numbering
        for (idx, step) in self.steps.iter().enumerate() {
            if step.step_number != idx + 1 {
                return Err(ReasoningError::InvalidStep(
                    format!("Step numbering inconsistent at index {}", idx)
                ));
            }
        }

        Ok(())
    }
}

impl Default for ReasoningChain {
    fn default() -> Self {
        Self::new()
    }
}

impl fmt::Display for ReasoningChain {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}", self.visualize())
    }
}

/// Configuration for the multi-step reasoner
#[derive(Debug, Clone)]
pub struct ReasoningConfig {
    /// Maximum reasoning depth
    pub max_depth: usize,

    /// Maximum number of sub-questions
    pub max_sub_questions: usize,

    /// Model to use for reasoning
    pub model: String,

    /// Temperature for generation
    pub temperature: f64,

    /// Enable verbose logging
    pub verbose: bool,
}

impl Default for ReasoningConfig {
    fn default() -> Self {
        Self {
            max_depth: 10,
            max_sub_questions: 5,
            model: "gpt-3.5-turbo".to_string(),
            temperature: 0.7,
            verbose: false,
        }
    }
}

/// Multi-step reasoner using DSPy for complex problem decomposition
///
/// This reasoner implements the three-phase approach:
/// 1. Decompose complex questions into sub-questions
/// 2. Solve each sub-question using ReAct
/// 3. Synthesize sub-answers into a final conclusion
pub struct MultiStepReasoner {
    agent: Py<PyAny>,
    config: ReasoningConfig,
}

impl MultiStepReasoner {
    /// Create a new multi-step reasoner with default configuration
    pub fn new(config: ReasoningConfig) -> Result<Self> {
        Python::with_gil(|py| Self::new_with_py(py, config))
    }

    /// Create a new multi-step reasoner with explicit Python context
    pub fn new_with_py(py: Python, config: ReasoningConfig) -> Result<Self> {
        // Import DSPy (verify it's available)
        let _dspy = PyModule::import_bound(py, "dspy")
            .map_err(|e| ReasoningError::PythonError(e))?;

        // Create the multi-step agent module
        let module = PyModule::from_code_bound(
            py,
            r#"
import dspy

class MultiStepAgent(dspy.Module):
    """Advanced multi-step reasoning agent with decomposition"""

    def __init__(self, max_sub_questions=5):
        super().__init__()
        self.max_sub_questions = max_sub_questions

        # Decompose complex questions
        self.decompose = dspy.ChainOfThought(
            "complex_question -> sub_questions: list[str]"
        )

        # Solve individual sub-questions
        self.react = dspy.ReAct(
            "question -> answer: str, confidence: float"
        )

        # Synthesize final answer
        self.synthesize = dspy.ChainOfThought(
            "question, answers: list[str] -> final_answer: str, confidence: float"
        )

    def forward(self, question):
        """Execute multi-step reasoning"""

        # Phase 1: Decompose
        decomp = self.decompose(complex_question=question)

        # Extract sub-questions (limit to max)
        sub_questions_raw = decomp.sub_questions
        if isinstance(sub_questions_raw, str):
            sub_questions = [
                q.strip() for q in sub_questions_raw.split('\n')
                if q.strip() and not q.strip().startswith('#')
            ]
        else:
            sub_questions = list(sub_questions_raw)

        sub_questions = sub_questions[:self.max_sub_questions]

        # Phase 2: Solve each sub-question
        sub_answers = []
        sub_confidences = []

        for sq in sub_questions:
            if sq:
                result = self.react(question=sq)
                answer = getattr(result, 'answer', str(result))
                confidence = getattr(result, 'confidence', 0.8)

                sub_answers.append(f"{sq}: {answer}")
                sub_confidences.append(float(confidence))

        # Phase 3: Synthesize
        answers_text = '\n'.join(sub_answers)
        final = self.synthesize(
            question=question,
            answers=sub_answers
        )

        final_answer = getattr(final, 'final_answer', str(final))
        final_confidence = getattr(final, 'confidence',
                                   sum(sub_confidences) / len(sub_confidences) if sub_confidences else 0.7)

        return dspy.Prediction(
            answer=final_answer,
            sub_questions=sub_questions,
            sub_answers=sub_answers,
            sub_confidences=sub_confidences,
            confidence=float(final_confidence)
        )
"#,
            "multi_step_reasoning.py",
            "multi_step_reasoning",
        ).map_err(|e| ReasoningError::PythonError(e))?;

        // Create agent instance
        let agent_class = module.getattr("MultiStepAgent")
            .map_err(|e| ReasoningError::PythonError(e))?;

        let kwargs = PyDict::new_bound(py);
        kwargs.set_item("max_sub_questions", config.max_sub_questions)
            .map_err(|e| ReasoningError::PythonError(e))?;

        let agent = agent_class.call((), Some(&kwargs))
            .map_err(|e| ReasoningError::PythonError(e))?;

        Ok(Self {
            agent: agent.unbind(),
            config,
        })
    }

    /// Execute multi-step reasoning on a complex question
    pub fn reason(&self, question: &str) -> Result<ReasoningChain> {
        Python::with_gil(|py| self.reason_with_py(py, question))
    }

    /// Execute reasoning with explicit Python context
    pub fn reason_with_py(&self, py: Python, question: &str) -> Result<ReasoningChain> {
        let agent = self.agent.bind(py);

        // Call the agent's forward method
        let result = agent.call_method1("forward", (question,))
            .map_err(|e| ReasoningError::PythonError(e))?;

        // Extract results
        let final_answer: String = result.getattr("answer")
            .and_then(|a| a.extract())
            .map_err(|e| ReasoningError::SynthesisFailed(format!("Failed to extract answer: {}", e)))?;

        let final_confidence: f64 = result.getattr("confidence")
            .and_then(|c| c.extract())
            .unwrap_or(0.8);

        // Build reasoning chain
        let mut chain = ReasoningChain::new();
        chain.add_metadata("original_question", question);
        chain.add_metadata("model", &self.config.model);

        // Extract sub-questions and answers
        let sub_questions: Vec<String> = result.getattr("sub_questions")
            .and_then(|sq| sq.extract())
            .unwrap_or_default();

        let sub_answers: Vec<String> = result.getattr("sub_answers")
            .and_then(|sa| sa.extract())
            .unwrap_or_default();

        let sub_confidences: Vec<f64> = result.getattr("sub_confidences")
            .and_then(|sc| sc.extract())
            .unwrap_or_else(|_| vec![0.8; sub_answers.len()]);

        // Add decomposition step
        chain.add_step(
            ReasoningStep::new(1, question.to_string())
                .with_thought("Decomposing complex question into manageable sub-questions")
                .with_action("decompose")
                .with_observation(format!("Identified {} sub-questions", sub_questions.len()))
                .with_conclusion(sub_questions.join("; "))
        );

        // Add solving steps
        for (idx, ((sub_q, sub_a), conf)) in sub_questions.iter()
            .zip(sub_answers.iter())
            .zip(sub_confidences.iter())
            .enumerate() {
            let step_num = idx + 2;
            chain.add_step(
                ReasoningStep::new(step_num, sub_q.clone())
                    .with_thought(format!("Solving sub-question {}/{}", idx + 1, sub_questions.len()))
                    .with_action("solve")
                    .with_observation(sub_a.clone())
                    .with_confidence(*conf)
            );
        }

        // Add synthesis step
        let synthesis_step = sub_questions.len() + 2;
        chain.add_step(
            ReasoningStep::new(synthesis_step, "Synthesize final answer".to_string())
                .with_thought("Combining all sub-answers into coherent conclusion")
                .with_action("synthesize")
                .with_observation(format!("Integrated {} sub-answers", sub_answers.len()))
                .with_conclusion(final_answer.clone())
                .with_confidence(final_confidence)
        );

        chain.set_conclusion(final_answer);
        chain.set_confidence(final_confidence);

        if self.config.verbose {
            println!("{}", chain.visualize());
        }

        chain.validate()?;

        Ok(chain)
    }

    /// Get the configuration
    pub fn config(&self) -> &ReasoningConfig {
        &self.config
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_reasoning_step_builder() {
        let step = ReasoningStep::new(1, "What is 2+2?".to_string())
            .with_thought("Simple arithmetic")
            .with_action("calculate")
            .with_observation("4")
            .with_conclusion("The answer is 4")
            .with_confidence(1.0);

        assert_eq!(step.step_number, 1);
        assert_eq!(step.question, "What is 2+2?");
        assert_eq!(step.confidence, Some(1.0));
    }

    #[test]
    fn test_reasoning_chain() {
        let mut chain = ReasoningChain::new();

        chain.add_step(
            ReasoningStep::new(1, "Question 1".to_string())
                .with_conclusion("Answer 1")
        );

        chain.add_step(
            ReasoningStep::new(2, "Question 2".to_string())
                .with_conclusion("Answer 2")
        );

        chain.set_conclusion("Final answer");
        chain.set_confidence(0.9);

        assert_eq!(chain.len(), 2);
        assert!(chain.validate().is_ok());
    }

    #[test]
    fn test_chain_serialization() {
        let mut chain = ReasoningChain::new();
        chain.add_step(ReasoningStep::new(1, "Test".to_string()));
        chain.set_conclusion("Done");

        let json = chain.to_json().unwrap();
        let restored = ReasoningChain::from_json(&json).unwrap();

        assert_eq!(chain.len(), restored.len());
        assert_eq!(chain.final_conclusion, restored.final_conclusion);
    }
}
