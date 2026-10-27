"""The team's existing test suite: 100% line coverage, every test green.

Plain asserts, so it runs with pytest or with the demo's own runner.
"""
from pricing import discount, shipping_fee, loyalty_points


def test_discount_big_order():
    assert discount(2000) == 1800


def test_discount_small_order():
    assert discount(500) == 500


def test_discount_rejects_negative():
    try:
        discount(-5)
    except ValueError:
        return
    raise AssertionError("expected ValueError")


def test_free_shipping():
    assert shipping_fee(2000, True) == 0


def test_shipping_metro_manila():
    assert shipping_fee(500, True) == 99


def test_shipping_province():
    assert shipping_fee(500, False) == 149


def test_points():
    assert loyalty_points(1200) == 12


def test_points_cap():
    assert loyalty_points(9000) == 50
