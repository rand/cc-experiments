---
skill_id: rust-pyo3-dspy-agents
title: PyO3 DSPy ReAct Agents
category: rust
subcategory: pyo3-dspy
complexity: advanced
prerequisites:
  - rust-pyo3-dspy-fundamentals
  - rust-pyo3-dspy-type-system
  - ml-dspy-agents
  - ml-dspy-react
tags:
  - rust
  - python
  - pyo3
  - dspy
  - agents
  - react
  - tools
  - reasoning
version: 1.0.0
last_updated: 2025-10-30
learning_outcomes:
  - Implement ReAct agents from Rust with DSPy
  - Build and manage tool registries in Rust
  - Execute tools from Rust side with error recovery
  - Persist agent state across reasoning chains
  - Handle multi-step reasoning patterns
  - Deploy production agent systems
related_skills:
  - rust-pyo3-dspy-fundamentals
  - rust-pyo3-dspy-rag-pipelines
  - ml-dspy-agents
  - rust-async-tokio
resources:
  - REFERENCE.md (800+ lines): Complete agent patterns
  - 3 Python scripts (900+ lines): Tool registry, state manager, agent runner
  - 7 Rust+Python examples (1,500+ lines): Working agent systems
---

# PyO3 DSPy ReAct Agents

## Overview

Master building intelligent ReAct (Reason-Act-Observe) agents using DSPy from Rust. Learn to implement tool registries, manage agent state, handle multi-step reasoning chains, and deploy production-ready agent systems that combine Rust's performance with DSPy's powerful reasoning abstractions.

ReAct agents iterate through reasoning, action selection, and observation cycles to solve complex problems. This skill teaches you how to orchestrate these patterns from Rust, giving you the safety and performance benefits of Rust while leveraging DSPy's advanced agent capabilities.

## Prerequisites

**Required**:
- PyO3 DSPy fundamentals (module calling, error handling)
- DSPy agent patterns (ReAct, tool usage, signatures)
- Rust async programming (Tokio)
- Understanding of agent architectures

**Recommended**:
- RAG pipeline experience
- State management patterns
- Distributed systems concepts
- Production monitoring practices

## When to Use

**Ideal for**:
- **Complex multi-step tasks** requiring reasoning chains
- **Tool-using agents** that interact with external systems
- **High-performance agent systems** serving many users
- **Production agent services** with strict reliability requirements
- **Embedded agents** in Rust applications (CLI tools, services)
- **Type-safe agent orchestration** with compile-time guarantees

**Not ideal for**:
- Simple single-step predictions (use basic modules)
- Pure Python prototypes (overhead not justified)
- Tasks without clear action space (use RAG instead)
- Real-time systems with microsecond latency requirements

## Learning Path

### 1. ReAct Pattern Fundamentals

The ReAct pattern implements a loop: **Reason** → **Act** → **Observe** → repeat.

**Basic ReAct Call from Rust**:

```rust
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};
use serde::{Deserialize, Serialize};

#[derive(Debug, Serialize, Deserialize)]
struct AgentStep {
    thought: String,
    action: String,
    observation: String,
}

fn call_react_agent(py: Python, question: &str, max_steps: usize) -> PyResult<String> {
    // Import DSPy
    let dspy = PyModule::import(py, "dspy")?;

    // Create ReAct module
    let react = dspy.getattr("ReAct")?;
    let signature = "question -> answer";
    let agent = react.call1(((signature,),))?;

    // Configure max steps
    agent.setattr("max_iters", max_steps)?;

    // Execute agent
    let result = agent.call1(((question,),))?;

    // Extract final answer
    let answer: String = result.getattr("answer")?.extract()?;

    Ok(answer)
}

fn main() -> PyResult<()> {
    Python::with_gil(|py| {
        // Configure DSPy LM
        configure_lm(py)?;

        let answer = call_react_agent(
            py,
            "What is the capital of France and what is its population?",
            5
        )?;

        println!("Final answer: {}", answer);
        Ok(())
    })
}
```

**With Step Tracing**:

