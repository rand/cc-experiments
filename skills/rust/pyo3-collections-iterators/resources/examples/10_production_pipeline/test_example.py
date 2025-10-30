"""Test production data pipeline."""
import production_pipeline

def test_data_pipeline():
    pipeline = production_pipeline.DataPipeline()

    # Add records
    pipeline.add_record(1, 100.0, "A", 1000)
    pipeline.add_record(2, 200.0, "B", 2000)
    pipeline.add_record(3, 50.0, "A", 3000)
    pipeline.add_record(4, 300.0, "C", 4000)

    assert len(pipeline) == 4

def test_pipeline_filtering():
    pipeline = production_pipeline.DataPipeline()
    pipeline.add_record(1, 100.0, "A", 1000)
    pipeline.add_record(2, 200.0, "B", 2000)
    pipeline.add_record(3, 50.0, "A", 3000)

    # Filter value > 80
    pipeline.add_filter("value", 80.0)

    results = pipeline.execute(parallel=False)
    assert len(results) == 2  # Only 100 and 200 pass

def test_pipeline_transforms():
    pipeline = production_pipeline.DataPipeline()
    pipeline.add_record(1, 10.0, "A", 1000)
    pipeline.add_record(2, 20.0, "B", 2000)

    pipeline.add_transform("multiply", 2.0)

    results = pipeline.execute(parallel=False)
    assert results[0][1] == 20.0  # 10 * 2
    assert results[1][1] == 40.0  # 20 * 2

def test_statistics():
    pipeline = production_pipeline.DataPipeline()
    pipeline.add_record(1, 10.0, "A", 1000)
    pipeline.add_record(2, 20.0, "B", 2000)
    pipeline.add_record(3, 30.0, "C", 3000)

    stats = pipeline.statistics()
    assert stats["count"] == 3
    assert stats["sum"] == 60.0
    assert stats["mean"] == 20.0
    assert stats["min"] == 10.0
    assert stats["max"] == 30.0

def test_grouping():
    pipeline = production_pipeline.DataPipeline()
    pipeline.add_record(1, 100.0, "A", 1000)
    pipeline.add_record(2, 200.0, "B", 2000)
    pipeline.add_record(3, 150.0, "A", 3000)

    groups = pipeline.group_by_category()
    assert len(groups) == 2
    assert groups["A"] == [100.0, 150.0]
    assert groups["B"] == [200.0]

def test_time_series():
    data = [(1000, 10.0), (2000, 20.0), (3000, 30.0), (4000, 25.0), (5000, 35.0)]
    ts = production_pipeline.TimeSeriesProcessor(data)

    # Moving average with window=3
    ma = ts.moving_average(3)
    assert len(ma) == 3

    # Resample to 2000ms intervals
    resampled = ts.resample(2000)
    assert len(resampled) > 0

def test_anomaly_detection():
    # Create data with one outlier
    data = [(i, 10.0) for i in range(100)]
    data.append((100, 100.0))  # Outlier

    ts = production_pipeline.TimeSeriesProcessor(data)
    anomalies = ts.detect_anomalies(3.0)  # 3 std devs

    assert len(anomalies) > 0
    assert (100, 100.0) in anomalies

if __name__ == "__main__":
    test_data_pipeline()
    test_pipeline_filtering()
    test_pipeline_transforms()
    test_statistics()
    test_grouping()
    test_time_series()
    test_anomaly_detection()
    print("All tests passed!")
