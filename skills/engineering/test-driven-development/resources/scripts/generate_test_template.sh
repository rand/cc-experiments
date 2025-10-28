#!/usr/bin/env bash
#
# Generate Test Template
#
# Generates test file templates for new features following TDD best practices.
# Supports multiple languages and testing frameworks with customizable templates.
#
# Features:
# - Language-specific test templates (Python, TypeScript, Rust, Go)
# - Framework detection and template selection
# - Arrange-Act-Assert structure
# - Parameterized test examples
# - Fixture/setup boilerplate
# - BDD-style templates (Given-When-Then)
#
# Usage:
#   generate_test_template.sh python MyClass        # Python unittest
#   generate_test_template.sh typescript MyComponent # TypeScript/Jest
#   generate_test_template.sh rust my_module        # Rust tests
#   generate_test_template.sh go MyStruct           # Go tests
#   generate_test_template.sh --help

set -euo pipefail

VERSION="1.0.0"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
LANGUAGE=""
NAME=""
FRAMEWORK=""
STYLE="aaa"  # arrange-act-assert or bdd
OUTPUT_DIR=""
DRY_RUN=false

usage() {
    cat << EOF
Generate Test Template v${VERSION}

Generate test file templates for TDD following best practices.

Usage:
    $(basename "$0") LANGUAGE NAME [OPTIONS]

Languages:
    python          Python test files (pytest or unittest)
    typescript      TypeScript test files (Jest or Vitest)
    javascript      JavaScript test files (Jest)
    rust            Rust test files
    go              Go test files

Options:
    --framework FRAMEWORK   Specify testing framework
    --style STYLE          Test style: aaa (arrange-act-assert) or bdd (given-when-then)
    --output-dir DIR       Output directory (default: current directory)
    --dry-run              Show template without creating file
    --help                 Show this help message
    --json                 Output metadata as JSON

Examples:
    # Python with pytest
    $(basename "$0") python Calculator --framework pytest

    # TypeScript with Jest
    $(basename "$0") typescript UserService --framework jest

    # BDD style test
    $(basename "$0") python OrderProcessor --style bdd

    # Rust module tests
    $(basename "$0") rust string_utils

    # Go table-driven tests
    $(basename "$0") go Validator
EOF
}

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

generate_python_pytest() {
    local name=$1
    local style=$2
    local filename="test_${name,,}.py"

    if [[ "$style" == "bdd" ]]; then
        cat << EOF
"""
Tests for ${name}

BDD-style tests using Given-When-Then pattern.
"""

import pytest
from ${name,,} import ${name}


class Describe${name}:
    """${name} behavior specification"""

    def test_when_created_then_has_default_state(self):
        """
        Given: No preconditions
        When: ${name} is created
        Then: It should have default state
        """
        # When
        instance = ${name}()

        # Then
        assert instance is not None
        # TODO: Add specific assertions

    def test_given_valid_input_when_processing_then_returns_expected_result(self):
        """
        Given: A ${name} instance with valid input
        When: Processing the input
        Then: Should return expected result
        """
        # Given
        instance = ${name}()
        valid_input = "test_input"

        # When
        result = instance.process(valid_input)

        # Then
        assert result is not None
        # TODO: Add specific assertions

    def test_given_invalid_input_when_processing_then_raises_error(self):
        """
        Given: A ${name} instance with invalid input
        When: Processing the input
        Then: Should raise ValueError
        """
        # Given
        instance = ${name}()
        invalid_input = None

        # When/Then
        with pytest.raises(ValueError):
            instance.process(invalid_input)


@pytest.mark.parametrize("input,expected", [
    ("input1", "expected1"),
    ("input2", "expected2"),
    # TODO: Add more test cases
])
def test_${name,,}_with_various_inputs(input, expected):
    """Test ${name} with parameterized inputs"""
    instance = ${name}()
    result = instance.process(input)
    assert result == expected


@pytest.fixture
def ${name,,}_instance():
    """Fixture providing a ${name} instance"""
    instance = ${name}()
    # TODO: Add setup
    yield instance
    # TODO: Add teardown if needed


def test_using_fixture(${name,,}_instance):
    """Test using fixture"""
    # Arrange
    # (instance provided by fixture)

    # Act
    result = ${name,,}_instance.some_method()

    # Assert
    assert result is not None
EOF
    else
        cat << EOF
"""
Tests for ${name}

Unit tests following Arrange-Act-Assert pattern.
"""

import pytest
from ${name,,} import ${name}


class Test${name}:
    """Test suite for ${name}"""

    def test_initialization(self):
        """Test ${name} can be initialized"""
        # Arrange
        # (no preconditions)

        # Act
        instance = ${name}()

        # Assert
        assert instance is not None
        # TODO: Add specific assertions about initial state

    def test_basic_functionality(self):
        """Test basic functionality of ${name}"""
        # Arrange
        instance = ${name}()
        test_input = "test_value"

        # Act
        result = instance.process(test_input)

        # Assert
        assert result is not None
        # TODO: Add specific assertions about the result

    def test_error_handling(self):
        """Test ${name} handles errors appropriately"""
        # Arrange
        instance = ${name}()
        invalid_input = None

        # Act & Assert
        with pytest.raises(ValueError):
            instance.process(invalid_input)

    @pytest.mark.parametrize("input,expected", [
        ("case1", "result1"),
        ("case2", "result2"),
        ("case3", "result3"),
    ])
    def test_multiple_cases(self, input, expected):
        """Test ${name} with multiple input cases"""
        # Arrange
        instance = ${name}()

        # Act
        result = instance.process(input)

        # Assert
        assert result == expected


@pytest.fixture
def ${name,,}():
    """Fixture providing a configured ${name} instance"""
    instance = ${name}()
    # TODO: Configure instance as needed
    yield instance
    # TODO: Cleanup if needed


def test_with_fixture(${name,,}):
    """Test using fixture"""
    # Arrange
    test_data = "test"

    # Act
    result = ${name,,}.process(test_data)

    # Assert
    assert result is not None
EOF
    fi

    echo "$filename"
}

