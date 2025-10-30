"""Mixed Rust/Python package.

This package combines fast Rust implementations (in _core) with
a convenient Python API and pure Python utilities.
"""

from typing import List, Tuple

# Import Rust core functions
from ._core import fibonacci as _rust_fibonacci
from ._core import gcd as _rust_gcd
from ._core import sum_range as _rust_sum_range

__version__ = "0.1.0"
__all__ = ["fibonacci", "gcd", "lcm", "sum_range", "fibonacci_sequence", "MathUtils"]


def fibonacci(n: int) -> int:
    """Calculate the nth Fibonacci number.

    This is a Python wrapper around the fast Rust implementation.

    Args:
        n: Position in Fibonacci sequence (0-indexed)

    Returns:
        The nth Fibonacci number

    Raises:
        ValueError: If n is negative

    Example:
        >>> fibonacci(10)
        55
    """
    if n < 0:
        raise ValueError("n must be non-negative")
    return _rust_fibonacci(n)


def gcd(a: int, b: int) -> int:
    """Calculate the greatest common divisor of two numbers.

    Args:
        a: First number
        b: Second number

    Returns:
        GCD of a and b

    Example:
        >>> gcd(48, 18)
        6
    """
    return _rust_gcd(a, b)


def lcm(a: int, b: int) -> int:
    """Calculate the least common multiple of two numbers.

    This is a pure Python function that uses the Rust GCD implementation.

    Args:
        a: First number
        b: Second number

    Returns:
        LCM of a and b

    Example:
        >>> lcm(12, 18)
        36
    """
    if a == 0 or b == 0:
        return 0
    return abs(a * b) // gcd(a, b)


def sum_range(start: int, end: int) -> int:
    """Sum all integers in a range [start, end).

    Args:
        start: Start of range (inclusive)
        end: End of range (exclusive)

    Returns:
        Sum of all integers in the range

    Example:
        >>> sum_range(1, 101)
        5050
    """
    return _rust_sum_range(start, end)


def fibonacci_sequence(n: int) -> List[int]:
    """Generate the first n Fibonacci numbers.

    This pure Python function calls the Rust fibonacci implementation
    for each value.

    Args:
        n: Number of Fibonacci numbers to generate

    Returns:
        List of first n Fibonacci numbers

    Example:
        >>> fibonacci_sequence(7)
        [0, 1, 1, 2, 3, 5, 8]
    """
    return [fibonacci(i) for i in range(n)]


class MathUtils:
    """Pure Python utility class demonstrating Python-only code.

    This class shows how to include pure Python functionality
    alongside Rust extensions.
    """

    @staticmethod
    def is_even(n: int) -> bool:
        """Check if a number is even.

        Args:
            n: Number to check

        Returns:
            True if n is even, False otherwise
        """
        return n % 2 == 0

    @staticmethod
    def factorize(n: int) -> List[Tuple[int, int]]:
        """Prime factorization of a number.

        Args:
            n: Number to factorize

        Returns:
            List of (prime, exponent) tuples

        Example:
            >>> MathUtils.factorize(60)
            [(2, 2), (3, 1), (5, 1)]
        """
        if n <= 1:
            return []

        factors = []
        d = 2
        while d * d <= n:
            exponent = 0
            while n % d == 0:
                n //= d
                exponent += 1
            if exponent > 0:
                factors.append((d, exponent))
            d += 1

        if n > 1:
            factors.append((n, 1))

        return factors
