#!/usr/bin/env python3
"""
Circuit breaker implementation for LM API calls with state management.

Implements the circuit breaker pattern for handling API failures with:
- State machine (closed, open, half-open)
- Failure threshold tracking
- Timeout and retry strategies
- Redis persistence for distributed systems
- Health check probes
- CLI for management and monitoring
"""

import argparse
import asyncio
import json
import logging
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, TypeVar

import httpx

try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

T = TypeVar('T')


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation, requests pass through
    OPEN = "open"          # Failure threshold exceeded, requests blocked
    HALF_OPEN = "half_open"  # Testing recovery, limited requests allowed


@dataclass
class CircuitConfig:
    """Circuit breaker configuration."""
    service: str
    failure_threshold: int = 5
    timeout_seconds: int = 60
    half_open_max_calls: int = 3
    success_threshold: int = 2
    reset_timeout: int = 300
    health_check_interval: int = 30

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "service": self.service,
            "failure_threshold": self.failure_threshold,
            "timeout_seconds": self.timeout_seconds,
            "half_open_max_calls": self.half_open_max_calls,
            "success_threshold": self.success_threshold,
            "reset_timeout": self.reset_timeout,
            "health_check_interval": self.health_check_interval
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CircuitConfig":
        """Create from dictionary."""
        return cls(**data)


@dataclass
class CircuitMetrics:
    """Circuit breaker metrics."""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    rejected_requests: int = 0
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    last_failure_time: Optional[float] = None
    last_success_time: Optional[float] = None
    state_transitions: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "rejected_requests": self.rejected_requests,
            "consecutive_failures": self.consecutive_failures,
            "consecutive_successes": self.consecutive_successes,
            "last_failure_time": self.last_failure_time,
            "last_success_time": self.last_success_time,
            "state_transitions": self.state_transitions
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CircuitMetrics":
        """Create from dictionary."""
        return cls(**data)


