import asyncio
import pytest

try:
    import production_service
except ImportError:
    pytest.skip("Module not built. Run: maturin develop", allow_module_level=True)

@pytest.mark.asyncio
async def test_service():
    service = production_service.AsyncService(max_concurrent=5)

    result = await service.process_request([1, 2, 3, 4, 5])
    assert result == [2, 4, 6, 8, 10]

    stats = await service.get_stats()
    assert stats["requests"] == 1
    assert stats["successes"] == 1

if __name__ == "__main__":
    async def main():
        service = production_service.AsyncService(max_concurrent=10)

        # Process requests
        results = await asyncio.gather(
            service.process_request([1, 2, 3]),
            service.process_request([4, 5, 6]),
            service.process_request([7, 8, 9]),
        )

        print("Results:", results)

        stats = await service.get_stats()
        print("Stats:", stats)

        health = await service.health_check()
        print("Health:", health)

    asyncio.run(main())
