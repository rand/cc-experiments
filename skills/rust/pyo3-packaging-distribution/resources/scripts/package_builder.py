#!/usr/bin/env python3
"""
PyO3 Package Builder - Build wheels for multiple platforms with cross-compilation
"""
import argparse
import json
import logging
import sys
import subprocess
import shutil
import traceback
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
import tempfile

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class Platform(Enum):
    LINUX_X86_64 = "linux-x86_64"
    LINUX_AARCH64 = "linux-aarch64"
    MACOS_X86_64 = "macos-x86_64"
    MACOS_AARCH64 = "macos-aarch64"
    WINDOWS_X64 = "windows-x64"
    WINDOWS_X86 = "windows-x86"

class ManylinuxVersion(Enum):
    MANYLINUX_2_28 = "2_28"
    MANYLINUX_2_31 = "2_31"
    MUSLLINUX_1_2 = "musllinux_1_2"

@dataclass
class BuildConfig:
    project_dir: Path
    platforms: List[Platform]
    python_versions: List[str]
    manylinux: Optional[ManylinuxVersion] = ManylinuxVersion.MANYLINUX_2_28
    output_dir: Optional[Path] = None
    release: bool = True
    use_docker: bool = False
    use_zig: bool = False

    def to_dict(self):
        return {
            k: str(v) if isinstance(v, (Path, Enum)) else [str(x) for x in v] if isinstance(v, list) else v
            for k, v in asdict(self).items()
        }

@dataclass
class BuildResult:
    success: bool
    platform: Platform
    wheels: List[Path]
    build_time_seconds: float
    errors: List[str] = None

    def to_dict(self):
        return {
            'success': self.success,
            'platform': str(self.platform.value),
            'wheels': [str(w) for w in self.wheels],
            'build_time_seconds': self.build_time_seconds,
            'errors': self.errors or []
        }

