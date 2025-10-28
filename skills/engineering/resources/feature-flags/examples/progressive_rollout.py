"""
Progressive Rollout Implementation

Production-ready example showing how to implement progressive rollouts
with percentage-based, canary, and ring-based deployment strategies.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import hashlib
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RolloutStrategy(Enum):
    """Rollout strategy types"""
    PERCENTAGE = "percentage"
    CANARY = "canary"
    RING = "ring"
    USER_LIST = "user_list"


@dataclass
class RolloutConfig:
    """Rollout configuration"""
    strategy: RolloutStrategy
    percentage: Optional[float] = None
    canary_users: Optional[List[str]] = None
    canary_hosts: Optional[List[str]] = None
    rings: Optional[Dict[str, float]] = None
    user_allowlist: Optional[List[str]] = None
    user_blocklist: Optional[List[str]] = None


class ProgressiveRollout:
    """
    Progressive rollout implementation with multiple strategies

    Supports:
    - Percentage-based rollout (consistent hashing)
    - Canary deployment (specific users/hosts)
    - Ring-based deployment (progressive expansion)
    - User allowlist/blocklist

    Usage:
        rollout = ProgressiveRollout('new-feature', RolloutConfig(
            strategy=RolloutStrategy.PERCENTAGE,
            percentage=25.0
        ))

        if rollout.is_enabled(user_id='user-123'):
            # Show new feature
            pass
    """

    def __init__(self, feature_key: str, config: RolloutConfig):
        """
        Initialize progressive rollout

        Args:
            feature_key: Unique feature key
            config: Rollout configuration
        """
        self.feature_key = feature_key
        self.config = config
        self._validate_config()

    def _validate_config(self):
        """Validate rollout configuration"""
        if self.config.strategy == RolloutStrategy.PERCENTAGE:
            if self.config.percentage is None:
                raise ValueError("Percentage required for PERCENTAGE strategy")
            if not 0 <= self.config.percentage <= 100:
                raise ValueError("Percentage must be between 0 and 100")

        elif self.config.strategy == RolloutStrategy.CANARY:
            if not self.config.canary_users and not self.config.canary_hosts:
                raise ValueError("Canary users or hosts required for CANARY strategy")

        elif self.config.strategy == RolloutStrategy.RING:
            if not self.config.rings:
                raise ValueError("Rings configuration required for RING strategy")

    def is_enabled(
        self,
        user_id: str,
        host: Optional[str] = None,
        ring: Optional[str] = None
    ) -> bool:
        """
        Check if feature is enabled for user

        Args:
            user_id: User identifier
            host: Host identifier (for canary deployment)
            ring: Ring identifier (for ring-based rollout)

        Returns:
            True if feature should be enabled
        """
        # Check blocklist first
        if self.config.user_blocklist and user_id in self.config.user_blocklist:
            logger.debug(f"User {user_id} blocked for {self.feature_key}")
            return False

        # Check allowlist
        if self.config.user_allowlist and user_id in self.config.user_allowlist:
            logger.debug(f"User {user_id} allowed for {self.feature_key}")
            return True

        # Apply strategy
        if self.config.strategy == RolloutStrategy.PERCENTAGE:
            return self._percentage_rollout(user_id)

        elif self.config.strategy == RolloutStrategy.CANARY:
            return self._canary_rollout(user_id, host)

        elif self.config.strategy == RolloutStrategy.RING:
            return self._ring_rollout(user_id, ring)

        elif self.config.strategy == RolloutStrategy.USER_LIST:
            return user_id in (self.config.user_allowlist or [])

        return False

    def _percentage_rollout(self, user_id: str) -> bool:
        """
        Percentage-based rollout using consistent hashing

        Ensures same user always gets same result (deterministic)
        """
        # Create hash of feature_key + user_id
        hash_input = f"{self.feature_key}:{user_id}"
        hash_value = int(hashlib.md5(hash_input.encode()).hexdigest(), 16)

        # Convert to percentage (0-100)
        bucket = (hash_value % 10000) / 100.0

        enabled = bucket < self.config.percentage
        logger.debug(
            f"User {user_id} in bucket {bucket:.2f}% "
            f"(threshold: {self.config.percentage}%) = {enabled}"
        )
        return enabled

    def _canary_rollout(self, user_id: str, host: Optional[str] = None) -> bool:
        """Canary rollout for specific users or hosts"""
        if self.config.canary_users and user_id in self.config.canary_users:
            logger.debug(f"User {user_id} is canary user")
            return True

        if host and self.config.canary_hosts and host in self.config.canary_hosts:
            logger.debug(f"Host {host} is canary host")
            return True

        return False

    def _ring_rollout(self, user_id: str, ring: Optional[str] = None) -> bool:
        """
        Ring-based rollout with progressive expansion

        Rings typically represent environments or user groups:
        - ring0: Internal users (100%)
        - ring1: Early adopters (50%)
        - ring2: General users (25%)
        - ring3: All users (100%)
        """
        if not ring or ring not in self.config.rings:
            return False

        percentage = self.config.rings[ring]
        return self._percentage_rollout(user_id) if percentage < 100 else True


class RolloutScheduler:
    """
    Rollout scheduler for automated progressive rollouts

    Gradually increases rollout percentage over time according to schedule.

    Usage:
        schedule = [
            (0, 1.0),      # Start: 1%
            (1, 5.0),      # Day 1: 5%
            (3, 25.0),     # Day 3: 25%
            (7, 50.0),     # Day 7: 50%
            (14, 100.0)    # Day 14: 100%
        ]

        scheduler = RolloutScheduler('new-feature', schedule, start_date)
        current_percentage = scheduler.get_current_percentage()
    """

    def __init__(
        self,
        feature_key: str,
        schedule: List[tuple[int, float]],
        start_timestamp: float
    ):
        """
        Initialize rollout scheduler

        Args:
            feature_key: Feature key
            schedule: List of (day, percentage) tuples
            start_timestamp: Start timestamp (Unix time)
        """
        self.feature_key = feature_key
        self.schedule = sorted(schedule, key=lambda x: x[0])
        self.start_timestamp = start_timestamp

    def get_current_percentage(self, current_timestamp: Optional[float] = None) -> float:
        """
        Get current rollout percentage based on schedule

        Args:
            current_timestamp: Current timestamp (defaults to now)

        Returns:
            Current percentage
        """
        if current_timestamp is None:
            import time
            current_timestamp = time.time()

        days_elapsed = (current_timestamp - self.start_timestamp) / 86400

        # Find appropriate percentage from schedule
        percentage = 0.0
        for day, pct in self.schedule:
            if days_elapsed >= day:
                percentage = pct
            else:
                break

        logger.info(
            f"{self.feature_key}: {days_elapsed:.1f} days elapsed, "
            f"rollout at {percentage}%"
        )
        return percentage

    def is_complete(self, current_timestamp: Optional[float] = None) -> bool:
        """Check if rollout is complete (100%)"""
        return self.get_current_percentage(current_timestamp) >= 100.0


class RolloutManager:
    """
    Manage multiple progressive rollouts

    Centralized management of feature rollouts with monitoring and controls.

    Usage:
        manager = RolloutManager()

        manager.create_rollout('feature-a', RolloutConfig(
            strategy=RolloutStrategy.PERCENTAGE,
            percentage=25.0
        ))

        if manager.is_enabled('feature-a', user_id='user-123'):
            # Feature code
            pass
    """

    def __init__(self):
        self.rollouts: Dict[str, ProgressiveRollout] = {}
        self.metrics: Dict[str, Dict[str, int]] = {}

    def create_rollout(self, feature_key: str, config: RolloutConfig):
        """Create a new rollout"""
        rollout = ProgressiveRollout(feature_key, config)
        self.rollouts[feature_key] = rollout
        self.metrics[feature_key] = {
            'total_checks': 0,
            'enabled_count': 0,
            'disabled_count': 0
        }
        logger.info(f"Created rollout for {feature_key}")

    def update_rollout(self, feature_key: str, config: RolloutConfig):
        """Update existing rollout configuration"""
        if feature_key not in self.rollouts:
            raise ValueError(f"Rollout {feature_key} not found")

        rollout = ProgressiveRollout(feature_key, config)
        self.rollouts[feature_key] = rollout
        logger.info(f"Updated rollout for {feature_key}")

    def delete_rollout(self, feature_key: str):
        """Delete a rollout"""
        if feature_key in self.rollouts:
            del self.rollouts[feature_key]
            logger.info(f"Deleted rollout for {feature_key}")

    def is_enabled(
        self,
        feature_key: str,
        user_id: str,
        **kwargs
    ) -> bool:
        """
        Check if feature is enabled for user

        Args:
            feature_key: Feature key
            user_id: User identifier
            **kwargs: Additional context (host, ring, etc.)

        Returns:
            True if feature should be enabled
        """
        if feature_key not in self.rollouts:
            logger.warning(f"Rollout {feature_key} not found")
            return False

        rollout = self.rollouts[feature_key]
        enabled = rollout.is_enabled(user_id, **kwargs)

        # Update metrics
        self.metrics[feature_key]['total_checks'] += 1
        if enabled:
            self.metrics[feature_key]['enabled_count'] += 1
        else:
            self.metrics[feature_key]['disabled_count'] += 1

        return enabled

    def get_metrics(self, feature_key: str) -> Dict[str, Any]:
        """Get rollout metrics"""
        if feature_key not in self.metrics:
            return {}

        metrics = self.metrics[feature_key].copy()
        if metrics['total_checks'] > 0:
            metrics['enabled_percentage'] = (
                metrics['enabled_count'] / metrics['total_checks'] * 100
            )
        return metrics

    def get_all_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get metrics for all rollouts"""
        return {
            feature_key: self.get_metrics(feature_key)
            for feature_key in self.rollouts.keys()
        }