```rust
#[derive(Debug, Clone)]
struct ReActTrace {
    steps: Vec<AgentStep>,
    final_answer: String,
    total_steps: usize,
}

fn call_react_with_trace(
    py: Python,
    question: &str,
    max_steps: usize,
) -> PyResult<ReActTrace> {
    let dspy = PyModule::import(py, "dspy")?;
    let react = dspy.getattr("ReAct")?;

    let signature = "question -> answer";
    let agent = react.call1(((signature,),))?;
    agent.setattr("max_iters", max_steps)?;

    // Execute
    let result = agent.call1(((question,),))?;

    // Extract trace
    let mut steps = Vec::new();

    if let Ok(history) = result.getattr("trajectory") {
        let py_list: &PyList = history.downcast()?;

        for item in py_list.iter() {
            let thought: String = item.getattr("thought")?.extract()?;
            let action: String = item.getattr("action")?.extract()?;
            let observation: String = item.getattr("observation")?.extract()?;

            steps.push(AgentStep {
                thought,
                action,
                observation,
            });
        }
    }

    let final_answer: String = result.getattr("answer")?.extract()?;
    let total_steps = steps.len();

    Ok(ReActTrace {
        steps,
        final_answer,
        total_steps,
    })
}
```

### 2. Tool Registry Implementation

**Rust-side Tool Registry**:

```rust
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyModule};
use std::collections::HashMap;
use anyhow::{Context, Result};

type ToolFn = Box<dyn Fn(&str) -> Result<String> + Send + Sync>;

pub struct ToolRegistry {
    tools: HashMap<String, ToolFn>,
}

impl ToolRegistry {
    pub fn new() -> Self {
        Self {
            tools: HashMap::new(),
        }
    }

    pub fn register<F>(&mut self, name: &str, tool: F)
    where
        F: Fn(&str) -> Result<String> + Send + Sync + 'static,
    {
        self.tools.insert(name.to_string(), Box::new(tool));
    }

    pub fn execute(&self, name: &str, input: &str) -> Result<String> {
        let tool = self.tools
            .get(name)
            .ok_or_else(|| anyhow::anyhow!("Tool not found: {}", name))?;

        tool(input)
    }

    pub fn list_tools(&self) -> Vec<String> {
        self.tools.keys().cloned().collect()
    }

    pub fn to_python_tools(&self, py: Python) -> PyResult<PyObject> {
        // Convert to Python tool list for DSPy
        let tools_list = PyList::empty(py);

        for tool_name in self.tools.keys() {
            let tool_dict = PyDict::new(py);
            tool_dict.set_item("name", tool_name)?;
            tool_dict.set_item("description", format!("Tool: {}", tool_name))?;
            tools_list.append(tool_dict)?;
        }

        Ok(tools_list.into())
    }
}

// Example tools
fn search_tool(query: &str) -> Result<String> {
    // In real implementation, call search API
    Ok(format!("Search results for: {}", query))
}

fn calculator_tool(expression: &str) -> Result<String> {
    // In real implementation, safely evaluate math
    Ok(format!("Calculated: {} = 42", expression))
}

fn weather_tool(location: &str) -> Result<String> {
    // In real implementation, call weather API
    Ok(format!("Weather in {}: Sunny, 72°F", location))
}

fn main() -> Result<()> {
    let mut registry = ToolRegistry::new();

    registry.register("search", search_tool);
    registry.register("calculator", calculator_tool);
    registry.register("weather", weather_tool);

    // Test tool execution
    let result = registry.execute("search", "rust programming")?;
    println!("Tool result: {}", result);

    Ok(())
}
```

**Integrating Tools with DSPy ReAct**:

