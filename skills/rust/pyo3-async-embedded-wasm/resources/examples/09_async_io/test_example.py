import asyncio
import tempfile
import pytest

try:
    import async_io
except ImportError:
    pytest.skip("Module not built. Run: maturin develop", allow_module_level=True)


@pytest.mark.asyncio
async def test_async_write_read():
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
        path = f.name

    content = "Hello from async Rust!"
    await async_io.async_write_file(path, content)
    result = await async_io.async_read_file(path)

    assert result == content

    import os

    os.unlink(path)


@pytest.mark.asyncio
async def test_async_list_dir():
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        entries = await async_io.async_list_dir(tmpdir)
        assert isinstance(entries, list)


if __name__ == "__main__":

    async def main():
        print("Async I/O Example\n")

        # File operations
        print("1. File operations:")
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            path = f.name

        content = "Hello from async Rust I/O!"
        result = await async_io.async_write_file(path, content)
        print(f"   Write: {result}")

        result = await async_io.async_read_file(path)
        print(f"   Read: {result}")

        import os

        os.unlink(path)

        # Directory listing
        print("\n2. Directory listing:")
        entries = await async_io.async_list_dir(".")
        print(f"   Found {len(entries)} entries in current directory")

        print("\nNote: HTTP example requires network connectivity")

    asyncio.run(main())
