use anyhow::Result;
use qdrant_integration::{QdrantClient, SearchFilter, VectorPoint};
use tracing::info;

/// Example: Document ingestion and search
async fn example_document_search() -> Result<()> {
    // Initialize client
    let client = QdrantClient::new("http://localhost:6333", None).await?;

    // Health check
    if !client.health_check().await? {
        anyhow::bail!("Qdrant is not healthy");
    }

    let collection_name = "documents";

    // Delete existing collection if exists
    if client.collection_exists(collection_name).await? {
        client.delete_collection(collection_name).await?;
    }

    // Create collection (384 dimensions for sentence-transformers/all-MiniLM-L6-v2)
    client
        .create_collection(collection_name, 384, "Cosine")
        .await?;

    // Prepare sample documents with embeddings
    let documents = vec![
        VectorPoint {
            id: "doc1".to_string(),
            vector: vec![0.1; 384], // Placeholder embedding
            payload: serde_json::json!({
                "text": "Qdrant is a vector similarity search engine and vector database.",
                "category": "database",
                "source": "documentation",
                "timestamp": 1234567890,
                "tags": ["vectors", "search", "database"]
            }),
        },
        VectorPoint {
            id: "doc2".to_string(),
            vector: vec![0.2; 384],
            payload: serde_json::json!({
                "text": "Vector databases are optimized for similarity search using embeddings.",
                "category": "database",
                "source": "article",
                "timestamp": 1234567900,
                "tags": ["vectors", "embeddings", "similarity"]
            }),
        },
        VectorPoint {
            id: "doc3".to_string(),
            vector: vec![0.3; 384],
            payload: serde_json::json!({
                "text": "Machine learning models generate dense vector representations of data.",
                "category": "machine-learning",
                "source": "tutorial",
                "timestamp": 1234567910,
                "tags": ["ml", "embeddings", "vectors"]
            }),
        },
        VectorPoint {
            id: "doc4".to_string(),
            vector: vec![0.15; 384],
            payload: serde_json::json!({
                "text": "Qdrant supports filtered search with rich metadata.",
                "category": "database",
                "source": "documentation",
                "timestamp": 1234567920,
                "tags": ["qdrant", "search", "metadata"]
            }),
        },
        VectorPoint {
            id: "doc5".to_string(),
            vector: vec![0.25; 384],
            payload: serde_json::json!({
                "text": "Retrieval augmented generation combines search with language models.",
                "category": "rag",
                "source": "research",
                "timestamp": 1234567930,
                "tags": ["rag", "llm", "retrieval"]
            }),
        },
    ];

    // Upsert documents
    client.upsert_vectors(collection_name, documents).await?;

    println!("\n=== Unfiltered Search ===");
    let query_vector = vec![0.12; 384]; // Query embedding (placeholder)
    let results = client
        .search(collection_name, query_vector.clone(), 3, None)
        .await?;

    for (i, result) in results.iter().enumerate() {
        println!("\nResult {}:", i + 1);
        println!("  ID: {}", result.id);
        println!("  Score: {:.4}", result.score);
        println!("  Text: {}", result.payload["text"].as_str().unwrap_or(""));
        println!(
            "  Category: {}",
            result.payload["category"].as_str().unwrap_or("")
        );
    }

    println!("\n=== Filtered Search (category=database) ===");
    let filter = SearchFilter {
        must: vec![("category".to_string(), "database".to_string())],
        score_threshold: Some(0.0),
    };
    let filtered_results = client
        .search(collection_name, query_vector.clone(), 5, Some(filter))
        .await?;

    for (i, result) in filtered_results.iter().enumerate() {
        println!("\nResult {}:", i + 1);
        println!("  ID: {}", result.id);
        println!("  Score: {:.4}", result.score);
        println!("  Text: {}", result.payload["text"].as_str().unwrap_or(""));
        println!("  Tags: {:?}", result.payload["tags"]);
    }

    println!("\n=== Search with Score Threshold ===");
    let threshold_filter = SearchFilter {
        must: vec![],
        score_threshold: Some(0.95), // Only high similarity results
    };
    let threshold_results = client
        .search(collection_name, query_vector, 10, Some(threshold_filter))
        .await?;

    println!(
        "Results with score >= 0.95: {}",
        threshold_results.len()
    );
    for result in threshold_results {
        println!("  ID: {}, Score: {:.4}", result.id, result.score);
    }

    // Get collection info
    println!("\n=== Collection Info ===");
    client.get_collection_info(collection_name).await?;

    Ok(())
}

#[tokio::main]
async fn main() -> Result<()> {
    // Initialize tracing
    tracing_subscriber::fmt()
        .with_env_filter(
            tracing_subscriber::EnvFilter::from_default_env()
                .add_directive(tracing::Level::INFO.into()),
        )
        .init();

    info!("Starting Qdrant integration example");

    // Run example
    example_document_search().await?;

    info!("Example completed successfully");
    Ok(())
}
