# PyO3 DSPy ReAct Agents - Complete Reference

Comprehensive technical reference for building production-ready ReAct agents using DSPy from Rust via PyO3. Covers complete implementation patterns for tool registries, state management, error recovery, multi-step reasoning, parallel execution, and production deployment.

## Table of Contents

1. [ReAct Pattern Implementation](#react-pattern-implementation)
2. [Tool Registry Architecture](#tool-registry-architecture)
3. [Tool Execution](#tool-execution)
4. [Agent State Management](#agent-state-management)
5. [Error Recovery Strategies](#error-recovery-strategies)
6. [Multi-Step Reasoning](#multi-step-reasoning)
7. [Parallel Agent Execution](#parallel-agent-execution)
8. [Production Agent Systems](#production-agent-systems)
9. [Observability](#observability)
10. [Best Practices Summary](#best-practices-summary)

---

## ReAct Pattern Implementation

### Basic ReAct Loop

The ReAct pattern implements an iterative cycle: **Reason** → **Act** → **Observe** → repeat until task complete.

**Simple ReAct Agent**:

```rust
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList, PyModule};
use serde::{Deserialize, Serialize};
use anyhow::{Context, Result};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ReActConfig {
    pub signature: String,
    pub max_iterations: usize,
    pub temperature: f32,
}

impl Default for ReActConfig {
    fn default() -> Self {
        Self {
            signature: "question -> answer".to_string(),
            max_iterations: 5,
            temperature: 0.7,
        }
    }
}

pub struct ReActAgent {
    agent: Py<PyAny>,
    config: ReActConfig,
}

impl ReActAgent {
    pub fn new(config: ReActConfig) -> PyResult<Self> {
        Python::with_gil(|py| {
            let dspy = PyModule::import(py, "dspy")?;

            // Create ReAct module
            let react_class = dspy.getattr("ReAct")?;
            let agent = react_class.call1(((config.signature.as_str(),),))?;

            // Configure max iterations
            agent.setattr("max_iters", config.max_iterations)?;

            Ok(Self {
                agent: agent.into(),
                config,
            })
        })
    }

    pub fn forward(&self, question: &str) -> PyResult<String> {
        Python::with_gil(|py| {
            let result = self.agent.as_ref(py)
                .call_method1("forward", ((question,),))?;

            let answer: String = result.getattr("answer")?.extract()?;
            Ok(answer)
        })
    }
}

// Usage
fn main() -> Result<()> {
    // Configure DSPy LM first
    configure_dspy_lm()?;

    let config = ReActConfig::default();
    let agent = ReActAgent::new(config)?;

    let answer = agent.forward("What is the capital of France?")?;
    println!("Answer: {}", answer);

    Ok(())
}

fn configure_dspy_lm() -> Result<()> {
    Python::with_gil(|py| {
        let dspy = PyModule::import(py, "dspy")?;
        let lm = dspy.getattr("OpenAI")?.call1((("gpt-3.5-turbo",),))?;
        dspy.getattr("settings")?.call_method1("configure", ((lm,),))?;
        Ok(())
    })
}
```

### Extracting Trajectory

**Complete trajectory extraction with all steps**:

```rust
use pyo3::types::PyList;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AgentStep {
    pub step_number: usize,
    pub thought: String,
    pub action: String,
    pub observation: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ReActResult {
    pub answer: String,
    pub trajectory: Vec<AgentStep>,
    pub total_iterations: usize,
    pub success: bool,
}

impl ReActAgent {
    pub fn forward_with_trace(&self, question: &str) -> PyResult<ReActResult> {
        Python::with_gil(|py| {
            let result = self.agent.as_ref(py)
                .call_method1("forward", ((question,),))?;

            let answer: String = result.getattr("answer")?.extract()?;

            // Extract trajectory
            let mut trajectory = Vec::new();

            if let Ok(traj) = result.getattr("trajectory") {
                let py_list: &PyList = traj.downcast()?;

                for (idx, step) in py_list.iter().enumerate() {
                    let thought = step.getattr("thought")
                        .ok()
                        .and_then(|t| t.extract::<String>().ok())
                        .unwrap_or_default();

                    let action = step.getattr("action")
                        .ok()
                        .and_then(|a| a.extract::<String>().ok())
                        .unwrap_or_default();

                    let observation = step.getattr("observation")
                        .ok()
                        .and_then(|o| o.extract::<String>().ok())
                        .unwrap_or_default();

                    trajectory.push(AgentStep {
                        step_number: idx + 1,
                        thought,
                        action,
                        observation,
                    });
                }
            }

            let total_iterations = trajectory.len();
            let success = !answer.is_empty();

            Ok(ReActResult {
                answer,
                trajectory,
                total_iterations,
                success,
            })
        })
    }
}
```

### Custom ReAct Module

**Define custom ReAct behavior in Python, call from Rust**:

**Python module** (custom_react.py):
```python
import dspy

class CustomReActAgent(dspy.Module):
    """ReAct agent with custom reasoning prompts."""

    def __init__(self, signature, tools=None, max_iters=5):
        super().__init__()
        self.signature = signature
        self.max_iters = max_iters
        self.tools = tools or []

        # Custom signature with explicit reasoning
        self.think = dspy.ChainOfThought("question, context -> thought")
        self.act = dspy.Predict("thought, available_tools -> action, tool_input")
        self.react = dspy.ReAct(signature, tools=self.tools)

    def forward(self, question, context=""):
        # Add custom pre-processing
        enhanced_question = f"{question}\nContext: {context}" if context else question

        # Execute ReAct
        result = self.react(question=enhanced_question)

        return result
```

**Rust wrapper**:
```rust
use pyo3::types::PyModule;

pub struct CustomReActAgent {
    agent: Py<PyAny>,
}

impl CustomReActAgent {
    pub fn new(tools: Vec<String>, max_iters: usize) -> PyResult<Self> {
        Python::with_gil(|py| {
            // Load custom module
            let custom_module = PyModule::from_code(
                py,
                include_str!("../python/custom_react.py"),
                "custom_react.py",
                "custom_react",
            )?;

            let agent_class = custom_module.getattr("CustomReActAgent")?;

            // Convert tools to Python list
            let py_tools = PyList::new(py, &tools);

            // Create agent instance
            let agent = agent_class.call1((
                "question, context -> answer",
                py_tools,
                max_iters,
            ))?;

            Ok(Self {
                agent: agent.into(),
            })
        })
    }

    pub fn forward(&self, question: &str, context: &str) -> PyResult<String> {
        Python::with_gil(|py| {
            let result = self.agent.as_ref(py).call_method1(
                "forward",
                ((question, context),)
            )?;

            result.getattr("answer")?.extract()
        })
    }
}
```

---

## Tool Registry Architecture

### Complete Tool Registry Implementation

**Full-featured tool registry with validation and monitoring**:

```rust
use std::collections::HashMap;
use std::sync::{Arc, Mutex};
use chrono::{DateTime, Utc};

type ToolFn = Box<dyn Fn(&str) -> Result<String> + Send + Sync>;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ToolMetadata {
    pub name: String,
    pub description: String,
    pub parameters: Vec<ToolParameter>,
    pub returns: String,
    pub examples: Vec<String>,
    pub created_at: DateTime<Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ToolParameter {
    pub name: String,
    pub type_name: String,
    pub description: String,
    pub required: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ToolExecution {
    pub tool_name: String,
    pub input: String,
    pub output: Result<String, String>,
    pub duration_ms: u64,
    pub timestamp: DateTime<Utc>,
}

pub struct ToolRegistry {
    tools: HashMap<String, ToolFn>,
    metadata: HashMap<String, ToolMetadata>,
    execution_history: Arc<Mutex<Vec<ToolExecution>>>,
}

impl ToolRegistry {
    pub fn new() -> Self {
        Self {
            tools: HashMap::new(),
            metadata: HashMap::new(),
            execution_history: Arc::new(Mutex::new(Vec::new())),
        }
    }

    pub fn register<F>(
        &mut self,
        name: &str,
        metadata: ToolMetadata,
        tool: F,
    ) where
        F: Fn(&str) -> Result<String> + Send + Sync + 'static,
    {
        self.tools.insert(name.to_string(), Box::new(tool));
        self.metadata.insert(name.to_string(), metadata);
    }

    pub fn execute(&self, name: &str, input: &str) -> Result<String> {
        let start = std::time::Instant::now();

        let tool = self.tools.get(name)
            .ok_or_else(|| anyhow::anyhow!("Tool not found: {}", name))?;

        let result = tool(input);
        let duration_ms = start.elapsed().as_millis() as u64;

        // Record execution
        let execution = ToolExecution {
            tool_name: name.to_string(),
            input: input.to_string(),
            output: result.as_ref()
                .map(|s| s.clone())
                .map_err(|e| e.to_string()),
            duration_ms,
            timestamp: Utc::now(),
        };

        self.execution_history.lock().unwrap().push(execution);

        result
    }

    pub fn list_tools(&self) -> Vec<String> {
        self.tools.keys().cloned().collect()
    }

    pub fn get_metadata(&self, name: &str) -> Option<&ToolMetadata> {
        self.metadata.get(name)
    }

    pub fn get_execution_stats(&self, tool_name: &str) -> ToolStats {
        let history = self.execution_history.lock().unwrap();

        let executions: Vec<_> = history.iter()
            .filter(|e| e.tool_name == tool_name)
            .collect();

        let total = executions.len();
        let successful = executions.iter()
            .filter(|e| e.output.is_ok())
            .count();
        let failed = total - successful;

        let avg_duration = if total > 0 {
            executions.iter()
                .map(|e| e.duration_ms)
                .sum::<u64>() / total as u64
        } else {
            0
        };

        ToolStats {
            tool_name: tool_name.to_string(),
            total_executions: total,
            successful_executions: successful,
            failed_executions: failed,
            average_duration_ms: avg_duration,
        }
    }

    pub fn to_python_tools(&self, py: Python) -> PyResult<PyObject> {
        let tools_list = PyList::empty(py);

        for (name, metadata) in &self.metadata {
            let tool_dict = PyDict::new(py);
            tool_dict.set_item("name", name)?;
            tool_dict.set_item("description", &metadata.description)?;

            // Add parameters
            let params_list = PyList::empty(py);
            for param in &metadata.parameters {
                let param_dict = PyDict::new(py);
                param_dict.set_item("name", &param.name)?;
                param_dict.set_item("type", &param.type_name)?;
                param_dict.set_item("description", &param.description)?;
                param_dict.set_item("required", param.required)?;
                params_list.append(param_dict)?;
            }
            tool_dict.set_item("parameters", params_list)?;

            tools_list.append(tool_dict)?;
        }

        Ok(tools_list.into())
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ToolStats {
    pub tool_name: String,
    pub total_executions: usize,
    pub successful_executions: usize,
    pub failed_executions: usize,
    pub average_duration_ms: u64,
}
```

### Example Tool Implementations

**Production-ready tool implementations**:

```rust
use reqwest;
use serde_json::Value;

// Search tool
pub fn create_search_tool(api_key: String) -> impl Fn(&str) -> Result<String> + Send + Sync {
    move |query: &str| {
        // Call search API (example with Serper.dev)
        let client = reqwest::blocking::Client::new();
        let response = client
            .post("https://google.serper.dev/search")
            .header("X-API-KEY", &api_key)
            .json(&serde_json::json!({
                "q": query,
                "num": 5
            }))
            .send()?;

        let data: Value = response.json()?;

        let results = data["organic"]
            .as_array()
            .ok_or_else(|| anyhow::anyhow!("No results"))?
            .iter()
            .take(3)
            .map(|r| format!("{}: {}", r["title"], r["snippet"]))
            .collect::<Vec<_>>()
            .join("\n\n");

        Ok(results)
    }
}

// Calculator tool
pub fn calculator_tool(expression: &str) -> Result<String> {
    use evalexpr::eval;

    let result = eval(expression)
        .map_err(|e| anyhow::anyhow!("Calculation error: {}", e))?;

    Ok(result.to_string())
}

// Weather tool
pub fn create_weather_tool(api_key: String) -> impl Fn(&str) -> Result<String> + Send + Sync {
    move |location: &str| {
        let client = reqwest::blocking::Client::new();
        let response = client
            .get("https://api.openweathermap.org/data/2.5/weather")
            .query(&[
                ("q", location),
                ("appid", &api_key),
                ("units", "metric"),
            ])
            .send()?;

        let data: Value = response.json()?;

        let temp = data["main"]["temp"].as_f64().unwrap_or(0.0);
        let description = data["weather"][0]["description"]
            .as_str()
            .unwrap_or("unknown");

        Ok(format!("Weather in {}: {}, {}°C", location, description, temp))
    }
}

// File system tool
pub fn filesystem_tool(path: &str) -> Result<String> {
    use std::fs;

    // Security: validate path is in allowed directory
    let allowed_dir = std::env::var("ALLOWED_DIR")?;
    let canonical_path = fs::canonicalize(path)?;

    if !canonical_path.starts_with(&allowed_dir) {
        return Err(anyhow::anyhow!("Path not allowed"));
    }

    if canonical_path.is_file() {
        let contents = fs::read_to_string(&canonical_path)?;
        Ok(format!("File contents:\n{}", contents))
    } else if canonical_path.is_dir() {
        let entries: Vec<_> = fs::read_dir(&canonical_path)?
            .filter_map(|e| e.ok())
            .map(|e| e.file_name().to_string_lossy().to_string())
            .collect();
        Ok(format!("Directory contents:\n{}", entries.join("\n")))
    } else {
        Err(anyhow::anyhow!("Invalid path"))
    }
}

// Database query tool
pub fn create_database_tool(
    connection_string: String,
) -> impl Fn(&str) -> Result<String> + Send + Sync {
    move |query: &str| {
        use sqlx::{PgPool, postgres::PgPoolOptions};

        // Security: only allow SELECT queries
        if !query.trim().to_uppercase().starts_with("SELECT") {
            return Err(anyhow::anyhow!("Only SELECT queries allowed"));
        }

        let rt = tokio::runtime::Runtime::new()?;
        rt.block_on(async {
            let pool = PgPoolOptions::new()
                .max_connections(1)
                .connect(&connection_string)
                .await?;

            let rows = sqlx::query(query)
                .fetch_all(&pool)
                .await?;

            // Format results
            let result = format!("Query returned {} rows", rows.len());
            Ok(result)
        })
    }
}
```

---

## Tool Execution

### Safe Tool Execution

**Execute tools with timeout, validation, and sandboxing**:

```rust
use tokio::time::{timeout, Duration};
use std::sync::Arc;

#[derive(Debug, Clone)]
pub struct ToolExecutionConfig {
    pub timeout: Duration,
    pub max_retries: usize,
    pub validate_input: bool,
    pub validate_output: bool,
}

impl Default for ToolExecutionConfig {
    fn default() -> Self {
        Self {
            timeout: Duration::from_secs(30),
            max_retries: 3,
            validate_input: true,
            validate_output: true,
        }
    }
}

pub struct SafeToolExecutor {
    registry: Arc<ToolRegistry>,
    config: ToolExecutionConfig,
}

impl SafeToolExecutor {
    pub fn new(registry: Arc<ToolRegistry>, config: ToolExecutionConfig) -> Self {
        Self { registry, config }
    }

    pub async fn execute(
        &self,
        tool_name: &str,
        input: &str,
    ) -> Result<String> {
        // Validate input
        if self.config.validate_input {
            self.validate_tool_input(tool_name, input)?;
        }

        // Execute with timeout
        let registry = Arc::clone(&self.registry);
        let tool_name = tool_name.to_string();
        let input = input.to_string();

        let result = timeout(
            self.config.timeout,
            tokio::task::spawn_blocking(move || {
                registry.execute(&tool_name, &input)
            })
        ).await
            .map_err(|_| anyhow::anyhow!("Tool execution timeout"))?
            .map_err(|e| anyhow::anyhow!("Tool execution failed: {}", e))??;

        // Validate output
        if self.config.validate_output {
            self.validate_tool_output(tool_name.as_str(), &result)?;
        }

        Ok(result)
    }

    fn validate_tool_input(&self, tool_name: &str, input: &str) -> Result<()> {
        // Check input length
        if input.len() > 10_000 {
            return Err(anyhow::anyhow!("Input too long"));
        }

        // Check for suspicious patterns
        let suspicious = ["rm -rf", "DROP TABLE", "eval(", "exec("];
        for pattern in &suspicious {
            if input.contains(pattern) {
                return Err(anyhow::anyhow!("Suspicious input pattern detected"));
            }
        }

        // Tool-specific validation
        if let Some(metadata) = self.registry.get_metadata(tool_name) {
            // Validate required parameters are present
            for param in &metadata.parameters {
                if param.required && !input.contains(&param.name) {
                    return Err(anyhow::anyhow!(
                        "Missing required parameter: {}",
                        param.name
                    ));
                }
            }
        }

        Ok(())
    }

    fn validate_tool_output(&self, tool_name: &str, output: &str) -> Result<()> {
        // Check output length
        if output.len() > 100_000 {
            return Err(anyhow::anyhow!("Output too long"));
        }

        // Check for error markers
        if output.contains("Error:") || output.contains("Exception:") {
            return Err(anyhow::anyhow!("Tool returned error: {}", output));
        }

        Ok(())
    }
}
```

### Tool Execution Hooks

**Add pre/post execution hooks for logging, metrics, etc.**:

```rust
pub type PreExecutionHook = Arc<dyn Fn(&str, &str) + Send + Sync>;
pub type PostExecutionHook = Arc<dyn Fn(&str, &str, &Result<String>) + Send + Sync>;

pub struct HookedToolExecutor {
    executor: SafeToolExecutor,
    pre_hooks: Vec<PreExecutionHook>,
    post_hooks: Vec<PostExecutionHook>,
}

impl HookedToolExecutor {
    pub fn new(executor: SafeToolExecutor) -> Self {
        Self {
            executor,
            pre_hooks: Vec::new(),
            post_hooks: Vec::new(),
        }
    }

    pub fn add_pre_hook<F>(&mut self, hook: F)
    where
        F: Fn(&str, &str) + Send + Sync + 'static,
    {
        self.pre_hooks.push(Arc::new(hook));
    }

    pub fn add_post_hook<F>(&mut self, hook: F)
    where
        F: Fn(&str, &str, &Result<String>) + Send + Sync + 'static,
    {
        self.post_hooks.push(Arc::new(hook));
    }

    pub async fn execute(&self, tool_name: &str, input: &str) -> Result<String> {
        // Pre-execution hooks
        for hook in &self.pre_hooks {
            hook(tool_name, input);
        }

        // Execute tool
        let result = self.executor.execute(tool_name, input).await;

        // Post-execution hooks
        for hook in &self.post_hooks {
            hook(tool_name, input, &result);
        }

        result
    }
}

// Example hooks
fn logging_pre_hook(tool_name: &str, input: &str) {
    tracing::info!(
        tool = tool_name,
        input_len = input.len(),
        "Executing tool"
    );
}

fn logging_post_hook(tool_name: &str, input: &str, result: &Result<String>) {
    match result {
        Ok(output) => tracing::info!(
            tool = tool_name,
            output_len = output.len(),
            "Tool execution successful"
        ),
        Err(e) => tracing::error!(
            tool = tool_name,
            error = %e,
            "Tool execution failed"
        ),
    }
}

fn metrics_post_hook(tool_name: &str, input: &str, result: &Result<String>) {
    // Record metrics
    if result.is_ok() {
        metrics::counter!("tool_success", "tool" => tool_name.to_string()).increment(1);
    } else {
        metrics::counter!("tool_failure", "tool" => tool_name.to_string()).increment(1);
    }
}
```

---

## Agent State Management

### Comprehensive Memory System

**Full memory implementation with persistence and retrieval**:

```rust
use std::collections::{HashMap, VecDeque};
use chrono::{DateTime, Utc};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AgentMemory {
    // Short-term memory (recent conversation)
    pub conversation_history: VecDeque<ConversationTurn>,
    pub max_history_size: usize,

    // Long-term memory (facts and knowledge)
    pub facts: HashMap<String, Fact>,

    // Working memory (current task context)
    pub working_memory: HashMap<String, String>,

    // Metadata
    pub agent_id: String,
    pub created_at: DateTime<Utc>,
    pub last_updated: DateTime<Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ConversationTurn {
    pub turn_id: String,
    pub question: String,
    pub answer: String,
    pub reasoning_steps: Vec<ReasoningStep>,
    pub tools_used: Vec<String>,
    pub timestamp: DateTime<Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Fact {
    pub key: String,
    pub value: String,
    pub source: String,
    pub confidence: f64,
    pub created_at: DateTime<Utc>,
    pub last_accessed: DateTime<Utc>,
    pub access_count: usize,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ReasoningStep {
    pub step_type: StepType,
    pub content: String,
    pub timestamp: DateTime<Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum StepType {
    Thought,
    Action,
    Observation,
    Conclusion,
}

impl AgentMemory {
    pub fn new(agent_id: String) -> Self {
        let now = Utc::now();
        Self {
            conversation_history: VecDeque::new(),
            max_history_size: 100,
            facts: HashMap::new(),
            working_memory: HashMap::new(),
            agent_id,
            created_at: now,
            last_updated: now,
        }
    }

    pub fn add_turn(&mut self, turn: ConversationTurn) {
        // Add to history
        self.conversation_history.push_back(turn);

        // Prune old history
        while self.conversation_history.len() > self.max_history_size {
            self.conversation_history.pop_front();
        }

        self.last_updated = Utc::now();
    }

    pub fn add_fact(&mut self, key: String, value: String, source: String, confidence: f64) {
        let now = Utc::now();

        if let Some(fact) = self.facts.get_mut(&key) {
            // Update existing fact
            fact.value = value;
            fact.confidence = confidence;
            fact.last_accessed = now;
            fact.access_count += 1;
        } else {
            // Add new fact
            self.facts.insert(
                key.clone(),
                Fact {
                    key,
                    value,
                    source,
                    confidence,
                    created_at: now,
                    last_accessed: now,
                    access_count: 1,
                },
            );
        }

        self.last_updated = Utc::now();
    }

    pub fn get_fact(&mut self, key: &str) -> Option<&Fact> {
        if let Some(fact) = self.facts.get_mut(key) {
            fact.last_accessed = Utc::now();
            fact.access_count += 1;
        }
        self.facts.get(key)
    }

    pub fn get_recent_context(&self, max_turns: usize) -> String {
        let recent: Vec<_> = self.conversation_history
            .iter()
            .rev()
            .take(max_turns)
            .rev()
            .collect();

        if recent.is_empty() {
            return String::new();
        }

        let mut context = String::new();
        context.push_str("Recent conversation:\n");

        for turn in recent {
            context.push_str(&format!("Q: {}\n", turn.question));
            context.push_str(&format!("A: {}\n\n", turn.answer));
        }

        context
    }

    pub fn get_relevant_facts(&self, query: &str, max_facts: usize) -> Vec<&Fact> {
        // Simple relevance: keyword matching
        let query_lower = query.to_lowercase();
        let keywords: Vec<&str> = query_lower.split_whitespace().collect();

        let mut scored_facts: Vec<_> = self.facts.values()
            .map(|fact| {
                let key_lower = fact.key.to_lowercase();
                let value_lower = fact.value.to_lowercase();

                let score = keywords.iter()
                    .filter(|kw| key_lower.contains(*kw) || value_lower.contains(*kw))
                    .count();

                (fact, score)
            })
            .filter(|(_, score)| *score > 0)
            .collect();

        scored_facts.sort_by(|a, b| b.1.cmp(&a.1));

        scored_facts.iter()
            .take(max_facts)
            .map(|(fact, _)| *fact)
            .collect()
    }

    pub fn get_full_context(&self, query: &str, max_turns: usize, max_facts: usize) -> String {
        let mut context = String::new();

        // Add relevant facts
        let facts = self.get_relevant_facts(query, max_facts);
        if !facts.is_empty() {
            context.push_str("Relevant facts:\n");
            for fact in facts {
                context.push_str(&format!("- {}: {} (confidence: {:.2})\n",
                    fact.key, fact.value, fact.confidence));
            }
            context.push('\n');
        }

        // Add recent conversation
        let recent_context = self.get_recent_context(max_turns);
        if !recent_context.is_empty() {
            context.push_str(&recent_context);
        }

        context
    }

    pub fn save_to_file(&self, path: &str) -> Result<()> {
        let json = serde_json::to_string_pretty(self)?;
        std::fs::write(path, json)?;
        Ok(())
    }

    pub fn load_from_file(path: &str) -> Result<Self> {
        let json = std::fs::read_to_string(path)?;
        let memory = serde_json::from_str(&json)?;
        Ok(memory)
    }

    pub fn clear_working_memory(&mut self) {
        self.working_memory.clear();
        self.last_updated = Utc::now();
    }

    pub fn prune_old_facts(&mut self, max_age_days: i64) {
        let cutoff = Utc::now() - chrono::Duration::days(max_age_days);

        self.facts.retain(|_, fact| {
            fact.last_accessed > cutoff || fact.access_count > 10
        });

        self.last_updated = Utc::now();
    }
}
```

### Memory-Enhanced Agent

**Agent that uses memory for context-aware responses**:

```rust
pub struct MemoryEnhancedAgent {
    agent: ReActAgent,
    memory: Arc<RwLock<AgentMemory>>,
    max_context_turns: usize,
    max_context_facts: usize,
}

impl MemoryEnhancedAgent {
    pub fn new(
        agent: ReActAgent,
        memory: Arc<RwLock<AgentMemory>>,
    ) -> Self {
        Self {
            agent,
            memory,
            max_context_turns: 3,
            max_context_facts: 5,
        }
    }

    pub async fn execute(&self, question: &str) -> Result<String> {
        // Get context from memory
        let context = {
            let mem = self.memory.read().await;
            mem.get_full_context(
                question,
                self.max_context_turns,
                self.max_context_facts,
            )
        };

        // Augment question with context
        let augmented = if context.is_empty() {
            question.to_string()
        } else {
            format!("Context:\n{}\n\nQuestion: {}", context, question)
        };

        // Execute agent
        let result = self.agent.forward_with_trace(&augmented)?;

        // Update memory
        {
            let mut mem = self.memory.write().await;

            let turn = ConversationTurn {
                turn_id: uuid::Uuid::new_v4().to_string(),
                question: question.to_string(),
                answer: result.answer.clone(),
                reasoning_steps: result.trajectory.iter().map(|step| {
                    ReasoningStep {
                        step_type: StepType::Thought,
                        content: step.thought.clone(),
                        timestamp: Utc::now(),
                    }
                }).collect(),
                tools_used: Vec::new(),
                timestamp: Utc::now(),
            };

            mem.add_turn(turn);
        }

        Ok(result.answer)
    }
}
```

---

## Error Recovery Strategies

### Retry with Exponential Backoff

**Production-ready retry implementation**:

```rust
use tokio::time::sleep;
use std::time::Duration;

#[derive(Debug, Clone)]
pub struct RetryConfig {
    pub max_attempts: usize,
    pub initial_delay: Duration,
    pub max_delay: Duration,
    pub multiplier: f32,
    pub jitter: bool,
}

impl Default for RetryConfig {
    fn default() -> Self {
        Self {
            max_attempts: 3,
            initial_delay: Duration::from_millis(100),
            max_delay: Duration::from_secs(10),
            multiplier: 2.0,
            jitter: true,
        }
    }
}

pub async fn retry_with_backoff<F, T, E>(
    operation: F,
    config: &RetryConfig,
) -> Result<T, E>
where
    F: Fn() -> futures::future::BoxFuture<'static, Result<T, E>>,
    E: std::fmt::Display,
{
    let mut attempt = 0;
    let mut delay = config.initial_delay;

    loop {
        attempt += 1;

        match operation().await {
            Ok(result) => return Ok(result),
            Err(e) => {
                if attempt >= config.max_attempts {
                    tracing::error!(
                        attempt = attempt,
                        error = %e,
                        "All retry attempts exhausted"
                    );
                    return Err(e);
                }

                tracing::warn!(
                    attempt = attempt,
                    max_attempts = config.max_attempts,
                    delay_ms = delay.as_millis(),
                    error = %e,
                    "Operation failed, retrying"
                );

                // Apply jitter if enabled
                let actual_delay = if config.jitter {
                    let jitter_range = delay.as_millis() as f32 * 0.1;
                    let jitter = rand::random::<f32>() * jitter_range * 2.0 - jitter_range;
                    Duration::from_millis((delay.as_millis() as f32 + jitter) as u64)
                } else {
                    delay
                };

                sleep(actual_delay).await;

                // Calculate next delay
                delay = std::cmp::min(
                    Duration::from_millis(
                        (delay.as_millis() as f32 * config.multiplier) as u64
                    ),
                    config.max_delay,
                );
            }
        }
    }
}

// Usage with agent execution
pub async fn execute_agent_with_retry(
    agent: &ReActAgent,
    question: &str,
    config: &RetryConfig,
) -> Result<String> {
    retry_with_backoff(
        || {
            let question = question.to_string();
            Box::pin(async move {
                Python::with_gil(|py| {
                    // Execute agent
                    agent.forward(&question)
                }).map_err(|e| anyhow::anyhow!("{}", e))
            })
        },
        config,
    ).await
}
```

### Circuit Breaker Implementation

**Complete circuit breaker with state transitions**:

```rust
use std::sync::atomic::{AtomicUsize, AtomicU64, Ordering};
use std::sync::Arc;

#[derive(Debug, Clone, Copy, PartialEq)]
pub enum CircuitState {
    Closed,
    Open,
    HalfOpen,
}

pub struct CircuitBreaker {
    // Configuration
    failure_threshold: usize,
    success_threshold: usize,
    timeout: Duration,

    // State
    state: Arc<Mutex<CircuitState>>,
    failure_count: AtomicUsize,
    success_count: AtomicUsize,
    last_failure_time: AtomicU64,

    // Metrics
    total_calls: AtomicUsize,
    successful_calls: AtomicUsize,
    failed_calls: AtomicUsize,
    rejected_calls: AtomicUsize,
}

impl CircuitBreaker {
    pub fn new(
        failure_threshold: usize,
        success_threshold: usize,
        timeout: Duration,
    ) -> Self {
        Self {
            failure_threshold,
            success_threshold,
            timeout,
            state: Arc::new(Mutex::new(CircuitState::Closed)),
            failure_count: AtomicUsize::new(0),
            success_count: AtomicUsize::new(0),
            last_failure_time: AtomicU64::new(0),
            total_calls: AtomicUsize::new(0),
            successful_calls: AtomicUsize::new(0),
            failed_calls: AtomicUsize::new(0),
            rejected_calls: AtomicUsize::new(0),
        }
    }

    pub async fn call<F, T>(&self, f: F) -> Result<T>
    where
        F: Future<Output = Result<T>>,
    {
        self.total_calls.fetch_add(1, Ordering::Relaxed);

        let current_state = *self.state.lock().unwrap();

        match current_state {
            CircuitState::Open => {
                self.try_half_open()?;
                self.call_half_open(f).await
            }
            CircuitState::HalfOpen => {
                self.call_half_open(f).await
            }
            CircuitState::Closed => {
                self.call_closed(f).await
            }
        }
    }

    fn try_half_open(&self) -> Result<()> {
        let last_failure = self.last_failure_time.load(Ordering::Relaxed);
        let now = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_secs();

        if now - last_failure >= self.timeout.as_secs() {
            let mut state = self.state.lock().unwrap();
            if *state == CircuitState::Open {
                *state = CircuitState::HalfOpen;
                tracing::info!("Circuit breaker transitioning to half-open");
            }
            Ok(())
        } else {
            self.rejected_calls.fetch_add(1, Ordering::Relaxed);
            Err(anyhow::anyhow!("Circuit breaker is open"))
        }
    }

    async fn call_closed<F, T>(&self, f: F) -> Result<T>
    where
        F: Future<Output = Result<T>>,
    {
        match f.await {
            Ok(result) => {
                self.failure_count.store(0, Ordering::Relaxed);
                self.successful_calls.fetch_add(1, Ordering::Relaxed);
                Ok(result)
            }
            Err(e) => {
                let failures = self.failure_count.fetch_add(1, Ordering::Relaxed) + 1;
                self.failed_calls.fetch_add(1, Ordering::Relaxed);

                if failures >= self.failure_threshold {
                    self.transition_to_open();
                }

                Err(e)
            }
        }
    }

    async fn call_half_open<F, T>(&self, f: F) -> Result<T>
    where
        F: Future<Output = Result<T>>,
    {
        match f.await {
            Ok(result) => {
                let successes = self.success_count.fetch_add(1, Ordering::Relaxed) + 1;
                self.successful_calls.fetch_add(1, Ordering::Relaxed);

                if successes >= self.success_threshold {
                    self.transition_to_closed();
                }

                Ok(result)
            }
            Err(e) => {
                self.failed_calls.fetch_add(1, Ordering::Relaxed);
                self.transition_to_open();
                Err(e)
            }
        }
    }

    fn transition_to_open(&self) {
        let mut state = self.state.lock().unwrap();
        *state = CircuitState::Open;

        let now = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_secs();
        self.last_failure_time.store(now, Ordering::Relaxed);

        self.success_count.store(0, Ordering::Relaxed);

        tracing::warn!("Circuit breaker opened");
    }

    fn transition_to_closed(&self) {
        let mut state = self.state.lock().unwrap();
        *state = CircuitState::Closed;

        self.failure_count.store(0, Ordering::Relaxed);
        self.success_count.store(0, Ordering::Relaxed);

        tracing::info!("Circuit breaker closed");
    }

    pub fn get_metrics(&self) -> CircuitBreakerMetrics {
        CircuitBreakerMetrics {
            state: *self.state.lock().unwrap(),
            total_calls: self.total_calls.load(Ordering::Relaxed),
            successful_calls: self.successful_calls.load(Ordering::Relaxed),
            failed_calls: self.failed_calls.load(Ordering::Relaxed),
            rejected_calls: self.rejected_calls.load(Ordering::Relaxed),
        }
    }
}

#[derive(Debug, Clone)]
pub struct CircuitBreakerMetrics {
    pub state: CircuitState,
    pub total_calls: usize,
    pub successful_calls: usize,
    pub failed_calls: usize,
    pub rejected_calls: usize,
}
```

### Fallback Strategies

**Implement fallback when primary agent fails**:

```rust
pub struct FallbackAgent {
    primary: ReActAgent,
    fallback: ReActAgent,
    circuit_breaker: Arc<CircuitBreaker>,
}

impl FallbackAgent {
    pub fn new(
        primary: ReActAgent,
        fallback: ReActAgent,
        circuit_breaker: Arc<CircuitBreaker>,
    ) -> Self {
        Self {
            primary,
            fallback,
            circuit_breaker,
        }
    }

    pub async fn execute(&self, question: &str) -> Result<String> {
        // Try primary with circuit breaker
        let primary_result = self.circuit_breaker.call(async {
            self.primary.forward(question)
                .map_err(|e| anyhow::anyhow!("{}", e))
        }).await;

        match primary_result {
            Ok(answer) => {
                tracing::info!("Primary agent succeeded");
                Ok(answer)
            }
            Err(e) => {
                tracing::warn!(
                    error = %e,
                    "Primary agent failed, falling back to secondary"
                );

                // Use fallback
                self.fallback.forward(question)
                    .map_err(|e| anyhow::anyhow!("Fallback also failed: {}", e))
            }
        }
    }
}
```

---

## Multi-Step Reasoning

### Question Decomposition

**Decompose complex questions into sub-questions**:

```rust
pub struct DecomposingAgent {
    decomposer: Py<PyAny>,
    solver: Py<PyAny>,
    synthesizer: Py<PyAny>,
}

impl DecomposingAgent {
    pub fn new() -> PyResult<Self> {
        Python::with_gil(|py| {
            let dspy = PyModule::import(py, "dspy")?;

            // Create modules
            let decomposer = dspy.getattr("ChainOfThought")?
                .call1((("complex_question -> sub_questions",),))?;

            let solver = dspy.getattr("ReAct")?
                .call1((("question -> answer",),))?;

            let synthesizer = dspy.getattr("ChainOfThought")?
                .call1((("sub_answers -> final_answer",),))?;

            Ok(Self {
                decomposer: decomposer.into(),
                solver: solver.into(),
                synthesizer: synthesizer.into(),
            })
        })
    }

    pub fn execute(&self, question: &str) -> PyResult<MultiStepResult> {
        Python::with_gil(|py| {
            // Step 1: Decompose question
            let decomp_result = self.decomposer.as_ref(py).call_method1(
                "forward",
                ((question,),)
            )?;

            let sub_questions_str: String = decomp_result
                .getattr("sub_questions")?
                .extract()?;

            let sub_questions: Vec<String> = sub_questions_str
                .lines()
                .map(|s| s.trim().to_string())
                .filter(|s| !s.is_empty())
                .collect();

            // Step 2: Solve each sub-question
            let mut sub_answers = Vec::new();

            for (idx, sub_q) in sub_questions.iter().enumerate() {
                tracing::info!(
                    step = idx + 1,
                    total = sub_questions.len(),
                    question = sub_q,
                    "Solving sub-question"
                );

                let answer_result = self.solver.as_ref(py).call_method1(
                    "forward",
                    ((sub_q.as_str(),),)
                )?;

                let answer: String = answer_result.getattr("answer")?.extract()?;
                sub_answers.push(format!("Q{}: {}\nA{}: {}", idx + 1, sub_q, idx + 1, answer));
            }

            // Step 3: Synthesize final answer
            let synthesis_input = sub_answers.join("\n\n");

            let final_result = self.synthesizer.as_ref(py).call_method1(
                "forward",
                ((synthesis_input.as_str(),),)
            )?;

            let final_answer: String = final_result.getattr("final_answer")?.extract()?;

            Ok(MultiStepResult {
                original_question: question.to_string(),
                sub_questions,
                sub_answers: sub_answers.iter()
                    .map(|s| s.lines().last().unwrap_or("").to_string())
                    .collect(),
                final_answer,
                total_steps: sub_questions.len(),
            })
        })
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MultiStepResult {
    pub original_question: String,
    pub sub_questions: Vec<String>,
    pub sub_answers: Vec<String>,
    pub final_answer: String,
    pub total_steps: usize,
}
```

### Reasoning Chain Logging

**Complete reasoning chain tracking and export**:

```rust
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ReasoningChain {
    pub chain_id: String,
    pub question: String,
    pub steps: Vec<DetailedReasoningStep>,
    pub final_conclusion: String,
    pub total_duration_ms: u64,
    pub timestamp: DateTime<Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DetailedReasoningStep {
    pub step_number: usize,
    pub step_type: String,
    pub thought: String,
    pub action: Option<String>,
    pub tool_used: Option<String>,
    pub tool_input: Option<String>,
    pub observation: Option<String>,
    pub confidence: Option<f64>,
    pub duration_ms: u64,
}

pub struct ReasoningChainLogger {
    chains: Arc<Mutex<Vec<ReasoningChain>>>,
    log_dir: String,
}

impl ReasoningChainLogger {
    pub fn new(log_dir: String) -> Result<Self> {
        std::fs::create_dir_all(&log_dir)?;

        Ok(Self {
            chains: Arc::new(Mutex::new(Vec::new())),
            log_dir,
        })
    }

    pub fn log_chain(&self, chain: ReasoningChain) -> Result<()> {
        // Add to in-memory log
        self.chains.lock().unwrap().push(chain.clone());

        // Write to file
        let filename = format!(
            "{}/chain_{}.json",
            self.log_dir,
            chain.chain_id
        );

        let json = serde_json::to_string_pretty(&chain)?;
        std::fs::write(filename, json)?;

        Ok(())
    }

    pub fn export_all(&self, path: &str) -> Result<()> {
        let chains = self.chains.lock().unwrap();
        let json = serde_json::to_string_pretty(&*chains)?;
        std::fs::write(path, json)?;
        Ok(())
    }

    pub fn get_statistics(&self) -> ReasoningStats {
        let chains = self.chains.lock().unwrap();

        let total = chains.len();
        let avg_steps = if total > 0 {
            chains.iter().map(|c| c.steps.len()).sum::<usize>() / total
        } else {
            0
        };

        let avg_duration = if total > 0 {
            chains.iter().map(|c| c.total_duration_ms).sum::<u64>() / total as u64
        } else {
            0
        };

        ReasoningStats {
            total_chains: total,
            average_steps: avg_steps,
            average_duration_ms: avg_duration,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ReasoningStats {
    pub total_chains: usize,
    pub average_steps: usize,
    pub average_duration_ms: u64,
}
```

---

## Parallel Agent Execution

### Agent Pool Management

**Production agent pool with work distribution**:

```rust
use tokio::sync::{Semaphore, RwLock};
use std::sync::Arc;

pub struct AgentPool {
    agents: Arc<RwLock<Vec<ReActAgent>>>,
    semaphore: Arc<Semaphore>,
    size: usize,
}

impl AgentPool {
    pub async fn new(size: usize, config: ReActConfig) -> Result<Self> {
        let mut agents = Vec::with_capacity(size);

        for _ in 0..size {
            let agent = ReActAgent::new(config.clone())?;
            agents.push(agent);
        }

        Ok(Self {
            agents: Arc::new(RwLock::new(agents)),
            semaphore: Arc::new(Semaphore::new(size)),
            size,
        })
    }

    pub async fn execute(&self, question: String) -> Result<String> {
        // Acquire permit
        let _permit = self.semaphore.acquire().await?;

        // Get agent from pool
        let agent = {
            let agents = self.agents.read().await;
            agents.first()
                .ok_or_else(|| anyhow::anyhow!("No agents available"))?
                .clone()
        };

        // Execute (permit released on drop)
        agent.forward(&question)
            .map_err(|e| anyhow::anyhow!("{}", e))
    }

    pub async fn execute_batch(&self, questions: Vec<String>) -> Vec<Result<String>> {
        let mut handles = Vec::new();

        for question in questions {
            let pool = self.clone();
            let handle = tokio::spawn(async move {
                pool.execute(question).await
            });
            handles.push(handle);
        }

        let mut results = Vec::new();
        for handle in handles {
            let result = handle.await
                .map_err(|e| anyhow::anyhow!("{}", e))
                .and_then(|r| r);
            results.push(result);
        }

        results
    }
}

impl Clone for AgentPool {
    fn clone(&self) -> Self {
        Self {
            agents: Arc::clone(&self.agents),
            semaphore: Arc::clone(&self.semaphore),
            size: self.size,
        }
    }
}
```

### Parallel Execution with Result Aggregation

**Execute multiple agents and combine results**:

```rust
use futures::stream::{self, StreamExt};

pub async fn execute_parallel_with_voting(
    agents: Vec<ReActAgent>,
    question: &str,
    consensus_threshold: f32,
) -> Result<String> {
    // Execute all agents in parallel
    let results = stream::iter(agents)
        .map(|agent| {
            let question = question.to_string();
            async move {
                agent.forward(&question)
            }
        })
        .buffer_unordered(agents.len())
        .collect::<Vec<_>>()
        .await;

    // Count answers
    let mut answer_counts: HashMap<String, usize> = HashMap::new();
    let mut total_valid = 0;

    for result in results {
        if let Ok(answer) = result {
            *answer_counts.entry(answer).or_insert(0) += 1;
            total_valid += 1;
        }
    }

    // Find consensus
    if let Some((answer, count)) = answer_counts.iter()
        .max_by_key(|(_, count)| *count)
    {
        let confidence = *count as f32 / total_valid as f32;

        if confidence >= consensus_threshold {
            Ok(answer.clone())
        } else {
            Err(anyhow::anyhow!(
                "No consensus reached (confidence: {:.2})",
                confidence
            ))
        }
    } else {
        Err(anyhow::anyhow!("No valid answers"))
    }
}
```

---

## Production Agent Systems

### Complete Production Architecture

**Enterprise-ready agent system**:

```rust
use prometheus::{Counter, Histogram, Registry};

pub struct ProductionAgentSystem {
    // Components
    agent_pool: Arc<AgentPool>,
    tool_registry: Arc<ToolRegistry>,
    memory_store: Arc<RwLock<HashMap<String, AgentMemory>>>,
    circuit_breaker: Arc<CircuitBreaker>,
    chain_logger: Arc<ReasoningChainLogger>,

    // Metrics
    metrics: Arc<Metrics>,
}

struct Metrics {
    requests_total: Counter,
    requests_success: Counter,
    requests_failure: Counter,
    request_duration: Histogram,
    reasoning_steps: Histogram,
}

impl ProductionAgentSystem {
    pub async fn new(config: SystemConfig) -> Result<Self> {
        // Initialize agent pool
        let agent_pool = AgentPool::new(
            config.pool_size,
            config.agent_config,
        ).await?;

        // Initialize tool registry
        let tool_registry = Arc::new(ToolRegistry::new());

        // Initialize memory store
        let memory_store = Arc::new(RwLock::new(HashMap::new()));

        // Initialize circuit breaker
        let circuit_breaker = Arc::new(CircuitBreaker::new(
            config.circuit_breaker_threshold,
            config.circuit_breaker_success_threshold,
            config.circuit_breaker_timeout,
        ));

        // Initialize chain logger
        let chain_logger = Arc::new(ReasoningChainLogger::new(
            config.log_dir.clone(),
        )?);

        // Initialize metrics
        let metrics = Arc::new(Metrics::new()?);

        Ok(Self {
            agent_pool: Arc::new(agent_pool),
            tool_registry,
            memory_store,
            circuit_breaker,
            chain_logger,
            metrics,
        })
    }

    pub async fn execute_task(
        &self,
        user_id: String,
        question: String,
    ) -> Result<ExecutionResult> {
        let start = std::time::Instant::now();
        self.metrics.requests_total.inc();

        // Get or create user memory
        let memory = {
            let mut store = self.memory_store.write().await;
            store.entry(user_id.clone())
                .or_insert_with(|| AgentMemory::new(user_id.clone()))
                .clone()
        };

        // Build context
        let context = memory.get_full_context(&question, 3, 5);
        let augmented_question = if context.is_empty() {
            question.clone()
        } else {
            format!("Context:\n{}\n\nQuestion: {}", context, question)
        };

        // Execute with circuit breaker
        let result = self.circuit_breaker.call(async {
            self.agent_pool.execute(augmented_question.clone()).await
        }).await;

        let duration = start.elapsed();

        match result {
            Ok(answer) => {
                self.metrics.requests_success.inc();
                self.metrics.request_duration.observe(duration.as_secs_f64());

                // Update memory
                {
                    let mut store = self.memory_store.write().await;
                    if let Some(mem) = store.get_mut(&user_id) {
                        let turn = ConversationTurn {
                            turn_id: uuid::Uuid::new_v4().to_string(),
                            question: question.clone(),
                            answer: answer.clone(),
                            reasoning_steps: Vec::new(),
                            tools_used: Vec::new(),
                            timestamp: Utc::now(),
                        };
                        mem.add_turn(turn);
                    }
                }

                Ok(ExecutionResult {
                    answer,
                    duration_ms: duration.as_millis() as u64,
                    success: true,
                })
            }
            Err(e) => {
                self.metrics.requests_failure.inc();
                Err(e)
            }
        }
    }

    pub async fn save_all_state(&self) -> Result<()> {
        // Save all memories
        let store = self.memory_store.read().await;
        for (user_id, memory) in store.iter() {
            let path = format!("./data/memories/{}.json", user_id);
            memory.save_to_file(&path)?;
        }

        // Export reasoning chains
        self.chain_logger.export_all("./data/chains.json")?;

        Ok(())
    }

    pub fn get_metrics(&self) -> SystemMetrics {
        let cb_metrics = self.circuit_breaker.get_metrics();
        let chain_stats = self.chain_logger.get_statistics();

        SystemMetrics {
            total_requests: self.metrics.requests_total.get() as usize,
            successful_requests: self.metrics.requests_success.get() as usize,
            failed_requests: self.metrics.requests_failure.get() as usize,
            circuit_breaker_state: cb_metrics.state,
            average_reasoning_steps: chain_stats.average_steps,
        }
    }
}

#[derive(Debug, Clone)]
pub struct SystemConfig {
    pub pool_size: usize,
    pub agent_config: ReActConfig,
    pub circuit_breaker_threshold: usize,
    pub circuit_breaker_success_threshold: usize,
    pub circuit_breaker_timeout: Duration,
    pub log_dir: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExecutionResult {
    pub answer: String,
    pub duration_ms: u64,
    pub success: bool,
}

#[derive(Debug, Clone)]
pub struct SystemMetrics {
    pub total_requests: usize,
    pub successful_requests: usize,
    pub failed_requests: usize,
    pub circuit_breaker_state: CircuitState,
    pub average_reasoning_steps: usize,
}

impl Metrics {
    fn new() -> Result<Self> {
        Ok(Self {
            requests_total: Counter::new("agent_requests_total", "Total requests")?,
            requests_success: Counter::new("agent_requests_success", "Successful requests")?,
            requests_failure: Counter::new("agent_requests_failure", "Failed requests")?,
            request_duration: Histogram::new("agent_request_duration_seconds", "Request duration")?,
            reasoning_steps: Histogram::new("agent_reasoning_steps", "Reasoning steps")?,
        })
    }
}
```

---

## Observability

### Structured Logging

**Comprehensive logging with tracing**:

```rust
use tracing::{info, warn, error, instrument, Span};
use tracing_subscriber::layer::SubscriberExt;

pub fn init_logging() -> Result<()> {
    let subscriber = tracing_subscriber::registry()
        .with(tracing_subscriber::fmt::layer())
        .with(tracing_subscriber::EnvFilter::from_default_env());

    tracing::subscriber::set_global_default(subscriber)?;

    Ok(())
}

#[instrument(skip(agent), fields(question_len = question.len()))]
pub async fn execute_with_tracing(
    agent: &ReActAgent,
    question: &str,
) -> Result<String> {
    let span = Span::current();

    info!("Starting agent execution");

    let start = std::time::Instant::now();

    let result = agent.forward(question);

    let duration = start.elapsed();

    match &result {
        Ok(answer) => {
            span.record("answer_len", answer.len());
            span.record("duration_ms", duration.as_millis());

            info!(
                duration_ms = duration.as_millis(),
                answer_len = answer.len(),
                "Agent execution successful"
            );
        }
        Err(e) => {
            span.record("error", &e.to_string());

            error!(
                duration_ms = duration.as_millis(),
                error = %e,
                "Agent execution failed"
            );
        }
    }

    result.map_err(|e| anyhow::anyhow!("{}", e))
}
```

### Performance Monitoring

**Detailed performance tracking**:

```rust
use std::time::Instant;

pub struct PerformanceMonitor {
    traces: Arc<Mutex<Vec<PerformanceTrace>>>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PerformanceTrace {
    pub operation: String,
    pub duration_ms: u64,
    pub timestamp: DateTime<Utc>,
    pub metadata: HashMap<String, String>,
}

impl PerformanceMonitor {
    pub fn new() -> Self {
        Self {
            traces: Arc::new(Mutex::new(Vec::new())),
        }
    }

    pub fn start_trace(&self, operation: String) -> TraceGuard {
        TraceGuard {
            operation,
            start: Instant::now(),
            monitor: self.traces.clone(),
            metadata: HashMap::new(),
        }
    }

    pub fn get_report(&self) -> PerformanceReport {
        let traces = self.traces.lock().unwrap();

        let mut op_stats: HashMap<String, Vec<u64>> = HashMap::new();

        for trace in traces.iter() {
            op_stats.entry(trace.operation.clone())
                .or_insert_with(Vec::new)
                .push(trace.duration_ms);
        }

        let stats: HashMap<String, OperationStats> = op_stats.iter()
            .map(|(op, durations)| {
                let total = durations.len();
                let sum: u64 = durations.iter().sum();
                let avg = if total > 0 { sum / total as u64 } else { 0 };
                let min = durations.iter().min().copied().unwrap_or(0);
                let max = durations.iter().max().copied().unwrap_or(0);

                (op.clone(), OperationStats {
                    count: total,
                    avg_ms: avg,
                    min_ms: min,
                    max_ms: max,
                })
            })
            .collect();

        PerformanceReport { stats }
    }
}

pub struct TraceGuard {
    operation: String,
    start: Instant,
    monitor: Arc<Mutex<Vec<PerformanceTrace>>>,
    metadata: HashMap<String, String>,
}

impl TraceGuard {
    pub fn add_metadata(&mut self, key: String, value: String) {
        self.metadata.insert(key, value);
    }
}

impl Drop for TraceGuard {
    fn drop(&mut self) {
        let duration = self.start.elapsed();

        let trace = PerformanceTrace {
            operation: self.operation.clone(),
            duration_ms: duration.as_millis() as u64,
            timestamp: Utc::now(),
            metadata: self.metadata.clone(),
        };

        self.monitor.lock().unwrap().push(trace);
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PerformanceReport {
    pub stats: HashMap<String, OperationStats>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OperationStats {
    pub count: usize,
    pub avg_ms: u64,
    pub min_ms: u64,
    pub max_ms: u64,
}
```

---

## Best Practices Summary

### Configuration Best Practices

✅ **DO**:
- Set reasonable max iterations (5-10 for most tasks)
- Configure timeouts for all operations
- Use environment variables for API keys
- Validate configuration before use
- Document configuration options

❌ **DON'T**:
- Allow unlimited iterations
- Hard-code credentials
- Skip configuration validation
- Use default configs in production

### Tool Management Best Practices

✅ **DO**:
- Validate tool inputs before execution
- Implement timeouts for all tools
- Log all tool executions
- Monitor tool performance
- Sandbox tool execution

❌ **DON'T**:
- Execute untrusted code
- Skip input validation
- Ignore tool failures
- Allow unbounded tool execution

### Memory Management Best Practices

✅ **DO**:
- Limit memory size (max 100 turns)
- Prune old facts regularly
- Persist memory to disk
- Use relevance scoring for retrieval
- Clear working memory between tasks

❌ **DON'T**:
- Allow unbounded growth
- Store sensitive data unencrypted
- Skip memory backups
- Use global memory state

### Error Handling Best Practices

✅ **DO**:
- Implement retry with backoff
- Use circuit breakers
- Provide fallback agents
- Log all errors with context
- Monitor error rates

❌ **DON'T**:
- Retry indefinitely
- Ignore circuit breaker state
- Expose internal errors to users
- Skip error logging

### Production Best Practices

✅ **DO**:
- Use agent pools for concurrency
- Monitor all metrics
- Implement structured logging
- Test failure scenarios
- Document system architecture

❌ **DON'T**:
- Deploy without monitoring
- Skip load testing
- Ignore performance metrics
- Use single agent instance

---

**Version**: 1.0.0
**Last Updated**: 2025-10-30
**Maintainer**: DSPy-PyO3 Integration Team
