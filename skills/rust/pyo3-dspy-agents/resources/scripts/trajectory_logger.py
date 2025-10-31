#!/usr/bin/env python3
"""
Trajectory Logger for DSPy ReAct Agents

Log and analyze agent trajectories (observation-thought-action sequences) for debugging.
Provides trajectory logging, analysis, replay, and visualization capabilities.

Usage:
    python trajectory_logger.py log --agent-id agent1 --trajectory traj.json
    python trajectory_logger.py analyze --agent-id agent1
    python trajectory_logger.py replay --trajectory-id traj123
    python trajectory_logger.py visualize --trajectory-id traj123 --output graph.html
    python trajectory_logger.py export --agent-id agent1 --format jsonl
"""

import os
import sys
import json
import time
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from collections import defaultdict
import hashlib


class StepType(str, Enum):
    """Types of trajectory steps."""
    OBSERVATION = "observation"
    THOUGHT = "thought"
    ACTION = "action"
    RESULT = "result"


class TrajectoryStatus(str, Enum):
    """Trajectory completion status."""
    SUCCESS = "success"
    FAILURE = "failure"
    TIMEOUT = "timeout"
    ERROR = "error"
    INCOMPLETE = "incomplete"


@dataclass
class TrajectoryStep:
    """Single step in agent trajectory."""
    step_number: int
    step_type: StepType
    content: str
    timestamp: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    duration_ms: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data['step_type'] = self.step_type.value
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TrajectoryStep':
        """Create from dictionary."""
        data['step_type'] = StepType(data['step_type'])
        return cls(**data)


@dataclass
class Trajectory:
    """Complete agent trajectory."""
    trajectory_id: str
    agent_id: str
    task: str
    steps: List[TrajectoryStep]
    status: TrajectoryStatus
    final_result: Optional[str] = None
    error_message: Optional[str] = None
    total_duration_ms: int = 0
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    completed_at: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.trajectory_id:
            self.trajectory_id = self._generate_id()

    def _generate_id(self) -> str:
        """Generate unique trajectory ID."""
        data = f"{self.agent_id}:{self.task}:{self.created_at}"
        return hashlib.md5(data.encode()).hexdigest()[:12]

    def add_step(
        self,
        step_type: StepType,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        duration_ms: int = 0,
    ):
        """Add step to trajectory."""
        step = TrajectoryStep(
            step_number=len(self.steps) + 1,
            step_type=step_type,
            content=content,
            timestamp=datetime.utcnow().isoformat(),
            metadata=metadata or {},
            duration_ms=duration_ms,
        )
        self.steps.append(step)
        self.total_duration_ms += duration_ms

    def complete(self, status: TrajectoryStatus, result: Optional[str] = None, error: Optional[str] = None):
        """Mark trajectory as complete."""
        self.status = status
        self.final_result = result
        self.error_message = error
        self.completed_at = datetime.utcnow().isoformat()

    def get_step_count_by_type(self) -> Dict[str, int]:
        """Get count of steps by type."""
        counts = defaultdict(int)
        for step in self.steps:
            counts[step.step_type.value] += 1
        return dict(counts)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data['status'] = self.status.value
        data['steps'] = [step.to_dict() for step in self.steps]
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Trajectory':
        """Create from dictionary."""
        steps_data = data.pop('steps', [])
        steps = [TrajectoryStep.from_dict(s) for s in steps_data]
        data['status'] = TrajectoryStatus(data['status'])
        return cls(steps=steps, **data)


@dataclass
class FailurePattern:
    """Common failure pattern."""
    pattern_id: str
    description: str
    occurrences: int
    example_trajectories: List[str]
    common_steps: List[str]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class TrajectoryAnalysis:
    """Trajectory analysis results."""
    agent_id: str
    total_trajectories: int
    successful_trajectories: int
    failed_trajectories: int
    success_rate: float
    average_steps: float
    average_duration_ms: float
    min_steps: int
    max_steps: int
    failure_patterns: List[FailurePattern]
    status_distribution: Dict[str, int]
    step_type_distribution: Dict[str, int]
    generated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data['failure_patterns'] = [fp.to_dict() for fp in self.failure_patterns]
        return data


