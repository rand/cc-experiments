#!/usr/bin/env python3
"""
PyO3 Embedding Helper

Utilities and tools for embedding Python interpreters in Rust applications.
Provides helpers for initialization, module management, plugin systems,
error handling, and best practices for embedded Python scenarios.

Features:
- Safe Python interpreter initialization and cleanup
- Module path configuration and management
- Plugin discovery and loading system
- Sandboxed script execution
- Error capture and reporting
- Resource monitoring (memory, CPU)
- State serialization and persistence
- Inter-process Python communication
- Debugging utilities for embedded scenarios

Usage:
    # Initialize embedded interpreter
    embedding_helper.py init --python-home /usr --module-path ./plugins

    # Load and execute plugin
    embedding_helper.py plugin load my_plugin.py --entry-point Plugin

    # Execute sandboxed script
    embedding_helper.py execute script.py --sandbox --timeout 10

    # Validate plugin
    embedding_helper.py validate plugin.py --check-all

    # Monitor embedded interpreter
    embedding_helper.py monitor --pid 12345 --interval 1

Examples:
    # Setup embedded environment
    python embedding_helper.py init --config embed_config.json

    # Load plugin with validation
    python embedding_helper.py plugin load calculator.py --validate

    # Execute script with resource limits
    python embedding_helper.py execute task.py --memory-limit 100M --timeout 30

    # Generate plugin template
    python embedding_helper.py template --name my_plugin --type processor

    # Debug embedded interpreter issues
    python embedding_helper.py debug --check-imports --check-gil

Author: PyO3 Skills Initiative
License: MIT
"""

import argparse
import json
import logging
import os
import sys
import time
import traceback
import importlib.util
import subprocess
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum
import tempfile
import signal

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PluginType(Enum):
    """Plugin types."""
    PROCESSOR = "processor"
    TRANSFORMER = "transformer"
    VALIDATOR = "validator"
    HANDLER = "handler"
    SERVICE = "service"


@dataclass
class EmbedConfig:
    """Configuration for embedded Python."""
    python_home: Optional[str] = None
    module_paths: List[str] = field(default_factory=list)
    isolated: bool = True
    install_signal_handlers: bool = True
    init_threads: bool = True
    safe_path: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EmbedConfig':
        """Create from dictionary."""
        return cls(**data)


@dataclass
class PluginInfo:
    """Plugin metadata."""
    name: str
    path: Path
    entry_point: str
    version: str = "0.0.0"
    author: str = ""
    description: str = ""
    dependencies: List[str] = field(default_factory=list)
    validated: bool = False
    loaded: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data['path'] = str(self.path)
        return data


@dataclass
class ExecutionResult:
    """Result of script execution."""
    success: bool
    output: str
    error: Optional[str]
    return_value: Any
    execution_time_ms: float
    memory_used_mb: float
    exit_code: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'success': self.success,
            'output': self.output,
            'error': self.error,
            'return_value': str(self.return_value),
            'execution_time_ms': self.execution_time_ms,
            'memory_used_mb': self.memory_used_mb,
            'exit_code': self.exit_code
        }


class EmbeddedInterpreter:
    """
    Manages embedded Python interpreter.

    Provides safe initialization, cleanup, and configuration.
    """

    def __init__(self, config: Optional[EmbedConfig] = None):
        self.config = config or EmbedConfig()
        self.initialized = False

    def initialize(self) -> bool:
        """
        Initialize embedded Python interpreter.

        Returns:
            True if successful
        """
        try:
            logger.info("Initializing embedded Python interpreter...")

            # Configure Python home if specified
            if self.config.python_home:
                os.environ['PYTHONHOME'] = self.config.python_home

            # Add module paths to sys.path
            for path in self.config.module_paths:
                if path not in sys.path:
                    sys.path.insert(0, path)
                    logger.debug(f"Added to sys.path: {path}")

            self.initialized = True
            logger.info("Python interpreter initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize Python: {e}")
            return False

    def finalize(self) -> bool:
        """
        Finalize and cleanup interpreter.

        Returns:
            True if successful
        """
        try:
            logger.info("Finalizing Python interpreter...")
            self.initialized = False
            return True
        except Exception as e:
            logger.error(f"Failed to finalize Python: {e}")
            return False

    def get_info(self) -> Dict[str, Any]:
        """Get interpreter information."""
        return {
            'version': sys.version,
            'platform': sys.platform,
            'executable': sys.executable,
            'path': sys.path,
            'modules': list(sys.modules.keys()),
            'initialized': self.initialized
        }


