//! Stateful Agent Library
//!
//! This library provides persistent memory management for conversational AI agents.
//! It implements the AgentMemory pattern for maintaining conversation history,
//! storing facts, and building context for multi-turn interactions.

use anyhow::{Context, Result};
use chrono::{DateTime, Duration, Utc};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::fs;
use std::path::Path;

/// Represents a single turn in a conversation with the agent
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ConversationTurn {
    /// The question asked by the user
    pub question: String,
    /// The answer provided by the agent
    pub answer: String,
    /// Number of reasoning steps taken (for ReAct agents)
    pub reasoning_steps: usize,
    /// When this turn occurred
    pub timestamp: DateTime<Utc>,
    /// Optional metadata for the turn
    #[serde(default)]
    pub metadata: HashMap<String, String>,
}

impl ConversationTurn {
    /// Create a new conversation turn
    pub fn new(question: String, answer: String, reasoning_steps: usize) -> Self {
        Self {
            question,
            answer,
            reasoning_steps,
            timestamp: Utc::now(),
            metadata: HashMap::new(),
        }
    }

    /// Add metadata to this turn
    pub fn with_metadata(mut self, key: String, value: String) -> Self {
        self.metadata.insert(key, value);
        self
    }

    /// Calculate a simple relevance score to a query (0.0 to 1.0)
    pub fn relevance_to(&self, query: &str) -> f32 {
        let query_lower = query.to_lowercase();
        let question_lower = self.question.to_lowercase();
        let answer_lower = self.answer.to_lowercase();

        // Simple keyword matching
        let query_words: Vec<&str> = query_lower.split_whitespace().collect();
        let mut matches = 0;
        let total = query_words.len();

        for word in &query_words {
            if question_lower.contains(word) || answer_lower.contains(word) {
                matches += 1;
            }
        }

        if total == 0 {
            0.0
        } else {
            matches as f32 / total as f32
        }
    }

    /// Estimate the size of this turn in bytes
    pub fn estimate_size(&self) -> usize {
        self.question.len()
            + self.answer.len()
            + self.metadata.iter().map(|(k, v)| k.len() + v.len()).sum::<usize>()
            + 64 // Approximate overhead
    }
}

/// Persistent memory for conversational agents
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AgentMemory {
    /// History of all conversation turns
    conversation_history: Vec<ConversationTurn>,
    /// Key-value store of learned facts
    facts: HashMap<String, String>,
    /// When this memory was created
    created_at: DateTime<Utc>,
    /// When this memory was last modified
    last_updated: DateTime<Utc>,
    /// Optional metadata for the entire memory
    #[serde(default)]
    metadata: HashMap<String, String>,
}

impl AgentMemory {
    /// Create a new empty agent memory
    pub fn new() -> Self {
        let now = Utc::now();
        Self {
            conversation_history: Vec::new(),
            facts: HashMap::new(),
            created_at: now,
            last_updated: now,
            metadata: HashMap::new(),
        }
    }

    /// Add a conversation turn to the history
    pub fn add_turn(&mut self, question: String, answer: String, steps: usize) {
        let turn = ConversationTurn::new(question, answer, steps);
        self.conversation_history.push(turn);
        self.last_updated = Utc::now();
    }

    /// Add a conversation turn with metadata
    pub fn add_turn_with_metadata(
        &mut self,
        question: String,
        answer: String,
        steps: usize,
        metadata: HashMap<String, String>,
    ) {
        let mut turn = ConversationTurn::new(question, answer, steps);
        turn.metadata = metadata;
        self.conversation_history.push(turn);
        self.last_updated = Utc::now();
    }

    /// Add a fact to the knowledge base
    pub fn add_fact(&mut self, key: String, value: String) {
        self.facts.insert(key, value);
        self.last_updated = Utc::now();
    }

    /// Get a fact by key
    pub fn get_fact(&self, key: &str) -> Option<&String> {
        self.facts.get(key)
    }

    /// Remove a fact by key
    pub fn remove_fact(&mut self, key: &str) -> Option<String> {
        self.last_updated = Utc::now();
        self.facts.remove(key)
    }

    /// Get all facts
    pub fn facts(&self) -> &HashMap<String, String> {
        &self.facts
    }

    /// Get the conversation history
    pub fn history(&self) -> &[ConversationTurn] {
        &self.conversation_history
    }

    /// Get the number of conversation turns
    pub fn turn_count(&self) -> usize {
        self.conversation_history.len()
    }

