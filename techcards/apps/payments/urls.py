from django.urls import path
from . import views

app_name = "payments"

urlpatterns = [
    path("", views.tariff_list, name="tariffs"),
    path("<int:tariff_pk>/pay/", views.initiate_payment, name="pay"),
    path("return/<int:pk>/", views.payment_return, name="payment_return"),
    path("webhook/yookassa/", views.yookassa_webhook, name="yookassa_webhook"),
    path("history/", views.payment_history, name="history"),
]
