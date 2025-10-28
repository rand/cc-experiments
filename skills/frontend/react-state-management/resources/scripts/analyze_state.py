#!/usr/bin/env python3
"""
Analyze React component state management patterns and identify issues.

This script analyzes React/TypeScript components to:
- Detect state management approaches (useState, useReducer, Context, etc.)
- Identify prop drilling issues
- Find stale closure risks
- Detect unnecessary derived state
- Suggest optimization opportunities
- Report state complexity metrics
"""

import argparse
import json
import os
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Set, Optional, Tuple


@dataclass
class StateUsage:
    """Represents a state hook usage."""
    hook_type: str  # useState, useReducer, useContext, etc.
    variable_name: str
    line_number: int
    initial_value: Optional[str] = None


@dataclass
class PropDrilling:
    """Represents detected prop drilling."""
    prop_name: str
    depth: int
    components: List[str]


@dataclass
class ComponentAnalysis:
    """Analysis results for a single component."""
    file_path: str
    component_name: str
    line_count: int
    state_hooks: List[StateUsage] = field(default_factory=list)
    effects: int = 0
    memos: int = 0
    callbacks: int = 0
    contexts: Set[str] = field(default_factory=set)
    prop_count: int = 0
    issues: List[Dict] = field(default_factory=list)


@dataclass
class AnalysisResult:
    """Complete analysis results."""
    components: List[ComponentAnalysis]
    total_files: int
    total_components: int
    state_distribution: Dict[str, int]
    issues_by_severity: Dict[str, int]
    suggestions: List[str]