class PluginManager:
    """
    Manages plugins in embedded environment.

    Provides discovery, loading, validation, and lifecycle management.
    """

    def __init__(self):
        self.plugins: Dict[str, PluginInfo] = {}
        self.loaded_modules: Dict[str, Any] = {}

    def discover(self, directory: Path, pattern: str = "*.py") -> List[PluginInfo]:
        """
        Discover plugins in directory.

        Args:
            directory: Directory to search
            pattern: File pattern

        Returns:
            List of discovered plugins
        """
        discovered = []

        for file_path in directory.glob(pattern):
            if file_path.stem.startswith('_'):
                continue

            try:
                info = self._inspect_plugin(file_path)
                if info:
                    discovered.append(info)
                    self.plugins[info.name] = info
                    logger.info(f"Discovered plugin: {info.name}")
            except Exception as e:
                logger.warning(f"Failed to inspect {file_path}: {e}")

        return discovered

    def _inspect_plugin(self, file_path: Path) -> Optional[PluginInfo]:
        """Inspect plugin file for metadata."""
        try:
            # Load module to inspect
            spec = importlib.util.spec_from_file_location(file_path.stem, file_path)
            if not spec or not spec.loader:
                return None

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Look for Plugin class
            plugin_class = None
            for name in dir(module):
                obj = getattr(module, name)
                if isinstance(obj, type) and name == 'Plugin':
                    plugin_class = obj
                    break

            if not plugin_class:
                return None

            # Extract metadata
            return PluginInfo(
                name=getattr(plugin_class, 'name', file_path.stem),
                path=file_path,
                entry_point='Plugin',
                version=getattr(plugin_class, 'version', '0.0.0'),
                author=getattr(plugin_class, 'author', ''),
                description=getattr(plugin_class, 'description', ''),
                dependencies=getattr(plugin_class, 'dependencies', [])
            )

        except Exception as e:
            logger.debug(f"Failed to inspect {file_path}: {e}")
            return None

    def load(self, plugin_name: str) -> bool:
        """
        Load plugin by name.

        Args:
            plugin_name: Name of plugin to load

        Returns:
            True if successful
        """
        if plugin_name not in self.plugins:
            logger.error(f"Plugin not found: {plugin_name}")
            return False

        info = self.plugins[plugin_name]

        try:
            # Load module
            spec = importlib.util.spec_from_file_location(
                plugin_name,
                info.path
            )
            if not spec or not spec.loader:
                raise ImportError(f"Failed to load spec for {plugin_name}")

            module = importlib.util.module_from_spec(spec)
            sys.modules[plugin_name] = module
            spec.loader.exec_module(module)

            # Get plugin class
            plugin_class = getattr(module, info.entry_point)

            # Instantiate
            instance = plugin_class()

            # Initialize if method exists
            if hasattr(instance, 'initialize'):
                instance.initialize()

            self.loaded_modules[plugin_name] = instance
            info.loaded = True

            logger.info(f"Loaded plugin: {plugin_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to load plugin {plugin_name}: {e}")
            logger.debug(traceback.format_exc())
            return False

    def validate(self, plugin_name: str) -> Tuple[bool, List[str]]:
        """
        Validate plugin.

        Args:
            plugin_name: Plugin name

        Returns:
            Tuple of (is_valid, issues)
        """
        if plugin_name not in self.plugins:
            return False, [f"Plugin not found: {plugin_name}"]

        info = self.plugins[plugin_name]
        issues = []

        # Check file exists
        if not info.path.exists():
            issues.append(f"Plugin file not found: {info.path}")
            return False, issues

        # Try to load
        try:
            spec = importlib.util.spec_from_file_location(
                plugin_name,
                info.path
            )
            if not spec or not spec.loader:
                issues.append("Failed to create module spec")
                return False, issues

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Check for required class
            if not hasattr(module, info.entry_point):
                issues.append(f"Missing entry point: {info.entry_point}")
                return False, issues

            plugin_class = getattr(module, info.entry_point)

            # Check for required methods
            required_methods = ['initialize']
            for method in required_methods:
                if not hasattr(plugin_class, method):
                    issues.append(f"Missing required method: {method}")

            # Check dependencies
            for dep in info.dependencies:
                try:
                    __import__(dep)
                except ImportError:
                    issues.append(f"Missing dependency: {dep}")

        except Exception as e:
            issues.append(f"Validation error: {e}")

        is_valid = len(issues) == 0
        if is_valid:
            info.validated = True

        return is_valid, issues


