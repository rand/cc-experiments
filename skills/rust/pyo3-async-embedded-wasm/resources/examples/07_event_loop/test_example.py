import asyncio
import pytest

try:
    import event_loop
except ImportError:
    pytest.skip("Module not built. Run: maturin develop", allow_module_level=True)


@pytest.mark.asyncio
async def test_event_loop():
    loop = event_loop.EventLoop()
    loop.emit("test_event")
    # Basic smoke test
    assert loop is not None


@pytest.mark.asyncio
async def test_schedule_task():
    result = await event_loop.schedule_task(10, "task1")
    assert "task1" in result


if __name__ == "__main__":

    async def main():
        print("Event Loop Example\n")

        # Schedule tasks
        print("1. Scheduling tasks:")
        result = await event_loop.schedule_task(100, "task_1")
        print(f"   {result}")

        result = await event_loop.schedule_task(50, "task_2")
        print(f"   {result}")

        print("\n2. Event loop with pub/sub:")
        loop = event_loop.EventLoop()

        # Emit events in background
        async def emit_events():
            await asyncio.sleep(0.1)
            for i in range(5):
                loop.emit(f"event_{i}")
                await asyncio.sleep(0.05)

        emit_task = asyncio.create_task(emit_events())
        events = await loop.subscribe()
        await emit_task

        print(f"   Received events: {events}")

    asyncio.run(main())
