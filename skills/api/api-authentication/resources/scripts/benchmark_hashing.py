#!/usr/bin/env python3
"""
Password Hashing Algorithm Benchmark

Compare performance and security characteristics of bcrypt, Argon2, and scrypt
password hashing algorithms. Helps determine optimal parameters for your use case.

Usage:
    python benchmark_hashing.py --algorithm all --iterations 100
    python benchmark_hashing.py --algorithm argon2 --tune
    python benchmark_hashing.py --compare --json

Examples:
    # Benchmark all algorithms
    python benchmark_hashing.py --algorithm all --iterations 50

    # Tune Argon2 parameters for 250-500ms target
    python benchmark_hashing.py --algorithm argon2 --tune --target-ms 350

    # Compare with custom parameters
    python benchmark_hashing.py --compare --bcrypt-rounds 12 --argon2-time 3 --argon2-memory 65536
"""

import argparse
import sys
import json
import time
import statistics
from typing import Dict, Any, List, Tuple
from datetime import datetime

try:
    import bcrypt
    BCRYPT_AVAILABLE = True
except ImportError:
    BCRYPT_AVAILABLE = False
    print("Warning: bcrypt not available. Install with: pip install bcrypt", file=sys.stderr)

try:
    from argon2 import PasswordHasher
    from argon2.low_level import hash_secret_raw, Type
    ARGON2_AVAILABLE = True
except ImportError:
    ARGON2_AVAILABLE = False
    print("Warning: argon2-cffi not available. Install with: pip install argon2-cffi", file=sys.stderr)

try:
    import hashlib
    import os
    HASHLIB_AVAILABLE = True
except ImportError:
    HASHLIB_AVAILABLE = False


