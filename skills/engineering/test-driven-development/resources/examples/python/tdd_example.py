"""
TDD Example: String Calculator Kata

This example demonstrates Test-Driven Development with the classic
String Calculator kata. Shows the progression from Red to Green to Refactor.

Before TDD: No tests, implementation-first approach
After TDD: Test-first, iterative development with continuous refactoring
"""

# ============================================================================
# BEFORE TDD: Implementation without tests
# ============================================================================

class StringCalculatorBeforeTDD:
    """String calculator implemented without TDD - harder to test, brittle"""

    def add(self, numbers: str) -> int:
        """Add numbers in a comma-separated string"""
        if not numbers:
            return 0

        # Complex logic all at once, hard to understand
        result = 0
        parts = numbers.split(',')
        for part in parts:
            try:
                num = int(part.strip())
                if num < 0:
                    raise ValueError(f"negatives not allowed: {num}")
                if num <= 1000:
                    result += num
            except ValueError as e:
                if "negatives not allowed" in str(e):
                    raise
                continue

        return result


# ============================================================================
# AFTER TDD: Test-driven implementation
# ============================================================================

import pytest


# ======================
# ITERATION 1: RED PHASE
# ======================
# Test: Empty string returns 0

def test_empty_string_returns_zero():
    """Given empty string, when add called, then returns 0"""
    calc = StringCalculator()
    assert calc.add("") == 0


# ======================
# ITERATION 1: GREEN PHASE
# ======================

class StringCalculator:
    """String calculator built with TDD"""

    def add(self, numbers: str) -> int:
        if not numbers:
            return 0
        return 0  # Simplest implementation


# ======================
# ITERATION 2: RED PHASE
# ======================
# Test: Single number returns that number

def test_single_number_returns_value():
    """Given single number, when add called, then returns that number"""
    calc = StringCalculator()
    assert calc.add("1") == 1
    assert calc.add("5") == 5


# ======================
# ITERATION 2: GREEN PHASE
# ======================

class StringCalculator:
    """String calculator built with TDD"""

    def add(self, numbers: str) -> int:
        if not numbers:
            return 0
        return int(numbers)


# ======================
# ITERATION 3: RED PHASE
# ======================
# Test: Two numbers separated by comma

def test_two_numbers_returns_sum():
    """Given two comma-separated numbers, when add called, then returns sum"""
    calc = StringCalculator()
    assert calc.add("1,2") == 3
    assert calc.add("5,10") == 15


# ======================
# ITERATION 3: GREEN PHASE
# ======================

class StringCalculator:
    """String calculator built with TDD"""

    def add(self, numbers: str) -> int:
        if not numbers:
            return 0

        parts = numbers.split(',')
        if len(parts) == 1:
            return int(parts[0])

        return int(parts[0]) + int(parts[1])


# ======================
# ITERATION 3: REFACTOR
# ======================
# Notice duplication, generalize the solution

class StringCalculator:
    """String calculator built with TDD"""

    def add(self, numbers: str) -> int:
        if not numbers:
            return 0

        return sum(int(n) for n in numbers.split(','))


# ======================
# ITERATION 4: RED PHASE
# ======================
# Test: Multiple numbers

def test_multiple_numbers_returns_sum():
    """Given multiple numbers, when add called, then returns sum"""
    calc = StringCalculator()
    assert calc.add("1,2,3") == 6
    assert calc.add("1,2,3,4,5") == 15


# ======================
# ITERATION 4: GREEN PHASE
# ======================
# Already passes! Refactoring paid off.


# ======================
# ITERATION 5: RED PHASE
# ======================
# Test: Newline as delimiter

def test_newline_delimiter():
    """Given newline delimiter, when add called, then returns sum"""
    calc = StringCalculator()
    assert calc.add("1\n2,3") == 6


# ======================
# ITERATION 5: GREEN PHASE
# ======================

class StringCalculator:
    """String calculator built with TDD"""

    def add(self, numbers: str) -> int:
        if not numbers:
            return 0

        # Replace newlines with commas
        numbers = numbers.replace('\n', ',')
        return sum(int(n) for n in numbers.split(','))


# ======================
# ITERATION 6: RED PHASE
# ======================
# Test: Negative numbers should raise exception

def test_negative_number_raises_exception():
    """Given negative number, when add called, then raises ValueError"""
    calc = StringCalculator()

    with pytest.raises(ValueError, match="negatives not allowed: -1"):
        calc.add("-1,2")


# ======================
# ITERATION 6: GREEN PHASE
# ======================

