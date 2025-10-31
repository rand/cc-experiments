#!/usr/bin/env python3
"""
Tool Registry Manager for DSPy ReAct Agents

Manage tool registry for DSPy ReAct agents - register, validate, and execute tools.
Provides comprehensive tool management with validation, execution, testing, and export.

Usage:
    python tool_registry.py register search --description "Web search" --params "query: str"
    python tool_registry.py list
    python tool_registry.py validate search
    python tool_registry.py execute search --params '{"query": "test"}'
    python tool_registry.py test search --mock-input sample.json
    python tool_registry.py export --format rust > tools.rs
"""

import os
import sys
import json
import time
import signal
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict, field
from datetime import datetime
from enum import Enum
from pathlib import Path


class ToolType(str, Enum):
    """Supported tool types."""
    FUNCTION = "function"
    API = "api"
    COMMAND = "command"
    SEARCH = "search"
    CALCULATOR = "calculator"
    CUSTOM = "custom"


class ParamType(str, Enum):
    """Supported parameter types."""
    STRING = "str"
    INTEGER = "int"
    FLOAT = "float"
    BOOLEAN = "bool"
    DICT = "dict"
    LIST = "list"


@dataclass
class ToolParameter:
    """Tool parameter definition."""
    name: str
    type_name: str
    description: str
    required: bool = True
    default: Optional[Any] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {k: v for k, v in asdict(self).items() if v is not None}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ToolParameter':
        """Create from dictionary."""
        return cls(**data)

    def validate_value(self, value: Any) -> tuple[bool, Optional[str]]:
        """Validate parameter value.

        Returns:
            (is_valid, error_message)
        """
        if value is None:
            if self.required and self.default is None:
                return False, f"Required parameter '{self.name}' is missing"
            return True, None

        # Type validation
        type_map = {
            ParamType.STRING: str,
            ParamType.INTEGER: int,
            ParamType.FLOAT: (int, float),
            ParamType.BOOLEAN: bool,
            ParamType.DICT: dict,
            ParamType.LIST: list,
        }

        expected_type = type_map.get(ParamType(self.type_name))
        if expected_type and not isinstance(value, expected_type):
            return False, f"Parameter '{self.name}' must be {self.type_name}, got {type(value).__name__}"

        return True, None


@dataclass
class ToolMetadata:
    """Tool metadata and schema."""
    name: str
    description: str
    tool_type: str
    parameters: List[ToolParameter]
    returns: str = "str"
    examples: List[str] = field(default_factory=list)
    timeout: int = 30  # seconds
    created_at: Optional[str] = None
    last_used: Optional[str] = None
    use_count: int = 0

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data['parameters'] = [p.to_dict() for p in self.parameters]
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ToolMetadata':
        """Create from dictionary."""
        params_data = data.pop('parameters', [])
        parameters = [ToolParameter.from_dict(p) for p in params_data]
        return cls(parameters=parameters, **data)

    def validate(self) -> tuple[bool, Optional[str]]:
        """Validate tool metadata.

        Returns:
            (is_valid, error_message)
        """
        if not self.name:
            return False, "Tool name is required"

        if not self.description:
            return False, "Tool description is required"

        if self.tool_type not in [t.value for t in ToolType]:
            return False, f"Invalid tool type: {self.tool_type}"

        if self.timeout < 1:
            return False, f"Timeout must be positive, got {self.timeout}"

        # Validate parameters
        param_names = set()
        for param in self.parameters:
            if param.name in param_names:
                return False, f"Duplicate parameter name: {param.name}"
            param_names.add(param.name)

            if param.type_name not in [t.value for t in ParamType]:
                return False, f"Invalid parameter type: {param.type_name}"

        return True, None


@dataclass
class ToolExecution:
    """Tool execution record."""
    tool_name: str
    input_params: Dict[str, Any]
    output: Optional[str]
    error: Optional[str]
    duration_ms: int
    timestamp: str
    success: bool

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ToolExecution':
        """Create from dictionary."""
        return cls(**data)


@dataclass
class ToolStats:
    """Tool execution statistics."""
    tool_name: str
    total_executions: int
    successful_executions: int
    failed_executions: int
    average_duration_ms: float
    min_duration_ms: int
    max_duration_ms: int
    last_execution: Optional[str]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


