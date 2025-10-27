#!/usr/bin/env python3
"""
TDD Session Tracker

Interactive tool to track Test-Driven Development sessions, monitoring
the Red-Green-Refactor cycle timing and providing analytics on your
TDD practice.

Features:
- Track Red, Green, Refactor phases with timing
- Session statistics and analytics
- Export session data to JSON
- Visual timeline of TDD cycles
- Identify slow phases and suggest improvements

Usage:
    tdd_session.py start                    # Start interactive session
    tdd_session.py stats --session-file SESSION.json
    tdd_session.py analyze --session-file SESSION.json
    tdd_session.py export --session-file SESSION.json --format json
"""

import argparse
import json
import sys
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import List, Optional


class Phase(Enum):
    """TDD Cycle phases"""
    RED = "red"
    GREEN = "green"
    REFACTOR = "refactor"


@dataclass
class Cycle:
    """Single Red-Green-Refactor cycle"""
    cycle_number: int
    red_start: datetime
    red_end: Optional[datetime] = None
    green_start: Optional[datetime] = None
    green_end: Optional[datetime] = None
    refactor_start: Optional[datetime] = None
    refactor_end: Optional[datetime] = None
    test_name: str = ""
    notes: str = ""

    @property
    def red_duration(self) -> Optional[float]:
        if self.red_end:
            return (self.red_end - self.red_start).total_seconds()
        return None

    @property
    def green_duration(self) -> Optional[float]:
        if self.green_start and self.green_end:
            return (self.green_end - self.green_start).total_seconds()
        return None

    @property
    def refactor_duration(self) -> Optional[float]:
        if self.refactor_start and self.refactor_end:
            return (self.refactor_end - self.refactor_start).total_seconds()
        return None

    @property
    def total_duration(self) -> Optional[float]:
        if self.refactor_end:
            return (self.refactor_end - self.red_start).total_seconds()
        return None

    @property
    def is_complete(self) -> bool:
        return self.refactor_end is not None


@dataclass
class Session:
    """TDD Practice session"""
    start_time: datetime
    end_time: Optional[datetime] = None
    cycles: List[Cycle] = None
    project_name: str = ""
    language: str = ""

    def __post_init__(self):
        if self.cycles is None:
            self.cycles = []

    @property
    def total_duration(self) -> Optional[float]:
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None

    @property
    def completed_cycles(self) -> List[Cycle]:
        return [c for c in self.cycles if c.is_complete]

    @property
    def average_cycle_time(self) -> Optional[float]:
        completed = self.completed_cycles
        if not completed:
            return None
        total = sum(c.total_duration for c in completed)
        return total / len(completed)