class PackageBuilder:
    def __init__(self):
        self.maturin_path = shutil.which('maturin')
        self.docker_path = shutil.which('docker')
        self.zig_path = shutil.which('zig')

    def check_tools(self) -> Dict[str, bool]:
        checks = {
            'maturin': self.maturin_path is not None,
            'docker': self.docker_path is not None,
            'zig': self.zig_path is not None,
            'cargo': shutil.which('cargo') is not None,
            'rustc': shutil.which('rustc') is not None,
        }
        return checks

    def get_platform_target(self, platform: Platform) -> str:
        targets = {
            Platform.LINUX_X86_64: "x86_64-unknown-linux-gnu",
            Platform.LINUX_AARCH64: "aarch64-unknown-linux-gnu",
            Platform.MACOS_X86_64: "x86_64-apple-darwin",
            Platform.MACOS_AARCH64: "aarch64-apple-darwin",
            Platform.WINDOWS_X64: "x86_64-pc-windows-msvc",
            Platform.WINDOWS_X86: "i686-pc-windows-msvc",
        }
        return targets[platform]

    def build_native(self, config: BuildConfig, python_version: str) -> BuildResult:
        import time
        start_time = time.time()
        errors = []
        wheels = []

        try:
            # Detect current platform
            import platform as plat
            system = plat.system().lower()
            machine = plat.machine().lower()

            if system == 'linux' and machine == 'x86_64':
                current = Platform.LINUX_X86_64
            elif system == 'linux' and 'aarch64' in machine:
                current = Platform.LINUX_AARCH64
            elif system == 'darwin' and machine == 'x86_64':
                current = Platform.MACOS_X86_64
            elif system == 'darwin' and machine == 'arm64':
                current = Platform.MACOS_AARCH64
            elif system == 'windows' and machine == 'amd64':
                current = Platform.WINDOWS_X64
            else:
                raise ValueError(f"Unsupported platform: {system} {machine}")

            if current not in config.platforms:
                logger.info(f"Skipping {current.value} (not in target platforms)")
                return BuildResult(True, current, [], time.time() - start_time)

            output_dir = config.output_dir or config.project_dir / 'dist'
            output_dir.mkdir(parents=True, exist_ok=True)

            cmd = [
                self.maturin_path or 'maturin',
                'build',
                '--release' if config.release else '--debug',
                '--out', str(output_dir),
                '--find-interpreter',
            ]

            # Add manylinux for Linux
            if system == 'linux' and config.manylinux:
                cmd.extend(['--manylinux', config.manylinux.value])

            # Add Python version constraint
            if python_version:
                cmd.extend(['-i', f'python{python_version}'])

            logger.info(f"Building for {current.value}: {' '.join(cmd)}")

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
                return BuildResult(False, current, [], build_time, errors)

            # Find generated wheels
            wheels = list(output_dir.glob('*.whl'))
            logger.info(f"Built {len(wheels)} wheels in {build_time:.2f}s")

            return BuildResult(True, current, wheels, build_time)

        except Exception as e:
            errors.append(str(e))
            return BuildResult(False, Platform.LINUX_X86_64, [], time.time() - start_time, errors)

    def build_with_docker(self, config: BuildConfig, platform: Platform) -> BuildResult:
        import time
        start_time = time.time()
        errors = []

        try:
            if not self.docker_path:
                raise ValueError("Docker not found")

            # Choose manylinux image
            if platform == Platform.LINUX_X86_64:
                image = f"quay.io/pypa/manylinux_{config.manylinux.value}_x86_64"
            elif platform == Platform.LINUX_AARCH64:
                image = f"quay.io/pypa/manylinux_{config.manylinux.value}_aarch64"
            else:
                raise ValueError(f"Docker build not supported for {platform}")

            output_dir = config.output_dir or config.project_dir / 'dist'
            output_dir.mkdir(parents=True, exist_ok=True)

            # Docker command
            cmd = [
                'docker', 'run', '--rm',
                '-v', f'{config.project_dir}:/io',
                image,
                'bash', '-c',
                'curl --proto "=https" --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y && '
                'source $HOME/.cargo/env && '
                'pip install maturin && '
                f'maturin build --release --out /io/dist --find-interpreter'
            ]

            logger.info(f"Building with Docker: {platform.value}")
            logger.info(f"Image: {image}")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False
            )

            build_time = time.time() - start_time

            if result.returncode != 0:
                errors.append(result.stderr)
                return BuildResult(False, platform, [], build_time, errors)

            wheels = list(output_dir.glob('*.whl'))
            logger.info(f"Built {len(wheels)} wheels with Docker in {build_time:.2f}s")

            return BuildResult(True, platform, wheels, build_time)

        except Exception as e:
            errors.append(str(e))
            return BuildResult(False, platform, [], time.time() - start_time, errors)

    def build_with_zig(self, config: BuildConfig, platform: Platform) -> BuildResult:
        import time
        start_time = time.time()
        errors = []

        try:
            if not self.zig_path:
                raise ValueError("Zig not found")

            output_dir = config.output_dir or config.project_dir / 'dist'
            output_dir.mkdir(parents=True, exist_ok=True)

            target = self.get_platform_target(platform)

            cmd = [
                self.maturin_path or 'maturin',
                'build',
                '--release' if config.release else '--debug',
                '--out', str(output_dir),
                '--target', target,
                '--zig',
                '--find-interpreter',
            ]

            logger.info(f"Building with Zig: {platform.value}")

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
                return BuildResult(False, platform, [], build_time, errors)

            wheels = list(output_dir.glob('*.whl'))
            logger.info(f"Built {len(wheels)} wheels with Zig in {build_time:.2f}s")

            return BuildResult(True, platform, wheels, build_time)

        except Exception as e:
            errors.append(str(e))
            return BuildResult(False, platform, [], time.time() - start_time, errors)

    def build_all(self, config: BuildConfig) -> List[BuildResult]:
        results = []

        for platform in config.platforms:
            for py_version in config.python_versions:
                logger.info(f"\n=== Building for {platform.value} (Python {py_version}) ===")

                if config.use_docker and platform in [Platform.LINUX_X86_64, Platform.LINUX_AARCH64]:
                    result = self.build_with_docker(config, platform)
                elif config.use_zig:
                    result = self.build_with_zig(config, platform)
                else:
                    result = self.build_native(config, py_version)

                results.append(result)

                if not result.success:
                    logger.error(f"Build failed for {platform.value}")
                    for error in result.errors:
                        logger.error(error)

        return results

    def inspect_wheel(self, wheel_path: Path) -> Dict[str, Any]:
        import zipfile

        info = {
            'path': str(wheel_path),
            'size_bytes': wheel_path.stat().st_size,
            'size_mb': wheel_path.stat().st_size / (1024 * 1024),
            'contents': [],
        }

        with zipfile.ZipFile(wheel_path, 'r') as zf:
            info['contents'] = zf.namelist()

        return info

