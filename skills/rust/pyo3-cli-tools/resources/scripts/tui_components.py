#!/usr/bin/env python3
"""
Terminal UI Component Library

Production-grade library for building terminal user interfaces with rich
components including progress bars, tables, menus, and layouts.

Features:
- Progress bar utilities (simple, multi-bar, spinner)
- Table rendering (ASCII, Unicode, markdown)
- Menu creation (single-select, multi-select)
- Layout management (grid, split, box)
- Color and styling support
- Demo and testing utilities
"""

import argparse
import json
import logging
import sys
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Any, Dict, Callable, Tuple
import shutil
import itertools
import threading


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class OutputFormat(Enum):
    """Output format options."""
    TEXT = "text"
    JSON = "json"


class TableStyle(Enum):
    """Table rendering styles."""
    ASCII = "ascii"
    UNICODE = "unicode"
    MARKDOWN = "markdown"
    SIMPLE = "simple"
    GRID = "grid"


class ProgressBarStyle(Enum):
    """Progress bar styles."""
    BASIC = "basic"
    BLOCK = "block"
    ARROW = "arrow"
    DOTS = "dots"


class Color:
    """ANSI color codes."""
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    ITALIC = "\033[3m"
    UNDERLINE = "\033[4m"

    # Foreground colors
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"

    # Background colors
    BG_BLACK = "\033[40m"
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"
    BG_BLUE = "\033[44m"
    BG_MAGENTA = "\033[45m"
    BG_CYAN = "\033[46m"
    BG_WHITE = "\033[47m"

    @staticmethod
    def rgb(r: int, g: int, b: int) -> str:
        """Create RGB foreground color."""
        return f"\033[38;2;{r};{g};{b}m"

    @staticmethod
    def bg_rgb(r: int, g: int, b: int) -> str:
        """Create RGB background color."""
        return f"\033[48;2;{r};{g};{b}m"

    @staticmethod
    def strip(text: str) -> str:
        """Strip ANSI codes from text."""
        import re
        return re.sub(r'\033\[[0-9;]*m', '', text)


@dataclass
class ProgressBar:
    """Progress bar component."""
    total: int
    width: int = 50
    style: ProgressBarStyle = ProgressBarStyle.BLOCK
    prefix: str = ""
    suffix: str = ""
    show_percentage: bool = True
    show_count: bool = True
    show_eta: bool = False
    color: str = Color.GREEN

    def __post_init__(self) -> None:
        """Initialize progress bar state."""
        self.current = 0
        self.start_time = time.time()

    def render(self, current: Optional[int] = None) -> str:
        """Render progress bar."""
        if current is not None:
            self.current = current

        percentage = self.current / self.total if self.total > 0 else 0
        filled_width = int(self.width * percentage)

        # Choose bar characters based on style
        if self.style == ProgressBarStyle.BLOCK:
            fill_char = "█"
            empty_char = "░"
        elif self.style == ProgressBarStyle.ARROW:
            fill_char = "="
            empty_char = " "
        elif self.style == ProgressBarStyle.DOTS:
            fill_char = "●"
            empty_char = "○"
        else:  # BASIC
            fill_char = "#"
            empty_char = "-"

        # Build bar
        bar = fill_char * filled_width + empty_char * (self.width - filled_width)

        # Build parts
        parts = []
        if self.prefix:
            parts.append(self.prefix)

        parts.append(f"{self.color}{bar}{Color.RESET}")

        if self.show_percentage:
            parts.append(f"{percentage * 100:5.1f}%")

        if self.show_count:
            parts.append(f"({self.current}/{self.total})")

        if self.show_eta and self.current > 0:
            elapsed = time.time() - self.start_time
            rate = self.current / elapsed
            remaining = (self.total - self.current) / rate if rate > 0 else 0
            parts.append(f"ETA: {remaining:.1f}s")

        if self.suffix:
            parts.append(self.suffix)

        return " ".join(parts)

    def update(self, amount: int = 1) -> None:
        """Update progress by amount."""
        self.current = min(self.current + amount, self.total)

    def is_complete(self) -> bool:
        """Check if progress is complete."""
        return self.current >= self.total


