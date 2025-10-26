---
name: tui-best-practices
description: Designing terminal user interfaces
---



# TUI Best Practices

**Use this skill when:**
- Designing terminal user interfaces
- Creating accessible TUIs
- Optimizing TUI performance
- Implementing keyboard navigation
- Building cross-platform TUIs

## Keyboard Shortcuts

Use consistent, discoverable shortcuts:

```
Standard Conventions:
- q / Ctrl+C: Quit
- h/j/k/l or arrows: Navigate
- Enter: Select/Confirm
- Esc: Cancel/Back
- /: Search
- ?: Help
- Tab: Next field
- Shift+Tab: Previous field
```

## Layout Design

```
Principles:
- Clear visual hierarchy
- Consistent spacing
- Meaningful borders
- Status information visible
- Help text always available
```

## Performance

```
Optimization:
- Limit redraws (only when state changes)
- Use double buffering
- Batch terminal updates
- Cache rendered content
- Throttle high-frequency events
```

## Accessibility

```
Guidelines:
- Support screen readers
- High contrast colors
- Keyboard-only navigation
- Clear focus indicators
- Avoid color-only information
```

## Error Handling

```
Best Practices:
- Show errors inline
- Provide actionable messages
- Don't crash on terminal resize
- Handle missing terminal features
- Graceful degradation
```

## Related Skills

- **bubbletea-architecture.md** - Go TUI patterns
- **ratatui-architecture.md** - Rust TUI patterns
