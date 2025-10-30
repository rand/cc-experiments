"""Test suite for channel-based communication patterns."""
import channels

def test_producer_consumer():
    items = [float(x) for x in range(100)]
    results = channels.producer_consumer(items, worker_count=4)
    expected = [x * x for x in items]
    assert sorted(results) == sorted(expected)
    print("Producer-consumer: OK")

def test_pipeline():
    numbers = list(range(1, 11))
    results = channels.pipeline_processing(numbers)
    # Filter evens, square, convert to string
    expected = [str(x * x) for x in numbers if x % 2 == 0]
    assert sorted(results) == sorted(expected)
    print("Pipeline: OK")

def test_fan_out_fan_in():
    tasks = [float(x) for x in range(10)]
    result = channels.fan_out_fan_in(tasks, workers=4)
    expected = sum(x * x for x in tasks)
    assert abs(result - expected) < 0.01
    print("Fan-out/Fan-in: OK")

def test_broadcast():
    results = channels.broadcast_compute(10.0, worker_count=5)
    assert len(results) == 5
    assert results[0] == 10.0
    assert results[4] == 50.0
    print("Broadcast: OK")

if __name__ == "__main__":
    print("=" * 60)
    print("Channel Communication Tests")
    print("=" * 60)
    test_producer_consumer()
    test_pipeline()
    test_fan_out_fan_in()
    test_broadcast()
    print("All tests passed!")
