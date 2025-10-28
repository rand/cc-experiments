#!/usr/bin/env python3
"""
Protocol Buffer Code Generator

Generates code from .proto files for multiple languages (Python, Go, Java, TypeScript).
Supports custom options, plugins, validation, and dependency management.

Features:
- Multi-language code generation (Python, Go, Java, TypeScript)
- protoc plugin support (grpc, grpc-web, custom)
- Dependency resolution and import handling
- Generated code validation
- Custom options and annotations
- Incremental generation (only changed files)
- Output organization and packaging

Usage:
    ./generate_proto_code.py --proto-file user.proto --language python
    ./generate_proto_code.py --proto-file user.proto --language go --go-package github.com/myorg/protos
    ./generate_proto_code.py --proto-dir ./protos --language python,go,typescript --json
    ./generate_proto_code.py --proto-file service.proto --plugin grpc --language python,go
    ./generate_proto_code.py --proto-file user.proto --validate --incremental
"""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import List, Dict, Set, Optional, Tuple


class Language(Enum):
    """Supported target languages for code generation"""
    PYTHON = "python"
    GO = "go"
    JAVA = "java"
    TYPESCRIPT = "typescript"
    CPP = "cpp"
    CSHARP = "csharp"


class Plugin(Enum):
    """Supported protoc plugins"""
    GRPC = "grpc"
    GRPC_WEB = "grpc-web"
    GRPC_GATEWAY = "grpc-gateway"
    VALIDATE = "validate"
    DOC = "doc"


@dataclass
class GenerationConfig:
    """Configuration for code generation"""
    proto_files: List[Path]
    proto_paths: List[Path]  # -I paths for imports
    languages: List[Language]
    plugins: List[Plugin]
    output_dir: Path
    go_package: Optional[str] = None
    java_package: Optional[str] = None
    java_multiple_files: bool = True
    python_package: Optional[str] = None
    typescript_package: Optional[str] = None
    validate: bool = False
    incremental: bool = False
    protoc_path: str = "protoc"
    plugin_paths: Dict[str, str] = field(default_factory=dict)
    custom_options: Dict[str, str] = field(default_factory=dict)


@dataclass
class GenerationResult:
    """Result of code generation"""
    success: bool
    language: Language
    proto_file: Path
    output_files: List[Path]
    errors: List[str]
    warnings: List[str]
    elapsed_seconds: float
    cache_hit: bool = False

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {
            'success': self.success,
            'language': self.language.value,
            'proto_file': str(self.proto_file),
            'output_files': [str(f) for f in self.output_files],
            'errors': self.errors,
            'warnings': self.warnings,
            'elapsed_seconds': self.elapsed_seconds,
            'cache_hit': self.cache_hit
        }


@dataclass
class CacheEntry:
    """Cache entry for incremental generation"""
    proto_hash: str
    output_files: List[Path]
    timestamp: float


