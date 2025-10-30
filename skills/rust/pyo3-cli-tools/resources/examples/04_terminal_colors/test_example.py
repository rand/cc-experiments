"""
Test suite for terminal colors example.
Demonstrates ANSI color codes and text formatting with PyO3.
"""
import terminal_colors


def test_basic_colors():
    """Test basic color application."""
    text = "Hello, World!"

    # Test different colors
    for color in ["red", "green", "blue", "yellow", "magenta", "cyan"]:
        colored = terminal_colors.colorize(text, color, False, False)
        assert text in colored
        assert "\x1b[" in colored  # Contains ANSI codes
        print(f"{color}: {colored}")


def test_bold_colors():
    """Test bold text colors."""
    text = "Bold text"
    colored = terminal_colors.colorize(text, "red", True, False)
    assert "\x1b[1m" in colored  # Bold code
    assert "\x1b[31m" in colored  # Red code
    print(f"Bold red: {colored}")


def test_background_colors():
    """Test background colors."""
    text = "Background"
    colored = terminal_colors.colorize(text, "blue", False, True)
    assert "\x1b[44m" in colored  # Blue background code
    print(f"Blue background: {colored}")


def test_rgb_colors():
    """Test RGB color support."""
    text = "RGB Color"

    # Test foreground RGB
    colored = terminal_colors.colorize_rgb(text, 255, 128, 0, False)
    assert "\x1b[38;2;" in colored
    print(f"RGB foreground: {colored}")

    # Test background RGB
    colored_bg = terminal_colors.colorize_rgb(text, 0, 128, 255, True)
    assert "\x1b[48;2;" in colored_bg
    print(f"RGB background: {colored_bg}")


def test_text_styles():
    """Test text styling."""
    text = "Styled text"

    styles = {
        "bold": "\x1b[1m",
        "dim": "\x1b[2m",
        "italic": "\x1b[3m",
        "underline": "\x1b[4m"
    }

    for style, code in styles.items():
        styled = terminal_colors.stylize(text, style)
        assert code in styled
        print(f"{style}: {styled}")


def test_status_messages():
    """Test status message formatting."""
    message = "Operation completed"

    statuses = ["success", "error", "warning", "info"]

    for status in statuses:
        formatted = terminal_colors.format_status(status, message)
        assert message in formatted
        assert any(icon in formatted for icon in ["✓", "✗", "⚠", "ℹ"])
        print(f"{status}: {formatted}")


def test_table_formatting():
    """Test table row formatting."""
    columns = ["Name", "Age", "City"]
    widths = [15, 5, 15]

    # Plain row
    row = terminal_colors.format_table_row(columns, widths, None)
    assert "Name" in row
    assert "│" in row
    print(f"\nPlain row: {row}")

    # Colored row
    colored_row = terminal_colors.format_table_row(columns, widths, "green")
    assert "\x1b[" in colored_row
    print(f"Colored row: {colored_row}")


def test_separators():
    """Test separator line generation."""
    width = 40

    styles = ["single", "double", "thick", "dotted"]

    for style in styles:
        sep = terminal_colors.format_separator(width, style)
        # Strip ANSI to get actual character count
        actual_len = terminal_colors.visible_length(sep)
        assert actual_len == width
        print(f"{style} separator: {sep}")


def test_ansi_stripping():
    """Test ANSI code removal."""
    text = "Hello"
    colored = terminal_colors.colorize(text, "red", True, False)

    # Colored text should have ANSI codes
    assert len(colored) > len(text)
    assert "\x1b[" in colored

    # Stripped text should match original
    stripped = terminal_colors.strip_ansi(colored)
    assert stripped == text
    print(f"\nOriginal: '{text}'")
    print(f"Colored: '{colored}'")
    print(f"Stripped: '{stripped}'")


def test_visible_length():
    """Test visible length calculation."""
    text = "Test"
    colored = terminal_colors.colorize(text, "blue", False, False)

    # Visible length should match original text
    visible_len = terminal_colors.visible_length(colored)
    assert visible_len == len(text)
    print(f"\nActual length: {len(colored)}")
    print(f"Visible length: {visible_len}")


def test_cli_integration():
    """Demonstrate CLI usage patterns."""
    print("\n" + "=" * 60)
    print("CLI Demo: File Processing Results")
    print("=" * 60)

    # Header
    header = terminal_colors.format_table_row(
        ["File", "Status", "Time"],
        [30, 15, 10],
        "cyan"
    )
    print(header)
    print(terminal_colors.format_separator(60, "single"))

    # Data rows
    files = [
        ("config.json", "success", "0.5s"),
        ("data.csv", "success", "1.2s"),
        ("broken.xml", "error", "0.1s"),
    ]

    for filename, status, time in files:
        status_msg = terminal_colors.format_status(status, status.capitalize())
        row = terminal_colors.format_table_row(
            [filename, status_msg, time],
            [30, 15, 10],
            None
        )
        print(row)

    print(terminal_colors.format_separator(60, "double"))


def test_error_handling():
    """Test error handling for invalid inputs."""
    # Invalid color
    try:
        terminal_colors.colorize("text", "invalid_color", False, False)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        print(f"\nCorrectly raised ValueError: {e}")

    # Invalid style
    try:
        terminal_colors.stylize("text", "invalid_style")
        assert False, "Should have raised ValueError"
    except ValueError as e:
        print(f"Correctly raised ValueError: {e}")


if __name__ == "__main__":
    print("=" * 60)
    print("Terminal Colors Example Tests")
    print("=" * 60)

    test_basic_colors()
    test_bold_colors()
    test_background_colors()
    test_rgb_colors()
    test_text_styles()
    test_status_messages()
    test_table_formatting()
    test_separators()
    test_ansi_stripping()
    test_visible_length()
    test_cli_integration()
    test_error_handling()

    print("\n" + "=" * 60)
    print("All tests passed!")
    print("=" * 60)
