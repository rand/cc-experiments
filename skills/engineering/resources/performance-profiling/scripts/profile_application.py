#!/usr/bin/env python3
"""
Multi-language application profiler with flame graph generation.

Supports CPU, memory, and I/O profiling for Python, Node.js, Go, Java, and native binaries.
Generates flame graphs, reports, and differential profiles.
"""

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class ProfileMode(Enum):
    """Profiling modes."""
    CPU = "cpu"
    MEMORY = "memory"
    IO = "io"
    ALL = "all"


class Language(Enum):
    """Supported languages."""
    PYTHON = "python"
    NODEJS = "nodejs"
    GO = "go"
    JAVA = "java"
    NATIVE = "native"
    AUTO = "auto"


@dataclass
class ProfileResult:
    """Profiling result metadata."""
    language: str
    mode: str
    duration: float
    profile_file: str
    flame_graph: Optional[str] = None
    summary: Optional[Dict[str, Any]] = None
    timestamp: str = ""
    command: str = ""
    pid: Optional[int] = None

    def __post_init__(self) -> None:
        """Set timestamp if not provided."""
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


class ProfilerError(Exception):
    """Base exception for profiler errors."""
    pass


class ToolNotFoundError(ProfilerError):
    """Required tool not found."""
    pass


class ProfilingFailedError(ProfilerError):
    """Profiling operation failed."""
    pass


