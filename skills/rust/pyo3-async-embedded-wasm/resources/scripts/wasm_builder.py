#!/usr/bin/env python3
"""
PyO3 WASM Builder - Build and optimize WebAssembly modules from PyO3 code
"""
import argparse, json, logging, sys, subprocess, shutil, traceback
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class WasmTarget(Enum):
    WEB = "web"
    NODEJS = "nodejs"
    BUNDLER = "bundler"
    WASI = "wasi"

class OptLevel(Enum):
    DEBUG = "0"
    SIZE = "z"
    SPEED = "3"

@dataclass
class BuildConfig:
    project_dir: Path
    target: WasmTarget
    opt_level: OptLevel
    strip: bool = True
    lto: bool = True
    output_dir: Optional[Path] = None

    def to_dict(self): return {k: str(v) if isinstance(v, (Path, Enum)) else v for k, v in asdict(self).items()}

@dataclass
class BuildResult:
    success: bool
    wasm_file: Optional[Path]
    js_file: Optional[Path]
    size_bytes: int
    build_time_seconds: float
    errors: List[str] = None

    def to_dict(self):
        return {
            'success': self.success,
            'wasm_file': str(self.wasm_file) if self.wasm_file else None,
            'js_file': str(self.js_file) if self.js_file else None,
            'size_bytes': self.size_bytes,
            'size_mb': self.size_bytes / (1024 * 1024),
            'build_time_seconds': self.build_time_seconds,
            'errors': self.errors or []
        }

class WasmBuilder:
    def __init__(self):
        self.cargo_path = shutil.which('cargo')
        self.wasm_pack_path = shutil.which('wasm-pack')
        
    def check_tools(self) -> Dict[str, bool]:
        checks = {
            'cargo': self.cargo_path is not None,
            'wasm-pack': self.wasm_pack_path is not None,
            'rustc': shutil.which('rustc') is not None,
        }
        
        # Check wasm32 target
        if checks['rustc']:
            try:
                result = subprocess.run(
                    ['rustup', 'target', 'list', '--installed'],
                    capture_output=True, text=True, check=False
                )
                checks['wasm32-unknown-unknown'] = 'wasm32-unknown-unknown' in result.stdout
                checks['wasm32-wasi'] = 'wasm32-wasi' in result.stdout
            except:
                checks['wasm32-unknown-unknown'] = False
                checks['wasm32-wasi'] = False
        
        return checks

    def install_target(self, target: str) -> bool:
        logger.info(f"Installing target: {target}")
        try:
            subprocess.run(
                ['rustup', 'target', 'add', target],
                check=True, capture_output=True
            )
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to install target: {e}")
            return False

    def build_wasm_pack(self, config: BuildConfig) -> BuildResult:
        import time
        start_time = time.time()
        errors = []

        try:
            cmd = [
                self.wasm_pack_path or 'wasm-pack',
                'build',
                str(config.project_dir),
                '--target', config.target.value,
                '--release' if config.opt_level != OptLevel.DEBUG else '--dev',
            ]

            if config.output_dir:
                cmd.extend(['--out-dir', str(config.output_dir)])

            logger.info(f"Building: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False
            )

            build_time = time.time() - start_time

            if result.returncode != 0:
                errors.append(result.stderr)
                return BuildResult(False, None, None, 0, build_time, errors)

            # Find output files
            out_dir = config.output_dir or config.project_dir / 'pkg'
            wasm_files = list(out_dir.glob('*.wasm'))
            js_files = list(out_dir.glob('*.js'))

            wasm_file = wasm_files[0] if wasm_files else None
            js_file = js_files[0] if js_files else None
            size = wasm_file.stat().st_size if wasm_file else 0

            return BuildResult(True, wasm_file, js_file, size, build_time)

        except Exception as e:
            errors.append(str(e))
            return BuildResult(False, None, None, 0, time.time() - start_time, errors)

    def build_cargo(self, config: BuildConfig) -> BuildResult:
        import time
        start_time = time.time()
        errors = []

        try:
            target = 'wasm32-wasi' if config.target == WasmTarget.WASI else 'wasm32-unknown-unknown'
            
            cmd = [
                self.cargo_path or 'cargo',
                'build',
                '--target', target,
                '--release',
            ]

            logger.info(f"Building: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                cwd=config.project_dir,
                capture_output=True,
                text=True,
                check=False
            )

            build_time = time.time() - start_time

            if result.returncode != 0:
                errors.append(result.stderr)
                return BuildResult(False, None, None, 0, build_time, errors)

            # Find WASM file
            wasm_dir = config.project_dir / 'target' / target / 'release'
            wasm_files = list(wasm_dir.glob('*.wasm'))
            
            wasm_file = wasm_files[0] if wasm_files else None
            size = wasm_file.stat().st_size if wasm_file else 0

            return BuildResult(True, wasm_file, None, size, build_time)

        except Exception as e:
            errors.append(str(e))
            return BuildResult(False, None, None, 0, time.time() - start_time, errors)

    def optimize(self, wasm_file: Path) -> bool:
        wasm_opt = shutil.which('wasm-opt')
        if not wasm_opt:
            logger.warning("wasm-opt not found, skipping optimization")
            return False

        try:
            logger.info("Optimizing WASM...")
            subprocess.run(
                [wasm_opt, '-Oz', str(wasm_file), '-o', str(wasm_file)],
                check=True, capture_output=True
            )
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Optimization failed: {e}")
            return False

