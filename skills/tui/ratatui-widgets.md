---
name: ratatui-widgets
description: Using Ratatui's built-in widgets
---



# Ratatui Widgets

**Use this skill when:**
- Using Ratatui's built-in widgets
- Building complex layouts
- Rendering tables, lists, and charts
- Creating responsive TUI designs

## Common Widgets

```rust
use ratatui::{
    layout::{Constraint, Direction, Layout},
    widgets::{Block, Borders, List, ListItem, Paragraph, Table, Row, Cell},
};

fn ui(f: &mut Frame, app: &App) {
    let chunks = Layout::default()
        .direction(Direction::Vertical)
        .constraints([
            Constraint::Length(3),
            Constraint::Min(0),
        ])
        .split(f.size());

    // Paragraph
    let paragraph = Paragraph::new("Hello, world!")
        .block(Block::default().title("Title").borders(Borders::ALL));
    f.render_widget(paragraph, chunks[0]);

    // List
    let items: Vec<ListItem> = app.items
        .iter()
        .map(|i| ListItem::new(i.as_str()))
        .collect();

    let list = List::new(items)
        .block(Block::default().title("List").borders(Borders::ALL))
        .highlight_style(Style::default().bg(Color::Gray));

    f.render_widget(list, chunks[1]);
}
```

## Table Widget

```rust
use ratatui::widgets::{Table, Row, Cell};

let rows = vec![
    Row::new(vec!["Name", "Age", "City"]),
    Row::new(vec!["Alice", "30", "NYC"]),
    Row::new(vec!["Bob", "25", "SF"]),
];

let table = Table::new(rows)
    .block(Block::default().title("Table").borders(Borders::ALL))
    .widths(&[
        Constraint::Percentage(40),
        Constraint::Percentage(20),
        Constraint::Percentage(40),
    ]);

f.render_widget(table, area);
```

## Related Skills

- **ratatui-architecture.md** - Core architecture patterns
- **tui-best-practices.md** - Design guidelines
