#!/usr/bin/env python3
"""
DSPy Module Inspector

Inspect DSPy module structure, generate Rust type definitions, and validate
module compatibility with PyO3.

Usage:
    python module_inspector.py inspect QAModule       # Inspect module
    python module_inspector.py codegen QAModule > types.rs  # Generate Rust types
    python module_inspector.py fields QAModule        # List fields
    python module_inspector.py validate QAModule      # Validate PyO3 compatibility
"""

import sys
import ast
import inspect
import json
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from dataclasses import dataclass, asdict


@dataclass
class SignatureField:
    """Represents a DSPy signature field."""
    name: str
    python_type: str
    is_input: bool
    is_output: bool
    description: Optional[str] = None
    default: Optional[Any] = None


@dataclass
class ModuleInfo:
    """Information about a DSPy module."""
    name: str
    signature: Optional[str]
    input_fields: List[SignatureField]
    output_fields: List[SignatureField]
    has_forward: bool
    base_classes: List[str]


class TypeMapper:
    """Maps Python types to Rust types."""

    # Basic type mappings
    BASIC_TYPES = {
        'str': 'String',
        'int': 'i64',
        'float': 'f64',
        'bool': 'bool',
        'None': '()',
    }

    # Collection type patterns
    COLLECTION_PATTERNS = {
        'List': ('Vec', 1),
        'list': ('Vec', 1),
        'Dict': ('HashMap', 2),
        'dict': ('HashMap', 2),
        'Set': ('HashSet', 1),
        'set': ('HashSet', 1),
        'Tuple': ('(', -1),  # Special handling
        'tuple': ('(', -1),
    }

    # Optional type pattern
    OPTIONAL_PATTERN = 'Optional'

    @classmethod
    def map_type(cls, python_type: str) -> str:
        """Map Python type annotation to Rust type.

        Args:
            python_type: Python type string (e.g., "str", "List[str]", "Optional[int]")

        Returns:
            Rust type string (e.g., "String", "Vec<String>", "Option<i64>")
        """
        # Handle None/NoneType
        if python_type in ('None', 'NoneType'):
            return '()'

        # Handle basic types
        if python_type in cls.BASIC_TYPES:
            return cls.BASIC_TYPES[python_type]

        # Handle Optional[T]
        if python_type.startswith('Optional['):
            inner = python_type[9:-1]  # Extract T from Optional[T]
            return f"Option<{cls.map_type(inner)}>"

        # Handle List[T]
        if python_type.startswith(('List[', 'list[')):
            inner = python_type[python_type.index('[')+1:-1]
            return f"Vec<{cls.map_type(inner)}>"

        # Handle Dict[K, V]
        if python_type.startswith(('Dict[', 'dict[')):
            inner = python_type[python_type.index('[')+1:-1]
            parts = cls._split_type_args(inner)
            if len(parts) == 2:
                key_type = cls.map_type(parts[0])
                val_type = cls.map_type(parts[1])
                return f"HashMap<{key_type}, {val_type}>"

        # Handle Tuple[T1, T2, ...]
        if python_type.startswith(('Tuple[', 'tuple[')):
            inner = python_type[python_type.index('[')+1:-1]
            parts = cls._split_type_args(inner)
            rust_types = [cls.map_type(p) for p in parts]
            return f"({', '.join(rust_types)})"

        # Default to String for unknown types
        return 'String'

    @staticmethod
    def _split_type_args(type_str: str) -> List[str]:
        """Split type arguments handling nested brackets.

        Args:
            type_str: Type arguments string (e.g., "str, int" or "List[str], Dict[str, int]")

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


class ModuleInspector:
    """Inspect DSPy modules."""

    def __init__(self):
        self.type_mapper = TypeMapper()

    def inspect_from_source(self, source_path: str, class_name: str) -> ModuleInfo:
        """Inspect module from Python source file.

        Args:
            source_path: Path to Python file
            class_name: Name of module class to inspect

        Returns:
            ModuleInfo object
        """
        with open(source_path) as f:
            source = f.read()

        tree = ast.parse(source)

        # Find class definition
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == class_name:
                return self._inspect_class_node(node, class_name)

        raise ValueError(f"Class {class_name} not found in {source_path}")

    def inspect_from_object(self, module_obj: Any) -> ModuleInfo:
        """Inspect module from Python object.

        Args:
            module_obj: DSPy module instance or class

        Returns:
            ModuleInfo object
        """
        if inspect.isclass(module_obj):
            cls = module_obj
            obj = None
        else:
            cls = module_obj.__class__
            obj = module_obj

        name = cls.__name__
        base_classes = [base.__name__ for base in cls.__bases__]
        has_forward = hasattr(cls, 'forward')

        # Try to extract signature
        signature = None
        input_fields = []
        output_fields = []

        # Check for signature attribute
        if obj and hasattr(obj, 'signature'):
            sig = obj.signature
            signature = str(sig)

            # Extract fields from signature
            if hasattr(sig, 'input_fields'):
                input_fields = self._extract_signature_fields(sig.input_fields, True)
            if hasattr(sig, 'output_fields'):
                output_fields = self._extract_signature_fields(sig.output_fields, False)

        return ModuleInfo(
            name=name,
            signature=signature,
            input_fields=input_fields,
            output_fields=output_fields,
            has_forward=has_forward,
            base_classes=base_classes
        )

    def _inspect_class_node(self, node: ast.ClassDef, name: str) -> ModuleInfo:
        """Inspect AST class node."""
        base_classes = [
            base.id if isinstance(base, ast.Name) else str(base)
            for base in node.bases
        ]

        has_forward = any(
            isinstance(item, ast.FunctionDef) and item.name == 'forward'
            for item in node.body
        )

        # Note: Signature extraction from __init__ or class attributes not yet implemented
        # Currently returns basic info
        return ModuleInfo(
            name=name,
            signature=None,
            input_fields=[],
            output_fields=[],
            has_forward=has_forward,
            base_classes=base_classes
        )

    def _extract_signature_fields(
        self,
        fields: Any,
        is_input: bool
    ) -> List[SignatureField]:
        """Extract fields from DSPy signature."""
        result = []

        if isinstance(fields, dict):
            for name, field_obj in fields.items():
                python_type = self._infer_field_type(field_obj)
                desc = getattr(field_obj, 'description', None)

                result.append(SignatureField(
                    name=name,
                    python_type=python_type,
                    is_input=is_input,
                    is_output=not is_input,
                    description=desc
                ))

        return result

    def _infer_field_type(self, field_obj: Any) -> str:
        """Infer Python type from field object."""
        # Try to get type annotation
        if hasattr(field_obj, 'annotation'):
            return str(field_obj.annotation)

        # Default to str
        return 'str'

    def generate_rust_types(self, info: ModuleInfo) -> str:
        """Generate Rust type definitions from module info.

        Args:
            info: ModuleInfo object

        Returns:
            Rust code as string
        """
        lines = []

        # Header comment
        lines.append(f"// Generated Rust types for {info.name}")
        lines.append("// DO NOT EDIT - Generated by module_inspector.py")
        lines.append("")

        # Imports
        lines.append("use pyo3::prelude::*;")
        lines.append("use serde::{Deserialize, Serialize};")
        if any('HashMap' in self.type_mapper.map_type(f.python_type) for f in info.input_fields + info.output_fields):
            lines.append("use std::collections::HashMap;")
        lines.append("")

        # Input struct
        if info.input_fields:
            lines.append(f"#[derive(Debug, Clone, Serialize, Deserialize)]")
            lines.append(f"pub struct {info.name}Input {{")

            for field in info.input_fields:
                rust_type = self.type_mapper.map_type(field.python_type)
                if field.description:
                    lines.append(f"    /// {field.description}")
                lines.append(f"    pub {field.name}: {rust_type},")

            lines.append("}")
            lines.append("")

        # Output struct
        if info.output_fields:
            lines.append(f"#[derive(Debug, Clone, Serialize, Deserialize)]")
            lines.append(f"pub struct {info.name}Output {{")

            for field in info.output_fields:
                rust_type = self.type_mapper.map_type(field.python_type)
                if field.description:
                    lines.append(f"    /// {field.description}")
                lines.append(f"    pub {field.name}: {rust_type},")

            lines.append("}")
            lines.append("")

        # Conversion implementations
        if info.input_fields:
            lines.append(f"impl {info.name}Input {{")
            lines.append(f"    /// Convert to Python dict for DSPy")
            lines.append(f"    pub fn to_py_dict(&self, py: Python) -> PyResult<Py<PyAny>> {{")
            lines.append(f"        let dict = pyo3::types::PyDict::new(py);")

            for field in info.input_fields:
                lines.append(f"        dict.set_item(\"{field.name}\", &self.{field.name})?;")

            lines.append(f"        Ok(dict.into())")
            lines.append(f"    }}")
            lines.append(f"}}")
            lines.append("")

        if info.output_fields:
            lines.append(f"impl {info.name}Output {{")
            lines.append(f"    /// Extract from Python prediction")
            lines.append(f"    pub fn from_py_prediction(prediction: &PyAny) -> PyResult<Self> {{")
            lines.append(f"        Ok(Self {{")

            for field in info.output_fields:
                lines.append(f"            {field.name}: prediction.getattr(\"{field.name}\")?.extract()?,")

            lines.append(f"        }})")
            lines.append(f"    }}")
            lines.append(f"}}")
            lines.append("")

        return '\n'.join(lines)

    def validate_pyo3_compatibility(self, info: ModuleInfo) -> Tuple[bool, List[str]]:
        """Validate module is compatible with PyO3.

        Args:
            info: ModuleInfo object

        Returns:
            (is_compatible, list_of_issues)
        """
        issues = []

        # Check has forward method
        if not info.has_forward:
            issues.append("Module does not have a forward() method")

        # Check base classes
        if 'Module' not in info.base_classes and 'dspy.Module' not in info.base_classes:
            issues.append("Module does not inherit from dspy.Module")

        # Check field types are mappable
        all_fields = info.input_fields + info.output_fields
        for field in all_fields:
            rust_type = self.type_mapper.map_type(field.python_type)
            if rust_type == 'String' and field.python_type not in ('str', 'String'):
                issues.append(f"Field '{field.name}' has unmapped type: {field.python_type}")

        is_compatible = len(issues) == 0
        return is_compatible, issues


def cmd_inspect(args):
    """Inspect module structure."""
    inspector = ModuleInspector()

    if args.source:
        # Inspect from source file
        info = inspector.inspect_from_source(args.source, args.module)
    else:
        # Try to import and inspect
        try:
            import dspy
            # Import module (assumes it's in Python path)
            parts = args.module.split('.')
            module = __import__(parts[0])
            for part in parts[1:]:
                module = getattr(module, part)

            info = inspector.inspect_from_object(module)
        except Exception as e:
            print(f"Error importing module: {e}", file=sys.stderr)
            print("Try using --source flag to specify source file", file=sys.stderr)
            sys.exit(1)

    # Print info
    print(f"Module: {info.name}")
    print(f"Base Classes: {', '.join(info.base_classes)}")
    print(f"Has forward(): {info.has_forward}")

    if info.signature:
        print(f"Signature: {info.signature}")

    if info.input_fields:
        print(f"\nInput Fields ({len(info.input_fields)}):")
        for field in info.input_fields:
            print(f"  - {field.name}: {field.python_type}")
            if field.description:
                print(f"    {field.description}")

    if info.output_fields:
        print(f"\nOutput Fields ({len(info.output_fields)}):")
        for field in info.output_fields:
            print(f"  - {field.name}: {field.python_type}")
            if field.description:
                print(f"    {field.description}")


def cmd_codegen(args):
    """Generate Rust code."""
    inspector = ModuleInspector()

    if args.source:
        info = inspector.inspect_from_source(args.source, args.module)
    else:
        try:
            # Import and inspect
            parts = args.module.split('.')
            module = __import__(parts[0])
            for part in parts[1:]:
                module = getattr(module, part)

            info = inspector.inspect_from_object(module)
        except Exception as e:
            print(f"// Error: {e}", file=sys.stderr)
            sys.exit(1)

    # Generate Rust code
    rust_code = inspector.generate_rust_types(info)
    print(rust_code)


def cmd_fields(args):
    """List module fields."""
    inspector = ModuleInspector()

    if args.source:
        info = inspector.inspect_from_source(args.source, args.module)
    else:
        try:
            parts = args.module.split('.')
            module = __import__(parts[0])
            for part in parts[1:]:
                module = getattr(module, part)

            info = inspector.inspect_from_object(module)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    # Output as JSON
    fields = {
        'inputs': [asdict(f) for f in info.input_fields],
        'outputs': [asdict(f) for f in info.output_fields]
    }

    print(json.dumps(fields, indent=2))


def cmd_validate(args):
    """Validate PyO3 compatibility."""
    inspector = ModuleInspector()

    if args.source:
        info = inspector.inspect_from_source(args.source, args.module)
    else:
        try:
            parts = args.module.split('.')
            module = __import__(parts[0])
            for part in parts[1:]:
                module = getattr(module, part)

            info = inspector.inspect_from_object(module)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    # Validate
    is_compatible, issues = inspector.validate_pyo3_compatibility(info)

    if is_compatible:
        print(f"✓ {info.name} is compatible with PyO3")
        sys.exit(0)
    else:
        print(f"✗ {info.name} has compatibility issues:")
        for issue in issues:
            print(f"  - {issue}")
        sys.exit(1)


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Inspect DSPy modules and generate Rust types"
    )
    parser.add_argument(
        '--source',
        help='Path to Python source file'
    )

    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # Inspect command
    p_inspect = subparsers.add_parser('inspect', help='Inspect module structure')
    p_inspect.add_argument('module', help='Module name or class name')

    # Codegen command
    p_codegen = subparsers.add_parser('codegen', help='Generate Rust types')
    p_codegen.add_argument('module', help='Module name or class name')

    # Fields command
    p_fields = subparsers.add_parser('fields', help='List fields as JSON')
    p_fields.add_argument('module', help='Module name or class name')

    # Validate command
    p_validate = subparsers.add_parser('validate', help='Validate PyO3 compatibility')
    p_validate.add_argument('module', help='Module name or class name')

    args = parser.parse_args()

    if args.command == 'inspect':
        cmd_inspect(args)
    elif args.command == 'codegen':
        cmd_codegen(args)
    elif args.command == 'fields':
        cmd_fields(args)
    elif args.command == 'validate':
        cmd_validate(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
