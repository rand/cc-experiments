#!/usr/bin/env python3
"""
DSPy Prediction Parser

Safely parse and validate DSPy prediction objects with type checking and error
reporting. Converts Python types to Rust-compatible JSON with comprehensive
validation and error handling.

Usage:
    python prediction_parser.py parse prediction.json --schema schema.json
    python prediction_parser.py validate prediction.json --expected-fields answer,reasoning
    python prediction_parser.py schema "answer: str, score: float"
    python prediction_parser.py test module.py --class QAModule --input input.json
"""

import sys
import json
import argparse
from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
from enum import Enum


class PythonType(Enum):
    """Python type enumeration."""
    STR = "str"
    INT = "int"
    FLOAT = "float"
    BOOL = "bool"
    NONE = "None"
    LIST = "list"
    DICT = "dict"
    TUPLE = "tuple"
    SET = "set"
    ANY = "Any"


@dataclass
class FieldSchema:
    """Schema for a single field."""
    name: str
    type: str
    required: bool = True
    default: Optional[Any] = None
    description: Optional[str] = None


@dataclass
class ValidationResult:
    """Result of validation operation."""
    valid: bool
    errors: List[str]
    warnings: List[str]


@dataclass
class ParseResult:
    """Result of parse operation."""
    success: bool
    data: Optional[Dict[str, Any]]
    errors: List[str]
    type_info: Dict[str, str]


class TypeMapper:
    """Maps Python types to Rust-compatible types."""

    # Basic type mappings
    BASIC_TYPES = {
        'str': 'String',
        'int': 'i64',
        'float': 'f64',
        'bool': 'bool',
        'None': '()',
        'NoneType': '()',
    }

    @classmethod
    def map_type(cls, python_type: str) -> str:
        """Map Python type to Rust type.

        Args:
            python_type: Python type string (e.g., "str", "List[str]")

        Returns:
            Rust type string (e.g., "String", "Vec<String>")
        """
        # Handle None/NoneType
        if python_type in ('None', 'NoneType'):
            return '()'

        # Handle basic types
        if python_type in cls.BASIC_TYPES:
            return cls.BASIC_TYPES[python_type]

        # Handle Optional[T]
        if python_type.startswith('Optional['):
            inner = python_type[9:-1]
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
            return "HashMap<String, serde_json::Value>"

        # Handle Tuple[T1, T2, ...]
        if python_type.startswith(('Tuple[', 'tuple[')):
            inner = python_type[python_type.index('[')+1:-1]
            parts = cls._split_type_args(inner)
            rust_types = [cls.map_type(p) for p in parts]
            return f"({', '.join(rust_types)})"

        # Handle Set[T]
        if python_type.startswith(('Set[', 'set[')):
            inner = python_type[python_type.index('[')+1:-1]
            return f"HashSet<{cls.map_type(inner)}>"

        # Default to serde_json::Value for unknown types
        return 'serde_json::Value'

    @staticmethod
    def _split_type_args(type_str: str) -> List[str]:
        """Split type arguments handling nested brackets."""
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


