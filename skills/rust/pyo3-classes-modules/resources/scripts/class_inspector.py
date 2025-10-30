#!/usr/bin/env python3
"""
PyO3 Class Inspector

Inspects PyO3 classes, validates protocol implementations, checks method signatures,
generates documentation, and tests inheritance hierarchies.

Usage:
    python class_inspector.py [command] [options]

Commands:
    inspect      - Inspect a PyO3 class or module
    validate     - Validate protocol implementations
    generate     - Generate documentation
    hierarchy    - Analyze class hierarchy
    compare      - Compare classes

Examples:
    # Inspect a class
    python class_inspector.py inspect MyClass --verbose

    # Validate protocols
    python class_inspector.py validate MyClass --protocol iterator

    # Generate documentation
    python class_inspector.py generate MyModule --output docs.md

    # Analyze hierarchy
    python class_inspector.py hierarchy MyClass --depth 3
"""

import argparse
import ast
import inspect
import json
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


@dataclass
class MethodInfo:
    """Information about a method."""
    name: str
    type: str  # instance, class, static, property
    signature: str
    docstring: Optional[str]
    is_special: bool
    is_private: bool


@dataclass
class PropertyInfo:
    """Information about a property."""
    name: str
    has_getter: bool
    has_setter: bool
    has_deleter: bool
    docstring: Optional[str]


@dataclass
class ClassInfo:
    """Complete class information."""
    name: str
    module: str
    bases: List[str]
    methods: List[MethodInfo]
    properties: List[PropertyInfo]
    class_variables: Dict[str, str]
    instance_variables: Set[str]
    protocols: List[str]
    docstring: Optional[str]


