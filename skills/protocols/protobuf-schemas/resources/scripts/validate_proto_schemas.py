#!/usr/bin/env python3
"""
Protocol Buffer Schema Validator

Validates Protocol Buffer schema files for:
- Syntax errors and parsing issues
- Field number conflicts and reserved ranges
- Naming convention violations
- Best practices (enum zero values, field number efficiency, etc.)
- Breaking changes between versions
- Import validation

Usage:
    ./validate_proto_schemas.py --proto-file user.proto
    ./validate_proto_schemas.py --proto-file user.proto --json
    ./validate_proto_schemas.py --proto-file user_v2.proto --check-breaking --baseline user_v1.proto
    ./validate_proto_schemas.py --proto-dir ./protos --json
"""

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import List, Dict, Set, Optional, Tuple


class Severity(Enum):
    """Validation issue severity levels"""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationIssue:
    """Represents a validation issue"""
    severity: Severity
    category: str
    message: str
    file: str
    line: Optional[int] = None
    field: Optional[str] = None
    suggestion: Optional[str] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        d = asdict(self)
        d['severity'] = self.severity.value
        return d


@dataclass
class ProtoField:
    """Represents a Protocol Buffer field"""
    name: str
    number: int
    type: str
    label: str  # optional, required, repeated
    line: int
    deprecated: bool = False


@dataclass
class ProtoEnum:
    """Represents a Protocol Buffer enum"""
    name: str
    values: Dict[str, int]  # name -> number
    line: int


@dataclass
class ProtoMessage:
    """Represents a Protocol Buffer message"""
    name: str
    fields: List[ProtoField]
    reserved_numbers: Set[int]
    reserved_names: Set[str]
    nested_messages: List['ProtoMessage']
    enums: List[ProtoEnum]
    line: int


@dataclass
class ProtoService:
    """Represents a Protocol Buffer service"""
    name: str
    methods: List[str]
    line: int


@dataclass
class ProtoFile:
    """Represents a parsed Protocol Buffer file"""
    path: str
    syntax: str  # proto2 or proto3
    package: str
    imports: List[str]
    messages: List[ProtoMessage]
    enums: List[ProtoEnum]
    services: List[ProtoService]
    options: Dict[str, str]