class TrajectoryStore:
    """Store and retrieve trajectories."""

    def __init__(self, storage_path: Optional[str] = None):
        """Initialize trajectory store.

        Args:
            storage_path: Path to storage directory (default: ./trajectories)
        """
        self.storage_path = Path(storage_path or "./trajectories")
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.index_path = self.storage_path / "index.json"
        self.index: Dict[str, Dict[str, Any]] = {}
        self._load_index()

    def _load_index(self):
        """Load trajectory index."""
        if self.index_path.exists():
            try:
                with open(self.index_path) as f:
                    self.index = json.load(f)
            except Exception as e:
                print(f"Warning: Failed to load index: {e}", file=sys.stderr)
                self.index = {}

    def _save_index(self):
        """Save trajectory index."""
        with open(self.index_path, 'w') as f:
            json.dump(self.index, f, indent=2)

    def save_trajectory(self, trajectory: Trajectory) -> bool:
        """Save trajectory to storage.

        Returns:
            Success status
        """
        try:
            traj_path = self.storage_path / f"{trajectory.trajectory_id}.json"
            with open(traj_path, 'w') as f:
                json.dump(trajectory.to_dict(), f, indent=2)

            # Update index
            self.index[trajectory.trajectory_id] = {
                "agent_id": trajectory.agent_id,
                "task": trajectory.task,
                "status": trajectory.status.value,
                "created_at": trajectory.created_at,
                "step_count": len(trajectory.steps),
            }
            self._save_index()

            return True
        except Exception as e:
            print(f"Error saving trajectory: {e}", file=sys.stderr)
            return False

    def load_trajectory(self, trajectory_id: str) -> Optional[Trajectory]:
        """Load trajectory by ID."""
        traj_path = self.storage_path / f"{trajectory_id}.json"
        if not traj_path.exists():
            return None

        try:
            with open(traj_path) as f:
                data = json.load(f)
            return Trajectory.from_dict(data)
        except Exception as e:
            print(f"Error loading trajectory: {e}", file=sys.stderr)
            return None

    def list_trajectories(
        self,
        agent_id: Optional[str] = None,
        status: Optional[TrajectoryStatus] = None,
        limit: Optional[int] = None,
    ) -> List[str]:
        """List trajectory IDs matching filters."""
        trajectory_ids = []

        for traj_id, info in self.index.items():
            if agent_id and info.get("agent_id") != agent_id:
                continue
            if status and info.get("status") != status.value:
                continue

            trajectory_ids.append(traj_id)

        # Sort by creation time (most recent first)
        trajectory_ids.sort(
            key=lambda tid: self.index[tid].get("created_at", ""),
            reverse=True,
        )

        if limit:
            trajectory_ids = trajectory_ids[:limit]

        return trajectory_ids

    def delete_trajectory(self, trajectory_id: str) -> bool:
        """Delete trajectory."""
        traj_path = self.storage_path / f"{trajectory_id}.json"

        try:
            if traj_path.exists():
                traj_path.unlink()

            if trajectory_id in self.index:
                del self.index[trajectory_id]
                self._save_index()

            return True
        except Exception as e:
            print(f"Error deleting trajectory: {e}", file=sys.stderr)
            return False


