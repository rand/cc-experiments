#!/usr/bin/env python3
"""
DSPy Signature Code Generator

Generate Rust struct definitions from DSPy signatures with full serde support
and conversion methods. Supports type annotations, complex types, and validation.

Usage:
    python signature_codegen.py generate "question, context -> answer" --module QA
    python signature_codegen.py generate-from-file module.py --class QAModule
    python signature_codegen.py validate generated.rs
    python signature_codegen.py list-types
"""

import sys
import re
import ast
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class FieldSpec:
    """Specification for a single field."""
    name: str
    python_type: str
    rust_type: str
    is_optional: bool
    description: Optional[str] = None


@dataclass
class SignatureSpec:
    """Complete signature specification."""
    module_name: str
    input_fields: List[FieldSpec]
    output_fields: List[FieldSpec]
    raw_signature: str


class TypeMapper:
    """Maps Python types to Rust types with support for complex types."""

    # Basic type mappings
    BASIC_TYPES = {
        'str': 'String',
        'int': 'i64',
        'float': 'f64',
        'bool': 'bool',
        'None': '()',
        'bytes': 'Vec<u8>',
    }

    @classmethod
    def map_type(cls, python_type: str) -> Tuple[str, bool]:
        """Map Python type to Rust type.

        Args:
            python_type: Python type string (e.g., "str", "List[str]", "Optional[int]")

        Returns:
            (rust_type, is_optional) tuple
        """
        python_type = python_type.strip()
        is_optional = False

        # Handle None/NoneType
        if python_type in ('None', 'NoneType'):
            return '()', False

        # Handle basic types
        if python_type in cls.BASIC_TYPES:
            return cls.BASIC_TYPES[python_type], False

        # Handle Optional[T]
        if python_type.startswith('Optional['):
            inner = python_type[9:-1]
            inner_type, _ = cls.map_type(inner)
            return f"Option<{inner_type}>", True

        # Handle Union[T, None] syntax
        if python_type.startswith('Union['):
            inner = python_type[6:-1]
            parts = cls._split_type_args(inner)
            # Check if it's Optional (Union with None)
            if 'None' in parts:
                non_none = [p for p in parts if p.strip() != 'None']
                if len(non_none) == 1:
                    inner_type, _ = cls.map_type(non_none[0])
                    return f"Option<{inner_type}>", True
            # Non-optional union - use first type as fallback
            first_type, _ = cls.map_type(parts[0])
            return first_type, False

        # Handle List[T]
        if python_type.startswith(('List[', 'list[')):
            start = python_type.index('[') + 1
            inner = python_type[start:-1]
            inner_type, _ = cls.map_type(inner)
            return f"Vec<{inner_type}>", False

        # Handle Dict[K, V]
        if python_type.startswith(('Dict[', 'dict[')):
            start = python_type.index('[') + 1
            inner = python_type[start:-1]
            parts = cls._split_type_args(inner)
            if len(parts) == 2:
                key_type, _ = cls.map_type(parts[0])
                val_type, _ = cls.map_type(parts[1])
                return f"HashMap<{key_type}, {val_type}>", False
            return 'HashMap<String, String>', False

        # Handle Tuple[T1, T2, ...]
        if python_type.startswith(('Tuple[', 'tuple[')):
            start = python_type.index('[') + 1
            inner = python_type[start:-1]
            parts = cls._split_type_args(inner)
            rust_types = [cls.map_type(p)[0] for p in parts]
            return f"({', '.join(rust_types)})", False

        # Handle Set/HashSet
        if python_type.startswith(('Set[', 'set[')):
            start = python_type.index('[') + 1
            inner = python_type[start:-1]
            inner_type, _ = cls.map_type(inner)
            return f"HashSet<{inner_type}>", False

        # Handle Any
        if python_type == 'Any':
            return 'serde_json::Value', False

        # Default to String for unknown types
        return 'String', False

    @staticmethod
    def _split_type_args(type_str: str) -> List[str]:
        """Split type arguments handling nested brackets.

        Args:
            type_str: Type arguments string (e.g., "str, int")

        Returns:
            List of type argument strings
        """
        parts = []
        current = []
        depth = 0

        for char in type_str:
            if char == '[':
                depth += 1
                current.append(char)
            elif char == ']':
                depth -= 1
                current.append(char)
            elif char == ',' and depth == 0:
                parts.append(''.join(current).strip())
                current = []
            else:
                current.append(char)

        if current:
            parts.append(''.join(current).strip())

        return parts


