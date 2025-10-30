#!/usr/bin/env python3
"""
Shell Completion Script Generator

Production-grade tool for generating shell completion scripts for Python CLI
applications. Supports bash, zsh, fish, and PowerShell with dynamic completion.

Features:
- Multi-shell support (bash, zsh, fish, PowerShell)
- Command discovery from CLI tools
- Option and argument extraction
- Dynamic completion support
- Installation helpers
- Validation and testing
"""

import argparse
import json
import logging
import re
import subprocess
import sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set, Any, Tuple


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class Shell(Enum):
    """Supported shell types."""
    BASH = "bash"
    ZSH = "zsh"
    FISH = "fish"
    POWERSHELL = "powershell"


class OutputFormat(Enum):
    """Output format options."""
    TEXT = "text"
    JSON = "json"


@dataclass
class CompletionOption:
    """Command line option definition."""
    name: str
    short: Optional[str] = None
    description: str = ""
    takes_value: bool = False
    value_type: Optional[str] = None
    choices: List[str] = field(default_factory=list)


@dataclass
class CompletionCommand:
    """Command definition for completion."""
    name: str
    description: str = ""
    options: List[CompletionOption] = field(default_factory=list)
    arguments: List[str] = field(default_factory=list)
    subcommands: List['CompletionCommand'] = field(default_factory=list)


@dataclass
class CompletionSpec:
    """Complete specification for shell completion."""
    program: str
    description: str
    commands: List[CompletionCommand]
    global_options: List[CompletionOption] = field(default_factory=list)


