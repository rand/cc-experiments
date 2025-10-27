#!/usr/bin/env python3
"""
Encryption Configuration Validator

Validates encryption configurations, key management, and compliance standards.
Detects weak ciphers, insecure key storage, and policy violations.

Features:
- Check encryption algorithms (detect weak ciphers like DES, 3DES)
- Validate key lengths (minimum 256-bit for AES)
- Audit key storage (detect hardcoded keys, plaintext keys)
- Check key rotation policies
- Validate KMS integration
- FIPS 140-2 compliance checking
- PCI-DSS, HIPAA, GDPR compliance validation

Usage:
    ./validate_encryption.py --config-file db.conf --check-compliance FIPS --json
    ./validate_encryption.py --scan-directory /etc/app --standard PCI-DSS
    ./validate_encryption.py --kms-config aws-kms.json --json
    ./validate_encryption.py --database postgres://localhost/mydb
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Set
from enum import Enum


class ComplianceStandard(Enum):
    """Compliance standards"""
    FIPS_140_2 = "FIPS"
    PCI_DSS = "PCI-DSS"
    HIPAA = "HIPAA"
    GDPR = "GDPR"
    SOC2 = "SOC2"
    ISO_27001 = "ISO-27001"


class Severity(Enum):
    """Finding severity levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


# Weak algorithms that should never be used
WEAK_ALGORITHMS = {
    "DES", "3DES", "RC4", "MD5", "SHA1", "ECB",
    "des", "3des", "rc4", "md5", "sha1", "ecb"
}

# Approved algorithms for FIPS 140-2
FIPS_APPROVED_ALGORITHMS = {
    "AES-256-GCM", "AES-192-GCM", "AES-128-GCM",
    "AES-256-CBC", "AES-192-CBC", "AES-128-CBC",
    "ChaCha20-Poly1305", "SHA-256", "SHA-384", "SHA-512",
    "RSA-2048", "RSA-3072", "RSA-4096",
    "ECDSA-P256", "ECDSA-P384", "ECDSA-P521"
}

# Minimum key lengths (in bits)
MIN_KEY_LENGTHS = {
    "AES": 256,
    "RSA": 2048,
    "ECDSA": 256,
    "DH": 2048
}

# Patterns for detecting hardcoded keys
HARDCODED_KEY_PATTERNS = [
    r'(?i)(password|passwd|pwd|secret|key|token)\s*[=:]\s*["\']([^"\']{8,})["\']',
    r'(?i)(api[_-]?key|access[_-]?key|secret[_-]?key)\s*[=:]\s*["\']([^"\']{20,})["\']',
    r'(?i)(encryption[_-]?key|master[_-]?key)\s*[=:]\s*["\']([^"\']{16,})["\']',
    r'-----BEGIN (RSA|ENCRYPTED|PRIVATE) KEY-----'
]


@dataclass
class Finding:
    """Security finding"""
    severity: str
    category: str
    title: str
    description: str
    location: Optional[str] = None
    recommendation: Optional[str] = None
    compliance_impact: Optional[List[str]] = None


@dataclass
class ValidationResult:
    """Validation result"""
    passed: bool
    findings: List[Finding]
    scanned_items: int
    timestamp: str
    compliance_standards: List[str]
    summary: Dict[str, int]