```rust
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyModule, PyList};
use std::sync::{Arc, Mutex};

pub struct ReActAgentWithTools {
    registry: Arc<Mutex<ToolRegistry>>,
    agent: Py<PyAny>,
}

impl ReActAgentWithTools {
    pub fn new(py: Python, registry: Arc<Mutex<ToolRegistry>>) -> PyResult<Self> {
        let dspy = PyModule::import(py, "dspy")?;

        // Define custom tool execution module
        let tool_executor = PyModule::from_code(
            py,
            r#"
import dspy

class ToolExecutor(dspy.Module):
    def __init__(self, tool_names):
        super().__init__()
        self.tool_names = tool_names
        self.react = dspy.ReAct(
            "question -> answer",
            tools=tool_names
        )

    def forward(self, question):
        return self.react(question=question)
"#,
            "tool_executor.py",
            "tool_executor",
        )?;

        let tool_names = {
            let reg = registry.lock().unwrap();
            reg.list_tools()
        };

        let py_tools = PyList::new(py, &tool_names);
        let executor_class = tool_executor.getattr("ToolExecutor")?;
        let agent = executor_class.call1((py_tools,))?;

        Ok(Self {
            registry,
            agent: agent.into(),
        })
    }

    pub fn execute(&self, py: Python, question: &str) -> PyResult<String> {
        // Hook tool execution
        let result = self.agent.as_ref(py).call_method1(
            "forward",
            ((question,),)
        )?;

        let answer: String = result.getattr("answer")?.extract()?;
        Ok(answer)
    }
}
```

### 3. Agent State Management

**Persistent Agent State**:

```rust
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use chrono::{DateTime, Utc};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AgentMemory {
    conversation_history: Vec<ConversationTurn>,
    facts: HashMap<String, String>,
    created_at: DateTime<Utc>,
    last_updated: DateTime<Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ConversationTurn {
    question: String,
    answer: String,
    reasoning_steps: usize,
    timestamp: DateTime<Utc>,
}

impl AgentMemory {
    pub fn new() -> Self {
        let now = Utc::now();
        Self {
            conversation_history: Vec::new(),
            facts: HashMap::new(),
            created_at: now,
            last_updated: now,
        }
    }

    pub fn add_turn(&mut self, question: String, answer: String, steps: usize) {
        self.conversation_history.push(ConversationTurn {
            question,
            answer,
            reasoning_steps: steps,
            timestamp: Utc::now(),
        });
        self.last_updated = Utc::now();
    }

    pub fn add_fact(&mut self, key: String, value: String) {
        self.facts.insert(key, value);
        self.last_updated = Utc::now();
    }

    pub fn get_context(&self, max_turns: usize) -> String {
        let recent_history: Vec<_> = self.conversation_history
            .iter()
            .rev()
            .take(max_turns)
            .rev()
            .collect();

        let mut context = String::new();

        if !self.facts.is_empty() {
            context.push_str("Known facts:\n");
            for (key, value) in &self.facts {
                context.push_str(&format!("- {}: {}\n", key, value));
            }
            context.push('\n');
        }

        if !recent_history.is_empty() {
            context.push_str("Recent conversation:\n");
            for turn in recent_history {
                context.push_str(&format!("Q: {}\n", turn.question));
                context.push_str(&format!("A: {}\n\n", turn.answer));
            }
        }

        context
    }

    pub fn save(&self, path: &str) -> Result<()> {
        let json = serde_json::to_string_pretty(self)?;
        std::fs::write(path, json)?;
        Ok(())
    }

    pub fn load(path: &str) -> Result<Self> {
        let json = std::fs::read_to_string(path)?;
        let memory = serde_json::from_str(&json)?;
        Ok(memory)
    }
}

// Stateful agent
pub struct StatefulReActAgent {
    registry: Arc<Mutex<ToolRegistry>>,
    memory: Arc<Mutex<AgentMemory>>,
    agent: Py<PyAny>,
}

impl StatefulReActAgent {
    pub fn execute_with_memory(
        &self,
        py: Python,
        question: &str,
    ) -> PyResult<String> {
        let context = {
            let mem = self.memory.lock().unwrap();
            mem.get_context(3)
        };

        // Augment question with context
        let augmented_question = if context.is_empty() {
            question.to_string()
        } else {
            format!("{}\n\nContext:\n{}\n\nQuestion: {}",
                context, context, question)
        };

        // Execute agent
        let result = self.agent.as_ref(py).call_method1(
            "forward",
            ((augmented_question,),)
        )?;

        let answer: String = result.getattr("answer")?.extract()?;

        // Update memory
        {
            let mut mem = self.memory.lock().unwrap();
            mem.add_turn(question.to_string(), answer.clone(), 0);
        }

        Ok(answer)
    }
}
```

### 4. Error Recovery Strategies

**Robust Tool Execution with Retry**:

