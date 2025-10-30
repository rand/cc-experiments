use criterion::{black_box, criterion_group, criterion_main, Criterion, BenchmarkId};
use qdrant_integration::{QdrantClient, VectorPoint};
use serde_json::json;
use std::time::Duration;

async fn setup_test_collection(client: &QdrantClient, name: &str, size: usize) {
    // Delete if exists
    let _ = client.delete_collection(name).await;

    // Create collection
    client
        .create_collection(name, 128, "Cosine")
        .await
        .expect("Failed to create collection");

    // Generate test points
    let points: Vec<VectorPoint> = (0..size)
        .map(|i| VectorPoint {
            id: format!("point_{}", i),
            vector: vec![i as f32 / size as f32; 128],
            payload: json!({
                "index": i,
                "category": format!("cat_{}", i % 10),
                "value": i as f64,
            }),
        })
        .collect();

    // Batch upsert
    client
        .upsert_vectors(name, points)
        .await
        .expect("Failed to upsert points");
}

fn benchmark_upsert(c: &mut Criterion) {
    let runtime = tokio::runtime::Runtime::new().unwrap();

    let mut group = c.benchmark_group("upsert");
    group.sample_size(10);
    group.measurement_time(Duration::from_secs(30));

    for size in [10, 100, 1000].iter() {
        group.bench_with_input(BenchmarkId::from_parameter(size), size, |b, &size| {
            b.to_async(&runtime).iter(|| async {
                let client = QdrantClient::new("http://localhost:6333", None)
                    .await
                    .expect("Failed to create client");

                let collection = format!("bench_upsert_{}", size);

                // Setup
                let _ = client.delete_collection(&collection).await;
                client
                    .create_collection(&collection, 128, "Cosine")
                    .await
                    .expect("Failed to create collection");

                // Generate points
                let points: Vec<VectorPoint> = (0..size)
                    .map(|i| VectorPoint {
                        id: format!("point_{}", i),
                        vector: vec![i as f32 / size as f32; 128],
                        payload: json!({
                            "index": i,
                            "category": format!("cat_{}", i % 10),
                        }),
                    })
                    .collect();

                // Benchmark upsert
                black_box(
                    client
                        .upsert_vectors(&collection, points)
                        .await
                        .expect("Failed to upsert"),
                );

                // Cleanup
                let _ = client.delete_collection(&collection).await;
            });
        });
    }

    group.finish();
}

fn benchmark_search(c: &mut Criterion) {
    let runtime = tokio::runtime::Runtime::new().unwrap();

    // Setup test data once
    let (client, collection_name) = runtime.block_on(async {
        let client = QdrantClient::new("http://localhost:6333", None)
            .await
            .expect("Failed to create client");

        let collection = "bench_search";
        setup_test_collection(&client, collection, 1000).await;

        (client, collection.to_string())
    });

    let mut group = c.benchmark_group("search");
    group.sample_size(50);

    for limit in [1, 10, 50, 100].iter() {
        group.bench_with_input(BenchmarkId::from_parameter(limit), limit, |b, &limit| {
            b.to_async(&runtime).iter(|| {
                let client = client.clone();
                let collection = collection_name.clone();
                async move {
                    let query_vector = vec![0.5; 128];
                    black_box(
                        client
                            .search(&collection, query_vector, limit, None)
                            .await
                            .expect("Search failed"),
                    );
                }
            });
        });
    }

    group.finish();

    // Cleanup
    runtime.block_on(async {
        let _ = client.delete_collection(&collection_name).await;
    });
}

fn benchmark_filtered_search(c: &mut Criterion) {
    let runtime = tokio::runtime::Runtime::new().unwrap();

    let (client, collection_name) = runtime.block_on(async {
        let client = QdrantClient::new("http://localhost:6333", None)
            .await
            .expect("Failed to create client");

        let collection = "bench_filtered_search";
        setup_test_collection(&client, collection, 1000).await;

        (client, collection.to_string())
    });

    let mut group = c.benchmark_group("filtered_search");
    group.sample_size(50);

    group.bench_function("with_filter", |b| {
        b.to_async(&runtime).iter(|| {
            let client = client.clone();
            let collection = collection_name.clone();
            async move {
                let query_vector = vec![0.5; 128];
                let filter = qdrant_integration::SearchFilter {
                    must: vec![("category".to_string(), "cat_5".to_string())],
                    score_threshold: Some(0.0),
                };

                black_box(
                    client
                        .search(&collection, query_vector, 10, Some(filter))
                        .await
                        .expect("Search failed"),
                );
            }
        });
    });

    group.bench_function("without_filter", |b| {
        b.to_async(&runtime).iter(|| {
            let client = client.clone();
            let collection = collection_name.clone();
            async move {
                let query_vector = vec![0.5; 128];
                black_box(
                    client
                        .search(&collection, query_vector, 10, None)
                        .await
                        .expect("Search failed"),
                );
            }
        });
    });

    group.finish();

    // Cleanup
    runtime.block_on(async {
        let _ = client.delete_collection(&collection_name).await;
    });
}

criterion_group!(
    benches,
    benchmark_upsert,
    benchmark_search,
    benchmark_filtered_search
);
criterion_main!(benches);
