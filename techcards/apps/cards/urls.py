from django.urls import path
from . import views

app_name = "cards"

urlpatterns = [
    path("", views.card_wizard_step1, name="wizard_step1"),
    path("<int:doc_id>/input/", views.card_wizard_step2, name="wizard_step2"),
    path("<int:pk>/", views.card_detail, name="card_detail"),
    path("<int:pk>/download/docx/", views.card_download_docx, name="download_docx"),
    path("<int:pk>/download/pdf/", views.card_download_pdf, name="download_pdf"),
    path("<int:pk>/delete/", views.card_delete, name="card_delete"),
    path("example/", views.card_example, name="card_example"),
]
