#!/usr/bin/env python3
"""
CSP Generator

Generates Content Security Policy by crawling a site and analyzing resources.
Creates policies based on actual resource usage patterns.
"""

import argparse
import json
import sys
from collections import defaultdict
from typing import Dict, List, Set, Optional
from urllib.parse import urlparse, urljoin
import requests
from bs4 import BeautifulSoup


class CSPGenerator:
    """Generates CSP policies by analyzing web pages."""

    def __init__(self, timeout: int = 10, max_pages: int = 50):
        self.timeout = timeout
        self.max_pages = max_pages
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'CSPGenerator/1.0'
        })

        # Track resource sources by directive
        self.sources: Dict[str, Set[str]] = defaultdict(set)
        self.inline_scripts: List[str] = []
        self.inline_styles: List[str] = []
        self.visited_urls: Set[str] = set()
        self.base_domain: Optional[str] = None

    def crawl(self, start_url: str, depth: int = 2) -> None:
        """Crawl site starting from URL."""
        parsed = urlparse(start_url)
        self.base_domain = f"{parsed.scheme}://{parsed.netloc}"

        self._crawl_recursive(start_url, depth)

    def _crawl_recursive(self, url: str, depth: int) -> None:
        """Recursively crawl pages."""
        if depth < 0 or len(self.visited_urls) >= self.max_pages:
            return

        if url in self.visited_urls:
            return

        self.visited_urls.add(url)
        print(f"Crawling: {url}", file=sys.stderr)

        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()

            content_type = response.headers.get('content-type', '')
            if 'text/html' not in content_type:
                return

            soup = BeautifulSoup(response.text, 'html.parser')
            self._analyze_page(soup, url)

            # Find links to crawl
            if depth > 0:
                for link in soup.find_all('a', href=True):
                    next_url = urljoin(url, link['href'])
                    parsed = urlparse(next_url)

                    # Only crawl same domain
                    if f"{parsed.scheme}://{parsed.netloc}" == self.base_domain:
                        # Remove fragment
                        next_url = next_url.split('#')[0]
                        self._crawl_recursive(next_url, depth - 1)

        except requests.RequestException as e:
            print(f"Error crawling {url}: {e}", file=sys.stderr)

    def _analyze_page(self, soup: BeautifulSoup, page_url: str) -> None:
        """Analyze page for CSP directives."""

        # Script sources
        for script in soup.find_all('script'):
            if script.get('src'):
                src = urljoin(page_url, script['src'])
                origin = self._get_origin(src)
                self.sources['script-src'].add(origin)
            elif script.string:
                # Inline script
                self.inline_scripts.append(script.string.strip())

        # Style sources
        for link in soup.find_all('link', rel='stylesheet'):
            if link.get('href'):
                href = urljoin(page_url, link['href'])
                origin = self._get_origin(href)
                self.sources['style-src'].add(origin)

        for style in soup.find_all('style'):
            if style.string:
                # Inline style
                self.inline_styles.append(style.string.strip())

        # Image sources
        for img in soup.find_all('img', src=True):
            src = urljoin(page_url, img['src'])
            if src.startswith('data:'):
                self.sources['img-src'].add('data:')
            else:
                origin = self._get_origin(src)
                self.sources['img-src'].add(origin)

        # Font sources
        for link in soup.find_all('link', rel='preload', as_='font'):
            if link.get('href'):
                href = urljoin(page_url, link['href'])
                origin = self._get_origin(href)
                self.sources['font-src'].add(origin)

        # Media sources
        for media in soup.find_all(['audio', 'video'], src=True):
            src = urljoin(page_url, media['src'])
            origin = self._get_origin(src)
            self.sources['media-src'].add(origin)

        for source in soup.find_all('source', src=True):
            src = urljoin(page_url, source['src'])
            origin = self._get_origin(src)
            self.sources['media-src'].add(origin)

        # Object/embed sources
        for obj in soup.find_all(['object', 'embed'], src=True):
            src = urljoin(page_url, obj['src'])
            origin = self._get_origin(src)
            self.sources['object-src'].add(origin)

        # Frame sources
        for frame in soup.find_all(['iframe', 'frame'], src=True):
            src = urljoin(page_url, frame['src'])
            origin = self._get_origin(src)
            self.sources['frame-src'].add(origin)

        # Form actions
        for form in soup.find_all('form', action=True):
            action = urljoin(page_url, form['action'])
            origin = self._get_origin(action)
            self.sources['form-action'].add(origin)

        # Manifest
        for link in soup.find_all('link', rel='manifest'):
            if link.get('href'):
                href = urljoin(page_url, link['href'])
                origin = self._get_origin(href)
                self.sources['manifest-src'].add(origin)

    def _get_origin(self, url: str) -> str:
        """Extract origin from URL."""
        parsed = urlparse(url)

        # Special cases
        if url.startswith('data:'):
            return 'data:'
        if url.startswith('blob:'):
            return 'blob:'

        origin = f"{parsed.scheme}://{parsed.netloc}"

        # Normalize self
        if origin == self.base_domain:
            return "'self'"

        return origin

    def generate_policy(
        self,
        strict: bool = False,
        allow_inline: bool = False,
        use_hashes: bool = False
    ) -> str:
        """Generate CSP policy string."""
        directives = []

        # Always set default-src
        default_sources = ["'self'"]
        directives.append(f"default-src {' '.join(default_sources)}")

        # Script-src
        script_sources = self._get_sources('script-src', strict)
        if self.inline_scripts:
            if use_hashes:
                # Generate hashes for inline scripts
                import hashlib
                import base64
                for script in self.inline_scripts[:5]:  # Limit to first 5
                    script_hash = hashlib.sha256(script.encode()).digest()
                    hash_value = base64.b64encode(script_hash).decode()
                    script_sources.add(f"'sha256-{hash_value}'")
            elif allow_inline:
                script_sources.add("'unsafe-inline'")

        if script_sources:
            directives.append(f"script-src {' '.join(sorted(script_sources))}")

        # Style-src
        style_sources = self._get_sources('style-src', strict)
        if self.inline_styles and allow_inline:
            style_sources.add("'unsafe-inline'")

        if style_sources:
            directives.append(f"style-src {' '.join(sorted(style_sources))}")

        # Img-src
        img_sources = self._get_sources('img-src', strict)
        if img_sources:
            directives.append(f"img-src {' '.join(sorted(img_sources))}")

        # Font-src
        font_sources = self._get_sources('font-src', strict)
        if font_sources:
            directives.append(f"font-src {' '.join(sorted(font_sources))}")

        # Connect-src (default to self for API calls)
        connect_sources = self._get_sources('connect-src', strict)
        if not connect_sources:
            connect_sources = {"'self'"}
        directives.append(f"connect-src {' '.join(sorted(connect_sources))}")

        # Media-src
        media_sources = self._get_sources('media-src', strict)
        if media_sources:
            directives.append(f"media-src {' '.join(sorted(media_sources))}")

        # Object-src (always none in strict mode)
        if strict or 'object-src' not in self.sources:
            directives.append("object-src 'none'")
        else:
            object_sources = self._get_sources('object-src', strict)
            directives.append(f"object-src {' '.join(sorted(object_sources))}")

        # Frame-src
        frame_sources = self._get_sources('frame-src', strict)
        if frame_sources:
            directives.append(f"frame-src {' '.join(sorted(frame_sources))}")

        # Form-action
        form_sources = self._get_sources('form-action', strict)
        if not form_sources:
            form_sources = {"'self'"}
        directives.append(f"form-action {' '.join(sorted(form_sources))}")

        # Base-uri (always restrict)
        directives.append("base-uri 'self'")

        # Frame-ancestors (prevent clickjacking)
        if strict:
            directives.append("frame-ancestors 'none'")

        # Manifest-src
        manifest_sources = self._get_sources('manifest-src', strict)
        if manifest_sources:
            directives.append(f"manifest-src {' '.join(sorted(manifest_sources))}")

        return '; '.join(directives)

    def _get_sources(self, directive: str, strict: bool) -> Set[str]:
        """Get sources for directive."""
        sources = self.sources.get(directive, set()).copy()

        # Always include 'self' unless strict mode excludes it
        if sources and not strict:
            sources.add("'self'")

        return sources

    def generate_report(self) -> Dict:
        """Generate detailed report."""
        return {
            'pages_crawled': len(self.visited_urls),
            'base_domain': self.base_domain,
            'inline_scripts': len(self.inline_scripts),
            'inline_styles': len(self.inline_styles),
            'sources': {
                directive: sorted(list(sources))
                for directive, sources in self.sources.items()
            },
            'urls_crawled': sorted(list(self.visited_urls))
        }


