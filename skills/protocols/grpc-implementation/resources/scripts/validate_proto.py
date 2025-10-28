#!/usr/bin/env python3
"""
Proto File Validator

Validates Protocol Buffer definitions, checks naming conventions, detects
breaking changes, and suggests improvements.

Usage:
    ./validate_proto.py --proto-file api.proto --json
    ./validate_proto.py --proto-file api.proto --check-breaking --baseline baseline.proto
    ./validate_proto.py --help

Features:
- Parse and validate .proto syntax
- Check naming conventions (PascalCase messages, snake_case fields)
- Detect breaking changes between versions
- Validate service definitions
- Check for best practices (reserved fields, deprecation)
- Output as JSON or human-readable text
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict


@dataclass
class ValidationIssue:
    """Represents a validation issue found in a proto file"""
    severity: str  # 'error', 'warning', 'info'
    category: str  # 'syntax', 'naming', 'best_practice', 'breaking_change'
    message: str
    line: Optional[int] = None
    field: Optional[str] = None


@dataclass
class ProtoMessage:
    """Represents a Protocol Buffer message"""
    name: str
    fields: List[Tuple[str, int, str]]  # (name, number, type)
    line: int


@dataclass
class ProtoService:
    """Represents a Protocol Buffer service"""
    name: str
    methods: List[Tuple[str, str, str]]  # (name, request, response)
    line: int


@dataclass
class ProtoFile:
    """Parsed Protocol Buffer file"""
    syntax: str
    package: str
    messages: List[ProtoMessage]
    services: List[ProtoService]
    imports: List[str]
    options: Dict[str, str]


class ProtoValidator:
    """Validates Protocol Buffer files"""

    def __init__(self):
        self.issues: List[ValidationIssue] = []

    def validate_file(self, proto_file: Path) -> Tuple[ProtoFile, List[ValidationIssue]]:
        """Validate a proto file and return parsed structure and issues"""
        self.issues = []

        if not proto_file.exists():
            self.add_issue('error', 'syntax', f"File not found: {proto_file}")
            return None, self.issues

        content = proto_file.read_text()
        lines = content.split('\n')

        # Parse proto file
        proto = self.parse_proto(lines)

        # Run validations
        self.validate_syntax(proto, lines)
        self.validate_naming_conventions(proto)
        self.validate_best_practices(proto, lines)

        return proto, self.issues

    def parse_proto(self, lines: List[str]) -> ProtoFile:
        """Parse proto file into structured format"""
        syntax = "proto3"  # default
        package = ""
        messages = []
        services = []
        imports = []
        options = {}

        current_message = None
        current_service = None

        for i, line in enumerate(lines, 1):
            line = line.strip()

            # Skip comments and empty lines
            if not line or line.startswith('//'):
                continue

            # Parse syntax
            if line.startswith('syntax'):
                match = re.match(r'syntax\s*=\s*"([^"]+)"', line)
                if match:
                    syntax = match.group(1)

            # Parse package
            elif line.startswith('package'):
                match = re.match(r'package\s+([^;]+);', line)
                if match:
                    package = match.group(1).strip()

            # Parse imports
            elif line.startswith('import'):
                match = re.match(r'import\s+"([^"]+)"', line)
                if match:
                    imports.append(match.group(1))

            # Parse options
            elif line.startswith('option'):
                match = re.match(r'option\s+(\w+)\s*=\s*"([^"]+)"', line)
                if match:
                    options[match.group(1)] = match.group(2)

            # Parse message
            elif line.startswith('message'):
                match = re.match(r'message\s+(\w+)', line)
                if match:
                    current_message = ProtoMessage(
                        name=match.group(1),
                        fields=[],
                        line=i
                    )
                    messages.append(current_message)

            # Parse message field
            elif current_message and '=' in line and not line.startswith('}'):
                # Parse field: type name = number;
                match = re.match(r'(repeated\s+)?(\w+)\s+(\w+)\s*=\s*(\d+)', line)
                if match:
                    field_type = match.group(2)
                    field_name = match.group(3)
                    field_number = int(match.group(4))
                    current_message.fields.append((field_name, field_number, field_type))

            # End message
            elif line.startswith('}') and current_message:
                current_message = None

            # Parse service
            elif line.startswith('service'):
                match = re.match(r'service\s+(\w+)', line)
                if match:
                    current_service = ProtoService(
                        name=match.group(1),
                        methods=[],
                        line=i
                    )
                    services.append(current_service)

            # Parse RPC method
            elif current_service and line.startswith('rpc'):
                # rpc MethodName(Request) returns (Response);
                match = re.match(r'rpc\s+(\w+)\s*\(\s*(?:stream\s+)?(\w+)\s*\)\s*returns\s*\(\s*(?:stream\s+)?(\w+)\s*\)', line)
                if match:
                    method_name = match.group(1)
                    request_type = match.group(2)
                    response_type = match.group(3)
                    current_service.methods.append((method_name, request_type, response_type))

            # End service
            elif line.startswith('}') and current_service:
                current_service = None

        return ProtoFile(
            syntax=syntax,
            package=package,
            messages=messages,
            services=services,
            imports=imports,
            options=options
        )

    def validate_syntax(self, proto: ProtoFile, lines: List[str]):
        """Validate proto syntax"""
        if not proto:
            return

        # Check syntax version
        if proto.syntax != "proto3":
            self.add_issue(
                'warning',
                'syntax',
                f"Using {proto.syntax} (proto3 is recommended for new projects)"
            )

        # Check package declaration
        if not proto.package:
            self.add_issue(
                'warning',
                'syntax',
                "Missing package declaration (recommended for namespace management)"
            )

        # Check for duplicat field numbers
        for message in proto.messages:
            field_numbers = {}
            for field_name, field_num, field_type in message.fields:
                if field_num in field_numbers:
                    self.add_issue(
                        'error',
                        'syntax',
                        f"Duplicate field number {field_num} in message {message.name} "
                        f"(fields '{field_numbers[field_num]}' and '{field_name}')",
                        line=message.line
                    )
                else:
                    field_numbers[field_num] = field_name

        # Check for reserved ranges (19000-19999)
        for message in proto.messages:
            for field_name, field_num, _ in message.fields:
                if 19000 <= field_num <= 19999:
                    self.add_issue(
                        'error',
                        'syntax',
                        f"Field {field_name} in {message.name} uses reserved range (19000-19999)",
                        line=message.line,
                        field=field_name
                    )

    def validate_naming_conventions(self, proto: ProtoFile):
        """Validate naming conventions"""
        if not proto:
            return

        # Check message names (PascalCase)
        for message in proto.messages:
            if not self.is_pascal_case(message.name):
                self.add_issue(
                    'warning',
                    'naming',
                    f"Message name '{message.name}' should be PascalCase",
                    line=message.line
                )

        # Check field names (snake_case)
        for message in proto.messages:
            for field_name, field_num, _ in message.fields:
                if not self.is_snake_case(field_name):
                    self.add_issue(
                        'warning',
                        'naming',
                        f"Field name '{field_name}' in {message.name} should be snake_case",
                        line=message.line,
                        field=field_name
                    )

        # Check service names (PascalCase + "Service" suffix)
        for service in proto.services:
            if not self.is_pascal_case(service.name):
                self.add_issue(
                    'warning',
                    'naming',
                    f"Service name '{service.name}' should be PascalCase",
                    line=service.line
                )

            if not service.name.endswith('Service'):
                self.add_issue(
                    'info',
                    'naming',
                    f"Service name '{service.name}' should end with 'Service' (convention)",
                    line=service.line
                )

        # Check RPC method names (PascalCase)
        for service in proto.services:
            for method_name, _, _ in service.methods:
                if not self.is_pascal_case(method_name):
                    self.add_issue(
                        'warning',
                        'naming',
                        f"RPC method '{method_name}' in {service.name} should be PascalCase",
                        line=service.line
                    )

        # Check package name (lowercase with dots)
        if proto.package:
            if not re.match(r'^[a-z][a-z0-9.]*[a-z0-9]$', proto.package):
                self.add_issue(
                    'warning',
                    'naming',
                    f"Package name '{proto.package}' should be lowercase with dots (e.g., 'users.v1')"
                )

    def validate_best_practices(self, proto: ProtoFile, lines: List[str]):
        """Validate best practices"""
        if not proto:
            return

        # Check for language-specific options
        if 'go_package' not in proto.options:
            self.add_issue(
                'info',
                'best_practice',
                "Missing 'go_package' option (recommended for Go code generation)"
            )

        # Check field number usage (1-15 are most efficient)
        for message in proto.messages:
            frequent_fields = [f for f in message.fields if f[1] > 15]
            if frequent_fields:
                self.add_issue(
                    'info',
                    'best_practice',
                    f"Message {message.name} has fields with numbers > 15 "
                    f"(use 1-15 for frequently used fields for efficiency)",
                    line=message.line
                )

        # Check for request/response naming pattern
        for service in proto.services:
            for method_name, request_type, response_type in service.methods:
                expected_request = f"{method_name}Request"
                expected_response = f"{method_name}Response"

                if request_type != expected_request:
                    self.add_issue(
                        'info',
                        'best_practice',
                        f"RPC {method_name} request type '{request_type}' doesn't follow convention "
                        f"(expected '{expected_request}')",
                        line=service.line
                    )

                if response_type != expected_response:
                    self.add_issue(
                        'info',
                        'best_practice',
                        f"RPC {method_name} response type '{response_type}' doesn't follow convention "
                        f"(expected '{expected_response}')",
                        line=service.line
                    )

        # Check for reserved fields usage
        has_reserved = any('reserved' in line for line in lines)
        if not has_reserved and len(proto.messages) > 0:
            self.add_issue(
                'info',
                'best_practice',
                "No reserved fields found (consider reserving deleted field numbers for backward compatibility)"
            )

        # Check for enum with UNSPECIFIED
        for line in lines:
            if 'enum' in line:
                # Look for UNSPECIFIED = 0 pattern
                enum_name = re.search(r'enum\s+(\w+)', line)
                if enum_name:
                    # Check if next non-comment line has UNSPECIFIED = 0
                    # This is a simplified check
                    self.add_issue(
                        'info',
                        'best_practice',
                        f"Ensure enum {enum_name.group(1)} has first value = 0 with '_UNSPECIFIED' suffix"
                    )

    def check_breaking_changes(self, old_proto: ProtoFile, new_proto: ProtoFile) -> List[ValidationIssue]:
        """Check for breaking changes between two versions"""
        breaking_changes = []

        # Check for deleted messages
        old_message_names = {m.name for m in old_proto.messages}
        new_message_names = {m.name for m in new_proto.messages}
        deleted_messages = old_message_names - new_message_names

        for msg_name in deleted_messages:
            breaking_changes.append(ValidationIssue(
                severity='error',
                category='breaking_change',
                message=f"Message '{msg_name}' was deleted (breaking change)"
            ))

        # Check for field changes in existing messages
        old_messages = {m.name: m for m in old_proto.messages}
        new_messages = {m.name: m for m in new_proto.messages}

        for msg_name in old_message_names & new_message_names:
            old_msg = old_messages[msg_name]
            new_msg = new_messages[msg_name]

            # Check field number changes
            old_fields = {num: (name, typ) for name, num, typ in old_msg.fields}
            new_fields = {num: (name, typ) for name, num, typ in new_msg.fields}

            # Deleted fields (should be reserved)
            deleted_field_nums = set(old_fields.keys()) - set(new_fields.keys())
            for field_num in deleted_field_nums:
                field_name, _ = old_fields[field_num]
                breaking_changes.append(ValidationIssue(
                    severity='warning',
                    category='breaking_change',
                    message=f"Field '{field_name}' (number {field_num}) deleted from {msg_name} "
                           f"(should be reserved)",
                    field=field_name
                ))

            # Changed field types
            for field_num in set(old_fields.keys()) & set(new_fields.keys()):
                old_name, old_type = old_fields[field_num]
                new_name, new_type = new_fields[field_num]

                if old_type != new_type:
                    breaking_changes.append(ValidationIssue(
                        severity='error',
                        category='breaking_change',
                        message=f"Field {field_num} in {msg_name} changed type from {old_type} to {new_type} "
                               f"(breaking change)",
                        field=new_name
                    ))

        # Check for deleted services
        old_service_names = {s.name for s in old_proto.services}
        new_service_names = {s.name for s in new_proto.services}
        deleted_services = old_service_names - new_service_names

        for svc_name in deleted_services:
            breaking_changes.append(ValidationIssue(
                severity='error',
                category='breaking_change',
                message=f"Service '{svc_name}' was deleted (breaking change)"
            ))

        # Check for deleted RPC methods
        old_services = {s.name: s for s in old_proto.services}
        new_services = {s.name: s for s in new_proto.services}

        for svc_name in old_service_names & new_service_names:
            old_svc = old_services[svc_name]
            new_svc = new_services[svc_name]

            old_methods = {m[0] for m in old_svc.methods}
            new_methods = {m[0] for m in new_svc.methods}
            deleted_methods = old_methods - new_methods

            for method_name in deleted_methods:
                breaking_changes.append(ValidationIssue(
                    severity='error',
                    category='breaking_change',
                    message=f"RPC method '{method_name}' deleted from service {svc_name} (breaking change)"
                ))

        return breaking_changes

    def add_issue(self, severity: str, category: str, message: str,
                  line: Optional[int] = None, field: Optional[str] = None):
        """Add a validation issue"""
        self.issues.append(ValidationIssue(
            severity=severity,
            category=category,
            message=message,
            line=line,
            field=field
        ))

    @staticmethod
    def is_pascal_case(name: str) -> bool:
        """Check if name is PascalCase"""
        return bool(re.match(r'^[A-Z][a-zA-Z0-9]*$', name))

    @staticmethod
    def is_snake_case(name: str) -> bool:
        """Check if name is snake_case"""
        return bool(re.match(r'^[a-z][a-z0-9_]*$', name))


def format_issues_text(issues: List[ValidationIssue]) -> str:
    """Format issues as human-readable text"""
    if not issues:
        return "✓ No issues found"

    output = []

    # Group by severity
    errors = [i for i in issues if i.severity == 'error']
    warnings = [i for i in issues if i.severity == 'warning']
    infos = [i for i in issues if i.severity == 'info']

    if errors:
        output.append(f"\n{'='*60}")
        output.append(f"ERRORS ({len(errors)}):")
        output.append('='*60)
        for issue in errors:
            location = f" [Line {issue.line}]" if issue.line else ""
            field = f" (field: {issue.field})" if issue.field else ""
            output.append(f"  ✗ {issue.message}{location}{field}")

    if warnings:
        output.append(f"\n{'='*60}")
        output.append(f"WARNINGS ({len(warnings)}):")
        output.append('='*60)
        for issue in warnings:
            location = f" [Line {issue.line}]" if issue.line else ""
            field = f" (field: {issue.field})" if issue.field else ""
            output.append(f"  ! {issue.message}{location}{field}")

    if infos:
        output.append(f"\n{'='*60}")
        output.append(f"INFO ({len(infos)}):")
        output.append('='*60)
        for issue in infos:
            location = f" [Line {issue.line}]" if issue.line else ""
            field = f" (field: {issue.field})" if issue.field else ""
            output.append(f"  ℹ {issue.message}{location}{field}")

    output.append(f"\n{'='*60}")
    output.append(f"Summary: {len(errors)} errors, {len(warnings)} warnings, {len(infos)} info")
    output.append('='*60)

    return '\n'.join(output)


def format_issues_json(proto: Optional[ProtoFile], issues: List[ValidationIssue]) -> str:
    """Format issues as JSON"""
    result = {
        'valid': len([i for i in issues if i.severity == 'error']) == 0,
        'summary': {
            'errors': len([i for i in issues if i.severity == 'error']),
            'warnings': len([i for i in issues if i.severity == 'warning']),
            'info': len([i for i in issues if i.severity == 'info'])
        },
        'issues': [asdict(i) for i in issues]
    }

    if proto:
        result['proto'] = {
            'syntax': proto.syntax,
            'package': proto.package,
            'messages': [{'name': m.name, 'field_count': len(m.fields)} for m in proto.messages],
            'services': [{'name': s.name, 'method_count': len(s.methods)} for s in proto.services],
            'imports': proto.imports
        }

    return json.dumps(result, indent=2)


def main():
    parser = argparse.ArgumentParser(
        description='Validate Protocol Buffer definitions',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic validation
  %(prog)s --proto-file api.proto

  # JSON output
  %(prog)s --proto-file api.proto --json

  # Check breaking changes
  %(prog)s --proto-file api_v2.proto --check-breaking --baseline api_v1.proto

  # Save report
  %(prog)s --proto-file api.proto --json > validation-report.json

Categories:
  - syntax: Proto syntax errors
  - naming: Naming convention violations
  - best_practice: Best practice recommendations
  - breaking_change: Breaking changes between versions

Severity Levels:
  - error: Must fix (blocks build/deployment)
  - warning: Should fix (violates conventions)
  - info: Consider fixing (suggestions)
        """
    )

    parser.add_argument(
        '--proto-file',
        type=Path,
        required=True,
        help='Path to .proto file to validate'
    )

    parser.add_argument(
        '--check-breaking',
        action='store_true',
        help='Check for breaking changes'
    )

    parser.add_argument(
        '--baseline',
        type=Path,
        help='Baseline .proto file for breaking change detection'
    )

    parser.add_argument(
        '--json',
        action='store_true',
        help='Output as JSON'
    )

    parser.add_argument(
        '--help-categories',
        action='store_true',
        help='Show validation category descriptions and exit'
    )

    args = parser.parse_args()

    if args.help_categories:
        print("""
Validation Categories:
======================

SYNTAX
  - Missing syntax declaration
  - Invalid proto syntax
  - Duplicate field numbers
  - Use of reserved field number range (19000-19999)
  - Missing package declaration

NAMING
  - Messages should be PascalCase (e.g., UserProfile)
  - Fields should be snake_case (e.g., user_id)
  - Services should be PascalCase ending with 'Service'
  - RPC methods should be PascalCase (e.g., GetUser)
  - Packages should be lowercase with dots (e.g., users.v1)

BEST_PRACTICE
  - Missing language-specific options (go_package, java_package)
  - Field numbers > 15 (less efficient encoding)
  - Request/response type naming conventions
  - Missing reserved fields for deleted fields
  - Enum first value should be 0 with UNSPECIFIED suffix

BREAKING_CHANGE
  - Deleted messages or services
  - Deleted RPC methods
  - Changed field types
  - Deleted fields (should be reserved)
  - Reused field numbers
        """)
        sys.exit(0)

    # Validate proto file
    validator = ProtoValidator()
    proto, issues = validator.validate_file(args.proto_file)

    # Check breaking changes if requested
    if args.check_breaking:
        if not args.baseline:
            print("Error: --baseline required when using --check-breaking", file=sys.stderr)
            sys.exit(1)

        baseline_proto, _ = validator.validate_file(args.baseline)
        if baseline_proto and proto:
            breaking_changes = validator.check_breaking_changes(baseline_proto, proto)
            issues.extend(breaking_changes)

    # Output results
    if args.json:
        print(format_issues_json(proto, issues))
    else:
        print(format_issues_text(issues))

    # Exit with error code if there are errors
    error_count = len([i for i in issues if i.severity == 'error'])
    sys.exit(1 if error_count > 0 else 0)


if __name__ == '__main__':
    main()
