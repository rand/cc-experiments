#!/usr/bin/env python3
"""
PyO3 Plugin Manager

A comprehensive plugin management system for PyO3-based applications.
Provides plugin discovery, loading, unloading, hot-reload, lifecycle management,
dependency resolution, and state management.

Features:
- Plugin discovery from directories and entry points
- Dynamic loading and unloading
- Hot-reload capabilities with state preservation
- Lifecycle hooks (initialize, shutdown, reload)
- Dependency resolution and ordering
- Plugin isolation and error recovery
- State persistence and restoration
- Comprehensive validation and diagnostics

Usage:
    # List available plugins
    plugin_manager.py list --verbose

    # Load specific plugins
    plugin_manager.py load plugin1 plugin2 --config config.json

    # Reload a plugin with state preservation
    plugin_manager.py reload plugin_name --preserve-state

    # Discover plugins in directories
    plugin_manager.py discover /path/to/plugins --recursive

    # Validate plugin dependencies
    plugin_manager.py validate plugin_name

    # Monitor loaded plugins
    plugin_manager.py monitor --interval 5

Examples:
    # Discover all plugins in directory
    python plugin_manager.py discover ./plugins --verbose

    # Load plugins with dependency resolution
    python plugin_manager.py load data_processor visualizer --resolve-deps

    # Hot reload a plugin
    python plugin_manager.py reload data_processor --preserve-state

    # Export plugin state
    python plugin_manager.py export plugin_name --output state.json

    # Validate all loaded plugins
    python plugin_manager.py validate --all

Author: PyO3 Skills Initiative
License: MIT
"""

import argparse
import importlib
import importlib.util
import inspect
import json
import logging
import os
import sys
import time
import traceback
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Type, Protocol
from enum import Enum
import hashlib
import pickle
import threading
from collections import defaultdict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PluginState(Enum):
    """Plugin lifecycle states."""
    DISCOVERED = "discovered"
    LOADED = "loaded"
    INITIALIZED = "initialized"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    FAILED = "failed"
    UNLOADED = "unloaded"


class PluginInterface(Protocol):
    """Protocol defining the plugin interface."""

    name: str
    version: str
    dependencies: List[str]

    def initialize(self) -> None:
        """Initialize the plugin."""
        ...

    def shutdown(self) -> None:
        """Shutdown the plugin."""
        ...

    def get_state(self) -> Dict[str, Any]:
        """Get plugin state for persistence."""
        ...

    def set_state(self, state: Dict[str, Any]) -> None:
        """Restore plugin state."""
        ...


@dataclass
class PluginMetadata:
    """Metadata for a plugin."""
    name: str
    version: str
    author: str = ""
    description: str = ""
    dependencies: List[str] = field(default_factory=list)
    entry_point: str = ""
    module_path: str = ""
    file_hash: str = ""
    load_order: int = 0
    state: PluginState = PluginState.DISCOVERED
    error_message: str = ""
    load_time: float = 0.0
    last_reload: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data['state'] = self.state.value
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PluginMetadata':
        """Create from dictionary."""
        if 'state' in data and isinstance(data['state'], str):
            data['state'] = PluginState(data['state'])
        return cls(**data)


@dataclass
class PluginEntry:
    """Entry for a loaded plugin."""
    metadata: PluginMetadata
    instance: Optional[Any] = None
    module: Optional[Any] = None
    class_type: Optional[Type] = None
    state_data: Dict[str, Any] = field(default_factory=dict)
    error_count: int = 0
    last_error: Optional[str] = None