class ToolRegistry:
    """Manage tool registry for DSPy ReAct agents."""

    def __init__(self, registry_path: Optional[str] = None):
        """Initialize tool registry.

        Args:
            registry_path: Path to registry JSON file (default: ./tool_registry.json)
        """
        self.registry_path = registry_path or "./tool_registry.json"
        self.tools: Dict[str, ToolMetadata] = {}
        self.executions: List[ToolExecution] = []
        self.builtin_tools: Dict[str, Callable] = {}

        self._register_builtin_tools()
        self.load()

    def _register_builtin_tools(self):
        """Register built-in example tools."""
        # Search tool
        self.builtin_tools['search'] = self._search_tool

        # Calculator tool
        self.builtin_tools['calculator'] = self._calculator_tool

    def _search_tool(self, query: str) -> str:
        """Example search tool (mock implementation)."""
        return f"Search results for: {query}\n1. Example result 1\n2. Example result 2\n3. Example result 3"

    def _calculator_tool(self, expression: str) -> str:
        """Example calculator tool (safe evaluation)."""
        try:
            # Only allow basic arithmetic
            allowed_chars = set('0123456789+-*/(). ')
            if not all(c in allowed_chars for c in expression):
                raise ValueError("Only basic arithmetic operations allowed")

            result = eval(expression, {"__builtins__": {}})
            return str(result)
        except Exception as e:
            raise ValueError(f"Calculation error: {e}")

    def register(
        self,
        name: str,
        description: str,
        tool_type: str,
        parameters: List[ToolParameter],
        returns: str = "str",
        examples: Optional[List[str]] = None,
        timeout: int = 30,
    ) -> tuple[bool, Optional[str]]:
        """Register a new tool.

        Returns:
            (success, error_message)
        """
        metadata = ToolMetadata(
            name=name,
            description=description,
            tool_type=tool_type,
            parameters=parameters,
            returns=returns,
            examples=examples or [],
            timeout=timeout,
        )

        # Validate metadata
        is_valid, error = metadata.validate()
        if not is_valid:
            return False, error

        # Check for duplicates
        if name in self.tools:
            return False, f"Tool '{name}' already registered"

        self.tools[name] = metadata
        self.save()

        return True, None

    def unregister(self, name: str) -> tuple[bool, Optional[str]]:
        """Unregister a tool.

        Returns:
            (success, error_message)
        """
        if name not in self.tools:
            return False, f"Tool '{name}' not found"

        del self.tools[name]
        self.save()

        return True, None

    def get_metadata(self, name: str) -> Optional[ToolMetadata]:
        """Get tool metadata."""
        return self.tools.get(name)

    def list_tools(self) -> List[str]:
        """List all registered tools."""
        return sorted(self.tools.keys())

    def validate_tool(self, name: str) -> tuple[bool, Optional[str]]:
        """Validate tool exists and is properly configured.

        Returns:
            (is_valid, error_message)
        """
        if name not in self.tools:
            return False, f"Tool '{name}' not found"

        metadata = self.tools[name]
        return metadata.validate()

    def execute(
        self,
        name: str,
        params: Dict[str, Any],
        timeout_override: Optional[int] = None,
    ) -> tuple[Optional[str], Optional[str]]:
        """Execute a tool with given parameters.

        Returns:
            (output, error)
        """
        start_time = time.time()

        # Validate tool exists
        if name not in self.tools:
            error = f"Tool '{name}' not found"
            self._record_execution(name, params, None, error, 0, False)
            return None, error

        metadata = self.tools[name]
        timeout = timeout_override or metadata.timeout

        # Validate parameters
        validation_error = self._validate_params(metadata, params)
        if validation_error:
            self._record_execution(name, params, None, validation_error, 0, False)
            return None, validation_error

        # Execute tool with timeout
        try:
            output = self._execute_with_timeout(name, params, timeout)
            duration = int((time.time() - start_time) * 1000)

            self._record_execution(name, params, output, None, duration, True)

            # Update metadata
            metadata.last_used = datetime.utcnow().isoformat()
            metadata.use_count += 1
            self.save()

            return output, None

        except TimeoutError as e:
            duration = int((time.time() - start_time) * 1000)
            error = f"Tool execution timeout after {timeout}s"
            self._record_execution(name, params, None, error, duration, False)
            return None, error

        except Exception as e:
            duration = int((time.time() - start_time) * 1000)
            error = f"Tool execution error: {e}"
            self._record_execution(name, params, None, error, duration, False)
            return None, error

    def _validate_params(
        self,
        metadata: ToolMetadata,
        params: Dict[str, Any],
    ) -> Optional[str]:
        """Validate execution parameters.

        Returns:
            Error message if invalid, None if valid
        """
        # Check all required parameters are present
        for param in metadata.parameters:
            value = params.get(param.name, param.default)
            is_valid, error = param.validate_value(value)
            if not is_valid:
                return error

        # Check for unknown parameters
        known_params = {p.name for p in metadata.parameters}
        unknown_params = set(params.keys()) - known_params
        if unknown_params:
            return f"Unknown parameters: {', '.join(unknown_params)}"

        return None

    def _execute_with_timeout(
        self,
        name: str,
        params: Dict[str, Any],
        timeout: int,
    ) -> str:
        """Execute tool with timeout protection."""

        class TimeoutException(Exception):
            pass

        def timeout_handler(signum, frame):
            raise TimeoutException("Tool execution timeout")

        # Get tool function
        if name not in self.builtin_tools:
            raise ValueError(f"Tool '{name}' has no implementation")

        tool_fn = self.builtin_tools[name]

        # Set timeout
        old_handler = signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(timeout)

        try:
            # Execute tool
            result = tool_fn(**params)
            signal.alarm(0)  # Cancel alarm
            return result
        except TimeoutException:
            raise TimeoutError(f"Tool execution exceeded {timeout}s timeout")
        finally:
            signal.signal(signal.SIGALRM, old_handler)

    def _record_execution(
        self,
        tool_name: str,
        params: Dict[str, Any],
        output: Optional[str],
        error: Optional[str],
        duration_ms: int,
        success: bool,
    ):
        """Record tool execution."""
        execution = ToolExecution(
            tool_name=tool_name,
            input_params=params,
            output=output,
            error=error,
            duration_ms=duration_ms,
            timestamp=datetime.utcnow().isoformat(),
            success=success,
        )
        self.executions.append(execution)

    def get_stats(self, tool_name: str) -> Optional[ToolStats]:
        """Get execution statistics for a tool."""
        if tool_name not in self.tools:
            return None

        tool_execs = [e for e in self.executions if e.tool_name == tool_name]

        if not tool_execs:
            return ToolStats(
                tool_name=tool_name,
                total_executions=0,
                successful_executions=0,
                failed_executions=0,
                average_duration_ms=0.0,
                min_duration_ms=0,
                max_duration_ms=0,
                last_execution=None,
            )

        total = len(tool_execs)
        successful = sum(1 for e in tool_execs if e.success)
        failed = total - successful

        durations = [e.duration_ms for e in tool_execs]
        avg_duration = sum(durations) / len(durations)
        min_duration = min(durations)
        max_duration = max(durations)

        last_exec = max(tool_execs, key=lambda e: e.timestamp)

        return ToolStats(
            tool_name=tool_name,
            total_executions=total,
            successful_executions=successful,
            failed_executions=failed,
            average_duration_ms=avg_duration,
            min_duration_ms=min_duration,
            max_duration_ms=max_duration,
            last_execution=last_exec.timestamp,
        )

    def export_schema(self, format_type: str = "json") -> str:
        """Export tool schemas in specified format.

        Args:
            format_type: Output format (json, rust, python)

        Returns:
            Formatted schema string
        """
        if format_type == "json":
            return self._export_json()
        elif format_type == "rust":
            return self._export_rust()
        elif format_type == "python":
            return self._export_python()
        else:
            raise ValueError(f"Unsupported format: {format_type}")

    def _export_json(self) -> str:
        """Export as JSON."""
        schema = {
            "tools": [meta.to_dict() for meta in self.tools.values()]
        }
        return json.dumps(schema, indent=2)

    def _export_rust(self) -> str:
        """Export as Rust structs."""
        lines = [
            "// Auto-generated tool definitions",
            "use serde::{Deserialize, Serialize};",
            "",
            "#[derive(Debug, Clone, Serialize, Deserialize)]",
            "pub struct ToolParameter {",
            "    pub name: String,",
            "    pub type_name: String,",
            "    pub description: String,",
            "    pub required: bool,",
            "}",
            "",
            "#[derive(Debug, Clone, Serialize, Deserialize)]",
            "pub struct ToolMetadata {",
            "    pub name: String,",
            "    pub description: String,",
            "    pub parameters: Vec<ToolParameter>,",
            "    pub returns: String,",
            "}",
            "",
            "pub fn get_tool_definitions() -> Vec<ToolMetadata> {",
            "    vec![",
        ]

        for metadata in self.tools.values():
            lines.append(f"        ToolMetadata {{")
            lines.append(f'            name: "{metadata.name}".to_string(),')
            lines.append(f'            description: "{metadata.description}".to_string(),')
            lines.append(f"            parameters: vec![")

            for param in metadata.parameters:
                lines.append(f"                ToolParameter {{")
                lines.append(f'                    name: "{param.name}".to_string(),')
                lines.append(f'                    type_name: "{param.type_name}".to_string(),')
                lines.append(f'                    description: "{param.description}".to_string(),')
                lines.append(f"                    required: {str(param.required).lower()},")
                lines.append(f"                }},")

            lines.append(f"            ],")
            lines.append(f'            returns: "{metadata.returns}".to_string(),')
            lines.append(f"        }},")

        lines.append("    ]")
        lines.append("}")

        return "\n".join(lines)

    def _export_python(self) -> str:
        """Export as Python definitions."""
        lines = [
            "# Auto-generated tool definitions",
            "from typing import Dict, List, Any",
            "",
            "TOOL_DEFINITIONS = [",
        ]

        for metadata in self.tools.values():
            lines.append("    {")
            lines.append(f'        "name": "{metadata.name}",')
            lines.append(f'        "description": "{metadata.description}",')
            lines.append(f'        "parameters": [')

            for param in metadata.parameters:
                lines.append("            {")
                lines.append(f'                "name": "{param.name}",')
                lines.append(f'                "type": "{param.type_name}",')
                lines.append(f'                "description": "{param.description}",')
                lines.append(f'                "required": {param.required},')
                lines.append("            },")

            lines.append("        ],")
            lines.append(f'        "returns": "{metadata.returns}",')
            lines.append("    },")

        lines.append("]")

        return "\n".join(lines)

    def save(self):
        """Save registry to file."""
        data = {
            "tools": {name: meta.to_dict() for name, meta in self.tools.items()},
            "executions": [exec.to_dict() for exec in self.executions[-1000:]],  # Keep last 1000
        }

        with open(self.registry_path, 'w') as f:
            json.dump(data, f, indent=2)

    def load(self):
        """Load registry from file."""
        if not os.path.exists(self.registry_path):
            return

        try:
            with open(self.registry_path) as f:
                data = json.load(f)

            self.tools = {
                name: ToolMetadata.from_dict(meta)
                for name, meta in data.get("tools", {}).items()
            }

            self.executions = [
                ToolExecution.from_dict(exec)
                for exec in data.get("executions", [])
            ]

        except Exception as e:
            print(f"Warning: Failed to load registry: {e}", file=sys.stderr)