class TypeInspector:
    """Inspect and validate Python types."""

    @staticmethod
    def infer_type(value: Any) -> str:
        """Infer Python type from value.

        Args:
            value: Python value to inspect

        Returns:
            Type string (e.g., "str", "List[str]")
        """
        if value is None:
            return "None"

        value_type = type(value)

        # Basic types
        if value_type is str:
            return "str"
        elif value_type is int:
            return "int"
        elif value_type is float:
            return "float"
        elif value_type is bool:
            return "bool"

        # Collection types
        elif value_type is list:
            if not value:
                return "List[Any]"
            # Infer from first element
            first_type = TypeInspector.infer_type(value[0])
            return f"List[{first_type}]"

        elif value_type is dict:
            if not value:
                return "Dict[str, Any]"
            # Infer from first entry
            first_key = next(iter(value.keys()))
            first_val = value[first_key]
            key_type = TypeInspector.infer_type(first_key)
            val_type = TypeInspector.infer_type(first_val)
            return f"Dict[{key_type}, {val_type}]"

        elif value_type is tuple:
            if not value:
                return "Tuple[()]"
            element_types = [TypeInspector.infer_type(v) for v in value]
            return f"Tuple[{', '.join(element_types)}]"

        elif value_type is set:
            if not value:
                return "Set[Any]"
            first_type = TypeInspector.infer_type(next(iter(value)))
            return f"Set[{first_type}]"

        else:
            return "Any"

    @staticmethod
    def validate_type(value: Any, expected_type: str) -> Tuple[bool, Optional[str]]:
        """Validate value matches expected type.

        Args:
            value: Value to validate
            expected_type: Expected type string

        Returns:
            (is_valid, error_message)
        """
        actual_type = TypeInspector.infer_type(value)

        # Handle None/Optional
        if value is None:
            if expected_type.startswith('Optional['):
                return True, None
            else:
                return False, f"Expected {expected_type}, got None"

        # Basic type checks
        if expected_type in ('str', 'int', 'float', 'bool', 'None'):
            if actual_type == expected_type:
                return True, None
            else:
                return False, f"Expected {expected_type}, got {actual_type}"

        # Optional handling
        if expected_type.startswith('Optional['):
            inner = expected_type[9:-1]
            return TypeInspector.validate_type(value, inner)

        # List validation
        if expected_type.startswith(('List[', 'list[')):
            if not isinstance(value, list):
                return False, f"Expected list, got {type(value).__name__}"

            # Extract inner type
            inner = expected_type[expected_type.index('[')+1:-1]
            if inner == 'Any':
                return True, None

            # Validate all elements
            for i, item in enumerate(value):
                valid, err = TypeInspector.validate_type(item, inner)
                if not valid:
                    return False, f"List element {i}: {err}"

            return True, None

        # Dict validation
        if expected_type.startswith(('Dict[', 'dict[')):
            if not isinstance(value, dict):
                return False, f"Expected dict, got {type(value).__name__}"
            return True, None  # Simplified - could validate key/value types

        # Tuple validation
        if expected_type.startswith(('Tuple[', 'tuple[')):
            if not isinstance(value, tuple):
                return False, f"Expected tuple, got {type(value).__name__}"
            return True, None

        # Set validation
        if expected_type.startswith(('Set[', 'set[')):
            if not isinstance(value, set):
                return False, f"Expected set, got {type(value).__name__}"
            return True, None

        # Any type
        if expected_type == 'Any':
            return True, None

        return True, None  # Unknown types pass


class PredictionParser:
    """Parse and validate DSPy predictions."""

    def __init__(self):
        self.type_mapper = TypeMapper()
        self.type_inspector = TypeInspector()

    def parse(
        self,
        prediction_data: Dict[str, Any],
        schema: Optional[Dict[str, FieldSchema]] = None
    ) -> ParseResult:
        """Parse prediction data with optional schema validation.

        Args:
            prediction_data: Raw prediction data
            schema: Optional schema for validation

        Returns:
            ParseResult with parsed data and type info
        """
        errors = []
        type_info = {}
        parsed_data = {}

        try:
            # Extract and validate each field
            for field_name, field_value in prediction_data.items():
                # Infer type
                python_type = self.type_inspector.infer_type(field_value)
                rust_type = self.type_mapper.map_type(python_type)
                type_info[field_name] = rust_type

                # Validate against schema if provided
                if schema and field_name in schema:
                    field_schema = schema[field_name]
                    valid, err = self.type_inspector.validate_type(
                        field_value,
                        field_schema.type
                    )
                    if not valid:
                        errors.append(f"Field '{field_name}': {err}")
                        continue

                # Convert to JSON-compatible format
                parsed_value = self._convert_to_json(field_value)
                parsed_data[field_name] = parsed_value

            # Check for missing required fields
            if schema:
                for field_name, field_schema in schema.items():
                    if field_schema.required and field_name not in parsed_data:
                        errors.append(
                            f"Missing required field: '{field_name}'"
                        )

        except Exception as e:
            errors.append(f"Parse error: {str(e)}")

        return ParseResult(
            success=len(errors) == 0,
            data=parsed_data if len(errors) == 0 else None,
            errors=errors,
            type_info=type_info
        )

    def validate(
        self,
        prediction_data: Dict[str, Any],
        expected_fields: List[str]
    ) -> ValidationResult:
        """Validate prediction has expected fields.

        Args:
            prediction_data: Prediction data to validate
            expected_fields: List of expected field names

        Returns:
            ValidationResult with errors and warnings
        """
        errors = []
        warnings = []

        # Check for missing fields
        for field in expected_fields:
            if field not in prediction_data:
                errors.append(f"Missing expected field: '{field}'")
            elif prediction_data[field] is None:
                warnings.append(f"Field '{field}' is None")

        # Check for unexpected fields
        for field in prediction_data:
            if field not in expected_fields:
                warnings.append(f"Unexpected field: '{field}'")

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )

    def _convert_to_json(self, value: Any) -> Any:
        """Convert Python value to JSON-compatible format.

        Args:
            value: Python value to convert

        Returns:
            JSON-compatible value
        """
        if value is None:
            return None

        value_type = type(value)

        # Basic types
        if value_type in (str, int, float, bool):
            return value

        # Collections
        elif value_type is list:
            return [self._convert_to_json(v) for v in value]

        elif value_type is dict:
            return {
                str(k): self._convert_to_json(v)
                for k, v in value.items()
            }

        elif value_type is tuple:
            return [self._convert_to_json(v) for v in value]

        elif value_type is set:
            return [self._convert_to_json(v) for v in value]

        else:
            # Try to convert to string
            return str(value)


