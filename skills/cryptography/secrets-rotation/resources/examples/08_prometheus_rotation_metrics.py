#!/usr/bin/env python3
"""
Prometheus Metrics Exporter for Secret Rotation

Demonstrates:
- Exposing rotation metrics for monitoring
- Tracking rotation success/failure rates
- Certificate expiry monitoring
- Rotation duration tracking
- Alerting integration

Prerequisites:
    pip install prometheus-client boto3 google-cloud-secret-manager cryptography

Prometheus Setup:
    # prometheus.yml
    scrape_configs:
      - job_name: 'secret-rotation'
        static_configs:
          - targets: ['localhost:8000']
        scrape_interval: 30s

Grafana Dashboard:
    - Import dashboard from grafana-dashboard.json
    - Connect to Prometheus datasource
"""

import time
import json
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional

import boto3
from cryptography import x509
from cryptography.hazmat.backends import default_backend

from prometheus_client import (
    Counter, Gauge, Histogram, Info,
    start_http_server, CollectorRegistry
)


class SecretRotationMetrics:
    """
    Prometheus metrics for secret rotation monitoring.
    """

    def __init__(self, registry: Optional[CollectorRegistry] = None):
        """
        Initialize metrics collectors.

        Args:
            registry: Prometheus registry (None for default)
        """
        self.registry = registry

        # Rotation counters
        self.rotations_total = Counter(
            'secret_rotations_total',
            'Total number of secret rotations',
            ['secret_type', 'status'],
            registry=registry
        )

        self.rotation_errors = Counter(
            'secret_rotation_errors_total',
            'Total number of rotation errors',
            ['secret_type', 'error_type'],
            registry=registry
        )

        # Rotation duration
        self.rotation_duration = Histogram(
            'secret_rotation_duration_seconds',
            'Secret rotation duration in seconds',
            ['secret_type'],
            buckets=[1, 5, 10, 30, 60, 120, 300, 600],
            registry=registry
        )

        # Certificate metrics
        self.cert_expiry_days = Gauge(
            'certificate_expiry_days',
            'Days until certificate expiration',
            ['domain', 'cert_path'],
            registry=registry
        )

        self.cert_valid = Gauge(
            'certificate_valid',
            'Certificate validity (1=valid, 0=expired)',
            ['domain', 'cert_path'],
            registry=registry
        )

        # Secret age
        self.secret_age_days = Gauge(
            'secret_age_days',
            'Days since secret was last rotated',
            ['secret_id', 'secret_type'],
            registry=registry
        )

        self.secret_rotation_needed = Gauge(
            'secret_rotation_needed',
            'Secret needs rotation (1=yes, 0=no)',
            ['secret_id', 'secret_type'],
            registry=registry
        )

        # System info
        self.rotation_info = Info(
            'secret_rotation',
            'Secret rotation system information',
            registry=registry
        )

        # Last rotation timestamp
        self.last_rotation_timestamp = Gauge(
            'secret_last_rotation_timestamp',
            'Unix timestamp of last rotation',
            ['secret_id', 'secret_type'],
            registry=registry
        )

        # Rotation success rate (sliding window)
        self.rotation_success_rate = Gauge(
            'secret_rotation_success_rate',
            'Rotation success rate (last 24h)',
            ['secret_type'],
            registry=registry
        )

    def record_rotation(self, secret_type: str, duration: float, status: str = 'success'):
        """
        Record a rotation event.

        Args:
            secret_type: Type of secret (database, api_key, certificate, etc.)
            duration: Rotation duration in seconds
            status: Rotation status (success, failed)
        """
        self.rotations_total.labels(secret_type=secret_type, status=status).inc()
        self.rotation_duration.labels(secret_type=secret_type).observe(duration)

        if status == 'failed':
            self.rotation_errors.labels(secret_type=secret_type, error_type='unknown').inc()

    def record_rotation_error(self, secret_type: str, error_type: str):
        """
        Record a rotation error.

        Args:
            secret_type: Type of secret
            error_type: Error classification (timeout, auth_failed, invalid_creds, etc.)
        """
        self.rotation_errors.labels(secret_type=secret_type, error_type=error_type).inc()
        self.rotations_total.labels(secret_type=secret_type, status='failed').inc()

    def update_secret_age(self, secret_id: str, secret_type: str, last_rotation: datetime):
        """
        Update secret age metric.

        Args:
            secret_id: Secret identifier
            secret_type: Secret type
            last_rotation: Last rotation datetime
        """
        age_days = (datetime.utcnow() - last_rotation).days
        self.secret_age_days.labels(secret_id=secret_id, secret_type=secret_type).set(age_days)

        # Update last rotation timestamp
        self.last_rotation_timestamp.labels(
            secret_id=secret_id,
            secret_type=secret_type
        ).set(last_rotation.timestamp())

    def update_certificate_expiry(self, domain: str, cert_path: str, cert_data: bytes):
        """
        Update certificate expiry metrics.

        Args:
            domain: Domain name
            cert_path: Certificate file path
            cert_data: Certificate data (PEM)
        """
        try:
            cert = x509.load_pem_x509_certificate(cert_data, default_backend())

            # Days until expiry
            days_until_expiry = (cert.not_valid_after - datetime.utcnow()).days
            self.cert_expiry_days.labels(domain=domain, cert_path=cert_path).set(days_until_expiry)

            # Valid or expired
            is_valid = 1 if datetime.utcnow() < cert.not_valid_after else 0
            self.cert_valid.labels(domain=domain, cert_path=cert_path).set(is_valid)

        except Exception as e:
            print(f"Error parsing certificate {cert_path}: {e}")
            self.cert_valid.labels(domain=domain, cert_path=cert_path).set(0)

    def check_rotation_needed(self, secret_id: str, secret_type: str,
                             max_age_days: int) -> bool:
        """
        Check if secret needs rotation.

        Args:
            secret_id: Secret identifier
            secret_type: Secret type
            max_age_days: Maximum age before rotation needed

        Returns:
            True if rotation needed
        """
        # This would query your secret manager for last rotation time
        # For demonstration, we'll use a placeholder
        needs_rotation = False  # Replace with actual check

        self.secret_rotation_needed.labels(
            secret_id=secret_id,
            secret_type=secret_type
        ).set(1 if needs_rotation else 0)

        return needs_rotation