    /// Get context string from the last N turns
    pub fn get_context(&self, max_turns: usize) -> String {
        let recent_history: Vec<_> = self
            .conversation_history
            .iter()
            .rev()
            .take(max_turns)
            .rev()
            .collect();

        let mut context = String::new();

        // Add facts section
        if !self.facts.is_empty() {
            context.push_str("Known facts:\n");
            for (key, value) in &self.facts {
                context.push_str(&format!("- {}: {}\n", key, value));
            }
            context.push('\n');
        }

        // Add conversation history
        if !recent_history.is_empty() {
            context.push_str("Recent conversation:\n");
            for (idx, turn) in recent_history.iter().enumerate() {
                context.push_str(&format!("Turn {}:\n", idx + 1));
                context.push_str(&format!("Q: {}\n", turn.question));
                context.push_str(&format!("A: {}\n\n", turn.answer));
            }
        }

        context
    }

    /// Get context with relevance filtering
    pub fn get_context_with_relevance(
        &self,
        query: &str,
        max_turns: usize,
        min_relevance: f32,
    ) -> String {
        // Score and sort turns by relevance
        let mut scored_turns: Vec<_> = self
            .conversation_history
            .iter()
            .map(|turn| (turn, turn.relevance_to(query)))
            .filter(|(_, score)| *score >= min_relevance)
            .collect();

        scored_turns.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap());

        let relevant_turns: Vec<_> = scored_turns
            .iter()
            .take(max_turns)
            .map(|(turn, _)| *turn)
            .collect();

        let mut context = String::new();

        // Add facts
        if !self.facts.is_empty() {
            context.push_str("Known facts:\n");
            for (key, value) in &self.facts {
                context.push_str(&format!("- {}: {}\n", key, value));
            }
            context.push('\n');
        }

        // Add relevant turns
        if !relevant_turns.is_empty() {
            context.push_str("Relevant previous conversation:\n");
            for turn in relevant_turns {
                context.push_str(&format!("Q: {}\n", turn.question));
                context.push_str(&format!("A: {}\n\n", turn.answer));
            }
        }