```rust
use std::time::Duration;
use tokio::time::sleep;

#[derive(Debug, Clone)]
pub struct RetryConfig {
    max_retries: usize,
    initial_delay: Duration,
    max_delay: Duration,
    backoff_multiplier: f32,
}

impl Default for RetryConfig {
    fn default() -> Self {
        Self {
            max_retries: 3,
            initial_delay: Duration::from_millis(100),
            max_delay: Duration::from_secs(5),
            backoff_multiplier: 2.0,
        }
    }
}

pub async fn execute_tool_with_retry(
    registry: &ToolRegistry,
    tool_name: &str,
    input: &str,
    config: &RetryConfig,
) -> Result<String> {
    let mut attempts = 0;
    let mut delay = config.initial_delay;

    loop {
        attempts += 1;

        match registry.execute(tool_name, input) {
            Ok(result) => return Ok(result),
            Err(e) => {
                if attempts >= config.max_retries {
                    return Err(anyhow::anyhow!(
                        "Tool execution failed after {} attempts: {}",
                        attempts, e
                    ));
                }

                eprintln!(
                    "Tool execution failed (attempt {}/{}): {}. Retrying in {:?}...",
                    attempts, config.max_retries, e, delay
                );

                sleep(delay).await;

                delay = std::cmp::min(
                    Duration::from_secs_f32(delay.as_secs_f32() * config.backoff_multiplier),
                    config.max_delay
                );
            }
        }
    }
}

// Circuit breaker pattern
use std::sync::atomic::{AtomicUsize, Ordering};

pub struct CircuitBreaker {
    failure_threshold: usize,
    success_threshold: usize,
    timeout: Duration,
    failure_count: AtomicUsize,
    success_count: AtomicUsize,
    last_failure_time: Mutex<Option<std::time::Instant>>,
    state: Mutex<CircuitState>,
}

#[derive(Debug, Clone, Copy, PartialEq)]
enum CircuitState {
    Closed,
    Open,
    HalfOpen,
}

impl CircuitBreaker {
    pub fn new(failure_threshold: usize, timeout: Duration) -> Self {
        Self {
            failure_threshold,
            success_threshold: 2,
            timeout,
            failure_count: AtomicUsize::new(0),
            success_count: AtomicUsize::new(0),
            last_failure_time: Mutex::new(None),
            state: Mutex::new(CircuitState::Closed),
        }
    }

    pub fn call<F, T>(&self, f: F) -> Result<T>
    where
        F: FnOnce() -> Result<T>,
    {
        let mut state = self.state.lock().unwrap();

        match *state {
            CircuitState::Open => {
                let last_failure = self.last_failure_time.lock().unwrap();
                if let Some(time) = *last_failure {
                    if time.elapsed() > self.timeout {
                        *state = CircuitState::HalfOpen;
                        drop(state);
                        drop(last_failure);
                        return self.call_half_open(f);
                    }
                }
                Err(anyhow::anyhow!("Circuit breaker is open"))
            }
            CircuitState::HalfOpen => {
                drop(state);
                self.call_half_open(f)
            }
            CircuitState::Closed => {
                drop(state);
                self.call_closed(f)
            }
        }
    }

    fn call_closed<F, T>(&self, f: F) -> Result<T>
    where
        F: FnOnce() -> Result<T>,
    {
        match f() {
            Ok(result) => {
                self.failure_count.store(0, Ordering::Relaxed);
                Ok(result)
            }
            Err(e) => {
                let failures = self.failure_count.fetch_add(1, Ordering::Relaxed) + 1;

                if failures >= self.failure_threshold {
                    let mut state = self.state.lock().unwrap();
                    *state = CircuitState::Open;

                    let mut last_failure = self.last_failure_time.lock().unwrap();
                    *last_failure = Some(std::time::Instant::now());
                }

                Err(e)
            }
        }
    }

    fn call_half_open<F, T>(&self, f: F) -> Result<T>
    where
        F: FnOnce() -> Result<T>,
    {
        match f() {
            Ok(result) => {
                let successes = self.success_count.fetch_add(1, Ordering::Relaxed) + 1;

                if successes >= self.success_threshold {
                    let mut state = self.state.lock().unwrap();
                    *state = CircuitState::Closed;
                    self.success_count.store(0, Ordering::Relaxed);
                    self.failure_count.store(0, Ordering::Relaxed);
                }

                Ok(result)
            }
            Err(e) => {
                let mut state = self.state.lock().unwrap();
                *state = CircuitState::Open;

                let mut last_failure = self.last_failure_time.lock().unwrap();
                *last_failure = Some(std::time::Instant::now());

                self.success_count.store(0, Ordering::Relaxed);

                Err(e)
            }
        }
    }
}
```

