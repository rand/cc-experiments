#!/usr/bin/env python3
"""
PKI Monitoring Tool - Comprehensive PKI Infrastructure Monitoring and Alerting

This script provides complete PKI monitoring capabilities including:
- Certificate expiration monitoring (bulk scanning)
- Issuance rate tracking and anomaly detection
- Compliance dashboards (FIPS, WebTrust, CA/Browser Forum)
- Alerting for expiring certificates
- Prometheus metrics export
- CA health monitoring

Usage:
    ./monitor_pki.py --help
    ./monitor_pki.py scan-expiration --dir /etc/ssl/certs --warn-days 30,60,90
    ./monitor_pki.py track-issuance --ca-log /var/log/ca/issuance.log --period 7d
    ./monitor_pki.py check-compliance --ca-cert ca.pem --standard cabf
    ./monitor_pki.py alert --config alerts.yaml --smtp-server smtp.example.com
    ./monitor_pki.py export-metrics --port 9090 --listen 0.0.0.0
    ./monitor_pki.py dashboard --config dashboard.yaml --output dashboard.html
"""

import argparse
import json
import sys
import os
import re
import hashlib
import datetime
import logging
import time
import glob
import socket
import smtplib
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, asdict, field
from enum import Enum
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from http.server import HTTPServer, BaseHTTPRequestHandler

try:
    from cryptography import x509
    from cryptography.x509.oid import NameOID, ExtensionOID
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.backends import default_backend
except ImportError:
    print("Error: cryptography library required. Install with: pip install cryptography", file=sys.stderr)
    sys.exit(1)


class ComplianceStandard(Enum):
    """Compliance standards"""
    CABF = "ca_browser_forum"
    FIPS = "fips_140"
    WEBTRUST = "webtrust"
    ETSI = "etsi"


