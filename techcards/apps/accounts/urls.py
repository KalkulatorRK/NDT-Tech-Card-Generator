from django.urls import path
from . import views

app_name = "accounts"

urlpatterns = [
    path("", views.CabinetView.as_view(), name="cabinet"),
    path("profile/edit/", views.ProfileUpdateView.as_view(), name="profile_edit"),
]
