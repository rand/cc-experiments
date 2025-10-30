# Example 08: Interactive Prompts

User input handling with validation, password input, confirmations, and selections.

## Features
- Text prompts
- Hidden password input
- Yes/no confirmation
- Single/multi-select menus
- Integer input with validation

## Usage
```python
import interactive_prompts

name = interactive_prompts.prompt("Enter name: ")
password = interactive_prompts.prompt_password("Password: ")
if interactive_prompts.confirm("Continue?", True):
    choice = interactive_prompts.select("Pick one:", ["A", "B", "C"])
```

## Next Steps
- Example 09: TUI components
