use anyhow::Result;
use serde_json;

// Generated types module
mod generated;
use generated::*;

fn main() -> Result<()> {
    println!("=== Automated Rust Type Generation Workflow ===\n");
    println!("This example demonstrates build-time code generation from DSPy signatures.\n");

    // Example 1: Simple Question-Answering
    println!("1. Simple Question-Answering (question -> answer)");
    println!("   {}", "-".repeat(60));
    let qa = QuestionToAnswer {
        question: "What is DSPy?".to_string(),
        answer: "DSPy is a framework for algorithmically optimizing LM prompts and weights."
            .to_string(),
    };
    println!("   Question: {}", qa.question);
    println!("   Answer: {}", qa.answer);
    println!("   JSON: {}\n", serde_json::to_string(&qa)?);

    // Example 2: Translation with Context
    println!("2. Translation (source_text, target_language -> translated_text)");
    println!("   {}", "-".repeat(60));
    let translation = SourceTextTargetLanguageToTranslatedText {
        source_text: "Hello, world!".to_string(),
        target_language: "Spanish".to_string(),
        translated_text: "¡Hola, mundo!".to_string(),
    };
    println!("   Source: {} ({})", translation.source_text, translation.target_language);
    println!("   Translation: {}", translation.translated_text);
    println!("   JSON: {}\n", serde_json::to_string(&translation)?);

    // Example 3: Multi-step Reasoning
    println!("3. Multi-step Reasoning (context, question -> reasoning, answer)");
    println!("   {}", "-".repeat(60));
    let reasoning = ContextQuestionToReasoningAnswer {
        context: "Rust is a systems programming language focused on safety and performance."
            .to_string(),
        question: "Why is Rust popular for systems programming?".to_string(),
        reasoning: "Given the context states Rust focuses on safety and performance, \
                    these are key requirements for systems programming where direct \
                    hardware access and reliability are critical."
            .to_string(),
        answer: "Rust's focus on memory safety without garbage collection and \
                 zero-cost abstractions makes it ideal for systems programming."
            .to_string(),
    };
    println!("   Context: {}", reasoning.context);
    println!("   Question: {}", reasoning.question);
    println!("   Reasoning: {}", reasoning.reasoning);
    println!("   Answer: {}", reasoning.answer);
    println!("   JSON (pretty):");
    println!("{}\n", serde_json::to_string_pretty(&reasoning)?);

    // Example 4: Classification
    println!("4. Classification (text, categories -> label, confidence)");
    println!("   {}", "-".repeat(60));
    let classification = TextCategoriesToLabelConfidence {
        text: "This product exceeded my expectations! Highly recommended.".to_string(),
        categories: "positive, negative, neutral".to_string(),
        label: "positive".to_string(),
        confidence: "0.95".to_string(),
    };
    println!("   Text: {}", classification.text);
    println!("   Categories: {}", classification.categories);
    println!("   Label: {} (confidence: {})", classification.label, classification.confidence);
    println!("   JSON: {}\n", serde_json::to_string(&classification)?);

    // Example 5: Information Extraction
    println!("5. Information Extraction (document -> entities, relations, summary)");
    println!("   {}", "-".repeat(60));
    let extraction = DocumentToEntitiesRelationsSummary {
        document: "Apple Inc. CEO Tim Cook announced the new iPhone 15 at the \
                   Cupertino headquarters on September 12, 2023."
            .to_string(),
        entities: "Apple Inc. (ORG), Tim Cook (PERSON), iPhone 15 (PRODUCT), \
                   Cupertino (LOC), September 12, 2023 (DATE)"
            .to_string(),
        relations: "Tim Cook -> CEO_OF -> Apple Inc., iPhone 15 -> ANNOUNCED_BY -> Tim Cook"
            .to_string(),
        summary: "Apple CEO Tim Cook unveiled iPhone 15 at Cupertino headquarters.".to_string(),
    };
    println!("   Document: {}", extraction.document);
    println!("   Entities: {}", extraction.entities);
    println!("   Relations: {}", extraction.relations);
    println!("   Summary: {}", extraction.summary);
    println!("   JSON (pretty):");
    println!("{}\n", serde_json::to_string_pretty(&extraction)?);

    // Example 6: SQL Generation
    println!("6. SQL Generation (natural_language_query -> sql_query)");
    println!("   {}", "-".repeat(60));
    let sql_gen = NaturalLanguageQueryToSqlQuery {
        natural_language_query: "Find all users who registered in the last 30 days".to_string(),
        sql_query: "SELECT * FROM users WHERE registration_date >= NOW() - INTERVAL '30 days'"
            .to_string(),
    };
    println!("   Natural Language: {}", sql_gen.natural_language_query);
    println!("   SQL: {}", sql_gen.sql_query);
    println!("   JSON: {}\n", serde_json::to_string(&sql_gen)?);

    // Example 7: Code Generation
    println!("7. Code Generation (description, language -> code, explanation)");
    println!("   {}", "-".repeat(60));
    let code_gen = DescriptionLanguageToCodeExplanation {
        description: "Sort a vector of integers in descending order".to_string(),
        language: "Rust".to_string(),
        code: "let mut nums = vec![3, 1, 4, 1, 5];\nnums.sort_by(|a, b| b.cmp(a));".to_string(),
        explanation: "Uses sort_by with reversed comparison to sort descending. \
                      The closure |a, b| b.cmp(a) compares in reverse order."
            .to_string(),
    };
    println!("   Description: {}", code_gen.description);
    println!("   Language: {}", code_gen.language);
    println!("   Code:\n{}", code_gen.code);
    println!("   Explanation: {}", code_gen.explanation);
    println!("   JSON (pretty):");
    println!("{}\n", serde_json::to_string_pretty(&code_gen)?);

    // Example 8: Summarization with Constraints
    println!("8. Summarization (article, max_length -> summary)");
    println!("   {}", "-".repeat(60));
    let summarization = ArticleMaxLengthToSummary {
        article: "Rust is a multi-paradigm programming language focused on performance \
                  and safety, especially safe concurrency. It is syntactically similar \
                  to C++, but provides memory safety without using garbage collection."
            .to_string(),
        max_length: "50".to_string(),
        summary: "Rust: fast, safe, concurrent language without GC.".to_string(),
    };
    println!("   Article: {}", summarization.article);
    println!("   Max Length: {}", summarization.max_length);
    println!("   Summary ({} chars): {}",
             summarization.summary.len(),
             summarization.summary);
    println!("   JSON: {}\n", serde_json::to_string(&summarization)?);

    // Demonstrate type safety
    println!("\n=== Type Safety Demonstration ===");
    println!("All structs are strongly typed at compile time:");
    println!("- No runtime type checking needed");
    println!("- IDE autocomplete works perfectly");
    println!("- Impossible to mix up field names");
    println!("- Serde serialization is automatic\n");

    // Show clone and debug capabilities
    println!("=== Derived Traits ===");
    let qa_clone = qa.clone();
    println!("Clone: {:?}", qa_clone);
    println!("\nAll generated types support:");
    println!("- Debug: Pretty-printing");
    println!("- Clone: Duplicate instances");
    println!("- Serialize: Convert to JSON/bincode/etc");
    println!("- Deserialize: Parse from JSON/bincode/etc");

    println!("\n=== Build-time Code Generation ===");
    println!("These types were generated automatically by build.rs");
    println!("- Defined in: signatures.txt");
    println!("- Generated by: signature_codegen.py");
    println!("- Output: src/generated.rs");
    println!("- Triggered: On cargo build when signatures.txt changes");

    println!("\n=== Development Workflow ===");
    println!("1. Add signature to signatures.txt:");
    println!("   input -> output");
    println!("2. Run cargo build:");
    println!("   - build.rs detects change");
    println!("   - Runs signature_codegen.py");
    println!("   - Generates new types");
    println!("3. Use generated types:");
    println!("   use generated::InputToOutput;");
    println!("   let instance = InputToOutput {{ ... }};");

    Ok(())
}