class SignatureParser:
    """Parse DSPy signature strings into structured specifications."""

    @staticmethod
    def parse_signature(signature: str, module_name: str = "Module") -> SignatureSpec:
        """Parse a DSPy signature string.

        Args:
            signature: Signature string (e.g., "question, context -> answer")
            module_name: Name for the module

        Returns:
            SignatureSpec object
        """
        # Split on arrow
        parts = signature.split('->')
        if len(parts) != 2:
            raise ValueError(f"Invalid signature format: {signature}")

        input_str = parts[0].strip()
        output_str = parts[1].strip()

        # Parse input fields (handle commas inside brackets)
        input_fields = []
        if input_str:
            for field_def in SignatureParser._split_fields(input_str):
                field_spec = SignatureParser._parse_field(field_def.strip())
                input_fields.append(field_spec)

        # Parse output fields (handle commas inside brackets)
        output_fields = []
        if output_str:
            for field_def in SignatureParser._split_fields(output_str):
                field_spec = SignatureParser._parse_field(field_def.strip())
                output_fields.append(field_spec)

        return SignatureSpec(
            module_name=module_name,
            input_fields=input_fields,
            output_fields=output_fields,
            raw_signature=signature
        )

    @staticmethod
    def _split_fields(fields_str: str) -> List[str]:
        """Split field definitions handling nested brackets.

        Args:
            fields_str: Field definitions string

        Returns:
            List of field definition strings
        """
        fields = []
        current = []
        depth = 0

        for char in fields_str:
            if char == '[':
                depth += 1
                current.append(char)
            elif char == ']':
                depth -= 1
                current.append(char)
            elif char == ',' and depth == 0:
                fields.append(''.join(current).strip())
                current = []
            else:
                current.append(char)

        if current:
            fields.append(''.join(current).strip())

        return fields

    @staticmethod
    def _parse_field(field_def: str) -> FieldSpec:
        """Parse a field definition with optional type annotation.

        Args:
            field_def: Field string (e.g., "question: str" or "answer")

        Returns:
            FieldSpec object
        """
        # Check for type annotation
        if ':' in field_def:
            name, type_str = field_def.split(':', 1)
            name = name.strip()
            type_str = type_str.strip()
        else:
            name = field_def.strip()
            type_str = 'str'  # Default to str

        # Map type
        rust_type, is_optional = TypeMapper.map_type(type_str)

        return FieldSpec(
            name=name,
            python_type=type_str,
            rust_type=rust_type,
            is_optional=is_optional
        )

    @staticmethod
    def parse_from_python_module(source_path: str, class_name: str) -> SignatureSpec:
        """Extract signature from Python DSPy module source.

        Args:
            source_path: Path to Python file
            class_name: Name of module class

        Returns:
            SignatureSpec object
        """
        with open(source_path) as f:
            source = f.read()

        tree = ast.parse(source)

        # Find class definition
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == class_name:
                return SignatureParser._extract_signature_from_class(node, class_name)

        raise ValueError(f"Class {class_name} not found in {source_path}")

    @staticmethod
    def _extract_signature_from_class(node: ast.ClassDef, class_name: str) -> SignatureSpec:
        """Extract signature from class AST node.

        Args:
            node: AST ClassDef node
            class_name: Name of the class

        Returns:
            SignatureSpec object
        """
        # Look for signature in __init__ or as class attribute
        signature_str = None

        # Check __init__ for signature assignment
        for item in node.body:
            if isinstance(item, ast.FunctionDef) and item.name == '__init__':
                for stmt in item.body:
                    if isinstance(stmt, ast.Assign):
                        for target in stmt.targets:
                            if (isinstance(target, ast.Attribute) and
                                target.attr in ('signature', 'generate', 'predict')):
                                # Try to extract signature string
                                if isinstance(stmt.value, ast.Call):
                                    for arg in stmt.value.args:
                                        if isinstance(arg, ast.Constant):
                                            signature_str = arg.value
                                            break

        if not signature_str:
            raise ValueError(f"Could not find signature in {class_name}")

        return SignatureParser.parse_signature(signature_str, class_name)


