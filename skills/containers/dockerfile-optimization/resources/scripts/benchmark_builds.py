#!/usr/bin/env python3
"""
Benchmark Docker build times with different optimization strategies.

Compares:
- Build with cache
- Build without cache
- BuildKit vs legacy builder
- Different base images
- Multi-stage vs single-stage
"""

import argparse
import json
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Any, Optional


@dataclass
class BuildResult:
    """Results from a single build."""
    name: str
    duration: float
    image_size: int
    success: bool
    error: Optional[str] = None
    cache_used: bool = False


@dataclass
class BenchmarkResults:
    """Complete benchmark results."""
    dockerfile: str
    builds: List[BuildResult] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)


class DockerBuildBenchmark:
    """Benchmark Docker builds with various strategies."""

    def __init__(self, dockerfile: Path, image_name: str, context: Path = None):
        self.dockerfile = dockerfile
        self.image_name = image_name
        self.context = context or dockerfile.parent
        self.results = BenchmarkResults(dockerfile=str(dockerfile))

    def run_benchmarks(self, strategies: List[str]) -> BenchmarkResults:
        """Run all requested benchmark strategies."""
        print(f"Starting benchmarks for {self.dockerfile}")
        print(f"Image: {self.image_name}")
        print(f"Context: {self.context}")
        print()

        for strategy in strategies:
            if strategy == 'cached':
                self._benchmark_cached_build()
            elif strategy == 'no-cache':
                self._benchmark_no_cache_build()
            elif strategy == 'buildkit':
                self._benchmark_buildkit()
            elif strategy == 'legacy':
                self._benchmark_legacy()
            elif strategy == 'parallel':
                self._benchmark_parallel_stages()
            elif strategy == 'cache-mount':
                self._benchmark_cache_mount()

        return self.results

    def _benchmark_cached_build(self) -> None:
        """Benchmark build with cache."""
        print("Benchmarking: Cached build")

        # First build to warm cache
        self._build_image(f"{self.image_name}:cache-warm", use_cache=True, quiet=True)

        # Timed build
        result = self._build_image(f"{self.image_name}:cached", use_cache=True)
        result.name = "Cached build"
        result.cache_used = True
        self.results.builds.append(result)

        self._print_result(result)

    def _benchmark_no_cache_build(self) -> None:
        """Benchmark build without cache."""
        print("Benchmarking: No-cache build")

        result = self._build_image(f"{self.image_name}:no-cache", use_cache=False)
        result.name = "No-cache build"
        self.results.builds.append(result)

        self._print_result(result)

    def _benchmark_buildkit(self) -> None:
        """Benchmark with BuildKit enabled."""
        print("Benchmarking: BuildKit")

        result = self._build_image(
            f"{self.image_name}:buildkit",
            use_cache=False,
            use_buildkit=True
        )
        result.name = "BuildKit"
        self.results.builds.append(result)

        self._print_result(result)

    def _benchmark_legacy(self) -> None:
        """Benchmark with legacy builder."""
        print("Benchmarking: Legacy builder")

        result = self._build_image(
            f"{self.image_name}:legacy",
            use_cache=False,
            use_buildkit=False
        )
        result.name = "Legacy builder"
        self.results.builds.append(result)

        self._print_result(result)

    def _benchmark_parallel_stages(self) -> None:
        """Benchmark parallel stage execution (BuildKit feature)."""
        print("Benchmarking: Parallel stages (BuildKit)")

        # Check if Dockerfile has multiple FROM statements
        content = self.dockerfile.read_text()
        from_count = content.upper().count('FROM ')

        if from_count < 2:
            print("  Skipped: Dockerfile does not have multiple stages")
            return

        result = self._build_image(
            f"{self.image_name}:parallel",
            use_cache=False,
            use_buildkit=True
        )
        result.name = "Parallel stages"
        self.results.builds.append(result)

        self._print_result(result)

    def _benchmark_cache_mount(self) -> None:
        """Benchmark cache mount feature (BuildKit)."""
        print("Benchmarking: Cache mounts (BuildKit)")

        # Check if Dockerfile uses cache mounts
        content = self.dockerfile.read_text()
        if '--mount=type=cache' not in content:
            print("  Skipped: Dockerfile does not use cache mounts")
            return

        # First build to populate cache
        self._build_image(f"{self.image_name}:cache-mount-warm", use_buildkit=True, quiet=True)

        # Timed build with cache mounts
        result = self._build_image(
            f"{self.image_name}:cache-mount",
            use_cache=False,
            use_buildkit=True
        )
        result.name = "Cache mounts"
        result.cache_used = True
        self.results.builds.append(result)

        self._print_result(result)

    def _build_image(
        self,
        tag: str,
        use_cache: bool = True,
        use_buildkit: bool = True,
        quiet: bool = False
    ) -> BuildResult:
        """Build Docker image and measure time."""
        cmd = ['docker', 'build']

        if not use_cache:
            cmd.append('--no-cache')

        cmd.extend(['-t', tag, '-f', str(self.dockerfile)])

        if quiet:
            cmd.append('--quiet')

        cmd.append(str(self.context))

        env = None
        if use_buildkit:
            env = {'DOCKER_BUILDKIT': '1'}

        start_time = time.time()

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                env=env,
                timeout=600  # 10 minute timeout
            )

            duration = time.time() - start_time

            if result.returncode == 0:
                # Get image size
                size = self._get_image_size(tag)
                return BuildResult(
                    name=tag,
                    duration=duration,
                    image_size=size,
                    success=True
                )
            else:
                return BuildResult(
                    name=tag,
                    duration=duration,
                    image_size=0,
                    success=False,
                    error=result.stderr
                )

        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            return BuildResult(
                name=tag,
                duration=duration,
                image_size=0,
                success=False,
                error="Build timeout (>10 minutes)"
            )
        except Exception as e:
            duration = time.time() - start_time
            return BuildResult(
                name=tag,
                duration=duration,
                image_size=0,
                success=False,
                error=str(e)
            )

    def _get_image_size(self, tag: str) -> int:
        """Get image size in bytes."""
        try:
            result = subprocess.run(
                ['docker', 'image', 'inspect', tag, '--format={{.Size}}'],
                capture_output=True,
                text=True,
                check=True
            )
            return int(result.stdout.strip())
        except:
            return 0

    def _print_result(self, result: BuildResult) -> None:
        """Print single benchmark result."""
        if result.success:
            size_mb = result.image_size / (1024 * 1024)
            print(f"  ✓ {result.name}: {result.duration:.2f}s (size: {size_mb:.2f}MB)")
        else:
            print(f"  ✗ {result.name}: Failed after {result.duration:.2f}s")
            if result.error:
                print(f"    Error: {result.error[:100]}")
        print()

    def cleanup(self) -> None:
        """Remove benchmark images."""
        print("Cleaning up benchmark images...")
        for build in self.results.builds:
            if build.success:
                try:
                    subprocess.run(
                        ['docker', 'rmi', '-f', f"{self.image_name}:{build.name}"],
                        capture_output=True,
                        check=False
                    )
                except:
                    pass


