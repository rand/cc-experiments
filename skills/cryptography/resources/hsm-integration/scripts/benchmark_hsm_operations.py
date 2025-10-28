#!/usr/bin/env python3
"""
HSM Performance Benchmark Tool

Benchmark cryptographic operations, measure throughput and latency,
test concurrent operations, compare vendors, and perform detailed analysis.

Supports: SoftHSM, Thales Luna, AWS CloudHSM, YubiHSM
"""

import argparse
import concurrent.futures
import getpass
import json
import statistics
import sys
import threading
import time
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

try:
    import PyKCS11
    from PyKCS11 import PyKCS11Error
    PKCS11_AVAILABLE = True
except ImportError:
    PKCS11_AVAILABLE = False
    print("Error: PyKCS11 not available. Install with: pip install PyKCS11", file=sys.stderr)
    sys.exit(1)


class BenchmarkType(Enum):
    """Benchmark operation types."""
    RSA_SIGN = "rsa-sign"
    RSA_VERIFY = "rsa-verify"
    RSA_ENCRYPT = "rsa-encrypt"
    RSA_DECRYPT = "rsa-decrypt"
    ECDSA_SIGN = "ecdsa-sign"
    ECDSA_VERIFY = "ecdsa-verify"
    AES_ENCRYPT = "aes-encrypt"
    AES_DECRYPT = "aes-decrypt"
    RANDOM = "random"
    KEY_GEN_RSA = "keygen-rsa"
    KEY_GEN_EC = "keygen-ec"
    KEY_GEN_AES = "keygen-aes"


