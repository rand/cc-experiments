//! Stateful DSPy Module Example
//!
//! Demonstrates wrapping DSPy modules in Rust structs with:
//! - Query history tracking
//! - State serialization/deserialization
//! - GIL management patterns
//! - Py<PyAny> for holding Python objects

use anyhow::{Context, Result};
use chrono::{DateTime, Utc};
use pyo3::prelude::*;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

/// Represents a single query-response interaction
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct QueryRecord {
    pub timestamp: DateTime<Utc>,
    pub query: String,
    pub response: String,
    pub metadata: HashMap<String, String>,
}

/// Serializable module state
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ModuleState {
    pub history: Vec<QueryRecord>,
    pub created_at: DateTime<Utc>,
    pub query_count: usize,
    pub module_type: String,
}

/// Stateful wrapper around a DSPy module
///
/// This struct demonstrates key PyO3 patterns:
/// - Storing Python objects with Py<PyAny>
/// - GIL acquisition for method calls
/// - Rust-side state management
/// - Serialization for persistence
pub struct StatefulModule {
    /// Python module reference (GIL-independent)
    module: Py<PyAny>,
    /// Query history tracked in Rust
    history: Vec<QueryRecord>,
    /// Module creation timestamp
    created_at: DateTime<Utc>,
    /// Total number of queries processed
    query_count: usize,
    /// Module type identifier
    module_type: String,
}

impl StatefulModule {
    /// Initialize a new stateful module wrapper
    ///
    /// # GIL Pattern
    /// Acquires GIL to create Python module, then stores as Py<PyAny>
    pub fn new(module_type: &str) -> Result<Self> {
        let module = Python::with_gil(|py| {
            // Create a simple DSPy-like module
            let dspy = py.import_bound("dspy")?;

            // Create a basic ChainOfThought module
            let signature = "question -> answer";
            let module = dspy
                .getattr("ChainOfThought")?
                .call1((signature,))?;

            // Store as Py<PyAny> - this allows us to hold the Python object
            // across GIL acquisition boundaries
            Ok::<Py<PyAny>, PyErr>(module.unbind())
        })?;

        Ok(Self {
            module,
            history: Vec::new(),
            created_at: Utc::now(),
            query_count: 0,
            module_type: module_type.to_string(),
        })
    }

    /// Execute a query and track in history
    ///
    /// # GIL Pattern
    /// - Acquire GIL with `with_gil`
    /// - Access module with `as_ref(py)`
    /// - Extract Rust data before releasing GIL
    pub fn query(&mut self, question: &str) -> Result<String> {
        self.query_with_metadata(question, HashMap::new())
    }

    /// Execute a query with custom metadata
    pub fn query_with_metadata(
        &mut self,
        question: &str,
        metadata: HashMap<String, String>,
    ) -> Result<String> {
        let timestamp = Utc::now();

        // Acquire GIL for Python interaction
        let response = Python::with_gil(|py| {
            // Access the stored module through bind(py)
            let module = self.module.bind(py);

            // Call the module's forward method
            let result = module.call_method1("forward", (question,))?;

            // Extract the answer attribute
            let answer = result.getattr("answer")?;

            // Convert to Rust string before releasing GIL
            let response_text = answer.extract::<String>()?;

            Ok::<String, PyErr>(response_text)
        })
        .context("Failed to execute query")?;

        // Record in history (pure Rust operation, no GIL needed)
        let record = QueryRecord {
            timestamp,
            query: question.to_string(),
            response: response.clone(),
            metadata,
        };

        self.history.push(record);
        self.query_count += 1;

        Ok(response)
    }

    /// Get the complete query history
    pub fn get_history(&self) -> &[QueryRecord] {
        &self.history
    }

    /// Get recent history entries
    pub fn get_recent_history(&self, count: usize) -> &[QueryRecord] {
        let start = self.history.len().saturating_sub(count);
        &self.history[start..]
    }

    /// Search history for queries matching a pattern
    pub fn search_history(&self, pattern: &str) -> Vec<&QueryRecord> {
        self.history
            .iter()
            .filter(|record| {
                record.query.contains(pattern) || record.response.contains(pattern)
            })
            .collect()
    }

    /// Clear query history while keeping module
    pub fn clear_history(&mut self) {
        self.history.clear();
    }

    /// Reset module to initial state
    ///
    /// # GIL Pattern
    /// Re-initialize Python module within GIL context
    pub fn reset(&mut self) -> Result<()> {
        self.history.clear();
        self.query_count = 0;
        self.created_at = Utc::now();

        // Re-initialize module
        Python::with_gil(|py| {
            let dspy = py.import_bound("dspy")?;
            let signature = "question -> answer";
            let module = dspy.getattr("ChainOfThought")?.call1((signature,))?;
            self.module = module.unbind();
            Ok::<(), PyErr>(())
        })?;

        Ok(())
    }

    /// Serialize state to JSON file
    ///
    /// Note: Only Rust-side state is serialized.
    /// Python module state is not persisted.
    pub fn save_state(&self, path: &str) -> Result<()> {
        let state = ModuleState {
            history: self.history.clone(),
            created_at: self.created_at,
            query_count: self.query_count,
            module_type: self.module_type.clone(),
        };

        let json = serde_json::to_string_pretty(&state)
            .context("Failed to serialize state")?;

        std::fs::write(path, json)
            .context("Failed to write state file")?;

        Ok(())
    }

