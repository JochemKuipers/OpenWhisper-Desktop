from django.urls import include, path
from rest_framework import routers
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from openwhisper.apps.api.views import ChatViewSet, MessageViewSet, UserViewSet, UserChatsAPIView, ChatMessagesAPIView

router = routers.DefaultRouter()
router.register(r"users", UserViewSet, basename="user")
router.register(r"chats", ChatViewSet, basename="chat")
router.register(r"messages", MessageViewSet, basename="message")

urlpatterns = [
    path("", include(router.urls)),
    path("chats/<int:user_id>/", UserChatsAPIView.as_view(), name="user-chats"),
    path("chats/<int:chat_id>/messages/", ChatMessagesAPIView.as_view(), name="chat-messages"),
    path("token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
]
