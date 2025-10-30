"""
Test basic async functionality with PyO3
"""
import asyncio
import pytest

# Import will work after building with: maturin develop
try:
    import async_basic
except ImportError:
    pytest.skip("Module not built yet. Run: maturin develop", allow_module_level=True)


@pytest.mark.asyncio
async def test_async_sleep():
    """Test basic async sleep function"""
    result = await async_basic.async_sleep(1)
    assert result == "Sleep completed"


@pytest.mark.asyncio
async def test_async_compute():
    """Test async computation"""
    result = await async_basic.async_compute(10)
    assert result == 55  # Sum of 1..10


@pytest.mark.asyncio
async def test_async_greet():
    """Test async greeting"""
    result = await async_basic.async_greet("World")
    assert result == "Hello, World!"


@pytest.mark.asyncio
async def test_async_divide():
    """Test async division with error handling"""
    result = await async_basic.async_divide(10.0, 2.0)
    assert result == 5.0


@pytest.mark.asyncio
async def test_async_divide_by_zero():
    """Test async division by zero raises error"""
    with pytest.raises(ValueError, match="Cannot divide by zero"):
        await async_basic.async_divide(10.0, 0.0)


@pytest.mark.asyncio
async def test_concurrent_execution():
    """Test running multiple async functions concurrently"""
    results = await asyncio.gather(
        async_basic.async_greet("Alice"),
        async_basic.async_greet("Bob"),
        async_basic.async_compute(5),
    )
    assert results == ["Hello, Alice!", "Hello, Bob!", 15]


if __name__ == "__main__":
    # Run a simple example
    async def main():
        print("Testing basic async operations...")

        result = await async_basic.async_sleep(1)
        print(f"Sleep result: {result}")

        result = await async_basic.async_compute(100)
        print(f"Sum of 1..100: {result}")

        result = await async_basic.async_greet("PyO3")
        print(f"Greeting: {result}")

        result = await async_basic.async_divide(42.0, 7.0)
        print(f"Division result: {result}")

    asyncio.run(main())
