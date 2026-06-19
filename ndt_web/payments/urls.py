"""URL-маршруты приложения «Платежи»."""

from django.urls import path
from . import views

urlpatterns = [
    path('', views.tariffs_view, name='tariffs'),
    path('<int:tariff_id>/checkout/', views.checkout_view, name='checkout'),
    path('success/<int:payment_id>/', views.payment_success_view, name='payment_success'),
    path('webhook/yookassa/', views.yookassa_webhook_view, name='yookassa_webhook'),
]