# CLI Commands

def cmd_register(args, registry: ToolRegistry):
    """Register a new tool."""
    # Parse parameters
    parameters = []
    if args.params:
        for param_str in args.params:
            # Format: "name: type: description" or "name: type"
            parts = param_str.split(':', 2)
            if len(parts) < 2:
                print(f"Invalid parameter format: {param_str}")
                print("Expected format: 'name: type' or 'name: type: description'")
                sys.exit(1)

            name = parts[0].strip()
            type_name = parts[1].strip()
            description = parts[2].strip() if len(parts) > 2 else f"{name} parameter"

            parameters.append(ToolParameter(
                name=name,
                type_name=type_name,
                description=description,
                required=True,
            ))

    success, error = registry.register(
        name=args.name,
        description=args.description,
        tool_type=args.type,
        parameters=parameters,
        returns=args.returns,
        examples=args.examples or [],
        timeout=args.timeout,
    )

    if success:
        print(f"✓ Tool '{args.name}' registered successfully")
    else:
        print(f"✗ Registration failed: {error}")
        sys.exit(1)


def cmd_list(args, registry: ToolRegistry):
    """List all registered tools."""
    tools = registry.list_tools()

    if not tools:
        print("No tools registered")
        return

    print(f"\nRegistered Tools ({len(tools)}):\n")
    print("=" * 80)

    for tool_name in tools:
        metadata = registry.get_metadata(tool_name)
        if metadata:
            print(f"\n{tool_name}")
            print(f"  Type: {metadata.tool_type}")
            print(f"  Description: {metadata.description}")
            print(f"  Parameters: {len(metadata.parameters)}")

            if args.verbose:
                for param in metadata.parameters:
                    req = "required" if param.required else "optional"
                    print(f"    - {param.name} ({param.type_name}, {req}): {param.description}")

            stats = registry.get_stats(tool_name)
            if stats and stats.total_executions > 0:
                success_rate = (stats.successful_executions / stats.total_executions) * 100
                print(f"  Executions: {stats.total_executions} (success rate: {success_rate:.1f}%)")

    print("\n" + "=" * 80 + "\n")