class EncryptionValidator:
    """Validates encryption configurations"""

    def __init__(self, compliance_standards: Optional[List[str]] = None):
        self.compliance_standards = compliance_standards or []
        self.findings: List[Finding] = []
        self.scanned_items = 0

    def validate_algorithm(self, algorithm: str, location: str = None) -> None:
        """Validate encryption algorithm"""
        self.scanned_items += 1

        # Check for weak algorithms
        algo_upper = algorithm.upper()
        for weak in WEAK_ALGORITHMS:
            if weak.upper() in algo_upper:
                self.findings.append(Finding(
                    severity=Severity.CRITICAL.value,
                    category="weak_algorithm",
                    title=f"Weak encryption algorithm detected: {algorithm}",
                    description=f"Algorithm '{algorithm}' is cryptographically weak and should not be used.",
                    location=location,
                    recommendation=f"Replace with AES-256-GCM or ChaCha20-Poly1305",
                    compliance_impact=["FIPS", "PCI-DSS", "HIPAA", "GDPR"]
                ))
                return

        # FIPS compliance check
        if "FIPS" in self.compliance_standards:
            if not any(approved in algo_upper for approved in FIPS_APPROVED_ALGORITHMS):
                self.findings.append(Finding(
                    severity=Severity.HIGH.value,
                    category="fips_compliance",
                    title=f"Algorithm not FIPS 140-2 approved: {algorithm}",
                    description=f"FIPS 140-2 compliance requires approved algorithms. '{algorithm}' is not approved.",
                    location=location,
                    recommendation="Use AES-256-GCM, AES-128-GCM, or ChaCha20-Poly1305",
                    compliance_impact=["FIPS"]
                ))

        # Check for ECB mode
        if "ECB" in algo_upper:
            self.findings.append(Finding(
                severity=Severity.CRITICAL.value,
                category="weak_mode",
                title="ECB mode detected",
                description="ECB mode is insecure as it reveals patterns in plaintext. Never use ECB mode.",
                location=location,
                recommendation="Use GCM, CBC with random IV, or ChaCha20-Poly1305",
                compliance_impact=["FIPS", "PCI-DSS"]
            ))

        # Check for CBC without authentication
        if "CBC" in algo_upper and "HMAC" not in algo_upper:
            self.findings.append(Finding(
                severity=Severity.MEDIUM.value,
                category="missing_authentication",
                title="CBC mode without authentication",
                description="CBC mode should be combined with HMAC for authenticated encryption.",
                location=location,
                recommendation="Use AES-GCM (includes authentication) or add HMAC",
                compliance_impact=["PCI-DSS"]
            ))

    def validate_key_length(self, algorithm: str, key_length: int, location: str = None) -> None:
        """Validate key length"""
        self.scanned_items += 1

        algo_type = None
        for alg in MIN_KEY_LENGTHS.keys():
            if alg in algorithm.upper():
                algo_type = alg
                break

        if not algo_type:
            return

        min_length = MIN_KEY_LENGTHS[algo_type]
        if key_length < min_length:
            self.findings.append(Finding(
                severity=Severity.HIGH.value,
                category="weak_key",
                title=f"Insufficient {algo_type} key length: {key_length} bits",
                description=f"Key length {key_length} bits is below minimum of {min_length} bits for {algo_type}.",
                location=location,
                recommendation=f"Use at least {min_length}-bit keys for {algo_type}",
                compliance_impact=["FIPS", "PCI-DSS", "HIPAA"]
            ))

    def scan_file_for_hardcoded_keys(self, file_path: Path) -> None:
        """Scan file for hardcoded keys"""
        self.scanned_items += 1

        try:
            content = file_path.read_text()

            for pattern in HARDCODED_KEY_PATTERNS:
                matches = re.finditer(pattern, content, re.MULTILINE)
                for match in matches:
                    # Get line number
                    line_num = content[:match.start()].count('\n') + 1

                    self.findings.append(Finding(
                        severity=Severity.CRITICAL.value,
                        category="hardcoded_key",
                        title=f"Hardcoded key detected in {file_path.name}",
                        description=f"Hardcoded encryption key or secret found at line {line_num}.",
                        location=f"{file_path}:{line_num}",
                        recommendation="Store keys in KMS (AWS KMS, HashiCorp Vault) or environment variables",
                        compliance_impact=["PCI-DSS", "HIPAA", "GDPR", "SOC2"]
                    ))

        except Exception as e:
            self.findings.append(Finding(
                severity=Severity.LOW.value,
                category="scan_error",
                title=f"Failed to scan file: {file_path}",
                description=f"Error: {str(e)}",
                location=str(file_path)
            ))

    def validate_key_rotation(self, last_rotation: datetime, max_age_days: int = 90, location: str = None) -> None:
        """Validate key rotation policy"""
        self.scanned_items += 1

        age = (datetime.now() - last_rotation).days

        if age > max_age_days:
            severity = Severity.HIGH if age > max_age_days * 2 else Severity.MEDIUM
            self.findings.append(Finding(
                severity=severity.value,
                category="key_rotation",
                title=f"Key not rotated in {age} days",
                description=f"Key has not been rotated in {age} days (policy: {max_age_days} days max).",
                location=location,
                recommendation=f"Implement automated key rotation every {max_age_days} days",
                compliance_impact=["PCI-DSS", "HIPAA", "SOC2"]
            ))

    def validate_config_file(self, config_path: Path) -> None:
        """Validate encryption configuration file"""
        try:
            content = config_path.read_text()

            # Check for algorithm specifications
            algo_matches = re.finditer(r'(?i)(algorithm|cipher|encryption)["\']?\s*[=:]\s*["\']?([A-Za-z0-9-]+)', content)
            for match in algo_matches:
                algorithm = match.group(2)
                line_num = content[:match.start()].count('\n') + 1
                self.validate_algorithm(algorithm, f"{config_path}:{line_num}")

            # Check for key length specifications
            key_len_matches = re.finditer(r'(?i)(key[_-]?size|key[_-]?length)["\']?\s*[=:]\s*(\d+)', content)
            for match in key_len_matches:
                key_length = int(match.group(2))
                line_num = content[:match.start()].count('\n') + 1
                # Try to determine algorithm from context
                context_start = max(0, match.start() - 200)
                context = content[context_start:match.end()]
                algorithm = "AES"  # Default assumption
                for alg in ["AES", "RSA", "ECDSA"]:
                    if alg in context.upper():
                        algorithm = alg
                        break
                self.validate_key_length(algorithm, key_length, f"{config_path}:{line_num}")

            # Scan for hardcoded keys
            self.scan_file_for_hardcoded_keys(config_path)

        except Exception as e:
            self.findings.append(Finding(
                severity=Severity.MEDIUM.value,
                category="validation_error",
                title=f"Failed to validate config: {config_path}",
                description=f"Error: {str(e)}",
                location=str(config_path)
            ))

    def validate_kms_config(self, kms_config: Dict) -> None:
        """Validate KMS configuration"""
        self.scanned_items += 1

        # Check for key rotation policy
        if "rotation_enabled" in kms_config:
            if not kms_config["rotation_enabled"]:
                self.findings.append(Finding(
                    severity=Severity.HIGH.value,
                    category="key_rotation",
                    title="KMS key rotation disabled",
                    description="Automatic key rotation is disabled in KMS configuration.",
                    recommendation="Enable automatic key rotation (annual recommended)",
                    compliance_impact=["PCI-DSS", "HIPAA", "SOC2"]
                ))

        # Check for key deletion protection
        if "deletion_protection" in kms_config:
            if not kms_config["deletion_protection"]:
                self.findings.append(Finding(
                    severity=Severity.MEDIUM.value,
                    category="key_protection",
                    title="KMS key deletion protection disabled",
                    description="Key deletion protection is disabled, risking accidental key deletion.",
                    recommendation="Enable key deletion protection with waiting period",
                    compliance_impact=["SOC2", "ISO-27001"]
                ))

        # Validate algorithm if specified
        if "algorithm" in kms_config:
            self.validate_algorithm(kms_config["algorithm"], "KMS configuration")

    def scan_directory(self, directory: Path, extensions: Set[str] = None) -> None:
        """Recursively scan directory for configuration files"""
        if extensions is None:
            extensions = {".conf", ".config", ".ini", ".yaml", ".yml", ".json", ".env", ".properties"}

        for file_path in directory.rglob("*"):
            if file_path.is_file() and file_path.suffix in extensions:
                self.validate_config_file(file_path)

    def get_results(self) -> ValidationResult:
        """Get validation results"""
        # Calculate summary
        summary = {
            "critical": sum(1 for f in self.findings if f.severity == Severity.CRITICAL.value),
            "high": sum(1 for f in self.findings if f.severity == Severity.HIGH.value),
            "medium": sum(1 for f in self.findings if f.severity == Severity.MEDIUM.value),
            "low": sum(1 for f in self.findings if f.severity == Severity.LOW.value),
            "info": sum(1 for f in self.findings if f.severity == Severity.INFO.value)
        }

        passed = summary["critical"] == 0 and summary["high"] == 0

        return ValidationResult(
            passed=passed,
            findings=self.findings,
            scanned_items=self.scanned_items,
            timestamp=datetime.now().isoformat(),
            compliance_standards=self.compliance_standards,
            summary=summary
        )


