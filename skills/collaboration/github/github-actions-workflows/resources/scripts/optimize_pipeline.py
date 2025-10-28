#!/usr/bin/env python3
"""
GitHub Actions Pipeline Optimizer

Analyzes GitHub Actions workflows and suggests optimizations for:
- Parallelization opportunities
- Caching improvements
- Matrix build strategies
- Cost optimization
- Performance enhancements

Usage:
    ./optimize_pipeline.py .github/workflows/ci.yml
    ./optimize_pipeline.py workflow.yml --json
    ./optimize_pipeline.py . --all --suggestions
"""

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

try:
    import yaml
except ImportError:
    print("Error: PyYAML is required. Install with: pip install pyyaml", file=sys.stderr)
    sys.exit(1)


@dataclass
class Optimization:
    """Represents an optimization suggestion."""
    category: str  # parallelization, caching, matrix, cost, performance
    priority: str  # high, medium, low
    title: str
    description: str
    impact: str
    implementation: Optional[str] = None
    estimated_savings: Optional[str] = None


@dataclass
class PipelineAnalysis:
    """Analysis results for a workflow."""
    file: str
    workflow_name: str
    total_jobs: int
    parallel_jobs: int
    sequential_jobs: int
    has_caching: bool
    has_matrix: bool
    has_concurrency: bool
    estimated_runtime: Optional[int] = None  # minutes
    runner_os_count: Dict[str, int] = field(default_factory=dict)
    optimizations: List[Optimization] = field(default_factory=list)


class PipelineOptimizer:
    """Analyzes and optimizes GitHub Actions pipelines."""

    def __init__(self):
        self.cacheable_actions = {
            'actions/setup-node': {'cache_param': 'cache', 'cache_values': ['npm', 'yarn', 'pnpm']},
            'actions/setup-python': {'cache_param': 'cache', 'cache_values': ['pip', 'pipenv', 'poetry']},
            'actions/setup-go': {'cache_param': 'cache', 'cache_values': [True]},
            'actions/setup-java': {'cache_param': 'cache', 'cache_values': ['maven', 'gradle', 'sbt']},
        }

        self.runner_costs = {
            'ubuntu-latest': 1,
            'ubuntu-20.04': 1,
            'ubuntu-22.04': 1,
            'windows-latest': 2,
            'windows-2019': 2,
            'windows-2022': 2,
            'macos-latest': 10,
            'macos-12': 10,
            'macos-13': 10,
            'macos-14': 10,
        }

    def analyze_workflow(self, filepath: Path) -> PipelineAnalysis:
        """Analyze a workflow file for optimization opportunities."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                workflow = yaml.safe_load(f)
        except Exception as e:
            print(f"Error reading workflow: {e}", file=sys.stderr)
            return None

        if not workflow or 'jobs' not in workflow:
            return None

        analysis = PipelineAnalysis(
            file=str(filepath),
            workflow_name=workflow.get('name', 'Unnamed Workflow'),
            total_jobs=len(workflow['jobs']),
            parallel_jobs=0,
            sequential_jobs=0,
            has_caching=False,
            has_matrix=False,
            has_concurrency='concurrency' in workflow
        )

        # Analyze job structure
        self._analyze_job_structure(workflow, analysis)

        # Analyze caching
        self._analyze_caching(workflow, analysis)

        # Analyze matrix opportunities
        self._analyze_matrix_opportunities(workflow, analysis)

        # Analyze runner usage
        self._analyze_runner_usage(workflow, analysis)

        # Generate optimizations
        self._generate_parallelization_optimizations(workflow, analysis)
        self._generate_caching_optimizations(workflow, analysis)
        self._generate_matrix_optimizations(workflow, analysis)
        self._generate_cost_optimizations(workflow, analysis)
        self._generate_performance_optimizations(workflow, analysis)

        # Sort optimizations by priority
        priority_order = {'high': 0, 'medium': 1, 'low': 2}
        analysis.optimizations.sort(key=lambda x: priority_order[x.priority])

        return analysis

    def _analyze_job_structure(self, workflow: Dict, analysis: PipelineAnalysis):
        """Analyze job dependencies and parallelization."""
        jobs = workflow['jobs']
        job_deps = {}

        for job_name, job in jobs.items():
            needs = job.get('needs', [])
            if isinstance(needs, str):
                needs = [needs]
            job_deps[job_name] = needs

        # Count parallel vs sequential
        for job_name, deps in job_deps.items():
            if deps:
                analysis.sequential_jobs += 1
            else:
                analysis.parallel_jobs += 1

    def _analyze_caching(self, workflow: Dict, analysis: PipelineAnalysis):
        """Analyze caching usage."""
        for job_name, job in workflow['jobs'].items():
            steps = job.get('steps', [])
            for step in steps:
                if not isinstance(step, dict):
                    continue

                uses = step.get('uses', '')

                if 'actions/cache' in uses:
                    analysis.has_caching = True
                    return

                # Check for cache parameters in setup actions
                for action, config in self.cacheable_actions.items():
                    if action in uses:
                        cache_value = step.get('with', {}).get(config['cache_param'])
                        if cache_value in config['cache_values']:
                            analysis.has_caching = True
                            return

    def _analyze_matrix_opportunities(self, workflow: Dict, analysis: PipelineAnalysis):
        """Analyze matrix build usage."""
        for job_name, job in workflow['jobs'].items():
            if 'strategy' in job and 'matrix' in job['strategy']:
                analysis.has_matrix = True
                return

    def _analyze_runner_usage(self, workflow: Dict, analysis: PipelineAnalysis):
        """Analyze runner OS usage."""
        for job_name, job in workflow['jobs'].items():
            runs_on = job.get('runs-on', 'ubuntu-latest')

            if isinstance(runs_on, str):
                runner = runs_on
            elif isinstance(runs_on, list):
                runner = 'self-hosted'
            else:
                runner = 'unknown'

            analysis.runner_os_count[runner] = analysis.runner_os_count.get(runner, 0) + 1

    def _generate_parallelization_optimizations(self, workflow: Dict, analysis: PipelineAnalysis):
        """Generate parallelization optimization suggestions."""
        jobs = workflow['jobs']

        # Find sequential jobs that could be parallelized
        sequential_chains = self._find_sequential_chains(jobs)

        for chain in sequential_chains:
            if len(chain) >= 3:
                analysis.optimizations.append(Optimization(
                    category='parallelization',
                    priority='high',
                    title='Optimize Sequential Job Chain',
                    description=f'Jobs {" → ".join(chain)} are sequential. Consider parallelizing independent jobs.',
                    impact='Could reduce workflow runtime by 30-50%',
                    implementation=f"""