class ClassInspector:
    """Inspect PyO3 classes and modules."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose

    def log(self, message: str) -> None:
        """Log message if verbose."""
        if self.verbose:
            print(f"[INFO] {message}", file=sys.stderr)

    def inspect_class(self, cls: type) -> ClassInfo:
        """Inspect a class and return detailed information."""
        self.log(f"Inspecting class: {cls.__name__}")

        # Get base classes
        bases = [base.__name__ for base in cls.__bases__ if base != object]

        # Get methods
        methods = []
        properties = []
        
        for name, obj in inspect.getmembers(cls):
            if name.startswith('__') and name.endswith('__'):
                # Special method
                if callable(obj):
                    methods.append(self._inspect_method(name, obj, is_special=True))
            elif isinstance(obj, property):
                properties.append(self._inspect_property(name, obj))
            elif callable(obj):
                methods.append(self._inspect_method(name, obj))

        # Get class variables
        class_vars = {}
        for name, value in cls.__dict__.items():
            if not name.startswith('_') and not callable(value):
                class_vars[name] = type(value).__name__

        # Detect protocols
        protocols = self._detect_protocols(cls)

        return ClassInfo(
            name=cls.__name__,
            module=cls.__module__,
            bases=bases,
            methods=methods,
            properties=properties,
            class_variables=class_vars,
            instance_variables=set(),
            protocols=protocols,
            docstring=inspect.getdoc(cls)
        )

    def _inspect_method(self, name: str, method: Any, is_special: bool = False) -> MethodInfo:
        """Inspect a method."""
        try:
            sig = str(inspect.signature(method))
        except (ValueError, TypeError):
            sig = "(...)"

        # Determine method type
        if isinstance(method, classmethod):
            method_type = "classmethod"
        elif isinstance(method, staticmethod):
            method_type = "staticmethod"
        else:
            method_type = "instance"

        return MethodInfo(
            name=name,
            type=method_type,
            signature=sig,
            docstring=inspect.getdoc(method),
            is_special=is_special,
            is_private=name.startswith('_') and not is_special
        )

    def _inspect_property(self, name: str, prop: property) -> PropertyInfo:
        """Inspect a property."""
        return PropertyInfo(
            name=name,
            has_getter=prop.fget is not None,
            has_setter=prop.fset is not None,
            has_deleter=prop.fdel is not None,
            docstring=inspect.getdoc(prop.fget) if prop.fget else None
        )

    def _detect_protocols(self, cls: type) -> List[str]:
        """Detect which Python protocols a class implements."""
        protocols = []

        # Iterator protocol
        if hasattr(cls, '__iter__') and hasattr(cls, '__next__'):
            protocols.append('iterator')

        # Sequence protocol
        if hasattr(cls, '__len__') and hasattr(cls, '__getitem__'):
            protocols.append('sequence')

        # Mapping protocol
        if (hasattr(cls, '__len__') and hasattr(cls, '__getitem__') and
            hasattr(cls, 'keys')):
            protocols.append('mapping')

        # Context manager protocol
        if hasattr(cls, '__enter__') and hasattr(cls, '__exit__'):
            protocols.append('context_manager')

        # Callable protocol
        if hasattr(cls, '__call__'):
            protocols.append('callable')

        # Comparison protocol
        if hasattr(cls, '__eq__') or hasattr(cls, '__richcmp__'):
            protocols.append('comparison')

        # Numeric protocols
        if hasattr(cls, '__add__'):
            protocols.append('numeric')

        return protocols

    def validate_protocol(self, cls: type, protocol: str) -> Dict[str, Any]:
        """Validate that a class properly implements a protocol."""
        self.log(f"Validating {protocol} protocol for {cls.__name__}")

        results = {
            'protocol': protocol,
            'valid': False,
            'missing_methods': [],
            'present_methods': [],
            'issues': []
        }

        protocol_requirements = {
            'iterator': ['__iter__', '__next__'],
            'sequence': ['__len__', '__getitem__'],
            'mapping': ['__len__', '__getitem__', '__setitem__', 'keys'],
            'context_manager': ['__enter__', '__exit__'],
            'comparison': ['__eq__', '__ne__', '__lt__', '__le__', '__gt__', '__ge__'],
        }

        if protocol not in protocol_requirements:
            results['issues'].append(f"Unknown protocol: {protocol}")
            return results

        required_methods = protocol_requirements[protocol]

        for method_name in required_methods:
            if hasattr(cls, method_name):
                results['present_methods'].append(method_name)
            else:
                results['missing_methods'].append(method_name)

        results['valid'] = len(results['missing_methods']) == 0

        return results

    def analyze_hierarchy(self, cls: type, max_depth: int = 10) -> Dict[str, Any]:
        """Analyze class hierarchy."""
        self.log(f"Analyzing hierarchy for {cls.__name__}")

        def get_hierarchy(c: type, depth: int = 0) -> Dict[str, Any]:
            if depth > max_depth:
                return {'name': '...', 'truncated': True}

            bases = []
            for base in c.__bases__:
                if base != object:
                    bases.append(get_hierarchy(base, depth + 1))

            return {
                'name': c.__name__,
                'module': c.__module__,
                'bases': bases,
                'is_pyo3': self._is_pyo3_class(c)
            }

        return get_hierarchy(cls)

    def _is_pyo3_class(self, cls: type) -> bool:
        """Check if a class is a PyO3 class."""
        # Heuristic: PyO3 classes often have a Rust module
        module = getattr(cls, '__module__', '')
        return not module.startswith('__') and '.' not in module

    def generate_documentation(self, cls: type, format: str = 'markdown') -> str:
        """Generate documentation for a class."""
        info = self.inspect_class(cls)

        if format == 'markdown':
            return self._generate_markdown_docs(info)
        elif format == 'rst':
            return self._generate_rst_docs(info)
        else:
            raise ValueError(f"Unsupported format: {format}")

    def _generate_markdown_docs(self, info: ClassInfo) -> str:
        """Generate Markdown documentation."""
        lines = []

        # Header
        lines.append(f"# {info.name}")
        lines.append("")

        if info.docstring:
            lines.append(info.docstring)
            lines.append("")

        # Module and bases
        lines.append(f"**Module**: `{info.module}`")
        if info.bases:
            lines.append(f"**Bases**: {', '.join(f'`{b}`' for b in info.bases)}")
        lines.append("")

        # Protocols
        if info.protocols:
            lines.append("**Implements Protocols**: " + ", ".join(f"`{p}`" for p in info.protocols))
            lines.append("")

        # Properties
        if info.properties:
            lines.append("## Properties")
            lines.append("")
            for prop in info.properties:
                access = []
                if prop.has_getter:
                    access.append("read")
                if prop.has_setter:
                    access.append("write")
                lines.append(f"### {prop.name}")
                lines.append(f"**Access**: {', '.join(access)}")
                if prop.docstring:
                    lines.append(f"
{prop.docstring}")
                lines.append("")

        # Methods
        if info.methods:
            lines.append("## Methods")
            lines.append("")

            # Regular methods
            regular = [m for m in info.methods if not m.is_special and not m.is_private]
            if regular:
                lines.append("### Public Methods")
                lines.append("")
                for method in regular:
                    lines.append(f"#### {method.name}{method.signature}")
                    lines.append(f"**Type**: {method.type}")
                    if method.docstring:
                        lines.append(f"
{method.docstring}")
                    lines.append("")

            # Special methods
            special = [m for m in info.methods if m.is_special]
            if special:
                lines.append("### Special Methods")
                lines.append("")
                for method in special:
                    lines.append(f"- `{method.name}{method.signature}`")
                lines.append("")

        return "
".join(lines)

    def _generate_rst_docs(self, info: ClassInfo) -> str:
        """Generate reStructuredText documentation."""
        lines = []

        # Header
        lines.append(info.name)
        lines.append("=" * len(info.name))
        lines.append("")

        if info.docstring:
            lines.append(info.docstring)
            lines.append("")

        # Rest of RST generation...
        lines.append(".. note:: RST generation not fully implemented")

        return "
".join(lines)

    def compare_classes(self, cls1: type, cls2: type) -> Dict[str, Any]:
        """Compare two classes."""
        info1 = self.inspect_class(cls1)
        info2 = self.inspect_class(cls2)

        method_names1 = {m.name for m in info1.methods}
        method_names2 = {m.name for m in info2.methods}

        prop_names1 = {p.name for p in info1.properties}
        prop_names2 = {p.name for p in info2.properties}

        return {
            'class1': info1.name,
            'class2': info2.name,
            'common_methods': list(method_names1 & method_names2),
            'unique_to_class1': list(method_names1 - method_names2),
            'unique_to_class2': list(method_names2 - method_names1),
            'common_properties': list(prop_names1 & prop_names2),
            'unique_props_class1': list(prop_names1 - prop_names2),
            'unique_props_class2': list(prop_names2 - prop_names1),
            'common_protocols': list(set(info1.protocols) & set(info2.protocols)),
        }


def cmd_inspect(args):
    """Handle inspect command."""
    inspector = ClassInspector(verbose=args.verbose)

    # Import the module/class
    try:
        module_parts = args.target.rsplit('.', 1)
        if len(module_parts) == 2:
            module_name, class_name = module_parts
            module = __import__(module_name, fromlist=[class_name])
            target = getattr(module, class_name)
        else:
            module = __import__(args.target)
            target = module
    except (ImportError, AttributeError) as e:
        print(f"Error: Could not import {args.target}: {e}", file=sys.stderr)
        return 1

    if inspect.isclass(target):
        info = inspector.inspect_class(target)

        if args.json:
            print(json.dumps(asdict(info), indent=2, default=str))
        else:
            print(f"
Class: {info.name}")
            print(f"Module: {info.module}")
            if info.bases:
                print(f"Bases: {', '.join(info.bases)}")
            print(f"
Methods: {len(info.methods)}")
            print(f"Properties: {len(info.properties)}")
            print(f"Protocols: {', '.join(info.protocols) if info.protocols else 'None'}")

            if args.verbose:
                print("
Methods:")
                for method in info.methods:
                    print(f"  - {method.name}{method.signature} ({method.type})")

                print("
Properties:")
                for prop in info.properties:
                    access = "read" if prop.has_getter else ""
                    if prop.has_setter:
                        access += "/write" if access else "write"
                    print(f"  - {prop.name} ({access})")

    return 0


def cmd_validate(args):
    """Handle validate command."""
    inspector = ClassInspector(verbose=args.verbose)

    # Import class
    try:
        module_parts = args.target.rsplit('.', 1)
        if len(module_parts) == 2:
            module_name, class_name = module_parts
            module = __import__(module_name, fromlist=[class_name])
            cls = getattr(module, class_name)
        else:
            print("Error: Target must be a class (module.ClassName)", file=sys.stderr)
            return 1
    except (ImportError, AttributeError) as e:
        print(f"Error: Could not import {args.target}: {e}", file=sys.stderr)
        return 1

    result = inspector.validate_protocol(cls, args.protocol)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"
Protocol Validation: {args.protocol}")
        print(f"Class: {cls.__name__}")
        print(f"Valid: {'✓' if result['valid'] else '✗'}")

        if result['present_methods']:
            print(f"
Present methods:")
            for method in result['present_methods']:
                print(f"  ✓ {method}")

        if result['missing_methods']:
            print(f"
Missing methods:")
            for method in result['missing_methods']:
                print(f"  ✗ {method}")

        if result['issues']:
            print(f"
Issues:")
            for issue in result['issues']:
                print(f"  - {issue}")

    return 0 if result['valid'] else 1


def cmd_generate(args):
    """Handle generate command."""
    inspector = ClassInspector(verbose=args.verbose)

    # Import class
    try:
        module_parts = args.target.rsplit('.', 1)
        if len(module_parts) == 2:
            module_name, class_name = module_parts
            module = __import__(module_name, fromlist=[class_name])
            cls = getattr(module, class_name)
        else:
            print("Error: Target must be a class", file=sys.stderr)
            return 1
    except (ImportError, AttributeError) as e:
        print(f"Error: Could not import {args.target}: {e}", file=sys.stderr)
        return 1

    docs = inspector.generate_documentation(cls, format=args.format)

    if args.output:
        with open(args.output, 'w') as f:
            f.write(docs)
        print(f"Documentation written to: {args.output}")
    else:
        print(docs)

    return 0


def cmd_hierarchy(args):
    """Handle hierarchy command."""
    inspector = ClassInspector(verbose=args.verbose)

    # Import class
    try:
        module_parts = args.target.rsplit('.', 1)
        if len(module_parts) == 2:
            module_name, class_name = module_parts
            module = __import__(module_name, fromlist=[class_name])
            cls = getattr(module, class_name)
        else:
            print("Error: Target must be a class", file=sys.stderr)
            return 1
    except (ImportError, AttributeError) as e:
        print(f"Error: Could not import {args.target}: {e}", file=sys.stderr)
        return 1

    hierarchy = inspector.analyze_hierarchy(cls, max_depth=args.depth)

    if args.json:
        print(json.dumps(hierarchy, indent=2))
    else:
        def print_hierarchy(node, indent=0):
            prefix = "  " * indent
            pyo3_marker = " [PyO3]" if node.get('is_pyo3') else ""
            print(f"{prefix}- {node['name']}{pyo3_marker}")
            for base in node.get('bases', []):
                print_hierarchy(base, indent + 1)

        print("
Class Hierarchy:")
        print_hierarchy(hierarchy)

    return 0


def cmd_compare(args):
    """Handle compare command."""
    inspector = ClassInspector(verbose=args.verbose)

    # Import classes
    try:
        module_parts1 = args.class1.rsplit('.', 1)
        module_name1, class_name1 = module_parts1
        module1 = __import__(module_name1, fromlist=[class_name1])
        cls1 = getattr(module1, class_name1)

        module_parts2 = args.class2.rsplit('.', 1)
        module_name2, class_name2 = module_parts2
        module2 = __import__(module_name2, fromlist=[class_name2])
        cls2 = getattr(module2, class_name2)
    except (ImportError, AttributeError) as e:
        print(f"Error: Could not import classes: {e}", file=sys.stderr)
        return 1

    comparison = inspector.compare_classes(cls1, cls2)

    if args.json:
        print(json.dumps(comparison, indent=2))
    else:
        print(f"
Comparing: {comparison['class1']} vs {comparison['class2']}")
        print(f"
Common methods: {len(comparison['common_methods'])}")
        for method in comparison['common_methods']:
            print(f"  - {method}")

        print(f"
Unique to {comparison['class1']}: {len(comparison['unique_to_class1'])}")
        for method in comparison['unique_to_class1']:
            print(f"  - {method}")

        print(f"
Unique to {comparison['class2']}: {len(comparison['unique_to_class2'])}")
        for method in comparison['unique_to_class2']:
            print(f"  - {method}")

    return 0


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="PyO3 Class Inspector",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('--verbose', action='store_true', help='Verbose output')

    subparsers = parser.add_subparsers(dest='command', help='Command to run')

    # Inspect command
    inspect_parser = subparsers.add_parser('inspect', help='Inspect a class')
    inspect_parser.add_argument('target', help='Class to inspect (module.ClassName)')
    inspect_parser.add_argument('--json', action='store_true', help='Output as JSON')

    # Validate command
    validate_parser = subparsers.add_parser('validate', help='Validate protocol')
    validate_parser.add_argument('target', help='Class to validate')
    validate_parser.add_argument('--protocol', required=True, 
                                help='Protocol to validate (iterator, sequence, mapping, etc.)')
    validate_parser.add_argument('--json', action='store_true', help='Output as JSON')

    # Generate command
    generate_parser = subparsers.add_parser('generate', help='Generate documentation')
    generate_parser.add_argument('target', help='Class to document')
    generate_parser.add_argument('--format', choices=['markdown', 'rst'], default='markdown',
                                help='Documentation format')
    generate_parser.add_argument('--output', help='Output file (default: stdout)')

    # Hierarchy command
    hierarchy_parser = subparsers.add_parser('hierarchy', help='Analyze hierarchy')
    hierarchy_parser.add_argument('target', help='Class to analyze')
    hierarchy_parser.add_argument('--depth', type=int, default=10, help='Maximum depth')
    hierarchy_parser.add_argument('--json', action='store_true', help='Output as JSON')

    # Compare command
    compare_parser = subparsers.add_parser('compare', help='Compare classes')
    compare_parser.add_argument('class1', help='First class')
    compare_parser.add_argument('class2', help='Second class')
    compare_parser.add_argument('--json', action='store_true', help='Output as JSON')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    handlers = {
        'inspect': cmd_inspect,
        'validate': cmd_validate,
        'generate': cmd_generate,
        'hierarchy': cmd_hierarchy,
        'compare': cmd_compare,
    }

    handler = handlers.get(args.command)
    if handler:
        return handler(args)

    return 1


if __name__ == "__main__":
    sys.exit(main())
