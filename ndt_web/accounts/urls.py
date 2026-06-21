"""URL-маршруты приложения «Аккаунты»."""

from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register_view, name='register'),
    path('register/complete/', views.registration_complete_view, name='registration_complete'),
    path('verify/<uidb64>/<token>/', views.verify_email_view, name='verify_email'),
    path('resend-verification/', views.resend_verification_view, name='resend_verification'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/edit/', views.profile_edit_view, name='profile_edit'),
    path('password/change/', views.password_change_view, name='password_change'),
]

# Личный кабинет подключён через основной URL-конфигуратор (cabinet/)