def format_text_output(results: BenchmarkResults) -> str:
    """Format results as human-readable text."""
    lines = []
    lines.append("\n" + "=" * 80)
    lines.append(f"Docker Build Benchmark Results: {results.dockerfile}")
    lines.append("=" * 80)

    if not results.builds:
        lines.append("\nNo builds completed")
        return "\n".join(lines)

    # Summary table
    lines.append("\nBuild Strategy Comparison:")
    lines.append("-" * 80)
    lines.append(f"{'Strategy':<25} {'Time':<15} {'Size':<15} {'Status'}")
    lines.append("-" * 80)

    for build in results.builds:
        status = "✓ Success" if build.success else "✗ Failed"
        size_mb = build.image_size / (1024 * 1024) if build.success else 0
        cache_note = " (cached)" if build.cache_used else ""

        lines.append(
            f"{build.name:<25} {build.duration:>6.2f}s{cache_note:<8} "
            f"{size_mb:>6.2f}MB       {status}"
        )

    # Find fastest and slowest
    successful = [b for b in results.builds if b.success]
    if len(successful) >= 2:
        fastest = min(successful, key=lambda x: x.duration)
        slowest = max(successful, key=lambda x: x.duration)
        speedup = slowest.duration / fastest.duration

        lines.append("-" * 80)
        lines.append(f"Fastest: {fastest.name} ({fastest.duration:.2f}s)")
        lines.append(f"Slowest: {slowest.name} ({slowest.duration:.2f}s)")
        lines.append(f"Speedup: {speedup:.2f}x")

    # Recommendations
    lines.append("\nRecommendations:")

    if any(b.name == "BuildKit" and b.success for b in successful):
        buildkit = next(b for b in successful if b.name == "BuildKit")
        legacy = next((b for b in successful if b.name == "Legacy builder"), None)
        if legacy and buildkit.duration < legacy.duration:
            improvement = ((legacy.duration - buildkit.duration) / legacy.duration) * 100
            lines.append(f"  • Use BuildKit: {improvement:.1f}% faster than legacy builder")

    if any(b.cache_used and b.success for b in results.builds):
        lines.append("  • Leverage layer caching for faster rebuilds")

    if any(b.name == "Parallel stages" and b.success for b in results.builds):
        lines.append("  • Multi-stage builds enable parallel execution with BuildKit")

    if any(b.name == "Cache mounts" and b.success for b in results.builds):
        lines.append("  • Use cache mounts (--mount=type=cache) for package managers")

    lines.append("\n")
    return "\n".join(lines)


