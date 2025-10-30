use anyhow::Result;
use context_manager::{ContextManager, Document, TruncationStrategy};

fn main() -> Result<()> {
    println!("Context Window Management Example");
    println!("==================================\n");

    // Initialize context manager for GPT-3.5-turbo (8k context)
    let manager = ContextManager::new(8192, "gpt-3.5-turbo")?;

    // Create sample documents with relevance scores
    let documents = vec![
        Document::new(
            "rust-memory-safety",
            "Rust provides memory safety without garbage collection through its ownership system. \
             The ownership model ensures that each value has a single owner, and when the owner \
             goes out of scope, the value is dropped. This prevents common bugs like null pointer \
             dereferences, buffer overflows, and data races at compile time.",
            0.95,
        ),
        Document::new(
            "rust-ownership",
            "The Rust ownership model consists of three main rules: each value has a single owner, \
             there can only be one owner at a time, and when the owner goes out of scope, the value \
             is dropped. This is enforced at compile time through the borrow checker.",
            0.92,
        ),
        Document::new(
            "rust-performance",
            "Rust achieves performance comparable to C and C++ through zero-cost abstractions. \
             The compiler optimizes code aggressively, and there's no runtime or garbage collector. \
             Rust's ownership system allows for efficient memory management without sacrificing safety.",
            0.88,
        ),
        Document::new(
            "rust-concurrency",
            "Rust's ownership and type system enable fearless concurrency. The compiler prevents \
             data races at compile time by ensuring that mutable data is not shared across threads. \
             This is achieved through Send and Sync traits, which mark types as safe to transfer \
             or share between threads.",
            0.85,
        ),
        Document::new(
            "rust-ecosystem",
            "The Rust ecosystem includes Cargo for package management, crates.io for library sharing, \
             and rustup for toolchain management. The community has built thousands of high-quality \
             libraries for web development, systems programming, embedded systems, and more.",
            0.78,
        ),
    ];

    let system_prompt = "You are a helpful AI assistant that answers questions about Rust programming language.";
    let query = "What are the key features of Rust that make it safe and performant?";

    println!("System Prompt: {}", system_prompt);
    println!("Query: {}", query);
    println!("\nRetrieved Documents: {}", documents.len());

    // Demonstrate all truncation strategies
    let strategies = vec![
        TruncationStrategy::Head,
        TruncationStrategy::Tail,
        TruncationStrategy::Middle,
        TruncationStrategy::SlidingWindow,
    ];

    for strategy in strategies {
        println!("\n{}", "=".repeat(60));
        println!("Truncation Strategy: {}", strategy);
        println!("{}", "=".repeat(60));

        let context = manager.build_context(
            system_prompt,
            query,
            &documents,
            strategy,
        )?;

        manager.print_stats(&context);

        println!("\nIncluded Documents:");
        for (i, doc) in context.documents.iter().enumerate() {
            if doc.id == "..." {
                println!("  {}", doc.content);
            } else {
                println!("  [{}] {} (relevance: {:.2}, tokens: {})",
                         i + 1,
                         doc.id,
                         doc.relevance,
                         doc.token_count.unwrap_or(0));
            }
        }
    }

    // Demonstrate priority-based selection with tight budget
    println!("\n{}", "=".repeat(60));
    println!("Priority-Based Selection (Tight Budget)");
    println!("{}", "=".repeat(60));

    let mut tight_manager = ContextManager::new(4096, "gpt-3.5-turbo")?;
    tight_manager.set_budget_allocation(300, 150, 500)?;

    let tight_context = tight_manager.build_context(
        system_prompt,
        query,
        &documents,
        TruncationStrategy::Head,
    )?;

    tight_manager.print_stats(&tight_context);

    println!("\nPriority Order:");
    let mut sorted_docs = documents.clone();
    sorted_docs.sort_by(|a, b| b.priority().partial_cmp(&a.priority()).unwrap());

    for (i, doc) in sorted_docs.iter().enumerate() {
        let included = tight_context.documents.iter().any(|d| d.id == doc.id);
        println!("  {}. {} (priority: {:.3}, relevance: {:.2}) {}",
                 i + 1,
                 doc.id,
                 doc.priority(),
                 doc.relevance,
                 if included { "✓" } else { "✗" });
    }

    println!("\n{}", "=".repeat(60));
    println!("Summary");
    println!("{}", "=".repeat(60));
    println!("\nKey Takeaways:");
    println!("1. Head strategy: Best for sequential processing");
    println!("2. Tail strategy: Best for recent context priority");
    println!("3. Middle strategy: Maintains context boundaries");
    println!("4. Sliding window: Best for streaming/progressive processing");
    println!("\nPrioritization ensures highest-relevance documents are included first.");
    println!("Token counting with tiktoken provides accurate budget management.");
    println!("Smart truncation prevents context overflow while preserving quality.");

    Ok(())
}
