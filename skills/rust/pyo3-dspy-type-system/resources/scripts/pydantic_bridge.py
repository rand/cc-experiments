#!/usr/bin/env python3
"""
Pydantic-Rust Serde Bridge

Bidirectional conversion between Pydantic models and Rust serde types.
Generates Rust struct definitions, validates schemas, and tests round-trip conversions.
"""

import argparse
import ast
import json
import re
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

try:
    from pydantic import BaseModel, ValidationError, create_model
    from pydantic.fields import FieldInfo
except ImportError:
    print("Error: pydantic not found. Install with: pip install pydantic", file=sys.stderr)
    sys.exit(1)


class RustType(Enum):
    """Rust type representations"""
    STRING = "String"
    I32 = "i32"
    I64 = "i64"
    F32 = "f32"
    F64 = "f64"
    BOOL = "bool"
    VEC = "Vec"
    OPTION = "Option"
    HASHMAP = "HashMap"
    CUSTOM = "custom"


@dataclass
class FieldMapping:
    """Mapping between Pydantic and Rust field"""
    name: str
    python_type: str
    rust_type: str
    optional: bool
    default: Optional[Any] = None
    description: Optional[str] = None


@dataclass
class ModelMapping:
    """Complete model mapping"""
    name: str
    fields: List[FieldMapping]
    description: Optional[str] = None


class PythonTypeAnalyzer:
    """Analyzes Python type annotations"""

    @staticmethod
    def parse_type_annotation(annotation: Any) -> Tuple[str, bool]:
        """
        Parse Python type annotation to string representation.
        Returns (type_string, is_optional)
        """
        if annotation is None or annotation == type(None):
            return ("None", False)

        # Handle string annotations
        if isinstance(annotation, str):
            return (annotation, "Optional" in annotation or "None" in annotation)

        # Get the type name
        type_str = str(annotation)

        # Check for Optional/Union with None
        is_optional = False
        if hasattr(annotation, "__origin__"):
            origin = annotation.__origin__
            args = getattr(annotation, "__args__", ())

            # Optional[X] or Union[X, None]
            if origin is Union:
                if type(None) in args:
                    is_optional = True
                    # Get non-None types
                    non_none = [arg for arg in args if arg is not type(None)]
                    if len(non_none) == 1:
                        type_str = str(non_none[0])
                    else:
                        type_str = f"Union[{', '.join(str(t) for t in non_none)}]"
            # List[X]
            elif origin is list:
                if args:
                    inner = PythonTypeAnalyzer.parse_type_annotation(args[0])[0]
                    type_str = f"List[{inner}]"
                else:
                    type_str = "List"
            # Dict[K, V]
            elif origin is dict:
                if args and len(args) == 2:
                    key_type = PythonTypeAnalyzer.parse_type_annotation(args[0])[0]
                    val_type = PythonTypeAnalyzer.parse_type_annotation(args[1])[0]
                    type_str = f"Dict[{key_type}, {val_type}]"
                else:
                    type_str = "Dict"

        # Clean up type string
        type_str = type_str.replace("typing.", "").replace("<class '", "").replace("'>", "")

        return (type_str, is_optional)


class RustTypeConverter:
    """Converts Python types to Rust types"""

    # Type mapping from Python to Rust
    TYPE_MAP = {
        "str": RustType.STRING.value,
        "int": RustType.I64.value,
        "float": RustType.F64.value,
        "bool": RustType.BOOL.value,
    }

    @classmethod
    def convert_type(cls, python_type: str, optional: bool = False) -> str:
        """Convert Python type to Rust type"""
        # Handle List types
        if python_type.startswith("List["):
            inner = python_type[5:-1]
            rust_inner = cls.convert_type(inner, False)
            rust_type = f"Vec<{rust_inner}>"
        # Handle Dict types
        elif python_type.startswith("Dict["):
            match = re.match(r"Dict\[(.*?),\s*(.*?)\]", python_type)
            if match:
                key_type = cls.convert_type(match.group(1), False)
                val_type = cls.convert_type(match.group(2), False)
                rust_type = f"HashMap<{key_type}, {val_type}>"
            else:
                rust_type = "HashMap<String, serde_json::Value>"
        # Handle basic types
        else:
            rust_type = cls.TYPE_MAP.get(python_type, python_type)

        # Wrap in Option if optional
        if optional:
            rust_type = f"Option<{rust_type}>"

        return rust_type


