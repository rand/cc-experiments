//! Stateful ReAct Agent Demo
//!
//! This demonstrates a conversational agent with persistent memory that:
//! - Maintains conversation history across multiple turns
//! - Stores and retrieves facts
//! - Augments questions with relevant context
//! - Persists state to disk
//! - Implements memory management strategies

use anyhow::{Context, Result};
use chrono::{Duration, Utc};
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList, PyTuple};
use stateful_agent::{AgentMemory, ConversationTurn};
use std::collections::HashMap;
use std::sync::{Arc, Mutex};

/// Tool function signature
type ToolFn = Arc<dyn Fn(&str) -> Result<String> + Send + Sync>;

/// Registry of available tools
#[derive(Clone)]
struct ToolRegistry {
    tools: HashMap<String, ToolFn>,
}

impl ToolRegistry {
    /// Create a new tool registry
    fn new() -> Self {
        Self {
            tools: HashMap::new(),
        }
    }

    /// Register a tool
    fn register<F>(&mut self, name: &str, func: F)
    where
        F: Fn(&str) -> Result<String> + Send + Sync + 'static,
    {
        self.tools.insert(name.to_string(), Arc::new(func));
    }

    /// Execute a tool by name
    fn execute(&self, name: &str, input: &str) -> Result<String> {
        let tool = self
            .tools
            .get(name)
            .ok_or_else(|| anyhow::anyhow!("Tool '{}' not found", name))?;
        tool(input)
    }

    /// Get list of available tool names
    fn tool_names(&self) -> Vec<String> {
        self.tools.keys().cloned().collect()
    }

    /// Convert to Python-compatible format
    fn to_python_dict(&self, py: Python) -> PyResult<Py<PyDict>> {
        let dict = PyDict::new(py);

        for name in self.tool_names() {
            // Create a simple tool description
            let tool_desc = PyDict::new(py);
            tool_desc.set_item("name", name.clone())?;
            tool_desc.set_item("description", format!("Tool: {}", name))?;
            dict.set_item(name, tool_desc)?;
        }

        Ok(dict.into())
    }
}

/// Stateful ReAct Agent with memory
struct StatefulReActAgent {
    registry: Arc<Mutex<ToolRegistry>>,
    memory: Arc<Mutex<AgentMemory>>,
    agent: Option<Py<PyAny>>,
}

impl StatefulReActAgent {
    /// Create a new stateful agent
    fn new() -> Self {
        Self {
            registry: Arc::new(Mutex::new(ToolRegistry::new())),
            memory: Arc::new(Mutex::new(AgentMemory::new())),
            agent: None,
        }
    }

    /// Initialize the DSPy agent
    fn initialize(&mut self, py: Python) -> PyResult<()> {
        // Import DSPy
        let dspy = py.import("dspy")?;

        // Configure LM (using OpenAI for demo)
        let openai_class = dspy.getattr("OpenAI")?;
        let lm = openai_class.call1(("gpt-3.5-turbo",))?;

        let settings = dspy.getattr("settings")?;
        settings.call_method1("configure", (lm,))?;

        // Create ReAct agent
        let react_class = dspy.getattr("ReAct")?;
        let signature = "question -> answer";
        let agent = react_class.call1((signature,))?;

        self.agent = Some(agent.into());
        Ok(())
    }

    /// Execute agent with memory context
    fn execute_with_memory(&self, py: Python, question: &str) -> PyResult<String> {
        let agent = self
            .agent
            .as_ref()
            .ok_or_else(|| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>("Agent not initialized"))?;

        // Build context from memory
        let context = {
            let mem = self.memory.lock().unwrap();
            mem.get_context(3) // Last 3 turns
        };

        // Augment question with context
        let augmented_question = if context.is_empty() {
            question.to_string()
        } else {
            format!(
                "Context from previous conversation:\n{}\n\nCurrent question: {}",
                context, question
            )
        };

        // Execute agent
        let result = agent
            .as_ref(py)
            .call_method1("forward", (augmented_question,))?;

        let answer: String = result.getattr("answer")?.extract()?;

        // Update memory
        {
            let mut mem = self.memory.lock().unwrap();
            mem.add_turn(question.to_string(), answer.clone(), 0);
        }

        Ok(answer)
    }