class CommandDiscovery:
    """Discover commands and options from CLI tools."""

    @staticmethod
    def discover_from_help(program: str) -> Optional[CompletionSpec]:
        """
        Discover commands by parsing --help output.

        Args:
            program: Program name or path

        Returns:
            CompletionSpec if successful, None otherwise
        """
        try:
            # Get main help
            result = subprocess.run(
                [program, "--help"],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode != 0:
                logger.warning(f"Failed to get help for {program}")
                return None

            help_text = result.stdout

            # Parse help text
            description = CommandDiscovery._extract_description(help_text)
            global_options = CommandDiscovery._extract_options(help_text)
            commands = CommandDiscovery._extract_commands(help_text, program)

            return CompletionSpec(
                program=program,
                description=description,
                commands=commands,
                global_options=global_options
            )

        except Exception as e:
            logger.error(f"Error discovering commands: {e}")
            return None

    @staticmethod
    def _extract_description(help_text: str) -> str:
        """Extract program description from help text."""
        lines = help_text.split('\n')
        for i, line in enumerate(lines):
            if line.strip() and not line.startswith((' ', '-')):
                # Take first non-indented line
                return line.strip()
        return ""

    @staticmethod
    def _extract_options(help_text: str) -> List[CompletionOption]:
        """Extract options from help text."""
        options = []

        # Pattern for options: -s, --long ARGS  Description
        option_pattern = re.compile(
            r'^\s*(-[a-zA-Z]),?\s*(--[a-z-]+)?\s*([A-Z_]+)?\s+(.+?)$',
            re.MULTILINE
        )

        # Pattern for long-only options: --long ARGS  Description
        long_pattern = re.compile(
            r'^\s*(--[a-z-]+)\s*([A-Z_]+)?\s+(.+?)$',
            re.MULTILINE
        )

        for match in option_pattern.finditer(help_text):
            short = match.group(1)
            long = match.group(2)
            value_arg = match.group(3)
            description = match.group(4).strip()

            if long:
                options.append(CompletionOption(
                    name=long,
                    short=short,
                    description=description,
                    takes_value=bool(value_arg),
                    value_type=value_arg.lower() if value_arg else None
                ))

        for match in long_pattern.finditer(help_text):
            long = match.group(1)
            value_arg = match.group(2)
            description = match.group(3).strip()

            # Skip if already added
            if not any(opt.name == long for opt in options):
                options.append(CompletionOption(
                    name=long,
                    description=description,
                    takes_value=bool(value_arg),
                    value_type=value_arg.lower() if value_arg else None
                ))

        return options

    @staticmethod
    def _extract_commands(help_text: str, program: str) -> List[CompletionCommand]:
        """Extract subcommands from help text."""
        commands = []

        # Look for commands section
        in_commands = False
        command_pattern = re.compile(r'^\s+([a-z-]+)\s+(.+?)$')

        for line in help_text.split('\n'):
            if re.match(r'(Commands|Available commands|Subcommands):', line, re.IGNORECASE):
                in_commands = True
                continue

            if in_commands:
                if not line.strip():
                    continue
                if not line.startswith(' '):
                    break

                match = command_pattern.match(line)
                if match:
                    cmd_name = match.group(1)
                    cmd_desc = match.group(2).strip()

                    # Try to get command help
                    cmd_options = CommandDiscovery._get_command_options(program, cmd_name)

                    commands.append(CompletionCommand(
                        name=cmd_name,
                        description=cmd_desc,
                        options=cmd_options
                    ))

        return commands

    @staticmethod
    def _get_command_options(program: str, command: str) -> List[CompletionOption]:
        """Get options for a specific command."""
        try:
            result = subprocess.run(
                [program, command, "--help"],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0:
                return CommandDiscovery._extract_options(result.stdout)

        except Exception:
            pass

        return []


class BashCompletionGenerator:
    """Generate bash completion scripts."""

    @staticmethod
    def generate(spec: CompletionSpec) -> str:
        """Generate bash completion script."""
        script = f'''# Bash completion for {spec.program}
# Generated by completion-builder

_{spec.program.replace("-", "_")}_completion() {{
    local cur prev words cword
    _init_completion || return

    local commands="{' '.join(cmd.name for cmd in spec.commands)}"
    local global_opts="{' '.join(opt.name for opt in spec.global_options)}"

    # Handle subcommands
    if [[ $cword -eq 1 ]]; then
        COMPREPLY=($(compgen -W "$commands $global_opts" -- "$cur"))
        return 0
    fi

    local command="${{words[1]}}"

    case "$command" in
'''

        # Add command-specific completions
        for cmd in spec.commands:
            opts = ' '.join(opt.name for opt in cmd.options)
            script += f'''        {cmd.name})
            local opts="{opts}"
            COMPREPLY=($(compgen -W "$opts" -- "$cur"))
            return 0
            ;;
'''

        script += '''    esac

    COMPREPLY=($(compgen -W "$global_opts" -- "$cur"))
    return 0
}

'''
        script += f'complete -F _{spec.program.replace("-", "_")}_completion {spec.program}\n'

        return script


class ZshCompletionGenerator:
    """Generate zsh completion scripts."""

    @staticmethod
    def generate(spec: CompletionSpec) -> str:
        """Generate zsh completion script."""
        script = f'''#compdef {spec.program}
# Zsh completion for {spec.program}
# Generated by completion-builder

_{spec.program.replace("-", "_")}() {{
    local -a commands
    local -a global_options

    global_options=(
'''

        # Add global options
        for opt in spec.global_options:
            desc = opt.description.replace("'", "\\'")
            if opt.short:
                script += f"        '{opt.short}[{desc}]'\n"
            script += f"        '{opt.name}[{desc}]'\n"

        script += '    )\n\n'

        # Add commands
        script += '    commands=(\n'
        for cmd in spec.commands:
            desc = cmd.description.replace("'", "\\'")
            script += f"        '{cmd.name}:{desc}'\n"
        script += '    )\n\n'

        # Main completion logic
        script += '''    _arguments -C \\
        $global_options \\
        '1: :->command' \\
        '*::arg:->args'

    case $state in
        command)
            _describe 'command' commands
            ;;
        args)
            case $words[1] in
'''

        # Add per-command completions
        for cmd in spec.commands:
            script += f'                {cmd.name})\n'
            script += '                    local -a options\n'
            script += '                    options=(\n'
            for opt in cmd.options:
                desc = opt.description.replace("'", "\\'")
                if opt.short:
                    script += f"                        '{opt.short}[{desc}]'\n"
                script += f"                        '{opt.name}[{desc}]'\n"
            script += '                    )\n'
            script += '                    _arguments $options\n'
            script += '                    ;;\n'

        script += '''            esac
            ;;
    esac
}

'''
        script += f'_{spec.program.replace("-", "_")} "$@"\n'

        return script


class FishCompletionGenerator:
    """Generate fish completion scripts."""

    @staticmethod
    def generate(spec: CompletionSpec) -> str:
        """Generate fish completion script."""
        script = f'''# Fish completion for {spec.program}
# Generated by completion-builder

# Global options
'''

        # Add global options
        for opt in spec.global_options:
            opt_name = opt.name.lstrip('-')
            short = f" -s {opt.short.lstrip('-')}" if opt.short else ""
            desc = opt.description.replace("'", "\\'")

            script += f"complete -c {spec.program}{short} -l {opt_name} -d '{desc}'\n"

        script += '\n# Subcommands\n'

        # Add subcommands
        for cmd in spec.commands:
            desc = cmd.description.replace("'", "\\'")
            script += f"complete -c {spec.program} -n '__fish_use_subcommand' -a {cmd.name} -d '{desc}'\n"

        # Add per-command options
        for cmd in spec.commands:
            if cmd.options:
                script += f'\n# Options for {cmd.name}\n'
                for opt in cmd.options:
                    opt_name = opt.name.lstrip('-')
                    short = f" -s {opt.short.lstrip('-')}" if opt.short else ""
                    desc = opt.description.replace("'", "\\'")

                    script += f"complete -c {spec.program} -n '__fish_seen_subcommand_from {cmd.name}'{short} -l {opt_name} -d '{desc}'\n"

        return script


class PowerShellCompletionGenerator:
    """Generate PowerShell completion scripts."""

    @staticmethod
    def generate(spec: CompletionSpec) -> str:
        """Generate PowerShell completion script."""
        script = f'''# PowerShell completion for {spec.program}
# Generated by completion-builder

Register-ArgumentCompleter -Native -CommandName {spec.program} -ScriptBlock {{
    param($wordToComplete, $commandAst, $cursorPosition)

    $commands = @(
'''

        # Add commands
        for cmd in spec.commands:
            desc = cmd.description.replace('"', '`"')
            script += f'        @{{ Name = "{cmd.name}"; Description = "{desc}" }}\n'

        script += '''    )

    $globalOptions = @(
'''

        # Add global options
        for opt in spec.global_options:
            desc = opt.description.replace('"', '`"')
            script += f'        @{{ Name = "{opt.name}"; Description = "{desc}" }}\n'

        script += '''    )

    # Get command context
    $tokens = $commandAst.CommandElements
    $currentToken = $tokens[-1].ToString()

    if ($tokens.Count -eq 2) {
        # Complete commands
        $completions = $commands + $globalOptions
    } else {
        $command = $tokens[1].ToString()

        # Command-specific completions
        switch ($command) {
'''

        # Add per-command completions
        for cmd in spec.commands:
            script += f'            "{cmd.name}" {{\n'
            script += '                $completions = @(\n'
            for opt in cmd.options:
                desc = opt.description.replace('"', '`"')
                script += f'                    @{{ Name = "{opt.name}"; Description = "{desc}" }}\n'
            script += '                )\n'
            script += '                break\n'
            script += '            }\n'

        script += '''            default {
                $completions = $globalOptions
            }
        }
    }

    $completions | Where-Object { $_.Name -like "$wordToComplete*" } | ForEach-Object {
        [System.Management.Automation.CompletionResult]::new(
            $_.Name,
            $_.Name,
            'ParameterName',
            $_.Description
        )
    }
}
'''

        return script


class CompletionInstaller:
    """Install completion scripts to appropriate locations."""

    INSTALL_PATHS = {
        Shell.BASH: [
            Path.home() / ".bash_completion",
            Path("/etc/bash_completion.d"),
            Path("/usr/local/etc/bash_completion.d")
        ],
        Shell.ZSH: [
            Path.home() / ".zsh" / "completion",
            Path("/usr/local/share/zsh/site-functions"),
            Path("/usr/share/zsh/site-functions")
        ],
        Shell.FISH: [
            Path.home() / ".config" / "fish" / "completions",
            Path("/usr/local/share/fish/vendor_completions.d"),
            Path("/usr/share/fish/vendor_completions.d")
        ],
        Shell.POWERSHELL: [
            Path.home() / "Documents" / "PowerShell" / "Scripts"
        ]
    }

    @staticmethod
    def install(shell: Shell, program: str, script: str) -> Tuple[bool, str]:
        """
        Install completion script.

        Returns:
            (success, path) tuple
        """
        paths = CompletionInstaller.INSTALL_PATHS.get(shell, [])

        for install_path in paths:
            if install_path.exists() or install_path.parent.exists():
                try:
                    # Create directory if needed
                    install_path.mkdir(parents=True, exist_ok=True)

                    # Determine filename
                    if shell == Shell.BASH:
                        filename = install_path / program if install_path.is_dir() else install_path
                    elif shell == Shell.ZSH:
                        filename = install_path / f"_{program}"
                    elif shell == Shell.FISH:
                        filename = install_path / f"{program}.fish"
                    elif shell == Shell.POWERSHELL:
                        filename = install_path / f"{program}-completion.ps1"
                    else:
                        continue

                    # Write script
                    filename.write_text(script)
                    logger.info(f"Installed {shell.value} completion to {filename}")

                    return True, str(filename)

                except Exception as e:
                    logger.warning(f"Failed to install to {install_path}: {e}")
                    continue

        return False, ""

    @staticmethod
    def get_install_instructions(shell: Shell, program: str) -> str:
        """Get manual installation instructions."""
        if shell == Shell.BASH:
            return f'''
To install manually:
1. Copy the completion script to one of these locations:
   - ~/.bash_completion
   - /etc/bash_completion.d/{program}
   - /usr/local/etc/bash_completion.d/{program}

2. Reload bash:
   source ~/.bashrc
'''
        elif shell == Shell.ZSH:
            return f'''
To install manually:
1. Copy the completion script to one of these locations:
   - ~/.zsh/completion/_{program}
   - /usr/local/share/zsh/site-functions/_{program}

2. Make sure this directory is in your $fpath
3. Reload zsh:
   exec zsh
'''
        elif shell == Shell.FISH:
            return f'''
To install manually:
1. Copy the completion script to:
   - ~/.config/fish/completions/{program}.fish

2. Reload fish:
   exec fish
'''
        elif shell == Shell.POWERSHELL:
            return f'''
To install manually:
1. Copy the completion script to:
   - ~/Documents/PowerShell/Scripts/{program}-completion.ps1

2. Add to your profile:
   . ~/Documents/PowerShell/Scripts/{program}-completion.ps1
'''
        else:
            return ""


class CompletionValidator:
    """Validate completion scripts."""

    @staticmethod
    def validate_bash(script: str) -> List[str]:
        """Validate bash completion script."""
        issues = []

        if not re.search(r'_init_completion', script):
            issues.append("Missing _init_completion call")

        if not re.search(r'complete -F', script):
            issues.append("Missing complete -F command")

        if not re.search(r'COMPREPLY=', script):
            issues.append("Missing COMPREPLY assignment")

        return issues

    @staticmethod
    def validate_zsh(script: str) -> List[str]:
        """Validate zsh completion script."""
        issues = []

        if not re.search(r'#compdef', script):
            issues.append("Missing #compdef directive")

        if not re.search(r'_arguments', script):
            issues.append("Missing _arguments call")

        return issues

    @staticmethod
    def validate_fish(script: str) -> List[str]:
        """Validate fish completion script."""
        issues = []

        if not re.search(r'complete -c', script):
            issues.append("Missing complete -c commands")

        return issues

    @staticmethod
    def validate_powershell(script: str) -> List[str]:
        """Validate PowerShell completion script."""
        issues = []

        if not re.search(r'Register-ArgumentCompleter', script):
            issues.append("Missing Register-ArgumentCompleter")

        if not re.search(r'CompletionResult', script):
            issues.append("Missing CompletionResult creation")

        return issues


class CompletionBuilderApp:
    """Main completion builder application."""

    def __init__(self) -> None:
        """Initialize completion builder."""
        self.parser = self._create_parser()

    def _create_parser(self) -> argparse.ArgumentParser:
        """Create argument parser."""
        parser = argparse.ArgumentParser(
            prog="completion-builder",
            description="Generate shell completion scripts",
            formatter_class=argparse.RawDescriptionHelpFormatter
        )

        parser.add_argument(
            "--version",
            action="version",
            version="completion-builder 1.0.0"
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
            help="Generate completion script"
        )
        generate_parser.add_argument(
            "program",
            help="Program name to generate completions for"
        )
        generate_parser.add_argument(
            "--shell",
            choices=["bash", "zsh", "fish", "powershell", "all"],
            default="bash",
            help="Target shell (default: bash)"
        )
        generate_parser.add_argument(
            "--output",
            type=Path,
            help="Output file (default: stdout)"
        )
        generate_parser.add_argument(
            "--spec",
            type=Path,
            help="Completion spec file (JSON)"
        )

        # install command
        install_parser = subparsers.add_parser(
            "install",
            help="Generate and install completion script"
        )
        install_parser.add_argument(
            "program",
            help="Program name"
        )
        install_parser.add_argument(
            "--shell",
            choices=["bash", "zsh", "fish", "powershell"],
            default="bash",
            help="Target shell (default: bash)"
        )

        # test command
        test_parser = subparsers.add_parser(
            "test",
            help="Test completion script"
        )
        test_parser.add_argument(
            "script",
            type=Path,
            help="Completion script to test"
        )
        test_parser.add_argument(
            "--shell",
            choices=["bash", "zsh", "fish", "powershell"],
            required=True,
            help="Shell type"
        )

        # validate command
        validate_parser = subparsers.add_parser(
            "validate",
            help="Validate completion script"
        )
        validate_parser.add_argument(
            "script",
            type=Path,
            help="Completion script to validate"
        )
        validate_parser.add_argument(
            "--shell",
            choices=["bash", "zsh", "fish", "powershell"],
            required=True,
            help="Shell type"
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
            elif parsed_args.command == "install":
                return self.cmd_install(parsed_args)
            elif parsed_args.command == "test":
                return self.cmd_test(parsed_args)
            elif parsed_args.command == "validate":
                return self.cmd_validate(parsed_args)
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
        logger.info(f"Generating completion for: {args.program}")

        # Get completion spec
        if args.spec:
            with open(args.spec, 'r') as f:
                spec_data = json.load(f)
            spec = self._load_spec(spec_data)
        else:
            spec = CommandDiscovery.discover_from_help(args.program)
            if not spec:
                logger.error(f"Failed to discover commands for {args.program}")
                return 1

        # Generate for specified shell(s)
        shells = [Shell(args.shell)] if args.shell != "all" else list(Shell)

        results = {}
        for shell in shells:
            script = self._generate_for_shell(shell, spec)
            results[shell.value] = script

            if args.output:
                if args.shell == "all":
                    output_path = args.output.parent / f"{args.output.stem}_{shell.value}{args.output.suffix}"
                else:
                    output_path = args.output

                output_path.write_text(script)
                logger.info(f"Written {shell.value} completion to {output_path}")
            elif len(shells) == 1:
                print(script)

        if args.output_format == "json":
            result = {
                "status": "success",
                "program": args.program,
                "shells": list(results.keys()),
                "scripts": results if not args.output else None
            }
            print(json.dumps(result, indent=2))

        return 0

    def cmd_install(self, args: argparse.Namespace) -> int:
        """Execute install command."""
        logger.info(f"Installing completion for: {args.program}")

        # Discover and generate
        spec = CommandDiscovery.discover_from_help(args.program)
        if not spec:
            logger.error(f"Failed to discover commands for {args.program}")
            return 1

        shell = Shell(args.shell)
        script = self._generate_for_shell(shell, spec)

        # Install
        success, path = CompletionInstaller.install(shell, args.program, script)

        if success:
            if args.output_format == "json":
                result = {
                    "status": "success",
                    "shell": args.shell,
                    "path": path
                }
                print(json.dumps(result, indent=2))
            else:
                print(f"Successfully installed {args.shell} completion to {path}")
                print(f"\nReload your shell to activate completions:")
                if shell == Shell.BASH:
                    print("  source ~/.bashrc")
                elif shell == Shell.ZSH:
                    print("  exec zsh")
                elif shell == Shell.FISH:
                    print("  exec fish")
            return 0
        else:
            logger.error("Failed to install completion")
            print("\nManual installation instructions:")
            print(CompletionInstaller.get_install_instructions(shell, args.program))
            return 1

    def cmd_test(self, args: argparse.Namespace) -> int:
        """Execute test command."""
        logger.info(f"Testing {args.shell} completion script: {args.script}")

        if not args.script.exists():
            logger.error(f"Script not found: {args.script}")
            return 1

        script = args.script.read_text()

        # Validate script
        shell = Shell(args.shell)
        issues = self._validate_script(shell, script)

        if args.output_format == "json":
            result = {
                "status": "valid" if not issues else "invalid",
                "issues": issues
            }
            print(json.dumps(result, indent=2))
        else:
            if issues:
                print("Validation issues found:")
                for issue in issues:
                    print(f"  - {issue}")
                return 1
            else:
                print("Script is valid")
                return 0

        return 1 if issues else 0

    def cmd_validate(self, args: argparse.Namespace) -> int:
        """Execute validate command."""
        return self.cmd_test(args)

    def _generate_for_shell(self, shell: Shell, spec: CompletionSpec) -> str:
        """Generate completion for specific shell."""
        if shell == Shell.BASH:
            return BashCompletionGenerator.generate(spec)
        elif shell == Shell.ZSH:
            return ZshCompletionGenerator.generate(spec)
        elif shell == Shell.FISH:
            return FishCompletionGenerator.generate(spec)
        elif shell == Shell.POWERSHELL:
            return PowerShellCompletionGenerator.generate(spec)
        else:
            raise ValueError(f"Unsupported shell: {shell}")

    def _validate_script(self, shell: Shell, script: str) -> List[str]:
        """Validate completion script."""
        if shell == Shell.BASH:
            return CompletionValidator.validate_bash(script)
        elif shell == Shell.ZSH:
            return CompletionValidator.validate_zsh(script)
        elif shell == Shell.FISH:
            return CompletionValidator.validate_fish(script)
        elif shell == Shell.POWERSHELL:
            return CompletionValidator.validate_powershell(script)
        else:
            return ["Unsupported shell"]

    def _load_spec(self, data: Dict[str, Any]) -> CompletionSpec:
        """Load completion spec from data."""
        commands = []
        for cmd_data in data.get('commands', []):
            options = [
                CompletionOption(**opt) for opt in cmd_data.get('options', [])
            ]
            commands.append(CompletionCommand(
                name=cmd_data['name'],
                description=cmd_data.get('description', ''),
                options=options
            ))

        global_options = [
            CompletionOption(**opt) for opt in data.get('global_options', [])
        ]

        return CompletionSpec(
            program=data['program'],
            description=data.get('description', ''),
            commands=commands,
            global_options=global_options
        )


def main() -> int:
    """Main entry point."""
    app = CompletionBuilderApp()
    return app.run()


if __name__ == "__main__":
    sys.exit(main())