@dataclass
class Spinner:
    """Spinner animation component."""
    frames: List[str] = field(default_factory=lambda: ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"])
    message: str = "Loading"
    color: str = Color.CYAN

    def __post_init__(self) -> None:
        """Initialize spinner state."""
        self.frame_idx = 0
        self.running = False
        self.thread: Optional[threading.Thread] = None

    def render(self) -> str:
        """Render current spinner frame."""
        frame = self.frames[self.frame_idx]
        return f"\r{self.color}{frame}{Color.RESET} {self.message}"

    def next_frame(self) -> None:
        """Move to next frame."""
        self.frame_idx = (self.frame_idx + 1) % len(self.frames)

    def start(self) -> None:
        """Start spinner animation."""
        self.running = True

        def animate() -> None:
            while self.running:
                sys.stdout.write(self.render())
                sys.stdout.flush()
                time.sleep(0.1)
                self.next_frame()

        self.thread = threading.Thread(target=animate, daemon=True)
        self.thread.start()

    def stop(self) -> None:
        """Stop spinner animation."""
        self.running = False
        if self.thread:
            self.thread.join()
        sys.stdout.write("\r" + " " * (len(self.message) + 10) + "\r")
        sys.stdout.flush()


@dataclass
class Table:
    """Table component for rendering tabular data."""
    headers: List[str]
    rows: List[List[Any]]
    style: TableStyle = TableStyle.UNICODE
    align: Optional[List[str]] = None
    max_width: Optional[int] = None

    def __post_init__(self) -> None:
        """Initialize table."""
        if self.align is None:
            self.align = ["left"] * len(self.headers)

        if self.max_width is None:
            term_size = shutil.get_terminal_size((80, 20))
            self.max_width = term_size.columns

    def render(self) -> str:
        """Render table."""
        if self.style == TableStyle.ASCII:
            return self._render_ascii()
        elif self.style == TableStyle.UNICODE:
            return self._render_unicode()
        elif self.style == TableStyle.MARKDOWN:
            return self._render_markdown()
        elif self.style == TableStyle.SIMPLE:
            return self._render_simple()
        elif self.style == TableStyle.GRID:
            return self._render_grid()
        else:
            return self._render_simple()

    def _calculate_column_widths(self) -> List[int]:
        """Calculate optimal column widths."""
        widths = [len(Color.strip(str(h))) for h in self.headers]

        for row in self.rows:
            for i, cell in enumerate(row):
                widths[i] = max(widths[i], len(Color.strip(str(cell))))

        # Adjust for max width
        total_width = sum(widths) + len(widths) * 3  # borders and padding
        if total_width > self.max_width:
            # Proportionally reduce column widths
            scale = (self.max_width - len(widths) * 3) / sum(widths)
            widths = [max(10, int(w * scale)) for w in widths]

        return widths

    def _format_cell(self, cell: Any, width: int, align: str) -> str:
        """Format a single cell."""
        text = str(cell)
        stripped = Color.strip(text)
        padding = width - len(stripped)

        if align == "right":
            return " " * padding + text
        elif align == "center":
            left_pad = padding // 2
            right_pad = padding - left_pad
            return " " * left_pad + text + " " * right_pad
        else:  # left
            return text + " " * padding

    def _render_ascii(self) -> str:
        """Render ASCII style table."""
        widths = self._calculate_column_widths()
        lines = []

        # Top border
        lines.append("+" + "+".join("-" * (w + 2) for w in widths) + "+")

        # Header
        header_cells = [
            self._format_cell(h, w, "center")
            for h, w in zip(self.headers, widths)
        ]
        lines.append("| " + " | ".join(header_cells) + " |")

        # Header separator
        lines.append("+" + "+".join("=" * (w + 2) for w in widths) + "+")

        # Rows
        for row in self.rows:
            row_cells = [
                self._format_cell(cell, w, a)
                for cell, w, a in zip(row, widths, self.align)
            ]
            lines.append("| " + " | ".join(row_cells) + " |")

        # Bottom border
        lines.append("+" + "+".join("-" * (w + 2) for w in widths) + "+")

        return "\n".join(lines)

    def _render_unicode(self) -> str:
        """Render Unicode style table."""
        widths = self._calculate_column_widths()
        lines = []

        # Top border
        lines.append("┌" + "┬".join("─" * (w + 2) for w in widths) + "┐")

        # Header
        header_cells = [
            self._format_cell(h, w, "center")
            for h, w in zip(self.headers, widths)
        ]
        lines.append("│ " + " │ ".join(header_cells) + " │")

        # Header separator
        lines.append("├" + "┼".join("─" * (w + 2) for w in widths) + "┤")

        # Rows
        for row in self.rows:
            row_cells = [
                self._format_cell(cell, w, a)
                for cell, w, a in zip(row, widths, self.align)
            ]
            lines.append("│ " + " │ ".join(row_cells) + " │")

        # Bottom border
        lines.append("└" + "┴".join("─" * (w + 2) for w in widths) + "┘")

        return "\n".join(lines)

    def _render_markdown(self) -> str:
        """Render Markdown style table."""
        widths = self._calculate_column_widths()
        lines = []

        # Header
        header_cells = [
            self._format_cell(h, w, "left")
            for h, w in zip(self.headers, widths)
        ]
        lines.append("| " + " | ".join(header_cells) + " |")

        # Separator
        sep_cells = [
            "-" * w if a == "left" else
            ":" + "-" * (w - 1) if a == "right" else
            ":" + "-" * (w - 2) + ":"
            for w, a in zip(widths, self.align)
        ]
        lines.append("| " + " | ".join(sep_cells) + " |")

        # Rows
        for row in self.rows:
            row_cells = [
                self._format_cell(cell, w, a)
                for cell, w, a in zip(row, widths, self.align)
            ]
            lines.append("| " + " | ".join(row_cells) + " |")

        return "\n".join(lines)

    def _render_simple(self) -> str:
        """Render simple style table."""
        widths = self._calculate_column_widths()
        lines = []

        # Header
        header_cells = [
            self._format_cell(h, w, "left")
            for h, w in zip(self.headers, widths)
        ]
        lines.append("  ".join(header_cells))

        # Separator
        lines.append("  ".join("-" * w for w in widths))

        # Rows
        for row in self.rows:
            row_cells = [
                self._format_cell(cell, w, a)
                for cell, w, a in zip(row, widths, self.align)
            ]
            lines.append("  ".join(row_cells))

        return "\n".join(lines)

    def _render_grid(self) -> str:
        """Render grid style table."""
        widths = self._calculate_column_widths()
        lines = []

        # Top border
        lines.append("+" + "+".join("-" * (w + 2) for w in widths) + "+")

        # Header
        header_cells = [
            self._format_cell(h, w, "center")
            for h, w in zip(self.headers, widths)
        ]
        lines.append("| " + " | ".join(header_cells) + " |")

        # Separator
        lines.append("+" + "+".join("-" * (w + 2) for w in widths) + "+")

        # Rows
        for row in self.rows:
            row_cells = [
                self._format_cell(cell, w, a)
                for cell, w, a in zip(row, widths, self.align)
            ]
            lines.append("| " + " | ".join(row_cells) + " |")
            lines.append("+" + "+".join("-" * (w + 2) for w in widths) + "+")

        return "\n".join(lines)


@dataclass
class Box:
    """Box component for framing content."""
    content: str
    title: Optional[str] = None
    width: Optional[int] = None
    style: str = "unicode"
    padding: int = 1

    def render(self) -> str:
        """Render box."""
        if self.width is None:
            term_size = shutil.get_terminal_size((80, 20))
            self.width = min(term_size.columns - 4, 100)

        if self.style == "unicode":
            return self._render_unicode()
        elif self.style == "ascii":
            return self._render_ascii()
        elif self.style == "double":
            return self._render_double()
        else:
            return self._render_unicode()

    def _render_unicode(self) -> str:
        """Render Unicode box."""
        lines = []
        content_width = self.width - 2 - 2 * self.padding

        # Top border
        if self.title:
            title_line = f"┤ {self.title} ├"
            padding_left = (self.width - len(title_line)) // 2
            padding_right = self.width - len(title_line) - padding_left
            lines.append("┌" + "─" * padding_left + title_line + "─" * padding_right + "┐")
        else:
            lines.append("┌" + "─" * (self.width - 2) + "┐")

        # Top padding
        for _ in range(self.padding):
            lines.append("│" + " " * (self.width - 2) + "│")

        # Content
        for line in self.content.split('\n'):
            stripped = Color.strip(line)
            if len(stripped) > content_width:
                # Wrap line
                words = line.split()
                current_line = ""
                for word in words:
                    if len(Color.strip(current_line + " " + word)) <= content_width:
                        current_line += (" " if current_line else "") + word
                    else:
                        if current_line:
                            padding_needed = content_width - len(Color.strip(current_line))
                            lines.append(f"│{' ' * self.padding}{current_line}{' ' * padding_needed}{' ' * self.padding}│")
                        current_line = word

                if current_line:
                    padding_needed = content_width - len(Color.strip(current_line))
                    lines.append(f"│{' ' * self.padding}{current_line}{' ' * padding_needed}{' ' * self.padding}│")
            else:
                padding_needed = content_width - len(stripped)
                lines.append(f"│{' ' * self.padding}{line}{' ' * padding_needed}{' ' * self.padding}│")

        # Bottom padding
        for _ in range(self.padding):
            lines.append("│" + " " * (self.width - 2) + "│")

        # Bottom border
        lines.append("└" + "─" * (self.width - 2) + "┘")

        return "\n".join(lines)

    def _render_ascii(self) -> str:
        """Render ASCII box."""
        lines = []
        content_width = self.width - 2 - 2 * self.padding

        # Top border
        if self.title:
            title_line = f"[ {self.title} ]"
            padding_left = (self.width - len(title_line)) // 2
            padding_right = self.width - len(title_line) - padding_left
            lines.append("+" + "-" * padding_left + title_line + "-" * padding_right + "+")
        else:
            lines.append("+" + "-" * (self.width - 2) + "+")

        # Content
        for line in self.content.split('\n'):
            stripped = Color.strip(line)
            padding_needed = content_width - len(stripped)
            lines.append(f"|{' ' * self.padding}{line}{' ' * padding_needed}{' ' * self.padding}|")

        # Bottom border
        lines.append("+" + "-" * (self.width - 2) + "+")

        return "\n".join(lines)

    def _render_double(self) -> str:
        """Render double-line box."""
        lines = []
        content_width = self.width - 2 - 2 * self.padding

        # Top border
        if self.title:
            title_line = f"╡ {self.title} ╞"
            padding_left = (self.width - len(title_line)) // 2
            padding_right = self.width - len(title_line) - padding_left
            lines.append("╔" + "═" * padding_left + title_line + "═" * padding_right + "╗")
        else:
            lines.append("╔" + "═" * (self.width - 2) + "╗")

        # Content
        for line in self.content.split('\n'):
            stripped = Color.strip(line)
            padding_needed = content_width - len(stripped)
            lines.append(f"║{' ' * self.padding}{line}{' ' * padding_needed}{' ' * self.padding}║")

        # Bottom border
        lines.append("╚" + "═" * (self.width - 2) + "╝")

        return "\n".join(lines)


@dataclass
class Menu:
    """Interactive menu component."""
    title: str
    options: List[str]
    multi_select: bool = False
    selected: List[int] = field(default_factory=list)

    def render(self) -> str:
        """Render menu."""
        lines = [f"{Color.BOLD}{self.title}{Color.RESET}", ""]

        for i, option in enumerate(self.options):
            prefix = f"{Color.GREEN}[✓]{Color.RESET}" if i in self.selected else "[ ]"
            marker = f"{Color.CYAN}→{Color.RESET}" if i == 0 else " "
            lines.append(f"{marker} {prefix} {option}")

        lines.append("")
        if self.multi_select:
            lines.append("Space: select, Enter: confirm, q: cancel")
        else:
            lines.append("Enter: select, q: cancel")

        return "\n".join(lines)

    def select(self, index: int) -> None:
        """Toggle selection at index."""
        if 0 <= index < len(self.options):
            if self.multi_select:
                if index in self.selected:
                    self.selected.remove(index)
                else:
                    self.selected.append(index)
            else:
                self.selected = [index]

    def get_selected(self) -> List[str]:
        """Get selected option names."""
        return [self.options[i] for i in sorted(self.selected)]


class Layout:
    """Layout manager for terminal UI."""

    @staticmethod
    def horizontal_split(left: str, right: str, ratio: float = 0.5) -> str:
        """Split content horizontally."""
        term_width = shutil.get_terminal_size((80, 20)).columns
        left_width = int(term_width * ratio)
        right_width = term_width - left_width - 3  # Account for separator

        left_lines = left.split('\n')
        right_lines = right.split('\n')
        max_lines = max(len(left_lines), len(right_lines))

        # Pad shorter side
        left_lines += [""] * (max_lines - len(left_lines))
        right_lines += [""] * (max_lines - len(right_lines))

        result = []
        for left_line, right_line in zip(left_lines, right_lines):
            left_stripped = Color.strip(left_line)
            left_pad = left_width - len(left_stripped)
            result.append(f"{left_line}{' ' * left_pad} │ {right_line}")

        return "\n".join(result)

    @staticmethod
    def vertical_split(top: str, bottom: str, separator: bool = True) -> str:
        """Split content vertically."""
        lines = []
        lines.extend(top.split('\n'))

        if separator:
            term_width = shutil.get_terminal_size((80, 20)).columns
            lines.append("─" * term_width)

        lines.extend(bottom.split('\n'))

        return "\n".join(lines)

    @staticmethod
    def grid(items: List[str], columns: int = 2) -> str:
        """Arrange items in grid."""
        term_width = shutil.get_terminal_size((80, 20)).columns
        col_width = term_width // columns - 2

        result = []
        for i in range(0, len(items), columns):
            row_items = items[i:i + columns]
            row_lines = [item.split('\n') for item in row_items]
            max_lines = max(len(lines) for lines in row_lines)

            # Pad each item
            for lines in row_lines:
                lines.extend([""] * (max_lines - len(lines)))

            # Combine row
            for line_idx in range(max_lines):
                line_parts = []
                for item_lines in row_lines:
                    line = item_lines[line_idx]
                    stripped = Color.strip(line)
                    padding = col_width - len(stripped)
                    line_parts.append(line + " " * padding)

                result.append("  ".join(line_parts))

        return "\n".join(result)


class TUIComponentsApp:
    """Main TUI components application."""

    def __init__(self) -> None:
        """Initialize TUI components app."""
        self.parser = self._create_parser()

    def _create_parser(self) -> argparse.ArgumentParser:
        """Create argument parser."""
        parser = argparse.ArgumentParser(
            prog="tui-components",
            description="Terminal UI component library and demos",
            formatter_class=argparse.RawDescriptionHelpFormatter
        )

        parser.add_argument(
            "--version",
            action="version",
            version="tui-components 1.0.0"
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

        # demo command
        demo_parser = subparsers.add_parser(
            "demo",
            help="Run component demos"
        )
        demo_parser.add_argument(
            "component",
            nargs="?",
            choices=["progress", "spinner", "table", "box", "menu", "layout", "all"],
            default="all",
            help="Component to demo"
        )

        # render command
        render_parser = subparsers.add_parser(
            "render",
            help="Render component from spec"
        )
        render_parser.add_argument(
            "spec",
            type=argparse.FileType('r'),
            help="Component specification (JSON)"
        )

        # test command
        test_parser = subparsers.add_parser(
            "test",
            help="Test component rendering"
        )
        test_parser.add_argument(
            "component",
            choices=["progress", "table", "box"],
            help="Component to test"
        )

        # export command
        export_parser = subparsers.add_parser(
            "export",
            help="Export rendered component"
        )
        export_parser.add_argument(
            "component",
            choices=["progress", "table", "box"],
            help="Component to export"
        )
        export_parser.add_argument(
            "--output",
            type=argparse.FileType('w'),
            default=sys.stdout,
            help="Output file"
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
            if parsed_args.command == "demo":
                return self.cmd_demo(parsed_args)
            elif parsed_args.command == "render":
                return self.cmd_render(parsed_args)
            elif parsed_args.command == "test":
                return self.cmd_test(parsed_args)
            elif parsed_args.command == "export":
                return self.cmd_export(parsed_args)
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

    def cmd_demo(self, args: argparse.Namespace) -> int:
        """Execute demo command."""
        if args.component == "all" or args.component == "progress":
            self._demo_progress()
            print("\n")

        if args.component == "all" or args.component == "spinner":
            self._demo_spinner()
            print("\n")

        if args.component == "all" or args.component == "table":
            self._demo_table()
            print("\n")

        if args.component == "all" or args.component == "box":
            self._demo_box()
            print("\n")

        if args.component == "all" or args.component == "menu":
            self._demo_menu()
            print("\n")

        if args.component == "all" or args.component == "layout":
            self._demo_layout()
            print("\n")

        return 0

    def _demo_progress(self) -> None:
        """Demo progress bar."""
        print(f"{Color.BOLD}Progress Bar Demo{Color.RESET}\n")

        # Basic progress bar
        bar = ProgressBar(total=50, style=ProgressBarStyle.BLOCK, prefix="Download:")
        for i in range(51):
            print(f"\r{bar.render(i)}", end="", flush=True)
            time.sleep(0.02)
        print()

        # Arrow style
        bar = ProgressBar(total=30, style=ProgressBarStyle.ARROW, prefix="Build:", color=Color.BLUE)
        for i in range(31):
            print(f"\r{bar.render(i)}", end="", flush=True)
            time.sleep(0.03)
        print()

    def _demo_spinner(self) -> None:
        """Demo spinner."""
        print(f"{Color.BOLD}Spinner Demo{Color.RESET}\n")

        spinner = Spinner(message="Processing...")
        spinner.start()
        time.sleep(2)
        spinner.stop()
        print(f"{Color.GREEN}✓{Color.RESET} Done!\n")

    def _demo_table(self) -> None:
        """Demo table rendering."""
        print(f"{Color.BOLD}Table Demo{Color.RESET}\n")

        headers = ["Name", "Age", "City", "Status"]
        rows = [
            ["Alice", 30, "New York", f"{Color.GREEN}Active{Color.RESET}"],
            ["Bob", 25, "San Francisco", f"{Color.YELLOW}Pending{Color.RESET}"],
            ["Charlie", 35, "Los Angeles", f"{Color.GREEN}Active{Color.RESET}"],
            ["Diana", 28, "Chicago", f"{Color.RED}Inactive{Color.RESET}"],
        ]

        # Unicode table
        table = Table(headers, rows, style=TableStyle.UNICODE, align=["left", "right", "left", "center"])
        print("Unicode Style:")
        print(table.render())
        print()

        # Markdown table
        table = Table(headers, rows, style=TableStyle.MARKDOWN)
        print("Markdown Style:")
        print(table.render())
        print()

    def _demo_box(self) -> None:
        """Demo box rendering."""
        print(f"{Color.BOLD}Box Demo{Color.RESET}\n")

        content = f"""This is a {Color.CYAN}boxed content{Color.RESET} example.
It can contain multiple lines and colored text.
Boxes automatically wrap long lines to fit the specified width."""

        box = Box(content, title="Information", style="unicode")
        print(box.render())
        print()

        box = Box(content, title="Warning", style="double")
        print(box.render())
        print()

    def _demo_menu(self) -> None:
        """Demo menu rendering."""
        print(f"{Color.BOLD}Menu Demo{Color.RESET}\n")

        menu = Menu(
            title="Select options:",
            options=["Option 1", "Option 2", "Option 3", "Option 4"],
            multi_select=True
        )
        menu.select(0)
        menu.select(2)

        print(menu.render())

    def _demo_layout(self) -> None:
        """Demo layout management."""
        print(f"{Color.BOLD}Layout Demo{Color.RESET}\n")

        left_content = "Left Panel\n" + "\n".join(f"Line {i}" for i in range(5))
        right_content = "Right Panel\n" + "\n".join(f"Item {i}" for i in range(5))

        split = Layout.horizontal_split(left_content, right_content, ratio=0.4)
        print("Horizontal Split:")
        print(split)
        print()

    def cmd_render(self, args: argparse.Namespace) -> int:
        """Execute render command."""
        logger.info("Rendering component from spec")

        spec = json.load(args.spec)
        component_type = spec.get('type')

        if component_type == 'table':
            table = Table(
                headers=spec['headers'],
                rows=spec['rows'],
                style=TableStyle(spec.get('style', 'unicode'))
            )
            print(table.render())
        elif component_type == 'box':
            box = Box(
                content=spec['content'],
                title=spec.get('title'),
                style=spec.get('style', 'unicode')
            )
            print(box.render())
        else:
            logger.error(f"Unknown component type: {component_type}")
            return 1

        return 0

    def cmd_test(self, args: argparse.Namespace) -> int:
        """Execute test command."""
        logger.info(f"Testing {args.component} component")

        if args.component == "progress":
            bar = ProgressBar(total=10)
            for i in range(11):
                bar.update()
            assert bar.is_complete()

        elif args.component == "table":
            table = Table(
                headers=["A", "B"],
                rows=[["1", "2"], ["3", "4"]],
                style=TableStyle.UNICODE
            )
            output = table.render()
            assert "A" in output and "B" in output

        elif args.component == "box":
            box = Box("Test content", title="Test")
            output = box.render()
            assert "Test content" in output

        if args.output_format == "json":
            result = {"status": "success", "component": args.component}
            print(json.dumps(result, indent=2))
        else:
            print(f"{args.component} test passed")

        return 0

    def cmd_export(self, args: argparse.Namespace) -> int:
        """Execute export command."""
        logger.info(f"Exporting {args.component} component")

        if args.component == "table":
            table = Table(
                headers=["Column 1", "Column 2"],
                rows=[["Value 1", "Value 2"]],
                style=TableStyle.UNICODE
            )
            args.output.write(table.render())

        elif args.component == "box":
            box = Box("Exported content", title="Export")
            args.output.write(box.render())

        elif args.component == "progress":
            bar = ProgressBar(total=100, width=50)
            bar.current = 75
            args.output.write(bar.render())

        return 0


def main() -> int:
    """Main entry point."""
    app = TUIComponentsApp()
    return app.run()


if __name__ == "__main__":
    sys.exit(main())