# Current (sequential):
jobs:
  {chain[0]}:
    steps: [...]
  {chain[1]}:
    needs: {chain[0]}
    steps: [...]

# Optimized (parallel):
jobs:
  {chain[0]}:
    steps: [...]
  {chain[1]}:
    steps: [...]  # Remove needs if independent
  final:
    needs: [{chain[0]}, {chain[1]}]
    steps: [...]
""",
                    estimated_savings='15-30 minutes per run'
                ))

        # Check for artifact rebuilding
        self._check_artifact_rebuilding(workflow, analysis)

    def _find_sequential_chains(self, jobs: Dict) -> List[List[str]]:
        """Find chains of sequential jobs."""
        chains = []
        visited = set()

        for job_name in jobs:
            if job_name in visited:
                continue

            chain = [job_name]
            current = job_name

            # Follow the chain forward
            while True:
                next_jobs = [
                    name for name, job in jobs.items()
                    if job.get('needs') == current
                ]

                if len(next_jobs) == 1:
                    next_job = next_jobs[0]
                    chain.append(next_job)
                    visited.add(next_job)
                    current = next_job
                else:
                    break

            if len(chain) > 1:
                chains.append(chain)

        return chains

    def _check_artifact_rebuilding(self, workflow: Dict, analysis: PipelineAnalysis):
        """Check for jobs that rebuild the same artifacts."""
        jobs = workflow['jobs']
        build_commands = {}

        for job_name, job in jobs.items():
            steps = job.get('steps', [])
            for step in steps:
                if not isinstance(step, dict) or 'run' not in step:
                    continue

                run_cmd = step['run']
                if any(cmd in run_cmd for cmd in ['npm run build', 'yarn build', 'cargo build', 'go build']):
                    if run_cmd not in build_commands:
                        build_commands[run_cmd] = []
                    build_commands[run_cmd].append(job_name)

        for cmd, job_names in build_commands.items():
            if len(job_names) > 1:
                analysis.optimizations.append(Optimization(
                    category='parallelization',
                    priority='high',
                    title='Eliminate Duplicate Builds',
                    description=f'Build command "{cmd[:50]}..." is executed in multiple jobs: {", ".join(job_names)}',
                    impact='Reduces build time and runner usage',
                    implementation="""
