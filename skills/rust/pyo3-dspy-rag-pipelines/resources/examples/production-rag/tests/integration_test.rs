//! Integration tests for Production RAG system
//!
//! These tests verify end-to-end functionality of the RAG system.
//! Run with: cargo test --test integration

use anyhow::Result;
use serde_json::json;

// Mock configuration for testing
const TEST_BASE_URL: &str = "http://localhost:8080";

/// Helper to check if server is running
async fn is_server_running() -> bool {
    reqwest::Client::new()
        .get(format!("{}/health", TEST_BASE_URL))
        .send()
        .await
        .is_ok()
}

/// Test health endpoint
#[tokio::test]
async fn test_health_endpoint() -> Result<()> {
    if !is_server_running().await {
        println!("Server not running, skipping test");
        return Ok(());
    }

    let client = reqwest::Client::new();
    let response = client
        .get(format!("{}/health", TEST_BASE_URL))
        .send()
        .await?;

    assert!(response.status().is_success());

    let body: serde_json::Value = response.json().await?;
    assert!(body.get("status").is_some());
    assert!(body.get("components").is_some());

    println!("Health check response: {}", serde_json::to_string_pretty(&body)?);
    Ok(())
}

/// Test document indexing
#[tokio::test]
async fn test_index_documents() -> Result<()> {
    if !is_server_running().await {
        println!("Server not running, skipping test");
        return Ok(());
    }

    let client = reqwest::Client::new();

    let payload = json!({
        "documents": [
            {
                "id": "test-doc-1",
                "text": "Rust is a systems programming language.",
                "metadata": {"category": "test"}
            }
        ],
        "chunk_size": 512,
        "overlap": 50
    });

    let response = client
        .post(format!("{}/index", TEST_BASE_URL))
        .json(&payload)
        .send()
        .await?;

    assert!(response.status().is_success());

    let body: serde_json::Value = response.json().await?;
    assert!(body.get("indexed").is_some());
    assert!(body.get("duration_ms").is_some());

    let indexed = body["indexed"].as_u64().unwrap();
    assert!(indexed > 0, "Should have indexed at least one chunk");

    println!("Indexed {} chunks", indexed);
    Ok(())
}

/// Test query endpoint
#[tokio::test]
async fn test_query() -> Result<()> {
    if !is_server_running().await {
        println!("Server not running, skipping test");
        return Ok(());
    }

    let client = reqwest::Client::new();

    // First, index a document
    let index_payload = json!({
        "documents": [
            {
                "id": "query-test-doc",
                "text": "Rust provides memory safety without garbage collection.",
                "metadata": {"test": true}
            }
        ]
    });

    client
        .post(format!("{}/index", TEST_BASE_URL))
        .json(&index_payload)
        .send()
        .await?;

    // Wait for indexing
    tokio::time::sleep(tokio::time::Duration::from_secs(2)).await;

    // Now query
    let query_payload = json!({
        "query": "How does Rust ensure memory safety?",
        "top_k": 3,
        "rerank": false
    });

    let response = client
        .post(format!("{}/query", TEST_BASE_URL))
        .json(&query_payload)
        .send()
        .await?;

    assert!(response.status().is_success());

    let body: serde_json::Value = response.json().await?;
    assert!(body.get("answer").is_some());
    assert!(body.get("sources").is_some());
    assert!(body.get("latency_ms").is_some());

    let sources = body["sources"].as_array().unwrap();
    println!("Query returned {} sources", sources.len());

    Ok(())
}

/// Test metrics endpoint
#[tokio::test]
async fn test_metrics_endpoint() -> Result<()> {
    if !is_server_running().await {
        println!("Server not running, skipping test");
        return Ok(());
    }

    let client = reqwest::Client::new();
    let response = client
        .get(format!("{}/metrics", TEST_BASE_URL))
        .send()
        .await?;

    assert!(response.status().is_success());

    let body = response.text().await?;
    assert!(body.contains("rag_queries_total"));
    assert!(body.contains("rag_cache_hits_total"));

    println!("Metrics endpoint working");
    Ok(())
}

/// Test error handling for invalid requests
#[tokio::test]
async fn test_error_handling() -> Result<()> {
    if !is_server_running().await {
        println!("Server not running, skipping test");
        return Ok(());
    }

    let client = reqwest::Client::new();

    // Test invalid JSON
    let response = client
        .post(format!("{}/query", TEST_BASE_URL))
        .header("Content-Type", "application/json")
        .body("invalid json")
        .send()
        .await?;

    assert!(response.status().is_client_error());

    // Test missing required fields
    let response = client
        .post(format!("{}/query", TEST_BASE_URL))
        .json(&json!({}))
        .send()
        .await?;

    assert!(response.status().is_client_error());

    println!("Error handling tests passed");
    Ok(())
}