class ReportGenerator:
    @staticmethod
    def generate_text(results: List[BuildResult]) -> str:
        lines = ["=== Build Report ===\n"]

        total = len(results)
        successful = sum(1 for r in results if r.success)
        failed = total - successful

        lines.append(f"Total builds: {total}")
        lines.append(f"Successful: {successful}")
        lines.append(f"Failed: {failed}")
        lines.append("")

        for result in results:
            status = "✓" if result.success else "✗"
            lines.append(f"{status} {result.platform.value}")
            lines.append(f"  Time: {result.build_time_seconds:.2f}s")

            if result.wheels:
                lines.append(f"  Wheels: {len(result.wheels)}")
                for wheel in result.wheels:
                    lines.append(f"    - {wheel.name}")

            if result.errors:
                lines.append("  Errors:")
                for error in result.errors:
                    lines.append(f"    {error}")

            lines.append("")

        return "\n".join(lines)

    @staticmethod
    def generate_json(results: List[BuildResult]) -> str:
        data = {
            'results': [r.to_dict() for r in results],
            'summary': {
                'total': len(results),
                'successful': sum(1 for r in results if r.success),
                'failed': sum(1 for r in results if not r.success),
            }
        }
        return json.dumps(data, indent=2)

def main():
    parser = argparse.ArgumentParser(description='PyO3 Package Builder')
    parser.add_argument('--verbose', '-v', action='store_true')
    parser.add_argument('--json', action='store_true')

    subparsers = parser.add_subparsers(dest='command')

    # Check command
    check_parser = subparsers.add_parser('check', help='Check build tools')

    # Build command
    build_parser = subparsers.add_parser('build', help='Build wheels')
    build_parser.add_argument('project', type=Path, help='Project directory')
    build_parser.add_argument('--platform', type=str, action='append',
                              choices=[p.value for p in Platform],
                              help='Target platforms (can specify multiple)')
    build_parser.add_argument('--python', type=str, action='append',
                              help='Python versions (e.g., 3.8, 3.9)')
    build_parser.add_argument('--manylinux', type=str,
                              default='2_28',
                              help='Manylinux version')
    build_parser.add_argument('--output', '-o', type=Path, help='Output directory')
    build_parser.add_argument('--docker', action='store_true', help='Use Docker')
    build_parser.add_argument('--zig', action='store_true', help='Use Zig')

    # Inspect command
    inspect_parser = subparsers.add_parser('inspect', help='Inspect wheel')
    inspect_parser.add_argument('wheel', type=Path, help='Wheel file')

    args = parser.parse_args()
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    builder = PackageBuilder()

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

                if not checks.get('maturin'):
                    print("\nInstall maturin: pip install maturin")
                if not checks.get('docker'):
                    print("Install Docker: https://www.docker.com/")
                if not checks.get('zig'):
                    print("Install Zig: https://ziglang.org/")

        elif args.command == 'build':
            # Parse platforms
            platforms = []
            if args.platform:
                for p in args.platform:
                    platforms.append(Platform(p))
            else:
                # Default: current platform only
                import platform as plat
                system = plat.system().lower()
                machine = plat.machine().lower()

                if system == 'linux' and machine == 'x86_64':
                    platforms = [Platform.LINUX_X86_64]
                elif system == 'darwin':
                    platforms = [Platform.MACOS_X86_64, Platform.MACOS_AARCH64]
                elif system == 'windows':
                    platforms = [Platform.WINDOWS_X64]

            # Parse Python versions
            python_versions = args.python or ['3.8', '3.9', '3.10', '3.11', '3.12']

            # Build config
            config = BuildConfig(
                project_dir=args.project,
                platforms=platforms,
                python_versions=python_versions,
                manylinux=ManylinuxVersion(f"manylinux_{args.manylinux}") if not args.manylinux.startswith('musl') else ManylinuxVersion(f"musllinux_{args.manylinux.replace('musllinux_', '')}"),
                output_dir=args.output,
                release=True,
                use_docker=args.docker,
                use_zig=args.zig,
            )

            # Build
            results = builder.build_all(config)

            # Report
            report_gen = ReportGenerator()
            if args.json:
                print(report_gen.generate_json(results))
            else:
                print(report_gen.generate_text(results))

            # Exit with error if any builds failed
            if any(not r.success for r in results):
                sys.exit(1)

        elif args.command == 'inspect':
            info = builder.inspect_wheel(args.wheel)

            if args.json:
                print(json.dumps(info, indent=2))
            else:
                print(f"\nWheel: {info['path']}")
                print(f"Size: {info['size_mb']:.2f} MB")
                print(f"\nContents ({len(info['contents'])} files):")
                for item in info['contents'][:20]:  # First 20
                    print(f"  {item}")
                if len(info['contents']) > 20:
                    print(f"  ... and {len(info['contents']) - 20} more")

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
