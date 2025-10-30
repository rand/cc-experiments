"""Test suite for production data processing pipeline."""
import production_pipeline

def test_pipeline_basic():
    pipeline = production_pipeline.DataPipeline(thread_count=4, batch_size=1000)

    data = [1.0, 4.0, 9.0, 16.0, 25.0]
    results, stats = pipeline.process(data)

    # Transform: sqrt(x) * 2
    expected = [2.0, 4.0, 6.0, 8.0, 10.0]
    assert results == expected
    assert stats.items_processed == 5
    assert stats.items_filtered == 0
    assert stats.items_failed == 0
    print(f"Basic pipeline: {stats.items_processed} items in {stats.duration_secs:.6f}s")

def test_pipeline_filtering():
    pipeline = production_pipeline.DataPipeline(thread_count=4, batch_size=1000)

    data = [1.0, -2.0, 4.0, -5.0, 9.0]
    results, stats = pipeline.process(data)

    # Only positive values: [1.0, 4.0, 9.0] -> [2.0, 4.0, 6.0]
    expected = [2.0, 4.0, 6.0]
    assert results == expected
    assert stats.items_processed == 3
    assert stats.items_filtered == 2
    print(f"Filtering: {stats.items_processed} processed, {stats.items_filtered} filtered")

def test_pipeline_error_handling():
    pipeline = production_pipeline.DataPipeline(thread_count=4, batch_size=1000)

    data = [1.0, float('nan'), 4.0, float('inf'), 9.0]
    results, stats = pipeline.process(data)

    # Valid values: [1.0, 4.0, 9.0]
    expected = [2.0, 4.0, 6.0]
    assert results == expected
    assert stats.items_processed == 3
    assert stats.items_failed == 2
    print(f"Error handling: {stats.items_processed} processed, {stats.items_failed} failed")

def test_pipeline_batched():
    pipeline = production_pipeline.DataPipeline(thread_count=4, batch_size=100)

    data = list(range(1, 1001))
    data = [float(x) for x in data]
    results, stats = pipeline.process_batched(data)

    assert stats.items_processed == 1000
    print(f"Batched processing: {stats.items_processed} items in {stats.duration_secs:.6f}s")
    print(f"  Throughput: {stats.items_processed / stats.duration_secs:.0f} items/sec")

def test_aggregate_pipeline():
    data = [1.0, 2.0, 3.0, 4.0, 5.0]

    mean, stddev, min_val, max_val, count = production_pipeline.aggregate_pipeline(data)

    assert count == 5
    assert abs(mean - 3.0) < 0.01
    assert abs(min_val - 1.0) < 0.01
    assert abs(max_val - 5.0) < 0.01
    print(f"\nAggregate: mean={mean:.2f}, stddev={stddev:.2f}, min={min_val}, max={max_val}, count={count}")

def test_large_dataset():
    pipeline = production_pipeline.DataPipeline(thread_count=8, batch_size=10000)

    # 1 million items
    import random
    data = [float(random.randint(1, 100)) for _ in range(1000000)]

    results, stats = pipeline.process_batched(data)

    print(f"\nLarge dataset (1M items):")
    print(f"  Processed: {stats.items_processed}")
    print(f"  Duration: {stats.duration_secs:.4f}s")
    print(f"  Throughput: {stats.items_processed / stats.duration_secs:.0f} items/sec")

if __name__ == "__main__":
    print("=" * 60)
    print("Production Pipeline Tests")
    print("=" * 60)

    test_pipeline_basic()
    test_pipeline_filtering()
    test_pipeline_error_handling()
    test_pipeline_batched()
    test_aggregate_pipeline()
    test_large_dataset()

    print("\n" + "=" * 60)
    print("All tests passed!")
    print("=" * 60)