@dataclass
class BenchmarkResult:
    """Single benchmark run result."""
    operation: str
    iterations: int
    total_time: float
    operations_per_second: float
    latency_ms: float
    latency_min_ms: float
    latency_max_ms: float
    latency_p50_ms: float
    latency_p95_ms: float
    latency_p99_ms: float
    latency_stddev_ms: float
    bytes_processed: Optional[int] = None
    throughput_mbps: Optional[float] = None
    errors: int = 0
    latencies: List[float] = field(default_factory=list, repr=False)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary without latencies list."""
        data = asdict(self)
        data.pop('latencies', None)
        return data


@dataclass
class ConcurrentBenchmarkResult:
    """Concurrent benchmark result."""
    operation: str
    workers: int
    total_operations: int
    total_time: float
    aggregate_ops_per_second: float
    per_worker_ops_per_second: float
    errors: int = 0
    worker_results: List[BenchmarkResult] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data['worker_results'] = [w.to_dict() for w in self.worker_results]
        return data


class HSMBenchmark:
    """HSM performance benchmark."""

    def __init__(
        self,
        library_path: str,
        slot: int,
        pin: Optional[str] = None,
        verbose: bool = False
    ):
        """Initialize benchmark."""
        self.library_path = library_path
        self.slot = slot
        self.pin = pin
        self.verbose = verbose
        self.pkcs11 = None

        # Thread-local storage for sessions
        self.thread_local = threading.local()

    def _get_session(self):
        """Get thread-local session."""
        if not hasattr(self.thread_local, 'session'):
            session = self.pkcs11.openSession(
                self.slot,
                PyKCS11.CKF_SERIAL_SESSION | PyKCS11.CKF_RW_SESSION
            )

            if self.pin:
                session.login(self.pin)

            self.thread_local.session = session

        return self.thread_local.session

    def _close_session(self):
        """Close thread-local session."""
        if hasattr(self.thread_local, 'session'):
            try:
                if self.pin:
                    self.thread_local.session.logout()
                self.thread_local.session.closeSession()
            except:
                pass
            delattr(self.thread_local, 'session')

    def connect(self):
        """Connect to HSM."""
        try:
            self.pkcs11 = PyKCS11.PyKCS11Lib()
            self.pkcs11.load(self.library_path)

            if self.verbose:
                info = self.pkcs11.getInfo()
                print(f"Connected to: {info.manufacturerID} v{info.libraryVersion}")

        except PyKCS11Error as e:
            raise Exception(f"Failed to connect to HSM: {e}")

    def disconnect(self):
        """Disconnect from HSM."""
        self._close_session()

    def benchmark_operation(
        self,
        operation_type: BenchmarkType,
        iterations: int = 1000,
        data_size: int = 1024,
        key_size: int = 2048,
        warmup: int = 10
    ) -> BenchmarkResult:
        """Benchmark a specific operation."""
        if self.verbose:
            print(f"Benchmarking {operation_type.value} ({iterations} iterations)...")

        # Setup
        setup_data = self._setup_benchmark(operation_type, data_size, key_size)

        # Warmup
        if warmup > 0:
            for _ in range(warmup):
                try:
                    self._execute_operation(operation_type, setup_data)
                except:
                    pass

        # Run benchmark
        latencies = []
        errors = 0
        bytes_processed = 0

        start_time = time.perf_counter()

        for i in range(iterations):
            op_start = time.perf_counter()
            try:
                result = self._execute_operation(operation_type, setup_data)
                op_end = time.perf_counter()
                latencies.append((op_end - op_start) * 1000)  # Convert to ms

                if result:
                    bytes_processed += len(result)

            except Exception as e:
                errors += 1
                if self.verbose:
                    print(f"Error in iteration {i}: {e}")

        end_time = time.perf_counter()
        total_time = end_time - start_time

        # Calculate statistics
        ops_per_second = iterations / total_time if total_time > 0 else 0
        avg_latency = statistics.mean(latencies) if latencies else 0

        result = BenchmarkResult(
            operation=operation_type.value,
            iterations=iterations,
            total_time=total_time,
            operations_per_second=ops_per_second,
            latency_ms=avg_latency,
            latency_min_ms=min(latencies) if latencies else 0,
            latency_max_ms=max(latencies) if latencies else 0,
            latency_p50_ms=statistics.median(latencies) if latencies else 0,
            latency_p95_ms=self._percentile(latencies, 95) if latencies else 0,
            latency_p99_ms=self._percentile(latencies, 99) if latencies else 0,
            latency_stddev_ms=statistics.stdev(latencies) if len(latencies) > 1 else 0,
            bytes_processed=bytes_processed if bytes_processed > 0 else None,
            throughput_mbps=(bytes_processed / total_time / 1024 / 1024) if bytes_processed > 0 and total_time > 0 else None,
            errors=errors,
            latencies=latencies
        )

        # Cleanup
        self._cleanup_benchmark(operation_type, setup_data)

        return result

    def benchmark_concurrent(
        self,
        operation_type: BenchmarkType,
        workers: int = 4,
        iterations_per_worker: int = 250,
        data_size: int = 1024,
        key_size: int = 2048
    ) -> ConcurrentBenchmarkResult:
        """Benchmark concurrent operations."""
        if self.verbose:
            print(f"Benchmarking {operation_type.value} with {workers} workers...")

        start_time = time.perf_counter()

        # Run workers in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [
                executor.submit(
                    self._worker_benchmark,
                    operation_type,
                    iterations_per_worker,
                    data_size,
                    key_size
                )
                for _ in range(workers)
            ]

            worker_results = [f.result() for f in concurrent.futures.as_completed(futures)]

        end_time = time.perf_counter()
        total_time = end_time - start_time

        # Aggregate results
        total_operations = sum(r.iterations for r in worker_results)
        total_errors = sum(r.errors for r in worker_results)
        aggregate_ops_per_second = total_operations / total_time if total_time > 0 else 0
        per_worker_ops_per_second = aggregate_ops_per_second / workers

        return ConcurrentBenchmarkResult(
            operation=operation_type.value,
            workers=workers,
            total_operations=total_operations,
            total_time=total_time,
            aggregate_ops_per_second=aggregate_ops_per_second,
            per_worker_ops_per_second=per_worker_ops_per_second,
            errors=total_errors,
            worker_results=worker_results
        )

    def _worker_benchmark(
        self,
        operation_type: BenchmarkType,
        iterations: int,
        data_size: int,
        key_size: int
    ) -> BenchmarkResult:
        """Worker function for concurrent benchmark."""
        return self.benchmark_operation(
            operation_type,
            iterations=iterations,
            data_size=data_size,
            key_size=key_size,
            warmup=5  # Reduced warmup for workers
        )

    def _setup_benchmark(
        self,
        operation_type: BenchmarkType,
        data_size: int,
        key_size: int
    ) -> Dict[str, Any]:
        """Setup benchmark environment."""
        session = self._get_session()
        setup_data = {}

        # Generate test data
        test_data = bytes([i % 256 for i in range(data_size)])
        setup_data['data'] = test_data

        # Generate keys based on operation type
        if operation_type in [BenchmarkType.RSA_SIGN, BenchmarkType.RSA_VERIFY,
                               BenchmarkType.RSA_ENCRYPT, BenchmarkType.RSA_DECRYPT]:
            keys = self._generate_rsa_keypair(session, key_size)
            setup_data['public_key'] = keys[0]
            setup_data['private_key'] = keys[1]

            # Pre-generate signature for verify operations
            if operation_type == BenchmarkType.RSA_VERIFY:
                mechanism = PyKCS11.Mechanism(PyKCS11.CKM_SHA256_RSA_PKCS, None)
                signature = session.sign(keys[1], test_data, mechanism)
                setup_data['signature'] = bytes(signature)

            # Pre-encrypt for decrypt operations
            if operation_type == BenchmarkType.RSA_DECRYPT:
                mechanism = PyKCS11.Mechanism(PyKCS11.CKM_RSA_PKCS, None)
                ciphertext = session.encrypt(keys[0], test_data[:100], mechanism)  # RSA has size limits
                setup_data['ciphertext'] = bytes(ciphertext)

        elif operation_type in [BenchmarkType.ECDSA_SIGN, BenchmarkType.ECDSA_VERIFY]:
            keys = self._generate_ec_keypair(session)
            setup_data['public_key'] = keys[0]
            setup_data['private_key'] = keys[1]

            # Pre-generate signature for verify
            if operation_type == BenchmarkType.ECDSA_VERIFY:
                mechanism = PyKCS11.Mechanism(PyKCS11.CKM_ECDSA_SHA256, None)
                signature = session.sign(keys[1], test_data, mechanism)
                setup_data['signature'] = bytes(signature)

        elif operation_type in [BenchmarkType.AES_ENCRYPT, BenchmarkType.AES_DECRYPT]:
            key = self._generate_aes_key(session, 32)  # AES-256
            setup_data['key'] = key

            # Generate IV
            setup_data['iv'] = bytes([0] * 16)

            # Pre-encrypt for decrypt
            if operation_type == BenchmarkType.AES_DECRYPT:
                mechanism = PyKCS11.Mechanism(PyKCS11.CKM_AES_CBC_PAD, setup_data['iv'])
                ciphertext = session.encrypt(key, test_data, mechanism)
                setup_data['ciphertext'] = bytes(ciphertext)

        return setup_data

    def _execute_operation(
        self,
        operation_type: BenchmarkType,
        setup_data: Dict[str, Any]
    ) -> Optional[bytes]:
        """Execute single operation."""
        session = self._get_session()

        if operation_type == BenchmarkType.RSA_SIGN:
            mechanism = PyKCS11.Mechanism(PyKCS11.CKM_SHA256_RSA_PKCS, None)
            result = session.sign(setup_data['private_key'], setup_data['data'], mechanism)
            return bytes(result)

        elif operation_type == BenchmarkType.RSA_VERIFY:
            mechanism = PyKCS11.Mechanism(PyKCS11.CKM_SHA256_RSA_PKCS, None)
            session.verify(setup_data['public_key'], setup_data['data'], setup_data['signature'], mechanism)
            return None

        elif operation_type == BenchmarkType.RSA_ENCRYPT:
            mechanism = PyKCS11.Mechanism(PyKCS11.CKM_RSA_PKCS, None)
            result = session.encrypt(setup_data['public_key'], setup_data['data'][:100], mechanism)
            return bytes(result)

        elif operation_type == BenchmarkType.RSA_DECRYPT:
            mechanism = PyKCS11.Mechanism(PyKCS11.CKM_RSA_PKCS, None)
            result = session.decrypt(setup_data['private_key'], setup_data['ciphertext'], mechanism)
            return bytes(result)

        elif operation_type == BenchmarkType.ECDSA_SIGN:
            mechanism = PyKCS11.Mechanism(PyKCS11.CKM_ECDSA_SHA256, None)
            result = session.sign(setup_data['private_key'], setup_data['data'], mechanism)
            return bytes(result)

        elif operation_type == BenchmarkType.ECDSA_VERIFY:
            mechanism = PyKCS11.Mechanism(PyKCS11.CKM_ECDSA_SHA256, None)
            session.verify(setup_data['public_key'], setup_data['data'], setup_data['signature'], mechanism)
            return None

        elif operation_type == BenchmarkType.AES_ENCRYPT:
            mechanism = PyKCS11.Mechanism(PyKCS11.CKM_AES_CBC_PAD, setup_data['iv'])
            result = session.encrypt(setup_data['key'], setup_data['data'], mechanism)
            return bytes(result)

        elif operation_type == BenchmarkType.AES_DECRYPT:
            mechanism = PyKCS11.Mechanism(PyKCS11.CKM_AES_CBC_PAD, setup_data['iv'])
            result = session.decrypt(setup_data['key'], setup_data['ciphertext'], mechanism)
            return bytes(result)

        elif operation_type == BenchmarkType.RANDOM:
            result = session.generateRandom(1024)
            return bytes(result)

        elif operation_type == BenchmarkType.KEY_GEN_RSA:
            keys = self._generate_rsa_keypair(session, 2048)
            session.destroyObject(keys[0])
            session.destroyObject(keys[1])
            return None

        elif operation_type == BenchmarkType.KEY_GEN_EC:
            keys = self._generate_ec_keypair(session)
            session.destroyObject(keys[0])
            session.destroyObject(keys[1])
            return None

        elif operation_type == BenchmarkType.KEY_GEN_AES:
            key = self._generate_aes_key(session, 32)
            session.destroyObject(key)
            return None

        return None

    def _cleanup_benchmark(self, operation_type: BenchmarkType, setup_data: Dict[str, Any]):
        """Cleanup benchmark environment."""
        session = self._get_session()

        # Delete generated keys
        try:
            if 'public_key' in setup_data:
                session.destroyObject(setup_data['public_key'])
            if 'private_key' in setup_data:
                session.destroyObject(setup_data['private_key'])
            if 'key' in setup_data:
                session.destroyObject(setup_data['key'])
        except:
            pass

    def _generate_rsa_keypair(self, session, modulus_bits: int = 2048) -> Tuple[int, int]:
        """Generate RSA key pair."""
        public_template = [
            (PyKCS11.CKA_CLASS, PyKCS11.CKO_PUBLIC_KEY),
            (PyKCS11.CKA_KEY_TYPE, PyKCS11.CKK_RSA),
            (PyKCS11.CKA_ENCRYPT, True),
            (PyKCS11.CKA_VERIFY, True),
            (PyKCS11.CKA_WRAP, True),
            (PyKCS11.CKA_MODULUS_BITS, modulus_bits),
            (PyKCS11.CKA_PUBLIC_EXPONENT, (0x01, 0x00, 0x01)),
        ]

        private_template = [
            (PyKCS11.CKA_CLASS, PyKCS11.CKO_PRIVATE_KEY),
            (PyKCS11.CKA_KEY_TYPE, PyKCS11.CKK_RSA),
            (PyKCS11.CKA_DECRYPT, True),
            (PyKCS11.CKA_SIGN, True),
            (PyKCS11.CKA_UNWRAP, True),
            (PyKCS11.CKA_SENSITIVE, True),
            (PyKCS11.CKA_EXTRACTABLE, False),
        ]

        return session.generateKeyPair(
            public_template,
            private_template,
            mecha=PyKCS11.MechanismRSAPKCSKeyPairGen
        )

    def _generate_ec_keypair(self, session) -> Tuple[int, int]:
        """Generate EC key pair (P-256)."""
        # P-256 curve OID
        curve_oid = bytes([0x06, 0x08, 0x2a, 0x86, 0x48, 0xce, 0x3d, 0x03, 0x01, 0x07])

        public_template = [
            (PyKCS11.CKA_CLASS, PyKCS11.CKO_PUBLIC_KEY),
            (PyKCS11.CKA_KEY_TYPE, PyKCS11.CKK_EC),
            (PyKCS11.CKA_VERIFY, True),
            (PyKCS11.CKA_EC_PARAMS, curve_oid),
        ]

        private_template = [
            (PyKCS11.CKA_CLASS, PyKCS11.CKO_PRIVATE_KEY),
            (PyKCS11.CKA_KEY_TYPE, PyKCS11.CKK_EC),
            (PyKCS11.CKA_SIGN, True),
            (PyKCS11.CKA_SENSITIVE, True),
            (PyKCS11.CKA_EXTRACTABLE, False),
        ]

        return session.generateKeyPair(
            public_template,
            private_template,
            mecha=PyKCS11.MechanismECKeyPairGen
        )

    def _generate_aes_key(self, session, key_size: int = 32) -> int:
        """Generate AES key."""
        template = [
            (PyKCS11.CKA_CLASS, PyKCS11.CKO_SECRET_KEY),
            (PyKCS11.CKA_KEY_TYPE, PyKCS11.CKK_AES),
            (PyKCS11.CKA_ENCRYPT, True),
            (PyKCS11.CKA_DECRYPT, True),
            (PyKCS11.CKA_SENSITIVE, True),
            (PyKCS11.CKA_EXTRACTABLE, False),
            (PyKCS11.CKA_VALUE_LEN, key_size),
        ]

        return session.generateKey(template, mecha=PyKCS11.MechanismAESKeyGen)

    @staticmethod
    def _percentile(data: List[float], percentile: int) -> float:
        """Calculate percentile."""
        if not data:
            return 0.0

        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile / 100.0)
        return sorted_data[min(index, len(sorted_data) - 1)]


def format_result_text(result: BenchmarkResult) -> str:
    """Format benchmark result as text."""
    lines = []
    lines.append(f"Operation: {result.operation}")
    lines.append(f"Iterations: {result.iterations}")
    lines.append(f"Total Time: {result.total_time:.3f}s")
    lines.append(f"Operations/sec: {result.operations_per_second:.2f}")
    lines.append(f"")
    lines.append(f"Latency:")
    lines.append(f"  Mean: {result.latency_ms:.3f}ms")
    lines.append(f"  Min: {result.latency_min_ms:.3f}ms")
    lines.append(f"  Max: {result.latency_max_ms:.3f}ms")
    lines.append(f"  P50: {result.latency_p50_ms:.3f}ms")
    lines.append(f"  P95: {result.latency_p95_ms:.3f}ms")
    lines.append(f"  P99: {result.latency_p99_ms:.3f}ms")
    lines.append(f"  StdDev: {result.latency_stddev_ms:.3f}ms")

    if result.throughput_mbps:
        lines.append(f"")
        lines.append(f"Throughput: {result.throughput_mbps:.2f} MB/s")

    if result.errors > 0:
        lines.append(f"")
        lines.append(f"Errors: {result.errors}")

    return "\n".join(lines)


def format_concurrent_result_text(result: ConcurrentBenchmarkResult) -> str:
    """Format concurrent benchmark result as text."""
    lines = []
    lines.append(f"Concurrent Benchmark: {result.operation}")
    lines.append(f"Workers: {result.workers}")
    lines.append(f"Total Operations: {result.total_operations}")
    lines.append(f"Total Time: {result.total_time:.3f}s")
    lines.append(f"Aggregate Ops/sec: {result.aggregate_ops_per_second:.2f}")
    lines.append(f"Per-Worker Ops/sec: {result.per_worker_ops_per_second:.2f}")

    if result.errors > 0:
        lines.append(f"Errors: {result.errors}")

    lines.append("")
    lines.append("Worker Results:")

    for i, worker in enumerate(result.worker_results, 1):
        lines.append(f"  Worker {i}:")
        lines.append(f"    Ops/sec: {worker.operations_per_second:.2f}")
        lines.append(f"    Latency (mean): {worker.latency_ms:.3f}ms")

    return "\n".join(lines)


def format_comparison_table(results: List[BenchmarkResult]) -> str:
    """Format multiple results as comparison table."""
    lines = []
    lines.append(f"{'Operation':<20} {'Ops/sec':<12} {'Latency (ms)':<15} {'P95 (ms)':<12} {'P99 (ms)':<12}")
    lines.append("-" * 80)

    for result in results:
        lines.append(
            f"{result.operation:<20} "
            f"{result.operations_per_second:>11.2f} "
            f"{result.latency_ms:>14.3f} "
            f"{result.latency_p95_ms:>11.3f} "
            f"{result.latency_p99_ms:>11.3f}"
        )

    return "\n".join(lines)


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="HSM performance benchmark tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Benchmark RSA-2048 signing
  %(prog)s --library /usr/lib/softhsm/libsofthsm2.so --slot 0 --pin 1234 \\
    --operation rsa-sign --iterations 1000

  # Benchmark multiple operations
  %(prog)s --library /usr/lib/softhsm/libsofthsm2.so --slot 0 --pin 1234 \\
    --operation rsa-sign --operation ecdsa-sign --operation aes-encrypt

  # Concurrent benchmark
  %(prog)s --library /usr/lib/softhsm/libsofthsm2.so --slot 0 --pin 1234 \\
    --operation rsa-sign --concurrent --workers 4

  # Full suite
  %(prog)s --library /usr/lib/softhsm/libsofthsm2.so --slot 0 --pin 1234 \\
    --suite all --json > results.json
        """
    )

    parser.add_argument(
        "--library",
        required=True,
        help="Path to PKCS#11 library"
    )

    parser.add_argument(
        "--slot",
        type=int,
        default=0,
        help="Slot number (default: 0)"
    )

    parser.add_argument(
        "--pin",
        help="User PIN (will prompt if not provided)"
    )

    parser.add_argument(
        "--operation",
        action="append",
        choices=[op.value for op in BenchmarkType],
        help="Operation to benchmark (can specify multiple)"
    )

    parser.add_argument(
        "--suite",
        choices=["all", "sign", "encrypt", "keygen"],
        help="Run predefined suite of benchmarks"
    )

    parser.add_argument(
        "--iterations",
        type=int,
        default=1000,
        help="Number of iterations per benchmark (default: 1000)"
    )

    parser.add_argument(
        "--data-size",
        type=int,
        default=1024,
        help="Data size in bytes (default: 1024)"
    )

    parser.add_argument(
        "--key-size",
        type=int,
        default=2048,
        help="RSA key size in bits (default: 2048)"
    )

    parser.add_argument(
        "--concurrent",
        action="store_true",
        help="Run concurrent benchmark"
    )

    parser.add_argument(
        "--workers",
        type=int,
        default=4,
        help="Number of concurrent workers (default: 4)"
    )

    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON"
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output"
    )

    args = parser.parse_args()

    # Determine operations to benchmark
    operations = []

    if args.suite:
        if args.suite == "all":
            operations = [
                BenchmarkType.RSA_SIGN,
                BenchmarkType.RSA_VERIFY,
                BenchmarkType.ECDSA_SIGN,
                BenchmarkType.ECDSA_VERIFY,
                BenchmarkType.AES_ENCRYPT,
                BenchmarkType.AES_DECRYPT,
                BenchmarkType.RANDOM,
            ]
        elif args.suite == "sign":
            operations = [
                BenchmarkType.RSA_SIGN,
                BenchmarkType.RSA_VERIFY,
                BenchmarkType.ECDSA_SIGN,
                BenchmarkType.ECDSA_VERIFY,
            ]
        elif args.suite == "encrypt":
            operations = [
                BenchmarkType.RSA_ENCRYPT,
                BenchmarkType.RSA_DECRYPT,
                BenchmarkType.AES_ENCRYPT,
                BenchmarkType.AES_DECRYPT,
            ]
        elif args.suite == "keygen":
            operations = [
                BenchmarkType.KEY_GEN_RSA,
                BenchmarkType.KEY_GEN_EC,
                BenchmarkType.KEY_GEN_AES,
            ]
    elif args.operation:
        operations = [BenchmarkType(op) for op in args.operation]
    else:
        parser.error("Must specify --operation or --suite")

    # Get PIN if not provided
    pin = args.pin
    if not pin:
        pin = getpass.getpass("Enter PIN: ")

    # Run benchmarks
    try:
        benchmark = HSMBenchmark(args.library, args.slot, pin, args.verbose)
        benchmark.connect()

        results = []

        for operation in operations:
            if args.concurrent:
                result = benchmark.benchmark_concurrent(
                    operation,
                    workers=args.workers,
                    iterations_per_worker=args.iterations // args.workers,
                    data_size=args.data_size,
                    key_size=args.key_size
                )

                if args.json:
                    results.append(result.to_dict())
                else:
                    print(format_concurrent_result_text(result))
                    print()
            else:
                result = benchmark.benchmark_operation(
                    operation,
                    iterations=args.iterations,
                    data_size=args.data_size,
                    key_size=args.key_size
                )

                results.append(result)

                if not args.json and args.verbose:
                    print(format_result_text(result))
                    print()

        benchmark.disconnect()

        # Output results
        if args.json:
            if args.concurrent:
                print(json.dumps(results, indent=2))
            else:
                print(json.dumps([r.to_dict() for r in results], indent=2))
        else:
            if not args.concurrent and len(results) > 1:
                print("\nComparison:")
                print(format_comparison_table(results))

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
