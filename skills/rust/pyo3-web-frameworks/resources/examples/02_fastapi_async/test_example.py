"""
Test suite for fastapi_async PyO3 module.

Run with: pytest test_example.py -v
Build first: maturin develop
"""

import pytest
import asyncio
import fastapi_async


@pytest.mark.asyncio
async def test_fetch_data_async():
    """Test async data fetching."""
    result = await fastapi_async.fetch_data_async(42, 10)
    assert result == "Data for ID 42"

    result = await fastapi_async.fetch_data_async(100, 5)
    assert result == "Data for ID 100"


@pytest.mark.asyncio
async def test_process_batch_async():
    """Test concurrent batch processing."""
    items = ["hello", "world", "test"]
    results = await fastapi_async.process_batch_async(items)
    assert results == ["HELLO", "WORLD", "TEST"]

    # Empty batch
    results = await fastapi_async.process_batch_async([])
    assert results == []


@pytest.mark.asyncio
async def test_compute_with_progress():
    """Test async computation."""
    result = await fastapi_async.compute_with_progress(100)
    assert result == sum(range(100))

    result = await fastapi_async.compute_with_progress(1000)
    assert result == sum(range(1000))


@pytest.mark.asyncio
async def test_api_call_with_timeout():
    """Test async API call with timeout."""
    # Should succeed (timeout longer than processing time)
    result = await fastapi_async.api_call_with_timeout("/api/test", 200)
    assert "Response from /api/test" in result

    # Should timeout
    with pytest.raises(RuntimeError, match="timeout"):
        await fastapi_async.api_call_with_timeout("/api/slow", 10)


@pytest.mark.asyncio
async def test_aggregate_async():
    """Test async data aggregation."""
    sources = ["source1", "source2", "source3"]
    result = await fastapi_async.aggregate_async(sources)
    assert "Data from source1" in result
    assert "Data from source2" in result
    assert "Data from source3" in result


@pytest.mark.asyncio
async def test_async_counter():
    """Test async counter with shared state."""
    counter = fastapi_async.AsyncCounter()

    # Test increment
    count = await counter.increment_async()
    assert count == 1

    count = await counter.increment_async()
    assert count == 2

    # Test get
    count = await counter.get_count_async()
    assert count == 2

    # Test reset
    await counter.reset_async()
    count = await counter.get_count_async()
    assert count == 0


@pytest.mark.asyncio
async def test_async_counter_concurrent():
    """Test async counter with concurrent increments."""
    counter = fastapi_async.AsyncCounter()

    # Run 10 concurrent increments
    tasks = [counter.increment_async() for _ in range(10)]
    results = await asyncio.gather(*tasks)

    # Should have values 1-10 in some order
    assert sorted(results) == list(range(1, 11))

    final_count = await counter.get_count_async()
    assert final_count == 10


@pytest.mark.asyncio
async def test_process_with_concurrency():
    """Test batch processing with concurrency limit."""
    items = [1.0, 2.0, 3.0, 4.0, 5.0]
    results = await fastapi_async.process_with_concurrency(items, 2)
    assert results == [1.0, 4.0, 9.0, 16.0, 25.0]

    # Single concurrent task
    results = await fastapi_async.process_with_concurrency([2.0], 1)
    assert results == [4.0]


@pytest.mark.asyncio
async def test_fetch_with_retry():
    """Test async retry logic."""
    # Should succeed after retries
    result = await fastapi_async.fetch_with_retry("http://example.com", 5)
    assert "Success" in result
    assert "after" in result

    # Should fail after max retries
    with pytest.raises(RuntimeError, match="Failed after"):
        await fastapi_async.fetch_with_retry("http://always-fails.com", 2)


@pytest.mark.asyncio
async def test_concurrent_operations():
    """Test multiple async operations running concurrently."""
    # Run multiple operations in parallel
    task1 = fastapi_async.fetch_data_async(1, 20)
    task2 = fastapi_async.compute_with_progress(50)
    task3 = fastapi_async.aggregate_async(["a", "b"])

    results = await asyncio.gather(task1, task2, task3)

    assert results[0] == "Data for ID 1"
    assert results[1] == sum(range(50))
    assert "Data from a" in results[2]


def test_fastapi_integration():
    """Test integration with FastAPI."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    app = FastAPI()

    @app.get("/fetch/{id}")
    async def fetch_endpoint(id: int):
        result = await fastapi_async.fetch_data_async(id, 10)
        return {"data": result}

    @app.post("/process")
    async def process_endpoint(items: list[str]):
        results = await fastapi_async.process_batch_async(items)
        return {"results": results}

    client = TestClient(app)

    # Test fetch endpoint
    response = client.get("/fetch/42")
    assert response.status_code == 200
    assert response.json()["data"] == "Data for ID 42"

    # Test process endpoint
    response = client.post("/process", json=["hello", "world"])
    assert response.status_code == 200
    assert response.json()["results"] == ["HELLO", "WORLD"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