# Create a dedicated build job:
jobs:
  build:
    steps:
      - run: npm run build
      - uses: actions/upload-artifact@v4
        with:
          name: dist
          path: dist/

  test:
    needs: build
    steps:
      - uses: actions/download-artifact@v4
      - run: npm test
""",
                    estimated_savings='10-20 minutes per run'
                ))

    def _generate_caching_optimizations(self, workflow: Dict, analysis: PipelineAnalysis):
        """Generate caching optimization suggestions."""
        for job_name, job in workflow['jobs'].items():
            steps = job.get('steps', [])

            # Check for setup actions without caching
            missing_cache = []
            for step in steps:
                if not isinstance(step, dict) or 'uses' not in step:
                    continue

                uses = step['uses']

                for action, config in self.cacheable_actions.items():
                    if action in uses:
                        cache_value = step.get('with', {}).get(config['cache_param'])
                        if not cache_value:
                            missing_cache.append((action, job_name))

            for action, job in missing_cache:
                action_name = action.split('/')[-1]
                cache_examples = self.cacheable_actions[action]['cache_values']
                cache_value = cache_examples[0]

                analysis.optimizations.append(Optimization(
                    category='caching',
                    priority='high',
                    title=f'Enable Caching for {action_name}',
                    description=f'Job "{job}" uses {action} without caching',
                    impact='Can reduce dependency installation time by 50-90%',
                    implementation=f"""
- uses: {action}
  with:
    cache: '{cache_value}'
""",
                    estimated_savings='2-10 minutes per run'
                ))

        # Check for Docker layer caching
        if not analysis.has_caching:
            for job_name, job in workflow['jobs'].items():
                steps = job.get('steps', [])
                for step in steps:
                    if isinstance(step, dict) and 'docker/build-push-action' in step.get('uses', ''):
                        analysis.optimizations.append(Optimization(
                            category='caching',
                            priority='medium',
                            title='Enable Docker Layer Caching',
                            description=f'Job "{job_name}" builds Docker images without layer caching',
                            impact='Can reduce Docker build time by 60-80%',
                            implementation="""
- uses: docker/build-push-action@v5
  with:
    cache-from: type=gha
    cache-to: type=gha,mode=max
""",
                            estimated_savings='5-15 minutes per run'
                        ))

    def _generate_matrix_optimizations(self, workflow: Dict, analysis: PipelineAnalysis):
        """Generate matrix build optimization suggestions."""
        jobs = workflow['jobs']

        # Look for duplicate job patterns
        similar_jobs = self._find_similar_jobs(jobs)

        for job_group in similar_jobs:
            if len(job_group) >= 2:
                analysis.optimizations.append(Optimization(
                    category='matrix',
                    priority='medium',
                    title='Use Matrix Build',
                    description=f'Jobs {", ".join(job_group)} have similar structure and could use a matrix build',
                    impact='Reduces workflow complexity and maintenance',
                    implementation=f"""
# Instead of separate jobs:
jobs:
  test-node-18:
    runs-on: ubuntu-latest
    steps: [...]

  test-node-20:
    runs-on: ubuntu-latest
    steps: [...]

# Use matrix:
jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        node: [18, 20]
    steps:
      - uses: actions/setup-node@v4
        with:
          node-version: ${{{{ matrix.node }}}}