class DependencyResolver:
    """Resolves plugin dependencies and determines load order."""

    def __init__(self):
        self.graph: Dict[str, Set[str]] = defaultdict(set)

    def add_dependency(self, plugin: str, dependency: str) -> None:
        """Add a dependency relationship."""
        self.graph[plugin].add(dependency)

    def resolve(self, plugins: List[str]) -> List[str]:
        """
        Resolve dependencies and return plugins in load order.

        Uses topological sort to determine correct order.
        Raises ValueError if circular dependencies detected.
        """
        # Build graph for requested plugins
        visited = set()
        temp_mark = set()
        result = []

        def visit(plugin: str) -> None:
            if plugin in temp_mark:
                raise ValueError(f"Circular dependency detected involving {plugin}")
            if plugin in visited:
                return

            temp_mark.add(plugin)
            for dep in self.graph.get(plugin, set()):
                visit(dep)
            temp_mark.remove(plugin)
            visited.add(plugin)
            result.append(plugin)

        for plugin in plugins:
            if plugin not in visited:
                visit(plugin)

        return result

    def validate(self, plugin: str, available: Set[str]) -> Tuple[bool, List[str]]:
        """
        Validate that all dependencies are available.

        Returns (is_valid, missing_dependencies).
        """
        missing = []
        for dep in self.graph.get(plugin, set()):
            if dep not in available:
                missing.append(dep)
        return len(missing) == 0, missing


class PluginDiscovery:
    """Discovers plugins from various sources."""

    def __init__(self):
        self.discovered: Dict[str, PluginMetadata] = {}

    def discover_directory(
        self,
        directory: Path,
        recursive: bool = False,
        pattern: str = "*.py"
    ) -> List[PluginMetadata]:
        """
        Discover plugins in a directory.

        Looks for Python files with a Plugin class that matches the interface.
        """
        discovered = []

        if recursive:
            files = directory.rglob(pattern)
        else:
            files = directory.glob(pattern)

        for file_path in files:
            if file_path.stem.startswith('_'):
                continue

            try:
                metadata = self._inspect_file(file_path)
                if metadata:
                    discovered.append(metadata)
                    self.discovered[metadata.name] = metadata
                    logger.info(f"Discovered plugin: {metadata.name} v{metadata.version}")
            except Exception as e:
                logger.warning(f"Failed to inspect {file_path}: {e}")

        return discovered

    def _inspect_file(self, file_path: Path) -> Optional[PluginMetadata]:
        """Inspect a Python file for plugin class."""
        # Calculate file hash
        file_hash = self._calculate_hash(file_path)

        # Load module
        spec = importlib.util.spec_from_file_location(file_path.stem, file_path)
        if not spec or not spec.loader:
            return None

        module = importlib.util.module_from_spec(spec)

        try:
            spec.loader.exec_module(module)
        except Exception as e:
            logger.warning(f"Failed to load module {file_path}: {e}")
            return None

        # Find plugin class
        plugin_class = None
        for name, obj in inspect.getmembers(module):
            if inspect.isclass(obj) and name == 'Plugin':
                plugin_class = obj
                break

        if not plugin_class:
            return None

        # Extract metadata
        name = getattr(plugin_class, 'name', file_path.stem)
        version = getattr(plugin_class, 'version', '0.0.0')
        author = getattr(plugin_class, 'author', '')
        description = getattr(plugin_class, 'description', '')
        dependencies = getattr(plugin_class, 'dependencies', [])

        return PluginMetadata(
            name=name,
            version=version,
            author=author,
            description=description,
            dependencies=dependencies,
            entry_point=f"{file_path.stem}.Plugin",
            module_path=str(file_path),
            file_hash=file_hash,
            state=PluginState.DISCOVERED
        )

    def _calculate_hash(self, file_path: Path) -> str:
        """Calculate SHA256 hash of file."""
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                sha256.update(chunk)
        return sha256.hexdigest()

    def discover_entry_points(self, group: str = 'pyo3_plugins') -> List[PluginMetadata]:
        """Discover plugins via entry points."""
        discovered = []

        try:
            from importlib.metadata import entry_points

            eps = entry_points()
            if hasattr(eps, 'select'):
                # Python 3.10+
                plugin_eps = eps.select(group=group)
            else:
                # Python 3.9
                plugin_eps = eps.get(group, [])

            for ep in plugin_eps:
                try:
                    plugin_class = ep.load()
                    metadata = PluginMetadata(
                        name=getattr(plugin_class, 'name', ep.name),
                        version=getattr(plugin_class, 'version', '0.0.0'),
                        author=getattr(plugin_class, 'author', ''),
                        description=getattr(plugin_class, 'description', ''),
                        dependencies=getattr(plugin_class, 'dependencies', []),
                        entry_point=ep.value,
                        state=PluginState.DISCOVERED
                    )
                    discovered.append(metadata)
                    self.discovered[metadata.name] = metadata
                    logger.info(f"Discovered plugin via entry point: {metadata.name}")
                except Exception as e:
                    logger.warning(f"Failed to load entry point {ep.name}: {e}")
        except ImportError:
            logger.warning("importlib.metadata not available, skipping entry point discovery")

        return discovered


