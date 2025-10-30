# Example 09: TUI Components

Terminal UI components including boxes, menus, panels, and trees.

## Features
- Box drawing (multiple styles)
- Interactive menus
- Panels with titles
- Tree structures
- Cursor control
- Terminal size detection

## Usage
```python
import tui_components

# Draw a box
box = tui_components.draw_box("Title", ["Content"], 40, "light")
for line in box:
    print(line)

# Create a menu
menu = tui_components.draw_menu("Options", ["A", "B"], 0)

# Draw a tree
tree = tui_components.draw_tree("Root", [("Branch", ["Leaf"])])
```

## Next Steps
- Example 10: Production CLI tool