"""
                ))

    def _find_similar_jobs(self, jobs: Dict) -> List[List[str]]:
        """Find groups of jobs with similar names."""
        job_groups = {}

        for job_name in jobs:
            # Extract base name (remove version numbers, suffixes)
            base_name = job_name.rstrip('0123456789-')

            if base_name not in job_groups:
                job_groups[base_name] = []
            job_groups[base_name].append(job_name)

        return [group for group in job_groups.values() if len(group) >= 2]

    def _generate_cost_optimizations(self, workflow: Dict, analysis: PipelineAnalysis):
        """Generate cost optimization suggestions."""
        # Check for expensive runners
        for runner, count in analysis.runner_os_count.items():
            cost_multiplier = self.runner_costs.get(runner, 1)

            if cost_multiplier >= 10:  # macOS
                analysis.optimizations.append(Optimization(
                    category='cost',
                    priority='high',
                    title='Optimize macOS Runner Usage',
                    description=f'{count} job(s) use macOS runners which cost 10x more than Linux',
                    impact='Could reduce costs by 80-90% for affected jobs',
                    implementation="""
# Use Linux for CI, macOS only for macOS-specific testing:
strategy:
  matrix:
    os: [ubuntu-latest]  # Default to Linux
    include:
      - os: macos-latest  # Only when needed
        if: github.ref == 'refs/heads/main'
""",
                    estimated_savings='$50-200 per month'
                ))

            elif cost_multiplier == 2:  # Windows
                analysis.optimizations.append(Optimization(
                    category='cost',
                    priority='medium',
                    title='Optimize Windows Runner Usage',
                    description=f'{count} job(s) use Windows runners which cost 2x more than Linux',
                    impact='Could reduce costs by 50% for affected jobs',
                    implementation="""
# Use Linux when possible:
runs-on: ubuntu-latest  # Instead of windows-latest
""",
                    estimated_savings='$20-80 per month'
                ))

        # Check for concurrency control
        if not analysis.has_concurrency:
            analysis.optimizations.append(Optimization(
                category='cost',
                priority='medium',
                title='Add Concurrency Control',
                description='Workflow has no concurrency control, wasting runner minutes on outdated runs',
                impact='Reduces wasted runner minutes by 20-40%',
                implementation="""
concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true
""",
                estimated_savings='$10-50 per month'
            ))

    def _generate_performance_optimizations(self, workflow: Dict, analysis: PipelineAnalysis):
        """Generate performance optimization suggestions."""
        # Check for path filters
        triggers = workflow.get('on', {})
        if isinstance(triggers, dict):
            for trigger in ['push', 'pull_request']:
                if trigger in triggers:
                    trigger_config = triggers[trigger]
                    if isinstance(trigger_config, dict) and 'paths' not in trigger_config:
                        analysis.optimizations.append(Optimization(
                            category='performance',
                            priority='low',
                            title='Add Path Filters',
                            description=f'No path filters on {trigger} trigger',
                            impact='Prevents unnecessary workflow runs',
                            implementation=f"""
on:
  {trigger}:
    paths:
      - 'src/**'
      - 'tests/**'
      - '!docs/**'
""",
                            estimated_savings='10-30% fewer runs'
                        ))

        # Check for shallow checkouts
        for job_name, job in workflow['jobs'].items():
            steps = job.get('steps', [])
            for step in steps:
                if isinstance(step, dict) and 'actions/checkout' in step.get('uses', ''):
                    fetch_depth = step.get('with', {}).get('fetch-depth')
                    if fetch_depth is None or fetch_depth != 1:
                        analysis.optimizations.append(Optimization(
                            category='performance',
                            priority='low',
                            title='Use Shallow Checkout',
                            description=f'Job "{job_name}" does not use shallow git checkout',
                            impact='Reduces checkout time for large repositories',
                            implementation="""
- uses: actions/checkout@v4
  with:
    fetch-depth: 1  # Shallow clone
