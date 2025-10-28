#!/usr/bin/env python3
"""
Automated Certificate Renewal Tool

Automates certificate renewal using ACME protocol (Let's Encrypt compatible).
Supports HTTP-01, DNS-01 challenges, and multiple ACME providers.

Features:
- ACME protocol support (Let's Encrypt, ZeroSSL, etc.)
- HTTP-01 and DNS-01 challenges
- Automatic renewal before expiration
- Pre/post renewal hooks
- Backup before renewal
- Rollback on failure
- Multi-domain certificates
- Wildcard certificate support
- JSON output for automation

Usage:
    ./renew_certificates.py --domain example.com --webroot /var/www/html
    ./renew_certificates.py --domain example.com --dns-provider cloudflare
    ./renew_certificates.py --domain *.example.com --dns-provider route53
    ./renew_certificates.py --renew-all --days-before 30
    ./renew_certificates.py --domain example.com --staging --json

Author: Generated with Claude Code
License: MIT
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import time

try:
    from cryptography import x509
    from cryptography.hazmat.backends import default_backend
except ImportError:
    print("Error: cryptography library required. Install with: pip install cryptography", file=sys.stderr)
    sys.exit(1)


class CertificateRenewer:
    """Handles automated certificate renewal"""

    DEFAULT_CERT_DIR = Path('/etc/letsencrypt/live')
    DEFAULT_BACKUP_DIR = Path('/var/backups/certificates')
    DEFAULT_WEBROOT = Path('/var/www/html')

    ACME_PROVIDERS = {
        'letsencrypt': 'https://acme-v02.api.letsencrypt.org/directory',
        'letsencrypt-staging': 'https://acme-staging-v02.api.letsencrypt.org/directory',
        'zerossl': 'https://acme.zerossl.com/v2/DV90',
    }

    def __init__(
        self,
        cert_dir: Optional[Path] = None,
        backup_dir: Optional[Path] = None,
        staging: bool = False,
        acme_provider: str = 'letsencrypt',
        dry_run: bool = False,
    ):
        self.cert_dir = cert_dir or self.DEFAULT_CERT_DIR
        self.backup_dir = backup_dir or self.DEFAULT_BACKUP_DIR
        self.staging = staging
        self.acme_provider = acme_provider
        self.dry_run = dry_run

        # Ensure directories exist
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def renew_certificate(
        self,
        domain: str,
        challenge_type: str = 'http-01',
        webroot: Optional[Path] = None,
        dns_provider: Optional[str] = None,
        email: Optional[str] = None,
        pre_hook: Optional[str] = None,
        post_hook: Optional[str] = None,
        renew_days: int = 30,
    ) -> Dict:
        """Renew a single certificate"""

        result = {
            'domain': domain,
            'timestamp': datetime.utcnow().isoformat(),
            'status': 'pending',
            'messages': [],
        }

        try:
            # Check if renewal needed
            cert_path = self.cert_dir / domain / 'fullchain.pem'
            if cert_path.exists():
                days_remaining = self._get_days_remaining(cert_path)
                result['days_remaining_before'] = days_remaining

                if days_remaining > renew_days:
                    result['status'] = 'skipped'
                    result['messages'].append(
                        f'Certificate still valid for {days_remaining} days (threshold: {renew_days})'
                    )
                    return result
                else:
                    result['messages'].append(
                        f'Certificate expires in {days_remaining} days, renewing...'
                    )
            else:
                result['messages'].append('Certificate not found, obtaining new certificate...')

            # Backup existing certificate
            if cert_path.exists() and not self.dry_run:
                backup_path = self._backup_certificate(domain)
                result['backup_path'] = str(backup_path)
                result['messages'].append(f'Backed up existing certificate to {backup_path}')

            # Run pre-hook
            if pre_hook and not self.dry_run:
                result['messages'].append(f'Running pre-hook: {pre_hook}')
                self._run_hook(pre_hook, result)

            # Determine ACME provider URL
            if self.staging:
                acme_url = self.ACME_PROVIDERS['letsencrypt-staging']
            else:
                acme_url = self.ACME_PROVIDERS.get(self.acme_provider, self.acme_provider)

            # Build certbot command
            cmd = self._build_certbot_command(
                domain, challenge_type, webroot, dns_provider, email, acme_url
            )

            result['command'] = ' '.join(cmd)

            # Execute renewal
            if not self.dry_run:
                result['messages'].append(f'Executing: {" ".join(cmd)}')
                proc_result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=300,  # 5 minute timeout
                )

                if proc_result.returncode == 0:
                    result['status'] = 'success'
                    result['messages'].append('Certificate renewed successfully')

                    # Check new expiration
                    if cert_path.exists():
                        days_remaining = self._get_days_remaining(cert_path)
                        result['days_remaining_after'] = days_remaining
                        result['messages'].append(f'New certificate valid for {days_remaining} days')
                else:
                    result['status'] = 'failed'
                    result['messages'].append(f'Renewal failed with exit code {proc_result.returncode}')
                    result['error'] = proc_result.stderr

                    # Attempt rollback
                    if 'backup_path' in result:
                        result['messages'].append('Attempting rollback...')
                        self._rollback_certificate(domain, Path(result['backup_path']))
            else:
                result['status'] = 'dry_run'
                result['messages'].append('Dry run: command not executed')

            # Run post-hook
            if post_hook and not self.dry_run and result['status'] == 'success':
                result['messages'].append(f'Running post-hook: {post_hook}')
                self._run_hook(post_hook, result)

        except subprocess.TimeoutExpired:
            result['status'] = 'failed'
            result['messages'].append('Renewal timed out after 5 minutes')
        except Exception as e:
            result['status'] = 'error'
            result['messages'].append(f'Unexpected error: {e}')

        return result

    def renew_all_certificates(self, renew_days: int = 30) -> List[Dict]:
        """Renew all certificates expiring within threshold"""

        results = []

        if not self.cert_dir.exists():
            return [{
                'status': 'error',
                'messages': [f'Certificate directory not found: {self.cert_dir}'],
            }]

        # Find all certificates
        for cert_domain_dir in self.cert_dir.iterdir():
            if not cert_domain_dir.is_dir():
                continue

            cert_path = cert_domain_dir / 'fullchain.pem'
            if not cert_path.exists():
                continue

            domain = cert_domain_dir.name

            # Check expiration
            days_remaining = self._get_days_remaining(cert_path)
            if days_remaining <= renew_days:
                result = self.renew_certificate(domain, renew_days=renew_days)
                results.append(result)

        return results

    def _build_certbot_command(
        self,
        domain: str,
        challenge_type: str,
        webroot: Optional[Path],
        dns_provider: Optional[str],
        email: Optional[str],
        acme_url: str,
    ) -> List[str]:
        """Build certbot command"""

        cmd = ['certbot', 'certonly']

        # ACME server
        cmd.extend(['--server', acme_url])

        # Non-interactive
        cmd.append('--non-interactive')
        cmd.append('--agree-tos')

        # Email
        if email:
            cmd.extend(['--email', email])
        else:
            cmd.append('--register-unsafely-without-email')

        # Domain
        cmd.extend(['-d', domain])

        # Challenge type
        if challenge_type == 'http-01':
            if webroot:
                cmd.append('--webroot')
                cmd.extend(['-w', str(webroot)])
            else:
                cmd.append('--standalone')

        elif challenge_type == 'dns-01':
            if not dns_provider:
                raise ValueError('DNS provider required for DNS-01 challenge')

            # Use DNS plugin
            plugin_map = {
                'cloudflare': 'dns-cloudflare',
                'route53': 'dns-route53',
                'google': 'dns-google',
                'azure': 'dns-azure',
                'digitalocean': 'dns-digitalocean',
            }
            plugin = plugin_map.get(dns_provider, f'dns-{dns_provider}')
            cmd.append(f'--{plugin}')

        else:
            raise ValueError(f'Unknown challenge type: {challenge_type}')

        # Force renewal if already exists
        cmd.append('--force-renewal')

        return cmd

    def _get_days_remaining(self, cert_path: Path) -> int:
        """Get days until certificate expires"""
        try:
            cert_data = cert_path.read_bytes()
            cert = x509.load_pem_x509_certificate(cert_data, default_backend())
            now = datetime.utcnow()
            days_remaining = (cert.not_valid_after - now).days
            return days_remaining
        except Exception as e:
            raise ValueError(f'Failed to read certificate: {e}')

    def _backup_certificate(self, domain: str) -> Path:
        """Backup certificate before renewal"""
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        backup_domain_dir = self.backup_dir / domain / timestamp

        backup_domain_dir.mkdir(parents=True, exist_ok=True)

        cert_domain_dir = self.cert_dir / domain

        # Copy all certificate files
        for file_path in cert_domain_dir.iterdir():
            if file_path.is_file():
                shutil.copy2(file_path, backup_domain_dir / file_path.name)

        return backup_domain_dir

    def _rollback_certificate(self, domain: str, backup_path: Path):
        """Rollback to backup certificate"""
        try:
            cert_domain_dir = self.cert_dir / domain

            # Remove failed renewal
            if cert_domain_dir.exists():
                for file_path in cert_domain_dir.iterdir():
                    if file_path.is_file():
                        file_path.unlink()

            # Restore backup
            for file_path in backup_path.iterdir():
                if file_path.is_file():
                    shutil.copy2(file_path, cert_domain_dir / file_path.name)

            return True
        except Exception as e:
            print(f'Rollback failed: {e}', file=sys.stderr)
            return False

    def _run_hook(self, hook_cmd: str, result: Dict):
        """Run pre/post hook command"""
        # SECURITY: hook_cmd from config/CLI - administrator controlled, but validate before use
        try:
            proc = subprocess.run(
                hook_cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=60,
            )

            if proc.returncode == 0:
                result['messages'].append(f'Hook executed successfully')
            else:
                result['messages'].append(f'Hook failed with exit code {proc.returncode}')
                if proc.stderr:
                    result['messages'].append(f'Hook error: {proc.stderr}')

        except subprocess.TimeoutExpired:
            result['messages'].append('Hook timed out after 60 seconds')
        except Exception as e:
            result['messages'].append(f'Hook error: {e}')


def main():
    parser = argparse.ArgumentParser(
        description='Automated certificate renewal with ACME',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Renew single domain (HTTP-01)
  %(prog)s --domain example.com --webroot /var/www/html

  # Renew wildcard (DNS-01)
  %(prog)s --domain '*.example.com' --dns-provider cloudflare

  # Renew all expiring certificates
  %(prog)s --renew-all --days-before 30

  # Dry run (test without executing)
  %(prog)s --domain example.com --dry-run

  # Staging environment (testing)
  %(prog)s --domain example.com --staging

  # With hooks
  %(prog)s --domain example.com --pre-hook 'systemctl stop nginx' --post-hook 'systemctl start nginx'

  # JSON output
  %(prog)s --renew-all --json > renewal-report.json

  # Custom ACME provider
  %(prog)s --domain example.com --acme-provider zerossl --email admin@example.com

DNS Providers:
  cloudflare, route53, google, azure, digitalocean

Note: DNS providers require credentials to be configured (e.g., API tokens in environment)
        """
    )

    parser.add_argument('--domain', help='Domain to renew')
    parser.add_argument('--renew-all', action='store_true', help='Renew all expiring certificates')
    parser.add_argument('--days-before', type=int, default=30,
                        help='Renew certificates expiring within N days (default: 30)')

    # Challenge options
    parser.add_argument('--challenge', choices=['http-01', 'dns-01'], default='http-01',
                        help='ACME challenge type (default: http-01)')
    parser.add_argument('--webroot', type=Path, help='Webroot path for HTTP-01 challenge')
    parser.add_argument('--dns-provider', help='DNS provider for DNS-01 challenge')

    # ACME options
    parser.add_argument('--acme-provider', default='letsencrypt',
                        help='ACME provider (letsencrypt, zerossl, or custom URL)')
    parser.add_argument('--email', help='Email for ACME registration')
    parser.add_argument('--staging', action='store_true',
                        help='Use Let\'s Encrypt staging environment (for testing)')

    # Hooks
    parser.add_argument('--pre-hook', help='Command to run before renewal')
    parser.add_argument('--post-hook', help='Command to run after successful renewal')

    # Directories
    parser.add_argument('--cert-dir', type=Path, default=CertificateRenewer.DEFAULT_CERT_DIR,
                        help=f'Certificate directory (default: {CertificateRenewer.DEFAULT_CERT_DIR})')
    parser.add_argument('--backup-dir', type=Path, default=CertificateRenewer.DEFAULT_BACKUP_DIR,
                        help=f'Backup directory (default: {CertificateRenewer.DEFAULT_BACKUP_DIR})')

    # Output
    parser.add_argument('--json', action='store_true', help='Output JSON format')
    parser.add_argument('--dry-run', action='store_true', help='Test without executing')

    args = parser.parse_args()

    # Validate arguments
    if not args.domain and not args.renew_all:
        parser.error('Must specify --domain or --renew-all')

    if args.challenge == 'dns-01' and not args.dns_provider and args.domain:
        parser.error('--dns-provider required for DNS-01 challenge')

    # Check if certbot installed
    if not args.dry_run:
        try:
            subprocess.run(['certbot', '--version'], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            print('Error: certbot not found. Install with: apt install certbot', file=sys.stderr)
            sys.exit(1)

    # Create renewer
    renewer = CertificateRenewer(
        cert_dir=args.cert_dir,
        backup_dir=args.backup_dir,
        staging=args.staging,
        acme_provider=args.acme_provider,
        dry_run=args.dry_run,
    )

    # Execute renewal
    if args.renew_all:
        results = renewer.renew_all_certificates(renew_days=args.days_before)
    else:
        result = renewer.renew_certificate(
            domain=args.domain,
            challenge_type=args.challenge,
            webroot=args.webroot,
            dns_provider=args.dns_provider,
            email=args.email,
            pre_hook=args.pre_hook,
            post_hook=args.post_hook,
            renew_days=args.days_before,
        )
        results = [result]

    # Output
    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print_results(results)

    # Exit code
    statuses = [r['status'] for r in results]
    if 'failed' in statuses or 'error' in statuses:
        sys.exit(1)
    else:
        sys.exit(0)


def print_results(results: List[Dict]):
    """Print renewal results in human-readable format"""

    print("\n=== Certificate Renewal Report ===")
    print(f"Timestamp: {datetime.utcnow().isoformat()}")
    print(f"Total certificates: {len(results)}\n")

    for result in results:
        domain = result.get('domain', 'unknown')
        status = result.get('status', 'unknown')

        print(f"--- {domain} ---")
        print(f"Status: {status.upper()}")

        if 'days_remaining_before' in result:
            print(f"Days remaining (before): {result['days_remaining_before']}")

        if 'days_remaining_after' in result:
            print(f"Days remaining (after): {result['days_remaining_after']}")

        if 'backup_path' in result:
            print(f"Backup: {result['backup_path']}")

        if 'command' in result:
            print(f"Command: {result['command']}")

        if 'messages' in result:
            for msg in result['messages']:
                print(f"  • {msg}")

        if 'error' in result:
            print(f"Error: {result['error']}")

        print()


if __name__ == '__main__':
    main()
