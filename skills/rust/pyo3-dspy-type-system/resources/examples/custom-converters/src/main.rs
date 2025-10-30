use anyhow::Result;
use custom_converters::{Citation, Document, FromPyAny, ToPyDict};
use pyo3::prelude::*;

/// Standalone binary for testing
fn main() -> Result<()> {
    println!("Custom Type Converters Example\n");

    pyo3::prepare_freethreaded_python();

    Python::with_gil(|py| {
        // Create sample document
        println!("Creating sample document...");
        let doc = Document::new(
            "Research Paper on Type Systems",
            "This paper explores advanced type system concepts in modern programming languages.",
            "https://research.example.com/papers/type-systems-2024",
        )
        .with_metadata("author", "Jane Smith")
        .with_metadata("year", "2024")
        .with_metadata("doi", "10.1234/example.2024.001");

        let doc_dict = doc.to_py_dict(py)?;
        println!("Document as Python dict:");
        println!("  Title: {}", doc.title);
        println!("  Source: {}", doc.source);
        println!("  Timestamp: {}", doc.timestamp);
        println!("  Metadata: {:?}\n", doc.metadata);

        // Convert back to Rust
        println!("Converting back to Rust...");
        let doc_bound = doc_dict.bind(py);
        let doc_any = doc_bound.as_any();
        let doc_roundtrip = Document::from_py_any(doc_any)?;
        println!("Roundtrip successful!");
        println!("  Title: {}", doc_roundtrip.title);
        println!("  Content length: {} chars\n", doc_roundtrip.content.len());

        // Create citation
        println!("Creating citation...");
        let citation = Citation::new(
            "Smith (2024) discusses type system evolution in detail.",
            "APA",
        )
        .with_document(doc_roundtrip)
        .with_page_numbers(vec![15, 16, 17, 18]);

        println!("Citation created:");
        println!("  Text: {}", citation.text);
        println!("  Style: {}", citation.citation_style);
        println!("  Documents: {}", citation.documents.len());
        println!("  Pages: {:?}\n", citation.page_numbers);

        let citation_dict = citation.to_py_dict(py)?;

        // Convert citation back to Rust
        println!("Converting citation back to Rust...");
        let citation_bound = citation_dict.bind(py);
        let citation_any = citation_bound.as_any();
        let citation_roundtrip = Citation::from_py_any(citation_any)?;
        println!("Roundtrip successful!");
        println!("  Text: {}", citation_roundtrip.text);
        println!("  Style: {}", citation_roundtrip.citation_style);
        println!("  Documents: {}", citation_roundtrip.documents.len());
        if let Some(pages) = &citation_roundtrip.page_numbers {
            println!("  Pages: {:?}", pages);
        }

        println!("\n=== All conversions successful! ===");
        println!("\nKey features demonstrated:");
        println!("  ✓ Custom Document type with metadata");
        println!("  ✓ Custom Citation type with nested documents");
        println!("  ✓ DateTime handling (chrono → Python → chrono)");
        println!("  ✓ Bidirectional conversion (Rust ↔ Python)");
        println!("  ✓ Nested struct conversion");
        println!("  ✓ Optional field handling");

        Ok::<_, anyhow::Error>(())
    })?;

    Ok(())
}
