#!/usr/bin/env python3
"""
Next.js Sitemap Generator

Generates sitemap.xml from Next.js routes by scanning the app directory structure.
Supports App Router, dynamic routes, and customizable priorities.

Usage:
    ./generate_sitemap.py
    ./generate_sitemap.py --app-dir ./app --output public/sitemap.xml
    ./generate_sitemap.py --base-url https://example.com
    ./generate_sitemap.py --exclude /admin /api --json
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from xml.dom import minidom
from xml.etree.ElementTree import Element, SubElement, tostring


class RouteInfo:
    """Information about a Next.js route."""

    def __init__(
        self,
        path: str,
        priority: float = 0.5,
        changefreq: str = 'weekly',
        lastmod: Optional[str] = None,
    ):
        self.path = path
        self.priority = priority
        self.changefreq = changefreq
        self.lastmod = lastmod or datetime.now().strftime('%Y-%m-%d')

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'path': self.path,
            'priority': self.priority,
            'changefreq': self.changefreq,
            'lastmod': self.lastmod,
        }


class SitemapGenerator:
    """Generate sitemap from Next.js App Router directory."""

    def __init__(
        self,
        app_dir: str = './app',
        base_url: str = 'https://example.com',
        exclude_patterns: Optional[List[str]] = None,
    ):
        self.app_dir = Path(app_dir)
        self.base_url = base_url.rstrip('/')
        self.exclude_patterns = exclude_patterns or []
        self.routes: List[RouteInfo] = []

    def is_excluded(self, path: str) -> bool:
        """Check if path matches any exclude pattern."""
        for pattern in self.exclude_patterns:
            if path.startswith(pattern):
                return True
        return False

    def get_priority(self, path: str) -> float:
        """Determine priority based on path depth and type."""
        # Root page gets highest priority
        if path == '/':
            return 1.0

        # Count path segments
        segments = [s for s in path.split('/') if s]
        depth = len(segments)

        # Check for dynamic routes
        is_dynamic = '[' in path

        # Priority based on depth and type
        if depth == 1:
            return 0.9 if not is_dynamic else 0.7
        elif depth == 2:
            return 0.7 if not is_dynamic else 0.6
        else:
            return 0.5

    def get_changefreq(self, path: str) -> str:
        """Determine change frequency based on path type."""
        if path == '/':
            return 'daily'
        elif 'blog' in path or 'news' in path:
            return 'weekly'
        elif 'docs' in path:
            return 'monthly'
        else:
            return 'weekly'

    def scan_directory(self, dir_path: Path, route_path: str = '') -> None:
        """Recursively scan directory for route files."""
        if not dir_path.exists() or not dir_path.is_dir():
            return

        # Check for page.tsx, page.ts, page.jsx, page.js
        page_files = [
            'page.tsx', 'page.ts', 'page.jsx', 'page.js'
        ]

        has_page = any((dir_path / f).exists() for f in page_files)

        if has_page:
            # This directory represents a route
            current_route = route_path or '/'

            if not self.is_excluded(current_route):
                route_info = RouteInfo(
                    path=current_route,
                    priority=self.get_priority(current_route),
                    changefreq=self.get_changefreq(current_route),
                )
                self.routes.append(route_info)

        # Scan subdirectories
        for item in dir_path.iterdir():
            if not item.is_dir():
                continue

            dirname = item.name

            # Skip special Next.js directories
            if dirname.startswith(('_', '.')):
                continue

            # Handle route groups (folder)
            if dirname.startswith('(') and dirname.endswith(')'):
                # Route groups don't affect the URL
                self.scan_directory(item, route_path)
                continue

            # Handle dynamic routes [param]
            if dirname.startswith('[') and dirname.endswith(']'):
                # Dynamic route - we'll mark it but won't include specific instances
                param_name = dirname[1:-1]
                new_route = f"{route_path}/{dirname}"

                # Check if there's a page at this level
                if any((item / f).exists() for f in page_files):
                    if not self.is_excluded(new_route):
                        route_info = RouteInfo(
                            path=new_route,
                            priority=self.get_priority(new_route),
                            changefreq=self.get_changefreq(new_route),
                        )
                        self.routes.append(route_info)

                # Continue scanning subdirectories
                self.scan_directory(item, new_route)
                continue

            # Handle catch-all routes [...param]
            if dirname.startswith('[...') and dirname.endswith(']'):
                new_route = f"{route_path}/{dirname}"
                if not self.is_excluded(new_route):
                    route_info = RouteInfo(
                        path=new_route,
                        priority=0.5,
                        changefreq='weekly',
                    )
                    self.routes.append(route_info)
                continue

            # Handle optional catch-all [[...param]]
            if dirname.startswith('[[...') and dirname.endswith(']]'):
                new_route = f"{route_path}/{dirname}"
                if not self.is_excluded(new_route):
                    route_info = RouteInfo(
                        path=new_route,
                        priority=0.5,
                        changefreq='weekly',
                    )
                    self.routes.append(route_info)
                continue

            # Regular directory
            new_route = f"{route_path}/{dirname}"
            self.scan_directory(item, new_route)

    def generate_routes(self) -> List[RouteInfo]:
        """Generate list of routes from app directory."""
        self.routes = []
        self.scan_directory(self.app_dir)
        return self.routes

    def generate_xml(self) -> str:
        """Generate sitemap XML."""
        urlset = Element('urlset')
        urlset.set('xmlns', 'http://www.sitemaps.org/schemas/sitemap/0.9')

        for route in self.routes:
            url_elem = SubElement(urlset, 'url')

            # Build full URL
            full_url = f"{self.base_url}{route.path}"

            SubElement(url_elem, 'loc').text = full_url
            SubElement(url_elem, 'lastmod').text = route.lastmod
            SubElement(url_elem, 'changefreq').text = route.changefreq
            SubElement(url_elem, 'priority').text = str(route.priority)

        # Pretty print XML
        xml_string = tostring(urlset, encoding='unicode')
        dom = minidom.parseString(xml_string)
        return dom.toprettyxml(indent='  ', encoding='UTF-8').decode('utf-8')

    def generate_json(self) -> str:
        """Generate sitemap as JSON."""
        data = {
            'generated': datetime.now().isoformat(),
            'base_url': self.base_url,
            'routes': [route.to_dict() for route in self.routes],
        }
        return json.dumps(data, indent=2)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Generate sitemap.xml from Next.js App Router',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s
  %(prog)s --app-dir ./app --output public/sitemap.xml
  %(prog)s --base-url https://example.com
  %(prog)s --exclude /admin /api /private
  %(prog)s --json
  %(prog)s --dry-run

Notes:
  - Scans app directory for page.tsx/ts/jsx/js files
  - Supports dynamic routes ([id]), catch-all ([...slug]), and optional catch-all ([[...slug]])
  - Route groups (folder) are ignored in URL paths
  - Automatically assigns priorities based on path depth
  - Change frequencies are assigned based on path patterns
        """
    )

    parser.add_argument(
        '--app-dir',
        default='./app',
        help='Path to Next.js app directory (default: ./app)'
    )

    parser.add_argument(
        '--base-url',
        default='https://example.com',
        help='Base URL for the site (default: https://example.com)'
    )

    parser.add_argument(
        '--output', '-o',
        default='public/sitemap.xml',
        help='Output file path (default: public/sitemap.xml)'
    )

    parser.add_argument(
        '--exclude',
        nargs='+',
        default=['/api', '/_'],
        help='Paths to exclude from sitemap (default: /api /_)'
    )

    parser.add_argument(
        '--json',
        action='store_true',
        help='Output JSON instead of XML'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Print sitemap without writing to file'
    )

    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Verbose output'
    )

    args = parser.parse_args()

    # Check if app directory exists
    if not os.path.exists(args.app_dir):
        print(f"Error: App directory not found: {args.app_dir}", file=sys.stderr)
        sys.exit(1)

    # Generate sitemap
    generator = SitemapGenerator(
        app_dir=args.app_dir,
        base_url=args.base_url,
        exclude_patterns=args.exclude,
    )

    if args.verbose:
        print(f"Scanning {args.app_dir}...", file=sys.stderr)

    routes = generator.generate_routes()

    if args.verbose:
        print(f"Found {len(routes)} routes", file=sys.stderr)

    if not routes:
        print("Warning: No routes found", file=sys.stderr)

    # Generate output
    if args.json:
        output = generator.generate_json()
    else:
        output = generator.generate_xml()

    # Write or print
    if args.dry_run:
        print(output)
    else:
        # Create output directory if needed
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(args.output, 'w') as f:
            f.write(output)

        print(f"Sitemap generated: {args.output}")

        if args.verbose:
            print(f"\nRoute summary:")
            for route in routes:
                print(f"  {route.path} (priority: {route.priority}, changefreq: {route.changefreq})")


if __name__ == '__main__':
    main()