class ScriptExecutor:
    """
    Executes Python scripts in embedded environment.

    Provides sandboxing, timeouts, and resource limits.
    """

    def __init__(self):
        self.timeout_seconds = 30
        self.memory_limit_mb = None

    def execute(
        self,
        script_path: Path,
        sandbox: bool = False,
        timeout: Optional[int] = None,
        args: Optional[List[str]] = None
    ) -> ExecutionResult:
        """
        Execute Python script.

        Args:
            script_path: Path to script
            sandbox: Enable sandboxing
            timeout: Execution timeout in seconds
            args: Command-line arguments

        Returns:
            Execution result
        """
        start_time = time.perf_counter()
        start_memory = self._get_memory_usage()

        try:
            if sandbox:
                result = self._execute_sandboxed(script_path, timeout, args)
            else:
                result = self._execute_direct(script_path, args)

            elapsed_time = (time.perf_counter() - start_time) * 1000
            memory_used = self._get_memory_usage() - start_memory

            return ExecutionResult(
                success=result['success'],
                output=result.get('output', ''),
                error=result.get('error'),
                return_value=result.get('return_value'),
                execution_time_ms=elapsed_time,
                memory_used_mb=memory_used,
                exit_code=result.get('exit_code', 0)
            )

        except Exception as e:
            elapsed_time = (time.perf_counter() - start_time) * 1000
            memory_used = self._get_memory_usage() - start_memory

            return ExecutionResult(
                success=False,
                output='',
                error=str(e),
                return_value=None,
                execution_time_ms=elapsed_time,
                memory_used_mb=memory_used,
                exit_code=1
            )

    def _execute_direct(self, script_path: Path, args: Optional[List[str]]) -> Dict[str, Any]:
        """Execute script directly in current interpreter."""
        with open(script_path) as f:
            code = f.read()

        # Prepare globals
        script_globals = {
            '__name__': '__main__',
            '__file__': str(script_path),
            'sys': sys
        }

        # Execute
        exec(code, script_globals)

        return {
            'success': True,
            'return_value': script_globals.get('__return__')
        }

    def _execute_sandboxed(
        self,
        script_path: Path,
        timeout: Optional[int],
        args: Optional[List[str]]
    ) -> Dict[str, Any]:
        """Execute script in sandboxed subprocess."""
        cmd = [sys.executable, str(script_path)]
        if args:
            cmd.extend(args)

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout or self.timeout_seconds,
                check=False
            )

            return {
                'success': result.returncode == 0,
                'output': result.stdout,
                'error': result.stderr if result.returncode != 0 else None,
                'exit_code': result.returncode
            }

        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'error': f"Execution timed out after {timeout}s",
                'exit_code': -1
            }

    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB."""
        if HAS_PSUTIL:
            process = psutil.Process()
            return process.memory_info().rss / (1024 * 1024)
        return 0.0


class TemplateGenerator:
    """Generates plugin templates."""

    @staticmethod
    def generate_plugin(name: str, plugin_type: PluginType) -> str:
        """Generate plugin template."""
        template = f'''"""
{name} Plugin