class RotationMonitor:
    """
    Automated monitoring of rotation status and metrics.
    """

    def __init__(self, metrics: SecretRotationMetrics):
        """
        Initialize monitor.

        Args:
            metrics: Metrics instance
        """
        self.metrics = metrics
        self.aws_clients: Dict[str, boto3.client] = {}

    def add_aws_region(self, region: str):
        """Add AWS region to monitor."""
        self.aws_clients[region] = boto3.client('secretsmanager', region_name=region)

    def monitor_aws_secrets(self, region: str):
        """
        Monitor AWS Secrets Manager secrets.

        Args:
            region: AWS region
        """
        client = self.aws_clients.get(region)
        if not client:
            return

        print(f"[{datetime.utcnow().isoformat()}] Monitoring AWS secrets: {region}")

        # List all secrets
        paginator = client.get_paginator('list_secrets')

        for page in paginator.paginate():
            for secret in page['SecretList']:
                secret_id = secret['Name']

                # Get metadata
                try:
                    metadata = client.describe_secret(SecretId=secret_id)

                    # Update age metric
                    if 'LastRotatedDate' in metadata:
                        last_rotated = metadata['LastRotatedDate'].replace(tzinfo=None)
                        self.metrics.update_secret_age(
                            secret_id=secret_id,
                            secret_type='aws_secret',
                            last_rotation=last_rotated
                        )

                        # Check if rotation needed (90 days)
                        age_days = (datetime.utcnow() - last_rotated).days
                        needs_rotation = age_days > 90

                        self.metrics.secret_rotation_needed.labels(
                            secret_id=secret_id,
                            secret_type='aws_secret'
                        ).set(1 if needs_rotation else 0)

                except Exception as e:
                    print(f"  Error checking {secret_id}: {e}")

    def monitor_certificates(self, cert_dir: str = '/etc/letsencrypt/live'):
        """
        Monitor TLS certificates.

        Args:
            cert_dir: Certificate directory
        """
        print(f"[{datetime.utcnow().isoformat()}] Monitoring certificates: {cert_dir}")

        cert_path = Path(cert_dir)

        for cert_file in cert_path.glob('*/fullchain.pem'):
            domain = cert_file.parent.name

            try:
                cert_data = cert_file.read_bytes()
                self.metrics.update_certificate_expiry(
                    domain=domain,
                    cert_path=str(cert_file),
                    cert_data=cert_data
                )

            except Exception as e:
                print(f"  Error checking {domain}: {e}")

    def calculate_success_rates(self):
        """
        Calculate rotation success rates.

        Note: This is a placeholder. In production, you'd query
        Prometheus for historical data to calculate rates.
        """
        # Example: Query last 24h of rotations from your tracking system
        # and update success rate metric
        pass


def rotation_example_with_metrics():
    """
    Example: Secret rotation with metrics tracking.
    """
    metrics = SecretRotationMetrics()

    # Simulate database rotation
    secret_type = 'database'
    start_time = time.time()

    try:
        print(f"[{datetime.utcnow().isoformat()}] Starting rotation: {secret_type}")

        # Simulate rotation work
        time.sleep(2)

        # Success
        duration = time.time() - start_time
        metrics.record_rotation(secret_type, duration, status='success')

        print(f"  Rotation complete in {duration:.2f}s")

    except Exception as e:
        # Failure
        duration = time.time() - start_time
        metrics.record_rotation(secret_type, duration, status='failed')
        metrics.record_rotation_error(secret_type, error_type='timeout')

        print(f"  Rotation failed: {e}")


def main():
    """
    Main monitoring loop.
    """
    print("Starting Secret Rotation Metrics Exporter")

    # Initialize metrics
    metrics = SecretRotationMetrics()

    # Set system info
    metrics.rotation_info.info({
        'version': '1.0.0',
        'environment': 'production',
        'region': 'us-east-1'
    })

    # Start Prometheus HTTP server
    start_http_server(8000)
    print("Metrics server started on :8000")

    # Initialize monitor
    monitor = RotationMonitor(metrics)
    monitor.add_aws_region('us-east-1')
    monitor.add_aws_region('us-west-2')

    # Monitoring loop
    while True:
        try:
            # Monitor AWS secrets
            for region in ['us-east-1', 'us-west-2']:
                monitor.monitor_aws_secrets(region)

            # Monitor certificates
            monitor.monitor_certificates()

            # Calculate success rates
            monitor.calculate_success_rates()

            print(f"[{datetime.utcnow().isoformat()}] Monitoring cycle complete")

        except Exception as e:
            print(f"ERROR in monitoring loop: {e}")

        # Wait before next cycle (5 minutes)
        time.sleep(300)


if __name__ == '__main__':
    # Run example rotation with metrics
    rotation_example_with_metrics()

    # Start monitoring (uncomment for production)
    # main()
