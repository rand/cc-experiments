use pyo3::prelude::*;
use std::io::{self, Write};

/// Read a line of input from the user
#[pyfunction]
fn prompt(message: String) -> PyResult<String> {
    print!("{}", message);
    io::stdout().flush()?;

    let mut input = String::new();
    io::stdin().read_line(&mut input)?;

    Ok(input.trim().to_string())
}

/// Read a password (hidden input)
#[pyfunction]
fn prompt_password(message: String) -> PyResult<String> {
    print!("{}", message);
    io::stdout().flush()?;

    let password = rpassword::read_password().map_err(|e| {
        PyErr::new::<pyo3::exceptions::PyIOError, _>(format!("Failed to read password: {}", e))
    })?;

    Ok(password)
}

/// Confirm with yes/no prompt
#[pyfunction]
fn confirm(message: String, default: Option<bool>) -> PyResult<bool> {
    let suffix = match default {
        Some(true) => " [Y/n]: ",
        Some(false) => " [y/N]: ",
        None => " [y/n]: ",
    };

    print!("{}{}", message, suffix);
    io::stdout().flush()?;

    let mut input = String::new();
    io::stdin().read_line(&mut input)?;

    let trimmed = input.trim().to_lowercase();

    Ok(match trimmed.as_str() {
        "" => default.unwrap_or(false),
        "y" | "yes" => true,
        "n" | "no" => false,
        _ => default.unwrap_or(false),
    })
}

/// Select from a list of options
#[pyfunction]
fn select(message: String, options: Vec<String>) -> PyResult<usize> {
    println!("{}", message);

    for (i, option) in options.iter().enumerate() {
        println!("  {}. {}", i + 1, option);
    }

    print!("Enter choice (1-{}): ", options.len());
    io::stdout().flush()?;

    let mut input = String::new();
    io::stdin().read_line(&mut input)?;

    let choice: usize = input.trim().parse().map_err(|_| {
        PyErr::new::<pyo3::exceptions::PyValueError, _>("Invalid number")
    })?;

    if choice < 1 || choice > options.len() {
        return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
            "Choice out of range"
        ));
    }

    Ok(choice - 1)
}

/// Multi-select from options
#[pyfunction]
fn multiselect(message: String, options: Vec<String>) -> PyResult<Vec<usize>> {
    println!("{}", message);
    println!("(Enter numbers separated by commas, e.g., 1,3,5)");

    for (i, option) in options.iter().enumerate() {
        println!("  {}. {}", i + 1, option);
    }

    print!("Enter choices: ");
    io::stdout().flush()?;

    let mut input = String::new();
    io::stdin().read_line(&mut input)?;

    let choices: Result<Vec<usize>, _> = input
        .trim()
        .split(',')
        .map(|s| s.trim().parse::<usize>())
        .collect();

    let choices = choices.map_err(|_| {
        PyErr::new::<pyo3::exceptions::PyValueError, _>("Invalid number format")
    })?;

    // Validate and convert to 0-indexed
    let mut indices = Vec::new();
    for choice in choices {
        if choice < 1 || choice > options.len() {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                "Choice out of range"
            ));
        }
        indices.push(choice - 1);
    }

    Ok(indices)
}

/// Prompt for integer input
#[pyfunction]
fn prompt_int(message: String, min: Option<i64>, max: Option<i64>) -> PyResult<i64> {
    loop {
        let range_msg = match (min, max) {
            (Some(mn), Some(mx)) => format!(" ({}-{})", mn, mx),
            (Some(mn), None) => format!(" (>= {})", mn),
            (None, Some(mx)) => format!(" (<= {})", mx),
            (None, None) => String::new(),
        };

        print!("{}{}: ", message, range_msg);
        io::stdout().flush()?;

        let mut input = String::new();
        io::stdin().read_line(&mut input)?;

        match input.trim().parse::<i64>() {
            Ok(num) => {
                if let Some(mn) = min {
                    if num < mn {
                        println!("Value must be >= {}", mn);
                        continue;
                    }
                }

                if let Some(mx) = max {
                    if num > mx {
                        println!("Value must be <= {}", mx);
                        continue;
                    }
                }

                return Ok(num);
            }
            Err(_) => {
                println!("Please enter a valid number");
                continue;
            }
        }
    }
}

#[pymodule]
fn interactive_prompts(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(prompt, m)?)?;
    m.add_function(wrap_pyfunction!(prompt_password, m)?)?;
    m.add_function(wrap_pyfunction!(confirm, m)?)?;
    m.add_function(wrap_pyfunction!(select, m)?)?;
    m.add_function(wrap_pyfunction!(multiselect, m)?)?;
    m.add_function(wrap_pyfunction!(prompt_int, m)?)?;
    Ok(())
}