def cmd_validate(args, registry: ToolRegistry):
    """Validate a tool."""
    is_valid, error = registry.validate_tool(args.name)

    if is_valid:
        print(f"✓ Tool '{args.name}' is valid")

        metadata = registry.get_metadata(args.name)
        if metadata:
            print(f"  Description: {metadata.description}")
            print(f"  Type: {metadata.tool_type}")
            print(f"  Parameters: {len(metadata.parameters)}")
            print(f"  Timeout: {metadata.timeout}s")

        sys.exit(0)
    else:
        print(f"✗ Tool '{args.name}' is invalid: {error}")
        sys.exit(1)


def cmd_execute(args, registry: ToolRegistry):
    """Execute a tool."""
    try:
        params = json.loads(args.params) if args.params else {}
    except json.JSONDecodeError as e:
        print(f"✗ Invalid JSON parameters: {e}")
        sys.exit(1)

    print(f"Executing tool '{args.name}'...")

    output, error = registry.execute(args.name, params, args.timeout)

    if error:
        print(f"✗ Execution failed: {error}")
        sys.exit(1)
    else:
        print(f"✓ Execution successful!")
        print(f"\nOutput:\n{output}")

        stats = registry.get_stats(args.name)
        if stats:
            print(f"\nStats: {stats.total_executions} executions, "
                  f"avg {stats.average_duration_ms:.0f}ms")


