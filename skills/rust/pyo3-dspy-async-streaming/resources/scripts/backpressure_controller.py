#!/usr/bin/env python3
"""
Backpressure Controller for Streaming Pipelines

Manages backpressure in streaming pipelines with adaptive flow control,
queue monitoring, circuit breaker integration, and multiple drop strategies.
"""

import argparse
import asyncio
import json
import sys
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple


class DropStrategy(Enum):
    """Queue overflow drop strategies"""
    DROP_OLDEST = "drop-oldest"
    DROP_NEWEST = "drop-newest"
    DROP_ON_FULL = "drop-on-full"
    BACKPRESSURE = "backpressure"


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half-open"


@dataclass
class BackpressureMetrics:
    """Metrics for backpressure monitoring"""
    queue_depth: int = 0
    max_queue_depth: int = 0
    items_dropped: int = 0
    items_processed: int = 0
    total_latency_ms: float = 0.0
    avg_latency_ms: float = 0.0
    current_rate: float = 0.0
    backpressure_events: int = 0
    circuit_state: str = "closed"
    last_updated: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary"""
        return {
            "queue_depth": self.queue_depth,
            "max_queue_depth": self.max_queue_depth,
            "items_dropped": self.items_dropped,
            "items_processed": self.items_processed,
            "total_latency_ms": round(self.total_latency_ms, 2),
            "avg_latency_ms": round(self.avg_latency_ms, 2),
            "current_rate": round(self.current_rate, 2),
            "backpressure_events": self.backpressure_events,
            "circuit_state": self.circuit_state,
            "last_updated": self.last_updated,
        }


@dataclass
class BackpressureConfig:
    """Configuration for backpressure controller"""
    max_queue_size: int = 1000
    target_latency_ms: float = 100.0
    strategy: DropStrategy = DropStrategy.BACKPRESSURE
    adaptive_rate: bool = True
    min_rate: float = 1.0
    max_rate: float = 1000.0
    rate_increase_factor: float = 1.2
    rate_decrease_factor: float = 0.8
    circuit_failure_threshold: int = 5
    circuit_timeout_s: float = 30.0
    high_water_mark: float = 0.8
    low_water_mark: float = 0.5


class CircuitBreaker:
    """Circuit breaker for backpressure control"""

    def __init__(self, failure_threshold: int, timeout_s: float):
        self.failure_threshold = failure_threshold
        self.timeout_s = timeout_s
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = 0.0
        self.success_count = 0

    def record_success(self) -> None:
        """Record successful operation"""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= 3:
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                self.success_count = 0
        elif self.state == CircuitState.CLOSED:
            self.failure_count = max(0, self.failure_count - 1)

    def record_failure(self) -> None:
        """Record failed operation"""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN

    def can_proceed(self) -> bool:
        """Check if operation can proceed"""
        if self.state == CircuitState.CLOSED:
            return True

        if self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time >= self.timeout_s:
                self.state = CircuitState.HALF_OPEN
                self.success_count = 0
                return True
            return False

        return True  # HALF_OPEN allows attempts

    def get_state(self) -> str:
        """Get current circuit state"""
        return self.state.value


class AdaptiveRateLimiter:
    """Adaptive rate limiter based on queue depth and latency"""

    def __init__(self, config: BackpressureConfig):
        self.config = config
        self.current_rate = config.max_rate
        self.last_adjustment = time.time()
        self.latency_samples: deque = deque(maxlen=100)

    def adjust_rate(self, queue_depth: int, latency_ms: float) -> float:
        """Adjust rate based on current conditions"""
        now = time.time()
        if now - self.last_adjustment < 1.0:
            return self.current_rate

        self.latency_samples.append(latency_ms)
        avg_latency = sum(self.latency_samples) / len(self.latency_samples)

        queue_ratio = queue_depth / self.config.max_queue_size

        # Decrease rate if queue is filling or latency is high
        if queue_ratio > self.config.high_water_mark or avg_latency > self.config.target_latency_ms:
            self.current_rate *= self.config.rate_decrease_factor
        # Increase rate if queue is draining and latency is acceptable
        elif queue_ratio < self.config.low_water_mark and avg_latency < self.config.target_latency_ms * 0.8:
            self.current_rate *= self.config.rate_increase_factor

        # Clamp to min/max
        self.current_rate = max(
            self.config.min_rate,
            min(self.config.max_rate, self.current_rate)
        )

        self.last_adjustment = now
        return self.current_rate

    def get_delay(self) -> float:
        """Get delay between operations based on current rate"""
        return 1.0 / self.current_rate if self.current_rate > 0 else 0.0


class BackpressureController:
    """Main backpressure controller"""

    def __init__(self, name: str, config: BackpressureConfig):
        self.name = name
        self.config = config
        self.queue: deque = deque(maxlen=config.max_queue_size)
        self.metrics = BackpressureMetrics(max_queue_depth=config.max_queue_size)
        self.circuit_breaker = CircuitBreaker(
            config.circuit_failure_threshold,
            config.circuit_timeout_s
        )
        self.rate_limiter = AdaptiveRateLimiter(config)
        self.processing_times: deque = deque(maxlen=100)

    async def enqueue(self, item: Any) -> bool:
        """Enqueue item with backpressure handling"""
        if not self.circuit_breaker.can_proceed():
            self.metrics.backpressure_events += 1
            return False

        if len(self.queue) >= self.config.max_queue_size:
            return self._handle_overflow(item)

        self.queue.append((item, time.time()))
        self.metrics.queue_depth = len(self.queue)
        return True

    def _handle_overflow(self, item: Any) -> bool:
        """Handle queue overflow based on strategy"""
        if self.config.strategy == DropStrategy.DROP_OLDEST:
            self.queue.popleft()
            self.queue.append((item, time.time()))
            self.metrics.items_dropped += 1
            return True
        elif self.config.strategy == DropStrategy.DROP_NEWEST:
            self.metrics.items_dropped += 1
            return False
        elif self.config.strategy == DropStrategy.DROP_ON_FULL:
            self.metrics.items_dropped += 1
            return False
        else:  # BACKPRESSURE
            self.metrics.backpressure_events += 1
            return False

    async def dequeue(self) -> Optional[Any]:
        """Dequeue item for processing"""
        if not self.queue:
            return None

        item, enqueue_time = self.queue.popleft()
        latency_ms = (time.time() - enqueue_time) * 1000

        self.processing_times.append(latency_ms)
        self.metrics.queue_depth = len(self.queue)
        self.metrics.items_processed += 1
        self.metrics.total_latency_ms += latency_ms

        if self.metrics.items_processed > 0:
            self.metrics.avg_latency_ms = (
                self.metrics.total_latency_ms / self.metrics.items_processed
            )

        # Adjust rate if adaptive
        if self.config.adaptive_rate:
            self.metrics.current_rate = self.rate_limiter.adjust_rate(
                len(self.queue), latency_ms
            )

        return item

    def record_success(self) -> None:
        """Record successful processing"""
        self.circuit_breaker.record_success()
        self.metrics.circuit_state = self.circuit_breaker.get_state()

    def record_failure(self) -> None:
        """Record failed processing"""
        self.circuit_breaker.record_failure()
        self.metrics.circuit_state = self.circuit_breaker.get_state()

    def get_metrics(self) -> BackpressureMetrics:
        """Get current metrics"""
        self.metrics.last_updated = time.time()
        return self.metrics

    def get_status(self) -> Dict[str, Any]:
        """Get detailed status"""
        return {
            "name": self.name,
            "config": {
                "max_queue_size": self.config.max_queue_size,
                "strategy": self.config.strategy.value,
                "adaptive_rate": self.config.adaptive_rate,
                "target_latency_ms": self.config.target_latency_ms,
            },
            "metrics": self.metrics.to_dict(),
            "circuit_breaker": {
                "state": self.circuit_breaker.get_state(),
                "failure_count": self.circuit_breaker.failure_count,
            },
            "rate_limiter": {
                "current_rate": round(self.rate_limiter.current_rate, 2),
                "delay_ms": round(self.rate_limiter.get_delay() * 1000, 2),
            },
        }


class BackpressureMonitor:
    """Monitor for backpressure controllers"""

    def __init__(self):
        self.controllers: Dict[str, BackpressureController] = {}

    def register(self, controller: BackpressureController) -> None:
        """Register controller for monitoring"""
        self.controllers[controller.name] = controller

    def get_controller(self, name: str) -> Optional[BackpressureController]:
        """Get controller by name"""
        return self.controllers.get(name)

    def get_all_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get metrics for all controllers"""
        return {
            name: controller.get_status()
            for name, controller in self.controllers.items()
        }


