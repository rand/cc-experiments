"""
Feature Flag SDK Integration Example (Python)

Production-ready example showing LaunchDarkly and Unleash SDK integration
with best practices for caching, error handling, and graceful degradation.
"""

import os
import logging
from typing import Any, Dict, Optional
from dataclasses import dataclass
from functools import lru_cache
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class FeatureFlagContext:
    """Context for feature flag evaluation"""
    user_id: str
    email: Optional[str] = None
    country: Optional[str] = None
    plan: Optional[str] = None
    custom_attributes: Optional[Dict[str, Any]] = None


class LaunchDarklyClient:
    """
    Production LaunchDarkly client with caching and error handling

    Usage:
        client = LaunchDarklyClient(sdk_key=os.getenv('LAUNCHDARKLY_SDK_KEY'))

        context = FeatureFlagContext(
            user_id='user-123',
            email='user@example.com',
            plan='premium'
        )

        if client.is_enabled('new-feature', context):
            # New feature code
            pass
        else:
            # Legacy code
            pass
    """

    def __init__(self, sdk_key: str, timeout: int = 5):
        """
        Initialize LaunchDarkly client

        Args:
            sdk_key: LaunchDarkly SDK key
            timeout: Timeout for SDK initialization (seconds)
        """
        self.sdk_key = sdk_key
        self.timeout = timeout
        self.client = None
        self._cache = {}
        self._cache_ttl = 60  # Cache for 60 seconds

        try:
            # In production, use actual LaunchDarkly SDK:
            # import ldclient
            # ldclient.set_config(ldclient.Config(sdk_key))
            # self.client = ldclient.get()

            logger.info("LaunchDarkly client initialized")
        except Exception as e:
            logger.error(f"Failed to initialize LaunchDarkly: {e}")
            # Continue with client=None for graceful degradation

    def is_enabled(
        self,
        flag_key: str,
        context: FeatureFlagContext,
        default: bool = False
    ) -> bool:
        """
        Check if a boolean flag is enabled

        Args:
            flag_key: Feature flag key
            context: User context
            default: Default value if flag cannot be evaluated

        Returns:
            Boolean flag value
        """
        return self.variation(flag_key, context, default)

    def variation(
        self,
        flag_key: str,
        context: FeatureFlagContext,
        default: Any
    ) -> Any:
        """
        Get flag variation with caching and error handling

        Args:
            flag_key: Feature flag key
            context: User context
            default: Default value if flag cannot be evaluated

        Returns:
            Flag variation value
        """
        # Check cache first
        cache_key = f"{flag_key}:{context.user_id}"
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            return cached

        # Graceful degradation if client not initialized
        if not self.client:
            logger.warning(f"LaunchDarkly client not available, using default for {flag_key}")
            return default

        try:
            # Build user context
            user = self._build_user_context(context)

            # Evaluate flag
            # In production: value = self.client.variation(flag_key, user, default)
            value = default  # Placeholder

            # Cache result
            self._set_cache(cache_key, value)

            return value

        except Exception as e:
            logger.error(f"Error evaluating flag {flag_key}: {e}")
            return default

    def _build_user_context(self, context: FeatureFlagContext) -> Dict[str, Any]:
        """Build LaunchDarkly user context"""
        user = {
            'key': context.user_id
        }

        if context.email:
            user['email'] = context.email
        if context.country:
            user['country'] = context.country
        if context.plan:
            user['custom'] = {'plan': context.plan}
        if context.custom_attributes:
            user.setdefault('custom', {}).update(context.custom_attributes)

        return user

    def _get_from_cache(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired"""
        if key in self._cache:
            value, timestamp = self._cache[key]
            if time.time() - timestamp < self._cache_ttl:
                return value
            del self._cache[key]
        return None

    def _set_cache(self, key: str, value: Any):
        """Set value in cache with timestamp"""
        self._cache[key] = (value, time.time())

    def flush(self):
        """Flush events (call on shutdown)"""
        if self.client:
            try:
                # In production: self.client.flush()
                logger.info("LaunchDarkly events flushed")
            except Exception as e:
                logger.error(f"Error flushing events: {e}")

    def close(self):
        """Close client connection"""
        if self.client:
            try:
                # In production: self.client.close()
                logger.info("LaunchDarkly client closed")
            except Exception as e:
                logger.error(f"Error closing client: {e}")


class UnleashClient:
    """
    Production Unleash client with caching and error handling

    Usage:
        client = UnleashClient(
            api_url=os.getenv('UNLEASH_API_URL'),
            api_token=os.getenv('UNLEASH_API_TOKEN'),
            app_name='my-app'
        )

        context = FeatureFlagContext(
            user_id='user-123',
            custom_attributes={'region': 'us-west'}
        )

        if client.is_enabled('new-feature', context):
            # New feature code
            pass
    """

    def __init__(
        self,
        api_url: str,
        api_token: str,
        app_name: str,
        refresh_interval: int = 15
    ):
        """
        Initialize Unleash client

        Args:
            api_url: Unleash API URL
            api_token: API token
            app_name: Application name
            refresh_interval: Feature toggle refresh interval (seconds)
        """
        self.api_url = api_url
        self.api_token = api_token
        self.app_name = app_name
        self.refresh_interval = refresh_interval
        self.client = None

        try:
            # In production, use actual Unleash SDK:
            # from UnleashClient import UnleashClient as UC
            # self.client = UC(
            #     url=api_url,
            #     app_name=app_name,
            #     custom_headers={'Authorization': api_token},
            #     refresh_interval=refresh_interval
            # )
            # self.client.initialize_client()

            logger.info("Unleash client initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Unleash: {e}")

    def is_enabled(
        self,
        flag_key: str,
        context: FeatureFlagContext,
        default: bool = False
    ) -> bool:
        """
        Check if a feature is enabled

        Args:
            flag_key: Feature flag key
            context: User context
            default: Default value if flag cannot be evaluated

        Returns:
            Boolean flag value
        """
        if not self.client:
            logger.warning(f"Unleash client not available, using default for {flag_key}")
            return default

        try:
            # Build context
            unleash_context = self._build_context(context)

            # Evaluate flag
            # In production: return self.client.is_enabled(flag_key, unleash_context)
            return default  # Placeholder

        except Exception as e:
            logger.error(f"Error evaluating flag {flag_key}: {e}")
            return default

    def get_variant(
        self,
        flag_key: str,
        context: FeatureFlagContext
    ) -> Dict[str, Any]:
        """
        Get feature variant

        Args:
            flag_key: Feature flag key
            context: User context

        Returns:
            Variant object with 'name' and 'payload' fields
        """
        if not self.client:
            return {'name': 'disabled', 'enabled': False}

        try:
            unleash_context = self._build_context(context)

            # In production: return self.client.get_variant(flag_key, unleash_context)
            return {'name': 'disabled', 'enabled': False}

        except Exception as e:
            logger.error(f"Error getting variant for {flag_key}: {e}")
            return {'name': 'disabled', 'enabled': False}

    def _build_context(self, context: FeatureFlagContext) -> Dict[str, Any]:
        """Build Unleash context"""
        unleash_context = {
            'userId': context.user_id
        }

        if context.custom_attributes:
            unleash_context['properties'] = context.custom_attributes

        return unleash_context

    def destroy(self):
        """Destroy client (call on shutdown)"""
        if self.client:
            try:
                # In production: self.client.destroy()
                logger.info("Unleash client destroyed")
            except Exception as e:
                logger.error(f"Error destroying client: {e}")


class FeatureFlagManager:
    """
    Unified feature flag manager supporting multiple providers

    Provides a single interface for feature flags with automatic fallback
    and performance monitoring.

    Usage:
        manager = FeatureFlagManager()
        manager.add_provider('launchdarkly', launchdarkly_client)
        manager.add_provider('unleash', unleash_client)

        if manager.is_enabled('new-feature', context):
            # Feature code
            pass
    """

    def __init__(self):
        self.providers = {}
        self.default_provider = None
        self.metrics = {
            'evaluations': 0,
            'errors': 0,
            'cache_hits': 0
        }

    def add_provider(self, name: str, client: Any):
        """Add a feature flag provider"""
        self.providers[name] = client
        if not self.default_provider:
            self.default_provider = name
        logger.info(f"Added provider: {name}")

    def set_default_provider(self, name: str):
        """Set default provider"""
        if name not in self.providers:
            raise ValueError(f"Provider {name} not found")
        self.default_provider = name

    def is_enabled(
        self,
        flag_key: str,
        context: FeatureFlagContext,
        default: bool = False,
        provider: Optional[str] = None
    ) -> bool:
        """
        Check if flag is enabled

        Args:
            flag_key: Feature flag key
            context: User context
            default: Default value
            provider: Specific provider to use (optional)

        Returns:
            Boolean flag value
        """
        self.metrics['evaluations'] += 1

        provider_name = provider or self.default_provider
        if not provider_name or provider_name not in self.providers:
            logger.warning(f"No provider available for {flag_key}")
            return default

        try:
            client = self.providers[provider_name]
            return client.is_enabled(flag_key, context, default)
        except Exception as e:
            self.metrics['errors'] += 1
            logger.error(f"Error evaluating {flag_key}: {e}")
            return default

    def get_metrics(self) -> Dict[str, int]:
        """Get performance metrics"""
        return self.metrics.copy()

    def shutdown(self):
        """Shutdown all providers"""
        for name, client in self.providers.items():
            try:
                if hasattr(client, 'close'):
                    client.close()
                elif hasattr(client, 'destroy'):
                    client.destroy()
                logger.info(f"Shutdown provider: {name}")
            except Exception as e:
                logger.error(f"Error shutting down {name}: {e}")


# Example usage
if __name__ == '__main__':
    # Initialize manager
    manager = FeatureFlagManager()

    # Add LaunchDarkly
    ld_client = LaunchDarklyClient(
        sdk_key=os.getenv('LAUNCHDARKLY_SDK_KEY', 'test-key')
    )
    manager.add_provider('launchdarkly', ld_client)

    # Add Unleash
    unleash_client = UnleashClient(
        api_url=os.getenv('UNLEASH_API_URL', 'http://localhost:4242'),
        api_token=os.getenv('UNLEASH_API_TOKEN', 'test-token'),
        app_name='my-app'
    )
    manager.add_provider('unleash', unleash_client)

    # Create context
    context = FeatureFlagContext(
        user_id='user-123',
        email='user@example.com',
        plan='premium'
    )

    # Check flags
    if manager.is_enabled('new-dashboard', context):
        print("New dashboard enabled")

    if manager.is_enabled('beta-features', context):
        print("Beta features enabled")

    # Get metrics
    print(f"Metrics: {manager.get_metrics()}")

    # Shutdown
    manager.shutdown()