    /// Load state from JSON file
    ///
    /// Note: This only loads Rust-side state.
    /// Python module is re-initialized.
    pub fn load_state(path: &str, module_type: &str) -> Result<Self> {
        let json = std::fs::read_to_string(path)
            .context("Failed to read state file")?;

        let state: ModuleState = serde_json::from_str(&json)
            .context("Failed to deserialize state")?;

        // Create new module
        let mut module = Self::new(module_type)?;

        // Restore state
        module.history = state.history;
        module.created_at = state.created_at;
        module.query_count = state.query_count;
        module.module_type = state.module_type;

        Ok(module)
    }

    /// Get module statistics
    pub fn get_stats(&self) -> ModuleStats {
        ModuleStats {
            total_queries: self.query_count,
            history_size: self.history.len(),
            created_at: self.created_at,
            uptime_seconds: (Utc::now() - self.created_at).num_seconds(),
        }
    }

    /// Trim history to maximum size
    pub fn trim_history(&mut self, max_entries: usize) {
        if self.history.len() > max_entries {
            let start = self.history.len() - max_entries;
            self.history.drain(0..start);
        }
    }
}

/// Module statistics
#[derive(Debug)]
pub struct ModuleStats {
    pub total_queries: usize,
    pub history_size: usize,
    pub created_at: DateTime<Utc>,
    pub uptime_seconds: i64,
}

fn main() -> Result<()> {
    println!("=== Stateful DSPy Module Example ===\n");

    // Initialize DSPy with dummy LM for demonstration
    Python::with_gil(|py| {
        let code = r#"
import dspy

class DummyLM(dspy.LM):
    def __call__(self, prompt, **kwargs):
        return ["This is a dummy response for demonstration purposes."]

    def __init__(self):
        super().__init__(model="dummy")

dspy.settings.configure(lm=DummyLM())
"#;
        py.run_bound(code, None, None)
    })?;

    // Create stateful module
    println!("Initializing stateful DSPy module...");
    let mut module = StatefulModule::new("ChainOfThought")?;
    println!("Module initialized: {}\n", module.module_type);

    // Execute multiple queries with state tracking
    println!("--- Query 1 ---");
    let mut metadata1 = HashMap::new();
    metadata1.insert("model".to_string(), "dummy".to_string());
    metadata1.insert("temperature".to_string(), "0.7".to_string());

    let response1 = module.query_with_metadata(
        "What is machine learning?",
        metadata1,
    )?;
    println!("Query: What is machine learning?");
    println!("Response: {}", response1);
    println!("History entries: {}\n", module.get_history().len());

    // Second query
    println!("--- Query 2 ---");
    let mut metadata2 = HashMap::new();
    metadata2.insert("model".to_string(), "dummy".to_string());

    let response2 = module.query_with_metadata(
        "How do neural networks work?",
        metadata2,
    )?;
    println!("Query: How do neural networks work?");
    println!("Response: {}", response2);
    println!("History entries: {}\n", module.get_history().len());

    // Third query
    println!("--- Query 3 ---");
    let response3 = module.query("Explain backpropagation")?;
    println!("Query: Explain backpropagation");
    println!("Response: {}", response3);
    println!("History entries: {}\n", module.get_history().len());

    // Display statistics
    println!("--- Module Statistics ---");
    let stats = module.get_stats();
    println!("Total queries: {}", stats.total_queries);
    println!("History size: {}", stats.history_size);
    println!("Created at: {}", stats.created_at);
    println!("Uptime: {} seconds\n", stats.uptime_seconds);

    // Display complete history
    println!("--- Query History ---");
    for (i, record) in module.get_history().iter().enumerate() {
        println!("{}. [{}] {}", i + 1, record.timestamp, record.query);
        println!("   Response: {}", record.response);
        if !record.metadata.is_empty() {
            println!("   Metadata: {:?}", record.metadata);
        }
        println!();
    }

    // Search history
    println!("--- Searching History ---");
    let results = module.search_history("neural");
    println!("Found {} results for 'neural':", results.len());
    for record in results {
        println!("- {}: {}", record.timestamp, record.query);
    }
    println!();

    // Save state
    let state_file = "module_state.json";
    println!("--- Saving State ---");
    module.save_state(state_file)?;
    println!("State saved to: {}\n", state_file);

    // Load state
    println!("--- Loading State ---");
    let loaded_module = StatefulModule::load_state(state_file, "ChainOfThought")?;
    println!("Loaded state with {} history entries", loaded_module.get_history().len());

    let loaded_stats = loaded_module.get_stats();
    println!("Loaded module created at: {}", loaded_stats.created_at);
    println!("Total queries in loaded state: {}\n", loaded_stats.total_queries);

    // Demonstrate history trimming
    println!("--- History Management ---");
    let mut trim_module = loaded_module;
    println!("History before trim: {}", trim_module.get_history().len());
    trim_module.trim_history(2);
    println!("History after trim(2): {}", trim_module.get_history().len());

    println!("\nRecent entries:");
    for record in trim_module.get_recent_history(2) {
        println!("- {}", record.query);
    }
    println!();

    // Demonstrate clear and reset
    println!("--- Reset Operations ---");
    trim_module.clear_history();
    println!("After clear_history(): {} entries", trim_module.get_history().len());

    trim_module.reset()?;
    println!("After reset(): Module reinitialized");
    let reset_stats = trim_module.get_stats();
    println!("New query count: {}", reset_stats.total_queries);

    println!("\n=== Example Complete ===");
    println!("Key takeaways:");
    println!("1. Py<PyAny> allows storing Python objects across GIL boundaries");
    println!("2. State can be maintained in Rust while wrapping Python modules");
    println!("3. GIL acquisition is scoped with Python::with_gil");
    println!("4. Serialization enables state persistence");
    println!("5. History tracking provides audit trail for queries");

    Ok(())
}