class ProtoParser:
    """Parser for Protocol Buffer files"""

    def __init__(self, file_path: str):
        self.file_path = file_path
        self.lines = []
        self.current_line = 0

    def parse(self) -> ProtoFile:
        """Parse a .proto file"""
        with open(self.file_path, 'r') as f:
            self.lines = f.readlines()

        proto_file = ProtoFile(
            path=self.file_path,
            syntax="proto2",  # Default
            package="",
            imports=[],
            messages=[],
            enums=[],
            services=[],
            options={}
        )

        for i, line in enumerate(self.lines):
            line = line.strip()
            if not line or line.startswith('//'):
                continue

            # Remove inline comments
            if '//' in line:
                line = line[:line.index('//')]

            # Parse syntax
            if line.startswith('syntax'):
                match = re.match(r'syntax\s*=\s*"(proto[23])"\s*;', line)
                if match:
                    proto_file.syntax = match.group(1)

            # Parse package
            elif line.startswith('package'):
                match = re.match(r'package\s+([\w.]+)\s*;', line)
                if match:
                    proto_file.package = match.group(1)

            # Parse imports
            elif line.startswith('import'):
                match = re.match(r'import\s+"([^"]+)"\s*;', line)
                if match:
                    proto_file.imports.append(match.group(1))

            # Parse options
            elif line.startswith('option'):
                match = re.match(r'option\s+([\w.]+)\s*=\s*"([^"]+)"\s*;', line)
                if match:
                    proto_file.options[match.group(1)] = match.group(2)

            # Parse messages (simplified)
            elif line.startswith('message'):
                message = self._parse_message(i)
                if message:
                    proto_file.messages.append(message)

            # Parse enums (top-level)
            elif line.startswith('enum'):
                enum = self._parse_enum(i)
                if enum:
                    proto_file.enums.append(enum)

            # Parse services
            elif line.startswith('service'):
                service = self._parse_service(i)
                if service:
                    proto_file.services.append(service)

        return proto_file

    def _parse_message(self, start_line: int) -> Optional[ProtoMessage]:
        """Parse a message definition"""
        line = self.lines[start_line].strip()
        match = re.match(r'message\s+(\w+)\s*\{', line)
        if not match:
            return None

        message_name = match.group(1)
        fields = []
        reserved_numbers = set()
        reserved_names = set()
        nested_messages = []
        enums = []

        i = start_line + 1
        brace_count = 1

        while i < len(self.lines) and brace_count > 0:
            line = self.lines[i].strip()

            if '{' in line:
                brace_count += line.count('{')
            if '}' in line:
                brace_count -= line.count('}')

            if brace_count == 0:
                break

            # Parse field
            if line and not line.startswith('//'):
                # Remove inline comments
                if '//' in line:
                    line = line[:line.index('//')]

                # Parse reserved numbers
                if line.startswith('reserved'):
                    reserved_numbers.update(self._parse_reserved_numbers(line))
                    reserved_names.update(self._parse_reserved_names(line))

                # Parse field definition
                elif '=' in line:
                    field_match = re.match(
                        r'(optional|required|repeated)?\s*(\w+(?:\.\w+)*)\s+(\w+)\s*=\s*(\d+)',
                        line
                    )
                    if field_match:
                        label = field_match.group(1) or 'optional'
                        field_type = field_match.group(2)
                        field_name = field_match.group(3)
                        field_number = int(field_match.group(4))

                        deprecated = '[deprecated = true]' in line or '[deprecated=true]' in line

                        fields.append(ProtoField(
                            name=field_name,
                            number=field_number,
                            type=field_type,
                            label=label,
                            line=i + 1,
                            deprecated=deprecated
                        ))

                # Parse nested message
                elif line.startswith('message'):
                    nested = self._parse_message(i)
                    if nested:
                        nested_messages.append(nested)

                # Parse nested enum
                elif line.startswith('enum'):
                    enum = self._parse_enum(i)
                    if enum:
                        enums.append(enum)

            i += 1

        return ProtoMessage(
            name=message_name,
            fields=fields,
            reserved_numbers=reserved_numbers,
            reserved_names=reserved_names,
            nested_messages=nested_messages,
            enums=enums,
            line=start_line + 1
        )

    def _parse_enum(self, start_line: int) -> Optional[ProtoEnum]:
        """Parse an enum definition"""
        line = self.lines[start_line].strip()
        match = re.match(r'enum\s+(\w+)\s*\{', line)
        if not match:
            return None

        enum_name = match.group(1)
        values = {}

        i = start_line + 1
        while i < len(self.lines):
            line = self.lines[i].strip()

            if '}' in line:
                break

            # Parse enum value
            if '=' in line and not line.startswith('//'):
                # Remove inline comments
                if '//' in line:
                    line = line[:line.index('//')]

                value_match = re.match(r'(\w+)\s*=\s*(\d+)', line)
                if value_match:
                    value_name = value_match.group(1)
                    value_number = int(value_match.group(2))
                    values[value_name] = value_number

            i += 1

        return ProtoEnum(
            name=enum_name,
            values=values,
            line=start_line + 1
        )

    def _parse_service(self, start_line: int) -> Optional[ProtoService]:
        """Parse a service definition"""
        line = self.lines[start_line].strip()
        match = re.match(r'service\s+(\w+)\s*\{', line)
        if not match:
            return None

        service_name = match.group(1)
        methods = []

        i = start_line + 1
        while i < len(self.lines):
            line = self.lines[i].strip()

            if '}' in line:
                break

            # Parse RPC method
            if line.startswith('rpc'):
                method_match = re.match(r'rpc\s+(\w+)', line)
                if method_match:
                    methods.append(method_match.group(1))

            i += 1

        return ProtoService(
            name=service_name,
            methods=methods,
            line=start_line + 1
        )

    def _parse_reserved_numbers(self, line: str) -> Set[int]:
        """Parse reserved field numbers"""
        numbers = set()

        # Match: reserved 1, 2, 3;
        single_pattern = r'reserved\s+([\d,\s]+);'
        match = re.match(single_pattern, line)
        if match:
            number_str = match.group(1)
            for num in number_str.split(','):
                num = num.strip()
                if num.isdigit():
                    numbers.add(int(num))

        # Match: reserved 1 to 10;
        range_pattern = r'reserved\s+(\d+)\s+to\s+(\d+)'
        match = re.search(range_pattern, line)
        if match:
            start = int(match.group(1))
            end = int(match.group(2))
            numbers.update(range(start, end + 1))

        return numbers

    def _parse_reserved_names(self, line: str) -> Set[str]:
        """Parse reserved field names"""
        names = set()

        # Match: reserved "name1", "name2";
        pattern = r'"(\w+)"'
        matches = re.findall(pattern, line)
        names.update(matches)

        return names