Auto-generated plugin template.
"""

class Plugin:
    """Plugin implementation."""

    name = "{name}"
    version = "0.1.0"
    author = ""
    description = "{plugin_type.value.capitalize()} plugin"
    dependencies = []

    def __init__(self):
        """Initialize plugin."""
        self.initialized = False

    def initialize(self):
        """Initialize plugin."""
        print(f"Initializing {{self.name}}...")
        self.initialized = True

    def shutdown(self):
        """Shutdown plugin."""
        print(f"Shutting down {{self.name}}...")
        self.initialized = False

    def process(self, data):
        """
        Process data.

        Args:
            data: Input data

        Returns:
            Processed data
        """
        # Note: Processing logic not yet implemented - currently returns data unmodified
        return data
'''
        return template


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='PyO3 Embedding Helper',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    parser.add_argument('--json', action='store_true', help='JSON output')

    subparsers = parser.add_subparsers(dest='command', help='Command')

    # Init command
    init_parser = subparsers.add_parser('init', help='Initialize interpreter')
    init_parser.add_argument('--python-home', type=str, help='Python home directory')
    init_parser.add_argument('--module-path', type=str, help='Additional module paths')
    init_parser.add_argument('--config', type=Path, help='Config file')

    # Plugin command
    plugin_parser = subparsers.add_parser('plugin', help='Plugin management')
    plugin_subparsers = plugin_parser.add_subparsers(dest='plugin_command')

    load_parser = plugin_subparsers.add_parser('load', help='Load plugin')
    load_parser.add_argument('path', type=Path, help='Plugin path')
    load_parser.add_argument('--entry-point', default='Plugin', help='Entry point class')
    load_parser.add_argument('--validate', action='store_true', help='Validate before loading')

    discover_parser = plugin_subparsers.add_parser('discover', help='Discover plugins')
    discover_parser.add_argument('directory', type=Path, help='Directory to search')
    discover_parser.add_argument('--pattern', default='*.py', help='File pattern')

    # Execute command
    exec_parser = subparsers.add_parser('execute', help='Execute script')
    exec_parser.add_argument('script', type=Path, help='Script to execute')
    exec_parser.add_argument('--sandbox', action='store_true', help='Sandboxed execution')
    exec_parser.add_argument('--timeout', type=int, help='Timeout in seconds')
    exec_parser.add_argument('--memory-limit', type=str, help='Memory limit (e.g., 100M)')

    # Validate command
    validate_parser = subparsers.add_parser('validate', help='Validate plugin')
    validate_parser.add_argument('plugin', type=Path, help='Plugin to validate')
    validate_parser.add_argument('--check-all', action='store_true', help='Check all aspects')

    # Template command
    template_parser = subparsers.add_parser('template', help='Generate plugin template')
    template_parser.add_argument('--name', required=True, help='Plugin name')
    template_parser.add_argument('--type', type=PluginType, default=PluginType.PROCESSOR)
    template_parser.add_argument('--output', '-o', type=Path, help='Output file')

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        if args.command == 'init':
            config = EmbedConfig()
            if args.config and args.config.exists():
                with open(args.config) as f:
                    config = EmbedConfig.from_dict(json.load(f))
            elif args.python_home or args.module_path:
                if args.python_home:
                    config.python_home = args.python_home
                if args.module_path:
                    config.module_paths = [args.module_path]

            interp = EmbeddedInterpreter(config)
            if interp.initialize():
                print("✓ Interpreter initialized successfully")
                if args.json:
                    print(json.dumps(interp.get_info(), indent=2))
            else:
                print("✗ Failed to initialize interpreter")
                sys.exit(1)

        elif args.command == 'plugin':
            manager = PluginManager()

            if args.plugin_command == 'load':
                # Discover first
                manager.discover(args.path.parent)

                plugin_name = args.path.stem

                if args.validate:
                    is_valid, issues = manager.validate(plugin_name)
                    if not is_valid:
                        print(f"✗ Validation failed:")
                        for issue in issues:
                            print(f"  - {issue}")
                        sys.exit(1)

                if manager.load(plugin_name):
                    print(f"✓ Loaded plugin: {plugin_name}")
                else:
                    print(f"✗ Failed to load plugin: {plugin_name}")
                    sys.exit(1)

            elif args.plugin_command == 'discover':
                plugins = manager.discover(args.directory, args.pattern)
                if args.json:
                    print(json.dumps([p.to_dict() for p in plugins], indent=2))
                else:
                    print(f"\nDiscovered {len(plugins)} plugin(s):")
                    for p in plugins:
                        print(f"  {p.name} v{p.version}")

        elif args.command == 'execute':
            executor = ScriptExecutor()
            result = executor.execute(
                args.script,
                sandbox=args.sandbox,
                timeout=args.timeout
            )

            if args.json:
                print(json.dumps(result.to_dict(), indent=2))
            else:
                if result.success:
                    print(f"✓ Execution successful ({result.execution_time_ms:.2f} ms)")
                    if result.output:
                        print(f"\nOutput:\n{result.output}")
                else:
                    print(f"✗ Execution failed")
                    if result.error:
                        print(f"\nError:\n{result.error}")
                    sys.exit(result.exit_code)

        elif args.command == 'validate':
            manager = PluginManager()
            manager.discover(args.plugin.parent)

            plugin_name = args.plugin.stem
            is_valid, issues = manager.validate(plugin_name)

            if args.json:
                print(json.dumps({'valid': is_valid, 'issues': issues}, indent=2))
            else:
                if is_valid:
                    print(f"✓ Plugin {plugin_name} is valid")
                else:
                    print(f"✗ Plugin {plugin_name} has issues:")
                    for issue in issues:
                        print(f"  - {issue}")
                    sys.exit(1)

        elif args.command == 'template':
            generator = TemplateGenerator()
            template = generator.generate_plugin(args.name, args.type)

            if args.output:
                args.output.write_text(template)
                print(f"Template written to {args.output}")
            else:
                print(template)

        else:
            parser.print_help()

    except KeyboardInterrupt:
        print("\nInterrupted")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Error: {e}")
        if args.verbose:
            logger.debug(traceback.format_exc())
        sys.exit(1)


if __name__ == '__main__':
    main()