class RustCodeGenerator:
    """Generate Rust code from signature specifications."""

    @staticmethod
    def generate(spec: SignatureSpec) -> str:
        """Generate complete Rust module from specification.

        Args:
            spec: SignatureSpec object

        Returns:
            Rust code as string
        """
        lines = []

        # Header comment
        lines.append(f"// Generated Rust types for {spec.module_name}")
        lines.append(f"// Source signature: {spec.raw_signature}")
        lines.append("// DO NOT EDIT - Generated by signature_codegen.py")
        lines.append("")

        # Imports
        imports = RustCodeGenerator._generate_imports(spec)
        lines.extend(imports)
        lines.append("")

        # Input struct
        if spec.input_fields:
            input_struct = RustCodeGenerator._generate_struct(
                f"{spec.module_name}Input",
                spec.input_fields,
                "Input parameters for DSPy module"
            )
            lines.extend(input_struct)
            lines.append("")

            # Input impl
            input_impl = RustCodeGenerator._generate_input_impl(
                f"{spec.module_name}Input",
                spec.input_fields
            )
            lines.extend(input_impl)
            lines.append("")

        # Output struct
        if spec.output_fields:
            output_struct = RustCodeGenerator._generate_struct(
                f"{spec.module_name}Output",
                spec.output_fields,
                "Output from DSPy module"
            )
            lines.extend(output_struct)
            lines.append("")

            # Output impl
            output_impl = RustCodeGenerator._generate_output_impl(
                f"{spec.module_name}Output",
                spec.output_fields
            )
            lines.extend(output_impl)
            lines.append("")

        return '\n'.join(lines)

    @staticmethod
    def _generate_imports(spec: SignatureSpec) -> List[str]:
        """Generate import statements based on types used."""
        imports = [
            "use pyo3::prelude::*;",
            "use serde::{Deserialize, Serialize};",
        ]

        all_fields = spec.input_fields + spec.output_fields
        all_types = ' '.join(f.rust_type for f in all_fields)

        if 'HashMap' in all_types:
            imports.append("use std::collections::HashMap;")
        if 'HashSet' in all_types:
            imports.append("use std::collections::HashSet;")
        if 'serde_json::Value' in all_types:
            imports.append("use serde_json::Value;")

        return imports

    @staticmethod
    def _generate_struct(name: str, fields: List[FieldSpec], doc: str) -> List[str]:
        """Generate struct definition."""
        lines = []

        lines.append(f"/// {doc}")
        lines.append("#[derive(Debug, Clone, Serialize, Deserialize)]")
        lines.append(f"pub struct {name} {{")

        for field in fields:
            if field.description:
                lines.append(f"    /// {field.description}")
            lines.append(f"    pub {field.name}: {field.rust_type},")

        lines.append("}")

        return lines

    @staticmethod
    def _generate_input_impl(struct_name: str, fields: List[FieldSpec]) -> List[str]:
        """Generate impl block for input struct with to_py_dict method."""
        lines = []

        lines.append(f"impl {struct_name} {{")
        lines.append("    /// Convert to Python dict for DSPy")
        lines.append("    pub fn to_py_dict(&self, py: Python) -> PyResult<Py<PyAny>> {")
        lines.append("        let dict = pyo3::types::PyDict::new(py);")

        for field in fields:
            if field.is_optional:
                # Handle Option types
                lines.append(f"        if let Some(ref val) = self.{field.name} {{")
                lines.append(f"            dict.set_item(\"{field.name}\", val)?;")
                lines.append("        }")
            else:
                lines.append(f"        dict.set_item(\"{field.name}\", &self.{field.name})?;")

        lines.append("        Ok(dict.into())")
        lines.append("    }")
        lines.append("}")

        return lines

    @staticmethod
    def _generate_output_impl(struct_name: str, fields: List[FieldSpec]) -> List[str]:
        """Generate impl block for output struct with from_py_prediction method."""
        lines = []

        lines.append(f"impl {struct_name} {{")
        lines.append("    /// Extract from Python prediction")
        lines.append("    pub fn from_py_prediction(prediction: &PyAny) -> PyResult<Self> {")
        lines.append("        Ok(Self {")

        for field in fields:
            if field.is_optional:
                # Handle Option types with safe extraction
                lines.append(f"            {field.name}: prediction")
                lines.append(f"                .getattr(\"{field.name}\")")
                lines.append("                .ok()")
                lines.append("                .and_then(|attr| attr.extract().ok()),")
            else:
                lines.append(f"            {field.name}: prediction.getattr(\"{field.name}\")?.extract()?,")

        lines.append("        })")
        lines.append("    }")
        lines.append("}")

        return lines


