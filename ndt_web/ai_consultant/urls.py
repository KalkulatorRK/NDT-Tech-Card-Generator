from django.urls import path
from ai_consultant import views

app_name = 'ai_consultant'

urlpatterns = [
    path('consultant/', views.chat_page_view, name='chat'),
    path('api/consultant/ask/', views.ask_view, name='ask'),
]