class SchemaParser:
    """Parse schema definitions."""

    @staticmethod
    def parse_schema_string(schema_str: str) -> Dict[str, FieldSchema]:
        """Parse schema from string format.

        Format: "field1: type1, field2: type2, ..."

        Args:
            schema_str: Schema definition string

        Returns:
            Dictionary of field schemas
        """
        schema = {}

        # Split by comma
        field_defs = [f.strip() for f in schema_str.split(',')]

        for field_def in field_defs:
            if ':' not in field_def:
                continue

            # Parse "name: type"
            parts = field_def.split(':', 1)
            field_name = parts[0].strip()
            field_type = parts[1].strip()

            # Check if optional
            required = not field_type.startswith('Optional[')

            schema[field_name] = FieldSchema(
                name=field_name,
                type=field_type,
                required=required
            )

        return schema

    @staticmethod
    def parse_schema_json(schema_json: Dict[str, Any]) -> Dict[str, FieldSchema]:
        """Parse schema from JSON format.

        Args:
            schema_json: Schema definition as JSON

        Returns:
            Dictionary of field schemas
        """
        schema = {}

        for field_name, field_def in schema_json.items():
            if isinstance(field_def, str):
                # Simple format: {"field": "type"}
                schema[field_name] = FieldSchema(
                    name=field_name,
                    type=field_def
                )
            elif isinstance(field_def, dict):
                # Full format: {"field": {"type": "str", "required": true}}
                schema[field_name] = FieldSchema(
                    name=field_name,
                    type=field_def.get('type', 'Any'),
                    required=field_def.get('required', True),
                    default=field_def.get('default'),
                    description=field_def.get('description')
                )

        return schema


def cmd_parse(args):
    """Parse prediction from JSON file."""
    parser = PredictionParser()

    # Load prediction data
    try:
        with open(args.prediction) as f:
            prediction_data = json.load(f)
    except Exception as e:
        print(f"Error loading prediction: {e}", file=sys.stderr)
        sys.exit(1)

    # Load schema if provided
    schema = None
    if args.schema:
        try:
            with open(args.schema) as f:
                schema_json = json.load(f)
            schema = SchemaParser.parse_schema_json(schema_json)
        except Exception as e:
            print(f"Error loading schema: {e}", file=sys.stderr)
            sys.exit(1)

    # Parse
    result = parser.parse(prediction_data, schema)

    # Output result
    output = {
        'success': result.success,
        'data': result.data,
        'errors': result.errors,
        'type_info': result.type_info
    }

    if args.output:
        with open(args.output, 'w') as f:
            json.dump(output, f, indent=2)
    else:
        print(json.dumps(output, indent=2))

    sys.exit(0 if result.success else 1)


def cmd_validate(args):
    """Validate prediction has expected fields."""
    parser = PredictionParser()

    # Load prediction data
    try:
        with open(args.prediction) as f:
            prediction_data = json.load(f)
    except Exception as e:
        print(f"Error loading prediction: {e}", file=sys.stderr)
        sys.exit(1)

    # Parse expected fields
    expected_fields = [f.strip() for f in args.expected_fields.split(',')]

    # Validate
    result = parser.validate(prediction_data, expected_fields)

    # Output result
    output = {
        'valid': result.valid,
        'errors': result.errors,
        'warnings': result.warnings
    }

    print(json.dumps(output, indent=2))

    # Print summary
    if result.valid:
        print("\n✓ Validation passed", file=sys.stderr)
        if result.warnings:
            print(f"  ({len(result.warnings)} warnings)", file=sys.stderr)
    else:
        print(f"\n✗ Validation failed ({len(result.errors)} errors)", file=sys.stderr)
        for error in result.errors:
            print(f"  - {error}", file=sys.stderr)

    sys.exit(0 if result.valid else 1)


