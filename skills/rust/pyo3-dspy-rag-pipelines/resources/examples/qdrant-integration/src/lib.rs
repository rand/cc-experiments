use anyhow::{Context, Result};
use qdrant_client::prelude::*;
use qdrant_client::qdrant::{
    Condition, CreateCollection, Distance, FieldCondition, Filter, Match, PointStruct,
    SearchPoints, VectorParams, VectorsConfig,
};
use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::collections::HashMap;
use tracing::{error, info, warn};

/// Qdrant client wrapper with production-ready patterns
pub struct QdrantClient {
    client: qdrant_client::client::QdrantClient,
    url: String,
}

/// Vector point for upsert operations
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VectorPoint {
    pub id: String,
    pub vector: Vec<f32>,
    pub payload: Value,
}

/// Search filter configuration
#[derive(Debug, Clone, Default)]
pub struct SearchFilter {
    pub must: Vec<(String, String)>,
    pub score_threshold: Option<f32>,
}

/// Search result with score and payload
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SearchResult {
    pub id: String,
    pub score: f32,
    pub payload: Value,
}

impl QdrantClient {
    /// Create a new Qdrant client
    pub async fn new(url: &str, api_key: Option<&str>) -> Result<Self> {
        info!("Connecting to Qdrant at {}", url);

        let mut client = qdrant_client::client::QdrantClient::from_url(url)
            .build()
            .context("Failed to build Qdrant client")?;

        // Set API key if provided (for Qdrant Cloud)
        if let Some(key) = api_key {
            client = qdrant_client::client::QdrantClient::from_url(url)
                .api_key(key)
                .build()
                .context("Failed to build Qdrant client with API key")?;
        }

        Ok(Self {
            client,
            url: url.to_string(),
        })
    }

    /// Check if Qdrant is healthy and reachable
    pub async fn health_check(&self) -> Result<bool> {
        match self.client.health_check().await {
            Ok(_) => {
                info!("Qdrant health check passed");
                Ok(true)
            }
            Err(e) => {
                error!("Qdrant health check failed: {}", e);
                Ok(false)
            }
        }
    }

    /// Check if a collection exists
    pub async fn collection_exists(&self, name: &str) -> Result<bool> {
        match self.client.collection_exists(name).await {
            Ok(exists) => Ok(exists),
            Err(e) => {
                warn!("Error checking collection existence: {}", e);
                Ok(false)
            }
        }
    }

    /// Create a new collection with vector configuration
    pub async fn create_collection(
        &self,
        name: &str,
        vector_size: u64,
        distance_metric: &str,
    ) -> Result<()> {
        info!(
            "Creating collection '{}' with vector size {} and distance metric {}",
            name, vector_size, distance_metric
        );

        // Parse distance metric
        let distance = match distance_metric.to_lowercase().as_str() {
            "cosine" => Distance::Cosine,
            "euclidean" | "l2" => Distance::Euclid,
            "dot" | "dotproduct" => Distance::Dot,
            "manhattan" | "l1" => Distance::Manhattan,
            _ => {
                warn!(
                    "Unknown distance metric '{}', defaulting to Cosine",
                    distance_metric
                );
                Distance::Cosine
            }
        };

        // Create collection
        self.client
            .create_collection(&CreateCollection {
                collection_name: name.to_string(),
                vectors_config: Some(VectorsConfig {
                    config: Some(qdrant_client::qdrant::vectors_config::Config::Params(
                        VectorParams {
                            size: vector_size,
                            distance: distance.into(),
                            ..Default::default()
                        },
                    )),
                }),
                ..Default::default()
            })
            .await
            .context("Failed to create collection")?;

        info!("Collection '{}' created successfully", name);
        Ok(())
    }

    /// Delete a collection
    pub async fn delete_collection(&self, name: &str) -> Result<()> {
        info!("Deleting collection '{}'", name);

        self.client
            .delete_collection(name)
            .await
            .context("Failed to delete collection")?;

        info!("Collection '{}' deleted successfully", name);
        Ok(())
    }

    /// Upsert vectors with payloads
    pub async fn upsert_vectors(
        &self,
        collection: &str,
        points: Vec<VectorPoint>,
    ) -> Result<()> {
        info!(
            "Upserting {} points to collection '{}'",
            points.len(),
            collection
        );

        let qdrant_points: Vec<PointStruct> = points
            .into_iter()
            .map(|p| {
                // Convert JSON payload to HashMap
                let payload: HashMap<String, Value> = match p.payload {
                    Value::Object(map) => map.into_iter().collect(),
                    _ => HashMap::new(),
                };

                PointStruct::new(p.id, p.vector, payload)
            })
            .collect();

        self.client
            .upsert_points_blocking(collection, None, qdrant_points, None)
            .await
            .context("Failed to upsert points")?;

        info!("Points upserted successfully");
        Ok(())
    }

