#!/usr/bin/env python3
"""
Security Headers Scanner

Scans URLs for security headers and grades security posture.
Provides detailed analysis of header configuration and recommendations.
"""

import argparse
import json
import sys
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse
import requests
from dataclasses import dataclass, asdict


@dataclass
class HeaderCheck:
    """Result of a security header check."""
    present: bool
    value: Optional[str]
    score: int
    max_score: int
    issues: List[str]
    recommendations: List[str]


@dataclass
class ScanResult:
    """Complete security scan result for a URL."""
    url: str
    status_code: int
    headers: Dict[str, HeaderCheck]
    total_score: int
    max_score: int
    grade: str
    redirect_chain: List[str]


class SecurityHeadersScanner:
    """Scans and analyzes security headers."""

    # Header scoring weights
    HEADER_SCORES = {
        'strict-transport-security': 20,
        'content-security-policy': 30,
        'x-frame-options': 10,
        'x-content-type-options': 10,
        'referrer-policy': 10,
        'permissions-policy': 10,
        'x-xss-protection': 5,
        'content-type': 5
    }

    def __init__(self, timeout: int = 10, follow_redirects: bool = True):
        self.timeout = timeout
        self.follow_redirects = follow_redirects
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'SecurityHeadersScanner/1.0'
        })

    def scan(self, url: str) -> ScanResult:
        """Scan a URL for security headers."""
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url

        try:
            response = self.session.get(
                url,
                timeout=self.timeout,
                allow_redirects=self.follow_redirects
            )

            redirect_chain = [str(r.url) for r in response.history]
            redirect_chain.append(str(response.url))

            headers = {k.lower(): v for k, v in response.headers.items()}

            checks = {
                'hsts': self._check_hsts(headers),
                'csp': self._check_csp(headers),
                'x-frame-options': self._check_x_frame_options(headers),
                'x-content-type-options': self._check_x_content_type_options(headers),
                'referrer-policy': self._check_referrer_policy(headers),
                'permissions-policy': self._check_permissions_policy(headers),
                'x-xss-protection': self._check_x_xss_protection(headers),
                'cookies': self._check_cookies(response.cookies)
            }

            total_score = sum(check.score for check in checks.values())
            max_score = sum(check.max_score for check in checks.values())
            grade = self._calculate_grade(total_score, max_score)

            return ScanResult(
                url=str(response.url),
                status_code=response.status_code,
                headers=checks,
                total_score=total_score,
                max_score=max_score,
                grade=grade,
                redirect_chain=redirect_chain
            )

        except requests.RequestException as e:
            print(f"Error scanning {url}: {e}", file=sys.stderr)
            sys.exit(1)

    def _check_hsts(self, headers: Dict[str, str]) -> HeaderCheck:
        """Check Strict-Transport-Security header."""
        header = headers.get('strict-transport-security')
        max_score = self.HEADER_SCORES['strict-transport-security']

        if not header:
            return HeaderCheck(
                present=False,
                value=None,
                score=0,
                max_score=max_score,
                issues=["HSTS header missing"],
                recommendations=[
                    "Add: Strict-Transport-Security: max-age=31536000; includeSubDomains; preload"
                ]
            )

        issues = []
        recommendations = []
        score = max_score

        # Parse max-age
        max_age = 0
        for directive in header.split(';'):
            directive = directive.strip()
            if directive.startswith('max-age='):
                try:
                    max_age = int(directive.split('=')[1])
                except ValueError:
                    issues.append("Invalid max-age value")
                    score -= 5

        # Check max-age value
        if max_age == 0:
            issues.append("max-age is 0 (HSTS disabled)")
            score -= 10
        elif max_age < 15768000:  # 6 months
            issues.append(f"max-age too short ({max_age} seconds)")
            recommendations.append("Increase max-age to at least 15768000 (6 months)")
            score -= 5

        # Check includeSubDomains
        if 'includesubdomains' not in header.lower():
            issues.append("Missing includeSubDomains directive")
            recommendations.append("Add includeSubDomains directive")
            score -= 3

        # Check preload
        if 'preload' not in header.lower():
            recommendations.append("Consider adding preload directive and submitting to hstspreload.org")
            score -= 2

        return HeaderCheck(
            present=True,
            value=header,
            score=max(score, 0),
            max_score=max_score,
            issues=issues,
            recommendations=recommendations
        )

    def _check_csp(self, headers: Dict[str, str]) -> HeaderCheck:
        """Check Content-Security-Policy header."""
        header = headers.get('content-security-policy')
        max_score = self.HEADER_SCORES['content-security-policy']

        if not header:
            return HeaderCheck(
                present=False,
                value=None,
                score=0,
                max_score=max_score,
                issues=["CSP header missing"],
                recommendations=[
                    "Add: Content-Security-Policy: default-src 'self'; script-src 'self'; object-src 'none'"
                ]
            )

        issues = []
        recommendations = []
        score = max_score

        # Check for unsafe directives
        if "'unsafe-inline'" in header:
            issues.append("Contains 'unsafe-inline' directive")
            recommendations.append("Remove 'unsafe-inline' and use nonces or hashes")
            score -= 10

        if "'unsafe-eval'" in header:
            issues.append("Contains 'unsafe-eval' directive")
            recommendations.append("Remove 'unsafe-eval' if possible")
            score -= 8

        # Check for wildcard sources
        if " * " in header or header.startswith("* ") or header.endswith(" *"):
            issues.append("Contains wildcard (*) source")
            recommendations.append("Replace wildcards with specific domains")
            score -= 5

        # Check for default-src
        if 'default-src' not in header:
            issues.append("Missing default-src directive")
            recommendations.append("Add default-src directive as fallback")
            score -= 5

        # Check for object-src
        if 'object-src' not in header:
            recommendations.append("Add object-src 'none' to block plugins")
            score -= 2

        # Check for base-uri
        if 'base-uri' not in header:
            recommendations.append("Add base-uri 'self' to prevent base tag injection")
            score -= 2

        return HeaderCheck(
            present=True,
            value=header,
            score=max(score, 0),
            max_score=max_score,
            issues=issues,
            recommendations=recommendations
        )

    def _check_x_frame_options(self, headers: Dict[str, str]) -> HeaderCheck:
        """Check X-Frame-Options header."""
        header = headers.get('x-frame-options')
        max_score = self.HEADER_SCORES['x-frame-options']

        if not header:
            csp = headers.get('content-security-policy', '')
            if 'frame-ancestors' in csp:
                return HeaderCheck(
                    present=False,
                    value=None,
                    score=max_score,
                    max_score=max_score,
                    issues=[],
                    recommendations=["Using CSP frame-ancestors (modern alternative)"]
                )

            return HeaderCheck(
                present=False,
                value=None,
                score=0,
                max_score=max_score,
                issues=["X-Frame-Options missing"],
                recommendations=["Add: X-Frame-Options: DENY or use CSP frame-ancestors"]
            )

        issues = []
        recommendations = []
        score = max_score

        value = header.upper()
        if value == 'DENY':
            pass  # Perfect
        elif value == 'SAMEORIGIN':
            recommendations.append("Consider using DENY for maximum protection")
            score -= 2
        elif value.startswith('ALLOW-FROM'):
            issues.append("ALLOW-FROM is deprecated")
            recommendations.append("Use CSP frame-ancestors instead")
            score -= 5
        else:
            issues.append(f"Invalid value: {header}")
            score -= 5

        return HeaderCheck(
            present=True,
            value=header,
            score=max(score, 0),
            max_score=max_score,
            issues=issues,
            recommendations=recommendations
        )

    def _check_x_content_type_options(self, headers: Dict[str, str]) -> HeaderCheck:
        """Check X-Content-Type-Options header."""
        header = headers.get('x-content-type-options')
        max_score = self.HEADER_SCORES['x-content-type-options']

        if not header:
            return HeaderCheck(
                present=False,
                value=None,
                score=0,
                max_score=max_score,
                issues=["X-Content-Type-Options missing"],
                recommendations=["Add: X-Content-Type-Options: nosniff"]
            )

        issues = []
        score = max_score

        if header.lower() != 'nosniff':
            issues.append(f"Invalid value: {header}")
            score = 0

        return HeaderCheck(
            present=True,
            value=header,
            score=score,
            max_score=max_score,
            issues=issues,
            recommendations=[]
        )

    def _check_referrer_policy(self, headers: Dict[str, str]) -> HeaderCheck:
        """Check Referrer-Policy header."""
        header = headers.get('referrer-policy')
        max_score = self.HEADER_SCORES['referrer-policy']

        valid_policies = {
            'no-referrer': 10,
            'no-referrer-when-downgrade': 8,
            'origin': 7,
            'origin-when-cross-origin': 9,
            'same-origin': 9,
            'strict-origin': 10,
            'strict-origin-when-cross-origin': 10,
            'unsafe-url': 2
        }

        if not header:
            return HeaderCheck(
                present=False,
                value=None,
                score=0,
                max_score=max_score,
                issues=["Referrer-Policy missing"],
                recommendations=["Add: Referrer-Policy: strict-origin-when-cross-origin"]
            )

        issues = []
        recommendations = []
        policy = header.lower()

        if policy not in valid_policies:
            issues.append(f"Invalid policy: {header}")
            score = 0
        else:
            score = valid_policies[policy]
            if policy == 'unsafe-url':
                issues.append("Using 'unsafe-url' leaks full URL")
                recommendations.append("Use strict-origin-when-cross-origin instead")
            elif policy == 'no-referrer-when-downgrade':
                recommendations.append("Consider strict-origin-when-cross-origin for better privacy")

        return HeaderCheck(
            present=True,
            value=header,
            score=score,
            max_score=max_score,
            issues=issues,
            recommendations=recommendations
        )

    def _check_permissions_policy(self, headers: Dict[str, str]) -> HeaderCheck:
        """Check Permissions-Policy header."""
        header = headers.get('permissions-policy')
        max_score = self.HEADER_SCORES['permissions-policy']

        # Check for legacy Feature-Policy
        feature_policy = headers.get('feature-policy')

        if not header and not feature_policy:
            return HeaderCheck(
                present=False,
                value=None,
                score=0,
                max_score=max_score,
                issues=["Permissions-Policy missing"],
                recommendations=[
                    "Add: Permissions-Policy: geolocation=(), camera=(), microphone=()"
                ]
            )

        if feature_policy and not header:
            return HeaderCheck(
                present=True,
                value=feature_policy,
                score=max_score - 2,
                max_score=max_score,
                issues=[],
                recommendations=["Migrate from Feature-Policy to Permissions-Policy"]
            )

        return HeaderCheck(
            present=True,
            value=header,
            score=max_score,
            max_score=max_score,
            issues=[],
            recommendations=[]
        )

    def _check_x_xss_protection(self, headers: Dict[str, str]) -> HeaderCheck:
        """Check X-XSS-Protection header."""
        header = headers.get('x-xss-protection')
        max_score = self.HEADER_SCORES['x-xss-protection']

        if not header:
            return HeaderCheck(
                present=False,
                value=None,
                score=max_score,
                max_score=max_score,
                issues=[],
                recommendations=["X-XSS-Protection is deprecated; use CSP instead"]
            )

        recommendations = []
        score = max_score

        if header != '0':
            recommendations.append("Set to '0' (XSS filters are deprecated and can introduce vulnerabilities)")
            score -= 3

        return HeaderCheck(
            present=True,
            value=header,
            score=max(score, 0),
            max_score=max_score,
            issues=[],
            recommendations=recommendations
        )

    def _check_cookies(self, cookies) -> HeaderCheck:
        """Check cookie security attributes."""
        issues = []
        recommendations = []
        score = 5
        max_score = 5

        if not cookies:
            return HeaderCheck(
                present=False,
                value=None,
                score=max_score,
                max_score=max_score,
                issues=[],
                recommendations=[]
            )

        for cookie in cookies:
            cookie_issues = []

            if not cookie.secure:
                cookie_issues.append(f"Cookie '{cookie.name}' missing Secure attribute")

            if not cookie.has_nonstandard_attr('HttpOnly'):
                cookie_issues.append(f"Cookie '{cookie.name}' missing HttpOnly attribute")

            samesite = cookie.get_nonstandard_attr('SameSite')
            if not samesite:
                cookie_issues.append(f"Cookie '{cookie.name}' missing SameSite attribute")
            elif samesite.lower() == 'none' and not cookie.secure:
                cookie_issues.append(f"Cookie '{cookie.name}' has SameSite=None without Secure")

            if cookie_issues:
                issues.extend(cookie_issues)
                score -= 1

        if issues:
            recommendations.append("Add Secure, HttpOnly, and SameSite attributes to all cookies")

        return HeaderCheck(
            present=True,
            value=f"{len(cookies)} cookie(s) found",
            score=max(score, 0),
            max_score=max_score,
            issues=issues,
            recommendations=recommendations
        )

    def _calculate_grade(self, score: int, max_score: int) -> str:
        """Calculate letter grade from score."""
        percentage = (score / max_score) * 100 if max_score > 0 else 0

        if percentage >= 95:
            return 'A+'
        elif percentage >= 90:
            return 'A'
        elif percentage >= 85:
            return 'A-'
        elif percentage >= 80:
            return 'B+'
        elif percentage >= 75:
            return 'B'
        elif percentage >= 70:
            return 'B-'
        elif percentage >= 65:
            return 'C+'
        elif percentage >= 60:
            return 'C'
        elif percentage >= 55:
            return 'C-'
        elif percentage >= 50:
            return 'D'
        else:
            return 'F'


