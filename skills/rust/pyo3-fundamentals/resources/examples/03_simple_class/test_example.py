"""
Test suite for simple_class PyO3 module.

Run with: pytest test_example.py -v
Build first: maturin develop
"""

import pytest
import simple_class as sc


class TestCounter:
    """Test Counter class."""

    def test_create_counter(self):
        """Test counter creation."""
        c1 = sc.Counter()
        assert c1.value == 0

        c2 = sc.Counter(10)
        assert c2.value == 10

    def test_increment_decrement(self):
        """Test increment and decrement."""
        c = sc.Counter(5)
        c.increment()
        assert c.value == 6
        c.decrement()
        assert c.value == 5

    def test_add(self):
        """Test adding to counter."""
        c = sc.Counter(10)
        c.add(5)
        assert c.value == 15
        c.add(-3)
        assert c.value == 12

    def test_reset(self):
        """Test reset."""
        c = sc.Counter(42)
        c.reset()
        assert c.value == 0

    def test_get_value(self):
        """Test immutable get_value method."""
        c = sc.Counter(7)
        assert c.get_value() == 7

    def test_repr_str(self):
        """Test string representations."""
        c = sc.Counter(5)
        assert repr(c) == "Counter(value=5)"
        assert str(c) == "Counter: 5"


class TestPoint:
    """Test Point class."""

    def test_create_point(self):
        """Test point creation."""
        p = sc.Point(3.0, 4.0)
        assert p.x == 3.0
        assert p.y == 4.0

    def test_distance_from_origin(self):
        """Test distance calculation from origin."""
        p = sc.Point(3.0, 4.0)
        assert abs(p.distance_from_origin() - 5.0) < 1e-10

    def test_distance_from(self):
        """Test distance between two points."""
        p1 = sc.Point(0.0, 0.0)
        p2 = sc.Point(3.0, 4.0)
        assert abs(p1.distance_from(p2) - 5.0) < 1e-10

    def test_move_by(self):
        """Test moving point."""
        p = sc.Point(1.0, 2.0)
        p.move_by(3.0, 4.0)
        assert p.x == 4.0
        assert p.y == 6.0

    def test_origin(self):
        """Test static method for origin."""
        p = sc.Point.origin()
        assert p.x == 0.0
        assert p.y == 0.0

    def test_repr(self):
        """Test string representation."""
        p = sc.Point(1.5, 2.5)
        assert repr(p) == "Point(x=1.5, y=2.5)"


class TestPerson:
    """Test Person class."""

    def test_create_person(self):
        """Test person creation."""
        p = sc.Person("Alice", 30)
        assert p.name == "Alice"
        assert p.age == 30

    def test_empty_name_error(self):
        """Test that empty name raises error."""
        with pytest.raises(ValueError, match="Name cannot be empty"):
            sc.Person("", 25)

    def test_greet(self):
        """Test greeting method."""
        p = sc.Person("Bob", 25)
        assert p.greet() == "Hello, I'm Bob and I'm 25 years old."

    def test_is_adult(self):
        """Test adult check."""
        p1 = sc.Person("Child", 15)
        assert not p1.is_adult()

        p2 = sc.Person("Adult", 18)
        assert p2.is_adult()

    def test_birthday(self):
        """Test birthday method."""
        p = sc.Person("Alice", 29)
        p.birthday()
        assert p.age == 30

    def test_name_immutable(self):
        """Test that name is read-only."""
        p = sc.Person("Alice", 30)
        # Name should be read-only (get but not set)
        with pytest.raises(AttributeError):
            p.name = "Bob"


class TestBankAccount:
    """Test BankAccount class."""

    def test_create_account(self):
        """Test account creation."""
        acc1 = sc.BankAccount("ACC001")
        assert acc1.get_balance() == 0.0

        acc2 = sc.BankAccount("ACC002", 100.0)
        assert acc2.get_balance() == 100.0

    def test_negative_initial_balance(self):
        """Test that negative initial balance raises error."""
        with pytest.raises(ValueError, match="Initial balance cannot be negative"):
            sc.BankAccount("ACC001", -100.0)

    def test_deposit(self):
        """Test deposit."""
        acc = sc.BankAccount("ACC001", 100.0)
        acc.deposit(50.0)
        assert acc.get_balance() == 150.0

    def test_deposit_negative(self):
        """Test that negative deposit raises error."""
        acc = sc.BankAccount("ACC001", 100.0)
        with pytest.raises(ValueError, match="Deposit amount must be positive"):
            acc.deposit(-10.0)

    def test_withdraw(self):
        """Test withdrawal."""
        acc = sc.BankAccount("ACC001", 100.0)
        acc.withdraw(30.0)
        assert acc.get_balance() == 70.0

    def test_withdraw_insufficient_funds(self):
        """Test that overdraft raises error."""
        acc = sc.BankAccount("ACC001", 50.0)
        with pytest.raises(ValueError, match="Insufficient funds"):
            acc.withdraw(100.0)

    def test_transfer(self):
        """Test transfer between accounts."""
        acc1 = sc.BankAccount("ACC001", 100.0)
        acc2 = sc.BankAccount("ACC002", 50.0)

        acc1.transfer(acc2, 30.0)
        assert acc1.get_balance() == 70.0
        assert acc2.get_balance() == 80.0

    def test_transfer_insufficient_funds(self):
        """Test that transfer with insufficient funds raises error."""
        acc1 = sc.BankAccount("ACC001", 20.0)
        acc2 = sc.BankAccount("ACC002", 50.0)

        with pytest.raises(ValueError, match="Insufficient funds"):
            acc1.transfer(acc2, 30.0)


class TestRectangle:
    """Test Rectangle class."""

    def test_create_rectangle(self):
        """Test rectangle creation."""
        r = sc.Rectangle(4.0, 5.0)
        assert r.width == 4.0
        assert r.height == 5.0

    def test_invalid_dimensions(self):
        """Test that non-positive dimensions raise error."""
        with pytest.raises(ValueError, match="Width and height must be positive"):
            sc.Rectangle(0.0, 5.0)

        with pytest.raises(ValueError, match="Width and height must be positive"):
            sc.Rectangle(4.0, -1.0)

    def test_area(self):
        """Test area calculation."""
        r = sc.Rectangle(4.0, 5.0)
        assert r.area() == 20.0

    def test_perimeter(self):
        """Test perimeter calculation."""
        r = sc.Rectangle(4.0, 5.0)
        assert r.perimeter() == 18.0

    def test_is_square(self):
        """Test square detection."""
        r1 = sc.Rectangle(5.0, 5.0)
        assert r1.is_square()

        r2 = sc.Rectangle(4.0, 5.0)
        assert not r2.is_square()

    def test_scale(self):
        """Test scaling."""
        r = sc.Rectangle(4.0, 5.0)
        r.scale(2.0)
        assert r.width == 8.0
        assert r.height == 10.0

    def test_scale_negative(self):
        """Test that negative scale factor raises error."""
        r = sc.Rectangle(4.0, 5.0)
        with pytest.raises(ValueError, match="Scale factor must be positive"):
            r.scale(-1.0)

    def test_square_static_method(self):
        """Test static square constructor."""
        r = sc.Rectangle.square(5.0)
        assert r.width == 5.0
        assert r.height == 5.0
        assert r.is_square()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