class CircuitBreaker:
    """Circuit breaker for API calls with state persistence."""

    def __init__(
        self,
        config: CircuitConfig,
        redis_client: Optional[redis.Redis] = None,
        storage_path: Optional[Path] = None
    ):
        """Initialize circuit breaker.

        Args:
            config: Circuit breaker configuration
            redis_client: Optional Redis client for distributed state
            storage_path: Optional local file path for state persistence
        """
        self.config = config
        self.redis_client = redis_client
        self.storage_path = storage_path or Path(f".circuit_breaker_{config.service}.json")

        self.state = CircuitState.CLOSED
        self.metrics = CircuitMetrics()
        self.state_opened_at: Optional[float] = None

        # Load persisted state
        asyncio.create_task(self._load_state())

    async def _load_state(self) -> None:
        """Load state from persistence layer."""
        try:
            if self.redis_client:
                await self._load_from_redis()
            elif self.storage_path.exists():
                await self._load_from_file()
        except Exception as e:
            logger.warning(f"Failed to load state: {e}")

    async def _load_from_redis(self) -> None:
        """Load state from Redis."""
        if not self.redis_client:
            return

        key = f"circuit_breaker:{self.config.service}"
        data = await self.redis_client.get(key)

        if data:
            state_data = json.loads(data)
            self.state = CircuitState(state_data["state"])
            self.metrics = CircuitMetrics.from_dict(state_data["metrics"])
            self.state_opened_at = state_data.get("state_opened_at")

    async def _load_from_file(self) -> None:
        """Load state from local file."""
        if not self.storage_path.exists():
            return

        with open(self.storage_path, 'r') as f:
            state_data = json.load(f)
            self.state = CircuitState(state_data["state"])
            self.metrics = CircuitMetrics.from_dict(state_data["metrics"])
            self.state_opened_at = state_data.get("state_opened_at")

    async def _save_state(self) -> None:
        """Save state to persistence layer."""
        try:
            if self.redis_client:
                await self._save_to_redis()
            else:
                await self._save_to_file()
        except Exception as e:
            logger.error(f"Failed to save state: {e}")

    async def _save_to_redis(self) -> None:
        """Save state to Redis."""
        if not self.redis_client:
            return

        key = f"circuit_breaker:{self.config.service}"
        data = json.dumps({
            "state": self.state.value,
            "metrics": self.metrics.to_dict(),
            "state_opened_at": self.state_opened_at,
            "config": self.config.to_dict()
        })

        await self.redis_client.set(key, data, ex=self.config.reset_timeout)

    async def _save_to_file(self) -> None:
        """Save state to local file."""
        with open(self.storage_path, 'w') as f:
            json.dump({
                "state": self.state.value,
                "metrics": self.metrics.to_dict(),
                "state_opened_at": self.state_opened_at,
                "config": self.config.to_dict()
            }, f, indent=2)

    async def _transition_state(self, new_state: CircuitState, reason: str) -> None:
        """Transition to new state."""
        old_state = self.state
        self.state = new_state

        if new_state == CircuitState.OPEN:
            self.state_opened_at = time.time()

        transition = {
            "from": old_state.value,
            "to": new_state.value,
            "reason": reason,
            "timestamp": time.time()
        }
        self.metrics.state_transitions.append(transition)

        logger.info(f"Circuit breaker [{self.config.service}]: {old_state.value} -> {new_state.value} ({reason})")

        await self._save_state()

    async def _check_timeout(self) -> None:
        """Check if circuit should transition from OPEN to HALF_OPEN."""
        if self.state == CircuitState.OPEN and self.state_opened_at:
            elapsed = time.time() - self.state_opened_at
            if elapsed >= self.config.timeout_seconds:
                await self._transition_state(CircuitState.HALF_OPEN, "timeout expired")

    def _should_allow_request(self) -> bool:
        """Check if request should be allowed based on current state."""
        if self.state == CircuitState.CLOSED:
            return True

        if self.state == CircuitState.OPEN:
            return False

        if self.state == CircuitState.HALF_OPEN:
            return self.metrics.consecutive_successes < self.config.half_open_max_calls

        return False

    async def call(self, func: Callable[[], T], *args, **kwargs) -> T:
        """Execute function with circuit breaker protection.

        Args:
            func: Function to execute
            *args: Positional arguments for function
            **kwargs: Keyword arguments for function

        Returns:
            Function result

        Raises:
            CircuitBreakerOpenError: If circuit is open
            Exception: Any exception from the function
        """
        await self._check_timeout()

        if not self._should_allow_request():
            self.metrics.rejected_requests += 1
            await self._save_state()
            raise CircuitBreakerOpenError(f"Circuit breaker is {self.state.value} for {self.config.service}")

        self.metrics.total_requests += 1

        try:
            result = await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)
            await self._on_success()
            return result
        except Exception as e:
            await self._on_failure(e)
            raise

    async def _on_success(self) -> None:
        """Handle successful request."""
        self.metrics.successful_requests += 1
        self.metrics.consecutive_successes += 1
        self.metrics.consecutive_failures = 0
        self.metrics.last_success_time = time.time()

        if self.state == CircuitState.HALF_OPEN:
            if self.metrics.consecutive_successes >= self.config.success_threshold:
                await self._transition_state(CircuitState.CLOSED, "success threshold reached")

        await self._save_state()

    async def _on_failure(self, error: Exception) -> None:
        """Handle failed request."""
        self.metrics.failed_requests += 1
        self.metrics.consecutive_failures += 1
        self.metrics.consecutive_successes = 0
        self.metrics.last_failure_time = time.time()

        if self.state == CircuitState.CLOSED:
            if self.metrics.consecutive_failures >= self.config.failure_threshold:
                await self._transition_state(CircuitState.OPEN, "failure threshold exceeded")
        elif self.state == CircuitState.HALF_OPEN:
            await self._transition_state(CircuitState.OPEN, "failure in half-open state")

        await self._save_state()

    async def reset(self) -> None:
        """Reset circuit breaker to closed state."""
        self.state = CircuitState.CLOSED
        self.metrics = CircuitMetrics()
        self.state_opened_at = None
        await self._save_state()
        logger.info(f"Circuit breaker [{self.config.service}] reset")

    def get_status(self) -> Dict[str, Any]:
        """Get current circuit breaker status."""
        return {
            "service": self.config.service,
            "state": self.state.value,
            "metrics": self.metrics.to_dict(),
            "config": self.config.to_dict(),
            "state_opened_at": self.state_opened_at
        }


class CircuitBreakerOpenError(Exception):
    """Exception raised when circuit breaker is open."""
    pass


async def configure_circuit_breaker(args: argparse.Namespace) -> None:
    """Configure circuit breaker."""
    config = CircuitConfig(
        service=args.service,
        failure_threshold=args.threshold,
        timeout_seconds=args.timeout,
        half_open_max_calls=args.half_open_calls,
        success_threshold=args.success_threshold,
        reset_timeout=args.reset_timeout
    )

    storage_path = Path(f".circuit_breaker_{args.service}.json")
    with open(storage_path, 'w') as f:
        json.dump({"config": config.to_dict()}, f, indent=2)

    logger.info(f"Circuit breaker configured for {args.service}")
    print(json.dumps(config.to_dict(), indent=2))


async def show_status(args: argparse.Namespace) -> None:
    """Show circuit breaker status."""
    storage_path = Path(f".circuit_breaker_{args.service}.json")

    if not storage_path.exists():
        logger.error(f"No configuration found for {args.service}")
        sys.exit(1)

    with open(storage_path, 'r') as f:
        data = json.load(f)

    print(json.dumps(data, indent=2))


