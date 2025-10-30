// Re-export main module types for library usage
pub use crate::context_manager::*;

pub mod context_manager {
    use anyhow::{Context as AnyhowContext, Result};
    use serde::{Deserialize, Serialize};
    use std::fmt;
    use tiktoken_rs::{cl100k_base, CoreBPE};

    /// Truncation strategy for context overflow handling
    #[derive(Debug, Clone, Copy, Serialize, Deserialize)]
    pub enum TruncationStrategy {
        /// Keep earliest content, discard from end
        Head,
        /// Keep latest content, discard from beginning
        Tail,
        /// Keep beginning and end, remove middle
        Middle,
        /// Keep most recent within sliding window
        SlidingWindow,
    }

    impl fmt::Display for TruncationStrategy {
        fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
            match self {
                Self::Head => write!(f, "Head"),
                Self::Tail => write!(f, "Tail"),
                Self::Middle => write!(f, "Middle"),
                Self::SlidingWindow => write!(f, "SlidingWindow"),
            }
        }
    }

    /// Document with relevance score for prioritization
    #[derive(Debug, Clone, Serialize, Deserialize)]
    pub struct Document {
        pub id: String,
        pub content: String,
        pub relevance: f64,
        pub token_count: Option<usize>,
    }

    impl Document {
        pub fn new(id: impl Into<String>, content: impl Into<String>, relevance: f64) -> Self {
            Self {
                id: id.into(),
                content: content.into(),
                relevance,
                token_count: None,
            }
        }

        /// Calculate priority score for ordering
        pub fn priority(&self) -> f64 {
            // Priority = relevance (60%) + inverse length penalty (20%) + completeness bonus (20%)
            let length_score = 1.0 / (1.0 + (self.content.len() as f64).sqrt() / 1000.0);
            let completeness = if self.content.ends_with('.') || self.content.ends_with('!') {
                1.0
            } else {
                0.5
            };

            (self.relevance * 0.6) + (length_score * 0.2) + (completeness * 0.2)
        }
    }

    /// Token budget allocation for different context components
    #[derive(Debug, Clone, Copy)]
    pub struct TokenBudget {
        pub system_prompt: usize,
        pub query: usize,
        pub response: usize,
        pub documents: usize,
    }

    impl TokenBudget {
        pub fn total(&self) -> usize {
            self.system_prompt + self.query + self.response + self.documents
        }
    }

    /// Assembled context ready for LLM consumption
    #[derive(Debug, Clone, Serialize, Deserialize)]
    pub struct AssembledContext {
        pub system_prompt: String,
        pub query: String,
        pub documents: Vec<Document>,
        pub total_tokens: usize,
        pub documents_omitted: usize,
        pub truncation_applied: bool,
    }

    impl AssembledContext {
        pub fn new(
            system_prompt: String,
            query: String,
            documents: Vec<Document>,
            total_tokens: usize,
        ) -> Self {
            Self {
                system_prompt,
                query,
                documents,
                total_tokens,
                documents_omitted: 0,
                truncation_applied: false,
            }
        }
    }

    /// Context window manager with token counting and smart truncation
    pub struct ContextManager {
        context_limit: usize,
        model_name: String,
        tokenizer: CoreBPE,
        budget: TokenBudget,
    }

    impl ContextManager {
        /// Create a new context manager for a specific model
        pub fn new(context_limit: usize, model_name: impl Into<String>) -> Result<Self> {
            let tokenizer = cl100k_base()
                .context("Failed to initialize tiktoken tokenizer")?;

            // Default budget allocation for 8k context
            let budget = Self::default_budget(context_limit);

            Ok(Self {
                context_limit,
                model_name: model_name.into(),
                tokenizer,
                budget,
            })
        }

        /// Default budget allocation (6% system, 2.5% query, 12.5% response, 79% documents)
        fn default_budget(limit: usize) -> TokenBudget {
            TokenBudget {
                system_prompt: (limit as f64 * 0.06) as usize,
                query: (limit as f64 * 0.025) as usize,
                response: (limit as f64 * 0.125) as usize,
                documents: (limit as f64 * 0.79) as usize,
            }
        }

        /// Set custom budget allocation
        pub fn set_budget_allocation(
            &mut self,
            system: usize,
            query: usize,
            response: usize,
        ) -> Result<()> {
            let documents = self.context_limit
                .checked_sub(system + query + response)
                .context("Budget exceeds context limit")?;

            self.budget = TokenBudget {
                system_prompt: system,
                query,
                response,
                documents,
            };

            Ok(())
        }

        /// Count tokens in text using tiktoken
        pub fn count_tokens(&self, text: &str) -> Result<usize> {
            let tokens = self.tokenizer.encode_with_special_tokens(text);
            Ok(tokens.len())
        }

        /// Count tokens for multiple documents
        pub fn count_document_tokens(&self, docs: &mut [Document]) -> Result<()> {
            for doc in docs.iter_mut() {
                doc.token_count = Some(self.count_tokens(&doc.content)?);
            }
            Ok(())
        }

        /// Build context with smart truncation and prioritization
        pub fn build_context(
            &self,
            system_prompt: &str,
            query: &str,
            documents: &[Document],
            strategy: TruncationStrategy,
        ) -> Result<AssembledContext> {
            // Count tokens for each component
            let system_tokens = self.count_tokens(system_prompt)?;
            let query_tokens = self.count_tokens(query)?;

            // Clone and count document tokens
            let mut docs = documents.to_vec();
            self.count_document_tokens(&mut docs)?;

            // Sort by priority (descending)
            docs.sort_by(|a, b| b.priority().partial_cmp(&a.priority()).unwrap());

            // Calculate available budget for documents
            let available_for_docs = self.budget.documents;

            // Select and truncate documents
            let (selected_docs, truncated) = self.select_documents(
                &docs,
                available_for_docs,
                strategy,
            )?;

            let total_tokens = system_tokens + query_tokens +
                selected_docs.iter()
                    .map(|d| d.token_count.unwrap_or(0))
                    .sum::<usize>();

            let mut context = AssembledContext::new(
                system_prompt.to_string(),
                query.to_string(),
                selected_docs,
                total_tokens,
            );

            context.documents_omitted = docs.len().saturating_sub(context.documents.len());
            context.truncation_applied = truncated;

            Ok(context)
        }

        /// Select documents that fit within token budget
        fn select_documents(
            &self,
            docs: &[Document],
            budget: usize,
            strategy: TruncationStrategy,
        ) -> Result<(Vec<Document>, bool)> {
            let mut selected = Vec::new();
            let mut used_tokens = 0;
            let mut truncated = false;

            match strategy {
                TruncationStrategy::Head => {
                    // Add documents from start until budget exhausted
                    for doc in docs.iter() {
                        let doc_tokens = doc.token_count.unwrap_or(0);
                        if used_tokens + doc_tokens <= budget {
                            selected.push(doc.clone());
                            used_tokens += doc_tokens;
                        } else {
                            truncated = true;
                            break;
                        }
                    }
                }

                TruncationStrategy::Tail => {
                    // Add documents from end until budget exhausted
                    for doc in docs.iter().rev() {
                        let doc_tokens = doc.token_count.unwrap_or(0);
                        if used_tokens + doc_tokens <= budget {
                            selected.insert(0, doc.clone());
                            used_tokens += doc_tokens;
                        } else {
                            truncated = true;
                            break;
                        }
                    }
                }

                TruncationStrategy::Middle => {
                    // Keep beginning and end, remove middle if needed
                    if docs.is_empty() {
                        return Ok((selected, false));
                    }

                    // Calculate total tokens
                    let total_tokens: usize = docs.iter()
                        .map(|d| d.token_count.unwrap_or(0))
                        .sum();

                    if total_tokens <= budget {
                        // All fit
                        selected = docs.to_vec();
                    } else {
                        // Need to remove middle
                        truncated = true;
                        let half_budget = budget / 2;

                        // Add from start
                        let mut head_tokens = 0;
                        let mut head_count = 0;
                        for doc in docs.iter() {
                            let doc_tokens = doc.token_count.unwrap_or(0);
                            if head_tokens + doc_tokens <= half_budget {
                                selected.push(doc.clone());
                                head_tokens += doc_tokens;
                                head_count += 1;
                            } else {
                                break;
                            }
                        }

                        // Add from end
                        let mut tail_tokens = 0;
                        let mut tail_docs = Vec::new();
                        for doc in docs.iter().rev() {
                            let doc_tokens = doc.token_count.unwrap_or(0);
                            if tail_tokens + doc_tokens <= half_budget &&
                               tail_docs.len() + head_count < docs.len() {
                                tail_docs.insert(0, doc.clone());
                                tail_tokens += doc_tokens;
                            } else {
                                break;
                            }
                        }

                        // Add ellipsis marker if there's a gap
                        if head_count + tail_docs.len() < docs.len() {
                            let marker = Document::new(
                                "...",
                                format!("... {} documents omitted ...",
                                       docs.len() - head_count - tail_docs.len()),
                                0.0,
                            );
                            selected.push(marker);
                        }

                        selected.extend(tail_docs);
                    }
                }

                TruncationStrategy::SlidingWindow => {
                    // Keep most recent documents within budget
                    let mut window = Vec::new();
                    let mut window_tokens = 0;

                    for doc in docs.iter().rev() {
                        let doc_tokens = doc.token_count.unwrap_or(0);
                        if window_tokens + doc_tokens <= budget {
                            window.insert(0, doc.clone());
                            window_tokens += doc_tokens;
                        } else {
                            truncated = true;
                            break;
                        }
                    }

                    selected = window;
                }
            }

            Ok((selected, truncated))
        }

        /// Print context statistics
        pub fn print_stats(&self, context: &AssembledContext) {
            println!("\nContext Statistics");
            println!("==================");
            println!("Model: {}", self.model_name);
            println!("Context Limit: {} tokens", self.context_limit);
            println!("\nToken Budget:");
            println!("  System: {} tokens", self.budget.system_prompt);
            println!("  Query: {} tokens", self.budget.query);
            println!("  Response: {} tokens", self.budget.response);
            println!("  Documents: {} tokens", self.budget.documents);
            println!("\nActual Usage:");
            println!("  Total: {} tokens ({:.1}%)",
                     context.total_tokens,
                     (context.total_tokens as f64 / self.context_limit as f64) * 100.0);
            println!("  Documents included: {}", context.documents.len());
            println!("  Documents omitted: {}", context.documents_omitted);
            println!("  Truncation applied: {}", context.truncation_applied);
        }
    }

    #[cfg(test)]
    mod tests {
        use super::*;

        #[test]
        fn test_token_counting() -> Result<()> {
            let manager = ContextManager::new(8192, "gpt-3.5-turbo")?;

            let text = "Hello, world!";
            let count = manager.count_tokens(text)?;

            assert!(count > 0);
            assert!(count < 10); // Should be ~3-4 tokens

            Ok(())
        }

        #[test]
        fn test_document_priority() {
            let doc1 = Document::new("1", "Short content.", 0.9);
            let doc2 = Document::new("2", "Much longer content that goes on and on...", 0.8);

            // Higher relevance should win despite length penalty
            assert!(doc1.priority() > doc2.priority());
        }

        #[test]
        fn test_budget_allocation() -> Result<()> {
            let mut manager = ContextManager::new(8192, "gpt-3.5-turbo")?;

            manager.set_budget_allocation(400, 200, 800)?;

            assert_eq!(manager.budget.system_prompt, 400);
            assert_eq!(manager.budget.query, 200);
            assert_eq!(manager.budget.response, 800);
            assert_eq!(manager.budget.documents, 6792);

            Ok(())
        }

        #[test]
        fn test_context_building() -> Result<()> {
            let manager = ContextManager::new(8192, "gpt-3.5-turbo")?;

            let docs = vec![
                Document::new("1", "Test document one", 0.9),
                Document::new("2", "Test document two", 0.8),
            ];

            let context = manager.build_context(
                "System prompt",
                "User query",
                &docs,
                TruncationStrategy::Head,
            )?;

            assert_eq!(context.system_prompt, "System prompt");
            assert_eq!(context.query, "User query");
            assert!(context.total_tokens > 0);
            assert!(context.total_tokens < 8192);

            Ok(())
        }

        #[test]
        fn test_truncation_strategies() -> Result<()> {
            let manager = ContextManager::new(4096, "gpt-3.5-turbo")?;

            let docs = vec![
                Document::new("1", "A".repeat(1000), 0.9),
                Document::new("2", "B".repeat(1000), 0.8),
                Document::new("3", "C".repeat(1000), 0.7),
                Document::new("4", "D".repeat(1000), 0.6),
            ];

            // Head strategy
            let head_ctx = manager.build_context(
                "System",
                "Query",
                &docs,
                TruncationStrategy::Head,
            )?;
            assert!(head_ctx.documents[0].id == "1");

            // Tail strategy
            let tail_ctx = manager.build_context(
                "System",
                "Query",
                &docs,
                TruncationStrategy::Tail,
            )?;
            assert!(tail_ctx.documents.last().unwrap().id == "4");

            Ok(())
        }
    }
}
