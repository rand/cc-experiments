use pyo3::prelude::*;

/// ANSI color codes
const RESET: &str = "\x1b[0m";
const BOLD: &str = "\x1b[1m";
const DIM: &str = "\x1b[2m";
const ITALIC: &str = "\x1b[3m";
const UNDERLINE: &str = "\x1b[4m";

/// Apply color to text using ANSI codes
///
/// # Arguments
/// * `text` - Text to colorize
/// * `color` - Color name (red, green, blue, yellow, magenta, cyan, white, black)
/// * `bold` - Make text bold
/// * `background` - Apply as background color
///
/// # Returns
/// Colored text with ANSI codes
#[pyfunction]
fn colorize(
    text: String,
    color: String,
    bold: bool,
    background: bool,
) -> PyResult<String> {
    let color_code = match color.to_lowercase().as_str() {
        "red" => if background { "41" } else { "31" },
        "green" => if background { "42" } else { "32" },
        "yellow" => if background { "43" } else { "33" },
        "blue" => if background { "44" } else { "34" },
        "magenta" => if background { "45" } else { "35" },
        "cyan" => if background { "46" } else { "36" },
        "white" => if background { "47" } else { "37" },
        "black" => if background { "40" } else { "30" },
        _ => return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
            format!("Unknown color: {}", color)
        )),
    };

    let bold_code = if bold { BOLD } else { "" };

    Ok(format!("{}\x1b[{}m{}{}", bold_code, color_code, text, RESET))
}

/// Apply RGB color to text (24-bit color)
///
/// # Arguments
/// * `text` - Text to colorize
/// * `r` - Red component (0-255)
/// * `g` - Green component (0-255)
/// * `b` - Blue component (0-255)
/// * `background` - Apply as background color
#[pyfunction]
fn colorize_rgb(
    text: String,
    r: u8,
    g: u8,
    b: u8,
    background: bool,
) -> String {
    let prefix = if background { 48 } else { 38 };
    format!("\x1b[{};2;{};{};{}m{}{}", prefix, r, g, b, text, RESET)
}

/// Apply text styling
///
/// # Arguments
/// * `text` - Text to style
/// * `style` - Style name (bold, dim, italic, underline)
#[pyfunction]
fn stylize(text: String, style: String) -> PyResult<String> {
    let style_code = match style.to_lowercase().as_str() {
        "bold" => BOLD,
        "dim" => DIM,
        "italic" => ITALIC,
        "underline" => UNDERLINE,
        _ => return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
            format!("Unknown style: {}", style)
        )),
    };

    Ok(format!("{}{}{}", style_code, text, RESET))
}

/// Create a formatted message with status indicator
///
/// # Arguments
/// * `status` - Status type (success, error, warning, info)
/// * `message` - Message text
#[pyfunction]
fn format_status(status: String, message: String) -> PyResult<String> {
    let (icon, color) = match status.to_lowercase().as_str() {
        "success" => ("✓", "green"),
        "error" => ("✗", "red"),
        "warning" => ("⚠", "yellow"),
        "info" => ("ℹ", "blue"),
        _ => return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
            format!("Unknown status: {}", status)
        )),
    };

    let colored_icon = colorize(icon.to_string(), color.to_string(), true, false)?;
    Ok(format!("{} {}", colored_icon, message))
}

/// Create a formatted table row
///
/// # Arguments
/// * `columns` - Column values
/// * `widths` - Column widths
/// * `color` - Optional color for the row
#[pyfunction]
fn format_table_row(
    columns: Vec<String>,
    widths: Vec<usize>,
    color: Option<String>,
) -> PyResult<String> {
    if columns.len() != widths.len() {
        return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
            "Columns and widths must have same length"
        ));
    }

    let formatted_cols: Vec<String> = columns
        .iter()
        .zip(widths.iter())
        .map(|(col, width)| {
            let padded = format!("{:<width$}", col, width = width);
            if let Some(ref c) = color {
                colorize(padded, c.clone(), false, false).unwrap_or(padded)
            } else {
                padded
            }
        })
        .collect();

    Ok(formatted_cols.join(" │ "))
}

/// Create a horizontal separator line
#[pyfunction]
fn format_separator(width: usize, style: String) -> PyResult<String> {
    let char = match style.as_str() {
        "single" => "─",
        "double" => "═",
        "thick" => "━",
        "dotted" => "┈",
        _ => return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
            format!("Unknown style: {}", style)
        )),
    };

    Ok(char.repeat(width))
}

/// Strip ANSI codes from text
#[pyfunction]
fn strip_ansi(text: String) -> String {
    let re = regex::Regex::new(r"\x1b\[[0-9;]*m").unwrap();
    re.replace_all(&text, "").to_string()
}

/// Get visible length of text (excluding ANSI codes)
#[pyfunction]
fn visible_length(text: String) -> usize {
    strip_ansi(text).len()
}

#[pymodule]
fn terminal_colors(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(colorize, m)?)?;
    m.add_function(wrap_pyfunction!(colorize_rgb, m)?)?;
    m.add_function(wrap_pyfunction!(stylize, m)?)?;
    m.add_function(wrap_pyfunction!(format_status, m)?)?;
    m.add_function(wrap_pyfunction!(format_table_row, m)?)?;
    m.add_function(wrap_pyfunction!(format_separator, m)?)?;
    m.add_function(wrap_pyfunction!(strip_ansi, m)?)?;
    m.add_function(wrap_pyfunction!(visible_length, m)?)?;
    Ok(())
}