class ReactStateAnalyzer:
    """Analyze React component state management."""

    def __init__(self, directory: str, extensions: List[str] = None):
        self.directory = Path(directory)
        self.extensions = extensions or ['.tsx', '.ts', '.jsx', '.js']

        # Patterns for detection
        self.state_hooks = {
            'useState': re.compile(r'const\s+\[(\w+),\s*\w+\]\s*=\s*useState(?:<[^>]+>)?\((.*?)\)', re.MULTILINE),
            'useReducer': re.compile(r'const\s+\[(\w+),\s*\w+\]\s*=\s*useReducer\('),
            'useContext': re.compile(r'const\s+(\w+)\s*=\s*useContext\((\w+)\)'),
        }

        self.hook_patterns = {
            'useEffect': re.compile(r'useEffect\('),
            'useMemo': re.compile(r'useMemo\('),
            'useCallback': re.compile(r'useCallback\('),
        }

        self.component_pattern = re.compile(
            r'(?:export\s+)?(?:default\s+)?(?:const|function)\s+(\w+)\s*(?:=\s*(?:\([^)]*\)|[^=]+)\s*=>|\\([^)]*\\))',
            re.MULTILINE
        )

    def analyze(self) -> AnalysisResult:
        """Analyze all React files in directory."""
        components = []

        for file_path in self._find_react_files():
            try:
                content = file_path.read_text(encoding='utf-8')
                file_components = self._analyze_file(str(file_path), content)
                components.extend(file_components)
            except Exception as e:
                print(f"Error analyzing {file_path}: {e}", file=sys.stderr)

        return self._generate_results(components)

    def _find_react_files(self) -> List[Path]:
        """Find all React files in directory."""
        files = []
        for ext in self.extensions:
            files.extend(self.directory.rglob(f'*{ext}'))

        # Filter to likely React files
        react_files = []
        for file_path in files:
            if self._is_react_file(file_path):
                react_files.append(file_path)

        return react_files

    def _is_react_file(self, file_path: Path) -> bool:
        """Check if file is a React component."""
        try:
            content = file_path.read_text(encoding='utf-8')
            # Check for React imports or JSX
            return (
                'from "react"' in content or
                "from 'react'" in content or
                '<' in content and '>' in content
            )
        except:
            return False

    def _analyze_file(self, file_path: str, content: str) -> List[ComponentAnalysis]:
        """Analyze a single file."""
        components = []
        lines = content.split('\n')

        # Find component definitions
        component_names = self._find_components(content)

        for comp_name in component_names:
            analysis = ComponentAnalysis(
                file_path=file_path,
                component_name=comp_name,
                line_count=len(lines),
            )

            # Analyze state hooks
            analysis.state_hooks = self._find_state_hooks(content)

            # Count other hooks
            analysis.effects = len(self.hook_patterns['useEffect'].findall(content))
            analysis.memos = len(self.hook_patterns['useMemo'].findall(content))
            analysis.callbacks = len(self.hook_patterns['useCallback'].findall(content))

            # Find context usage
            analysis.contexts = self._find_contexts(content)

            # Count props
            analysis.prop_count = self._count_props(content, comp_name)

            # Detect issues
            analysis.issues = self._detect_issues(content, analysis)

            components.append(analysis)

        return components

    def _find_components(self, content: str) -> List[str]:
        """Find component names in file."""
        matches = self.component_pattern.findall(content)
        # Filter to likely component names (start with uppercase)
        return [name for name in matches if name and name[0].isupper()]

    def _find_state_hooks(self, content: str) -> List[StateUsage]:
        """Find all state hook usages."""
        state_hooks = []
        lines = content.split('\n')

        for hook_type, pattern in self.state_hooks.items():
            for match in pattern.finditer(content):
                # Find line number
                line_num = content[:match.start()].count('\n') + 1

                if hook_type == 'useState':
                    var_name = match.group(1)
                    initial_value = match.group(2).strip() if len(match.groups()) > 1 else None
                    state_hooks.append(StateUsage(
                        hook_type=hook_type,
                        variable_name=var_name,
                        line_number=line_num,
                        initial_value=initial_value,
                    ))
                elif hook_type == 'useReducer':
                    var_name = match.group(1)
                    state_hooks.append(StateUsage(
                        hook_type=hook_type,
                        variable_name=var_name,
                        line_number=line_num,
                    ))
                elif hook_type == 'useContext':
                    var_name = match.group(1)
                    context_name = match.group(2)
                    state_hooks.append(StateUsage(
                        hook_type=f'useContext({context_name})',
                        variable_name=var_name,
                        line_number=line_num,
                    ))

        return state_hooks

    def _find_contexts(self, content: str) -> Set[str]:
        """Find all context usages."""
        contexts = set()
        context_pattern = re.compile(r'useContext\((\w+)\)')
        for match in context_pattern.finditer(content):
            contexts.add(match.group(1))
        return contexts

    def _count_props(self, content: str, component_name: str) -> int:
        """Count props in component."""
        # Try to find props type/interface
        props_pattern = re.compile(
            rf'(?:function|const)\s+{component_name}\s*(?:<[^>]+>)?\s*\((?:\{{([^}}]+)\}}|(\w+):\s*(\w+))\)',
            re.MULTILINE
        )
        match = props_pattern.search(content)
        if match:
            props_text = match.group(1) or match.group(2)
            if props_text:
                # Count commas as rough prop count
                return props_text.count(',') + 1
        return 0

    def _detect_issues(self, content: str, analysis: ComponentAnalysis) -> List[Dict]:
        """Detect state management issues."""
        issues = []

        # Issue 1: Too many useState calls
        use_state_count = len([h for h in analysis.state_hooks if h.hook_type == 'useState'])
        if use_state_count > 5:
            issues.append({
                'severity': 'warning',
                'type': 'too_many_useState',
                'message': f'Component has {use_state_count} useState calls. Consider useReducer.',
                'line': analysis.state_hooks[0].line_number if analysis.state_hooks else 0,
            })

        # Issue 2: Stale closure risk in useEffect
        stale_closure_pattern = re.compile(
            r'useEffect\([^,]*\),\s*\[\s*\]',
            re.DOTALL
        )
        for match in stale_closure_pattern.finditer(content):
            effect_body = match.group(0)
            # Check if state variables are used without function form
            for state in analysis.state_hooks:
                if state.hook_type == 'useState':
                    var_name = state.variable_name
                    # Check for direct reference (not in setter form)
                    if f'{var_name} +' in effect_body or f'{var_name} -' in effect_body:
                        issues.append({
                            'severity': 'error',
                            'type': 'stale_closure',
                            'message': f'Potential stale closure: {var_name} used in useEffect with empty deps',
                            'line': content[:match.start()].count('\n') + 1,
                        })

        # Issue 3: Unnecessary derived state
        derived_state_pattern = re.compile(
            r'useEffect\([^}]*set\w+\([^)]*\),\s*\[[^\]]+\]',
            re.DOTALL
        )
        if derived_state_pattern.search(content):
            issues.append({
                'severity': 'warning',
                'type': 'derived_state',
                'message': 'Potential derived state in useEffect. Consider useMemo instead.',
                'line': 0,
            })

        # Issue 4: Missing React.memo with many props
        if analysis.prop_count > 3:
            if 'React.memo' not in content and 'memo(' not in content:
                issues.append({
                    'severity': 'info',
                    'type': 'missing_memo',
                    'message': f'Component has {analysis.prop_count} props. Consider React.memo.',
                    'line': 0,
                })

        # Issue 5: Expensive computation without useMemo
        expensive_patterns = [
            r'\.filter\(',
            r'\.map\(',
            r'\.reduce\(',
            r'\.sort\(',
        ]
        for pattern in expensive_patterns:
            if re.search(pattern, content) and analysis.memos == 0:
                issues.append({
                    'severity': 'info',
                    'type': 'missing_useMemo',
                    'message': 'Expensive array operations detected. Consider useMemo.',
                    'line': 0,
                })
                break

        return issues

    def _generate_results(self, components: List[ComponentAnalysis]) -> AnalysisResult:
        """Generate final analysis results."""
        state_distribution = defaultdict(int)
        issues_by_severity = defaultdict(int)
        suggestions = []

        for comp in components:
            for state in comp.state_hooks:
                state_distribution[state.hook_type] += 1

            for issue in comp.issues:
                issues_by_severity[issue['severity']] += 1

        # Generate suggestions
        total_use_state = state_distribution.get('useState', 0)
        if total_use_state > len(components) * 3:
            suggestions.append(
                'High useState usage detected. Consider using useReducer or a state library like Zustand.'
            )

        if issues_by_severity.get('error', 0) > 0:
            suggestions.append(
                'Critical stale closure issues detected. Review useEffect dependencies.'
            )

        if issues_by_severity.get('warning', 0) > 5:
            suggestions.append(
                'Multiple optimization opportunities. Review useMemo, useCallback, and React.memo usage.'
            )

        return AnalysisResult(
            components=components,
            total_files=len(set(c.file_path for c in components)),
            total_components=len(components),
            state_distribution=dict(state_distribution),
            issues_by_severity=dict(issues_by_severity),
            suggestions=suggestions,
        )


