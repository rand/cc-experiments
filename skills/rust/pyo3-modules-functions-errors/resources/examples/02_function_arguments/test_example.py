"""Tests for function_arguments example."""

import pytest
import function_arguments as fa


def test_greet_person_without_age():
    """Test greeting without age."""
    assert fa.greet_person("Alice") == "Hello, Alice"


def test_greet_person_with_age():
    """Test greeting with age."""
    assert fa.greet_person("Bob", 25) == "Bob is 25 years old"
    assert fa.greet_person("Charlie", age=30) == "Charlie is 30 years old"


def test_power_defaults():
    """Test power function with default arguments."""
    assert fa.power(3) == 9  # 3^2
    assert fa.power(5, 3) == 125  # 5^3
    assert fa.power(10, 2, 7) == 2  # 10^2 % 7 = 100 % 7 = 2


def test_power_with_kwargs():
    """Test power function with keyword arguments."""
    assert fa.power(base=2, exponent=10) == 1024
    assert fa.power(base=7, exponent=3, modulo=10) == 3


def test_process_text_defaults():
    """Test text processing with defaults."""
    assert fa.process_text("  hello  ") == "hello"


def test_process_text_uppercase():
    """Test text processing with uppercase."""
    assert fa.process_text("hello", uppercase=True) == "HELLO"
    assert fa.process_text("  world  ", uppercase=True, trim=True) == "WORLD"


def test_process_text_repeat():
    """Test text processing with repetition."""
    assert fa.process_text("ab", repeat=3) == "ababab"
    assert fa.process_text("x", uppercase=True, repeat=4) == "XXXX"


def test_process_text_keyword_only():
    """Test that process_text parameters are keyword-only."""
    # This should work
    fa.process_text("test", uppercase=True)

    # Positional arguments after text should fail
    with pytest.raises(TypeError):
        fa.process_text("test", True)  # uppercase as positional


def test_sum_numbers():
    """Test variable positional arguments."""
    assert fa.sum_numbers() == 0
    assert fa.sum_numbers(1) == 1
    assert fa.sum_numbers(1, 2, 3) == 6
    assert fa.sum_numbers(10, 20, 30, 40) == 100


def test_uppercase_keys():
    """Test variable keyword arguments."""
    result = fa.uppercase_keys()
    assert result == {}

    result = fa.uppercase_keys(name="Alice", age=30)
    assert result == {"NAME": "Alice", "AGE": 30}

    result = fa.uppercase_keys(a=1, b=2, c=3)
    assert result == {"A": 1, "B": 2, "C": 3}


def test_combine_args():
    """Test combining *args and **kwargs."""
    result = fa.combine_args("Items")
    assert result["text"] == "Items: "

    result = fa.combine_args("Numbers", 1, 2, 3)
    assert result["text"] == "Numbers: 1, 2, 3"

    result = fa.combine_args("Letters", "a", "b", "c", separator=" | ")
    assert result["text"] == "Letters: a | b | c"

    result = fa.combine_args("Data", "x", "y", flag=True, count=5)
    assert "options" in result
    assert result["options"]["flag"] is True
    assert result["options"]["count"] == 5


def test_complex_signature():
    """Test complex function signature."""
    # Only required argument
    result = fa.complex_signature(100)
    assert result["required"] == 100
    assert result["optional"] is None
    assert result["with_default"] == 42
    assert result["keyword_only"] == "default"

    # With optional
    result = fa.complex_signature(100, "test")
    assert result["optional"] == "test"

    # With all positional
    result = fa.complex_signature(100, "test", 99)
    assert result["with_default"] == 99

    # With keyword-only
    result = fa.complex_signature(100, keyword_only="custom")
    assert result["keyword_only"] == "custom"

    # Full specification
    result = fa.complex_signature(
        100, "optional_val", 50, keyword_only="kw_val"
    )
    assert result["required"] == 100
    assert result["optional"] == "optional_val"
    assert result["with_default"] == 50
    assert result["keyword_only"] == "kw_val"


def test_make_config_minimal():
    """Test config creation with minimal arguments."""
    config = fa.make_config("MyConfig")
    assert "Config: MyConfig" in config
    assert "Enabled: True" in config


def test_make_config_full():
    """Test config creation with all arguments."""
    config = fa.make_config(
        "FullConfig",
        values=["a", "b", "c"],
        enabled=False,
        tags=["prod", "critical"]
    )
    assert "Config: FullConfig" in config
    assert "Enabled: False" in config
    assert "Values: a, b, c" in config
    assert "Tags: prod, critical" in config


def test_make_config_keyword_only_tags():
    """Test that tags must be keyword-only."""
    # This should work
    fa.make_config("Test", tags=["tag1"])

    # Positional tags should fail
    with pytest.raises(TypeError):
        fa.make_config("Test", ["val1"], True, ["tag1"])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
