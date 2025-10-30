import asyncio
import pytest

try:
    import concurrent_tasks
except ImportError:
    pytest.skip("Module not built. Run: maturin develop", allow_module_level=True)

@pytest.mark.asyncio
async def test_parallel_execute():
    results = await concurrent_tasks.parallel_execute(5, 10)
    assert len(results) == 5

@pytest.mark.asyncio
async def test_race_tasks():
    result = await concurrent_tasks.race_tasks([100, 50, 200])
    assert "Task 1 won" in result

if __name__ == "__main__":
    asyncio.run(concurrent_tasks.parallel_execute(3, 10))