    /// Execute with relevance-based context
    fn execute_with_relevance(
        &self,
        py: Python,
        question: &str,
        max_context_turns: usize,
        min_relevance: f32,
    ) -> PyResult<String> {
        let agent = self
            .agent
            .as_ref()
            .ok_or_else(|| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>("Agent not initialized"))?;

        // Build relevance-based context
        let context = {
            let mem = self.memory.lock().unwrap();
            mem.get_context_with_relevance(question, max_context_turns, min_relevance)
        };

        // Augment question
        let augmented_question = if context.is_empty() {
            question.to_string()
        } else {
            format!(
                "Relevant context:\n{}\n\nQuestion: {}",
                context, question
            )
        };

        // Execute
        let result = agent
            .as_ref(py)
            .call_method1("forward", (augmented_question,))?;

        let answer: String = result.getattr("answer")?.extract()?;

        // Update memory
        {
            let mut mem = self.memory.lock().unwrap();
            mem.add_turn(question.to_string(), answer.clone(), 0);
        }

        Ok(answer)
    }

    /// Save memory to file
    fn save_memory(&self, path: &str) -> Result<()> {
        let mem = self.memory.lock().unwrap();
        mem.save(path)
    }

    /// Load memory from file
    fn load_memory(&mut self, path: &str) -> Result<()> {
        let loaded = AgentMemory::load(path)?;
        let mut mem = self.memory.lock().unwrap();
        *mem = loaded;
        Ok(())
    }

    /// Get memory statistics
    fn memory_stats(&self) -> String {
        let mem = self.memory.lock().unwrap();
        let stats = mem.stats();
        stats.to_string()
    }

    /// Add a fact to memory
    fn add_fact(&self, key: String, value: String) {
        let mut mem = self.memory.lock().unwrap();
        mem.add_fact(key, value);
    }

    /// Prune memory using various strategies
    fn prune_memory(&self, strategy: PruneStrategy) {
        let mut mem = self.memory.lock().unwrap();

        match strategy {
            PruneStrategy::KeepLast(n) => {
                mem.prune_history(n);
            }
            PruneStrategy::ByAge(hours) => {
                let duration = Duration::hours(hours as i64);
                mem.prune_by_age(duration);
            }
            PruneStrategy::Compact(keep_recent) => {
                mem.compact(keep_recent);
            }
        }
    }
}

/// Memory pruning strategies
enum PruneStrategy {
    /// Keep only the last N turns
    KeepLast(usize),
    /// Remove turns older than N hours
    ByAge(usize),
    /// Compact old history into summary, keeping N recent
    Compact(usize),
}

/// Demo function: Basic conversation with memory
fn demo_basic_conversation() -> Result<()> {
    println!("\n=== Demo 1: Basic Conversation with Memory ===\n");

    Python::with_gil(|py| -> PyResult<()> {
        let mut agent = StatefulReActAgent::new();

        // Note: In real usage, initialize DSPy agent here
        // agent.initialize(py)?;

        // Simulate conversation (without actual DSPy for demo)
        println!("Turn 1:");
        println!("Q: What is the capital of France?");
        let answer1 = "Paris is the capital of France.";
        println!("A: {}\n", answer1);

        // Add to memory manually for demo
        {
            let mut mem = agent.memory.lock().unwrap();
            mem.add_turn(
                "What is the capital of France?".to_string(),
                answer1.to_string(),
                3,
            );
        }

        println!("Turn 2:");
        println!("Q: What is the population?");
        let context = {
            let mem = agent.memory.lock().unwrap();
            mem.get_context(5)
        };
        println!("Context used:\n{}", context);

        let answer2 = "Based on the context about Paris, the population is approximately 2.2 million.";
        println!("A: {}\n", answer2);

        {
            let mut mem = agent.memory.lock().unwrap();
            mem.add_turn(
                "What is the population?".to_string(),
                answer2.to_string(),
                2,
            );
        }

        // Save memory
        agent.save_memory("demo_memory.json")?;
        println!("Memory saved to: demo_memory.json\n");

        // Show stats
        println!("{}", agent.memory_stats());

        Ok(())
    })?;

    Ok(())
}

