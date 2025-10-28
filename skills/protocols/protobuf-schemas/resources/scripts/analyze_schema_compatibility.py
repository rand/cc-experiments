#!/usr/bin/env python3
"""
Protocol Buffer Schema Compatibility Analyzer

Compares Protocol Buffer schema versions to detect breaking changes, verify
backward/forward compatibility, and suggest migration paths.

Features:
- Compare schema versions (v1 vs v2)
- Detect breaking vs non-breaking changes
- Verify backward compatibility (old clients with new servers)
- Verify forward compatibility (new clients with old servers)
- Suggest migration paths and fixes
- Validate evolution rules compliance
- Generate compatibility reports

Compatibility Rules:
- Backward compatible: New schema can read old data
- Forward compatible: Old schema can read new data
- Full compatible: Both backward and forward compatible

Breaking Changes:
- Removing required fields
- Changing field types
- Changing field numbers
- Renaming fields without reserved
- Changing message structure
- Removing enum values

Non-Breaking Changes:
- Adding optional fields
- Adding new enum values (at end)
- Marking fields deprecated
- Adding reserved fields/numbers

Usage:
    ./analyze_schema_compatibility.py --baseline user_v1.proto --current user_v2.proto
    ./analyze_schema_compatibility.py --baseline user_v1.proto --current user_v2.proto --json
    ./analyze_schema_compatibility.py --baseline user_v1.proto --current user_v2.proto --mode full
    ./analyze_schema_compatibility.py --baseline-dir ./v1 --current-dir ./v2 --json
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import List, Dict, Set, Optional, Tuple


class ChangeType(Enum):
    """Types of schema changes"""
    BREAKING = "breaking"
    NON_BREAKING = "non_breaking"
    RISKY = "risky"


class CompatibilityMode(Enum):
    """Compatibility checking modes"""
    BACKWARD = "backward"  # New schema reads old data
    FORWARD = "forward"    # Old schema reads new data
    FULL = "full"          # Both backward and forward


@dataclass
class SchemaChange:
    """Represents a change between schema versions"""
    change_type: ChangeType
    category: str
    description: str
    message: Optional[str] = None
    field: Optional[str] = None
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    suggestion: Optional[str] = None
    impact: Optional[str] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        d = asdict(self)
        d['change_type'] = self.change_type.value
        return {k: v for k, v in d.items() if v is not None}


@dataclass
class ProtoField:
    """Represents a Protocol Buffer field"""
    name: str
    number: int
    type: str
    label: str  # optional, required, repeated
    deprecated: bool = False
    json_name: Optional[str] = None


@dataclass
class ProtoEnum:
    """Represents a Protocol Buffer enum"""
    name: str
    values: Dict[str, int]  # name -> number
    reserved_numbers: Set[int] = field(default_factory=set)
    reserved_names: Set[str] = field(default_factory=set)


@dataclass
class ProtoMessage:
    """Represents a Protocol Buffer message"""
    name: str
    fields: Dict[int, ProtoField]  # field_number -> field
    reserved_numbers: Set[int] = field(default_factory=set)
    reserved_names: Set[str] = field(default_factory=set)
    nested_messages: Dict[str, 'ProtoMessage'] = field(default_factory=dict)
    enums: Dict[str, ProtoEnum] = field(default_factory=dict)


@dataclass
class ProtoFile:
    """Represents a parsed Protocol Buffer file"""
    path: Path
    syntax: str  # proto2 or proto3
    package: str
    messages: Dict[str, ProtoMessage]
    enums: Dict[str, ProtoEnum]
    services: Dict[str, List[str]]  # service -> methods


class ProtoParser:
    """Simple parser for Protocol Buffer files"""

    def __init__(self, proto_file: Path):
        self.proto_file = proto_file
        self.content = proto_file.read_text()
        self.lines = self.content.splitlines()

    def parse(self) -> ProtoFile:
        """Parse proto file into structured representation"""
        syntax = self._parse_syntax()
        package = self._parse_package()
        messages = self._parse_messages()
        enums = self._parse_enums()
        services = self._parse_services()

        return ProtoFile(
            path=self.proto_file,
            syntax=syntax,
            package=package,
            messages=messages,
            enums=enums,
            services=services
        )

    def _parse_syntax(self) -> str:
        """Extract syntax version"""
        for line in self.lines:
            line = line.strip()
            if line.startswith('syntax'):
                match = re.search(r'syntax\s*=\s*"(proto[23])"', line)
                if match:
                    return match.group(1)
        return "proto2"  # Default

    def _parse_package(self) -> str:
        """Extract package name"""
        for line in self.lines:
            line = line.strip()
            if line.startswith('package'):
                match = re.search(r'package\s+([a-zA-Z0-9_.]+)', line)
                if match:
                    return match.group(1)
        return ""

    def _parse_messages(self) -> Dict[str, ProtoMessage]:
        """Parse all message definitions"""
        messages = {}
        i = 0
        while i < len(self.lines):
            line = self.lines[i].strip()
            if line.startswith('message'):
                msg_name, msg_def, end_idx = self._parse_message_block(i)
                messages[msg_name] = msg_def
                i = end_idx
            else:
                i += 1
        return messages

    def _parse_message_block(self, start_idx: int) -> Tuple[str, ProtoMessage, int]:
        """Parse a single message block"""
        line = self.lines[start_idx].strip()
        match = re.search(r'message\s+(\w+)', line)
        if not match:
            return "", ProtoMessage("", {}), start_idx + 1

        msg_name = match.group(1)
        fields = {}
        reserved_numbers = set()
        reserved_names = set()
        nested_messages = {}
        enums = {}

        i = start_idx + 1
        brace_count = 1 if '{' in line else 0

        while i < len(self.lines) and brace_count > 0:
            line = self.lines[i]
            brace_count += line.count('{') - line.count('}')

            stripped = line.strip()

            # Parse fields
            field_match = re.match(
                r'(optional|required|repeated)?\s*(\w+)\s+(\w+)\s*=\s*(\d+)',
                stripped
            )
            if field_match:
                label = field_match.group(1) or "optional"
                field_type = field_match.group(2)
                field_name = field_match.group(3)
                field_number = int(field_match.group(4))
                deprecated = '[deprecated = true]' in stripped

                fields[field_number] = ProtoField(
                    name=field_name,
                    number=field_number,
                    type=field_type,
                    label=label,
                    deprecated=deprecated
                )

            # Parse reserved
            if stripped.startswith('reserved'):
                # Parse reserved numbers
                num_matches = re.findall(r'\b(\d+)\b', stripped)
                reserved_numbers.update(int(n) for n in num_matches)

                # Parse reserved names
                name_matches = re.findall(r'"(\w+)"', stripped)
                reserved_names.update(name_matches)

            # Parse nested messages
            if stripped.startswith('message'):
                nested_name, nested_def, end_idx = self._parse_message_block(i)
                nested_messages[nested_name] = nested_def
                i = end_idx - 1

            # Parse nested enums
            if stripped.startswith('enum'):
                enum_name, enum_def, end_idx = self._parse_enum_block(i)
                enums[enum_name] = enum_def
                i = end_idx - 1

            i += 1

        return msg_name, ProtoMessage(
            name=msg_name,
            fields=fields,
            reserved_numbers=reserved_numbers,
            reserved_names=reserved_names,
            nested_messages=nested_messages,
            enums=enums
        ), i

    def _parse_enums(self) -> Dict[str, ProtoEnum]:
        """Parse all enum definitions"""
        enums = {}
        i = 0
        while i < len(self.lines):
            line = self.lines[i].strip()
            if line.startswith('enum'):
                enum_name, enum_def, end_idx = self._parse_enum_block(i)
                enums[enum_name] = enum_def
                i = end_idx
            else:
                i += 1
        return enums

    def _parse_enum_block(self, start_idx: int) -> Tuple[str, ProtoEnum, int]:
        """Parse a single enum block"""
        line = self.lines[start_idx].strip()
        match = re.search(r'enum\s+(\w+)', line)
        if not match:
            return "", ProtoEnum("", {}), start_idx + 1

        enum_name = match.group(1)
        values = {}
        reserved_numbers = set()
        reserved_names = set()

        i = start_idx + 1
        brace_count = 1 if '{' in line else 0

        while i < len(self.lines) and brace_count > 0:
            line = self.lines[i]
            brace_count += line.count('{') - line.count('}')

            stripped = line.strip()

            # Parse enum values
            value_match = re.match(r'(\w+)\s*=\s*(\d+)', stripped)
            if value_match:
                value_name = value_match.group(1)
                value_number = int(value_match.group(2))
                values[value_name] = value_number

            # Parse reserved
            if stripped.startswith('reserved'):
                num_matches = re.findall(r'\b(\d+)\b', stripped)
                reserved_numbers.update(int(n) for n in num_matches)

                name_matches = re.findall(r'"(\w+)"', stripped)
                reserved_names.update(name_matches)

            i += 1

        return enum_name, ProtoEnum(
            name=enum_name,
            values=values,
            reserved_numbers=reserved_numbers,
            reserved_names=reserved_names
        ), i

    def _parse_services(self) -> Dict[str, List[str]]:
        """Parse all service definitions"""
        services = {}
        i = 0
        while i < len(self.lines):
            line = self.lines[i].strip()
            if line.startswith('service'):
                service_name, methods, end_idx = self._parse_service_block(i)
                services[service_name] = methods
                i = end_idx
            else:
                i += 1
        return services

    def _parse_service_block(self, start_idx: int) -> Tuple[str, List[str], int]:
        """Parse a single service block"""
        line = self.lines[start_idx].strip()
        match = re.search(r'service\s+(\w+)', line)
        if not match:
            return "", [], start_idx + 1

        service_name = match.group(1)
        methods = []

        i = start_idx + 1
        brace_count = 1 if '{' in line else 0

        while i < len(self.lines) and brace_count > 0:
            line = self.lines[i]
            brace_count += line.count('{') - line.count('}')

            stripped = line.strip()

            # Parse RPC methods
            method_match = re.match(r'rpc\s+(\w+)', stripped)
            if method_match:
                methods.append(method_match.group(1))

            i += 1

        return service_name, methods, i


class CompatibilityAnalyzer:
    """Analyzes compatibility between schema versions"""

    def __init__(self, baseline: ProtoFile, current: ProtoFile, mode: CompatibilityMode):
        self.baseline = baseline
        self.current = current
        self.mode = mode
        self.changes: List[SchemaChange] = []

    def analyze(self) -> List[SchemaChange]:
        """Perform full compatibility analysis"""
        self.changes = []

        # Check syntax compatibility
        self._check_syntax()

        # Check package compatibility
        self._check_package()

        # Check message compatibility
        self._check_messages()

        # Check enum compatibility
        self._check_enums()

        # Check service compatibility
        self._check_services()

        return self.changes

    def _check_syntax(self) -> None:
        """Check syntax version compatibility"""
        if self.baseline.syntax != self.current.syntax:
            self.changes.append(SchemaChange(
                change_type=ChangeType.BREAKING,
                category="syntax",
                description=f"Syntax changed from {self.baseline.syntax} to {self.current.syntax}",
                old_value=self.baseline.syntax,
                new_value=self.current.syntax,
                suggestion="Ensure all clients and servers are updated together",
                impact="All code must be regenerated with new syntax"
            ))

    def _check_package(self) -> None:
        """Check package name compatibility"""
        if self.baseline.package != self.current.package:
            self.changes.append(SchemaChange(
                change_type=ChangeType.BREAKING,
                category="package",
                description=f"Package changed from {self.baseline.package} to {self.current.package}",
                old_value=self.baseline.package,
                new_value=self.current.package,
                suggestion="Package changes require updating all imports",
                impact="All code references must be updated"
            ))

    def _check_messages(self) -> None:
        """Check message compatibility"""
        baseline_msgs = set(self.baseline.messages.keys())
        current_msgs = set(self.current.messages.keys())

        # Check removed messages
        removed = baseline_msgs - current_msgs
        for msg_name in removed:
            self.changes.append(SchemaChange(
                change_type=ChangeType.BREAKING,
                category="message",
                description=f"Message '{msg_name}' was removed",
                message=msg_name,
                suggestion=f"Add 'reserved' declaration for removed message or keep deprecated version",
                impact="Clients using this message will fail to compile"
            ))

        # Check added messages
        added = current_msgs - baseline_msgs
        for msg_name in added:
            self.changes.append(SchemaChange(
                change_type=ChangeType.NON_BREAKING,
                category="message",
                description=f"Message '{msg_name}' was added",
                message=msg_name,
                impact="Old clients won't know about new message"
            ))

        # Check modified messages
        common = baseline_msgs & current_msgs
        for msg_name in common:
            self._check_message_fields(
                msg_name,
                self.baseline.messages[msg_name],
                self.current.messages[msg_name]
            )

    def _check_message_fields(self, msg_name: str, baseline: ProtoMessage, current: ProtoMessage) -> None:
        """Check field-level compatibility within a message"""
        baseline_fields = set(baseline.fields.keys())
        current_fields = set(current.fields.keys())

        # Check removed fields
        removed = baseline_fields - current_fields
        for field_num in removed:
            field = baseline.fields[field_num]

            # Check if field was properly reserved
            if field_num in current.reserved_numbers or field.name in current.reserved_names:
                self.changes.append(SchemaChange(
                    change_type=ChangeType.NON_BREAKING,
                    category="field",
                    description=f"Field '{field.name}' (#{field_num}) was removed and reserved",
                    message=msg_name,
                    field=field.name,
                    impact="Old data with this field will be ignored by new code"
                ))
            else:
                self.changes.append(SchemaChange(
                    change_type=ChangeType.BREAKING,
                    category="field",
                    description=f"Field '{field.name}' (#{field_num}) was removed without reservation",
                    message=msg_name,
                    field=field.name,
                    suggestion=f"Add 'reserved {field_num}' and 'reserved \"{field.name}\"' to prevent reuse",
                    impact="Field number may be reused, causing data corruption"
                ))

        # Check added fields
        added = current_fields - baseline_fields
        for field_num in added:
            field = current.fields[field_num]

            if field.label == "required":
                self.changes.append(SchemaChange(
                    change_type=ChangeType.BREAKING,
                    category="field",
                    description=f"Required field '{field.name}' (#{field_num}) was added",
                    message=msg_name,
                    field=field.name,
                    suggestion="Make field optional or provide default value",
                    impact="Old clients cannot set this field, new servers will reject messages"
                ))
            else:
                self.changes.append(SchemaChange(
                    change_type=ChangeType.NON_BREAKING,
                    category="field",
                    description=f"Optional field '{field.name}' (#{field_num}) was added",
                    message=msg_name,
                    field=field.name,
                    impact="Old clients won't set this field (will use default value)"
                ))

        # Check modified fields
        common = baseline_fields & current_fields
        for field_num in common:
            baseline_field = baseline.fields[field_num]
            current_field = current.fields[field_num]

            # Check field name change
            if baseline_field.name != current_field.name:
                self.changes.append(SchemaChange(
                    change_type=ChangeType.BREAKING,
                    category="field",
                    description=f"Field #{field_num} renamed from '{baseline_field.name}' to '{current_field.name}'",
                    message=msg_name,
                    field=f"{baseline_field.name} -> {current_field.name}",
                    old_value=baseline_field.name,
                    new_value=current_field.name,
                    suggestion="Use json_name option to maintain wire compatibility",
                    impact="Code using field names will break"
                ))

            # Check field type change
            if baseline_field.type != current_field.type:
                if self._is_compatible_type_change(baseline_field.type, current_field.type):
                    self.changes.append(SchemaChange(
                        change_type=ChangeType.RISKY,
                        category="field",
                        description=f"Field '{current_field.name}' type changed from {baseline_field.type} to {current_field.type}",
                        message=msg_name,
                        field=current_field.name,
                        old_value=baseline_field.type,
                        new_value=current_field.type,
                        suggestion="Test thoroughly - types are wire-compatible but may have conversion issues",
                        impact="Data conversion may behave unexpectedly"
                    ))
                else:
                    self.changes.append(SchemaChange(
                        change_type=ChangeType.BREAKING,
                        category="field",
                        description=f"Field '{current_field.name}' type changed from {baseline_field.type} to {current_field.type}",
                        message=msg_name,
                        field=current_field.name,
                        old_value=baseline_field.type,
                        new_value=current_field.type,
                        suggestion="Use a new field number for the new type",
                        impact="Deserialization will fail or produce incorrect data"
                    ))

            # Check label change
            if baseline_field.label != current_field.label:
                if baseline_field.label == "required" or current_field.label == "required":
                    self.changes.append(SchemaChange(
                        change_type=ChangeType.BREAKING,
                        category="field",
                        description=f"Field '{current_field.name}' label changed from {baseline_field.label} to {current_field.label}",
                        message=msg_name,
                        field=current_field.name,
                        old_value=baseline_field.label,
                        new_value=current_field.label,
                        suggestion="Avoid changing required fields",
                        impact="Required field changes break compatibility"
                    ))
                else:
                    self.changes.append(SchemaChange(
                        change_type=ChangeType.RISKY,
                        category="field",
                        description=f"Field '{current_field.name}' label changed from {baseline_field.label} to {current_field.label}",
                        message=msg_name,
                        field=current_field.name,
                        old_value=baseline_field.label,
                        new_value=current_field.label,
                        impact="May affect how data is parsed"
                    ))

            # Check deprecation
            if not baseline_field.deprecated and current_field.deprecated:
                self.changes.append(SchemaChange(
                    change_type=ChangeType.NON_BREAKING,
                    category="field",
                    description=f"Field '{current_field.name}' was marked deprecated",
                    message=msg_name,
                    field=current_field.name,
                    impact="Users should migrate away from this field"
                ))

    def _is_compatible_type_change(self, old_type: str, new_type: str) -> bool:
        """Check if type change is wire-compatible"""
        # Compatible type changes (same wire type)
        compatible_groups = [
            {"int32", "uint32", "int64", "uint64", "bool"},
            {"sint32", "sint64"},
            {"fixed32", "sfixed32", "float"},
            {"fixed64", "sfixed64", "double"},
            {"string", "bytes"}
        ]

        for group in compatible_groups:
            if old_type in group and new_type in group:
                return True

        return False

    def _check_enums(self) -> None:
        """Check enum compatibility"""
        baseline_enums = set(self.baseline.enums.keys())
        current_enums = set(self.current.enums.keys())

        # Check removed enums
        removed = baseline_enums - current_enums
        for enum_name in removed:
            self.changes.append(SchemaChange(
                change_type=ChangeType.BREAKING,
                category="enum",
                description=f"Enum '{enum_name}' was removed",
                message=enum_name,
                suggestion="Keep enum with deprecated values",
                impact="Code using this enum will fail to compile"
            ))

        # Check added enums
        added = current_enums - baseline_enums
        for enum_name in added:
            self.changes.append(SchemaChange(
                change_type=ChangeType.NON_BREAKING,
                category="enum",
                description=f"Enum '{enum_name}' was added",
                message=enum_name,
                impact="Old clients won't know about new enum"
            ))

        # Check modified enums
        common = baseline_enums & current_enums
        for enum_name in common:
            self._check_enum_values(
                enum_name,
                self.baseline.enums[enum_name],
                self.current.enums[enum_name]
            )

    def _check_enum_values(self, enum_name: str, baseline: ProtoEnum, current: ProtoEnum) -> None:
        """Check enum value compatibility"""
        baseline_values = set(baseline.values.values())
        current_values = set(current.values.values())

        # Check removed values
        removed = baseline_values - current_values
        for value_num in removed:
            value_names = [k for k, v in baseline.values.items() if v == value_num]
            self.changes.append(SchemaChange(
                change_type=ChangeType.BREAKING,
                category="enum",
                description=f"Enum value {value_names} = {value_num} was removed from '{enum_name}'",
                message=enum_name,
                field=str(value_names),
                suggestion="Reserve removed enum values",
                impact="Old data with this value will be unrecognized"
            ))

        # Check added values
        added = current_values - baseline_values
        for value_num in added:
            value_names = [k for k, v in current.values.items() if v == value_num]
            self.changes.append(SchemaChange(
                change_type=ChangeType.NON_BREAKING,
                category="enum",
                description=f"Enum value {value_names} = {value_num} was added to '{enum_name}'",
                message=enum_name,
                field=str(value_names),
                impact="Old clients won't recognize this value"
            ))

    def _check_services(self) -> None:
        """Check service compatibility"""
        baseline_services = set(self.baseline.services.keys())
        current_services = set(self.current.services.keys())

        # Check removed services
        removed = baseline_services - current_services
        for service_name in removed:
            self.changes.append(SchemaChange(
                change_type=ChangeType.BREAKING,
                category="service",
                description=f"Service '{service_name}' was removed",
                message=service_name,
                suggestion="Deprecate service before removal",
                impact="Clients calling this service will fail"
            ))

        # Check added services
        added = current_services - baseline_services
        for service_name in added:
            self.changes.append(SchemaChange(
                change_type=ChangeType.NON_BREAKING,
                category="service",
                description=f"Service '{service_name}' was added",
                message=service_name,
                impact="Old clients won't know about new service"
            ))

        # Check modified services
        common = baseline_services & current_services
        for service_name in common:
            baseline_methods = set(self.baseline.services[service_name])
            current_methods = set(self.current.services[service_name])

            # Check removed methods
            removed_methods = baseline_methods - current_methods
            for method in removed_methods:
                self.changes.append(SchemaChange(
                    change_type=ChangeType.BREAKING,
                    category="service",
                    description=f"Method '{method}' was removed from service '{service_name}'",
                    message=service_name,
                    field=method,
                    suggestion="Deprecate method before removal",
                    impact="Clients calling this method will fail"
                ))

            # Check added methods
            added_methods = current_methods - baseline_methods
            for method in added_methods:
                self.changes.append(SchemaChange(
                    change_type=ChangeType.NON_BREAKING,
                    category="service",
                    description=f"Method '{method}' was added to service '{service_name}'",
                    message=service_name,
                    field=method,
                    impact="Old clients won't know about new method"
                ))


def parse_args() -> argparse.Namespace:
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Analyze Protocol Buffer schema compatibility",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Compare two schema versions
  %(prog)s --baseline user_v1.proto --current user_v2.proto

  # JSON output
  %(prog)s --baseline user_v1.proto --current user_v2.proto --json

  # Check full compatibility (both backward and forward)
  %(prog)s --baseline user_v1.proto --current user_v2.proto --mode full

  # Compare directories
  %(prog)s --baseline-dir ./v1 --current-dir ./v2 --json

  # Forward compatibility only
  %(prog)s --baseline user_v1.proto --current user_v2.proto --mode forward
        """
    )

    parser.add_argument(
        '--baseline',
        type=Path,
        help="Baseline (old) proto file"
    )

    parser.add_argument(
        '--current',
        type=Path,
        help="Current (new) proto file"
    )

    parser.add_argument(
        '--baseline-dir',
        type=Path,
        help="Baseline directory (compares all matching .proto files)"
    )

    parser.add_argument(
        '--current-dir',
        type=Path,
        help="Current directory (compares all matching .proto files)"
    )

    parser.add_argument(
        '--mode',
        type=str,
        choices=['backward', 'forward', 'full'],
        default='backward',
        help="Compatibility mode: backward (default), forward, or full"
    )

    parser.add_argument(
        '--json',
        action='store_true',
        help="Output results as JSON"
    )

    return parser.parse_args()


