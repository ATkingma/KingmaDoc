from decimal import Decimal

# Orders of at least this amount get the discount.
DISCOUNT_THRESHOLD = Decimal("100")
DISCOUNT_RATE = Decimal("0.10")


def apply_discount(total):
    """10% off orders of 100 or more."""
    if total >= DISCOUNT_THRESHOLD:
        return (total * (1 - DISCOUNT_RATE)).quantize(Decimal("0.01"))
    return total
