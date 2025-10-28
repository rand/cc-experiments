#!/usr/bin/env python3
"""
Automated accessibility auditing with axe-core

Scans web pages for accessibility violations using axe-core via Selenium.
Supports multiple URLs, custom rules, and JSON/HTML output.

Usage:
    ./check_accessibility.py <url> [options]
    ./check_accessibility.py https://example.com
    ./check_accessibility.py https://example.com --standard wcag2aa --json
    ./check_accessibility.py urls.txt --batch --output report.html
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass, asdict

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from selenium.common.exceptions import WebDriverException
    import requests
except ImportError as e:
    print(f"Error: Missing required package: {e}", file=sys.stderr)
    print("Install with: pip install selenium requests", file=sys.stderr)
    sys.exit(1)


@dataclass
class Violation:
    """Accessibility violation details"""
    id: str
    impact: str
    description: str
    help: str
    help_url: str
    tags: List[str]
    nodes: List[Dict]

    @property
    def affected_elements(self) -> int:
        return len(self.nodes)


@dataclass
class AuditResult:
    """Complete audit result for a URL"""
    url: str
    timestamp: str
    violations: List[Violation]
    passes: int
    incomplete: int
    inapplicable: int
    total_issues: int
    critical_issues: int
    serious_issues: int
    moderate_issues: int
    minor_issues: int

    @property
    def has_violations(self) -> bool:
        return self.total_issues > 0

    def to_dict(self):
        return {
            **asdict(self),
            'violations': [asdict(v) for v in self.violations]
        }


class AccessibilityChecker:
    """Automated accessibility checker using axe-core"""

    # axe-core CDN URL
    AXE_SCRIPT_URL = "https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.8.2/axe.min.js"

    # Impact levels
    IMPACT_LEVELS = ['critical', 'serious', 'moderate', 'minor']

    # WCAG standards
    STANDARDS = {
        'wcag2a': ['wcag2a'],
        'wcag2aa': ['wcag2a', 'wcag2aa'],
        'wcag2aaa': ['wcag2a', 'wcag2aa', 'wcag2aaa'],
        'wcag21aa': ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'],
        'wcag22aa': ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'],
        'best-practice': ['best-practice'],
    }

    def __init__(self, headless: bool = True, timeout: int = 30):
        """Initialize checker with Chrome driver"""
        self.headless = headless
        self.timeout = timeout
        self.driver: Optional[webdriver.Chrome] = None
        self.axe_script: Optional[str] = None

    def __enter__(self):
        """Context manager entry"""
        self._init_driver()
        self._load_axe_script()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        if self.driver:
            self.driver.quit()

    def _init_driver(self):
        """Initialize Chrome WebDriver"""
        options = Options()
        if self.headless:
            options.add_argument('--headless=new')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')

        try:
            self.driver = webdriver.Chrome(options=options)
            self.driver.set_page_load_timeout(self.timeout)
        except WebDriverException as e:
            print(f"Error: Failed to initialize Chrome driver: {e}", file=sys.stderr)
            print("Make sure ChromeDriver is installed and in PATH", file=sys.stderr)
            sys.exit(1)

    def _load_axe_script(self):
        """Load axe-core script from CDN"""
        try:
            response = requests.get(self.AXE_SCRIPT_URL, timeout=10)
            response.raise_for_status()
            self.axe_script = response.text
        except requests.RequestException as e:
            print(f"Error: Failed to load axe-core script: {e}", file=sys.stderr)
            sys.exit(1)

    def check_url(
        self,
        url: str,
        standard: str = 'wcag2aa',
        rules: Optional[List[str]] = None
    ) -> AuditResult:
        """
        Check accessibility violations for a URL

        Args:
            url: URL to check
            standard: WCAG standard to check against
            rules: Optional list of specific rule IDs to check

        Returns:
            AuditResult with violations
        """
        if not self.driver or not self.axe_script:
            raise RuntimeError("Checker not initialized")

        # Load page
        try:
            self.driver.get(url)
        except WebDriverException as e:
            raise RuntimeError(f"Failed to load URL {url}: {e}")

        # Inject axe-core
        self.driver.execute_script(self.axe_script)

        # Build axe options
        tags = self.STANDARDS.get(standard, ['wcag2aa'])
        axe_options = {
            'runOnly': {
                'type': 'tag',
                'values': tags
            }
        }

        if rules:
            axe_options['rules'] = {rule: {'enabled': True} for rule in rules}

        # Run axe
        axe_script = f"return axe.run({json.dumps(axe_options)})"
        try:
            results = self.driver.execute_async_script(f"""
                var callback = arguments[arguments.length - 1];
                {axe_script}.then(callback);
            """)
        except WebDriverException as e:
            raise RuntimeError(f"Failed to run axe-core: {e}")

        # Parse results
        violations = [
            Violation(
                id=v['id'],
                impact=v.get('impact', 'unknown'),
                description=v['description'],
                help=v['help'],
                help_url=v['helpUrl'],
                tags=v['tags'],
                nodes=v['nodes']
            )
            for v in results.get('violations', [])
        ]

        # Count by impact
        impact_counts = {level: 0 for level in self.IMPACT_LEVELS}
        for violation in violations:
            if violation.impact in impact_counts:
                impact_counts[violation.impact] += violation.affected_elements

        return AuditResult(
            url=url,
            timestamp=datetime.utcnow().isoformat() + 'Z',
            violations=violations,
            passes=len(results.get('passes', [])),
            incomplete=len(results.get('incomplete', [])),
            inapplicable=len(results.get('inapplicable', [])),
            total_issues=sum(v.affected_elements for v in violations),
            critical_issues=impact_counts['critical'],
            serious_issues=impact_counts['serious'],
            moderate_issues=impact_counts['moderate'],
            minor_issues=impact_counts['minor']
        )


def format_text_report(results: List[AuditResult]) -> str:
    """Format results as text report"""
    lines = []
    lines.append("=" * 80)
    lines.append("ACCESSIBILITY AUDIT REPORT")
    lines.append("=" * 80)
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"Total URLs: {len(results)}")
    lines.append("")

    for result in results:
        lines.append("-" * 80)
        lines.append(f"URL: {result.url}")
        lines.append(f"Timestamp: {result.timestamp}")
        lines.append("")
        lines.append(f"Summary:")
        lines.append(f"  Total Issues: {result.total_issues}")
        lines.append(f"  Critical: {result.critical_issues}")
        lines.append(f"  Serious: {result.serious_issues}")
        lines.append(f"  Moderate: {result.moderate_issues}")
        lines.append(f"  Minor: {result.minor_issues}")
        lines.append(f"  Passes: {result.passes}")
        lines.append(f"  Incomplete: {result.incomplete}")
        lines.append("")

        if result.violations:
            lines.append("Violations:")
            lines.append("")
            for i, violation in enumerate(result.violations, 1):
                lines.append(f"{i}. {violation.id} [{violation.impact.upper()}]")
                lines.append(f"   Description: {violation.description}")
                lines.append(f"   Help: {violation.help}")
                lines.append(f"   URL: {violation.help_url}")
                lines.append(f"   Affected elements: {violation.affected_elements}")
                lines.append(f"   Tags: {', '.join(violation.tags)}")
                lines.append("")

                # Show first 3 affected elements
                for j, node in enumerate(violation.nodes[:3], 1):
                    target = node.get('target', ['unknown'])[0]
                    html = node.get('html', '')[:100]
                    lines.append(f"   Element {j}: {target}")
                    lines.append(f"   HTML: {html}...")
                    lines.append("")

                if violation.affected_elements > 3:
                    remaining = violation.affected_elements - 3
                    lines.append(f"   ... and {remaining} more element(s)")
                    lines.append("")
        else:
            lines.append("No violations found!")
            lines.append("")

    lines.append("=" * 80)
    return "\n".join(lines)


def format_json_report(results: List[AuditResult]) -> str:
    """Format results as JSON report"""
    report = {
        'generated': datetime.now().isoformat(),
        'total_urls': len(results),
        'results': [r.to_dict() for r in results]
    }
    return json.dumps(report, indent=2)


def format_html_report(results: List[AuditResult]) -> str:
    """Format results as HTML report"""
    html = [
        '<!DOCTYPE html>',
        '<html lang="en">',
        '<head>',
        '  <meta charset="UTF-8">',
        '  <meta name="viewport" content="width=device-width, initial-scale=1.0">',
        '  <title>Accessibility Audit Report</title>',
        '  <style>',
        '    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 2rem; line-height: 1.6; }',
        '    h1 { border-bottom: 3px solid #333; padding-bottom: 0.5rem; }',
        '    h2 { color: #555; margin-top: 2rem; }',
        '    .summary { background: #f5f5f5; padding: 1rem; border-radius: 4px; margin: 1rem 0; }',
        '    .violation { border-left: 4px solid #dc3545; padding: 1rem; margin: 1rem 0; background: #fff5f5; }',
        '    .violation.critical { border-left-color: #dc3545; background: #fff5f5; }',
        '    .violation.serious { border-left-color: #fd7e14; background: #fff9f0; }',
        '    .violation.moderate { border-left-color: #ffc107; background: #fffef0; }',
        '    .violation.minor { border-left-color: #17a2b8; background: #f0f9ff; }',
        '    .badge { display: inline-block; padding: 0.25rem 0.5rem; border-radius: 3px; font-size: 0.875rem; font-weight: bold; }',
        '    .badge.critical { background: #dc3545; color: white; }',
        '    .badge.serious { background: #fd7e14; color: white; }',
        '    .badge.moderate { background: #ffc107; color: black; }',
        '    .badge.minor { background: #17a2b8; color: white; }',
        '    .node { background: #f8f9fa; padding: 0.5rem; margin: 0.5rem 0; border-radius: 3px; }',
        '    code { background: #f8f9fa; padding: 0.125rem 0.25rem; border-radius: 3px; font-size: 0.875em; }',
        '    a { color: #0066cc; }',
        '    .success { color: #28a745; font-weight: bold; }',
        '  </style>',
        '</head>',
        '<body>',
        '  <h1>Accessibility Audit Report</h1>',
        f'  <p><strong>Generated:</strong> {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>',
        f'  <p><strong>Total URLs:</strong> {len(results)}</p>',
    ]

    for result in results:
        html.append(f'  <h2>{result.url}</h2>')
        html.append('  <div class="summary">')
        html.append(f'    <p><strong>Timestamp:</strong> {result.timestamp}</p>')
        html.append(f'    <p><strong>Total Issues:</strong> {result.total_issues}</p>')
        html.append(f'    <p><strong>Critical:</strong> {result.critical_issues} | ')
        html.append(f'<strong>Serious:</strong> {result.serious_issues} | ')
        html.append(f'<strong>Moderate:</strong> {result.moderate_issues} | ')
        html.append(f'<strong>Minor:</strong> {result.minor_issues}</p>')
        html.append(f'    <p><strong>Passes:</strong> {result.passes} | ')
        html.append(f'<strong>Incomplete:</strong> {result.incomplete}</p>')
        html.append('  </div>')

        if result.violations:
            for i, violation in enumerate(result.violations, 1):
                html.append(f'  <div class="violation {violation.impact}">')
                html.append(f'    <h3>{i}. {violation.id} ')
                html.append(f'<span class="badge {violation.impact}">{violation.impact.upper()}</span></h3>')
                html.append(f'    <p><strong>Description:</strong> {violation.description}</p>')
                html.append(f'    <p><strong>Help:</strong> {violation.help}</p>')
                html.append(f'    <p><strong>More info:</strong> <a href="{violation.help_url}" target="_blank">{violation.help_url}</a></p>')
                html.append(f'    <p><strong>Affected elements:</strong> {violation.affected_elements}</p>')
                html.append(f'    <p><strong>Tags:</strong> {", ".join(violation.tags)}</p>')

                if violation.nodes:
                    html.append('    <h4>Affected Elements:</h4>')
                    for j, node in enumerate(violation.nodes[:5], 1):
                        target = node.get('target', ['unknown'])[0]
                        html_snippet = node.get('html', '')[:100]
                        html.append('    <div class="node">')
                        html.append(f'      <p><strong>Element {j}:</strong> <code>{target}</code></p>')
                        html.append(f'      <p><strong>HTML:</strong> <code>{html_snippet}...</code></p>')
                        html.append('    </div>')

                    if violation.affected_elements > 5:
                        remaining = violation.affected_elements - 5
                        html.append(f'    <p><em>... and {remaining} more element(s)</em></p>')

                html.append('  </div>')
        else:
            html.append('  <p class="success">✓ No violations found!</p>')

    html.extend([
        '</body>',
        '</html>'
    ])

    return '\n'.join(html)


def main():
    parser = argparse.ArgumentParser(
        description='Automated accessibility auditing with axe-core',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s https://example.com
  %(prog)s https://example.com --standard wcag21aa
  %(prog)s https://example.com --json --output report.json
  %(prog)s urls.txt --batch --output report.html
  %(prog)s https://example.com --rules color-contrast button-name

Standards:
  wcag2a, wcag2aa (default), wcag2aaa, wcag21aa, wcag22aa, best-practice
        """
    )

    parser.add_argument(
        'url',
        help='URL to check or file with URLs (one per line) if --batch'
    )
    parser.add_argument(
        '--standard',
        default='wcag2aa',
        choices=['wcag2a', 'wcag2aa', 'wcag2aaa', 'wcag21aa', 'wcag22aa', 'best-practice'],
        help='WCAG standard to check against (default: wcag2aa)'
    )
    parser.add_argument(
        '--rules',
        nargs='+',
        help='Specific axe rule IDs to check'
    )
    parser.add_argument(
        '--batch',
        action='store_true',
        help='Treat URL argument as file with multiple URLs'
    )
    parser.add_argument(
        '--json',
        action='store_true',
        help='Output in JSON format'
    )
    parser.add_argument(
        '--html',
        action='store_true',
        help='Output in HTML format'
    )
    parser.add_argument(
        '--output', '-o',
        help='Write output to file instead of stdout'
    )
    parser.add_argument(
        '--timeout',
        type=int,
        default=30,
        help='Page load timeout in seconds (default: 30)'
    )
    parser.add_argument(
        '--no-headless',
        action='store_true',
        help='Show browser window (not headless)'
    )

    args = parser.parse_args()

    # Get URLs to check
    urls = []
    if args.batch:
        try:
            with open(args.url) as f:
                urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]
        except IOError as e:
            print(f"Error: Failed to read URL file: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        urls = [args.url]

    if not urls:
        print("Error: No URLs to check", file=sys.stderr)
        sys.exit(1)

    # Run checks
    results = []
    try:
        with AccessibilityChecker(
            headless=not args.no_headless,
            timeout=args.timeout
        ) as checker:
            for i, url in enumerate(urls, 1):
                print(f"Checking {i}/{len(urls)}: {url}", file=sys.stderr)
                try:
                    result = checker.check_url(url, args.standard, args.rules)
                    results.append(result)
                except RuntimeError as e:
                    print(f"Error checking {url}: {e}", file=sys.stderr)
                    continue

    except KeyboardInterrupt:
        print("\nInterrupted by user", file=sys.stderr)
        sys.exit(130)

    if not results:
        print("Error: No results to report", file=sys.stderr)
        sys.exit(1)

    # Format output
    if args.json:
        output = format_json_report(results)
    elif args.html:
        output = format_html_report(results)
    else:
        output = format_text_report(results)

    # Write output
    if args.output:
        try:
            Path(args.output).write_text(output)
            print(f"Report written to: {args.output}", file=sys.stderr)
        except IOError as e:
            print(f"Error: Failed to write output file: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        print(output)

    # Exit code based on violations
    total_issues = sum(r.total_issues for r in results)
    sys.exit(1 if total_issues > 0 else 0)


if __name__ == '__main__':
    main()
