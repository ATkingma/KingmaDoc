from django.urls import path

from shop import views

urlpatterns = [
    path("orders/", views.create_order),
    path("orders/<int:order_id>/pay/", views.pay_order),
]
