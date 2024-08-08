"""
This file is for routing to the consumer
"""
from django.urls import path, re_path

from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/waiting/(?P<room_name>\w+)/(?P<character_id>\w+)/$', consumers.WaitingConsumer.as_asgi()),
]
