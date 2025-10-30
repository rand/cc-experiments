"""Test suite for TUI components."""
import tui_components


def test_draw_box():
    """Test box drawing."""
    lines = tui_components.draw_box("Title", ["Line 1", "Line 2"], 40, "light")
    assert len(lines) == 4  # top + 2 content + bottom
    print(f"Box with {len(lines)} lines:")
    for line in lines:
        print(line)


def test_draw_menu():
    """Test menu drawing."""
    menu = tui_components.draw_menu("Options", ["Item 1", "Item 2", "Item 3"], 1)
    assert len(menu) > 0
    print(f"\nMenu:")
    for line in menu:
        print(line)


def test_draw_tree():
    """Test tree drawing."""
    tree = tui_components.draw_tree(
        "Root",
        [("Branch 1", ["Leaf 1", "Leaf 2"]), ("Branch 2", ["Leaf 3"])]
    )
    print(f"\nTree:")
    for line in tree:
        print(line)


def test_terminal_size():
    """Test terminal size detection."""
    width, height = tui_components.get_terminal_size()
    assert width > 0 and height > 0
    print(f"\nTerminal size: {width}x{height}")


if __name__ == "__main__":
    print("=" * 60)
    print("TUI Components Tests")
    print("=" * 60)
    test_draw_box()
    test_draw_menu()
    test_draw_tree()
    test_terminal_size()
    print("\nAll tests passed!")
