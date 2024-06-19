from django.urls import path
from . import consumers

websocket_urlpatterns = [
    path('ws/sensor-data/', consumers.SensorDataConsumer.as_asgi()),
]