/// Demo function: Fact storage and retrieval
fn demo_fact_storage() -> Result<()> {
    println!("\n=== Demo 2: Fact Storage and Retrieval ===\n");

    let mut memory = AgentMemory::new();

    // Store facts
    println!("Storing facts...");
    memory.add_fact("user_name".to_string(), "Alice".to_string());
    memory.add_fact("favorite_color".to_string(), "blue".to_string());
    memory.add_fact("city".to_string(), "San Francisco".to_string());
    memory.add_fact("occupation".to_string(), "Software Engineer".to_string());

    println!("Facts stored: {}\n", memory.facts().len());

    // Add conversations
    memory.add_turn(
        "What's my name?".to_string(),
        "Your name is Alice.".to_string(),
        1,
    );

    memory.add_turn(
        "What do I do for work?".to_string(),
        "You are a Software Engineer.".to_string(),
        1,
    );

    // Build context
    let context = memory.get_context(10);
    println!("Full context:\n{}", context);

    // Retrieve specific fact
    if let Some(name) = memory.get_fact("user_name") {
        println!("Retrieved fact - user_name: {}", name);
    }

    Ok(())
}

/// Demo function: Memory persistence
fn demo_persistence() -> Result<()> {
    println!("\n=== Demo 3: Memory Persistence ===\n");

    // Create and populate memory
    let mut memory = AgentMemory::new();

    for i in 0..5 {
        memory.add_turn(
            format!("Question {}", i + 1),
            format!("Answer to question {}", i + 1),
            2,
        );
    }

    memory.add_fact("session_id".to_string(), "abc123".to_string());
    memory.add_fact("user_id".to_string(), "user_42".to_string());

    println!("Original memory:");
    println!("- Turns: {}", memory.turn_count());
    println!("- Facts: {}", memory.facts().len());

    // Save
    let path = "persistent_memory.json";
    memory.save(path)?;
    println!("\nMemory saved to: {}", path);

    // Load
    let loaded = AgentMemory::load(path)?;
    println!("\nLoaded memory:");
    println!("- Turns: {}", loaded.turn_count());
    println!("- Facts: {}", loaded.facts().len());

    // Verify integrity
    assert_eq!(memory.turn_count(), loaded.turn_count());
    assert_eq!(memory.facts().len(), loaded.facts().len());
    println!("\nIntegrity check: PASSED");

    Ok(())
}

/// Demo function: Memory pruning strategies
fn demo_pruning() -> Result<()> {
    println!("\n=== Demo 4: Memory Pruning Strategies ===\n");

    // Create memory with many turns
    let mut memory = AgentMemory::new();

    for i in 0..20 {
        memory.add_turn(
            format!("Question about topic {}", i % 5),
            format!("Answer for question {}", i),
            1,
        );
    }

    println!("Initial: {} turns", memory.turn_count());
    println!("Estimated size: {} bytes\n", memory.estimate_size());

    // Strategy 1: Keep last N
    let mut mem1 = memory.clone();
    mem1.prune_history(10);
    println!("After keeping last 10: {} turns", mem1.turn_count());

    // Strategy 2: Compact with summary
    let mut mem2 = memory.clone();
    mem2.compact(5);
    println!("After compacting (keep 5): {} turns", mem2.turn_count());
    println!("New size: {} bytes\n", mem2.estimate_size());

    // Strategy 3: Relevance-based
    let query = "topic 3";
    let relevant = memory.search_history(query);
    println!("Turns relevant to '{}': {}", query, relevant.len());

    Ok(())
}