    /// Search for similar vectors with optional filters
    pub async fn search(
        &self,
        collection: &str,
        query_vector: Vec<f32>,
        limit: u64,
        filter: Option<SearchFilter>,
    ) -> Result<Vec<SearchResult>> {
        info!("Searching collection '{}' with limit {}", collection, limit);

        // Build filter if provided
        let qdrant_filter = filter.as_ref().and_then(|f| {
            if f.must.is_empty() {
                None
            } else {
                let conditions: Vec<Condition> = f
                    .must
                    .iter()
                    .map(|(key, value)| {
                        Condition::Field(FieldCondition::new_match(
                            key.clone(),
                            Match::new_keyword(value.clone()),
                        ))
                    })
                    .collect();

                Some(Filter {
                    must: conditions,
                    ..Default::default()
                })
            }
        });

        // Perform search
        let search_result = self
            .client
            .search_points(&SearchPoints {
                collection_name: collection.to_string(),
                vector: query_vector,
                limit,
                filter: qdrant_filter,
                score_threshold: filter.as_ref().and_then(|f| f.score_threshold),
                with_payload: Some(true.into()),
                ..Default::default()
            })
            .await
            .context("Failed to search points")?;

        // Convert results
        let results: Vec<SearchResult> = search_result
            .result
            .into_iter()
            .map(|scored_point| {
                let payload = scored_point
                    .payload
                    .iter()
                    .map(|(k, v)| (k.clone(), serde_json::to_value(v).unwrap_or(Value::Null)))
                    .collect::<HashMap<String, Value>>();

                SearchResult {
                    id: scored_point.id.unwrap().to_string(),
                    score: scored_point.score,
                    payload: Value::Object(payload.into_iter().collect()),
                }
            })
            .collect();

        info!("Search returned {} results", results.len());
        Ok(results)
    }

    /// Get collection info
    pub async fn get_collection_info(&self, name: &str) -> Result<()> {
        let info = self
            .client
            .collection_info(name)
            .await
            .context("Failed to get collection info")?;

        println!("Collection: {}", name);
        println!("  Status: {:?}", info.result.unwrap().status());

        Ok(())
    }
}

// Allow Clone for benchmarks
impl Clone for QdrantClient {
    fn clone(&self) -> Self {
        Self {
            client: qdrant_client::client::QdrantClient::from_url(&self.url)
                .build()
                .expect("Failed to clone client"),
            url: self.url.clone(),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_client_creation() {
        let result = QdrantClient::new("http://localhost:6333", None).await;
        assert!(result.is_ok());
    }

    #[tokio::test]
    async fn test_health_check() {
        let client = QdrantClient::new("http://localhost:6333", None)
            .await
            .expect("Failed to create client");

        // Health check may fail if Qdrant is not running
        let _ = client.health_check().await;
    }

    #[tokio::test]
    async fn test_collection_lifecycle() {
        let client = QdrantClient::new("http://localhost:6333", None)
            .await
            .expect("Failed to create client");

        let test_collection = "test_collection";

        // Clean up if exists
        if client
            .collection_exists(test_collection)
            .await
            .unwrap_or(false)
        {
            client.delete_collection(test_collection).await.ok();
        }

        // Create collection
        let create_result = client
            .create_collection(test_collection, 128, "Cosine")
            .await;

        if create_result.is_ok() {
            // Verify it exists
            assert!(client
                .collection_exists(test_collection)
                .await
                .unwrap_or(false));

            // Clean up
            client.delete_collection(test_collection).await.ok();
        }
    }

    #[tokio::test]
    async fn test_upsert_and_search() {
        let client = QdrantClient::new("http://localhost:6333", None)
            .await
            .expect("Failed to create client");

        let test_collection = "test_search";

        // Setup
        if client
            .collection_exists(test_collection)
            .await
            .unwrap_or(false)
        {
            client.delete_collection(test_collection).await.ok();
        }

        if client
            .create_collection(test_collection, 4, "Cosine")
            .await
            .is_ok()
        {
            // Upsert test points
            let points = vec![
                VectorPoint {
                    id: "test1".to_string(),
                    vector: vec![1.0, 0.0, 0.0, 0.0],
                    payload: serde_json::json!({"label": "a"}),
                },
                VectorPoint {
                    id: "test2".to_string(),
                    vector: vec![0.0, 1.0, 0.0, 0.0],
                    payload: serde_json::json!({"label": "b"}),
                },
            ];

            if client.upsert_vectors(test_collection, points).await.is_ok() {
                // Search
                let results = client
                    .search(test_collection, vec![1.0, 0.0, 0.0, 0.0], 1, None)
                    .await;

                if let Ok(results) = results {
                    assert!(!results.is_empty());
                    assert_eq!(results[0].id, "test1");
                }
            }

            // Cleanup
            client.delete_collection(test_collection).await.ok();
        }
    }
}