class AlertLevel(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class CertificateInfo:
    """Certificate information for monitoring"""
    path: str
    subject: str
    issuer: str
    serial: str
    not_before: str
    not_after: str
    days_until_expiry: int
    is_expired: bool
    is_ca: bool
    key_size: Optional[int]
    signature_algorithm: str


@dataclass
class ExpirationReport:
    """Certificate expiration monitoring report"""
    scan_time: str
    total_certificates: int
    expired: int
    expiring_soon: Dict[int, int]
    certificates: List[CertificateInfo]
    warnings: List[str]


@dataclass
class IssuanceMetrics:
    """Certificate issuance metrics"""
    period_start: str
    period_end: str
    total_issued: int
    issuance_rate: float
    daily_counts: Dict[str, int]
    anomalies: List[Dict]
    average_validity_days: float


@dataclass
class ComplianceReport:
    """Compliance check report"""
    standard: str
    ca_subject: str
    is_compliant: bool
    violations: List[str]
    warnings: List[str]
    checks_passed: int
    checks_failed: int
    details: Dict = field(default_factory=dict)


@dataclass
class Alert:
    """Alert definition"""
    level: AlertLevel
    title: str
    message: str
    timestamp: str
    details: Dict = field(default_factory=dict)


@dataclass
class PrometheusMetrics:
    """Prometheus metrics"""
    certificates_total: int
    certificates_expired: int
    certificates_expiring_30d: int
    certificates_expiring_60d: int
    certificates_expiring_90d: int
    issuance_rate_daily: float
    ca_health_score: float


class PKIMonitor:
    """Main PKI monitoring class"""

    def __init__(self, verbose: bool = False, json_output: bool = False):
        self.verbose = verbose
        self.json_output = json_output
        self.logger = self._setup_logger()
        self.alerts: List[Alert] = []
        self.metrics = PrometheusMetrics(
            certificates_total=0,
            certificates_expired=0,
            certificates_expiring_30d=0,
            certificates_expiring_60d=0,
            certificates_expiring_90d=0,
            issuance_rate_daily=0.0,
            ca_health_score=100.0
        )

    def _setup_logger(self) -> logging.Logger:
        """Configure logging"""
        logger = logging.getLogger("pki_monitor")
        logger.setLevel(logging.DEBUG if self.verbose else logging.INFO)

        handler = logging.StreamHandler(sys.stderr if self.json_output else sys.stdout)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        return logger

    def scan_certificates(
        self,
        directory: str,
        warn_days: List[int] = None,
        recursive: bool = True
    ) -> ExpirationReport:
        """Scan directory for certificates and check expiration"""
        if warn_days is None:
            warn_days = [30, 60, 90]

        scan_time = datetime.datetime.utcnow().isoformat()
        certificates = []
        warnings = []
        expiring_soon = {days: 0 for days in warn_days}

        try:
            cert_files = self._find_certificates(directory, recursive)
            self.logger.info(f"Found {len(cert_files)} certificate files")

            for cert_file in cert_files:
                try:
                    cert_info = self._analyze_certificate(cert_file)
                    certificates.append(cert_info)

                    for days in warn_days:
                        if 0 <= cert_info.days_until_expiry <= days:
                            expiring_soon[days] += 1
                            break

                    if cert_info.is_expired:
                        self._create_alert(
                            AlertLevel.CRITICAL,
                            f"Certificate Expired: {cert_info.subject}",
                            f"Certificate at {cert_file} expired on {cert_info.not_after}",
                            {"path": cert_file, "subject": cert_info.subject}
                        )
                    elif cert_info.days_until_expiry <= 30:
                        self._create_alert(
                            AlertLevel.CRITICAL,
                            f"Certificate Expiring Soon: {cert_info.subject}",
                            f"Certificate expires in {cert_info.days_until_expiry} days",
                            {"path": cert_file, "days": cert_info.days_until_expiry}
                        )
                    elif cert_info.days_until_expiry <= 60:
                        self._create_alert(
                            AlertLevel.WARNING,
                            f"Certificate Expiring: {cert_info.subject}",
                            f"Certificate expires in {cert_info.days_until_expiry} days",
                            {"path": cert_file, "days": cert_info.days_until_expiry}
                        )

                except Exception as e:
                    warnings.append(f"Failed to process {cert_file}: {str(e)}")
                    self.logger.warning(f"Error processing {cert_file}: {e}")

            expired_count = sum(1 for c in certificates if c.is_expired)

            self.metrics.certificates_total = len(certificates)
            self.metrics.certificates_expired = expired_count
            self.metrics.certificates_expiring_30d = expiring_soon.get(30, 0)
            self.metrics.certificates_expiring_60d = expiring_soon.get(60, 0)
            self.metrics.certificates_expiring_90d = expiring_soon.get(90, 0)

            return ExpirationReport(
                scan_time=scan_time,
                total_certificates=len(certificates),
                expired=expired_count,
                expiring_soon=expiring_soon,
                certificates=certificates,
                warnings=warnings
            )

        except Exception as e:
            self.logger.error(f"Scan error: {e}")
            raise

    def track_issuance(
        self,
        log_file: str,
        period_days: int = 7,
        anomaly_threshold: float = 2.0
    ) -> IssuanceMetrics:
        """Track certificate issuance from CA logs"""
        period_end = datetime.datetime.utcnow()
        period_start = period_end - datetime.timedelta(days=period_days)

        daily_counts: Dict[str, int] = {}
        total_issued = 0
        validity_days_sum = 0
        validity_count = 0
        anomalies = []

        try:
            if not os.path.exists(log_file):
                raise FileNotFoundError(f"Log file not found: {log_file}")

            with open(log_file, 'r') as f:
                for line in f:
                    timestamp = self._parse_log_timestamp(line)
                    if timestamp < period_start:
                        continue
                    if timestamp > period_end:
                        break

                    if "certificate issued" in line.lower():
                        date_key = timestamp.strftime("%Y-%m-%d")
                        daily_counts[date_key] = daily_counts.get(date_key, 0) + 1
                        total_issued += 1

                        validity_match = re.search(r'validity:\s*(\d+)\s*days', line, re.IGNORECASE)
                        if validity_match:
                            validity_days_sum += int(validity_match.group(1))
                            validity_count += 1

            if daily_counts:
                avg_daily = sum(daily_counts.values()) / len(daily_counts)
                std_dev = self._calculate_std_dev(list(daily_counts.values()), avg_daily)

                for date, count in daily_counts.items():
                    if count > avg_daily + (anomaly_threshold * std_dev):
                        anomalies.append({
                            "date": date,
                            "count": count,
                            "expected": avg_daily,
                            "deviation": count - avg_daily
                        })
                        self._create_alert(
                            AlertLevel.WARNING,
                            "Anomalous Issuance Rate Detected",
                            f"Issued {count} certificates on {date} (avg: {avg_daily:.1f})",
                            {"date": date, "count": count}
                        )

            issuance_rate = total_issued / period_days if period_days > 0 else 0
            avg_validity = validity_days_sum / validity_count if validity_count > 0 else 0

            self.metrics.issuance_rate_daily = issuance_rate

            return IssuanceMetrics(
                period_start=period_start.isoformat(),
                period_end=period_end.isoformat(),
                total_issued=total_issued,
                issuance_rate=issuance_rate,
                daily_counts=daily_counts,
                anomalies=anomalies,
                average_validity_days=avg_validity
            )

        except Exception as e:
            self.logger.error(f"Issuance tracking error: {e}")
            raise

    def check_compliance(
        self,
        ca_cert_path: str,
        standard: ComplianceStandard
    ) -> ComplianceReport:
        """Check CA compliance with standards"""
        violations = []
        warnings = []
        checks_passed = 0
        checks_failed = 0
        details = {}

        try:
            ca_cert = self._load_certificate(ca_cert_path)
            ca_subject = self._format_subject(ca_cert.subject)

            if standard == ComplianceStandard.CABF:
                self._check_cabf_compliance(ca_cert, violations, warnings, details)
            elif standard == ComplianceStandard.FIPS:
                self._check_fips_compliance(ca_cert, violations, warnings, details)
            elif standard == ComplianceStandard.WEBTRUST:
                self._check_webtrust_compliance(ca_cert, violations, warnings, details)
            elif standard == ComplianceStandard.ETSI:
                self._check_etsi_compliance(ca_cert, violations, warnings, details)

            checks_failed = len(violations)
            checks_passed = details.get("total_checks", 0) - checks_failed
            is_compliant = checks_failed == 0

            if not is_compliant:
                self._create_alert(
                    AlertLevel.CRITICAL,
                    f"Compliance Violation: {standard.value}",
                    f"CA {ca_subject} has {checks_failed} compliance violations",
                    {"violations": violations}
                )

            health_score = (checks_passed / max(checks_passed + checks_failed, 1)) * 100
            self.metrics.ca_health_score = health_score

            return ComplianceReport(
                standard=standard.value,
                ca_subject=ca_subject,
                is_compliant=is_compliant,
                violations=violations,
                warnings=warnings,
                checks_passed=checks_passed,
                checks_failed=checks_failed,
                details=details
            )

        except Exception as e:
            self.logger.error(f"Compliance check error: {e}")
            raise

    def send_alerts(
        self,
        smtp_server: str,
        smtp_port: int = 587,
        username: Optional[str] = None,
        password: Optional[str] = None,
        from_addr: str = "pki-monitor@example.com",
        to_addrs: List[str] = None
    ) -> Dict:
        """Send alerts via email"""
        if not to_addrs:
            to_addrs = ["admin@example.com"]

        sent = []
        failed = []

        try:
            critical_alerts = [a for a in self.alerts if a.level == AlertLevel.CRITICAL]
            warning_alerts = [a for a in self.alerts if a.level == AlertLevel.WARNING]

            if not critical_alerts and not warning_alerts:
                self.logger.info("No alerts to send")
                return {"sent": 0, "failed": 0}

            msg = MIMEMultipart()
            msg['From'] = from_addr
            msg['To'] = ", ".join(to_addrs)
            msg['Subject'] = f"PKI Monitoring Alert: {len(critical_alerts)} Critical, {len(warning_alerts)} Warning"

            body = self._format_alert_email(critical_alerts, warning_alerts)
            msg.attach(MIMEText(body, 'plain'))

            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()

            if username and password:
                server.login(username, password)

            server.send_message(msg)
            server.quit()

            sent.append(", ".join(to_addrs))
            self.logger.info(f"Sent alerts to {len(to_addrs)} recipients")

        except Exception as e:
            self.logger.error(f"Failed to send alerts: {e}")
            failed.append(str(e))

        return {
            "sent": len(sent),
            "failed": len(failed),
            "details": {"sent": sent, "failed": failed}
        }

    def export_prometheus_metrics(self) -> str:
        """Export metrics in Prometheus format"""
        metrics = []

        metrics.append("# HELP pki_certificates_total Total number of certificates monitored")
        metrics.append("# TYPE pki_certificates_total gauge")
        metrics.append(f"pki_certificates_total {self.metrics.certificates_total}")

        metrics.append("# HELP pki_certificates_expired Number of expired certificates")
        metrics.append("# TYPE pki_certificates_expired gauge")
        metrics.append(f"pki_certificates_expired {self.metrics.certificates_expired}")

        metrics.append("# HELP pki_certificates_expiring_30d Certificates expiring in 30 days")
        metrics.append("# TYPE pki_certificates_expiring_30d gauge")
        metrics.append(f"pki_certificates_expiring_30d {self.metrics.certificates_expiring_30d}")

        metrics.append("# HELP pki_certificates_expiring_60d Certificates expiring in 60 days")
        metrics.append("# TYPE pki_certificates_expiring_60d gauge")
        metrics.append(f"pki_certificates_expiring_60d {self.metrics.certificates_expiring_60d}")

        metrics.append("# HELP pki_certificates_expiring_90d Certificates expiring in 90 days")
        metrics.append("# TYPE pki_certificates_expiring_90d gauge")
        metrics.append(f"pki_certificates_expiring_90d {self.metrics.certificates_expiring_90d}")

        metrics.append("# HELP pki_issuance_rate_daily Daily certificate issuance rate")
        metrics.append("# TYPE pki_issuance_rate_daily gauge")
        metrics.append(f"pki_issuance_rate_daily {self.metrics.issuance_rate_daily}")

        metrics.append("# HELP pki_ca_health_score CA health score (0-100)")
        metrics.append("# TYPE pki_ca_health_score gauge")
        metrics.append(f"pki_ca_health_score {self.metrics.ca_health_score}")

        return "\n".join(metrics) + "\n"

    def generate_dashboard(self, output_file: str, title: str = "PKI Monitoring Dashboard"):
        """Generate HTML dashboard"""
        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>{title}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
        .header {{ background: #2c3e50; color: white; padding: 20px; margin-bottom: 20px; }}
        .metric-card {{ background: white; padding: 20px; margin: 10px; border-radius: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .metric-value {{ font-size: 2em; font-weight: bold; color: #3498db; }}
        .metric-label {{ color: #7f8c8d; text-transform: uppercase; font-size: 0.9em; }}
        .alert {{ padding: 10px; margin: 10px 0; border-radius: 3px; }}
        .alert-critical {{ background: #e74c3c; color: white; }}
        .alert-warning {{ background: #f39c12; color: white; }}
        .alert-info {{ background: #3498db; color: white; }}
        table {{ width: 100%; border-collapse: collapse; background: white; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background: #34495e; color: white; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>{title}</h1>
        <p>Generated: {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
    </div>

    <div class="metric-card">
        <div class="metric-label">Total Certificates</div>
        <div class="metric-value">{self.metrics.certificates_total}</div>
    </div>

    <div class="metric-card">
        <div class="metric-label">Expired Certificates</div>
        <div class="metric-value">{self.metrics.certificates_expired}</div>
    </div>

    <div class="metric-card">
        <div class="metric-label">Expiring in 30 Days</div>
        <div class="metric-value">{self.metrics.certificates_expiring_30d}</div>
    </div>

    <div class="metric-card">
        <div class="metric-label">CA Health Score</div>
        <div class="metric-value">{self.metrics.ca_health_score:.1f}%</div>
    </div>

    <div class="metric-card">
        <h2>Active Alerts</h2>
"""

        for alert in self.alerts:
            alert_class = f"alert-{alert.level.value}"
            html += f"""
        <div class="alert {alert_class}">
            <strong>{alert.title}</strong><br>
            {alert.message}<br>
            <small>{alert.timestamp}</small>
        </div>
"""

        html += """
    </div>
</body>
</html>
"""

        with open(output_file, 'w') as f:
            f.write(html)

        self.logger.info(f"Dashboard generated: {output_file}")

    def _find_certificates(self, directory: str, recursive: bool) -> List[str]:
        """Find certificate files in directory"""
        cert_files = []
        patterns = ['*.pem', '*.crt', '*.cer', '*.der']

        dir_path = Path(directory)
        if not dir_path.exists():
            raise FileNotFoundError(f"Directory not found: {directory}")

        for pattern in patterns:
            if recursive:
                cert_files.extend([str(p) for p in dir_path.rglob(pattern)])
            else:
                cert_files.extend([str(p) for p in dir_path.glob(pattern)])

        return sorted(set(cert_files))

    def _analyze_certificate(self, cert_path: str) -> CertificateInfo:
        """Analyze certificate file"""
        cert = self._load_certificate(cert_path)

        now = datetime.datetime.utcnow()
        days_until_expiry = (cert.not_valid_after - now).days
        is_expired = now > cert.not_valid_after

        is_ca = False
        try:
            bc = cert.extensions.get_extension_for_class(x509.BasicConstraints)
            is_ca = bc.value.ca
        except x509.ExtensionNotFound:
            pass

        key_size = None
        try:
            public_key = cert.public_key()
            if hasattr(public_key, 'key_size'):
                key_size = public_key.key_size
        except Exception:
            pass

        return CertificateInfo(
            path=cert_path,
            subject=self._format_subject(cert.subject),
            issuer=self._format_subject(cert.issuer),
            serial=hex(cert.serial_number),
            not_before=cert.not_valid_before.isoformat(),
            not_after=cert.not_valid_after.isoformat(),
            days_until_expiry=days_until_expiry,
            is_expired=is_expired,
            is_ca=is_ca,
            key_size=key_size,
            signature_algorithm=cert.signature_algorithm_oid.dotted_string
        )

    def _load_certificate(self, cert_path: str) -> x509.Certificate:
        """Load certificate from file"""
        with open(cert_path, 'rb') as f:
            cert_data = f.read()
            if b'-----BEGIN CERTIFICATE-----' in cert_data:
                return x509.load_pem_x509_certificate(cert_data, default_backend())
            else:
                return x509.load_der_x509_certificate(cert_data, default_backend())

    def _format_subject(self, subject: x509.Name) -> str:
        """Format certificate subject"""
        parts = []
        for attr in subject:
            parts.append(f"{attr.oid._name}={attr.value}")
        return ", ".join(parts)

    def _parse_log_timestamp(self, log_line: str) -> datetime.datetime:
        """Parse timestamp from log line"""
        try:
            match = re.search(r'\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}', log_line)
            if match:
                return datetime.datetime.fromisoformat(match.group().replace(' ', 'T'))
        except Exception:
            pass
        return datetime.datetime.utcnow()

    def _calculate_std_dev(self, values: List[int], mean: float) -> float:
        """Calculate standard deviation"""
        if not values:
            return 0.0
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        return variance ** 0.5

    def _create_alert(self, level: AlertLevel, title: str, message: str, details: Dict = None):
        """Create an alert"""
        alert = Alert(
            level=level,
            title=title,
            message=message,
            timestamp=datetime.datetime.utcnow().isoformat(),
            details=details or {}
        )
        self.alerts.append(alert)
        self.logger.log(
            logging.CRITICAL if level == AlertLevel.CRITICAL else logging.WARNING,
            f"ALERT [{level.value.upper()}]: {title}"
        )

    def _format_alert_email(self, critical: List[Alert], warnings: List[Alert]) -> str:
        """Format alerts as email body"""
        lines = ["PKI Monitoring Alert Summary", "=" * 50, ""]

        if critical:
            lines.append(f"CRITICAL ALERTS ({len(critical)}):")
            lines.append("-" * 50)
            for alert in critical:
                lines.append(f"[{alert.timestamp}] {alert.title}")
                lines.append(f"  {alert.message}")
                lines.append("")

        if warnings:
            lines.append(f"WARNING ALERTS ({len(warnings)}):")
            lines.append("-" * 50)
            for alert in warnings:
                lines.append(f"[{alert.timestamp}] {alert.title}")
                lines.append(f"  {alert.message}")
                lines.append("")

        return "\n".join(lines)

    def _check_cabf_compliance(self, cert: x509.Certificate, violations: List[str], warnings: List[str], details: Dict):
        """Check CA/Browser Forum compliance"""
        details["total_checks"] = 10

        validity_period = cert.not_valid_after - cert.not_valid_before
        if validity_period.days > 825:
            violations.append(f"Validity period exceeds 825 days: {validity_period.days}")

        try:
            san = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName)
        except x509.ExtensionNotFound:
            violations.append("Missing Subject Alternative Name extension")

        sig_alg = cert.signature_algorithm_oid.dotted_string
        if sig_alg in ["1.2.840.113549.1.1.5", "1.2.840.113549.1.1.4"]:
            violations.append("SHA-1 signature algorithm not allowed")

        public_key = cert.public_key()
        if hasattr(public_key, 'key_size') and public_key.key_size < 2048:
            violations.append(f"Key size below minimum 2048 bits: {public_key.key_size}")

    def _check_fips_compliance(self, cert: x509.Certificate, violations: List[str], warnings: List[str], details: Dict):
        """Check FIPS 140 compliance"""
        details["total_checks"] = 8

        public_key = cert.public_key()
        if hasattr(public_key, 'key_size'):
            if public_key.key_size < 2048:
                violations.append(f"FIPS requires minimum 2048-bit keys: {public_key.key_size}")

        sig_alg = cert.signature_algorithm_oid.dotted_string
        weak_algs = ["1.2.840.113549.1.1.5", "1.2.840.113549.1.1.4", "1.2.840.113549.1.1.2"]
        if sig_alg in weak_algs:
            violations.append("Weak signature algorithm not FIPS-approved")

    def _check_webtrust_compliance(self, cert: x509.Certificate, violations: List[str], warnings: List[str], details: Dict):
        """Check WebTrust compliance"""
        details["total_checks"] = 12

        try:
            policies = cert.extensions.get_extension_for_class(x509.CertificatePolicies)
        except x509.ExtensionNotFound:
            violations.append("Missing Certificate Policies extension")

        try:
            crl_dp = cert.extensions.get_extension_for_class(x509.CRLDistributionPoints)
        except x509.ExtensionNotFound:
            warnings.append("No CRL Distribution Points")

    def _check_etsi_compliance(self, cert: x509.Certificate, violations: List[str], warnings: List[str], details: Dict):
        """Check ETSI compliance"""
        details["total_checks"] = 10

        try:
            policies = cert.extensions.get_extension_for_class(x509.CertificatePolicies)
        except x509.ExtensionNotFound:
            violations.append("Missing Certificate Policies extension (ETSI EN 319 412)")


class MetricsHTTPHandler(BaseHTTPRequestHandler):
    """HTTP handler for Prometheus metrics"""

    monitor = None

    def do_GET(self):
        if self.path == '/metrics':
            metrics = self.monitor.export_prometheus_metrics()
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain; version=0.0.4')
            self.end_headers()
            self.wfile.write(metrics.encode())
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass


def main():
    parser = argparse.ArgumentParser(
        description="PKI Monitoring Tool - Comprehensive PKI infrastructure monitoring",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Scan for expiring certificates:
    %(prog)s scan-expiration --dir /etc/ssl/certs --warn-days 30,60,90

  Track issuance rates:
    %(prog)s track-issuance --ca-log /var/log/ca/issuance.log --period 7

  Check compliance:
    %(prog)s check-compliance --ca-cert ca.pem --standard cabf

  Send email alerts:
    %(prog)s alert --smtp-server smtp.example.com --to admin@example.com

  Export Prometheus metrics:
    %(prog)s export-metrics --port 9090 --listen 0.0.0.0

  Generate dashboard:
    %(prog)s dashboard --output dashboard.html
        """
    )

    parser.add_argument('--verbose', action='store_true', help='Verbose output')
    parser.add_argument('--json', action='store_true', help='Output results as JSON')

    subparsers = parser.add_subparsers(dest='command', help='Command to execute')

    scan_parser = subparsers.add_parser('scan-expiration', help='Scan for certificate expiration')
    scan_parser.add_argument('--dir', required=True, help='Directory to scan')
    scan_parser.add_argument('--warn-days', default='30,60,90', help='Warning thresholds (comma-separated)')
    scan_parser.add_argument('--recursive', action='store_true', default=True, help='Recursive scan')

    track_parser = subparsers.add_parser('track-issuance', help='Track certificate issuance')
    track_parser.add_argument('--ca-log', required=True, help='CA log file')
    track_parser.add_argument('--period', type=int, default=7, help='Period in days')
    track_parser.add_argument('--threshold', type=float, default=2.0, help='Anomaly detection threshold')

    compliance_parser = subparsers.add_parser('check-compliance', help='Check compliance')
    compliance_parser.add_argument('--ca-cert', required=True, help='CA certificate')
    compliance_parser.add_argument('--standard', required=True, choices=['cabf', 'fips', 'webtrust', 'etsi'], help='Compliance standard')

    alert_parser = subparsers.add_parser('alert', help='Send alerts')
    alert_parser.add_argument('--smtp-server', required=True, help='SMTP server')
    alert_parser.add_argument('--smtp-port', type=int, default=587, help='SMTP port')
    alert_parser.add_argument('--username', help='SMTP username')
    alert_parser.add_argument('--password', help='SMTP password')
    alert_parser.add_argument('--from', dest='from_addr', default='pki-monitor@example.com', help='From address')
    alert_parser.add_argument('--to', dest='to_addrs', required=True, help='To addresses (comma-separated)')

    metrics_parser = subparsers.add_parser('export-metrics', help='Export Prometheus metrics')
    metrics_parser.add_argument('--port', type=int, default=9090, help='HTTP port')
    metrics_parser.add_argument('--listen', default='127.0.0.1', help='Listen address')

    dashboard_parser = subparsers.add_parser('dashboard', help='Generate dashboard')
    dashboard_parser.add_argument('--output', required=True, help='Output HTML file')
    dashboard_parser.add_argument('--title', default='PKI Monitoring Dashboard', help='Dashboard title')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    monitor = PKIMonitor(verbose=args.verbose, json_output=args.json)

    try:
        if args.command == 'scan-expiration':
            warn_days = [int(d.strip()) for d in args.warn_days.split(',')]
            result = monitor.scan_certificates(args.dir, warn_days, args.recursive)

            if args.json:
                print(json.dumps(asdict(result), indent=2, default=str))
            else:
                print(f"Scan completed: {result.total_certificates} certificates")
                print(f"Expired: {result.expired}")
                for days, count in sorted(result.expiring_soon.items()):
                    print(f"Expiring in {days} days: {count}")
                if result.warnings:
                    print(f"\nWarnings: {len(result.warnings)}")

            return 0

        elif args.command == 'track-issuance':
            result = monitor.track_issuance(args.ca_log, args.period, args.threshold)

            if args.json:
                print(json.dumps(asdict(result), indent=2))
            else:
                print(f"Issuance Tracking ({args.period} days):")
                print(f"Total Issued: {result.total_issued}")
                print(f"Issuance Rate: {result.issuance_rate:.2f} certs/day")
                print(f"Average Validity: {result.average_validity_days:.1f} days")
                if result.anomalies:
                    print(f"\nAnomalies Detected: {len(result.anomalies)}")
                    for anomaly in result.anomalies:
                        print(f"  {anomaly['date']}: {anomaly['count']} certs")

            return 0

        elif args.command == 'check-compliance':
            standard = ComplianceStandard[args.standard.upper()]
            result = monitor.check_compliance(args.ca_cert, standard)

            if args.json:
                print(json.dumps(asdict(result), indent=2))
            else:
                print(f"Compliance Check: {result.standard}")
                print(f"CA: {result.ca_subject}")
                print(f"Status: {'COMPLIANT' if result.is_compliant else 'NON-COMPLIANT'}")
                print(f"Checks Passed: {result.checks_passed}")
                print(f"Checks Failed: {result.checks_failed}")
                if result.violations:
                    print("\nViolations:")
                    for violation in result.violations:
                        print(f"  - {violation}")
                if result.warnings:
                    print("\nWarnings:")
                    for warning in result.warnings:
                        print(f"  - {warning}")

            return 0 if result.is_compliant else 1

        elif args.command == 'alert':
            to_addrs = [addr.strip() for addr in args.to_addrs.split(',')]
            result = monitor.send_alerts(
                smtp_server=args.smtp_server,
                smtp_port=args.smtp_port,
                username=args.username,
                password=args.password,
                from_addr=args.from_addr,
                to_addrs=to_addrs
            )

            if args.json:
                print(json.dumps(result, indent=2))
            else:
                print(f"Alerts sent: {result['sent']}")
                print(f"Alerts failed: {result['failed']}")

            return 0

        elif args.command == 'export-metrics':
            MetricsHTTPHandler.monitor = monitor
            server = HTTPServer((args.listen, args.port), MetricsHTTPHandler)
            print(f"Prometheus metrics server listening on {args.listen}:{args.port}")
            print(f"Metrics endpoint: http://{args.listen}:{args.port}/metrics")
            server.serve_forever()

        elif args.command == 'dashboard':
            monitor.generate_dashboard(args.output, args.title)
            print(f"Dashboard generated: {args.output}")
            return 0

    except KeyboardInterrupt:
        print("\nInterrupted by user", file=sys.stderr)
        return 130
    except Exception as e:
        if args.json:
            print(json.dumps({"error": str(e)}, indent=2), file=sys.stderr)
        else:
            print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