/// Demo function: Relevance-based context
fn demo_relevance_context() -> Result<()> {
    println!("\n=== Demo 5: Relevance-Based Context ===\n");

    let mut memory = AgentMemory::new();

    // Add diverse conversation topics
    let topics = vec![
        ("What is machine learning?", "ML is a type of AI that learns from data."),
        ("How do I cook pasta?", "Boil water, add pasta, cook for 8-10 minutes."),
        ("Explain neural networks", "Neural networks are ML models inspired by the brain."),
        ("What's the weather like?", "It's sunny and 75°F today."),
        ("What is deep learning?", "Deep learning uses multi-layer neural networks."),
    ];

    for (q, a) in topics {
        memory.add_turn(q.to_string(), a.to_string(), 2);
    }

    // Query with relevance filtering
    let query = "What are the types of machine learning?";
    println!("Query: {}\n", query);

    let context = memory.get_context_with_relevance(query, 3, 0.3);
    println!("Relevant context (min relevance: 0.3):\n{}", context);

    // Show relevance scores
    println!("Relevance scores:");
    for turn in memory.history() {
        let score = turn.relevance_to(query);
        println!("  {:.2}: {}", score, turn.question);
    }

    Ok(())
}

/// Demo function: Memory merging
fn demo_memory_merge() -> Result<()> {
    println!("\n=== Demo 6: Memory Merging ===\n");

    // Create multiple agent memories
    let mut mem1 = AgentMemory::new();
    mem1.add_fact("agent_id".to_string(), "agent_1".to_string());
    mem1.add_turn("Question 1".to_string(), "Answer 1".to_string(), 1);

    let mut mem2 = AgentMemory::new();
    mem2.add_fact("agent_id".to_string(), "agent_2".to_string());
    mem2.add_turn("Question 2".to_string(), "Answer 2".to_string(), 1);

    let mut mem3 = AgentMemory::new();
    mem3.add_fact("shared_fact".to_string(), "shared_value".to_string());
    mem3.add_turn("Question 3".to_string(), "Answer 3".to_string(), 1);

    println!("Memory 1: {} turns, {} facts", mem1.turn_count(), mem1.facts().len());
    println!("Memory 2: {} turns, {} facts", mem2.turn_count(), mem2.facts().len());
    println!("Memory 3: {} turns, {} facts", mem3.turn_count(), mem3.facts().len());

    // Merge
    let merged = AgentMemory::merge(vec![mem1, mem2, mem3]);
    println!("\nMerged memory: {} turns, {} facts", merged.turn_count(), merged.facts().len());

    // Show merged conversation history (chronological)
    println!("\nMerged conversation history:");
    for (i, turn) in merged.history().iter().enumerate() {
        println!("  {}: {}", i + 1, turn.question);
    }

    Ok(())
}

/// Main demo runner
fn main() -> Result<()> {
    println!("╔════════════════════════════════════════════════╗");
    println!("║    Stateful Agent with Memory Demo            ║");
    println!("╚════════════════════════════════════════════════╝");

    // Run all demos
    demo_basic_conversation()?;
    demo_fact_storage()?;
    demo_persistence()?;
    demo_pruning()?;
    demo_relevance_context()?;
    demo_memory_merge()?;

    println!("\n╔════════════════════════════════════════════════╗");
    println!("║    All Demos Completed Successfully!          ║");
    println!("╚════════════════════════════════════════════════╝\n");

    println!("Generated files:");
    println!("  - demo_memory.json (basic conversation)");
    println!("  - persistent_memory.json (persistence demo)");
    println!("\nTo use with real DSPy:");
    println!("  1. Uncomment agent.initialize(py)? in demo_basic_conversation()");
    println!("  2. Set OPENAI_API_KEY environment variable");
    println!("  3. Run: cargo run --bin stateful-agent");

    Ok(())
}
