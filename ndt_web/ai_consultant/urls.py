from django.urls import path
from ai_consultant import views
from django.views.generic import RedirectView

app_name = 'ai_consultant'

urlpatterns = [
    path('consultant/', views.chat_page_view, name='chat'),
    path('api/consultant/ask/', views.ask_view, name='ask'),
    path('consult/', RedirectView.as_view(pattern_name='ai_consultant:chat', permanent=True), name='consult_short'),
]