class RustValidator:
    """Validate generated Rust code."""

    @staticmethod
    def validate(rust_code: str) -> Tuple[bool, List[str]]:
        """Basic validation of Rust code.

        Args:
            rust_code: Rust source code

        Returns:
            (is_valid, list_of_issues)
        """
        issues = []

        # Check for required imports
        if 'use pyo3::prelude::*;' not in rust_code:
            issues.append("Missing PyO3 import")

        if 'use serde::{Deserialize, Serialize};' not in rust_code:
            issues.append("Missing serde imports")

        # Check for struct definitions
        if not re.search(r'pub struct \w+Input', rust_code):
            issues.append("Missing Input struct definition")

        if not re.search(r'pub struct \w+Output', rust_code):
            issues.append("Missing Output struct definition")

        # Check for required methods
        if 'fn to_py_dict' not in rust_code:
            issues.append("Missing to_py_dict method")

        if 'fn from_py_prediction' not in rust_code:
            issues.append("Missing from_py_prediction method")

        # Check for proper derives
        if '#[derive(Debug, Clone, Serialize, Deserialize)]' not in rust_code:
            issues.append("Missing required derives")

        return len(issues) == 0, issues


def cmd_generate(args):
    """Generate Rust code from signature string."""
    try:
        signature = args.signature
        module_name = args.module or "Module"

        # Parse signature
        spec = SignatureParser.parse_signature(signature, module_name)

        # Generate Rust code
        rust_code = RustCodeGenerator.generate(spec)

        print(rust_code)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_generate_from_file(args):
    """Generate Rust code from Python module file."""
    try:
        source_path = args.file
        class_name = args.class_name

        # Parse module
        spec = SignatureParser.parse_from_python_module(source_path, class_name)

        # Generate Rust code
        rust_code = RustCodeGenerator.generate(spec)

        print(rust_code)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_validate(args):
    """Validate generated Rust code."""
    try:
        rust_file = args.rust_file

        with open(rust_file) as f:
            rust_code = f.read()

        is_valid, issues = RustValidator.validate(rust_code)

        if is_valid:
            print(f"✓ {rust_file} is valid")
            sys.exit(0)
        else:
            print(f"✗ {rust_file} has validation issues:")
            for issue in issues:
                print(f"  - {issue}")
            sys.exit(1)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_list_types(args):
    """List supported type mappings."""
    print("\nSupported Type Mappings:\n")
    print("=" * 60)
    print("\nPrimitive Types:")
    for py_type, rust_type in TypeMapper.BASIC_TYPES.items():
        print(f"  {py_type:15} -> {rust_type}")

    print("\nCollection Types:")
    print(f"  {'List[T]':15} -> Vec<T>")
    print(f"  {'Dict[K, V]':15} -> HashMap<K, V>")
    print(f"  {'Set[T]':15} -> HashSet<T>")
    print(f"  {'Tuple[T1, T2]':15} -> (T1, T2)")

    print("\nOptional Types:")
    print(f"  {'Optional[T]':15} -> Option<T>")
    print(f"  {'Union[T, None]':15} -> Option<T>")

    print("\nSpecial Types:")
    print(f"  {'Any':15} -> serde_json::Value")

    print("\n" + "=" * 60)

    print("\nExamples:")
    examples = [
        ("str", "String"),
        ("int", "i64"),
        ("Optional[str]", "Option<String>"),
        ("List[str]", "Vec<String>"),
        ("Dict[str, int]", "HashMap<String, i64>"),
        ("List[Optional[str]]", "Vec<Option<String>>"),
        ("Tuple[str, int, float]", "(String, i64, f64)"),
    ]

    for py_type, expected_rust in examples:
        rust_type, _ = TypeMapper.map_type(py_type)
        print(f"  {py_type:25} -> {rust_type}")

    print()


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate Rust types from DSPy signatures"
    )
    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # Generate command
    p_generate = subparsers.add_parser('generate', help='Generate from signature string')
    p_generate.add_argument('signature', help='Signature string (e.g., "q -> a")')
    p_generate.add_argument('--module', help='Module name (default: Module)')

    # Generate from file command
    p_gen_file = subparsers.add_parser('generate-from-file', help='Generate from Python file')
    p_gen_file.add_argument('file', help='Path to Python module file')
    p_gen_file.add_argument('--class', dest='class_name', required=True,
                           help='Class name to extract')

    # Validate command
    p_validate = subparsers.add_parser('validate', help='Validate Rust code')
    p_validate.add_argument('rust_file', help='Path to Rust file')

    # List types command
    p_list = subparsers.add_parser('list-types', help='List supported type mappings')

    args = parser.parse_args()

    if args.command == 'generate':
        cmd_generate(args)
    elif args.command == 'generate-from-file':
        cmd_generate_from_file(args)
    elif args.command == 'validate':
        cmd_validate(args)
    elif args.command == 'list-types':
        cmd_list_types(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
