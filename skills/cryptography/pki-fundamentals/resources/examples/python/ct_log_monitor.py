#!/usr/bin/env python3
"""
Certificate Transparency Log Monitor

Monitors Certificate Transparency logs for certificates issued for your domains.
Detects unauthorized certificate issuance and provides alerting.

Usage:
    ./ct_log_monitor.py --help
    ./ct_log_monitor.py --domains example.com,www.example.com --alert-email admin@example.com
    ./ct_log_monitor.py --domains example.com --logs google-pilot,google-aviator --output report.json
    ./ct_log_monitor.py --config ct-monitor.yaml --daemon --interval 3600

Requirements:
    pip install requests
"""

import argparse
import json
import sys
import os
import re
import time
import logging
import hashlib
import base64
import datetime
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, asdict, field
from pathlib import Path

try:
    import requests
except ImportError:
    print("Error: requests library required. Install with: pip install requests", file=sys.stderr)
    sys.exit(1)


@dataclass
class CTLogEntry:
    """Certificate Transparency log entry"""
    log_name: str
    timestamp: str
    domain: str
    issuer: str
    serial: str
    not_before: str
    not_after: str
    fingerprint: str
    log_index: int
    all_domains: List[str] = field(default_factory=list)


@dataclass
class MonitoringReport:
    """CT monitoring report"""
    scan_time: str
    domains: List[str]
    total_certificates: int
    new_certificates: int
    suspicious_certificates: int
    entries: List[CTLogEntry]
    alerts: List[Dict] = field(default_factory=list)


