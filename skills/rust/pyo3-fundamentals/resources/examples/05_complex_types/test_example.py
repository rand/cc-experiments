"""Test suite for complex_types module."""

import pytest
import complex_types as ct


def test_safe_divide():
    result = ct.safe_divide(10, 2)
    assert result.success
    assert result.value == 5

    result = ct.safe_divide(10, 0)
    assert not result.success
    assert result.value is None


def test_parse_int():
    assert ct.parse_int("42") == 42
    assert ct.parse_int("invalid") is None


def test_address():
    addr = ct.Address("123 Main St", "NYC", "10001", "USA")
    assert addr.city == "NYC"


def test_user():
    user = ct.User(1, "Alice", "alice@test.com", 30, None)
    assert user.name == "Alice"
    assert user.has_email()
    assert not user.has_address()


def test_message():
    msg = ct.Message.info("Test message")
    assert msg.msg_type == "INFO"


def test_datastore():
    store = ct.DataStore()
    store.add_value("key1", 10)
    store.add_value("key1", 20)
    assert ct.DataStore.get_sum(store, "key1") == 30


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
