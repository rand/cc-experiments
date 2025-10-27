#!/usr/bin/env python3
"""
SEO Tag Checker for URLs

Validates SEO tags on web pages including meta tags, Open Graph, Twitter Cards,
structured data, and canonical URLs.

Usage:
    ./check_seo.py <url>
    ./check_seo.py <url> --json
    ./check_seo.py <url> --check-all
    ./check_seo.py <url> --output report.json
"""

import argparse
import json
import sys
from typing import Dict, List, Optional, Any
from urllib.parse import urlparse, urljoin
import re

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("Error: Required packages not installed.", file=sys.stderr)
    print("Install with: pip install requests beautifulsoup4", file=sys.stderr)
    sys.exit(1)


class SEOChecker:
    """Check SEO tags and metadata on web pages."""

    def __init__(self, url: str):
        self.url = url
        self.soup: Optional[BeautifulSoup] = None
        self.response: Optional[requests.Response] = None
        self.issues: List[Dict[str, Any]] = []
        self.warnings: List[Dict[str, Any]] = []
        self.successes: List[Dict[str, Any]] = []

    def fetch_page(self) -> bool:
        """Fetch the web page."""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (compatible; SEOChecker/1.0; +http://example.com/bot)'
            }
            self.response = requests.get(self.url, headers=headers, timeout=30)
            self.response.raise_for_status()
            self.soup = BeautifulSoup(self.response.text, 'html.parser')
            return True
        except requests.exceptions.RequestException as e:
            self.add_issue('fetch', f"Failed to fetch URL: {e}", severity='error')
            return False

    def add_issue(self, category: str, message: str, severity: str = 'error'):
        """Add an issue to the list."""
        self.issues.append({
            'category': category,
            'message': message,
            'severity': severity
        })

    def add_warning(self, category: str, message: str, details: Optional[str] = None):
        """Add a warning to the list."""
        warning = {
            'category': category,
            'message': message
        }
        if details:
            warning['details'] = details
        self.warnings.append(warning)

    def add_success(self, category: str, message: str, value: Optional[str] = None):
        """Add a success to the list."""
        success = {
            'category': category,
            'message': message
        }
        if value:
            success['value'] = value
        self.successes.append(success)

    def check_title(self) -> Dict[str, Any]:
        """Check title tag."""
        title_tag = self.soup.find('title')

        if not title_tag:
            self.add_issue('title', 'Missing <title> tag')
            return {'present': False}

        title = title_tag.get_text().strip()
        length = len(title)

        result = {
            'present': True,
            'value': title,
            'length': length,
        }

        if not title:
            self.add_issue('title', 'Title tag is empty')
        elif length < 30:
            self.add_warning('title', f'Title is too short ({length} chars)',
                           'Recommended: 50-60 characters')
        elif length > 60:
            self.add_warning('title', f'Title is too long ({length} chars)',
                           'May be truncated in search results')
        else:
            self.add_success('title', f'Title length is optimal ({length} chars)', title)

        return result

    def check_meta_description(self) -> Dict[str, Any]:
        """Check meta description."""
        desc_tag = self.soup.find('meta', attrs={'name': 'description'})

        if not desc_tag:
            self.add_issue('description', 'Missing meta description')
            return {'present': False}

        description = desc_tag.get('content', '').strip()
        length = len(description)

        result = {
            'present': True,
            'value': description,
            'length': length,
        }

        if not description:
            self.add_issue('description', 'Meta description is empty')
        elif length < 120:
            self.add_warning('description', f'Description is too short ({length} chars)',
                           'Recommended: 150-160 characters')
        elif length > 160:
            self.add_warning('description', f'Description is too long ({length} chars)',
                           'May be truncated in search results')
        else:
            self.add_success('description', f'Description length is optimal ({length} chars)', description[:50] + '...')

        return result

    def check_canonical(self) -> Dict[str, Any]:
        """Check canonical URL."""
        canonical_tag = self.soup.find('link', attrs={'rel': 'canonical'})

        if not canonical_tag:
            self.add_warning('canonical', 'Missing canonical URL')
            return {'present': False}

        canonical_url = canonical_tag.get('href', '').strip()

        result = {
            'present': True,
            'value': canonical_url,
        }

        if not canonical_url:
            self.add_issue('canonical', 'Canonical URL is empty')
        else:
            # Check if canonical is absolute
            if not canonical_url.startswith(('http://', 'https://')):
                self.add_warning('canonical', 'Canonical URL should be absolute',
                               canonical_url)
            else:
                self.add_success('canonical', 'Canonical URL is set', canonical_url)

        return result

    def check_open_graph(self) -> Dict[str, Any]:
        """Check Open Graph tags."""
        og_tags = {}

        for tag in self.soup.find_all('meta', attrs={'property': re.compile(r'^og:')}):
            property_name = tag.get('property', '')
            content = tag.get('content', '')
            og_tags[property_name] = content

        result = {
            'present': bool(og_tags),
            'tags': og_tags,
        }

        required_og = ['og:title', 'og:description', 'og:image', 'og:url', 'og:type']
        missing_og = [tag for tag in required_og if tag not in og_tags]

        if missing_og:
            self.add_warning('open_graph', f'Missing recommended OG tags: {", ".join(missing_og)}')

        if og_tags:
            self.add_success('open_graph', f'Found {len(og_tags)} Open Graph tags')

            # Check og:image dimensions
            if 'og:image' in og_tags:
                if 'og:image:width' not in og_tags or 'og:image:height' not in og_tags:
                    self.add_warning('open_graph', 'og:image missing width/height',
                                   'Recommended: 1200x630')

        return result

    def check_twitter_cards(self) -> Dict[str, Any]:
        """Check Twitter Card tags."""
        twitter_tags = {}

        for tag in self.soup.find_all('meta', attrs={'name': re.compile(r'^twitter:')}):
            name = tag.get('name', '')
            content = tag.get('content', '')
            twitter_tags[name] = content

        result = {
            'present': bool(twitter_tags),
            'tags': twitter_tags,
        }

        required_twitter = ['twitter:card', 'twitter:title', 'twitter:description']
        missing_twitter = [tag for tag in required_twitter if tag not in twitter_tags]

        if missing_twitter:
            self.add_warning('twitter', f'Missing recommended Twitter tags: {", ".join(missing_twitter)}')

        if twitter_tags:
            self.add_success('twitter', f'Found {len(twitter_tags)} Twitter Card tags')

        return result

    def check_structured_data(self) -> Dict[str, Any]:
        """Check structured data (JSON-LD)."""
        json_ld_scripts = self.soup.find_all('script', attrs={'type': 'application/ld+json'})

        structured_data = []
        for script in json_ld_scripts:
            try:
                data = json.loads(script.string)
                structured_data.append(data)
            except (json.JSONDecodeError, TypeError) as e:
                self.add_warning('structured_data', f'Invalid JSON-LD: {e}')

        result = {
            'present': bool(structured_data),
            'count': len(structured_data),
            'types': [],
        }

        if structured_data:
            for data in structured_data:
                if isinstance(data, dict):
                    schema_type = data.get('@type', 'Unknown')
                    result['types'].append(schema_type)

            self.add_success('structured_data', f'Found {len(structured_data)} JSON-LD blocks',
                           ', '.join(result['types']))
        else:
            self.add_warning('structured_data', 'No structured data (JSON-LD) found')

        return result

    def check_headings(self) -> Dict[str, Any]:
        """Check heading structure."""
        h1_tags = self.soup.find_all('h1')

        result = {
            'h1_count': len(h1_tags),
            'h1_values': [h1.get_text().strip() for h1 in h1_tags],
        }

        if len(h1_tags) == 0:
            self.add_issue('headings', 'No <h1> tag found')
        elif len(h1_tags) > 1:
            self.add_warning('headings', f'Multiple <h1> tags found ({len(h1_tags)})',
                           'Best practice: Use only one <h1> per page')
        else:
            self.add_success('headings', 'Single <h1> tag found', h1_tags[0].get_text().strip())

        return result

    def check_images(self) -> Dict[str, Any]:
        """Check image alt attributes."""
        images = self.soup.find_all('img')
        images_without_alt = [img for img in images if not img.get('alt')]

        result = {
            'total': len(images),
            'without_alt': len(images_without_alt),
        }

        if images_without_alt:
            self.add_warning('images', f'{len(images_without_alt)} of {len(images)} images missing alt text')
        elif images:
            self.add_success('images', f'All {len(images)} images have alt text')

        return result

    def check_robots_meta(self) -> Dict[str, Any]:
        """Check robots meta tag."""
        robots_tag = self.soup.find('meta', attrs={'name': 'robots'})

        if not robots_tag:
            return {'present': False}

        robots_content = robots_tag.get('content', '').strip()

        result = {
            'present': True,
            'value': robots_content,
        }

        if 'noindex' in robots_content.lower():
            self.add_warning('robots', 'Page has "noindex" directive', robots_content)

        if 'nofollow' in robots_content.lower():
            self.add_warning('robots', 'Page has "nofollow" directive', robots_content)

        return result

    def check_viewport(self) -> Dict[str, Any]:
        """Check viewport meta tag."""
        viewport_tag = self.soup.find('meta', attrs={'name': 'viewport'})

        if not viewport_tag:
            self.add_warning('viewport', 'Missing viewport meta tag',
                           'Required for mobile-friendly pages')
            return {'present': False}

        viewport_content = viewport_tag.get('content', '').strip()

        result = {
            'present': True,
            'value': viewport_content,
        }

        if 'width=device-width' in viewport_content:
            self.add_success('viewport', 'Viewport meta tag is set correctly', viewport_content)
        else:
            self.add_warning('viewport', 'Viewport meta tag missing width=device-width')

        return result

    def check_hreflang(self) -> Dict[str, Any]:
        """Check hreflang tags."""
        hreflang_tags = self.soup.find_all('link', attrs={'rel': 'alternate', 'hreflang': True})

        result = {
            'present': bool(hreflang_tags),
            'count': len(hreflang_tags),
            'languages': {},
        }

        for tag in hreflang_tags:
            hreflang = tag.get('hreflang', '')
            href = tag.get('href', '')
            result['languages'][hreflang] = href

        if hreflang_tags:
            self.add_success('hreflang', f'Found {len(hreflang_tags)} hreflang tags')

        return result

    def check_all(self) -> Dict[str, Any]:
        """Run all SEO checks."""
        if not self.fetch_page():
            return {'error': 'Failed to fetch page'}

        results = {
            'url': self.url,
            'status_code': self.response.status_code if self.response else None,
            'title': self.check_title(),
            'description': self.check_meta_description(),
            'canonical': self.check_canonical(),
            'open_graph': self.check_open_graph(),
            'twitter_cards': self.check_twitter_cards(),
            'structured_data': self.check_structured_data(),
            'headings': self.check_headings(),
            'images': self.check_images(),
            'robots': self.check_robots_meta(),
            'viewport': self.check_viewport(),
            'hreflang': self.check_hreflang(),
            'issues': self.issues,
            'warnings': self.warnings,
            'successes': self.successes,
        }

        return results


