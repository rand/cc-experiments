#!/usr/bin/env python3
"""
CLI Application Boilerplate Generator

Production-grade tool for generating Python CLI applications with multiple
framework support, test scaffolds, and comprehensive documentation.

Supports:
- argparse, click, typer frameworks
- Command structure generation
- Test scaffolding with pytest
- Documentation generation
- Project structure setup
- Configuration files
"""

import argparse
import json
import logging
import sys
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, TextIO
import textwrap


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class Framework(Enum):
    """Supported CLI frameworks."""
    ARGPARSE = "argparse"
    CLICK = "click"
    TYPER = "typer"


class OutputFormat(Enum):
    """Output format options."""
    TEXT = "text"
    JSON = "json"


@dataclass
class CommandDefinition:
    """Definition of a CLI command."""
    name: str
    description: str
    arguments: List[Dict[str, Any]] = field(default_factory=list)
    options: List[Dict[str, Any]] = field(default_factory=list)
    subcommands: List['CommandDefinition'] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'name': self.name,
            'description': self.description,
            'arguments': self.arguments,
            'options': self.options,
            'subcommands': [sc.to_dict() for sc in self.subcommands]
        }


@dataclass
class ProjectConfig:
    """Configuration for CLI project generation."""
    name: str
    description: str
    version: str
    author: str
    framework: Framework
    output_dir: Path
    commands: List[CommandDefinition] = field(default_factory=list)
    generate_tests: bool = True
    generate_docs: bool = True
    use_typing: bool = True
    python_version: str = "3.9"