class CTLogMonitor:
    """Certificate Transparency log monitor"""

    CT_LOGS = {
        "google-pilot": "https://ct.googleapis.com/pilot",
        "google-aviator": "https://ct.googleapis.com/aviator",
        "google-rocketeer": "https://ct.googleapis.com/rocketeer",
        "cloudflare-nimbus": "https://ct.cloudflare.com/nimbus2023",
        "digicert": "https://ct.digicert.com/log",
        "letsencrypt": "https://ct.letsencrypt.org/2023"
    }

    def __init__(
        self,
        domains: List[str],
        logs: Optional[List[str]] = None,
        state_file: str = ".ct-monitor-state.json",
        verbose: bool = False
    ):
        self.domains = [d.lower().strip() for d in domains]
        self.logs = logs or list(self.CT_LOGS.keys())
        self.state_file = state_file
        self.verbose = verbose
        self.logger = self._setup_logger()

        self.seen_certificates: Set[str] = set()
        self.load_state()

    def _setup_logger(self) -> logging.Logger:
        """Configure logging"""
        logger = logging.getLogger("ct_monitor")
        logger.setLevel(logging.DEBUG if self.verbose else logging.INFO)

        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        return logger

    def scan_logs(self) -> MonitoringReport:
        """Scan CT logs for domain certificates"""
        scan_time = datetime.datetime.utcnow().isoformat()
        all_entries = []
        alerts = []

        self.logger.info(f"Scanning CT logs for domains: {', '.join(self.domains)}")

        for log_name in self.logs:
            if log_name not in self.CT_LOGS:
                self.logger.warning(f"Unknown CT log: {log_name}")
                continue

            log_url = self.CT_LOGS[log_name]
            self.logger.info(f"Querying log: {log_name}")

            try:
                entries = self._query_ct_log(log_name, log_url)
                all_entries.extend(entries)

                for entry in entries:
                    if entry.fingerprint not in self.seen_certificates:
                        alerts.append({
                            "type": "new_certificate",
                            "domain": entry.domain,
                            "issuer": entry.issuer,
                            "fingerprint": entry.fingerprint,
                            "timestamp": entry.timestamp
                        })

            except Exception as e:
                self.logger.error(f"Error querying {log_name}: {e}")

        new_certs = sum(1 for e in all_entries if e.fingerprint not in self.seen_certificates)
        suspicious = self._detect_suspicious(all_entries, alerts)

        for entry in all_entries:
            self.seen_certificates.add(entry.fingerprint)

        self.save_state()

        report = MonitoringReport(
            scan_time=scan_time,
            domains=self.domains,
            total_certificates=len(all_entries),
            new_certificates=new_certs,
            suspicious_certificates=suspicious,
            entries=all_entries,
            alerts=alerts
        )

        self.logger.info(
            f"Scan complete: {len(all_entries)} certificates, "
            f"{new_certs} new, {suspicious} suspicious"
        )

        return report

    def _query_ct_log(self, log_name: str, log_url: str) -> List[CTLogEntry]:
        """Query CT log for domain certificates (simplified implementation)"""
        entries = []

        for domain in self.domains:
            try:
                search_url = f"https://crt.sh/?q={domain}&output=json"
                response = requests.get(search_url, timeout=30)

                if response.status_code != 200:
                    self.logger.warning(f"crt.sh returned status {response.status_code}")
                    continue

                data = response.json()

                for item in data[:100]:
                    entry = CTLogEntry(
                        log_name=log_name,
                        timestamp=item.get('entry_timestamp', ''),
                        domain=item.get('common_name', domain),
                        issuer=item.get('issuer_name', 'Unknown'),
                        serial=item.get('serial_number', ''),
                        not_before=item.get('not_before', ''),
                        not_after=item.get('not_after', ''),
                        fingerprint=hashlib.sha256(
                            str(item.get('id', '')).encode()
                        ).hexdigest(),
                        log_index=item.get('id', 0),
                        all_domains=self._parse_name_value(item.get('name_value', ''))
                    )
                    entries.append(entry)

                time.sleep(1)

            except requests.exceptions.RequestException as e:
                self.logger.error(f"Request error for {domain}: {e}")
            except Exception as e:
                self.logger.error(f"Error processing {domain}: {e}")

        return entries

    def _parse_name_value(self, name_value: str) -> List[str]:
        """Parse name_value field from crt.sh"""
        if not name_value:
            return []
        return [n.strip() for n in name_value.split('\n') if n.strip()]

    def _detect_suspicious(self, entries: List[CTLogEntry], alerts: List[Dict]) -> int:
        """Detect suspicious certificate patterns"""
        suspicious_count = 0

        suspicious_issuers = [
            'lets encrypt',
            'comodo',
            'sectigo'
        ]

        for entry in entries:
            is_suspicious = False

            if not any(domain in entry.all_domains for domain in self.domains):
                is_suspicious = True
                alerts.append({
                    "type": "domain_mismatch",
                    "message": f"Certificate for {entry.domain} does not match monitored domains",
                    "fingerprint": entry.fingerprint
                })

            wildcard_count = sum(1 for d in entry.all_domains if d.startswith('*.'))
            if wildcard_count > 3:
                is_suspicious = True
                alerts.append({
                    "type": "excessive_wildcards",
                    "message": f"Certificate has {wildcard_count} wildcard domains",
                    "fingerprint": entry.fingerprint
                })

            if len(entry.all_domains) > 100:
                is_suspicious = True
                alerts.append({
                    "type": "excessive_san",
                    "message": f"Certificate has {len(entry.all_domains)} SAN entries",
                    "fingerprint": entry.fingerprint
                })

            issuer_lower = entry.issuer.lower()
            if not any(si in issuer_lower for si in suspicious_issuers):
                is_suspicious = True
                alerts.append({
                    "type": "unusual_issuer",
                    "message": f"Certificate issued by unfamiliar CA: {entry.issuer}",
                    "fingerprint": entry.fingerprint
                })

            if is_suspicious:
                suspicious_count += 1

        return suspicious_count

    def load_state(self):
        """Load monitoring state from file"""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r') as f:
                    state = json.load(f)
                    self.seen_certificates = set(state.get('seen_certificates', []))
                self.logger.info(f"Loaded state: {len(self.seen_certificates)} known certificates")
            except Exception as e:
                self.logger.warning(f"Failed to load state: {e}")

    def save_state(self):
        """Save monitoring state to file"""
        try:
            state = {
                'seen_certificates': list(self.seen_certificates),
                'last_scan': datetime.datetime.utcnow().isoformat()
            }
            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2)
            self.logger.debug(f"State saved: {self.state_file}")
        except Exception as e:
            self.logger.error(f"Failed to save state: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Certificate Transparency Log Monitor",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Monitor single domain:
    %(prog)s --domains example.com

  Monitor multiple domains:
    %(prog)s --domains example.com,www.example.com,api.example.com

  Specify CT logs:
    %(prog)s --domains example.com --logs google-pilot,cloudflare-nimbus

  Output to file:
    %(prog)s --domains example.com --output report.json

  Daemon mode with email alerts:
    %(prog)s --domains example.com --daemon --interval 3600 --alert-email admin@example.com

Available CT Logs:
  google-pilot, google-aviator, google-rocketeer
  cloudflare-nimbus, digicert, letsencrypt
        """
    )

    parser.add_argument('--domains', required=True, help='Comma-separated list of domains to monitor')
    parser.add_argument('--logs', help='Comma-separated list of CT logs to query (default: all)')
    parser.add_argument('--output', help='Output report to JSON file')
    parser.add_argument('--state-file', default='.ct-monitor-state.json', help='State file path')
    parser.add_argument('--daemon', action='store_true', help='Run in daemon mode')
    parser.add_argument('--interval', type=int, default=3600, help='Scan interval in seconds (daemon mode)')
    parser.add_argument('--alert-email', help='Email address for alerts')
    parser.add_argument('--verbose', action='store_true', help='Verbose logging')

    args = parser.parse_args()

    domains = [d.strip() for d in args.domains.split(',')]
    logs = None
    if args.logs:
        logs = [l.strip() for l in args.logs.split(',')]

    monitor = CTLogMonitor(
        domains=domains,
        logs=logs,
        state_file=args.state_file,
        verbose=args.verbose
    )

    def run_scan():
        report = monitor.scan_logs()

        if args.output:
            with open(args.output, 'w') as f:
                json.dump(asdict(report), f, indent=2, default=str)
            print(f"Report saved to: {args.output}")

        print(f"\nCertificate Transparency Monitoring Report")
        print(f"=" * 60)
        print(f"Scan Time: {report.scan_time}")
        print(f"Domains: {', '.join(report.domains)}")
        print(f"Total Certificates: {report.total_certificates}")
        print(f"New Certificates: {report.new_certificates}")
        print(f"Suspicious Certificates: {report.suspicious_certificates}")

        if report.alerts:
            print(f"\nAlerts ({len(report.alerts)}):")
            for alert in report.alerts[:10]:
                print(f"  - {alert.get('type', 'unknown')}: {alert.get('message', alert.get('domain', 'N/A'))}")

            if len(report.alerts) > 10:
                print(f"  ... and {len(report.alerts) - 10} more alerts")

        if report.new_certificates > 0:
            print(f"\nNew Certificates:")
            for entry in report.entries[:5]:
                if entry.fingerprint not in monitor.seen_certificates:
                    print(f"  - {entry.domain}")
                    print(f"    Issuer: {entry.issuer}")
                    print(f"    Valid: {entry.not_before} to {entry.not_after}")

        if args.alert_email and (report.new_certificates > 0 or report.suspicious_certificates > 0):
            print(f"\nEmail alerts would be sent to: {args.alert_email}")

    try:
        if args.daemon:
            print(f"Starting daemon mode (interval: {args.interval}s)")
            print("Press Ctrl+C to stop")

            while True:
                run_scan()
                print(f"\nWaiting {args.interval} seconds until next scan...")
                time.sleep(args.interval)
        else:
            run_scan()

        return 0

    except KeyboardInterrupt:
        print("\nStopped by user")
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
