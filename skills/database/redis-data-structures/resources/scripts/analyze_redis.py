#!/usr/bin/env python3
"""
Redis Memory and Key Pattern Analyzer

Analyzes Redis memory usage, key patterns, and provides optimization recommendations.
"""

import argparse
import json
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Tuple

try:
    import redis
except ImportError:
    print("Error: redis package required. Install with: pip install redis", file=sys.stderr)
    sys.exit(1)


@dataclass
class KeyPattern:
    """Represents a key pattern analysis."""
    pattern: str
    count: int
    total_memory: int
    avg_memory: float
    max_memory: int
    ttl_set: int
    ttl_not_set: int
    type_distribution: Dict[str, int]
    encoding_distribution: Dict[str, int]


@dataclass
class MemoryAnalysis:
    """Complete memory analysis results."""
    total_memory_used: int
    total_memory_human: str
    total_keys: int
    total_expires: int
    avg_key_size: float
    patterns: List[KeyPattern]
    type_distribution: Dict[str, int]
    encoding_distribution: Dict[str, int]
    recommendations: List[str]


class RedisAnalyzer:
    """Analyzes Redis memory usage and key patterns."""

    def __init__(self, host: str = 'localhost', port: int = 6379,
                 password: Optional[str] = None, db: int = 0):
        """Initialize Redis connection."""
        self.client = redis.Redis(
            host=host,
            port=port,
            password=password,
            db=db,
            decode_responses=True
        )

    def _format_bytes(self, bytes_val: int) -> str:
        """Format bytes to human-readable string."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_val < 1024.0:
                return f"{bytes_val:.2f}{unit}"
            bytes_val /= 1024.0
        return f"{bytes_val:.2f}PB"

    def _extract_pattern(self, key: str) -> str:
        """Extract pattern from key by replacing IDs with placeholders."""
        # Replace UUIDs
        key = re.sub(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',
                     '<uuid>', key, flags=re.IGNORECASE)

        # Replace numbers (likely IDs)
        key = re.sub(r'\b\d+\b', '<id>', key)

        # Replace hexadecimal strings
        key = re.sub(r'\b[0-9a-f]{8,}\b', '<hex>', key, flags=re.IGNORECASE)

        return key

    def _get_key_memory(self, key: str) -> int:
        """Get memory usage for a specific key."""
        try:
            return self.client.memory_usage(key) or 0
        except redis.exceptions.ResponseError:
            # MEMORY USAGE not available, estimate
            return len(key.encode()) + 100  # Key overhead + approximate value

    def _get_key_ttl(self, key: str) -> int:
        """Get TTL for key (-1 = no expiry, -2 = doesn't exist)."""
        return self.client.ttl(key)

    def _get_key_type(self, key: str) -> str:
        """Get data type of key."""
        return self.client.type(key)

    def _get_key_encoding(self, key: str) -> str:
        """Get encoding of key."""
        try:
            return self.client.object('encoding', key) or 'unknown'
        except redis.exceptions.ResponseError:
            return 'unknown'

    def analyze_keys(self, pattern: str = '*', sample_size: Optional[int] = None) -> MemoryAnalysis:
        """
        Analyze Redis keys and memory usage.

        Args:
            pattern: Key pattern to match (default: all keys)
            sample_size: Limit analysis to N keys (default: all)

        Returns:
            MemoryAnalysis object with complete analysis
        """
        # Get server info
        info = self.client.info('memory')
        total_memory = info.get('used_memory', 0)

        # Scan keys
        patterns_data = defaultdict(lambda: {
            'count': 0,
            'total_memory': 0,
            'max_memory': 0,
            'ttl_set': 0,
            'ttl_not_set': 0,
            'types': defaultdict(int),
            'encodings': defaultdict(int)
        })

        total_keys = 0
        total_expires = 0
        type_distribution = defaultdict(int)
        encoding_distribution = defaultdict(int)

        cursor = 0
        while True:
            cursor, keys = self.client.scan(cursor, match=pattern, count=1000)

            for key in keys:
                total_keys += 1

                # Sample limit
                if sample_size and total_keys > sample_size:
                    break

                # Get key info
                memory = self._get_key_memory(key)
                ttl = self._get_key_ttl(key)
                key_type = self._get_key_type(key)
                encoding = self._get_key_encoding(key)

                # Extract pattern
                key_pattern = self._extract_pattern(key)

                # Update pattern data
                p_data = patterns_data[key_pattern]
                p_data['count'] += 1
                p_data['total_memory'] += memory
                p_data['max_memory'] = max(p_data['max_memory'], memory)
                p_data['types'][key_type] += 1
                p_data['encodings'][encoding] += 1

                if ttl > 0:
                    p_data['ttl_set'] += 1
                    total_expires += 1
                else:
                    p_data['ttl_not_set'] += 1

                # Update global stats
                type_distribution[key_type] += 1
                encoding_distribution[encoding] += 1

            if cursor == 0 or (sample_size and total_keys >= sample_size):
                break

        # Build pattern results
        patterns = []
        for pattern_key, data in patterns_data.items():
            avg_memory = data['total_memory'] / data['count'] if data['count'] > 0 else 0
            patterns.append(KeyPattern(
                pattern=pattern_key,
                count=data['count'],
                total_memory=data['total_memory'],
                avg_memory=avg_memory,
                max_memory=data['max_memory'],
                ttl_set=data['ttl_set'],
                ttl_not_set=data['ttl_not_set'],
                type_distribution=dict(data['types']),
                encoding_distribution=dict(data['encodings'])
            ))

        # Sort by memory usage
        patterns.sort(key=lambda x: x.total_memory, reverse=True)

        # Generate recommendations
        recommendations = self._generate_recommendations(
            patterns, type_distribution, encoding_distribution, total_keys, total_expires
        )

        avg_key_size = total_memory / total_keys if total_keys > 0 else 0

        return MemoryAnalysis(
            total_memory_used=total_memory,
            total_memory_human=self._format_bytes(total_memory),
            total_keys=total_keys,
            total_expires=total_expires,
            avg_key_size=avg_key_size,
            patterns=patterns,
            type_distribution=dict(type_distribution),
            encoding_distribution=dict(encoding_distribution),
            recommendations=recommendations
        )

    def _generate_recommendations(self, patterns: List[KeyPattern],
                                   type_dist: Dict, encoding_dist: Dict,
                                   total_keys: int, total_expires: int) -> List[str]:
        """Generate optimization recommendations."""
        recommendations = []

        # Check for keys without TTL
        no_ttl_ratio = (total_keys - total_expires) / total_keys if total_keys > 0 else 0
        if no_ttl_ratio > 0.5:
            recommendations.append(
                f"High ratio of keys without TTL ({no_ttl_ratio:.1%}). "
                "Consider setting expiration on temporary data."
            )

        # Check for large keys
        large_patterns = [p for p in patterns if p.max_memory > 1_000_000]  # > 1MB
        if large_patterns:
            recommendations.append(
                f"Found {len(large_patterns)} pattern(s) with keys > 1MB. "
                "Consider splitting large values or using compression."
            )

        # Check encoding efficiency
        if 'hashtable' in encoding_dist and 'ziplist' in encoding_dist:
            ht_count = encoding_dist['hashtable']
            zl_count = encoding_dist['ziplist']
            if ht_count > zl_count * 2:
                recommendations.append(
                    "Many keys using hashtable encoding. Consider keeping hashes/sets smaller "
                    "to use ziplist encoding (more memory efficient)."
                )

        # Check string encoding
        if 'raw' in encoding_dist:
            raw_count = encoding_dist['raw']
            if raw_count > total_keys * 0.3:
                recommendations.append(
                    f"{raw_count} keys using 'raw' string encoding. "
                    "Consider using shorter strings or integers where possible."
                )

        # Check for fragmented patterns
        single_key_patterns = [p for p in patterns if p.count == 1]
        if len(single_key_patterns) > total_keys * 0.1:
            recommendations.append(
                f"Found {len(single_key_patterns)} single-key patterns. "
                "Consider using consistent naming conventions to reduce fragmentation."
            )

        # Check type distribution
        if 'string' in type_dist and type_dist['string'] > total_keys * 0.7:
            recommendations.append(
                "High usage of string type. Consider using hashes for multi-field objects "
                "to reduce memory overhead."
            )

        if not recommendations:
            recommendations.append("No major optimization opportunities detected. Good job!")

        return recommendations

    def find_large_keys(self, threshold_mb: float = 1.0, limit: int = 10) -> List[Tuple[str, int, str]]:
        """
        Find largest keys in Redis.

        Args:
            threshold_mb: Minimum size in MB
            limit: Maximum number of keys to return

        Returns:
            List of (key, memory_bytes, memory_human) tuples
        """
        threshold_bytes = int(threshold_mb * 1024 * 1024)
        large_keys = []

        cursor = 0
        while True:
            cursor, keys = self.client.scan(cursor, count=1000)

            for key in keys:
                memory = self._get_key_memory(key)
                if memory >= threshold_bytes:
                    large_keys.append((key, memory, self._format_bytes(memory)))

            if cursor == 0:
                break

        # Sort by size and limit
        large_keys.sort(key=lambda x: x[1], reverse=True)
        return large_keys[:limit]

    def analyze_pattern(self, pattern: str) -> Dict:
        """
        Detailed analysis of specific key pattern.

        Args:
            pattern: Key pattern to analyze

        Returns:
            Dictionary with detailed pattern analysis
        """
        keys = list(self.client.scan_iter(match=pattern))

        if not keys:
            return {'error': 'No keys found matching pattern'}

        # Sample keys for detailed analysis
        sample_keys = keys[:min(100, len(keys))]

        memories = []
        ttls = []
        types = defaultdict(int)
        encodings = defaultdict(int)

        for key in sample_keys:
            memories.append(self._get_key_memory(key))
            ttl = self._get_key_ttl(key)
            if ttl > 0:
                ttls.append(ttl)
            types[self._get_key_type(key)] += 1
            encodings[self._get_key_encoding(key)] += 1

        return {
            'pattern': pattern,
            'total_keys': len(keys),
            'sample_size': len(sample_keys),
            'memory': {
                'total': sum(memories),
                'total_human': self._format_bytes(sum(memories)),
                'avg': sum(memories) / len(memories) if memories else 0,
                'avg_human': self._format_bytes(sum(memories) / len(memories)) if memories else '0B',
                'min': min(memories) if memories else 0,
                'max': max(memories) if memories else 0,
            },
            'ttl': {
                'keys_with_ttl': len(ttls),
                'keys_without_ttl': len(sample_keys) - len(ttls),
                'avg_ttl': sum(ttls) / len(ttls) if ttls else None,
                'min_ttl': min(ttls) if ttls else None,
                'max_ttl': max(ttls) if ttls else None,
            },
            'types': dict(types),
            'encodings': dict(encodings),
            'sample_keys': sample_keys[:10]  # First 10 keys
        }


def main():
    parser = argparse.ArgumentParser(
        description='Analyze Redis memory usage and key patterns',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze all keys
  %(prog)s

  # Analyze with JSON output
  %(prog)s --json

  # Analyze specific pattern
  %(prog)s --pattern "user:*"

  # Find large keys
  %(prog)s --large-keys --threshold 5

  # Detailed pattern analysis
  %(prog)s --analyze-pattern "session:*"

  # Connect to remote Redis
  %(prog)s --host redis.example.com --port 6380 --password secret
        """
    )

    # Connection options
    parser.add_argument('--host', default='localhost', help='Redis host (default: localhost)')
    parser.add_argument('--port', type=int, default=6379, help='Redis port (default: 6379)')
    parser.add_argument('--password', help='Redis password')
    parser.add_argument('--db', type=int, default=0, help='Redis database (default: 0)')

    # Analysis options
    parser.add_argument('--pattern', default='*', help='Key pattern to analyze (default: *)')
    parser.add_argument('--sample-size', type=int, help='Limit analysis to N keys')
    parser.add_argument('--large-keys', action='store_true', help='Find largest keys')
    parser.add_argument('--threshold', type=float, default=1.0,
                       help='Threshold in MB for large keys (default: 1.0)')
    parser.add_argument('--limit', type=int, default=10,
                       help='Maximum number of large keys to show (default: 10)')
    parser.add_argument('--analyze-pattern', help='Detailed analysis of specific pattern')

    # Output options
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')

    args = parser.parse_args()

    try:
        analyzer = RedisAnalyzer(
            host=args.host,
            port=args.port,
            password=args.password,
            db=args.db
        )

        # Test connection
        analyzer.client.ping()

        if args.large_keys:
            # Find large keys
            large_keys = analyzer.find_large_keys(args.threshold, args.limit)

            if args.json:
                result = [{'key': k, 'memory_bytes': m, 'memory_human': h}
                         for k, m, h in large_keys]
                print(json.dumps(result, indent=2))
            else:
                print(f"\nLarge Keys (> {args.threshold} MB):")
                print("-" * 80)
                for key, memory, human in large_keys:
                    print(f"{human:>12} {key}")

        elif args.analyze_pattern:
            # Detailed pattern analysis
            result = analyzer.analyze_pattern(args.analyze_pattern)

            if args.json:
                print(json.dumps(result, indent=2))
            else:
                if 'error' in result:
                    print(f"Error: {result['error']}")
                    sys.exit(1)

                print(f"\nPattern Analysis: {result['pattern']}")
                print("-" * 80)
                print(f"Total keys: {result['total_keys']:,}")
                print(f"Sample size: {result['sample_size']:,}")
                print(f"\nMemory:")
                print(f"  Total: {result['memory']['total_human']}")
                print(f"  Average: {result['memory']['avg_human']}")
                print(f"  Range: {analyzer._format_bytes(result['memory']['min'])} - "
                      f"{analyzer._format_bytes(result['memory']['max'])}")
                print(f"\nTTL:")
                print(f"  Keys with TTL: {result['ttl']['keys_with_ttl']}")
                print(f"  Keys without TTL: {result['ttl']['keys_without_ttl']}")
                if result['ttl']['avg_ttl']:
                    print(f"  Average TTL: {result['ttl']['avg_ttl']:.0f} seconds")
                print(f"\nTypes: {json.dumps(result['types'], indent=2)}")
                print(f"\nEncodings: {json.dumps(result['encodings'], indent=2)}")
                if args.verbose and result['sample_keys']:
                    print(f"\nSample Keys:")
                    for key in result['sample_keys']:
                        print(f"  {key}")

        else:
            # Full analysis
            analysis = analyzer.analyze_keys(args.pattern, args.sample_size)

            if args.json:
                # Convert to dict for JSON serialization
                result = {
                    'total_memory_used': analysis.total_memory_used,
                    'total_memory_human': analysis.total_memory_human,
                    'total_keys': analysis.total_keys,
                    'total_expires': analysis.total_expires,
                    'avg_key_size': analysis.avg_key_size,
                    'patterns': [asdict(p) for p in analysis.patterns],
                    'type_distribution': analysis.type_distribution,
                    'encoding_distribution': analysis.encoding_distribution,
                    'recommendations': analysis.recommendations
                }
                print(json.dumps(result, indent=2))
            else:
                print("\n" + "=" * 80)
                print("Redis Memory Analysis")
                print("=" * 80)
                print(f"\nTotal Memory Used: {analysis.total_memory_human}")
                print(f"Total Keys: {analysis.total_keys:,}")
                print(f"Keys with Expiration: {analysis.total_expires:,}")
                print(f"Average Key Size: {analyzer._format_bytes(analysis.avg_key_size)}")

                print(f"\n\nType Distribution:")
                print("-" * 40)
                for key_type, count in sorted(analysis.type_distribution.items(),
                                             key=lambda x: x[1], reverse=True):
                    pct = (count / analysis.total_keys * 100) if analysis.total_keys > 0 else 0
                    print(f"{key_type:15} {count:8,} ({pct:5.1f}%)")

                print(f"\n\nEncoding Distribution:")
                print("-" * 40)
                for encoding, count in sorted(analysis.encoding_distribution.items(),
                                              key=lambda x: x[1], reverse=True):
                    pct = (count / analysis.total_keys * 100) if analysis.total_keys > 0 else 0
                    print(f"{encoding:15} {count:8,} ({pct:5.1f}%)")

                print(f"\n\nTop Patterns by Memory:")
                print("-" * 80)
                for i, pattern in enumerate(analysis.patterns[:20], 1):
                    pct = (pattern.total_memory / analysis.total_memory_used * 100) \
                          if analysis.total_memory_used > 0 else 0
                    print(f"\n{i}. {pattern.pattern}")
                    print(f"   Keys: {pattern.count:,} | "
                          f"Memory: {analyzer._format_bytes(pattern.total_memory)} ({pct:.1f}%) | "
                          f"Avg: {analyzer._format_bytes(pattern.avg_memory)}")
                    print(f"   TTL: {pattern.ttl_set} with, {pattern.ttl_not_set} without")
                    if args.verbose:
                        print(f"   Types: {pattern.type_distribution}")
                        print(f"   Encodings: {pattern.encoding_distribution}")

                print(f"\n\nRecommendations:")
                print("-" * 80)
                for i, rec in enumerate(analysis.recommendations, 1):
                    print(f"{i}. {rec}")

                print("\n")

    except redis.exceptions.ConnectionError as e:
        print(f"Error: Cannot connect to Redis at {args.host}:{args.port}", file=sys.stderr)
        print(f"Details: {e}", file=sys.stderr)
        sys.exit(1)
    except redis.exceptions.AuthenticationError:
        print("Error: Authentication failed. Check password.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