class ProtoValidator:
    """Validator for Protocol Buffer schemas"""

    def __init__(self):
        self.issues: List[ValidationIssue] = []

    def validate(self, proto_file: ProtoFile) -> List[ValidationIssue]:
        """Validate a Protocol Buffer file"""
        self.issues = []

        # Syntax validation
        self._validate_syntax(proto_file)

        # Package validation
        self._validate_package(proto_file)

        # Message validation
        for message in proto_file.messages:
            self._validate_message(proto_file, message)

        # Enum validation
        for enum in proto_file.enums:
            self._validate_enum(proto_file, enum)

        # Service validation
        for service in proto_file.services:
            self._validate_service(proto_file, service)

        # Import validation
        self._validate_imports(proto_file)

        # Options validation
        self._validate_options(proto_file)

        return self.issues

    def _validate_syntax(self, proto_file: ProtoFile):
        """Validate syntax declaration"""
        if not proto_file.syntax:
            self.issues.append(ValidationIssue(
                severity=Severity.ERROR,
                category="syntax",
                message="Missing syntax declaration",
                file=proto_file.path,
                suggestion="Add 'syntax = \"proto3\";' at the top of the file"
            ))

        if proto_file.syntax == "proto2":
            self.issues.append(ValidationIssue(
                severity=Severity.WARNING,
                category="syntax",
                message="Using proto2 syntax (proto3 recommended)",
                file=proto_file.path,
                suggestion="Migrate to proto3 for better performance and features"
            ))

    def _validate_package(self, proto_file: ProtoFile):
        """Validate package declaration"""
        if not proto_file.package:
            self.issues.append(ValidationIssue(
                severity=Severity.WARNING,
                category="package",
                message="Missing package declaration",
                file=proto_file.path,
                suggestion="Add package declaration (e.g., 'package users.v1;')"
            ))
        else:
            # Check package naming convention (lowercase, versioned)
            if not re.match(r'^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)*$', proto_file.package):
                self.issues.append(ValidationIssue(
                    severity=Severity.WARNING,
                    category="naming",
                    message=f"Package name '{proto_file.package}' should be lowercase",
                    file=proto_file.path,
                    suggestion="Use lowercase package names (e.g., 'users.v1')"
                ))

            # Check for version suffix
            if not re.search(r'\.v\d+$', proto_file.package):
                self.issues.append(ValidationIssue(
                    severity=Severity.INFO,
                    category="versioning",
                    message=f"Package '{proto_file.package}' lacks version suffix",
                    file=proto_file.path,
                    suggestion="Add version suffix (e.g., '.v1') for better versioning"
                ))

    def _validate_message(self, proto_file: ProtoFile, message: ProtoMessage, parent: str = ""):
        """Validate a message definition"""
        full_name = f"{parent}.{message.name}" if parent else message.name

        # Check message naming (PascalCase)
        if not re.match(r'^[A-Z][A-Za-z0-9]*$', message.name):
            self.issues.append(ValidationIssue(
                severity=Severity.WARNING,
                category="naming",
                message=f"Message name '{full_name}' should be PascalCase",
                file=proto_file.path,
                line=message.line,
                suggestion=f"Rename to {self._to_pascal_case(message.name)}"
            ))

        # Validate fields
        field_numbers = set()
        for field in message.fields:
            self._validate_field(proto_file, message, field, full_name)
            field_numbers.add(field.number)

        # Check for field number conflicts
        self._check_field_number_conflicts(proto_file, message, field_numbers)

        # Check reserved fields
        self._check_reserved_usage(proto_file, message, field_numbers)

        # Validate nested messages
        for nested in message.nested_messages:
            self._validate_message(proto_file, nested, full_name)

        # Validate nested enums
        for enum in message.enums:
            self._validate_enum(proto_file, enum, full_name)

    def _validate_field(self, proto_file: ProtoFile, message: ProtoMessage, field: ProtoField, parent: str):
        """Validate a field definition"""
        # Check field naming (snake_case)
        if not re.match(r'^[a-z][a-z0-9_]*$', field.name):
            self.issues.append(ValidationIssue(
                severity=Severity.WARNING,
                category="naming",
                message=f"Field '{parent}.{field.name}' should be snake_case",
                file=proto_file.path,
                line=field.line,
                suggestion=f"Rename to {self._to_snake_case(field.name)}"
            ))

        # Check field number range
        if field.number < 1:
            self.issues.append(ValidationIssue(
                severity=Severity.ERROR,
                category="field_number",
                message=f"Field '{parent}.{field.name}' has invalid number {field.number} (must be >= 1)",
                file=proto_file.path,
                line=field.line
            ))

        if field.number >= 19000 and field.number <= 19999:
            self.issues.append(ValidationIssue(
                severity=Severity.ERROR,
                category="field_number",
                message=f"Field '{parent}.{field.name}' uses reserved range 19000-19999",
                file=proto_file.path,
                line=field.line,
                suggestion="Use field numbers outside the reserved range"
            ))

        # Check field number efficiency (1-15 for frequent fields)
        if field.number > 15:
            self.issues.append(ValidationIssue(
                severity=Severity.INFO,
                category="performance",
                message=f"Field '{parent}.{field.name}' uses number {field.number} (>15, 2-byte tag)",
                file=proto_file.path,
                line=field.line,
                suggestion="Use field numbers 1-15 for frequently set fields (1-byte tag)"
            ))

        # Check proto2 required fields
        if proto_file.syntax == "proto2" and field.label == "required":
            self.issues.append(ValidationIssue(
                severity=Severity.WARNING,
                category="best_practice",
                message=f"Field '{parent}.{field.name}' is required (proto2 anti-pattern)",
                file=proto_file.path,
                line=field.line,
                suggestion="Avoid 'required' fields for better schema evolution"
            ))

    def _validate_enum(self, proto_file: ProtoFile, enum: ProtoEnum, parent: str = ""):
        """Validate an enum definition"""
        full_name = f"{parent}.{enum.name}" if parent else enum.name

        # Check enum naming (PascalCase)
        if not re.match(r'^[A-Z][A-Za-z0-9]*$', enum.name):
            self.issues.append(ValidationIssue(
                severity=Severity.WARNING,
                category="naming",
                message=f"Enum name '{full_name}' should be PascalCase",
                file=proto_file.path,
                line=enum.line,
                suggestion=f"Rename to {self._to_pascal_case(enum.name)}"
            ))

        # Check for zero value
        if 0 not in enum.values.values():
            self.issues.append(ValidationIssue(
                severity=Severity.ERROR,
                category="enum",
                message=f"Enum '{full_name}' missing zero value (required in proto3)",
                file=proto_file.path,
                line=enum.line,
                suggestion=f"Add '{enum.name.upper()}_UNSPECIFIED = 0' as first value"
            ))

        # Check enum value naming (UPPER_SNAKE_CASE with prefix)
        enum_prefix = enum.name.upper() + "_"
        for value_name in enum.values.keys():
            if not re.match(r'^[A-Z][A-Z0-9_]*$', value_name):
                self.issues.append(ValidationIssue(
                    severity=Severity.WARNING,
                    category="naming",
                    message=f"Enum value '{full_name}.{value_name}' should be UPPER_SNAKE_CASE",
                    file=proto_file.path,
                    line=enum.line,
                    suggestion=f"Rename to {value_name.upper()}"
                ))

            if not value_name.startswith(enum_prefix):
                self.issues.append(ValidationIssue(
                    severity=Severity.INFO,
                    category="naming",
                    message=f"Enum value '{full_name}.{value_name}' lacks prefix '{enum_prefix}'",
                    file=proto_file.path,
                    line=enum.line,
                    suggestion=f"Add prefix: {enum_prefix}{value_name}"
                ))

    def _validate_service(self, proto_file: ProtoFile, service: ProtoService):
        """Validate a service definition"""
        # Check service naming (PascalCase with 'Service' suffix)
        if not re.match(r'^[A-Z][A-Za-z0-9]*$', service.name):
            self.issues.append(ValidationIssue(
                severity=Severity.WARNING,
                category="naming",
                message=f"Service name '{service.name}' should be PascalCase",
                file=proto_file.path,
                line=service.line,
                suggestion=f"Rename to {self._to_pascal_case(service.name)}"
            ))

        if not service.name.endswith('Service'):
            self.issues.append(ValidationIssue(
                severity=Severity.INFO,
                category="naming",
                message=f"Service name '{service.name}' should end with 'Service'",
                file=proto_file.path,
                line=service.line,
                suggestion=f"Rename to {service.name}Service"
            ))

        # Check for empty services
        if not service.methods:
            self.issues.append(ValidationIssue(
                severity=Severity.WARNING,
                category="service",
                message=f"Service '{service.name}' has no methods",
                file=proto_file.path,
                line=service.line
            ))

    def _validate_imports(self, proto_file: ProtoFile):
        """Validate imports"""
        for import_path in proto_file.imports:
            # Check if import file exists (relative to current file)
            base_dir = os.path.dirname(proto_file.path)
            import_file = os.path.join(base_dir, import_path)

            if not os.path.exists(import_file):
                self.issues.append(ValidationIssue(
                    severity=Severity.WARNING,
                    category="import",
                    message=f"Import '{import_path}' not found",
                    file=proto_file.path,
                    suggestion=f"Check if file exists: {import_file}"
                ))

    def _validate_options(self, proto_file: ProtoFile):
        """Validate file options"""
        # Check for language-specific options
        recommended_options = {
            'go_package': 'Go',
            'java_package': 'Java',
            'java_multiple_files': 'Java'
        }

        for option, language in recommended_options.items():
            if option not in proto_file.options:
                self.issues.append(ValidationIssue(
                    severity=Severity.INFO,
                    category="options",
                    message=f"Missing option '{option}' for {language} code generation",
                    file=proto_file.path,
                    suggestion=f"Add 'option {option} = \"...\";'"
                ))

    def _check_field_number_conflicts(self, proto_file: ProtoFile, message: ProtoMessage, field_numbers: Set[int]):
        """Check for field number conflicts"""
        duplicates = []
        seen = {}

        for field in message.fields:
            if field.number in seen:
                duplicates.append((field, seen[field.number]))
            else:
                seen[field.number] = field

        for field1, field2 in duplicates:
            self.issues.append(ValidationIssue(
                severity=Severity.ERROR,
                category="field_number",
                message=f"Duplicate field number {field1.number} in message '{message.name}' (fields: {field1.name}, {field2.name})",
                file=proto_file.path,
                line=field1.line
            ))

    def _check_reserved_usage(self, proto_file: ProtoFile, message: ProtoMessage, field_numbers: Set[int]):
        """Check if fields use reserved numbers or names"""
        for field in message.fields:
            if field.number in message.reserved_numbers:
                self.issues.append(ValidationIssue(
                    severity=Severity.ERROR,
                    category="reserved",
                    message=f"Field '{field.name}' uses reserved number {field.number}",
                    file=proto_file.path,
                    line=field.line,
                    suggestion="Use a different field number"
                ))

            if field.name in message.reserved_names:
                self.issues.append(ValidationIssue(
                    severity=Severity.ERROR,
                    category="reserved",
                    message=f"Field name '{field.name}' is reserved",
                    file=proto_file.path,
                    line=field.line,
                    suggestion="Use a different field name"
                ))

    def _to_pascal_case(self, name: str) -> str:
        """Convert name to PascalCase"""
        words = re.split(r'[_\s]+', name)
        return ''.join(word.capitalize() for word in words)

    def _to_snake_case(self, name: str) -> str:
        """Convert name to snake_case"""
        # Insert underscore before uppercase letters
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()


