from decimal import Decimal

from django.db import transaction

from shop.models import Order, OrderLine, Product


class OrderError(Exception):
    pass


@transaction.atomic
def place_order(customer, items):
    """Create an order for (product_id, quantity) pairs and reserve the stock."""
    if not items:
        raise OrderError("An order needs at least one product.")
    order = Order.objects.create(customer=customer)
    total = Decimal("0")
    for product_id, quantity in items:
        product = Product.objects.select_for_update().get(pk=product_id)
        if quantity > product.stock:
            raise OrderError(f"Only {product.stock} of {product.name} left.")
        product.stock -= quantity
        product.save()
        OrderLine.objects.create(order=order, product=product, quantity=quantity)
        total += product.price * quantity
    order.total = total
    order.save()
    return order


def mark_paid(order):
    if order.status != "new":
        raise OrderError("Only new orders can be paid.")
    order.status = "paid"
    order.save()