/// Test query with reranking
#[tokio::test]
async fn test_query_with_reranking() -> Result<()> {
    if !is_server_running().await {
        println!("Server not running, skipping test");
        return Ok(());
    }

    let client = reqwest::Client::new();

    // Index documents
    let index_payload = json!({
        "documents": [
            {
                "id": "rerank-1",
                "text": "Rust ownership prevents memory leaks.",
                "metadata": {}
            },
            {
                "id": "rerank-2",
                "text": "Python has automatic garbage collection.",
                "metadata": {}
            }
        ]
    });

    client
        .post(format!("{}/index", TEST_BASE_URL))
        .json(&index_payload)
        .send()
        .await?;

    tokio::time::sleep(tokio::time::Duration::from_secs(2)).await;

    // Query with reranking
    let query_payload = json!({
        "query": "How does Rust manage memory?",
        "top_k": 2,
        "rerank": true
    });

    let response = client
        .post(format!("{}/query", TEST_BASE_URL))
        .json(&query_payload)
        .send()
        .await?;

    assert!(response.status().is_success());

    let body: serde_json::Value = response.json().await?;
    let sources = body["sources"].as_array().unwrap();

    // With reranking, Rust-related document should rank higher
    if !sources.is_empty() {
        let top_source = &sources[0];
        println!("Top source: {}", top_source["text"]);
    }

    Ok(())
}

/// Benchmark query latency
#[tokio::test]
async fn test_query_latency() -> Result<()> {
    if !is_server_running().await {
        println!("Server not running, skipping test");
        return Ok(());
    }

    let client = reqwest::Client::new();

    // Index a document
    let index_payload = json!({
        "documents": [{
            "id": "latency-test",
            "text": "Test document for latency measurement.",
            "metadata": {}
        }]
    });

    client
        .post(format!("{}/index", TEST_BASE_URL))
        .json(&index_payload)
        .send()
        .await?;

    tokio::time::sleep(tokio::time::Duration::from_secs(2)).await;

    // Measure query latency
    let query_payload = json!({
        "query": "What is this about?",
        "top_k": 3,
        "rerank": false
    });

    let start = std::time::Instant::now();
    let response = client
        .post(format!("{}/query", TEST_BASE_URL))
        .json(&query_payload)
        .send()
        .await?;
    let elapsed = start.elapsed();

    assert!(response.status().is_success());

    let body: serde_json::Value = response.json().await?;
    let server_latency = body["latency_ms"].as_u64().unwrap();

    println!("Client-measured latency: {}ms", elapsed.as_millis());
    println!("Server-reported latency: {}ms", server_latency);

    // Assert reasonable latency (< 5 seconds)
    assert!(elapsed.as_secs() < 5, "Query took too long");

    Ok(())
}

/// Test batch indexing
#[tokio::test]
async fn test_batch_indexing() -> Result<()> {
    if !is_server_running().await {
        println!("Server not running, skipping test");
        return Ok(());
    }

    let client = reqwest::Client::new();

    // Create batch of documents
    let documents: Vec<_> = (0..10)
        .map(|i| {
            json!({
                "id": format!("batch-{}", i),
                "text": format!("Document number {} for batch testing.", i),
                "metadata": {"batch": i}
            })
        })
        .collect();

    let payload = json!({
        "documents": documents,
        "chunk_size": 256,
        "overlap": 25
    });

    let response = client
        .post(format!("{}/index", TEST_BASE_URL))
        .json(&payload)
        .send()
        .await?;

    assert!(response.status().is_success());

    let body: serde_json::Value = response.json().await?;
    let indexed = body["indexed"].as_u64().unwrap();

    println!("Batch indexed {} chunks", indexed);
    assert!(indexed >= 10, "Should index at least 10 chunks");

    Ok(())
}

/// Test concurrent queries
#[tokio::test]
async fn test_concurrent_queries() -> Result<()> {
    if !is_server_running().await {
        println!("Server not running, skipping test");
        return Ok(());
    }

    let client = reqwest::Client::new();

    // Index a document first
    let index_payload = json!({
        "documents": [{
            "id": "concurrent-test",
            "text": "Test document for concurrent queries.",
            "metadata": {}
        }]
    });

    client
        .post(format!("{}/index", TEST_BASE_URL))
        .json(&index_payload)
        .send()
        .await?;

    tokio::time::sleep(tokio::time::Duration::from_secs(2)).await;

    // Execute concurrent queries
    let mut handles = vec![];

    for i in 0..5 {
        let client = client.clone();
        let handle = tokio::spawn(async move {
            let payload = json!({
                "query": format!("Query number {}", i),
                "top_k": 2,
                "rerank": false
            });

            client
                .post(format!("{}/query", TEST_BASE_URL))
                .json(&payload)
                .send()
                .await
        });
        handles.push(handle);
    }

    // Wait for all queries
    let results = futures::future::join_all(handles).await;

    // Check all succeeded
    for (i, result) in results.iter().enumerate() {
        match result {
            Ok(Ok(response)) => {
                assert!(response.status().is_success(), "Query {} failed", i);
            }
            _ => panic!("Query {} failed", i),
        }
    }

    println!("All 5 concurrent queries succeeded");
    Ok(())
}
