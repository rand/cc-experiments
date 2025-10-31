#!/usr/bin/env python3
"""
PyO3 Cross-Language Debugging Utilities

Provides tools for debugging across Python and Rust boundaries.
"""

import argparse
import json
import os
import platform
import re
import subprocess
import sys
import time
import traceback
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Dict, Optional, Any, Tuple


@dataclass
class StackFrame:
    """Represents a single stack frame."""
    index: int
    language: str  # 'python' or 'rust'
    function: str
    file: Optional[str]
    line: Optional[int]
    address: Optional[str]
    module: Optional[str]


@dataclass
class StackTrace:
    """Complete stack trace."""
    frames: List[StackFrame]
    crash_reason: Optional[str]
    signal: Optional[str]


class CrossLanguageDebugger:
    """Cross-language debugging utilities for PyO3."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose

    def log(self, msg: str) -> None:
        if self.verbose:
            print(f"[DEBUG] {msg}", file=sys.stderr)

    def parse_python_traceback(self, tb_text: str) -> List[StackFrame]:
        """Parse Python traceback."""
        frames = []
        lines = tb_text.strip().split('\n')
        
        frame_idx = 0
        for i, line in enumerate(lines):
            if line.strip().startswith('File "'):
                match = re.match(r'\s*File "([^"]+)", line (\d+), in (.+)', line)
                if match:
                    frames.append(StackFrame(
                        index=frame_idx,
                        language='python',
                        function=match.group(3).strip(),
                        file=match.group(1),
                        line=int(match.group(2)),
                        address=None,
                        module=None
                    ))
                    frame_idx += 1
        
        return frames

    def parse_rust_backtrace(self, bt_text: str) -> List[StackFrame]:
        """Parse Rust backtrace."""
        frames = []
        lines = bt_text.strip().split('\n')
        
        frame_pattern = re.compile(
            r'\s*(\d+):\s+0x([0-9a-f]+)\s+-\s+(.+?)(?:\s+at\s+(.+?):(\d+))?$'
        )
        
        for line in lines:
            match = frame_pattern.match(line)
            if match:
                idx, addr, func, file, line_num = match.groups()
                frames.append(StackFrame(
                    index=int(idx),
                    language='rust',
                    function=func.strip(),
                    file=file if file else None,
                    line=int(line_num) if line_num else None,
                    address=f"0x{addr}",
                    module=None
                ))
        
        return frames

    def parse_lldb_backtrace(self, bt_text: str) -> List[StackFrame]:
        """Parse lldb backtrace."""
        frames = []
        lines = bt_text.strip().split('\n')
        
        # Pattern: frame #0: 0xaddr module`function at file:line
        frame_pattern = re.compile(
            r'\s*(?:\*\s+)?frame\s+#(\d+):'
            r'\s+0x([0-9a-f]+)'
            r'\s+([^`]+)`([^\s]+)'
            r'(?:\s+at\s+([^:]+):(\d+))?'
        )
        
        for line in lines:
            match = frame_pattern.match(line)
            if match:
                idx, addr, module, func, file, line_num = match.groups()
                
                # Determine language from module
                lang = 'rust' if '.so' in module or 'lib' in module else 'python'
                if 'python' in module.lower():
                    lang = 'python'
                
                frames.append(StackFrame(
                    index=int(idx),
                    language=lang,
                    function=func.strip(),
                    file=file if file else None,
                    line=int(line_num) if line_num else None,
                    address=f"0x{addr}",
                    module=module.strip()
                ))
        
        return frames

    def aggregate_stacktrace(self, python_tb: Optional[str] = None,
                            rust_bt: Optional[str] = None,
                            lldb_bt: Optional[str] = None) -> StackTrace:
        """Aggregate stack traces from multiple sources."""
        all_frames = []
        
        if python_tb:
            all_frames.extend(self.parse_python_traceback(python_tb))
        if rust_bt:
            all_frames.extend(self.parse_rust_backtrace(rust_bt))
        if lldb_bt:
            all_frames.extend(self.parse_lldb_backtrace(lldb_bt))
        
        # Reindex frames
        for i, frame in enumerate(all_frames):
            frame.index = i
        
        return StackTrace(frames=all_frames, crash_reason=None, signal=None)

    def print_stacktrace(self, st: StackTrace) -> None:
        """Print formatted stack trace."""
        print("\n" + "=" * 70)
        print("Cross-Language Stack Trace")
        print("=" * 70)
        
        if st.crash_reason:
            print(f"\nCrash Reason: {st.crash_reason}")
        if st.signal:
            print(f"Signal: {st.signal}")
        
        print(f"\nTotal Frames: {len(st.frames)}\n")
        
        for frame in st.frames:
            lang_icon = "🐍" if frame.language == 'python' else "🦀"
            print(f"Frame #{frame.index}: {lang_icon} [{frame.language.upper()}]")
            print(f"  Function: {frame.function}")
            if frame.file:
                location = f"{frame.file}"
                if frame.line:
                    location += f":{frame.line}"
                print(f"  Location: {location}")
            if frame.address:
                print(f"  Address:  {frame.address}")
            if frame.module:
                print(f"  Module:   {frame.module}")
            print()

    def capture_live_stacktrace(self, pid: int) -> StackTrace:
        """Capture stack trace from running process."""
        self.log(f"Attaching to process {pid}...")
        
        system = platform.system()
        
        if system == "Darwin" or system == "Linux":
            # Use lldb
            cmd = [
                "lldb",
                "-p", str(pid),
                "-batch",
                "-o", "thread backtrace all",
                "-o", "detach",
                "-o", "quit"
            ]
        else:
            raise NotImplementedError(f"Platform {system} not supported")
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                print(f"Error capturing stacktrace: {result.stderr}")
                return StackTrace(frames=[], crash_reason=None, signal=None)
            
            return self.aggregate_stacktrace(lldb_bt=result.stdout)
            
        except subprocess.TimeoutExpired:
            print("Timeout while capturing stacktrace")
            return StackTrace(frames=[], crash_reason=None, signal=None)
        except FileNotFoundError:
            print("lldb not found - install debugging tools")
            return StackTrace(frames=[], crash_reason=None, signal=None)

    def analyze_core_dump(self, core_path: str, executable: str) -> StackTrace:
        """Analyze core dump file."""
        self.log(f"Analyzing core dump: {core_path}")
        
        cmd = [
            "lldb",
            "-c", core_path,
            executable,
            "-batch",
            "-o", "thread backtrace all",
            "-o", "quit"
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            st = self.aggregate_stacktrace(lldb_bt=result.stdout)
            
            # Try to extract crash reason
            if "signal" in result.stdout.lower():
                match = re.search(r'signal\s+(\w+)', result.stdout, re.I)
                if match:
                    st.signal = match.group(1)
            
            return st
            
        except Exception as e:
            print(f"Error analyzing core dump: {e}")
            return StackTrace(frames=[], crash_reason=str(e), signal=None)

    def set_breakpoint(self, function: str, condition: Optional[str] = None,
                      commands: Optional[List[str]] = None) -> str:
        """Generate breakpoint configuration."""
        config = f"breakpoint set --name {function}\n"
        
        if condition:
            config += f"breakpoint modify --condition '{condition}'\n"
        
        if commands:
            config += "breakpoint command add\n"
            for cmd in commands:
                config += f"{cmd}\n"
            config += "DONE\n"
        
        return config

    def create_lldbinit(self, output_path: str, breakpoints: List[Dict[str, Any]]) -> None:
        """Create .lldbinit file with breakpoints."""
        with open(output_path, 'w') as f:
            f.write("# Auto-generated lldb configuration\n\n")
            
            for bp in breakpoints:
                config = self.set_breakpoint(
                    function=bp['function'],
                    condition=bp.get('condition'),
                    commands=bp.get('commands')
                )
                f.write(config + "\n")
            
            f.write("# Continue execution\n")
            f.write("continue\n")
        
        print(f"Created lldb configuration: {output_path}")

class MemoryLeakDetector:
    """Detect memory leaks in PyO3 applications."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose

    def check_valgrind_available(self) -> bool:
        """Check if valgrind is installed."""
        try:
            result = subprocess.run(
                ["valgrind", "--version"],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def run_valgrind(self, command: List[str], timeout: int = 300) -> Dict[str, Any]:
        """Run valgrind memory leak detection."""
        if not self.check_valgrind_available():
            print("Error: valgrind not installed")
            return {}
        
        valgrind_cmd = [
            "valgrind",
            "--leak-check=full",
            "--show-leak-kinds=all",
            "--track-origins=yes",
            "--verbose",
        ] + command
        
        print(f"Running: {' '.join(valgrind_cmd)}")
        print("This may take a while...\n")
        
        try:
            result = subprocess.run(
                valgrind_cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            return self.parse_valgrind_output(result.stderr)
            
        except subprocess.TimeoutExpired:
            print(f"Valgrind timed out after {timeout}s")
            return {}

    def parse_valgrind_output(self, output: str) -> Dict[str, Any]:
        """Parse valgrind output."""
        report = {
            "definitely_lost": 0,
            "indirectly_lost": 0,
            "possibly_lost": 0,
            "still_reachable": 0,
            "suppressed": 0,
            "total_allocs": 0,
            "total_frees": 0,
        }
        
        # Parse leak summary
        patterns = {
            "definitely_lost": r"definitely lost:\s+([\d,]+) bytes",
            "indirectly_lost": r"indirectly lost:\s+([\d,]+) bytes",
            "possibly_lost": r"possibly lost:\s+([\d,]+) bytes",
            "still_reachable": r"still reachable:\s+([\d,]+) bytes",
        }
        
        for key, pattern in patterns.items():
            match = re.search(pattern, output)
            if match:
                value_str = match.group(1).replace(',', '')
                report[key] = int(value_str)
        
        # Parse alloc/free counts
        alloc_match = re.search(r"total heap usage:\s+([\d,]+) allocs", output)
        if alloc_match:
            report["total_allocs"] = int(alloc_match.group(1).replace(',', ''))
        
        free_match = re.search(r"([\d,]+) frees", output)
        if free_match:
            report["total_frees"] = int(free_match.group(1).replace(',', ''))
        
        return report

    def print_leak_report(self, report: Dict[str, Any]) -> None:
        """Print memory leak report."""
        print("\n" + "=" * 70)
        print("Memory Leak Report")
        print("=" * 70)
        
        print(f"\nTotal allocations: {report.get('total_allocs', 0):,}")
        print(f"Total frees:       {report.get('total_frees', 0):,}")
        
        definitely = report.get('definitely_lost', 0)
        indirectly = report.get('indirectly_lost', 0)
        possibly = report.get('possibly_lost', 0)
        reachable = report.get('still_reachable', 0)
        
        print(f"\nLeak Summary:")
        print(f"  Definitely lost:  {definitely:,} bytes")
        print(f"  Indirectly lost:  {indirectly:,} bytes")
        print(f"  Possibly lost:    {possibly:,} bytes")
        print(f"  Still reachable:  {reachable:,} bytes")
        
        total_leaked = definitely + indirectly + possibly
        
        if total_leaked == 0:
            print(f"\n✓ No memory leaks detected!")
        elif total_leaked < 1000:
            print(f"\n⚠ Minor leaks detected ({total_leaked} bytes)")
        else:
            print(f"\n✗ Significant leaks detected ({total_leaked:,} bytes)")

class PerformanceProfiler:
    """Performance profiling integration."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose

    def check_perf_available(self) -> bool:
        """Check if perf is available (Linux only)."""
        if platform.system() != "Linux":
            return False
        try:
            result = subprocess.run(
                ["perf", "--version"],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def profile_with_perf(self, command: List[str], output: str = "perf.data") -> None:
        """Profile with Linux perf."""
        if not self.check_perf_available():
            print("Error: perf not available (Linux only)")
            return
        
        perf_cmd = ["perf", "record", "-g", "-o", output, "--"] + command
        
        print(f"Running: {' '.join(perf_cmd)}")
        
        try:
            subprocess.run(perf_cmd, check=True)
            print(f"\nProfile data saved to: {output}")
            print(f"\nTo view:")
            print(f"  perf report -i {output}")
            print(f"\nTo generate flamegraph:")
            print(f"  perf script -i {output} | stackcollapse-perf.pl | flamegraph.pl > flamegraph.svg")
        except subprocess.CalledProcessError as e:
            print(f"Error running perf: {e}")

def cmd_stacktrace(args):
    """Handle stacktrace command."""
    debugger = CrossLanguageDebugger(verbose=args.verbose)
    
    if args.core_dump:
        st = debugger.analyze_core_dump(args.core_dump, args.executable)
    elif args.pid:
        st = debugger.capture_live_stacktrace(args.pid)
    else:
        print("Error: Specify --core-dump or --pid")
        return 1
    
    debugger.print_stacktrace(st)
    
    if args.output:
        with open(args.output, 'w') as f:
            json.dump({
                'frames': [asdict(frame) for frame in st.frames],
                'crash_reason': st.crash_reason,
                'signal': st.signal,
            }, f, indent=2)
        print(f"\nStacktrace saved to: {args.output}")
    
    return 0

def cmd_breakpoint(args):
    """Handle breakpoint command."""
    debugger = CrossLanguageDebugger(verbose=args.verbose)
    
    breakpoints = [{
        'function': args.function,
        'condition': args.condition,
        'commands': args.commands.split(';') if args.commands else None,
    }]
    
    output_path = args.output or ".lldbinit"
    debugger.create_lldbinit(output_path, breakpoints)
    
    print(f"\nTo use:")
    print(f"  lldb -- python your_script.py")
    print(f"  (lldb) command source {output_path}")
    
    return 0

def cmd_memleak(args):
    """Handle memory leak detection."""
    detector = MemoryLeakDetector(verbose=args.verbose)
    
    if args.command:
        command = args.command.split()
        report = detector.run_valgrind(command, timeout=args.timeout)
        detector.print_leak_report(report)
    else:
        print("Error: Specify --command")
        return 1
    
    return 0

def cmd_profile(args):
    """Handle profiling command."""
    profiler = PerformanceProfiler(verbose=args.verbose)
    
    if args.command:
        command = args.command.split()
        profiler.profile_with_perf(command, output=args.output or "perf.data")
    else:
        print("Error: Specify --command")
        return 1
    
    return 0

def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="PyO3 Cross-Language Debugging Utilities",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Stacktrace command
    st_parser = subparsers.add_parser("stacktrace", help="Aggregate stack traces")
    st_parser.add_argument("--core-dump", help="Core dump file path")
    st_parser.add_argument("--executable", default="python", help="Executable path")
    st_parser.add_argument("--pid", type=int, help="Process ID")
    st_parser.add_argument("--output", help="Save to JSON file")
    
    # Breakpoint command
    bp_parser = subparsers.add_parser("breakpoint", help="Set coordinated breakpoints")
    bp_parser.add_argument("--function", required=True, help="Function name")
    bp_parser.add_argument("--condition", help="Break condition")
    bp_parser.add_argument("--commands", help="Commands to run (semicolon-separated)")
    bp_parser.add_argument("--output", help="Output lldbinit file path")
    
    # Memory leak command
    ml_parser = subparsers.add_parser("memleak", help="Detect memory leaks")
    ml_parser.add_argument("--command", required=True, help="Command to run")
    ml_parser.add_argument("--timeout", type=int, default=300, help="Timeout in seconds")
    
    # Profile command
    prof_parser = subparsers.add_parser("profile", help="Profile performance")
    prof_parser.add_argument("--command", required=True, help="Command to profile")
    prof_parser.add_argument("--output", help="Output file")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 0
    
    handlers = {
        "stacktrace": cmd_stacktrace,
        "breakpoint": cmd_breakpoint,
        "memleak": cmd_memleak,
        "profile": cmd_profile,
    }
    
    handler = handlers.get(args.command)
    if handler:
        return handler(args)
    
    return 1

if __name__ == "__main__":
    sys.exit(main())
