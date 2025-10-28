#!/usr/bin/env python3
"""
ARIA usage analyzer for HTML/React files

Analyzes ARIA attributes in HTML and React/JSX files, detecting common
mistakes, invalid combinations, and best practice violations.

Usage:
    ./analyze_aria.py <file_or_directory>
    ./analyze_aria.py src/components/
    ./analyze_aria.py src/App.jsx --json
    ./analyze_aria.py . --recursive --report issues
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict


@dataclass
class Issue:
    """ARIA issue details"""
    severity: str  # error, warning, info
    category: str
    message: str
    file: str
    line: int
    column: int
    context: str
    suggestion: Optional[str] = None


@dataclass
class FileReport:
    """ARIA analysis report for a single file"""
    file: str
    total_lines: int
    aria_attributes: int
    aria_roles: int
    issues: List[Issue]

    @property
    def errors(self) -> int:
        return sum(1 for i in self.issues if i.severity == 'error')

    @property
    def warnings(self) -> int:
        return sum(1 for i in self.issues if i.severity == 'warning')

    @property
    def has_issues(self) -> bool:
        return len(self.issues) > 0

    def to_dict(self):
        return {
            **asdict(self),
            'errors': self.errors,
            'warnings': self.warnings
        }


class AriaAnalyzer:
    """Analyze ARIA usage in HTML/JSX files"""

    # Valid ARIA roles
    VALID_ROLES = {
        # Landmark roles
        'banner', 'complementary', 'contentinfo', 'form', 'main',
        'navigation', 'region', 'search',
        # Document structure roles
        'article', 'definition', 'directory', 'document', 'feed',
        'figure', 'group', 'heading', 'img', 'list', 'listitem',
        'math', 'none', 'note', 'presentation', 'separator', 'table',
        'term', 'toolbar', 'tooltip',
        # Widget roles
        'button', 'checkbox', 'gridcell', 'link', 'menuitem',
        'menuitemcheckbox', 'menuitemradio', 'option', 'progressbar',
        'radio', 'scrollbar', 'searchbox', 'slider', 'spinbutton',
        'switch', 'tab', 'tabpanel', 'textbox', 'treeitem',
        # Composite roles
        'combobox', 'grid', 'listbox', 'menu', 'menubar', 'radiogroup',
        'tablist', 'tree', 'treegrid',
        # Window roles
        'alertdialog', 'dialog',
        # Live region roles
        'alert', 'log', 'marquee', 'status', 'timer',
        # Abstract roles (should not be used)
        'command', 'composite', 'input', 'landmark', 'range',
        'roletype', 'section', 'sectionhead', 'select', 'structure',
        'widget', 'window'
    }

    # Abstract roles that should not be used
    ABSTRACT_ROLES = {
        'command', 'composite', 'input', 'landmark', 'range',
        'roletype', 'section', 'sectionhead', 'select', 'structure',
        'widget', 'window'
    }

    # Valid ARIA attributes
    VALID_ATTRIBUTES = {
        'aria-activedescendant', 'aria-atomic', 'aria-autocomplete',
        'aria-busy', 'aria-checked', 'aria-colcount', 'aria-colindex',
        'aria-colspan', 'aria-controls', 'aria-current', 'aria-describedby',
        'aria-details', 'aria-disabled', 'aria-dropeffect', 'aria-errormessage',
        'aria-expanded', 'aria-flowto', 'aria-grabbed', 'aria-haspopup',
        'aria-hidden', 'aria-invalid', 'aria-keyshortcuts', 'aria-label',
        'aria-labelledby', 'aria-level', 'aria-live', 'aria-modal',
        'aria-multiline', 'aria-multiselectable', 'aria-orientation',
        'aria-owns', 'aria-placeholder', 'aria-posinset', 'aria-pressed',
        'aria-readonly', 'aria-relevant', 'aria-required', 'aria-roledescription',
        'aria-rowcount', 'aria-rowindex', 'aria-rowspan', 'aria-selected',
        'aria-setsize', 'aria-sort', 'aria-valuemax', 'aria-valuemin',
        'aria-valuenow', 'aria-valuetext'
    }

    # Elements that should not have role attribute
    SEMANTIC_ELEMENTS = {
        'header', 'nav', 'main', 'footer', 'aside', 'section', 'article',
        'button', 'a', 'input', 'select', 'textarea', 'form', 'table',
        'ul', 'ol', 'li', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'
    }

    # Roles that require aria-label or aria-labelledby
    ROLES_REQUIRING_LABEL = {
        'region', 'form', 'navigation', 'complementary', 'search'
    }

    # Roles that require specific ARIA attributes
    REQUIRED_ATTRIBUTES = {
        'checkbox': ['aria-checked'],
        'combobox': ['aria-expanded', 'aria-controls'],
        'heading': ['aria-level'],
        'listbox': ['aria-label', 'aria-labelledby'],
        'option': ['aria-selected'],
        'progressbar': ['aria-valuenow', 'aria-valuemin', 'aria-valuemax'],
        'radio': ['aria-checked'],
        'scrollbar': ['aria-valuenow', 'aria-valuemin', 'aria-valuemax'],
        'slider': ['aria-valuenow', 'aria-valuemin', 'aria-valuemax'],
        'spinbutton': ['aria-valuenow', 'aria-valuemin', 'aria-valuemax'],
        'switch': ['aria-checked'],
        'tab': ['aria-selected'],
    }

    # Mutually exclusive ARIA attributes
    MUTUALLY_EXCLUSIVE = [
        {'aria-label', 'aria-labelledby'},
    ]

    def __init__(self):
        self.issues: List[Issue] = []

    def analyze_file(self, file_path: Path) -> FileReport:
        """Analyze a single file for ARIA issues"""
        self.issues = []

        try:
            content = file_path.read_text()
        except (IOError, UnicodeDecodeError) as e:
            self.issues.append(Issue(
                severity='error',
                category='file',
                message=f'Failed to read file: {e}',
                file=str(file_path),
                line=0,
                column=0,
                context=''
            ))
            return FileReport(
                file=str(file_path),
                total_lines=0,
                aria_attributes=0,
                aria_roles=0,
                issues=self.issues
            )

        lines = content.split('\n')
        aria_count = 0
        role_count = 0

        # Analyze each line
        for line_num, line in enumerate(lines, 1):
            # Count ARIA usage
            aria_count += len(re.findall(r'aria-\w+', line))
            role_count += len(re.findall(r'\brole=', line))

            # Check for issues
            self._check_line(line, line_num, str(file_path))

        return FileReport(
            file=str(file_path),
            total_lines=len(lines),
            aria_attributes=aria_count,
            aria_roles=role_count,
            issues=self.issues
        )

    def _check_line(self, line: str, line_num: int, file_path: str):
        """Check a single line for ARIA issues"""
        # Check for invalid ARIA attributes
        aria_attrs = re.finditer(r'(aria-[\w-]+)\s*=\s*["{]([^"{}]+)["}]', line)
        for match in aria_attrs:
            attr, value = match.groups()
            col = match.start() + 1

            if attr not in self.VALID_ATTRIBUTES:
                self.issues.append(Issue(
                    severity='error',
                    category='invalid-attribute',
                    message=f'Invalid ARIA attribute: {attr}',
                    file=file_path,
                    line=line_num,
                    column=col,
                    context=line.strip(),
                    suggestion='Check spelling or remove invalid attribute'
                ))

            # Check specific attribute values
            self._check_attribute_value(attr, value, line, line_num, col, file_path)

        # Check for invalid roles
        role_matches = re.finditer(r'\brole\s*=\s*["{]([^"{}]+)["}]', line)
        for match in role_matches:
            role = match.group(1).strip()
            col = match.start() + 1

            if role not in self.VALID_ROLES:
                self.issues.append(Issue(
                    severity='error',
                    category='invalid-role',
                    message=f'Invalid ARIA role: {role}',
                    file=file_path,
                    line=line_num,
                    column=col,
                    context=line.strip(),
                    suggestion='Use a valid ARIA role from the specification'
                ))
            elif role in self.ABSTRACT_ROLES:
                self.issues.append(Issue(
                    severity='error',
                    category='abstract-role',
                    message=f'Abstract role should not be used: {role}',
                    file=file_path,
                    line=line_num,
                    column=col,
                    context=line.strip(),
                    suggestion='Use a concrete role instead'
                ))

            # Check if role requires label
            if role in self.ROLES_REQUIRING_LABEL:
                if 'aria-label' not in line and 'aria-labelledby' not in line:
                    self.issues.append(Issue(
                        severity='warning',
                        category='missing-label',
                        message=f'Role "{role}" requires aria-label or aria-labelledby',
                        file=file_path,
                        line=line_num,
                        column=col,
                        context=line.strip(),
                        suggestion='Add aria-label or aria-labelledby'
                    ))

        # Check for redundant roles on semantic elements
        for element in self.SEMANTIC_ELEMENTS:
            pattern = r'<' + element + r'\s+[^>]*\brole\s*=\s*["{]([^"{}]+)["}]'
            matches = re.finditer(pattern, line, re.IGNORECASE)
            for match in matches:
                role = match.group(1)
                col = match.start() + 1
                self.issues.append(Issue(
                    severity='warning',
                    category='redundant-role',
                    message=f'Redundant role "{role}" on semantic <{element}> element',
                    file=file_path,
                    line=line_num,
                    column=col,
                    context=line.strip(),
                    suggestion=f'Remove role attribute; <{element}> has implicit semantics'
                ))

        # Check for aria-hidden on focusable elements
        if 'aria-hidden="true"' in line or "aria-hidden='true'" in line or 'aria-hidden={true}' in line:
            if re.search(r'<(button|a|input|select|textarea)\b', line, re.IGNORECASE):
                col = line.find('aria-hidden') + 1
                self.issues.append(Issue(
                    severity='error',
                    category='hidden-focusable',
                    message='aria-hidden="true" on focusable element',
                    file=file_path,
                    line=line_num,
                    column=col,
                    context=line.strip(),
                    suggestion='Remove aria-hidden or make element non-focusable with tabindex="-1"'
                ))

        # Check for both aria-label and aria-labelledby
        if ('aria-label' in line and 'aria-labelledby' in line):
            col = line.find('aria-label') + 1
            self.issues.append(Issue(
                severity='warning',
                category='conflicting-labels',
                message='Both aria-label and aria-labelledby present',
                file=file_path,
                line=line_num,
                column=col,
                context=line.strip(),
                suggestion='Use only one: aria-labelledby takes precedence'
            ))

        # Check for empty aria-label
        empty_label = re.search(r'aria-label\s*=\s*["{]\s*["}]', line)
        if empty_label:
            col = empty_label.start() + 1
            self.issues.append(Issue(
                severity='error',
                category='empty-label',
                message='Empty aria-label provides no information',
                file=file_path,
                line=line_num,
                column=col,
                context=line.strip(),
                suggestion='Provide descriptive label text or remove attribute'
            ))

        # Check for positive tabindex
        tabindex = re.search(r'tabindex\s*=\s*["{]([1-9]\d*)["}]', line)
        if tabindex:
            col = tabindex.start() + 1
            self.issues.append(Issue(
                severity='warning',
                category='positive-tabindex',
                message=f'Positive tabindex ({tabindex.group(1)}) breaks natural tab order',
                file=file_path,
                line=line_num,
                column=col,
                context=line.strip(),
                suggestion='Use tabindex="0" or "-1" only'
            ))

    def _check_attribute_value(
        self,
        attr: str,
        value: str,
        line: str,
        line_num: int,
        col: int,
        file_path: str
    ):
        """Check specific ARIA attribute values"""
        # aria-checked: must be true, false, or mixed
        if attr == 'aria-checked':
            if value not in ['true', 'false', 'mixed']:
                self.issues.append(Issue(
                    severity='error',
                    category='invalid-value',
                    message=f'Invalid aria-checked value: "{value}"',
                    file=file_path,
                    line=line_num,
                    column=col,
                    context=line.strip(),
                    suggestion='Use "true", "false", or "mixed"'
                ))

        # aria-expanded: must be true or false
        elif attr == 'aria-expanded':
            if value not in ['true', 'false']:
                self.issues.append(Issue(
                    severity='error',
                    category='invalid-value',
                    message=f'Invalid aria-expanded value: "{value}"',
                    file=file_path,
                    line=line_num,
                    column=col,
                    context=line.strip(),
                    suggestion='Use "true" or "false"'
                ))

        # aria-hidden: must be true or false
        elif attr == 'aria-hidden':
            if value not in ['true', 'false']:
                self.issues.append(Issue(
                    severity='error',
                    category='invalid-value',
                    message=f'Invalid aria-hidden value: "{value}"',
                    file=file_path,
                    line=line_num,
                    column=col,
                    context=line.strip(),
                    suggestion='Use "true" or "false"'
                ))

        # aria-invalid: must be true, false, grammar, or spelling
        elif attr == 'aria-invalid':
            if value not in ['true', 'false', 'grammar', 'spelling']:
                self.issues.append(Issue(
                    severity='error',
                    category='invalid-value',
                    message=f'Invalid aria-invalid value: "{value}"',
                    file=file_path,
                    line=line_num,
                    column=col,
                    context=line.strip(),
                    suggestion='Use "true", "false", "grammar", or "spelling"'
                ))

        # aria-live: must be off, polite, or assertive
        elif attr == 'aria-live':
            if value not in ['off', 'polite', 'assertive']:
                self.issues.append(Issue(
                    severity='error',
                    category='invalid-value',
                    message=f'Invalid aria-live value: "{value}"',
                    file=file_path,
                    line=line_num,
                    column=col,
                    context=line.strip(),
                    suggestion='Use "off", "polite", or "assertive"'
                ))

        # aria-pressed: must be true, false, or mixed
        elif attr == 'aria-pressed':
            if value not in ['true', 'false', 'mixed']:
                self.issues.append(Issue(
                    severity='error',
                    category='invalid-value',
                    message=f'Invalid aria-pressed value: "{value}"',
                    file=file_path,
                    line=line_num,
                    column=col,
                    context=line.strip(),
                    suggestion='Use "true", "false", or "mixed"'
                ))

        # aria-selected: must be true or false
        elif attr == 'aria-selected':
            if value not in ['true', 'false']:
                self.issues.append(Issue(
                    severity='error',
                    category='invalid-value',
                    message=f'Invalid aria-selected value: "{value}"',
                    file=file_path,
                    line=line_num,
                    column=col,
                    context=line.strip(),
                    suggestion='Use "true" or "false"'
                ))


def format_text_report(reports: List[FileReport]) -> str:
    """Format reports as text"""
    lines = []
    lines.append("=" * 80)
    lines.append("ARIA ANALYSIS REPORT")
    lines.append("=" * 80)

    total_files = len(reports)
    total_issues = sum(len(r.issues) for r in reports)
    total_errors = sum(r.errors for r in reports)
    total_warnings = sum(r.warnings for r in reports)

    lines.append(f"Files analyzed: {total_files}")
    lines.append(f"Total issues: {total_issues}")
    lines.append(f"  Errors: {total_errors}")
    lines.append(f"  Warnings: {total_warnings}")
    lines.append("")

    # Group issues by category
    issues_by_category = defaultdict(int)
    for report in reports:
        for issue in report.issues:
            issues_by_category[issue.category] += 1

    if issues_by_category:
        lines.append("Issues by category:")
        for category, count in sorted(issues_by_category.items(), key=lambda x: -x[1]):
            lines.append(f"  {category}: {count}")
        lines.append("")

    # Show files with issues
    for report in reports:
        if not report.has_issues:
            continue

        lines.append("-" * 80)
        lines.append(f"File: {report.file}")
        lines.append(f"Lines: {report.total_lines}")
        lines.append(f"ARIA attributes: {report.aria_attributes}")
        lines.append(f"ARIA roles: {report.aria_roles}")
        lines.append(f"Issues: {len(report.issues)} ({report.errors} errors, {report.warnings} warnings)")
        lines.append("")

        for i, issue in enumerate(report.issues, 1):
            severity_marker = "ERROR" if issue.severity == "error" else "WARN"
            lines.append(f"{i}. [{severity_marker}] Line {issue.line}:{issue.column}")
            lines.append(f"   Category: {issue.category}")
            lines.append(f"   Message: {issue.message}")
            lines.append(f"   Context: {issue.context}")
            if issue.suggestion:
                lines.append(f"   Suggestion: {issue.suggestion}")
            lines.append("")

    lines.append("=" * 80)
    return "\n".join(lines)


def format_json_report(reports: List[FileReport]) -> str:
    """Format reports as JSON"""
    report = {
        'total_files': len(reports),
        'total_issues': sum(len(r.issues) for r in reports),
        'total_errors': sum(r.errors for r in reports),
        'total_warnings': sum(r.warnings for r in reports),
        'files': [r.to_dict() for r in reports]
    }
    return json.dumps(report, indent=2)


def main():
    parser = argparse.ArgumentParser(
        description='Analyze ARIA usage in HTML/JSX files',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s src/App.jsx
  %(prog)s src/components/ --recursive
  %(prog)s . --recursive --json --output aria-report.json
  %(prog)s src/ --recursive --report issues
        """
    )

    parser.add_argument(
        'path',
        help='File or directory to analyze'
    )
    parser.add_argument(
        '--recursive', '-r',
        action='store_true',
        help='Recursively analyze directories'
    )
    parser.add_argument(
        '--extensions',
        nargs='+',
        default=['.html', '.htm', '.jsx', '.tsx', '.js', '.ts'],
        help='File extensions to analyze (default: .html .htm .jsx .tsx .js .ts)'
    )
    parser.add_argument(
        '--json',
        action='store_true',
        help='Output in JSON format'
    )
    parser.add_argument(
        '--output', '-o',
        help='Write output to file'
    )
    parser.add_argument(
        '--report',
        choices=['all', 'issues'],
        default='all',
        help='Report type: all files or only files with issues (default: all)'
    )

    args = parser.parse_args()

    # Get files to analyze
    path = Path(args.path)
    files = []

    if path.is_file():
        files = [path]
    elif path.is_dir():
        if args.recursive:
            for ext in args.extensions:
                files.extend(path.rglob(f'*{ext}'))
        else:
            for ext in args.extensions:
                files.extend(path.glob(f'*{ext}'))
    else:
        print(f"Error: Path not found: {path}", file=sys.stderr)
        sys.exit(1)

    if not files:
        print(f"Error: No files found to analyze", file=sys.stderr)
        sys.exit(1)

    # Analyze files
    print(f"Analyzing {len(files)} file(s)...", file=sys.stderr)
    analyzer = AriaAnalyzer()
    reports = []

    for file in sorted(files):
        report = analyzer.analyze_file(file)
        if args.report == 'issues' and not report.has_issues:
            continue
        reports.append(report)

    if not reports:
        print("No files to report", file=sys.stderr)
        sys.exit(0)

    # Format output
    if args.json:
        output = format_json_report(reports)
    else:
        output = format_text_report(reports)

    # Write output
    if args.output:
        try:
            Path(args.output).write_text(output)
            print(f"Report written to: {args.output}", file=sys.stderr)
        except IOError as e:
            print(f"Error: Failed to write output: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        print(output)

    # Exit code based on errors
    total_errors = sum(r.errors for r in reports)
    sys.exit(1 if total_errors > 0 else 0)


if __name__ == '__main__':
    main()
