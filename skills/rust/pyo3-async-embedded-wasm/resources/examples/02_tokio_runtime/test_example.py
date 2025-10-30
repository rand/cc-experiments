"""
Test Tokio runtime integration with PyO3
"""
import asyncio
import pytest

try:
    import tokio_runtime
except ImportError:
    pytest.skip("Module not built yet. Run: maturin develop", allow_module_level=True)


@pytest.mark.asyncio
async def test_spawn_background_task():
    """Test spawning background tasks"""
    result = await tokio_runtime.spawn_background_task(3, 10)
    assert "Spawned background task" in result
    assert "3 iterations" in result


@pytest.mark.asyncio
async def test_concurrent_tasks():
    """Test concurrent task execution"""
    urls = [
        "https://api.example.com/1",
        "https://api.example.com/2",
        "https://api.example.com/3",
    ]
    results = await tokio_runtime.concurrent_tasks(urls)
    assert len(results) == 3
    assert all("Fetched:" in r for r in results)


@pytest.mark.asyncio
async def test_shared_counter():
    """Test shared state with Arc<Mutex>"""
    result = await tokio_runtime.shared_counter_demo(10)
    assert result == 10


@pytest.mark.asyncio
async def test_timeout_success():
    """Test timeout with operation completing in time"""
    result = await tokio_runtime.with_timeout(100, 200)
    assert result == "Operation completed"


@pytest.mark.asyncio
async def test_timeout_failure():
    """Test timeout with operation exceeding time limit"""
    with pytest.raises(TimeoutError, match="Operation timed out"):
        await tokio_runtime.with_timeout(200, 100)


@pytest.mark.asyncio
async def test_channel_communication():
    """Test channel-based communication"""
    messages = await tokio_runtime.channel_demo(5)
    assert len(messages) == 5
    assert messages[0] == "Message 0"
    assert messages[4] == "Message 4"


@pytest.mark.asyncio
async def test_concurrent_operations():
    """Test running multiple operations concurrently"""
    results = await asyncio.gather(
        tokio_runtime.shared_counter_demo(5),
        tokio_runtime.channel_demo(3),
        tokio_runtime.with_timeout(50, 100),
    )
    assert results[0] == 5  # counter
    assert len(results[1]) == 3  # messages
    assert results[2] == "Operation completed"  # timeout


if __name__ == "__main__":
    async def main():
        print("Testing Tokio runtime integration...")

        print("\n1. Spawning background task:")
        result = await tokio_runtime.spawn_background_task(3, 100)
        print(f"   {result}")

        print("\n2. Concurrent tasks:")
        urls = ["https://api.github.com", "https://api.python.org", "https://crates.io"]
        results = await tokio_runtime.concurrent_tasks(urls)
        for r in results:
            print(f"   {r}")

        print("\n3. Shared counter:")
        count = await tokio_runtime.shared_counter_demo(10)
        print(f"   Final count: {count}")

        print("\n4. Timeout (success):")
        try:
            result = await tokio_runtime.with_timeout(50, 100)
            print(f"   {result}")
        except TimeoutError as e:
            print(f"   Timeout: {e}")

        print("\n5. Timeout (failure):")
        try:
            result = await tokio_runtime.with_timeout(200, 100)
            print(f"   {result}")
        except TimeoutError as e:
            print(f"   Timeout: {e}")

        print("\n6. Channel communication:")
        messages = await tokio_runtime.channel_demo(5)
        print(f"   Received {len(messages)} messages")
        for msg in messages:
            print(f"   - {msg}")

    asyncio.run(main())