class TDDSessionTracker:
    """Track TDD practice sessions"""

    def __init__(self):
        self.session: Optional[Session] = None
        self.current_cycle: Optional[Cycle] = None
        self.current_phase: Optional[Phase] = None

    def start_session(self, project_name: str = "", language: str = ""):
        """Start a new TDD session"""
        self.session = Session(
            start_time=datetime.now(),
            project_name=project_name,
            language=language
        )
        print(f"Session started at {self.session.start_time.strftime('%H:%M:%S')}")
        if project_name:
            print(f"Project: {project_name}")
        if language:
            print(f"Language: {language}")
        print("\nCommands: red, green, refactor, done, skip, stats, help, quit")

    def start_red_phase(self, test_name: str = ""):
        """Start Red phase (write failing test)"""
        if not self.session:
            print("Error: No active session. Start a session first.")
            return

        # Complete previous cycle if exists
        if self.current_cycle and not self.current_cycle.is_complete:
            print("Warning: Previous cycle incomplete. Marking as skipped.")

        cycle_num = len(self.session.cycles) + 1
        self.current_cycle = Cycle(
            cycle_number=cycle_num,
            red_start=datetime.now(),
            test_name=test_name
        )
        self.current_phase = Phase.RED
        self.session.cycles.append(self.current_cycle)

        print(f"\n[Cycle {cycle_num}] RED phase started")
        if test_name:
            print(f"Test: {test_name}")
        print("Write your failing test. Type 'green' when test is written and failing.")

    def start_green_phase(self):
        """Start Green phase (make test pass)"""
        if not self.current_cycle:
            print("Error: No active cycle. Start with 'red' phase.")
            return

        if self.current_phase != Phase.RED:
            print("Error: Must be in RED phase to move to GREEN.")
            return

        self.current_cycle.red_end = datetime.now()
        self.current_cycle.green_start = datetime.now()
        self.current_phase = Phase.GREEN

        red_time = self.current_cycle.red_duration
        print(f"\nGREEN phase started (RED took {red_time:.1f}s)")
        print("Implement code to make test pass. Type 'refactor' when test passes.")

    def start_refactor_phase(self):
        """Start Refactor phase (improve code)"""
        if not self.current_cycle:
            print("Error: No active cycle.")
            return

        if self.current_phase != Phase.GREEN:
            print("Error: Must be in GREEN phase to move to REFACTOR.")
            return

        self.current_cycle.green_end = datetime.now()
        self.current_cycle.refactor_start = datetime.now()
        self.current_phase = Phase.REFACTOR

        green_time = self.current_cycle.green_duration
        print(f"\nREFACTOR phase started (GREEN took {green_time:.1f}s)")
        print("Improve code quality. Type 'done' when refactoring complete.")

    def complete_cycle(self, notes: str = ""):
        """Complete current cycle"""
        if not self.current_cycle:
            print("Error: No active cycle.")
            return

        if self.current_phase != Phase.REFACTOR:
            print("Error: Must be in REFACTOR phase to complete cycle.")
            return

        self.current_cycle.refactor_end = datetime.now()
        if notes:
            self.current_cycle.notes = notes

        # Print cycle summary
        cycle = self.current_cycle
        print(f"\n[Cycle {cycle.cycle_number}] COMPLETE!")
        print(f"  RED:      {cycle.red_duration:.1f}s")
        print(f"  GREEN:    {cycle.green_duration:.1f}s")
        print(f"  REFACTOR: {cycle.refactor_duration:.1f}s")
        print(f"  TOTAL:    {cycle.total_duration:.1f}s")

        # Check if cycle time is good
        total = cycle.total_duration
        if total > 600:  # 10 minutes
            print("  ⚠ Cycle took >10 minutes. Consider smaller steps.")
        elif total < 120:  # 2 minutes
            print("  ✓ Good cycle time!")

        self.current_cycle = None
        self.current_phase = None

    def end_session(self):
        """End the current session"""
        if not self.session:
            print("Error: No active session.")
            return

        self.session.end_time = datetime.now()
        print(f"\nSession ended at {self.session.end_time.strftime('%H:%M:%S')}")
        self.show_stats()

    def show_stats(self):
        """Show session statistics"""
        if not self.session:
            print("No active session.")
            return

        completed = self.session.completed_cycles
        if not completed:
            print("No completed cycles yet.")
            return

        print("\n=== Session Statistics ===")
        print(f"Completed cycles: {len(completed)}")

        # Average times
        avg_red = sum(c.red_duration for c in completed) / len(completed)
        avg_green = sum(c.green_duration for c in completed) / len(completed)
        avg_refactor = sum(c.refactor_duration for c in completed) / len(completed)
        avg_total = sum(c.total_duration for c in completed) / len(completed)

        print(f"\nAverage phase times:")
        print(f"  RED:      {avg_red:.1f}s")
        print(f"  GREEN:    {avg_green:.1f}s")
        print(f"  REFACTOR: {avg_refactor:.1f}s")
        print(f"  TOTAL:    {avg_total:.1f}s")

        # Identify slowest phase
        times = {"RED": avg_red, "GREEN": avg_green, "REFACTOR": avg_refactor}
        slowest = max(times, key=times.get)
        print(f"\nSlowest phase: {slowest}")

        # Total session time
        if self.session.end_time:
            total_time = self.session.total_duration
            print(f"\nTotal session time: {total_time/60:.1f} minutes")

    def save_session(self, filepath: Path):
        """Save session to JSON file"""
        if not self.session:
            print("Error: No active session to save.")
            return

        def serialize(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            if isinstance(obj, Cycle):
                return {
                    'cycle_number': obj.cycle_number,
                    'test_name': obj.test_name,
                    'notes': obj.notes,
                    'red_start': obj.red_start.isoformat(),
                    'red_end': obj.red_end.isoformat() if obj.red_end else None,
                    'green_start': obj.green_start.isoformat() if obj.green_start else None,
                    'green_end': obj.green_end.isoformat() if obj.green_end else None,
                    'refactor_start': obj.refactor_start.isoformat() if obj.refactor_start else None,
                    'refactor_end': obj.refactor_end.isoformat() if obj.refactor_end else None,
                    'red_duration': obj.red_duration,
                    'green_duration': obj.green_duration,
                    'refactor_duration': obj.refactor_duration,
                    'total_duration': obj.total_duration,
                }
            raise TypeError(f"Type {type(obj)} not serializable")

        data = {
            'start_time': self.session.start_time.isoformat(),
            'end_time': self.session.end_time.isoformat() if self.session.end_time else None,
            'project_name': self.session.project_name,
            'language': self.session.language,
            'cycles': [serialize(c) for c in self.session.cycles],
        }

        filepath.write_text(json.dumps(data, indent=2))
        print(f"Session saved to {filepath}")


def load_session(filepath: Path) -> Session:
    """Load session from JSON file"""
    data = json.loads(filepath.read_text())

    cycles = []
    for c in data.get('cycles', []):
        cycle = Cycle(
            cycle_number=c['cycle_number'],
            red_start=datetime.fromisoformat(c['red_start']),
            red_end=datetime.fromisoformat(c['red_end']) if c['red_end'] else None,
            green_start=datetime.fromisoformat(c['green_start']) if c['green_start'] else None,
            green_end=datetime.fromisoformat(c['green_end']) if c['green_end'] else None,
            refactor_start=datetime.fromisoformat(c['refactor_start']) if c['refactor_start'] else None,
            refactor_end=datetime.fromisoformat(c['refactor_end']) if c['refactor_end'] else None,
            test_name=c.get('test_name', ''),
            notes=c.get('notes', ''),
        )
        cycles.append(cycle)

    return Session(
        start_time=datetime.fromisoformat(data['start_time']),
        end_time=datetime.fromisoformat(data['end_time']) if data.get('end_time') else None,
        cycles=cycles,
        project_name=data.get('project_name', ''),
        language=data.get('language', ''),
    )


def analyze_session(session: Session, output_json: bool = False):
    """Analyze session and provide insights"""
    completed = session.completed_cycles
    if not completed:
        print("No completed cycles to analyze.")
        return

    # Calculate statistics
    stats = {
        'total_cycles': len(completed),
        'average_red_time': sum(c.red_duration for c in completed) / len(completed),
        'average_green_time': sum(c.green_duration for c in completed) / len(completed),
        'average_refactor_time': sum(c.refactor_duration for c in completed) / len(completed),
        'average_cycle_time': sum(c.total_duration for c in completed) / len(completed),
        'fastest_cycle': min(c.total_duration for c in completed),
        'slowest_cycle': max(c.total_duration for c in completed),
    }

    if output_json:
        print(json.dumps(stats, indent=2))
        return

    print("\n=== TDD Session Analysis ===")
    print(f"\nTotal completed cycles: {stats['total_cycles']}")
    print(f"\nAverage phase times:")
    print(f"  RED:      {stats['average_red_time']:.1f}s")
    print(f"  GREEN:    {stats['average_green_time']:.1f}s")
    print(f"  REFACTOR: {stats['average_refactor_time']:.1f}s")
    print(f"  TOTAL:    {stats['average_cycle_time']:.1f}s")
    print(f"\nCycle time range: {stats['fastest_cycle']:.1f}s - {stats['slowest_cycle']:.1f}s")

    # Recommendations
    print("\n=== Recommendations ===")

    avg_cycle = stats['average_cycle_time']
    if avg_cycle > 600:
        print("⚠ Average cycle time >10 minutes")
        print("  - Consider breaking tests into smaller steps")
        print("  - Each test should focus on one behavior")

    if stats['average_red_time'] > 120:
        print("⚠ RED phase taking too long")
        print("  - Write simpler tests")
        print("  - Focus on one assertion per test")

    if stats['average_green_time'] > 300:
        print("⚠ GREEN phase taking too long")
        print("  - Implement simpler solutions first")
        print("  - Consider 'fake it' approach")

    if stats['average_refactor_time'] < 30:
        print("⚠ REFACTOR phase very short")
        print("  - Are you refactoring enough?")
        print("  - Look for duplication and improvements")

    # Timeline visualization
    print("\n=== Cycle Timeline ===")
    for cycle in completed[:10]:  # Show first 10
        red_bar = '█' * int(cycle.red_duration / 10)
        green_bar = '█' * int(cycle.green_duration / 10)
        refactor_bar = '█' * int(cycle.refactor_duration / 10)

        print(f"Cycle {cycle.cycle_number:2d}: ", end='')
        print(f"R:{red_bar:10s} G:{green_bar:10s} Ref:{refactor_bar:10s}", end='')
        print(f" ({cycle.total_duration:.0f}s)")


def interactive_session():
    """Run interactive TDD session"""
    tracker = TDDSessionTracker()

    print("=== TDD Session Tracker ===")
    project = input("Project name (optional): ").strip()
    language = input("Language (optional): ").strip()

    tracker.start_session(project, language)

    while True:
        try:
            command = input("\n> ").strip().lower()

            if command == "quit" or command == "q":
                if tracker.session:
                    save = input("Save session? (y/n): ").strip().lower()
                    if save == 'y':
                        filename = f"tdd_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                        tracker.save_session(Path(filename))
                break

            elif command == "red" or command == "r":
                test_name = input("Test name (optional): ").strip()
                tracker.start_red_phase(test_name)

            elif command == "green" or command == "g":
                tracker.start_green_phase()

            elif command == "refactor" or command == "ref":
                tracker.start_refactor_phase()

            elif command == "done" or command == "d":
                notes = input("Notes (optional): ").strip()
                tracker.complete_cycle(notes)

            elif command == "stats" or command == "s":
                tracker.show_stats()

            elif command == "help" or command == "h":
                print("\nCommands:")
                print("  red/r       - Start RED phase (write failing test)")
                print("  green/g     - Start GREEN phase (make test pass)")
                print("  refactor/ref- Start REFACTOR phase (improve code)")
                print("  done/d      - Complete current cycle")
                print("  stats/s     - Show session statistics")
                print("  help/h      - Show this help")
                print("  quit/q      - End session and quit")

            else:
                print(f"Unknown command: {command}. Type 'help' for commands.")

        except KeyboardInterrupt:
            print("\nSession interrupted.")
            break
        except Exception as e:
            print(f"Error: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Track TDD practice sessions and analyze Red-Green-Refactor cycles"
    )
    parser.add_argument(
        "command",
        choices=["start", "stats", "analyze", "export"],
        help="Command to execute"
    )
    parser.add_argument(
        "--session-file",
        type=Path,
        help="Session JSON file"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output in JSON format"
    )

    args = parser.parse_args()

    if args.command == "start":
        interactive_session()

    elif args.command == "stats":
        if not args.session_file:
            print("Error: --session-file required for stats command")
            sys.exit(1)
        session = load_session(args.session_file)
        tracker = TDDSessionTracker()
        tracker.session = session
        tracker.show_stats()

    elif args.command == "analyze":
        if not args.session_file:
            print("Error: --session-file required for analyze command")
            sys.exit(1)
        session = load_session(args.session_file)
        analyze_session(session, output_json=args.json)

    elif args.command == "export":
        if not args.session_file:
            print("Error: --session-file required for export command")
            sys.exit(1)
        session = load_session(args.session_file)
        data = {
            'start_time': session.start_time.isoformat(),
            'end_time': session.end_time.isoformat() if session.end_time else None,
            'project_name': session.project_name,
            'language': session.language,
            'total_cycles': len(session.cycles),
            'completed_cycles': len(session.completed_cycles),
            'cycles': [
                {
                    'cycle_number': c.cycle_number,
                    'test_name': c.test_name,
                    'red_duration': c.red_duration,
                    'green_duration': c.green_duration,
                    'refactor_duration': c.refactor_duration,
                    'total_duration': c.total_duration,
                }
                for c in session.cycles if c.is_complete
            ]
        }
        print(json.dumps(data, indent=2))


if __name__ == "__main__":
    main()