# Example usage
if __name__ == '__main__':
    import time

    # Example 1: Percentage-based rollout
    print("=== Percentage-based Rollout ===")
    rollout = ProgressiveRollout('new-ui', RolloutConfig(
        strategy=RolloutStrategy.PERCENTAGE,
        percentage=25.0
    ))

    test_users = [f"user-{i}" for i in range(100)]
    enabled_count = sum(1 for user in test_users if rollout.is_enabled(user))
    print(f"Enabled for {enabled_count}/100 users (~25% expected)")

    # Example 2: Canary deployment
    print("\n=== Canary Deployment ===")
    canary_rollout = ProgressiveRollout('beta-feature', RolloutConfig(
        strategy=RolloutStrategy.CANARY,
        canary_users=['user-1', 'user-2', 'user-3']
    ))

    print(f"user-1 enabled: {canary_rollout.is_enabled('user-1')}")
    print(f"user-99 enabled: {canary_rollout.is_enabled('user-99')}")

    # Example 3: Ring-based rollout
    print("\n=== Ring-based Rollout ===")
    ring_rollout = ProgressiveRollout('premium-feature', RolloutConfig(
        strategy=RolloutStrategy.RING,
        rings={
            'internal': 100.0,
            'early-adopter': 50.0,
            'standard': 25.0,
            'all': 100.0
        }
    ))

    print(f"Internal user: {ring_rollout.is_enabled('user-1', ring='internal')}")
    print(f"Early adopter: {ring_rollout.is_enabled('user-2', ring='early-adopter')}")

    # Example 4: Scheduled rollout
    print("\n=== Scheduled Rollout ===")
    schedule = [
        (0, 1.0),
        (1, 5.0),
        (3, 25.0),
        (7, 50.0),
        (14, 100.0)
    ]

    start_time = time.time()
    scheduler = RolloutScheduler('scheduled-feature', schedule, start_time)
    print(f"Current percentage: {scheduler.get_current_percentage()}%")

    # Simulate day 7
    day_7_time = start_time + (7 * 86400)
    print(f"Day 7 percentage: {scheduler.get_current_percentage(day_7_time)}%")

    # Example 5: Rollout manager
    print("\n=== Rollout Manager ===")
    manager = RolloutManager()

    manager.create_rollout('feature-a', RolloutConfig(
        strategy=RolloutStrategy.PERCENTAGE,
        percentage=50.0
    ))

    manager.create_rollout('feature-b', RolloutConfig(
        strategy=RolloutStrategy.CANARY,
        canary_users=['admin-1', 'admin-2']
    ))

    # Check multiple features
    for i in range(10):
        user = f"user-{i}"
        feature_a = manager.is_enabled('feature-a', user)
        feature_b = manager.is_enabled('feature-b', user)
        print(f"{user}: feature-a={feature_a}, feature-b={feature_b}")

    print("\nMetrics:")
    for feature, metrics in manager.get_all_metrics().items():
        print(f"{feature}: {metrics}")