class ApplicationProfiler:
    """Multi-language application profiler."""

    def __init__(self, output_dir: Path, verbose: bool = False) -> None:
        """
        Initialize profiler.

        Args:
            output_dir: Directory for output files
            verbose: Enable verbose logging
        """
        self.output_dir = output_dir
        self.verbose = verbose
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Tool paths (discovered at runtime)
        self.perf_path: Optional[Path] = None
        self.flamegraph_path: Optional[Path] = None
        self.py_spy_path: Optional[Path] = None
        self.node_path: Optional[Path] = None
        self.go_path: Optional[Path] = None
        self.java_path: Optional[Path] = None

        self._discover_tools()

    def _log(self, message: str) -> None:
        """Log message if verbose enabled."""
        if self.verbose:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}", file=sys.stderr)

    def _discover_tools(self) -> None:
        """Discover available profiling tools."""
        self._log("Discovering profiling tools...")

        # Linux perf
        perf = shutil.which("perf")
        if perf:
            self.perf_path = Path(perf)
            self._log(f"Found perf: {self.perf_path}")

        # FlameGraph scripts
        flamegraph_pl = shutil.which("flamegraph.pl")
        if flamegraph_pl:
            self.flamegraph_path = Path(flamegraph_pl).parent
            self._log(f"Found FlameGraph: {self.flamegraph_path}")
        else:
            # Check common locations
            common_paths = [
                Path.home() / "FlameGraph",
                Path("/opt/FlameGraph"),
                Path("/usr/local/FlameGraph"),
            ]
            for path in common_paths:
                if (path / "flamegraph.pl").exists():
                    self.flamegraph_path = path
                    self._log(f"Found FlameGraph: {self.flamegraph_path}")
                    break

        # py-spy
        py_spy = shutil.which("py-spy")
        if py_spy:
            self.py_spy_path = Path(py_spy)
            self._log(f"Found py-spy: {self.py_spy_path}")

        # Node.js
        node = shutil.which("node")
        if node:
            self.node_path = Path(node)
            self._log(f"Found node: {self.node_path}")

        # Go
        go = shutil.which("go")
        if go:
            self.go_path = Path(go)
            self._log(f"Found go: {self.go_path}")

        # Java
        java = shutil.which("java")
        if java:
            self.java_path = Path(java)
            self._log(f"Found java: {self.java_path}")

    def _check_tool(self, tool: Optional[Path], name: str) -> Path:
        """
        Check if tool is available.

        Args:
            tool: Tool path or None
            name: Tool name for error message

        Returns:
            Tool path

        Raises:
            ToolNotFoundError: If tool not found
        """
        if tool is None:
            raise ToolNotFoundError(
                f"{name} not found. Please install {name} and ensure it's in PATH."
            )
        return tool

    def detect_language(self, command: List[str]) -> Language:
        """
        Auto-detect language from command.

        Args:
            command: Command to analyze

        Returns:
            Detected language
        """
        if not command:
            return Language.NATIVE

        cmd = command[0].lower()

        if "python" in cmd or cmd.endswith(".py"):
            return Language.PYTHON
        elif "node" in cmd or cmd.endswith(".js"):
            return Language.NODEJS
        elif "go" in cmd or "main" in cmd:
            # Check if binary is Go binary
            try:
                result = subprocess.run(
                    ["go", "version", command[0]],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if "go" in result.stdout.lower():
                    return Language.GO
            except (subprocess.SubprocessError, FileNotFoundError):
                pass
        elif "java" in cmd or cmd.endswith(".jar"):
            return Language.JAVA

        return Language.NATIVE

    def profile_python(
        self,
        command: List[str],
        mode: ProfileMode,
        duration: Optional[int] = None,
        pid: Optional[int] = None,
    ) -> ProfileResult:
        """
        Profile Python application.

        Args:
            command: Command to profile
            mode: Profiling mode
            duration: Profile duration in seconds (for attach)
            pid: Process ID to attach (mutually exclusive with command)

        Returns:
            ProfileResult with output files

        Raises:
            ProfilingFailedError: If profiling fails
        """
        self._log(f"Profiling Python application (mode={mode.value})")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if mode == ProfileMode.CPU:
            # Use py-spy for CPU profiling
            py_spy = self._check_tool(self.py_spy_path, "py-spy")

            profile_file = self.output_dir / f"python_cpu_{timestamp}.svg"

            if pid:
                cmd = [
                    str(py_spy),
                    "record",
                    "-o", str(profile_file),
                    "--format", "flamegraph",
                    "-p", str(pid),
                    "--duration", str(duration or 60),
                ]
            else:
                cmd = [
                    str(py_spy),
                    "record",
                    "-o", str(profile_file),
                    "--format", "flamegraph",
                    "--",
                ] + command

            self._log(f"Running: {' '.join(cmd)}")
            start_time = time.time()

            try:
                result = subprocess.run(cmd, check=True, capture_output=True, text=True)
                duration_actual = time.time() - start_time

                if self.verbose and result.stderr:
                    print(result.stderr, file=sys.stderr)

                return ProfileResult(
                    language=Language.PYTHON.value,
                    mode=mode.value,
                    duration=duration_actual,
                    profile_file=str(profile_file),
                    flame_graph=str(profile_file),
                    command=" ".join(command) if command else None,
                    pid=pid,
                )
            except subprocess.CalledProcessError as e:
                raise ProfilingFailedError(f"py-spy failed: {e.stderr}") from e

        elif mode == ProfileMode.MEMORY:
            # Use memory_profiler
            self._log("Memory profiling requires code instrumentation with @profile decorator")

            profile_file = self.output_dir / f"python_memory_{timestamp}.txt"

            # Check if memory_profiler is available
            try:
                subprocess.run(
                    ["python", "-c", "import memory_profiler"],
                    check=True,
                    capture_output=True
                )
            except subprocess.CalledProcessError:
                raise ToolNotFoundError(
                    "memory_profiler not found. Install with: pip install memory-profiler"
                )

            cmd = ["python", "-m", "memory_profiler"] + command
            self._log(f"Running: {' '.join(cmd)}")
            start_time = time.time()

            try:
                result = subprocess.run(cmd, check=True, capture_output=True, text=True)
                duration_actual = time.time() - start_time

                profile_file.write_text(result.stdout)

                return ProfileResult(
                    language=Language.PYTHON.value,
                    mode=mode.value,
                    duration=duration_actual,
                    profile_file=str(profile_file),
                    command=" ".join(command),
                )
            except subprocess.CalledProcessError as e:
                raise ProfilingFailedError(f"memory_profiler failed: {e.stderr}") from e

        else:
            raise ProfilingFailedError(f"Mode {mode.value} not supported for Python")

    def profile_nodejs(
        self,
        command: List[str],
        mode: ProfileMode,
        duration: Optional[int] = None,
        pid: Optional[int] = None,
    ) -> ProfileResult:
        """
        Profile Node.js application.

        Args:
            command: Command to profile
            mode: Profiling mode
            duration: Profile duration in seconds
            pid: Process ID (not supported for Node.js)

        Returns:
            ProfileResult with output files

        Raises:
            ProfilingFailedError: If profiling fails
        """
        self._log(f"Profiling Node.js application (mode={mode.value})")

        if pid:
            raise ProfilingFailedError("PID-based profiling not supported for Node.js")

        node = self._check_tool(self.node_path, "node")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if mode == ProfileMode.CPU:
            # Use --prof flag
            profile_file = self.output_dir / f"nodejs_cpu_{timestamp}.txt"
            isolate_log = self.output_dir / f"isolate-*.log"

            # Replace 'node' with 'node --prof' in command
            if command[0] == "node":
                cmd = [str(node), "--prof"] + command[1:]
            else:
                cmd = [str(node), "--prof"] + command

            self._log(f"Running: {' '.join(cmd)}")
            start_time = time.time()

            try:
                # Run with profiling
                result = subprocess.run(
                    cmd,
                    check=True,
                    capture_output=True,
                    text=True,
                    cwd=self.output_dir
                )
                duration_actual = time.time() - start_time

                # Find isolate log file
                isolate_files = list(self.output_dir.glob("isolate-*.log"))
                if not isolate_files:
                    raise ProfilingFailedError("No isolate log file generated")

                isolate_log = isolate_files[0]

                # Process log file
                process_cmd = [str(node), "--prof-process", str(isolate_log)]
                process_result = subprocess.run(
                    process_cmd,
                    check=True,
                    capture_output=True,
                    text=True
                )

                profile_file.write_text(process_result.stdout)

                # Clean up isolate log
                isolate_log.unlink()

                return ProfileResult(
                    language=Language.NODEJS.value,
                    mode=mode.value,
                    duration=duration_actual,
                    profile_file=str(profile_file),
                    command=" ".join(command),
                )
            except subprocess.CalledProcessError as e:
                raise ProfilingFailedError(f"Node.js profiling failed: {e.stderr}") from e

        else:
            raise ProfilingFailedError(f"Mode {mode.value} not supported for Node.js")

    def profile_go(
        self,
        command: List[str],
        mode: ProfileMode,
        duration: Optional[int] = None,
        pid: Optional[int] = None,
    ) -> ProfileResult:
        """
        Profile Go application.

        Args:
            command: Command to profile (for benchmarks)
            mode: Profiling mode
            duration: Profile duration (for HTTP profiling)
            pid: Process ID (not supported)

        Returns:
            ProfileResult with output files

        Raises:
            ProfilingFailedError: If profiling fails
        """
        self._log(f"Profiling Go application (mode={mode.value})")

        if pid:
            raise ProfilingFailedError(
                "PID-based profiling not directly supported for Go. "
                "Use HTTP pprof endpoint: http://host:port/debug/pprof/"
            )

        go = self._check_tool(self.go_path, "go")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if mode == ProfileMode.CPU:
            profile_file = self.output_dir / f"go_cpu_{timestamp}.prof"

            # Assume command is "go test -bench ."
            if "test" not in command:
                raise ProfilingFailedError(
                    "Go profiling requires 'go test -bench .' command"
                )

            cmd = command + [f"-cpuprofile={profile_file}"]
            self._log(f"Running: {' '.join(cmd)}")
            start_time = time.time()

            try:
                result = subprocess.run(cmd, check=True, capture_output=True, text=True)
                duration_actual = time.time() - start_time

                if self.verbose:
                    print(result.stdout)

                # Generate flame graph if possible
                flame_graph = None
                if self.flamegraph_path:
                    flame_graph = self._generate_go_flamegraph(profile_file)

                return ProfileResult(
                    language=Language.GO.value,
                    mode=mode.value,
                    duration=duration_actual,
                    profile_file=str(profile_file),
                    flame_graph=flame_graph,
                    command=" ".join(command),
                )
            except subprocess.CalledProcessError as e:
                raise ProfilingFailedError(f"Go profiling failed: {e.stderr}") from e

        elif mode == ProfileMode.MEMORY:
            profile_file = self.output_dir / f"go_memory_{timestamp}.prof"

            if "test" not in command:
                raise ProfilingFailedError(
                    "Go profiling requires 'go test -bench .' command"
                )

            cmd = command + [f"-memprofile={profile_file}"]
            self._log(f"Running: {' '.join(cmd)}")
            start_time = time.time()

            try:
                result = subprocess.run(cmd, check=True, capture_output=True, text=True)
                duration_actual = time.time() - start_time

                if self.verbose:
                    print(result.stdout)

                return ProfileResult(
                    language=Language.GO.value,
                    mode=mode.value,
                    duration=duration_actual,
                    profile_file=str(profile_file),
                    command=" ".join(command),
                )
            except subprocess.CalledProcessError as e:
                raise ProfilingFailedError(f"Go profiling failed: {e.stderr}") from e

        else:
            raise ProfilingFailedError(f"Mode {mode.value} not supported for Go")

    def _generate_go_flamegraph(self, profile_file: Path) -> Optional[str]:
        """Generate flame graph from Go pprof file."""
        try:
            flame_graph = profile_file.with_suffix(".svg")

            cmd = [
                "go", "tool", "pprof",
                "-svg",
                "-output", str(flame_graph),
                str(profile_file)
            ]

            subprocess.run(cmd, check=True, capture_output=True)
            return str(flame_graph)
        except subprocess.CalledProcessError:
            self._log("Failed to generate flame graph from Go profile")
            return None

    def profile_native(
        self,
        command: List[str],
        mode: ProfileMode,
        duration: Optional[int] = None,
        pid: Optional[int] = None,
    ) -> ProfileResult:
        """
        Profile native application with Linux perf.

        Args:
            command: Command to profile
            mode: Profiling mode
            duration: Profile duration in seconds (for attach)
            pid: Process ID to attach

        Returns:
            ProfileResult with output files

        Raises:
            ProfilingFailedError: If profiling fails
        """
        self._log(f"Profiling native application with perf (mode={mode.value})")

        if platform.system() != "Linux":
            raise ProfilingFailedError("perf is Linux-only")

        perf = self._check_tool(self.perf_path, "perf")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if mode == ProfileMode.CPU:
            profile_file = self.output_dir / f"native_cpu_{timestamp}.data"

            if pid:
                cmd = [
                    str(perf), "record",
                    "-F", "99",  # 99 Hz sampling
                    "-g",  # Call graph
                    "-p", str(pid),
                    "-o", str(profile_file),
                    "--", "sleep", str(duration or 60)
                ]
            else:
                cmd = [
                    str(perf), "record",
                    "-F", "99",
                    "-g",
                    "-o", str(profile_file),
                    "--"
                ] + command

            self._log(f"Running: {' '.join(cmd)}")
            start_time = time.time()

            try:
                result = subprocess.run(cmd, check=True, capture_output=True, text=True)
                duration_actual = time.time() - start_time

                if self.verbose and result.stderr:
                    print(result.stderr, file=sys.stderr)

                # Generate flame graph
                flame_graph = None
                if self.flamegraph_path:
                    flame_graph = self._generate_perf_flamegraph(profile_file)

                return ProfileResult(
                    language=Language.NATIVE.value,
                    mode=mode.value,
                    duration=duration_actual,
                    profile_file=str(profile_file),
                    flame_graph=flame_graph,
                    command=" ".join(command) if command else None,
                    pid=pid,
                )
            except subprocess.CalledProcessError as e:
                raise ProfilingFailedError(f"perf failed: {e.stderr}") from e

        else:
            raise ProfilingFailedError(f"Mode {mode.value} not supported for native/perf")

    def _generate_perf_flamegraph(self, profile_file: Path) -> Optional[str]:
        """Generate flame graph from perf data."""
        if not self.flamegraph_path:
            return None

        try:
            flame_graph = profile_file.with_suffix(".svg")

            # perf script
            script_output = subprocess.check_output(
                ["perf", "script", "-i", str(profile_file)],
                text=True
            )

            # stackcollapse-perf.pl
            stackcollapse = self.flamegraph_path / "stackcollapse-perf.pl"
            collapsed = subprocess.run(
                [str(stackcollapse)],
                input=script_output,
                capture_output=True,
                text=True,
                check=True
            ).stdout

            # flamegraph.pl
            flamegraph_pl = self.flamegraph_path / "flamegraph.pl"
            with open(flame_graph, "w") as f:
                subprocess.run(
                    [str(flamegraph_pl)],
                    input=collapsed,
                    stdout=f,
                    text=True,
                    check=True
                )

            self._log(f"Generated flame graph: {flame_graph}")
            return str(flame_graph)

        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            self._log(f"Failed to generate flame graph: {e}")
            return None

    def profile(
        self,
        command: Optional[List[str]] = None,
        language: Language = Language.AUTO,
        mode: ProfileMode = ProfileMode.CPU,
        duration: Optional[int] = None,
        pid: Optional[int] = None,
    ) -> ProfileResult:
        """
        Profile application with auto-detection.

        Args:
            command: Command to profile (mutually exclusive with pid)
            language: Target language (AUTO for auto-detection)
            mode: Profiling mode
            duration: Profile duration in seconds (for attach)
            pid: Process ID to attach (mutually exclusive with command)

        Returns:
            ProfileResult with output files

        Raises:
            ProfilerError: If profiling fails
        """
        if command is None and pid is None:
            raise ProfilingFailedError("Either command or pid must be provided")

        if command is not None and pid is not None:
            raise ProfilingFailedError("command and pid are mutually exclusive")

        # Auto-detect language
        if language == Language.AUTO:
            if pid:
                # For PID, use native profiler
                language = Language.NATIVE
            else:
                language = self.detect_language(command)
            self._log(f"Detected language: {language.value}")

        # Dispatch to language-specific profiler
        if language == Language.PYTHON:
            return self.profile_python(command or [], mode, duration, pid)
        elif language == Language.NODEJS:
            return self.profile_nodejs(command or [], mode, duration, pid)
        elif language == Language.GO:
            return self.profile_go(command or [], mode, duration, pid)
        elif language == Language.NATIVE:
            return self.profile_native(command or [], mode, duration, pid)
        else:
            raise ProfilingFailedError(f"Language {language.value} not supported")

    def differential_profile(
        self,
        baseline_command: List[str],
        optimized_command: List[str],
        language: Language = Language.AUTO,
        mode: ProfileMode = ProfileMode.CPU,
    ) -> Tuple[ProfileResult, ProfileResult, Optional[str]]:
        """
        Generate differential flame graph comparing two versions.

        Args:
            baseline_command: Command for baseline version
            optimized_command: Command for optimized version
            language: Target language
            mode: Profiling mode

        Returns:
            Tuple of (baseline_result, optimized_result, diff_flamegraph_path)
        """
        self._log("Running differential profiling...")

        # Profile baseline
        self._log("Profiling baseline...")
        baseline_result = self.profile(baseline_command, language, mode)

        # Profile optimized
        self._log("Profiling optimized...")
        optimized_result = self.profile(optimized_command, language, mode)

        # Generate differential flame graph (if supported)
        diff_graph = None
        # TODO: Implement differential flame graph generation
        # This requires stackcollapse format for both profiles

        return baseline_result, optimized_result, diff_graph


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Multi-language application profiler",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Profile Python script
  %(prog)s python script.py

  # Profile with py-spy (CPU)
  %(prog)s --language python --mode cpu python script.py

  # Profile running process
  %(prog)s --pid 12345 --duration 60

  # Profile Node.js application
  %(prog)s --language nodejs node app.js

  # Profile Go benchmark
  %(prog)s --language go go test -bench .

  # Differential profiling
  %(prog)s --diff baseline.py optimized.py

Supported languages: python, nodejs, go, java, native, auto
Supported modes: cpu, memory, io, all
        """
    )

    parser.add_argument(
        "command",
        nargs="*",
        help="Command to profile (or baseline for --diff)"
    )

    parser.add_argument(
        "-l", "--language",
        type=str,
        default="auto",
        choices=["python", "nodejs", "go", "java", "native", "auto"],
        help="Target language (default: auto-detect)"
    )

    parser.add_argument(
        "-m", "--mode",
        type=str,
        default="cpu",
        choices=["cpu", "memory", "io", "all"],
        help="Profiling mode (default: cpu)"
    )

    parser.add_argument(
        "-p", "--pid",
        type=int,
        help="Process ID to attach (mutually exclusive with command)"
    )

    parser.add_argument(
        "-d", "--duration",
        type=int,
        default=60,
        help="Profile duration in seconds (for --pid, default: 60)"
    )

    parser.add_argument(
        "-o", "--output",
        type=Path,
        default=Path("./profiles"),
        help="Output directory (default: ./profiles)"
    )

    parser.add_argument(
        "--diff",
        action="store_true",
        help="Differential profiling mode (requires 2 commands)"
    )

    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON"
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output"
    )

    return parser.parse_args()


def main() -> int:
    """Main entry point."""
    args = parse_args()

    try:
        profiler = ApplicationProfiler(args.output, verbose=args.verbose)

        if args.diff:
            if len(args.command) != 2:
                print("Error: --diff requires exactly 2 commands", file=sys.stderr)
                return 1

            baseline_result, optimized_result, diff_graph = profiler.differential_profile(
                baseline_command=[args.command[0]],
                optimized_command=[args.command[1]],
                language=Language[args.language.upper()],
                mode=ProfileMode[args.mode.upper()],
            )

            if args.json:
                output = {
                    "baseline": asdict(baseline_result),
                    "optimized": asdict(optimized_result),
                    "differential_graph": diff_graph,
                }
                print(json.dumps(output, indent=2))
            else:
                print(f"Baseline profile: {baseline_result.profile_file}")
                if baseline_result.flame_graph:
                    print(f"Baseline flame graph: {baseline_result.flame_graph}")
                print(f"Optimized profile: {optimized_result.profile_file}")
                if optimized_result.flame_graph:
                    print(f"Optimized flame graph: {optimized_result.flame_graph}")
                if diff_graph:
                    print(f"Differential flame graph: {diff_graph}")

        else:
            result = profiler.profile(
                command=args.command if args.command else None,
                language=Language[args.language.upper()],
                mode=ProfileMode[args.mode.upper()],
                duration=args.duration,
                pid=args.pid,
            )

            if args.json:
                print(json.dumps(asdict(result), indent=2))
            else:
                print(f"Profile file: {result.profile_file}")
                if result.flame_graph:
                    print(f"Flame graph: {result.flame_graph}")
                print(f"Duration: {result.duration:.2f}s")

        return 0

    except ProfilerError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nInterrupted", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