def format_text_report(results: Dict[str, Any]) -> str:
    """Format results as human-readable text."""
    lines = []
    lines.append(f"\n{'='*60}")
    lines.append(f"SEO CHECK REPORT: {results['url']}")
    lines.append(f"{'='*60}\n")

    if 'error' in results:
        lines.append(f"ERROR: {results['error']}\n")
        return '\n'.join(lines)

    lines.append(f"Status Code: {results.get('status_code', 'N/A')}\n")

    # Summary
    lines.append("SUMMARY")
    lines.append("-" * 60)
    lines.append(f"Issues:    {len(results['issues'])}")
    lines.append(f"Warnings:  {len(results['warnings'])}")
    lines.append(f"Successes: {len(results['successes'])}\n")

    # Issues
    if results['issues']:
        lines.append("ISSUES")
        lines.append("-" * 60)
        for issue in results['issues']:
            lines.append(f"[{issue['severity'].upper()}] {issue['category']}: {issue['message']}")
        lines.append("")

    # Warnings
    if results['warnings']:
        lines.append("WARNINGS")
        lines.append("-" * 60)
        for warning in results['warnings']:
            lines.append(f"[WARN] {warning['category']}: {warning['message']}")
            if 'details' in warning:
                lines.append(f"       → {warning['details']}")
        lines.append("")

    # Successes
    if results['successes']:
        lines.append("SUCCESSES")
        lines.append("-" * 60)
        for success in results['successes']:
            lines.append(f"[OK] {success['category']}: {success['message']}")
            if 'value' in success:
                lines.append(f"     → {success['value']}")
        lines.append("")

    # Details
    lines.append("DETAILS")
    lines.append("-" * 60)

    if results['title']['present']:
        lines.append(f"Title: {results['title']['value']} ({results['title']['length']} chars)")

    if results['description']['present']:
        lines.append(f"Description: {results['description']['value'][:100]}... ({results['description']['length']} chars)")

    if results['canonical']['present']:
        lines.append(f"Canonical: {results['canonical']['value']}")

    if results['open_graph']['present']:
        lines.append(f"\nOpen Graph Tags ({len(results['open_graph']['tags'])}):")
        for key, value in results['open_graph']['tags'].items():
            lines.append(f"  {key}: {value[:80]}")

    if results['twitter_cards']['present']:
        lines.append(f"\nTwitter Card Tags ({len(results['twitter_cards']['tags'])}):")
        for key, value in results['twitter_cards']['tags'].items():
            lines.append(f"  {key}: {value[:80]}")

    if results['structured_data']['present']:
        lines.append(f"\nStructured Data:")
        lines.append(f"  Count: {results['structured_data']['count']}")
        lines.append(f"  Types: {', '.join(results['structured_data']['types'])}")

    lines.append(f"\n{'='*60}\n")

    return '\n'.join(lines)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Check SEO tags on web pages',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s https://example.com
  %(prog)s https://example.com --json
  %(prog)s https://example.com --output report.json
  %(prog)s https://example.com --check-all
        """
    )

    parser.add_argument('url', help='URL to check')
    parser.add_argument('--json', action='store_true', help='Output results as JSON')
    parser.add_argument('--output', '-o', help='Write results to file')
    parser.add_argument('--check-all', action='store_true',
                       help='Run all checks (default behavior)')

    args = parser.parse_args()

    # Validate URL
    parsed = urlparse(args.url)
    if not parsed.scheme or not parsed.netloc:
        print(f"Error: Invalid URL: {args.url}", file=sys.stderr)
        sys.exit(1)

    # Run checks
    checker = SEOChecker(args.url)
    results = checker.check_all()

    # Output results
    if args.json:
        output = json.dumps(results, indent=2)
    else:
        output = format_text_report(results)

    if args.output:
        with open(args.output, 'w') as f:
            f.write(output)
        print(f"Results written to {args.output}")
    else:
        print(output)

    # Exit code based on issues
    if results.get('issues'):
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == '__main__':
    main()