class PydanticAnalyzer:
    """Analyzes Pydantic models"""

    @staticmethod
    def extract_models_from_file(file_path: Path) -> Dict[str, type]:
        """Extract Pydantic models from Python file"""
        with open(file_path, 'r') as f:
            source = f.read()

        # Parse the Python file
        try:
            tree = ast.parse(source)
        except SyntaxError as e:
            raise ValueError(f"Failed to parse {file_path}: {e}")

        # Execute to get actual classes
        namespace = {}
        try:
            exec(source, namespace)
        except Exception as e:
            raise ValueError(f"Failed to execute {file_path}: {e}")

        # Find Pydantic models
        models = {}
        for name, obj in namespace.items():
            if isinstance(obj, type) and issubclass(obj, BaseModel) and obj is not BaseModel:
                models[name] = obj

        return models

    @staticmethod
    def analyze_model(model: type) -> ModelMapping:
        """Analyze a Pydantic model and create mapping"""
        fields = []

        # Get model docstring
        doc = model.__doc__

        # Analyze each field
        for field_name, field_info in model.model_fields.items():
            # Get type annotation
            annotation = field_info.annotation
            python_type, is_optional = PythonTypeAnalyzer.parse_type_annotation(annotation)

            # Check if field is optional (has default or None)
            is_optional = is_optional or field_info.default is not None

            # Convert to Rust type
            rust_type = RustTypeConverter.convert_type(python_type, is_optional)

            # Get field description
            description = field_info.description

            # Get default value
            default = None
            if field_info.default is not None and field_info.default != Ellipsis:
                default = field_info.default

            fields.append(FieldMapping(
                name=field_name,
                python_type=python_type,
                rust_type=rust_type,
                optional=is_optional,
                default=default,
                description=description
            ))

        return ModelMapping(
            name=model.__name__,
            fields=fields,
            description=doc
        )


class RustCodeGenerator:
    """Generates Rust code from model mappings"""

    @staticmethod
    def generate_struct(mapping: ModelMapping) -> str:
        """Generate Rust struct definition"""
        lines = []

        # Add description as doc comment
        if mapping.description:
            doc = mapping.description.strip()
            for line in doc.split('\n'):
                if line.strip():
                    lines.append(f"/// {line.strip()}")

        # Add derives
        lines.append("#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]")
        lines.append("#[serde(rename_all = \"snake_case\")]")

        # Struct declaration
        lines.append(f"pub struct {mapping.name} {{")

        # Fields
        for field in mapping.fields:
            # Add field description
            if field.description:
                lines.append(f"    /// {field.description}")

            # Add serde attributes for optional fields
            if field.optional:
                lines.append(f"    #[serde(skip_serializing_if = \"Option::is_none\")]")

            # Field declaration
            lines.append(f"    pub {field.name}: {field.rust_type},")

        lines.append("}")

        return "\n".join(lines)

    @staticmethod
    def generate_implementation(mapping: ModelMapping) -> str:
        """Generate impl block with helper methods"""
        lines = []

        lines.append(f"impl {mapping.name} {{")

        # Constructor
        lines.append("    /// Create a new instance")
        lines.append(f"    pub fn new(")

        required_fields = [f for f in mapping.fields if not f.optional]
        for i, field in enumerate(required_fields):
            comma = "," if i < len(required_fields) - 1 else ""
            lines.append(f"        {field.name}: {field.rust_type}{comma}")

        lines.append(f"    ) -> Self {{")
        lines.append(f"        Self {{")

        for field in mapping.fields:
            if field in required_fields:
                lines.append(f"            {field.name},")
            else:
                lines.append(f"            {field.name}: None,")

        lines.append("        }")
        lines.append("    }")

        # JSON conversion methods
        lines.append("")
        lines.append("    /// Deserialize from JSON string")
        lines.append("    pub fn from_json(json: &str) -> Result<Self, serde_json::Error> {")
        lines.append("        serde_json::from_str(json)")
        lines.append("    }")
        lines.append("")
        lines.append("    /// Serialize to JSON string")
        lines.append("    pub fn to_json(&self) -> Result<String, serde_json::Error> {")
        lines.append("        serde_json::to_string(self)")
        lines.append("    }")

        lines.append("}")

        return "\n".join(lines)


