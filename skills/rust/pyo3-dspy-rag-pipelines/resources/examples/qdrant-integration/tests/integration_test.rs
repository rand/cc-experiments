use anyhow::Result;
use qdrant_integration::{QdrantClient, SearchFilter, VectorPoint};

/// Integration test helper: setup test collection
async fn setup_test_collection(
    client: &QdrantClient,
    name: &str,
) -> Result<()> {
    // Delete if exists
    if client.collection_exists(name).await? {
        client.delete_collection(name).await?;
    }

    // Create collection
    client.create_collection(name, 128, "Cosine").await?;

    // Add test data
    let points = vec![
        VectorPoint {
            id: "test1".to_string(),
            vector: vec![1.0; 128],
            payload: serde_json::json!({
                "text": "Test document 1",
                "category": "test",
                "score": 10
            }),
        },
        VectorPoint {
            id: "test2".to_string(),
            vector: vec![0.5; 128],
            payload: serde_json::json!({
                "text": "Test document 2",
                "category": "test",
                "score": 20
            }),
        },
        VectorPoint {
            id: "test3".to_string(),
            vector: vec![0.1; 128],
            payload: serde_json::json!({
                "text": "Test document 3",
                "category": "other",
                "score": 30
            }),
        },
    ];

    client.upsert_vectors(name, points).await?;

    Ok(())
}

#[tokio::test]
async fn test_full_lifecycle() -> Result<()> {
    let client = QdrantClient::new("http://localhost:6333", None).await?;

    // Health check
    assert!(client.health_check().await?);

    let collection = "integration_test_lifecycle";

    // Setup
    setup_test_collection(&client, collection).await?;

    // Verify collection exists
    assert!(client.collection_exists(collection).await?);

    // Search
    let results = client
        .search(collection, vec![1.0; 128], 3, None)
        .await?;
    assert_eq!(results.len(), 3);

    // Cleanup
    client.delete_collection(collection).await?;
    assert!(!client.collection_exists(collection).await?);

    Ok(())
}

#[tokio::test]
async fn test_filtered_search() -> Result<()> {
    let client = QdrantClient::new("http://localhost:6333", None).await?;

    let collection = "integration_test_filtered";
    setup_test_collection(&client, collection).await?;

    // Search with filter
    let filter = SearchFilter {
        must: vec![("category".to_string(), "test".to_string())],
        score_threshold: None,
    };

    let results = client
        .search(collection, vec![1.0; 128], 10, Some(filter))
        .await?;

    // Should only return test1 and test2
    assert_eq!(results.len(), 2);
    for result in &results {
        assert_eq!(
            result.payload["category"].as_str().unwrap(),
            "test"
        );
    }

    // Cleanup
    client.delete_collection(collection).await?;

    Ok(())
}

#[tokio::test]
async fn test_score_threshold() -> Result<()> {
    let client = QdrantClient::new("http://localhost:6333", None).await?;

    let collection = "integration_test_threshold";
    setup_test_collection(&client, collection).await?;

    // Search with high score threshold
    let filter = SearchFilter {
        must: vec![],
        score_threshold: Some(0.99),
    };

    let results = client
        .search(collection, vec![1.0; 128], 10, Some(filter))
        .await?;

    // Only exact matches should pass
    assert!(!results.is_empty());
    for result in &results {
        assert!(result.score >= 0.99);
    }

    // Cleanup
    client.delete_collection(collection).await?;

    Ok(())
}

#[tokio::test]
async fn test_large_batch_upsert() -> Result<()> {
    let client = QdrantClient::new("http://localhost:6333", None).await?;

    let collection = "integration_test_batch";

    // Delete if exists
    if client.collection_exists(collection).await? {
        client.delete_collection(collection).await?;
    }

    // Create collection
    client.create_collection(collection, 64, "Cosine").await?;

    // Create 1000 points
    let points: Vec<VectorPoint> = (0..1000)
        .map(|i| VectorPoint {
            id: format!("batch_{}", i),
            vector: vec![i as f32 / 1000.0; 64],
            payload: serde_json::json!({
                "index": i,
                "batch": i / 100,
            }),
        })
        .collect();

    // Upsert
    client.upsert_vectors(collection, points).await?;

    // Search to verify
    let results = client
        .search(collection, vec![0.5; 64], 10, None)
        .await?;
    assert_eq!(results.len(), 10);

    // Cleanup
    client.delete_collection(collection).await?;

    Ok(())
}

#[tokio::test]
async fn test_empty_collection_search() -> Result<()> {
    let client = QdrantClient::new("http://localhost:6333", None).await?;

    let collection = "integration_test_empty";

    // Delete if exists
    if client.collection_exists(collection).await? {
        client.delete_collection(collection).await?;
    }

    // Create empty collection
    client.create_collection(collection, 32, "Cosine").await?;

    // Search empty collection
    let results = client
        .search(collection, vec![1.0; 32], 10, None)
        .await?;
    assert_eq!(results.len(), 0);

    // Cleanup
    client.delete_collection(collection).await?;

    Ok(())
}

#[tokio::test]
async fn test_multiple_filters() -> Result<()> {
    let client = QdrantClient::new("http://localhost:6333", None).await?;

    let collection = "integration_test_multi_filter";

    // Delete if exists
    if client.collection_exists(collection).await? {
        client.delete_collection(collection).await?;
    }

    // Create collection
    client.create_collection(collection, 32, "Cosine").await?;

    // Add data with multiple attributes
    let points = vec![
        VectorPoint {
            id: "1".to_string(),
            vector: vec![1.0; 32],
            payload: serde_json::json!({
                "category": "A",
                "type": "X",
            }),
        },
        VectorPoint {
            id: "2".to_string(),
            vector: vec![0.9; 32],
            payload: serde_json::json!({
                "category": "A",
                "type": "Y",
            }),
        },
        VectorPoint {
            id: "3".to_string(),
            vector: vec![0.8; 32],
            payload: serde_json::json!({
                "category": "B",
                "type": "X",
            }),
        },
    ];

    client.upsert_vectors(collection, points).await?;

    // Filter by category
    let filter = SearchFilter {
        must: vec![("category".to_string(), "A".to_string())],
        score_threshold: None,
    };

    let results = client
        .search(collection, vec![1.0; 32], 10, Some(filter))
        .await?;

    assert_eq!(results.len(), 2);

    // Cleanup
    client.delete_collection(collection).await?;

    Ok(())
}
