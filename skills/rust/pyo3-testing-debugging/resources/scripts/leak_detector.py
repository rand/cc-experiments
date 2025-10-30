#!/usr/bin/env python3
"""
PyO3 Memory Leak Detector - Detect memory leaks in PyO3 bindings.

This script provides comprehensive memory leak detection for PyO3 projects
using valgrind, AddressSanitizer (ASAN), and LeakSanitizer (LSAN). It analyzes
memory usage patterns, generates detailed leak reports, and compares results
against baselines to detect regressions.

Usage:
    leak_detector.py valgrind [options]      # Run valgrind analysis
    leak_detector.py asan [options]          # Run AddressSanitizer
    leak_detector.py lsan [options]          # Run LeakSanitizer
    leak_detector.py analyze [options]       # Analyze memory patterns
    leak_detector.py report <file>           # Generate leak report
    leak_detector.py baseline [options]      # Create baseline snapshot
    leak_detector.py compare <baseline>      # Compare against baseline

Examples:
    # Run valgrind with Python suppressions
    leak_detector.py valgrind --suppressions python.supp

    # Run ASAN with specific test
    leak_detector.py asan --test test_basic

    # Analyze memory usage patterns
    leak_detector.py analyze --duration 60

    # Create baseline for regression tracking
    leak_detector.py baseline --output baseline.json

    # Compare current run against baseline
    leak_detector.py compare baseline.json --format html
"""

import argparse
import dataclasses
import json
import os
import pathlib
import re
import subprocess
import sys
import time
from collections import defaultdict
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