class TemplateGenerator:
    """Generate code templates for different frameworks."""

    @staticmethod
    def generate_argparse_main(config: ProjectConfig) -> str:
        """Generate main file using argparse."""
        template = f'''#!/usr/bin/env python3
"""
{config.name}

{config.description}
"""

import argparse
import logging
import sys
from typing import Optional, List, Any

__version__ = "{config.version}"
__author__ = "{config.author}"


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class {config.name.title().replace('-', '')}CLI:
    """Main CLI application class."""

    def __init__(self) -> None:
        """Initialize CLI application."""
        self.parser = self._create_parser()

    def _create_parser(self) -> argparse.ArgumentParser:
        """Create argument parser."""
        parser = argparse.ArgumentParser(
            prog="{config.name}",
            description="{config.description}",
            formatter_class=argparse.RawDescriptionHelpFormatter
        )

        parser.add_argument(
            "--version",
            action="version",
            version=f"{{parser.prog}} {{__version__}}"
        )

        parser.add_argument(
            "--verbose", "-v",
            action="store_true",
            help="Enable verbose output"
        )

        parser.add_argument(
            "--output-format",
            choices=["text", "json"],
            default="text",
            help="Output format (default: text)"
        )

        subparsers = parser.add_subparsers(dest="command", help="Available commands")

{TemplateGenerator._generate_argparse_commands(config.commands)}

        return parser

    def run(self, args: Optional[List[str]] = None) -> int:
        """Run the CLI application."""
        try:
            parsed_args = self.parser.parse_args(args)

            if parsed_args.verbose:
                logging.getLogger().setLevel(logging.DEBUG)

            if not parsed_args.command:
                self.parser.print_help()
                return 0

            # Execute command
            command_method = f"cmd_{{parsed_args.command.replace('-', '_')}}"
            if hasattr(self, command_method):
                return getattr(self, command_method)(parsed_args)
            else:
                logger.error(f"Command not implemented: {{parsed_args.command}}")
                return 1

        except KeyboardInterrupt:
            logger.info("\\nOperation cancelled by user")
            return 130
        except Exception as e:
            logger.error(f"Error: {{e}}")
            if parsed_args.verbose if 'parsed_args' in locals() else False:
                logger.exception("Detailed error:")
            return 1
{TemplateGenerator._generate_argparse_command_methods(config.commands)}


def main() -> int:
    """Main entry point."""
    cli = {config.name.title().replace('-', '')}CLI()
    return cli.run()


if __name__ == "__main__":
    sys.exit(main())
'''
        return template

    @staticmethod
    def _generate_argparse_commands(commands: List[CommandDefinition], indent: int = 2) -> str:
        """Generate argparse command definitions."""
        lines = []
        indent_str = "    " * indent

        for cmd in commands:
            lines.append(f'{indent_str}# {cmd.name} command')
            lines.append(f'{indent_str}{cmd.name}_parser = subparsers.add_parser(')
            lines.append(f'{indent_str}    "{cmd.name}",')
            lines.append(f'{indent_str}    help="{cmd.description}"')
            lines.append(f'{indent_str})')

            # Add arguments
            for arg in cmd.arguments:
                arg_name = arg.get('name', 'arg')
                arg_help = arg.get('help', '')
                arg_type = arg.get('type', 'str')

                lines.append(f'{indent_str}{cmd.name}_parser.add_argument(')
                lines.append(f'{indent_str}    "{arg_name}",')
                if arg_type != 'str':
                    lines.append(f'{indent_str}    type={arg_type},')
                lines.append(f'{indent_str}    help="{arg_help}"')
                lines.append(f'{indent_str})')

            # Add options
            for opt in cmd.options:
                opt_name = opt.get('name', '--option')
                opt_help = opt.get('help', '')
                opt_type = opt.get('type', 'str')
                opt_default = opt.get('default')

                lines.append(f'{indent_str}{cmd.name}_parser.add_argument(')
                lines.append(f'{indent_str}    "{opt_name}",')
                if opt_type != 'str':
                    lines.append(f'{indent_str}    type={opt_type},')
                if opt_default is not None:
                    lines.append(f'{indent_str}    default={repr(opt_default)},')
                lines.append(f'{indent_str}    help="{opt_help}"')
                lines.append(f'{indent_str})')

            lines.append('')

        return '\n'.join(lines)

    @staticmethod
    def _generate_argparse_command_methods(commands: List[CommandDefinition], indent: int = 1) -> str:
        """Generate command method implementations."""
        lines = []
        indent_str = "    " * indent

        for cmd in commands:
            method_name = cmd.name.replace('-', '_')
            lines.append(f'\n{indent_str}def cmd_{method_name}(self, args: argparse.Namespace) -> int:')
            lines.append(f'{indent_str}    """Execute {cmd.name} command."""')
            lines.append(f'{indent_str}    logger.info("Executing {cmd.name} command")')
            lines.append(f'{indent_str}    ')
            lines.append(f'{indent_str}    # TODO: Implement {cmd.name} logic')
            lines.append(f'{indent_str}    ')
            lines.append(f'{indent_str}    if args.output_format == "json":')
            lines.append(f'{indent_str}        import json')
            lines.append(f'{indent_str}        result = {{"status": "success", "command": "{cmd.name}"}}')
            lines.append(f'{indent_str}        print(json.dumps(result, indent=2))')
            lines.append(f'{indent_str}    else:')
            lines.append(f'{indent_str}        print(f"{cmd.name} completed successfully")')
            lines.append(f'{indent_str}    ')
            lines.append(f'{indent_str}    return 0')

        return '\n'.join(lines)

    @staticmethod
    def generate_click_main(config: ProjectConfig) -> str:
        """Generate main file using click."""
        template = f'''#!/usr/bin/env python3
"""
{config.name}

{config.description}
"""

import click
import logging
import json
from typing import Optional

__version__ = "{config.version}"
__author__ = "{config.author}"


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@click.group()
@click.version_option(version=__version__)
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
@click.option('--output-format', type=click.Choice(['text', 'json']), default='text', help='Output format')
@click.pass_context
def cli(ctx: click.Context, verbose: bool, output_format: str) -> None:
    """
    {config.description}
    """
    ctx.ensure_object(dict)
    ctx.obj['verbose'] = verbose
    ctx.obj['output_format'] = output_format

    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)


{TemplateGenerator._generate_click_commands(config.commands)}


if __name__ == '__main__':
    cli(obj={{}})
'''
        return template

    @staticmethod
    def _generate_click_commands(commands: List[CommandDefinition]) -> str:
        """Generate click command definitions."""
        lines = []

        for cmd in commands:
            lines.append(f'@cli.command(name="{cmd.name}")')

            # Add options
            for opt in cmd.options:
                opt_name = opt.get('name', '--option').lstrip('-')
                opt_help = opt.get('help', '')
                opt_type = opt.get('type', 'str')
                opt_default = opt.get('default')

                type_map = {'str': 'str', 'int': 'int', 'float': 'float', 'bool': 'bool'}
                click_type = type_map.get(opt_type, 'str')

                if opt_default is not None:
                    lines.append(f"@click.option('--{opt_name}', type={click_type}, default={repr(opt_default)}, help='{opt_help}')")
                else:
                    lines.append(f"@click.option('--{opt_name}', type={click_type}, help='{opt_help}')")

            # Add arguments
            for arg in cmd.arguments:
                arg_name = arg.get('name', 'arg')
                arg_help = arg.get('help', '')
                arg_type = arg.get('type', 'str')

                type_map = {'str': 'str', 'int': 'int', 'float': 'float'}
                click_type = type_map.get(arg_type, 'str')

                lines.append(f"@click.argument('{arg_name}', type={click_type})")

            lines.append('@click.pass_context')

            # Generate function signature
            func_name = cmd.name.replace('-', '_')
            params = ['ctx: click.Context']

            for arg in cmd.arguments:
                arg_name = arg.get('name', 'arg')
                arg_type = arg.get('type', 'str')
                type_map = {'str': 'str', 'int': 'int', 'float': 'float'}
                python_type = type_map.get(arg_type, 'str')
                params.append(f'{arg_name}: {python_type}')

            for opt in cmd.options:
                opt_name = opt.get('name', '--option').lstrip('-').replace('-', '_')
                opt_type = opt.get('type', 'str')
                type_map = {'str': 'str', 'int': 'int', 'float': 'float', 'bool': 'bool'}
                python_type = type_map.get(opt_type, 'str')
                params.append(f'{opt_name}: {python_type}')

            lines.append(f'def {func_name}({", ".join(params)}) -> None:')
            lines.append(f'    """')
            lines.append(f'    {cmd.description}')
            lines.append(f'    """')
            lines.append(f'    logger.info("Executing {cmd.name} command")')
            lines.append(f'    ')
            lines.append(f'    # TODO: Implement {cmd.name} logic')
            lines.append(f'    ')
            lines.append(f"    if ctx.obj['output_format'] == 'json':")
            lines.append(f'        result = {{"status": "success", "command": "{cmd.name}"}}')
            lines.append(f'        click.echo(json.dumps(result, indent=2))')
            lines.append(f'    else:')
            lines.append(f'        click.echo(f"{cmd.name} completed successfully")')
            lines.append('')
            lines.append('')

        return '\n'.join(lines)

    @staticmethod
    def generate_typer_main(config: ProjectConfig) -> str:
        """Generate main file using typer."""
        template = f'''#!/usr/bin/env python3
"""
{config.name}

{config.description}
"""

import typer
import logging
import json
from typing import Optional, Annotated
from enum import Enum

__version__ = "{config.version}"
__author__ = "{config.author}"


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class OutputFormat(str, Enum):
    """Output format options."""
    TEXT = "text"
    JSON = "json"


app = typer.Typer(
    name="{config.name}",
    help="{config.description}",
    add_completion=True
)


def version_callback(value: bool) -> None:
    """Show version and exit."""
    if value:
        typer.echo(f"{config.name} {{__version__}}")
        raise typer.Exit()


@app.callback()
def main(
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable verbose output")] = False,
    output_format: Annotated[OutputFormat, typer.Option(help="Output format")] = OutputFormat.TEXT,
    version: Annotated[Optional[bool], typer.Option("--version", callback=version_callback, is_eager=True, help="Show version")] = None
) -> None:
    """
    {config.description}
    """
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)


{TemplateGenerator._generate_typer_commands(config.commands)}


if __name__ == "__main__":
    app()
'''
        return template

    @staticmethod
    def _generate_typer_commands(commands: List[CommandDefinition]) -> str:
        """Generate typer command definitions."""
        lines = []

        for cmd in commands:
            func_name = cmd.name.replace('-', '_')
            lines.append(f'@app.command(name="{cmd.name}")')

            # Generate function signature
            params = []

            for arg in cmd.arguments:
                arg_name = arg.get('name', 'arg')
                arg_help = arg.get('help', '')
                arg_type = arg.get('type', 'str')
                type_map = {'str': 'str', 'int': 'int', 'float': 'float'}
                python_type = type_map.get(arg_type, 'str')

                params.append(f'{arg_name}: Annotated[{python_type}, typer.Argument(help="{arg_help}")]')

            for opt in cmd.options:
                opt_name = opt.get('name', '--option').lstrip('-').replace('-', '_')
                opt_help = opt.get('help', '')
                opt_type = opt.get('type', 'str')
                opt_default = opt.get('default')

                type_map = {'str': 'str', 'int': 'int', 'float': 'float', 'bool': 'bool'}
                python_type = type_map.get(opt_type, 'str')

                if opt_default is not None:
                    params.append(f'{opt_name}: Annotated[{python_type}, typer.Option(help="{opt_help}")] = {repr(opt_default)}')
                else:
                    params.append(f'{opt_name}: Annotated[Optional[{python_type}], typer.Option(help="{opt_help}")] = None')

            if params:
                lines.append(f'def {func_name}(')
                for i, param in enumerate(params):
                    comma = ',' if i < len(params) - 1 else ''
                    lines.append(f'    {param}{comma}')
                lines.append(') -> None:')
            else:
                lines.append(f'def {func_name}() -> None:')

            lines.append(f'    """')
            lines.append(f'    {cmd.description}')
            lines.append(f'    """')
            lines.append(f'    logger.info("Executing {cmd.name} command")')
            lines.append(f'    ')
            lines.append(f'    # TODO: Implement {cmd.name} logic')
            lines.append(f'    ')
            lines.append(f'    typer.echo("{cmd.name} completed successfully")')
            lines.append('')
            lines.append('')

        return '\n'.join(lines)