""",
                            estimated_savings='30 seconds - 2 minutes per run'
                        ))

    def print_analysis(self, analysis: PipelineAnalysis, show_implementation: bool = True):
        """Print analysis results in human-readable format."""
        print(f"\n{'=' * 80}")
        print(f"Pipeline Analysis: {analysis.workflow_name}")
        print(f"File: {analysis.file}")
        print(f"{'=' * 80}\n")

        print("Overview:")
        print(f"  Total jobs: {analysis.total_jobs}")
        print(f"  Parallel jobs: {analysis.parallel_jobs}")
        print(f"  Sequential jobs: {analysis.sequential_jobs}")
        print(f"  Has caching: {'Yes' if analysis.has_caching else 'No'}")
        print(f"  Has matrix builds: {'Yes' if analysis.has_matrix else 'No'}")
        print(f"  Has concurrency control: {'Yes' if analysis.has_concurrency else 'No'}")

        if analysis.runner_os_count:
            print(f"\n  Runner usage:")
            for runner, count in analysis.runner_os_count.items():
                cost_mult = self.runner_costs.get(runner, 1)
                print(f"    {runner}: {count} job(s) (cost multiplier: {cost_mult}x)")

        if not analysis.optimizations:
            print("\n✓ No optimization opportunities found. Workflow is well-optimized!")
            return

        print(f"\nOptimizations ({len(analysis.optimizations)}):\n")

        for i, opt in enumerate(analysis.optimizations, 1):
            priority_icon = {
                'high': '🔴',
                'medium': '🟡',
                'low': '🟢'
            }[opt.priority]

            print(f"{i}. {priority_icon} [{opt.priority.upper()}] {opt.category.upper()}: {opt.title}")
            print(f"   {opt.description}")
            print(f"   Impact: {opt.impact}")

            if opt.estimated_savings:
                print(f"   Estimated savings: {opt.estimated_savings}")

            if show_implementation and opt.implementation:
                print(f"   Implementation:")
                for line in opt.implementation.strip().split('\n'):
                    print(f"   {line}")

            print()

    def export_json(self, analysis: PipelineAnalysis) -> str:
        """Export analysis as JSON."""
        output = {
            'file': analysis.file,
            'workflow_name': analysis.workflow_name,
            'overview': {
                'total_jobs': analysis.total_jobs,
                'parallel_jobs': analysis.parallel_jobs,
                'sequential_jobs': analysis.sequential_jobs,
                'has_caching': analysis.has_caching,
                'has_matrix': analysis.has_matrix,
                'has_concurrency': analysis.has_concurrency,
                'runner_usage': analysis.runner_os_count
            },
            'optimizations': [
                {
                    'category': opt.category,
                    'priority': opt.priority,
                    'title': opt.title,
                    'description': opt.description,
                    'impact': opt.impact,
                    'implementation': opt.implementation,
                    'estimated_savings': opt.estimated_savings
                }
                for opt in analysis.optimizations
            ],
            'optimization_count': len(analysis.optimizations)
        }

        return json.dumps(output, indent=2)


def main():
    parser = argparse.ArgumentParser(
        description='Analyze and optimize GitHub Actions pipelines',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Analyze single workflow:
    %(prog)s .github/workflows/ci.yml

  Analyze with JSON output:
    %(prog)s workflow.yml --json

  Show optimization suggestions:
    %(prog)s workflow.yml --suggestions
        """
    )

    parser.add_argument(
        'workflow_file',
        help='Path to workflow file'
    )

    parser.add_argument(
        '--json',
        action='store_true',
        help='Output results as JSON'
    )

    parser.add_argument(
        '--suggestions',
        action='store_true',
        default=True,
        help='Show implementation suggestions (default: true)'
    )

    parser.add_argument(
        '--no-implementation',
        action='store_true',
        help='Hide implementation details'
    )

    args = parser.parse_args()

    workflow_path = Path(args.workflow_file)

    if not workflow_path.exists():
        print(f"Error: Workflow file not found: {workflow_path}", file=sys.stderr)
        sys.exit(1)

    optimizer = PipelineOptimizer()
    analysis = optimizer.analyze_workflow(workflow_path)

    if not analysis:
        print("Error: Unable to analyze workflow", file=sys.stderr)
        sys.exit(1)

    if args.json:
        print(optimizer.export_json(analysis))
    else:
        show_impl = args.suggestions and not args.no_implementation
        optimizer.print_analysis(analysis, show_impl)


if __name__ == '__main__':
    main()
