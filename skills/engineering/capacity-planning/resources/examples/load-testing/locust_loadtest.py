#!/usr/bin/env python3
"""
Production Locust Load Test Scenario

This example demonstrates realistic load testing for capacity planning:
- Multiple user types with different behaviors
- Realistic think time and session patterns
- Custom metrics tracking
- Gradual ramp-up and sustained load
- Comprehensive reporting

Usage:
    # Run with Web UI
    locust -f locust_loadtest.py --host https://api.example.com

    # Run headless with specific load
    locust -f locust_loadtest.py --headless --users 1000 --spawn-rate 10 --run-time 30m --host https://api.example.com

    # Run with custom stages
    locust -f locust_loadtest.py --host https://api.example.com --users 5000 --spawn-rate 100
"""

from locust import HttpUser, task, between, events, LoadTestShape
import random
import time
import json


# Custom metrics tracking
request_latencies = []
error_counts = {}


@events.request.add_listener
def on_request(request_type, name, response_time, response_length, exception, **kwargs):
    """Track custom metrics for each request."""
    if exception is None:
        request_latencies.append(response_time)
    else:
        error_type = type(exception).__name__
        error_counts[error_type] = error_counts.get(error_type, 0) + 1


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Report custom metrics at end of test."""
    if request_latencies:
        import numpy as np
        print(f"\n{'='*60}")
        print(f"Custom Capacity Planning Metrics")
        print(f"{'='*60}")
        print(f"Total requests: {len(request_latencies)}")
        print(f"P50 latency: {np.percentile(request_latencies, 50):.2f}ms")
        print(f"P75 latency: {np.percentile(request_latencies, 75):.2f}ms")
        print(f"P90 latency: {np.percentile(request_latencies, 90):.2f}ms")
        print(f"P95 latency: {np.percentile(request_latencies, 95):.2f}ms")
        print(f"P99 latency: {np.percentile(request_latencies, 99):.2f}ms")
        print(f"Max latency: {max(request_latencies):.2f}ms")

        if error_counts:
            print(f"\nError breakdown:")
            for error_type, count in error_counts.items():
                print(f"  {error_type}: {count}")

        # Capacity recommendations
        p95 = np.percentile(request_latencies, 95)
        if p95 > 1000:
            print(f"\n⚠️  WARNING: P95 latency ({p95:.0f}ms) exceeds 1000ms")
            print("   Recommendation: Add capacity or optimize performance")
        elif p95 > 500:
            print(f"\n⚠️  CAUTION: P95 latency ({p95:.0f}ms) approaching limit")
            print("   Recommendation: Monitor closely and plan capacity addition")
        else:
            print(f"\n✓ OK: P95 latency ({p95:.0f}ms) within acceptable range")


class BrowsingUser(HttpUser):
    """
    Simulates users browsing the application.
    Typical pattern: View list → View details → Occasional action
    """

    wait_time = between(2, 5)  # Think time between actions
    weight = 3  # 3x more browsing users than others

    def on_start(self):
        """Setup before user starts."""
        self.user_id = random.randint(1, 10000)

    @task(10)
    def browse_items(self):
        """Browse item listings (most common action)."""
        page = random.randint(1, 10)
        self.client.get(
            f"/api/items?page={page}&limit=20",
            name="/api/items (browse)"
        )

    @task(5)
    def view_item_details(self):
        """View specific item details."""
        item_id = random.randint(1, 1000)
        self.client.get(
            f"/api/items/{item_id}",
            name="/api/items/:id"
        )

    @task(2)
    def search_items(self):
        """Search for items."""
        search_terms = ["laptop", "phone", "tablet", "monitor", "keyboard"]
        query = random.choice(search_terms)
        self.client.get(
            f"/api/items/search?q={query}",
            name="/api/items/search"
        )

    @task(1)
    def view_categories(self):
        """View category listings."""
        self.client.get("/api/categories", name="/api/categories")


class ShoppingUser(HttpUser):
    """
    Simulates users actively shopping.
    Pattern: Browse → Add to cart → View cart → Checkout
    """

    wait_time = between(1, 3)
    weight = 2

    def on_start(self):
        """Login and get session."""
        response = self.client.post(
            "/api/login",
            json={
                "username": f"user_{random.randint(1, 10000)}",
                "password": "test123"
            },
            name="/api/login"
        )

        if response.status_code == 200:
            self.token = response.json().get("token", "")
        else:
            self.token = ""

    def headers(self):
        """Get auth headers."""
        return {"Authorization": f"Bearer {self.token}"} if self.token else {}

    @task(5)
    def add_to_cart(self):
        """Add item to shopping cart."""
        item_id = random.randint(1, 1000)
        quantity = random.randint(1, 3)

        self.client.post(
            "/api/cart",
            json={
                "item_id": item_id,
                "quantity": quantity
            },
            headers=self.headers(),
            name="/api/cart (add)"
        )

    @task(3)
    def view_cart(self):
        """View shopping cart."""
        self.client.get(
            "/api/cart",
            headers=self.headers(),
            name="/api/cart (view)"
        )

    @task(1)
    def checkout(self):
        """Complete checkout process."""
        # View cart
        self.client.get("/api/cart", headers=self.headers())
        time.sleep(2)

        # Submit order
        self.client.post(
            "/api/orders",
            json={
                "payment_method": "credit_card",
                "shipping_address": "123 Main St"
            },
            headers=self.headers(),
            name="/api/orders (checkout)"
        )


class APIUser(HttpUser):
    """
    Simulates API clients (mobile apps, integrations).
    Higher request rate, more consistent patterns.
    """

    wait_time = between(0.5, 1.5)
    weight = 1

    def on_start(self):
        """Get API credentials."""
        self.api_key = "test_api_key"

    def headers(self):
        """Get API headers."""
        return {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json"
        }

    @task(5)
    def sync_data(self):
        """Sync data (common for mobile apps)."""
        since = int(time.time()) - 3600  # Last hour
        self.client.get(
            f"/api/sync?since={since}",
            headers=self.headers(),
            name="/api/sync"
        )

    @task(3)
    def get_user_profile(self):
        """Get user profile."""
        user_id = random.randint(1, 10000)
        self.client.get(
            f"/api/users/{user_id}/profile",
            headers=self.headers(),
            name="/api/users/:id/profile"
        )

    @task(2)
    def post_analytics(self):
        """Post analytics events."""
        self.client.post(
            "/api/analytics",
            json={
                "event": "page_view",
                "timestamp": int(time.time()),
                "properties": {}
            },
            headers=self.headers(),
            name="/api/analytics"
        )


class StagesShape(LoadTestShape):
    """
    Custom load test shape for capacity testing.

    Stages:
    1. Ramp up gradually (10 min)
    2. Sustain baseline load (20 min)
    3. Ramp to peak load (10 min)
    4. Sustain peak load (20 min)
    5. Ramp down (10 min)
    """

    stages = [
        # (duration_seconds, user_count)
        (600, 100),    # 10 min: Ramp to 100 users
        (1800, 100),   # 20 min: Hold at 100 users
        (2400, 500),   # 10 min: Ramp to 500 users
        (3600, 500),   # 20 min: Hold at 500 users
        (4200, 1000),  # 10 min: Ramp to 1000 users (peak)
        (5400, 1000),  # 20 min: Hold at 1000 users
        (6000, 0),     # 10 min: Ramp down to 0
    ]

    def tick(self):
        """Return user count for current time."""
        run_time = self.get_run_time()

        for duration, users in self.stages:
            if run_time < duration:
                # Calculate spawn rate (users per second)
                tick_data = (users, 10)  # 10 users/second spawn rate
                return tick_data

        return None  # End test


# Configuration
# To use the custom shape, run with: --shape-class=StagesShape