class ProjectGenerator:
    """Generate complete CLI project structure."""

    def __init__(self, config: ProjectConfig) -> None:
        """Initialize project generator."""
        self.config = config
        self.output_dir = config.output_dir

    def generate(self) -> None:
        """Generate complete project structure."""
        logger.info(f"Generating project: {self.config.name}")

        # Create directory structure
        self._create_directories()

        # Generate main CLI file
        self._generate_main_file()

        # Generate supporting files
        self._generate_setup_files()

        if self.config.generate_tests:
            self._generate_tests()

        if self.config.generate_docs:
            self._generate_docs()

        logger.info(f"Project generated successfully in {self.output_dir}")

    def _create_directories(self) -> None:
        """Create project directory structure."""
        dirs = [
            self.output_dir,
            self.output_dir / self.config.name.replace('-', '_'),
            self.output_dir / "tests",
            self.output_dir / "docs",
        ]

        for dir_path in dirs:
            dir_path.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Created directory: {dir_path}")

    def _generate_main_file(self) -> None:
        """Generate main CLI file."""
        module_name = self.config.name.replace('-', '_')
        main_file = self.output_dir / module_name / "cli.py"

        # Generate code based on framework
        if self.config.framework == Framework.ARGPARSE:
            code = TemplateGenerator.generate_argparse_main(self.config)
        elif self.config.framework == Framework.CLICK:
            code = TemplateGenerator.generate_click_main(self.config)
        elif self.config.framework == Framework.TYPER:
            code = TemplateGenerator.generate_typer_main(self.config)
        else:
            raise ValueError(f"Unsupported framework: {self.config.framework}")

        main_file.write_text(code)
        main_file.chmod(0o755)
        logger.info(f"Generated main file: {main_file}")

        # Generate __init__.py
        init_file = self.output_dir / module_name / "__init__.py"
        init_content = f'''"""
{self.config.name}

{self.config.description}
"""

__version__ = "{self.config.version}"
__author__ = "{self.config.author}"

from .cli import main

__all__ = ["main"]
'''
        init_file.write_text(init_content)

    def _generate_setup_files(self) -> None:
        """Generate setup and configuration files."""
        # pyproject.toml
        pyproject = self.output_dir / "pyproject.toml"

        dependencies = []
        if self.config.framework == Framework.CLICK:
            dependencies.append('click>=8.0')
        elif self.config.framework == Framework.TYPER:
            dependencies.append('typer[all]>=0.9')

        pyproject_content = f'''[project]
name = "{self.config.name}"
version = "{self.config.version}"
description = "{self.config.description}"
authors = [
    {{name = "{self.config.author}"}}
]
requires-python = ">={self.config.python_version}"
dependencies = {dependencies}

[project.scripts]
{self.config.name} = "{self.config.name.replace('-', '_')}.cli:main"

[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]

[tool.mypy]
python_version = "{self.config.python_version}"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
'''
        pyproject.write_text(pyproject_content)
        logger.info(f"Generated pyproject.toml")

        # README.md
        readme = self.output_dir / "README.md"
        readme_content = f'''# {self.config.name}

{self.config.description}

## Installation

```bash
pip install -e .
```

## Usage

```bash
{self.config.name} --help
```

## Commands

'''
        for cmd in self.config.commands:
            readme_content += f'### {cmd.name}\n\n{cmd.description}\n\n'
            readme_content += f'```bash\n{self.config.name} {cmd.name} --help\n```\n\n'

        readme.write_text(readme_content)
        logger.info("Generated README.md")

        # .gitignore
        gitignore = self.output_dir / ".gitignore"
        gitignore_content = '''__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg
.pytest_cache/
.mypy_cache/
.coverage
htmlcov/
.env
venv/
ENV/
'''
        gitignore.write_text(gitignore_content)

    def _generate_tests(self) -> None:
        """Generate test scaffold."""
        tests_dir = self.output_dir / "tests"

        # __init__.py
        (tests_dir / "__init__.py").write_text("")

        # test_cli.py
        test_file = tests_dir / "test_cli.py"
        module_name = self.config.name.replace('-', '_')

        test_content = f'''"""
Tests for {self.config.name} CLI
"""

import pytest
from {module_name}.cli import main


def test_version() -> None:
    """Test version flag."""
    # Note: Version test implementation pending
    pass


def test_help() -> None:
    """Test help output."""
    # Note: Help test implementation pending
    pass


'''
        for cmd in self.config.commands:
            func_name = cmd.name.replace('-', '_')
            test_content += f'''def test_{func_name}() -> None:
    """Test {cmd.name} command."""
    # Note: Command test implementation pending
    pass


'''

        test_file.write_text(test_content)
        logger.info(f"Generated test scaffold: {test_file}")

    def _generate_docs(self) -> None:
        """Generate documentation."""
        docs_dir = self.output_dir / "docs"

        # API documentation
        api_doc = docs_dir / "api.md"
        api_content = f'''# {self.config.name} API Documentation

## Commands

'''
        for cmd in self.config.commands:
            api_content += f'''### {cmd.name}

{cmd.description}

**Usage:**
```bash
{self.config.name} {cmd.name}
```

'''
            if cmd.arguments:
                api_content += '**Arguments:**\n\n'
                for arg in cmd.arguments:
                    api_content += f'- `{arg.get("name")}`: {arg.get("help")}\n'
                api_content += '\n'

            if cmd.options:
                api_content += '**Options:**\n\n'
                for opt in cmd.options:
                    api_content += f'- `{opt.get("name")}`: {opt.get("help")}\n'
                api_content += '\n'

        api_doc.write_text(api_content)
        logger.info("Generated API documentation")


