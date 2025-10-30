//! Production-ready library demonstrating best practices
//!
//! A complete text processing library with:
//! - Input validation
//! - Error handling
//! - Performance optimization
//! - Comprehensive API
//! - Documentation
//! - Tests

use pyo3::exceptions::{PyTypeError, PyValueError};
use pyo3::prelude::*;
use std::collections::HashMap;

/// Text statistics
#[pyclass]
#[derive(Clone)]
pub struct TextStats {
    #[pyo3(get)]
    pub char_count: usize,
    #[pyo3(get)]
    pub word_count: usize,
    #[pyo3(get)]
    pub line_count: usize,
    #[pyo3(get)]
    pub avg_word_length: f64,
    #[pyo3(get)]
    pub unique_words: usize,
}

#[pymethods]
impl TextStats {
    fn __repr__(&self) -> String {
        format!(
            "TextStats(chars={}, words={}, lines={}, avg_word_len={:.2})",
            self.char_count, self.word_count, self.line_count, self.avg_word_length
        )
    }
}

/// Main text processor class
#[pyclass]
pub struct TextProcessor {
    text: String,
    case_sensitive: bool,
}

#[pymethods]
impl TextProcessor {
    #[new]
    #[pyo3(signature = (text, case_sensitive=false))]
    fn new(text: String, case_sensitive: bool) -> PyResult<Self> {
        if text.is_empty() {
            return Err(PyValueError::new_err("Text cannot be empty"));
        }
        Ok(TextProcessor { text, case_sensitive })
    }

    /// Get text statistics
    fn stats(&self) -> TextStats {
        let words: Vec<&str> = self.text.split_whitespace().collect();
        let unique: std::collections::HashSet<String> = words
            .iter()
            .map(|w| {
                if self.case_sensitive {
                    w.to_string()
                } else {
                    w.to_lowercase()
                }
            })
            .collect();

        let total_word_len: usize = words.iter().map(|w| w.len()).sum();
        let avg_word_length = if words.is_empty() {
            0.0
        } else {
            total_word_len as f64 / words.len() as f64
        };

        TextStats {
            char_count: self.text.len(),
            word_count: words.len(),
            line_count: self.text.lines().count(),
            avg_word_length,
            unique_words: unique.len(),
        }
    }

    /// Count word occurrences
    fn word_frequency(&self) -> HashMap<String, usize> {
        let mut freq: HashMap<String, usize> = HashMap::new();
        for word in self.text.split_whitespace() {
            let key = if self.case_sensitive {
                word.to_string()
            } else {
                word.to_lowercase()
            };
            *freq.entry(key).or_insert(0) += 1;
        }
        freq
    }

    /// Find most common words
    fn most_common(&self, n: usize) -> Vec<(String, usize)> {
        let mut freq: Vec<(String, usize)> = self.word_frequency().into_iter().collect();
        freq.sort_by(|a, b| b.1.cmp(&a.1));
        freq.into_iter().take(n).collect()
    }

    /// Search for a pattern
    fn find_all(&self, pattern: &str) -> Vec<usize> {
        let search_text = if self.case_sensitive {
            self.text.clone()
        } else {
            self.text.to_lowercase()
        };
        let search_pattern = if self.case_sensitive {
            pattern.to_string()
        } else {
            pattern.to_lowercase()
        };

        search_text
            .match_indices(&search_pattern)
            .map(|(i, _)| i)
            .collect()
    }

    /// Replace pattern
    fn replace_all(&self, pattern: &str, replacement: &str) -> String {
        if self.case_sensitive {
            self.text.replace(pattern, replacement)
        } else {
            // Simple case-insensitive replace
            let lower_text = self.text.to_lowercase();
            let lower_pattern = pattern.to_lowercase();
            let mut result = String::new();
            let mut last_end = 0;

            for (start, _) in lower_text.match_indices(&lower_pattern) {
                result.push_str(&self.text[last_end..start]);
                result.push_str(replacement);
                last_end = start + pattern.len();
            }
            result.push_str(&self.text[last_end..]);
            result
        }
    }

    /// Extract sentences
    fn sentences(&self) -> Vec<String> {
        self.text
            .split(&['.', '!', '?'][..])
            .map(|s| s.trim().to_string())
            .filter(|s| !s.is_empty())
            .collect()
    }

    /// Get text preview
    fn preview(&self, max_chars: usize) -> String {
        if self.text.len() <= max_chars {
            self.text.clone()
        } else {
            format!("{}...", &self.text[..max_chars])
        }
    }
}

/// Standalone utility functions

#[pyfunction]
/// Count words in text
fn count_words(text: &str) -> usize {
    text.split_whitespace().count()
}

#[pyfunction]
/// Reverse text
fn reverse_text(text: &str) -> String {
    text.chars().rev().collect()
}

#[pyfunction]
/// Check if text is palindrome
fn is_palindrome(text: &str) -> bool {
    let cleaned: String = text
        .chars()
        .filter(|c| c.is_alphanumeric())
        .map(|c| c.to_lowercase().next().unwrap())
        .collect();
    cleaned == cleaned.chars().rev().collect::<String>()
}

#[pyfunction]
/// Calculate reading time (words per minute)
#[pyo3(signature = (text, wpm=200))]
fn reading_time(text: &str, wpm: usize) -> f64 {
    let words = count_words(text);
    words as f64 / wpm as f64
}

#[pyfunction]
/// Truncate text to max words
fn truncate(text: &str, max_words: usize) -> String {
    let words: Vec<&str> = text.split_whitespace().take(max_words).collect();
    words.join(" ")
}

#[pyfunction]
/// Extract URLs from text (simple pattern)
fn extract_urls(text: &str) -> Vec<String> {
    text.split_whitespace()
        .filter(|word| word.starts_with("http://") || word.starts_with("https://"))
        .map(|s| s.to_string())
        .collect()
}

#[pymodule]
fn production_library(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add("__version__", "0.1.0")?;
    m.add_class::<TextStats>()?;
    m.add_class::<TextProcessor>()?;
    m.add_function(wrap_pyfunction!(count_words, m)?)?;
    m.add_function(wrap_pyfunction!(reverse_text, m)?)?;
    m.add_function(wrap_pyfunction!(is_palindrome, m)?)?;
    m.add_function(wrap_pyfunction!(reading_time, m)?)?;
    m.add_function(wrap_pyfunction!(truncate, m)?)?;
    m.add_function(wrap_pyfunction!(extract_urls, m)?)?;
    Ok(())
}