### 5. Multi-Step Reasoning

**Complex Reasoning Chains**:

```rust
use pyo3::prelude::*;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ReasoningChain {
    steps: Vec<ReasoningStep>,
    final_conclusion: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ReasoningStep {
    step_number: usize,
    question: String,
    thought: String,
    action: Option<String>,
    observation: Option<String>,
    conclusion: Option<String>,
}

pub struct MultiStepReasoner {
    agent: Py<PyAny>,
    max_depth: usize,
}

impl MultiStepReasoner {
    pub fn new(py: Python, max_depth: usize) -> PyResult<Self> {
        let dspy = PyModule::import(py, "dspy")?;

        // Create advanced ReAct with decomposition
        let module = PyModule::from_code(
            py,
            r#"
import dspy

class MultiStepAgent(dspy.Module):
    def __init__(self):
        super().__init__()
        self.decompose = dspy.ChainOfThought("complex_question -> sub_questions")
        self.react = dspy.ReAct("question -> answer")
        self.synthesize = dspy.ChainOfThought("answers -> final_answer")

    def forward(self, question):
        # Decompose into sub-questions
        decomp = self.decompose(complex_question=question)
        sub_questions = decomp.sub_questions.split('\n')

        # Solve each sub-question
        sub_answers = []
        for sq in sub_questions:
            if sq.strip():
                answer = self.react(question=sq.strip())
                sub_answers.append(f"{sq}: {answer.answer}")

        # Synthesize final answer
        answers_text = '\n'.join(sub_answers)
        final = self.synthesize(answers=answers_text)

        return dspy.Prediction(
            answer=final.final_answer,
            sub_questions=sub_questions,
            sub_answers=sub_answers
        )
"#,
            "multi_step.py",
            "multi_step",
        )?;

        let agent_class = module.getattr("MultiStepAgent")?;
        let agent = agent_class.call0()?;

        Ok(Self {
            agent: agent.into(),
            max_depth,
        })
    }

    pub fn reason(&self, py: Python, question: &str) -> PyResult<ReasoningChain> {
        let result = self.agent.as_ref(py).call_method1(
            "forward",
            ((question,),)
        )?;

        let final_answer: String = result.getattr("answer")?.extract()?;

        // Extract reasoning chain
        let mut steps = Vec::new();

        if let Ok(sub_questions) = result.getattr("sub_questions") {
            let questions: Vec<String> = sub_questions.extract()?;

            if let Ok(sub_answers) = result.getattr("sub_answers") {
                let answers: Vec<String> = sub_answers.extract()?;

                for (idx, (q, a)) in questions.iter().zip(answers.iter()).enumerate() {
                    steps.push(ReasoningStep {
                        step_number: idx + 1,
                        question: q.clone(),
                        thought: "Analyzing sub-question".to_string(),
                        action: Some("solve".to_string()),
                        observation: Some(a.clone()),
                        conclusion: None,
                    });
                }
            }
        }

        Ok(ReasoningChain {
            steps,
            final_conclusion: Some(final_answer),
        })
    }
}
```

### 6. Production Agent System

**Complete Production Architecture**:

```rust
use tokio::sync::RwLock;
use std::sync::Arc;
use anyhow::Result;

pub struct ProductionAgentSystem {
    tool_registry: Arc<Mutex<ToolRegistry>>,
    agent_pool: Arc<RwLock<Vec<Py<PyAny>>>>,
    memory_store: Arc<RwLock<HashMap<String, AgentMemory>>>,
    circuit_breaker: Arc<CircuitBreaker>,
    metrics: Arc<Mutex<AgentMetrics>>,
}

#[derive(Debug, Default)]
struct AgentMetrics {
    total_requests: usize,
    successful_requests: usize,
    failed_requests: usize,
    total_reasoning_steps: usize,
    average_latency_ms: f64,
}

impl ProductionAgentSystem {
    pub async fn new(pool_size: usize) -> Result<Self> {
        let mut tool_registry = ToolRegistry::new();

        // Register production tools
        tool_registry.register("search", search_tool);
        tool_registry.register("calculator", calculator_tool);
        tool_registry.register("weather", weather_tool);

        let tool_registry = Arc::new(Mutex::new(tool_registry));

        // Initialize agent pool
        let mut agent_pool = Vec::new();

        Python::with_gil(|py| -> PyResult<()> {
            for _ in 0..pool_size {
                let agent = create_react_agent(py)?;
                agent_pool.push(agent);
            }
            Ok(())
        })?;

        Ok(Self {
            tool_registry,
            agent_pool: Arc::new(RwLock::new(agent_pool)),
            memory_store: Arc::new(RwLock::new(HashMap::new())),
            circuit_breaker: Arc::new(CircuitBreaker::new(5, Duration::from_secs(30))),
            metrics: Arc::new(Mutex::new(AgentMetrics::default())),
        })
    }

    pub async fn execute_task(
        &self,
        user_id: &str,
        question: &str,
    ) -> Result<String> {
        let start = std::time::Instant::now();

        // Get or create user memory
        let memory = {
            let mut store = self.memory_store.write().await;
            store.entry(user_id.to_string())
                .or_insert_with(AgentMemory::new)
                .clone()
        };

        // Execute with circuit breaker
        let result = self.circuit_breaker.call(|| {
            Python::with_gil(|py| -> Result<String> {
                // Get agent from pool
                let agent_pool = self.agent_pool.blocking_read();
                let agent = agent_pool.first()
                    .ok_or_else(|| anyhow::anyhow!("No agents available"))?;

                // Augment with context
                let context = memory.get_context(3);
                let augmented = if context.is_empty() {
                    question.to_string()
                } else {
                    format!("{}\n\nQuestion: {}", context, question)
                };

                // Execute
                let result = agent.as_ref(py).call_method1(
                    "forward",
                    ((augmented,),)
                )?;

                let answer: String = result.getattr("answer")?.extract()?;
                Ok(answer)
            })
        })?;

        // Update metrics
        {
            let mut metrics = self.metrics.lock().unwrap();
            metrics.total_requests += 1;
            metrics.successful_requests += 1;

            let elapsed = start.elapsed().as_millis() as f64;
            metrics.average_latency_ms =
                (metrics.average_latency_ms * (metrics.total_requests - 1) as f64 + elapsed)
                / metrics.total_requests as f64;
        }

        // Update memory
        {
            let mut store = self.memory_store.write().await;
            if let Some(mem) = store.get_mut(user_id) {
                mem.add_turn(question.to_string(), result.clone(), 0);
            }
        }

        Ok(result)
    }

    pub fn get_metrics(&self) -> AgentMetrics {
        self.metrics.lock().unwrap().clone()
    }

    pub async fn save_all_memories(&self, directory: &str) -> Result<()> {
        let store = self.memory_store.read().await;

        std::fs::create_dir_all(directory)?;

        for (user_id, memory) in store.iter() {
            let path = format!("{}/{}.json", directory, user_id);
            memory.save(&path)?;
        }

        Ok(())
    }
}

fn create_react_agent(py: Python) -> PyResult<Py<PyAny>> {
    let dspy = PyModule::import(py, "dspy")?;
    let react = dspy.getattr("ReAct")?;
    let signature = "question -> answer";
    let agent = react.call1(((signature,),))?;
    Ok(agent.into())
}

#[tokio::main]
async fn main() -> Result<()> {
    // Initialize production system
    let system = ProductionAgentSystem::new(4).await?;

    // Execute task
    let answer = system.execute_task(
        "user_123",
        "What's the weather in San Francisco?"
    ).await?;

    println!("Answer: {}", answer);

    // Get metrics
    let metrics = system.get_metrics();
    println!("Metrics: {:?}", metrics);

    // Save memories
    system.save_all_memories("./agent_memories").await?;

    Ok(())
}
```

### 7. Parallel Agent Execution

**Running Multiple Agents Concurrently**:

```rust
use tokio::task::JoinSet;

pub async fn execute_parallel_agents(
    system: &ProductionAgentSystem,
    user_id: &str,
    questions: Vec<String>,
) -> Result<Vec<Result<String>>> {
    let mut join_set = JoinSet::new();

    for question in questions {
        let system_clone = system.clone();
        let user_id = user_id.to_string();

        join_set.spawn(async move {
            system_clone.execute_task(&user_id, &question).await
        });
    }

    let mut results = Vec::new();
    while let Some(result) = join_set.join_next().await {
        results.push(result?);
    }

    Ok(results)
}
```

### 8. Agent Observability

**Comprehensive Logging and Tracing**:

```rust
use tracing::{info, warn, error, instrument};

#[instrument(skip(py, agent), fields(question_len = question.len()))]
pub fn traced_agent_call(
    py: Python,
    agent: &Py<PyAny>,
    question: &str,
) -> PyResult<String> {
    info!("Executing agent with question");

    let start = std::time::Instant::now();

    let result = agent.as_ref(py).call_method1(
        "forward",
        ((question,),)
    );

    let elapsed = start.elapsed();

    match result {
        Ok(prediction) => {
            let answer: String = prediction.getattr("answer")?.extract()?;
            info!(
                duration_ms = elapsed.as_millis(),
                answer_len = answer.len(),
                "Agent execution successful"
            );
            Ok(answer)
        }
        Err(e) => {
            error!(
                duration_ms = elapsed.as_millis(),
                error = %e,
                "Agent execution failed"
            );
            Err(e)
        }
    }
}
```

## Resources

### REFERENCE.md

Comprehensive 800+ line guide covering:
- ReAct pattern implementation details
- Tool registry architectures
- State persistence strategies
- Error recovery patterns (retry, circuit breaker, fallback)
- Multi-step reasoning algorithms
- Production deployment patterns
- Agent pool management
- Memory optimization
- Monitoring and observability
- Security considerations for tool execution
- Cost optimization strategies

**Load**: `cat skills/rust/pyo3-dspy-agents/resources/REFERENCE.md`

### Scripts

**1. tool_registry_manager.py** (~300 lines)
- Manage tool registries
- Validate tool definitions
- Generate Rust tool bindings
- Test tool execution
- Monitor tool performance

**Usage**:
```bash
# Create registry
python resources/scripts/tool_registry_manager.py create registry.json

# Add tool
python resources/scripts/tool_registry_manager.py add-tool registry.json search "Search tool"

# Validate
python resources/scripts/tool_registry_manager.py validate registry.json

# Generate Rust code
python resources/scripts/tool_registry_manager.py codegen registry.json > tools.rs
```

**2. agent_state_manager.py** (~300 lines)
- Manage agent state and memory
- Persist conversation history
- Export/import state
- Analyze agent performance
- Generate state reports

**Usage**:
```bash
# Export state
python resources/scripts/agent_state_manager.py export user_123 > state.json

# Import state
python resources/scripts/agent_state_manager.py import state.json

# Analyze
python resources/scripts/agent_state_manager.py analyze state.json
```

**3. agent_runner.py** (~300 lines)
- Run and test agents
- Benchmark agent performance
- Compare different agent configurations
- Generate test reports

**Usage**:
```bash
# Run agent
python resources/scripts/agent_runner.py run --question "What is AI?"

# Benchmark
python resources/scripts/agent_runner.py benchmark questions.txt

# Compare
python resources/scripts/agent_runner.py compare config1.json config2.json
```

### Examples