class CLIGeneratorApp:
    """Main CLI generator application."""

    def __init__(self) -> None:
        """Initialize CLI generator."""
        self.parser = self._create_parser()

    def _create_parser(self) -> argparse.ArgumentParser:
        """Create argument parser."""
        parser = argparse.ArgumentParser(
            prog="cli-generator",
            description="Generate Python CLI application boilerplate",
            formatter_class=argparse.RawDescriptionHelpFormatter
        )

        parser.add_argument(
            "--version",
            action="version",
            version="cli-generator 1.0.0"
        )

        parser.add_argument(
            "--verbose", "-v",
            action="store_true",
            help="Enable verbose output"
        )

        parser.add_argument(
            "--output-format",
            choices=["text", "json"],
            default="text",
            help="Output format (default: text)"
        )

        subparsers = parser.add_subparsers(dest="command", help="Available commands")

        # generate command
        generate_parser = subparsers.add_parser(
            "generate",
            help="Generate a new CLI project"
        )
        generate_parser.add_argument(
            "name",
            help="Project name"
        )
        generate_parser.add_argument(
            "--description",
            default="A command-line tool",
            help="Project description"
        )
        generate_parser.add_argument(
            "--version",
            dest="proj_version",
            default="0.1.0",
            help="Project version"
        )
        generate_parser.add_argument(
            "--author",
            default="",
            help="Project author"
        )
        generate_parser.add_argument(
            "--framework",
            choices=["argparse", "click", "typer"],
            default="argparse",
            help="CLI framework to use"
        )
        generate_parser.add_argument(
            "--output-dir",
            type=Path,
            default=Path.cwd(),
            help="Output directory"
        )
        generate_parser.add_argument(
            "--no-tests",
            action="store_true",
            help="Skip test generation"
        )
        generate_parser.add_argument(
            "--no-docs",
            action="store_true",
            help="Skip documentation generation"
        )

        # init command
        init_parser = subparsers.add_parser(
            "init",
            help="Initialize CLI project from config file"
        )
        init_parser.add_argument(
            "config",
            type=Path,
            help="Configuration file path (JSON)"
        )

        # add-command command
        add_cmd_parser = subparsers.add_parser(
            "add-command",
            help="Add a new command to existing project"
        )
        add_cmd_parser.add_argument(
            "name",
            help="Command name"
        )
        add_cmd_parser.add_argument(
            "--description",
            default="Command description",
            help="Command description"
        )
        add_cmd_parser.add_argument(
            "--project-dir",
            type=Path,
            default=Path.cwd(),
            help="Project directory"
        )

        # scaffold command
        scaffold_parser = subparsers.add_parser(
            "scaffold",
            help="Generate project scaffold from interactive prompts"
        )
        scaffold_parser.add_argument(
            "--output-dir",
            type=Path,
            default=Path.cwd(),
            help="Output directory"
        )

        return parser

    def run(self, args: Optional[List[str]] = None) -> int:
        """Run the CLI application."""
        try:
            parsed_args = self.parser.parse_args(args)

            if parsed_args.verbose:
                logging.getLogger().setLevel(logging.DEBUG)

            if not parsed_args.command:
                self.parser.print_help()
                return 0

            # Execute command
            if parsed_args.command == "generate":
                return self.cmd_generate(parsed_args)
            elif parsed_args.command == "init":
                return self.cmd_init(parsed_args)
            elif parsed_args.command == "add-command":
                return self.cmd_add_command(parsed_args)
            elif parsed_args.command == "scaffold":
                return self.cmd_scaffold(parsed_args)
            else:
                logger.error(f"Command not implemented: {parsed_args.command}")
                return 1

        except KeyboardInterrupt:
            logger.info("\nOperation cancelled by user")
            return 130
        except Exception as e:
            logger.error(f"Error: {e}")
            if hasattr(parsed_args, 'verbose') and parsed_args.verbose:
                logger.exception("Detailed error:")
            return 1

    def cmd_generate(self, args: argparse.Namespace) -> int:
        """Execute generate command."""
        logger.info(f"Generating CLI project: {args.name}")

        # Create configuration
        config = ProjectConfig(
            name=args.name,
            description=args.description,
            version=args.proj_version,
            author=args.author,
            framework=Framework(args.framework),
            output_dir=args.output_dir / args.name,
            commands=[
                CommandDefinition(
                    name="example",
                    description="Example command",
                    arguments=[
                        {"name": "input", "help": "Input file", "type": "str"}
                    ],
                    options=[
                        {"name": "--output", "help": "Output file", "type": "str", "default": "output.txt"}
                    ]
                )
            ],
            generate_tests=not args.no_tests,
            generate_docs=not args.no_docs
        )

        # Generate project
        generator = ProjectGenerator(config)
        generator.generate()

        if args.output_format == "json":
            result = {
                "status": "success",
                "project": args.name,
                "directory": str(config.output_dir),
                "framework": args.framework
            }
            print(json.dumps(result, indent=2))
        else:
            print(f"\nProject '{args.name}' generated successfully!")
            print(f"Location: {config.output_dir}")
            print(f"Framework: {args.framework}")
            print("\nNext steps:")
            print(f"  cd {args.name}")
            print("  pip install -e .")
            print(f"  {args.name} --help")

        return 0

    def cmd_init(self, args: argparse.Namespace) -> int:
        """Execute init command."""
        logger.info(f"Initializing project from config: {args.config}")

        if not args.config.exists():
            logger.error(f"Config file not found: {args.config}")
            return 1

        # Load configuration
        with open(args.config, 'r') as f:
            config_data = json.load(f)

        # Parse commands
        commands = []
        for cmd_data in config_data.get('commands', []):
            commands.append(CommandDefinition(
                name=cmd_data['name'],
                description=cmd_data['description'],
                arguments=cmd_data.get('arguments', []),
                options=cmd_data.get('options', [])
            ))

        config = ProjectConfig(
            name=config_data['name'],
            description=config_data['description'],
            version=config_data.get('version', '0.1.0'),
            author=config_data.get('author', ''),
            framework=Framework(config_data.get('framework', 'argparse')),
            output_dir=Path(config_data.get('output_dir', '.')) / config_data['name'],
            commands=commands,
            generate_tests=config_data.get('generate_tests', True),
            generate_docs=config_data.get('generate_docs', True)
        )

        # Generate project
        generator = ProjectGenerator(config)
        generator.generate()

        if args.output_format == "json":
            result = {
                "status": "success",
                "project": config.name,
                "directory": str(config.output_dir)
            }
            print(json.dumps(result, indent=2))
        else:
            print(f"Project initialized successfully from {args.config}")

        return 0

    def cmd_add_command(self, args: argparse.Namespace) -> int:
        """Execute add-command command."""
        logger.info(f"Adding command: {args.name}")

        # Note: Adding command to existing project not yet supported

        if args.output_format == "json":
            result = {
                "status": "success",
                "command": args.name,
                "message": "Command addition not yet implemented"
            }
            print(json.dumps(result, indent=2))
        else:
            print(f"Command '{args.name}' would be added to {args.project_dir}")
            print("Note: This feature is not yet implemented")

        return 0

    def cmd_scaffold(self, args: argparse.Namespace) -> int:
        """Execute scaffold command."""
        logger.info("Starting interactive scaffold")

        # Note: Interactive scaffolding not yet implemented

        if args.output_format == "json":
            result = {
                "status": "success",
                "message": "Interactive scaffolding not yet implemented"
            }
            print(json.dumps(result, indent=2))
        else:
            print("Interactive scaffolding would start here")
            print("Note: This feature is not yet implemented")

        return 0


def main() -> int:
    """Main entry point."""
    app = CLIGeneratorApp()
    return app.run()


if __name__ == "__main__":
    sys.exit(main())