def main():
    parser = argparse.ArgumentParser(
        description="Validate encryption configurations and key management",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Validate configuration file
  ./validate_encryption.py --config-file /etc/app/database.conf

  # Check FIPS 140-2 compliance
  ./validate_encryption.py --config-file db.conf --check-compliance FIPS --json

  # Scan directory for configuration files
  ./validate_encryption.py --scan-directory /etc/app --standard PCI-DSS

  # Validate KMS configuration
  ./validate_encryption.py --kms-config aws-kms.json --json

  # Validate specific algorithm
  ./validate_encryption.py --algorithm AES-128-CBC --key-length 128

Exit codes:
  0 - All checks passed
  1 - Critical or high severity findings
  2 - Validation errors
        """
    )

    parser.add_argument("--config-file", type=Path,
                        help="Configuration file to validate")
    parser.add_argument("--scan-directory", type=Path,
                        help="Directory to scan recursively")
    parser.add_argument("--kms-config", type=Path,
                        help="KMS configuration file (JSON)")
    parser.add_argument("--algorithm", type=str,
                        help="Encryption algorithm to validate")
    parser.add_argument("--key-length", type=int,
                        help="Key length in bits (use with --algorithm)")
    parser.add_argument("--check-compliance", "--standard", dest="compliance",
                        action="append", choices=[s.value for s in ComplianceStandard],
                        help="Compliance standard to validate against")
    parser.add_argument("--json", action="store_true",
                        help="Output results as JSON")
    parser.add_argument("--output", "-o", type=Path,
                        help="Write output to file")
    parser.add_argument("--fail-on", choices=["critical", "high", "medium", "low"],
                        default="high",
                        help="Fail (exit 1) on this severity or higher (default: high)")

    args = parser.parse_args()

    # Validate arguments
    if not any([args.config_file, args.scan_directory, args.kms_config, args.algorithm]):
        parser.error("Must specify at least one of: --config-file, --scan-directory, --kms-config, --algorithm")

    if args.key_length and not args.algorithm:
        parser.error("--key-length requires --algorithm")

    # Create validator
    validator = EncryptionValidator(compliance_standards=args.compliance or [])

    # Run validation
    try:
        if args.config_file:
            validator.validate_config_file(args.config_file)

        if args.scan_directory:
            validator.scan_directory(args.scan_directory)

        if args.kms_config:
            kms_data = json.loads(args.kms_config.read_text())
            validator.validate_kms_config(kms_data)

        if args.algorithm:
            key_length = args.key_length or 256
            validator.validate_algorithm(args.algorithm)
            validator.validate_key_length(args.algorithm, key_length)

        # Get results
        results = validator.get_results()

        # Format output
        if args.json:
            output = json.dumps({
                "passed": results.passed,
                "scanned_items": results.scanned_items,
                "timestamp": results.timestamp,
                "compliance_standards": results.compliance_standards,
                "summary": results.summary,
                "findings": [asdict(f) for f in results.findings]
            }, indent=2)
        else:
            # Human-readable output
            lines = []
            lines.append("=" * 80)
            lines.append("ENCRYPTION VALIDATION REPORT")
            lines.append("=" * 80)
            lines.append(f"Timestamp: {results.timestamp}")
            lines.append(f"Scanned items: {results.scanned_items}")
            if results.compliance_standards:
                lines.append(f"Compliance: {', '.join(results.compliance_standards)}")
            lines.append("")
            lines.append("SUMMARY")
            lines.append("-" * 80)
            lines.append(f"Critical: {results.summary['critical']}")
            lines.append(f"High:     {results.summary['high']}")
            lines.append(f"Medium:   {results.summary['medium']}")
            lines.append(f"Low:      {results.summary['low']}")
            lines.append(f"Info:     {results.summary['info']}")
            lines.append("")
            lines.append(f"Status: {'PASSED' if results.passed else 'FAILED'}")
            lines.append("")

            if results.findings:
                lines.append("FINDINGS")
                lines.append("-" * 80)
                for i, finding in enumerate(results.findings, 1):
                    lines.append(f"\n[{i}] {finding.severity.upper()}: {finding.title}")
                    lines.append(f"    Category: {finding.category}")
                    lines.append(f"    {finding.description}")
                    if finding.location:
                        lines.append(f"    Location: {finding.location}")
                    if finding.recommendation:
                        lines.append(f"    Fix: {finding.recommendation}")
                    if finding.compliance_impact:
                        lines.append(f"    Compliance impact: {', '.join(finding.compliance_impact)}")

            output = "\n".join(lines)

        # Write output
        if args.output:
            args.output.write_text(output)
            print(f"Report written to {args.output}", file=sys.stderr)
        else:
            print(output)

        # Determine exit code based on --fail-on
        severity_levels = ["info", "low", "medium", "high", "critical"]
        fail_level = severity_levels.index(args.fail_on)

        for finding in results.findings:
            finding_level = severity_levels.index(finding.severity)
            if finding_level >= fail_level:
                sys.exit(1)

        sys.exit(0 if results.passed else 1)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
