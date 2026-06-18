"""Main URL configuration for NDT Tech Cards application."""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    # allauth authentication
    path("accounts/", include("allauth.urls")),
    # Local apps
    path("", include("apps.core.urls")),
    path("cards/", include("apps.cards.urls")),
    path("quality/", include("apps.quality.urls")),
    path("payments/", include("apps.payments.urls")),
    path("cabinet/", include("apps.accounts.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