def format_json_output(results: BenchmarkResults) -> str:
    """Format results as JSON."""
    data = {
        'dockerfile': results.dockerfile,
        'timestamp': results.timestamp,
        'builds': [
            {
                'name': build.name,
                'duration': build.duration,
                'image_size': build.image_size,
                'success': build.success,
                'error': build.error,
                'cache_used': build.cache_used
            }
            for build in results.builds
        ]
    }

    # Add summary
    successful = [b for b in results.builds if b.success]
    if successful:
        fastest = min(successful, key=lambda x: x.duration)
        slowest = max(successful, key=lambda x: x.duration)

        data['summary'] = {
            'total_builds': len(results.builds),
            'successful': len(successful),
            'failed': len(results.builds) - len(successful),
            'fastest': {
                'name': fastest.name,
                'duration': fastest.duration
            },
            'slowest': {
                'name': slowest.name,
                'duration': slowest.duration
            }
        }

    return json.dumps(data, indent=2)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Benchmark Docker build times with different strategies'
    )
    parser.add_argument(
        'image',
        help='Base image name for benchmarks (e.g., myapp)'
    )
    parser.add_argument(
        '-f', '--dockerfile',
        default='Dockerfile',
        help='Path to Dockerfile (default: ./Dockerfile)'
    )
    parser.add_argument(
        '-c', '--context',
        help='Build context directory (default: Dockerfile directory)'
    )
    parser.add_argument(
        '-s', '--strategy',
        action='append',
        choices=['cached', 'no-cache', 'buildkit', 'legacy', 'parallel', 'cache-mount'],
        help='Strategies to benchmark (can be specified multiple times)'
    )
    parser.add_argument(
        '--all',
        action='store_true',
        help='Run all benchmark strategies'
    )
    parser.add_argument(
        '--json',
        action='store_true',
        help='Output in JSON format'
    )
    parser.add_argument(
        '--cleanup',
        action='store_true',
        help='Remove benchmark images after completion'
    )

    args = parser.parse_args()

    # Validate Dockerfile
    dockerfile = Path(args.dockerfile)
    if not dockerfile.exists():
        print(f"Error: Dockerfile not found: {dockerfile}", file=sys.stderr)
        sys.exit(1)

    # Determine context
    context = Path(args.context) if args.context else dockerfile.parent

    # Determine strategies
    if args.all:
        strategies = ['cached', 'no-cache', 'buildkit', 'legacy', 'parallel', 'cache-mount']
    elif args.strategy:
        strategies = args.strategy
    else:
        # Default strategies
        strategies = ['cached', 'no-cache', 'buildkit']

    # Run benchmarks
    benchmark = DockerBuildBenchmark(dockerfile, args.image, context)

    try:
        results = benchmark.run_benchmarks(strategies)

        # Output results
        if args.json:
            print(format_json_output(results))
        else:
            print(format_text_output(results))

        # Cleanup if requested
        if args.cleanup:
            benchmark.cleanup()

    except KeyboardInterrupt:
        print("\nBenchmark interrupted", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"Error running benchmarks: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