def cmd_test(args, registry: ToolRegistry):
    """Test a tool with mock input."""
    if args.mock_input:
        try:
            with open(args.mock_input) as f:
                test_data = json.load(f)
        except Exception as e:
            print(f"✗ Failed to load mock input: {e}")
            sys.exit(1)
    else:
        # Generate default test data
        metadata = registry.get_metadata(args.name)
        if not metadata:
            print(f"✗ Tool '{args.name}' not found")
            sys.exit(1)

        test_data = {}
        for param in metadata.parameters:
            if param.required:
                # Generate test value based on type
                if param.type_name == ParamType.STRING.value:
                    test_data[param.name] = "test"
                elif param.type_name == ParamType.INTEGER.value:
                    test_data[param.name] = 42
                elif param.type_name == ParamType.FLOAT.value:
                    test_data[param.name] = 3.14
                elif param.type_name == ParamType.BOOLEAN.value:
                    test_data[param.name] = True
                elif param.type_name == ParamType.DICT.value:
                    test_data[param.name] = {}
                elif param.type_name == ParamType.LIST.value:
                    test_data[param.name] = []

    print(f"Testing tool '{args.name}' with mock input:")
    print(json.dumps(test_data, indent=2))
    print()

    output, error = registry.execute(args.name, test_data)

    if error:
        print(f"✗ Test failed: {error}")
        sys.exit(1)
    else:
        print(f"✓ Test passed!")
        print(f"\nOutput:\n{output}")


def cmd_export(args, registry: ToolRegistry):
    """Export tool schemas."""
    try:
        schema = registry.export_schema(args.format)

        if args.output:
            with open(args.output, 'w') as f:
                f.write(schema)
            print(f"✓ Schema exported to {args.output}")
        else:
            print(schema)

    except Exception as e:
        print(f"✗ Export failed: {e}")
        sys.exit(1)