class StringCalculator:
    """String calculator built with TDD"""

    def add(self, numbers: str) -> int:
        if not numbers:
            return 0

        numbers = numbers.replace('\n', ',')
        nums = [int(n) for n in numbers.split(',')]

        # Check for negatives
        negatives = [n for n in nums if n < 0]
        if negatives:
            raise ValueError(f"negatives not allowed: {negatives[0]}")

        return sum(nums)


# ======================
# ITERATION 7: RED PHASE
# ======================
# Test: Multiple negatives in exception message

def test_multiple_negatives_in_exception():
    """Given multiple negatives, when add called, then shows all in error"""
    calc = StringCalculator()

    with pytest.raises(ValueError, match="negatives not allowed: -1, -3"):
        calc.add("1,-1,2,-3")


# ======================
# ITERATION 7: GREEN PHASE & REFACTOR
# ======================

class StringCalculator:
    """String calculator built with TDD - final version"""

    def add(self, numbers: str) -> int:
        """
        Add numbers from comma or newline separated string.

        Args:
            numbers: String containing numbers separated by commas or newlines

        Returns:
            Sum of all numbers

        Raises:
            ValueError: If negative numbers are present
        """
        if not numbers:
            return 0

        nums = self._parse_numbers(numbers)
        self._validate_no_negatives(nums)
        return sum(nums)

    def _parse_numbers(self, numbers: str) -> list[int]:
        """Parse string into list of integers"""
        numbers = numbers.replace('\n', ',')
        return [int(n) for n in numbers.split(',')]

    def _validate_no_negatives(self, nums: list[int]) -> None:
        """Raise ValueError if any negative numbers"""
        negatives = [n for n in nums if n < 0]
        if negatives:
            neg_str = ', '.join(str(n) for n in negatives)
            raise ValueError(f"negatives not allowed: {neg_str}")


# ============================================================================
# COMPLETE TEST SUITE
# ============================================================================

class TestStringCalculator:
    """Complete test suite showing TDD progression"""

    def test_empty_string_returns_zero(self):
        calc = StringCalculator()
        assert calc.add("") == 0

    def test_single_number_returns_value(self):
        calc = StringCalculator()
        assert calc.add("1") == 1
        assert calc.add("5") == 5

    def test_two_numbers_returns_sum(self):
        calc = StringCalculator()
        assert calc.add("1,2") == 3
        assert calc.add("5,10") == 15

    def test_multiple_numbers_returns_sum(self):
        calc = StringCalculator()
        assert calc.add("1,2,3") == 6
        assert calc.add("1,2,3,4,5") == 15

    def test_newline_delimiter(self):
        calc = StringCalculator()
        assert calc.add("1\n2,3") == 6

    def test_negative_number_raises_exception(self):
        calc = StringCalculator()
        with pytest.raises(ValueError, match="negatives not allowed: -1"):
            calc.add("-1,2")

    def test_multiple_negatives_in_exception(self):
        calc = StringCalculator()
        with pytest.raises(ValueError, match="negatives not allowed: -1, -3"):
            calc.add("1,-1,2,-3")

    @pytest.mark.parametrize("input,expected", [
        ("", 0),
        ("1", 1),
        ("1,2", 3),
        ("1,2,3,4,5", 15),
        ("1\n2,3", 6),
    ])
    def test_various_inputs(self, input, expected):
        """Parameterized tests for various valid inputs"""
        calc = StringCalculator()
        assert calc.add(input) == expected


# ============================================================================
# KEY TAKEAWAYS
# ============================================================================

"""
TDD Lessons from this example:

1. START SIMPLE
   - First test: empty string
   - Don't try to solve everything at once

2. INCREMENTAL PROGRESS
   - Each test adds one new behavior
   - Implementation grows organically

3. RED-GREEN-REFACTOR CYCLE
   - Write failing test (RED)
   - Make it pass simply (GREEN)
   - Improve design (REFACTOR)

4. TESTS DRIVE DESIGN
   - Public API emerged from tests
   - Private methods extracted during refactoring
   - Code is testable by definition

5. CONFIDENCE IN REFACTORING
   - Tests enable fearless refactoring
   - Can improve design without breaking functionality
   - Regression safety built-in

6. DOCUMENTATION
   - Tests serve as living documentation
   - Examples of how to use the API
   - Expected behaviors clearly specified

COMPARISON: Before TDD vs After TDD

Before TDD:
- All logic in one method
- Hard to test
- Unclear what it supports
- Difficult to modify
- No safety net

After TDD:
- Clean, focused methods
- 100% test coverage
- Clear API and behavior
- Easy to extend
- Comprehensive test suite

TIME INVESTMENT:
- More time upfront writing tests
- MUCH less time debugging
- MUCH less time fixing regressions
- Net productivity gain over project lifetime
"""
