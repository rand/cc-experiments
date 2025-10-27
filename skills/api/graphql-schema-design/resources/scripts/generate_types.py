#!/usr/bin/env python3
"""
GraphQL TypeScript Type Generator

Generates TypeScript type definitions from GraphQL schemas.
Supports interfaces, unions, enums, and input types.
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, List, Dict


@dataclass
class TypeDefinition:
    """Represents a GraphQL type"""
    name: str
    kind: str  # object, interface, union, enum, input, scalar
    fields: Optional[Dict[str, str]] = None
    implements: Optional[List[str]] = None
    union_types: Optional[List[str]] = None
    enum_values: Optional[List[str]] = None
    description: Optional[str] = None

    def __post_init__(self):
        if self.fields is None:
            self.fields = {}
        if self.implements is None:
            self.implements = []
        if self.union_types is None:
            self.union_types = []
        if self.enum_values is None:
            self.enum_values = []


class TypeScriptGenerator:
    """Generate TypeScript definitions from GraphQL schema"""

    def __init__(self, schema_content: str, nullable_by_default: bool = False):
        self.schema = schema_content
        self.lines = schema_content.split('\n')
        self.types: Dict[str, TypeDefinition] = {}
        self.nullable_by_default = nullable_by_default

    def parse(self):
        """Parse GraphQL schema"""
        i = 0
        while i < len(self.lines):
            line = self.lines[i].strip()

            # Skip empty lines and comments
            if not line or line.startswith('#'):
                i += 1
                continue

            # Parse type definitions
            if match := re.match(r'^(type|interface|union|enum|input|scalar)\s+(\w+)', line):
                kind, name = match.groups()
                description = self._get_description(i)
                i = self._parse_type(i, kind, name, description)
            else:
                i += 1

    def _get_description(self, line_num: int) -> Optional[str]:
        """Extract description from previous lines"""
        if line_num == 0:
            return None

        # Check for triple-quote description
        prev_line = self.lines[line_num - 1].strip()
        if '"""' in prev_line:
            # Extract description
            desc_lines = []
            j = line_num - 1
            while j >= 0:
                line = self.lines[j].strip()
                if '"""' in line:
                    desc_lines.insert(0, line.replace('"""', '').strip())
                    if line.count('"""') == 2:  # Single-line description
                        break
                    j -= 1
                    while j >= 0 and '"""' not in self.lines[j]:
                        desc_lines.insert(0, self.lines[j].strip())
                        j -= 1
                    break
                j -= 1
            return ' '.join(desc_lines).strip() if desc_lines else None
        return None

    def _parse_type(self, start: int, kind: str, name: str, description: Optional[str]) -> int:
        """Parse a type definition"""
        typedef = TypeDefinition(name=name, kind=kind, description=description)

        if kind == 'scalar':
            self.types[name] = typedef
            return start + 1

        if kind == 'enum':
            i = start + 1
            while i < len(self.lines):
                line = self.lines[i].strip()
                if '}' in line:
                    break
                if line and not line.startswith('#'):
                    # Extract enum value
                    if match := re.match(r'^(\w+)', line):
                        typedef.enum_values.append(match.group(1))
                i += 1
            self.types[name] = typedef
            return i + 1

        if kind == 'union':
            # Parse union types
            line = self.lines[start]
            if match := re.search(r'=\s*(.+)', line):
                union_str = match.group(1)
                typedef.union_types = [
                    t.strip() for t in union_str.split('|')
                ]
            self.types[name] = typedef
            return start + 1

        # Parse object/interface/input type
        line = self.lines[start]
        if match := re.search(r'implements\s+([\w\s&]+)', line):
            typedef.implements = [
                t.strip() for t in match.group(1).replace('&', ' ').split()
            ]

        i = start + 1
        while i < len(self.lines):
            line = self.lines[i].strip()
            if '}' in line:
                break

            # Parse field
            if match := re.match(r'^(\w+)\s*(\([^)]*\))?\s*:\s*(.+)', line):
                field_name = match.group(1)
                field_type = match.group(3).strip()

                # Remove directives
                field_type = re.sub(r'@\w+(\([^)]*\))?', '', field_type).strip()

                typedef.fields[field_name] = field_type

            i += 1

        self.types[name] = typedef
        return i + 1

    def generate(self) -> str:
        """Generate TypeScript definitions"""
        self.parse()

        lines = [
            "/**",
            " * Generated TypeScript types from GraphQL schema",
            " * DO NOT EDIT MANUALLY",
            " */",
            "",
        ]

        # Generate custom scalars
        scalar_types = [t for t in self.types.values() if t.kind == 'scalar']
        if scalar_types:
            lines.append("// Custom Scalars")
            for typedef in scalar_types:
                ts_type = self._map_scalar_to_ts(typedef.name)
                if typedef.description:
                    lines.append(f"/** {typedef.description} */")
                lines.append(f"export type {typedef.name} = {ts_type};")
            lines.append("")

        # Generate enums
        enum_types = [t for t in self.types.values() if t.kind == 'enum']
        if enum_types:
            lines.append("// Enums")
            for typedef in enum_types:
                if typedef.description:
                    lines.append(f"/** {typedef.description} */")
                lines.append(f"export enum {typedef.name} {{")
                for value in typedef.enum_values:
                    lines.append(f"  {value} = '{value}',")
                lines.append("}")
                lines.append("")

        # Generate interfaces
        interface_types = [t for t in self.types.values() if t.kind == 'interface']
        if interface_types:
            lines.append("// Interfaces")
            for typedef in interface_types:
                if typedef.description:
                    lines.append(f"/** {typedef.description} */")
                lines.append(f"export interface {typedef.name} {{")
                for field_name, field_type in typedef.fields.items():
                    ts_type = self._graphql_to_ts_type(field_type)
                    lines.append(f"  {field_name}: {ts_type};")
                lines.append("}")
                lines.append("")

        # Generate unions
        union_types = [t for t in self.types.values() if t.kind == 'union']
        if union_types:
            lines.append("// Unions")
            for typedef in union_types:
                if typedef.description:
                    lines.append(f"/** {typedef.description} */")
                union_str = ' | '.join(typedef.union_types)
                lines.append(f"export type {typedef.name} = {union_str};")
                lines.append("")

        # Generate input types
        input_types = [t for t in self.types.values() if t.kind == 'input']
        if input_types:
            lines.append("// Input Types")
            for typedef in input_types:
                if typedef.description:
                    lines.append(f"/** {typedef.description} */")
                lines.append(f"export interface {typedef.name} {{")
                for field_name, field_type in typedef.fields.items():
                    ts_type = self._graphql_to_ts_type(field_type)
                    lines.append(f"  {field_name}: {ts_type};")
                lines.append("}")
                lines.append("")

        # Generate object types
        object_types = [
            t for t in self.types.values()
            if t.kind in ('type', 'object') and t.name not in ('Query', 'Mutation', 'Subscription')
        ]
        if object_types:
            lines.append("// Object Types")
            for typedef in object_types:
                if typedef.description:
                    lines.append(f"/** {typedef.description} */")

                # Handle interface implementation
                extends = ""
                if typedef.implements:
                    extends = f" extends {', '.join(typedef.implements)}"

                lines.append(f"export interface {typedef.name}{extends} {{")
                for field_name, field_type in typedef.fields.items():
                    ts_type = self._graphql_to_ts_type(field_type)
                    lines.append(f"  {field_name}: {ts_type};")
                lines.append("}")
                lines.append("")

        # Generate Query/Mutation/Subscription types
        for op_name in ['Query', 'Mutation', 'Subscription']:
            if op_name in self.types:
                typedef = self.types[op_name]
                lines.append(f"// {op_name}")
                lines.append(f"export interface {op_name} {{")
                for field_name, field_type in typedef.fields.items():
                    ts_type = self._graphql_to_ts_type(field_type)
                    lines.append(f"  {field_name}: {ts_type};")
                lines.append("}")
                lines.append("")

        return '\n'.join(lines)

    def _map_scalar_to_ts(self, scalar_name: str) -> str:
        """Map GraphQL scalar to TypeScript type"""
        mapping = {
            'Int': 'number',
            'Float': 'number',
            'String': 'string',
            'Boolean': 'boolean',
            'ID': 'string',
            'DateTime': 'string',
            'Date': 'string',
            'Time': 'string',
            'JSON': 'any',
            'JSONObject': 'Record<string, any>',
            'Email': 'string',
            'URL': 'string',
            'UUID': 'string',
        }
        return mapping.get(scalar_name, 'any')

    def _graphql_to_ts_type(self, graphql_type: str) -> str:
        """Convert GraphQL type to TypeScript type"""
        graphql_type = graphql_type.strip()

        # Handle non-null types
        is_required = graphql_type.endswith('!')
        if is_required:
            graphql_type = graphql_type[:-1]

        # Handle list types
        is_list = graphql_type.startswith('[') and graphql_type.endswith(']')
        if is_list:
            inner_type = graphql_type[1:-1]
            inner_ts_type = self._graphql_to_ts_type(inner_type)
            ts_type = f"Array<{inner_ts_type}>"
        else:
            # Map scalar or use type name
            ts_type = self._map_scalar_to_ts(graphql_type)
            if ts_type == 'any' and graphql_type in self.types:
                ts_type = graphql_type

        # Handle nullability
        if not is_required and not self.nullable_by_default:
            ts_type = f"{ts_type} | null"

        return ts_type