        context
    }

    /// Get turns from the last N seconds/minutes/hours
    pub fn get_recent_turns(&self, duration: Duration) -> Vec<&ConversationTurn> {
        let cutoff = Utc::now() - duration;
        self.conversation_history
            .iter()
            .filter(|turn| turn.timestamp > cutoff)
            .collect()
    }

    /// Search history by keyword
    pub fn search_history(&self, keyword: &str) -> Vec<&ConversationTurn> {
        let keyword_lower = keyword.to_lowercase();
        self.conversation_history
            .iter()
            .filter(|turn| {
                turn.question.to_lowercase().contains(&keyword_lower)
                    || turn.answer.to_lowercase().contains(&keyword_lower)
            })
            .collect()
    }

    /// Prune history to keep only last N turns
    pub fn prune_history(&mut self, keep_last: usize) {
        if self.conversation_history.len() > keep_last {
            let skip = self.conversation_history.len() - keep_last;
            self.conversation_history = self.conversation_history.iter().skip(skip).cloned().collect();
            self.last_updated = Utc::now();
        }
    }

    /// Remove turns older than duration
    pub fn prune_by_age(&mut self, max_age: Duration) {
        let cutoff = Utc::now() - max_age;
        self.conversation_history
            .retain(|turn| turn.timestamp > cutoff);
        self.last_updated = Utc::now();
    }

    /// Remove turns with relevance below threshold
    pub fn prune_irrelevant(&mut self, query: &str, min_relevance: f32) {
        self.conversation_history
            .retain(|turn| turn.relevance_to(query) >= min_relevance);
        self.last_updated = Utc::now();
    }

    /// Estimate total memory size in bytes
    pub fn estimate_size(&self) -> usize {
        let history_size: usize = self
            .conversation_history
            .iter()
            .map(|turn| turn.estimate_size())
            .sum();

        let facts_size: usize = self
            .facts
            .iter()
            .map(|(k, v)| k.len() + v.len())
            .sum();

        history_size + facts_size + 128 // Overhead
    }

    /// Compact memory by summarizing old history
    pub fn compact(&mut self, keep_recent: usize) {
        if self.conversation_history.len() <= keep_recent {
            return;
        }

        // Keep recent turns, summarize the rest
        let split_point = self.conversation_history.len() - keep_recent;
        let old_turns = &self.conversation_history[..split_point];

        // Create summary turn
        let summary = format!(
            "Summary of {} previous conversation turns covering topics: {}",
            old_turns.len(),
            self.extract_topics(old_turns).join(", ")
        );

        let summary_turn = ConversationTurn::new(
            "Previous conversation summary".to_string(),
            summary,
            0,
        );

        // Replace old turns with summary
        let mut new_history = vec![summary_turn];
        new_history.extend(self.conversation_history.iter().skip(split_point).cloned());
        self.conversation_history = new_history;
        self.last_updated = Utc::now();
    }

    /// Extract main topics from turns (simple keyword extraction)
    fn extract_topics(&self, turns: &[ConversationTurn]) -> Vec<String> {
        // Simple implementation - extract first few words from questions
        turns
            .iter()
            .filter_map(|turn| {
                turn.question
                    .split_whitespace()
                    .take(3)
                    .collect::<Vec<_>>()
                    .join(" ")
                    .split('?')
                    .next()
                    .map(|s| s.to_string())
            })
            .take(5)
            .collect()
    }

    /// Save memory to JSON file
    pub fn save<P: AsRef<Path>>(&self, path: P) -> Result<()> {
        let json = serde_json::to_string_pretty(self)
            .context("Failed to serialize memory to JSON")?;
        fs::write(path.as_ref(), json)
            .context(format!("Failed to write memory to {:?}", path.as_ref()))?;
        Ok(())
    }

    /// Load memory from JSON file
    pub fn load<P: AsRef<Path>>(path: P) -> Result<Self> {
        let json = fs::read_to_string(path.as_ref())
            .context(format!("Failed to read memory from {:?}", path.as_ref()))?;
        let memory: Self = serde_json::from_str(&json)
            .context("Failed to deserialize memory from JSON")?;
        Ok(memory)
    }

    /// Save memory to compressed JSON file (gzip)
    #[cfg(feature = "compression")]
    pub fn save_compressed<P: AsRef<Path>>(&self, path: P) -> Result<()> {
        use flate2::write::GzEncoder;
        use flate2::Compression;
        use std::io::Write;

        let json = serde_json::to_string_pretty(self)?;
        let file = fs::File::create(path.as_ref())?;
        let mut encoder = GzEncoder::new(file, Compression::default());
        encoder.write_all(json.as_bytes())?;
        encoder.finish()?;
        Ok(())
    }

    /// Load memory from compressed JSON file
    #[cfg(feature = "compression")]
    pub fn load_compressed<P: AsRef<Path>>(path: P) -> Result<Self> {
        use flate2::read::GzDecoder;
        use std::io::Read;

        let file = fs::File::open(path.as_ref())?;
        let mut decoder = GzDecoder::new(file);
        let mut json = String::new();
        decoder.read_to_string(&mut json)?;
        let memory: Self = serde_json::from_str(&json)?;
        Ok(memory)
    }

    /// Merge multiple memories into one
    pub fn merge(memories: Vec<Self>) -> Self {
        if memories.is_empty() {
            return Self::new();
        }

        let mut merged = memories[0].clone();

        for memory in memories.iter().skip(1) {
            // Merge conversation histories
            merged.conversation_history.extend(memory.conversation_history.clone());

            // Merge facts (later memories override)
            for (k, v) in &memory.facts {
                merged.facts.insert(k.clone(), v.clone());
            }

            // Update timestamps
            if memory.created_at < merged.created_at {
                merged.created_at = memory.created_at;
            }
            if memory.last_updated > merged.last_updated {
                merged.last_updated = memory.last_updated;
            }
        }

        // Sort conversation history by timestamp
        merged.conversation_history.sort_by_key(|turn| turn.timestamp);

        merged
    }

    /// Share specific facts with another memory
    pub fn share_facts_with(&self, other: &mut Self, fact_keys: Vec<&str>) {
        for key in fact_keys {
            if let Some(value) = self.facts.get(key) {
                other.add_fact(key.to_string(), value.clone());
            }
        }
    }

    /// Get statistics about the memory
    pub fn stats(&self) -> MemoryStats {
        MemoryStats {
            turn_count: self.conversation_history.len(),
            fact_count: self.facts.len(),
            estimated_size_bytes: self.estimate_size(),
            created_at: self.created_at,
            last_updated: self.last_updated,
            oldest_turn: self.conversation_history.first().map(|t| t.timestamp),
            newest_turn: self.conversation_history.last().map(|t| t.timestamp),
        }
    }
}

