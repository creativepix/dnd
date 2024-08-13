from django.contrib import admin
from django.urls import path, include
from . import views as chat_views

urlpatterns = [
    path('', chat_views.chat_home, name='chat-home'),
    path('rooms/<str:room_name>/', chat_views.dnd_room, name='chat-room'),
    path('api/get_transcript', chat_views.get_transcript, name='get-transcript'),
]
