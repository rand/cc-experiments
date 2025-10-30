#!/usr/bin/env python3
"""
Async Runtime Management for pyo3-asyncio Integration

Helper script for managing async runtimes (Tokio <-> asyncio) with pyo3-asyncio.
Provides initialization, bridging, task spawning, error handling, and benchmarking.

Usage:
    python async_runtime.py init --runtime tokio
    python async_runtime.py test --async-fn test.py::async_function
    python async_runtime.py benchmark --tasks 100 --duration 10
    python async_runtime.py config --show
"""

import argparse
import asyncio
import inspect
import json
import sys
import time
import traceback
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Coroutine, Dict, List, Optional, Tuple
from importlib import import_module


class RuntimeType(Enum):
    """Supported async runtime types."""
    TOKIO = "tokio"
    ASYNCIO = "asyncio"
    TOKIO_CURRENT_THREAD = "tokio-current-thread"
    TOKIO_MULTI_THREAD = "tokio-multi-thread"


@dataclass
class RuntimeConfig:
    """Configuration for async runtime."""
    runtime_type: RuntimeType = RuntimeType.TOKIO_MULTI_THREAD
    worker_threads: int = 4
    max_blocking_threads: int = 512
    thread_stack_size: int = 2 * 1024 * 1024  # 2MB
    enable_io: bool = True
    enable_time: bool = True
    event_interval: int = 61
    max_io_events_per_tick: int = 1024

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary."""
        return {
            "runtime_type": self.runtime_type.value,
            "worker_threads": self.worker_threads,
            "max_blocking_threads": self.max_blocking_threads,
            "thread_stack_size": self.thread_stack_size,
            "enable_io": self.enable_io,
            "enable_time": self.enable_time,
            "event_interval": self.event_interval,
            "max_io_events_per_tick": self.max_io_events_per_tick,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RuntimeConfig":
        """Create config from dictionary."""
        runtime_type = RuntimeType(data.get("runtime_type", "tokio-multi-thread"))
        return cls(
            runtime_type=runtime_type,
            worker_threads=data.get("worker_threads", 4),
            max_blocking_threads=data.get("max_blocking_threads", 512),
            thread_stack_size=data.get("thread_stack_size", 2 * 1024 * 1024),
            enable_io=data.get("enable_io", True),
            enable_time=data.get("enable_time", True),
            event_interval=data.get("event_interval", 61),
            max_io_events_per_tick=data.get("max_io_events_per_tick", 1024),
        )


@dataclass
class TaskStats:
    """Statistics for async task execution."""
    total_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    total_time: float = 0.0
    min_time: float = float('inf')
    max_time: float = 0.0
    errors: List[str] = field(default_factory=list)

    def record_success(self, duration: float):
        """Record successful task completion."""
        self.completed_tasks += 1
        self.total_time += duration
        self.min_time = min(self.min_time, duration)
        self.max_time = max(self.max_time, duration)

    def record_failure(self, error: str):
        """Record task failure."""
        self.failed_tasks += 1
        self.errors.append(error)

    def avg_time(self) -> float:
        """Calculate average task time."""
        if self.completed_tasks == 0:
            return 0.0
        return self.total_time / self.completed_tasks

    def summary(self) -> Dict[str, Any]:
        """Get summary statistics."""
        return {
            "total": self.total_tasks,
            "completed": self.completed_tasks,
            "failed": self.failed_tasks,
            "success_rate": self.completed_tasks / self.total_tasks if self.total_tasks > 0 else 0.0,
            "avg_time_ms": self.avg_time() * 1000,
            "min_time_ms": self.min_time * 1000 if self.min_time != float('inf') else 0,
            "max_time_ms": self.max_time * 1000,
            "total_time_s": self.total_time,
            "error_count": len(self.errors),
        }


class AsyncRuntimeManager:
    """Manager for pyo3-asyncio runtime operations."""

    def __init__(self, config: RuntimeConfig):
        self.config = config
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self.stats = TaskStats()

    def initialize(self) -> bool:
        """Initialize the async runtime."""
        try:
            # Get or create event loop
            try:
                self.loop = asyncio.get_running_loop()
                print(f"Using existing event loop: {self.loop}")
            except RuntimeError:
                self.loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self.loop)
                print(f"Created new event loop: {self.loop}")

            # Configure loop policy for better compatibility
            if sys.platform == 'win32':
                # Use ProactorEventLoop on Windows for better subprocess support
                asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

            print(f"Runtime initialized: {self.config.runtime_type.value}")
            print(f"Worker threads: {self.config.worker_threads}")
            print(f"Event loop: {type(self.loop).__name__}")

            return True
        except Exception as e:
            print(f"Failed to initialize runtime: {e}")
            traceback.print_exc()
            return False

    async def spawn_task(self, coro: Coroutine) -> Any:
        """Spawn an async task and return its result."""
        start_time = time.time()
        self.stats.total_tasks += 1

        try:
            result = await coro
            duration = time.time() - start_time
            self.stats.record_success(duration)
            return result
        except Exception as e:
            error_msg = f"{type(e).__name__}: {str(e)}"
            self.stats.record_failure(error_msg)
            raise

    async def spawn_tasks(self, coros: List[Coroutine]) -> List[Any]:
        """Spawn multiple async tasks concurrently."""
        tasks = [asyncio.create_task(self.spawn_task(coro)) for coro in coros]
        return await asyncio.gather(*tasks, return_exceptions=True)

    def run_until_complete(self, coro: Coroutine) -> Any:
        """Run a coroutine until completion."""
        if self.loop is None:
            raise RuntimeError("Runtime not initialized")

        try:
            # Check if we're already in an event loop
            try:
                asyncio.get_running_loop()
                # Already in a loop, create a task
                return asyncio.ensure_future(coro)
            except RuntimeError:
                # Not in a loop, run until complete
                return self.loop.run_until_complete(coro)
        except KeyboardInterrupt:
            print("\nInterrupted by user")
            return None

    def shutdown(self):
        """Shutdown the runtime gracefully."""
        if self.loop is not None and not self.loop.is_closed():
            # Cancel all pending tasks
            pending = asyncio.all_tasks(self.loop)
            for task in pending:
                task.cancel()

            # Wait for tasks to be cancelled
            if pending:
                self.loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))

            # Close the loop
            self.loop.close()
            print("Runtime shutdown complete")


class AsyncFunctionTester:
    """Test harness for async functions."""

    def __init__(self, runtime_manager: AsyncRuntimeManager):
        self.runtime = runtime_manager

    def load_function(self, function_spec: str) -> Tuple[Callable, Dict[str, Any]]:
        """
        Load an async function from a module spec.

        Format: module.path::function_name or file.py::function_name
        """
        if "::" not in function_spec:
            raise ValueError(f"Invalid function spec: {function_spec}. Expected format: module::function")

        module_path, func_name = function_spec.split("::", 1)

        # Handle file path
        if module_path.endswith(".py"):
            module_path = module_path[:-3]
            spec_path = Path(module_path).resolve()

            # Add parent directory to sys.path
            parent_dir = str(spec_path.parent)
            if parent_dir not in sys.path:
                sys.path.insert(0, parent_dir)

            module_name = spec_path.stem
            module = import_module(module_name)
        else:
            # Import as module
            module = import_module(module_path)

        # Get function
        if not hasattr(module, func_name):
            raise AttributeError(f"Module {module_path} has no function {func_name}")

        func = getattr(module, func_name)

        # Verify it's async
        if not asyncio.iscoroutinefunction(func):
            raise TypeError(f"Function {func_name} is not an async function")

        # Get function signature
        sig = inspect.signature(func)
        params = {
            name: {
                "type": str(param.annotation) if param.annotation != inspect.Parameter.empty else "Any",
                "default": param.default if param.default != inspect.Parameter.empty else None,
            }
            for name, param in sig.parameters.items()
        }

        return func, params

    async def test_function(self, func: Callable, args: List[Any] = None, kwargs: Dict[str, Any] = None) -> Dict[str, Any]:
        """Test an async function with given arguments."""
        args = args or []
        kwargs = kwargs or {}

        start_time = time.time()

        try:
            result = await func(*args, **kwargs)
            duration = time.time() - start_time

            return {
                "success": True,
                "result": result,
                "duration_ms": duration * 1000,
                "error": None,
            }
        except Exception as e:
            duration = time.time() - start_time

            return {
                "success": False,
                "result": None,
                "duration_ms": duration * 1000,
                "error": {
                    "type": type(e).__name__,
                    "message": str(e),
                    "traceback": traceback.format_exc(),
                },
            }


class AsyncBenchmark:
    """Benchmark harness for async operations."""

    def __init__(self, runtime_manager: AsyncRuntimeManager):
        self.runtime = runtime_manager

    async def simple_task(self, task_id: int, delay: float = 0.001) -> int:
        """Simple async task for benchmarking."""
        await asyncio.sleep(delay)
        return task_id

    async def io_task(self, task_id: int) -> int:
        """IO-bound async task."""
        # Simulate IO operation
        await asyncio.sleep(0.01)
        return task_id * 2

    async def cpu_task(self, task_id: int, iterations: int = 1000) -> int:
        """CPU-bound task (still async for testing)."""
        result = 0
        for i in range(iterations):
            result += i
        await asyncio.sleep(0)  # Yield control
        return result

    async def run_benchmark(self, task_count: int, duration: float, task_type: str = "simple") -> Dict[str, Any]:
        """Run benchmark with specified parameters."""
        print(f"Starting benchmark: {task_count} tasks, {duration}s duration, type={task_type}")

        # Select task function
        task_func = {
            "simple": self.simple_task,
            "io": self.io_task,
            "cpu": self.cpu_task,
        }.get(task_type, self.simple_task)

        start_time = time.time()
        completed = 0

        # Run tasks until duration expires
        while time.time() - start_time < duration:
            batch_size = min(task_count, 100)  # Process in batches
            coros = [task_func(i) for i in range(batch_size)]

            await self.runtime.spawn_tasks(coros)
            completed += batch_size

        total_duration = time.time() - start_time

        results = {
            "task_type": task_type,
            "total_tasks": completed,
            "duration_s": total_duration,
            "tasks_per_second": completed / total_duration,
            "avg_task_time_ms": (total_duration / completed) * 1000 if completed > 0 else 0,
            "stats": self.runtime.stats.summary(),
        }

        return results


def init_command(args):
    """Initialize async runtime."""
    runtime_type = RuntimeType(args.runtime)
    config = RuntimeConfig(
        runtime_type=runtime_type,
        worker_threads=args.threads,
    )

    manager = AsyncRuntimeManager(config)

    if manager.initialize():
        print("\nRuntime initialized successfully!")
        print(f"Configuration: {json.dumps(config.to_dict(), indent=2)}")

        # Save config
        config_path = Path(".async_runtime_config.json")
        config_path.write_text(json.dumps(config.to_dict(), indent=2))
        print(f"\nConfiguration saved to: {config_path}")

        manager.shutdown()
        return 0
    else:
        print("\nRuntime initialization failed!")
        return 1


def test_command(args):
    """Test an async function."""
    config = load_config()
    manager = AsyncRuntimeManager(config)

    if not manager.initialize():
        print("Failed to initialize runtime")
        return 1

    tester = AsyncFunctionTester(manager)

    try:
        print(f"Loading function: {args.async_fn}")
        func, params = tester.load_function(args.async_fn)

        print(f"\nFunction signature:")
        print(f"  Name: {func.__name__}")
        print(f"  Parameters: {json.dumps(params, indent=4)}")

        # Run test
        print("\nRunning test...")
        result = manager.run_until_complete(tester.test_function(func))

        print("\nTest results:")
        print(json.dumps(result, indent=2, default=str))

        return 0 if result["success"] else 1

    except Exception as e:
        print(f"\nTest failed: {e}")
        traceback.print_exc()
        return 1
    finally:
        manager.shutdown()


def benchmark_command(args):
    """Run async benchmark."""
    config = load_config()
    manager = AsyncRuntimeManager(config)

    if not manager.initialize():
        print("Failed to initialize runtime")
        return 1

    benchmark = AsyncBenchmark(manager)

    try:
        result = manager.run_until_complete(
            benchmark.run_benchmark(args.tasks, args.duration, args.type)
        )

        print("\nBenchmark Results:")
        print("=" * 60)
        print(json.dumps(result, indent=2))
        print("=" * 60)

        return 0

    except Exception as e:
        print(f"\nBenchmark failed: {e}")
        traceback.print_exc()
        return 1
    finally:
        manager.shutdown()


def config_command(args):
    """Show or update configuration."""
    config_path = Path(".async_runtime_config.json")

    if args.show:
        if config_path.exists():
            config_data = json.loads(config_path.read_text())
            print("Current configuration:")
            print(json.dumps(config_data, indent=2))
        else:
            print("No configuration file found. Run 'init' first.")
            return 1

    return 0


def load_config() -> RuntimeConfig:
    """Load configuration from file or use defaults."""
    config_path = Path(".async_runtime_config.json")

    if config_path.exists():
        config_data = json.loads(config_path.read_text())
        return RuntimeConfig.from_dict(config_data)
    else:
        return RuntimeConfig()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Async Runtime Management for pyo3-asyncio",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Init command
    init_parser = subparsers.add_parser("init", help="Initialize async runtime")
    init_parser.add_argument(
        "--runtime",
        choices=["tokio", "asyncio", "tokio-current-thread", "tokio-multi-thread"],
        default="tokio-multi-thread",
        help="Runtime type to use",
    )
    init_parser.add_argument(
        "--threads",
        type=int,
        default=4,
        help="Number of worker threads",
    )

    # Test command
    test_parser = subparsers.add_parser("test", help="Test an async function")
    test_parser.add_argument(
        "--async-fn",
        required=True,
        help="Async function to test (format: module::function or file.py::function)",
    )

    # Benchmark command
    bench_parser = subparsers.add_parser("benchmark", help="Run async benchmark")
    bench_parser.add_argument(
        "--tasks",
        type=int,
        default=100,
        help="Number of tasks per batch",
    )
    bench_parser.add_argument(
        "--duration",
        type=float,
        default=10.0,
        help="Benchmark duration in seconds",
    )
    bench_parser.add_argument(
        "--type",
        choices=["simple", "io", "cpu"],
        default="simple",
        help="Task type to benchmark",
    )

    # Config command
    config_parser = subparsers.add_parser("config", help="Show or update configuration")
    config_parser.add_argument(
        "--show",
        action="store_true",
        help="Show current configuration",
    )

    args = parser.parse_args()

    if args.command == "init":
        return init_command(args)
    elif args.command == "test":
        return test_command(args)
    elif args.command == "benchmark":
        return benchmark_command(args)
    elif args.command == "config":
        return config_command(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