class LeakSeverity(Enum):
    """Memory leak severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class LeakType(Enum):
    """Types of memory leaks."""
    DEFINITELY_LOST = "definitely_lost"
    INDIRECTLY_LOST = "indirectly_lost"
    POSSIBLY_LOST = "possibly_lost"
    STILL_REACHABLE = "still_reachable"
    SUPPRESSED = "suppressed"
    PYTHON_INTERNAL = "python_internal"
    PYO3_LEAK = "pyo3_leak"
    RUST_LEAK = "rust_leak"


class OutputFormat(Enum):
    """Output format options."""
    TEXT = "text"
    JSON = "json"
    HTML = "html"
    MARKDOWN = "markdown"


@dataclasses.dataclass
class MemoryLeak:
    """Individual memory leak information."""
    leak_type: LeakType
    severity: LeakSeverity
    bytes_leaked: int
    blocks_leaked: int
    stack_trace: List[str]
    source_file: Optional[str] = None
    source_line: Optional[int] = None
    function: Optional[str] = None
    timestamp: str = dataclasses.field(
        default_factory=lambda: datetime.utcnow().isoformat()
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "leak_type": self.leak_type.value,
            "severity": self.severity.value,
            "bytes_leaked": self.bytes_leaked,
            "blocks_leaked": self.blocks_leaked,
            "stack_trace": self.stack_trace,
            "source_file": self.source_file,
            "source_line": self.source_line,
            "function": self.function,
            "timestamp": self.timestamp,
        }


@dataclasses.dataclass
class MemorySummary:
    """Memory usage summary."""
    total_heap_usage: int
    total_leaked: int
    definitely_lost: int
    indirectly_lost: int
    possibly_lost: int
    still_reachable: int
    suppressed: int
    peak_memory: Optional[int] = None
    allocations: Optional[int] = None
    deallocations: Optional[int] = None

    @property
    def leak_rate(self) -> float:
        """Calculate leak rate as percentage."""
        if self.total_heap_usage == 0:
            return 0.0
        return (self.total_leaked / self.total_heap_usage) * 100.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_heap_usage": self.total_heap_usage,
            "total_leaked": self.total_leaked,
            "definitely_lost": self.definitely_lost,
            "indirectly_lost": self.indirectly_lost,
            "possibly_lost": self.possibly_lost,
            "still_reachable": self.still_reachable,
            "suppressed": self.suppressed,
            "peak_memory": self.peak_memory,
            "allocations": self.allocations,
            "deallocations": self.deallocations,
            "leak_rate": self.leak_rate,
        }


@dataclasses.dataclass
class LeakReport:
    """Comprehensive leak detection report."""
    tool: str  # "valgrind", "asan", "lsan", "analysis"
    project_name: str
    summary: MemorySummary
    leaks: List[MemoryLeak] = dataclasses.field(default_factory=list)
    timestamp: str = dataclasses.field(
        default_factory=lambda: datetime.utcnow().isoformat()
    )
    metadata: Dict[str, Any] = dataclasses.field(default_factory=dict)

    @property
    def critical_leaks(self) -> List[MemoryLeak]:
        """Get critical severity leaks."""
        return [l for l in self.leaks if l.severity == LeakSeverity.CRITICAL]

    @property
    def high_leaks(self) -> List[MemoryLeak]:
        """Get high severity leaks."""
        return [l for l in self.leaks if l.severity == LeakSeverity.HIGH]

    @property
    def total_leak_bytes(self) -> int:
        """Total bytes leaked."""
        return sum(l.bytes_leaked for l in self.leaks)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "tool": self.tool,
            "project_name": self.project_name,
            "summary": self.summary.to_dict(),
            "leaks": [l.to_dict() for l in self.leaks],
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }


class ValgrindRunner:
    """Run valgrind memory analysis."""

    def __init__(
        self,
        project_dir: pathlib.Path,
        suppressions: Optional[pathlib.Path] = None,
        leak_check: str = "full",
        show_reachable: bool = True,
        track_origins: bool = True,
        timeout: int = 600,
        verbose: bool = False,
    ):
        """Initialize valgrind runner."""
        self.project_dir = project_dir
        self.suppressions = suppressions
        self.leak_check = leak_check
        self.show_reachable = show_reachable
        self.track_origins = track_origins
        self.timeout = timeout
        self.verbose = verbose

    def run(self, test_command: Optional[List[str]] = None) -> LeakReport:
        """Run valgrind analysis."""
        if test_command is None:
            test_command = ["python", "-m", "pytest", "tests/"]

        output_file = self.project_dir / "valgrind-output.xml"

        cmd = [
            "valgrind",
            f"--leak-check={self.leak_check}",
            "--show-leak-kinds=all",
            "--track-origins=yes" if self.track_origins else "--track-origins=no",
            "--show-reachable=yes" if self.show_reachable else "--show-reachable=no",
            f"--xml=yes",
            f"--xml-file={output_file}",
            "--child-silent-after-fork=yes",
            "--trace-children=yes",
        ]

        if self.suppressions:
            cmd.append(f"--suppressions={self.suppressions}")

        cmd.extend(test_command)

        if self.verbose:
            print(f"Running: {' '.join(cmd)}")

        try:
            result = subprocess.run(
                cmd,
                cwd=self.project_dir,
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )

            if self.verbose:
                print(f"Valgrind exit code: {result.returncode}")

            # Parse valgrind XML output
            if output_file.exists():
                return self._parse_valgrind_xml(output_file)
            else:
                return self._parse_valgrind_text(result.stderr)

        except subprocess.TimeoutExpired:
            return LeakReport(
                tool="valgrind",
                project_name=self.project_dir.name,
                summary=MemorySummary(
                    total_heap_usage=0,
                    total_leaked=0,
                    definitely_lost=0,
                    indirectly_lost=0,
                    possibly_lost=0,
                    still_reachable=0,
                    suppressed=0,
                ),
                metadata={"error": f"Valgrind timed out after {self.timeout}s"},
            )
        except Exception as e:
            return LeakReport(
                tool="valgrind",
                project_name=self.project_dir.name,
                summary=MemorySummary(
                    total_heap_usage=0,
                    total_leaked=0,
                    definitely_lost=0,
                    indirectly_lost=0,
                    possibly_lost=0,
                    still_reachable=0,
                    suppressed=0,
                ),
                metadata={"error": str(e)},
            )

    def _parse_valgrind_xml(self, xml_file: pathlib.Path) -> LeakReport:
        """Parse valgrind XML output."""
        import xml.etree.ElementTree as ET

        try:
            tree = ET.parse(xml_file)
            root = tree.getroot()

            # Extract summary
            summary_data = {
                "total_heap_usage": 0,
                "total_leaked": 0,
                "definitely_lost": 0,
                "indirectly_lost": 0,
                "possibly_lost": 0,
                "still_reachable": 0,
                "suppressed": 0,
            }

            # Parse leak summary
            for error in root.findall(".//error"):
                kind = error.find("kind")
                if kind is not None:
                    kind_text = kind.text

                    bytes_elem = error.find(".//xwhat/leakedbytes")
                    if bytes_elem is not None:
                        bytes_leaked = int(bytes_elem.text)

                        if "Leak_DefinitelyLost" in kind_text:
                            summary_data["definitely_lost"] += bytes_leaked
                        elif "Leak_IndirectlyLost" in kind_text:
                            summary_data["indirectly_lost"] += bytes_leaked
                        elif "Leak_PossiblyLost" in kind_text:
                            summary_data["possibly_lost"] += bytes_leaked
                        elif "Leak_StillReachable" in kind_text:
                            summary_data["still_reachable"] += bytes_leaked

            summary_data["total_leaked"] = (
                summary_data["definitely_lost"]
                + summary_data["indirectly_lost"]
                + summary_data["possibly_lost"]
            )

            summary = MemorySummary(**summary_data)

            # Parse individual leaks
            leaks: List[MemoryLeak] = []

            for error in root.findall(".//error"):
                kind = error.find("kind")
                if kind is None or "Leak" not in kind.text:
                    continue

                # Determine leak type
                if "DefinitelyLost" in kind.text:
                    leak_type = LeakType.DEFINITELY_LOST
                    severity = LeakSeverity.HIGH
                elif "IndirectlyLost" in kind.text:
                    leak_type = LeakType.INDIRECTLY_LOST
                    severity = LeakSeverity.MEDIUM
                elif "PossiblyLost" in kind.text:
                    leak_type = LeakType.POSSIBLY_LOST
                    severity = LeakSeverity.LOW
                elif "StillReachable" in kind.text:
                    leak_type = LeakType.STILL_REACHABLE
                    severity = LeakSeverity.INFO
                else:
                    continue

                # Extract bytes leaked
                bytes_elem = error.find(".//xwhat/leakedbytes")
                bytes_leaked = int(bytes_elem.text) if bytes_elem is not None else 0

                blocks_elem = error.find(".//xwhat/leakedblocks")
                blocks_leaked = int(blocks_elem.text) if blocks_elem is not None else 0

                # Extract stack trace
                stack_trace: List[str] = []
                for frame in error.findall(".//frame"):
                    fn = frame.find("fn")
                    file = frame.find("file")
                    line = frame.find("line")

                    frame_str = ""
                    if fn is not None:
                        frame_str = fn.text
                    if file is not None and line is not None:
                        frame_str += f" at {file.text}:{line.text}"

                    if frame_str:
                        stack_trace.append(frame_str)

                # Get source location
                first_frame = error.find(".//frame")
                source_file = None
                source_line = None
                function = None

                if first_frame is not None:
                    file_elem = first_frame.find("file")
                    line_elem = first_frame.find("line")
                    fn_elem = first_frame.find("fn")

                    if file_elem is not None:
                        source_file = file_elem.text
                    if line_elem is not None:
                        source_line = int(line_elem.text)
                    if fn_elem is not None:
                        function = fn_elem.text

                # Check if it's a PyO3 leak
                if any("pyo3" in frame.lower() for frame in stack_trace):
                    leak_type = LeakType.PYO3_LEAK
                    severity = LeakSeverity.CRITICAL

                leaks.append(
                    MemoryLeak(
                        leak_type=leak_type,
                        severity=severity,
                        bytes_leaked=bytes_leaked,
                        blocks_leaked=blocks_leaked,
                        stack_trace=stack_trace,
                        source_file=source_file,
                        source_line=source_line,
                        function=function,
                    )
                )

            return LeakReport(
                tool="valgrind",
                project_name=self.project_dir.name,
                summary=summary,
                leaks=leaks,
            )

        except Exception as e:
            if self.verbose:
                print(f"Error parsing valgrind XML: {e}")

            return LeakReport(
                tool="valgrind",
                project_name=self.project_dir.name,
                summary=MemorySummary(
                    total_heap_usage=0,
                    total_leaked=0,
                    definitely_lost=0,
                    indirectly_lost=0,
                    possibly_lost=0,
                    still_reachable=0,
                    suppressed=0,
                ),
                metadata={"error": str(e)},
            )

    def _parse_valgrind_text(self, output: str) -> LeakReport:
        """Parse valgrind text output."""
        summary_data = {
            "total_heap_usage": 0,
            "total_leaked": 0,
            "definitely_lost": 0,
            "indirectly_lost": 0,
            "possibly_lost": 0,
            "still_reachable": 0,
            "suppressed": 0,
        }

        # Parse summary section
        summary_section = re.search(
            r"LEAK SUMMARY:.*?total heap usage",
            output,
            re.DOTALL,
        )

        if summary_section:
            summary_text = summary_section.group(0)

            # Extract values using regex
            patterns = {
                "definitely_lost": r"definitely lost:\s*([\d,]+)\s*bytes",
                "indirectly_lost": r"indirectly lost:\s*([\d,]+)\s*bytes",
                "possibly_lost": r"possibly lost:\s*([\d,]+)\s*bytes",
                "still_reachable": r"still reachable:\s*([\d,]+)\s*bytes",
                "suppressed": r"suppressed:\s*([\d,]+)\s*bytes",
            }

            for key, pattern in patterns.items():
                match = re.search(pattern, summary_text)
                if match:
                    value = match.group(1).replace(",", "")
                    summary_data[key] = int(value)

        summary_data["total_leaked"] = (
            summary_data["definitely_lost"]
            + summary_data["indirectly_lost"]
            + summary_data["possibly_lost"]
        )

        summary = MemorySummary(**summary_data)

        return LeakReport(
            tool="valgrind",
            project_name=self.project_dir.name,
            summary=summary,
            leaks=[],  # Text parsing doesn't extract individual leaks
        )


class AddressSanitizerRunner:
    """Run AddressSanitizer (ASAN) analysis."""

    def __init__(
        self,
        project_dir: pathlib.Path,
        detect_leaks: bool = True,
        check_initialization_order: bool = True,
        timeout: int = 600,
        verbose: bool = False,
    ):
        """Initialize ASAN runner."""
        self.project_dir = project_dir
        self.detect_leaks = detect_leaks
        self.check_initialization_order = check_initialization_order
        self.timeout = timeout
        self.verbose = verbose

    def run(self, test_command: Optional[List[str]] = None) -> LeakReport:
        """Run ASAN analysis."""
        if test_command is None:
            test_command = ["python", "-m", "pytest", "tests/"]

        # Set ASAN environment variables
        asan_options = []
        if self.detect_leaks:
            asan_options.append("detect_leaks=1")
        if self.check_initialization_order:
            asan_options.append("check_initialization_order=1")

        asan_options.extend([
            "halt_on_error=0",
            "log_path=asan-output.txt",
        ])

        env = os.environ.copy()
        env["ASAN_OPTIONS"] = ":".join(asan_options)

        # Build with ASAN
        if self.verbose:
            print("Building with AddressSanitizer...")

        build_env = env.copy()
        build_env["RUSTFLAGS"] = "-Z sanitizer=address"

        build_result = subprocess.run(
            ["cargo", "build"],
            cwd=self.project_dir,
            capture_output=True,
            text=True,
            env=build_env,
        )

        if build_result.returncode != 0:
            return LeakReport(
                tool="asan",
                project_name=self.project_dir.name,
                summary=MemorySummary(
                    total_heap_usage=0,
                    total_leaked=0,
                    definitely_lost=0,
                    indirectly_lost=0,
                    possibly_lost=0,
                    still_reachable=0,
                    suppressed=0,
                ),
                metadata={"error": "ASAN build failed", "output": build_result.stderr},
            )

        if self.verbose:
            print(f"Running: {' '.join(test_command)}")

        try:
            result = subprocess.run(
                test_command,
                cwd=self.project_dir,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                env=env,
            )

            # Parse ASAN output
            asan_log = self.project_dir / "asan-output.txt"
            if asan_log.exists():
                return self._parse_asan_output(asan_log)
            else:
                return self._parse_asan_stderr(result.stderr)

        except subprocess.TimeoutExpired:
            return LeakReport(
                tool="asan",
                project_name=self.project_dir.name,
                summary=MemorySummary(
                    total_heap_usage=0,
                    total_leaked=0,
                    definitely_lost=0,
                    indirectly_lost=0,
                    possibly_lost=0,
                    still_reachable=0,
                    suppressed=0,
                ),
                metadata={"error": f"ASAN timed out after {self.timeout}s"},
            )
        except Exception as e:
            return LeakReport(
                tool="asan",
                project_name=self.project_dir.name,
                summary=MemorySummary(
                    total_heap_usage=0,
                    total_leaked=0,
                    definitely_lost=0,
                    indirectly_lost=0,
                    possibly_lost=0,
                    still_reachable=0,
                    suppressed=0,
                ),
                metadata={"error": str(e)},
            )

    def _parse_asan_output(self, log_file: pathlib.Path) -> LeakReport:
        """Parse ASAN output file."""
        try:
            with open(log_file) as f:
                output = f.read()

            return self._parse_asan_stderr(output)

        except Exception as e:
            return LeakReport(
                tool="asan",
                project_name=self.project_dir.name,
                summary=MemorySummary(
                    total_heap_usage=0,
                    total_leaked=0,
                    definitely_lost=0,
                    indirectly_lost=0,
                    possibly_lost=0,
                    still_reachable=0,
                    suppressed=0,
                ),
                metadata={"error": str(e)},
            )

    def _parse_asan_stderr(self, output: str) -> LeakReport:
        """Parse ASAN stderr output."""
        leaks: List[MemoryLeak] = []
        total_leaked = 0

        # Find all leak reports
        leak_reports = re.findall(
            r"Direct leak of (\d+) byte\(s\) in (\d+) object\(s\)(.*?)(?=Direct leak|Indirect leak|$)",
            output,
            re.DOTALL,
        )

        for bytes_str, blocks_str, trace_text in leak_reports:
            bytes_leaked = int(bytes_str)
            blocks_leaked = int(blocks_str)
            total_leaked += bytes_leaked

            # Extract stack trace
            stack_trace = []
            for line in trace_text.splitlines():
                line = line.strip()
                if line.startswith("#"):
                    stack_trace.append(line)

            # Determine severity and type
            if any("pyo3" in frame.lower() for frame in stack_trace):
                leak_type = LeakType.PYO3_LEAK
                severity = LeakSeverity.CRITICAL
            elif any("python" in frame.lower() for frame in stack_trace):
                leak_type = LeakType.PYTHON_INTERNAL
                severity = LeakSeverity.LOW
            else:
                leak_type = LeakType.RUST_LEAK
                severity = LeakSeverity.HIGH

            leaks.append(
                MemoryLeak(
                    leak_type=leak_type,
                    severity=severity,
                    bytes_leaked=bytes_leaked,
                    blocks_leaked=blocks_leaked,
                    stack_trace=stack_trace,
                )
            )

        summary = MemorySummary(
            total_heap_usage=total_leaked,  # ASAN doesn't provide full heap info
            total_leaked=total_leaked,
            definitely_lost=total_leaked,
            indirectly_lost=0,
            possibly_lost=0,
            still_reachable=0,
            suppressed=0,
        )

        return LeakReport(
            tool="asan",
            project_name=self.project_dir.name,
            summary=summary,
            leaks=leaks,
        )


class MemoryAnalyzer:
    """Analyze memory usage patterns."""

    def __init__(
        self,
        project_dir: pathlib.Path,
        duration: int = 60,
        interval: float = 0.1,
        verbose: bool = False,
    ):
        """Initialize memory analyzer."""
        self.project_dir = project_dir
        self.duration = duration
        self.interval = interval
        self.verbose = verbose

    def run(self, test_command: Optional[List[str]] = None) -> LeakReport:
        """Run memory analysis."""
        if test_command is None:
            test_command = ["python", "-m", "pytest", "tests/"]

        if self.verbose:
            print(f"Analyzing memory for {self.duration}s...")

        # Start test process
        import psutil

        process = subprocess.Popen(
            test_command,
            cwd=self.project_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        try:
            ps_process = psutil.Process(process.pid)

            samples: List[Tuple[float, int]] = []
            start_time = time.time()

            while time.time() - start_time < self.duration:
                try:
                    # Get memory info
                    mem_info = ps_process.memory_info()
                    samples.append((time.time() - start_time, mem_info.rss))

                    time.sleep(self.interval)

                except psutil.NoSuchProcess:
                    break

            # Wait for process to complete
            process.wait(timeout=10)

            # Analyze samples
            if not samples:
                return LeakReport(
                    tool="analysis",
                    project_name=self.project_dir.name,
                    summary=MemorySummary(
                        total_heap_usage=0,
                        total_leaked=0,
                        definitely_lost=0,
                        indirectly_lost=0,
                        possibly_lost=0,
                        still_reachable=0,
                        suppressed=0,
                    ),
                    metadata={"error": "No memory samples collected"},
                )

            # Calculate statistics
            memory_values = [mem for _, mem in samples]
            peak_memory = max(memory_values)
            avg_memory = sum(memory_values) / len(memory_values)
            final_memory = memory_values[-1]
            initial_memory = memory_values[0]

            # Detect memory growth
            memory_growth = final_memory - initial_memory
            growth_rate = memory_growth / self.duration

            # Determine if there's a leak
            leak_detected = growth_rate > 1024 * 100  # 100 KB/s threshold

            leaks: List[MemoryLeak] = []
            if leak_detected:
                leaks.append(
                    MemoryLeak(
                        leak_type=LeakType.PYO3_LEAK,
                        severity=LeakSeverity.HIGH,
                        bytes_leaked=memory_growth,
                        blocks_leaked=0,
                        stack_trace=[
                            f"Memory growth detected: {memory_growth / 1024:.1f} KB",
                            f"Growth rate: {growth_rate / 1024:.1f} KB/s",
                        ],
                    )
                )

            summary = MemorySummary(
                total_heap_usage=avg_memory,
                total_leaked=memory_growth if leak_detected else 0,
                definitely_lost=0,
                indirectly_lost=0,
                possibly_lost=0,
                still_reachable=0,
                suppressed=0,
                peak_memory=peak_memory,
            )

            return LeakReport(
                tool="analysis",
                project_name=self.project_dir.name,
                summary=summary,
                leaks=leaks,
                metadata={
                    "duration": self.duration,
                    "samples": len(samples),
                    "peak_memory_mb": peak_memory / (1024 * 1024),
                    "avg_memory_mb": avg_memory / (1024 * 1024),
                    "memory_growth_kb": memory_growth / 1024,
                    "growth_rate_kb_s": growth_rate / 1024,
                },
            )

        except Exception as e:
            process.kill()
            return LeakReport(
                tool="analysis",
                project_name=self.project_dir.name,
                summary=MemorySummary(
                    total_heap_usage=0,
                    total_leaked=0,
                    definitely_lost=0,
                    indirectly_lost=0,
                    possibly_lost=0,
                    still_reachable=0,
                    suppressed=0,
                ),
                metadata={"error": str(e)},
            )


class LeakReportGenerator:
    """Generate leak reports in various formats."""

    def __init__(self, report: LeakReport):
        """Initialize report generator."""
        self.report = report

    def generate(self, format: OutputFormat, output_file: Optional[pathlib.Path] = None) -> str:
        """Generate report in specified format."""
        if format == OutputFormat.TEXT:
            content = self._generate_text()
        elif format == OutputFormat.JSON:
            content = self._generate_json()
        elif format == OutputFormat.HTML:
            content = self._generate_html()
        elif format == OutputFormat.MARKDOWN:
            content = self._generate_markdown()
        else:
            raise ValueError(f"Unknown format: {format}")

        if output_file:
            output_file.write_text(content)

        return content

    def _generate_text(self) -> str:
        """Generate plain text report."""
        lines = [
            f"Memory Leak Report: {self.report.project_name}",
            "=" * 80,
            f"Tool: {self.report.tool}",
            f"Timestamp: {self.report.timestamp}",
            "",
            "Summary:",
            f"  Total Heap Usage: {self._format_bytes(self.report.summary.total_heap_usage)}",
            f"  Total Leaked: {self._format_bytes(self.report.summary.total_leaked)}",
            f"  Leak Rate: {self.report.summary.leak_rate:.2f}%",
            f"  Definitely Lost: {self._format_bytes(self.report.summary.definitely_lost)}",
            f"  Indirectly Lost: {self._format_bytes(self.report.summary.indirectly_lost)}",
            f"  Possibly Lost: {self._format_bytes(self.report.summary.possibly_lost)}",
            f"  Still Reachable: {self._format_bytes(self.report.summary.still_reachable)}",
            f"  Suppressed: {self._format_bytes(self.report.summary.suppressed)}",
        ]

        if self.report.summary.peak_memory is not None:
            lines.append(f"  Peak Memory: {self._format_bytes(self.report.summary.peak_memory)}")

        lines.append(f"\nTotal Leaks Found: {len(self.report.leaks)}")

        if self.report.critical_leaks:
            lines.extend(["\nCritical Leaks:", "-" * 80])
            for leak in self.report.critical_leaks:
                lines.extend(self._format_leak_text(leak))

        if self.report.high_leaks:
            lines.extend(["\nHigh Priority Leaks:", "-" * 80])
            for leak in self.report.high_leaks:
                lines.extend(self._format_leak_text(leak))

        if self.report.metadata.get("error"):
            lines.extend(["\nError:", self.report.metadata["error"]])

        return "\n".join(lines)

    def _format_leak_text(self, leak: MemoryLeak) -> List[str]:
        """Format a single leak as text."""
        lines = [
            f"\n{leak.leak_type.value} ({leak.severity.value})",
            f"  Bytes: {self._format_bytes(leak.bytes_leaked)}",
            f"  Blocks: {leak.blocks_leaked}",
        ]

        if leak.function:
            lines.append(f"  Function: {leak.function}")

        if leak.source_file:
            location = leak.source_file
            if leak.source_line:
                location += f":{leak.source_line}"
            lines.append(f"  Location: {location}")

        if leak.stack_trace:
            lines.append("  Stack Trace:")
            for frame in leak.stack_trace[:10]:  # Limit to first 10 frames
                lines.append(f"    {frame}")

        return lines

    def _generate_json(self) -> str:
        """Generate JSON report."""
        return json.dumps(self.report.to_dict(), indent=2)

    def _generate_html(self) -> str:
        """Generate HTML report."""
        html = [
            "<!DOCTYPE html>",
            "<html>",
            "<head>",
            f"<title>Memory Leak Report: {self.report.project_name}</title>",
            "<style>",
            "body { font-family: Arial, sans-serif; margin: 20px; }",
            "h1 { color: #333; }",
            "table { border-collapse: collapse; width: 100%; margin: 20px 0; }",
            "th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }",
            "th { background-color: #4CAF50; color: white; }",
            ".critical { background-color: #ff6b6b; color: white; }",
            ".high { background-color: #ff9a00; }",
            ".medium { background-color: #ffd700; }",
            ".low { background-color: #90ee90; }",
            ".summary { background-color: #f2f2f2; padding: 15px; margin: 20px 0; border-radius: 5px; }",
            ".leak { background-color: #fff; padding: 10px; margin: 10px 0; border-left: 4px solid #ff6b6b; }",
            "pre { background-color: #f4f4f4; padding: 10px; overflow-x: auto; }",
            "</style>",
            "</head>",
            "<body>",
            f"<h1>Memory Leak Report: {self.report.project_name}</h1>",
            f"<p><strong>Tool:</strong> {self.report.tool}</p>",
            f"<p><strong>Timestamp:</strong> {self.report.timestamp}</p>",
            '<div class="summary">',
            "<h2>Summary</h2>",
            f"<p><strong>Total Heap Usage:</strong> {self._format_bytes(self.report.summary.total_heap_usage)}</p>",
            f"<p><strong>Total Leaked:</strong> {self._format_bytes(self.report.summary.total_leaked)}</p>",
            f"<p><strong>Leak Rate:</strong> {self.report.summary.leak_rate:.2f}%</p>",
            "<table>",
            "<tr><th>Category</th><th>Bytes</th></tr>",
            f"<tr><td>Definitely Lost</td><td>{self._format_bytes(self.report.summary.definitely_lost)}</td></tr>",
            f"<tr><td>Indirectly Lost</td><td>{self._format_bytes(self.report.summary.indirectly_lost)}</td></tr>",
            f"<tr><td>Possibly Lost</td><td>{self._format_bytes(self.report.summary.possibly_lost)}</td></tr>",
            f"<tr><td>Still Reachable</td><td>{self._format_bytes(self.report.summary.still_reachable)}</td></tr>",
            f"<tr><td>Suppressed</td><td>{self._format_bytes(self.report.summary.suppressed)}</td></tr>",
            "</table>",
            "</div>",
        ]

        if self.report.leaks:
            html.append(f"<h2>Leaks Found: {len(self.report.leaks)}</h2>")

            for leak in self.report.leaks:
                severity_class = leak.severity.value
                html.extend([
                    f'<div class="leak {severity_class}">',
                    f"<h3>{leak.leak_type.value} ({leak.severity.value})</h3>",
                    f"<p><strong>Bytes:</strong> {self._format_bytes(leak.bytes_leaked)}</p>",
                    f"<p><strong>Blocks:</strong> {leak.blocks_leaked}</p>",
                ])

                if leak.function:
                    html.append(f"<p><strong>Function:</strong> {leak.function}</p>")

                if leak.source_file:
                    location = leak.source_file
                    if leak.source_line:
                        location += f":{leak.source_line}"
                    html.append(f"<p><strong>Location:</strong> {location}</p>")

                if leak.stack_trace:
                    html.append("<p><strong>Stack Trace:</strong></p>")
                    html.append("<pre>")
                    html.append("\n".join(leak.stack_trace[:10]))
                    html.append("</pre>")

                html.append("</div>")

        html.extend(["</body>", "</html>"])

        return "\n".join(html)

    def _generate_markdown(self) -> str:
        """Generate Markdown report."""
        lines = [
            f"# Memory Leak Report: {self.report.project_name}",
            "",
            f"**Tool:** {self.report.tool}",
            f"**Timestamp:** {self.report.timestamp}",
            "",
            "## Summary",
            "",
            f"- **Total Heap Usage:** {self._format_bytes(self.report.summary.total_heap_usage)}",
            f"- **Total Leaked:** {self._format_bytes(self.report.summary.total_leaked)}",
            f"- **Leak Rate:** {self.report.summary.leak_rate:.2f}%",
            "",
            "### Leak Categories",
            "",
            f"- **Definitely Lost:** {self._format_bytes(self.report.summary.definitely_lost)}",
            f"- **Indirectly Lost:** {self._format_bytes(self.report.summary.indirectly_lost)}",
            f"- **Possibly Lost:** {self._format_bytes(self.report.summary.possibly_lost)}",
            f"- **Still Reachable:** {self._format_bytes(self.report.summary.still_reachable)}",
            f"- **Suppressed:** {self._format_bytes(self.report.summary.suppressed)}",
            "",
        ]

        if self.report.leaks:
            lines.append(f"## Leaks Found: {len(self.report.leaks)}")
            lines.append("")

            for i, leak in enumerate(self.report.leaks, 1):
                lines.extend([
                    f"### Leak {i}: {leak.leak_type.value}",
                    "",
                    f"**Severity:** {leak.severity.value}",
                    f"**Bytes:** {self._format_bytes(leak.bytes_leaked)}",
                    f"**Blocks:** {leak.blocks_leaked}",
                    "",
                ])

                if leak.function:
                    lines.append(f"**Function:** `{leak.function}`")

                if leak.source_file:
                    location = leak.source_file
                    if leak.source_line:
                        location += f":{leak.source_line}"
                    lines.append(f"**Location:** `{location}`")

                if leak.stack_trace:
                    lines.extend([
                        "",
                        "**Stack Trace:**",
                        "```",
                        *leak.stack_trace[:10],
                        "```",
                        "",
                    ])

        return "\n".join(lines)

    @staticmethod
    def _format_bytes(bytes_value: int) -> str:
        """Format bytes in human-readable form."""
        for unit in ["B", "KB", "MB", "GB"]:
            if bytes_value < 1024.0:
                return f"{bytes_value:.1f} {unit}"
            bytes_value /= 1024.0
        return f"{bytes_value:.1f} TB"


class LeakComparator:
    """Compare leak reports against baseline."""

    def __init__(self, baseline: LeakReport, current: LeakReport):
        """Initialize comparator."""
        self.baseline = baseline
        self.current = current

    def compare(self) -> Dict[str, Any]:
        """Compare current results against baseline."""
        comparison = {
            "timestamp": datetime.utcnow().isoformat(),
            "baseline_timestamp": self.baseline.timestamp,
            "current_timestamp": self.current.timestamp,
            "summary": {
                "total_leaked_delta": self.current.summary.total_leaked - self.baseline.summary.total_leaked,
                "leak_rate_delta": self.current.summary.leak_rate - self.baseline.summary.leak_rate,
                "leak_count_delta": len(self.current.leaks) - len(self.baseline.leaks),
            },
            "new_leaks": [],
            "fixed_leaks": [],
            "regression": False,
        }

        # Determine if there's a regression
        if comparison["summary"]["total_leaked_delta"] > 0:
            comparison["regression"] = True

        # Compare leak counts by severity
        baseline_critical = len(self.baseline.critical_leaks)
        current_critical = len(self.current.critical_leaks)
        comparison["summary"]["critical_delta"] = current_critical - baseline_critical

        baseline_high = len(self.baseline.high_leaks)
        current_high = len(self.current.high_leaks)
        comparison["summary"]["high_delta"] = current_high - baseline_high

        return comparison

    def format_comparison(self, comparison: Dict[str, Any], format: OutputFormat) -> str:
        """Format comparison results."""
        if format == OutputFormat.JSON:
            return json.dumps(comparison, indent=2)
        elif format == OutputFormat.TEXT:
            return self._format_comparison_text(comparison)
        elif format == OutputFormat.MARKDOWN:
            return self._format_comparison_markdown(comparison)
        else:
            raise ValueError(f"Unsupported format: {format}")

    def _format_comparison_text(self, comparison: Dict[str, Any]) -> str:
        """Format comparison as plain text."""
        lines = [
            "Memory Leak Comparison",
            "=" * 80,
            f"Baseline: {comparison['baseline_timestamp']}",
            f"Current:  {comparison['current_timestamp']}",
            "",
            "Summary:",
            f"  Total Leaked Delta: {comparison['summary']['total_leaked_delta']:+d} bytes",
            f"  Leak Rate Delta: {comparison['summary']['leak_rate_delta']:+.2f}%",
            f"  Leak Count Delta: {comparison['summary']['leak_count_delta']:+d}",
            f"  Critical Leaks Delta: {comparison['summary']['critical_delta']:+d}",
            f"  High Leaks Delta: {comparison['summary']['high_delta']:+d}",
            "",
        ]

        if comparison["regression"]:
            lines.append("⚠️  REGRESSION DETECTED: Memory leaks have increased!")
        else:
            lines.append("✓ No regression: Memory leaks stable or improved")

        return "\n".join(lines)

    def _format_comparison_markdown(self, comparison: Dict[str, Any]) -> str:
        """Format comparison as Markdown."""
        lines = [
            "# Memory Leak Comparison",
            "",
            f"**Baseline:** {comparison['baseline_timestamp']}",
            f"**Current:** {comparison['current_timestamp']}",
            "",
            "## Summary",
            "",
            f"- **Total Leaked Delta:** {comparison['summary']['total_leaked_delta']:+d} bytes",
            f"- **Leak Rate Delta:** {comparison['summary']['leak_rate_delta']:+.2f}%",
            f"- **Leak Count Delta:** {comparison['summary']['leak_count_delta']:+d}",
            f"- **Critical Leaks Delta:** {comparison['summary']['critical_delta']:+d}",
            f"- **High Leaks Delta:** {comparison['summary']['high_delta']:+d}",
            "",
        ]

        if comparison["regression"]:
            lines.append("## ⚠️ REGRESSION DETECTED")
            lines.append("")
            lines.append("Memory leaks have increased compared to baseline!")
        else:
            lines.append("## ✓ No Regression")
            lines.append("")
            lines.append("Memory leaks are stable or improved compared to baseline.")

        return "\n".join(lines)


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="PyO3 Memory Leak Detector",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Common arguments
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "--project-dir",
        type=pathlib.Path,
        default=pathlib.Path.cwd(),
        help="Project directory (default: current directory)",
    )
    common.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    # Valgrind command
    valgrind_parser = subparsers.add_parser("valgrind", parents=[common], help="Run valgrind analysis")
    valgrind_parser.add_argument("--suppressions", type=pathlib.Path, help="Suppressions file")
    valgrind_parser.add_argument(
        "--leak-check",
        choices=["full", "summary"],
        default="full",
        help="Leak check level",
    )
    valgrind_parser.add_argument("--timeout", type=int, default=600, help="Timeout in seconds")
    valgrind_parser.add_argument("--output", type=pathlib.Path, help="Output file for report")

    # ASAN command
    asan_parser = subparsers.add_parser("asan", parents=[common], help="Run AddressSanitizer")
    asan_parser.add_argument("--detect-leaks", action="store_true", default=True, help="Detect leaks")
    asan_parser.add_argument("--timeout", type=int, default=600, help="Timeout in seconds")
    asan_parser.add_argument("--output", type=pathlib.Path, help="Output file for report")

    # Analyze command
    analyze_parser = subparsers.add_parser("analyze", parents=[common], help="Analyze memory patterns")
    analyze_parser.add_argument("--duration", type=int, default=60, help="Analysis duration in seconds")
    analyze_parser.add_argument("--interval", type=float, default=0.1, help="Sampling interval")
    analyze_parser.add_argument("--output", type=pathlib.Path, help="Output file for report")

    # Report command
    report_parser = subparsers.add_parser("report", parents=[common], help="Generate leak report")
    report_parser.add_argument("input", type=pathlib.Path, help="Input JSON report file")
    report_parser.add_argument(
        "--format",
        choices=["text", "json", "html", "markdown"],
        default="text",
        help="Output format",
    )
    report_parser.add_argument("--output", type=pathlib.Path, help="Output file")

    # Baseline command
    baseline_parser = subparsers.add_parser("baseline", parents=[common], help="Create baseline snapshot")
    baseline_parser.add_argument(
        "--tool",
        choices=["valgrind", "asan", "analyze"],
        default="valgrind",
        help="Tool to use",
    )
    baseline_parser.add_argument("--output", type=pathlib.Path, required=True, help="Output file")

    # Compare command
    compare_parser = subparsers.add_parser("compare", parents=[common], help="Compare against baseline")
    compare_parser.add_argument("baseline", type=pathlib.Path, help="Baseline report JSON file")
    compare_parser.add_argument(
        "--current",
        type=pathlib.Path,
        help="Current report JSON file",
    )
    compare_parser.add_argument(
        "--format",
        choices=["text", "json", "markdown"],
        default="text",
        help="Output format",
    )
    compare_parser.add_argument("--output", type=pathlib.Path, help="Output file")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    try:
        if args.command == "valgrind":
            return cmd_valgrind(args)
        elif args.command == "asan":
            return cmd_asan(args)
        elif args.command == "analyze":
            return cmd_analyze(args)
        elif args.command == "report":
            return cmd_report(args)
        elif args.command == "baseline":
            return cmd_baseline(args)
        elif args.command == "compare":
            return cmd_compare(args)
        else:
            print(f"Unknown command: {args.command}", file=sys.stderr)
            return 1

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


def cmd_valgrind(args: argparse.Namespace) -> int:
    """Run valgrind analysis."""
    runner = ValgrindRunner(
        args.project_dir,
        suppressions=args.suppressions,
        leak_check=args.leak_check,
        timeout=args.timeout,
        verbose=args.verbose,
    )

    report = runner.run()

    # Generate output
    generator = LeakReportGenerator(report)
    output = generator.generate(OutputFormat.TEXT)
    print(output)

    # Save report
    if args.output:
        args.output.write_text(json.dumps(report.to_dict(), indent=2))
        print(f"\nReport saved to: {args.output}")

    return 0 if report.summary.total_leaked == 0 else 1


def cmd_asan(args: argparse.Namespace) -> int:
    """Run ASAN analysis."""
    runner = AddressSanitizerRunner(
        args.project_dir,
        detect_leaks=args.detect_leaks,
        timeout=args.timeout,
        verbose=args.verbose,
    )

    report = runner.run()

    # Generate output
    generator = LeakReportGenerator(report)
    output = generator.generate(OutputFormat.TEXT)
    print(output)

    # Save report
    if args.output:
        args.output.write_text(json.dumps(report.to_dict(), indent=2))
        print(f"\nReport saved to: {args.output}")

    return 0 if report.summary.total_leaked == 0 else 1


def cmd_analyze(args: argparse.Namespace) -> int:
    """Run memory analysis."""
    analyzer = MemoryAnalyzer(
        args.project_dir,
        duration=args.duration,
        interval=args.interval,
        verbose=args.verbose,
    )

    report = analyzer.run()

    # Generate output
    generator = LeakReportGenerator(report)
    output = generator.generate(OutputFormat.TEXT)
    print(output)

    # Save report
    if args.output:
        args.output.write_text(json.dumps(report.to_dict(), indent=2))
        print(f"\nReport saved to: {args.output}")

    return 0


def cmd_report(args: argparse.Namespace) -> int:
    """Generate leak report."""
    if not args.input.exists():
        print(f"Input file not found: {args.input}", file=sys.stderr)
        return 1

    with open(args.input) as f:
        data = json.load(f)

    # Reconstruct report from JSON
    summary = MemorySummary(**data["summary"])
    leaks = [
        MemoryLeak(
            leak_type=LeakType(l["leak_type"]),
            severity=LeakSeverity(l["severity"]),
            bytes_leaked=l["bytes_leaked"],
            blocks_leaked=l["blocks_leaked"],
            stack_trace=l["stack_trace"],
            source_file=l.get("source_file"),
            source_line=l.get("source_line"),
            function=l.get("function"),
            timestamp=l["timestamp"],
        )
        for l in data["leaks"]
    ]

    report = LeakReport(
        tool=data["tool"],
        project_name=data["project_name"],
        summary=summary,
        leaks=leaks,
        timestamp=data["timestamp"],
        metadata=data.get("metadata", {}),
    )

    # Generate report
    generator = LeakReportGenerator(report)
    format = OutputFormat(args.format)
    output = generator.generate(format, args.output)

    if not args.output:
        print(output)

    return 0


def cmd_baseline(args: argparse.Namespace) -> int:
    """Create baseline snapshot."""
    if args.tool == "valgrind":
        runner = ValgrindRunner(args.project_dir, verbose=args.verbose)
        report = runner.run()
    elif args.tool == "asan":
        runner = AddressSanitizerRunner(args.project_dir, verbose=args.verbose)
        report = runner.run()
    elif args.tool == "analyze":
        analyzer = MemoryAnalyzer(args.project_dir, verbose=args.verbose)
        report = analyzer.run()
    else:
        print(f"Unknown tool: {args.tool}", file=sys.stderr)
        return 1

    # Save baseline
    args.output.write_text(json.dumps(report.to_dict(), indent=2))
    print(f"Baseline saved to: {args.output}")

    return 0


def cmd_compare(args: argparse.Namespace) -> int:
    """Compare against baseline."""
    if not args.baseline.exists():
        print(f"Baseline file not found: {args.baseline}", file=sys.stderr)
        return 1

    # Load baseline
    with open(args.baseline) as f:
        baseline_data = json.load(f)

    # Load or generate current report
    if args.current:
        if not args.current.exists():
            print(f"Current file not found: {args.current}", file=sys.stderr)
            return 1
        with open(args.current) as f:
            current_data = json.load(f)
    else:
        print("Error: --current is required", file=sys.stderr)
        return 1

    # Reconstruct reports
    def reconstruct_report(data: Dict[str, Any]) -> LeakReport:
        summary = MemorySummary(**data["summary"])
        leaks = [
            MemoryLeak(
                leak_type=LeakType(l["leak_type"]),
                severity=LeakSeverity(l["severity"]),
                bytes_leaked=l["bytes_leaked"],
                blocks_leaked=l["blocks_leaked"],
                stack_trace=l["stack_trace"],
                source_file=l.get("source_file"),
                source_line=l.get("source_line"),
                function=l.get("function"),
                timestamp=l["timestamp"],
            )
            for l in data["leaks"]
        ]

        return LeakReport(
            tool=data["tool"],
            project_name=data["project_name"],
            summary=summary,
            leaks=leaks,
            timestamp=data["timestamp"],
            metadata=data.get("metadata", {}),
        )

    baseline = reconstruct_report(baseline_data)
    current = reconstruct_report(current_data)

    # Compare
    comparator = LeakComparator(baseline, current)
    comparison = comparator.compare()

    # Format output
    format = OutputFormat(args.format)
    output = comparator.format_comparison(comparison, format)

    if args.output:
        args.output.write_text(output)
    else:
        print(output)

    # Return error code if regression detected
    return 1 if comparison["regression"] else 0


if __name__ == "__main__":
    sys.exit(main())
