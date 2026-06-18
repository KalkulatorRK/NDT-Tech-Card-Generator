from django.urls import path
from . import views

app_name = "quality"

urlpatterns = [
    path("", views.quality_home, name="home"),
    path("<int:doc_id>/", views.quality_assess, name="assess"),
]