**1. basic-react/** - Basic ReAct agent
- Simple ReAct integration
- Tool registration
- Result extraction

**2. tool-using-agent/** - Agent with custom tools
- Multiple tool registration
- Tool execution from Rust
- Error handling

**3. stateful-agent/** - Agent with memory
- Conversation history
- Fact storage
- Context augmentation

**4. multi-step-reasoning/** - Complex reasoning chains
- Problem decomposition
- Sub-question solving
- Answer synthesis

**5. production-agent-service/** - Full production system
- Agent pool management
- Circuit breakers
- Metrics and monitoring
- Memory persistence

**6. parallel-agents/** - Concurrent agent execution
- Tokio integration
- Parallel task execution
- Result aggregation

**7. agent-observability/** - Tracing and logging
- Structured logging
- Performance tracing
- Error tracking
- Dashboard integration

## Best Practices

### DO

✅ **Implement circuit breakers** for tool execution
✅ **Use retry strategies** with exponential backoff
✅ **Persist agent state** regularly
✅ **Monitor agent performance** with metrics
✅ **Limit reasoning depth** to prevent infinite loops
✅ **Validate tool outputs** before returning to agent
✅ **Use agent pools** for high-throughput scenarios
✅ **Log all reasoning steps** for debugging
✅ **Test tools independently** before agent integration
✅ **Set timeouts** for all external tool calls

### DON'T

❌ **Execute untrusted code** in tools without sandboxing
❌ **Store sensitive data** in agent memory unencrypted
❌ **Allow unlimited reasoning steps** (set max iterations)
❌ **Ignore tool execution errors** (implement fallbacks)
❌ **Mix synchronous and async** contexts incorrectly
❌ **Hold GIL** during expensive tool operations
❌ **Skip input validation** for tools
❌ **Forget to clean up** agent resources
❌ **Use global state** for agent memory
❌ **Expose internal errors** to end users

## Common Pitfalls

### 1. Infinite Reasoning Loops

**Problem**: Agent gets stuck in reasoning loop without termination

**Solution**: Set max iterations and implement loop detection
```rust
let agent = react.call1(((signature,),))?;
agent.setattr("max_iters", 10)?;
```

### 2. Tool Execution Failures

**Problem**: Tools fail intermittently, breaking agent execution

**Solution**: Implement retry with exponential backoff and fallback
```rust
let result = execute_tool_with_retry(
    &registry,
    "search",
    query,
    &RetryConfig::default()
).await?;
```

### 3. Memory Leaks

**Problem**: Agent memory grows unbounded over time

**Solution**: Implement memory pruning and limits
```rust
if memory.conversation_history.len() > 100 {
    memory.conversation_history = memory.conversation_history
        .split_off(memory.conversation_history.len() - 50);
}
```

### 4. GIL Contention

**Problem**: Multiple agents contending for GIL causing poor performance

**Solution**: Use agent pools and minimize GIL hold time
```rust
// Good: Release GIL between agent calls
let result = Python::with_gil(|py| agent.call(py))?;
process_result(&result);  // GIL released
```

## Troubleshooting

### Issue: Agent Returns Empty Answer

**Symptom**: Agent executes but returns empty or malformed answer

**Solution**:
- Check DSPy signature matches expected output
- Verify LM is properly configured
- Increase max tokens in LM config
- Check for Python exceptions in agent execution

### Issue: Tool Not Found

**Symptom**: `Tool not found: tool_name`

**Solution**:
```rust
// Verify tool is registered
let tools = registry.list_tools();
assert!(tools.contains(&"tool_name".to_string()));

// Check tool names match exactly (case-sensitive)
```

### Issue: Circuit Breaker Always Open

**Symptom**: Circuit breaker prevents all requests

**Solution**:
- Check failure threshold is not too low
- Verify timeout is sufficient for recovery
- Monitor underlying tool health
- Implement proper error classification

### Issue: Memory Not Persisting

**Symptom**: Agent memory lost between runs

**Solution**:
```rust
// Save memory after each interaction
system.save_all_memories("./memories").await?;

// Load memory on system startup
memory_store.load_all_memories("./memories").await?;
```

## Next Steps

**After mastering agents**:
1. **pyo3-dspy-async-streaming**: Async agent execution and streaming
2. **pyo3-dspy-production**: Advanced production patterns
3. **pyo3-dspy-rag-pipelines**: Combine agents with RAG
4. **pyo3-dspy-optimization**: Optimize agent performance

## References

- [DSPy ReAct Documentation](https://dspy-docs.vercel.app/docs/building-blocks/modules#react)
- [ReAct Paper](https://arxiv.org/abs/2210.03629)
- [Tokio Async Runtime](https://tokio.rs)
- [Circuit Breaker Pattern](https://martinfowler.com/bliki/CircuitBreaker.html)
- [Agent Architectures](https://www.anthropic.com/research/building-effective-agents)

---

**Version**: 1.0.0
**Last Updated**: 2025-10-30
**Maintainer**: DSPy-PyO3 Integration Team