async def monitor_command(args: argparse.Namespace) -> None:
    """Monitor queue backpressure"""
    config = BackpressureConfig(
        max_queue_size=args.max_queue_size,
        target_latency_ms=args.target_latency,
    )
    controller = BackpressureController(args.queue_name, config)

    print(f"Monitoring queue: {args.queue_name}")
    print(f"Interval: {args.interval}s")
    print("-" * 80)

    try:
        while True:
            status = controller.get_status()
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            print(f"\n[{timestamp}]")
            print(f"Queue Depth: {status['metrics']['queue_depth']}/{status['config']['max_queue_size']}")
            print(f"Avg Latency: {status['metrics']['avg_latency_ms']:.2f}ms")
            print(f"Items Processed: {status['metrics']['items_processed']}")
            print(f"Items Dropped: {status['metrics']['items_dropped']}")
            print(f"Backpressure Events: {status['metrics']['backpressure_events']}")
            print(f"Circuit State: {status['circuit_breaker']['state']}")
            print(f"Current Rate: {status['rate_limiter']['current_rate']:.2f} items/s")

            await asyncio.sleep(args.interval)
    except KeyboardInterrupt:
        print("\nMonitoring stopped.")


async def configure_command(args: argparse.Namespace) -> None:
    """Configure backpressure controller"""
    strategy = DropStrategy(args.strategy)
    config = BackpressureConfig(
        max_queue_size=args.max_queue_size,
        target_latency_ms=args.target_latency,
        strategy=strategy,
        adaptive_rate=args.adaptive,
        min_rate=args.min_rate,
        max_rate=args.max_rate,
    )

    print(f"Configuration for queue: {args.queue_name}")
    print(json.dumps({
        "max_queue_size": config.max_queue_size,
        "target_latency_ms": config.target_latency_ms,
        "strategy": config.strategy.value,
        "adaptive_rate": config.adaptive_rate,
        "min_rate": config.min_rate,
        "max_rate": config.max_rate,
    }, indent=2))


