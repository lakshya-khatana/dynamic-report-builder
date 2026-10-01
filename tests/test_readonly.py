import pytest

from errors.exceptions import ReadOnlyViolationError
from security.readonly import check_readonly


def test_select_passes():
    check_readonly("SELECT * FROM orders WHERE amount > 100")


def test_insert_blocked():
    with pytest.raises(ReadOnlyViolationError):
        check_readonly("INSERT INTO orders (id) VALUES (1)")


def test_drop_blocked():
    with pytest.raises(ReadOnlyViolationError):
        check_readonly("DROP TABLE orders")


def test_column_named_like_keyword_not_falsely_blocked():
    # "updates" contains "UPDATE" as a substring but is a legit table/column name
    check_readonly("SELECT * FROM updates WHERE id = 1")
