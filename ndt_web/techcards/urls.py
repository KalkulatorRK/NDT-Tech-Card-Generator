"""URL-маршруты приложения «Технологические карты»."""

from django.urls import path
from . import views

urlpatterns = [
    # Главная страница
    path('', views.home_view, name='home'),

    # Личный кабинет
    path('cabinet/', views.cabinet_view, name='cabinet'),

    # Список техкарт
    path('techcards/', views.techcard_list_view, name='techcard_list'),

    # Выбор метода и документа
    path('techcards/method/', views.method_select_view, name='method_select'),

    # Многошаговая форма создания техкарты
    path('techcards/create/<str:doc_code>/step1/', views.create_step1_view, name='create_step1'),
    path('techcards/create/<str:doc_code>/step2/', views.create_step2_view, name='create_step2'),
    path('techcards/create/<str:doc_code>/step3/', views.create_step3_view, name='create_step3'),
    path('techcards/create/<str:doc_code>/step4/', views.create_step4_view, name='create_step4'),
    path('techcards/generate/<str:doc_code>/', views.generate_card_view, name='generate_card'),

    # Просмотр, скачивание, удаление
    path('techcards/<int:pk>/', views.techcard_detail_view, name='techcard_detail'),
    path('techcards/<int:pk>/download/<str:file_type>/', views.download_file_view, name='download_file'),
    path('techcards/<int:pk>/delete/', views.delete_techcard_view, name='delete_techcard'),

    # AJAX
    path('ajax/sources/', views.get_sources_ajax, name='ajax_sources'),
    path('ajax/joint-zones/', views.get_joint_zones_ajax, name='ajax_joint_zones'),
]