def cmd_stats(args, registry: ToolRegistry):
    """Show tool statistics."""
    if args.name:
        # Stats for specific tool
        stats = registry.get_stats(args.name)
        if not stats:
            print(f"✗ Tool '{args.name}' not found or has no executions")
            sys.exit(1)

        print(f"\nStatistics for '{args.name}':\n")
        print(f"  Total executions: {stats.total_executions}")
        print(f"  Successful: {stats.successful_executions}")
        print(f"  Failed: {stats.failed_executions}")

        if stats.total_executions > 0:
            success_rate = (stats.successful_executions / stats.total_executions) * 100
            print(f"  Success rate: {success_rate:.1f}%")

        print(f"  Average duration: {stats.average_duration_ms:.0f}ms")
        print(f"  Min duration: {stats.min_duration_ms}ms")
        print(f"  Max duration: {stats.max_duration_ms}ms")

        if stats.last_execution:
            print(f"  Last execution: {stats.last_execution}")
    else:
        # Stats for all tools
        print(f"\nTool Statistics:\n")
        print("=" * 80)

        for tool_name in sorted(registry.list_tools()):
            stats = registry.get_stats(tool_name)
            if stats and stats.total_executions > 0:
                success_rate = (stats.successful_executions / stats.total_executions) * 100
                print(f"\n{tool_name}:")
                print(f"  Executions: {stats.total_executions} "
                      f"({stats.successful_executions} success, {stats.failed_executions} failed)")
                print(f"  Success rate: {success_rate:.1f}%")
                print(f"  Avg duration: {stats.average_duration_ms:.0f}ms")

        print("\n" + "=" * 80 + "\n")


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Tool Registry Manager for DSPy ReAct Agents"
    )
    parser.add_argument(
        '--registry',
        default='./tool_registry.json',
        help='Path to registry file (default: ./tool_registry.json)'
    )

    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # Register command
    parser_reg = subparsers.add_parser('register', help='Register a new tool')
    parser_reg.add_argument('name', help='Tool name')
    parser_reg.add_argument('--description', required=True, help='Tool description')
    parser_reg.add_argument('--type', default='custom', help='Tool type (default: custom)')
    parser_reg.add_argument('--params', nargs='+', help='Parameters (format: "name: type: description")')
    parser_reg.add_argument('--returns', default='str', help='Return type (default: str)')
    parser_reg.add_argument('--examples', nargs='+', help='Usage examples')
    parser_reg.add_argument('--timeout', type=int, default=30, help='Timeout in seconds (default: 30)')

    # List command
    parser_list = subparsers.add_parser('list', help='List all tools')
    parser_list.add_argument('--verbose', '-v', action='store_true', help='Show detailed information')

    # Validate command
    parser_val = subparsers.add_parser('validate', help='Validate a tool')
    parser_val.add_argument('name', help='Tool name')

    # Execute command
    parser_exec = subparsers.add_parser('execute', help='Execute a tool')
    parser_exec.add_argument('name', help='Tool name')
    parser_exec.add_argument('--params', help='Tool parameters as JSON')
    parser_exec.add_argument('--timeout', type=int, help='Timeout override in seconds')

    # Test command
    parser_test = subparsers.add_parser('test', help='Test a tool with mock input')
    parser_test.add_argument('name', help='Tool name')
    parser_test.add_argument('--mock-input', help='Path to JSON file with test data')

    # Export command
    parser_export = subparsers.add_parser('export', help='Export tool schemas')
    parser_export.add_argument('--format', choices=['json', 'rust', 'python'],
                               default='json', help='Export format (default: json)')
    parser_export.add_argument('--output', '-o', help='Output file (default: stdout)')

    # Stats command
    parser_stats = subparsers.add_parser('stats', help='Show tool statistics')
    parser_stats.add_argument('name', nargs='?', help='Tool name (optional, shows all if omitted)')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Initialize registry
    registry = ToolRegistry(args.registry)

    # Execute command
    if args.command == 'register':
        cmd_register(args, registry)
    elif args.command == 'list':
        cmd_list(args, registry)
    elif args.command == 'validate':
        cmd_validate(args, registry)
    elif args.command == 'execute':
        cmd_execute(args, registry)
    elif args.command == 'test':
        cmd_test(args, registry)
    elif args.command == 'export':
        cmd_export(args, registry)
    elif args.command == 'stats':
        cmd_stats(args, registry)


if __name__ == "__main__":
    main()