async def stats_command(args: argparse.Namespace) -> None:
    """Display statistics"""
    config = BackpressureConfig(max_queue_size=args.max_queue_size)
    controller = BackpressureController(args.queue_name, config)

    status = controller.get_status()
    print(json.dumps(status, indent=2))


async def test_command(args: argparse.Namespace) -> None:
    """Test backpressure with load patterns"""
    config = BackpressureConfig(
        max_queue_size=args.max_queue_size,
        strategy=DropStrategy(args.strategy),
    )
    controller = BackpressureController("test", config)

    print(f"Testing with load pattern: {args.load_pattern}")
    print(f"Duration: {args.duration}s")
    print("-" * 80)

    async def producer():
        """Simulate producer"""
        patterns = {
            "steady": lambda t: 10,
            "burst": lambda t: 100 if int(t) % 5 == 0 else 1,
            "ramp": lambda t: int(t * 2),
            "spike": lambda t: 500 if int(t) == args.duration // 2 else 10,
        }

        pattern_fn = patterns.get(args.load_pattern, patterns["steady"])
        start_time = time.time()

        while time.time() - start_time < args.duration:
            elapsed = time.time() - start_time
            rate = pattern_fn(elapsed)

            for _ in range(rate):
                await controller.enqueue({"data": f"item-{time.time()}"})

            await asyncio.sleep(0.1)

    async def consumer():
        """Simulate consumer"""
        start_time = time.time()

        while time.time() - start_time < args.duration:
            item = await controller.dequeue()
            if item:
                controller.record_success()
                await asyncio.sleep(0.01)  # Simulate processing
            else:
                await asyncio.sleep(0.01)

    async def monitor():
        """Monitor during test"""
        start_time = time.time()

        while time.time() - start_time < args.duration:
            metrics = controller.get_metrics()
            print(f"Queue: {metrics.queue_depth}, "
                  f"Processed: {metrics.items_processed}, "
                  f"Dropped: {metrics.items_dropped}, "
                  f"Latency: {metrics.avg_latency_ms:.2f}ms")
            await asyncio.sleep(1)

    await asyncio.gather(producer(), consumer(), monitor())

    print("\nTest Complete:")
    final_status = controller.get_status()
    print(json.dumps(final_status, indent=2))


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Backpressure controller for streaming pipelines"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Monitor command
    monitor_parser = subparsers.add_parser("monitor", help="Monitor queue backpressure")
    monitor_parser.add_argument("--queue-name", default="default", help="Queue name")
    monitor_parser.add_argument("--max-queue-size", type=int, default=1000)
    monitor_parser.add_argument("--target-latency", type=float, default=100.0)
    monitor_parser.add_argument("--interval", type=float, default=5.0, help="Update interval (s)")

    # Configure command
    config_parser = subparsers.add_parser("configure", help="Configure backpressure")
    config_parser.add_argument("--queue-name", default="default", help="Queue name")
    config_parser.add_argument("--max-queue-size", type=int, default=1000)
    config_parser.add_argument("--target-latency", type=float, default=100.0)
    config_parser.add_argument(
        "--strategy",
        choices=["drop-oldest", "drop-newest", "drop-on-full", "backpressure"],
        default="backpressure"
    )
    config_parser.add_argument("--adaptive", action="store_true")
    config_parser.add_argument("--min-rate", type=float, default=1.0)
    config_parser.add_argument("--max-rate", type=float, default=1000.0)

    # Stats command
    stats_parser = subparsers.add_parser("stats", help="Display statistics")
    stats_parser.add_argument("--queue-name", default="default", help="Queue name")
    stats_parser.add_argument("--max-queue-size", type=int, default=1000)

    # Test command
    test_parser = subparsers.add_parser("test", help="Test with load patterns")
    test_parser.add_argument(
        "--load-pattern",
        choices=["steady", "burst", "ramp", "spike"],
        default="steady"
    )
    test_parser.add_argument("--duration", type=int, default=10, help="Test duration (s)")
    test_parser.add_argument("--max-queue-size", type=int, default=100)
    test_parser.add_argument(
        "--strategy",
        choices=["drop-oldest", "drop-newest", "drop-on-full", "backpressure"],
        default="backpressure"
    )

    args = parser.parse_args()

    # Execute command
    commands = {
        "monitor": monitor_command,
        "configure": configure_command,
        "stats": stats_command,
        "test": test_command,
    }

    asyncio.run(commands[args.command](args))


if __name__ == "__main__":
    main()