def main():
    parser = argparse.ArgumentParser(
        description="Generate Content Security Policy by crawling a site",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s https://example.com
  %(prog)s https://example.com --strict
  %(prog)s https://example.com --depth 3 --max-pages 100
  %(prog)s https://example.com --use-hashes --json
  %(prog)s https://example.com --allow-inline --report
        """
    )

    parser.add_argument(
        'url',
        help='Starting URL to crawl'
    )
    parser.add_argument(
        '--depth',
        type=int,
        default=2,
        help='Crawl depth (default: 2)'
    )
    parser.add_argument(
        '--max-pages',
        type=int,
        default=50,
        help='Maximum pages to crawl (default: 50)'
    )
    parser.add_argument(
        '--timeout',
        type=int,
        default=10,
        help='Request timeout in seconds (default: 10)'
    )
    parser.add_argument(
        '--strict',
        action='store_true',
        help='Generate strict policy (no unsafe directives)'
    )
    parser.add_argument(
        '--allow-inline',
        action='store_true',
        help="Include 'unsafe-inline' for inline scripts/styles"
    )
    parser.add_argument(
        '--use-hashes',
        action='store_true',
        help='Generate hashes for inline scripts (first 5)'
    )
    parser.add_argument(
        '--report',
        action='store_true',
        help='Include detailed report of sources found'
    )
    parser.add_argument(
        '--json',
        action='store_true',
        help='Output as JSON'
    )

    args = parser.parse_args()

    generator = CSPGenerator(timeout=args.timeout, max_pages=args.max_pages)

    print(f"Crawling {args.url}...", file=sys.stderr)
    generator.crawl(args.url, depth=args.depth)

    policy = generator.generate_policy(
        strict=args.strict,
        allow_inline=args.allow_inline,
        use_hashes=args.use_hashes
    )

    if args.json:
        result = {
            'policy': policy,
            'directives': dict(
                line.split(' ', 1) if ' ' in line else (line, '')
                for line in policy.split('; ')
            )
        }

        if args.report:
            result['report'] = generator.generate_report()

        print(json.dumps(result, indent=2))
    else:
        print("\nGenerated CSP Policy:")
        print("=" * 80)
        print(policy)
        print("=" * 80)

        if args.report:
            report = generator.generate_report()
            print("\nReport:")
            print(f"  Pages crawled: {report['pages_crawled']}")
            print(f"  Base domain: {report['base_domain']}")
            print(f"  Inline scripts: {report['inline_scripts']}")
            print(f"  Inline styles: {report['inline_styles']}")
            print("\n  Sources by directive:")
            for directive, sources in report['sources'].items():
                print(f"    {directive}:")
                for source in sources:
                    print(f"      - {source}")

        print("\nNext steps:")
        print("  1. Test policy in report-only mode:")
        print(f"     Content-Security-Policy-Report-Only: {policy}")
        print("  2. Monitor CSP violations in your report endpoint")
        print("  3. Adjust policy based on violations")
        print("  4. Deploy in enforcement mode:")
        print(f"     Content-Security-Policy: {policy}")


if __name__ == '__main__':
    main()