impl Default for AgentMemory {
    fn default() -> Self {
        Self::new()
    }
}

/// Statistics about agent memory
#[derive(Debug, Clone)]
pub struct MemoryStats {
    pub turn_count: usize,
    pub fact_count: usize,
    pub estimated_size_bytes: usize,
    pub created_at: DateTime<Utc>,
    pub last_updated: DateTime<Utc>,
    pub oldest_turn: Option<DateTime<Utc>>,
    pub newest_turn: Option<DateTime<Utc>>,
}

impl MemoryStats {
    /// Format statistics as human-readable string
    pub fn to_string(&self) -> String {
        format!(
            "Memory Statistics:\n\
             - Conversation turns: {}\n\
             - Facts stored: {}\n\
             - Estimated size: {} bytes ({:.2} KB)\n\
             - Created: {}\n\
             - Last updated: {}\n\
             - Oldest turn: {}\n\
             - Newest turn: {}",
            self.turn_count,
            self.fact_count,
            self.estimated_size_bytes,
            self.estimated_size_bytes as f64 / 1024.0,
            self.created_at.format("%Y-%m-%d %H:%M:%S UTC"),
            self.last_updated.format("%Y-%m-%d %H:%M:%S UTC"),
            self.oldest_turn
                .map(|t| t.format("%Y-%m-%d %H:%M:%S UTC").to_string())
                .unwrap_or_else(|| "N/A".to_string()),
            self.newest_turn
                .map(|t| t.format("%Y-%m-%d %H:%M:%S UTC").to_string())
                .unwrap_or_else(|| "N/A".to_string())
        )
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_memory_creation() {
        let memory = AgentMemory::new();
        assert_eq!(memory.turn_count(), 0);
        assert_eq!(memory.facts().len(), 0);
    }

    #[test]
    fn test_add_turn() {
        let mut memory = AgentMemory::new();
        memory.add_turn(
            "What is Rust?".to_string(),
            "A systems programming language".to_string(),
            3,
        );
        assert_eq!(memory.turn_count(), 1);
    }

    #[test]
    fn test_add_fact() {
        let mut memory = AgentMemory::new();
        memory.add_fact("language".to_string(), "Rust".to_string());
        assert_eq!(memory.get_fact("language"), Some(&"Rust".to_string()));
    }

    #[test]
    fn test_context_generation() {
        let mut memory = AgentMemory::new();
        memory.add_fact("name".to_string(), "Alice".to_string());
        memory.add_turn(
            "Hello".to_string(),
            "Hi there!".to_string(),
            1,
        );

        let context = memory.get_context(5);
        assert!(context.contains("Alice"));
        assert!(context.contains("Hello"));
    }

    #[test]
    fn test_relevance_scoring() {
        let turn = ConversationTurn::new(
            "What is machine learning?".to_string(),
            "ML is a type of AI".to_string(),
            2,
        );

        assert!(turn.relevance_to("machine learning") > 0.5);
        assert!(turn.relevance_to("cooking") < 0.1);
    }

    #[test]
    fn test_prune_history() {
        let mut memory = AgentMemory::new();
        for i in 0..10 {
            memory.add_turn(
                format!("Question {}", i),
                format!("Answer {}", i),
                1,
            );
        }

        memory.prune_history(5);
        assert_eq!(memory.turn_count(), 5);
    }

    #[test]
    fn test_serialization() {
        let mut memory = AgentMemory::new();
        memory.add_fact("test".to_string(), "value".to_string());
        memory.add_turn("Q".to_string(), "A".to_string(), 1);

        let json = serde_json::to_string(&memory).unwrap();
        let restored: AgentMemory = serde_json::from_str(&json).unwrap();

        assert_eq!(restored.turn_count(), 1);
        assert_eq!(restored.facts().len(), 1);
    }

    #[test]
    fn test_memory_merge() {
        let mut mem1 = AgentMemory::new();
        mem1.add_fact("fact1".to_string(), "value1".to_string());
        mem1.add_turn("Q1".to_string(), "A1".to_string(), 1);

        let mut mem2 = AgentMemory::new();
        mem2.add_fact("fact2".to_string(), "value2".to_string());
        mem2.add_turn("Q2".to_string(), "A2".to_string(), 1);

        let merged = AgentMemory::merge(vec![mem1, mem2]);
        assert_eq!(merged.turn_count(), 2);
        assert_eq!(merged.facts().len(), 2);
    }
}