class SchemaValidator:
    """Validates schema compatibility"""

    @staticmethod
    def extract_rust_struct(rust_code: str, struct_name: str) -> Optional[Dict[str, str]]:
        """Extract field types from Rust struct definition"""
        # Find struct definition
        pattern = rf"pub\s+struct\s+{struct_name}\s*\{{(.*?)\}}"
        match = re.search(pattern, rust_code, re.DOTALL)

        if not match:
            return None

        struct_body = match.group(1)

        # Extract fields
        fields = {}
        field_pattern = r"pub\s+(\w+):\s*([^,]+),"
        for field_match in re.finditer(field_pattern, struct_body):
            field_name = field_match.group(1)
            field_type = field_match.group(2).strip()
            fields[field_name] = field_type

        return fields

    @staticmethod
    def validate_compatibility(pydantic_model: type, rust_struct_fields: Dict[str, str]) -> List[str]:
        """Validate that Pydantic model is compatible with Rust struct"""
        errors = []

        mapping = PydanticAnalyzer.analyze_model(pydantic_model)

        # Check each Pydantic field
        for field in mapping.fields:
            if field.name not in rust_struct_fields:
                errors.append(f"Field '{field.name}' missing in Rust struct")
            else:
                rust_type = rust_struct_fields[field.name]
                expected_type = field.rust_type

                # Normalize type strings for comparison
                rust_type_norm = rust_type.replace(" ", "")
                expected_type_norm = expected_type.replace(" ", "")

                if rust_type_norm != expected_type_norm:
                    errors.append(
                        f"Field '{field.name}' type mismatch: "
                        f"Rust has '{rust_type}', expected '{expected_type}'"
                    )

        # Check for extra Rust fields
        pydantic_fields = {f.name for f in mapping.fields}
        for rust_field in rust_struct_fields:
            if rust_field not in pydantic_fields:
                errors.append(f"Extra field '{rust_field}' in Rust struct")

        return errors


class BidirectionalTester:
    """Tests bidirectional conversion"""

    @staticmethod
    def test_round_trip(model: type, json_data: str) -> Tuple[bool, Optional[str]]:
        """Test round-trip conversion: JSON -> Pydantic -> JSON"""
        try:
            # Parse JSON
            data = json.loads(json_data)

            # Create Pydantic instance
            instance = model(**data)

            # Serialize back to JSON
            serialized = instance.model_dump_json()

            # Parse both for comparison
            original_data = json.loads(json_data)
            round_trip_data = json.loads(serialized)

            # Compare (allowing for None vs missing keys)
            if original_data != round_trip_data:
                # Check if differences are only None values
                diff = []
                for key in set(original_data.keys()) | set(round_trip_data.keys()):
                    orig_val = original_data.get(key)
                    rt_val = round_trip_data.get(key)
                    if orig_val != rt_val:
                        diff.append(f"  {key}: {orig_val} -> {rt_val}")

                return False, "Round-trip data mismatch:\n" + "\n".join(diff)

            return True, None

        except ValidationError as e:
            return False, f"Validation error: {e}"
        except Exception as e:
            return False, f"Error: {e}"


