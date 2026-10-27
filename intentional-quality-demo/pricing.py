"""Checkout rules for a Philippine online shop. This is the code under test."""


def discount(total):
    """10% promo on orders of PHP 1,000 or more."""
    if total < 0:
        raise ValueError("total cannot be negative")
    if total >= 1000:
        return round(total * 0.9, 2)
    return total


def shipping_fee(total, in_metro_manila):
    """Free shipping from PHP 1,500. Otherwise PHP 99 in Metro Manila, PHP 149 elsewhere."""
    if total >= 1500:
        return 0
    return 99 if in_metro_manila else 149


def loyalty_points(total):
    """1 point per PHP 100 spent, capped at 50 points per order."""
    points = total // 100
    if points > 50:
        points = 50
    return points