def main():
    parser = argparse.ArgumentParser(
        description='Generate TypeScript types from GraphQL schema',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s schema.graphql -o types.ts
  %(prog)s schema.graphql --nullable-by-default
  cat schema.graphql | %(prog)s - --json
        """
    )

    parser.add_argument(
        'schema_file',
        help='GraphQL schema file (use - for stdin)'
    )
    parser.add_argument(
        '-o', '--output',
        help='Output file (default: stdout)'
    )
    parser.add_argument(
        '--nullable-by-default',
        action='store_true',
        help='Make fields nullable by default (opposite of GraphQL)'
    )
    parser.add_argument(
        '--json',
        action='store_true',
        help='Output type information as JSON'
    )

    args = parser.parse_args()

    # Read schema
    try:
        if args.schema_file == '-':
            schema_content = sys.stdin.read()
        else:
            schema_path = Path(args.schema_file)
            if not schema_path.exists():
                print(f"Error: File not found: {args.schema_file}", file=sys.stderr)
                return 1
            schema_content = schema_path.read_text()
    except Exception as e:
        print(f"Error reading schema: {e}", file=sys.stderr)
        return 1

    # Generate types
    generator = TypeScriptGenerator(schema_content, args.nullable_by_default)

    if args.json:
        generator.parse()
        output = json.dumps({
            'types': [
                {
                    'name': t.name,
                    'kind': t.kind,
                    'fields': t.fields,
                    'implements': t.implements,
                    'union_types': t.union_types,
                    'enum_values': t.enum_values,
                    'description': t.description,
                }
                for t in generator.types.values()
            ]
        }, indent=2)
    else:
        output = generator.generate()

    # Write output
    try:
        if args.output:
            Path(args.output).write_text(output)
            print(f"Generated types written to {args.output}", file=sys.stderr)
        else:
            print(output)
    except Exception as e:
        print(f"Error writing output: {e}", file=sys.stderr)
        return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