def cmd_convert(args: argparse.Namespace) -> int:
    """Convert Pydantic model to Rust struct"""
    try:
        models = PydanticAnalyzer.extract_models_from_file(args.file)

        if args.class_name:
            if args.class_name not in models:
                print(f"Error: Model '{args.class_name}' not found", file=sys.stderr)
                print(f"Available models: {', '.join(models.keys())}", file=sys.stderr)
                return 1

            models_to_convert = {args.class_name: models[args.class_name]}
        else:
            models_to_convert = models

        # Generate Rust code
        output = []
        output.append("// Generated from Pydantic models")
        output.append("// Do not edit manually\n")

        if "HashMap" in str(models_to_convert):
            output.append("use std::collections::HashMap;\n")

        for name, model in models_to_convert.items():
            mapping = PydanticAnalyzer.analyze_model(model)
            output.append(RustCodeGenerator.generate_struct(mapping))
            output.append("")
            output.append(RustCodeGenerator.generate_implementation(mapping))
            output.append("")

        print("\n".join(output))
        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_schema(args: argparse.Namespace) -> int:
    """Generate JSON schema from Pydantic model"""
    try:
        models = PydanticAnalyzer.extract_models_from_file(args.file)

        if args.class_name not in models:
            print(f"Error: Model '{args.class_name}' not found", file=sys.stderr)
            return 1

        model = models[args.class_name]
        schema = model.model_json_schema()

        print(json.dumps(schema, indent=2))
        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_validate(args: argparse.Namespace) -> int:
    """Validate Pydantic model against Rust struct"""
    try:
        # Load Pydantic models
        models = PydanticAnalyzer.extract_models_from_file(args.pydantic_file)

        # Load Rust code
        with open(args.rust_file, 'r') as f:
            rust_code = f.read()

        # Validate each model
        all_valid = True
        for name, model in models.items():
            rust_fields = SchemaValidator.extract_rust_struct(rust_code, name)

            if rust_fields is None:
                print(f"⚠️  Struct '{name}' not found in Rust code")
                all_valid = False
                continue

            errors = SchemaValidator.validate_compatibility(model, rust_fields)

            if errors:
                print(f"❌ {name}: Validation failed")
                for error in errors:
                    print(f"  - {error}")
                all_valid = False
            else:
                print(f"✅ {name}: Valid")

        return 0 if all_valid else 1

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_test(args: argparse.Namespace) -> int:
    """Test bidirectional conversion"""
    try:
        # Load Pydantic models
        models = PydanticAnalyzer.extract_models_from_file(args.pydantic_file)

        if args.class_name not in models:
            print(f"Error: Model '{args.class_name}' not found", file=sys.stderr)
            return 1

        model = models[args.class_name]

        # Load JSON data
        with open(args.json_file, 'r') as f:
            json_data = f.read()

        # Test round-trip
        success, error = BidirectionalTester.test_round_trip(model, json_data)

        if success:
            print(f"✅ Round-trip test passed for {args.class_name}")
            return 0
        else:
            print(f"❌ Round-trip test failed for {args.class_name}")
            print(error)
            return 1

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def main() -> int:
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Bridge Pydantic models and Rust serde types",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Convert Pydantic model to Rust struct
  %(prog)s convert model.py --class User > user.rs

  # Generate JSON schema
  %(prog)s schema model.py --class User

  # Validate compatibility
  %(prog)s validate model.py types.rs

  # Test round-trip conversion
  %(prog)s test model.py types.rs --json data.json --class User
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to run')

    # Convert command
    convert_parser = subparsers.add_parser('convert', help='Convert Pydantic to Rust')
    convert_parser.add_argument('file', type=Path, help='Python file with Pydantic models')
    convert_parser.add_argument('--class', dest='class_name', help='Specific class to convert')

    # Schema command
    schema_parser = subparsers.add_parser('schema', help='Generate JSON schema')
    schema_parser.add_argument('file', type=Path, help='Python file with Pydantic models')
    schema_parser.add_argument('--class', dest='class_name', required=True, help='Class name')

    # Validate command
    validate_parser = subparsers.add_parser('validate', help='Validate compatibility')
    validate_parser.add_argument('pydantic_file', type=Path, help='Python file')
    validate_parser.add_argument('rust_file', type=Path, help='Rust file')

    # Test command
    test_parser = subparsers.add_parser('test', help='Test round-trip conversion')
    test_parser.add_argument('pydantic_file', type=Path, help='Python file')
    test_parser.add_argument('rust_file', type=Path, help='Rust file')
    test_parser.add_argument('--json', dest='json_file', type=Path, required=True, help='JSON test data')
    test_parser.add_argument('--class', dest='class_name', required=True, help='Class name')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Dispatch to command
    if args.command == 'convert':
        return cmd_convert(args)
    elif args.command == 'schema':
        return cmd_schema(args)
    elif args.command == 'validate':
        return cmd_validate(args)
    elif args.command == 'test':
        return cmd_test(args)
    else:
        print(f"Unknown command: {args.command}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