class CargoConfigGenerator:
    @staticmethod
    def generate_wasm_config(opt_level: OptLevel, strip: bool, lto: bool) -> str:
        config = f'''[profile.release]
opt-level = "{opt_level.value}"
lto = {str(lto).lower()}
strip = {str(strip).lower()}
codegen-units = 1
panic = "abort"
'''
        return config

    @staticmethod
    def write_config(project_dir: Path, config: str):
        cargo_toml = project_dir / 'Cargo.toml'
        if not cargo_toml.exists():
            logger.error("Cargo.toml not found")
            return False

        # Append or update profile section
        content = cargo_toml.read_text()
        
        if '[profile.release]' in content:
            logger.info("Updating existing profile.release section")
            # Simple append for now
            content += '\n' + config
        else:
            content += '\n' + config

        cargo_toml.write_text(content)
        return True

def main():
    parser = argparse.ArgumentParser(description='PyO3 WASM Builder')
    parser.add_argument('--verbose', '-v', action='store_true')
    parser.add_argument('--json', action='store_true')

    subparsers = parser.add_subparsers(dest='command')

    # Check command
    check_parser = subparsers.add_parser('check', help='Check build tools')

    # Build command
    build_parser = subparsers.add_parser('build', help='Build WASM module')
    build_parser.add_argument('project', type=Path, help='Project directory')
    build_parser.add_argument('--target', type=WasmTarget, default=WasmTarget.WEB)
    build_parser.add_argument('--opt', type=OptLevel, default=OptLevel.SIZE)
    build_parser.add_argument('--no-strip', action='store_true')
    build_parser.add_argument('--no-lto', action='store_true')
    build_parser.add_argument('--output', '-o', type=Path)
    build_parser.add_argument('--use-cargo', action='store_true', help='Use cargo instead of wasm-pack')
    build_parser.add_argument('--optimize', action='store_true', help='Run wasm-opt')

    # Config command
    config_parser = subparsers.add_parser('config', help='Generate Cargo config')
    config_parser.add_argument('project', type=Path)
    config_parser.add_argument('--opt', type=OptLevel, default=OptLevel.SIZE)
    config_parser.add_argument('--strip', action='store_true', default=True)
    config_parser.add_argument('--lto', action='store_true', default=True)

    # Optimize command
    opt_parser = subparsers.add_parser('optimize', help='Optimize WASM file')
    opt_parser.add_argument('wasm_file', type=Path)

    args = parser.parse_args()
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    builder = WasmBuilder()

    try:
        if args.command == 'check':
            checks = builder.check_tools()
            
            if args.json:
                print(json.dumps(checks, indent=2))
            else:
                print("\nBuild Tools Check:")
                for tool, available in checks.items():
                    status = "✓" if available else "✗"
                    print(f"  {status} {tool}")
                
                if not checks.get('wasm32-unknown-unknown'):
                    print("\nInstall wasm32 target: rustup target add wasm32-unknown-unknown")
                if not checks.get('wasm-pack'):
                    print("Install wasm-pack: cargo install wasm-pack")

        elif args.command == 'build':
            config = BuildConfig(
                project_dir=args.project,
                target=args.target,
                opt_level=args.opt,
                strip=not args.no_strip,
                lto=not args.no_lto,
                output_dir=args.output
            )

            if args.use_cargo:
                result = builder.build_cargo(config)
            else:
                result = builder.build_wasm_pack(config)

            if result.success and args.optimize and result.wasm_file:
                builder.optimize(result.wasm_file)

            if args.json:
                print(json.dumps(result.to_dict(), indent=2))
            else:
                if result.success:
                    print(f"\n✓ Build successful!")
                    print(f"  WASM: {result.wasm_file}")
                    if result.js_file:
                        print(f"  JS:   {result.js_file}")
                    print(f"  Size: {result.size_bytes / 1024:.1f} KB")
                    print(f"  Time: {result.build_time_seconds:.2f}s")
                else:
                    print(f"\n✗ Build failed!")
                    if result.errors:
                        for error in result.errors:
                            print(f"  {error}")
                    sys.exit(1)

        elif args.command == 'config':
            generator = CargoConfigGenerator()
            config = generator.generate_wasm_config(args.opt, args.strip, args.lto)
            
            if generator.write_config(args.project, config):
                print("✓ Config updated")
            else:
                print("✗ Failed to update config")
                sys.exit(1)

        elif args.command == 'optimize':
            if builder.optimize(args.wasm_file):
                print(f"✓ Optimized {args.wasm_file}")
            else:
                print(f"✗ Optimization failed")
                sys.exit(1)

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
