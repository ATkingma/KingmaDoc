import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from shop.models import Customer, Order
from shop.services import OrderError, mark_paid, place_order


@login_required
@require_POST
def create_order(request):
    customer = Customer.objects.get(email=request.user.email)
    items = [(i["product"], i["quantity"]) for i in json.loads(request.body)["items"]]
    try:
        order = place_order(customer, items)
    except OrderError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    return JsonResponse({"id": order.pk, "total": str(order.total)}, status=201)


@login_required
@require_POST
def pay_order(request, order_id):
    order = Order.objects.get(pk=order_id, customer__email=request.user.email)
    try:
        mark_paid(order)
    except OrderError as exc:
        return JsonResponse({"error": str(exc)}, status=409)
    return JsonResponse({"id": order.pk, "status": order.status})
