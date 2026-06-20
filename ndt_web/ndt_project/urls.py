"""
Главная конфигурация URL-маршрутов приложения «НК-Карта».
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView

# Настройка заголовка административного сайта
admin.site.site_header = 'НК-Карта — Администрирование'
admin.site.site_title = 'НК-Карта'
admin.site.index_title = 'Панель управления'

urlpatterns = [
    # Административная панель
    path('admin/', admin.site.urls),

    # Главная страница
    path('', include('techcards.urls')),

    # Аутентификация и личный кабинет
    path('accounts/', include('accounts.urls')),

    # Оценка качества
    path('quality/', include('quality.urls')),

    # Платежи
    path('payments/', include('payments.urls')),

    # Форум и чаты
    path('forum/', include('forum.urls')),

    # Контакты
    path('contacts/', TemplateView.as_view(template_name='contacts.html'), name='contacts'),
]

# Раздача медиафайлов в режиме разработки
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