def format_output(result: AnalysisResult, format_type: str = 'text') -> str:
    """Format analysis results."""
    if format_type == 'json':
        data = {
            'summary': {
                'total_files': result.total_files,
                'total_components': result.total_components,
                'state_distribution': result.state_distribution,
                'issues_by_severity': result.issues_by_severity,
            },
            'components': [
                {
                    'file': c.file_path,
                    'name': c.component_name,
                    'state_hooks': len(c.state_hooks),
                    'effects': c.effects,
                    'memos': c.memos,
                    'callbacks': c.callbacks,
                    'contexts': list(c.contexts),
                    'props': c.prop_count,
                    'issues': c.issues,
                }
                for c in result.components
            ],
            'suggestions': result.suggestions,
        }
        return json.dumps(data, indent=2)

    # Text format
    lines = []
    lines.append('=' * 80)
    lines.append('React State Management Analysis')
    lines.append('=' * 80)
    lines.append('')

    lines.append('Summary:')
    lines.append(f'  Files analyzed: {result.total_files}')
    lines.append(f'  Components found: {result.total_components}')
    lines.append('')

    lines.append('State Distribution:')
    for hook_type, count in sorted(result.state_distribution.items()):
        lines.append(f'  {hook_type}: {count}')
    lines.append('')

    lines.append('Issues by Severity:')
    for severity in ['error', 'warning', 'info']:
        count = result.issues_by_severity.get(severity, 0)
        if count > 0:
            lines.append(f'  {severity.upper()}: {count}')
    lines.append('')

    if result.issues_by_severity:
        lines.append('Component Details:')
        lines.append('')

        for comp in result.components:
            if comp.issues:
                lines.append(f'  {comp.component_name} ({comp.file_path}):')
                lines.append(f'    State hooks: {len(comp.state_hooks)}')
                lines.append(f'    Effects: {comp.effects}, Memos: {comp.memos}, Callbacks: {comp.callbacks}')

                if comp.issues:
                    lines.append(f'    Issues:')
                    for issue in comp.issues:
                        severity = issue['severity'].upper()
                        lines.append(f'      [{severity}] {issue["message"]}')
                        if issue.get('line', 0) > 0:
                            lines.append(f'              Line {issue["line"]}')
                lines.append('')

    if result.suggestions:
        lines.append('Suggestions:')
        for suggestion in result.suggestions:
            lines.append(f'  - {suggestion}')
        lines.append('')

    lines.append('=' * 80)

    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(
        description='Analyze React component state management patterns',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s ./src
  %(prog)s ./src --json
  %(prog)s ./src --extensions .tsx .ts
  %(prog)s ./src --json > analysis.json
        """
    )

    parser.add_argument(
        'directory',
        help='Directory to analyze'
    )

    parser.add_argument(
        '--extensions',
        nargs='+',
        default=['.tsx', '.ts', '.jsx', '.js'],
        help='File extensions to analyze (default: .tsx .ts .jsx .js)'
    )

    parser.add_argument(
        '--json',
        action='store_true',
        help='Output in JSON format'
    )

    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Verbose output'
    )

    args = parser.parse_args()

    if not os.path.isdir(args.directory):
        print(f"Error: {args.directory} is not a directory", file=sys.stderr)
        sys.exit(1)

    if args.verbose:
        print(f"Analyzing React components in {args.directory}...", file=sys.stderr)

    analyzer = ReactStateAnalyzer(args.directory, args.extensions)
    result = analyzer.analyze()

    format_type = 'json' if args.json else 'text'
    output = format_output(result, format_type)
    print(output)

    # Exit with error code if critical issues found
    if result.issues_by_severity.get('error', 0) > 0:
        sys.exit(1)


if __name__ == '__main__':
    main()