class TrajectoryAnalyzer:
    """Analyze agent trajectories."""

    def __init__(self, store: TrajectoryStore):
        """Initialize analyzer with trajectory store."""
        self.store = store

    def analyze_agent(self, agent_id: str) -> Optional[TrajectoryAnalysis]:
        """Analyze all trajectories for an agent."""
        trajectory_ids = self.store.list_trajectories(agent_id=agent_id)

        if not trajectory_ids:
            return None

        trajectories = []
        for traj_id in trajectory_ids:
            traj = self.store.load_trajectory(traj_id)
            if traj:
                trajectories.append(traj)

        if not trajectories:
            return None

        # Calculate statistics
        total = len(trajectories)
        successful = sum(1 for t in trajectories if t.status == TrajectoryStatus.SUCCESS)
        failed = total - successful
        success_rate = (successful / total) * 100 if total > 0 else 0.0

        step_counts = [len(t.steps) for t in trajectories]
        avg_steps = sum(step_counts) / len(step_counts) if step_counts else 0.0
        min_steps = min(step_counts) if step_counts else 0
        max_steps = max(step_counts) if step_counts else 0

        durations = [t.total_duration_ms for t in trajectories]
        avg_duration = sum(durations) / len(durations) if durations else 0.0

        # Status distribution
        status_dist = defaultdict(int)
        for t in trajectories:
            status_dist[t.status.value] += 1

        # Step type distribution
        step_type_dist = defaultdict(int)
        for t in trajectories:
            for step in t.steps:
                step_type_dist[step.step_type.value] += 1

        # Detect failure patterns
        failure_patterns = self._detect_failure_patterns(
            [t for t in trajectories if t.status != TrajectoryStatus.SUCCESS]
        )

        return TrajectoryAnalysis(
            agent_id=agent_id,
            total_trajectories=total,
            successful_trajectories=successful,
            failed_trajectories=failed,
            success_rate=success_rate,
            average_steps=avg_steps,
            average_duration_ms=avg_duration,
            min_steps=min_steps,
            max_steps=max_steps,
            failure_patterns=failure_patterns,
            status_distribution=dict(status_dist),
            step_type_distribution=dict(step_type_dist),
        )

    def _detect_failure_patterns(self, failed_trajectories: List[Trajectory]) -> List[FailurePattern]:
        """Detect common failure patterns."""
        if not failed_trajectories:
            return []

        patterns = []

        # Pattern 1: Timeout failures
        timeout_trajs = [t for t in failed_trajectories if t.status == TrajectoryStatus.TIMEOUT]
        if timeout_trajs:
            patterns.append(FailurePattern(
                pattern_id="timeout",
                description="Trajectories that exceeded maximum iterations or time limit",
                occurrences=len(timeout_trajs),
                example_trajectories=[t.trajectory_id for t in timeout_trajs[:3]],
                common_steps=[],
            ))

        # Pattern 2: Error failures
        error_trajs = [t for t in failed_trajectories if t.status == TrajectoryStatus.ERROR]
        if error_trajs:
            # Group by error message
            error_groups = defaultdict(list)
            for t in error_trajs:
                error_key = (t.error_message or "unknown")[:50]
                error_groups[error_key].append(t)

            for error_msg, trajs in error_groups.items():
                patterns.append(FailurePattern(
                    pattern_id=f"error_{hashlib.md5(error_msg.encode()).hexdigest()[:8]}",
                    description=f"Error: {error_msg}",
                    occurrences=len(trajs),
                    example_trajectories=[t.trajectory_id for t in trajs[:3]],
                    common_steps=[],
                ))

        # Pattern 3: Short trajectories (likely early failures)
        short_trajs = [t for t in failed_trajectories if len(t.steps) < 3]
        if short_trajs:
            patterns.append(FailurePattern(
                pattern_id="early_failure",
                description="Trajectories that failed in the first few steps",
                occurrences=len(short_trajs),
                example_trajectories=[t.trajectory_id for t in short_trajs[:3]],
                common_steps=[],
            ))

        return patterns


class TrajectoryReplayer:
    """Replay trajectories for debugging."""

    def __init__(self, store: TrajectoryStore):
        """Initialize replayer with trajectory store."""
        self.store = store

    def replay(
        self,
        trajectory_id: str,
        step_delay_ms: int = 100,
        verbose: bool = True,
    ) -> bool:
        """Replay trajectory step by step.

        Args:
            trajectory_id: ID of trajectory to replay
            step_delay_ms: Delay between steps in milliseconds
            verbose: Print detailed step information

        Returns:
            Success status
        """
        trajectory = self.store.load_trajectory(trajectory_id)
        if not trajectory:
            print(f"Trajectory '{trajectory_id}' not found")
            return False

        print(f"\n{'='*80}")
        print(f"Replaying Trajectory: {trajectory_id}")
        print(f"Agent: {trajectory.agent_id}")
        print(f"Task: {trajectory.task}")
        print(f"Status: {trajectory.status.value}")
        print(f"Total Steps: {len(trajectory.steps)}")
        print(f"Duration: {trajectory.total_duration_ms}ms")
        print(f"{'='*80}\n")

        for step in trajectory.steps:
            self._replay_step(step, verbose)
            if step_delay_ms > 0:
                time.sleep(step_delay_ms / 1000)

        print(f"\n{'='*80}")
        print(f"Replay Complete")
        if trajectory.final_result:
            print(f"Result: {trajectory.final_result}")
        if trajectory.error_message:
            print(f"Error: {trajectory.error_message}")
        print(f"{'='*80}\n")

        return True

    def _replay_step(self, step: TrajectoryStep, verbose: bool):
        """Replay single step."""
        step_icon = {
            StepType.OBSERVATION: "👁️",
            StepType.THOUGHT: "💭",
            StepType.ACTION: "⚡",
            StepType.RESULT: "✅",
        }.get(step.step_type, "•")

        print(f"{step_icon} Step {step.step_number} [{step.step_type.value.upper()}]")

        if verbose:
            print(f"  Timestamp: {step.timestamp}")
            print(f"  Duration: {step.duration_ms}ms")

        print(f"  Content: {step.content}")

        if verbose and step.metadata:
            print(f"  Metadata: {json.dumps(step.metadata, indent=4)}")

        print()