class ProtoCompiler:
    """Manages protoc compilation and code generation"""

    def __init__(self, config: GenerationConfig):
        self.config = config
        self.cache: Dict[Tuple[Path, Language], CacheEntry] = {}
        self.cache_file = config.output_dir / ".proto_cache.json"
        self._load_cache()

    def _load_cache(self) -> None:
        """Load cache from file for incremental builds"""
        if not self.config.incremental or not self.cache_file.exists():
            return

        try:
            with open(self.cache_file, 'r') as f:
                data = json.load(f)
                for key_str, entry_dict in data.items():
                    proto_path, lang = key_str.rsplit(':', 1)
                    key = (Path(proto_path), Language(lang))
                    self.cache[key] = CacheEntry(
                        proto_hash=entry_dict['proto_hash'],
                        output_files=[Path(f) for f in entry_dict['output_files']],
                        timestamp=entry_dict['timestamp']
                    )
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            print(f"Warning: Failed to load cache: {e}", file=sys.stderr)
            self.cache = {}

    def _save_cache(self) -> None:
        """Save cache to file for incremental builds"""
        if not self.config.incremental:
            return

        try:
            self.config.output_dir.mkdir(parents=True, exist_ok=True)
            data = {}
            for (proto_path, lang), entry in self.cache.items():
                key_str = f"{proto_path}:{lang.value}"
                data[key_str] = {
                    'proto_hash': entry.proto_hash,
                    'output_files': [str(f) for f in entry.output_files],
                    'timestamp': entry.timestamp
                }
            with open(self.cache_file, 'w') as f:
                json.dump(data, f, indent=2)
        except (IOError, OSError) as e:
            print(f"Warning: Failed to save cache: {e}", file=sys.stderr)

    def _compute_proto_hash(self, proto_file: Path) -> str:
        """Compute hash of proto file and its dependencies"""
        hasher = hashlib.sha256()
        hasher.update(proto_file.read_bytes())

        # Include import dependencies in hash
        imports = self._extract_imports(proto_file)
        for import_path in sorted(imports):
            for proto_path in self.config.proto_paths:
                full_import = proto_path / import_path
                if full_import.exists():
                    hasher.update(full_import.read_bytes())
                    break

        return hasher.hexdigest()

    def _extract_imports(self, proto_file: Path) -> List[str]:
        """Extract import statements from proto file"""
        imports = []
        with open(proto_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line.startswith('import') and not line.startswith('//'):
                    # Extract: import "path/to/file.proto";
                    match = line.split('"')
                    if len(match) >= 2:
                        imports.append(match[1])
        return imports

    def _check_cache(self, proto_file: Path, language: Language) -> Optional[CacheEntry]:
        """Check if cached result is valid"""
        if not self.config.incremental:
            return None

        cache_key = (proto_file, language)
        if cache_key not in self.cache:
            return None

        cached = self.cache[cache_key]
        current_hash = self._compute_proto_hash(proto_file)

        if cached.proto_hash != current_hash:
            return None

        # Check if all output files still exist
        if not all(f.exists() for f in cached.output_files):
            return None

        return cached

    def _verify_protoc(self) -> Tuple[bool, Optional[str]]:
        """Verify protoc is available"""
        try:
            result = subprocess.run(
                [self.config.protoc_path, "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return True, result.stdout.strip()
            return False, f"protoc failed: {result.stderr}"
        except FileNotFoundError:
            return False, f"protoc not found at: {self.config.protoc_path}"
        except subprocess.TimeoutExpired:
            return False, "protoc version check timed out"

    def _verify_plugin(self, plugin: Plugin) -> Tuple[bool, Optional[str]]:
        """Verify plugin is available"""
        plugin_name = f"protoc-gen-{plugin.value}"

        # Check custom plugin paths first
        if plugin.value in self.config.plugin_paths:
            plugin_path = self.config.plugin_paths[plugin.value]
            if not Path(plugin_path).exists():
                return False, f"Plugin not found: {plugin_path}"
            return True, None

        # Check PATH
        if shutil.which(plugin_name):
            return True, None

        return False, f"Plugin not found: {plugin_name} (install or specify --plugin-path)"

    def generate(self, proto_file: Path, language: Language) -> GenerationResult:
        """Generate code for a single proto file and language"""
        import time
        start_time = time.time()

        # Check cache
        cached = self._check_cache(proto_file, language)
        if cached:
            return GenerationResult(
                success=True,
                language=language,
                proto_file=proto_file,
                output_files=cached.output_files,
                errors=[],
                warnings=["Using cached result"],
                elapsed_seconds=time.time() - start_time,
                cache_hit=True
            )

        errors = []
        warnings = []

        # Verify proto file exists
        if not proto_file.exists():
            errors.append(f"Proto file not found: {proto_file}")
            return GenerationResult(
                success=False,
                language=language,
                proto_file=proto_file,
                output_files=[],
                errors=errors,
                warnings=warnings,
                elapsed_seconds=time.time() - start_time
            )

        # Build protoc command
        cmd = [self.config.protoc_path]

        # Add proto paths
        for proto_path in self.config.proto_paths:
            cmd.extend(["-I", str(proto_path)])

        # Add language-specific output
        output_dir = self.config.output_dir / language.value
        output_dir.mkdir(parents=True, exist_ok=True)

        if language == Language.PYTHON:
            cmd.append(f"--python_out={output_dir}")
        elif language == Language.GO:
            if self.config.go_package:
                cmd.append(f"--go_opt=module={self.config.go_package}")
            cmd.append(f"--go_out={output_dir}")
        elif language == Language.JAVA:
            if self.config.java_package:
                cmd.append(f"--java_opt=package={self.config.java_package}")
            if self.config.java_multiple_files:
                cmd.append("--java_opt=multiple_files=true")
            cmd.append(f"--java_out={output_dir}")
        elif language == Language.TYPESCRIPT:
            cmd.append(f"--ts_out={output_dir}")
        elif language == Language.CPP:
            cmd.append(f"--cpp_out={output_dir}")
        elif language == Language.CSHARP:
            cmd.append(f"--csharp_out={output_dir}")

        # Add plugins
        for plugin in self.config.plugins:
            plugin_available, plugin_error = self._verify_plugin(plugin)
            if not plugin_available:
                warnings.append(plugin_error)
                continue

            if plugin == Plugin.GRPC:
                if language == Language.PYTHON:
                    cmd.append(f"--grpc_python_out={output_dir}")
                elif language == Language.GO:
                    cmd.append(f"--go-grpc_out={output_dir}")
                elif language == Language.JAVA:
                    cmd.append(f"--grpc-java_out={output_dir}")
            elif plugin == Plugin.GRPC_WEB:
                if language == Language.TYPESCRIPT:
                    cmd.append(f"--grpc-web_out=import_style=typescript,mode=grpcwebtext:{output_dir}")
            elif plugin == Plugin.VALIDATE:
                cmd.append(f"--validate_out=lang={language.value}:{output_dir}")

        # Add custom plugin paths
        for plugin_name, plugin_path in self.config.plugin_paths.items():
            cmd.append(f"--plugin=protoc-gen-{plugin_name}={plugin_path}")

        # Add proto file
        cmd.append(str(proto_file))

        # Execute protoc
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode != 0:
                errors.append(f"protoc failed: {result.stderr}")
                return GenerationResult(
                    success=False,
                    language=language,
                    proto_file=proto_file,
                    output_files=[],
                    errors=errors,
                    warnings=warnings,
                    elapsed_seconds=time.time() - start_time
                )

            if result.stderr:
                warnings.append(result.stderr.strip())

        except subprocess.TimeoutExpired:
            errors.append(f"protoc timed out after 30 seconds")
            return GenerationResult(
                success=False,
                language=language,
                proto_file=proto_file,
                output_files=[],
                errors=errors,
                warnings=warnings,
                elapsed_seconds=time.time() - start_time
            )
        except Exception as e:
            errors.append(f"protoc execution failed: {e}")
            return GenerationResult(
                success=False,
                language=language,
                proto_file=proto_file,
                output_files=[],
                errors=errors,
                warnings=warnings,
                elapsed_seconds=time.time() - start_time
            )

        # Find generated files
        output_files = self._find_generated_files(proto_file, language, output_dir)

        # Validate generated code if requested
        if self.config.validate:
            validation_errors = self._validate_generated_code(output_files, language)
            errors.extend(validation_errors)

        success = len(errors) == 0

        # Update cache
        if success and self.config.incremental:
            proto_hash = self._compute_proto_hash(proto_file)
            self.cache[(proto_file, language)] = CacheEntry(
                proto_hash=proto_hash,
                output_files=output_files,
                timestamp=time.time()
            )

        return GenerationResult(
            success=success,
            language=language,
            proto_file=proto_file,
            output_files=output_files,
            errors=errors,
            warnings=warnings,
            elapsed_seconds=time.time() - start_time
        )

    def _find_generated_files(self, proto_file: Path, language: Language, output_dir: Path) -> List[Path]:
        """Find files generated from proto file"""
        proto_name = proto_file.stem
        generated = []

        if language == Language.PYTHON:
            pb2 = output_dir / f"{proto_name}_pb2.py"
            if pb2.exists():
                generated.append(pb2)
            grpc = output_dir / f"{proto_name}_pb2_grpc.py"
            if grpc.exists():
                generated.append(grpc)

        elif language == Language.GO:
            pb_go = output_dir / f"{proto_name}.pb.go"
            if pb_go.exists():
                generated.append(pb_go)
            grpc_go = output_dir / f"{proto_name}_grpc.pb.go"
            if grpc_go.exists():
                generated.append(grpc_go)

        elif language == Language.JAVA:
            # Java generates multiple files, search recursively
            for file in output_dir.rglob("*.java"):
                generated.append(file)

        elif language == Language.TYPESCRIPT:
            pb_ts = output_dir / f"{proto_name}_pb.ts"
            if pb_ts.exists():
                generated.append(pb_ts)
            grpc_ts = output_dir / f"{proto_name}_grpc_pb.ts"
            if grpc_ts.exists():
                generated.append(grpc_ts)

        return generated

    def _validate_generated_code(self, files: List[Path], language: Language) -> List[str]:
        """Validate generated code compiles/imports correctly"""
        errors = []

        if not files:
            return ["No generated files found"]

        if language == Language.PYTHON:
            for file in files:
                # Try to compile Python file
                try:
                    import py_compile
                    py_compile.compile(file, doraise=True)
                except py_compile.PyCompileError as e:
                    errors.append(f"Python compile error in {file.name}: {e}")

        elif language == Language.GO:
            # Try to run go vet
            try:
                result = subprocess.run(
                    ["go", "vet"] + [str(f) for f in files],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode != 0:
                    errors.append(f"go vet failed: {result.stderr}")
            except FileNotFoundError:
                errors.append("go not found (skipping validation)")
            except subprocess.TimeoutExpired:
                errors.append("go vet timed out")

        elif language == Language.TYPESCRIPT:
            # Try to run tsc --noEmit
            try:
                result = subprocess.run(
                    ["tsc", "--noEmit"] + [str(f) for f in files],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode != 0:
                    errors.append(f"TypeScript compilation failed: {result.stderr}")
            except FileNotFoundError:
                errors.append("tsc not found (skipping validation)")
            except subprocess.TimeoutExpired:
                errors.append("tsc validation timed out")

        return errors

    def generate_all(self) -> List[GenerationResult]:
        """Generate code for all proto files and languages"""
        results = []

        # Verify protoc
        protoc_available, protoc_error = self._verify_protoc()
        if not protoc_available:
            for proto_file in self.config.proto_files:
                for language in self.config.languages:
                    results.append(GenerationResult(
                        success=False,
                        language=language,
                        proto_file=proto_file,
                        output_files=[],
                        errors=[protoc_error],
                        warnings=[],
                        elapsed_seconds=0.0
                    ))
            return results

        # Generate for each proto file and language
        for proto_file in self.config.proto_files:
            for language in self.config.languages:
                result = self.generate(proto_file, language)
                results.append(result)

        # Save cache
        if self.config.incremental:
            self._save_cache()

        return results


def parse_args() -> argparse.Namespace:
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Generate code from Protocol Buffer schemas",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate Python code
  %(prog)s --proto-file user.proto --language python

  # Generate Go code with package
  %(prog)s --proto-file user.proto --language go --go-package github.com/myorg/protos

  # Generate multiple languages
  %(prog)s --proto-file user.proto --language python,go,typescript

  # Generate from directory
  %(prog)s --proto-dir ./protos --language python --json

  # Generate with gRPC plugin
  %(prog)s --proto-file service.proto --plugin grpc --language python,go

  # Incremental generation with validation
  %(prog)s --proto-file user.proto --language python --validate --incremental

  # Custom proto paths
  %(prog)s --proto-file user.proto -I ./protos -I ./vendor --language go
        """
    )

    parser.add_argument(
        '--proto-file',
        type=Path,
        help="Proto file to generate code from"
    )

    parser.add_argument(
        '--proto-dir',
        type=Path,
        help="Directory containing proto files (generates from all .proto files)"
    )

    parser.add_argument(
        '-I', '--proto-path',
        type=Path,
        action='append',
        dest='proto_paths',
        help="Proto import path (can be specified multiple times)"
    )

    parser.add_argument(
        '--language', '-l',
        required=True,
        help="Target language(s): python,go,java,typescript,cpp,csharp (comma-separated)"
    )

    parser.add_argument(
        '--plugin',
        choices=['grpc', 'grpc-web', 'grpc-gateway', 'validate', 'doc'],
        action='append',
        dest='plugins',
        help="Enable protoc plugin (can be specified multiple times)"
    )

    parser.add_argument(
        '--output-dir', '-o',
        type=Path,
        default=Path("./generated"),
        help="Output directory for generated code (default: ./generated)"
    )

    parser.add_argument(
        '--go-package',
        help="Go package path (e.g., github.com/myorg/protos)"
    )

    parser.add_argument(
        '--java-package',
        help="Java package name"
    )

    parser.add_argument(
        '--java-multiple-files',
        action='store_true',
        default=True,
        help="Generate separate Java file per message (default: true)"
    )

    parser.add_argument(
        '--validate',
        action='store_true',
        help="Validate generated code compiles correctly"
    )

    parser.add_argument(
        '--incremental',
        action='store_true',
        help="Enable incremental generation (skip unchanged files)"
    )

    parser.add_argument(
        '--protoc',
        default='protoc',
        help="Path to protoc binary (default: protoc)"
    )

    parser.add_argument(
        '--plugin-path',
        action='append',
        dest='plugin_paths',
        help="Custom plugin path: name=/path/to/plugin (can be specified multiple times)"
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
    if not args.proto_file and not args.proto_dir:
        print("Error: Must specify --proto-file or --proto-dir", file=sys.stderr)
        return 1

    # Parse languages
    try:
        languages = [Language(lang.strip()) for lang in args.language.split(',')]
    except ValueError as e:
        print(f"Error: Invalid language: {e}", file=sys.stderr)
        return 1

    # Parse plugins
    plugins = []
    if args.plugins:
        try:
            plugins = [Plugin(p) for p in args.plugins]
        except ValueError as e:
            print(f"Error: Invalid plugin: {e}", file=sys.stderr)
            return 1

    # Parse plugin paths
    plugin_paths = {}
    if args.plugin_paths:
        for path_spec in args.plugin_paths:
            if '=' not in path_spec:
                print(f"Error: Invalid plugin path format: {path_spec} (expected name=/path)", file=sys.stderr)
                return 1
            name, path = path_spec.split('=', 1)
            plugin_paths[name] = path

    # Collect proto files
    proto_files = []
    if args.proto_file:
        proto_files.append(args.proto_file)
    elif args.proto_dir:
        if not args.proto_dir.is_dir():
            print(f"Error: Not a directory: {args.proto_dir}", file=sys.stderr)
            return 1
        proto_files.extend(args.proto_dir.glob("*.proto"))
        if not proto_files:
            print(f"Error: No .proto files found in {args.proto_dir}", file=sys.stderr)
            return 1

    # Setup proto paths
    proto_paths = args.proto_paths or []
    if args.proto_file:
        proto_paths.append(args.proto_file.parent)
    if args.proto_dir:
        proto_paths.append(args.proto_dir)

    # Create configuration
    config = GenerationConfig(
        proto_files=proto_files,
        proto_paths=proto_paths,
        languages=languages,
        plugins=plugins,
        output_dir=args.output_dir,
        go_package=args.go_package,
        java_package=args.java_package,
        java_multiple_files=args.java_multiple_files,
        validate=args.validate,
        incremental=args.incremental,
        protoc_path=args.protoc,
        plugin_paths=plugin_paths
    )

    # Generate code
    compiler = ProtoCompiler(config)
    results = compiler.generate_all()

    # Output results
    if args.json:
        output = {
            'total': len(results),
            'successful': sum(1 for r in results if r.success),
            'failed': sum(1 for r in results if not r.success),
            'cache_hits': sum(1 for r in results if r.cache_hit),
            'results': [r.to_dict() for r in results]
        }
        print(json.dumps(output, indent=2))
    else:
        print(f"\nGeneration Summary:")
        print(f"  Total: {len(results)}")
        print(f"  Successful: {sum(1 for r in results if r.success)}")
        print(f"  Failed: {sum(1 for r in results if not r.success)}")
        if config.incremental:
            print(f"  Cache hits: {sum(1 for r in results if r.cache_hit)}")
        print()

        for result in results:
            status = "✓" if result.success else "✗"
            cache = " (cached)" if result.cache_hit else ""
            print(f"{status} {result.proto_file.name} -> {result.language.value}{cache} ({result.elapsed_seconds:.2f}s)")

            if result.output_files:
                for output_file in result.output_files:
                    print(f"    {output_file}")

            if result.warnings:
                for warning in result.warnings:
                    print(f"    Warning: {warning}")

            if result.errors:
                for error in result.errors:
                    print(f"    Error: {error}")

    # Exit with error if any generation failed
    if any(not r.success for r in results):
        return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