async def test_circuit_breaker(args: argparse.Namespace) -> None:
    """Test circuit breaker with API endpoint."""
    storage_path = Path(f".circuit_breaker_{args.service}.json")

    if not storage_path.exists():
        logger.error(f"No configuration found for {args.service}")
        sys.exit(1)

    with open(storage_path, 'r') as f:
        data = json.load(f)
        config = CircuitConfig.from_dict(data.get("config", {}))

    breaker = CircuitBreaker(config, storage_path=storage_path)
    await breaker._load_state()

    async def make_request():
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(args.endpoint)
            response.raise_for_status()
            return response.json()

    try:
        result = await breaker.call(make_request)
        logger.info(f"Request succeeded: {result}")
        print(json.dumps(breaker.get_status(), indent=2))
    except CircuitBreakerOpenError as e:
        logger.error(f"Circuit breaker blocked request: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Request failed: {e}")
        print(json.dumps(breaker.get_status(), indent=2))
        sys.exit(1)


async def reset_circuit_breaker(args: argparse.Namespace) -> None:
    """Reset circuit breaker."""
    storage_path = Path(f".circuit_breaker_{args.service}.json")

    if not storage_path.exists():
        logger.error(f"No configuration found for {args.service}")
        sys.exit(1)

    with open(storage_path, 'r') as f:
        data = json.load(f)
        config = CircuitConfig.from_dict(data.get("config", {}))

    breaker = CircuitBreaker(config, storage_path=storage_path)
    await breaker._load_state()
    await breaker.reset()

    logger.info(f"Circuit breaker reset for {args.service}")


async def monitor_circuit_breakers(args: argparse.Namespace) -> None:
    """Monitor multiple circuit breakers."""
    services = args.services.split(',')

    try:
        while True:
            print("\033[2J\033[H")  # Clear screen
            print(f"Circuit Breaker Monitor - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print("=" * 80)

            for service in services:
                storage_path = Path(f".circuit_breaker_{service}.json")

                if not storage_path.exists():
                    print(f"\n{service}: No configuration found")
                    continue

                with open(storage_path, 'r') as f:
                    data = json.load(f)

                state = data.get("state", "unknown")
                metrics = data.get("metrics", {})

                print(f"\n{service}:")
                print(f"  State: {state}")
                print(f"  Total Requests: {metrics.get('total_requests', 0)}")
                print(f"  Success: {metrics.get('successful_requests', 0)}")
                print(f"  Failed: {metrics.get('failed_requests', 0)}")
                print(f"  Rejected: {metrics.get('rejected_requests', 0)}")
                print(f"  Consecutive Failures: {metrics.get('consecutive_failures', 0)}")

            await asyncio.sleep(args.refresh)

    except KeyboardInterrupt:
        print("\nMonitoring stopped")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="Circuit breaker for LM API calls")
    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # Configure command
    configure_parser = subparsers.add_parser('configure', help='Configure circuit breaker')
    configure_parser.add_argument('--service', required=True, help='Service name')
    configure_parser.add_argument('--threshold', type=int, default=5, help='Failure threshold')
    configure_parser.add_argument('--timeout', type=int, default=60, help='Timeout in seconds')
    configure_parser.add_argument('--half-open-calls', type=int, default=3, help='Max calls in half-open state')
    configure_parser.add_argument('--success-threshold', type=int, default=2, help='Success threshold to close')
    configure_parser.add_argument('--reset-timeout', type=int, default=300, help='Reset timeout in seconds')

    # Status command
    status_parser = subparsers.add_parser('status', help='Show circuit breaker status')
    status_parser.add_argument('--service', required=True, help='Service name')

    # Test command
    test_parser = subparsers.add_parser('test', help='Test circuit breaker')
    test_parser.add_argument('--service', required=True, help='Service name')
    test_parser.add_argument('--endpoint', required=True, help='API endpoint to test')

    # Reset command
    reset_parser = subparsers.add_parser('reset', help='Reset circuit breaker')
    reset_parser.add_argument('--service', required=True, help='Service name')

    # Monitor command
    monitor_parser = subparsers.add_parser('monitor', help='Monitor circuit breakers')
    monitor_parser.add_argument('--services', required=True, help='Comma-separated service names')
    monitor_parser.add_argument('--refresh', type=int, default=5, help='Refresh interval in seconds')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Execute command
    if args.command == 'configure':
        asyncio.run(configure_circuit_breaker(args))
    elif args.command == 'status':
        asyncio.run(show_status(args))
    elif args.command == 'test':
        asyncio.run(test_circuit_breaker(args))
    elif args.command == 'reset':
        asyncio.run(reset_circuit_breaker(args))
    elif args.command == 'monitor':
        asyncio.run(monitor_circuit_breakers(args))


if __name__ == '__main__':
    main()
