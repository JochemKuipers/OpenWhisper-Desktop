from django.urls import path

from openwhisper.apps.chat import consumers

websocket_urlpatterns = [
    path("ws/social/", consumers.SocialConsumer.as_asgi()),  # type: ignore[arg-type]
    # ASGI consumer, not an HttpResponse view; django-stubs types path() as URL patterns only.
    path("ws/chats/<int:chat_id>/", consumers.ChatConsumer.as_asgi()),  # type: ignore[arg-type]
]