def format_text_output(result: ScanResult) -> str:
    """Format scan result as human-readable text."""
    output = []
    output.append("=" * 80)
    output.append(f"Security Headers Scan: {result.url}")
    output.append("=" * 80)
    output.append(f"Status Code: {result.status_code}")
    output.append(f"Grade: {result.grade} ({result.total_score}/{result.max_score})")
    output.append("")

    if len(result.redirect_chain) > 1:
        output.append("Redirect Chain:")
        for i, url in enumerate(result.redirect_chain, 1):
            output.append(f"  {i}. {url}")
        output.append("")

    for name, check in result.headers.items():
        output.append(f"{name.upper()}: {'✓' if check.present else '✗'}")
        output.append(f"  Score: {check.score}/{check.max_score}")

        if check.value:
            output.append(f"  Value: {check.value}")

        if check.issues:
            output.append("  Issues:")
            for issue in check.issues:
                output.append(f"    - {issue}")

        if check.recommendations:
            output.append("  Recommendations:")
            for rec in check.recommendations:
                output.append(f"    - {rec}")

        output.append("")

    return "\n".join(output)


def main():
    parser = argparse.ArgumentParser(
        description="Scan URLs for security headers and grade security posture",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s https://example.com
  %(prog)s example.com --json
  %(prog)s example.com example.org --json > results.json
  %(prog)s https://example.com --timeout 30 --no-redirects
        """
    )

    parser.add_argument(
        'urls',
        nargs='+',
        help='URLs to scan (https:// prefix optional)'
    )
    parser.add_argument(
        '--json',
        action='store_true',
        help='Output results as JSON'
    )
    parser.add_argument(
        '--timeout',
        type=int,
        default=10,
        help='Request timeout in seconds (default: 10)'
    )
    parser.add_argument(
        '--no-redirects',
        action='store_true',
        help='Do not follow redirects'
    )

    args = parser.parse_args()

    scanner = SecurityHeadersScanner(
        timeout=args.timeout,
        follow_redirects=not args.no_redirects
    )

    results = []
    for url in args.urls:
        result = scanner.scan(url)
        results.append(result)

        if not args.json:
            print(format_text_output(result))
            if len(args.urls) > 1:
                print("\n")

    if args.json:
        json_results = [
            {
                'url': r.url,
                'status_code': r.status_code,
                'grade': r.grade,
                'total_score': r.total_score,
                'max_score': r.max_score,
                'redirect_chain': r.redirect_chain,
                'headers': {
                    name: asdict(check)
                    for name, check in r.headers.items()
                }
            }
            for r in results
        ]
        print(json.dumps(json_results, indent=2))

    # Exit with error code if any scan received F grade
    if any(r.grade == 'F' for r in results):
        sys.exit(1)


if __name__ == '__main__':
    main()