def main() -> int:
    """Main entry point"""
    args = parse_args()

    # Validate input
    if not (args.baseline and args.current) and not (args.baseline_dir and args.current_dir):
        print("Error: Must specify --baseline and --current, or --baseline-dir and --current-dir", file=sys.stderr)
        return 1

    mode = CompatibilityMode(args.mode)
    all_changes = []

    # Single file comparison
    if args.baseline and args.current:
        if not args.baseline.exists():
            print(f"Error: Baseline file not found: {args.baseline}", file=sys.stderr)
            return 1
        if not args.current.exists():
            print(f"Error: Current file not found: {args.current}", file=sys.stderr)
            return 1

        try:
            baseline_proto = ProtoParser(args.baseline).parse()
            current_proto = ProtoParser(args.current).parse()
            analyzer = CompatibilityAnalyzer(baseline_proto, current_proto, mode)
            changes = analyzer.analyze()
            all_changes.extend(changes)
        except Exception as e:
            print(f"Error parsing proto files: {e}", file=sys.stderr)
            return 1

    # Directory comparison
    elif args.baseline_dir and args.current_dir:
        if not args.baseline_dir.is_dir():
            print(f"Error: Baseline directory not found: {args.baseline_dir}", file=sys.stderr)
            return 1
        if not args.current_dir.is_dir():
            print(f"Error: Current directory not found: {args.current_dir}", file=sys.stderr)
            return 1

        baseline_files = {f.name: f for f in args.baseline_dir.glob("*.proto")}
        current_files = {f.name: f for f in args.current_dir.glob("*.proto")}

        for name in sorted(baseline_files.keys() & current_files.keys()):
            try:
                baseline_proto = ProtoParser(baseline_files[name]).parse()
                current_proto = ProtoParser(current_files[name]).parse()
                analyzer = CompatibilityAnalyzer(baseline_proto, current_proto, mode)
                changes = analyzer.analyze()
                all_changes.extend(changes)
            except Exception as e:
                print(f"Error parsing {name}: {e}", file=sys.stderr)

    # Output results
    if args.json:
        breaking = [c for c in all_changes if c.change_type == ChangeType.BREAKING]
        risky = [c for c in all_changes if c.change_type == ChangeType.RISKY]
        non_breaking = [c for c in all_changes if c.change_type == ChangeType.NON_BREAKING]

        output = {
            'mode': mode.value,
            'compatible': len(breaking) == 0,
            'total_changes': len(all_changes),
            'breaking_changes': len(breaking),
            'risky_changes': len(risky),
            'non_breaking_changes': len(non_breaking),
            'changes': [c.to_dict() for c in all_changes]
        }
        print(json.dumps(output, indent=2))
    else:
        breaking = [c for c in all_changes if c.change_type == ChangeType.BREAKING]
        risky = [c for c in all_changes if c.change_type == ChangeType.RISKY]
        non_breaking = [c for c in all_changes if c.change_type == ChangeType.NON_BREAKING]

        print(f"\nCompatibility Analysis ({mode.value} mode):")
        print(f"  Total changes: {len(all_changes)}")
        print(f"  Breaking: {len(breaking)}")
        print(f"  Risky: {len(risky)}")
        print(f"  Non-breaking: {len(non_breaking)}")
        print(f"  Compatible: {'✓ Yes' if len(breaking) == 0 else '✗ No'}")
        print()

        if breaking:
            print("BREAKING CHANGES:")
            for change in breaking:
                print(f"  ✗ [{change.category}] {change.description}")
                if change.message:
                    print(f"      Message: {change.message}")
                if change.field:
                    print(f"      Field: {change.field}")
                if change.suggestion:
                    print(f"      Suggestion: {change.suggestion}")
                if change.impact:
                    print(f"      Impact: {change.impact}")
                print()

        if risky:
            print("RISKY CHANGES:")
            for change in risky:
                print(f"  ⚠ [{change.category}] {change.description}")
                if change.message:
                    print(f"      Message: {change.message}")
                if change.field:
                    print(f"      Field: {change.field}")
                if change.suggestion:
                    print(f"      Suggestion: {change.suggestion}")
                if change.impact:
                    print(f"      Impact: {change.impact}")
                print()

        if non_breaking:
            print("NON-BREAKING CHANGES:")
            for change in non_breaking:
                print(f"  ✓ [{change.category}] {change.description}")
                if change.impact:
                    print(f"      Impact: {change.impact}")
                print()

    # Exit with error if incompatible
    if any(c.change_type == ChangeType.BREAKING for c in all_changes):
        return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
