use pyo3::prelude::*;
use std::io::{self, Write};

/// Box drawing characters
const BOX_CHARS: &[(&str, &str, &str, &str, &str, &str)] = &[
    ("┌", "─", "┐", "│", "└", "┘"), // light
    ("╔", "═", "╗", "║", "╚", "╝"), // heavy
    ("+", "-", "+", "|", "+", "+"), // ascii
];

/// Draw a box around text
#[pyfunction]
fn draw_box(
    title: String,
    content: Vec<String>,
    width: usize,
    style: String,
) -> PyResult<Vec<String>> {
    let box_style = match style.as_str() {
        "light" => BOX_CHARS[0],
        "heavy" => BOX_CHARS[1],
        "ascii" => BOX_CHARS[2],
        _ => return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>("Invalid style")),
    };

    let (tl, h, tr, v, bl, br) = box_style;

    let mut lines = Vec::new();

    // Top border with title
    let title_len = title.chars().count();
    let padding = if title_len < width - 4 {
        width - title_len - 4
    } else {
        0
    };

    let top = if !title.is_empty() {
        format!("{} {} {}{}", tl, title, h.repeat(padding), tr)
    } else {
        format!("{}{}{}", tl, h.repeat(width - 2), tr)
    };

    lines.push(top);

    // Content lines
    for line in content {
        let line_len = line.chars().count();
        let padding = if line_len < width - 4 {
            width - line_len - 4
        } else {
            0
        };

        lines.push(format!("{} {} {}{}", v, line, " ".repeat(padding), v));
    }

    // Bottom border
    lines.push(format!("{}{}{}", bl, h.repeat(width - 2), br));

    Ok(lines)
}

/// Create a menu
#[pyfunction]
fn draw_menu(title: String, items: Vec<String>, selected: usize) -> Vec<String> {
    let mut lines = vec![format!("┌─ {} ─┐", title)];

    for (i, item) in items.iter().enumerate() {
        let marker = if i == selected { "▶" } else { " " };
        lines.push(format!("│ {} {} │", marker, item));
    }

    lines.push("└────────┘".to_string());
    lines
}

/// Create a panel with title
#[pyfunction]
fn draw_panel(title: String, lines: Vec<String>, width: usize) -> Vec<String> {
    let mut output = Vec::new();

    // Title bar
    output.push(format!("╔═ {} ═╗", title));

    // Content
    for line in lines {
        let padded = format!("{:<width$}", line, width = width - 4);
        output.push(format!("║ {} ║", padded));
    }

    // Bottom
    output.push(format!("╚{}╝", "═".repeat(width - 2)));

    output
}

/// Create a tree structure
#[pyfunction]
fn draw_tree(root: String, children: Vec<(String, Vec<String>)>) -> Vec<String> {
    let mut lines = Vec::new();

    lines.push(root);

    for (i, (branch, sub_items)) in children.iter().enumerate() {
        let is_last = i == children.len() - 1;
        let prefix = if is_last { "└─" } else { "├─" };
        let sub_prefix = if is_last { "  " } else { "│ " };

        lines.push(format!("{} {}", prefix, branch));

        for (j, item) in sub_items.iter().enumerate() {
            let is_sub_last = j == sub_items.len() - 1;
            let sub_marker = if is_sub_last { "└─" } else { "├─" };

            lines.push(format!("{}  {} {}", sub_prefix, sub_marker, item));
        }
    }

    lines
}

/// Clear the terminal screen
#[pyfunction]
fn clear_screen() {
    print!("\x1B[2J\x1B[H");
    io::stdout().flush().unwrap();
}

/// Move cursor to position
#[pyfunction]
fn move_cursor(row: usize, col: usize) {
    print!("\x1B[{};{}H", row, col);
    io::stdout().flush().unwrap();
}

/// Hide/show cursor
#[pyfunction]
fn set_cursor_visibility(visible: bool) {
    if visible {
        print!("\x1B[?25h");
    } else {
        print!("\x1B[?25l");
    }
    io::stdout().flush().unwrap();
}

/// Get terminal size
#[pyfunction]
fn get_terminal_size() -> (usize, usize) {
    if let Some((width, height)) = term_size::dimensions() {
        (width, height)
    } else {
        (80, 24) // Default fallback
    }
}

#[pymodule]
fn tui_components(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(draw_box, m)?)?;
    m.add_function(wrap_pyfunction!(draw_menu, m)?)?;
    m.add_function(wrap_pyfunction!(draw_panel, m)?)?;
    m.add_function(wrap_pyfunction!(draw_tree, m)?)?;
    m.add_function(wrap_pyfunction!(clear_screen, m)?)?;
    m.add_function(wrap_pyfunction!(move_cursor, m)?)?;
    m.add_function(wrap_pyfunction!(set_cursor_visibility, m)?)?;
    m.add_function(wrap_pyfunction!(get_terminal_size, m)?)?;
    Ok(())
}