class HashingBenchmark:
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.results = {
            'timestamp': datetime.utcnow().isoformat(),
            'benchmarks': []
        }

    def log(self, message: str):
        """Log message if verbose"""
        if self.verbose:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")

    def benchmark_bcrypt(
        self,
        password: str,
        rounds: int = 12,
        iterations: int = 10
    ) -> Dict[str, Any]:
        """Benchmark bcrypt hashing"""
        if not BCRYPT_AVAILABLE:
            return {'error': 'bcrypt not available'}

        self.log(f"Benchmarking bcrypt (rounds={rounds}, iterations={iterations})...")

        times = []
        hash_result = None

        # Hash benchmarks
        for i in range(iterations):
            start = time.perf_counter()
            hash_result = bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=rounds))
            elapsed = (time.perf_counter() - start) * 1000  # ms
            times.append(elapsed)

            if self.verbose and i % max(1, iterations // 10) == 0:
                print(f"  Iteration {i+1}/{iterations}: {elapsed:.2f}ms")

        # Verify benchmark (single iteration)
        verify_times = []
        for _ in range(min(iterations, 10)):  # Verify is fast, do fewer iterations
            start = time.perf_counter()
            bcrypt.checkpw(password.encode(), hash_result)
            elapsed = (time.perf_counter() - start) * 1000
            verify_times.append(elapsed)

        result = {
            'algorithm': 'bcrypt',
            'parameters': {
                'rounds': rounds,
                'work_factor': 2 ** rounds
            },
            'hash_time_ms': {
                'mean': statistics.mean(times),
                'median': statistics.median(times),
                'stdev': statistics.stdev(times) if len(times) > 1 else 0,
                'min': min(times),
                'max': max(times)
            },
            'verify_time_ms': {
                'mean': statistics.mean(verify_times),
                'median': statistics.median(verify_times)
            },
            'iterations': iterations,
            'hash_size': len(hash_result)
        }

        self.log(f"  Mean hash time: {result['hash_time_ms']['mean']:.2f}ms")
        self.results['benchmarks'].append(result)

        return result

    def benchmark_argon2(
        self,
        password: str,
        time_cost: int = 3,
        memory_cost: int = 65536,
        parallelism: int = 4,
        iterations: int = 10
    ) -> Dict[str, Any]:
        """Benchmark Argon2 hashing"""
        if not ARGON2_AVAILABLE:
            return {'error': 'argon2 not available'}

        self.log(f"Benchmarking Argon2id (time={time_cost}, memory={memory_cost}KB, parallelism={parallelism})...")

        ph = PasswordHasher(
            time_cost=time_cost,
            memory_cost=memory_cost,
            parallelism=parallelism,
            hash_len=32,
            salt_len=16,
            type=Type.ID  # Argon2id
        )

        times = []
        hash_result = None

        # Hash benchmarks
        for i in range(iterations):
            start = time.perf_counter()
            hash_result = ph.hash(password)
            elapsed = (time.perf_counter() - start) * 1000  # ms
            times.append(elapsed)

            if self.verbose and i % max(1, iterations // 10) == 0:
                print(f"  Iteration {i+1}/{iterations}: {elapsed:.2f}ms")

        # Verify benchmark
        verify_times = []
        for _ in range(min(iterations, 10)):
            start = time.perf_counter()
            ph.verify(hash_result, password)
            elapsed = (time.perf_counter() - start) * 1000
            verify_times.append(elapsed)

        result = {
            'algorithm': 'argon2id',
            'parameters': {
                'time_cost': time_cost,
                'memory_cost_kb': memory_cost,
                'parallelism': parallelism,
                'hash_length': 32,
                'salt_length': 16
            },
            'hash_time_ms': {
                'mean': statistics.mean(times),
                'median': statistics.median(times),
                'stdev': statistics.stdev(times) if len(times) > 1 else 0,
                'min': min(times),
                'max': max(times)
            },
            'verify_time_ms': {
                'mean': statistics.mean(verify_times),
                'median': statistics.median(verify_times)
            },
            'iterations': iterations,
            'hash_size': len(hash_result)
        }

        self.log(f"  Mean hash time: {result['hash_time_ms']['mean']:.2f}ms")
        self.results['benchmarks'].append(result)

        return result

    def benchmark_scrypt(
        self,
        password: str,
        n: int = 2**14,  # CPU/memory cost (16384)
        r: int = 8,       # Block size
        p: int = 1,       # Parallelization
        iterations: int = 10
    ) -> Dict[str, Any]:
        """Benchmark scrypt hashing"""
        if not HASHLIB_AVAILABLE:
            return {'error': 'hashlib not available'}

        self.log(f"Benchmarking scrypt (N={n}, r={r}, p={p})...")

        times = []
        hash_result = None
        salt = os.urandom(16)

        # Hash benchmarks
        for i in range(iterations):
            start = time.perf_counter()
            hash_result = hashlib.scrypt(
                password.encode(),
                salt=salt,
                n=n,
                r=r,
                p=p,
                dklen=32
            )
            elapsed = (time.perf_counter() - start) * 1000  # ms
            times.append(elapsed)

            if self.verbose and i % max(1, iterations // 10) == 0:
                print(f"  Iteration {i+1}/{iterations}: {elapsed:.2f}ms")

        # Verify benchmark (just re-hash, scrypt doesn't have built-in verify)
        verify_times = []
        for _ in range(min(iterations, 10)):
            start = time.perf_counter()
            hashlib.scrypt(password.encode(), salt=salt, n=n, r=r, p=p, dklen=32)
            elapsed = (time.perf_counter() - start) * 1000
            verify_times.append(elapsed)

        result = {
            'algorithm': 'scrypt',
            'parameters': {
                'N': n,
                'r': r,
                'p': p,
                'dklen': 32,
                'memory_cost_kb': (128 * n * r * p) // 1024  # Approximate
            },
            'hash_time_ms': {
                'mean': statistics.mean(times),
                'median': statistics.median(times),
                'stdev': statistics.stdev(times) if len(times) > 1 else 0,
                'min': min(times),
                'max': max(times)
            },
            'verify_time_ms': {
                'mean': statistics.mean(verify_times),
                'median': statistics.median(verify_times)
            },
            'iterations': iterations,
            'hash_size': len(hash_result) if hash_result else 0
        }

        self.log(f"  Mean hash time: {result['hash_time_ms']['mean']:.2f}ms")
        self.results['benchmarks'].append(result)

        return result

    def tune_argon2(
        self,
        password: str,
        target_ms: float = 350,
        tolerance_ms: float = 100,
        max_attempts: int = 20
    ) -> Dict[str, Any]:
        """Auto-tune Argon2 parameters to hit target time"""
        if not ARGON2_AVAILABLE:
            return {'error': 'argon2 not available'}

        self.log(f"Tuning Argon2 for target: {target_ms}ms (±{tolerance_ms}ms)...")

        # Starting parameters
        time_cost = 2
        memory_cost = 65536  # 64MB
        parallelism = 4

        best_params = None
        best_time = None

        for attempt in range(max_attempts):
            self.log(f"  Attempt {attempt+1}: time={time_cost}, memory={memory_cost}KB, parallelism={parallelism}")

            # Quick benchmark (3 iterations)
            result = self.benchmark_argon2(
                password,
                time_cost,
                memory_cost,
                parallelism,
                iterations=3
            )

            mean_time = result['hash_time_ms']['mean']
            self.log(f"    Result: {mean_time:.2f}ms")

            # Check if within target range
            if target_ms - tolerance_ms <= mean_time <= target_ms + tolerance_ms:
                best_params = result['parameters']
                best_time = mean_time
                self.log(f"  ✓ Found optimal parameters!")
                break

            # Adjust parameters
            if mean_time < target_ms - tolerance_ms:
                # Too fast, increase difficulty
                if time_cost < 10:
                    time_cost += 1
                else:
                    memory_cost = int(memory_cost * 1.5)
            else:
                # Too slow, decrease difficulty
                if time_cost > 1:
                    time_cost -= 1
                else:
                    memory_cost = int(memory_cost * 0.75)

            best_params = result['parameters']
            best_time = mean_time

        return {
            'target_ms': target_ms,
            'achieved_ms': best_time,
            'parameters': best_params,
            'attempts': attempt + 1
        }

    def compare_algorithms(
        self,
        password: str,
        bcrypt_rounds: int = 12,
        argon2_time: int = 3,
        argon2_memory: int = 65536,
        scrypt_n: int = 2**14,
        iterations: int = 10
    ) -> Dict[str, Any]:
        """Compare all algorithms side-by-side"""
        self.log("Comparing password hashing algorithms...")

        comparison = {
            'password_length': len(password),
            'iterations': iterations,
            'results': []
        }

        # Benchmark bcrypt
        if BCRYPT_AVAILABLE:
            bcrypt_result = self.benchmark_bcrypt(password, bcrypt_rounds, iterations)
            comparison['results'].append(bcrypt_result)

        # Benchmark Argon2
        if ARGON2_AVAILABLE:
            argon2_result = self.benchmark_argon2(
                password,
                argon2_time,
                argon2_memory,
                4,
                iterations
            )
            comparison['results'].append(argon2_result)

        # Benchmark scrypt
        if HASHLIB_AVAILABLE:
            scrypt_result = self.benchmark_scrypt(password, scrypt_n, 8, 1, iterations)
            comparison['results'].append(scrypt_result)

        # Determine winner (closest to 250-500ms target)
        target_ms = 350
        best_algorithm = None
        best_distance = float('inf')

        for result in comparison['results']:
            mean_time = result['hash_time_ms']['mean']
            distance = abs(mean_time - target_ms)

            if distance < best_distance:
                best_distance = distance
                best_algorithm = result['algorithm']

        comparison['recommendation'] = {
            'algorithm': best_algorithm,
            'reason': f'Closest to optimal 250-500ms range (target: {target_ms}ms)'
        }

        return comparison


def format_comparison_table(comparison: Dict[str, Any]) -> str:
    """Format comparison results as a table"""
    lines = []
    lines.append("\nPassword Hashing Algorithm Comparison")
    lines.append("=" * 80)

    # Header
    lines.append(f"{'Algorithm':<15} {'Hash Time':<15} {'Verify Time':<15} {'Memory':<15}")
    lines.append("-" * 80)

    # Results
    for result in comparison['results']:
        algo = result['algorithm']
        hash_time = f"{result['hash_time_ms']['mean']:.2f}ms"
        verify_time = f"{result['verify_time_ms']['mean']:.2f}ms"

        # Get memory usage
        if algo == 'bcrypt':
            memory = "~4KB"
        elif algo == 'argon2id':
            memory = f"{result['parameters']['memory_cost_kb']}KB"
        elif algo == 'scrypt':
            memory = f"{result['parameters']['memory_cost_kb']}KB"
        else:
            memory = "N/A"

        lines.append(f"{algo:<15} {hash_time:<15} {verify_time:<15} {memory:<15}")

    lines.append("=" * 80)

    # Recommendation
    if 'recommendation' in comparison:
        rec = comparison['recommendation']
        lines.append(f"\nRecommendation: {rec['algorithm']}")
        lines.append(f"Reason: {rec['reason']}")

    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(
        description='Password Hashing Algorithm Benchmark',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Benchmark all algorithms
  python benchmark_hashing.py --algorithm all --iterations 50

  # Tune Argon2 for 350ms target
  python benchmark_hashing.py --algorithm argon2 --tune --target-ms 350

  # Compare with custom parameters
  python benchmark_hashing.py --compare --bcrypt-rounds 14 --argon2-time 4

  # Quick test
  python benchmark_hashing.py --algorithm bcrypt --iterations 10 --password "test123"
        """
    )

    parser.add_argument('--algorithm', type=str,
                       choices=['bcrypt', 'argon2', 'scrypt', 'all'],
                       help='Algorithm to benchmark')
    parser.add_argument('--password', type=str, default='test_password_12345',
                       help='Password to hash (default: test_password_12345)')
    parser.add_argument('--iterations', type=int, default=10,
                       help='Number of iterations (default: 10)')

    # bcrypt options
    parser.add_argument('--bcrypt-rounds', type=int, default=12,
                       help='bcrypt rounds (default: 12)')

    # Argon2 options
    parser.add_argument('--argon2-time', type=int, default=3,
                       help='Argon2 time cost (default: 3)')
    parser.add_argument('--argon2-memory', type=int, default=65536,
                       help='Argon2 memory cost in KB (default: 65536)')
    parser.add_argument('--argon2-parallelism', type=int, default=4,
                       help='Argon2 parallelism (default: 4)')

    # scrypt options
    parser.add_argument('--scrypt-n', type=int, default=2**14,
                       help='scrypt N parameter (default: 16384)')
    parser.add_argument('--scrypt-r', type=int, default=8,
                       help='scrypt r parameter (default: 8)')
    parser.add_argument('--scrypt-p', type=int, default=1,
                       help='scrypt p parameter (default: 1)')

    # Operations
    parser.add_argument('--tune', action='store_true',
                       help='Auto-tune Argon2 parameters')
    parser.add_argument('--target-ms', type=float, default=350,
                       help='Target hashing time in ms for tuning (default: 350)')
    parser.add_argument('--compare', action='store_true',
                       help='Compare all algorithms')

    # Output
    parser.add_argument('--json', action='store_true',
                       help='Output results as JSON')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Verbose output')

    args = parser.parse_args()

    benchmark = HashingBenchmark(verbose=args.verbose)

    try:
        # Tune Argon2
        if args.tune:
            if args.algorithm and args.algorithm != 'argon2':
                print("Error: --tune only works with argon2", file=sys.stderr)
                sys.exit(1)

            result = benchmark.tune_argon2(args.password, args.target_ms)

            if args.json:
                print(json.dumps(result, indent=2))
            else:
                print(f"\nArgon2 Tuning Results:")
                print(f"Target: {result['target_ms']}ms")
                print(f"Achieved: {result['achieved_ms']:.2f}ms")
                print(f"Attempts: {result['attempts']}")
                print(f"\nOptimal Parameters:")
                for key, value in result['parameters'].items():
                    print(f"  {key}: {value}")

        # Compare all algorithms
        elif args.compare:
            comparison = benchmark.compare_algorithms(
                args.password,
                args.bcrypt_rounds,
                args.argon2_time,
                args.argon2_memory,
                args.scrypt_n,
                args.iterations
            )

            if args.json:
                print(json.dumps(comparison, indent=2))
            else:
                print(format_comparison_table(comparison))

        # Benchmark specific algorithm
        elif args.algorithm:
            if args.algorithm == 'bcrypt' or args.algorithm == 'all':
                benchmark.benchmark_bcrypt(
                    args.password,
                    args.bcrypt_rounds,
                    args.iterations
                )

            if args.algorithm == 'argon2' or args.algorithm == 'all':
                benchmark.benchmark_argon2(
                    args.password,
                    args.argon2_time,
                    args.argon2_memory,
                    args.argon2_parallelism,
                    args.iterations
                )

            if args.algorithm == 'scrypt' or args.algorithm == 'all':
                benchmark.benchmark_scrypt(
                    args.password,
                    args.scrypt_n,
                    args.scrypt_r,
                    args.scrypt_p,
                    args.iterations
                )

            if args.json:
                print(json.dumps(benchmark.results, indent=2))
            else:
                print(f"\nBenchmark Results:")
                for result in benchmark.results['benchmarks']:
                    print(f"\n{result['algorithm'].upper()}:")
                    print(f"  Mean hash time: {result['hash_time_ms']['mean']:.2f}ms")
                    print(f"  Median hash time: {result['hash_time_ms']['median']:.2f}ms")
                    print(f"  Std deviation: {result['hash_time_ms']['stdev']:.2f}ms")
                    print(f"  Mean verify time: {result['verify_time_ms']['mean']:.2f}ms")
                    print(f"  Parameters: {result['parameters']}")

        else:
            parser.print_help()
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n\nBenchmark interrupted by user", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        if args.json:
            print(json.dumps({'error': str(e)}, indent=2), file=sys.stderr)
        else:
            print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