class TrajectoryVisualizer:
    """Visualize trajectories."""

    def __init__(self, store: TrajectoryStore):
        """Initialize visualizer with trajectory store."""
        self.store = store

    def generate_mermaid(self, trajectory_id: str) -> Optional[str]:
        """Generate Mermaid diagram for trajectory."""
        trajectory = self.store.load_trajectory(trajectory_id)
        if not trajectory:
            return None

        lines = [
            "graph TD",
            f'    Start["Start: {trajectory.task[:40]}..."]',
        ]

        prev_node = "Start"
        for i, step in enumerate(trajectory.steps):
            node_id = f"S{i+1}"
            step_label = step.content[:40].replace('"', "'")

            # Node styling based on step type
            if step.step_type == StepType.OBSERVATION:
                node_shape = f'{node_id}["{step_label}"]'
                style = f"    style {node_id} fill:#e3f2fd"
            elif step.step_type == StepType.THOUGHT:
                node_shape = f'{node_id}{"{" + step_label + "}"}'
                style = f"    style {node_id} fill:#fff3e0"
            elif step.step_type == StepType.ACTION:
                node_shape = f'{node_id}["{step_label}"]'
                style = f"    style {node_id} fill:#f3e5f5"
            else:
                node_shape = f'{node_id}["{step_label}"]'
                style = f"    style {node_id} fill:#e8f5e9"

            lines.append(f"    {node_shape}")
            lines.append(f"    {prev_node} --> {node_id}")
            lines.append(style)

            prev_node = node_id

        # End node
        if trajectory.status == TrajectoryStatus.SUCCESS:
            lines.append(f'    End["✓ Success"]')
            lines.append(f"    style End fill:#c8e6c9")
        else:
            lines.append(f'    End["✗ {trajectory.status.value}"]')
            lines.append(f"    style End fill:#ffcdd2")

        lines.append(f"    {prev_node} --> End")

        return "\n".join(lines)

    def generate_html(self, trajectory_id: str, output_path: str) -> bool:
        """Generate HTML visualization for trajectory."""
        mermaid = self.generate_mermaid(trajectory_id)
        if not mermaid:
            return False

        trajectory = self.store.load_trajectory(trajectory_id)
        if not trajectory:
            return False

        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Trajectory: {trajectory_id}</title>
    <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            margin: 20px;
            background: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h1 {{ color: #333; }}
        .metadata {{
            background: #f9f9f9;
            padding: 15px;
            border-radius: 4px;
            margin: 20px 0;
        }}
        .metadata div {{ margin: 5px 0; }}
        .mermaid {{ margin: 20px 0; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Trajectory Visualization</h1>
        <div class="metadata">
            <div><strong>Trajectory ID:</strong> {trajectory_id}</div>
            <div><strong>Agent:</strong> {trajectory.agent_id}</div>
            <div><strong>Task:</strong> {trajectory.task}</div>
            <div><strong>Status:</strong> {trajectory.status.value}</div>
            <div><strong>Steps:</strong> {len(trajectory.steps)}</div>
            <div><strong>Duration:</strong> {trajectory.total_duration_ms}ms</div>
            <div><strong>Created:</strong> {trajectory.created_at}</div>
        </div>
        <div class="mermaid">
{mermaid}
        </div>
    </div>
    <script>
        mermaid.initialize({{ startOnLoad: true, theme: 'default' }});
    </script>
</body>
</html>"""

        try:
            with open(output_path, 'w') as f:
                f.write(html)
            return True
        except Exception as e:
            print(f"Error writing HTML: {e}", file=sys.stderr)
            return False


# CLI Commands

def cmd_log(args, store: TrajectoryStore):
    """Log a trajectory from file."""
    try:
        with open(args.trajectory) as f:
            data = json.load(f)

        trajectory = Trajectory.from_dict(data)

        if args.agent_id:
            trajectory.agent_id = args.agent_id

        success = store.save_trajectory(trajectory)

        if success:
            print(f"✓ Trajectory '{trajectory.trajectory_id}' logged successfully")
            print(f"  Agent: {trajectory.agent_id}")
            print(f"  Steps: {len(trajectory.steps)}")
            print(f"  Status: {trajectory.status.value}")
        else:
            print("✗ Failed to log trajectory")
            sys.exit(1)

    except Exception as e:
        print(f"✗ Error logging trajectory: {e}")
        sys.exit(1)


def cmd_analyze(args, store: TrajectoryStore):
    """Analyze trajectories for an agent."""
    analyzer = TrajectoryAnalyzer(store)
    analysis = analyzer.analyze_agent(args.agent_id)

    if not analysis:
        print(f"No trajectories found for agent '{args.agent_id}'")
        sys.exit(1)

    print(f"\n{'='*80}")
    print(f"Trajectory Analysis: {args.agent_id}")
    print(f"{'='*80}\n")

    print(f"Total Trajectories: {analysis.total_trajectories}")
    print(f"Successful: {analysis.successful_trajectories}")
    print(f"Failed: {analysis.failed_trajectories}")
    print(f"Success Rate: {analysis.success_rate:.1f}%\n")

    print(f"Average Steps: {analysis.average_steps:.1f}")
    print(f"Min Steps: {analysis.min_steps}")
    print(f"Max Steps: {analysis.max_steps}\n")

    print(f"Average Duration: {analysis.average_duration_ms:.0f}ms\n")

    print("Status Distribution:")
    for status, count in sorted(analysis.status_distribution.items()):
        print(f"  {status}: {count}")

    print("\nStep Type Distribution:")
    for step_type, count in sorted(analysis.step_type_distribution.items()):
        print(f"  {step_type}: {count}")

    if analysis.failure_patterns:
        print(f"\nFailure Patterns ({len(analysis.failure_patterns)}):")
        for pattern in analysis.failure_patterns:
            print(f"\n  {pattern.pattern_id} ({pattern.occurrences} occurrences)")
            print(f"  {pattern.description}")
            if pattern.example_trajectories:
                print(f"  Examples: {', '.join(pattern.example_trajectories[:3])}")

    print(f"\n{'='*80}\n")

    if args.output:
        try:
            with open(args.output, 'w') as f:
                json.dump(analysis.to_dict(), f, indent=2)
            print(f"✓ Analysis saved to {args.output}")
        except Exception as e:
            print(f"✗ Error saving analysis: {e}")


def cmd_replay(args, store: TrajectoryStore):
    """Replay a trajectory."""
    replayer = TrajectoryReplayer(store)
    success = replayer.replay(
        args.trajectory_id,
        step_delay_ms=args.delay,
        verbose=args.verbose,
    )

    if not success:
        sys.exit(1)


def cmd_visualize(args, store: TrajectoryStore):
    """Visualize a trajectory."""
    visualizer = TrajectoryVisualizer(store)

    if args.output:
        success = visualizer.generate_html(args.trajectory_id, args.output)
        if success:
            print(f"✓ Visualization saved to {args.output}")
        else:
            print(f"✗ Failed to generate visualization")
            sys.exit(1)
    else:
        mermaid = visualizer.generate_mermaid(args.trajectory_id)
        if mermaid:
            print(mermaid)
        else:
            print(f"✗ Trajectory '{args.trajectory_id}' not found")
            sys.exit(1)


def cmd_export(args, store: TrajectoryStore):
    """Export trajectories."""
    trajectory_ids = store.list_trajectories(
        agent_id=args.agent_id,
        limit=args.limit,
    )

    if not trajectory_ids:
        print("No trajectories found")
        sys.exit(1)

    trajectories = []
    for traj_id in trajectory_ids:
        traj = store.load_trajectory(traj_id)
        if traj:
            trajectories.append(traj)

    if args.format == "jsonl":
        output = "\n".join(json.dumps(t.to_dict()) for t in trajectories)
    elif args.format == "json":
        output = json.dumps([t.to_dict() for t in trajectories], indent=2)
    else:
        print(f"✗ Unsupported format: {args.format}")
        sys.exit(1)

    if args.output:
        try:
            with open(args.output, 'w') as f:
                f.write(output)
            print(f"✓ Exported {len(trajectories)} trajectories to {args.output}")
        except Exception as e:
            print(f"✗ Error writing export: {e}")
            sys.exit(1)
    else:
        print(output)


def cmd_list(args, store: TrajectoryStore):
    """List trajectories."""
    status = TrajectoryStatus(args.status) if args.status else None

    trajectory_ids = store.list_trajectories(
        agent_id=args.agent_id,
        status=status,
        limit=args.limit,
    )

    if not trajectory_ids:
        print("No trajectories found")
        return

    print(f"\nTrajectories ({len(trajectory_ids)}):\n")
    print("=" * 80)

    for traj_id in trajectory_ids:
        info = store.index.get(traj_id, {})
        print(f"\n{traj_id}")
        print(f"  Agent: {info.get('agent_id', 'unknown')}")
        print(f"  Task: {info.get('task', 'unknown')[:60]}")
        print(f"  Status: {info.get('status', 'unknown')}")
        print(f"  Steps: {info.get('step_count', 0)}")
        print(f"  Created: {info.get('created_at', 'unknown')}")

    print("\n" + "=" * 80 + "\n")


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Trajectory Logger for DSPy ReAct Agents"
    )
    parser.add_argument(
        '--storage',
        default='./trajectories',
        help='Path to trajectory storage directory (default: ./trajectories)'
    )

    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # Log command
    parser_log = subparsers.add_parser('log', help='Log a trajectory from file')
    parser_log.add_argument('--agent-id', help='Override agent ID')
    parser_log.add_argument('--trajectory', required=True, help='Path to trajectory JSON file')

    # Analyze command
    parser_analyze = subparsers.add_parser('analyze', help='Analyze trajectories for an agent')
    parser_analyze.add_argument('--agent-id', required=True, help='Agent ID to analyze')
    parser_analyze.add_argument('--output', '-o', help='Save analysis to file')

    # Replay command
    parser_replay = subparsers.add_parser('replay', help='Replay a trajectory')
    parser_replay.add_argument('--trajectory-id', required=True, help='Trajectory ID to replay')
    parser_replay.add_argument('--delay', type=int, default=100, help='Delay between steps in ms (default: 100)')
    parser_replay.add_argument('--verbose', '-v', action='store_true', help='Show detailed step information')

    # Visualize command
    parser_vis = subparsers.add_parser('visualize', help='Visualize a trajectory')
    parser_vis.add_argument('--trajectory-id', required=True, help='Trajectory ID to visualize')
    parser_vis.add_argument('--output', '-o', help='Output HTML file (default: print Mermaid to stdout)')

    # Export command
    parser_export = subparsers.add_parser('export', help='Export trajectories')
    parser_export.add_argument('--agent-id', help='Filter by agent ID')
    parser_export.add_argument('--format', choices=['json', 'jsonl'], default='jsonl',
                               help='Export format (default: jsonl)')
    parser_export.add_argument('--limit', type=int, help='Limit number of trajectories')
    parser_export.add_argument('--output', '-o', help='Output file (default: stdout)')

    # List command
    parser_list = subparsers.add_parser('list', help='List trajectories')
    parser_list.add_argument('--agent-id', help='Filter by agent ID')
    parser_list.add_argument('--status', help='Filter by status')
    parser_list.add_argument('--limit', type=int, help='Limit number of results')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Initialize store
    store = TrajectoryStore(args.storage)

    # Execute command
    if args.command == 'log':
        cmd_log(args, store)
    elif args.command == 'analyze':
        cmd_analyze(args, store)
    elif args.command == 'replay':
        cmd_replay(args, store)
    elif args.command == 'visualize':
        cmd_visualize(args, store)
    elif args.command == 'export':
        cmd_export(args, store)
    elif args.command == 'list':
        cmd_list(args, store)


if __name__ == "__main__":
    main()
