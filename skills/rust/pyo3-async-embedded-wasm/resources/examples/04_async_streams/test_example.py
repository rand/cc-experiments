"""
Test async stream operations with PyO3
"""
import asyncio
import time
import pytest

try:
    import async_streams
except ImportError:
    pytest.skip("Module not built yet. Run: maturin develop", allow_module_level=True)


@pytest.mark.asyncio
async def test_async_range():
    """Test basic async range stream"""
    result = await async_streams.async_range(0, 10)
    assert result == list(range(0, 10))


@pytest.mark.asyncio
async def test_async_map():
    """Test stream mapping"""
    data = [1, 2, 3, 4, 5]
    result = await async_streams.async_map(data, 3)
    assert result == [3, 6, 9, 12, 15]


@pytest.mark.asyncio
async def test_async_filter():
    """Test stream filtering"""
    data = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    result = await async_streams.async_filter(data, 5)
    assert result == [5, 6, 7, 8, 9, 10]


@pytest.mark.asyncio
async def test_async_delayed_stream():
    """Test stream with delays"""
    start = time.time()
    result = await async_streams.async_delayed_stream(5, 10)
    duration = time.time() - start

    assert len(result) == 5
    assert result == [0, 1, 2, 3, 4]
    # Should take at least 40ms (5 items * 10ms - 1)
    assert duration >= 0.04


@pytest.mark.asyncio
async def test_async_backpressure():
    """Test backpressure handling"""
    data = list(range(20))
    # Small buffer (5), slow processing (10ms)
    result = await async_streams.async_backpressure(data, 5, 5)
    assert len(result) == 20
    assert result == [x * 2 for x in data]


@pytest.mark.asyncio
async def test_async_chunks():
    """Test stream chunking"""
    data = list(range(10))
    result = await async_streams.async_chunks(data, 3)
    assert len(result) == 4
    assert result[0] == [0, 1, 2]
    assert result[1] == [3, 4, 5]
    assert result[2] == [6, 7, 8]
    assert result[3] == [9]


@pytest.mark.asyncio
async def test_async_fold():
    """Test stream folding/accumulation"""
    data = [1, 2, 3, 4, 5]
    result = await async_streams.async_fold(data)
    assert result == 15


@pytest.mark.asyncio
async def test_async_merge_streams():
    """Test merging multiple streams"""
    stream1 = [1, 2, 3]
    stream2 = [4, 5, 6]
    result = await async_streams.async_merge_streams(stream1, stream2)
    # Order may vary, but all elements should be present
    assert sorted(result) == [1, 2, 3, 4, 5, 6]


@pytest.mark.asyncio
async def test_async_stream_errors():
    """Test error handling in streams"""
    data = [1, 2, 3, 4, 5]
    result = await async_streams.async_stream_errors(data, 3)
    # Should have processed all except where error occurred
    assert len(result) == 5


@pytest.mark.asyncio
async def test_async_rate_limited():
    """Test rate-limited stream"""
    start = time.time()
    result = await async_streams.async_rate_limited(5, 10)  # 10 items per second
    duration = time.time() - start

    assert len(result) == 5
    # Should take at least 400ms (5 items at 10/sec = 100ms each - 1)
    assert duration >= 0.4


if __name__ == "__main__":
    async def main():
        print("Testing async stream operations...")

        print("\n1. Basic range:")
        result = await async_streams.async_range(0, 5)
        print(f"   Range 0..5: {result}")

        print("\n2. Map (multiply by 2):")
        result = await async_streams.async_map([1, 2, 3, 4, 5], 2)
        print(f"   Mapped: {result}")

        print("\n3. Filter (>= 3):")
        result = await async_streams.async_filter([1, 2, 3, 4, 5], 3)
        print(f"   Filtered: {result}")

        print("\n4. Delayed stream (3 items, 50ms delay):")
        start = time.time()
        result = await async_streams.async_delayed_stream(3, 50)
        duration = time.time() - start
        print(f"   Result: {result}")
        print(f"   Duration: {duration:.2f}s")

        print("\n5. Backpressure (10 items, buffer=3, delay=5ms):")
        data = list(range(10))
        result = await async_streams.async_backpressure(data, 3, 5)
        print(f"   Processed {len(result)} items")

        print("\n6. Chunks (size=3):")
        result = await async_streams.async_chunks(list(range(10)), 3)
        print(f"   Chunks: {result}")

        print("\n7. Fold (sum):")
        result = await async_streams.async_fold([1, 2, 3, 4, 5])
        print(f"   Sum: {result}")

        print("\n8. Merge streams:")
        result = await async_streams.async_merge_streams([1, 2, 3], [4, 5, 6])
        print(f"   Merged: {result}")

        print("\n9. Rate limited (5 items at 10/sec):")
        start = time.time()
        result = await async_streams.async_rate_limited(5, 10)
        duration = time.time() - start
        print(f"   Result: {result}")
        print(f"   Duration: {duration:.2f}s")

    asyncio.run(main())
