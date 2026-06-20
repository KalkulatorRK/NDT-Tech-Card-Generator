"""URL-маршруты форума."""
from django.urls import path
from . import views

urlpatterns = [
    path('', views.forum_index, name='forum_index'),
    path('room/<int:room_id>/', views.chat_room_view, name='chat_room'),
    path('private/', views.private_chat_view, name='private_chat'),
    path('create/', views.create_room_view, name='create_room'),
    # AJAX
    path('room/<int:room_id>/send/', views.send_message_view, name='send_message'),
    path('room/<int:room_id>/poll/', views.get_new_messages_view, name='poll_messages'),
    path('unread/', views.get_unread_counts_view, name='unread_counts'),
]