class BreakingChangeDetector:
    """Detects breaking changes between schema versions"""

    def __init__(self, old_file: ProtoFile, new_file: ProtoFile):
        self.old_file = old_file
        self.new_file = new_file
        self.issues: List[ValidationIssue] = []

    def detect_breaking_changes(self) -> List[ValidationIssue]:
        """Detect breaking changes between two schema versions"""
        self.issues = []

        # Check package changes
        if self.old_file.package != self.new_file.package:
            self.issues.append(ValidationIssue(
                severity=Severity.ERROR,
                category="breaking",
                message=f"Package changed: '{self.old_file.package}' → '{self.new_file.package}'",
                file=self.new_file.path,
                suggestion="Package changes are breaking; use new version instead"
            ))

        # Check message changes
        self._check_message_changes()

        # Check enum changes
        self._check_enum_changes()

        # Check service changes
        self._check_service_changes()

        return self.issues

    def _check_message_changes(self):
        """Check for breaking changes in messages"""
        old_messages = {m.name: m for m in self.old_file.messages}
        new_messages = {m.name: m for m in self.new_file.messages}

        # Check deleted messages
        for name in old_messages:
            if name not in new_messages:
                self.issues.append(ValidationIssue(
                    severity=Severity.ERROR,
                    category="breaking",
                    message=f"Message '{name}' deleted (breaking change)",
                    file=self.new_file.path,
                    suggestion="Mark as deprecated instead of deleting"
                ))

        # Check field changes
        for name in old_messages:
            if name in new_messages:
                self._check_field_changes(old_messages[name], new_messages[name])

    def _check_field_changes(self, old_message: ProtoMessage, new_message: ProtoMessage):
        """Check for breaking changes in fields"""
        old_fields = {f.number: f for f in old_message.fields}
        new_fields = {f.number: f for f in new_message.fields}

        # Check deleted fields
        for number in old_fields:
            if number not in new_fields:
                if number not in new_message.reserved_numbers:
                    self.issues.append(ValidationIssue(
                        severity=Severity.ERROR,
                        category="breaking",
                        message=f"Field {number} ('{old_fields[number].name}') deleted in '{new_message.name}' without reservation",
                        file=self.new_file.path,
                        line=new_message.line,
                        suggestion=f"Add 'reserved {number};' and 'reserved \"{old_fields[number].name}\";'"
                    ))

        # Check field type changes
        for number in old_fields:
            if number in new_fields:
                old_field = old_fields[number]
                new_field = new_fields[number]

                if old_field.type != new_field.type:
                    self.issues.append(ValidationIssue(
                        severity=Severity.ERROR,
                        category="breaking",
                        message=f"Field {number} type changed: {old_field.type} → {new_field.type} in '{new_message.name}'",
                        file=self.new_file.path,
                        line=new_field.line,
                        suggestion="Type changes are breaking; use new field number"
                    ))

                if old_field.label != new_field.label:
                    self.issues.append(ValidationIssue(
                        severity=Severity.ERROR,
                        category="breaking",
                        message=f"Field {number} label changed: {old_field.label} → {new_field.label} in '{new_message.name}'",
                        file=self.new_file.path,
                        line=new_field.line,
                        suggestion="Label changes (repeated ↔ singular) are breaking"
                    ))

    def _check_enum_changes(self):
        """Check for breaking changes in enums"""
        old_enums = {e.name: e for e in self.old_file.enums}
        new_enums = {e.name: e for e in self.new_file.enums}

        # Check deleted enums
        for name in old_enums:
            if name not in new_enums:
                self.issues.append(ValidationIssue(
                    severity=Severity.ERROR,
                    category="breaking",
                    message=f"Enum '{name}' deleted (breaking change)",
                    file=self.new_file.path,
                    suggestion="Mark as deprecated instead of deleting"
                ))

        # Check enum value changes
        for name in old_enums:
            if name in new_enums:
                old_enum = old_enums[name]
                new_enum = new_enums[name]

                # Check for removed values
                for value_name, value_number in old_enum.values.items():
                    if value_name not in new_enum.values:
                        self.issues.append(ValidationIssue(
                            severity=Severity.WARNING,
                            category="breaking",
                            message=f"Enum value '{name}.{value_name}' removed",
                            file=self.new_file.path,
                            line=new_enum.line,
                            suggestion="Old clients may still send this value"
                        ))

                # Check for changed value numbers
                for value_name in old_enum.values:
                    if value_name in new_enum.values:
                        if old_enum.values[value_name] != new_enum.values[value_name]:
                            self.issues.append(ValidationIssue(
                                severity=Severity.ERROR,
                                category="breaking",
                                message=f"Enum value '{name}.{value_name}' number changed: {old_enum.values[value_name]} → {new_enum.values[value_name]}",
                                file=self.new_file.path,
                                line=new_enum.line,
                                suggestion="Value number changes are breaking"
                            ))

    def _check_service_changes(self):
        """Check for breaking changes in services"""
        old_services = {s.name: s for s in self.old_file.services}
        new_services = {s.name: s for s in self.new_file.services}

        # Check deleted services
        for name in old_services:
            if name not in new_services:
                self.issues.append(ValidationIssue(
                    severity=Severity.ERROR,
                    category="breaking",
                    message=f"Service '{name}' deleted (breaking change)",
                    file=self.new_file.path,
                    suggestion="Mark as deprecated instead of deleting"
                ))

        # Check method changes
        for name in old_services:
            if name in new_services:
                old_service = old_services[name]
                new_service = new_services[name]

                # Check for removed methods
                for method in old_service.methods:
                    if method not in new_service.methods:
                        self.issues.append(ValidationIssue(
                            severity=Severity.ERROR,
                            category="breaking",
                            message=f"Method '{name}.{method}' removed (breaking change)",
                            file=self.new_file.path,
                            line=new_service.line,
                            suggestion="Mark as deprecated instead of removing"
                        ))


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Validate Protocol Buffer schema files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --proto-file user.proto
  %(prog)s --proto-file user.proto --json
  %(prog)s --proto-file user_v2.proto --check-breaking --baseline user_v1.proto
  %(prog)s --proto-dir ./protos --json
        """
    )

    parser.add_argument(
        '--proto-file',
        help='Path to .proto file to validate'
    )

    parser.add_argument(
        '--proto-dir',
        help='Directory containing .proto files (validates all)'
    )

    parser.add_argument(
        '--check-breaking',
        action='store_true',
        help='Check for breaking changes'
    )

    parser.add_argument(
        '--baseline',
        help='Baseline .proto file for breaking change detection'
    )

    parser.add_argument(
        '--json',
        action='store_true',
        help='Output results as JSON'
    )

    parser.add_argument(
        '--severity',
        choices=['error', 'warning', 'info'],
        default='info',
        help='Minimum severity level to report (default: info)'
    )

    args = parser.parse_args()

    if not args.proto_file and not args.proto_dir:
        parser.error("Either --proto-file or --proto-dir must be specified")

    # Collect files to validate
    files_to_validate = []
    if args.proto_file:
        files_to_validate.append(args.proto_file)
    elif args.proto_dir:
        for root, dirs, files in os.walk(args.proto_dir):
            for file in files:
                if file.endswith('.proto'):
                    files_to_validate.append(os.path.join(root, file))

    # Validate files
    all_issues = []
    severity_threshold = Severity[args.severity.upper()]

    for file_path in files_to_validate:
        try:
            # Parse file
            parser_instance = ProtoParser(file_path)
            proto_file = parser_instance.parse()

            # Validate
            validator = ProtoValidator()
            issues = validator.validate(proto_file)

            # Check breaking changes if requested
            if args.check_breaking and args.baseline:
                baseline_parser = ProtoParser(args.baseline)
                baseline_file = baseline_parser.parse()

                detector = BreakingChangeDetector(baseline_file, proto_file)
                breaking_issues = detector.detect_breaking_changes()
                issues.extend(breaking_issues)

            # Filter by severity
            severity_order = {Severity.ERROR: 3, Severity.WARNING: 2, Severity.INFO: 1}
            threshold_value = severity_order[severity_threshold]
            issues = [i for i in issues if severity_order[i.severity] >= threshold_value]

            all_issues.extend(issues)

        except Exception as e:
            all_issues.append(ValidationIssue(
                severity=Severity.ERROR,
                category="parse_error",
                message=f"Failed to parse file: {str(e)}",
                file=file_path
            ))

    # Output results
    if args.json:
        output = {
            'files_validated': len(files_to_validate),
            'issues': [issue.to_dict() for issue in all_issues],
            'summary': {
                'errors': sum(1 for i in all_issues if i.severity == Severity.ERROR),
                'warnings': sum(1 for i in all_issues if i.severity == Severity.WARNING),
                'info': sum(1 for i in all_issues if i.severity == Severity.INFO)
            }
        }
        print(json.dumps(output, indent=2))
    else:
        print(f"Validated {len(files_to_validate)} file(s)\n")

        if not all_issues:
            print("✓ No issues found!")
        else:
            # Group by severity
            errors = [i for i in all_issues if i.severity == Severity.ERROR]
            warnings = [i for i in all_issues if i.severity == Severity.WARNING]
            info = [i for i in all_issues if i.severity == Severity.INFO]

            for severity_name, issues in [('ERRORS', errors), ('WARNINGS', warnings), ('INFO', info)]:
                if issues:
                    print(f"{severity_name} ({len(issues)}):")
                    for issue in issues:
                        location = f"{issue.file}:{issue.line}" if issue.line else issue.file
                        print(f"  [{issue.category}] {location}")
                        print(f"    {issue.message}")
                        if issue.suggestion:
                            print(f"    💡 {issue.suggestion}")
                        print()

            print(f"Summary: {len(errors)} errors, {len(warnings)} warnings, {len(info)} info")

    # Exit with error code if errors found
    error_count = sum(1 for i in all_issues if i.severity == Severity.ERROR)
    sys.exit(1 if error_count > 0 else 0)


if __name__ == '__main__':
    main()