generate_typescript_jest() {
    local name=$1
    local style=$2
    local filename="${name}.test.ts"

    if [[ "$style" == "bdd" ]]; then
        cat << EOF
/**
 * Tests for ${name}
 * BDD-style tests using Given-When-Then pattern
 */

import { ${name} } from './${name}';

describe('${name}', () => {
    describe('when created', () => {
        it('should have default state', () => {
            // When
            const instance = new ${name}();

            // Then
            expect(instance).toBeDefined();
            // TODO: Add specific expectations
        });
    });

    describe('given valid input', () => {
        it('should process and return expected result', () => {
            // Given
            const instance = new ${name}();
            const validInput = 'test';

            // When
            const result = instance.process(validInput);

            // Then
            expect(result).toBeDefined();
            // TODO: Add specific expectations
        });
    });

    describe('given invalid input', () => {
        it('should throw error', () => {
            // Given
            const instance = new ${name}();
            const invalidInput = null;

            // When/Then
            expect(() => {
                instance.process(invalidInput);
            }).toThrow();
        });
    });
});

describe.each([
    ['input1', 'expected1'],
    ['input2', 'expected2'],
    // TODO: Add more cases
])('${name} with %s', (input, expected) => {
    it(\`should return \${expected}\`, () => {
        const instance = new ${name}();
        const result = instance.process(input);
        expect(result).toBe(expected);
    });
});
EOF
    else
        cat << EOF
/**
 * Tests for ${name}
 * Arrange-Act-Assert pattern
 */

import { ${name} } from './${name}';

describe('${name}', () => {
    let instance: ${name};

    beforeEach(() => {
        // Arrange: Create fresh instance for each test
        instance = new ${name}();
    });

    it('should be created', () => {
        // Assert
        expect(instance).toBeDefined();
    });

    it('should process input correctly', () => {
        // Arrange
        const input = 'test';

        // Act
        const result = instance.process(input);

        // Assert
        expect(result).toBeDefined();
        // TODO: Add specific expectations
    });

    it('should handle errors', () => {
        // Arrange
        const invalidInput = null;

        // Act & Assert
        expect(() => {
            instance.process(invalidInput);
        }).toThrow();
    });

    describe('with various inputs', () => {
        it.each([
            ['input1', 'expected1'],
            ['input2', 'expected2'],
            // TODO: Add more test cases
        ])('should return %s for %s', (input, expected) => {
            // Act
            const result = instance.process(input);

            // Assert
            expect(result).toBe(expected);
        });
    });
});

describe('${name} integration', () => {
    it('should work with real dependencies', () => {
        // Arrange
        const instance = new ${name}();
        // TODO: Setup dependencies

        // Act
        const result = instance.complexOperation();

        // Assert
        expect(result).toBeDefined();
    });
});
EOF
    fi

    echo "$filename"
}

generate_rust_tests() {
    local name=$1
    local filename="${name}.rs"

    cat << EOF
//! Tests for ${name}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_${name,,}_creation() {
        // Arrange & Act
        let instance = ${name}::new();

        // Assert
        assert!(instance.is_valid());
    }

    #[test]
    fn test_${name,,}_basic_functionality() {
        // Arrange
        let mut instance = ${name}::new();
        let input = "test";

        // Act
        let result = instance.process(input);

        // Assert
        assert!(result.is_ok());
        // TODO: Add specific assertions
    }

    #[test]
    fn test_${name,,}_error_handling() {
        // Arrange
        let mut instance = ${name}::new();
        let invalid_input = "";

        // Act
        let result = instance.process(invalid_input);

        // Assert
        assert!(result.is_err());
    }

    #[test]
    #[should_panic(expected = "invalid input")]
    fn test_${name,,}_panics_on_invalid_input() {
        // Arrange
        let instance = ${name}::new();

        // Act (should panic)
        instance.process_or_panic("");
    }

    // Parameterized-style tests
    #[test]
    fn test_${name,,}_with_various_inputs() {
        let test_cases = vec![
            ("input1", "expected1"),
            ("input2", "expected2"),
            // TODO: Add more cases
        ];

        for (input, expected) in test_cases {
            // Arrange
            let instance = ${name}::new();

            // Act
            let result = instance.process(input).unwrap();

            // Assert
            assert_eq!(result, expected, "Failed for input: {}", input);
        }
    }

    // Property-based test example (requires proptest crate)
    // use proptest::prelude::*;
    //
    // proptest! {
    //     #[test]
    //     fn test_${name,,}_property(s in "\\\\PC*") {
    //         let instance = ${name}::new();
    //         let result = instance.process(&s);
    //         prop_assert!(result.is_ok());
    //     }
    // }
}
EOF

    echo "$filename"
}

generate_go_tests() {
    local name=$1
    local filename="${name,,}_test.go"

    cat << EOF
package main

import (
    "testing"
)

func Test${name}_Creation(t *testing.T) {
    // Arrange & Act
    instance := New${name}()

    // Assert
    if instance == nil {
        t.Fatal("expected ${name} instance, got nil")
    }
}

func Test${name}_BasicFunctionality(t *testing.T) {
    // Arrange
    instance := New${name}()
    input := "test"

    // Act
    result, err := instance.Process(input)

    // Assert
    if err != nil {
        t.Fatalf("unexpected error: %v", err)
    }
    if result == "" {
        t.Error("expected non-empty result")
    }
    // TODO: Add specific assertions
}

func Test${name}_ErrorHandling(t *testing.T) {
    // Arrange
    instance := New${name}()
    invalidInput := ""

    // Act
    _, err := instance.Process(invalidInput)

    // Assert
    if err == nil {
        t.Error("expected error for invalid input, got nil")
    }
}

// Table-driven tests (Go best practice)
func Test${name}_TableDriven(t *testing.T) {
    tests := []struct {
        name     string
        input    string
        expected string
        wantErr  bool
    }{
        {
            name:     "valid input 1",
            input:    "test1",
            expected: "result1",
            wantErr:  false,
        },
        {
            name:     "valid input 2",
            input:    "test2",
            expected: "result2",
            wantErr:  false,
        },
        {
            name:     "invalid input",
            input:    "",
            expected: "",
            wantErr:  true,
        },
        // TODO: Add more test cases
    }

    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            // Arrange
            instance := New${name}()

            // Act
            result, err := instance.Process(tt.input)

            // Assert
            if (err != nil) != tt.wantErr {
                t.Errorf("Process() error = %v, wantErr %v", err, tt.wantErr)
                return
            }
            if result != tt.expected {
                t.Errorf("Process() = %v, want %v", result, tt.expected)
            }
        })
    }
}

// Benchmark example
func Benchmark${name}_Process(b *testing.B) {
    instance := New${name}()
    input := "benchmark_input"

    b.ResetTimer()
    for i := 0; i < b.N; i++ {
        instance.Process(input)
    }
}
EOF

    echo "$filename"
}

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --framework)
                FRAMEWORK="$2"
                shift 2
                ;;
            --style)
                STYLE="$2"
                shift 2
                ;;
            --output-dir)
                OUTPUT_DIR="$2"
                shift 2
                ;;
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --help)
                usage
                exit 0
                ;;
            --json)
                OUTPUT_JSON=true
                shift
                ;;
            -*)
                log_error "Unknown option: $1"
                usage
                exit 1
                ;;
            *)
                if [[ -z "$LANGUAGE" ]]; then
                    LANGUAGE="$1"
                elif [[ -z "$NAME" ]]; then
                    NAME="$1"
                else
                    log_error "Unexpected argument: $1"
                    usage
                    exit 1
                fi
                shift
                ;;
        esac
    done
}

main() {
    parse_args "$@"

    if [[ -z "$LANGUAGE" ]] || [[ -z "$NAME" ]]; then
        log_error "LANGUAGE and NAME are required"
        usage
        exit 1
    fi

    # Convert language to lowercase
    LANGUAGE="${LANGUAGE,,}"

    # Generate template based on language
    case "$LANGUAGE" in
        python|py)
            if [[ -z "$FRAMEWORK" ]]; then
                FRAMEWORK="pytest"
            fi
            content=$(generate_python_pytest "$NAME" "$STYLE")
            ;;
        typescript|ts)
            if [[ -z "$FRAMEWORK" ]]; then
                FRAMEWORK="jest"
            fi
            content=$(generate_typescript_jest "$NAME" "$STYLE")
            ;;
        javascript|js)
            if [[ -z "$FRAMEWORK" ]]; then
                FRAMEWORK="jest"
            fi
            content=$(generate_typescript_jest "$NAME" "$STYLE")
            ;;
        rust|rs)
            content=$(generate_rust_tests "$NAME")
            ;;
        go|golang)
            content=$(generate_go_tests "$NAME")
            ;;
        *)
            log_error "Unsupported language: $LANGUAGE"
            log_error "Supported: python, typescript, javascript, rust, go"
            exit 1
            ;;
    esac

    # Determine output file
    if [[ -n "$OUTPUT_DIR" ]]; then
        output_file="$OUTPUT_DIR/$(basename "$content")"
    else
        output_file="$content"
    fi

    # Read the template content (it's the filename, we need to regenerate)
    template=""
    case "$LANGUAGE" in
        python|py)
            template=$(generate_python_pytest "$NAME" "$STYLE" | tail -n +2)
            ;;
        typescript|ts|javascript|js)
            template=$(generate_typescript_jest "$NAME" "$STYLE" | tail -n +2)
            ;;
        rust|rs)
            template=$(generate_rust_tests "$NAME" | tail -n +2)
            ;;
        go|golang)
            template=$(generate_go_tests "$NAME" | tail -n +2)
            ;;
    esac

    if [[ "$DRY_RUN" == true ]]; then
        log_info "Dry run - would create: $output_file"
        echo "$template"
    else
        # Create output directory if needed
        if [[ -n "$OUTPUT_DIR" ]]; then
            mkdir -p "$OUTPUT_DIR"
        fi

        # Check if file exists
        if [[ -f "$output_file" ]]; then
            log_warn "File already exists: $output_file"
            read -p "Overwrite? (y/n) " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                log_info "Aborted"
                exit 0
            fi
        fi

        # Write file
        echo "$template" > "$output_file"
        log_success "Created test file: $output_file"

        # Output JSON metadata if requested
        if [[ "${OUTPUT_JSON:-false}" == true ]]; then
            cat << EOF
{
  "file": "$output_file",
  "language": "$LANGUAGE",
  "framework": "$FRAMEWORK",
  "style": "$STYLE",
  "name": "$NAME"
}
EOF
        fi
    fi
}

main "$@"