def cmd_schema(args):
    """Generate schema from definition string."""
    schema = SchemaParser.parse_schema_string(args.definition)

    # Convert to JSON format with Rust types
    type_mapper = TypeMapper()
    output = {}

    for field_name, field_schema in schema.items():
        rust_type = type_mapper.map_type(field_schema.type)
        output[field_name] = {
            'python_type': field_schema.type,
            'rust_type': rust_type,
            'required': field_schema.required
        }

    print(json.dumps(output, indent=2))


def cmd_test(args):
    """Test parser with DSPy module."""
    import importlib.util
    import os

    parser = PredictionParser()

    # Load module
    try:
        module_path = Path(args.module).resolve()
        spec = importlib.util.spec_from_file_location("test_module", module_path)
        module = importlib.util.module_from_spec(spec)

        # Add parent directory to sys.path for imports
        parent_dir = str(module_path.parent)
        if parent_dir not in sys.path:
            sys.path.insert(0, parent_dir)

        spec.loader.exec_module(module)
    except Exception as e:
        print(f"Error loading module: {e}", file=sys.stderr)
        sys.exit(1)

    # Get class
    try:
        module_class = getattr(module, args.cls)
    except AttributeError:
        print(f"Class '{args.cls}' not found in module", file=sys.stderr)
        sys.exit(1)

    # Load input data
    try:
        with open(args.input) as f:
            input_data = json.load(f)
    except Exception as e:
        print(f"Error loading input: {e}", file=sys.stderr)
        sys.exit(1)

    # Create instance and run
    try:
        instance = module_class()

        # Call forward method
        result = instance.forward(**input_data)

        # Convert result to dict
        if hasattr(result, '__dict__'):
            result_dict = result.__dict__
        elif hasattr(result, 'model_dump'):
            # Pydantic model
            result_dict = result.model_dump()
        elif isinstance(result, dict):
            result_dict = result
        else:
            # Try to extract attributes
            result_dict = {
                attr: getattr(result, attr)
                for attr in dir(result)
                if not attr.startswith('_')
            }

        # Parse result
        parse_result = parser.parse(result_dict)

        # Output
        output = {
            'success': parse_result.success,
            'data': parse_result.data,
            'errors': parse_result.errors,
            'type_info': parse_result.type_info
        }

        print(json.dumps(output, indent=2))

        sys.exit(0 if parse_result.success else 1)

    except Exception as e:
        print(f"Error running module: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Parse and validate DSPy predictions"
    )

    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # Parse command
    p_parse = subparsers.add_parser('parse', help='Parse prediction from JSON')
    p_parse.add_argument('prediction', help='Path to prediction JSON file')
    p_parse.add_argument('--schema', help='Path to schema JSON file')
    p_parse.add_argument('--output', '-o', help='Output file (default: stdout)')

    # Validate command
    p_validate = subparsers.add_parser('validate', help='Validate prediction')
    p_validate.add_argument('prediction', help='Path to prediction JSON file')
    p_validate.add_argument(
        '--expected-fields',
        required=True,
        help='Comma-separated list of expected fields'
    )

    # Schema command
    p_schema = subparsers.add_parser('schema', help='Generate schema')
    p_schema.add_argument(
        'definition',
        help='Schema definition (e.g., "answer: str, score: float")'
    )

    # Test command
    p_test = subparsers.add_parser('test', help='Test with DSPy module')
    p_test.add_argument('module', help='Path to Python module')
    p_test.add_argument('--class', dest='cls', required=True, help='Module class name')
    p_test.add_argument('--input', required=True, help='Path to input JSON file')

    args = parser.parse_args()

    if args.command == 'parse':
        cmd_parse(args)
    elif args.command == 'validate':
        cmd_validate(args)
    elif args.command == 'schema':
        cmd_schema(args)
    elif args.command == 'test':
        cmd_test(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
