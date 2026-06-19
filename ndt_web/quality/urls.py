"""URL-маршруты приложения «Оценка качества»."""

from django.urls import path
from . import views

urlpatterns = [
    path('', views.quality_form_view, name='quality_form'),
    path('<int:pk>/pdf/', views.download_assessment_pdf_view, name='quality_pdf'),
]