class PluginManager:
    """
    Manages plugin lifecycle, dependencies, and state.

    Provides comprehensive plugin management including discovery, loading,
    unloading, hot-reload, dependency resolution, and state persistence.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.plugins: Dict[str, PluginEntry] = {}
        self.discovery = PluginDiscovery()
        self.resolver = DependencyResolver()
        self.lock = threading.RLock()
        self._monitor_thread: Optional[threading.Thread] = None
        self._monitoring = False

    def discover(
        self,
        source: Path,
        recursive: bool = False,
        use_entry_points: bool = False
    ) -> List[PluginMetadata]:
        """
        Discover plugins from directory or entry points.
        """
        discovered = []

        if source.is_dir():
            discovered.extend(self.discovery.discover_directory(source, recursive))

        if use_entry_points:
            discovered.extend(self.discovery.discover_entry_points())

        # Build dependency graph
        for metadata in discovered:
            for dep in metadata.dependencies:
                self.resolver.add_dependency(metadata.name, dep)

        return discovered

    def load(
        self,
        plugin_name: str,
        resolve_deps: bool = True,
        initialize: bool = True
    ) -> bool:
        """
        Load a plugin (and optionally its dependencies).

        Returns True if successful, False otherwise.
        """
        with self.lock:
            # Check if already loaded
            if plugin_name in self.plugins:
                logger.info(f"Plugin {plugin_name} already loaded")
                return True

            # Get metadata
            if plugin_name not in self.discovery.discovered:
                logger.error(f"Plugin {plugin_name} not discovered")
                return False

            metadata = self.discovery.discovered[plugin_name]

            # Resolve dependencies if requested
            if resolve_deps:
                plugins_to_load = self.resolver.resolve([plugin_name])
            else:
                plugins_to_load = [plugin_name]

            # Load in dependency order
            for name in plugins_to_load:
                if name not in self.plugins:
                    if not self._load_single(name, initialize):
                        logger.error(f"Failed to load plugin: {name}")
                        return False

            return True

    def _load_single(self, plugin_name: str, initialize: bool) -> bool:
        """Load a single plugin."""
        if plugin_name not in self.discovery.discovered:
            logger.error(f"Plugin {plugin_name} not discovered")
            return False

        metadata = self.discovery.discovered[plugin_name]
        start_time = time.time()

        try:
            # Load module
            if metadata.module_path:
                spec = importlib.util.spec_from_file_location(
                    plugin_name,
                    metadata.module_path
                )
                if not spec or not spec.loader:
                    raise ImportError(f"Failed to load spec for {plugin_name}")

                module = importlib.util.module_from_spec(spec)
                sys.modules[plugin_name] = module
                spec.loader.exec_module(module)
            else:
                module = importlib.import_module(metadata.entry_point.rsplit('.', 1)[0])

            # Get plugin class
            plugin_class = None
            for name, obj in inspect.getmembers(module):
                if inspect.isclass(obj) and name == 'Plugin':
                    plugin_class = obj
                    break

            if not plugin_class:
                raise ValueError(f"No Plugin class found in {plugin_name}")

            # Instantiate
            instance = plugin_class()

            # Create entry
            entry = PluginEntry(
                metadata=metadata,
                instance=instance,
                module=module,
                class_type=plugin_class
            )

            # Initialize if requested
            if initialize and hasattr(instance, 'initialize'):
                instance.initialize()
                metadata.state = PluginState.INITIALIZED
            else:
                metadata.state = PluginState.LOADED

            metadata.load_time = time.time() - start_time
            self.plugins[plugin_name] = entry

            logger.info(f"Loaded plugin: {plugin_name} in {metadata.load_time:.3f}s")
            return True

        except Exception as e:
            metadata.state = PluginState.FAILED
            metadata.error_message = str(e)
            logger.error(f"Failed to load plugin {plugin_name}: {e}")
            logger.debug(traceback.format_exc())
            return False

    def unload(self, plugin_name: str, preserve_state: bool = False) -> bool:
        """
        Unload a plugin.

        Optionally preserves state for later restoration.
        """
        with self.lock:
            if plugin_name not in self.plugins:
                logger.warning(f"Plugin {plugin_name} not loaded")
                return False

            entry = self.plugins[plugin_name]

            try:
                # Save state if requested
                if preserve_state and hasattr(entry.instance, 'get_state'):
                    entry.state_data = entry.instance.get_state()

                # Shutdown
                if hasattr(entry.instance, 'shutdown'):
                    entry.instance.shutdown()

                # Remove from sys.modules
                if entry.module and plugin_name in sys.modules:
                    del sys.modules[plugin_name]

                entry.metadata.state = PluginState.UNLOADED
                del self.plugins[plugin_name]

                logger.info(f"Unloaded plugin: {plugin_name}")
                return True

            except Exception as e:
                logger.error(f"Error unloading plugin {plugin_name}: {e}")
                entry.error_count += 1
                entry.last_error = str(e)
                return False

    def reload(self, plugin_name: str, preserve_state: bool = True) -> bool:
        """
        Hot-reload a plugin, optionally preserving state.
        """
        with self.lock:
            if plugin_name not in self.plugins:
                logger.error(f"Plugin {plugin_name} not loaded")
                return False

            entry = self.plugins[plugin_name]

            # Save state
            state_data = {}
            if preserve_state and hasattr(entry.instance, 'get_state'):
                try:
                    state_data = entry.instance.get_state()
                except Exception as e:
                    logger.warning(f"Failed to save state for {plugin_name}: {e}")

            # Unload
            if not self.unload(plugin_name, preserve_state=False):
                return False

            # Re-discover to get updated file
            if entry.metadata.module_path:
                path = Path(entry.metadata.module_path)
                if path.exists():
                    self.discovery.discover_directory(path.parent, recursive=False)

            # Reload
            if not self.load(plugin_name, resolve_deps=False, initialize=True):
                return False

            # Restore state
            if preserve_state and state_data:
                new_entry = self.plugins[plugin_name]
                if hasattr(new_entry.instance, 'set_state'):
                    try:
                        new_entry.instance.set_state(state_data)
                        logger.info(f"Restored state for {plugin_name}")
                    except Exception as e:
                        logger.warning(f"Failed to restore state for {plugin_name}: {e}")

            self.plugins[plugin_name].metadata.last_reload = time.time()
            logger.info(f"Reloaded plugin: {plugin_name}")
            return True

    def validate(self, plugin_name: str) -> Tuple[bool, List[str]]:
        """
        Validate plugin dependencies.

        Returns (is_valid, issues).
        """
        if plugin_name not in self.discovery.discovered:
            return False, [f"Plugin {plugin_name} not discovered"]

        available = set(self.discovery.discovered.keys())
        is_valid, missing = self.resolver.validate(plugin_name, available)

        issues = []
        if not is_valid:
            issues.append(f"Missing dependencies: {', '.join(missing)}")

        return is_valid, issues

    def get_state(self, plugin_name: str) -> Optional[Dict[str, Any]]:
        """Get current state of a plugin."""
        if plugin_name not in self.plugins:
            return None

        entry = self.plugins[plugin_name]
        if hasattr(entry.instance, 'get_state'):
            return entry.instance.get_state()
        return {}

    def export_state(self, plugin_name: str, output_path: Path) -> bool:
        """Export plugin state to file."""
        state = self.get_state(plugin_name)
        if state is None:
            logger.error(f"Plugin {plugin_name} not loaded")
            return False

        try:
            with open(output_path, 'w') as f:
                json.dump(state, f, indent=2)
            logger.info(f"Exported state for {plugin_name} to {output_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to export state: {e}")
            return False

    def list_plugins(self, state_filter: Optional[PluginState] = None) -> List[PluginMetadata]:
        """List all plugins, optionally filtered by state."""
        plugins = list(self.discovery.discovered.values())

        if state_filter:
            plugins = [p for p in plugins if p.state == state_filter]

        return sorted(plugins, key=lambda p: p.name)

    def start_monitoring(self, interval: float = 5.0) -> None:
        """Start monitoring loaded plugins for changes."""
        if self._monitoring:
            logger.warning("Monitoring already active")
            return

        self._monitoring = True
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            args=(interval,),
            daemon=True
        )
        self._monitor_thread.start()
        logger.info(f"Started monitoring with {interval}s interval")

    def stop_monitoring(self) -> None:
        """Stop monitoring."""
        self._monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5.0)
        logger.info("Stopped monitoring")

    def _monitor_loop(self, interval: float) -> None:
        """Monitor loop for file changes."""
        while self._monitoring:
            try:
                with self.lock:
                    for name, entry in list(self.plugins.items()):
                        if not entry.metadata.module_path:
                            continue

                        path = Path(entry.metadata.module_path)
                        if not path.exists():
                            logger.warning(f"Plugin file missing: {name}")
                            continue

                        # Check if file changed
                        current_hash = self.discovery._calculate_hash(path)
                        if current_hash != entry.metadata.file_hash:
                            logger.info(f"Detected change in {name}, reloading...")
                            self.reload(name, preserve_state=True)

                time.sleep(interval)
            except Exception as e:
                logger.error(f"Error in monitor loop: {e}")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='PyO3 Plugin Manager',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )

    parser.add_argument(
        '--json',
        action='store_true',
        help='Output in JSON format'
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to execute')

    # Discover command
    discover_parser = subparsers.add_parser('discover', help='Discover plugins')
    discover_parser.add_argument('path', type=Path, help='Directory to search')
    discover_parser.add_argument('--recursive', '-r', action='store_true', help='Recursive search')
    discover_parser.add_argument('--entry-points', action='store_true', help='Also discover entry points')

    # List command
    list_parser = subparsers.add_parser('list', help='List plugins')
    list_parser.add_argument('--state', choices=[s.value for s in PluginState], help='Filter by state')

    # Load command
    load_parser = subparsers.add_parser('load', help='Load plugin(s)')
    load_parser.add_argument('plugins', nargs='+', help='Plugin names to load')
    load_parser.add_argument('--resolve-deps', action='store_true', help='Resolve dependencies')
    load_parser.add_argument('--no-init', action='store_true', help='Skip initialization')

    # Unload command
    unload_parser = subparsers.add_parser('unload', help='Unload plugin')
    unload_parser.add_argument('plugin', help='Plugin name')
    unload_parser.add_argument('--preserve-state', action='store_true', help='Preserve state')

    # Reload command
    reload_parser = subparsers.add_parser('reload', help='Reload plugin')
    reload_parser.add_argument('plugin', help='Plugin name')
    reload_parser.add_argument('--no-preserve', action='store_true', help='Don\'t preserve state')

    # Validate command
    validate_parser = subparsers.add_parser('validate', help='Validate plugin')
    validate_parser.add_argument('plugin', nargs='?', help='Plugin name (or --all)')
    validate_parser.add_argument('--all', action='store_true', help='Validate all plugins')

    # Export command
    export_parser = subparsers.add_parser('export', help='Export plugin state')
    export_parser.add_argument('plugin', help='Plugin name')
    export_parser.add_argument('--output', '-o', type=Path, required=True, help='Output file')

    # Monitor command
    monitor_parser = subparsers.add_parser('monitor', help='Monitor plugins for changes')
    monitor_parser.add_argument('--interval', type=float, default=5.0, help='Check interval (seconds)')

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Create manager
    manager = PluginManager()

    try:
        if args.command == 'discover':
            plugins = manager.discover(args.path, args.recursive, args.entry_points)

            if args.json:
                print(json.dumps([p.to_dict() for p in plugins], indent=2))
            else:
                print(f"\nDiscovered {len(plugins)} plugin(s):")
                for p in plugins:
                    print(f"  {p.name} v{p.version}")
                    if args.verbose:
                        print(f"    Path: {p.module_path}")
                        print(f"    Dependencies: {', '.join(p.dependencies) if p.dependencies else 'none'}")

        elif args.command == 'list':
            state_filter = PluginState(args.state) if args.state else None
            plugins = manager.list_plugins(state_filter)

            if args.json:
                print(json.dumps([p.to_dict() for p in plugins], indent=2))
            else:
                print(f"\n{len(plugins)} plugin(s):")
                for p in plugins:
                    print(f"  {p.name} v{p.version} [{p.state.value}]")
                    if args.verbose:
                        print(f"    Author: {p.author}")
                        print(f"    Dependencies: {', '.join(p.dependencies) if p.dependencies else 'none'}")
                        if p.load_time > 0:
                            print(f"    Load time: {p.load_time:.3f}s")

        elif args.command == 'load':
            # First discover if not done
            for plugin_name in args.plugins:
                success = manager.load(
                    plugin_name,
                    resolve_deps=args.resolve_deps,
                    initialize=not args.no_init
                )
                if not success:
                    sys.exit(1)
            print(f"Successfully loaded {len(args.plugins)} plugin(s)")

        elif args.command == 'unload':
            success = manager.unload(args.plugin, args.preserve_state)
            if not success:
                sys.exit(1)
            print(f"Successfully unloaded {args.plugin}")

        elif args.command == 'reload':
            success = manager.reload(args.plugin, preserve_state=not args.no_preserve)
            if not success:
                sys.exit(1)
            print(f"Successfully reloaded {args.plugin}")

        elif args.command == 'validate':
            if args.all:
                plugins = manager.list_plugins()
                results = {}
                for p in plugins:
                    is_valid, issues = manager.validate(p.name)
                    results[p.name] = {'valid': is_valid, 'issues': issues}

                if args.json:
                    print(json.dumps(results, indent=2))
                else:
                    print("\nValidation results:")
                    for name, result in results.items():
                        status = "✓" if result['valid'] else "✗"
                        print(f"  {status} {name}")
                        if result['issues']:
                            for issue in result['issues']:
                                print(f"      {issue}")
            else:
                if not args.plugin:
                    parser.error("Either provide plugin name or use --all")

                is_valid, issues = manager.validate(args.plugin)
                if args.json:
                    print(json.dumps({'valid': is_valid, 'issues': issues}, indent=2))
                else:
                    if is_valid:
                        print(f"✓ {args.plugin} is valid")
                    else:
                        print(f"✗ {args.plugin} has issues:")
                        for issue in issues:
                            print(f"    {issue}")
                        sys.exit(1)

        elif args.command == 'export':
            success = manager.export_state(args.plugin, args.output)
            if not success:
                sys.exit(1)
            print(f"Exported state to {args.output}")

        elif args.command == 'monitor':
            print(f"Monitoring plugins (interval: {args.interval}s)")
            print("Press Ctrl+C to stop")
            manager.start_monitoring(args.interval)
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\nStopping monitor...")
                manager.stop_monitoring()

        else:
            parser.print_help()
            sys.exit(1)

    except KeyboardInterrupt:
        print("\nInterrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Error: {e}")
        if args.verbose:
            logger.debug(traceback.format_exc())
        sys.exit(1)


if __name__ == '__main__':
    main()
